"""Real local Chromium browser journeys with owned synthetic account cleanup."""

import argparse
import json
import secrets
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server
from backend import create_app
from project_config import ROOT, postgres, mongo_client, mongo_database
from scripts.verify_api import QuietHandler
from scripts.verify_cases import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--research', action='store_true', help='Also check the full research explorer/relationships; write step-2 evidence separately.')
    parser.add_argument('--cases', action='store_true', help='Include analyst cases, role boundaries and controlled recovery; write step-3 evidence separately.')
    parser.add_argument('--fleets', action='store_true', help='Include fleet/work-order journeys and all earlier checks; write step-4 evidence separately.')
    parser.add_argument('--admin', action='store_true', help='Include admin roles/data/import pages and all earlier checks; write step-5 evidence separately.')
    parser.add_argument('--analytics', action='store_true', help='Include native analytics and dashboard journeys plus earlier checks; write step-6 evidence separately.')
    parser.add_argument('--accounts', action='store_true', help='Include account deletion and earlier journeys; write unique dated evidence without replacing milestones.')
    args = parser.parse_args()
    include_analytics = args.analytics or args.accounts
    include_admin = args.admin or include_analytics
    include_cases = args.cases or args.fleets or include_admin
    milestone = 7 if args.accounts else 6 if args.analytics else 5 if args.admin else 4 if args.fleets else 3 if args.cases else 2 if args.research else 1
    node = shutil.which('node')
    candidates = [Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),
                  Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')]
    browser = next((path for path in candidates if path.is_file()), None)
    if not node or browser is None:
        raise SystemExit('Browser checks require Node.js 22+ and an installed Chrome/Edge. Application startup does not require Node.')
    before = snapshot()
    run_id = uuid4().hex
    suffixes = ['owner', 'other'] + (['analyst', 'analyst-other', 'admin'] if include_cases else [])
    if include_admin:suffixes += ['pagination-'+str(n) for n in range(8)]
    if args.accounts:suffixes += ['delete-success','delete-lost','delete-json','delete-used']
    emails = [f'frontend-verification-{run_id}-{suffix}@example.invalid' for suffix in suffixes]
    password = secrets.token_urlsafe(24)
    profile_path = ROOT / 'data/logs' / ('frontend-' + run_id) / 'browser-profile'
    screenshots = ROOT / f'docs/screenshots/frontend-step-{milestone}'
    evidence_directory = ROOT / 'docs/account_deletion' / ('browser-' + datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + run_id[:8])
    if args.accounts:screenshots = evidence_directory / 'screenshots'
    app = create_app()
    server = make_server('127.0.0.1', 0, app, threaded=True, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = {'baseUrl': f'http://127.0.0.1:{server.server_port}', 'emails': emails, 'password': password,
              'profilePath': str(profile_path), 'screenshotPath': str(screenshots), 'browserPath': str(browser),
              'includeResearch': args.research or include_cases, 'includeCases': include_cases, 'includeFleets': args.fleets or include_admin,
              'includeAdmin': include_admin, 'includeAnalytics':include_analytics, 'includeAccounts':args.accounts, 'caseFixtures': None}
    admin_assertions=[]
    analytics_assertions=None
    account_assertions=[]
    with postgres() as connection:
        import_rows_before=connection.execute('SELECT count(*) FROM data_import_log').fetchone()[0]
    try:
        if include_cases:
            from scripts.frontend_case_fixtures import prepare_case_fixtures
            config['caseFixtures'] = prepare_case_fixtures(app, config['baseUrl'], emails, password, 'Pending browser-test note ' + run_id)
        if include_admin:
            from scripts.frontend_admin_fixtures import prepare_admin_fixtures
            admin_assertions=prepare_admin_fixtures(config['baseUrl'],emails,password,config['caseFixtures']['adminId'])
        if include_analytics:
            from scripts.analytics_checks import native_analytics_checks
            analytics_assertions=native_analytics_checks()
        if args.accounts:
            from scripts.local_api import ApiError, LocalApi
            account_clients=[];config['accountFixtures']=[]
            for email in emails[-4:]:
                client=LocalApi(config['baseUrl']);client.request('/api/auth/csrf')
                user=client.request('/api/auth/login',{'email':email,'password':password},method='POST')['user']
                account_clients.append(client);config['accountFixtures'].append(user)
            with postgres() as connection:
                vehicle_id=connection.execute("SELECT model_year_id FROM vehicle_catalogue WHERE make='HONDA' AND model='CIVIC' AND year=2022").fetchone()[0]
            account_clients[-1].request('/api/saved-vehicles',{'modelYearId':vehicle_id,'nickname':'Account deletion guard fixture'},method='POST')
        result = subprocess.run([node, str(ROOT / 'scripts/browser_frontend_checks.mjs')], input=json.dumps(config),
                                text=True, encoding='utf-8', capture_output=True, cwd=ROOT, timeout=600)
        if result.returncode:
            print(result.stderr.replace(password, '[redacted]'), file=sys.stderr)
            raise RuntimeError('Browser checks failed; owned fixture cleanup still runs.')
        browser_report = json.loads(result.stdout)
        if args.accounts:
            for index,client in enumerate(account_clients):
                try:
                    client.request('/api/auth/me')
                except ApiError:
                    pass
                assert client.last_status==(401 if index<3 else 200), 'Unexpected target-session state after account deletion'
            account_assertions.append('Three independently signed-in target sessions are revoked after browser deletion; protected owner session remains valid.')
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close()
        app.extensions['mongo_client'].close()
        with postgres() as connection, mongo_client() as cleanup_client:
            if include_cases:
                owned_users = [row[0] for row in connection.execute('SELECT user_id FROM app_user WHERE email=ANY(%s)', (emails,)).fetchall()]
                owned_cases = [row[0] for row in connection.execute('''SELECT case_id FROM analysis_case WHERE created_by=ANY(%s)
                    UNION SELECT case_id FROM case_content_operation WHERE owner_id=ANY(%s)''', (owned_users, owned_users)).fetchall()]
                if owned_cases:
                    mongo_database(cleanup_client).case_details.delete_many({'caseId': {'$in': owned_cases}})
                connection.execute('DELETE FROM analysis_case WHERE created_by=ANY(%s)', (owned_users,))
                connection.execute('DELETE FROM case_content_operation WHERE owner_id=ANY(%s)', (owned_users,))
            connection.execute('DELETE FROM app_user WHERE email=ANY(%s)', (emails,))
        # Delete only this owned browser profile, after checking its absolute target.
        resolved = profile_path.resolve()
        if not resolved.is_relative_to((ROOT / 'data/logs').resolve()) or resolved.name != 'browser-profile':
            raise RuntimeError('Unexpected browser profile cleanup target')
        if resolved.exists():
            shutil.rmtree(resolved, ignore_errors=True)
    after = snapshot()
    assert before == after, 'Synthetic accounts/saves remain or unrelated stored counts changed'
    with postgres() as connection:
        account_roles = dict(connection.execute('SELECT role,count(*) FROM app_user GROUP BY role ORDER BY role').fetchall())
        assert connection.execute('SELECT count(*) FROM data_import_log').fetchone()[0]==import_rows_before
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), **browser_report,
              'owned_synthetic_accounts_saves_sessions_removed': True, 'record_counts_unchanged_after_cleanup': True,
              'record_counts': after, 'screenshots_directory': screenshots.relative_to(ROOT).as_posix(),
              'case_recovery_faults_injected_only_in_owned_verifier': include_cases,
              'admin_native_assertions': admin_assertions, 'existing_import_history_preserved': True,
              'analytics_native_checks': analytics_assertions,
              'account_deletion_native_assertions': account_assertions,
              'account_role_check': {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'counts': account_roles},
              'limitations': ['Browser journeys were checked in the installed Chromium browser at desktop and 390px mobile sizes.',
                             'These checks do not establish compatibility with every browser or a complete accessibility audit.',
                             ('Admin import initiation and broader final whole-application evaluation remain.' if args.accounts else 'Performance benchmarks and final whole-application evaluation remain.' if args.analytics else 'Analytics integration and performance benchmarks remain.' if args.admin else 'Admin browser screens, analytics and performance benchmarks remain.' if args.fleets else 'Fleet/admin browser screens, analytics and performance benchmarks remain.' if include_cases else 'Case/fleet/admin browser screens, analytics and performance benchmarks remain.'),
                             'Controlled case projection/deletion faults leave the real database services running; they are enabled only for the case verifier.',
                             'The JSON discovery endpoint moved from / to /api; / now serves the browser interface.']}
    report_path = ROOT / f'docs/frontend_step_{milestone}_verification_report.json'
    if args.accounts:
        evidence_directory.mkdir(parents=True,exist_ok=True)
        report_path=evidence_directory / 'frontend_report.json'
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f"Passed {len(report['checks'])} real-browser checks in {report['browser']}; owned fixtures removed and counts preserved.")
    print('Evidence: ' + report_path.relative_to(ROOT).as_posix())


if __name__ == '__main__':
    main()
