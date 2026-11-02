"""Import the full approved, valid-model-year vehicle scope from local ZIPs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_config import mongo_client, mongo_database, postgres
from etl.runner import import_lock, run_imports


def main():
    with postgres() as connection, mongo_client() as client:
        with import_lock(connection):
            run_imports(connection, mongo_database(client))


if __name__ == "__main__":
    main()
