"""Saved-vehicle routes, ownership, validation and SQL guards without real databases."""

import copy
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

from psycopg import OperationalError
from psycopg.errors import UniqueViolation

from backend import create_app
from backend.services.auth import token_hash
from backend.services.saved_vehicles import AlreadySaved, PostgresSavedVehicleStore, VehicleNotFound


class MemorySavedStore:
    def __init__(self):
        self.rows, self.next_id, self.commits = {}, 1, 0

    def get(self, user_id, saved_id):
        row = self.rows.get(saved_id)
        return copy.deepcopy({key: value for key, value in row.items() if key != "owner"}) if row and row["owner"] == user_id else None

    def list(self, user_id, page, size):
        rows = [self.get(user_id, key) for key in sorted(self.rows, reverse=True) if self.rows[key]["owner"] == user_id]
        return {"items": rows[(page-1)*size:page*size],
                "pagination": {"page": page, "pageSize": size, "total": len(rows), "totalPages": (len(rows)+size-1)//size}}

    def create(self, user_id, model_year_id, nickname):
        if model_year_id not in {42, 43}:
            raise VehicleNotFound("Vehicle not found in the imported catalogue")
        if any(row["owner"] == user_id and row["modelYearId"] == model_year_id for row in self.rows.values()):
            raise AlreadySaved("This vehicle is already in your saved vehicles")
        identifier = self.next_id
        self.next_id += 1
        self.rows[identifier] = {"owner": user_id, "savedVehicleId": identifier, "modelYearId": model_year_id,
                                 "nickname": nickname, "savedAt": datetime.now(timezone.utc).isoformat(),
                                 "vehicle": {"year": 2022, "make": "HONDA", "model": "CIVIC"}}
        return self.get(user_id, identifier)

    def rename(self, user_id, saved_id, nickname):
        if self.get(user_id, saved_id) is None:
            return None
        self.rows[saved_id]["nickname"] = nickname
        return self.get(user_id, saved_id)

    def delete(self, user_id, saved_id):
        if self.get(user_id, saved_id) is None:
            return False
        del self.rows[saved_id]
        return True

    def commit(self):
        self.commits += 1


class SavedVehicleTests(unittest.TestCase):
    def setUp(self):
        self.saved = MemorySavedStore()
        self.tokens = {number: chr(96+number)*43 for number in [1, 2, 3]}
        self.users = {token_hash(token): {"userId": number, "role": "ADMIN" if number == 3 else "NORMAL_USER"}
                      for number, token in self.tokens.items()}
        self.auth = Mock()
        self.auth.session_user.side_effect = lambda digest: self.users.get(digest)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "unit-test-only", "MONGO_CLIENT_FACTORY": Mock,
                               "AUTH_STORE_FACTORY": lambda: self.auth, "SAVED_VEHICLE_STORE_FACTORY": lambda: self.saved,
                               "DUMMY_PASSWORD_HASH": "unused-with-prepared-sessions"})
        self.owner, self.other, self.admin = [self.client(number) for number in [1, 2, 3]]
        self.headers = {"X-CSRF-Token": "c"*43}

    def client(self, user_id):
        client = self.app.test_client()
        with client.session_transaction() as values:
            values["session_token"], values["csrf_token"] = self.tokens[user_id], "c"*43
        return client

    def create(self, client=None, **fields):
        return (client or self.owner).post("/api/saved-vehicles", json={"modelYearId": 42, **fields}, headers=self.headers)

    def test_anonymous_access_is_denied(self):
        client = self.app.test_client()
        self.assertEqual(client.get("/api/saved-vehicles").status_code, 401)
        token = client.get("/api/auth/csrf").json["csrfToken"]
        self.assertEqual(client.post("/api/saved-vehicles", json={"modelYearId": 42}, headers={"X-CSRF-Token": token}).status_code, 401)
        self.assertEqual(len(self.saved.rows), 0)

    def test_full_owner_crud(self):
        response = self.create(nickname="  My Civic  ")
        self.assertEqual(response.status_code, 201)
        item = response.json["savedVehicle"]
        self.assertNotIn("owner", item)
        self.assertEqual(item["nickname"], "My Civic")
        path = response.headers["Location"]
        self.assertEqual(self.owner.get(path).json["savedVehicle"], item)
        self.assertEqual(self.owner.get("/api/saved-vehicles").json["pagination"]["total"], 1)
        edited = self.owner.patch(path, json={"nickname": "Renamed"}, headers=self.headers)
        self.assertEqual(edited.json["savedVehicle"]["nickname"], "Renamed")
        removed = self.owner.delete(path, headers=self.headers)
        self.assertEqual(removed.status_code, 204)
        self.assertEqual(removed.data, b"")
        self.assertEqual(self.owner.get(path).status_code, 404)

    def test_other_user_cannot_list_read_rename_or_delete(self):
        response = self.create(nickname="Owner only")
        path = response.headers["Location"]
        self.assertEqual(self.other.get("/api/saved-vehicles").json["items"], [])
        foreign = self.other.get(path)
        absent = self.other.get("/api/saved-vehicles/9999")
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json, absent.json)
        self.assertEqual(self.other.patch(path, json={"nickname": "Hacked"}, headers=self.headers).status_code, 404)
        self.assertEqual(self.other.delete(path, headers=self.headers).status_code, 404)
        self.assertEqual(self.owner.get(path).json["savedVehicle"]["nickname"], "Owner only")

    def test_admin_has_no_personal_ownership_override(self):
        path = self.create().headers["Location"]
        self.assertEqual(self.admin.get(path).status_code, 404)
        self.assertEqual(self.admin.patch(path, json={"nickname": "Hacked"}, headers=self.headers).status_code, 404)
        self.assertEqual(self.admin.delete(path, headers=self.headers).status_code, 404)

    def test_duplicate_is_per_user_not_global(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(self.create(self.other).status_code, 201)
        self.assertEqual(len(self.saved.rows), 2)

    def test_owner_and_vehicle_cannot_be_spoofed_in_payload(self):
        self.assertEqual(self.create(userId=2).status_code, 400)
        path = self.create().headers["Location"]
        for extra in [{"userId": 2}, {"modelYearId": 43}]:
            self.assertEqual(self.owner.patch(path, json={"nickname": "changed", **extra}, headers=self.headers).status_code, 400)
        self.assertEqual(self.owner.get("/api/saved-vehicles?userId=2").status_code, 400)
        self.assertEqual(self.saved.rows[1]["owner"], 1)

    def test_missing_catalogue_vehicle_is_not_saved(self):
        self.assertEqual(self.create(modelYearId=9999).status_code, 404)
        self.assertEqual(self.saved.rows, {})
        self.assertEqual(self.saved.commits, 0)

    def test_invalid_model_year_identifiers(self):
        for value in [True, "42", None, 0, -1, 3.5, [], 2**63]:
            with self.subTest(value=value):
                self.assertEqual(self.create(modelYearId=value).status_code, 400)
        self.assertEqual(self.saved.rows, {})

    def test_nickname_validation(self):
        for value in [None, 3, False, "x"*101, "bad\0nickname", "two\nlines"]:
            with self.subTest(value=repr(value)):
                self.assertEqual(self.create(nickname=value).status_code, 400)
        path = self.create().headers["Location"]
        self.assertEqual(self.owner.patch(path, json={"nickname": "   "}, headers=self.headers).json["savedVehicle"]["nickname"], "")

    def test_all_writes_require_csrf(self):
        self.assertEqual(self.owner.post("/api/saved-vehicles", json={"modelYearId": 42}).status_code, 403)
        path = self.create().headers["Location"]
        self.assertEqual(self.owner.patch(path, json={"nickname": "No token"}).status_code, 403)
        self.assertEqual(self.owner.delete(path).status_code, 403)
        self.assertEqual(self.owner.get(path).status_code, 200)

    def test_invalid_and_duplicate_pagination(self):
        for query in ["page=0", "pageSize=101", "pageSize=0", "page=1&page=2", "unknown=yes"]:
            with self.subTest(query=query):
                self.assertEqual(self.owner.get("/api/saved-vehicles?"+query).status_code, 400)

    def test_stable_pagination_and_owner_scope(self):
        first = self.create().json["savedVehicle"]["savedVehicleId"]
        second = self.create(modelYearId=43).json["savedVehicle"]["savedVehicleId"]
        self.create(self.other)
        page1 = self.owner.get("/api/saved-vehicles?pageSize=1").json
        page2 = self.owner.get("/api/saved-vehicles?pageSize=1&page=2").json
        self.assertEqual(page1["pagination"]["total"], 2)
        self.assertEqual(page1["items"][0]["savedVehicleId"], second)
        self.assertEqual(page2["items"][0]["savedVehicleId"], first)

    def test_bad_url_identifiers(self):
        for value in [0, 2**63]:
            path = f"/api/saved-vehicles/{value}"
            self.assertEqual(self.owner.get(path).status_code, 400)
            self.assertEqual(self.owner.patch(path, json={"nickname": "x"}, headers=self.headers).status_code, 400)
            self.assertEqual(self.owner.delete(path, headers=self.headers).status_code, 400)

    def test_revoked_session_cannot_save(self):
        del self.users[token_hash(self.tokens[1])]
        self.assertEqual(self.create().status_code, 401)
        self.assertEqual(len(self.saved.rows), 0)

    def test_private_responses_are_not_cached(self):
        self.assertEqual(self.owner.get("/api/saved-vehicles").headers["Cache-Control"], "no-store")

    def test_workflow_connection_is_closed_after_response(self):
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = (1, 42, "My car", datetime.now(timezone.utc), "HONDA", "CIVIC", 2022)
        self.app.config["SAVED_VEHICLE_STORE_FACTORY"] = None
        self.app.config["WORKFLOW_PG_CONNECT"] = lambda: connection
        self.assertEqual(self.owner.get("/api/saved-vehicles/1").status_code, 200)
        connection.close.assert_called_once()

    def test_workflow_failure_is_sanitized(self):
        self.app.config["SAVED_VEHICLE_STORE_FACTORY"] = None
        self.app.config["WORKFLOW_PG_CONNECT"] = Mock(side_effect=OperationalError("DO_NOT_EXPOSE"))
        response = self.owner.get("/api/saved-vehicles")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("DO_NOT_EXPOSE", response.get_data(as_text=True))

    def test_sql_lookups_and_mutations_include_owner_and_use_parameters(self):
        connection = Mock()
        connection.execute.return_value.fetchone.return_value = None
        service = PostgresSavedVehicleStore(connection)
        service.get(44, 7)
        label = "Name'); DROP TABLE saved_vehicle; --"
        service.rename(44, 7, label)
        service.delete(44, 7)
        for call in connection.execute.call_args_list:
            self.assertIn("user_id=%s", call.args[0])
            self.assertIn(44, call.args[1])
            self.assertIn(7, call.args[1])
            self.assertNotIn(label, call.args[0])

    def test_duplicate_sql_write_rolls_back(self):
        connection = Mock()
        connection.execute.side_effect = UniqueViolation()
        with self.assertRaises(AlreadySaved):
            PostgresSavedVehicleStore(connection).create(1, 42, "test")
        connection.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
