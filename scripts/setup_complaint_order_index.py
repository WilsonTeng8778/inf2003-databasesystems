"""Add/check the measured complaint paging index, with dated native evidence.

This does not import data, reset databases, or remove any existing index.
Repeated runs retain the index and write separate verification evidence.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.complaints import search_complaints
from mongodb.schema import ensure_complaint_order_index
from project_config import ROOT, mongo_client, mongo_database, postgres
from scripts.benchmark_databases import (LOCAL, fingerprint, measure, mongo_metrics, mongo_workloads,
                                        safe_mongo_explain, source_snapshot, write_json)


def verify():
    run_id = datetime.now(LOCAL).strftime('%Y%m%dT%H%M%S') + '_' + uuid4().hex[:8]
    directory = ROOT / 'docs' / 'index_improvements' / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report = {'started_at_utc': datetime.now(timezone.utc), 'successful': False, 'checks': []}
    client = mongo_client()
    try:
        database = mongo_database(client)
        with postgres() as connection:
            before = source_snapshot(connection, database)
            identity = connection.execute("SELECT model_year_id FROM vehicle_catalogue WHERE make=%s AND model=%s AND year=%s",
                                          ('HONDA', 'CIVIC', 2022)).fetchone()[0]
        jobs = mongo_workloads(identity)
        service_options = [
            {'model_year_id': identity, 'received_from': date(2020, 1, 1), 'received_to': date(2026, 10, 22)},
            {'model_year_id': identity, 'received_from': date(2026, 1, 1), 'received_to': date(2026, 10, 22)},
            {'model_year_id': identity, 'component': 'STEERING'},
            {'model_year_id': identity, 'received_from': date(1900, 1, 1), 'received_to': date(1900, 12, 31)},
        ]
        prior_service = [fingerprint(search_complaints(database, page=page, **options))
                         for options in service_options for page in (1, 2)]
        report['service_scenarios'] = [{'filters': options, 'page': page}
                                     for options in service_options for page in (1, 2)]

        def queries(phase):
            results = []
            for definition in jobs:
                def fetch():
                    with database.complaints.find(definition['filter'], definition['projection'],
                            sort=list(definition['sort'].items()), limit=definition['limit'], max_time_ms=5000) as cursor:
                        return list(cursor)
                result = measure(fetch, 3, 15)
                plan = database.command({'explain': {'find': 'complaints', **{key: definition[key] for key in (
                    'filter', 'projection', 'sort', 'limit')}, 'maxTimeMS': 5000}, 'verbosity': 'executionStats'})
                plan_file = f"{definition['id']}_{phase}_plan.json"
                write_json(directory / plan_file, safe_mongo_explain(plan))
                results.append({'id': definition['id'], **result, 'metrics': mongo_metrics(plan), 'plan_file': plan_file})
            return results
        report['index_existed_before'] = 'vehicle_received_ordered' in database.complaints.index_information()
        report['before'] = queries('before')
        start = perf_counter_ns()
        ensure_complaint_order_index(database)
        report['create_index_call_ms'] = (perf_counter_ns() - start) / 1_000_000
        report['after'] = queries('after')
        later_service = [fingerprint(search_complaints(database, page=page, **options))
                         for options in service_options for page in (1, 2)]
        report['service_result_hashes_before'] = prior_service
        report['service_result_hashes_after'] = later_service
        report['checks'].append({'name': 'Eight service pages/counts/fields/order unchanged',
                                 'passed': prior_service == later_service})
        report['checks'].append({'name': 'Both ordered fetch results unchanged',
            'passed': all(a['ordered_result_sha256'] == b['ordered_result_sha256']
                          for a, b in zip(report['before'], report['after']))})
        report['checks'].append({'name': 'Both live queries use the new index without a blocking sort',
            'passed': all('vehicle_received_ordered' in result['metrics']['winning_indexes']
                          and 'SORT' not in result['metrics']['winning_stages'] for result in report['after'])})
        with postgres() as connection:
            after = source_snapshot(connection, database)
        old_indexes = before['mongo_indexes']['complaints']
        new_indexes = after['mongo_indexes']['complaints']
        report['checks'].append({'name': 'Every prior complaint index retained unchanged',
                                 'passed': all(index in new_indexes for index in old_indexes)})
        # Only this additive index is allowed to differ in the snapshots.
        before['mongo_indexes']['complaints'] = [index for index in old_indexes if index['name'] != 'vehicle_received_ordered']
        after['mongo_indexes']['complaints'] = [index for index in new_indexes if index['name'] != 'vehicle_received_ordered']
        report['checks'].append({'name': 'All public SQL counts/indexes and Mongo counts/other indexes unchanged',
                                 'passed': fingerprint(before) == fingerprint(after)})
        report['index_definition'] = database.complaints.index_information()['vehicle_received_ordered']
        stats = database.command('collStats', 'complaints')
        report['new_index_size_bytes'] = stats['indexSizes']['vehicle_received_ordered']
        report['successful'] = all(check['passed'] for check in report['checks'])
    except Exception as error:
        report['failure_type'] = type(error).__name__
    finally:
        client.close()
        report['finished_at_utc'] = datetime.now(timezone.utc)
        write_json(directory / 'report.json', report)
    print('Evidence:', directory.relative_to(ROOT).as_posix())
    print('Successful:', report['successful'])
    print('Checks passed:', sum(check['passed'] for check in report['checks']), '/', len(report['checks']))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(verify())
