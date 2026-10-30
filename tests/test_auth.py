"""Authentication HTTP contracts with an in-memory store; no real DB connections."""

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from psycopg import Error as PostgresError

from werkzeug.security import check_password_hash, generate_password_hash

from backend import create_app
from backend.auth import requires_roles
from backend.services.auth import AccountDeletionConflict, EmailTaken, LastAdministrator, PostgresAuthStore, RoleChangeDenied, token_hash

PASSWORD = "Local Test Password 2026!"


class MemoryAuthStore:
    def __init__(self):
        self.users, self.hashes, self.sessions = {}, {}, {}

    def create_user(self, email, password_hash):
        if any(user["email"] == email for user in self.users.values()):
            raise EmailTaken("An account with that email already exists")
        identifier = len(self.users) + 1
        self.users[identifier] = {"userId": identifier, "email": email, "role": "NORMAL_USER",
                                  "createdAt": datetime.now(timezone.utc).isoformat()}
        self.hashes[identifier] = password_hash
        return dict(self.users[identifier])

    def credentials(self, email):
        for identifier, user in self.users.items():
            if user["email"] == email:
                return dict(user), self.hashes[identifier]
        return None

    def open_session(self, user_id, digest, expires_at):
        self.sessions[digest] = (user_id, expires_at)

    def delete_session(self, digest):
        self.sessions.pop(digest, None)

    def session_user(self, digest):
        row = self.sessions.get(digest)
        if not row or row[1] <= datetime.now(timezone.utc) or row[0] not in self.users:
            return None
        return dict(self.users[row[0]])

    def list_users(self, page, page_size):
        users = list(self.users.values())
        return {"items": [dict(user) for user in users[(page-1)*page_size:page*page_size]],
                "pagination": {"page": page, "pageSize": page_size, "total": len(users)}}

    def change_role(self, actor_id, target_id, role):
        if self.users.get(actor_id, {}).get("role") != "ADMIN":
            raise RoleChangeDenied("Administrator access is required")
        target = self.users.get(target_id)
        if target is None:
            return None
        if target["role"] == "ADMIN" and role != "ADMIN" and sum(u["role"] == "ADMIN" for u in self.users.values()) <= 1:
            raise LastAdministrator("At least one administrator must remain")
        target["role"] = role
        return dict(target)

    def commit(self):
        pass


class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.known_hash = generate_password_hash(PASSWORD)

    def setUp(self):
        self.store = MemoryAuthStore()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "unit-test-only", "MONGO_CLIENT_FACTORY": Mock,
                               "AUTH_STORE_FACTORY": lambda: self.store, "DUMMY_PASSWORD_HASH": self.known_hash})

        @self.app.get("/__test__/analyst")
        @requires_roles("ANALYST", "ADMIN")
        def analyst_only():
            return {"allowed": True}

        self.client = self.app.test_client()

    def csrf(self, client=None):
        return (client or self.client).get("/api/auth/csrf").json["csrfToken"]

    def register(self, email="student@example.test", client=None):
        client = client or self.client
        return client.post("/api/auth/register", json={"email": email, "password": PASSWORD},
                           headers={"X-CSRF-Token": self.csrf(client)})

    def seed(self, email, role="NORMAL_USER"):
        user = self.store.create_user(email, self.known_hash)
        self.store.users[user["userId"]]["role"] = role
        return self.store.users[user["userId"]]

    def login(self, email, password=PASSWORD, client=None):
        client = client or self.client
        return client.post("/api/auth/login", json={"email": email, "password": password},
                           headers={"X-CSRF-Token": self.csrf(client)})

    def test_register_normalizes_email_hashes_password_and_signs_in(self):
        result = self.register(" Student@Example.Test ")
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json["user"]["email"], "student@example.test")
        self.assertEqual(result.json["user"]["role"], "NORMAL_USER")
        encoded = self.store.hashes[result.json["user"]["userId"]]
        self.assertNotEqual(encoded, PASSWORD)
        self.assertTrue(check_password_hash(encoded, PASSWORD))
        self.assertNotIn("password", result.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)

    def test_cookie_flags_and_no_store(self):
        response = self.register()
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_registration_rejects_client_selected_role(self):
        response = self.client.post("/api/auth/register", json={"email": "student@example.test", "password": PASSWORD, "role": "ADMIN"},
                                    headers={"X-CSRF-Token": self.csrf()})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(len(self.store.users), 0)

    def test_register_requires_csrf_and_rejects_foreign_origin(self):
        body = {"email": "student@example.test", "password": PASSWORD}
        self.assertEqual(self.client.post("/api/auth/register", json=body).status_code, 403)
        self.assertEqual(self.client.post("/api/auth/register", json=body, headers={"X-CSRF-Token": "x"*43}).status_code, 403)
        token = self.csrf()
        for origin in ["http://evil.example", "null", "http://[", "https://localhost"]:
            with self.subTest(origin=origin):
                response = self.client.post("/api/auth/register", json=body, headers={"X-CSRF-Token": token, "Origin": origin})
                self.assertEqual(response.status_code, 403)

    def test_csrf_from_another_cookie_session_is_rejected(self):
        other = self.app.test_client()
        response = self.client.post("/api/auth/register", json={"email": "student@example.test", "password": PASSWORD},
                                    headers={"X-CSRF-Token": self.csrf(other)})
        self.assertEqual(response.status_code, 403)

    def test_invalid_registration_fields(self):
        bodies = [[], {}, {"email": "not-an-email", "password": PASSWORD},
                  {"email": 3, "password": PASSWORD}, {"email": "x@example.test", "password": "short"},
                  {"email": "x@example.test", "password": "x"*129},
                  {"email": "x@example.test", "password": "invalid\0password123"},
                  {"email": "x@example.test", "password": "invalid\ud800password123"}]
        token = self.csrf()
        for body in bodies:
            with self.subTest(body=repr(body)):
                self.assertEqual(self.client.post("/api/auth/register", json=body,
                    headers={"X-CSRF-Token": token}).status_code, 400)
        self.assertEqual(len(self.store.users), 0)

    def test_duplicate_email_is_conflict(self):
        self.register()
        self.assertEqual(self.register("STUDENT@example.test").status_code, 409)

    def test_login_errors_do_not_reveal_which_credential_failed(self):
        self.seed("student@example.test")
        wrong = self.login("student@example.test", "incorrect-password")
        missing = self.login("missing@example.test")
        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(wrong.json, missing.json)
        self.assertNotIn("password_hash", wrong.get_data(as_text=True))

    def test_password_whitespace_is_preserved(self):
        self.store.create_user("student@example.test", generate_password_hash(" " + PASSWORD + " "))
        self.assertEqual(self.login("student@example.test").status_code, 401)
        self.assertEqual(self.login("student@example.test", " " + PASSWORD + " ").status_code, 200)

    def test_sign_in_rotates_csrf_and_session_identity(self):
        old_csrf = self.csrf()
        registered = self.client.post("/api/auth/register", json={"email": "student@example.test", "password": PASSWORD},
                                      headers={"X-CSRF-Token": old_csrf})
        self.assertNotEqual(registered.json["csrfToken"], old_csrf)
        with self.client.session_transaction() as values:
            old = values["session_token"]
        self.assertIn(token_hash(old), self.store.sessions)
        self.assertNotIn(old, self.store.sessions)
        self.assertEqual(self.login("student@example.test").status_code, 200)
        self.assertNotIn(token_hash(old), self.store.sessions)
        self.assertEqual(len(self.store.sessions), 1)

    def test_logout_revokes_captured_cookie(self):
        signed = self.register()
        old_cookie = self.client.get_cookie("vehicle_safety_session").value
        response = self.client.post("/api/auth/logout", json={}, headers={"X-CSRF-Token": signed.json["csrfToken"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        replay = self.app.test_client()
        replay.set_cookie("vehicle_safety_session", old_cookie)
        self.assertEqual(replay.get("/api/auth/me").status_code, 401)
        self.assertEqual(len(self.store.sessions), 0)

    def test_expired_and_deleted_user_sessions_are_rejected(self):
        self.register()
        digest = next(iter(self.store.sessions))
        identifier, _ = self.store.sessions[digest]
        self.store.sessions[digest] = (identifier, datetime.now(timezone.utc)-timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.login("student@example.test")
        del self.store.users[identifier]
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

    def test_anonymous_and_normal_users_cannot_administer(self):
        self.assertEqual(self.client.get("/api/admin/users").status_code, 401)
        signed = self.register()
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.assertEqual(self.client.patch("/api/admin/users/1/role", json={"role": "ADMIN"},
            headers={"X-CSRF-Token": signed.json["csrfToken"]}).status_code, 403)

    def test_analyst_guard_and_fresh_role_checks(self):
        user = self.seed("analyst@example.test", "ANALYST")
        self.login(user["email"])
        self.assertEqual(self.client.get("/__test__/analyst").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)
        self.store.users[user["userId"]]["role"] = "NORMAL_USER"
        self.assertEqual(self.client.get("/__test__/analyst").status_code, 403)

    def test_admin_can_change_roles_and_loses_access_after_revocation(self):
        admin = self.seed("admin@example.test", "ADMIN")
        second_admin = self.seed("second@example.test", "ADMIN")
        target = self.seed("normal@example.test")
        signed = self.login(admin["email"])
        self.assertEqual(self.client.get("/api/admin/users").status_code, 200)
        token = signed.json["csrfToken"]
        response = self.client.patch(f"/api/admin/users/{target['userId']}/role", json={"role": "ANALYST"},
                                    headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["user"]["role"], "ANALYST")
        response = self.client.patch(f"/api/admin/users/{admin['userId']}/role", json={"role": "NORMAL_USER"},
                                    headers={"X-CSRF-Token": token})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/admin/users").status_code, 403)

    def test_last_admin_and_role_validation(self):
        admin = self.seed("admin@example.test", "ADMIN")
        token = self.login(admin["email"]).json["csrfToken"]
        self.assertEqual(self.client.patch(f"/api/admin/users/{admin['userId']}/role", json={"role": "NORMAL_USER"},
            headers={"X-CSRF-Token": token}).status_code, 409)
        self.assertEqual(self.client.patch("/api/admin/users/999/role", json={"role": "ANALYST"},
            headers={"X-CSRF-Token": token}).status_code, 404)
        self.assertEqual(self.client.patch("/api/admin/users/1/role", json={"role": []},
            headers={"X-CSRF-Token": token}).status_code, 400)
        self.assertEqual(self.client.patch("/api/admin/users/1/role", json={"role": "ANALYST"}).status_code, 403)

    def test_json_content_type_and_body_limit(self):
        token = self.csrf()
        self.assertEqual(self.client.post("/api/auth/register", data="not JSON", headers={"X-CSRF-Token": token}).status_code, 415)
        self.assertEqual(self.client.post("/api/auth/register", json={"email": "x"*17000, "password": PASSWORD},
            headers={"X-CSRF-Token": token}).status_code, 413)

    def test_account_delete_requires_admin_before_store_access(self):
        self.store.delete_user = Mock()
        headers = {'X-CSRF-Token': self.csrf()}
        self.assertEqual(self.client.delete('/api/admin/users/99', json={'confirmEmail':'unused@example.test'}, headers=headers).status_code, 401)
        for role in ('NORMAL_USER', 'ANALYST'):
            user = self.seed(role.lower()+'@example.test', role)
            token = self.login(user['email']).json['csrfToken']
            self.assertEqual(self.client.delete('/api/admin/users/99', json={'confirmEmail':'unused@example.test'}, headers={'X-CSRF-Token':token}).status_code, 403)
        self.store.delete_user.assert_not_called()

    def test_admin_delete_binds_current_actor_target_and_normalized_confirmation(self):
        admin = self.seed('admin@example.test','ADMIN')
        token = self.login(admin['email']).json['csrfToken']
        self.store.delete_user=Mock(return_value=42)
        result=self.client.delete('/api/admin/users/42',json={'confirmEmail':' Unused@Example.Test '},headers={'X-CSRF-Token':token})
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json,{'deletedUserId':42})
        self.store.delete_user.assert_called_once_with(admin['userId'],42,'unused@example.test')
        self.assertEqual(result.headers['Cache-Control'],'no-store')

    def test_delete_rejects_csrf_extra_fields_invalid_ids_and_bad_email(self):
        admin=self.seed('admin@example.test','ADMIN');token=self.login(admin['email']).json['csrfToken']
        self.store.delete_user=Mock()
        path='/api/admin/users/42';valid={'confirmEmail':'unused@example.test'};headers={'X-CSRF-Token':token}
        self.assertEqual(self.client.delete(path,json=valid).status_code,403)
        for body in ({},{**valid,'actorId':admin['userId']},{**valid,'force':True},{'confirmEmail':[]},{'confirmEmail':'invalid'}):
            self.assertEqual(self.client.delete(path,json=body,headers=headers).status_code,400)
        for user_id in (0,9223372036854775808):
            self.assertEqual(self.client.delete(f'/api/admin/users/{user_id}',json=valid,headers=headers).status_code,400)
        self.assertEqual(self.client.delete(path+'?force=1',json=valid,headers=headers).status_code,400)
        self.store.delete_user.assert_not_called()

    def test_delete_conflicts_and_missing_account_are_explicit(self):
        admin=self.seed('admin@example.test','ADMIN');token=self.login(admin['email']).json['csrfToken']
        for error,status in ((AccountDeletionConflict('Account has work'),409),(LastAdministrator('At least one administrator must remain'),409),(RoleChangeDenied('Administrator access is required'),403)):
            self.store.delete_user=Mock(side_effect=error)
            result=self.client.delete('/api/admin/users/42',json={'confirmEmail':'unused@example.test'},headers={'X-CSRF-Token':token})
            self.assertEqual(result.status_code,status)
        self.store.delete_user=Mock(return_value=None)
        self.assertEqual(self.client.delete('/api/admin/users/42',json={'confirmEmail':'unused@example.test'},headers={'X-CSRF-Token':token}).status_code,404)

    def test_delete_repository_uses_guarded_function_and_bound_parameters(self):
        connection=Mock();connection.execute.return_value.fetchone.return_value=(42,)
        store=PostgresAuthStore(connection)
        value="unused' OR 1=1@example.test"
        self.assertEqual(store.delete_user(7,42,value),42)
        query,parameters=connection.execute.call_args.args
        self.assertEqual(query,'SELECT public.delete_unused_account(%s,%s,%s)')
        self.assertEqual(parameters,(7,42,value));self.assertNotIn(value,query)

    def test_delete_repository_maps_only_known_sqlstates_and_rolls_back(self):
        connection=Mock();store=PostgresAuthStore(connection)
        for code,kind in [('P2001',RoleChangeDenied),('P2002',AccountDeletionConflict),('P2003',LastAdministrator),('P2004',AccountDeletionConflict),('P2005',AccountDeletionConflict)]:
            error_type=type('NativeFixtureError',(PostgresError,),{'sqlstate':code})
            connection.execute.side_effect=error_type('PRIVATE_NATIVE_DIAGNOSTIC')
            with self.assertRaises(kind) as caught:store.delete_user(7,42,'unused@example.test')
            self.assertNotIn('PRIVATE_NATIVE_DIAGNOSTIC',str(caught.exception))
        self.assertEqual(connection.rollback.call_count,5)
        connection.execute.side_effect=PostgresError('OTHER_FIXTURE_FAILURE')
        with self.assertRaises(PostgresError):store.delete_user(7,42,'unused@example.test')


if __name__ == "__main__":
    unittest.main()
