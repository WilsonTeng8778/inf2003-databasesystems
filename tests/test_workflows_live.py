"""Opt-in integration checks against explicitly configured local *_test databases.

Set VEHICLE_TEST_ENV_FILE to an env file with the normal project settings and
preconfigured restricted roles. Only uniquely identified synthetic records are
created and removed. No database is dropped or emptied.
"""
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.uri_parser import parse_uri

ENV_FILE = os.getenv("VEHICLE_TEST_ENV_FILE")


@unittest.skipUnless(ENV_FILE, "Set VEHICLE_TEST_ENV_FILE for isolated live database checks")
class LiveWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv(Path(ENV_FILE), override=True, interpolate=False)
        host = os.getenv("POSTGRES_HOST")
        mongo_uri = os.getenv("MONGODB_URI", "")
        parsed = parse_uri(mongo_uri)
        if (host not in {"127.0.0.1", "localhost", "::1"} or
                not os.getenv("POSTGRES_DB", "").endswith("_test") or
                not os.getenv("MONGODB_DB", "").endswith("_test") or
                any(hostname not in {"127.0.0.1", "localhost", "::1"} for hostname, _ in parsed["nodelist"])):
            raise RuntimeError("Live checks require local PostgreSQL and MongoDB databases ending in _test")
        from project_config import postgres
        from backend import create_app
        cls.connection = postgres()
        cls.mongo_client = MongoClient(mongo_uri, tz_aware=True, serverSelectionTimeoutMS=3000)
        cls.database = cls.mongo_client[os.environ["MONGODB_DB"]]
        cls.created_users, cls.created_cases, cls.complaint_ids = [], [], []
        cls.make_id = cls.model_id = cls.recall_id = cls.other_recall_id = cls.investigation_id = None
        cls.year_ids = []
        cls.addClassCleanup(cls.cleanup)
        suffix = uuid4().hex[:12].upper()
        conn = cls.connection
        cls.make_id = conn.execute("INSERT INTO vehicle_make(name) VALUES (%s) RETURNING make_id", ("SYNTHETIC_"+suffix,)).fetchone()[0]
        cls.model_id = conn.execute("INSERT INTO vehicle_model(make_id,name) VALUES (%s,%s) RETURNING model_id", (cls.make_id, "TEST_MODEL")).fetchone()[0]
        for year in (2022, 2023):
            cls.year_ids.append(conn.execute("INSERT INTO model_year(model_id,year) VALUES (%s,%s) RETURNING model_year_id", (cls.model_id, year)).fetchone()[0])
        cls.recall_id = conn.execute("""INSERT INTO recall(campaign_number,report_date,summary)
            VALUES (%s,'2024-01-05','Synthetic recall for verification') RETURNING recall_id""", ("T"+suffix,)).fetchone()[0]
        cls.other_recall_id = conn.execute("""INSERT INTO recall(campaign_number,summary)
            VALUES (%s,'Synthetic other vehicle recall') RETURNING recall_id""", ("U"+suffix,)).fetchone()[0]
        conn.execute("INSERT INTO recall_vehicle(recall_id,model_year_id) VALUES (%s,%s),(%s,%s)",
                     (cls.recall_id, cls.year_ids[0], cls.other_recall_id, cls.year_ids[1]))
        cls.investigation_id = conn.execute("""INSERT INTO official_investigation(investigation_number,investigation_type,subject,opened_date)
            VALUES (%s,'TEST','Synthetic investigation','2024-02-01') RETURNING investigation_id""", ("I"+suffix,)).fetchone()[0]
        conn.execute("INSERT INTO investigation_vehicle(investigation_id,model_year_id) VALUES (%s,%s)", (cls.investigation_id, cls.year_ids[0]))
        conn.commit()
        base = int(uuid4().hex[:12], 16) + 10**14
        candidate_ids = [str(base), str(base + 1), str(base + 2)]
        for index, complaint_id in enumerate(candidate_ids):
            cls.database.complaints.insert_one({"_id": complaint_id, "odiNumber": complaint_id,
                "modelYearId": cls.year_ids[0 if index < 2 else 1],
                "vehicle": {"make": "SYNTHETIC_"+suffix, "model": "TEST_MODEL", "year": 2022 if index < 2 else 2023},
                "components": ["STEERING"] if index != 1 else ["BRAKES"],
                "incident": {"crash": False, "fire": False, "injuries": 0, "fatalities": 0},
                "receivedDate": datetime(2024, 3 + index, 1, tzinfo=timezone.utc), "incidentDate": None,
                "narrative": "Synthetic steering observation" if index == 0 else "Synthetic brake observation",
                "source": {"archives": ["synthetic-test"], "rowIds": [complaint_id]}})
            cls.complaint_ids.append(complaint_id)
        cls.app = create_app({"TESTING": True})
        cls.first, cls.second = cls.app.test_client(), cls.app.test_client()
        cls.tokens = {}
        for index, client in enumerate((cls.first, cls.second)):
            csrf = client.get("/api/auth/csrf").get_json()["csrfToken"]
            response = client.post("/api/auth/register", json={"email": f"synthetic-{suffix}-{index}@example.test",
                "password": "Synthetic Test Password 2026!"}, headers={"X-CSRF-Token": csrf})
            if response.status_code != 201:
                raise AssertionError(f"Synthetic registration failed: {response.status_code} {response.get_json()}")
            data = response.get_json()
            cls.created_users.append(data["user"]["userId"])
            cls.tokens[client] = data["csrfToken"]
        conn.execute("UPDATE app_user SET role='ANALYST' WHERE user_id=%s", (cls.created_users[0],))
        conn.commit()

    @classmethod
    def cleanup(cls):
        try:
            cls.connection.rollback()
            if cls.created_users:
                rows = cls.connection.execute("SELECT case_id FROM analysis_case WHERE created_by=ANY(%s)", (cls.created_users,)).fetchall()
                ids = list(set(cls.created_cases + [row[0] for row in rows]))
                if ids:
                    cls.database.case_details.delete_many({"caseId": {"$in": ids}})
                    cls.connection.execute("DELETE FROM analysis_case WHERE case_id=ANY(%s)", (ids,))
                    cls.connection.execute("DELETE FROM case_sync_outbox WHERE case_id=ANY(%s)", (ids,))
                cls.connection.execute("DELETE FROM app_user WHERE user_id=ANY(%s)", (cls.created_users,))
            if cls.investigation_id:
                cls.connection.execute("DELETE FROM investigation_vehicle WHERE investigation_id=%s", (cls.investigation_id,))
                cls.connection.execute("DELETE FROM official_investigation WHERE investigation_id=%s", (cls.investigation_id,))
            recall_ids = [value for value in (cls.recall_id, cls.other_recall_id) if value]
            if recall_ids:
                cls.connection.execute("DELETE FROM recall_vehicle WHERE recall_id=ANY(%s)", (recall_ids,))
                cls.connection.execute("DELETE FROM recall WHERE recall_id=ANY(%s)", (recall_ids,))
            if cls.year_ids:
                cls.connection.execute("DELETE FROM model_year WHERE model_year_id=ANY(%s)", (cls.year_ids,))
            if cls.model_id:
                cls.connection.execute("DELETE FROM vehicle_model WHERE model_id=%s", (cls.model_id,))
            if cls.make_id:
                cls.connection.execute("DELETE FROM vehicle_make WHERE make_id=%s", (cls.make_id,))
            cls.connection.commit()
            if cls.complaint_ids:
                cls.database.complaints.delete_many({"_id": {"$in": cls.complaint_ids}})
        finally:
            if hasattr(cls, "app"):
                cls.app.extensions["mongo_client"].close()
            cls.connection.close()
            cls.mongo_client.close()

    def write(self, client, method, path, body=None):
        return client.open(path, method=method, json=body if body is not None else {},
                           headers={"X-CSRF-Token": self.tokens[client]})

    def test_evidence_cases_fleets_and_outbox_recovery(self):
        first, second, vehicle = self.first, self.second, self.year_ids[0]
        self.assertEqual(first.get("/app").status_code, 200)
        static_response = first.get("/static/app.js")
        self.assertEqual(static_response.status_code, 200)
        static_response.close()
        self.assertEqual(first.get(f"/api/vehicles/{vehicle}/recalls").get_json()["pagination"]["total"], 1)
        self.assertEqual(first.get(f"/api/vehicles/{vehicle}/investigations").get_json()["pagination"]["total"], 1)
        complaints = first.get(f"/api/vehicles/{vehicle}/complaints?component=steering&fromDate=2024-03-01&toDate=2024-03-31")
        self.assertEqual(complaints.status_code, 200, complaints.get_json())
        self.assertEqual([item["odiNumber"] for item in complaints.get_json()["items"]], [self.complaint_ids[0]])
        self.assertEqual(first.get(f"/api/vehicles/{vehicle}/complaints?q=steering").get_json()["pagination"]["total"], 1)
        self.assertEqual(first.get(f"/api/vehicles/{vehicle}/insights").get_json()["totalComplaints"], 2)
        self.assertEqual(first.get(f"/api/vehicles/{vehicle}/complaints?fromDate=bad").status_code, 400)
        self.assertEqual(first.get("/api/datasets").status_code, 200)
        self.assertEqual(first.post("/api/cases", json={"modelYearId": vehicle, "title": "No CSRF"}).status_code, 403)
        self.assertEqual(second.get("/api/cases").status_code, 403)

        class BrokenCollection:
            def update_one(self, *args, **kwargs):
                raise ServerSelectionTimeoutError("simulated temporary outage")
            def delete_one(self, *args, **kwargs):
                raise ServerSelectionTimeoutError("simulated temporary outage")
        class BrokenDatabase:
            case_details = BrokenCollection()
        class BrokenClient:
            def __getitem__(self, key):
                return BrokenDatabase()
        real_client = self.app.extensions["mongo_client"]
        self.app.extensions["mongo_client"] = BrokenClient()
        try:
            response = self.write(first, "POST", "/api/cases", {"modelYearId": vehicle, "title": "Synthetic case"})
        finally:
            self.app.extensions["mongo_client"] = real_client
        self.assertEqual(response.status_code, 202, response.get_json())
        case_id = response.get_json()["case"]["caseId"]
        self.created_cases.append(case_id)
        self.assertIsNone(self.database.case_details.find_one({"caseId": case_id}))
        synced = self.write(first, "POST", f"/api/cases/{case_id}/sync")
        self.assertEqual(synced.get_json()["sync"]["pending"], 0)
        self.assertEqual(self.write(first, "PUT", f"/api/cases/{case_id}/links", {"complaintIds": [self.complaint_ids[2]]}).status_code, 400)
        self.assertEqual(self.write(first, "PUT", f"/api/cases/{case_id}/links", {"complaintIds": [self.complaint_ids[0]]}).status_code, 200)
        self.assertEqual(first.get(f"/api/cases/{case_id}/complaints").get_json()["items"][0]["odiNumber"], self.complaint_ids[0])
        self.assertEqual(self.write(first, "PUT", f"/api/cases/{case_id}/classification", {"tags": ["review"], "suspectedComponents": ["STEERING"]}).status_code, 200)
        note = self.write(first, "POST", f"/api/cases/{case_id}/notes", {"text": "Initial note"})
        self.assertEqual(note.status_code, 201, note.get_json())
        note_id = note.get_json()["details"]["notes"][0]["noteId"]
        self.assertEqual(self.write(first, "PATCH", f"/api/cases/{case_id}/notes/{note_id}", {"text": "Updated note"}).status_code, 200)
        self.assertEqual(self.write(first, "POST", f"/api/cases/{case_id}/sync").get_json()["sync"]["pending"], 0)
        self.assertEqual(first.get(f"/api/cases/{case_id}").get_json()["details"]["notes"][0]["text"], "Updated note")
        self.assertEqual(self.write(first, "DELETE", f"/api/cases/{case_id}/notes/{note_id}").status_code, 200)
        finding = self.write(first, "POST", f"/api/cases/{case_id}/findings", {"observation": "Synthetic finding"})
        finding_id = finding.get_json()["details"]["findings"][0]["findingId"]
        self.assertEqual(self.write(first, "PATCH", f"/api/cases/{case_id}/findings/{finding_id}", {"observation": "Revised finding"}).status_code, 200)
        self.assertEqual(self.write(first, "DELETE", f"/api/cases/{case_id}/findings/{finding_id}").status_code, 200)
        self.assertEqual(self.write(first, "PATCH", f"/api/cases/{case_id}", {"status": "CLOSED"}).status_code, 200)
        self.assertEqual(first.get(f"/api/cases/{case_id}").get_json()["history"][0]["to"], "CLOSED")
        self.connection.execute("UPDATE app_user SET role='ANALYST' WHERE user_id=%s", (self.created_users[1],))
        self.connection.commit()
        self.assertEqual(second.get(f"/api/cases/{case_id}").status_code, 404)
        self.assertEqual(self.write(second, "PATCH", f"/api/cases/{case_id}", {"status": "OPEN"}).status_code, 404)

        fleet_response = self.write(first, "POST", "/api/fleets", {"name": "Synthetic fleet"})
        self.assertEqual(fleet_response.status_code, 201, fleet_response.get_json())
        fleet_id = fleet_response.get_json()["fleet"]["fleetId"]
        self.assertEqual(second.get(f"/api/fleets/{fleet_id}").status_code, 404)
        self.assertEqual(self.write(first, "PATCH", f"/api/fleets/{fleet_id}", {"name": "Renamed synthetic fleet"}).status_code, 200)
        added = self.write(first, "POST", f"/api/fleets/{fleet_id}/vehicles", {"modelYearId": vehicle, "label": "Test vehicle"})
        self.assertEqual(added.status_code, 201, added.get_json())
        fleet_vehicle = added.get_json()["fleetVehicleId"]
        self.assertEqual(self.write(first, "POST", f"/api/fleets/{fleet_id}/vehicles", {"modelYearId": vehicle, "label": "Test vehicle"}).status_code, 409)
        self.assertEqual(first.get(f"/api/fleets/{fleet_id}/matches").get_json()["pagination"]["total"], 1)
        self.assertEqual(self.write(first, "POST", f"/api/fleets/{fleet_id}/work-orders", {"fleetVehicleId": fleet_vehicle, "recallId": self.other_recall_id}).status_code, 404)
        order = self.write(first, "POST", f"/api/fleets/{fleet_id}/work-orders", {"fleetVehicleId": fleet_vehicle, "recallId": self.recall_id})
        self.assertEqual(order.status_code, 201, order.get_json())
        order_id = order.get_json()["workOrderId"]
        self.assertEqual(self.write(first, "POST", f"/api/fleets/{fleet_id}/work-orders", {"fleetVehicleId": fleet_vehicle, "recallId": self.recall_id}).status_code, 409)
        self.assertEqual(self.write(first, "PATCH", f"/api/fleets/{fleet_id}/work-orders/{order_id}", {"status": "COMPLETED", "notes": "Synthetic note"}).status_code, 200)
        match = first.get(f"/api/fleets/{fleet_id}/matches").get_json()["items"][0]
        self.assertEqual((match["workOrderStatus"], match["workOrderNotes"]), ("COMPLETED", "Synthetic note"))
        self.assertEqual(self.write(first, "DELETE", f"/api/fleets/{fleet_id}/work-orders/{order_id}").status_code, 204)
        self.assertEqual(self.write(first, "DELETE", f"/api/fleets/{fleet_id}/vehicles/{fleet_vehicle}").status_code, 204)
        self.assertEqual(first.get(f"/api/fleets/{fleet_id}/matches").get_json()["pagination"]["total"], 0)
        self.assertEqual(self.write(second, "DELETE", f"/api/fleets/{fleet_id}").status_code, 404)
        self.assertEqual(self.write(first, "DELETE", f"/api/fleets/{fleet_id}").status_code, 204)

        self.app.extensions["mongo_client"] = BrokenClient()
        try:
            deleted = self.write(first, "DELETE", f"/api/cases/{case_id}")
        finally:
            self.app.extensions["mongo_client"] = real_client
        self.assertEqual(deleted.status_code, 202, deleted.get_json())
        self.assertIsNotNone(self.database.case_details.find_one({"caseId": case_id}))
        self.connection.execute("UPDATE app_user SET role='ADMIN' WHERE user_id=%s", (self.created_users[0],))
        self.connection.commit()
        repaired = self.write(first, "POST", "/api/admin/case-sync")
        self.assertEqual(repaired.get_json()["sync"]["pending"], 0)
        self.assertIsNone(self.database.case_details.find_one({"caseId": case_id}))
        self.assertEqual(first.get("/api/admin/imports").status_code, 200)
