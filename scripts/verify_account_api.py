"""Exercise real auth/deletion SQL through Flask using owned synthetic accounts."""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import create_app
from project_config import ROOT, postgres
from scripts.verify_cases import snapshot


def main():
    before = snapshot()
    run_id = uuid4().hex
    prefix = 'account-api-' + run_id
    emails = [prefix + '-' + suffix + '@example.invalid' for suffix in ('admin', 'unused', 'owner', 'analyst')]
    password = secrets.token_urlsafe(24)
    directory = ROOT / 'docs/account_deletion' / ('api-' + datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + run_id[:8])
    directory.mkdir(parents=True, exist_ok=False)
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'checks': [], 'successful': False,
              'scope': 'Flask test clients with real PostgreSQL auth/deletion SQL; only synthetic accounts targeted. No browser/server process or source imports.'}
    app = create_app({'TESTING': True})
    clients = [app.test_client() for _ in emails]

    def request(client, method, path, expected, body=None, csrf=True):
        headers = {}
        if method != 'GET' and csrf:
            headers['X-CSRF-Token'] = client.get('/api/auth/csrf').json['csrfToken']
        response = client.open(path, method=method, json=body, headers=headers)
        assert response.status_code == expected, f'{method} {path}: expected HTTP {expected}, got {response.status_code}'
        report['checks'].append({'method': method, 'path': path, 'status': expected})
        return response.json

    try:
        ids = [request(client, 'POST', '/api/auth/register', 201, {'email': email, 'password': password})['user']['userId']
               for client, email in zip(clients, emails)]
        with postgres() as c:
            for index, role in ((0, 'ADMIN'), (3, 'ANALYST')):
                c.execute('UPDATE app_user SET role=%s WHERE user_id=%s AND email=%s', (role, ids[index], emails[index]))
            model_year = c.execute("SELECT model_year_id FROM vehicle_catalogue WHERE make='HONDA' AND model='CIVIC' AND year=2022").fetchone()[0]
        path = '/api/admin/users/' + str(ids[1])
        request(app.test_client(), 'DELETE', path, 401, {'confirmEmail': emails[1]})
        request(clients[2], 'DELETE', path, 403, {'confirmEmail': emails[1]})
        request(clients[3], 'DELETE', path, 403, {'confirmEmail': emails[1]})
        request(clients[0], 'DELETE', path, 403, {'confirmEmail': emails[1]}, csrf=False)
        request(clients[0], 'DELETE', path, 409, {'confirmEmail': 'wrong@example.invalid'})
        request(clients[0], 'DELETE', path, 400, {'confirmEmail': emails[1], 'force': True})
        request(clients[0], 'DELETE', '/api/admin/users/' + str(ids[0]), 409, {'confirmEmail': emails[0]})
        request(clients[0], 'GET', '/api/auth/me', 200)
        saved = request(clients[2], 'POST', '/api/saved-vehicles', 201, {'modelYearId': model_year, 'nickname': 'Protected account fixture'})
        request(clients[0], 'DELETE', '/api/admin/users/' + str(ids[2]), 409, {'confirmEmail': emails[2]})
        with postgres() as c:
            assert c.execute('SELECT count(*) FROM saved_vehicle WHERE user_id=%s', (ids[2],)).fetchone()[0] == 1
        report['saved_vehicle_retained_after_conflict'] = True
        for index in (1, 3):
            result = request(clients[0], 'DELETE', '/api/admin/users/' + str(ids[index]), 200, {'confirmEmail': emails[index]})
            assert result == {'deletedUserId': ids[index]}
            request(clients[index], 'GET', '/api/auth/me', 401)
            request(clients[index], 'POST', '/api/auth/login', 401, {'email': emails[index], 'password': password})
            request(clients[0], 'DELETE', '/api/admin/users/' + str(ids[index]), 404, {'confirmEmail': emails[index]})
        request(clients[2], 'GET', '/api/auth/me', 200)
        report['deleted_user_sessions_revoked'] = True
        report['api_checks_passed'] = True
    except Exception as error:
        report['failure_type'] = type(error).__name__
    finally:
        app.extensions['mongo_client'].close()
        # Only this run's exact synthetic emails; never a real deletion target.
        with postgres() as c:
            c.execute('DELETE FROM app_user WHERE email=ANY(%s)', (emails,))
        after = snapshot()
        report['synthetic_accounts_and_owned_saves_sessions_removed'] = before == after
        report['record_counts'] = after
        report['successful'] = bool(report.get('api_checks_passed') and before == after)
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        (directory / 'api_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Account HTTP checks:', len(report['checks']), 'successful:', report['successful'])
    print('Evidence:', directory.relative_to(ROOT).as_posix())
    if not report['successful']:
        print('Failure category:', report.get('failure_type', 'cleanup count mismatch'))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
