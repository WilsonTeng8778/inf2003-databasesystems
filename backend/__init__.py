"""Flask application factory for research, session authentication and administration."""


def create_app(config=None):
    import os
    import secrets
    from datetime import timedelta
    from flask import Flask, jsonify, request, url_for
    from psycopg import Error as PostgresError
    from pymongo.errors import PyMongoError
    from werkzeug.exceptions import HTTPException

    from project_config import AppDatabaseNotConfigured, app_postgres, auth_postgres, mongo_client, workflow_postgres
    from backend.routes import api, close_postgres
    from backend.auth import admin, auth, close_auth_postgres, protect_writes
    from backend.saved_vehicles import close_workflow_postgres, saved
    from werkzeug.security import generate_password_hash

    app = Flask(__name__)
    app.config.from_mapping(
        PG_CONNECT=app_postgres, AUTH_PG_CONNECT=auth_postgres, WORKFLOW_PG_CONNECT=workflow_postgres,
        MONGO_CLIENT_FACTORY=mongo_client,
        SECRET_KEY=os.getenv("FLASK_SECRET_KEY"), SESSION_COOKIE_NAME="vehicle_safety_session",
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8), SESSION_REFRESH_EACH_REQUEST=False,
        MAX_CONTENT_LENGTH=16 * 1024, TRUSTED_HOSTS=["localhost", "127.0.0.1"],
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        raise AppDatabaseNotConfigured("Run scripts/setup_auth.py to generate the local signing key")
    if "DUMMY_PASSWORD_HASH" not in app.config:
        app.config["DUMMY_PASSWORD_HASH"] = generate_password_hash(secrets.token_urlsafe(32))
    app.extensions["mongo_client"] = app.config["MONGO_CLIENT_FACTORY"]()
    app.register_blueprint(api)
    app.register_blueprint(auth)
    app.register_blueprint(admin)
    app.register_blueprint(saved)
    app.before_request(protect_writes)
    app.teardown_appcontext(close_postgres)
    app.teardown_appcontext(close_auth_postgres)
    app.teardown_appcontext(close_workflow_postgres)

    @app.after_request
    def private_response_headers(response):
        if request.path.startswith(("/api/auth/", "/api/admin/", "/api/saved-vehicles")):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def index():
        return jsonify({"service": "Vehicle Safety Recall & Defect Investigation System",
                        "links": {"health": url_for("api.health"),
                                  "vehicleSearch": url_for("api.vehicles", year=2022, make="HONDA", model="CIVIC"),
                                  "safetyProfile": url_for("api.profile", year=2022, make="HONDA", model="CIVIC"),
                                  "csrf": url_for("auth.csrf"), "currentUser": url_for("auth.me"),
                                  "savedVehicles": url_for("saved.listing")}})

    def unavailable(error):
        app.logger.warning("Database request unavailable (%s)", type(error).__name__)
        return jsonify({"error": {"code": "database_unavailable",
                                  "message": "Vehicle data is temporarily unavailable."}}), 503

    for error in [PostgresError, PyMongoError, AppDatabaseNotConfigured]:
        app.register_error_handler(error, unavailable)

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({"error": {"code": error.name.lower().replace(" ", "_"),
                                                 "message": error.description}})
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def unexpected(error):
        # Connection details or raw exception text must not reach API clients/logs.
        app.logger.error("Unhandled API error (%s)", type(error).__name__)
        return jsonify({"error": {"code": "internal_error", "message": "The request could not be completed."}}), 500

    return app
