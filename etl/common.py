"""Shared validation, temporary COPY staging and durable import audit logs."""

from contextlib import contextmanager
from dataclasses import dataclass

from psycopg import sql

from etl.source import SOURCES, iter_rows, vehicle_key


@dataclass
class Counts:
    read: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: int = 0


def eligible_rows(source, counts):
    for line, row in iter_rows(source):
        counts.read += 1
        if len(row) != SOURCES[source][1]:
            counts.rejected += 1
            continue
        key = vehicle_key(row, source)
        if key is None:
            counts.skipped += 1
            continue
        yield line, row, key


def stage(connection, name, definitions, records):
    connection.execute(sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(
        sql.Identifier(name), sql.SQL(definitions)))
    with connection.cursor() as cursor:
        with cursor.copy(sql.SQL("COPY {} FROM STDIN").format(sql.Identifier(name))) as copy:
            for record in records:
                copy.write_row(record)


@contextmanager
def import_run(connection, name, digest=None, *, external_writes=False):
    import_id = connection.execute(
        "INSERT INTO data_import_log (dataset_name,source_sha256) VALUES (%s,%s) RETURNING import_id",
        (name, digest),
    ).fetchone()[0]
    connection.commit()
    counts = Counts()
    print(f"Importing {name}...", flush=True)
    try:
        yield counts
        connection.execute("""
            UPDATE data_import_log SET completed_at=now(), status='COMPLETED',
                records_read=%s, records_inserted=%s, records_updated=%s,
                records_skipped=%s, records_rejected=%s WHERE import_id=%s
        """, (counts.read, counts.inserted, counts.updated, counts.skipped, counts.rejected, import_id))
        connection.commit()
    except Exception as error:
        connection.rollback()
        if not external_writes:
            # The failed SQL stage was rolled back; predicted upsert counts are
            # not committed inserts/updates. MongoDB batches are independent.
            counts.inserted = counts.updated = 0
        # Exception type is safe to log; do not persist credentials or source row contents.
        connection.execute("""
            UPDATE data_import_log SET completed_at=now(), status='FAILED',
                records_read=%s, records_inserted=%s, records_updated=%s,
                records_skipped=%s, records_rejected=%s,
                error_summary=%s WHERE import_id=%s
        """, (counts.read, counts.inserted, counts.updated, counts.skipped, counts.rejected,
                type(error).__name__, import_id))
        connection.commit()
        raise
    print(f"{name}: {counts.read:,} rows read; {counts.inserted:,} entities inserted; "
          f"{counts.updated:,} existing entities refreshed; {counts.skipped:,} out of scope; "
          f"{counts.rejected:,} rejected", flush=True)


def vehicle_ids(connection):
    return {(make, model, year): identifier for identifier, make, model, year in
            connection.execute("SELECT model_year_id,make,model,year FROM vehicle_catalogue")}

