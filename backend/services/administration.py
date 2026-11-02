"""Bounded read-only dataset/import monitoring through explicit SQL projections."""

from datetime import datetime, timezone

from etl.source import SOURCES

DATASETS = {
    'vehicle_catalogue': ('Vehicle catalogue', 'PostgreSQL', 'make/model/year identities', list(SOURCES)),
    'recalls': ('Official recalls', 'PostgreSQL', 'recall campaigns', ['recalls']),
    'investigations': ('Official investigations', 'PostgreSQL', 'official investigations', ['investigations']),
    'complaints': ('Consumer complaints', 'MongoDB', 'merged complaint documents', ['complaints_2020_2024', 'complaints_2025_2026']),
}
RUN_FIELDS = ('importId', 'dataset', 'startedAt', 'completedAt', 'recordsRead', 'recordsInserted',
              'recordsUpdated', 'recordsSkipped', 'recordsRejected', 'status', 'sourceFingerprint', 'hasError', 'failureCategory')
RUN_COLUMNS = ('import_id,dataset_name,started_at,completed_at,records_read,records_inserted,'
               'records_updated,records_skipped,records_rejected,status,source_fingerprint,has_error,failure_category')


def public_run(row):
    return {key: value.isoformat() if isinstance(value, datetime) else value
            for key, value in zip(RUN_FIELDS, row, strict=True)}


def dataset_summary(connection, database):
    counts = dict(connection.execute('SELECT metric,value FROM admin_reference_counts').fetchall())
    counts['complaints'] = database.complaints.count_documents({}, maxTimeMS=5000)
    latest = {row[1]: public_run(row) for row in connection.execute(
        'SELECT DISTINCT ON (dataset_name) ' + RUN_COLUMNS +
        ' FROM admin_import_runs ORDER BY dataset_name,started_at DESC,import_id DESC').fetchall()}
    items = []
    for key, (title, storage, unit, sources) in DATASETS.items():
        item = {'key': key, 'title': title, 'database': storage, 'recordCount': counts[key], 'unit': unit,
                'sourceArchives': [SOURCES[source][0] for source in sources], 'latestRun': latest.get(key), 'relationships': []}
        if key == 'recalls':
            item['relationships'] = [{'label': 'Vehicle–recall links', 'count': counts['recall_vehicle']},
                                     {'label': 'Imported source rows', 'count': counts['recall_record']}]
        elif key == 'investigations':
            item['relationships'] = [{'label': 'Vehicle–investigation links', 'count': counts['investigation_vehicle']},
                                     {'label': 'Referenced recall links', 'count': counts['investigation_recall']}]
        items.append(item)
    return {'items': items, 'schemaVersion': counts['schema_version'], 'checkedAtUtc': datetime.now(timezone.utc).isoformat(),
            'interpretation': 'Current counts describe the imported snapshot, not a live NHTSA feed. '
                              'Import counters describe individual attempts and must not be summed as current record totals.'}


def import_runs(connection, *, dataset=None, status=None, page=1, page_size=20):
    conditions, values = [], []
    for column, value in [('dataset_name', dataset), ('status', status)]:
        if value is not None:
            conditions.append(column + '=%s'); values.append(value)
    where = ' WHERE ' + ' AND '.join(conditions) if conditions else ''
    total = connection.execute('SELECT count(*) FROM admin_import_runs' + where, values).fetchone()[0]
    rows = connection.execute('SELECT ' + RUN_COLUMNS + ' FROM admin_import_runs' + where +
                              ' ORDER BY started_at DESC,import_id DESC LIMIT %s OFFSET %s',
                              [*values, page_size, (page-1)*page_size]).fetchall()
    return {'items': [public_run(row) for row in rows], 'pagination': {
        'page': page, 'pageSize': page_size, 'total': total, 'totalPages': (total + page_size - 1) // page_size}}
