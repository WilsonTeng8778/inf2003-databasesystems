"""Apply session storage and provision narrowly scoped authentication credentials."""

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values, set_key
from psycopg import sql
from project_config import ROOT, postgres
from scripts.setup_account_deletion import apply as apply_account_deletion


def main():
    path = ROOT / ".env"
    if not path.is_file():
        raise RuntimeError("Configure .env before authentication setup")
    settings = dotenv_values(path, interpolate=False)
    role = settings.get("AUTH_POSTGRES_USER") or "vehicle_safety_auth"
    if role in {os.getenv("POSTGRES_USER", "postgres"), settings.get("APP_POSTGRES_USER"), "postgres", "public"}:
        raise ValueError("Authentication requires its own non-administrator database account")
    password = settings.get("AUTH_POSTGRES_PASSWORD")
    with postgres() as connection:
        connection.execute((ROOT / "sql/migrations/002_auth_sessions.sql").read_text(encoding="utf-8"), prepare=False)
        existing = connection.execute("""SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
            FROM pg_roles WHERE rolname=%s""", (role,)).fetchone()
        if existing:
            if any(existing) or not password:
                raise RuntimeError("Authentication role exists with unexpected permissions or missing local credentials")
        else:
            password = password or secrets.token_urlsafe(32)
            connection.execute(sql.SQL("""CREATE ROLE {} LOGIN PASSWORD {}
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS""").format(
                    sql.Identifier(role), sql.Literal(password)))
        database = connection.execute("SELECT current_database()").fetchone()[0]
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT SELECT ON app_user TO {}").format(sql.Identifier(role)))
        # Registration cannot insert a client-selected role, even at SQL level.
        connection.execute(sql.SQL("GRANT INSERT(email,password_hash),UPDATE(role) ON app_user TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT USAGE ON SEQUENCE public.app_user_user_id_seq TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT SELECT,INSERT,DELETE ON app_session TO {}").format(sql.Identifier(role)))
        apply_account_deletion(connection, role)
        connection.execute(sql.SQL("ALTER ROLE {} SET statement_timeout='5s'").format(sql.Identifier(role)))
        set_key(str(path), "AUTH_POSTGRES_USER", role)
        set_key(str(path), "AUTH_POSTGRES_PASSWORD", password)
        if not settings.get("FLASK_SECRET_KEY"):
            set_key(str(path), "FLASK_SECRET_KEY", secrets.token_urlsafe(48))
    print("Authentication storage and restricted SQL account ready; secrets saved only in ignored .env.")


if __name__ == "__main__":
    main()
