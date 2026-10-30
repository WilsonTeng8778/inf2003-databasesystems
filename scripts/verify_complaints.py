"""Verify complaint browsing over real local HTTP using read-only reference queries."""

import json
import sys
import threading
from datetime import datetime, time, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server
from backend import create_app
from project_config import ROOT, mongo_database
from scripts.support.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_auth import snapshot


def main():
    before = snapshot()
    app = create_app()
    database = mongo_database(app.extensions["mongo_client"])
    collection = database.complaints
    server = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    api = LocalApi(f"http://127.0.0.1:{server.server_port}")
    checks, assertions = [], []

    def request(path, expected=200, *, method="GET"):
        try:
            result = api.request(path, method=method)
        except ApiError as error:
            result = {"error": str(error)}
        assert api.last_status == expected, f"{method} {path}: HTTP {api.last_status}, expected {expected}"
        checks.append({"method": method, "path": path, "status": expected})
        return result

    def listing(filters=None, expected=200):
        return request("/api/complaints" + ("?" + urlencode(filters) if filters else ""), expected)

    def check_query(filters, reference):
        result = listing({**filters, "pageSize": 3})
        assert result["pagination"]["total"] == collection.count_documents(reference, maxTimeMS=5000)
        expected_ids = [doc["_id"] for doc in collection.find(
            reference, {"_id": 1}, sort=[("receivedDate", -1), ("_id", -1)], limit=3, max_time_ms=5000)]
        assert [item["odiNumber"] for item in result["items"]] == expected_ids
        return result

    try:
        request("/api/health")
        catalogue = request("/api/vehicles/search?year=2022&make=HONDA&model=CIVIC")
        identifier = catalogue["items"][0]["modelYearId"]
        base_filter = {"modelYearId": identifier}
        by_vehicle = check_query(base_filter, base_filter)
        assert by_vehicle["pagination"]["total"] == 885
        profile = request("/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC")
        assert by_vehicle["pagination"]["total"] == profile["consumerComplaints"]
        named = listing({"year": 2022, "make": " honda ", "model": "civic", "pageSize": 3})
        assert named == by_vehicle
        assertions.append("SQL catalogue identity, safety-profile count and MongoDB vehicle-label filters agree: 885 Civic complaints")

        first = by_vehicle["items"][0]
        sample = collection.find_one({"_id": first["odiNumber"]})
        detail = request("/api/complaints/" + first["odiNumber"])["complaint"]
        assert detail["narrative"] == sample["narrative"]
        assert first["narrativePreview"] == sample["narrative"][:240]
        assert first["narrativeTruncated"] == (len(sample["narrative"]) > 240)
        assert detail["source"]["componentRowCount"] == sample["source"]["componentRowCount"]
        assert "_id" not in detail and "source" not in first and "narrative" not in first
        assert detail["receivedDate"] == sample["receivedDate"].date().isoformat()
        assertions.append("list previews and full narrative/provenance details agree with the stored document")

        page2 = listing({**base_filter, "pageSize": 3, "page": 2})
        page1_ids = {item["odiNumber"] for item in by_vehicle["items"]}
        assert page1_ids.isdisjoint(item["odiNumber"] for item in page2["items"])
        assert by_vehicle == listing({**base_filter, "pageSize": 3})
        assert listing({**base_filter, "page": 10000})["items"] == []
        assertions.append("stable ordering, disjoint consecutive pages, repeat reads and empty out-of-range pages")

        for parameter, field in [("crash", "incident.crash"), ("fire", "incident.fire")]:
            for value in [True, False]:
                check_query({**base_filter, parameter: str(value).lower()}, {**base_filter, field: value})
        for parameter, field in [("hasInjuries", "incident.injuries"), ("hasFatalities", "incident.fatalities")]:
            for value in [True, False]:
                check_query({**base_filter, parameter: str(value).lower()},
                            {**base_filter, field: {"$gt": 0} if value else 0})
        assertions.append("positive/negative crash/fire and injury/fatality filters match MongoDB, with nulls excluded from false/zero")

        component = sample["components"][0]
        check_query({**base_filter, "component": component.lower()}, {**base_filter, "components": component})
        received = sample["receivedDate"].date()
        bounds = {"$gte": datetime.combine(received, time.min, timezone.utc),
                  "$lte": datetime.combine(received, time(23, 59, 59, 999000), timezone.utc)}
        on_day = check_query({**base_filter, "receivedFrom": received.isoformat(), "receivedTo": received.isoformat()},
                             {**base_filter, "receivedDate": bounds})
        assert on_day["pagination"]["total"] > 0
        check_query({**base_filter, "component": component, "crash": "false", "hasInjuries": "false",
                     "receivedFrom": "2020-01-01", "receivedTo": "2026-12-31"},
                    {**base_filter, "components": component, "incident.crash": False, "incident.injuries": 0,
                     "receivedDate": {"$gte": datetime(2020, 1, 1, tzinfo=timezone.utc),
                                      "$lte": datetime(2026, 12, 31, 23, 59, 59, 999000, tzinfo=timezone.utc)}})
        assertions.append("array membership, inclusive receipt-date bounds and combined nested filters match stored records")

        for terms in ["steering", '"steering wheel" -brake']:
            result = check_query({**base_filter, "q": terms}, {**base_filter, "$text": {"$search": terms}})
            if terms == "steering":
                assert result["pagination"]["total"] > 0
        assertions.append("narrative text search, quoted phrase and exclusion syntax execute through the existing text index")

        all_complaints = listing({"pageSize": 1})
        assert all_complaints["pagination"]["total"] == before["complaints"]
        assert len(all_complaints["items"]) == 1
        assert listing({"make": "NO_SUCH_MAKE"})["items"] == []
        request("/api/complaints/99999999999999999999", 404)
        for filters in [{"crash": "yes"}, {"hasInjuries": "null"}, {"pageSize": 101}, {"page": 10001},
                        {"receivedFrom": "2026-02-30"}, {"receivedFrom": "2026-02-01", "receivedTo": "2026-01-01"},
                        {"q": ""}, {"filter[$ne]": "anything"}]:
            listing(filters, 400)
        request("/api/complaints?year=2022&year=2023", 400)
        request("/api/complaints/invalid", 400)
        request("/api/complaints/123?unexpected=yes", 400)
        for method in ["POST", "PATCH", "DELETE"]:
            request("/api/complaints", 405, method=method)
            request("/api/complaints/" + first["odiNumber"], 405, method=method)
        assertions.append("unfiltered reads, missing results, invalid inputs and attempts to edit imported complaints are handled")
        indexes = collection.index_information()
        assert {"vehicle_received", "vehicle_components", "narrative_text"}.issubset(indexes)
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions["mongo_client"].close()
    after = snapshot()
    assert before == after, "Read-only checks unexpectedly changed stored record counts"
    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
        "assertions_passed": assertions, "record_counts_unchanged": True, "record_counts": after,
        "example": {"modelYearId": identifier, "make": "HONDA", "model": "CIVIC", "year": 2022,
                    "consumerComplaints": by_vehicle["pagination"]["total"], "sampleOdiNumber": first["odiNumber"]},
        "existing_indexes_checked": ["vehicle_received", "vehicle_components", "narrative_text"],
        "limitations": ["No fixture records are inserted; null serialization and database outages also have isolated unit coverage.",
                        "Counts and pages are separate reads; a concurrent data refresh can change their results.",
                        "Index existence and working queries do not establish a before/after performance benchmark.",
                        "The visual complaint explorer and analyst-case editing are later work."],
    }
    (ROOT / "docs/complaints_verification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(checks)} live HTTP checks; record counts unchanged.")
    print("Evidence: docs/complaints_verification_report.json")


if __name__ == "__main__":
    main()
