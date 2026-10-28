"""Capture read-only evidence for the imported dataset and research endpoints."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import create_app
from etl.source import RAW, SOURCES, normalized, source_sha256
from project_config import ROOT, app_postgres, mongo_client, mongo_database, workflow_postgres


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2022)
    parser.add_argument("--make", default="HONDA")
    parser.add_argument("--model", default="CIVIC")
    args = parser.parse_args()
    if not 1900 <= args.year <= 2100 or not args.make.strip() or not args.model.strip():
        parser.error("Provide a valid model year, make and model")
    with app_postgres() as reader, workflow_postgres() as workflow, mongo_client() as client:
        database = mongo_database(client)
        counts = {
            "vehicleIdentities": reader.execute("SELECT count(*) FROM vehicle_catalogue").fetchone()[0],
            "recallCampaigns": reader.execute("SELECT count(DISTINCT recall_id) FROM vehicle_recall_details").fetchone()[0],
            "recallVehicleLinks": reader.execute("SELECT count(*) FROM vehicle_recall_details").fetchone()[0],
            "officialInvestigations": reader.execute("SELECT count(DISTINCT investigation_id) FROM vehicle_investigation_details").fetchone()[0],
            "complaintDocuments": database.complaints.count_documents({}),
        }
        row = reader.execute("SELECT model_year_id FROM vehicle_catalogue WHERE year=%s AND make=%s AND model=%s",
                             (args.year, normalized(args.make), normalized(args.model))).fetchone()
        if row is None:
            raise RuntimeError("The selected example vehicle is not in this imported catalogue")
        vehicle_id = row[0]
        independent = {
            "recalls": reader.execute("SELECT count(*) FROM vehicle_recall_details WHERE model_year_id=%s", (vehicle_id,)).fetchone()[0],
            "investigations": reader.execute("SELECT count(*) FROM vehicle_investigation_details WHERE model_year_id=%s", (vehicle_id,)).fetchone()[0],
            "complaints": database.complaints.count_documents({"modelYearId": vehicle_id}),
        }
        rows = workflow.execute("""SELECT DISTINCT ON (dataset_name) dataset_name,completed_at,source_sha256,
            records_read,records_inserted,records_updated,records_skipped,records_rejected
            FROM data_import_log WHERE status='COMPLETED' ORDER BY dataset_name,completed_at DESC,import_id DESC""").fetchall()
        imports = [{"dataset": row[0], "completedAt": row[1].isoformat(), "sourceSha256": row[2],
                    "read": row[3], "inserted": row[4], "updated": row[5], "skipped": row[6], "rejected": row[7]} for row in rows]
        hashes = {key: source_sha256(key) for key, (filename, _) in SOURCES.items() if (RAW / filename).is_file()}
        expected = {"recalls": hashes.get("recalls"), "investigations": hashes.get("investigations"),
                    "complaints": ":".join(hashes[key] for key in ("complaints_2020_2024", "complaints_2025_2026"))
                    if all(key in hashes for key in ("complaints_2020_2024", "complaints_2025_2026")) else None}
        provenance = {item["dataset"]: expected[item["dataset"]] == item["sourceSha256"]
                      for item in imports if item["dataset"] in expected and expected[item["dataset"]] is not None}
        app = create_app({"TESTING": True})
        try:
            browser = app.test_client()
            query = {"year": args.year, "make": args.make, "model": args.model}
            endpoints = {"health": browser.get("/api/health"), "profile": browser.get("/api/vehicles/safety-profile", query_string=query),
                         "recalls": browser.get(f"/api/vehicles/{vehicle_id}/recalls?pageSize=5"),
                         "investigations": browser.get(f"/api/vehicles/{vehicle_id}/investigations?pageSize=5"),
                         "complaints": browser.get(f"/api/vehicles/{vehicle_id}/complaints?pageSize=5"),
                         "insights": browser.get(f"/api/vehicles/{vehicle_id}/insights")}
            statuses = {name: response.status_code for name, response in endpoints.items()}
            if any(status != 200 for status in statuses.values()):
                raise RuntimeError(f"Research endpoint check failed: {statuses}")
            profile, insight = endpoints["profile"].get_json(), endpoints["insights"].get_json()
            if (profile["officialRecallCampaigns"] != independent["recalls"] or
                    profile["officialInvestigations"] != independent["investigations"] or
                    profile["consumerComplaints"] != independent["complaints"] or
                    insight["totalComplaints"] != independent["complaints"]):
                raise RuntimeError("API counts do not match independent database counts")
            for kind in ("recalls", "investigations", "complaints"):
                if endpoints[kind].get_json()["pagination"]["total"] != independent[kind]:
                    raise RuntimeError(f"{kind} list total differs from the database")
        finally:
            app.extensions["mongo_client"].close()
        report = {"verifiedAtUtc": datetime.now(timezone.utc).isoformat(),
                  "environment": {"postgresql": reader.execute("SELECT version()").fetchone()[0],
                                  "mongodb": client.server_info()["version"]},
                  "counts": counts, "latestCompletedImports": imports, "localArchiveHashes": hashes,
                  "importHashesMatchLocalArchives": provenance, "apiStatuses": statuses,
                  "example": {"year": args.year, "make": normalized(args.make), "model": normalized(args.model),
                              "modelYearId": vehicle_id, "independentCounts": independent},
                  "limitations": ["Read-only research checks; case and fleet writes were checked separately with synthetic data.",
                                  "Counts describe this imported snapshot, not live NHTSA data or a VIN-specific determination."]}
    output = ROOT / "verification" / "results"
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"real-data-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(f"Read-only evidence saved to {path.relative_to(ROOT)}")
    print(f"Vehicle identities: {counts['vehicleIdentities']:,}; recalls: {counts['recallCampaigns']:,}; "
          f"investigations: {counts['officialInvestigations']:,}; complaints: {counts['complaintDocuments']:,}")
    print(f"Example profile counts: {independent}; archive hashes matched: {provenance}")


if __name__ == "__main__":
    main()
