"""Live HTTP authentication verification with owned, temporary synthetic accounts."""

import copy
import http.cookiejar
import io
import json
import secrets
import sys
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.serving import make_server
from backend import create_app
from backend.services.auth import token_hash
from project_config import ROOT, auth_postgres, postgres
from scripts.verify_api import QuietHandler, stored_counts
from scripts import create_admin, try_auth


class Client:
    def __init__(self):
        self.cookies = http.cookiejar.CookieJar()
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(self.cookies))
        self.csrf = None


def snapshot():
    counts = stored_counts()
    with postgres() as connection:
        counts["app_session"] = connection.execute("SELECT count(*) FROM app_session").fetchone()[0]
    return counts


def main():
    before = snapshot()
    prefix = "verification-" + uuid.uuid4().hex
    emails = [prefix + suffix + "@example.invalid" for suffix in ["-normal", "-admin", "-escalation", "-demo"]]
    password, admin_password = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    app = create_app()
    server = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    checks = []
    assertions = []

    def request(client, path, expected, *, method="GET", body=None, csrf=True):
        headers = {"Content-Type": "application/json"} if body is not None else {}
        if csrf and client.csrf:
            headers["X-CSRF-Token"] = client.csrf
        data = json.dumps(body).encode("utf-8") if body is not None else None
        try:
            response = client.opener.open(Request(base + path, data=data, headers=headers, method=method), timeout=15)
        except HTTPError as error:
            response = error
        with response:
            payload = json.load(response)
            assert response.status == expected, f"{method} {path}: HTTP {response.status}, expected {expected}"
        if "csrfToken" in payload:
            client.csrf = payload["csrfToken"]
        checks.append({"method": method, "path": path, "status": expected})
        return payload

    normal, anonymous, admin, replay = Client(), Client(), Client(), Client()
    try:
        request(anonymous, "/api/auth/me", 401)
        request(anonymous, "/api/admin/users", 401)
        request(normal, "/api/auth/register", 403, method="POST",
                body={"email": emails[0], "password": password}, csrf=False)
        request(normal, "/api/auth/csrf", 200)
        request(normal, "/api/auth/register", 400, method="POST",
                body={"email": emails[2], "password": password, "role": "ADMIN"})
        signed = request(normal, "/api/auth/register", 201, method="POST", body={"email": emails[0], "password": password})
        user_id = signed["user"]["userId"]
        assert signed["user"]["role"] == "NORMAL_USER" and "password" not in json.dumps(signed)
        request(normal, "/api/auth/me", 200)
        request(normal, "/api/auth/logout", 403, method="POST", body={}, csrf=False)
        request(normal, "/api/auth/register", 409, method="POST", body={"email": emails[0].upper(), "password": password})
        request(normal, "/api/admin/users", 403)
        request(normal, f"/api/admin/users/{user_id}/role", 403, method="PATCH", body={"role": "ADMIN"})
        with postgres() as connection:
            stored = connection.execute("SELECT password_hash FROM app_user WHERE user_id=%s", (user_id,)).fetchone()[0]
            assert stored != password and check_password_hash(stored, password)
        assertions.extend(["new registrations are NORMAL_USER", "client role escalation rejected", "password stored as a hash"])

        request(anonymous, "/api/auth/csrf", 200)
        bad = request(anonymous, "/api/auth/login", 401, method="POST", body={"email": emails[0], "password": "incorrect-password"})
        missing = request(anonymous, "/api/auth/login", 401, method="POST", body={"email": prefix+"-missing@example.invalid", "password": password})
        assert bad == missing
        request(anonymous, "/api/auth/login", 200, method="POST", body={"email": emails[0], "password": password})
        captured = next(copy.copy(cookie) for cookie in anonymous.cookies if cookie.name == "vehicle_safety_session")
        serializer = app.session_interface.get_signing_serializer(app)
        raw_token = serializer.loads(captured.value)["session_token"]
        with postgres() as connection:
            digest = connection.execute("SELECT token_hash FROM app_session WHERE token_hash=%s", (token_hash(raw_token),)).fetchone()[0]
            assert digest != raw_token and len(digest) == 64
        request(anonymous, "/api/auth/logout", 200, method="POST", body={})
        request(anonymous, "/api/auth/me", 401)
        replay.cookies.set_cookie(captured)
        request(replay, "/api/auth/me", 401)
        assertions.extend(["bad and unknown credentials return the same response", "server stores hashed session tokens", "logout revokes captured cookies"])

        with postgres() as connection:
            connection.execute("""UPDATE app_session SET created_at=now()-interval '2 hours',
                expires_at=now()-interval '1 hour' WHERE user_id=%s""", (user_id,))
        request(normal, "/api/auth/me", 401)
        request(normal, "/api/auth/csrf", 200)
        request(normal, "/api/auth/login", 200, method="POST", body={"email": emails[0], "password": password})
        assertions.append("expired sessions are rejected")

        with postgres() as connection:
            initial_admins = connection.execute("SELECT count(*) FROM app_user WHERE role='ADMIN'").fetchone()[0]
        if initial_admins == 0:
            with patch("builtins.input", return_value=emails[1]), patch("getpass.getpass", return_value=admin_password), redirect_stdout(io.StringIO()):
                create_admin.main()
            assertions.append("interactive first-administrator bootstrap works")
        else:
            with postgres() as connection:
                connection.execute("""INSERT INTO app_user(email,password_hash,role)
                    VALUES (%s,%s,'ADMIN')""", (emails[1], generate_password_hash(admin_password)))
        with postgres() as connection:
            admin_id = connection.execute("SELECT user_id FROM app_user WHERE email=%s", (emails[1],)).fetchone()[0]
        try:
            with patch("builtins.input", return_value=emails[2]), patch("getpass.getpass", return_value=admin_password), redirect_stdout(io.StringIO()):
                create_admin.main()
        except ValueError:
            assertions.append("first-admin bootstrap refuses a second bootstrap")
        else:
            raise AssertionError("First-admin bootstrap should refuse when an administrator already exists")
        request(admin, "/api/auth/csrf", 200)
        request(admin, "/api/auth/login", 200, method="POST", body={"email": emails[1], "password": admin_password})
        listed = request(admin, "/api/admin/users?pageSize=2", 200)
        assert all(set(item) == {"userId", "email", "role", "createdAt"} for item in listed["items"])
        request(admin, f"/api/admin/users/{user_id}/role", 200, method="PATCH", body={"role": "ANALYST"})
        assert request(normal, "/api/auth/me", 200)["user"]["role"] == "ANALYST"
        request(normal, "/api/admin/users", 403)
        request(admin, f"/api/admin/users/{user_id}/role", 200, method="PATCH", body={"role": "ADMIN"})
        request(normal, "/api/admin/users", 200)
        request(admin, f"/api/admin/users/{admin_id}/role", 200, method="PATCH", body={"role": "NORMAL_USER"})
        request(admin, "/api/admin/users", 403)
        if initial_admins == 0:
            request(normal, f"/api/admin/users/{user_id}/role", 409, method="PATCH", body={"role": "NORMAL_USER"})
            assertions.append("last administrator cannot be demoted")
        request(normal, f"/api/admin/users/{user_id}/role", 400, method="PATCH", body={"role": "UNKNOWN"})
        assertions.extend(["admin user listing omits credential fields", "administrator role changes work",
                           "role changes and revocation affect existing sessions immediately"])
        request(anonymous, "/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC", 200)
        request(normal, "/api/auth/logout", 200, method="POST", body={})
        request(admin, "/api/auth/logout", 200, method="POST", body={})
        with auth_postgres() as connection:
            role, can_insert_role, can_update_role, can_write_reference = connection.execute("""SELECT current_user,
                has_column_privilege(current_user,'app_user','role','INSERT'),
                has_column_privilege(current_user,'app_user','role','UPDATE'),
                has_table_privilege(current_user,'recall','INSERT,UPDATE,DELETE')""").fetchone()
            assert role != "postgres" and not can_insert_role and can_update_role and not can_write_reference
        assertions.append("auth SQL role cannot insert a chosen role or modify official records")
        for mode in [["--register"], []]:
            output = io.StringIO()
            with patch("sys.argv", ["try_auth.py", *mode, "--base-url", base]), patch("builtins.input", return_value=emails[3]), patch("getpass.getpass", return_value=password), redirect_stdout(output):
                try_auth.main()
            assert "Signed out" in output.getvalue() and password not in output.getvalue()
        assertions.append("interactive registration and login helpers complete and log out")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions["mongo_client"].close()
        # Only generated fixture emails are eligible for deletion. Session rows
        # cascade; no existing users, cases, fleets or source records are cleared.
        with postgres() as connection:
            connection.execute("DELETE FROM app_user WHERE email=ANY(%s)", (emails,))
    after = snapshot()
    assert before == after, "Owned fixtures were not fully cleaned up or unrelated records changed"
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "assertions_passed": assertions, "temporary_accounts_removed": True,
              "record_counts_unchanged_after_cleanup": before == after, "record_counts": after,
              "auth_sql_role": role, "last_admin_guard_tested_live": initial_admins == 0,
              "interactive_registration_login_flows_verified": 2,
              "first_admin_bootstrap_verified_live": initial_admins == 0,
              "limitations": ["Analyst case and fleet ownership enforcement awaits those workflow APIs.",
                               "Browser login forms are not implemented; authentication is through JSON APIs."]}
    (ROOT / "docs/auth_verification_report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
