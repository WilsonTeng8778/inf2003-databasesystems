"""HTTP behavior with fake connections; these tests do not access local databases."""

import unittest
from unittest.mock import Mock

from psycopg import OperationalError
from pymongo.errors import ServerSelectionTimeoutError

from backend import create_app
from backend.services.research import search_vehicles


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.connection = Mock()
        self.connect = Mock(return_value=self.connection)
        self.mongo = Mock()
        self.database = Mock()
        self.mongo.__getitem__ = Mock(return_value=self.database)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "unit-test-only", "PG_CONNECT": self.connect,
                               "MONGO_CLIENT_FACTORY": lambda: self.mongo})
        self.client = self.app.test_client()

    def test_index_links_and_no_database_queries(self):
        response = self.client.get("/api")
        self.assertEqual(response.status_code, 200)
        self.assertIn("safetyProfile", response.json["links"])
        self.connect.assert_not_called()

    def test_health_and_connection_cleanup(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "ok")
        self.connection.close.assert_called_once()

    def test_health_reports_partial_failure_without_secret_details(self):
        self.connect.side_effect = OperationalError("password=DO_NOT_EXPOSE")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["databases"], {"postgresql": "unavailable", "mongodb": "ok"})
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))

    def test_profile_normalization_real_query_shape_and_cleanup(self):
        self.connection.execute.return_value.fetchone.return_value = (42, "HONDA", "CIVIC", 2022, 4, 2)
        self.database.complaints.count_documents.return_value = 885
        self.database.complaints.aggregate.return_value = [{"_id": "STEERING", "count": 732}]
        response = self.client.get("/api/vehicles/safety-profile", query_string={
            "year": 2022, "make": " honda ", "model": " civic "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["consumerComplaints"], 885)
        self.assertEqual(self.connection.execute.call_args.args[1], ("HONDA", "CIVIC", 2022))
        self.database.complaints.count_documents.assert_called_once_with({"modelYearId": 42})
        self.connection.close.assert_called_once()

    def test_unknown_vehicle_does_not_query_complaints(self):
        self.connection.execute.return_value.fetchone.return_value = None
        response = self.client.get("/api/vehicles/safety-profile?year=2022&make=NO_SUCH_MAKE&model=NONE")
        self.assertEqual(response.status_code, 404)
        self.database.complaints.count_documents.assert_not_called()

    def test_invalid_profile_requests_do_not_open_connections(self):
        queries = ["", "year=2022&make=HONDA", "year=oops&make=HONDA&model=CIVIC",
                   "year=9999&make=HONDA&model=CIVIC", "year=2022&make=&model=CIVIC",
                   "year=2022&make=HONDA&model=CIVIC&year=2023",
                   "year=2022&make=HONDA&model=CIVIC&typo=yes",
                   "year=2022&make=HONDA&model=%00", "year=2022&make=" + "A" * 101 + "&model=CIVIC"]
        for query in queries:
            with self.subTest(query=query):
                response = self.client.get("/api/vehicles/safety-profile?" + query)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json)
        self.connect.assert_not_called()

    def test_search_pagination_is_bounded_and_normalized(self):
        self.connection.execute.return_value.fetchone.return_value = (3,)
        self.connection.execute.return_value.fetchall.return_value = [(42, "HONDA", "CIVIC", 2022)]
        response = self.client.get("/api/vehicles/search?make=honda&page=2&pageSize=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["pagination"], {"page": 2, "pageSize": 1, "total": 3, "totalPages": 3})
        self.assertEqual(self.connection.execute.call_args.args[1], ["HONDA", 1, 1])

    def test_invalid_pagination_does_not_query_database(self):
        for query in ["page=0", "page=-1", "page=1.5", "pageSize=101", "pageSize=0", "page=999999999999"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get("/api/vehicles/search?" + query).status_code, 400)
        self.connect.assert_not_called()

    def test_search_values_are_sql_parameters(self):
        self.connection.execute.return_value.fetchone.return_value = (0,)
        self.connection.execute.return_value.fetchall.return_value = []
        malicious = "HONDA' OR 1=1 --"
        result = search_vehicles(self.connection, make=malicious)
        self.assertEqual(result["items"], [])
        for call in self.connection.execute.call_args_list:
            self.assertNotIn(malicious, call.args[0])
            self.assertIn(malicious, call.args[1])

    def test_database_failure_returns_503_without_raw_exception(self):
        self.connect.side_effect = OperationalError("DO_NOT_EXPOSE password and connection settings")
        response = self.client.get("/api/vehicles/search")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json["error"]["code"], "database_unavailable")
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))

    def test_mongo_failure_and_sql_connection_cleanup(self):
        self.connection.execute.return_value.fetchone.return_value = (42, "HONDA", "CIVIC", 2022, 4, 2)
        self.database.complaints.count_documents.side_effect = ServerSelectionTimeoutError("DO_NOT_EXPOSE")
        response = self.client.get("/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))
        self.connection.close.assert_called_once()

    def test_unknown_route_and_write_method_are_json_errors(self):
        self.assertEqual(self.client.get("/api/missing").status_code, 404)
        response = self.client.post("/api/vehicles/search", json={"make": "HONDA"})
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.is_json)
        self.assertIn("GET", response.headers["Allow"])
        self.connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
