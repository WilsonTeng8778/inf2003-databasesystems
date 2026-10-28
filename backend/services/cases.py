"""Case persistence and an idempotent PostgreSQL-to-MongoDB outbox."""

from pymongo.errors import PyMongoError


CASE_QUERY = """SELECT c.case_id,c.title,c.model_year_id,c.created_by,c.assigned_to,
    c.priority,c.status,c.created_at,c.closed_at,v.make,v.model,v.year
    FROM analysis_case c JOIN vehicle_catalogue v USING(model_year_id)"""


def case_dict(row):
    if row is None:
        return None
    identifier, title, vehicle_id, creator, assigned, priority, status, created, closed, make, model, year = row
    return {"caseId": identifier, "title": title, "modelYearId": vehicle_id,
            "createdBy": creator, "assignedTo": assigned, "priority": priority, "status": status,
            "createdAt": created.isoformat(), "closedAt": closed.isoformat() if closed else None,
            "vehicle": {"make": make, "model": model, "year": year}}


def authorized_case(connection, case_id, user, *, lock=False):
    row = connection.execute(CASE_QUERY + """ WHERE c.case_id=%s
        AND (%s OR c.created_by=%s OR c.assigned_to=%s)""" + (" FOR UPDATE OF c" if lock else ""),
        (case_id, user["role"] == "ADMIN", user["userId"], user["userId"])).fetchone()
    return case_dict(row)


def list_cases(connection, user, page, size):
    where = " WHERE (%s OR c.created_by=%s OR c.assigned_to=%s)"
    params = (user["role"] == "ADMIN", user["userId"], user["userId"])
    total = connection.execute("SELECT count(*) FROM analysis_case c" + where, params).fetchone()[0]
    rows = connection.execute(CASE_QUERY + where +
        " ORDER BY c.created_at DESC,c.case_id DESC LIMIT %s OFFSET %s",
        (*params, size, (page - 1) * size)).fetchall()
    return {"items": [case_dict(row) for row in rows],
            "pagination": {"page": page, "pageSize": size, "total": total,
                           "totalPages": (total + size - 1) // size}}


def pending_count(connection, case_id=None):
    where = " WHERE completed_at IS NULL"
    params = ()
    if case_id is not None:
        where += " AND case_id=%s"
        params = (case_id,)
    return connection.execute("SELECT count(*) FROM case_sync_outbox" + where, params).fetchone()[0]


def reconcile(connection, database, case_id=None, limit=100):
    """Apply oldest pending job per case. Each Mongo operation can safely repeat.

    The SQL transaction locks the job while Mongo is changed. If SQL commit fails
    after a Mongo write, the job remains pending and replay is idempotent. A later
    DELETE cannot overtake a pending CREATE for the same case.
    """
    processed, unavailable = 0, False
    while processed < limit:
        condition, params = (" AND o.case_id=%s", (case_id,)) if case_id is not None else ("", ())
        row = connection.execute("""SELECT o.job_id,o.case_id,o.operation FROM case_sync_outbox o
            WHERE o.completed_at IS NULL""" + condition + """
            AND NOT EXISTS (SELECT 1 FROM case_sync_outbox earlier
                WHERE earlier.case_id=o.case_id AND earlier.job_id<o.job_id AND earlier.completed_at IS NULL)
            ORDER BY o.job_id LIMIT 1 FOR UPDATE OF o SKIP LOCKED""", params).fetchone()
        if row is None:
            connection.commit()
            break
        job_id, identifier, operation = row
        try:
            if operation == "CREATE":
                database.case_details.update_one({"caseId": identifier}, {"$setOnInsert": {
                    "caseId": identifier, "linkedComplaints": [], "suspectedComponents": [],
                    "findings": [], "notes": [], "tags": []}}, upsert=True)
            else:
                database.case_details.delete_one({"caseId": identifier})
            connection.execute("UPDATE case_sync_outbox SET completed_at=now() WHERE job_id=%s", (job_id,))
            connection.commit()
            processed += 1
        except PyMongoError:
            connection.rollback()
            unavailable = True
            break
    remaining = pending_count(connection, case_id)
    connection.commit()
    return {"processed": processed, "pending": remaining, "databaseUnavailable": unavailable}


def public_details(document):
    if document is None:
        return None
    result = {key: document.get(key, []) for key in
              ("linkedComplaints", "suspectedComponents", "findings", "notes", "tags")}
    for kind in ("findings", "notes"):
        result[kind] = [{**item, "createdAt": item["createdAt"].isoformat()}
                        for item in result[kind]]
    return result
