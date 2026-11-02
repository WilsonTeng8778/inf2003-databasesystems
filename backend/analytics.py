"""Public reference analytics: bounded date windows and server-owned aggregations."""

from flask import Blueprint, abort, current_app, jsonify

from backend.routes import calendar_date, number, pg, query_fields, text
from backend.services.analytics import months_between, vehicle_analytics
from project_config import mongo_database

analytics = Blueprint('analytics',__name__,url_prefix='/api/analytics')


@analytics.get('/vehicle')
def vehicle():
    query_fields({'make','model','year','receivedFrom','receivedTo'})
    make,model = text('make',required=True,maximum=100),text('model',required=True,maximum=256)
    year = number('year',minimum=1900,maximum=2100)
    start,end = calendar_date('receivedFrom'),calendar_date('receivedTo')
    if start is None or end is None:
        abort(400,description='receivedFrom and receivedTo are required for analytics')
    if start>end:
        abort(400,description='receivedFrom must be on or before receivedTo')
    if not 1900<=start.year<=2100 or not 1900<=end.year<=2100 or months_between(start,end)>120:
        abort(400,description='Choose dates from 1900 to 2100 covering at most 120 calendar months')
    result = vehicle_analytics(pg(),mongo_database(current_app.extensions['mongo_client']),make=make,model=model,year=year,received_from=start,received_to=end)
    if result is None:
        abort(404,description='No matching vehicle identities in the imported catalogue')
    return jsonify(result)
