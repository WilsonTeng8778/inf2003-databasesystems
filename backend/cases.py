"""Role- and owner-scoped analyst cases with MongoDB detail CRUD."""

import re
from datetime import datetime, timezone
from uuid import uuid4

from flask import Blueprint, abort, current_app, g, jsonify, url_for

from backend.auth import current_user, json_fields, requires_roles
from backend.routes import number, query_fields
from backend.services.cases import authorized_case, list_cases, pending_count, public_details, reconcile
from project_config import mongo_database

cases = Blueprint("cases", __name__, url_prefix="/api/cases")
case_admin = Blueprint("case_admin", __name__, url_prefix="/api/admin")


def pg():
    if "workflow_postgres" not in g:
        g.workflow_postgres = current_app.config["WORKFLOW_PG_CONNECT"]()
    return g.workflow_postgres


def mongo():
    return mongo_database(current_app.extensions["mongo_client"])


def identifier(value):
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        abort(400, description="Identifier must be a positive integer")
    return value


def clean_text(value, field, maximum, *, multiline=False):
    if not isinstance(value, str):
        abort(400, description=f"{field} must be text")
    value = value.strip()
    printable = value.replace("\n", "").replace("\r", "") if multiline else value
    if not value or len(value) > maximum or not printable.isprintable():
        abort(400, description=f"{field} must contain 1 to {maximum} printable characters")
    return value


def string_list(value, field, limit=30, maximum=80):
    if not isinstance(value, list) or len(value) > limit:
        abort(400, description=f"{field} must be a list of at most {limit} items")
    result = [clean_text(item, field, maximum) for item in value]
    if len(set(result)) != len(result):
        abort(400, description=f"{field} must not contain duplicates")
    return result


def get_case(case_id, *, lock=False):
    result = authorized_case(pg(), identifier(case_id), current_user(), lock=lock)
    if result is None:
        abort(404, description="Case not found")
    return result


def ready_document(case_id):
    if pending_count(pg(), case_id):
        abort(409, description="Case details are awaiting synchronization; retry synchronization first")
    document = mongo().case_details.find_one({"caseId": case_id}, {"_id": 0})
    if document is None:
        abort(409, description="Case details are missing; ask an administrator to investigate")
    return document


@cases.get("")
@requires_roles("ANALYST", "ADMIN")
def listing():
    query_fields({"page", "pageSize"})
    return jsonify(list_cases(pg(), current_user(), number("page", default=1),
                              number("pageSize", default=20, maximum=100)))


@cases.post("")
@requires_roles("ANALYST", "ADMIN")
def create():
    body = json_fields({"modelYearId", "title"}, {"priority"})
    vehicle_id = identifier(body["modelYearId"])
    title = clean_text(body["title"], "title", 200)
    priority = body.get("priority", "MEDIUM")
    if priority not in ("LOW", "MEDIUM", "HIGH"):
        abort(400, description="priority must be LOW, MEDIUM or HIGH")
    user_id = current_user()["userId"]
    row = pg().execute("""INSERT INTO analysis_case(title,model_year_id,created_by,assigned_to,priority)
        SELECT %s,model_year_id,%s,%s,%s FROM vehicle_catalogue WHERE model_year_id=%s RETURNING case_id""",
        (title, user_id, user_id, priority, vehicle_id)).fetchone()
    if row is None:
        abort(404, description="Vehicle not found")
    case_id = row[0]
    pg().execute("INSERT INTO case_sync_outbox(case_id,operation) VALUES (%s,'CREATE')", (case_id,))
    pg().commit()
    sync = reconcile(pg(), mongo(), case_id)
    result = get_case(case_id)
    result["syncStatus"] = "pending" if sync["pending"] else "ready"
    response = jsonify({"case": result, "sync": sync})
    response.status_code = 202 if sync["pending"] else 201
    response.headers["Location"] = url_for("cases.detail", case_id=case_id)
    return response


@cases.get("/<int:case_id>")
@requires_roles("ANALYST", "ADMIN")
def detail(case_id):
    query_fields(set())
    result = get_case(case_id)
    pending = pending_count(pg(), case_id)
    document = None if pending else mongo().case_details.find_one({"caseId": case_id}, {"_id": 0})
    result["syncStatus"] = "pending" if pending else ("ready" if document is not None else "missing")
    history = pg().execute("""SELECT old_status,new_status,changed_at FROM case_status_history
        WHERE case_id=%s ORDER BY history_id""", (case_id,)).fetchall()
    return jsonify({"case": result, "details": public_details(document),
                    "history": [{"from": old, "to": new, "changedAt": when.isoformat()}
                                for old, new, when in history]})


@cases.get("/<int:case_id>/complaints")
@requires_roles("ANALYST", "ADMIN")
def linked_complaints(case_id):
    query_fields(set())
    current = get_case(case_id)
    document = ready_document(case_id)
    identifiers = document["linkedComplaints"]
    records = list(mongo().complaints.find({"_id": {"$in": identifiers}, "modelYearId": current["modelYearId"]},
        {"_id": 1, "odiNumber": 1, "components": 1, "receivedDate": 1, "narrative": 1}))
    found = {item["_id"] for item in records}
    items = [{"odiNumber": item.get("odiNumber", item["_id"]), "components": item.get("components", []),
              "receivedDate": item["receivedDate"].isoformat() if item.get("receivedDate") else None,
              "narrative": item.get("narrative", "")} for item in records]
    return jsonify({"items": items, "missingIds": [item for item in identifiers if item not in found]})


@cases.patch("/<int:case_id>")
@requires_roles("ANALYST", "ADMIN")
def edit(case_id):
    body = json_fields(set(), {"title", "priority", "status"})
    if not body:
        abort(400, description="Provide at least one field to change")
    current = get_case(case_id, lock=True)
    title = clean_text(body["title"], "title", 200) if "title" in body else current["title"]
    priority, status = body.get("priority", current["priority"]), body.get("status", current["status"])
    if priority not in ("LOW", "MEDIUM", "HIGH") or status not in ("OPEN", "REVIEWING", "CLOSED"):
        abort(400, description="Invalid priority or status")
    pg().execute("""UPDATE analysis_case SET title=%s,priority=%s,status=%s,
        closed_at=CASE WHEN %s='CLOSED' THEN COALESCE(closed_at,now()) ELSE NULL END
        WHERE case_id=%s""", (title, priority, status, status, case_id))
    pg().commit()
    return jsonify({"case": get_case(case_id)})


@cases.delete("/<int:case_id>")
@requires_roles("ANALYST", "ADMIN")
def remove(case_id):
    query_fields(set())
    get_case(case_id, lock=True)
    pg().execute("INSERT INTO case_sync_outbox(case_id,operation) VALUES (%s,'DELETE') ON CONFLICT DO NOTHING", (case_id,))
    pg().execute("DELETE FROM analysis_case WHERE case_id=%s", (case_id,))
    pg().commit()
    sync = reconcile(pg(), mongo(), case_id)
    return (jsonify({"sync": sync}), 202) if sync["pending"] else ("", 204)


@cases.post("/<int:case_id>/sync")
@requires_roles("ANALYST", "ADMIN")
def sync_one(case_id):
    json_fields(set())
    get_case(case_id)
    return jsonify({"sync": reconcile(pg(), mongo(), case_id)})


@case_admin.post("/case-sync")
@requires_roles("ADMIN")
def sync_all():
    json_fields(set())
    return jsonify({"sync": reconcile(pg(), mongo())})


@cases.put("/<int:case_id>/links")
@requires_roles("ANALYST", "ADMIN")
def links(case_id):
    body = json_fields({"complaintIds"})
    ids = string_list(body["complaintIds"], "complaintIds", limit=100, maximum=40)
    if any(not value.isascii() or not value.isdecimal() for value in ids):
        abort(400, description="Complaint IDs must be numeric ODI identifiers")
    current = get_case(case_id, lock=True)
    ready_document(case_id)
    found = {doc["_id"] for doc in mongo().complaints.find(
        {"_id": {"$in": ids}, "modelYearId": current["modelYearId"]}, {"_id": 1})}
    if found != set(ids):
        abort(400, description="Every linked complaint must belong to this case's vehicle")
    mongo().case_details.update_one({"caseId": case_id}, {"$set": {"linkedComplaints": ids}})
    pg().commit()
    return jsonify({"details": public_details(ready_document(case_id))})


@cases.put("/<int:case_id>/classification")
@requires_roles("ANALYST", "ADMIN")
def classification(case_id):
    body = json_fields({"tags", "suspectedComponents"})
    tags = string_list(body["tags"], "tags")
    components = string_list(body["suspectedComponents"], "suspectedComponents")
    get_case(case_id, lock=True)
    ready_document(case_id)
    mongo().case_details.update_one({"caseId": case_id}, {"$set": {"tags": tags, "suspectedComponents": components}})
    pg().commit()
    return jsonify({"details": public_details(ready_document(case_id))})


@cases.route("/<int:case_id>/<kind>", methods=["POST"])
@cases.route("/<int:case_id>/<kind>/<entry_id>", methods=["PATCH", "DELETE"])
@requires_roles("ANALYST", "ADMIN")
def entry(case_id, kind, entry_id=None):
    if kind not in ("notes", "findings"):
        abort(404)
    id_key, text_key = ("noteId", "text") if kind == "notes" else ("findingId", "observation")
    if entry_id is not None and not re.fullmatch(r"[0-9a-f]{32}", entry_id):
        abort(400, description="Invalid entry identifier")
    from flask import request
    if request.method == "DELETE":
        query_fields(set())
        body = None
    else:
        body = json_fields({text_key})
        value = clean_text(body[text_key], text_key, 2000, multiline=True)
    get_case(case_id, lock=True)
    ready_document(case_id)
    collection = mongo().case_details
    if request.method == "POST":
        item = {id_key: uuid4().hex, "authorId": current_user()["userId"],
                "createdAt": datetime.now(timezone.utc), text_key: value}
        collection.update_one({"caseId": case_id}, {"$push": {kind: item}})
    elif request.method == "PATCH":
        result = collection.update_one({"caseId": case_id, f"{kind}.{id_key}": entry_id},
                                       {"$set": {f"{kind}.$.{text_key}": value}})
        if not result.matched_count:
            abort(404, description="Entry not found")
    else:
        result = collection.update_one({"caseId": case_id, f"{kind}.{id_key}": entry_id},
                                       {"$pull": {kind: {id_key: entry_id}}})
        if not result.matched_count:
            abort(404, description="Entry not found")
    pg().commit()
    return jsonify({"details": public_details(ready_document(case_id))}), 201 if entry_id is None else 200
