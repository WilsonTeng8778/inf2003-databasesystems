"""Database-only proof of combined SQL + MongoDB vehicle research."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_config import mongo_client, mongo_database, postgres
from backend.services.research import safety_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--make", default="HONDA")
    parser.add_argument("--model", default="CIVIC")
    parser.add_argument("--year", type=int, default=2022)
    args = parser.parse_args()
    with postgres() as connection, mongo_client() as client:
        result = safety_profile(connection, mongo_database(client), args.make, args.model, args.year)
    if result is None:
        print("No matching vehicle in the imported catalogue.")
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

