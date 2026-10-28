"""Verify imported data, SQL constraints/trigger, and CRUD with reversible demo data."""

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation
from pymongo.errors import DuplicateKeyError, WriteError
from project_config import ROOT, mongo_client, mongo_database, postgres
from scripts.safety_profile import safety_profile


def expect_sql_error(connection, error_type, statement, parameters):
    try:
        with connection.transaction():  # Savepoint; leaves surrounding verification usable.
            connection.execute(statement, parameters)
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def verify_crud(connection, database):
    evidence = []
    case_id = None
    try:
        vehicle, recall = connection.execute(
            """SELECT rv.model_year_id,rv.recall_id FROM recall_vehicle rv
               JOIN vehicle_catalogue v USING(model_year_id)
               WHERE v.make='HONDA' AND v.model='CIVIC' AND v.year=2022 LIMIT 1""").fetchone()
        user = connection.execute("""INSERT INTO app_user(email,password_hash,role)
            VALUES (%s,'VERIFICATION_ONLY_NOT_A_LOGIN','ANALYST') RETURNING user_id""",
            (f"verification-{uuid.uuid4().hex}@example.invalid",)).fetchone()[0]
        saved = connection.execute("""INSERT INTO saved_vehicle(user_id,model_year_id,nickname)
            VALUES (%s,%s,'demo') RETURNING saved_vehicle_id""", (user, vehicle)).fetchone()[0]
        connection.execute("UPDATE saved_vehicle SET nickname='renamed' WHERE saved_vehicle_id=%s", (saved,))
        assert connection.execute("SELECT nickname FROM saved_vehicle WHERE saved_vehicle_id=%s", (saved,)).fetchone()[0] == "renamed"
        expect_sql_error(connection, UniqueViolation,
                         "INSERT INTO saved_vehicle(user_id,model_year_id) VALUES (%s,%s)", (user, vehicle))
        connection.execute("DELETE FROM saved_vehicle WHERE saved_vehicle_id=%s", (saved,))
        evidence.append("saved_vehicle CRUD and duplicate constraint")

        case_id = connection.execute("""INSERT INTO analysis_case(title,model_year_id,created_by,assigned_to)
            VALUES ('Verification case',%s,%s,%s) RETURNING case_id""", (vehicle, user, user)).fetchone()[0]
        connection.execute("UPDATE analysis_case SET status='REVIEWING',priority='HIGH' WHERE case_id=%s", (case_id,))
        assert connection.execute("SELECT count(*) FROM case_status_history WHERE case_id=%s", (case_id,)).fetchone()[0] == 1
        expect_sql_error(connection, CheckViolation,
                         "UPDATE analysis_case SET status='CLOSED' WHERE case_id=%s", (case_id,))
        connection.execute("UPDATE analysis_case SET status='CLOSED',closed_at=now() WHERE case_id=%s", (case_id,))
        evidence.append("analysis_case workflow, closure constraint and status-history trigger")

        fleet = connection.execute("INSERT INTO fleet(owner_id,name) VALUES (%s,'Verification fleet') RETURNING fleet_id", (user,)).fetchone()[0]
        connection.execute("UPDATE fleet SET name='Renamed fleet' WHERE fleet_id=%s", (fleet,))
        fleet_vehicle = connection.execute("""INSERT INTO fleet_vehicle(fleet_id,model_year_id,label)
            VALUES (%s,%s,'Demo vehicle') RETURNING fleet_vehicle_id""", (fleet, vehicle)).fetchone()[0]
        connection.execute("UPDATE fleet_vehicle SET label='Renamed vehicle' WHERE fleet_vehicle_id=%s", (fleet_vehicle,))
        order = connection.execute("""INSERT INTO work_order(fleet_vehicle_id,model_year_id,recall_id)
            VALUES (%s,%s,%s) RETURNING work_order_id""", (fleet_vehicle, vehicle, recall)).fetchone()[0]
        connection.execute("UPDATE work_order SET status='IN_PROGRESS' WHERE work_order_id=%s", (order,))
        assert connection.execute("SELECT status FROM work_order WHERE work_order_id=%s", (order,)).fetchone()[0] == "IN_PROGRESS"
        mismatch = connection.execute("""SELECT recall_id FROM recall r WHERE NOT EXISTS
            (SELECT 1 FROM recall_vehicle rv WHERE rv.recall_id=r.recall_id AND rv.model_year_id=%s) LIMIT 1""", (vehicle,)).fetchone()[0]
        expect_sql_error(connection, ForeignKeyViolation,
                         "INSERT INTO work_order(fleet_vehicle_id,model_year_id,recall_id) VALUES (%s,%s,%s)",
                         (fleet_vehicle, vehicle, mismatch))
        connection.execute("DELETE FROM fleet WHERE fleet_id=%s", (fleet,))
        assert connection.execute("SELECT 1 FROM work_order WHERE work_order_id=%s", (order,)).fetchone() is None
        evidence.append("fleet/fleet_vehicle/work_order CRUD, recall-applicability FK and cascade")

        document = {"caseId": case_id, "linkedComplaints": [], "suspectedComponents": [],
                    "findings": [], "notes": [], "tags": []}
        database.case_details.insert_one(document)
        now = datetime.now(timezone.utc)
        complaint = database.complaints.find_one({"modelYearId": vehicle}, {"_id": 1})
        assert complaint is not None
        database.case_details.update_one({"caseId": case_id}, {"$addToSet": {
            "linkedComplaints": complaint["_id"], "tags": "verification"}})
        database.case_details.update_one({"caseId": case_id}, {"$push": {
            "findings": {"findingId": "F1", "authorId": user, "createdAt": now, "observation": "demo"},
            "notes": {"noteId": "N1", "authorId": user, "createdAt": now, "text": "demo"}}})
        database.case_details.update_one({"caseId": case_id, "findings.findingId": "F1"},
                                         {"$set": {"findings.$.observation": "edited"}})
        database.case_details.update_one({"caseId": case_id, "notes.noteId": "N1"},
                                         {"$set": {"notes.$.text": "edited"}})
        loaded = database.case_details.find_one({"caseId": case_id})
        assert loaded["findings"][0]["observation"] == "edited" and loaded["notes"][0]["text"] == "edited"
        database.case_details.update_one({"caseId": case_id}, {"$pull": {
            "linkedComplaints": complaint["_id"], "tags": "verification",
            "findings": {"findingId": "F1"}, "notes": {"noteId": "N1"}}})
        try:
            database.case_details.insert_one({key: value for key, value in document.items() if key != "_id"})
        except DuplicateKeyError:
            pass
        else:
            raise AssertionError("caseId unique index did not reject duplicate")
        try:
            database.case_details.insert_one({"caseId": -1})
        except WriteError:
            pass
        else:
            database.case_details.delete_one({"caseId": -1})
            raise AssertionError("MongoDB validator did not reject invalid case document")
        evidence.append("MongoDB document/nested CRUD, unique caseId and schema validation")
        database.case_details.delete_one({"caseId": case_id})
        connection.execute("DELETE FROM analysis_case WHERE case_id=%s", (case_id,))
        assert connection.execute("SELECT count(*) FROM case_status_history WHERE case_id=%s", (case_id,)).fetchone()[0] == 0
        return evidence
    finally:
        if case_id is not None:
            database.case_details.delete_one({"caseId": case_id})
        connection.rollback()  # All SQL verification records are temporary.


def main():
    with postgres() as connection, mongo_client() as client:
        database = mongo_database(client)
        tables = ["model_year", "recall", "recall_vehicle", "recall_record", "official_investigation",
                  "investigation_vehicle", "investigation_manufacturer"]
        counts = {name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in tables}
        counts["complaints"] = database.complaints.count_documents({})
        assert all(value > 0 for value in counts.values()), "Run imports first"
        source_profile = json.loads((ROOT / "docs" / "data_profile.json").read_text(encoding="utf-8"))
        sources = source_profile["sources"]
        expected = {
            "model_year": source_profile["catalogue"]["distinct_vehicles"],
            "recall": sources["recalls"]["distinct_identifiers"],
            "recall_record": sources["recalls"]["eligible_vehicle_rows"],
            "official_investigation": sources["investigations"]["distinct_identifiers"],
            "complaints": sum(value["distinct_identifiers"] for name, value in sources.items()
                              if name.startswith("complaints")),
        }
        for name, value in expected.items():
            assert counts[name] == value, f"Imported {name} count differs from inspected source scope"
        sql_ids = {row[0] for row in connection.execute("SELECT model_year_id FROM model_year")}
        mongo_ids = set(database.complaints.distinct("modelYearId"))
        assert not mongo_ids - sql_ids, "Complaint documents contain unknown SQL modelYearIds"
        conflicts = database.complaints.count_documents({"source.conflictingScalarColumns.0": {"$exists": True}})
        profile = safety_profile(connection, database, "HONDA", "CIVIC", 2022)
        assert profile is not None and profile["consumerComplaints"] > 0
        connection.rollback()
        checks = verify_crud(connection, database)
        latest_imports = [{"dataset": name, "rows_read": read, "inserted": inserted,
                           "refreshed": refreshed, "skipped": skipped, "rejected": rejected}
                          for name, read, inserted, refreshed, skipped, rejected in connection.execute("""
            SELECT DISTINCT ON (dataset_name) dataset_name,records_read,records_inserted,
                records_updated,records_skipped,records_rejected FROM data_import_log
            WHERE status='COMPLETED' ORDER BY dataset_name,import_id DESC
        """)]
        report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(),
                  "postgres_version": connection.execute("SHOW server_version").fetchone()[0],
                  "mongodb_version": client.server_info()["version"], "counts": counts,
                  "checks_passed": ["imported counts match inspected source scope",
                                    "cross-database vehicle references", "complaint scalar conflict audit", *checks],
                  "data_quality": {"complaints_with_conflicting_scalar_rows": conflicts},
                  "latest_successful_imports": latest_imports,
                  "idempotent_rerun_verified": len(latest_imports) == 4 and all(run["inserted"] == 0 for run in latest_imports),
                  "example_profile": profile,
                  "limitations": ["Database-only verification; no API/GUI or user-role enforcement yet.",
                                   "Index performance benchmarks are not yet implemented."]}
    target = ROOT / "docs" / "verification_report.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
