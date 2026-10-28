"""Create project databases and apply additive schema/index definitions."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psycopg import sql
from project_config import ROOT, mongo_client, mongo_database, postgres
from mongodb.schema import initialize


def setup():
    name = os.getenv("POSTGRES_DB", "vehicle_safety")
    if name in {"postgres", "template0", "template1"}:
        raise ValueError("POSTGRES_DB must be a dedicated project database.")
    with postgres("postgres", autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone()
        if not exists:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            print(f"Created PostgreSQL database {name}")
    with postgres() as connection:
        files = [ROOT / "sql" / "schema.sql", *sorted((ROOT / "sql" / "migrations").glob("*.sql")),
                 *[ROOT / "sql" / name for name in ["indexes.sql", "views.sql", "triggers.sql"]]]
        for path in files:
            connection.execute(path.read_text(encoding="utf-8"), prepare=False)
            print(f"Applied {path.relative_to(ROOT).as_posix()}")
    with mongo_client() as client:
        database = mongo_database(client)
        if database.name in {"admin", "config", "local"}:
            raise ValueError("MONGODB_DB must be a dedicated project database.")
        initialize(database)
        print(f"MongoDB {database.name}: validators and indexes ready")


if __name__ == "__main__":
    setup()
