"""Merge component rows into one MongoDB document per ODI complaint.

SQLite is temporary ETL staging only (Python's standard library), never an
application database. It bounds memory when grouping non-adjacent component rows.
"""

import json
import sqlite3
import tempfile
from contextlib import closing
from datetime import datetime, time, timezone
from itertools import groupby
from pathlib import Path

from pymongo import ReplaceOne

from etl.common import eligible_rows, import_run, vehicle_ids
from etl.source import ROOT, SOURCES, date_value, flag, integer, normalized, source_sha256, vehicle_key


def bson_date(raw):
    value = date_value(raw)
    return datetime.combine(value, time(), tzinfo=timezone.utc) if value else None


def merge_complaint(rows, identities):
    """Rows are (source, fields); reject an ODI reused for different vehicles.

    Incident totals are not summed across repeated component rows. Conflicting
    scalar values are flagged; retain the first row in deterministic source order.
    """
    source, first = rows[0]
    key = vehicle_key(first, source)
    odi = first[1].strip()
    if any(row[1].strip() != odi or vehicle_key(row, src) != key for src, row in rows):
        raise ValueError(f"Conflicting vehicle identities for ODI {odi}; refusing an ambiguous merge")
    components = sorted({normalized(row[11]) for _, row in rows if normalized(row[11])})
    scalar_columns = (6, 7, 8, 9, 10, 16, 17, 18, 19)
    conflicts = [index + 1 for index in scalar_columns if len({row[index].strip() for _, row in rows}) > 1]
    return {
        "_id": odi, "odiNumber": odi, "modelYearId": identities[key],
        "vehicle": {"make": key[0], "model": key[1], "year": key[2]},
        "manufacturer": normalized(first[2]), "components": components,
        "incident": {"crash": flag(first[6]), "fire": flag(first[8]),
                     "injuries": integer(first[9]), "fatalities": integer(first[10])},
        "mileage": integer(first[17]), "occurrences": integer(first[18]),
        "receivedDate": bson_date(first[16]), "incidentDate": bson_date(first[7]),
        "narrative": first[19].strip(),
        "source": {"archives": sorted({SOURCES[src][0] for src, _ in rows}),
                   "rowIds": sorted({row[0].strip() for _, row in rows}),
                   "componentRowCount": len(rows), "conflictingScalarColumns": conflicts},
    }


def import_complaints(connection, database):
    identities = vehicle_ids(connection)
    connection.commit()
    source_names = [name for name in SOURCES if name.startswith("complaints")]
    # Group both receipt windows in one pass: an ODI's components must never be
    # overwritten by processing one component row as a whole document.
    digest = ":".join(source_sha256(name) for name in source_names)
    staging_root = (ROOT / "data" / "staging").resolve()
    if not staging_root.is_relative_to(ROOT.resolve()):
        raise ValueError("ETL staging must remain inside the project workspace")
    staging_root.mkdir(parents=True, exist_ok=True)
    with import_run(connection, "complaints", digest, external_writes=True) as counts:
        with tempfile.TemporaryDirectory(prefix="complaints-", dir=staging_root) as directory:
            if not Path(directory).resolve().is_relative_to(staging_root):
                raise ValueError("Unexpected temporary staging location")
            with closing(sqlite3.connect(Path(directory) / "grouping.sqlite")) as staging:
                staging.execute("CREATE TABLE rows (odi TEXT NOT NULL, source TEXT NOT NULL, fields TEXT NOT NULL)")
                for source in source_names:
                    def records():
                        for _, row, _ in eligible_rows(source, counts):
                            if not row[1].strip().isdigit():
                                counts.rejected += 1
                                continue
                            # Only selected non-contact fields enter temporary staging.
                            safe = [""] * 51
                            for index in [0,1,2,3,4,5,6,7,8,9,10,11,16,17,18,19,45]:
                                safe[index] = row[index]
                            yield row[1].strip(), source, json.dumps(safe, ensure_ascii=False)
                    staging.executemany("INSERT INTO rows VALUES (?,?,?)", records())
                    staging.commit()
                staging.execute("CREATE INDEX idx_rows_odi ON rows(odi)")
                cursor = staging.execute("SELECT odi,source,fields FROM rows ORDER BY odi,rowid")
                operations = []
                for odi, group in groupby(cursor, key=lambda value: value[0]):
                    records_for_odi = [(src, json.loads(fields)) for _, src, fields in group]
                    document = merge_complaint(records_for_odi, identities)
                    operations.append(ReplaceOne({"_id": odi}, document, upsert=True))
                    if len(operations) >= 1000:
                        result = database.complaints.bulk_write(operations, ordered=False)
                        counts.inserted += result.upserted_count
                        counts.updated += result.matched_count
                        operations.clear()
                        completed = counts.inserted + counts.updated
                        if completed % 25000 == 0:
                            print(f"Complaints: {completed:,} documents processed", flush=True)
                if operations:
                    result = database.complaints.bulk_write(operations, ordered=False)
                    counts.inserted += result.upserted_count
                    counts.updated += result.matched_count
    # MongoDB writes are batched, not part of the SQL transaction. A failed run
    # may leave valid partial batches; rerun safely completes the same stable IDs.

