"""Retry pending case document operations without touching unrelated records."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.cases import reconcile
from project_config import mongo_client, mongo_database, workflow_postgres


def main():
    with workflow_postgres() as connection, mongo_client() as client:
        result = reconcile(connection, mongo_database(client))
    print(f"Case synchronization: {result['processed']} processed, {result['pending']} pending.")
    if result["databaseUnavailable"]:
        raise SystemExit("MongoDB unavailable; pending work was retained for retry.")


if __name__ == "__main__":
    main()
