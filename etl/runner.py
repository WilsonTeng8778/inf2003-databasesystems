"""One import pipeline and session lock shared by setup and admin entry points."""

from contextlib import contextmanager
from psycopg import sql

from etl.catalogue import import_catalogue
from etl.import_recalls import import_recalls
from etl.import_investigations import import_investigations
from etl.import_complaints import import_complaints

IMPORT_LOCK = 2003192026
IMPORTED_TABLES = ('manufacturer', 'vehicle_make', 'vehicle_model', 'model_year',
                   'manufacturer_make', 'vehicle_source', 'recall', 'recall_vehicle',
                   'recall_record', 'official_investigation', 'investigation_vehicle',
                   'investigation_manufacturer', 'investigation_component', 'investigation_recall')


class ImportBusy(RuntimeError):
    pass


@contextmanager
def import_lock(connection):
    acquired = connection.execute('SELECT pg_try_advisory_lock(%s)', (IMPORT_LOCK,)).fetchone()[0]
    connection.commit()
    if not acquired:
        raise ImportBusy('Another project import is running; wait for it to finish.')
    try:
        yield
    finally:
        # Restore a failed SQL transaction before releasing the session lock.
        # Closing a lost connection releases its session locks automatically.
        if not connection.closed:
            connection.rollback()
            connection.execute('SELECT pg_advisory_unlock(%s)', (IMPORT_LOCK,))
            connection.commit()


def run_imports(connection, database):
    import_catalogue(connection)
    import_recalls(connection)
    import_investigations(connection)
    import_complaints(connection, database)
    # Resolve the same tables as the import queries. Do not analyze unrelated
    # workflow tables or public data when verifying an isolated schema.
    for table in IMPORTED_TABLES:
        connection.execute(sql.SQL('ANALYZE {}').format(sql.Identifier(table)))
    connection.commit()
