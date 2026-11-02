"""Role/ownership checks, typed case input, operation receipts and retry endpoints."""

import re
from uuid import UUID

from flask import Blueprint, abort, current_app, g, jsonify, request, url_for

from backend.auth import current_user, json_fields, requires_roles
from backend.routes import number, query_fields
from backend.services.cases import CaseError, CaseService, PostgresCaseRepository, public_operation
from project_config import mongo_database

cases = Blueprint('cases', __name__, url_prefix='/api/analysis-cases')
analyst = requires_roles('ANALYST', 'ADMIN')


def service():
    if 'case_service' not in g:
        factory = current_app.config.get('CASE_SERVICE_FACTORY')
        if factory:
            g.case_service = factory()
        else:
            g.case_postgres = current_app.config['CASE_PG_CONNECT']()
            g.case_service = CaseService(PostgresCaseRepository(g.case_postgres),
                                         mongo_database(current_app.extensions['mongo_client']))
    return g.case_service


def close_case_postgres(error=None):
    connection = g.pop('case_postgres', None)
    if connection is not None:
        connection.close()


@cases.errorhandler(CaseError)
def case_error(error):
    return jsonify({'error': {'code': 'case_request_failed', 'message': str(error)}}), error.status


def identifier(value):
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        abort(400, description='Case and vehicle IDs must be positive integers')
    return value


def uuid_value(value):
    try:
        if not isinstance(value, str) or len(value) != 36:
            raise ValueError()
        return str(UUID(value))
    except ValueError:
        abort(400, description='Provide a UUID, including hyphens, for the operation/entry ID')


def plain(value, name, maximum):
    if not isinstance(value, str):
        abort(400, description=f'{name} must be a string')
    value = value.strip()
    # Notes may have paragraphs/tabs, but no other control characters.
    if not value or len(value) > maximum or not all(char.isprintable() or char in '\n\r\t' for char in value):
        abort(400, description=f'{name} must contain 1 to {maximum} text characters')
    if name == 'title' and not value.isprintable():
        abort(400, description='title must be printable on one line')
    return value


def enumeration(value, name, allowed):
    if not isinstance(value, str) or value not in allowed:
        abort(400, description=f'{name} must be one of ' + ', '.join(allowed))
    return value


def pagination():
    return number('page', default=1, maximum=10000), number('pageSize', default=20, maximum=100)


def receipt(action, case_id, body):
    operation_id = uuid_value(request.headers.get('Idempotency-Key'))
    result = service().perform(current_user(), operation_id, action, case_id, body)
    status = 202 if result['state'] == 'PENDING' else 201 if action == 'CREATE' else 200
    response = jsonify({'operation': result})
    response.status_code = status
    response.headers['Location'] = url_for('cases.operation_detail', operation_id=operation_id)
    return response


@cases.get('')
@analyst
def listing():
    query_fields({'page', 'pageSize'})
    page, size = pagination()
    return jsonify(service().repo.list_cases(current_user(), page, size))


@cases.post('')
@analyst
def create():
    body = json_fields({'title', 'modelYearId'}, {'priority'})
    body = {'title': plain(body['title'], 'title', 200), 'modelYearId': identifier(body['modelYearId']),
            'priority': enumeration(body.get('priority', 'MEDIUM'), 'priority', ('LOW', 'MEDIUM', 'HIGH'))}
    return receipt('CREATE', None, body)


@cases.get('/<int:case_id>')
@analyst
def detail(case_id):
    query_fields(set())
    return jsonify(service().get(current_user(), identifier(case_id)))


@cases.patch('/<int:case_id>')
@analyst
def update(case_id):
    identifier(case_id)
    body = json_fields(set(), {'title', 'priority', 'status'})
    if not body:
        abort(400, description='Provide title, priority or status')
    if 'title' in body:
        body['title'] = plain(body['title'], 'title', 200)
    if 'priority' in body:
        body['priority'] = enumeration(body['priority'], 'priority', ('LOW', 'MEDIUM', 'HIGH'))
    if 'status' in body:
        body['status'] = enumeration(body['status'], 'status', ('OPEN', 'REVIEWING', 'CLOSED'))
    return receipt('UPDATE', case_id, body)


@cases.delete('/<int:case_id>')
@analyst
def remove(case_id):
    query_fields(set())
    return receipt('DELETE', identifier(case_id), {})


@cases.patch('/<int:case_id>/content')
@analyst
def content(case_id):
    identifier(case_id)
    body = json_fields(set(), {'tags', 'suspectedComponents'})
    if not body:
        abort(400, description='Provide tags or suspectedComponents')
    for field, values in body.items():
        if not isinstance(values, list) or len(values) > 20:
            abort(400, description=f'{field} must be an array with at most 20 strings')
        clean = []
        for value in values:
            value = plain(value, field, 100)
            if not value.isprintable():
                abort(400, description=f'{field} values must be printable on one line')
            if field == 'suspectedComponents':
                value = ' '.join(value.upper().split())
            if value not in clean:
                clean.append(value)
        body[field] = clean
    return receipt('CONTENT', case_id, body)


def odi(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9]{1,20}', value) is None:
        abort(400, description='odiNumber must be a string of 1 to 20 ASCII digits')
    return value


@cases.post('/<int:case_id>/complaints')
@analyst
def link(case_id):
    identifier(case_id)
    body = json_fields({'odiNumber'})
    return receipt('LINK', case_id, {'odiNumber': odi(body['odiNumber'])})


@cases.delete('/<int:case_id>/complaints/<odi_number>')
@analyst
def unlink(case_id, odi_number):
    query_fields(set())
    return receipt('UNLINK', identifier(case_id), {'odiNumber': odi(odi_number)})


def entry_type(entry_kind):
    if entry_kind not in {'notes', 'findings'}:
        abort(404)
    return ('NOTE', 'text') if entry_kind == 'notes' else ('FINDING', 'observation')


@cases.post('/<int:case_id>/<entry_kind>')
@analyst
def add_entry(case_id, entry_kind):
    identifier(case_id)
    action, field = entry_type(entry_kind)
    body = json_fields({field})
    return receipt(action + '_ADD', case_id, {field: plain(body[field], field, 4000)})


@cases.patch('/<int:case_id>/<entry_kind>/<entry_id>')
@analyst
def edit_entry(case_id, entry_kind, entry_id):
    identifier(case_id)
    action, field = entry_type(entry_kind)
    body = json_fields({field})
    return receipt(action + '_EDIT', case_id, {'entryId': uuid_value(entry_id), field: plain(body[field], field, 4000)})


@cases.delete('/<int:case_id>/<entry_kind>/<entry_id>')
@analyst
def delete_entry(case_id, entry_kind, entry_id):
    query_fields(set())
    action, field = entry_type(entry_kind)
    return receipt(action + '_DELETE', identifier(case_id), {'entryId': uuid_value(entry_id)})


@cases.get('/<int:case_id>/history')
@analyst
def history(case_id):
    query_fields({'page', 'pageSize'})
    page, size = pagination()
    return jsonify(service().repo.history(current_user(), identifier(case_id), page, size))


@cases.get('/operations')
@analyst
def operations():
    query_fields({'page', 'pageSize', 'state'})
    page, size = pagination()
    state = enumeration(request.args.get('state', 'PENDING'), 'state', ('PENDING', 'APPLIED'))
    return jsonify(service().repo.list_operations(current_user(), state, page, size))


@cases.get('/operations/<operation_id>')
@analyst
def operation_detail(operation_id):
    query_fields(set())
    operation_id = uuid_value(operation_id)
    operation = service().repo.operation(current_user(), operation_id)
    if operation is None:
        abort(404, description='Case operation not found')
    return jsonify({'operation': public_operation(operation)})


@cases.post('/operations/<operation_id>/retry')
@analyst
def retry(operation_id):
    uuid_value(operation_id)
    json_fields(set())
    result = service().process(current_user(), operation_id)
    return jsonify({'operation': result}), 202 if result['state'] == 'PENDING' else 200
