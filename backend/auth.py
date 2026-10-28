"""Session authentication, CSRF protection, and role-gated administration."""

import hmac
import secrets
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, g, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.routes import number, query_fields
from backend.services.auth import (EmailTaken, LastAdministrator, PostgresAuthStore, ROLES,
                                   RoleChangeDenied, token_hash, validate_email, validate_password)

auth = Blueprint("auth", __name__, url_prefix="/api/auth")
admin = Blueprint("admin", __name__, url_prefix="/api/admin")


def auth_pg():
    if "auth_postgres" not in g:
        g.auth_postgres = current_app.config["AUTH_PG_CONNECT"]()
    return g.auth_postgres


def close_auth_postgres(error=None):
    connection = g.pop("auth_postgres", None)
    if connection is not None:
        connection.close()


def store():
    if "auth_store" not in g:
        factory = current_app.config.get("AUTH_STORE_FACTORY")
        g.auth_store = factory() if factory else PostgresAuthStore(auth_pg())
    return g.auth_store


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def protect_writes():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or request.url_rule is None:
        return
    expected, received = session.get("csrf_token"), request.headers.get("X-CSRF-Token", "")
    if (not isinstance(expected, str) or not expected.isascii() or len(received) != 43
            or not received.isascii() or not hmac.compare_digest(expected, received)):
        abort(403, description="A valid X-CSRF-Token header is required")
    origin = request.headers.get("Origin")
    if origin:
        try:
            parsed = urlsplit(origin)
        except ValueError:
            abort(403, description="Invalid request origin")
        if parsed.scheme != request.scheme or parsed.netloc.lower() != request.host.lower():
            abort(403, description="Cross-origin changes are not allowed")


def current_user():
    if "current_user" not in g:
        value = session.get("session_token")
        user = store().session_user(token_hash(value)) if isinstance(value, str) and len(value) == 43 else None
        if value and user is None:
            session.clear()
        g.current_user = user
    return g.current_user


def requires_roles(*roles):
    def decorate(function):
        @wraps(function)
        def guarded(*args, **kwargs):
            user = current_user()
            if user is None:
                abort(401, description="Sign in to continue")
            if roles and user["role"] not in roles:
                abort(403, description="You do not have permission for this action")
            return function(*args, **kwargs)
        return guarded
    return decorate


def json_fields(required, optional=()):
    query_fields(set())
    body = request.get_json()
    required, optional = set(required), set(optional)
    if not isinstance(body, dict) or not required <= set(body) or not set(body) <= required | optional:
        message = "Required JSON fields: " + ", ".join(sorted(required))
        if optional:
            message += "; optional: " + ", ".join(sorted(optional))
        abort(400, description=message)
    return body


def credentials(registration=False):
    body = json_fields({"email", "password"})
    try:
        return validate_email(body["email"]), validate_password(body["password"], registration=registration)
    except ValueError as error:
        abort(400, description=str(error))


def sign_in(user):
    persistence = store()
    old = session.get("session_token")
    if isinstance(old, str):
        persistence.delete_session(token_hash(old))
    value = secrets.token_urlsafe(32)
    persistence.open_session(user["userId"], token_hash(value),
                             datetime.now(timezone.utc) + current_app.permanent_session_lifetime)
    persistence.commit()
    session.clear()
    session.permanent = True
    session["session_token"] = value
    return {"user": user, "csrfToken": csrf_token()}


@auth.get("/csrf")
def csrf():
    return jsonify({"csrfToken": csrf_token()})


@auth.post("/register")
def register():
    email, password = credentials(registration=True)
    try:
        user = store().create_user(email, generate_password_hash(password))
    except EmailTaken as error:
        abort(409, description=str(error))
    return jsonify(sign_in(user)), 201


@auth.post("/login")
def login():
    email, password = credentials()
    result = store().credentials(email)
    # Use the same expensive password check for an unknown email.
    candidate = result[1] if result else current_app.config["DUMMY_PASSWORD_HASH"]
    if not check_password_hash(candidate, password) or result is None:
        abort(401, description="Invalid email or password")
    return jsonify(sign_in(result[0]))


@auth.get("/me")
@requires_roles()
def me():
    return jsonify({"user": current_user()})


@auth.post("/logout")
@requires_roles()
def logout():
    store().delete_session(token_hash(session["session_token"]))
    store().commit()
    session.clear()
    return jsonify({"message": "Signed out", "csrfToken": csrf_token()})


@admin.get("/users")
@requires_roles("ADMIN")
def users():
    query_fields({"page", "pageSize"})
    return jsonify(store().list_users(number("page", default=1), number("pageSize", default=20, maximum=100)))


@admin.patch("/users/<int:user_id>/role")
@requires_roles("ADMIN")
def change_role(user_id):
    if not 1 <= user_id <= 9223372036854775807:
        abort(400, description="Invalid user identifier")
    body = json_fields({"role"})
    if not isinstance(body["role"], str) or body["role"] not in ROLES:
        abort(400, description="role must be NORMAL_USER, ANALYST or ADMIN")
    try:
        user = store().change_role(current_user()["userId"], user_id, body["role"])
    except RoleChangeDenied as error:
        abort(403, description=str(error))
    except LastAdministrator as error:
        abort(409, description=str(error))
    if user is None:
        abort(404, description="User not found")
    store().commit()
    return jsonify({"user": user})
