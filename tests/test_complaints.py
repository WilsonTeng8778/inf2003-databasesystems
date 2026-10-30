"""Complaint API validation, output boundaries and failure behavior without databases."""

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock

from pymongo.errors import ExecutionTimeout, ServerSelectionTimeoutError

from backend import create_app


class ComplaintTests(unittest.TestCase):
    def setUp(self):
        self.sql = Mock()
        self.mongo, self.database = MagicMock(), Mock()
        self.mongo.__getitem__.return_value = self.database
        self.collection = self.database.complaints
        self.collection.count_documents.return_value = 3
        self.document = {
            "_id": "00123456", "odiNumber": "00123456", "modelYearId": 42,
            "vehicle": {"make": "HONDA", "model": "CIVIC", "year": 2022},
            "components": ["STEERING", "SUSPENSION"],
            "incident": {"crash": False, "fire": None, "injuries": 0, "fatalities": None},
            "receivedDate": datetime(2026, 10, 27, tzinfo=timezone.utc), "incidentDate": None,
            "narrative": "Steering sticks. " * 30, "mileage": 1500, "occurrences": 2,
            "manufacturer": "HONDA", "source": {"archives": ["source.zip"], "rowIds": ["1", "2"],
                "componentRowCount": 2, "conflictingScalarColumns": []},
        }
        self.cursor = MagicMock()
        self.cursor.__enter__.return_value = self.cursor
        self.cursor.__iter__.return_value = [self.document]
        self.collection.find.return_value = self.cursor
        self.collection.find_one.return_value = self.document
        app = create_app({"TESTING": True, "SECRET_KEY": "complaint-tests-only",
                          "DUMMY_PASSWORD_HASH": "not-used", "PG_CONNECT": self.sql,
                          "AUTH_PG_CONNECT": self.sql, "MONGO_CLIENT_FACTORY": lambda: self.mongo})
        self.client = app.test_client()

    def test_anonymous_list_preserves_flags_and_nulls_without_sql(self):
        response = self.client.get("/api/complaints")
        self.assertEqual(response.status_code, 200)
        item = response.json["items"][0]
        self.assertEqual(item["odiNumber"], "00123456")
        self.assertEqual(item["incident"], {"crash": False, "fire": None, "injuries": 0, "fatalities": None})
        self.assertEqual(item["receivedDate"], "2026-10-27")
        self.assertIsNone(item["incidentDate"])
        self.assertIn("allegations", response.json["interpretation"])
        self.sql.assert_not_called()

    def test_list_preview_is_bounded_and_excludes_detail_fields(self):
        item = self.client.get("/api/complaints").json["items"][0]
        self.assertEqual(len(item["narrativePreview"]), 240)
        self.assertTrue(item["narrativeTruncated"])
        self.assertTrue({"_id", "source", "narrative", "manufacturer", "mileage"}.isdisjoint(item))

    def test_detail_retains_full_narrative_and_source_provenance(self):
        self.document["privateExtra"] = "DO_NOT_EXPOSE"
        self.document["source"]["contact"] = "DO_NOT_EXPOSE"
        self.document["vehicle"]["contact"] = "DO_NOT_EXPOSE"
        response = self.client.get("/api/complaints/00123456")
        self.assertEqual(response.status_code, 200)
        item = response.json["complaint"]
        self.assertEqual(item["narrative"], self.document["narrative"])
        self.assertEqual(item["source"]["componentRowCount"], 2)
        self.assertEqual(item["components"], ["STEERING", "SUSPENSION"])
        self.assertNotIn("narrativePreview", item)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))
        self.assertEqual(self.collection.find_one.call_args.args[0], {"_id": "00123456"})
        self.sql.assert_not_called()

    def test_vehicle_and_array_filters_are_exact_and_normalized(self):
        response = self.client.get("/api/complaints", query_string={
            "modelYearId": 42, "year": 2022, "make": " honda ", "model": "civic", "component": " steering "})
        self.assertEqual(response.status_code, 200)
        query = self.collection.find.call_args.args[0]
        self.assertEqual(query, {"modelYearId": 42, "vehicle.year": 2022,
                                "vehicle.make": "HONDA", "vehicle.model": "CIVIC", "components": "STEERING"})

    def test_true_and_false_flags_and_count_filters(self):
        self.assertEqual(self.client.get("/api/complaints?crash=false&fire=TRUE&hasInjuries=true&hasFatalities=false").status_code, 200)
        query = self.collection.find.call_args.args[0]
        self.assertIs(query["incident.crash"], False)
        self.assertIs(query["incident.fire"], True)
        self.assertEqual(query["incident.injuries"], {"$gt": 0})
        self.assertEqual(query["incident.fatalities"], 0)
        self.client.get("/api/complaints?hasInjuries=false&hasFatalities=true")
        query = self.collection.find.call_args.args[0]
        self.assertEqual(query["incident.injuries"], 0)
        self.assertEqual(query["incident.fatalities"], {"$gt": 0})

    def test_receipt_date_bounds_include_both_calendar_days(self):
        response = self.client.get("/api/complaints?receivedFrom=2024-02-29&receivedTo=2024-02-29")
        self.assertEqual(response.status_code, 200)
        bounds = self.collection.find.call_args.args[0]["receivedDate"]
        self.assertEqual(bounds["$gte"], datetime(2024, 2, 29, tzinfo=timezone.utc))
        self.assertEqual(bounds["$lte"], datetime(2024, 2, 29, 23, 59, 59, 999000, tzinfo=timezone.utc))

    def test_one_sided_dates_and_last_representable_day(self):
        for query, operator in [("receivedFrom=2026-01-01", "$gte"), ("receivedTo=9999-12-31", "$lte")]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/complaints?" + query).status_code, 200)
                self.assertEqual(set(self.collection.find.call_args.args[0]["receivedDate"]), {operator})

    def test_text_search_preserves_phrase_and_negation_syntax(self):
        terms = '"steering wheel" -brake'
        response = self.client.get("/api/complaints", query_string={"q": terms})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.collection.find.call_args.args[0], {"$text": {"$search": terms}})

    def test_mongo_operators_and_regex_are_not_accepted_as_filter_structure(self):
        literal = '{"$ne":null}.*'
        self.assertEqual(self.client.get("/api/complaints", query_string={"make": literal}).status_code, 200)
        self.assertEqual(self.collection.find.call_args.args[0], {"vehicle.make": literal.upper()})

    def test_pagination_uses_same_filter_and_stable_order_with_time_limits(self):
        response = self.client.get("/api/complaints?year=2022&page=2&pageSize=1")
        self.assertEqual(response.json["pagination"], {"page": 2, "pageSize": 1, "total": 3, "totalPages": 3})
        self.assertEqual(self.collection.count_documents.call_args.args[0], self.collection.find.call_args.args[0])
        self.assertEqual(self.collection.count_documents.call_args.kwargs["maxTimeMS"], 5000)
        options = self.collection.find.call_args.kwargs
        self.assertEqual(options["sort"], [("receivedDate", -1), ("_id", -1)])
        self.assertEqual((options["skip"], options["limit"], options["max_time_ms"]), (1, 1, 5000))
        self.cursor.__exit__.assert_called_once()

    def test_unknown_filters_and_invalid_values_do_not_query_databases(self):
        queries = ["year=2022&year=2023", "filter[$ne]=x", "sort=whatever", "modelYearId=0", "year=1800",
                   "page=0", "page=10001", "page=1.5", "pageSize=101", "pageSize=0", "crash=0", "fire=",
                   "hasInjuries=yes", "hasFatalities=null", "make=", "model=%00", "component=" + "x" * 257,
                   "receivedFrom=2026-02-30", "receivedTo=20261027", "receivedTo=2026-1-01",
                   "receivedFrom=2026-02-01&receivedTo=2026-01-31", "q=", "q=%00", "q=" + "x" * 201]
        for query in queries:
            with self.subTest(query=query):
                response = self.client.get("/api/complaints?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.is_json)
        self.collection.count_documents.assert_not_called()
        self.collection.find.assert_not_called()
        self.sql.assert_not_called()

    def test_detail_invalid_ids_and_query_fields_do_not_query_mongo(self):
        for path in ["abc", "-1", "1.5", "123?unexpected=x", "1" * 21, "１２３"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get("/api/complaints/" + path).status_code, 400)
        self.collection.find_one.assert_not_called()

    def test_empty_results_and_out_of_range_page(self):
        self.collection.count_documents.return_value = 0
        self.cursor.__iter__.return_value = []
        result = self.client.get("/api/complaints?page=2").json
        self.assertEqual(result["items"], [])
        self.assertEqual(result["pagination"], {"page": 2, "pageSize": 20, "total": 0, "totalPages": 0})

    def test_missing_complaint_returns_404(self):
        self.collection.find_one.return_value = None
        response = self.client.get("/api/complaints/99999999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json["error"]["code"], "not_found")

    def test_null_dates_and_empty_narrative_serialize(self):
        self.document["receivedDate"], self.document["narrative"] = None, ""
        item = self.client.get("/api/complaints").json["items"][0]
        self.assertIsNone(item["receivedDate"])
        self.assertEqual(item["narrativePreview"], "")
        self.assertFalse(item["narrativeTruncated"])

    def test_database_unavailable_and_timeouts_have_sanitized_errors(self):
        self.collection.count_documents.side_effect = ServerSelectionTimeoutError("DO_NOT_EXPOSE")
        response = self.client.get("/api/complaints")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))
        self.collection.count_documents.side_effect = None
        self.collection.find_one.side_effect = ExecutionTimeout("DO_NOT_EXPOSE")
        response = self.client.get("/api/complaints/00123456")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))

    def test_cursor_failure_is_sanitized_and_cursor_is_closed(self):
        self.cursor.__iter__.side_effect = ExecutionTimeout("DO_NOT_EXPOSE")
        response = self.client.get("/api/complaints")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))
        self.cursor.__exit__.assert_called_once()

    def test_write_methods_are_rejected(self):
        for method in ["POST", "PATCH", "DELETE"]:
            for path in ["/api/complaints", "/api/complaints/00123456"]:
                with self.subTest(method=method, path=path):
                    response = self.client.open(path, method=method, json={"narrative": "overwrite"})
                    self.assertEqual(response.status_code, 405)
        self.collection.find_one.assert_not_called()
        self.collection.find.assert_not_called()


if __name__ == "__main__":
    unittest.main()
