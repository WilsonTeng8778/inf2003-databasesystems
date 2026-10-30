"""Real case CRUD, role boundaries and injected cross-database failures with owned cleanup."""

import copy
import getpass
import io
import json
import secrets
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flask import g
from psycopg import OperationalError
from pymongo.errors import AutoReconnect, OperationFailure
from werkzeug.serving import make_server
from backend import create_app
from backend.services.cases import CaseService, PostgresCaseRepository
from project_config import ROOT, case_postgres, mongo_client, mongo_database, postgres
from scripts.support.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_official_records import counts as reference_counts
from scripts import try_cases
from scripts.support.verification_reports import select_report_path


def snapshot():
    result = reference_counts()
    with postgres() as connection:
        for table in ['case_content_operation', 'case_status_history']:
            result[table] = connection.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    return result


def main(argv=None):
    report_path = select_report_path('cases', argv)
    before = snapshot()
    prefix = 'cases-verification-' + uuid4().hex
    emails = [prefix + suffix + '@example.invalid' for suffix in ['-owner', '-other', '-admin', '-normal']]
    password = secrets.token_urlsafe(24)
    faults, checks, assertions, servers = {}, [], [], []

    class FaultRepository(PostgresCaseRepository):
        def enqueue(self, operation_id, *args):
            result = super().enqueue(operation_id, *args)
            if faults.pop('sql_before_commit', None) == operation_id:
                raise OperationalError('Injected SQL failure before commit')
            return result

        def acknowledge(self, operation_id):
            super().acknowledge(operation_id)
            if faults.pop('sql_ack', None) == operation_id:
                raise OperationalError('Injected SQL acknowledgement failure')

    class FaultCollection:
        def __init__(self, collection):
            self.collection = collection

        def __getattr__(self, name):
            return getattr(self.collection, name)

        def replace_one(self, *args, **kwargs):
            mode = faults.pop('mongo_replace', None)
            if mode == 'before':
                raise AutoReconnect('Injected unavailable MongoDB write')
            result = self.collection.replace_one(*args, **kwargs)
            if mode == 'after':
                raise AutoReconnect('Injected lost response after MongoDB write')
            return result

        def delete_one(self, *args, **kwargs):
            if faults.pop('mongo_delete', None):
                raise AutoReconnect('Injected MongoDB delete failure')
            return self.collection.delete_one(*args, **kwargs)

    class FaultDatabase:
        def __init__(self, database):
            self.case_details = FaultCollection(database.case_details)
            self.complaints = database.complaints

    def start_server(*, injected):
        app = create_app()
        if injected:
            def factory():
                g.case_postgres = case_postgres()
                return CaseService(FaultRepository(g.case_postgres), FaultDatabase(mongo_database(app.extensions['mongo_client'])))
            app.config['CASE_SERVICE_FACTORY'] = factory
        server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((app, server, thread))
        return f'http://127.0.0.1:{server.server_port}'

    def request(client, path, expected=200, *, body=None, method='GET', key=None):
        try:
            result = client.request(path, body, method=method, headers={'Idempotency-Key': key} if key else None)
        except ApiError as error:
            result = {'error': str(error)}
        assert client.last_status == expected, f'{method} {path}: HTTP {client.last_status}, expected {expected}: {result}'
        checks.append({'method': method, 'path': path, 'status': expected})
        return result

    def change(client, path, body=None, *, method='POST', expected=200, key=None):
        return request(client, path, expected, body=body, method=method, key=key or str(uuid4()))

    def clone(client):
        other = LocalApi(client.base)
        for cookie in client.cookies:
            other.cookies.set_cookie(copy.copy(cookie))
        other.csrf_token = client.csrf_token
        return other

    users = []
    try:
        base = start_server(injected=True)
        owner, other, admin, normal = [LocalApi(base) for _ in range(4)]
        request(LocalApi(base), '/api/analysis-cases', 401)
        for client, email in zip([owner, other, admin, normal], emails):
            request(client, '/api/auth/csrf')
            users.append(request(client, '/api/auth/register', 201, body={'email': email, 'password': password}, method='POST')['user'])
        with postgres() as connection:
            for user, role in zip(users[:3], ['ANALYST', 'ANALYST', 'ADMIN']):
                connection.execute('UPDATE app_user SET role=%s WHERE user_id=%s', (role, user['userId']))
        request(normal, '/api/analysis-cases', 403)
        change(normal, '/api/analysis-cases', {'title': 'Forbidden', 'modelYearId': 1}, expected=403)
        found = request(owner, '/api/vehicles/search?year=2022&make=HONDA&model=CIVIC')['items'][0]
        vehicle_id = found['modelYearId']
        body = {'title': 'Synthetic steering review', 'modelYearId': vehicle_id}
        key = str(uuid4())
        created = change(owner, '/api/analysis-cases', body, expected=201, key=key)['operation']
        case_id = created['caseId']
        path = f'/api/analysis-cases/{case_id}'
        assert change(owner, '/api/analysis-cases', body, expected=201, key=key)['operation']['caseId'] == case_id
        change(owner, '/api/analysis-cases', {**body, 'title': 'Different'}, expected=409, key=key)
        detail = request(owner, path)
        assert detail['analysisCase']['createdBy'] == users[0]['userId'] and detail['content']['revision'] == 1
        assert owner.last_headers['Cache-Control'] == 'no-store'
        assert request(other, '/api/analysis-cases')['items'] == []
        for client in [other]:
            request(client, path, 404)
            change(client, path, {'title': 'Forbidden'}, method='PATCH', expected=404)
            change(client, path, method='DELETE', expected=404)
            request(client, '/api/analysis-cases/operations/' + created['operationId'], 404)
            change(client, '/api/analysis-cases/operations/' + created['operationId'] + '/retry', {}, expected=404)
        request(admin, path)
        request(other, path + '/history', 404)
        assert request(other, '/api/analysis-cases/operations?state=APPLIED')['items'] == []
        assert request(admin, '/api/analysis-cases')['pagination']['total'] >= 1
        change(admin, path, {'priority': 'HIGH'}, method='PATCH')
        assertions.append('authenticated analyst ownership, normal-user denial, admin oversight, private headers and create idempotency verified')

        complaint = request(owner, '/api/complaints?' + f'modelYearId={vehicle_id}&pageSize=1')['items'][0]['odiNumber']
        change(owner, path + '/complaints', {'odiNumber': complaint})
        change(owner, path + '/complaints', {'odiNumber': complaint})
        assert request(owner, path)['content']['linkedComplaints'] == [complaint]
        with mongo_client() as client:
            mismatch = mongo_database(client).complaints.find_one({'modelYearId': {'$ne': vehicle_id}}, {'_id': 1})['_id']
        change(owner, path + '/complaints', {'odiNumber': mismatch}, expected=404)
        change(owner, path + '/complaints/' + complaint, method='DELETE')
        for kind, field, id_field in [('notes', 'text', 'noteId'), ('findings', 'observation', 'findingId')]:
            key = str(uuid4())
            operation = change(owner, path + '/' + kind, {field: 'First observation'}, key=key)['operation']
            change(owner, path + '/' + kind, {field: 'First observation'}, key=key)
            entry = request(owner, path)['content'][kind][0]
            assert entry[id_field] == operation['operationId'] and entry['authorId'] == users[0]['userId']
            target = path + '/' + kind + '/' + entry[id_field]
            change(admin, target, {field: 'Edited observation'}, method='PATCH')
            assert request(owner, path)['content'][kind][0]['authorId'] == users[0]['userId']
            change(owner, target, method='DELETE')
            assert request(owner, path)['content'][kind] == []
        change(owner, path + '/content', {'tags': ['review', 'review'], 'suspectedComponents': ['steering']}, method='PATCH')
        content = request(owner, path)['content']
        assert content['tags'] == ['review'] and content['suspectedComponents'] == ['STEERING']
        for status in ['REVIEWING', 'CLOSED', 'OPEN']:
            change(owner, path, {'status': status}, method='PATCH')
        history = request(owner, path + '/history')['items']
        assert [(item['oldStatus'], item['newStatus']) for item in history] == [('OPEN', 'REVIEWING'), ('REVIEWING', 'CLOSED'), ('CLOSED', 'OPEN')]
        assert request(owner, path)['analysisCase']['closedAt'] is None
        assertions.append('real MongoDB link/unlink, nested note/finding CRUD, tags/components and SQL-triggered close/reopen history verified')

        for route, data, method in [('/api/analysis-cases', {**body, 'createdBy': users[1]['userId']}, 'POST'),
                                    (path, {'modelYearId': 1}, 'PATCH'), (path, {'assignedTo': users[1]['userId']}, 'PATCH'),
                                    (path, {'status': 'PENDING'}, 'PATCH'), (path + '/content', {'tags': {'$ne': None}}, 'PATCH')]:
            change(owner, route, data, method=method, expected=400)
        request(owner, path + '?ownerId=2', 400)
        request(owner, '/api/analysis-cases?pageSize=101', 400)
        saved_token, owner.csrf_token = owner.csrf_token, None
        change(owner, path, {'title': 'No CSRF'}, method='PATCH', expected=403)
        owner.csrf_token = saved_token
        request(owner, path, 400, body={'title': 'Missing key'}, method='PATCH')

        key = str(uuid4())
        original = request(owner, path)
        faults['sql_before_commit'] = key
        change(owner, path, {'status': 'CLOSED'}, method='PATCH', expected=503, key=key)
        assert request(owner, path) == original
        assert len(request(owner, path + '/history')['items']) == 3
        assertions.append('SQL failure before commit rolls back metadata/revision/history and makes no MongoDB change')

        faults['mongo_replace'] = 'before'
        pending_create = change(owner, '/api/analysis-cases', {**body, 'title': 'Pending create'}, expected=202)['operation']
        pending_path = '/api/analysis-cases/' + str(pending_create['caseId'])
        assert request(owner, pending_path)['content'] is None
        change(owner, pending_path, {'priority': 'HIGH'}, method='PATCH', expected=409)
        # A new normal server instance has no fault wrappers or in-memory operation state.
        fresh_base = start_server(injected=False)
        fresh = clone(owner)
        fresh.base = fresh_base
        change(fresh, '/api/analysis-cases/operations/' + pending_create['operationId'] + '/retry', {})
        assert request(fresh, pending_path)['content']['revision'] == 1
        assertions.append('pending create survives a new server instance and completes from its durable SQL payload')

        for fault, value in [('mongo_replace', 'after'), ('sql_ack', None)]:
            key = str(uuid4())
            faults[fault] = key if fault == 'sql_ack' else value
            before_notes = len(request(owner, path)['content']['notes'])
            operation = change(owner, path + '/notes', {'text': 'Retry-safe note'}, expected=202, key=key)['operation']
            with postgres() as connection:
                state, payload = connection.execute('SELECT state,payload FROM case_content_operation WHERE operation_id=%s', (key,)).fetchone()
                assert state == 'PENDING' and payload is not None
            change(fresh, '/api/analysis-cases/operations/' + operation['operationId'] + '/retry', {})
            assert len(request(fresh, path)['content']['notes']) == before_notes + 1
            change(fresh, '/api/analysis-cases/operations/' + operation['operationId'] + '/retry', {})
            assert len(request(fresh, path)['content']['notes']) == before_notes + 1
        assertions.append('MongoDB write with lost response and MongoDB-success/SQL-ack failure recover without duplicate notes')

        faults['mongo_delete'] = True
        deletion = change(owner, pending_path, method='DELETE', expected=202)['operation']
        request(owner, pending_path, 404)
        assert deletion['operationId'] in [item['operationId'] for item in request(owner, '/api/analysis-cases/operations')['items']]
        with postgres() as connection:
            connection.execute("UPDATE app_user SET role='NORMAL_USER' WHERE user_id=%s", (users[0]['userId'],))
        change(owner, '/api/analysis-cases/operations/' + deletion['operationId'] + '/retry', {}, expected=403)
        change(admin, '/api/analysis-cases/operations/' + deletion['operationId'] + '/retry', {})
        with postgres() as connection:
            connection.execute("UPDATE app_user SET role='ANALYST' WHERE user_id=%s", (users[0]['userId'],))
        with mongo_client() as client:
            assert mongo_database(client).case_details.find_one({'caseId': deletion['caseId']}) is None
        assertions.append('delete recovery remains authorized after SQL parent deletion; demotion blocks the owner and admin can finish cleanup')

        key = str(uuid4())
        peers = [clone(owner), clone(owner)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(change, peer, '/api/analysis-cases', {**body, 'title': 'Concurrent create'}, expected=201, key=key) for peer in peers]
            identifiers = [future.result()['operation']['caseId'] for future in futures]
        assert identifiers[0] == identifiers[1]
        concurrent_path = '/api/analysis-cases/' + str(identifiers[0])
        note_requests = [(clone(owner), str(uuid4()), {'text': 'Concurrent ' + str(index)}) for index in [1, 2]]
        def simultaneous(item):
            client, request_id, note = item
            try:
                return client.request(concurrent_path + '/notes', note, headers={'Idempotency-Key': request_id})
            except ApiError as error:
                assert error.status == 409
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent_results = list(pool.map(simultaneous, note_requests))
        for item, result in zip(note_requests, concurrent_results):
            client, request_id, note = item
            if result is None:
                change(client, concurrent_path + '/notes', note, key=request_id)
            else:
                assert result['operation']['state'] == 'APPLIED'
        assert {entry['text'] for entry in request(owner, concurrent_path)['content']['notes']} == {'Concurrent 1', 'Concurrent 2'}
        assertions.append('concurrent same-key creates produce one case; concurrent note requests serialize or return a retryable 409 without lost edits')

        answers = iter([emails[0], '2', '2022', 'HONDA', 'CIVIC', 'Interactive verification', '1', '10', '0'])
        output = io.StringIO()
        with patch('sys.argv', ['try_cases.py', '--base-url', fresh_base]), patch('builtins.input', side_effect=lambda prompt: next(answers)), patch('getpass.getpass', return_value=password), redirect_stdout(output):
            try_cases.main()
        assert 'Signed out' in output.getvalue() and 'APPLIED' in output.getvalue() and password not in output.getvalue()
        assertions.append('interactive case menu logs in, creates/lists a real case, checks pending operations and logs out')

        change(owner, path, method='DELETE')
        change(owner, concurrent_path, method='DELETE')
        for client in [owner, other, admin, normal]:
            request(client, '/api/auth/logout', body={}, method='POST')
        with case_postgres() as connection:
            role = connection.execute('SELECT current_user').fetchone()[0]
            for table in ['app_user', 'app_session', 'recall', 'official_investigation', 'saved_vehicle']:
                assert not connection.execute("SELECT has_table_privilege(current_user,%s,'SELECT,INSERT,UPDATE,DELETE')", (table,)).fetchone()[0]
            for column in ['created_by', 'assigned_to', 'model_year_id']:
                assert not connection.execute("SELECT has_column_privilege(current_user,'analysis_case',%s,'UPDATE')", (column,)).fetchone()[0]
            assert not connection.execute("SELECT has_table_privilege(current_user,'case_content_operation','DELETE')").fetchone()[0]
            assert connection.execute("SELECT count(*) FROM case_content_operation WHERE state='APPLIED' AND payload IS NOT NULL").fetchone()[0] == 0
        assertions.append('case SQL account cannot read credentials/sessions, mutate official records, change case ownership/vehicle or delete recovery receipts')
    finally:
        for app, server, thread in servers:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
            app.extensions['mongo_client'].close()
        with postgres() as connection, mongo_client() as client:
            owned_users = [row[0] for row in connection.execute('SELECT user_id FROM app_user WHERE email=ANY(%s)', (emails,)).fetchall()]
            owned_cases = [row[0] for row in connection.execute('''SELECT case_id FROM analysis_case WHERE created_by=ANY(%s)
                UNION SELECT case_id FROM case_content_operation WHERE owner_id=ANY(%s)''', (owned_users, owned_users)).fetchall()]
            if owned_cases:
                mongo_database(client).case_details.delete_many({'caseId': {'$in': owned_cases}})
            connection.execute('DELETE FROM analysis_case WHERE created_by=ANY(%s)', (owned_users,))
            connection.execute('DELETE FROM case_content_operation WHERE owner_id=ANY(%s)', (owned_users,))
            connection.execute('DELETE FROM app_user WHERE email=ANY(%s)', (emails,))
    after = snapshot()
    assert before == after, 'Owned fixtures remain or unrelated stored record counts changed'
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks, 'assertions_passed': assertions,
              'interactive_menu_verified': True, 'server_recreation_recovery_verified': True,
              'concurrent_requests_verified': True, 'case_sql_role': role,
              'synthetic_accounts_cases_content_operations_removed': True, 'record_counts_unchanged_after_cleanup': True,
              'record_counts': after, 'limitations': ['Faults are injected in the service boundary while both actual DBMSs stay running.',
              'Recovery is explicit through authenticated retry; no background worker is installed.',
              'There is no distributed SQL/MongoDB transaction or database row-level security.',
              'Sequence counters advance during synthetic CRUD; existing record counts/content are retained.',
              'Assignment/reassignment is not implemented; browser and performance coverage has separate evidence.']}
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Passed {len(checks)} recorded HTTP checks plus concurrent/interactive flows; owned fixtures removed and counts preserved.')
    print('Evidence: ' + report_path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
