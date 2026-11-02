"""ADMIN-only dataset summaries and filtered import history; no browser imports or resets."""

from flask import Blueprint, abort, current_app, jsonify, request

from backend.auth import requires_roles
from backend.routes import number, pg, query_fields
from backend.services.administration import DATASETS, dataset_summary, import_runs
from project_config import mongo_database

administration = Blueprint('administration', __name__, url_prefix='/api/admin')


@administration.get('/datasets')
@requires_roles('ADMIN')
def datasets():
    query_fields(set())
    return jsonify(dataset_summary(pg(), mongo_database(current_app.extensions['mongo_client'])))


@administration.get('/import-runs')
@requires_roles('ADMIN')
def imports():
    query_fields({'dataset', 'status', 'page', 'pageSize'})
    dataset, status = request.args.get('dataset'), request.args.get('status')
    if dataset is not None and dataset not in DATASETS:
        abort(400, description='dataset must be vehicle_catalogue, recalls, investigations or complaints')
    if status is not None and status not in {'RUNNING', 'COMPLETED', 'FAILED'}:
        abort(400, description='status must be RUNNING, COMPLETED or FAILED')
    page = number('page', default=1, maximum=10000)
    size = number('pageSize', default=20, maximum=100)
    return jsonify(import_runs(pg(), dataset=dataset, status=status, page=page, page_size=size))
