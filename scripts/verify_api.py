"""Verify real local HTTP requests using the existing databases; no imports/reset."""

import json
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import WSGIRequestHandler, make_server
from backend import create_app
from project_config import ROOT, app_postgres, mongo_client, mongo_database, postgres


class QuietHandler(WSGIRequestHandler):
    def log(self, kind, message, *args):
        pass


def stored_counts():
    tables = ["model_year", "recall", "official_investigation", "app_user", "saved_vehicle",
              "analysis_case", "fleet", "fleet_vehicle", "work_order"]
    with postgres() as connection, mongo_client() as client:
        counts = {name: connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in tables}
        database = mongo_database(client)
        counts["complaints"] = database.complaints.count_documents({})
        counts["case_details"] = database.case_details.count_documents({})
    return counts


def main():
    before = stored_counts()
    app = create_app()
    server = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = []

    def request(path, expected, method="GET"):
        try:
            response = urlopen(Request(base + path, method=method), timeout=15)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, f"{method} {path}: unexpected HTTP status {response.status}"
            assert response.headers.get_content_type() == "application/json"
            result = json.load(response)
        checks.append({"method": method, "path": path, "status": expected})
        return result

    try:
        request("/api", 200)
        health = request("/api/health", 200)
        assert health["databases"] == {"postgresql": "ok", "mongodb": "ok"}
        search = request("/api/vehicles/search?year=2022&make=honda&model=civic&pageSize=1", 200)
        assert search["pagination"]["total"] == 1 and len(search["items"]) == 1
        profile = request("/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC", 200)
        assert profile["modelYearId"] == search["items"][0]["modelYearId"]
        original = json.loads((ROOT / "docs" / "verification_report.json").read_text(encoding="utf-8"))["example_profile"]
        for key in ["officialRecallCampaigns", "officialInvestigations", "consumerComplaints"]:
            assert profile[key] == original[key], "API result differs from the verified imported snapshot"
        request("/api/vehicles/safety-profile?year=invalid&make=HONDA&model=CIVIC", 400)
        request("/api/vehicles/search?pageSize=101", 400)
        request("/api/vehicles/safety-profile?year=2022&make=NO_SUCH_MAKE&model=NONE", 404)
        request("/api/vehicles/search", 405, method="POST")
        with app_postgres() as connection:
            identity, read_only = connection.execute(
                "SELECT current_user,current_setting('default_transaction_read_only')").fetchone()
            can_read_users, can_write_recalls = connection.execute("""SELECT
                has_table_privilege(current_user,'app_user','SELECT'),
                has_table_privilege(current_user,'recall','INSERT,UPDATE,DELETE')""").fetchone()
            assert identity != "postgres" and read_only == "on"
            assert not can_read_users and not can_write_recalls
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions["mongo_client"].close()
    after = stored_counts()
    assert before == after, "API checks unexpectedly changed stored record counts"
    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "sql_reader": {"role": identity, "default_read_only": read_only == "on",
                       "can_read_user_table": can_read_users, "can_write_recalls": can_write_recalls},
        "record_counts_unchanged": before == after,
        "record_counts": after,
        "example_profile": profile,
        "limitations": ["This verifier covers research endpoints; authentication is verified separately by scripts/verify_auth.py.",
                        "Database-unavailable behavior is covered by mocked API tests, not by stopping live services."]}
    (ROOT / "docs" / "api_verification_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
