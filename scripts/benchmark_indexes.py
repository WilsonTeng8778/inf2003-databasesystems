"""Compare identical queries before/after indexing on isolated sampled copies.

BENCH_POSTGRES_DB and BENCH_MONGODB_DB must name separate existing databases
ending in _benchmark. Source tables/collections and indexes are never modified.
"""
import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from project_config import ROOT, app_postgres, mongo_client, mongo_database, postgres


def distribution(samples):
    values = sorted(samples)
    return {"samplesMs": [round(value, 3) for value in values],
            "medianMs": round(statistics.median(values), 3),
            "p95Ms": round(values[math.ceil(len(values) * .95) - 1], 3)}


def timed(operation, repeats):
    operation()  # One warm-up before each phase.
    samples, count = [], None
    for _ in range(repeats):
        start = time.perf_counter()
        result = operation()
        samples.append((time.perf_counter() - start) * 1000)
        count = len(result)
    return {**distribution(samples), "rowsReturned": count}


def postgres_phase(connection, model_year_id, repeats):
    query = "SELECT recall_id,report_date FROM benchmark_recalls WHERE model_year_id=%s ORDER BY recall_id"
    params = (model_year_id,)
    timings = timed(lambda: connection.execute(query, params).fetchall(), repeats)
    timings["plan"] = connection.execute("EXPLAIN (ANALYZE,BUFFERS,FORMAT JSON) " + query, params).fetchone()[0]
    return timings


def mongo_phase(database, name, model_year_id, repeats):
    collection = database[name]
    query = {"modelYearId": model_year_id}
    projection = {"_id": 1, "receivedDate": 1}
    order = [("receivedDate", -1), ("_id", 1)]
    timings = timed(lambda: list(collection.find(query, projection).sort(order)), repeats)
    plan = database.command({"explain": {"find": name, "filter": query,
        "projection": projection, "sort": {"receivedDate": -1, "_id": 1}}, "verbosity": "executionStats"})
    # MongoDB includes a machine hostname in serverInfo; the version is recorded
    # separately and the hostname is not needed for report evidence.
    plan.pop("serverInfo", None)
    timings["plan"] = plan
    return timings


def run(max_records, repeats):
    pg_target = os.getenv("BENCH_POSTGRES_DB", "")
    mongo_target = os.getenv("BENCH_MONGODB_DB", "")
    pg_source = os.getenv("POSTGRES_DB", "vehicle_safety")
    mongo_source = os.getenv("MONGODB_DB", "vehicle_safety")
    if (not pg_target.endswith("_benchmark") or not mongo_target.endswith("_benchmark") or
            pg_target == pg_source or mongo_target == mongo_source):
        raise ValueError("Set separate BENCH_POSTGRES_DB and BENCH_MONGODB_DB names ending in _benchmark")
    scratch = "benchmark_" + uuid4().hex
    with app_postgres() as source_pg, postgres(pg_target) as target_pg, mongo_client() as client:
        source_mongo, target_mongo = mongo_database(client), client[mongo_target]
        if scratch in target_mongo.list_collection_names():
            raise RuntimeError("Generated scratch collection already exists")
        target_mongo.create_collection(scratch)
        try:
            target_pg.execute("CREATE TEMP TABLE benchmark_recalls(model_year_id bigint,recall_id bigint,report_date date)")
            rows = source_pg.execute("""SELECT model_year_id,recall_id,report_date FROM vehicle_recall_details
                ORDER BY model_year_id,recall_id LIMIT %s""", (max_records,)).fetchall()
            if not rows:
                raise ValueError("No recall records in the source database")
            with target_pg.cursor().copy("COPY benchmark_recalls (model_year_id,recall_id,report_date) FROM STDIN") as copy:
                for row in rows:
                    copy.write_row(row)
            target_pg.execute("ANALYZE benchmark_recalls")
            pg_id = Counter(row[0] for row in rows).most_common(1)[0][0]

            counts, batch, copied = Counter(), [], 0
            for item in source_mongo.complaints.find({}, {"_id": 1, "modelYearId": 1, "receivedDate": 1}).sort("_id", 1).limit(max_records):
                if "modelYearId" not in item:
                    continue
                counts[item["modelYearId"]] += 1
                batch.append(item)
                if len(batch) == 1000:
                    target_mongo[scratch].insert_many(batch, ordered=False); copied += len(batch); batch = []
            if batch:
                target_mongo[scratch].insert_many(batch, ordered=False); copied += len(batch)
            if not counts:
                raise ValueError("No complaint documents in the source database")
            mongo_id = counts.most_common(1)[0][0]
            before_pg = postgres_phase(target_pg, pg_id, repeats)
            target_pg.execute("CREATE INDEX benchmark_recalls_model_id ON benchmark_recalls(model_year_id,recall_id)")
            target_pg.execute("ANALYZE benchmark_recalls")
            after_pg = postgres_phase(target_pg, pg_id, repeats)
            before_mongo = mongo_phase(target_mongo, scratch, mongo_id, repeats)
            target_mongo[scratch].create_index([("modelYearId", 1), ("receivedDate", -1), ("_id", 1)], name="benchmark_vehicle_date")
            after_mongo = mongo_phase(target_mongo, scratch, mongo_id, repeats)
            if before_pg["rowsReturned"] != after_pg["rowsReturned"] or before_mongo["rowsReturned"] != after_mongo["rowsReturned"]:
                raise RuntimeError("Before/after queries returned different row counts")
            snapshots = source_pg.execute("SELECT dataset_name,completed_at,records_read FROM dataset_snapshot ORDER BY dataset_name").fetchall()
            return {"measuredAtUtc": datetime.now(timezone.utc).isoformat(), "sampleLimit": max_records,
                    "repeats": repeats, "warmupsPerPhase": 1,
                    "interpretation": "Compare before/after within each database; the SQL and MongoDB workloads differ.",
                    "sampling": "First records in model-year/recall order for SQL and ODI identifier order for MongoDB; samples are not random.",
                    "environment": {"platform": platform.platform(), "python": platform.python_version(),
                                    "postgresql": target_pg.execute("SELECT version()").fetchone()[0],
                                    "mongodb": client.server_info()["version"]},
                    "sourceImports": [{"dataset": name, "completedAt": when.isoformat(), "recordsRead": count}
                                      for name, when, count in snapshots],
                    "postgresql": {"sourceRowsCopied": len(rows), "modelYearId": pg_id,
                        "query": "recall_id, report_date filtered by model_year_id, ordered by recall_id",
                        "index": "(model_year_id, recall_id)", "before": before_pg, "after": after_pg},
                    "mongodb": {"sourceDocumentsCopied": copied, "modelYearId": mongo_id,
                        "query": "complaint identifiers and receipt dates filtered by modelYearId, ordered by date and ID",
                        "index": "(modelYearId, receivedDate DESC, _id ASC)", "before": before_mongo, "after": after_mongo}}
        finally:
            # This exact random collection was created above in the separate benchmark DB.
            target_mongo.drop_collection(scratch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-records", type=int, default=50000)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.max_records <= 1000000 or not 3 <= args.repeats <= 20:
        parser.error("max-records must be 1..1000000 and repeats must be 3..20")
    result = run(args.max_records, args.repeats)
    output = ROOT / "benchmarks" / "results"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"index-benchmark-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Measured results and raw plans saved to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
