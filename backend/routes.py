"""Read-only research endpoints, validation, and request-scoped SQL connections."""

from flask import Blueprint, abort, current_app, g, jsonify, request
from datetime import date, datetime, time, timedelta, timezone
from psycopg import Error as PostgresError
from pymongo.errors import PyMongoError

from backend.services.research import safety_profile, search_vehicles
from backend.services.evidence import list_complaints, list_reference_records, complaint_insights
from etl.source import normalized
from project_config import AppDatabaseNotConfigured, mongo_database

api = Blueprint("api", __name__, url_prefix="/api")


def pg():
    if "postgres" not in g:
        connection = current_app.config["PG_CONNECT"]()
        connection.read_only = True
        g.postgres = connection
    return g.postgres


def close_postgres(error=None):
    connection = g.pop("postgres", None)
    if connection is not None:
        connection.close()


def query_fields(allowed):
    for field in request.args:
        if field not in allowed:
            abort(400, description=f"Unknown query parameter: {field}")
        if len(request.args.getlist(field)) != 1:
            abort(400, description=f"Provide {field} only once")


def number(field, *, required=False, default=None, minimum=1, maximum=2147483647):
    value = request.args.get(field)
    if value is None:
        if required:
            abort(400, description=f"{field} is required")
        return default
    value = value.strip()
    if not value.isascii() or not value.isdecimal() or len(value) > 10:
        abort(400, description=f"{field} must be an integer")
    parsed = int(value)
    if not minimum <= parsed <= maximum:
        abort(400, description=f"{field} must be between {minimum} and {maximum}")
    return parsed


def text(field, *, required=False, maximum=256):
    value = request.args.get(field)
    if value is None:
        if required:
            abort(400, description=f"{field} is required")
        return None
    value = normalized(value)
    if not value or len(value) > maximum or not value.isprintable():
        abort(400, description=f"{field} must contain 1 to {maximum} printable characters")
    return value


@api.get("/health")
def health():
    states = {"postgresql": "ok", "mongodb": "ok"}
    try:
        pg().execute("SELECT 1").fetchone()
    except (PostgresError, AppDatabaseNotConfigured):
        states["postgresql"] = "unavailable"
    try:
        current_app.extensions["mongo_client"].admin.command("ping")
    except PyMongoError:
        states["mongodb"] = "unavailable"
    okay = all(value == "ok" for value in states.values())
    return jsonify({"status": "ok" if okay else "unavailable", "databases": states}), 200 if okay else 503


@api.get("/datasets")
def datasets():
    query_fields(set())
    rows = pg().execute("SELECT dataset_name,completed_at,records_read FROM dataset_snapshot ORDER BY dataset_name").fetchall()
    return jsonify({"source": "NHTSA", "datasets": [{"name": name, "importedAt": when.isoformat(), "recordsRead": count}
                                                        for name, when, count in rows]})


@api.get("/vehicles/search")
def vehicles():
    query_fields({"year", "make", "model", "page", "pageSize"})
    filters = {
        "year": number("year", minimum=1900, maximum=2100),
        "make": text("make", maximum=100), "model": text("model"),
        "page": number("page", default=1),
        "page_size": number("pageSize", default=20, maximum=100),
    }
    return jsonify(search_vehicles(pg(), **filters))


@api.get("/vehicles/safety-profile")
def profile():
    query_fields({"year", "make", "model"})
    year = number("year", required=True, minimum=1900, maximum=2100)
    make, model = text("make", required=True, maximum=100), text("model", required=True)
    result = safety_profile(pg(), mongo_database(current_app.extensions["mongo_client"]), make, model, year)
    if result is None:
        abort(404, description="No matching vehicle in the imported catalogue")
    return jsonify(result)


def existing_vehicle(model_year_id):
    if not 1 <= model_year_id <= 9223372036854775807:
        abort(400, description="Invalid vehicle identifier")
    row = pg().execute("SELECT model_year_id FROM vehicle_catalogue WHERE model_year_id=%s",
                       (model_year_id,)).fetchone()
    if row is None:
        abort(404, description="No matching vehicle in the imported catalogue")


def date_filter(field):
    value = request.args.get(field)
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return datetime.combine(parsed, time.min, tzinfo=timezone.utc)
    except (ValueError, TypeError):
        abort(400, description=f"{field} must be a date in YYYY-MM-DD format")


@api.get("/vehicles/<int:model_year_id>/recalls")
@api.get("/vehicles/<int:model_year_id>/investigations")
def reference_records(model_year_id):
    query_fields({"page", "pageSize"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    existing_vehicle(model_year_id)
    kind = "recalls" if request.path.endswith("/recalls") else "investigations"
    return jsonify(list_reference_records(pg(), model_year_id, kind, page, size))


@api.get("/vehicles/<int:model_year_id>/complaints")
def complaints(model_year_id):
    query_fields({"page", "pageSize", "component", "q", "fromDate", "toDate"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    component, search = text("component", maximum=200), text("q", maximum=120)
    start, end = date_filter("fromDate"), date_filter("toDate")
    if start and end and start > end:
        abort(400, description="fromDate must not be later than toDate")
    existing_vehicle(model_year_id)
    exclusive_end = None if end and end.date() == date.max else (end + timedelta(days=1) if end else None)
    return jsonify(list_complaints(mongo_database(current_app.extensions["mongo_client"]),
                                  model_year_id, page, size, component, search, start, exclusive_end))


@api.get("/vehicles/<int:model_year_id>/insights")
def insights(model_year_id):
    query_fields(set())
    existing_vehicle(model_year_id)
    return jsonify(complaint_insights(mongo_database(current_app.extensions["mongo_client"]), model_year_id))
