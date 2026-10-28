"""Provision limited saved-vehicle access without changing stored project records."""

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
        raise RuntimeError("Configure .env before workflow setup")
    settings = dotenv_values(path, interpolate=False)
    role = settings.get("WORKFLOW_POSTGRES_USER") or "vehicle_safety_workflow"
    if role in {os.getenv("POSTGRES_USER", "postgres"), settings.get("APP_POSTGRES_USER"),
                settings.get("AUTH_POSTGRES_USER"), "postgres", "public"}:
        raise ValueError("Workflow access requires its own non-administrator SQL account")
    password = settings.get("WORKFLOW_POSTGRES_PASSWORD")
    with postgres() as connection:
        existing = connection.execute("""SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
            FROM pg_roles WHERE rolname=%s""", (role,)).fetchone()
        if existing:
            if any(existing) or not password:
                raise RuntimeError("Workflow role exists with unexpected permissions or missing local credentials")
        else:
            password = password or secrets.token_urlsafe(32)
            connection.execute(sql.SQL("""CREATE ROLE {} LOGIN PASSWORD {}
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS""").format(
                    sql.Identifier(role), sql.Literal(password)))
        database = connection.execute("SELECT current_database()").fetchone()[0]
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT SELECT ON vehicle_catalogue,saved_vehicle TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT INSERT(user_id,model_year_id,nickname),UPDATE(nickname),DELETE ON saved_vehicle TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("GRANT USAGE ON SEQUENCE public.saved_vehicle_saved_vehicle_id_seq TO {}").format(sql.Identifier(role)))
        connection.execute(sql.SQL("ALTER ROLE {} SET statement_timeout='5s'").format(sql.Identifier(role)))
        set_key(str(path), "WORKFLOW_POSTGRES_USER", role)
        set_key(str(path), "WORKFLOW_POSTGRES_PASSWORD", password)
    print("Saved-vehicle SQL access ready; credentials saved only in ignored .env. Existing records retained.")


if __name__ == "__main__":
    main()
