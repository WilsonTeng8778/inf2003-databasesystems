"""Check MongoDB validators and nested CRUD without needing PostgreSQL credentials.

Uses one temporary document with synthetic SQL references and removes it afterward.
This checks document structure, not cross-database referential integrity.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pymongo.errors import DuplicateKeyError, WriteError
from project_config import mongo_client, mongo_database
from mongodb.schema import initialize


def main():
    identifier = "verification-" + uuid.uuid4().hex
    case_id = int(uuid.uuid4().hex[:15], 16) + 1
    with mongo_client() as client:
        database = mongo_database(client)
        initialize(database)
        collection = database.case_details
        try:
            document = {"_id": identifier, "caseId": case_id, "linkedComplaints": [],
                        "suspectedComponents": [], "findings": [], "notes": [], "tags": []}
            collection.insert_one(document)
            collection.update_one({"_id": identifier}, {"$push": {"notes": {
                "noteId": "N1", "authorId": 1, "createdAt": datetime.now(timezone.utc), "text": "demo"}},
                "$addToSet": {"tags": "verification"}})
            collection.update_one({"_id": identifier, "notes.noteId": "N1"}, {"$set": {"notes.$.text": "edited"}})
            assert collection.find_one({"_id": identifier})["notes"][0]["text"] == "edited"
            try:
                collection.insert_one({**document, "_id": identifier + "-duplicate"})
            except DuplicateKeyError:
                pass
            else:
                raise AssertionError("caseId must be unique")
            try:
                collection.insert_one({"_id": identifier + "-invalid", "caseId": case_id + 1})
            except WriteError:
                pass
            else:
                raise AssertionError("Required document fields must be validated")
            collection.update_one({"_id": identifier}, {"$pull": {"notes": {"noteId": "N1"}, "tags": "verification"}})
            assert collection.find_one({"_id": identifier})["notes"] == []
        finally:
            collection.delete_many({"_id": {"$in": [identifier, identifier + "-duplicate", identifier + "-invalid"]}})
        print("MongoDB schema validation, unique caseId and nested CRUD passed; temporary documents removed.")


if __name__ == "__main__":
    main()
