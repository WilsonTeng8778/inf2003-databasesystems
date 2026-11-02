"""Real case orchestration with rollback-capable memory SQL and injected Mongo faults."""

import copy
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock

from bson.json_util import dumps
import json
from psycopg import OperationalError
from pymongo.errors import AutoReconnect, DuplicateKeyError

from backend import create_app
from backend.services.auth import token_hash
from backend.services.cases import CaseService, paged, public_case, public_operation


class MemoryRepository:
    def __init__(self):
        self.cases, self.ops = {}, {}
        self.next_id = 1
        self.fail_stage = self.fail_ack = self.commit_uncertain = False

    @contextmanager
    def transaction(self):
        before = copy.deepcopy((self.cases, self.ops))
        try:
            yield
        except Exception:
            self.cases, self.ops = before
            raise
        if self.commit_uncertain:
            self.commit_uncertain = False
            raise OperationalError('DO_NOT_EXPOSE uncertain committed SQL response')

    def request_lock(self, operation_id):
        pass

    def case(self, actor, case_id, *, lock=False):
        row = self.cases.get(case_id)
        return copy.deepcopy(row) if row and (actor['role'] == 'ADMIN' or row['created_by'] == actor['userId']) else None

    def operation(self, actor, operation_id, *, lock=False):
        row = self.ops.get(operation_id)
        allowed = actor is None or actor['role'] == 'ADMIN' or row and row['owner_id'] == actor['userId']
        return copy.deepcopy(row) if row and allowed else None

    def pending(self, case_id):
        return next((copy.deepcopy(row) for row in self.ops.values() if row['case_id'] == case_id and row['state'] == 'PENDING'), None)

    def create(self, actor, body):
        from backend.services.cases import CaseError
        if body['modelYearId'] != 42:
            raise CaseError(404, 'Vehicle not found in the imported catalogue')
        identifier = self.next_id
        self.next_id += 1
        self.cases[identifier] = {'case_id': identifier, 'model_year_id': 42, 'title': body['title'],
            'created_by': actor['userId'], 'assigned_to': actor['userId'], 'priority': body['priority'],
            'status': 'OPEN', 'content_revision': 1, 'created_at': datetime.now(timezone.utc), 'closed_at': None,
            'make': 'HONDA', 'model': 'CIVIC', 'year': 2022}
        return self.case(actor, identifier)

    def update(self, actor, row, body):
        stored = self.cases[row['case_id']]
        stored.update(body)
        stored['content_revision'] += 1
        stored['closed_at'] = (stored['closed_at'] or datetime.now(timezone.utc)) if stored['status'] == 'CLOSED' else None
        return self.case(actor, row['case_id'])

    def delete(self, row):
        del self.cases[row['case_id']]

    def enqueue(self, operation_id, actor, row, fingerprint, action, document):
        if self.fail_stage:
            self.fail_stage = False
            raise OperationalError('DO_NOT_EXPOSE SQL failure before commit')
        self.ops[operation_id] = {'operation_id': operation_id, 'case_id': row['case_id'], 'owner_id': row['created_by'],
            'requested_by': actor['userId'], 'request_hash': fingerprint, 'revision': row['content_revision'],
            'action': action, 'state': 'PENDING', 'payload': json.loads(dumps(document)) if document else None,
            'last_failure': None, 'created_at': datetime.now(timezone.utc), 'completed_at': None}
        return copy.deepcopy(self.ops[operation_id])

    def acknowledge(self, operation_id):
        self.ops[operation_id].update(state='APPLIED', payload=None, last_failure=None, completed_at=datetime.now(timezone.utc))
        if self.fail_ack:
            self.fail_ack = False
            raise OperationalError('DO_NOT_EXPOSE SQL acknowledgement failure')

    def record_failure(self, operation_id, category):
        if self.ops[operation_id]['state'] == 'PENDING':
            self.ops[operation_id]['last_failure'] = category

    def list_cases(self, actor, page, size):
        rows = [row for row in self.cases.values() if actor['role'] == 'ADMIN' or row['created_by'] == actor['userId']]
        return paged([{**public_case(row), 'syncState': 'PENDING' if self.pending(row['case_id']) else 'APPLIED'}
                      for row in rows[(page-1)*size:page*size]], len(rows), page, size)

    def list_operations(self, actor, state, page, size):
        rows = [row for row in self.ops.values() if row['state'] == state and
                (actor['role'] == 'ADMIN' or row['owner_id'] == actor['userId'])]
        return paged([public_operation(row) for row in rows[(page-1)*size:page*size]], len(rows), page, size)


class CaseTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.documents = MemoryRepository(), {}
        self.database = Mock()
        self.database.case_details.find_one.side_effect = self.find
        self.database.case_details.replace_one.side_effect = self.replace
        self.database.case_details.delete_one.side_effect = self.delete_document
        self.database.complaints.find_one.side_effect = lambda query, *a, **k: {'_id': '123'} if query == {'_id': '123', 'modelYearId': 42} else None
        self.service = CaseService(self.repo, self.database)
        roles = {1: 'ANALYST', 2: 'ANALYST', 3: 'ADMIN', 4: 'NORMAL_USER'}
        self.tokens = {user: chr(96+user)*43 for user in roles}
        self.users = {token_hash(self.tokens[user]): {'userId': user, 'role': role} for user, role in roles.items()}
        auth = Mock()
        auth.session_user.side_effect = lambda digest: self.users.get(digest)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'case-tests-only', 'DUMMY_PASSWORD_HASH': 'unused',
            'MONGO_CLIENT_FACTORY': Mock, 'AUTH_STORE_FACTORY': lambda: auth, 'CASE_SERVICE_FACTORY': lambda: self.service})
        self.clients = {}
        for user, token in self.tokens.items():
            client = self.app.test_client()
            with client.session_transaction() as values:
                values.update(session_token=token, csrf_token='x'*43)
            self.clients[user] = client

    def find(self, query, *args, **kwargs):
        return copy.deepcopy(self.documents.get(query['caseId']))

    def replace(self, query, document, **kwargs):
        old = self.documents.get(query['caseId'])
        if old and old.get('revision', 0) > document['revision']:
            raise DuplicateKeyError('existing newer case revision')
        self.documents[query['caseId']] = copy.deepcopy(document)
        return Mock(acknowledged=True)

    def delete_document(self, query):
        old = self.documents.get(query['caseId'])
        if old and old.get('revision', 0) <= query['$or'][0]['revision']['$lte']:
            del self.documents[query['caseId']]
        return Mock(acknowledged=True)

    def write(self, path='', body=None, method='POST', user=1, key=None, csrf=True):
        headers = {'Idempotency-Key': key or str(uuid4())}
        if csrf:
            headers['X-CSRF-Token'] = 'x'*43
        return self.clients[user].open('/api/analysis-cases' + path, method=method, json=body, headers=headers)

    def create(self, **kwargs):
        return self.write(body={'title': 'Steering case', 'modelYearId': 42}, **kwargs)

    def case_id(self):
        return self.create().json['operation']['caseId']

    def test_anonymous_and_normal_users_are_denied(self):
        self.assertEqual(self.app.test_client().get('/api/analysis-cases').status_code, 401)
        self.assertEqual(self.clients[4].get('/api/analysis-cases').status_code, 403)
        self.assertEqual(self.create(user=4).status_code, 403)
        self.assertEqual(self.repo.cases, {})

    def test_create_get_update_delete_and_private_headers(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        operation = created.json['operation']
        case_id = operation['caseId']
        path = f'/api/analysis-cases/{case_id}'
        self.assertEqual(created.headers['Location'], '/api/analysis-cases/operations/' + operation['operationId'])
        read = self.clients[1].get(path)
        self.assertEqual(read.json['analysisCase']['assignedTo'], 1)
        self.assertEqual(read.json['content']['notes'], [])
        self.assertEqual(read.headers['Cache-Control'], 'no-store')
        self.assertEqual(self.write(f'/{case_id}', {'title': 'Renamed', 'priority': 'HIGH', 'status': 'CLOSED'}, method='PATCH').status_code, 200)
        item = self.clients[1].get(path).json['analysisCase']
        self.assertEqual(item['title'], 'Renamed')
        self.assertIsNotNone(item['closedAt'])
        self.write(f'/{case_id}', {'status': 'OPEN'}, method='PATCH')
        self.assertIsNone(self.clients[1].get(path).json['analysisCase']['closedAt'])
        self.assertEqual(self.write(f'/{case_id}', method='DELETE').status_code, 200)
        self.assertNotIn(case_id, self.documents)
        self.assertEqual(self.clients[1].get(path).status_code, 404)

    def test_other_analyst_cannot_read_edit_delete_or_retry(self):
        response = self.create()
        case_id = response.json['operation']['caseId']
        operation_id = response.json['operation']['operationId']
        self.assertEqual(self.clients[2].get('/api/analysis-cases').json['items'], [])
        for actual in [self.clients[2].get(f'/api/analysis-cases/{case_id}'),
                       self.write(f'/{case_id}', {'title': 'Forbidden'}, method='PATCH', user=2),
                       self.write(f'/{case_id}', method='DELETE', user=2),
                       self.write(f'/operations/{operation_id}/retry', {}, user=2),
                       self.clients[2].get('/api/analysis-cases/operations/' + operation_id)]:
            self.assertEqual(actual.status_code, 404)
        self.assertEqual(self.repo.cases[case_id]['title'], 'Steering case')

    def test_admin_can_manage_and_recover_other_analyst_cases(self):
        case_id = self.case_id()
        self.assertEqual(self.clients[3].get(f'/api/analysis-cases/{case_id}').status_code, 200)
        self.assertEqual(self.write(f'/{case_id}', {'priority': 'HIGH'}, method='PATCH', user=3).status_code, 200)
        self.assertEqual(self.repo.cases[case_id]['created_by'], 1)

    def test_expired_or_demoted_session_cannot_write(self):
        self.users[token_hash(self.tokens[1])]['role'] = 'NORMAL_USER'
        self.assertEqual(self.create().status_code, 403)
        del self.users[token_hash(self.tokens[1])]
        self.assertEqual(self.clients[1].get('/api/analysis-cases').status_code, 401)

    def test_csrf_is_required(self):
        self.assertEqual(self.create(csrf=False).status_code, 403)
        self.assertEqual(self.repo.cases, {})

    def test_missing_or_invalid_idempotency_key_is_rejected(self):
        for key in [None, '', 'not-a-uuid', 'a'*100]:
            headers = {'X-CSRF-Token': 'x'*43}
            if key is not None:
                headers['Idempotency-Key'] = key
            response = self.clients[1].post('/api/analysis-cases', json={'title': 'Case', 'modelYearId': 42}, headers=headers)
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.repo.cases, {})

    def test_create_replay_does_not_create_another_case(self):
        key = str(uuid4())
        first, second = self.create(key=key), self.create(key=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(first.json['operation']['caseId'], second.json['operation']['caseId'])
        self.assertEqual(len(self.repo.cases), 1)
        self.assertEqual(self.database.case_details.replace_one.call_count, 1)

    def test_key_reuse_for_different_body_or_actor_is_conflict(self):
        key = str(uuid4())
        self.create(key=key)
        self.assertEqual(self.write(body={'title': 'Other', 'modelYearId': 42}, key=key).status_code, 409)
        self.assertEqual(self.create(key=key, user=2).status_code, 409)

    def test_link_checks_vehicle_and_unlink_preserves_official_document(self):
        case_id = self.case_id()
        self.assertEqual(self.write(f'/{case_id}/complaints', {'odiNumber': '123'}).status_code, 200)
        self.assertEqual(self.write(f'/{case_id}/complaints', {'odiNumber': '456'}).status_code, 404)
        self.assertEqual(self.documents[case_id]['linkedComplaints'], ['123'])
        self.write(f'/{case_id}/complaints', {'odiNumber': '123'})
        self.assertEqual(self.documents[case_id]['linkedComplaints'], ['123'])
        self.write(f'/{case_id}/complaints/123', method='DELETE')
        self.assertEqual(self.documents[case_id]['linkedComplaints'], [])
        self.database.complaints.delete_one.assert_not_called()

    def test_note_and_finding_nested_crud_keeps_authorship(self):
        case_id = self.case_id()
        for kind, field, id_field in [('notes', 'text', 'noteId'), ('findings', 'observation', 'findingId')]:
            response = self.write(f'/{case_id}/{kind}', {field: 'First\nparagraph'})
            entry_id = response.json['operation']['operationId']
            entry = self.documents[case_id][kind][0]
            self.assertEqual(entry[id_field], entry_id)
            self.assertEqual(entry['authorId'], 1)
            self.assertIsInstance(entry['createdAt'], datetime)
            self.write(f'/{case_id}/{kind}/{entry_id}', {field: 'Edited'}, method='PATCH', user=3)
            self.assertEqual(self.documents[case_id][kind][0]['authorId'], 1)
            self.assertEqual(self.documents[case_id][kind][0][field], 'Edited')
            self.write(f'/{case_id}/{kind}/{entry_id}', method='DELETE')
            self.assertEqual(self.documents[case_id][kind], [])

    def test_note_retry_is_not_a_second_append(self):
        case_id, key = self.case_id(), str(uuid4())
        self.write(f'/{case_id}/notes', {'text': 'One note'}, key=key)
        self.write(f'/{case_id}/notes', {'text': 'One note'}, key=key)
        self.assertEqual(len(self.documents[case_id]['notes']), 1)

    def test_missing_entry_does_not_change_revision(self):
        case_id = self.case_id()
        response = self.write(f'/{case_id}/notes/{uuid4()}', {'text': 'Missing'}, method='PATCH')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.repo.cases[case_id]['content_revision'], 1)

    def test_tags_and_components_are_bounded_and_deduplicated(self):
        case_id = self.case_id()
        response = self.write(f'/{case_id}/content', {'tags': ['review', 'review'], 'suspectedComponents': [' steering ', 'STEERING']}, method='PATCH')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.documents[case_id]['tags'], ['review'])
        self.assertEqual(self.documents[case_id]['suspectedComponents'], ['STEERING'])
        self.write(f'/{case_id}/content', {'tags': [], 'suspectedComponents': []}, method='PATCH')
        self.assertEqual(self.documents[case_id]['tags'], [])

    def test_sql_stage_failure_rolls_back_before_any_mongo_write(self):
        self.repo.fail_stage = True
        key = str(uuid4())
        response = self.create(key=key)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('DO_NOT_EXPOSE', response.get_data(as_text=True))
        self.assertEqual(self.repo.cases, {})
        self.assertEqual(self.repo.ops, {})
        self.database.case_details.replace_one.assert_not_called()
        self.assertEqual(self.create(key=key).status_code, 201)

    def test_uncertain_sql_commit_is_safe_to_retry_with_original_key(self):
        self.repo.commit_uncertain = True
        key = str(uuid4())
        self.assertEqual(self.create(key=key).status_code, 503)
        self.assertEqual(len(self.repo.cases), 1)
        self.assertEqual(self.create(key=key).status_code, 201)
        self.assertEqual(len(self.repo.cases), 1)

    def test_failed_mongo_create_is_pending_and_recoverable_after_new_service(self):
        self.database.case_details.replace_one.side_effect = AutoReconnect('DO_NOT_EXPOSE')
        response = self.create()
        self.assertEqual(response.status_code, 202)
        operation = response.json['operation']
        case_id, operation_id = operation['caseId'], operation['operationId']
        self.assertNotIn('DO_NOT_EXPOSE', response.get_data(as_text=True))
        self.assertIsNotNone(self.repo.ops[operation_id]['payload'])
        read = self.clients[1].get(f'/api/analysis-cases/{case_id}')
        self.assertIsNone(read.json['content'])
        self.assertEqual(read.json['sync']['state'], 'PENDING')
        self.assertEqual(self.write(f'/{case_id}', {'status': 'CLOSED'}, method='PATCH').status_code, 409)
        self.service = CaseService(self.repo, self.database)
        self.database.case_details.replace_one.side_effect = self.replace
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}).status_code, 200)
        self.assertIsNone(self.repo.ops[operation_id]['payload'])
        self.assertEqual(self.clients[1].get(f'/api/analysis-cases/{case_id}').json['content']['revision'], 1)

    def test_mongo_write_then_lost_response_retries_without_duplicates(self):
        def ambiguous(query, document, **kwargs):
            self.replace(query, document, **kwargs)
            raise AutoReconnect('DO_NOT_EXPOSE after successful Mongo write')
        self.database.case_details.replace_one.side_effect = ambiguous
        response = self.create()
        self.assertEqual(response.status_code, 202)
        self.database.case_details.replace_one.side_effect = self.replace
        operation_id = response.json['operation']['operationId']
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}).status_code, 200)
        self.assertEqual(len(self.documents), 1)

    def test_mongo_success_then_sql_ack_failure_keeps_recovery_payload(self):
        self.repo.fail_ack = True
        response = self.create()
        self.assertEqual(response.status_code, 202)
        operation_id = response.json['operation']['operationId']
        self.assertEqual(self.repo.ops[operation_id]['state'], 'PENDING')
        self.assertIsNotNone(self.repo.ops[operation_id]['payload'])
        self.assertEqual(len(self.documents), 1)
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}).status_code, 200)

    def test_pending_delete_retains_owned_task_after_sql_parent_is_gone(self):
        case_id = self.case_id()
        self.database.case_details.delete_one.side_effect = AutoReconnect('unavailable')
        response = self.write(f'/{case_id}', method='DELETE')
        self.assertEqual(response.status_code, 202)
        operation_id = response.json['operation']['operationId']
        self.assertNotIn(case_id, self.repo.cases)
        self.assertIn(case_id, self.documents)
        self.assertEqual(self.clients[1].get('/api/analysis-cases/operations').json['items'][0]['operationId'], operation_id)
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}, user=2).status_code, 404)
        self.database.case_details.delete_one.side_effect = self.delete_document
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}, user=3).status_code, 200)
        self.assertNotIn(case_id, self.documents)

    def test_applied_old_operation_cannot_overwrite_newer_content(self):
        created = self.create()
        case_id, operation_id = created.json['operation']['caseId'], created.json['operation']['operationId']
        self.write(f'/{case_id}/notes', {'text': 'Keep this'})
        self.write(f'/operations/{operation_id}/retry', {})
        self.assertEqual(len(self.documents[case_id]['notes']), 1)
        self.assertEqual(self.documents[case_id]['revision'], 2)

    def test_unacknowledged_mongo_write_does_not_mark_operation_applied(self):
        def unacknowledged(query, document, **kwargs):
            self.replace(query, document, **kwargs)
            return Mock(acknowledged=False)
        self.database.case_details.replace_one.side_effect = unacknowledged
        response = self.create()
        self.assertEqual(response.status_code, 202)
        operation_id = response.json['operation']['operationId']
        self.assertEqual(self.repo.ops[operation_id]['state'], 'PENDING')
        self.database.case_details.replace_one.side_effect = self.replace
        self.assertEqual(self.write(f'/operations/{operation_id}/retry', {}).status_code, 200)

    def test_newer_projection_is_a_pending_conflict_instead_of_an_overwrite(self):
        self.documents[1] = {'caseId': 1, 'revision': 999}
        response = self.create()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json['operation']['lastFailure'], 'CONTENT_CONFLICT')
        self.assertEqual(self.documents[1]['revision'], 999)

    def test_delete_with_lost_mongo_response_is_idempotent(self):
        case_id = self.case_id()
        def ambiguous_delete(query):
            self.delete_document(query)
            raise AutoReconnect('lost deletion response')
        self.database.case_details.delete_one.side_effect = ambiguous_delete
        response = self.write(f'/{case_id}', method='DELETE')
        self.assertEqual(response.status_code, 202)
        self.assertNotIn(case_id, self.documents)
        self.database.case_details.delete_one.side_effect = self.delete_document
        self.assertEqual(self.write('/operations/' + response.json['operation']['operationId'] + '/retry', {}).status_code, 200)

    def test_missing_or_manually_newer_mongo_content_is_not_silently_replaced(self):
        case_id = self.case_id()
        self.documents[case_id]['revision'] = 999
        response = self.write(f'/{case_id}', {'title': 'Do not commit'}, method='PATCH')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.repo.cases[case_id]['title'], 'Steering case')
        del self.documents[case_id]
        self.assertEqual(self.clients[1].get(f'/api/analysis-cases/{case_id}').status_code, 503)

    def test_entry_and_document_size_limits(self):
        case_id = self.case_id()
        self.documents[case_id]['notes'] = [{'noteId': str(uuid4()), 'text': 'x', 'authorId': 1,
                                            'createdAt': datetime.now(timezone.utc)} for _ in range(100)]
        self.assertEqual(self.write(f'/{case_id}/notes', {'text': 'too many'}).status_code, 409)
        self.documents[case_id]['notes'] = [{'noteId': str(uuid4()), 'text': 'x'*520000, 'authorId': 1,
                                            'createdAt': datetime.now(timezone.utc)}]
        self.assertEqual(self.write(f'/{case_id}', {'priority': 'HIGH'}, method='PATCH').status_code, 409)
        self.assertEqual(self.repo.cases[case_id]['priority'], 'MEDIUM')

    def test_create_and_patch_validation_prevents_identity_and_role_spoofing(self):
        for body in [{'title': '', 'modelYearId': 42}, {'title': 'Case', 'modelYearId': True},
                     {'title': 'x'*201, 'modelYearId': 42}, {'title': 'Case', 'modelYearId': 42, 'createdBy': 2},
                     {'title': 'Case', 'modelYearId': 42, 'priority': 'URGENT'}]:
            self.assertEqual(self.write(body=body).status_code, 400)
        case_id = self.case_id()
        for body in [{}, {'assignedTo': 2}, {'createdBy': 2}, {'modelYearId': 43}, {'status': 'INVALID'}, {'title': 'bad\x00'}]:
            self.assertEqual(self.write(f'/{case_id}', body, method='PATCH').status_code, 400)

    def test_content_validation_rejects_mongo_operator_objects_and_bad_arrays(self):
        case_id = self.case_id()
        for path, body, method in [(f'/{case_id}/content', {'tags': {'$ne': None}}, 'PATCH'),
                                   (f'/{case_id}/content', {'tags': ['x']*21}, 'PATCH'),
                                   (f'/{case_id}/content', {'notes': []}, 'PATCH'),
                                   (f'/{case_id}/notes', {'text': {'$set': 'bad'}}, 'POST'),
                                   (f'/{case_id}/notes', {'text': 'x'*4001}, 'POST'),
                                   (f'/{case_id}/findings', {'observation': 'x', 'authorId': 2}, 'POST'),
                                   (f'/{case_id}/complaints', {'odiNumber': 123}, 'POST')]:
            with self.subTest(path=path, body_type=type(body)):
                self.assertEqual(self.write(path, body, method=method).status_code, 400)

    def test_case_and_operation_pagination_and_unknown_queries(self):
        self.create()
        self.create()
        response = self.clients[1].get('/api/analysis-cases?pageSize=1&page=2')
        self.assertEqual(len(response.json['items']), 1)
        self.assertEqual(response.json['pagination']['total'], 2)
        for path in ['/api/analysis-cases?pageSize=101', '/api/analysis-cases?ownerId=2',
                     '/api/analysis-cases?page=10001', '/api/analysis-cases/operations?state=UNKNOWN',
                     '/api/analysis-cases/operations/invalid']:
            self.assertEqual(self.clients[1].get(path).status_code, 400)


if __name__ == '__main__':
    unittest.main()
