"""Small owner-scoped fleet recall and work-order workflow."""

from flask import Blueprint, abort, jsonify, url_for
from psycopg.errors import UniqueViolation

from backend.auth import current_user, json_fields, requires_roles
from backend.cases import clean_text, identifier, pg
from backend.routes import number, query_fields

fleets = Blueprint("fleets", __name__, url_prefix="/api/fleets")


def fleet_row(row):
    return {"fleetId": row[0], "name": row[1], "createdAt": row[2].isoformat()}


def get_fleet(fleet_id, *, lock=False):
    row = pg().execute("SELECT fleet_id,name,created_at FROM fleet WHERE fleet_id=%s AND owner_id=%s" +
                       (" FOR UPDATE" if lock else ""), (identifier(fleet_id), current_user()["userId"])).fetchone()
    if row is None:
        abort(404, description="Fleet not found")
    return fleet_row(row)


def commit_unique():
    try:
        pg().commit()
    except UniqueViolation:
        pg().rollback()
        abort(409, description="That record already exists")


@fleets.get("")
@requires_roles()
def listing():
    query_fields({"page", "pageSize"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    user_id = current_user()["userId"]
    total = pg().execute("SELECT count(*) FROM fleet WHERE owner_id=%s", (user_id,)).fetchone()[0]
    rows = pg().execute("""SELECT fleet_id,name,created_at FROM fleet WHERE owner_id=%s
        ORDER BY created_at DESC,fleet_id DESC LIMIT %s OFFSET %s""", (user_id, size, (page-1)*size)).fetchall()
    return jsonify({"items": [fleet_row(row) for row in rows],
                    "pagination": {"page": page, "pageSize": size, "total": total,
                                   "totalPages": (total + size - 1) // size}})


@fleets.post("")
@requires_roles()
def create():
    name = clean_text(json_fields({"name"})["name"], "name", 120)
    try:
        row = pg().execute("INSERT INTO fleet(owner_id,name) VALUES (%s,%s) RETURNING fleet_id,name,created_at",
                           (current_user()["userId"], name)).fetchone()
        commit_unique()
    except UniqueViolation:
        pg().rollback()
        abort(409, description="A fleet with that name already exists")
    response = jsonify({"fleet": fleet_row(row)})
    response.status_code = 201
    response.headers["Location"] = url_for("fleets.detail", fleet_id=row[0])
    return response


@fleets.get("/<int:fleet_id>")
@requires_roles()
def detail(fleet_id):
    query_fields({"page", "pageSize"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    fleet = get_fleet(fleet_id)
    total = pg().execute("SELECT count(*) FROM fleet_vehicle WHERE fleet_id=%s", (fleet_id,)).fetchone()[0]
    rows = pg().execute("""SELECT fv.fleet_vehicle_id,fv.model_year_id,fv.label,fv.created_at,
        v.make,v.model,v.year FROM fleet_vehicle fv JOIN vehicle_catalogue v USING(model_year_id)
        WHERE fv.fleet_id=%s ORDER BY fv.fleet_vehicle_id LIMIT %s OFFSET %s""",
        (fleet_id, size, (page-1)*size)).fetchall()
    vehicles = [{"fleetVehicleId": row[0], "modelYearId": row[1], "label": row[2],
                 "createdAt": row[3].isoformat(), "vehicle": {"make": row[4], "model": row[5], "year": row[6]}}
                for row in rows]
    return jsonify({"fleet": fleet, "vehicles": vehicles, "vehiclePagination":
                    {"page": page, "pageSize": size, "total": total, "totalPages": (total + size - 1) // size}})


@fleets.patch("/<int:fleet_id>")
@requires_roles()
def rename(fleet_id):
    name = clean_text(json_fields({"name"})["name"], "name", 120)
    get_fleet(fleet_id, lock=True)
    try:
        pg().execute("UPDATE fleet SET name=%s WHERE fleet_id=%s AND owner_id=%s",
                     (name, fleet_id, current_user()["userId"]))
        commit_unique()
    except UniqueViolation:
        pg().rollback()
        abort(409, description="A fleet with that name already exists")
    return jsonify({"fleet": get_fleet(fleet_id)})


@fleets.delete("/<int:fleet_id>")
@requires_roles()
def remove(fleet_id):
    query_fields(set())
    get_fleet(fleet_id, lock=True)
    pg().execute("DELETE FROM fleet WHERE fleet_id=%s AND owner_id=%s", (fleet_id, current_user()["userId"]))
    pg().commit()
    return "", 204


@fleets.post("/<int:fleet_id>/vehicles")
@requires_roles()
def add_vehicle(fleet_id):
    body = json_fields({"modelYearId", "label"})
    vehicle_id, label = identifier(body["modelYearId"]), clean_text(body["label"], "label", 120)
    get_fleet(fleet_id, lock=True)
    try:
        row = pg().execute("""INSERT INTO fleet_vehicle(fleet_id,model_year_id,label)
            SELECT %s,model_year_id,%s FROM vehicle_catalogue WHERE model_year_id=%s
            RETURNING fleet_vehicle_id""", (fleet_id, label, vehicle_id)).fetchone()
        if row is None:
            abort(404, description="Vehicle not found")
        commit_unique()
    except UniqueViolation:
        pg().rollback()
        abort(409, description="This fleet already has a vehicle with that label")
    return jsonify({"fleetVehicleId": row[0]}), 201


@fleets.delete("/<int:fleet_id>/vehicles/<int:vehicle_id>")
@requires_roles()
def remove_vehicle(fleet_id, vehicle_id):
    query_fields(set())
    get_fleet(fleet_id, lock=True)
    row = pg().execute("DELETE FROM fleet_vehicle WHERE fleet_id=%s AND fleet_vehicle_id=%s RETURNING fleet_vehicle_id",
                       (fleet_id, identifier(vehicle_id))).fetchone()
    if row is None:
        abort(404, description="Fleet vehicle not found")
    pg().commit()
    return "", 204


@fleets.get("/<int:fleet_id>/matches")
@requires_roles()
def matches(fleet_id):
    query_fields({"page", "pageSize"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    get_fleet(fleet_id)
    params = (fleet_id, current_user()["userId"])
    total = pg().execute("SELECT count(*) FROM fleet_recall_matches WHERE fleet_id=%s AND owner_id=%s", params).fetchone()[0]
    rows = pg().execute("""SELECT fleet_vehicle_id,label,model_year_id,make,model,year,recall_id,
        campaign_number,work_order_id,work_order_status,work_order_notes FROM fleet_recall_matches
        WHERE fleet_id=%s AND owner_id=%s ORDER BY fleet_vehicle_id,campaign_number LIMIT %s OFFSET %s""",
        (*params, size, (page-1)*size)).fetchall()
    names = ("fleetVehicleId", "label", "modelYearId", "make", "model", "year", "recallId",
             "campaignNumber", "workOrderId", "workOrderStatus", "workOrderNotes")
    return jsonify({"items": [dict(zip(names, row)) for row in rows],
                    "pagination": {"page": page, "pageSize": size, "total": total,
                                   "totalPages": (total + size - 1) // size},
                    "interpretation": "Matches use model year, make and model, not an individual VIN."})


@fleets.post("/<int:fleet_id>/work-orders")
@requires_roles()
def create_order(fleet_id):
    body = json_fields({"fleetVehicleId", "recallId"}, {"notes"})
    vehicle_id, recall_id = identifier(body["fleetVehicleId"]), identifier(body["recallId"])
    notes = body.get("notes", "")
    if notes:
        notes = clean_text(notes, "notes", 2000, multiline=True)
    elif not isinstance(notes, str):
        abort(400, description="notes must be text")
    get_fleet(fleet_id, lock=True)
    try:
        row = pg().execute("""INSERT INTO work_order(fleet_vehicle_id,model_year_id,recall_id,notes)
            SELECT fv.fleet_vehicle_id,fv.model_year_id,rv.recall_id,%s
            FROM fleet_vehicle fv JOIN recall_vehicle rv ON rv.model_year_id=fv.model_year_id
            WHERE fv.fleet_id=%s AND fv.fleet_vehicle_id=%s AND rv.recall_id=%s
            RETURNING work_order_id""", (notes, fleet_id, vehicle_id, recall_id)).fetchone()
        if row is None:
            abort(404, description="Matching fleet vehicle and recall not found")
        commit_unique()
    except UniqueViolation:
        pg().rollback()
        abort(409, description="A work order already exists for that vehicle and recall")
    return jsonify({"workOrderId": row[0]}), 201


@fleets.patch("/<int:fleet_id>/work-orders/<int:order_id>")
@requires_roles()
def edit_order(fleet_id, order_id):
    body = json_fields({"status"}, {"notes"})
    status = body["status"]
    if status not in ("OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"):
        abort(400, description="Invalid work-order status")
    notes = body.get("notes")
    if notes is not None:
        if not isinstance(notes, str):
            abort(400, description="notes must be text")
        notes = clean_text(notes, "notes", 2000, multiline=True) if notes.strip() else ""
    get_fleet(fleet_id, lock=True)
    row = pg().execute("""UPDATE work_order w SET status=%s,notes=COALESCE(%s,w.notes),
        completed_at=CASE WHEN %s='COMPLETED' THEN COALESCE(w.completed_at,now()) ELSE NULL END
        FROM fleet_vehicle fv WHERE w.fleet_vehicle_id=fv.fleet_vehicle_id AND fv.fleet_id=%s
        AND w.work_order_id=%s RETURNING w.work_order_id""",
        (status, notes, status, fleet_id, identifier(order_id))).fetchone()
    if row is None:
        abort(404, description="Work order not found")
    pg().commit()
    return jsonify({"workOrderId": row[0], "status": status})


@fleets.delete("/<int:fleet_id>/work-orders/<int:order_id>")
@requires_roles()
def remove_order(fleet_id, order_id):
    query_fields(set())
    get_fleet(fleet_id, lock=True)
    row = pg().execute("""DELETE FROM work_order w USING fleet_vehicle fv
        WHERE w.fleet_vehicle_id=fv.fleet_vehicle_id AND fv.fleet_id=%s AND w.work_order_id=%s
        RETURNING w.work_order_id""", (fleet_id, identifier(order_id))).fetchone()
    if row is None:
        abort(404, description="Work order not found")
    pg().commit()
    return "", 204
