"""Import the full approved, valid-model-year vehicle scope from local ZIPs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_config import mongo_client, mongo_database, postgres
from etl.catalogue import import_catalogue
from etl.import_recalls import import_recalls
from etl.import_investigations import import_investigations
from etl.import_complaints import import_complaints


def main():
    with postgres() as connection, mongo_client() as client:
        # Session lock survives stage commits. A second importer fails clearly.
        acquired = connection.execute("SELECT pg_try_advisory_lock(2003192026)").fetchone()[0]
        connection.commit()
        if not acquired:
            raise RuntimeError("Another project import is running; wait for it to finish.")
        try:
            import_catalogue(connection)
            import_recalls(connection)
            import_investigations(connection)
            import_complaints(connection, mongo_database(client))
            connection.execute("ANALYZE")
            connection.commit()
        finally:
            connection.execute("SELECT pg_advisory_unlock(2003192026)")
            connection.commit()


if __name__ == "__main__":
    main()
