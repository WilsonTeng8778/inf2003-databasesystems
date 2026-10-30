"""Interactive local client for analyst/admin cases; writes only the operator's choices."""

import argparse
import getpass
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.local_api import ApiError, LocalApi


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5000')
    args = parser.parse_args()
    api = LocalApi(args.base_url)
    api.request('/api/auth/csrf')
    login = api.request('/api/auth/login', {'email': input('Application email: ').strip(),
                                          'password': getpass.getpass('Application password: ')})
    last_write = None

    def show(result):
        print(json.dumps(result, indent=2))
        if isinstance(result, dict) and result.get('operation', {}).get('state') == 'PENDING':
            print('Change recorded in SQL; MongoDB synchronization is pending. Retry its operation ID.')

    def change(path, body=None, *, method='POST'):
        nonlocal last_write
        key = str(uuid4())
        last_write = (path, body, method, {'Idempotency-Key': key})
        print('Request ID:', key)
        return api.request(path, body, method=method, headers=last_write[3])

    try:
        if login['user']['role'] not in {'ANALYST', 'ADMIN'}:
            print('This account needs ANALYST or ADMIN access. An administrator assigns roles; normal registration cannot choose them.')
            return
        while True:
            print('\n1 List cases\n2 Create case\n3 View case\n4 Update title/priority/status\n5 Link or unlink complaint'
                  '\n6 Add/edit/remove note or finding\n7 Set tags/components\n8 Status history\n9 Delete case'
                  '\n10 Pending operations\n11 Retry operation\n12 Repeat last change with its original request ID\n0 Sign out')
            choice = input('Choice: ').strip()
            try:
                if choice == '0':
                    break
                if choice == '1':
                    show(api.request('/api/analysis-cases'))
                elif choice == '2':
                    year, make, model = input('Model year: ').strip(), input('Make: ').strip(), input('Model: ').strip()
                    from urllib.parse import urlencode
                    found = api.request('/api/vehicles/search?' + urlencode({'year': year, 'make': make, 'model': model}))['items']
                    if len(found) != 1:
                        print('No unique matching vehicle; try its exact catalogue labels.')
                        continue
                    show(change('/api/analysis-cases', {'title': input('Case title: ').strip(), 'modelYearId': found[0]['modelYearId']}))
                elif choice == '10':
                    show(api.request('/api/analysis-cases/operations'))
                elif choice == '11':
                    operation_id = input('Operation UUID: ').strip()
                    show(api.request('/api/analysis-cases/operations/' + operation_id + '/retry', {}))
                elif choice == '12':
                    if last_write:
                        path, body, method, headers = last_write
                        print('Reusing request ID:', headers['Idempotency-Key'])
                        show(api.request(path, body, method=method, headers=headers))
                    else:
                        print('No previous change in this session.')
                elif choice in {'3', '4', '5', '6', '7', '8', '9'}:
                    case_id = int(input('Case ID: '))
                    path = f'/api/analysis-cases/{case_id}'
                    if choice == '3':
                        show(api.request(path))
                    elif choice == '4':
                        field = input('Field (title/priority/status): ').strip()
                        show(change(path, {field: input('New value: ').strip()}, method='PATCH'))
                    elif choice == '5':
                        unlink = input('Action (link/unlink): ').strip() == 'unlink'
                        number = input('ODI complaint number: ').strip()
                        show(change(path + '/complaints/' + number, method='DELETE') if unlink else
                             change(path + '/complaints', {'odiNumber': number}))
                    elif choice == '6':
                        kind = input('Collection (notes/findings): ').strip()
                        action = input('Action (add/edit/remove): ').strip()
                        target = path + '/' + kind
                        if action != 'add':
                            target += '/' + input('Entry UUID from case detail: ').strip()
                        field = 'text' if kind == 'notes' else 'observation'
                        show(change(target, method='DELETE') if action == 'remove' else
                             change(target, {field: input('Content: ').strip()}, method='PATCH' if action == 'edit' else 'POST'))
                    elif choice == '7':
                        field = input('Field (tags/suspectedComponents): ').strip()
                        values = [value.strip() for value in input('Comma-separated values (blank clears): ').split(',') if value.strip()]
                        show(change(path + '/content', {field: values}, method='PATCH'))
                    elif choice == '8':
                        show(api.request(path + '/history'))
                    elif choice == '9':
                        show(change(path, method='DELETE'))
                else:
                    print('Choose a menu number.')
            except (ApiError, ValueError, OSError) as error:
                print(str(error) if isinstance(error, ApiError) else 'Check the input or local connection.')
                print('For an uncertain write response, repeat option 12 with the original request ID; inspect pending operations as well.')
    finally:
        try:
            api.request('/api/auth/logout', {})
            print('Signed out. Cases you did not delete remain stored.')
        except (ApiError, OSError):
            print('Logout unavailable; the session will expire normally.')


if __name__ == '__main__':
    main()
