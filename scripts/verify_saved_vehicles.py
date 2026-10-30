"""Live owner-scoped CRUD checks with synthetic users and cleanup of owned fixtures."""

import io
import json
import secrets
import sys
import threading
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.serving import make_server
from backend import create_app
from project_config import ROOT, postgres, workflow_postgres
from scripts import try_saved_vehicles
from scripts.support.local_api import ApiError, LocalApi
from scripts.verify_api import QuietHandler
from scripts.verify_auth import snapshot


def main():
    before = snapshot()
    prefix = "saved-verification-" + uuid.uuid4().hex
    emails = [prefix + suffix + "@example.invalid" for suffix in ["-owner", "-other"]]
    password = secrets.token_urlsafe(24)
    app = create_app()
    server = make_server("127.0.0.1", 0, app, request_handler=QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    first, second, anonymous = [LocalApi(base) for _ in range(3)]
    checks, assertions = [], []

    def request(client, path, expected, *, body=None, method=None, csrf=True):
        old_token = client.csrf_token
        if not csrf:
            client.csrf_token = None
        try:
            try:
                result = client.request(path, body, method=method)
            except ApiError as error:
                result = {"error": str(error)}
            assert client.last_status == expected, f"Unexpected HTTP {client.last_status} for {path}; expected {expected}"
            checks.append({"method": method or ("POST" if body is not None else "GET"), "path": path, "status": expected})
            return result
        finally:
            if not csrf:
                client.csrf_token = old_token

    try:
        request(anonymous, "/api/saved-vehicles", 401)
        users = []
        for client, email in zip([first, second], emails):
            request(client, "/api/auth/csrf", 200)
            user = request(client, "/api/auth/register", 201, body={"email": email, "password": password})["user"]
            users.append(user)
        found = request(first, "/api/vehicles/search?year=2022&make=HONDA&model=CIVIC", 200)
        model_year_id = found["items"][0]["modelYearId"]
        request(first, "/api/saved-vehicles", 403, body={"modelYearId": model_year_id}, csrf=False)
        request(first, "/api/saved-vehicles", 400, body={"modelYearId": model_year_id, "userId": users[1]["userId"]})
        item = request(first, "/api/saved-vehicles", 201, body={"modelYearId": model_year_id, "nickname": "Owner Civic"})["savedVehicle"]
        path = first.last_headers["Location"]
        assert path == f"/api/saved-vehicles/{item['savedVehicleId']}"
        assert request(first, path, 200)["savedVehicle"]["nickname"] == "Owner Civic"
        own_list = request(first, "/api/saved-vehicles?pageSize=1", 200)
        assert own_list["pagination"]["total"] == 1 and own_list["items"][0]["savedVehicleId"] == item["savedVehicleId"]
        assert request(second, "/api/saved-vehicles", 200)["items"] == []
        request(first, "/api/saved-vehicles", 409, body={"modelYearId": model_year_id})
        foreign = request(second, path, 404)
        assert foreign == request(second, "/api/saved-vehicles/9223372036854775807", 404)
        request(second, path, 404, body={"nickname": "Not mine"}, method="PATCH")
        request(second, path, 404, method="DELETE")
        assert request(first, path, 200)["savedVehicle"]["nickname"] == "Owner Civic"
        other_item = request(second, "/api/saved-vehicles", 201, body={"modelYearId": model_year_id, "nickname": "Other Civic"})["savedVehicle"]
        assert other_item["savedVehicleId"] != item["savedVehicleId"]
        assertions.extend(["full owner read/create/list works", "duplicate prevention is per user",
                           "foreign and nonexistent saved records are indistinguishable", "cross-user read/update/delete denied"])

        # An administrator's personal saved-vehicle routes still have no override.
        with postgres() as connection:
            connection.execute("UPDATE app_user SET role='ADMIN' WHERE user_id=%s", (users[1]["userId"],))
        request(second, path, 404)
        request(second, path, 404, body={"nickname": "Admin override"}, method="PATCH")
        request(second, path, 404, method="DELETE")
        assertions.append("ADMIN has no override on another user's personal saved records")

        renamed = request(first, path, 200, body={"nickname": "Renamed Civic"}, method="PATCH")
        assert renamed["savedVehicle"]["nickname"] == "Renamed Civic"
        with postgres() as connection:
            owner, label = connection.execute("SELECT user_id,nickname FROM saved_vehicle WHERE saved_vehicle_id=%s",
                                              (item["savedVehicleId"],)).fetchone()
            assert owner == users[0]["userId"] and label == "Renamed Civic"
            unknown_vehicle = connection.execute("SELECT max(model_year_id)+1000000 FROM model_year").fetchone()[0]
        request(first, path, 400, body={"nickname": "Move", "userId": users[1]["userId"]}, method="PATCH")
        request(first, path, 400, body={"nickname": "Move", "modelYearId": model_year_id}, method="PATCH")
        request(first, "/api/saved-vehicles?userId="+str(users[1]["userId"]), 400)
        request(first, "/api/saved-vehicles", 404, body={"modelYearId": unknown_vehicle})
        request(first, "/api/saved-vehicles", 400, body={"modelYearId": True})
        request(first, "/api/saved-vehicles", 400, body={"modelYearId": model_year_id, "nickname": "x"*101})
        request(first, "/api/saved-vehicles?pageSize=101", 400)
        request(first, path, 403, method="DELETE", csrf=False)
        request(first, path, 204, method="DELETE")
        request(first, path, 404)
        request(second, f"/api/saved-vehicles/{other_item['savedVehicleId']}", 200)
        assertions.extend(["renames persist with original owner", "owner/model identity cannot be changed via payload",
                           "invalid inputs and CSRF are enforced", "owner deletion preserves the other user's record"])

        # Exercise the actual interactive menu, supplying only operator prompts.
        answers = iter([emails[0], "2", "2022", "HONDA", "CIVIC", "Menu demo", "1",
                        "3", "__saved_id__", "Menu renamed", "4", "__saved_id__", "1", "0"])
        id_prompts = 0

        def operator(prompt):
            nonlocal id_prompts
            answer = next(answers)
            if answer == "__saved_id__":
                with postgres() as connection:
                    row = connection.execute("SELECT saved_vehicle_id,nickname FROM saved_vehicle WHERE user_id=%s",
                                             (users[0]["userId"],)).fetchone()
                assert row is not None
                if id_prompts == 1:
                    assert row[1] == "Menu renamed"
                id_prompts += 1
                return str(row[0])
            return answer

        output = io.StringIO()
        with patch("sys.argv", ["try_saved_vehicles.py", "--base-url", base]), patch("builtins.input", side_effect=operator), patch("getpass.getpass", return_value=password), redirect_stdout(output):
            try_saved_vehicles.main()
        assert "Saved vehicle removed" in output.getvalue() and "Signed out" in output.getvalue() and password not in output.getvalue()
        assertions.append("interactive menu saves, lists, renames, removes and signs out")
        request(second, f"/api/saved-vehicles/{other_item['savedVehicleId']}", 204, method="DELETE")
        for client in [first, second]:
            request(client, "/api/auth/logout", 200, body={})
        with workflow_postgres() as connection:
            role, can_read_users, can_write_reference, can_change_owner, can_change_nickname = connection.execute("""SELECT current_user,
                has_table_privilege(current_user,'app_user','SELECT'),
                has_table_privilege(current_user,'recall','INSERT,UPDATE,DELETE'),
                has_column_privilege(current_user,'saved_vehicle','user_id','UPDATE'),
                has_column_privilege(current_user,'saved_vehicle','nickname','UPDATE')""").fetchone()
            assert role != "postgres" and not can_read_users and not can_write_reference and not can_change_owner and can_change_nickname
        assertions.append("workflow SQL role cannot read credentials, modify reference data or change owner columns")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        app.extensions["mongo_client"].close()
        with postgres() as connection:
            connection.execute("DELETE FROM app_user WHERE email=ANY(%s)", (emails,))
    after = snapshot()
    assert before == after, "Owned fixtures were not fully removed or unrelated record counts changed"
    report = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "assertions_passed": assertions, "interactive_menu_verified": True,
              "workflow_sql_role": role, "temporary_accounts_removed": True,
              "record_counts_unchanged_after_cleanup": True, "record_counts": after,
              "limitations": ["Ownership enforcement is in the API/SQL predicates; database row-level security is not configured.",
                               "Analyst cases, fleets and the visual GUI are subsequent work."]}
    (ROOT / "docs/saved_vehicles_verification_report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
