"""Local interactive fleet/work-order client for an existing application account."""

import argparse
import getpass
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.local_api import ApiError, LocalApi


def check_fleet_support(api):
    # An anonymous 401 means the protected route exists. A generic 404 here
    # means the running server has not loaded the fleet routes at all.
    for path in ['/api/fleets', '/api/work-orders']:
        try:
            api.request(path)
        except ApiError as error:
            if error.status == 401:
                continue
            if error.status == 404:
                raise SystemExit(
                    f'The server at {api.base} has not loaded the fleet routes.\n'
                    'In the Flask server terminal, press Ctrl+C, then run:\n'
                    '  .\\.venv\\Scripts\\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000\n'
                    'Keep that terminal running and rerun try_fleets.py in a second terminal.\n'
                    'Restarting Flask retains your database records.'
                ) from None
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5000')
    args = parser.parse_args()
    api = LocalApi(args.base_url)
    check_fleet_support(api)
    api.request('/api/auth/csrf')
    api.request('/api/auth/login', {'email': input('Application email: ').strip(),
                                    'password': getpass.getpass('Application password (hidden): ')})

    def show(result):
        print(json.dumps(result, indent=2))

    try:
        while True:
            print('\n1 List my fleets\n2 Create fleet\n3 Rename fleet\n4 Delete fleet (includes its vehicles/orders)'
                  '\n5 List fleet vehicles\n6 Add fleet vehicle\n7 Rename vehicle label\n8 Remove vehicle (includes its orders)'
                  '\n9 Recall matches\n10 List my work orders\n11 Create recall work order\n12 Update work-order status/notes'
                  '\n13 Delete work order\n0 Sign out')
            action = input('Choice: ').strip()
            try:
                if action == '0':
                    break
                if action == '1':
                    show(api.request('/api/fleets'))
                elif action == '2':
                    show(api.request('/api/fleets', {'name': input('Fleet name: ').strip()}))
                elif action == '3':
                    fleet_id = int(input('Fleet ID: '))
                    show(api.request(f'/api/fleets/{fleet_id}', {'name': input('New name: ').strip()}, method='PATCH'))
                elif action == '4':
                    fleet_id = int(input('Fleet ID to delete with its vehicles/orders: '))
                    api.request(f'/api/fleets/{fleet_id}', method='DELETE')
                    print('Fleet and its vehicles/work orders removed.')
                elif action == '5':
                    fleet_id = int(input('Fleet ID: '))
                    show(api.request(f'/api/fleets/{fleet_id}/vehicles'))
                elif action == '6':
                    fleet_id = int(input('Fleet ID: '))
                    filters = {'year': int(input('Model year: ')), 'make': input('Make: ').strip(), 'model': input('Model: ').strip()}
                    found = api.request('/api/vehicles/search?' + urlencode(filters))['items']
                    if len(found) != 1:
                        print('Use an exact make/model/year from the catalogue.')
                        continue
                    show(api.request(f'/api/fleets/{fleet_id}/vehicles', {'modelYearId': found[0]['modelYearId'],
                                                                        'label': input('Physical vehicle label (e.g. Car 1): ').strip()}))
                elif action == '7':
                    vehicle_id = int(input('Fleet vehicle ID: '))
                    show(api.request(f'/api/fleet-vehicles/{vehicle_id}', {'label': input('New label: ').strip()}, method='PATCH'))
                elif action == '8':
                    vehicle_id = int(input('Fleet vehicle ID to remove with its work orders: '))
                    api.request(f'/api/fleet-vehicles/{vehicle_id}', method='DELETE')
                    print('Fleet vehicle and its work orders removed.')
                elif action == '9':
                    fleet_id = int(input('Fleet ID: '))
                    show(api.request(f'/api/fleets/{fleet_id}/recall-matches'))
                elif action == '10':
                    show(api.request('/api/work-orders'))
                elif action == '11':
                    show(api.request('/api/work-orders', {'fleetVehicleId': int(input('Fleet vehicle ID: ')),
                        'recallId': int(input('Recall ID from the match list: ')), 'notes': input('Notes (optional): ').strip()}))
                elif action == '12':
                    order_id = int(input('Work order ID: '))
                    field = input('Field (status/notes): ').strip()
                    value = input('New value: ')
                    show(api.request(f'/api/work-orders/{order_id}', {field: value.strip().upper() if field == 'status' else value}, method='PATCH'))
                elif action == '13':
                    order_id = int(input('Work order ID to delete: '))
                    api.request(f'/api/work-orders/{order_id}', method='DELETE')
                    print('Work order removed.')
                else:
                    print('Choose a menu number.')
            except (ApiError, ValueError, OSError) as error:
                print(str(error) if isinstance(error, ApiError) else 'Check the input or local connection.')
                if isinstance(error, ApiError) and error.status == 401:
                    break
    finally:
        try:
            api.request('/api/auth/logout', {})
            print('Signed out. Fleet records you did not delete remain stored.')
        except (ApiError, OSError):
            print('Logout unavailable; the session expires normally.')


if __name__ == '__main__':
    main()
