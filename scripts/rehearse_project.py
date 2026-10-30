"""Run the current technical acceptance journeys and retain one dated evidence index.

Uses owned verifier fixtures, never a full real-source import. This is not a
five-member presentation rehearsal or a fresh-machine/package installation.
"""

import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from project_config import ROOT, mongo_client, mongo_database, postgres
from scripts.admin_import import approved_sources
from scripts.benchmark_databases import fingerprint, mongo_workloads, sql_workloads, summarize, pg_metrics, mongo_metrics
from scripts.verify_cases import snapshot

LOCAL = ZoneInfo('Asia/Kuala_Lumpur')
SOURCE_DIRS = {'backend', 'etl', 'mongodb', 'sql', 'scripts', 'tests'}
SOURCE_FILES = {'.env.example', 'project_config.py', 'requirements.txt', 'requirements-evaluation.txt', 'AGENTS.md'}


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def source_snapshot(*, root=None, paths=None):
    root = Path(root or ROOT).resolve()
    if paths is None:
        raw = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=root)
        paths = raw.decode('utf-8').split('\0')
    files = {}
    for name in sorted(set(paths)):
        if not name:
            continue
        relative = Path(name)
        if relative.name == '.env' or '__pycache__' in relative.parts:
            continue
        if relative.parts[0] not in SOURCE_DIRS and name not in SOURCE_FILES:
            continue
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            raise ValueError('Implementation snapshot cannot follow a path outside the repository')
        if target.is_file():
            files[relative.as_posix()] = sha256(target)
    return {'file_count': len(files), 'files_sha256': files, 'snapshot_sha256': fingerprint(files)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def record_counts():
    result = snapshot()
    with postgres() as connection:
        result['data_import_log'] = connection.execute('SELECT count(*) FROM data_import_log').fetchone()[0]
    return result


def performance_evidence():
    """Validate saved evidence and today's result equivalence, without timing it."""
    folder = ROOT / 'docs/benchmarks/20261029T235059_28426da4'
    report = json.loads((folder / 'report.json').read_text(encoding='utf-8'))
    assert report['successful'], 'The saved benchmark run must be successful'
    files = ['report.json', 'summary.csv', 'postgres_timings.png', 'postgres_timings.svg',
             'mongodb_timings.png', 'mongodb_timings.svg', 'figure_metadata.json']
    jobs = {job['id']: job for job in report['workloads']}
    result = {'benchmark_original_started_at_utc': report['started_at_utc'],
              'benchmark_report': (folder / 'report.json').relative_to(ROOT).as_posix(),
              'timings_rerun': False, 'current_result_checks': [], 'plan_files_checked': 0}
    for job in report['workloads']:
        for phase in job['phases'].values():
            timings = [value for part in phase['rounds'] for value in part['samples_ms']]
            assert summarize(timings) == phase['summary'], 'Saved timing summary does not match raw samples'
            for part in phase['rounds']:
                assert part['ordered_result_sha256'] == job['ordered_result_sha256']
                path = (folder / part['plan_file']).resolve()
                assert path.is_relative_to(folder.resolve()) and path.is_file()
                plan = json.loads(path.read_text(encoding='utf-8'))
                metrics = pg_metrics(plan) if job['database'] == 'PostgreSQL' else mongo_metrics(plan)
                assert metrics == part['metrics'], 'Saved plan metrics do not match the raw plan'
                files.append(part['plan_file']);result['plan_files_checked'] += 1
    # Construct known, current read-only queries from application code. Never
    # execute SQL strings or Mongo commands supplied by a saved report.
    identity = report['selection']['model_year_id']
    with postgres(options='-c default_transaction_read_only=on -c statement_timeout=10000') as connection:
        for job in sql_workloads('public', identity):
            rows = connection.execute(job['query'], job['parameters']).fetchall()
            assert fingerprint(rows) == jobs[job['id']]['ordered_result_sha256'], 'Current SQL benchmark results changed'
            result['current_result_checks'].append({'workload': job['id'], 'returned': len(rows), 'ordered_result_matches': True})
    with mongo_client() as client:
        database = mongo_database(client)
        for job in mongo_workloads(identity):
            with database.complaints.find(job['filter'], job['projection'], sort=list(job['sort'].items()), limit=job['limit'], max_time_ms=5000) as cursor:
                rows = list(cursor)
            assert fingerprint(rows) == jobs[job['id']]['ordered_result_sha256'], 'Current MongoDB benchmark results changed'
            result['current_result_checks'].append({'workload': job['id'], 'returned': len(rows), 'ordered_result_matches': True})
    result['artifact_sha256'] = {name: sha256(folder / name) for name in files}
    result['successful'] = len(result['current_result_checks']) == 4
    return result


def evidence_path(output, filename):
    matches = [line[len('Evidence: '):].strip() for line in output.splitlines() if line.startswith('Evidence: ')]
    if len(matches) != 1:
        raise ValueError('Expected exactly one verifier evidence path')
    path = (ROOT / matches[0]).resolve()
    if path.is_dir():
        path = path / filename
    if not path.is_relative_to((ROOT / 'docs').resolve()) or path.suffix != '.json' or not path.is_file():
        raise ValueError('Verifier evidence must be a JSON file inside docs')
    return path


def child_summary(name, report):
    result = {'checks': len(report.get('checks', [])), 'verified_at_utc': report['verified_at_utc']}
    if name in ('case_workflows', 'fleet_workflows'):
        assert report['record_counts_unchanged_after_cleanup'] and report['interactive_menu_verified']
        if name == 'case_workflows':
            assert report['server_recreation_recovery_verified'] and report['concurrent_requests_verified']
            assert report['synthetic_accounts_cases_content_operations_removed']
            result['server_recreation_recovery_verified'] = True
        else:
            assert report['native_composite_foreign_key_verified'] and report['owned_synthetic_accounts_fleets_vehicles_orders_sessions_removed']
            result['concurrent_checks'] = len(report['concurrent_checks'])
        result['native_assertions'] = len(report['assertions_passed'])
    elif name == 'browser_journeys':
        assert report['uncaught_browser_exceptions'] == 0
        assert report['owned_synthetic_accounts_saves_sessions_removed'] and report['record_counts_unchanged_after_cleanup'] and report['existing_import_history_preserved']
        assert report['analytics_native_checks']['owned_collection_removed']
        result['browser'] = report['browser']
        result['native_admin_assertions'] = len(report['admin_native_assertions'])
        result['native_analytics_assertions'] = len(report['analytics_native_checks']['assertions'])
        result['native_account_assertions'] = len(report['account_deletion_native_assertions'])
        result['screenshots_directory'] = report['screenshots_directory']
    else:
        assert report['successful'], 'Native verifier reported failure'
    assert result['checks'] > 0
    result['successful'] = True
    return result


def main():
    started = datetime.now(timezone.utc)
    run_id = started.astimezone(LOCAL).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
    directory = ROOT / 'docs/rehearsals' / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {'started_at_utc': started.isoformat(), 'timezone': str(LOCAL), 'successful': False,
              'scope': 'Automated technical integration rehearsal on this working checkout; no full real-source import, fresh-machine install or timed team presentation.',
              'steps': [], 'pending_human_checks': ['Five-member normal-speed presentation rehearsal and speaker names',
                  'Teammate installation from the final source/data package and manual',
                  'Final report/template/page count, slides, MP4 duration and submission package/marker access']}
    before = counts_before = config_before = None
    lock_connection = None
    history = {path: sha256(path) for path in (ROOT / 'docs').glob('*verification_report.json')}
    baseline = ROOT / 'docs/readiness/20261030_review.json'
    for item in json.loads(baseline.read_text())['historical_evidence']:
        path = ROOT / item['path'];history[path] = sha256(path)
    settings = dotenv_values(ROOT / '.env', interpolate=False)
    sensitive = [value for key, value in settings.items() if value and ('PASSWORD' in key or 'SECRET' in key)]

    def sanitized(text):
        for value in sensitive:
            text = text.replace(value, '[redacted]')
        return text

    def command(name, arguments, *, filename=None):
        print('Running ' + name + '...', flush=True)
        start = perf_counter()
        completed = subprocess.run([sys.executable, *arguments], cwd=ROOT, text=True, encoding='utf-8',
                                   errors='replace', capture_output=True, timeout=900)
        step = {'name': name, 'command': [sys.executable, *arguments], 'exit_code': completed.returncode,
                'elapsed_seconds': round(perf_counter() - start, 3)}
        report['steps'].append(step)
        if completed.returncode:
            step['successful'] = False
            print(sanitized((completed.stdout + '\n' + completed.stderr)[-2800:]), flush=True)
            raise RuntimeError('A rehearsal verifier failed: ' + name)
        if name == 'automated_tests':
            log = completed.stdout + completed.stderr
            match = re.search(r'Ran (\d+) tests? in', log)
            assert match and re.search(r'\nOK(?:\s|$)', log), 'No successful unit test result found'
            step.update({'tests_run': int(match[1]), 'successful': True, 'log': 'automated_tests.txt'})
            (directory / 'automated_tests.txt').write_text(sanitized(log), encoding='utf-8')
        else:
            path = evidence_path(completed.stdout, filename)
            step.update(child_summary(name, json.loads(path.read_text(encoding='utf-8'))))
            step['evidence'] = path.relative_to(ROOT).as_posix();step['evidence_sha256'] = sha256(path)
        write_json(directory / 'progress.json', report)
        print('Passed ' + name + '.', flush=True)

    try:
        lock_connection = postgres(autocommit=True)
        assert lock_connection.execute('SELECT pg_try_advisory_lock(2003192027)').fetchone()[0], 'Another integration rehearsal is running'
        before = source_snapshot();assert before['file_count'] > 0
        report['source_before'] = before
        report['git_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        report['working_tree_dirty'] = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
        config_before = sha256(ROOT / '.env')  # Compared only in memory; never persisted.
        counts_before = record_counts();report['record_counts_before'] = counts_before
        report['source_archives_before'] = approved_sources()
        with mongo_client() as client:
            report['environment'] = {'python': platform.python_version(), 'os': platform.system() + ' ' + platform.release(),
                'postgres': lock_connection.execute('SHOW server_version').fetchone()[0], 'mongodb': client.server_info()['version'],
                'psycopg': version('psycopg'), 'pymongo': version('pymongo')}
        command('automated_tests', ['-m', 'unittest', 'discover', '-s', 'tests', '-v'])
        command('case_workflows', ['scripts/verify_cases.py', '--report-path', str(directory / 'cases_report.json')], filename='report.json')
        command('fleet_workflows', ['scripts/verify_fleets.py', '--report-path', str(directory / 'fleets_report.json')], filename='report.json')
        command('account_database_guards', ['scripts/verify_account_deletion.py'], filename='native_report.json')
        command('account_http_workflow', ['scripts/verify_account_api.py'], filename='api_report.json')
        command('admin_import_workflow', ['scripts/verify_admin_import.py'], filename='native_report.json')
        command('browser_journeys', ['scripts/verify_frontend.py', '--accounts'], filename='frontend_report.json')
        report['performance_evidence'] = performance_evidence()
        report['technical_checks_completed'] = True
    except Exception as error:
        report['failure_type'] = type(error).__name__
    finally:
        try:
            if before is not None:
                report['source_after'] = source_snapshot()
                report['tested_source_unchanged'] = before['snapshot_sha256'] == report['source_after']['snapshot_sha256']
                report['record_counts_after'] = record_counts()
                report['original_record_counts_retained'] = counts_before == report['record_counts_after']
                report['private_configuration_unchanged'] = config_before == sha256(ROOT / '.env')
                report['source_archives_after'] = approved_sources()
                report['source_archives_unchanged'] = report['source_archives_before'] == report['source_archives_after']
            report['historical_evidence_retained'] = all(sha256(path) == value for path, value in history.items())
        except Exception as error:
            report['final_check_failure_type'] = type(error).__name__
        if lock_connection is not None:
            lock_connection.close()  # Releases only this coordinator's session lock.
        report['successful'] = bool(report.get('technical_checks_completed') and all(report.get(key) is True for key in (
            'tested_source_unchanged', 'original_record_counts_retained', 'private_configuration_unchanged',
            'source_archives_unchanged', 'historical_evidence_retained')))
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(directory / 'report.json', report)
    print('Technical rehearsal successful:', report['successful'])
    print('Evidence:', (directory / 'report.json').relative_to(ROOT).as_posix())
    if not report['successful']:
        print('Failure category:', report.get('failure_type', report.get('final_check_failure_type', 'final consistency check')))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
