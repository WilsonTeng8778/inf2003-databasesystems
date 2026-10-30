"""Live fleet ownership, constraints, concurrency and terminal workflow with owned fixtures."""

import copy
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
from psycopg.errors import ForeignKeyViolation
from werkzeug.serving import make_server
from backend import create_app
from project_config import ROOT, postgres, workflow_postgres
from scripts.support.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_cases import snapshot
from scripts import try_fleets
from scripts.support.verification_reports import select_report_path


def main(argv=None):
    report_path = select_report_path('fleets', argv)
    before = snapshot()
    prefix = 'fleets-verification-' + uuid4().hex
    emails = [prefix + suffix + '@example.invalid' for suffix in ['-owner', '-other', '-admin']]
    password = secrets.token_urlsafe(24)
    app = create_app()
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    owner, other, admin = [LocalApi(base) for _ in range(3)]
    checks, assertions, concurrent_checks = [], [], []

    def request(client, path, expected=200, *, body=None, method='GET'):
        try:
            result = client.request(path, body, method=method)
        except ApiError as error:
            result = {'error': str(error)}
        assert client.last_status == expected, f'{method} {path}: HTTP {client.last_status}, expected {expected}: {result}'
        checks.append({'method': method, 'path': path, 'status': expected})
        return result

    def change(client, path, body=None, *, expected=200, method='POST'):
        return request(client, path, expected, body=body, method=method)

    def clone(client):
        result = LocalApi(base)
        for cookie in client.cookies:
            result.cookies.set_cookie(copy.copy(cookie))
        result.csrf_token = client.csrf_token
        return result

    def simultaneous(item):
        client, method, path, body = item
        try:
            result = client.request(path, body, method=method)
        except ApiError as error:
            result = {'error': str(error)}
        concurrent_checks.append({'method': method, 'path': path, 'status': client.last_status})
        return client.last_status, result

    try:
        request(LocalApi(base), '/api/fleets', 401)
        users = []
        for client, email in zip([owner, other, admin], emails):
            request(client, '/api/auth/csrf')
            users.append(change(client, '/api/auth/register', {'email': email, 'password': password}, expected=201)['user'])
        with postgres() as connection:
            connection.execute("UPDATE app_user SET role='ADMIN' WHERE user_id=%s", (users[2]['userId'],))
        vehicle = request(owner, '/api/vehicles/search?year=2022&make=HONDA&model=CIVIC')['items'][0]
        identity = vehicle['modelYearId']
        fleet = change(owner, '/api/fleets', {'name': '  Main fleet  '}, expected=201)['fleet']
        fleet_id, fleet_path = fleet['fleetId'], owner.last_headers['Location']
        assert fleet['name'] == 'Main fleet' and fleet['vehicleCount'] == 0
        assert request(owner, fleet_path)['fleet'] == fleet
        change(owner, fleet_path, {'name': 'Renamed fleet'}, method='PATCH')
        change(owner, '/api/fleets', {'name': 'Renamed fleet'}, expected=409)
        other_fleet = change(other, '/api/fleets', {'name': 'Renamed fleet'}, expected=201)['fleet']
        owner_second = change(owner, '/api/fleets', {'name': 'Second fleet'}, expected=201)['fleet']
        page1 = request(owner, '/api/fleets?pageSize=1')
        page2 = request(owner, '/api/fleets?pageSize=1&page=2')
        assert page1['pagination']['total'] == 2 and page1['items'][0]['fleetId'] != page2['items'][0]['fleetId']
        assert request(owner, fleet_path)['fleet']['name'] == 'Renamed fleet'
        assert owner.last_headers['Cache-Control'] == 'no-store'

        first = change(owner, fleet_path + '/vehicles', {'label': 'Car 1', 'modelYearId': identity}, expected=201)['fleetVehicle']
        first_path = owner.last_headers['Location']
        second = change(owner, fleet_path + '/vehicles', {'label': 'Car 2', 'modelYearId': identity}, expected=201)['fleetVehicle']
        second_path = owner.last_headers['Location']
        assert first['fleetVehicleId'] != second['fleetVehicleId'] and first['modelYearId'] == second['modelYearId']
        change(owner, fleet_path + '/vehicles', {'label': 'Car 1', 'modelYearId': identity}, expected=409)
        change(owner, first_path, {'label': 'Renamed car'}, method='PATCH')
        change(owner, second_path, {'label': 'Renamed car'}, method='PATCH', expected=409)
        assert request(owner, fleet_path)['fleet']['vehicleCount'] == 2
        assert request(owner, fleet_path + '/vehicles')['pagination']['total'] == 2
        match_path = fleet_path + '/recall-matches'
        matches = request(owner, match_path)
        assert matches['pagination']['total'] == 8
        one_vehicle = request(owner, match_path + f"?fleetVehicleId={first['fleetVehicleId']}")
        assert one_vehicle['pagination']['total'] == 4
        assert request(owner, one_vehicle['items'][0]['recallUrl'])['recall']['recallId'] == one_vehicle['items'][0]['recallId']
        recall_id = one_vehicle['items'][0]['recallId']
        assertions.append('normal users can create/read/rename fleets and physical vehicles; owner-local uniqueness, stable pages and two Civic identities produce 8 model-year recall matches')

        with postgres() as connection:
            unrelated_recall = connection.execute('''SELECT r.recall_id FROM recall r WHERE NOT EXISTS
                (SELECT 1 FROM recall_vehicle rv WHERE rv.recall_id=r.recall_id AND rv.model_year_id=%s) LIMIT 1''', (identity,)).fetchone()[0]
            no_recalls = connection.execute('SELECT model_year_id FROM vehicle_safety_summary WHERE recall_count=0 LIMIT 1').fetchone()[0]
            unknown_identity = connection.execute('SELECT max(model_year_id)+100000 FROM model_year').fetchone()[0]
        change(owner, fleet_path + '/vehicles', {'label': 'Unknown', 'modelYearId': unknown_identity}, expected=404)
        zero = change(owner, '/api/fleets/' + str(owner_second['fleetId']) + '/vehicles',
                      {'label': 'No-recall vehicle', 'modelYearId': no_recalls}, expected=201)['fleetVehicle']
        assert request(owner, '/api/fleets/' + str(owner_second['fleetId']) + '/recall-matches')['items'] == []
        request(owner, match_path + f"?fleetVehicleId={zero['fleetVehicleId']}", 404)
        change(owner, '/api/work-orders', {'fleetVehicleId': first['fleetVehicleId'], 'recallId': unrelated_recall}, expected=404)
        # A direct administrative INSERT is rejected as well: composite FK, not only API validation.
        with postgres(autocommit=True) as connection:
            try:
                with connection.transaction():
                    connection.execute('''INSERT INTO work_order(fleet_vehicle_id,model_year_id,recall_id)
                        VALUES (%s,%s,%s)''', (first['fleetVehicleId'], identity, unrelated_recall))
            except ForeignKeyViolation:
                pass
            else:
                raise AssertionError('Mismatched vehicle/recall bypassed the SQL composite foreign key')
        assertions.append('unmatched/unknown catalogue vehicles and cross-model recall orders are rejected; native composite foreign key rejects an invalid direct INSERT')

        body = {'fleetVehicleId': first['fleetVehicleId'], 'recallId': recall_id, 'notes': 'Initial tracking note'}
        order = change(owner, '/api/work-orders', body, expected=201)['workOrder']
        order_id, order_path = order['workOrderId'], owner.last_headers['Location']
        assert order['status'] == 'OPEN' and order['completedAt'] is None and order['modelYearId'] == identity
        change(owner, '/api/work-orders', body, expected=409)
        assert request(owner, order_path)['workOrder'] == order
        assert request(owner, fleet_path)['fleet']['workOrderCount'] == 1
        assert request(owner, match_path + '?tracked=true')['pagination']['total'] == 1
        assert request(owner, match_path + '?tracked=false')['pagination']['total'] == 7
        assert request(owner, f'/api/work-orders?fleetId={fleet_id}&fleetVehicleId=' + str(first['fleetVehicleId']) + '&status=open')['pagination']['total'] == 1
        change(owner, order_path, {'status': 'IN_PROGRESS', 'notes': 'Appointment scheduled\nOwner tracking'}, method='PATCH')
        complete = change(owner, order_path, {'status': 'COMPLETED'}, method='PATCH')['workOrder']['completedAt']
        assert complete is not None
        assert change(owner, order_path, {'status': 'COMPLETED', 'notes': 'Recorded'}, method='PATCH')['workOrder']['completedAt'] == complete
        assert change(owner, order_path, {'status': 'CANCELLED'}, method='PATCH')['workOrder']['completedAt'] is None
        assert change(owner, order_path, {'status': 'OPEN', 'notes': ''}, method='PATCH')['workOrder']['notes'] == ''
        assertions.append('work-order CRUD values, per-vehicle/recall uniqueness, tracked filters, status transitions and completion/reopen timestamps agree with SQL rules')

        for client in [other, admin]:
            foreign = request(client, fleet_path, 404)
            assert request(client, '/api/fleets/9223372036854775807', 404) == foreign
            change(client, fleet_path, {'name': 'Forbidden'}, method='PATCH', expected=404)
            change(client, fleet_path, method='DELETE', expected=404)
            request(client, fleet_path + '/vehicles', 404)
            request(client, match_path, 404)
            change(client, fleet_path + '/vehicles', {'label': 'Forbidden', 'modelYearId': identity}, expected=404)
            foreign = request(client, first_path, 404)
            assert request(client, '/api/fleet-vehicles/9223372036854775807', 404) == foreign
            change(client, first_path, {'label': 'Forbidden'}, method='PATCH', expected=404)
            change(client, first_path, method='DELETE', expected=404)
            change(client, '/api/work-orders', body, expected=404)
            foreign = request(client, order_path, 404)
            assert request(client, '/api/work-orders/9223372036854775807', 404) == foreign
            change(client, order_path, {'status': 'COMPLETED'}, method='PATCH', expected=404)
            change(client, order_path, method='DELETE', expected=404)
            assert request(client, f'/api/work-orders?fleetId={fleet_id}')['items'] == []
        assert request(admin, '/api/fleets')['items'] == []
        assertions.append('foreign fleet/vehicle/order reads and writes are denied for both another normal user and ADMIN; foreign and missing IDs are indistinguishable')

        for path, payload, method in [('/api/fleets', {'name': 'Wrong', 'ownerId': users[1]['userId']}, 'POST'),
                                      (fleet_path, {'name': ''}, 'PATCH'), (first_path, {'label': 'Wrong', 'fleetId': other_fleet['fleetId']}, 'PATCH'),
                                      (first_path, {'label': 'Wrong', 'modelYearId': no_recalls}, 'PATCH'),
                                      ('/api/work-orders', {**body, 'modelYearId': no_recalls}, 'POST'),
                                      (order_path, {'status': 'COMPLETED', 'completedAt': 'now'}, 'PATCH'),
                                      (order_path, {'status': 'UNKNOWN'}, 'PATCH'), (order_path, {'notes': 'x'*2001}, 'PATCH')]:
            change(owner, path, payload, method=method, expected=400)
        for path in ['/api/fleets?pageSize=101', '/api/work-orders?status=UNKNOWN', match_path + '?tracked=0',
                     '/api/work-orders?ownerId=2', '/api/fleets?page=1&page=2']:
            request(owner, path, 400)
        token, owner.csrf_token = owner.csrf_token, None
        change(owner, order_path, {'status': 'COMPLETED'}, method='PATCH', expected=403)
        owner.csrf_token = token

        # Same parent lock serializes partial edits, preserving both fields.
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(simultaneous, [
                (clone(owner), 'PATCH', order_path, {'status': 'COMPLETED'}),
                (clone(owner), 'PATCH', order_path, {'notes': 'Concurrent note retained'})]))
        assert all(status == 200 for status, result in results)
        current = request(owner, order_path)['workOrder']
        assert current['status'] == 'COMPLETED' and current['notes'] == 'Concurrent note retained'
        duplicate_body = {'fleetVehicleId': second['fleetVehicleId'], 'recallId': recall_id}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(simultaneous, [(clone(owner), 'POST', '/api/work-orders', duplicate_body) for _ in range(2)]))
        assert sorted(status for status, result in results) == [201, 409]
        second_order = next(result['workOrder'] for status, result in results if status == 201)
        assert request(owner, match_path + '?tracked=true')['pagination']['total'] == 2
        assertions.append('concurrent partial order edits retain both fields; concurrent duplicate creates produce exactly one order and a 409')

        change(owner, order_path, method='DELETE', expected=204)
        request(owner, order_path, 404)
        assert request(owner, match_path + '?tracked=true')['pagination']['total'] == 1
        change(owner, second_path, method='DELETE', expected=204)
        request(owner, '/api/work-orders/' + str(second_order['workOrderId']), 404)
        cascade_vehicle = change(owner, fleet_path + '/vehicles', {'modelYearId': identity, 'label': 'Cascade car'}, expected=201)['fleetVehicle']
        cascade_order = change(owner, '/api/work-orders', {'fleetVehicleId': cascade_vehicle['fleetVehicleId'], 'recallId': recall_id}, expected=201)['workOrder']
        change(owner, fleet_path, method='DELETE', expected=204)
        request(owner, '/api/fleet-vehicles/' + str(cascade_vehicle['fleetVehicleId']), 404)
        request(owner, '/api/work-orders/' + str(cascade_order['workOrderId']), 404)
        assertions.append('deleting an order restores untracked matching; vehicle and fleet deletions cascade only their dependent personal rows')

        race = change(owner, '/api/fleets', {'name': 'Delete race'}, expected=201)['fleet']
        race_path = '/api/fleets/' + str(race['fleetId'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(simultaneous, [(clone(owner), 'DELETE', race_path, None),
                (clone(owner), 'POST', race_path + '/vehicles', {'modelYearId': identity, 'label': 'Racing car'})]))
        assert results[0][0] == 204 and results[1][0] in {201, 404}
        request(owner, race_path, 404)
        with postgres() as connection:
            assert connection.execute('SELECT count(*) FROM fleet_vehicle WHERE fleet_id=%s', (race['fleetId'],)).fetchone()[0] == 0
        assertions.append('concurrent fleet deletion/vehicle creation leaves no orphan vehicle')

        # Drive the actual terminal client through a complete SQL workflow.
        answers = iter([emails[0], '2', 'Interactive fleet', '6', '__fleet__', '2022', 'HONDA', 'CIVIC', 'Menu car',
                        '9', '__fleet__', '11', '__vehicle__', str(recall_id), 'Menu order', '12', '__order__', 'status', 'COMPLETED',
                        '10', '4', '__fleet__', '0'])
        def operator(prompt):
            value = next(answers)
            with postgres() as connection:
                if value == '__fleet__':
                    return str(connection.execute("SELECT fleet_id FROM fleet WHERE owner_id=%s AND name='Interactive fleet'", (users[0]['userId'],)).fetchone()[0])
                if value == '__vehicle__':
                    return str(connection.execute("SELECT fv.fleet_vehicle_id FROM fleet_vehicle fv JOIN fleet f USING(fleet_id) WHERE f.owner_id=%s AND fv.label='Menu car'", (users[0]['userId'],)).fetchone()[0])
                if value == '__order__':
                    return str(connection.execute("SELECT w.work_order_id FROM work_order w JOIN fleet_vehicle fv USING(fleet_vehicle_id) JOIN fleet f USING(fleet_id) WHERE f.owner_id=%s AND fv.label='Menu car'", (users[0]['userId'],)).fetchone()[0])
            return value
        output = io.StringIO()
        with patch('sys.argv', ['try_fleets.py', '--base-url', base]), patch('builtins.input', side_effect=operator), patch('getpass.getpass', return_value=password), redirect_stdout(output):
            try_fleets.main()
        assert 'Fleet and its vehicles/work orders removed.' in output.getvalue() and 'COMPLETED' in output.getvalue() and 'Signed out' in output.getvalue()
        assert password not in output.getvalue()
        assertions.append('interactive menu creates a fleet/vehicle, browses recalls, creates/completes an order, reads it and deletes the fleet before logout')

        # Logout from the still-active fixture sessions; the terminal client used its own session.
        for client in [owner, other, admin]:
            change(client, '/api/auth/logout', {})
        with workflow_postgres() as connection:
            role = connection.execute('SELECT current_user').fetchone()[0]
            for table in ['app_user', 'app_session', 'recall', 'official_investigation', 'analysis_case', 'case_content_operation']:
                assert not connection.execute("SELECT has_table_privilege(current_user,%s,'SELECT,INSERT,UPDATE,DELETE')", (table,)).fetchone()[0]
            for table, column in [('fleet', 'owner_id'), ('fleet_vehicle', 'fleet_id'), ('fleet_vehicle', 'model_year_id'),
                                  ('work_order', 'fleet_vehicle_id'), ('work_order', 'model_year_id'), ('work_order', 'recall_id')]:
                assert not connection.execute("SELECT has_column_privilege(current_user,%s,%s,'UPDATE')", (table, column)).fetchone()[0]
            assert connection.execute("SELECT has_table_privilege(current_user,'fleet_recall_matches','SELECT')").fetchone()[0]
        assertions.append('workflow SQL role has recall-match view access without credentials/case/source-table access or ownership/identity UPDATE privileges')
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions['mongo_client'].close()
        with postgres() as connection:
            owned_users = [row[0] for row in connection.execute('SELECT user_id FROM app_user WHERE email=ANY(%s)', (emails,)).fetchall()]
            connection.execute('DELETE FROM fleet WHERE owner_id=ANY(%s)', (owned_users,))
            connection.execute('DELETE FROM app_user WHERE email=ANY(%s)', (emails,))
    after = snapshot()
    assert before == after, 'Synthetic fixtures remain or unrelated stored counts changed'
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': checks,
        'concurrent_checks': concurrent_checks, 'assertions_passed': assertions, 'interactive_menu_verified': True,
        'workflow_sql_role': role, 'native_composite_foreign_key_verified': True,
        'owned_synthetic_accounts_fleets_vehicles_orders_sessions_removed': True,
        'record_counts_unchanged_after_cleanup': True, 'record_counts': after,
        'example': {'modelYearId': identity, 'make': 'HONDA', 'model': 'CIVIC', 'year': 2022,
                    'recallsPerVehicle': 4, 'matchesForTwoPhysicalVehicles': 8},
        'limitations': ['Ownership is enforced by API/SQL predicates; PostgreSQL row-level security is not configured.',
                       'Model-year matches and user-entered work-order status do not verify VIN applicability or repair completion.',
                       'Concurrent operations were tested over real threaded HTTP; count/page reads do not share a snapshot.',
                       'Verification retains existing record counts/content; generated identity sequences advance normally.',
                       'This native/API/menu run has separate browser/analytics evidence and does not establish final package readiness.']}
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Passed {len(checks)} recorded HTTP checks, {len(concurrent_checks)} concurrent requests and the interactive flow; owned fixtures removed.')
    print('Evidence: ' + report_path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
