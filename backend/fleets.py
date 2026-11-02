"""Personal fleet/vehicle/work-order endpoints: every human role has the same owner scope."""

from flask import Blueprint, abort, current_app, g, jsonify, url_for

from backend.auth import current_user, json_fields, requires_roles
from backend.routes import boolean, number, query_fields, text
from backend.services.fleets import FleetError, INTERPRETATION, PostgresFleetStore, STATUSES

fleets = Blueprint('fleets', __name__, url_prefix='/api')
signed_in = requires_roles()


def store():
    if 'fleet_store' not in g:
        factory = current_app.config.get('FLEET_STORE_FACTORY')
        if factory:
            g.fleet_store = factory()
        else:
            g.fleet_postgres = current_app.config['WORKFLOW_PG_CONNECT']()
            g.fleet_store = PostgresFleetStore(g.fleet_postgres)
    return g.fleet_store


def close_fleet_postgres(error=None):
    connection = g.pop('fleet_postgres', None)
    if connection is not None:
        connection.close()


@fleets.errorhandler(FleetError)
def fleet_error(error):
    return jsonify({'error': {'code': 'fleet_request_failed', 'message': str(error)}}), error.status


def owner():
    return current_user()['userId']


def identifier(value):
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        abort(400, description='Identifiers must be positive integers')
    return value


def label(value, field):
    if not isinstance(value, str):
        abort(400, description=f'{field} must be a string')
    value = value.strip()
    if not value or len(value) > 100 or not value.isprintable():
        abort(400, description=f'{field} must contain 1 to 100 printable characters')
    return value


def notes(value):
    if not isinstance(value, str):
        abort(400, description='notes must be a string')
    value = value.strip()
    if len(value) > 2000 or not all(char.isprintable() or char in '\n\r\t' for char in value):
        abort(400, description='notes must contain at most 2000 text characters')
    return value


def status(value):
    if not isinstance(value, str) or value not in STATUSES:
        abort(400, description='status must be one of ' + ', '.join(STATUSES))
    return value


def pagination():
    return number('page', default=1, maximum=10000), number('pageSize', default=20, maximum=100)


def created(kind, item, endpoint, **identifiers):
    response = jsonify({kind: item, **({'interpretation': INTERPRETATION} if kind == 'workOrder' else {})})
    response.status_code = 201
    response.headers['Location'] = url_for(endpoint, **identifiers)
    return response


@fleets.get('/fleets')
@signed_in
def listing():
    query_fields({'page', 'pageSize'})
    page, size = pagination()
    return jsonify(store().list_fleets(owner(), page, size))


@fleets.post('/fleets')
@signed_in
def create():
    body = json_fields({'name'})
    name = label(body['name'], 'name')
    item = store().create_fleet(owner(), name)
    return created('fleet', item, 'fleets.detail', fleet_id=item['fleetId'])


@fleets.get('/fleets/<int:fleet_id>')
@signed_in
def detail(fleet_id):
    query_fields(set())
    identifier(fleet_id)
    return jsonify({'fleet': store().get_fleet(owner(), fleet_id)})


@fleets.patch('/fleets/<int:fleet_id>')
@signed_in
def rename(fleet_id):
    identifier(fleet_id)
    body = json_fields({'name'})
    name = label(body['name'], 'name')
    return jsonify({'fleet': store().rename_fleet(owner(), fleet_id, name)})


@fleets.delete('/fleets/<int:fleet_id>')
@signed_in
def remove(fleet_id):
    query_fields(set())
    identifier(fleet_id)
    store().delete_fleet(owner(), fleet_id)
    return '', 204


@fleets.get('/fleets/<int:fleet_id>/vehicles')
@signed_in
def vehicles(fleet_id):
    query_fields({'page', 'pageSize'})
    identifier(fleet_id)
    page, size = pagination()
    return jsonify(store().list_vehicles(owner(), fleet_id, page, size))


@fleets.post('/fleets/<int:fleet_id>/vehicles')
@signed_in
def add_vehicle(fleet_id):
    identifier(fleet_id)
    body = json_fields({'modelYearId', 'label'})
    model_year_id, name = identifier(body['modelYearId']), label(body['label'], 'label')
    item = store().create_vehicle(owner(), fleet_id, model_year_id, name)
    return created('fleetVehicle', item, 'fleets.vehicle_detail', vehicle_id=item['fleetVehicleId'])


@fleets.get('/fleet-vehicles/<int:vehicle_id>')
@signed_in
def vehicle_detail(vehicle_id):
    query_fields(set())
    identifier(vehicle_id)
    return jsonify({'fleetVehicle': store().get_vehicle(owner(), vehicle_id)})


@fleets.patch('/fleet-vehicles/<int:vehicle_id>')
@signed_in
def rename_vehicle(vehicle_id):
    identifier(vehicle_id)
    body = json_fields({'label'})
    name = label(body['label'], 'label')
    return jsonify({'fleetVehicle': store().rename_vehicle(owner(), vehicle_id, name)})


@fleets.delete('/fleet-vehicles/<int:vehicle_id>')
@signed_in
def remove_vehicle(vehicle_id):
    query_fields(set())
    identifier(vehicle_id)
    store().delete_vehicle(owner(), vehicle_id)
    return '', 204


@fleets.get('/fleets/<int:fleet_id>/recall-matches')
@signed_in
def matches(fleet_id):
    query_fields({'page', 'pageSize', 'fleetVehicleId', 'tracked'})
    identifier(fleet_id)
    page, size = pagination()
    vehicle_id, tracked = number('fleetVehicleId', maximum=9223372036854775807), boolean('tracked')
    result = store().matches(owner(), fleet_id, vehicle_id, tracked, page, size)
    for item in result['items']:
        item['recallUrl'] = url_for('official.recall', campaign_number=item['campaignNumber'])
    return jsonify(result)


@fleets.get('/work-orders')
@signed_in
def orders():
    query_fields({'page', 'pageSize', 'fleetId', 'fleetVehicleId', 'status'})
    page, size = pagination()
    fleet_id, vehicle_id = number('fleetId', maximum=9223372036854775807), number('fleetVehicleId', maximum=9223372036854775807)
    state = text('status', maximum=20)
    if state is not None:
        status(state)
    result = store().list_orders(owner(), fleet_id, vehicle_id, state, page, size)
    result['interpretation'] = INTERPRETATION
    return jsonify(result)


@fleets.post('/work-orders')
@signed_in
def create_order():
    body = json_fields({'fleetVehicleId', 'recallId'}, {'notes'})
    vehicle_id, recall_id = identifier(body['fleetVehicleId']), identifier(body['recallId'])
    content = notes(body.get('notes', ''))
    item = store().create_order(owner(), vehicle_id, recall_id, content)
    return created('workOrder', item, 'fleets.order_detail', order_id=item['workOrderId'])


@fleets.get('/work-orders/<int:order_id>')
@signed_in
def order_detail(order_id):
    query_fields(set())
    identifier(order_id)
    return jsonify({'workOrder': store().get_order(owner(), order_id), 'interpretation': INTERPRETATION})


@fleets.patch('/work-orders/<int:order_id>')
@signed_in
def update_order(order_id):
    identifier(order_id)
    body = json_fields(set(), {'status', 'notes'})
    if not body:
        abort(400, description='Provide status or notes')
    if 'status' in body:
        body['status'] = status(body['status'])
    if 'notes' in body:
        body['notes'] = notes(body['notes'])
    return jsonify({'workOrder': store().update_order(owner(), order_id, body), 'interpretation': INTERPRETATION})


@fleets.delete('/work-orders/<int:order_id>')
@signed_in
def remove_order(order_id):
    query_fields(set())
    identifier(order_id)
    store().delete_order(owner(), order_id)
    return '', 204
