"""Official SQL reference queries; all client values use bound parameters."""

from datetime import date


RECALL_FIELDS = {"recallId": "recall_id", "campaignNumber": "campaign_number",
                 "manufacturer": "manufacturer", "reportDate": "report_date", "summary": "summary",
                 "potentiallyAffected": "potentially_affected", "doNotDrive": "do_not_drive", "parkOutside": "park_outside"}
INVESTIGATION_FIELDS = {"investigationId": "investigation_id", "investigationNumber": "investigation_number",
                        "investigationType": "investigation_type", "subject": "subject", "summary": "summary",
                        "openedDate": "opened_date", "closedDate": "closed_date", "status": "status"}
VEHICLE_FIELDS = {"modelYearId": "model_year_id", "make": "make", "model": "model", "year": "year"}
RECORD_FIELDS = {"sourceRecordId": "source_record_id", **VEHICLE_FIELDS, "component": "component",
                 "manufacturingStarted": "manufacturing_started", "manufacturingEnded": "manufacturing_ended",
                 "sourceArchive": "source_archive", "sourceLine": "source_line"}
RECALL_NOTE = "Official recall snapshot; model-year matches do not establish VIN-specific applicability or repair completion."
INVESTIGATION_NOTE = ("Official NHTSA investigation snapshot, separate from internal analyst cases. "
                      "OPEN/CLOSED is derived from the stored closing date, not a live NHTSA status check.")


def columns(fields, alias="r"):
    # Fields and aliases are server constants, never request values.
    return ",".join(f"{alias}.{name}" for name in fields.values())


def record(row, fields):
    return {key: value.isoformat() if isinstance(value, date) else value
            for key, value in zip(fields, row, strict=True)}


def vehicle_conditions(filters, alias="v"):
    conditions, values = [], []
    for key, column in (("model_year_id", "model_year_id"), ("year", "year"), ("make", "make"), ("model", "model")):
        if filters.get(key) is not None:
            conditions.append(f"{alias}.{column}=%s")
            values.append(filters[key])
    return conditions, values


def conditions_for(kind, filters):
    conditions, values = [], []
    vehicle_where, vehicle_values = vehicle_conditions(filters)
    component = filters.get("component")
    if kind == "recall":
        # Scope component AND vehicle to the SAME source record, when combined.
        if component is not None:
            vehicle_where.append("v.component=%s")
            vehicle_values.append(component)
        if vehicle_where:
            view = "research_recall_record" if component is not None else "research_recall_vehicle"
            conditions.append(f"EXISTS (SELECT 1 FROM {view} v WHERE v.recall_id=r.recall_id AND " +
                              " AND ".join(vehicle_where) + ")")
            values.extend(vehicle_values)
        fields = (("manufacturer", "manufacturer"), ("do_not_drive", "do_not_drive"), ("park_outside", "park_outside"))
        date_column = "report_date"
    else:
        if vehicle_where:
            conditions.append("EXISTS (SELECT 1 FROM research_investigation_vehicle v "
                              "WHERE v.investigation_id=r.investigation_id AND " + " AND ".join(vehicle_where) + ")")
            values.extend(vehicle_values)
        for key, view, column in (("component", "research_investigation_component", "component"),
                                  ("manufacturer", "research_investigation_manufacturer", "manufacturer")):
            if filters.get(key) is not None:
                conditions.append(f"EXISTS (SELECT 1 FROM {view} x WHERE x.investigation_id=r.investigation_id AND x.{column}=%s)")
                values.append(filters[key])
        fields = (("status", "status"), ("investigation_type", "investigation_type"))
        date_column = "opened_date"
    for key, column in fields:
        if filters.get(key) is not None:
            conditions.append(f"r.{column}=%s")
            values.append(filters[key])
    for key, comparison in (("date_from", ">="), ("date_to", "<=")):
        if filters.get(key) is not None:
            conditions.append(f"r.{date_column}{comparison}%s")
            values.append(filters[key])
    return (" WHERE " + " AND ".join(conditions) if conditions else ""), values


def page_result(connection, *, view, fields, where, values, order, page, page_size):
    total = connection.execute("SELECT count(*) FROM " + view + " r" + where, values).fetchone()[0]
    rows = connection.execute("SELECT " + columns(fields) + " FROM " + view + " r" + where +
                              " ORDER BY " + order + " LIMIT %s OFFSET %s",
                              [*values, page_size, (page - 1) * page_size]).fetchall()
    return {"items": [record(row, fields) for row in rows], "pagination": {
        "page": page, "pageSize": page_size, "total": total, "totalPages": (total + page_size - 1) // page_size,
    }}


def search_official(connection, kind, *, page=1, page_size=20, **filters):
    where, values = conditions_for(kind, filters)
    is_recall = kind == "recall"
    result = page_result(connection, view="research_recall" if is_recall else "research_investigation",
                         fields=RECALL_FIELDS if is_recall else INVESTIGATION_FIELDS,
                         where=where, values=values, page=page, page_size=page_size,
                         order=("r.report_date DESC NULLS LAST,r.campaign_number" if is_recall else
                                "r.opened_date DESC NULLS LAST,r.investigation_number"))
    for item in result["items"]:
        summary = item.pop("summary")
        item["summaryPreview"] = summary[:240] if summary is not None else None
        item["summaryTruncated"] = len(summary) > 240 if summary is not None else False
    result["interpretation"] = RECALL_NOTE if is_recall else INVESTIGATION_NOTE
    return result


def find_official(connection, kind, identifier):
    is_recall = kind == "recall"
    fields = {**RECALL_FIELDS, "consequence": "consequence", "remedy": "remedy"} if is_recall else INVESTIGATION_FIELDS
    view = "research_recall" if is_recall else "research_investigation"
    column = "campaign_number" if is_recall else "investigation_number"
    row = connection.execute("SELECT " + columns(fields) + f" FROM {view} r WHERE r.{column}=%s", (identifier,)).fetchone()
    return record(row, fields) if row is not None else None


def official_detail(connection, kind, identifier):
    item = find_official(connection, kind, identifier)
    if item is None:
        return None
    is_recall = kind == "recall"
    key = "recall_id" if is_recall else "investigation_id"
    parent = item["recallId" if is_recall else "investigationId"]
    view = "research_recall_vehicle" if is_recall else "research_investigation_vehicle"
    item["affectedVehicleCount"] = connection.execute(f"SELECT count(*) FROM {view} WHERE {key}=%s", (parent,)).fetchone()[0]
    if is_recall:
        item["sourceRecordCount"] = connection.execute(
            "SELECT count(*) FROM research_recall_record WHERE recall_id=%s", (parent,)).fetchone()[0]
        item["components"] = [row[0] for row in connection.execute("""SELECT DISTINCT component
            FROM research_recall_record WHERE recall_id=%s AND component<>'' ORDER BY component""", (parent,)).fetchall()]
    else:
        for output, view, column in (("components", "research_investigation_component", "component"),
                                      ("manufacturers", "research_investigation_manufacturer", "manufacturer")):
            item[output] = [row[0] for row in connection.execute(
                f"SELECT {column} FROM {view} WHERE investigation_id=%s ORDER BY {column}", (parent,)).fetchall()]
        item["linkedRecalls"] = [{"campaignNumber": campaign, "inImportedSnapshot": recall_id is not None}
                                for campaign, recall_id in connection.execute("""SELECT campaign_number,recall_id
                                    FROM research_investigation_recall WHERE investigation_id=%s ORDER BY campaign_number""",
                                    (parent,)).fetchall()]
    return {kind: item, "interpretation": RECALL_NOTE if is_recall else INVESTIGATION_NOTE}


def related_records(connection, kind, identifier, *, records=False, page=1, page_size=20):
    parent = find_official(connection, kind, identifier)
    if parent is None:
        return None
    is_recall = kind == "recall"
    column = "recall_id" if is_recall else "investigation_id"
    view = "research_recall_record" if records else ("research_recall_vehicle" if is_recall else "research_investigation_vehicle")
    result = page_result(connection, view=view, fields=RECORD_FIELDS if records else VEHICLE_FIELDS,
                         where=f" WHERE r.{column}=%s", values=[parent["recallId" if is_recall else "investigationId"]],
                         order="r.source_record_id" if records else "r.make,r.model,r.year,r.model_year_id",
                         page=page, page_size=page_size)
    result["campaignNumber" if is_recall else "investigationNumber"] = identifier
    result["interpretation"] = RECALL_NOTE if is_recall else INVESTIGATION_NOTE
    return result
