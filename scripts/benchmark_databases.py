"""Reproducible index experiments on disposable full-sized copies, never app tables.

Run from the repository root. Evidence contains plans/hashes, not complaint text
or connection credentials. Cleanup accepts only this run's UUID namespace.
"""

import argparse
import hashlib
import json
import platform
import re
import statistics
import sys
from datetime import date, datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns
from uuid import uuid4
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from backend.services.complaints import LIST_FIELDS, complaint_query
from project_config import ROOT, mongo_client, mongo_database, postgres

LOCAL = ZoneInfo('Asia/Kuala_Lumpur')
TABLES = ('recall', 'recall_vehicle', 'recall_record')
RECEIVED_INDEX = [('modelYearId', 1), ('receivedDate', -1)]
ORDERED_INDEX = [*RECEIVED_INDEX, ('_id', -1)]
SCAN_TYPES = {'Seq Scan', 'Index Scan', 'Index Only Scan', 'Bitmap Heap Scan'}


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def write_json(path, value):
    path.write_text(json.dumps(value, default=json_value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def fingerprint(rows):
    """Order matters for rows/documents; object field order does not."""
    payload = json.dumps(rows, default=json_value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def summarize(samples):
    if len(samples) < 2 or any(value < 0 for value in samples):
        raise ValueError('At least two nonnegative measured samples are required')
    quartiles = statistics.quantiles(samples, n=4, method='inclusive')
    return {'n': len(samples), 'median_ms': statistics.median(samples),
            'p25_ms': quartiles[0], 'p75_ms': quartiles[2],
            'min_ms': min(samples), 'max_ms': max(samples)}


def measure(fetch, warmups, samples, expected=None):
    warmup_times, timings = [], []
    digest, count = expected, None
    for position in range(warmups + samples):
        start = perf_counter_ns()
        rows = fetch()
        elapsed = (perf_counter_ns() - start) / 1_000_000
        # Hashing is deliberately outside the measured fetch/decode interval.
        actual = fingerprint(rows)
        if digest is None:
            digest = actual
        if digest != actual:
            raise AssertionError('Ordered results changed across runs/index phases')
        count = len(rows)
        (warmup_times if position < warmups else timings).append(elapsed)
    return {'warmup_ms': warmup_times, 'samples_ms': timings,
            'result_count': count, 'ordered_result_sha256': digest, 'summary': summarize(timings)}


def owned_namespace(name, expected):
    if name != expected or not re.fullmatch(r'bench_[0-9a-f]{32}', name):
        raise ValueError('Refusing an unowned benchmark namespace')
    return name


def pg_metrics(explain):
    root = explain[0]['Plan']
    nodes = []

    def visit(node):
        if node.get('Node Type') in SCAN_TYPES:
            nodes.append({key: node[key] for key in (
                'Node Type', 'Relation Name', 'Index Name', 'Actual Rows', 'Actual Loops',
                'Rows Removed by Filter', 'Rows Removed by Index Recheck', 'Heap Fetches',
            ) if key in node})
        for child in node.get('Plans', []):
            visit(child)
    visit(root)
    return {'execution_ms': explain[0]['Execution Time'], 'planning_ms': explain[0]['Planning Time'],
            'returned_rows': root['Actual Rows'] * root['Actual Loops'],
            # Parent buffer counters include their children: do not sum nodes.
            'shared_hit_blocks': root.get('Shared Hit Blocks', 0),
            'shared_read_blocks': root.get('Shared Read Blocks', 0),
            'scan_rows_processed_estimate': sum((node.get('Actual Rows', 0)
                + node.get('Rows Removed by Filter', 0) + node.get('Rows Removed by Index Recheck', 0))
                * node.get('Actual Loops', 0) for node in nodes), 'scans': nodes}


def mongo_metrics(explain):
    stages, indexes = set(), set()

    def visit(value):
        if isinstance(value, dict):
            if 'stage' in value:
                stages.add(value['stage'])
            if 'indexName' in value:
                indexes.add(value['indexName'])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    # Do not accidentally report stages/indexes from rejected plans.
    visit(explain['queryPlanner']['winningPlan'])
    stats = explain['executionStats']
    return {**{key: stats[key] for key in (
        'nReturned', 'executionTimeMillis', 'totalDocsExamined', 'totalKeysExamined')},
        'winning_stages': sorted(stages), 'winning_indexes': sorted(indexes)}


def safe_mongo_explain(explain):
    # The native response also includes server hostname/port and other diagnostics.
    # Preserve complete planner/execution trees, whitelist the surrounding fields.
    return {key: explain[key] for key in ('explainVersion', 'queryPlanner', 'executionStats') if key in explain}


def source_snapshot(connection, database):
    tables = [row[0] for row in connection.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
    counts = {table: connection.execute(sql.SQL('SELECT count(*) FROM public.{}').format(
        sql.Identifier(table))).fetchone()[0] for table in tables}
    indexes = connection.execute(
        "SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname"
    ).fetchall()
    return {'postgres_counts': counts, 'postgres_indexes': indexes,
            'mongo_counts': {name: database[name].count_documents({}) for name in ('complaints', 'case_details')},
            'mongo_indexes': {name: list(database[name].list_indexes()) for name in ('complaints', 'case_details')}}


def environment(connection, client):
    settings = ['shared_buffers', 'work_mem', 'effective_cache_size', 'random_page_cost',
                'max_parallel_workers_per_gather', 'jit', 'default_statistics_target']
    result = {'os': f'{platform.system()} {platform.release()}', 'architecture': platform.machine(),
              'python': platform.python_version(), 'logical_cpu_threads': __import__('os').cpu_count(),
              'drivers': {name: version(name) for name in ('psycopg', 'pymongo')},
              'postgres_version': connection.execute('SHOW server_version').fetchone()[0],
              'mongo_version': client.server_info()['version'],
              'postgres_settings': {name: connection.execute(sql.SQL('SHOW {}').format(
                  sql.Identifier(name))).fetchone()[0] for name in settings}}
    if sys.platform == 'win32':
        import ctypes
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as key:
            result['cpu'] = winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()

        class Memory(ctypes.Structure):
            _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
                (name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total',
                    'page_available', 'virtual_total', 'virtual_available', 'extended')]
        memory = Memory()
        memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            result['physical_ram_bytes'] = memory.total
    return result


def sql_workloads(namespace, model_year_id):
    table = lambda name: sql.Identifier(namespace, name)
    return [
        {'id': 'pg_recall_lookup', 'parameters': [model_year_id], 'query': sql.SQL('''
SELECT r.campaign_number, r.report_date, r.summary
FROM {} rv JOIN {} r ON r.recall_id=rv.recall_id
WHERE rv.model_year_id=%s
ORDER BY r.report_date DESC NULLS LAST, r.campaign_number''').format(table('recall_vehicle'), table('recall'))},
        {'id': 'pg_component_source_rows', 'parameters': [model_year_id, 'STEERING'], 'query': sql.SQL('''
SELECT rr.source_record_id, r.campaign_number, rr.component, rr.manufacturing_started, rr.manufacturing_ended
FROM {} rr JOIN {} r ON r.recall_id=rr.recall_id
WHERE rr.model_year_id=%s AND rr.component=%s
ORDER BY rr.source_record_id LIMIT 20''').format(table('recall_record'), table('recall'))},
    ]


def mongo_workloads(model_year_id):
    return [{'id': identifier, 'filter': complaint_query(model_year_id=model_year_id,
            received_from=date.fromisoformat(start), received_to=date(2026, 10, 22)),
             'projection': LIST_FIELDS, 'sort': {'receivedDate': -1, '_id': -1}, 'limit': 20}
            for identifier, start in [('mongo_complaints_full_window', '2020-01-01'),
                                       ('mongo_complaints_2026', '2026-01-01')]]


def run(samples, warmups):
    namespace = 'bench_' + uuid4().hex
    started = datetime.now(timezone.utc)
    run_id = started.astimezone(LOCAL).strftime('%Y%m%dT%H%M%S') + '_' + namespace[-8:]
    directory = ROOT / 'docs' / 'benchmarks' / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {'run_id': run_id, 'started_at_utc': started, 'local_timezone': str(LOCAL),
              'namespace': namespace, 'method': {
                  'measured_samples_per_round': samples, 'excluded_warmups_per_round': warmups,
                  'rounds': 2, 'cache': 'Warm OS/DB cache; no cache flush or DB restart',
                  'timing': 'Client wall time through full fetch/decode; excludes hashing and EXPLAIN',
                  'connections': 'One reused local connection per DB; PostgreSQL auto-prepare disabled',
                  'hints': 'None; optimizers choose plans',
                  'postgres_phase_order': ['baseline', 'indexed', 'indexed', 'baseline'],
                  'mongo_phase_order': ['baseline', 'current', 'candidate', 'candidate', 'current', 'baseline'],
                  'baseline': 'Primary-key indexes retained; secondary workload indexes removed only from copies'},
              'workloads': [], 'cleanup': {'postgres_schema_removed': False, 'mongo_collection_removed': False}}
    pg_owned = mongo_owned = False
    connection = client = None
    error = None
    try:
        connection = postgres(autocommit=True, prepare_threshold=None,
                              options='-c statement_timeout=120000 -c lock_timeout=5000')
        client = mongo_client()
        database = mongo_database(client)
        report['environment'] = environment(connection, client)
        report['source_before'] = source_snapshot(connection, database)
        identity = connection.execute("SELECT model_year_id FROM vehicle_catalogue WHERE make=%s AND model=%s AND year=%s",
                                      ('HONDA', 'CIVIC', 2022)).fetchone()
        if not identity:
            raise AssertionError('The predefined benchmark vehicle is absent')
        model_year_id = identity[0]
        report['selection'] = {'make': 'HONDA', 'model': 'CIVIC', 'year': 2022, 'model_year_id': model_year_id}
        owned_namespace(namespace, namespace)
        connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(namespace)))
        pg_owned = True
        for name in TABLES:
            connection.execute(sql.SQL('CREATE TABLE {} AS SELECT * FROM public.{}').format(
                sql.Identifier(namespace, name), sql.Identifier(name)))
            columns = {'recall': ['recall_id'], 'recall_vehicle': ['recall_id', 'model_year_id'],
                       'recall_record': ['source_record_id']}[name]
            connection.execute(sql.SQL('ALTER TABLE {} ADD PRIMARY KEY ({})').format(
                sql.Identifier(namespace, name), sql.SQL(',').join(map(sql.Identifier, columns))))
            connection.execute(sql.SQL('VACUUM (ANALYZE) {}').format(sql.Identifier(namespace, name)))
        report['copied_sql_counts'] = {name: connection.execute(sql.SQL('SELECT count(*) FROM {}').format(
            sql.Identifier(namespace, name))).fetchone()[0] for name in TABLES}
        for name, count in report['copied_sql_counts'].items():
            assert count == report['source_before']['postgres_counts'][name], 'Incomplete SQL copy'

        # Explicit creation establishes ownership before copying. $merge never removes
        # or updates source documents and does not copy source indexes.
        database.create_collection(namespace)
        mongo_owned = True
        print('Copying all complaint documents into the owned benchmark collection...', flush=True)
        list(database.complaints.aggregate([{'$match': {}}, {'$merge': {
            'into': namespace, 'on': '_id', 'whenMatched': 'fail', 'whenNotMatched': 'insert'}}], maxTimeMS=120000))
        collection = database[namespace]
        report['copied_mongo_count'] = collection.count_documents({})
        assert report['copied_mongo_count'] == report['source_before']['mongo_counts']['complaints'], 'Incomplete Mongo copy'

        def pg_phase(phase):
            for name in ('bench_vehicle_recall', 'bench_source_vehicle'):
                connection.execute(sql.SQL('DROP INDEX IF EXISTS {}').format(sql.Identifier(namespace, name)))
            if phase == 'indexed':
                for name, table, columns in [('bench_vehicle_recall', 'recall_vehicle', ['model_year_id', 'recall_id']),
                                              ('bench_source_vehicle', 'recall_record', ['model_year_id', 'recall_id'])]:
                    connection.execute(sql.SQL('CREATE INDEX {} ON {} ({})').format(sql.Identifier(name),
                        sql.Identifier(namespace, table), sql.SQL(',').join(map(sql.Identifier, columns))))

        pg_jobs = sql_workloads(namespace, model_year_id)
        for job in pg_jobs:
            job['definition'] = {'sql': job.pop('query').as_string(connection), 'parameters': job.pop('parameters')}
            job['database'] = 'PostgreSQL'
            job['phases'] = {name: {'rounds': []} for name in ('baseline', 'indexed')}
        report['workloads'].extend(pg_jobs)
        for position, phase in enumerate(report['method']['postgres_phase_order']):
            pg_phase(phase)
            for job in pg_jobs:
                definition = job['definition']
                expected = job.get('ordered_result_sha256')
                result = measure(lambda: connection.execute(definition['sql'], definition['parameters']).fetchall(),
                                 warmups, samples, expected)
                job['ordered_result_sha256'] = result['ordered_result_sha256']
                plan = connection.execute('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) ' + definition['sql'],
                                          definition['parameters']).fetchone()[0]
                plan_file = f"{job['id']}_{phase}_{position + 1}_plan.json"
                write_json(directory / plan_file, plan)
                result.update({'metrics': pg_metrics(plan), 'plan_file': plan_file})
                job['phases'][phase]['rounds'].append(result)
            report.setdefault('sql_copy_indexes', {})[phase] = connection.execute(
                'SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname=%s ORDER BY tablename,indexname',
                (namespace,)).fetchall()
            print('Measured PostgreSQL phase:', phase, flush=True)

        mongo_jobs = [{'id': definition['id'], 'database': 'MongoDB', 'definition': definition,
                       'matched_documents': collection.count_documents(definition['filter']),
                       'phases': {name: {'rounds': []} for name in ('baseline', 'current', 'candidate')}}
                      for definition in mongo_workloads(model_year_id)]
        report['workloads'].extend(mongo_jobs)
        for position, phase in enumerate(report['method']['mongo_phase_order']):
            for index in list(collection.list_indexes()):
                if index['name'] != '_id_':
                    collection.drop_index(index['name'])
            if phase in ('current', 'candidate'):
                collection.create_index(RECEIVED_INDEX, name='vehicle_received')
            if phase == 'candidate':
                collection.create_index(ORDERED_INDEX, name='vehicle_received_ordered')
            for job in mongo_jobs:
                definition = job['definition']

                def fetch():
                    with collection.find(definition['filter'], definition['projection'],
                            sort=list(definition['sort'].items()), limit=definition['limit'], max_time_ms=60000) as cursor:
                        return list(cursor)
                result = measure(fetch, warmups, samples, job.get('ordered_result_sha256'))
                job['ordered_result_sha256'] = result['ordered_result_sha256']
                plan = database.command({'explain': {'find': namespace, **{key: definition[key] for key in (
                    'filter', 'projection', 'sort', 'limit')}, 'maxTimeMS': 60000}, 'verbosity': 'executionStats'})
                plan_file = f"{job['id']}_{phase}_{position + 1}_plan.json"
                write_json(directory / plan_file, safe_mongo_explain(plan))
                result.update({'metrics': mongo_metrics(plan), 'plan_file': plan_file})
                job['phases'][phase]['rounds'].append(result)
            report.setdefault('mongo_copy_indexes', {})[phase] = list(collection.list_indexes())
            print('Measured MongoDB phase:', phase, flush=True)
        for job in report['workloads']:
            for phase in job['phases'].values():
                phase['summary'] = summarize([value for result in phase['rounds'] for value in result['samples_ms']])
        report['copy_sizes'] = {'postgres_total_bytes': {name: connection.execute(
            'SELECT pg_total_relation_size(%s::regclass)', (f'{namespace}.{name}',)).fetchone()[0] for name in TABLES},
            'mongodb': {key: value for key, value in database.command('collStats', namespace).items()
                        if key in ('count', 'size', 'storageSize', 'totalIndexSize')}}
    except Exception as exc:
        # Exception messages may contain connection details. Save only the type.
        error = type(exc).__name__
        report['failure_type'] = error
    finally:
        cleanup_errors = []
        owned_namespace(namespace, namespace)
        if pg_owned:
            try:
                connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(namespace)))
                report['cleanup']['postgres_schema_removed'] = connection.execute(
                    'SELECT NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname=%s)', (namespace,)).fetchone()[0]
            except Exception as exc:
                cleanup_errors.append({'postgres': type(exc).__name__})
        if mongo_owned:
            try:
                database.drop_collection(namespace)
                report['cleanup']['mongo_collection_removed'] = namespace not in database.list_collection_names()
            except Exception as exc:
                cleanup_errors.append({'mongodb': type(exc).__name__})
        if connection is not None and client is not None:
            try:
                report['source_after'] = source_snapshot(connection, database)
                report['source_counts_and_indexes_unchanged'] = fingerprint(report['source_before']) == fingerprint(report['source_after'])
            except Exception as exc:
                cleanup_errors.append({'source_check': type(exc).__name__})
        report['cleanup_errors'] = cleanup_errors
        report['finished_at_utc'] = datetime.now(timezone.utc)
        report['successful'] = (error is None and not cleanup_errors and all(report['cleanup'].values())
                                and report.get('source_counts_and_indexes_unchanged') is True)
        write_json(directory / 'report.json', report)
        if connection is not None:
            connection.close()
        if client is not None:
            client.close()
    print('Evidence:', directory.relative_to(ROOT).as_posix())
    print('Successful:', report['successful'])
    if not report['successful']:
        print('Failure category:', error or 'Cleanup/source-invariance check failed')
        return 1
    for job in report['workloads']:
        print(job['id'], {name: round(phase['summary']['median_ms'], 3) for name, phase in job['phases'].items()})
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--samples', type=int, default=15, help='Measured runs per phase in each of two rounds (2..100)')
    parser.add_argument('--warmups', type=int, default=3, help='Excluded warmups per phase/round (1..20)')
    args = parser.parse_args()
    if not 2 <= args.samples <= 100 or not 1 <= args.warmups <= 20:
        parser.error('Use samples 2..100 and warmups 1..20')
    return run(args.samples, args.warmups)


if __name__ == '__main__':
    raise SystemExit(main())
