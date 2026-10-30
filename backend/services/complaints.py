"""Read-only complaint queries with explicit public fields and bounded operations."""

from datetime import datetime, time, timezone


INTERPRETATION = "Consumer complaints are allegations, not confirmed defects; vehicle matches are not VIN-specific."
COMMON_FIELDS = {field: 1 for field in (
    "odiNumber", "modelYearId", "vehicle", "components", "incident", "receivedDate", "incidentDate",
)}
LIST_FIELDS = {**COMMON_FIELDS, "narrative": 1}
DETAIL_FIELDS = {**LIST_FIELDS, "manufacturer": 1, "mileage": 1, "occurrences": 1, "source": 1}


def complaint_query(*, model_year_id=None, year=None, make=None, model=None, component=None,
                    received_from=None, received_to=None, crash=None, fire=None,
                    has_injuries=None, has_fatalities=None, q=None):
    query = {}
    for field, value in (("modelYearId", model_year_id), ("vehicle.year", year),
                         ("vehicle.make", make), ("vehicle.model", model), ("components", component),
                         ("incident.crash", crash), ("incident.fire", fire)):
        if value is not None:
            query[field] = value
    for field, value in (("incident.injuries", has_injuries), ("incident.fatalities", has_fatalities)):
        if value is not None:
            # Unknown/null counts do not mean zero reported injuries/fatalities.
            query[field] = {"$gt": 0} if value else 0
    if received_from is not None or received_to is not None:
        bounds = {}
        if received_from is not None:
            bounds["$gte"] = datetime.combine(received_from, time.min, timezone.utc)
        if received_to is not None:
            bounds["$lte"] = datetime.combine(received_to, time(23, 59, 59, 999000), timezone.utc)
        query["receivedDate"] = bounds
    if q is not None:
        query["$text"] = {"$search": q}
    return query


def public_complaint(document, *, detail=False):
    result = {field: document.get(field) for field in COMMON_FIELDS}
    for field, names in (("vehicle", ("make", "model", "year")),
                         ("incident", ("crash", "fire", "injuries", "fatalities"))):
        result[field] = {name: document.get(field, {}).get(name) for name in names}
    for field in ("receivedDate", "incidentDate"):
        value = result[field]
        result[field] = value.date().isoformat() if value is not None else None
    if detail:
        result.update({field: document.get(field) for field in (
            "narrative", "manufacturer", "mileage", "occurrences",
        )})
        source = document.get("source", {})
        result["source"] = {field: source.get(field) for field in (
            "archives", "rowIds", "componentRowCount", "conflictingScalarColumns",
        )}
    else:
        narrative = document.get("narrative", "")
        result["narrativePreview"] = narrative[:240]
        result["narrativeTruncated"] = len(narrative) > 240
    return result


def search_complaints(database, *, page=1, page_size=20, **filters):
    query = complaint_query(**filters)
    total = database.complaints.count_documents(query, maxTimeMS=5000)
    # ODI provides a deterministic tie-break for equal/null receipt dates.
    with database.complaints.find(query, LIST_FIELDS, sort=[("receivedDate", -1), ("_id", -1)],
                                  skip=(page - 1) * page_size, limit=page_size, max_time_ms=5000) as cursor:
        items = [public_complaint(document) for document in cursor]
    return {"items": items, "pagination": {
        "page": page, "pageSize": page_size, "total": total,
        "totalPages": (total + page_size - 1) // page_size,
    }, "interpretation": INTERPRETATION}


def get_complaint(database, odi_number):
    document = database.complaints.find_one({"_id": odi_number}, DETAIL_FIELDS, max_time_ms=5000)
    if document is None:
        return None
    return {"complaint": public_complaint(document, detail=True), "interpretation": INTERPRETATION}
