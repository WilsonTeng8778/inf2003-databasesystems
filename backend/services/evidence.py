"""Public reference records and transparent complaint aggregations."""


def pagination(page, size, total):
    return {"page": page, "pageSize": size, "total": total,
            "totalPages": (total + size - 1) // size}


def iso(value):
    return value.isoformat() if value is not None else None


REFERENCE = {
    "recalls": ("vehicle_recall_details", "report_date", (
        "recall_id", "campaign_number", "report_date", "summary", "consequence", "remedy",
        "potentially_affected", "do_not_drive", "park_outside"), (
        "recallId", "campaignNumber", "reportDate", "summary", "consequence", "remedy",
        "potentiallyAffected", "doNotDrive", "parkOutside")),
    "investigations": ("vehicle_investigation_details", "opened_date", (
        "investigation_id", "investigation_number", "investigation_type", "subject", "summary",
        "opened_date", "closed_date", "status"), (
        "investigationId", "investigationNumber", "investigationType", "subject", "summary",
        "openedDate", "closedDate", "status")),
}


def list_reference_records(connection, model_year_id, kind, page, size):
    view, sort, columns, names = REFERENCE[kind]  # Names come only from the fixed map.
    total = connection.execute(f"SELECT count(*) FROM {view} WHERE model_year_id=%s",
                               (model_year_id,)).fetchone()[0]
    rows = connection.execute(
        f"SELECT {','.join(columns)} FROM {view} WHERE model_year_id=%s "
        f"ORDER BY {sort} DESC NULLS LAST,{columns[0]} DESC LIMIT %s OFFSET %s",
        (model_year_id, size, (page - 1) * size)).fetchall()
    items = []
    for row in rows:
        item = dict(zip(names, row))
        for key in ("reportDate", "openedDate", "closedDate"):
            if key in item:
                item[key] = iso(item[key])
        items.append(item)
    return {"items": items, "pagination": pagination(page, size, total)}


def list_complaints(database, model_year_id, page, size, component=None, search=None, start=None, end=None):
    query = {"modelYearId": model_year_id}
    if component:
        query["components"] = component
    if search:
        query["$text"] = {"$search": search}
    if start or end:
        query["receivedDate"] = {}
        if start:
            query["receivedDate"]["$gte"] = start
        if end:
            query["receivedDate"]["$lt"] = end
    collection = database.complaints
    total = collection.count_documents(query, maxTimeMS=5000)
    cursor = (collection.find(query, {"_id": 1, "odiNumber": 1, "components": 1, "incident": 1,
                                      "receivedDate": 1, "incidentDate": 1, "narrative": 1})
              .sort([("receivedDate", -1), ("_id", 1)]).skip((page - 1) * size).limit(size).max_time_ms(5000))
    items = []
    for item in cursor:
        items.append({"odiNumber": item.get("odiNumber", item["_id"]),
                      "components": item.get("components", []), "incident": item.get("incident", {}),
                      "receivedDate": iso(item.get("receivedDate")),
                      "incidentDate": iso(item.get("incidentDate")), "narrative": item.get("narrative", "")})
    return {"items": items, "pagination": pagination(page, size, total),
            "interpretation": "Consumer complaints are allegations, not confirmed defects."}


def complaint_insights(database, model_year_id):
    query = {"modelYearId": model_year_id}
    collection = database.complaints
    total = collection.count_documents(query, maxTimeMS=5000)
    components = list(collection.aggregate([
        {"$match": query}, {"$unwind": "$components"},
        {"$group": {"_id": "$components", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}}, {"$limit": 10},
    ], maxTimeMS=5000))
    monthly = list(collection.aggregate([
        {"$match": {**query, "receivedDate": {"$ne": None}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$receivedDate"}},
                    "count": {"$sum": 1}}}, {"$sort": {"_id": 1}},
    ], maxTimeMS=5000))
    return {"totalComplaints": total, "components": components, "monthly": monthly,
            "interpretation": "Complaints are allegations. Component totals can overlap; dates are receipt dates."}
