"""Interactive, local-only bootstrap for the first administrator. No password arguments."""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from werkzeug.security import generate_password_hash
from backend.services.auth import PostgresAuthStore, validate_email, validate_password
from project_config import postgres


def main():
    email = validate_email(input("First administrator email: "))
    password = validate_password(getpass.getpass("Password (12–128 characters, hidden): "), registration=True)
    if password != getpass.getpass("Confirm password (hidden): "):
        raise ValueError("Passwords do not match")
    with postgres() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(2003,19)")
        if connection.execute("SELECT 1 FROM app_user WHERE role='ADMIN' LIMIT 1").fetchone():
            raise ValueError("An administrator already exists; use the authenticated admin API to assign further roles")
        user = PostgresAuthStore(connection).create_user(email, generate_password_hash(password))
        connection.execute("UPDATE app_user SET role='ADMIN' WHERE user_id=%s", (user["userId"],))
    print("First administrator created. Sign in using the normal login endpoint.")


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error))
