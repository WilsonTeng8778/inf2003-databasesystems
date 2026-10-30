"""Public complaint browsing; clients supply typed values, never MongoDB queries."""

import re

from flask import Blueprint, abort, current_app, jsonify, request

from backend.routes import boolean, calendar_date, number, query_fields, text
from backend.services.complaints import get_complaint, search_complaints
from project_config import mongo_database

complaints = Blueprint("complaints", __name__, url_prefix="/api/complaints")


@complaints.get("")
def listing():
    query_fields({"modelYearId", "year", "make", "model", "component", "receivedFrom", "receivedTo",
                  "crash", "fire", "hasInjuries", "hasFatalities", "q", "page", "pageSize"})
    filters = {
        "model_year_id": number("modelYearId"), "year": number("year", minimum=1900, maximum=2100),
        "make": text("make", maximum=100), "model": text("model"), "component": text("component"),
        "received_from": calendar_date("receivedFrom"), "received_to": calendar_date("receivedTo"),
        "crash": boolean("crash"), "fire": boolean("fire"),
        "has_injuries": boolean("hasInjuries"), "has_fatalities": boolean("hasFatalities"),
        "page": number("page", default=1, maximum=10000),
        "page_size": number("pageSize", default=20, maximum=100),
    }
    start, end = filters["received_from"], filters["received_to"]
    if start is not None and end is not None and start > end:
        abort(400, description="receivedFrom must be on or before receivedTo")
    q = request.args.get("q")
    if q is not None:
        q = q.strip()
        if not q or len(q) > 200 or not q.isprintable():
            abort(400, description="q must contain 1 to 200 printable characters")
    filters["q"] = q
    database = mongo_database(current_app.extensions["mongo_client"])
    return jsonify(search_complaints(database, **filters))


@complaints.get("/<odi_number>")
def detail(odi_number):
    query_fields(set())
    if re.fullmatch(r"[0-9]{1,20}", odi_number) is None:
        abort(400, description="ODI number must contain 1 to 20 ASCII digits")
    result = get_complaint(mongo_database(current_app.extensions["mongo_client"]), odi_number)
    if result is None:
        abort(404, description="No matching complaint in the imported snapshot")
    return jsonify(result)
