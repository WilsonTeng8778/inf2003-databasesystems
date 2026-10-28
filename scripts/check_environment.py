"""Check local tools, source files and authenticated database connections."""

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_config import mongo_client, postgres
from etl.source import RAW, SOURCES


def main():
    okay = True
    print(f"Python: {sys.version.split()[0]}")
    for command in ["psql", "mongosh"]:
        print(f"{command}: {shutil.which(command) or 'not on PATH (Python drivers can still connect)'}")
    for filename, _ in SOURCES.values():
        present = (RAW / filename).is_file()
        okay &= present
        print(f"Source {filename}: {'present' if present else 'MISSING'}")
    try:
        with postgres("postgres") as connection:
            print("PostgreSQL authenticated:", connection.execute("SHOW server_version").fetchone()[0])
    except Exception as error:
        okay = False
        print(f"PostgreSQL connection failed ({type(error).__name__}). Check .env and the Windows service.")
    try:
        with mongo_client() as client:
            client.admin.command("ping")
            print("MongoDB authenticated/reachable:", client.server_info()["version"])
    except Exception as error:
        okay = False
        print(f"MongoDB connection failed ({type(error).__name__}). Check .env and the Windows service.")
    return 0 if okay else 1


if __name__ == "__main__":
    raise SystemExit(main())

