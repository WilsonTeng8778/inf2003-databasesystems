"""Prepare a dedicated SQL reader and store its generated password in ignored .env."""

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values, set_key
from psycopg import sql
from project_config import ROOT, postgres


def main():
    path = ROOT / ".env"
    if not path.is_file():
        raise RuntimeError("Create and configure .env first")
    settings = dotenv_values(path, interpolate=False)
    role = settings.get("APP_POSTGRES_USER") or "vehicle_safety_reader"
    if role == os.getenv("POSTGRES_USER", "postgres") or role in {"postgres", "public"}:
        raise ValueError("The application reader must be separate from the setup account")
    password = settings.get("APP_POSTGRES_PASSWORD")
    with postgres() as connection:
        existing = connection.execute("""SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
            FROM pg_roles WHERE rolname=%s""", (role,)).fetchone()
        if existing:
            if any(existing) or not password:
                raise RuntimeError("Reader role already exists with unexpected permissions or missing local credentials")
        else:
            password = password or secrets.token_urlsafe(32)
            connection.execute(sql.SQL("""CREATE ROLE {} LOGIN PASSWORD {}
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS""").format(
                    sql.Identifier(role), sql.Literal(password)))
        database = connection.execute("SELECT current_database()").fetchone()[0]
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(database), sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        # Also upgrades an existing installation; no table rebuild or data import.
        connection.execute((ROOT / "sql/research_views.sql").read_text(encoding="utf-8"), prepare=False)
        connection.execute((ROOT / "sql/admin_views.sql").read_text(encoding="utf-8"), prepare=False)
        connection.execute(sql.SQL("""GRANT SELECT ON vehicle_catalogue,vehicle_safety_summary,
            research_recall,research_recall_vehicle,research_recall_record,research_investigation,
            research_investigation_vehicle,research_investigation_component,
            research_investigation_manufacturer,research_investigation_recall,
            admin_reference_counts,admin_import_runs TO {}""").format(
            sql.Identifier(role)))
        connection.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only=on").format(sql.Identifier(role)))
        connection.execute(sql.SQL("ALTER ROLE {} SET statement_timeout='5s'").format(sql.Identifier(role)))
        # Keep the SQL transaction open until both local settings are persisted.
        # A failed file write then rolls back a newly created role as well.
        set_key(str(path), "APP_POSTGRES_USER", role)
        set_key(str(path), "APP_POSTGRES_PASSWORD", password)
    print("SQL application reader ready; credentials saved locally in ignored .env (not printed).")


if __name__ == "__main__":
    main()
