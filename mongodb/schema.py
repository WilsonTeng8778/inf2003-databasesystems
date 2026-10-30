"""Application-owned document models, kept explicit for report reproducibility."""

DATE = {"bsonType": ["date", "null"]}
NUMBER = {"bsonType": ["int", "long", "null"], "minimum": 0}
FLAG = {"bsonType": ["bool", "null"]}
TEXT_ARRAY = {"bsonType": "array", "items": {"bsonType": "string"}, "uniqueItems": True}

# Match complaint pagination's date order and deterministic ODI tie-breaker.
COMPLAINT_ORDER_INDEX = [("modelYearId", 1), ("receivedDate", -1), ("_id", -1)]


def ensure_complaint_order_index(database):
    """Add the measured paging index; retain existing data and indexes."""
    return database.complaints.create_index(COMPLAINT_ORDER_INDEX, name="vehicle_received_ordered")

SCHEMAS = {
    "complaints": {
        "bsonType": "object",
        "required": ["_id", "odiNumber", "modelYearId", "vehicle", "components", "incident", "narrative", "source"],
        "properties": {
            "_id": {"bsonType": "string"}, "odiNumber": {"bsonType": "string"},
            "modelYearId": {"bsonType": ["int", "long"], "minimum": 1},
            "vehicle": {"bsonType": "object", "required": ["make", "model", "year"], "properties": {
                "make": {"bsonType": "string"}, "model": {"bsonType": "string"},
                "year": {"bsonType": "int", "minimum": 1900, "maximum": 2100}}},
            "components": TEXT_ARRAY,
            "incident": {"bsonType": "object", "properties": {
                "crash": FLAG, "fire": FLAG, "injuries": NUMBER, "fatalities": NUMBER}},
            "mileage": NUMBER, "occurrences": NUMBER,
            "receivedDate": DATE, "incidentDate": DATE,
            "narrative": {"bsonType": "string"},
            "source": {"bsonType": "object", "required": ["archives", "rowIds"], "properties": {
                "archives": TEXT_ARRAY, "rowIds": TEXT_ARRAY}},
        },
    },
    "case_details": {
        "bsonType": "object",
        "required": ["caseId", "linkedComplaints", "suspectedComponents", "findings", "notes", "tags"],
        "properties": {
            "caseId": {"bsonType": ["int", "long"], "minimum": 1},
            "revision": {"bsonType": ["int", "long"], "minimum": 0},
            "linkedComplaints": TEXT_ARRAY, "suspectedComponents": TEXT_ARRAY, "tags": TEXT_ARRAY,
            "findings": {"bsonType": "array", "items": {"bsonType": "object",
                "required": ["findingId", "authorId", "createdAt", "observation"], "properties": {
                    "findingId": {"bsonType": "string"}, "authorId": {"bsonType": ["int", "long"], "minimum": 1},
                    "createdAt": {"bsonType": "date"}, "observation": {"bsonType": "string"}}}},
            "notes": {"bsonType": "array", "items": {"bsonType": "object",
                "required": ["noteId", "authorId", "createdAt", "text"], "properties": {
                    "noteId": {"bsonType": "string"}, "authorId": {"bsonType": ["int", "long"], "minimum": 1},
                    "createdAt": {"bsonType": "date"}, "text": {"bsonType": "string"}}}},
        },
    },
}


def initialize(database):
    names = database.list_collection_names()
    for name, schema in SCHEMAS.items():
        options = {"validator": {"$jsonSchema": schema}, "validationLevel": "strict", "validationAction": "error"}
        if name in names:
            database.command({"collMod": name, **options})
        else:
            database.create_collection(name, **options)
    database.case_details.create_index("caseId", unique=True, name="case_id_unique")
    database.complaints.create_index([("modelYearId", 1), ("receivedDate", -1)], name="vehicle_received")
    ensure_complaint_order_index(database)
    database.complaints.create_index([("modelYearId", 1), ("components", 1)], name="vehicle_components")
    database.complaints.create_index([("narrative", "text")], name="narrative_text", default_language="english")

