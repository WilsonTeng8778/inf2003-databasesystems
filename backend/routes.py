"""Read-only research endpoints, validation, and request-scoped SQL connections."""

import re
from datetime import date

from flask import Blueprint, abort, current_app, g, jsonify, request
from psycopg import Error as PostgresError
from pymongo.errors import PyMongoError

from backend.services.research import safety_profile, search_vehicles
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
    if not value.isascii() or not value.isdecimal() or len(value) > max(10, len(str(maximum))):
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


def boolean(field):
    value = request.args.get(field)
    if value is None:
        return None
    value = value.strip().lower()
    if value not in {"true", "false"}:
        abort(400, description=f"{field} must be true or false")
    return value == "true"


def calendar_date(field):
    value = request.args.get(field)
    if value is None:
        return None
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    abort(400, description=f"{field} must be a valid YYYY-MM-DD date")


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
