"""Authenticated personal saved vehicles. Admins have no ownership override."""

from flask import Blueprint, abort, current_app, g, jsonify, url_for

from backend.auth import current_user, json_fields, requires_roles
from backend.routes import number, query_fields
from backend.services.saved_vehicles import AlreadySaved, PostgresSavedVehicleStore, VehicleNotFound

saved = Blueprint("saved", __name__, url_prefix="/api/saved-vehicles")


def store():
    if "saved_vehicle_store" not in g:
        factory = current_app.config.get("SAVED_VEHICLE_STORE_FACTORY")
        if factory:
            g.saved_vehicle_store = factory()
        else:
            g.workflow_postgres = current_app.config["WORKFLOW_PG_CONNECT"]()
            g.saved_vehicle_store = PostgresSavedVehicleStore(g.workflow_postgres)
    return g.saved_vehicle_store


def close_workflow_postgres(error=None):
    connection = g.pop("workflow_postgres", None)
    if connection is not None:
        connection.close()


def identifier(value):
    if type(value) is not int or not 1 <= value <= 9223372036854775807:
        abort(400, description="Vehicle identifiers must be positive integers")
    return value


def nickname(value):
    if not isinstance(value, str):
        abort(400, description="nickname must be a string")
    value = value.strip()
    if len(value) > 100 or (value and not value.isprintable()):
        abort(400, description="nickname must contain at most 100 printable characters")
    return value


@saved.get("")
@requires_roles()
def listing():
    query_fields({"page", "pageSize"})
    page, size = number("page", default=1), number("pageSize", default=20, maximum=100)
    return jsonify(store().list(current_user()["userId"], page, size))


@saved.post("")
@requires_roles()
def create():
    body = json_fields({"modelYearId"}, {"nickname"})
    vehicle_id, label = identifier(body["modelYearId"]), nickname(body.get("nickname", ""))
    try:
        result = store().create(current_user()["userId"], vehicle_id, label)
    except AlreadySaved as error:
        abort(409, description=str(error))
    except VehicleNotFound as error:
        abort(404, description=str(error))
    store().commit()
    response = jsonify({"savedVehicle": result})
    response.status_code = 201
    response.headers["Location"] = url_for("saved.detail", saved_id=result["savedVehicleId"])
    return response


@saved.get("/<int:saved_id>")
@requires_roles()
def detail(saved_id):
    query_fields(set())
    result = store().get(current_user()["userId"], identifier(saved_id))
    if result is None:
        abort(404, description="Saved vehicle not found")
    return jsonify({"savedVehicle": result})


@saved.patch("/<int:saved_id>")
@requires_roles()
def rename(saved_id):
    identifier(saved_id)
    body = json_fields({"nickname"})
    result = store().rename(current_user()["userId"], saved_id, nickname(body["nickname"]))
    if result is None:
        abort(404, description="Saved vehicle not found")
    store().commit()
    return jsonify({"savedVehicle": result})


@saved.delete("/<int:saved_id>")
@requires_roles()
def remove(saved_id):
    query_fields(set())
    if not store().delete(current_user()["userId"], identifier(saved_id)):
        abort(404, description="Saved vehicle not found")
    store().commit()
    return "", 204
