"""Read-only live HTTP verification of recall/investigation research and reader grants."""

import json
import sys
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server
from backend import create_app
from backend.services.official_records import conditions_for
from project_config import ROOT, app_postgres, postgres
from scripts.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_auth import snapshot


def counts():
    result = snapshot()
    with postgres() as connection:
        connection.read_only = True
        for name in ("recall_vehicle", "recall_record", "investigation_vehicle", "investigation_manufacturer",
                     "investigation_component", "investigation_recall"):
            result[name] = connection.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
    return result


def main():
    before = counts()
    app = create_app()
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

    def listing(resource, filters=None, expected=200):
        return request(f"/api/{resource}" + ("?" + urlencode(filters) if filters else ""), expected)

    try:
        with postgres(options="-c statement_timeout=10000") as connection:
            connection.read_only = True

            def compare(resource, filters, sql, parameters=()):
                rows = connection.execute(sql, parameters).fetchall()
                result = listing(resource, {**filters, "pageSize": 3})
                key = "campaignNumber" if resource == "recalls" else "investigationNumber"
                assert result["pagination"]["total"] == len(rows)
                assert [item[key] for item in result["items"]] == [row[0] for row in rows[:3]]
                return result

            request("/api/health")
            search = request("/api/vehicles/search?year=2022&make=HONDA&model=CIVIC")
            identity = search["items"][0]["modelYearId"]
            profile = request("/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC")
            recall_sql = """SELECT r.campaign_number,r.report_date FROM recall r
                JOIN recall_vehicle rv USING(recall_id) WHERE rv.model_year_id=%s
                ORDER BY r.report_date DESC NULLS LAST,r.campaign_number"""
            investigation_sql = """SELECT i.investigation_number,i.opened_date FROM official_investigation i
                JOIN investigation_vehicle iv USING(investigation_id) WHERE iv.model_year_id=%s
                ORDER BY i.opened_date DESC NULLS LAST,i.investigation_number"""
            recalls = compare("recalls", {"modelYearId": identity}, recall_sql, (identity,))
            investigations = compare("investigations", {"modelYearId": identity}, investigation_sql, (identity,))
            assert recalls["pagination"]["total"] == profile["officialRecallCampaigns"] == 4
            assert investigations["pagination"]["total"] == profile["officialInvestigations"] == 2
            for resource, previous in [("recalls", recalls), ("investigations", investigations)]:
                assert listing(resource, {"make": " honda ", "model": "civic", "year": 2022, "pageSize": 3}) == previous
            assertions.append("vehicle IDs and normalized labels agree with direct SQL and the safety profile: 4 Civic recalls, 2 investigations")

            recall = request(recalls["items"][0]["detailUrl"])["recall"]
            investigation = request(investigations["items"][0]["detailUrl"])["investigation"]
            recall_path = recalls["items"][0]["detailUrl"]
            investigation_path = investigations["items"][0]["detailUrl"]
            assert request(recall_path.lower())["recall"] == recall
            assert request(investigation_path.lower())["investigation"] == investigation
            official = connection.execute("""SELECT summary,consequence,remedy,report_date,do_not_drive,park_outside
                FROM recall WHERE recall_id=%s""", (recall["recallId"],)).fetchone()
            assert [recall[key] for key in ("summary", "consequence", "remedy", "reportDate", "doNotDrive", "parkOutside")] == [
                value.isoformat() if isinstance(value, date) else value for value in official]
            assert recalls["items"][0]["summaryPreview"] == (recall["summary"][:240] if recall["summary"] is not None else None)
            native_investigation = connection.execute("""SELECT summary,opened_date,closed_date,status
                FROM official_investigation WHERE investigation_id=%s""", (investigation["investigationId"],)).fetchone()
            assert [investigation[key] for key in ("summary", "openedDate", "closedDate", "status")] == [
                value.isoformat() if isinstance(value, date) else value for value in native_investigation]
            assertions.append("details retain full official text, dates and tri-state flags, with case-insensitive external identifiers")

            for item, table, column in [(recall, "recall_vehicle", "recall_id"),
                                         (investigation, "investigation_vehicle", "investigation_id")]:
                parent = item["recallId" if column == "recall_id" else "investigationId"]
                rows = connection.execute(f"""SELECT v.model_year_id,v.make,v.model,v.year FROM {table} x
                    JOIN vehicle_catalogue v USING(model_year_id) WHERE x.{column}=%s
                    ORDER BY v.make,v.model,v.year,v.model_year_id""", (parent,)).fetchall()
                page = request(item["links"]["vehicles"] + "?pageSize=3")
                assert page["pagination"]["total"] == len(rows) == item["affectedVehicleCount"]
                assert [x["modelYearId"] for x in page["items"]] == [row[0] for row in rows[:3]]
                assert request(item["links"]["vehicles"] + "?page=10000")["items"] == []
            assertions.append("affected vehicles are unique, sorted, paginated identities with correct total counts")

            for value in [True, False]:
                for parameter, column in [("doNotDrive", "do_not_drive"), ("parkOutside", "park_outside")]:
                    compare("recalls", {parameter: str(value).lower()}, f"""SELECT campaign_number,report_date FROM recall
                        WHERE {column}=%s ORDER BY report_date DESC NULLS LAST,campaign_number""", (value,))
            for status in ["OPEN", "CLOSED"]:
                compare("investigations", {"status": status.lower()}, """SELECT investigation_number,opened_date
                    FROM official_investigation WHERE status=%s ORDER BY opened_date DESC NULLS LAST,investigation_number""", (status,))
            compare("investigations", {"investigationType": investigation["investigationType"].lower()}, """SELECT investigation_number,opened_date
                FROM official_investigation WHERE investigation_type=%s ORDER BY opened_date DESC NULLS LAST,investigation_number""",
                (investigation["investigationType"],))

            for resource, item, parameter, column, table, key in [
                ("recalls", recall, "report", "report_date", "recall", "campaign_number"),
                ("investigations", investigation, "opened", "opened_date", "official_investigation", "investigation_number")]:
                value = item["reportDate" if resource == "recalls" else "openedDate"]
                assert value is not None
                result = compare(resource, {parameter + "From": value, parameter + "To": value},
                                 f"SELECT {key},{column} FROM {table} WHERE {column}=%s ORDER BY {column} DESC NULLS LAST,{key}", (value,))
                assert result["pagination"]["total"] > 0
            assertions.append("recall flags, official investigation status/type and inclusive report/open-date bounds match direct SQL")

            component = recall["components"][0]
            compare("recalls", {"modelYearId": identity, "component": component, "manufacturer": recall["manufacturer"]},
                    """SELECT DISTINCT r.campaign_number,r.report_date FROM recall r JOIN recall_record rr USING(recall_id)
                        JOIN manufacturer m ON m.manufacturer_id=r.reporting_manufacturer_id
                        WHERE rr.model_year_id=%s AND rr.component=%s AND m.name=%s
                        ORDER BY r.report_date DESC NULLS LAST,r.campaign_number""", (identity, component, recall["manufacturer"]))
            compare("investigations", {"modelYearId": identity, "component": investigation["components"][0],
                                       "manufacturer": investigation["manufacturers"][0]}, """SELECT DISTINCT i.investigation_number,i.opened_date
                FROM official_investigation i JOIN investigation_vehicle iv USING(investigation_id)
                JOIN investigation_component ic USING(investigation_id) JOIN investigation_manufacturer im USING(investigation_id)
                JOIN manufacturer m USING(manufacturer_id) WHERE iv.model_year_id=%s AND ic.component=%s AND m.name=%s
                ORDER BY i.opened_date DESC NULLS LAST,i.investigation_number""",
                (identity, investigation["components"][0], investigation["manufacturers"][0]))
            # Find an actual mixed campaign: this component belongs to another vehicle.
            mixed = connection.execute("""SELECT r.campaign_number,rv.model_year_id,rr.component FROM recall r
                JOIN recall_vehicle rv USING(recall_id)
                JOIN (SELECT DISTINCT recall_id,component FROM recall_record WHERE component<>'') rr USING(recall_id)
                WHERE NOT EXISTS (SELECT 1 FROM recall_record own WHERE own.recall_id=r.recall_id
                    AND own.model_year_id=rv.model_year_id AND own.component=rr.component) LIMIT 1""").fetchone()
            if mixed is not None:
                mismatch = listing("recalls", {"modelYearId": mixed[1], "component": mixed[2], "pageSize": 100})
                assert mixed[0] not in [x["campaignNumber"] for x in mismatch["items"]]
            # This snapshot can repeat all campaign components for every vehicle.
            # Inline SQL VALUES provide an edge case without inserting any records.
            cte = """WITH research_recall(recall_id) AS (VALUES (1)),
                research_recall_vehicle(recall_id,model_year_id) AS (VALUES (1,101),(1,202)),
                research_recall_record(recall_id,model_year_id,component) AS
                (VALUES (1,101,'STEERING'),(1,202,'BRAKES')) SELECT r.recall_id FROM research_recall r"""
            for filters, expected in [({"model_year_id": 101}, [(1,)]), ({"component": "BRAKES"}, [(1,)]),
                                      ({"model_year_id": 101, "component": "BRAKES"}, []),
                                      ({"model_year_id": 101, "component": "STEERING"}, [(1,)])]:
                where, parameters = conditions_for("recall", filters)
                assert connection.execute(cte + where, parameters).fetchall() == expected
            assertions.append("many-to-many filters avoid duplicate parent rows; inline SQL edge cases verify vehicle+component scope without stored fixtures")

            # Verify a large campaign still returns a small, correctly paginated source list.
            big = connection.execute("""SELECT r.campaign_number,count(*) AS n FROM recall_record rr
                JOIN recall r USING(recall_id) GROUP BY r.campaign_number ORDER BY n DESC,r.campaign_number LIMIT 1""").fetchone()
            big_detail = request("/api/recalls/" + big[0])["recall"]
            records1 = request(big_detail["links"]["records"] + "?pageSize=1")
            records2 = request(big_detail["links"]["records"] + "?pageSize=1&page=2")
            assert records1["pagination"]["total"] == big_detail["sourceRecordCount"] == big[1]
            assert len(records1["items"]) == 1 and len(records2["items"]) == 1
            assert records1["items"][0]["sourceRecordId"] != records2["items"][0]["sourceRecordId"]
            native = connection.execute("""SELECT source_archive,source_line,component,model_year_id
                FROM recall_record WHERE source_record_id=%s""", (records1["items"][0]["sourceRecordId"],)).fetchone()
            assert [records1["items"][0][key] for key in ("sourceArchive", "sourceLine", "component", "modelYearId")] == list(native)
            assertions.append("large campaign source rows preserve component/vehicle grain and archive/line provenance with bounded pages")

            external = connection.execute("""SELECT i.investigation_number,ir.campaign_number
                FROM investigation_recall ir JOIN official_investigation i USING(investigation_id)
                LEFT JOIN recall r USING(campaign_number) WHERE r.recall_id IS NULL LIMIT 1""").fetchone()
            assert external is not None
            external_detail = request("/api/investigations/" + external[0])["investigation"]
            link = next(link for link in external_detail["linkedRecalls"] if link["campaignNumber"] == external[1])
            assert not link["inImportedSnapshot"] and link["detailUrl"] is None
            for key, table, column in [("components", "investigation_component", "component"),
                                        ("manufacturers", "research_investigation_manufacturer", "manufacturer")]:
                expected = [row[0] for row in connection.execute(
                    f"SELECT {column} FROM {table} WHERE investigation_id=%s ORDER BY {column}",
                    (investigation["investigationId"],)).fetchall()]
                assert investigation[key] == expected
            assertions.append("investigation components/manufacturers are retained and out-of-snapshot recall references remain visible without a broken detail link")

            for resource, total in [("recalls", before["recall"]), ("investigations", before["official_investigation"])]:
                assert listing(resource, {"pageSize": 1})["pagination"]["total"] == total
                assert listing(resource, {"make": "NO_SUCH_MAKE"})["items"] == []
                for query in [{"pageSize": 101}, {"page": 10001}, {"year": "bad"}, {"unexpected": "yes"}]:
                    listing(resource, query, 400)
                request(f"/api/{resource}?year=2022&year=2023", 400)
            listing("recalls", {"doNotDrive": "null"}, 400)
            listing("recalls", {"reportFrom": "2026-02-30"}, 400)
            listing("investigations", {"status": "PENDING"}, 400)
            listing("investigations", {"openedFrom": "2026-02-01", "openedTo": "2026-01-01"}, 400)
            for resource in ["recalls", "investigations"]:
                request(f"/api/{resource}/bad-number", 400)
                request(f"/api/{resource}/MISSINGRECORD", 404)
                request(f"/api/{resource}/MISSINGRECORD/vehicles", 404)
            request("/api/recalls/MISSINGRECORD/records", 404)
            for path in [recall["links"]["vehicles"], recall["links"]["records"], investigation["links"]["vehicles"]]:
                request(path + "?pageSize=101", 400)
            for method in ["POST", "PATCH", "DELETE"]:
                for path in ["/api/recalls", recall_path, *recall["links"].values(),
                             "/api/investigations", investigation_path, *investigation["links"].values()]:
                    request(path, 405, method=method)
            assertions.append("unfiltered/empty lists, missing parent records, invalid queries and attempts to edit official records behave as documented")

        with app_postgres() as reader:
            role, read_only = reader.execute("SELECT current_user,current_setting('default_transaction_read_only')").fetchone()
            assert role != "postgres" and read_only == "on"
            views = ["research_recall", "research_recall_vehicle", "research_recall_record", "research_investigation",
                     "research_investigation_vehicle", "research_investigation_component",
                     "research_investigation_manufacturer", "research_investigation_recall"]
            for view in views:
                can_read, can_write = reader.execute("""SELECT has_table_privilege(current_user,%s,'SELECT'),
                    has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE')""", (view, view)).fetchone()
                assert can_read and not can_write
            protected = ["app_user", "app_session", "saved_vehicle", "analysis_case", "fleet", "fleet_vehicle", "work_order",
                         "recall", "official_investigation"]
            for table in protected:
                assert not reader.execute("SELECT has_table_privilege(current_user,%s,'SELECT,INSERT,UPDATE,DELETE')", (table,)).fetchone()[0]
            assertions.append("SQL reader has SELECT-only public research views and no direct access to account/workflow or official source tables")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions["mongo_client"].close()
    after = counts()
    assert before == after, "Read-only verification unexpectedly changed stored counts"
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "assertions_passed": assertions, "record_counts_unchanged": True, "record_counts": after,
              "sql_reader": {"role": role, "default_read_only": True, "select_only_research_views": views,
                             "no_direct_access_to_checked_tables": protected},
              "example": {"modelYearId": identity, "make": "HONDA", "model": "CIVIC", "year": 2022,
                          "recalls": 4, "officialInvestigations": 2, "campaignNumber": recall["campaignNumber"],
                          "investigationNumber": investigation["investigationNumber"]},
              "large_campaign": {"campaignNumber": big[0], "sourceRecords": big[1]},
              "limitations": ["No fixture records are inserted. Database outages/null serialization have isolated unit coverage.",
                              "Count and page reads are separate and may change during a concurrent import.",
                              "Investigation components are stored at investigation level, not per affected vehicle.",
                              "Vehicle/component mismatch logic also uses inline SQL VALUES; the current snapshot may lack such a mixed campaign.",
                              "These checks are functional evidence, not index performance benchmarks.",
                              "Analyst-case editing, fleet workflows and browser screens remain later work."]}
    (ROOT / "docs/official_records_verification_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Passed {len(checks)} live HTTP checks; stored counts unchanged; restricted SQL reader verified.")
    print("Evidence: docs/official_records_verification_report.json")


if __name__ == "__main__":
    main()
