"""Public read-only recall and official-investigation research endpoints."""

import re

from flask import Blueprint, abort, jsonify, url_for

from backend.routes import boolean, calendar_date, number, pg, query_fields, text
from backend.services.official_records import official_detail, related_records, search_official

official = Blueprint("official", __name__, url_prefix="/api")
COMMON_FILTERS = {"modelYearId", "year", "make", "model", "component", "manufacturer", "page", "pageSize"}


def pagination():
    return {"page": number("page", default=1, maximum=10000),
            "page_size": number("pageSize", default=20, maximum=100)}


def identifier(value):
    if re.fullmatch(r"[A-Za-z0-9]{1,20}", value) is None:
        abort(400, description="Record number must contain 1 to 20 ASCII letters or digits")
    return value.upper()


def filters_for(kind):
    is_recall = kind == "recall"
    start_field, end_field = ("reportFrom", "reportTo") if is_recall else ("openedFrom", "openedTo")
    query_fields(COMMON_FILTERS | {start_field, end_field} |
                 ({"doNotDrive", "parkOutside"} if is_recall else {"status", "investigationType"}))
    filters = {"model_year_id": number("modelYearId"), "year": number("year", minimum=1900, maximum=2100),
               "make": text("make", maximum=100), "model": text("model"), "component": text("component"),
               "manufacturer": text("manufacturer"), "date_from": calendar_date(start_field),
               "date_to": calendar_date(end_field), **pagination()}
    if filters["date_from"] is not None and filters["date_to"] is not None and filters["date_from"] > filters["date_to"]:
        abort(400, description=f"{start_field} must be on or before {end_field}")
    if is_recall:
        filters.update(do_not_drive=boolean("doNotDrive"), park_outside=boolean("parkOutside"))
    else:
        status = text("status", maximum=6)
        if status is not None and status not in {"OPEN", "CLOSED"}:
            abort(400, description="status must be OPEN or CLOSED")
        filters.update(status=status, investigation_type=text("investigationType", maximum=20))
    return filters


def listing(kind):
    filters = filters_for(kind)
    result = search_official(pg(), kind, **filters)
    for item in result["items"]:
        if kind == "recall":
            item["detailUrl"] = url_for("official.recall", campaign_number=item["campaignNumber"])
        else:
            item["detailUrl"] = url_for("official.investigation", investigation_number=item["investigationNumber"])
    return jsonify(result)


def detail(kind, value):
    query_fields(set())
    value = identifier(value)
    result = official_detail(pg(), kind, value)
    if result is None:
        abort(404, description="No matching official record in the imported snapshot")
    if kind == "recall":
        result["recall"]["links"] = {
            "vehicles": url_for("official.recall_vehicles", campaign_number=value),
            "records": url_for("official.recall_records", campaign_number=value),
        }
    else:
        item = result["investigation"]
        item["links"] = {"vehicles": url_for("official.investigation_vehicles", investigation_number=value)}
        for recall in item["linkedRecalls"]:
            recall["detailUrl"] = (url_for("official.recall", campaign_number=recall["campaignNumber"])
                                   if recall["inImportedSnapshot"] else None)
    return jsonify(result)


def related(kind, value, *, records=False):
    query_fields({"page", "pageSize"})
    value, pages = identifier(value), pagination()
    result = related_records(pg(), kind, value, records=records, **pages)
    if result is None:
        abort(404, description="No matching official record in the imported snapshot")
    return jsonify(result)


@official.get("/recalls")
def recalls():
    return listing("recall")


@official.get("/recalls/<campaign_number>")
def recall(campaign_number):
    return detail("recall", campaign_number)


@official.get("/recalls/<campaign_number>/vehicles")
def recall_vehicles(campaign_number):
    return related("recall", campaign_number)


@official.get("/recalls/<campaign_number>/records")
def recall_records(campaign_number):
    return related("recall", campaign_number, records=True)


@official.get("/investigations")
def investigations():
    return listing("investigation")


@official.get("/investigations/<investigation_number>")
def investigation(investigation_number):
    return detail("investigation", investigation_number)


@official.get("/investigations/<investigation_number>/vehicles")
def investigation_vehicles(investigation_number):
    return related("investigation", investigation_number)
