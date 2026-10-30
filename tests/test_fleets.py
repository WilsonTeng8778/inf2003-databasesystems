"""Fleet API ownership, validation and lifecycle tests without native DB connections."""

import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from psycopg import OperationalError
from psycopg.errors import UniqueViolation

from backend import create_app
from backend.services.auth import token_hash
from backend.services.fleets import FleetError, INTERPRETATION, PostgresFleetStore


class MemoryFleetStore:
    def __init__(self):
        self.fleets, self.vehicles, self.orders = {}, {}, {}
        self.counter = 0

    def next_id(self):
        self.counter += 1
        return self.counter

    def paged(self, rows, page, size):
        return {'items': copy.deepcopy(rows[(page-1)*size:page*size]), 'pagination': {
            'page': page, 'pageSize': size, 'total': len(rows), 'totalPages': (len(rows)+size-1)//size}}

    def get_fleet(self, owner, fleet_id):
        row = self.fleets.get(fleet_id)
        if row is None or row['owner'] != owner:
            raise FleetError(404, 'Fleet not found')
        item = {key: value for key, value in row.items() if key != 'owner'}
        vehicle_ids = {key for key, value in self.vehicles.items() if value['fleetId'] == fleet_id}
        return {**item, 'vehicleCount': len(vehicle_ids),
                'workOrderCount': sum(item['fleetVehicleId'] in vehicle_ids for item in self.orders.values())}

    def list_fleets(self, owner, page, size):
        return self.paged([self.get_fleet(owner, key) for key in sorted(self.fleets, reverse=True)
                           if self.fleets[key]['owner'] == owner], page, size)

    def create_fleet(self, owner, name):
        if any(row['owner'] == owner and row['name'] == name for row in self.fleets.values()):
            raise FleetError(409, 'Duplicate fleet name')
        key = self.next_id()
        self.fleets[key] = {'fleetId': key, 'owner': owner, 'name': name, 'createdAt': datetime.now(timezone.utc).isoformat()}
        return self.get_fleet(owner, key)

    def rename_fleet(self, owner, fleet_id, name):
        self.get_fleet(owner, fleet_id)
        if any(key != fleet_id and row['owner'] == owner and row['name'] == name for key, row in self.fleets.items()):
            raise FleetError(409, 'Duplicate fleet name')
        self.fleets[fleet_id]['name'] = name
        return self.get_fleet(owner, fleet_id)

    def delete_fleet(self, owner, fleet_id):
        self.get_fleet(owner, fleet_id)
        for key in list(self.vehicles):
            if self.vehicles[key]['fleetId'] == fleet_id:
                self.delete_vehicle(owner, key)
        del self.fleets[fleet_id]

    def get_vehicle(self, owner, vehicle_id):
        row = self.vehicles.get(vehicle_id)
        if row is None or self.fleets[row['fleetId']]['owner'] != owner:
            raise FleetError(404, 'Fleet vehicle not found')
        return copy.deepcopy(row)

    def list_vehicles(self, owner, fleet_id, page, size):
        self.get_fleet(owner, fleet_id)
        return self.paged([row for key, row in sorted(self.vehicles.items(), reverse=True) if row['fleetId'] == fleet_id], page, size)

    def create_vehicle(self, owner, fleet_id, model_year_id, label):
        self.get_fleet(owner, fleet_id)
        if model_year_id not in {42, 43, 44}:
            raise FleetError(404, 'Unknown catalogue vehicle')
        if any(row['fleetId'] == fleet_id and row['label'] == label for row in self.vehicles.values()):
            raise FleetError(409, 'Duplicate label')
        key = self.next_id()
        self.vehicles[key] = {'fleetVehicleId': key, 'fleetId': fleet_id, 'modelYearId': model_year_id, 'label': label,
            'createdAt': datetime.now(timezone.utc).isoformat(), 'vehicle': {'year': 2022, 'make': 'HONDA', 'model': 'CIVIC'}}
        return self.get_vehicle(owner, key)

    def rename_vehicle(self, owner, vehicle_id, label):
        row = self.get_vehicle(owner, vehicle_id)
        if any(key != vehicle_id and item['fleetId'] == row['fleetId'] and item['label'] == label for key, item in self.vehicles.items()):
            raise FleetError(409, 'Duplicate label')
        self.vehicles[vehicle_id]['label'] = label
        return self.get_vehicle(owner, vehicle_id)

    def delete_vehicle(self, owner, vehicle_id):
        self.get_vehicle(owner, vehicle_id)
        for key in list(self.orders):
            if self.orders[key]['fleetVehicleId'] == vehicle_id:
                del self.orders[key]
        del self.vehicles[vehicle_id]

    def matches(self, owner, fleet_id, vehicle_id, tracked, page, size):
        self.get_fleet(owner, fleet_id)
        if vehicle_id is not None and self.get_vehicle(owner, vehicle_id)['fleetId'] != fleet_id:
            raise FleetError(404, 'Fleet vehicle not found')
        rows = []
        for key, vehicle in self.vehicles.items():
            if vehicle['fleetId'] != fleet_id or vehicle_id is not None and key != vehicle_id:
                continue
            for recall in {42: [101, 102], 43: [103], 44: []}[vehicle['modelYearId']]:
                work = next((row for row in self.orders.values() if row['fleetVehicleId'] == key and row['recallId'] == recall), None)
                if tracked is not None and (work is not None) != tracked:
                    continue
                rows.append({**vehicle, 'recallId': recall, 'campaignNumber': str(recall),
                             'workOrderId': work['workOrderId'] if work else None,
                             'workOrderStatus': work['status'] if work else None})
        return {**self.paged(rows, page, size), 'interpretation': INTERPRETATION}

    def get_order(self, owner, order_id):
        row = self.orders.get(order_id)
        if row is None or self.fleets[row['fleetId']]['owner'] != owner:
            raise FleetError(404, 'Work order not found')
        result = copy.deepcopy(row)
        result['label'] = self.vehicles[row['fleetVehicleId']]['label']
        return result

    def list_orders(self, owner, fleet_id, vehicle_id, status, page, size):
        rows = [self.get_order(owner, key) for key, row in self.orders.items()
                if self.fleets[row['fleetId']]['owner'] == owner and (fleet_id is None or row['fleetId'] == fleet_id)
                and (vehicle_id is None or row['fleetVehicleId'] == vehicle_id) and (status is None or row['status'] == status)]
        return self.paged(rows, page, size)

    def create_order(self, owner, vehicle_id, recall_id, notes):
        vehicle = self.get_vehicle(owner, vehicle_id)
        if recall_id not in {42: [101, 102], 43: [103], 44: []}[vehicle['modelYearId']]:
            raise FleetError(404, 'Matching recall not found for this fleet vehicle')
        if any(row['fleetVehicleId'] == vehicle_id and row['recallId'] == recall_id for row in self.orders.values()):
            raise FleetError(409, 'Duplicate work order')
        key = self.next_id()
        self.orders[key] = {**vehicle, 'workOrderId': key, 'recallId': recall_id, 'campaignNumber': str(recall_id),
                            'status': 'OPEN', 'notes': notes, 'completedAt': None}
        return self.get_order(owner, key)

    def update_order(self, owner, order_id, fields):
        self.get_order(owner, order_id)
        self.orders[order_id].update(fields)
        row = self.orders[order_id]
        row['completedAt'] = (row['completedAt'] or datetime.now(timezone.utc).isoformat()) if row['status'] == 'COMPLETED' else None
        return self.get_order(owner, order_id)

    def delete_order(self, owner, order_id):
        self.get_order(owner, order_id)
        del self.orders[order_id]


class FleetTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryFleetStore()
        auth = Mock()
        self.tokens = {number: chr(96+number)*43 for number in [1, 2, 3]}
        self.users = {token_hash(value): {'userId': key, 'role': 'ADMIN' if key == 3 else 'NORMAL_USER'}
                      for key, value in self.tokens.items()}
        auth.session_user.side_effect = lambda value: self.users.get(value)
        self.app = create_app({'TESTING': True, 'SECRET_KEY': 'fleet-tests-only', 'DUMMY_PASSWORD_HASH': 'unused',
            'MONGO_CLIENT_FACTORY': Mock, 'AUTH_STORE_FACTORY': lambda: auth, 'FLEET_STORE_FACTORY': lambda: self.store})
        self.clients = {}
        for key, value in self.tokens.items():
            client = self.app.test_client()
            with client.session_transaction() as session:
                session.update(session_token=value, csrf_token='x'*43)
            self.clients[key] = client
        self.headers = {'X-CSRF-Token': 'x'*43}

    def write(self, path, body=None, *, method='POST', user=1):
        return self.clients[user].open('/api' + path, json=body, method=method, headers=self.headers)

    def fleet(self, name='My fleet', user=1):
        return self.write('/fleets', {'name': name}, user=user).json['fleet']['fleetId']

    def vehicle(self, fleet_id, label='Car 1', model=42, user=1):
        return self.write(f'/fleets/{fleet_id}/vehicles', {'label': label, 'modelYearId': model}, user=user).json['fleetVehicle']['fleetVehicleId']

    def order(self, vehicle_id, recall=101, user=1):
        return self.write('/work-orders', {'fleetVehicleId': vehicle_id, 'recallId': recall}, user=user)

    def test_anonymous_and_revoked_sessions_are_denied(self):
        for path in ['/api/fleets', '/api/fleet-vehicles/1', '/api/work-orders', '/api/fleets/1/recall-matches']:
            self.assertEqual(self.app.test_client().get(path).status_code, 401)
        self.users.clear()
        self.assertEqual(self.write('/fleets', {'name': 'Forbidden'}).status_code, 401)

    def test_normal_user_fleet_crud_and_location(self):
        result = self.write('/fleets', {'name': '  My fleet  '})
        self.assertEqual(result.status_code, 201)
        fleet_id = result.json['fleet']['fleetId']
        self.assertEqual(result.headers['Location'], f'/api/fleets/{fleet_id}')
        self.assertEqual(result.json['fleet']['name'], 'My fleet')
        self.assertEqual(self.write(f'/fleets/{fleet_id}', {'name': 'Renamed'}, method='PATCH').json['fleet']['name'], 'Renamed')
        self.assertEqual(self.clients[1].get('/api/fleets').json['pagination']['total'], 1)
        self.assertEqual(self.write(f'/fleets/{fleet_id}', method='DELETE').status_code, 204)
        self.assertEqual(self.clients[1].get(f'/api/fleets/{fleet_id}').status_code, 404)

    def test_other_users_including_admin_cannot_use_foreign_fleets(self):
        fleet_id = self.fleet()
        for user in [2, 3]:
            self.assertEqual(self.clients[user].get('/api/fleets').json['items'], [])
            foreign = self.clients[user].get(f'/api/fleets/{fleet_id}')
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json, self.clients[user].get('/api/fleets/999').json)
            self.assertEqual(self.write(f'/fleets/{fleet_id}', {'name': 'Forbidden'}, method='PATCH', user=user).status_code, 404)
            self.assertEqual(self.write(f'/fleets/{fleet_id}', method='DELETE', user=user).status_code, 404)
            self.assertEqual(self.clients[user].get(f'/api/fleets/{fleet_id}/vehicles').status_code, 404)
            self.assertEqual(self.clients[user].get(f'/api/fleets/{fleet_id}/recall-matches').status_code, 404)
            self.assertEqual(self.write(f'/fleets/{fleet_id}/vehicles', {'label': 'Wrong', 'modelYearId': 42}, user=user).status_code, 404)

    def test_fleet_names_are_unique_per_owner(self):
        self.fleet()
        self.assertEqual(self.write('/fleets', {'name': 'My fleet'}).status_code, 409)
        self.assertIsInstance(self.fleet(user=2), int)
        second = self.fleet('Second')
        self.assertEqual(self.write(f'/fleets/{second}', {'name': 'My fleet'}, method='PATCH').status_code, 409)

    def test_vehicle_crud_and_same_catalogue_can_describe_multiple_physical_vehicles(self):
        fleet_id = self.fleet()
        first, second = self.vehicle(fleet_id, 'Car 1'), self.vehicle(fleet_id, 'Car 2')
        self.assertNotEqual(first, second)
        self.assertEqual(self.clients[1].get(f'/api/fleets/{fleet_id}').json['fleet']['vehicleCount'], 2)
        self.assertEqual(self.write(f'/fleet-vehicles/{first}', {'label': 'New label'}, method='PATCH').json['fleetVehicle']['label'], 'New label')
        self.assertEqual(self.write(f'/fleet-vehicles/{first}', method='DELETE').status_code, 204)
        self.assertEqual(self.clients[1].get(f'/api/fleet-vehicles/{second}').status_code, 200)

    def test_vehicle_labels_are_unique_per_fleet(self):
        first, second = self.fleet('First'), self.fleet('Second')
        self.vehicle(first)
        self.vehicle(second)
        self.assertEqual(self.write(f'/fleets/{first}/vehicles', {'label': 'Car 1', 'modelYearId': 43}).status_code, 409)
        other = self.vehicle(first, 'Car 2')
        self.assertEqual(self.write(f'/fleet-vehicles/{other}', {'label': 'Car 1'}, method='PATCH').status_code, 409)

    def test_foreign_vehicle_ids_are_not_accessible_even_for_admin(self):
        fleet_id = self.fleet()
        vehicle_id = self.vehicle(fleet_id)
        for user in [2, 3]:
            foreign = self.clients[user].get(f'/api/fleet-vehicles/{vehicle_id}')
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json, self.clients[user].get('/api/fleet-vehicles/999').json)
            self.assertEqual(self.write(f'/fleet-vehicles/{vehicle_id}', {'label': 'Wrong'}, method='PATCH', user=user).status_code, 404)
            self.assertEqual(self.write(f'/fleet-vehicles/{vehicle_id}', method='DELETE', user=user).status_code, 404)
            self.assertEqual(self.order(vehicle_id, user=user).status_code, 404)

    def test_matches_filter_physical_vehicle_and_tracking_state(self):
        fleet_id = self.fleet()
        first, second = self.vehicle(fleet_id, 'Car 1'), self.vehicle(fleet_id, 'Car 2')
        self.order(first)
        path = f'/api/fleets/{fleet_id}/recall-matches'
        result = self.clients[1].get(path).json
        self.assertEqual(result['pagination']['total'], 4)
        self.assertIn('not VIN', result['interpretation'])
        self.assertTrue(result['items'][0]['recallUrl'].startswith('/api/recalls/'))
        self.assertEqual(self.clients[1].get(path + '?tracked=true').json['pagination']['total'], 1)
        self.assertEqual(self.clients[1].get(path + '?tracked=false').json['pagination']['total'], 3)
        self.assertEqual(self.clients[1].get(path + f'?fleetVehicleId={second}').json['pagination']['total'], 2)

    def test_match_vehicle_must_belong_to_selected_fleet(self):
        first, second = self.fleet('First'), self.fleet('Second')
        vehicle_id = self.vehicle(second)
        self.assertEqual(self.clients[1].get(f'/api/fleets/{first}/recall-matches?fleetVehicleId={vehicle_id}').status_code, 404)

    def test_unknown_catalogue_and_vehicle_with_no_recalls(self):
        fleet_id = self.fleet()
        self.assertEqual(self.write(f'/fleets/{fleet_id}/vehicles', {'label': 'Unknown', 'modelYearId': 999}).status_code, 404)
        vehicle_id = self.vehicle(fleet_id, model=44)
        self.assertEqual(self.clients[1].get(f'/api/fleets/{fleet_id}/recall-matches').json['items'], [])
        self.assertEqual(self.order(vehicle_id).status_code, 404)

    def test_work_order_requires_matching_recall_and_prevents_duplicates(self):
        vehicle_id = self.vehicle(self.fleet())
        self.assertEqual(self.order(vehicle_id, recall=103).status_code, 404)
        result = self.order(vehicle_id)
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json['workOrder']['modelYearId'], 42)
        self.assertEqual(result.json['workOrder']['status'], 'OPEN')
        self.assertIsNone(result.json['workOrder']['completedAt'])
        self.assertEqual(self.order(vehicle_id).status_code, 409)

    def test_order_status_notes_completion_timestamp_and_reopening(self):
        vehicle_id = self.vehicle(self.fleet())
        order_id = self.order(vehicle_id).json['workOrder']['workOrderId']
        path = f'/work-orders/{order_id}'
        for state in ['IN_PROGRESS', 'COMPLETED']:
            self.assertEqual(self.write(path, {'status': state}, method='PATCH').status_code, 200)
        completed = self.clients[1].get('/api' + path).json['workOrder']['completedAt']
        self.assertIsNotNone(completed)
        self.assertEqual(self.write(path, {'status': 'COMPLETED', 'notes': 'Scheduled\nUpdate'}, method='PATCH').json['workOrder']['completedAt'], completed)
        self.assertEqual(self.write(path, {'status': 'CANCELLED'}, method='PATCH').json['workOrder']['completedAt'], None)
        self.assertEqual(self.write(path, {'status': 'OPEN', 'notes': ''}, method='PATCH').json['workOrder']['notes'], '')

    def test_foreign_orders_and_lists_are_owner_scoped_including_admin(self):
        vehicle_id = self.vehicle(self.fleet())
        order_id = self.order(vehicle_id).json['workOrder']['workOrderId']
        for user in [2, 3]:
            self.assertEqual(self.clients[user].get('/api/work-orders').json['items'], [])
            foreign = self.clients[user].get(f'/api/work-orders/{order_id}')
            self.assertEqual(foreign.status_code, 404)
            self.assertEqual(foreign.json, self.clients[user].get('/api/work-orders/999').json)
            self.assertEqual(self.write(f'/work-orders/{order_id}', {'status': 'COMPLETED'}, method='PATCH', user=user).status_code, 404)
            self.assertEqual(self.write(f'/work-orders/{order_id}', method='DELETE', user=user).status_code, 404)

    def test_order_list_filters_and_case_insensitive_query_status(self):
        fleet_id = self.fleet()
        vehicle_id = self.vehicle(fleet_id)
        self.order(vehicle_id)
        self.assertEqual(self.clients[1].get(f'/api/work-orders?fleetId={fleet_id}&fleetVehicleId={vehicle_id}&status=open').json['pagination']['total'], 1)
        self.assertEqual(self.clients[1].get('/api/work-orders?status=COMPLETED').json['items'], [])

    def test_order_delete_makes_match_untracked_again(self):
        fleet_id = self.fleet()
        vehicle_id = self.vehicle(fleet_id)
        order_id = self.order(vehicle_id).json['workOrder']['workOrderId']
        response = self.write(f'/work-orders/{order_id}', method='DELETE')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b'')
        self.assertEqual(self.clients[1].get(f'/api/fleets/{fleet_id}/recall-matches?tracked=true').json['items'], [])

    def test_vehicle_delete_cascades_its_orders_and_fleet_delete_cascades_the_rest(self):
        fleet_id = self.fleet()
        first, second = self.vehicle(fleet_id), self.vehicle(fleet_id, 'Car 2')
        self.order(first)
        self.order(second)
        self.write(f'/fleet-vehicles/{first}', method='DELETE')
        self.assertEqual(len(self.store.orders), 1)
        self.write(f'/fleets/{fleet_id}', method='DELETE')
        self.assertEqual(self.store.vehicles, {})
        self.assertEqual(self.store.orders, {})

    def test_csrf_is_required_for_each_mutation(self):
        fleet_id = self.fleet()
        for method, path, body in [('POST', '/fleets', {'name': 'Other'}), ('PATCH', f'/fleets/{fleet_id}', {'name': 'Wrong'}),
                                   ('DELETE', f'/fleets/{fleet_id}', None), ('POST', '/work-orders', {'fleetVehicleId': 1, 'recallId': 101})]:
            self.assertEqual(self.clients[1].open('/api' + path, method=method, json=body).status_code, 403)

    def test_unknown_fields_prevent_ownership_and_identity_spoofing(self):
        self.assertEqual(self.write('/fleets', {'name': 'Fake', 'ownerId': 2}).status_code, 400)
        fleet_id = self.fleet()
        vehicle_id = self.vehicle(fleet_id)
        order_id = self.order(vehicle_id).json['workOrder']['workOrderId']
        for path, body in [(f'/fleets/{fleet_id}', {'name': 'Other', 'ownerId': 2}),
                           (f'/fleet-vehicles/{vehicle_id}', {'label': 'Other', 'modelYearId': 43}),
                           (f'/fleet-vehicles/{vehicle_id}', {'label': 'Other', 'fleetId': 2}),
                           (f'/work-orders/{order_id}', {'status': 'COMPLETED', 'completedAt': 'now'}),
                           (f'/work-orders/{order_id}', {'recallId': 103})]:
            self.assertEqual(self.write(path, body, method='PATCH').status_code, 400)

    def test_bad_strings_types_notes_and_statuses(self):
        for value in ['', 'x'*101, 'bad\x00', 42, {'$ne': None}]:
            self.assertEqual(self.write('/fleets', {'name': value}).status_code, 400)
        fleet_id = self.fleet()
        for value in [True, 0, -1, '42', 2**63]:
            self.assertEqual(self.write(f'/fleets/{fleet_id}/vehicles', {'modelYearId': value, 'label': 'Car'}).status_code, 400)
        for body in [{}, {'status': 'FINISHED'}, {'status': 1}, {'notes': 'x'*2001}, {'notes': None}, {'notes': 'bad\x00'}]:
            self.assertEqual(self.write('/work-orders/1', body, method='PATCH').status_code, 400)

    def test_invalid_pagination_duplicate_unknown_filters_and_bigint_bounds(self):
        for query in ['page=0', 'pageSize=101', 'page=10001', 'page=1&page=2', 'ownerId=2']:
            for path in ['/fleets', '/work-orders']:
                self.assertEqual(self.clients[1].get('/api' + path + '?' + query).status_code, 400)
        fleet_id = self.fleet()
        for query in ['tracked=0', 'fleetVehicleId=0', 'tracked=true&tracked=false']:
            self.assertEqual(self.clients[1].get(f'/api/fleets/{fleet_id}/recall-matches?' + query).status_code, 400)
        self.assertEqual(self.clients[1].get('/api/work-orders?fleetId=9223372036854775807').status_code, 200)
        self.assertEqual(self.clients[1].get('/api/work-orders?fleetId=9223372036854775808').status_code, 400)

    def test_stable_pages_and_private_cache_headers(self):
        first, second = self.fleet('First'), self.fleet('Second')
        self.fleet(user=2)
        page1 = self.clients[1].get('/api/fleets?pageSize=1').json
        page2 = self.clients[1].get('/api/fleets?pageSize=1&page=2').json
        self.assertEqual(page1['items'][0]['fleetId'], second)
        self.assertEqual(page2['items'][0]['fleetId'], first)
        self.assertEqual(page1['pagination']['total'], 2)
        for path in ['/api/fleets', '/api/work-orders', '/api/fleet-vehicles/999']:
            self.assertEqual(self.clients[1].get(path).headers['Cache-Control'], 'no-store')

    def test_sql_failure_is_sanitized_and_connection_is_closed(self):
        self.app.config['FLEET_STORE_FACTORY'] = None
        connection = MagicMock()
        connection.execute.side_effect = OperationalError('DO_NOT_EXPOSE')
        self.app.config['WORKFLOW_PG_CONNECT'] = lambda: connection
        response = self.clients[1].get('/api/fleets')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('DO_NOT_EXPOSE', response.get_data(as_text=True))
        connection.close.assert_called_once()

    def test_sql_values_are_bound_and_owner_filters_are_present(self):
        connection = MagicMock()
        row = {'fleet_id': 7, 'name': 'Name', 'created_at': datetime.now(timezone.utc), 'vehicle_count': 0, 'work_order_count': 0}
        connection.execute.return_value.fetchone.return_value = row
        repository = PostgresFleetStore(connection)
        value = "Name'); DROP TABLE fleet; --"
        repository.rename_fleet(44, 7, value)
        for call in connection.execute.call_args_list:
            self.assertNotIn(value, call.args[0])
            self.assertIn('owner_id=%s', call.args[0])
            self.assertIn(44, call.args[1])

    def test_duplicate_sql_write_is_rolled_back_by_transaction_context(self):
        connection = MagicMock()
        connection.execute.side_effect = UniqueViolation()
        with self.assertRaises(FleetError) as caught:
            PostgresFleetStore(connection).create_fleet(1, 'Name')
        self.assertEqual(caught.exception.status, 409)
        self.assertIs(connection.transaction.return_value.__exit__.call_args.args[0], UniqueViolation)


if __name__ == '__main__':
    unittest.main()
