"""Read-only vehicle queries. User-provided values use SQL parameters."""

from etl.source import normalized


def safety_profile(connection, database, make, model, year):
    vehicle = connection.execute("""SELECT model_year_id,make,model,year,recall_count,investigation_count
        FROM vehicle_safety_summary WHERE make=%s AND model=%s AND year=%s""",
        (normalized(make), normalized(model), year)).fetchone()
    if not vehicle:
        return None
    identifier, make, model, year, recalls, investigations = vehicle
    query = {"modelYearId": identifier}
    return {
        "modelYearId": identifier, "make": make, "model": model, "year": year,
        "officialRecallCampaigns": recalls, "officialInvestigations": investigations,
        "consumerComplaints": database.complaints.count_documents(query),
        "topComplaintComponents": list(database.complaints.aggregate([
            {"$match": query}, {"$unwind": "$components"},
            {"$group": {"_id": "$components", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}}, {"$limit": 10},
        ], maxTimeMS=5000)),
        "interpretation": "Complaints are allegations; matches are by model year/make/model, not VIN.",
    }


def search_vehicles(connection, *, year=None, make=None, model=None, page=1, page_size=20):
    conditions, parameters = [], []
    for column, value in [("year", year), ("make", make), ("model", model)]:
        if value is not None:
            # Column names are fixed constants above; values are never SQL text.
            conditions.append(f"{column}=%s")
            parameters.append(value)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    total = connection.execute("SELECT count(*) FROM vehicle_catalogue" + where, parameters).fetchone()[0]
    rows = connection.execute("""SELECT model_year_id,make,model,year FROM vehicle_catalogue""" + where +
        " ORDER BY make,model,year,model_year_id LIMIT %s OFFSET %s",
        [*parameters, page_size, (page - 1) * page_size]).fetchall()
    return {
        "items": [{"modelYearId": identifier, "make": make, "model": model, "year": year}
                  for identifier, make, model, year in rows],
        "pagination": {"page": page, "pageSize": page_size, "total": total,
                       "totalPages": (total + page_size - 1) // page_size},
    }
