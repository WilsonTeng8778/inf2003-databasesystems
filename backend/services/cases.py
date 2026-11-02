"""Case CRUD with a durable SQL outbox and idempotent MongoDB projection."""

import hashlib
import json
from datetime import datetime, timezone

from bson.json_util import dumps, loads
from psycopg import Error as PostgresError
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pymongo import timeout
from pymongo.errors import DuplicateKeyError, PyMongoError


class CaseError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class ProjectionConflict(Exception):
    pass


def public_case(row):
    fields = {'caseId': 'case_id', 'title': 'title', 'modelYearId': 'model_year_id',
              'createdBy': 'created_by', 'assignedTo': 'assigned_to', 'priority': 'priority', 'status': 'status',
              'createdAt': 'created_at', 'closedAt': 'closed_at', 'contentRevision': 'content_revision'}
    item = {key: value.isoformat() if isinstance(value, datetime) else value
            for key, column in fields.items() for value in [row[column]]}
    item['vehicle'] = {key: row[key] for key in ('make', 'model', 'year')}
    return item


def public_operation(row):
    fields = {'operationId': 'operation_id', 'caseId': 'case_id', 'revision': 'revision',
              'action': 'action', 'state': 'state', 'lastFailure': 'last_failure',
              'createdAt': 'created_at', 'completedAt': 'completed_at'}
    return {key: value.isoformat() if isinstance(value, datetime) else str(value) if key == 'operationId' else value
            for key, column in fields.items() for value in [row.get(column)]}


def public_content(document):
    if isinstance(document, datetime):
        return document.isoformat()
    if isinstance(document, list):
        return [public_content(item) for item in document]
    if isinstance(document, dict):
        return {key: public_content(value) for key, value in document.items() if key != '_id'}
    return document


def paged(items, total, page, size):
    return {'items': items, 'pagination': {'page': page, 'pageSize': size, 'total': total,
                                         'totalPages': (total + size - 1) // size}}


class PostgresCaseRepository:
    def __init__(self, connection):
        self.connection = connection
        connection.row_factory = dict_row

    def transaction(self):
        return self.connection.transaction()

    def request_lock(self, operation_id):
        self.connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,200319))', (operation_id,))

    def scope(self, actor, column):
        return ('TRUE', []) if actor['role'] == 'ADMIN' else (column + '=%s', [actor['userId']])

    def case(self, actor, case_id, *, lock=False):
        condition, values = self.scope(actor, 'c.created_by')
        return self.connection.execute('''SELECT c.*,v.make,v.model,v.year FROM analysis_case c
            JOIN vehicle_catalogue v USING(model_year_id) WHERE c.case_id=%s AND ''' + condition +
            (' FOR UPDATE OF c' if lock else ''), [case_id, *values]).fetchone()

    def list_cases(self, actor, page, size):
        condition, values = self.scope(actor, 'c.created_by')
        total = self.connection.execute('SELECT count(*) AS n FROM analysis_case c WHERE ' + condition, values).fetchone()['n']
        rows = self.connection.execute('''SELECT c.*,v.make,v.model,v.year,
            EXISTS(SELECT 1 FROM case_content_operation o WHERE o.case_id=c.case_id AND o.state='PENDING') AS pending
            FROM analysis_case c JOIN vehicle_catalogue v USING(model_year_id) WHERE ''' + condition +
            ' ORDER BY c.created_at DESC,c.case_id DESC LIMIT %s OFFSET %s', [*values, size, (page-1)*size]).fetchall()
        return paged([{**public_case(row), 'syncState': 'PENDING' if row['pending'] else 'APPLIED'} for row in rows], total, page, size)

    def operation(self, actor, operation_id, *, lock=False):
        condition, values = ('TRUE', []) if actor is None else self.scope(actor, 'owner_id')
        return self.connection.execute('SELECT * FROM case_content_operation WHERE operation_id=%s AND ' + condition +
                                       (' FOR UPDATE' if lock else ''), [operation_id, *values]).fetchone()

    def list_operations(self, actor, state, page, size):
        condition, values = self.scope(actor, 'owner_id')
        condition += ' AND state=%s'
        values.append(state)
        total = self.connection.execute('SELECT count(*) AS n FROM case_content_operation WHERE ' + condition, values).fetchone()['n']
        rows = self.connection.execute('SELECT * FROM case_content_operation WHERE ' + condition +
            ' ORDER BY created_at DESC,operation_id LIMIT %s OFFSET %s', [*values, size, (page-1)*size]).fetchall()
        return paged([public_operation(row) for row in rows], total, page, size)

    def pending(self, case_id):
        return self.connection.execute("SELECT * FROM case_content_operation WHERE case_id=%s AND state='PENDING'", (case_id,)).fetchone()

    def create(self, actor, body):
        found = self.connection.execute('''INSERT INTO analysis_case(title,model_year_id,created_by,assigned_to,priority,content_revision)
            SELECT %s,model_year_id,%s,%s,%s,1 FROM vehicle_catalogue WHERE model_year_id=%s RETURNING case_id''',
            (body['title'], actor['userId'], actor['userId'], body['priority'], body['modelYearId'])).fetchone()
        if found is None:
            raise CaseError(404, 'Vehicle not found in the imported catalogue')
        return self.case(actor, found['case_id'])

    def update(self, actor, row, body):
        status = body.get('status', row['status'])
        self.connection.execute('''UPDATE analysis_case SET title=%s,priority=%s,status=%s,
            closed_at=CASE WHEN %s='CLOSED' THEN COALESCE(closed_at,now()) ELSE NULL END,
            content_revision=content_revision+1 WHERE case_id=%s''',
            (body.get('title', row['title']), body.get('priority', row['priority']), status, status, row['case_id']))
        return self.case(actor, row['case_id'])

    def delete(self, row):
        self.connection.execute('DELETE FROM analysis_case WHERE case_id=%s', (row['case_id'],))

    def enqueue(self, operation_id, actor, row, fingerprint, action, document):
        payload = Jsonb(json.loads(dumps(document))) if document is not None else None
        return self.connection.execute('''INSERT INTO case_content_operation
            (operation_id,case_id,owner_id,requested_by,request_hash,revision,action,payload)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
            (operation_id, row['case_id'], row['created_by'], actor['userId'], fingerprint,
             row['content_revision'], action, payload)).fetchone()

    def acknowledge(self, operation_id):
        self.connection.execute("""UPDATE case_content_operation SET state='APPLIED',payload=NULL,
            last_failure=NULL,completed_at=now() WHERE operation_id=%s""", (operation_id,))

    def record_failure(self, operation_id, category):
        self.connection.execute("UPDATE case_content_operation SET last_failure=%s WHERE operation_id=%s AND state='PENDING'",
                                (category, operation_id))

    def history(self, actor, case_id, page, size):
        if self.case(actor, case_id) is None:
            raise CaseError(404, 'Analysis case not found')
        total = self.connection.execute('SELECT count(*) AS n FROM case_status_history WHERE case_id=%s', (case_id,)).fetchone()['n']
        rows = self.connection.execute('''SELECT history_id,old_status,new_status,changed_at FROM case_status_history
            WHERE case_id=%s ORDER BY history_id LIMIT %s OFFSET %s''', (case_id, size, (page-1)*size)).fetchall()
        items = [{'historyId': row['history_id'], 'oldStatus': row['old_status'], 'newStatus': row['new_status'],
                  'changedAt': row['changed_at'].isoformat()} for row in rows]
        return paged(items, total, page, size)


class CaseService:
    def __init__(self, repository, database):
        self.repo, self.database = repository, database

    def get(self, actor, case_id):
        with self.repo.transaction():
            row = self.repo.case(actor, case_id, lock=True)
            if row is None:
                raise CaseError(404, 'Analysis case not found')
            pending = self.repo.pending(case_id)
            content = None if pending else self.read_content(row)
            return {'analysisCase': public_case(row), 'content': public_content(content),
                    'sync': public_operation(pending) if pending else {'state': 'APPLIED'}}

    def read_content(self, row):
        with timeout(5):
            document = self.database.case_details.find_one({'caseId': row['case_id']}, max_time_ms=5000)
        if document is None or document.get('revision', 0) != row['content_revision']:
            raise CaseError(503, 'Case content is missing or inconsistent; inspect the stored case before editing')
        document.pop('_id', None)
        return document

    def perform(self, actor, operation_id, action, case_id, body):
        fingerprint = hashlib.sha256(json.dumps([actor['userId'], action, case_id, body],
                                               sort_keys=True, ensure_ascii=True).encode()).hexdigest()
        with self.repo.transaction():
            self.repo.request_lock(operation_id)
            previous = self.repo.operation(None, operation_id, lock=True)
            if previous:
                if previous['request_hash'] != fingerprint:
                    raise CaseError(409, 'Idempotency-Key was already used for another request')
                staged = previous
            else:
                if action == 'CREATE':
                    row = self.repo.create(actor, body)
                    document = {'caseId': row['case_id'], 'revision': 1, 'linkedComplaints': [],
                                'suspectedComponents': [], 'findings': [], 'notes': [], 'tags': []}
                else:
                    row = self.repo.case(actor, case_id, lock=True)
                    if row is None:
                        raise CaseError(404, 'Analysis case not found')
                    if self.repo.pending(case_id):
                        raise CaseError(409, 'A case change is pending; retry its operation before another edit')
                    if action == 'DELETE':
                        self.repo.delete(row)
                        row['content_revision'] += 1
                        document = None
                    else:
                        document = self.read_content(row)
                        self.change_content(document, row, actor, operation_id, action, body)
                        row = self.repo.update(actor, row, body if action == 'UPDATE' else {})
                        document['revision'] = row['content_revision']
                if document is not None and len(dumps(document).encode('utf-8')) > 512000:
                    raise CaseError(409, 'Case content exceeds the 512 KB limit; remove entries before adding more')
                staged = self.repo.enqueue(operation_id, actor, row, fingerprint,
                                           'DELETE' if action == 'DELETE' else 'REPLACE', document)
        return self.process(actor, operation_id, fallback=staged)

    def change_content(self, document, row, actor, operation_id, action, body):
        if action == 'UPDATE':
            return
        if action == 'CONTENT':
            document.update(body)
            return
        if action in {'LINK', 'UNLINK'}:
            number = body['odiNumber']
            if action == 'LINK':
                with timeout(5):
                    found = self.database.complaints.find_one({'_id': number, 'modelYearId': row['model_year_id']}, {'_id': 1}, max_time_ms=5000)
                if found is None:
                    raise CaseError(404, 'Complaint not found for this case vehicle')
                if number not in document['linkedComplaints']:
                    if len(document['linkedComplaints']) >= 200:
                        raise CaseError(409, 'A case can link at most 200 complaints')
                    document['linkedComplaints'].append(number)
            else:
                document['linkedComplaints'] = [item for item in document['linkedComplaints'] if item != number]
            return
        kind, verb = action.split('_')
        array, key, field = ('notes', 'noteId', 'text') if kind == 'NOTE' else ('findings', 'findingId', 'observation')
        entries = document[array]
        if verb == 'ADD':
            if len(entries) >= 100:
                raise CaseError(409, f'A case can contain at most 100 {array}')
            entries.append({key: operation_id, 'authorId': actor['userId'],
                            'createdAt': datetime.now(timezone.utc), field: body[field]})
        else:
            entry = next((entry for entry in entries if entry[key] == body['entryId']), None)
            if entry is None:
                raise CaseError(404, 'Case entry not found')
            if verb == 'EDIT':
                entry[field] = body[field]
            else:
                entries.remove(entry)

    def process(self, actor, operation_id, *, fallback=None):
        operation = fallback
        try:
            with self.repo.transaction():
                operation = self.repo.operation(actor, operation_id, lock=True)
                if operation is None:
                    raise CaseError(404, 'Case operation not found')
                if operation['state'] == 'APPLIED':
                    return public_operation(operation)
                case_id, revision = operation['case_id'], operation['revision']
                selector = {'caseId': case_id, '$or': [{'revision': {'$lte': revision}}, {'revision': {'$exists': False}}]}
                with timeout(5):
                    if operation['action'] == 'REPLACE':
                        document = loads(json.dumps(operation['payload']))
                        result = self.database.case_details.replace_one(selector, document, upsert=True)
                    else:
                        result = self.database.case_details.delete_one(selector)
                        if self.database.case_details.find_one({'caseId': case_id}, {'_id': 1}, max_time_ms=5000) is not None:
                            raise ProjectionConflict()
                    if not result.acknowledged:
                        raise PyMongoError('Case writes require acknowledged MongoDB write concern')
                self.repo.acknowledge(operation_id)
            operation = {**operation, 'state': 'APPLIED', 'last_failure': None, 'completed_at': datetime.now(timezone.utc)}
            return public_operation(operation)
        except (PyMongoError, PostgresError, ProjectionConflict) as error:
            if operation is None:
                raise
            category = ('SQL_ACKNOWLEDGEMENT_PENDING' if isinstance(error, PostgresError) else
                        'CONTENT_CONFLICT' if isinstance(error, (ProjectionConflict, DuplicateKeyError)) else 'MONGODB_UNAVAILABLE')
            try:
                self.repo.record_failure(operation_id, category)
            except PostgresError:
                pass
            return public_operation({**operation, 'state': 'PENDING', 'last_failure': category, 'completed_at': None})
