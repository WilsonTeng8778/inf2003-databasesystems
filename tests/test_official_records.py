"""Official-record HTTP contracts, parameter boundaries and SQL query behavior."""

import unittest
from datetime import date
from unittest.mock import MagicMock, Mock

from psycopg import OperationalError

from backend import create_app
from backend.services.official_records import RECALL_FIELDS, INVESTIGATION_FIELDS, RECORD_FIELDS


class OfficialRecordTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.connect = Mock(return_value=self.connection)
        self.mongo = MagicMock()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "official-record-tests-only",
                               "DUMMY_PASSWORD_HASH": "unused", "PG_CONNECT": self.connect,
                               "MONGO_CLIENT_FACTORY": lambda: self.mongo})
        self.client = self.app.test_client()
        self.recall = {"recallId": 12, "campaignNumber": "23V123000", "manufacturer": "HONDA",
                       "reportDate": date(2023, 4, 1), "summary": "Campaign summary " * 30,
                       "potentiallyAffected": 1200, "doNotDrive": False, "parkOutside": None,
                       "consequence": "Potential injury", "remedy": "Replace part"}
        self.investigation = {"investigationId": 24, "investigationNumber": "PE23001", "investigationType": "PE",
                              "subject": "Steering", "summary": "Official summary", "openedDate": date(2023, 1, 1),
                              "closedDate": None, "status": "OPEN"}

    def row(self, item, fields):
        return tuple(item[key] for key in fields)

    def list_data(self, kind="recall", total=3):
        item, fields = (self.recall, RECALL_FIELDS) if kind == "recall" else (self.investigation, INVESTIGATION_FIELDS)
        self.connection.execute.return_value.fetchone.return_value = (total,)
        self.connection.execute.return_value.fetchall.return_value = [self.row(item, fields)]

    def test_anonymous_recall_list_is_read_only_and_paginated(self):
        self.list_data()
        response = self.client.get("/api/recalls?pageSize=1&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["pagination"], {"page": 2, "pageSize": 1, "total": 3, "totalPages": 3})
        item = response.json["items"][0]
        self.assertEqual(item["reportDate"], "2023-04-01")
        self.assertIs(item["doNotDrive"], False)
        self.assertIsNone(item["parkOutside"])
        self.assertEqual(len(item["summaryPreview"]), 240)
        self.assertTrue(item["summaryTruncated"])
        self.assertNotIn("summary", item)
        self.assertEqual(item["detailUrl"], "/api/recalls/23V123000")
        self.assertTrue(self.connection.read_only)
        self.connection.close.assert_called_once()
        self.mongo.__getitem__.assert_not_called()

    def test_vehicle_and_component_filters_share_a_single_recall_source_row(self):
        self.list_data()
        response = self.client.get("/api/recalls?make=honda&model=civic&year=2022&component=steering")
        self.assertEqual(response.status_code, 200)
        count, page = self.connection.execute.call_args_list
        self.assertIn("EXISTS (SELECT 1 FROM research_recall_record v", count.args[0])
        self.assertIn("v.year=%s AND v.make=%s AND v.model=%s AND v.component=%s", count.args[0])
        self.assertEqual(count.args[1], [2022, "HONDA", "CIVIC", "STEERING"])
        self.assertEqual(page.args[1][:-2], count.args[1])
        self.assertIn("NULLS LAST,r.campaign_number", page.args[0])

    def test_vehicle_filter_without_component_uses_affected_vehicle_relationship(self):
        self.list_data()
        self.client.get("/api/recalls?modelYearId=42")
        query, values = self.connection.execute.call_args_list[0].args
        self.assertIn("research_recall_vehicle", query)
        self.assertNotIn("research_recall_record", query)
        self.assertEqual(values, [42])

    def test_recall_date_flags_and_manufacturer_parameters(self):
        self.list_data()
        response = self.client.get("/api/recalls?reportFrom=2024-02-29&reportTo=2024-02-29&doNotDrive=false&parkOutside=true&manufacturer=honda")
        self.assertEqual(response.status_code, 200)
        query, values = self.connection.execute.call_args_list[0].args
        self.assertIn("r.do_not_drive=%s", query)
        self.assertIn("r.report_date>=%s AND r.report_date<=%s", query)
        self.assertEqual(values, ["HONDA", False, True, date(2024, 2, 29), date(2024, 2, 29)])

    def test_recall_detail_has_full_text_counts_components_and_links(self):
        fields = {**RECALL_FIELDS, "consequence": "consequence", "remedy": "remedy"}
        self.connection.execute.return_value.fetchone.side_effect = [self.row(self.recall, fields), (727,), (18662,)]
        self.connection.execute.return_value.fetchall.return_value = [("STEERING",), ("SUSPENSION",)]
        response = self.client.get("/api/recalls/23v123000")
        self.assertEqual(response.status_code, 200)
        item = response.json["recall"]
        self.assertEqual(item["summary"], self.recall["summary"])
        self.assertEqual(item["remedy"], "Replace part")
        self.assertEqual(item["affectedVehicleCount"], 727)
        self.assertEqual(item["sourceRecordCount"], 18662)
        self.assertEqual(item["components"], ["STEERING", "SUSPENSION"])
        self.assertEqual(item["links"], {"vehicles": "/api/recalls/23V123000/vehicles", "records": "/api/recalls/23V123000/records"})
        self.assertEqual(self.connection.execute.call_args_list[0].args[1], ("23V123000",))

    def test_recall_vehicles_are_a_bounded_page(self):
        fields = {**RECALL_FIELDS, "consequence": "consequence", "remedy": "remedy"}
        self.connection.execute.return_value.fetchone.side_effect = [self.row(self.recall, fields), (727,)]
        self.connection.execute.return_value.fetchall.return_value = [(42, "HONDA", "CIVIC", 2022)]
        response = self.client.get("/api/recalls/23V123000/vehicles?page=2&pageSize=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"], [{"modelYearId": 42, "make": "HONDA", "model": "CIVIC", "year": 2022}])
        self.assertEqual(response.json["pagination"]["total"], 727)
        query, values = self.connection.execute.call_args.args
        self.assertIn("ORDER BY r.make,r.model,r.year,r.model_year_id LIMIT %s OFFSET %s", query)
        self.assertEqual(values, [12, 1, 1])

    def test_recall_source_records_preserve_grain_and_provenance(self):
        fields = {**RECALL_FIELDS, "consequence": "consequence", "remedy": "remedy"}
        self.connection.execute.return_value.fetchone.side_effect = [self.row(self.recall, fields), (18662,)]
        item = {"sourceRecordId": "0000123", "modelYearId": 42, "make": "HONDA", "model": "CIVIC", "year": 2022,
                "component": "STEERING", "manufacturingStarted": date(2022, 1, 1), "manufacturingEnded": None,
                "sourceArchive": "source.zip", "sourceLine": 55}
        self.connection.execute.return_value.fetchall.return_value = [self.row(item, RECORD_FIELDS)]
        response = self.client.get("/api/recalls/23V123000/records?pageSize=1")
        self.assertEqual(response.status_code, 200)
        result = response.json["items"][0]
        self.assertEqual(result["sourceRecordId"], "0000123")
        self.assertEqual(result["manufacturingStarted"], "2022-01-01")
        self.assertIsNone(result["manufacturingEnded"])
        self.assertEqual(result["sourceLine"], 55)
        self.assertEqual(response.json["pagination"]["total"], 18662)

    def test_investigation_list_preserves_unknown_closing_date(self):
        self.list_data("investigation")
        response = self.client.get("/api/investigations?status=open&investigationType=pe")
        self.assertEqual(response.status_code, 200)
        item = response.json["items"][0]
        self.assertEqual(item["status"], "OPEN")
        self.assertIsNone(item["closedDate"])
        self.assertEqual(item["detailUrl"], "/api/investigations/PE23001")
        self.assertIn("separate from internal analyst cases", response.json["interpretation"])
        self.assertEqual(self.connection.execute.call_args_list[0].args[1], ["OPEN", "PE"])

    def test_investigation_many_to_many_filters_do_not_multiply_parent_rows(self):
        self.list_data("investigation")
        self.client.get("/api/investigations?modelYearId=42&component=steering&manufacturer=honda")
        query, values = self.connection.execute.call_args_list[0].args
        self.assertEqual(query.count("EXISTS"), 3)
        self.assertNotIn(" JOIN ", query)
        self.assertEqual(values, [42, "STEERING", "HONDA"])

    def test_investigation_open_date_bounds(self):
        self.list_data("investigation")
        response = self.client.get("/api/investigations?openedFrom=2023-01-01&openedTo=2023-12-31")
        self.assertEqual(response.status_code, 200)
        query, values = self.connection.execute.call_args_list[0].args
        self.assertIn("r.opened_date>=%s AND r.opened_date<=%s", query)
        self.assertEqual(values, [date(2023, 1, 1), date(2023, 12, 31)])

    def test_investigation_detail_keeps_multiple_manufacturers_and_external_recalls(self):
        self.connection.execute.return_value.fetchone.side_effect = [self.row(self.investigation, INVESTIGATION_FIELDS), (1382,)]
        self.connection.execute.return_value.fetchall.side_effect = [
            [("STEERING",), ("SUSPENSION",)], [("FIRST MANUFACTURER",), ("SECOND MANUFACTURER",)],
            [("09V000000", None), ("23V123000", 12)]]
        response = self.client.get("/api/investigations/pe23001")
        self.assertEqual(response.status_code, 200)
        item = response.json["investigation"]
        self.assertEqual(len(item["manufacturers"]), 2)
        self.assertEqual(item["affectedVehicleCount"], 1382)
        self.assertEqual(item["linkedRecalls"], [
            {"campaignNumber": "09V000000", "inImportedSnapshot": False, "detailUrl": None},
            {"campaignNumber": "23V123000", "inImportedSnapshot": True, "detailUrl": "/api/recalls/23V123000"}])
        self.assertEqual(item["links"]["vehicles"], "/api/investigations/PE23001/vehicles")

    def test_investigation_related_vehicles_use_investigation_identity(self):
        self.connection.execute.return_value.fetchone.side_effect = [self.row(self.investigation, INVESTIGATION_FIELDS), (0,)]
        self.connection.execute.return_value.fetchall.return_value = []
        response = self.client.get("/api/investigations/pe23001/vehicles")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["items"], [])
        self.assertEqual(response.json["investigationNumber"], "PE23001")
        self.assertEqual(self.connection.execute.call_args.args[1], [24, 20, 0])

    def test_empty_official_lists(self):
        self.connection.execute.return_value.fetchone.return_value = (0,)
        self.connection.execute.return_value.fetchall.return_value = []
        for path in ["/api/recalls", "/api/investigations"]:
            with self.subTest(path=path):
                response = self.client.get(path + "?page=2")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json["items"], [])
                self.assertEqual(response.json["pagination"]["totalPages"], 0)

    def test_null_summary_and_report_date_are_preserved(self):
        self.recall["summary"], self.recall["reportDate"] = None, None
        self.list_data()
        item = self.client.get("/api/recalls").json["items"][0]
        self.assertIsNone(item["reportDate"])
        self.assertIsNone(item["summaryPreview"])
        self.assertFalse(item["summaryTruncated"])

    def test_missing_parent_gives_404_for_details_and_related_pages(self):
        self.connection.execute.return_value.fetchone.return_value = None
        for path in ["recalls/UNKNOWN", "recalls/UNKNOWN/vehicles", "recalls/UNKNOWN/records",
                     "investigations/UNKNOWN", "investigations/UNKNOWN/vehicles"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/api/" + path).status_code, 404)
        self.connection.execute.return_value.fetchall.assert_not_called()

    def test_invalid_list_inputs_never_open_connections(self):
        common = ["year=1800", "modelYearId=0", "year=2022&year=2023", "page=10001", "pageSize=101",
                  "page=0", "page=1.2", "make=", "model=%00", "component=" + "x" * 257,
                  "manufacturer=" + "x" * 257, "sort=anything", "filter[$ne]=yes"]
        queries = {"recalls": [*common, "doNotDrive=yes", "parkOutside=0", "reportFrom=2023-02-29",
                               "reportFrom=2023-02-01&reportTo=2023-01-01", "status=OPEN"],
                   "investigations": [*common, "status=PENDING", "investigationType=" + "x" * 21,
                                      "openedTo=2023-1-01", "openedFrom=2023-02-01&openedTo=2023-01-01",
                                      "doNotDrive=true"]}
        for resource, values in queries.items():
            for query in values:
                with self.subTest(resource=resource, query=query):
                    self.assertEqual(self.client.get("/api/" + resource + "?" + query).status_code, 400)
        self.connect.assert_not_called()

    def test_invalid_record_numbers_and_unsupported_detail_queries(self):
        for resource in ["recalls", "investigations"]:
            for value in ["bad-number", "x" * 21, "１２３", "123?unexpected=yes"]:
                with self.subTest(resource=resource, value=value):
                    self.assertEqual(self.client.get(f"/api/{resource}/{value}").status_code, 400)
        self.connect.assert_not_called()

    def test_invalid_related_page_inputs_are_checked_before_connection(self):
        for path in ["recalls/23V123000/vehicles", "recalls/23V123000/records", "investigations/PE23001/vehicles"]:
            for query in ["pageSize=101", "page=10001", "year=2022", "page=1&page=2"]:
                with self.subTest(path=path, query=query):
                    self.assertEqual(self.client.get("/api/" + path + "?" + query).status_code, 400)
        self.connect.assert_not_called()

    def test_injection_like_filter_values_remain_parameters(self):
        value = "HONDA' OR 1=1 --"
        for resource in ["recalls", "investigations"]:
            self.list_data("recall" if resource == "recalls" else "investigation")
            response = self.client.get("/api/" + resource, query_string={"make": value, "manufacturer": value})
            self.assertEqual(response.status_code, 200)
        for call in self.connection.execute.call_args_list:
            self.assertNotIn(value, call.args[0])
            self.assertIn(value, call.args[1])

    def test_connection_and_query_failures_are_sanitized_and_closed(self):
        self.connection.execute.side_effect = OperationalError("DO_NOT_EXPOSE")
        response = self.client.get("/api/recalls")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))
        self.connection.close.assert_called_once()
        self.connect.side_effect = OperationalError("DO_NOT_EXPOSE")
        response = self.client.get("/api/investigations/PE23001")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))

    def test_imported_official_records_reject_write_methods(self):
        for method in ["POST", "PATCH", "DELETE"]:
            for path in ["recalls", "recalls/23V123000", "recalls/23V123000/records", "recalls/23V123000/vehicles",
                         "investigations", "investigations/PE23001", "investigations/PE23001/vehicles"]:
                with self.subTest(method=method, path=path):
                    self.assertEqual(self.client.open("/api/" + path, method=method, json={}).status_code, 405)
        self.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
