"""Exercise synthetic workflows against public data in local *_test DBs only."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from dotenv import load_dotenv
from pymongo.uri_parser import parse_uri

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))
test_env = os.getenv("VEHICLE_TEST_ENV_FILE")
if not test_env or not Path(test_env).is_file():
    raise RuntimeError("Set VEHICLE_TEST_ENV_FILE to a dedicated local test configuration")
load_dotenv(test_env, override=True, interpolate=False)
mongo_uri = os.getenv("MONGODB_URI", "")
parsed = parse_uri(mongo_uri)
if (os.getenv("POSTGRES_HOST") not in {"127.0.0.1", "localhost", "::1"} or
        not os.getenv("POSTGRES_DB", "").endswith("_test") or
        not os.getenv("MONGODB_DB", "").endswith("_test") or
        any(host not in {"127.0.0.1", "localhost", "::1"} for host, _ in parsed["nodelist"])):
    raise RuntimeError("Verification requires local PostgreSQL and MongoDB databases ending in _test")
from backend import create_app
from project_config import mongo_client, mongo_database, postgres

with postgres() as connection, mongo_client() as mongo:
    database = mongo_database(mongo)
    def counts():
        sql = {table: connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
               for table in ("app_user", "analysis_case", "fleet", "fleet_vehicle", "work_order")}
        sql["case_details"] = database.case_details.count_documents({})
        return sql
    before = counts()
    app = create_app({"TESTING": True})
    client = app.test_client()
    user_id = case_id = fleet_id = None
    checks = {}
    try:
        token = client.get("/api/auth/csrf").get_json()["csrfToken"]
        response = client.post("/api/auth/register", json={"email": f"real-source-test-{uuid4().hex}@example.test",
            "password": "Synthetic Verification Password 2026!"}, headers={"X-CSRF-Token": token})
        if response.status_code != 201:
            raise RuntimeError(f"Synthetic registration failed ({response.status_code})")
        user_id, token = response.get_json()["user"]["userId"], response.get_json()["csrfToken"]
        connection.execute("UPDATE app_user SET role='ANALYST' WHERE user_id=%s", (user_id,))
        connection.commit()
        headers = {"X-CSRF-Token": token}
        search = client.get("/api/vehicles/search?year=2022&make=HONDA&model=CIVIC").get_json()
        vehicle = search["items"][0]["modelYearId"]
        complaints = client.get(f"/api/vehicles/{vehicle}/complaints?pageSize=1").get_json()["items"]
        recalls = client.get(f"/api/vehicles/{vehicle}/recalls?pageSize=1").get_json()["items"]
        if not complaints or not recalls:
            raise RuntimeError("Example vehicle has no complaint or recall in this snapshot")
        response = client.post("/api/cases", json={"modelYearId": vehicle, "title": "Synthetic real-source verification"}, headers=headers)
        if response.is_json and response.get_json().get("case"):
            case_id = response.get_json()["case"]["caseId"]
        if response.status_code != 201:
            raise RuntimeError(f"Case creation failed ({response.status_code})")
        response = client.put(f"/api/cases/{case_id}/links", json={"complaintIds": [complaints[0]["odiNumber"]]}, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Complaint link failed ({response.status_code})")
        response = client.post(f"/api/cases/{case_id}/findings", json={"observation": "Synthetic verification finding."}, headers=headers)
        if response.status_code != 201:
            raise RuntimeError(f"Finding creation failed ({response.status_code})")
        linked = client.get(f"/api/cases/{case_id}/complaints").get_json()["items"]
        if len(linked) != 1 or linked[0]["odiNumber"] != complaints[0]["odiNumber"]:
            raise RuntimeError("Linked public complaint did not round-trip")
        checks["caseLinkedRealComplaint"] = True
        response = client.post("/api/fleets", json={"name": "Synthetic verification fleet"}, headers=headers)
        if response.status_code != 201:
            raise RuntimeError(f"Fleet creation failed ({response.status_code})")
        fleet_id = response.get_json()["fleet"]["fleetId"]
        response = client.post(f"/api/fleets/{fleet_id}/vehicles", json={"modelYearId": vehicle, "label": "Synthetic vehicle"}, headers=headers)
        if response.status_code != 201:
            raise RuntimeError(f"Fleet vehicle creation failed ({response.status_code})")
        fleet_vehicle = response.get_json()["fleetVehicleId"]
        response = client.post(f"/api/fleets/{fleet_id}/work-orders", json={"fleetVehicleId": fleet_vehicle, "recallId": recalls[0]["recallId"]}, headers=headers)
        if response.status_code != 201:
            raise RuntimeError(f"Recall work order failed ({response.status_code})")
        checks["fleetWorkOrderForRealRecall"] = True
    finally:
        # Remove only the exact synthetic records created by this verification.
        connection.rollback()
        if case_id is not None:
            database.case_details.delete_one({"caseId": case_id})
            connection.execute("DELETE FROM analysis_case WHERE case_id=%s AND created_by=%s", (case_id, user_id))
            connection.execute("DELETE FROM case_sync_outbox WHERE case_id=%s", (case_id,))
        if fleet_id is not None:
            connection.execute("DELETE FROM fleet WHERE fleet_id=%s AND owner_id=%s", (fleet_id, user_id))
        if user_id is not None:
            connection.execute("DELETE FROM app_user WHERE user_id=%s", (user_id,))
        connection.commit()
        app.extensions["mongo_client"].close()
    after = counts()
    connection.commit()
    if before != after:
        raise RuntimeError("Synthetic workflow cleanup did not restore the baseline counts")
    result = {"verifiedAtUtc": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "syntheticWorkflowRecordsRemoved": True, "workflowCountsBefore": before,
              "workflowCountsAfter": after,
              "scope": "Synthetic user, case and fleet linked to real public source records in an isolated test database."}
    output = repo / "verification" / "results"
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"real-workflow-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2)
    print(f"Real-source workflow and targeted cleanup verified: {target.relative_to(repo)}")
