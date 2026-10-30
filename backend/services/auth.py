"""Authentication persistence. Sessions use hashed opaque tokens, not passwords."""

import re
from hashlib import sha256

from psycopg.errors import UniqueViolation
from psycopg import Error as PostgresError

ROLES = {"NORMAL_USER", "ANALYST", "ADMIN"}
PUBLIC_COLUMNS = "user_id,email,role,created_at"


class EmailTaken(ValueError):
    pass


class RoleChangeDenied(ValueError):
    pass


class LastAdministrator(ValueError):
    pass


class AccountDeletionConflict(ValueError):
    pass


def validate_email(value):
    if not isinstance(value, str):
        raise ValueError("email must be a string")
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) or not value.isprintable():
        raise ValueError("Provide a valid email address")
    return value


def validate_password(value, *, registration=False):
    minimum = 12 if registration else 1
    if not isinstance(value, str) or not minimum <= len(value) <= 128 or "\0" in value:
        raise ValueError(f"password must contain {minimum} to 128 characters")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ValueError("password contains invalid Unicode") from None
    return value  # Password whitespace is significant; never trim it.


def token_hash(value):
    return sha256(value.encode("utf-8")).hexdigest()


def public_user(row):
    if row is None:
        return None
    identifier, email, role, created_at = row
    return {"userId": identifier, "email": email, "role": role, "createdAt": created_at.isoformat()}


class PostgresAuthStore:
    def __init__(self, connection):
        self.connection = connection

    def create_user(self, email, password_hash):
        try:
            row = self.connection.execute(f"""INSERT INTO app_user(email,password_hash)
                VALUES (%s,%s) RETURNING {PUBLIC_COLUMNS}""", (email, password_hash)).fetchone()
        except UniqueViolation:
            self.connection.rollback()
            raise EmailTaken("An account with that email already exists") from None
        return public_user(row)

    def credentials(self, email):
        row = self.connection.execute(f"SELECT {PUBLIC_COLUMNS},password_hash FROM app_user WHERE email=%s", (email,)).fetchone()
        return (public_user(row[:4]), row[4]) if row else None

    def open_session(self, user_id, digest, expires_at):
        self.connection.execute("DELETE FROM app_session WHERE user_id=%s AND expires_at<=now()", (user_id,))
        self.connection.execute("INSERT INTO app_session(token_hash,user_id,expires_at) VALUES (%s,%s,%s)",
                                (digest, user_id, expires_at))

    def delete_session(self, digest):
        self.connection.execute("DELETE FROM app_session WHERE token_hash=%s", (digest,))

    def session_user(self, digest):
        row = self.connection.execute("""SELECT u.user_id,u.email,u.role,u.created_at
            FROM app_session s JOIN app_user u USING(user_id)
            WHERE s.token_hash=%s AND s.expires_at>now()""", (digest,)).fetchone()
        return public_user(row)

    def list_users(self, page, page_size):
        total = self.connection.execute("SELECT count(*) FROM app_user").fetchone()[0]
        rows = self.connection.execute(f"SELECT {PUBLIC_COLUMNS} FROM app_user ORDER BY user_id LIMIT %s OFFSET %s",
                                       (page_size, (page - 1) * page_size)).fetchall()
        return {"items": [public_user(row) for row in rows],
                "pagination": {"page": page, "pageSize": page_size, "total": total,
                               "totalPages": (total + page_size - 1) // page_size}}

    def change_role(self, actor_id, target_id, role):
        # Serialize role mutations, including the last-admin check. Recheck the
        # actor after acquiring the lock so a revoked admin cannot race a change.
        self.connection.execute("SELECT pg_advisory_xact_lock(2003,19)")
        actor = self.connection.execute("SELECT role FROM app_user WHERE user_id=%s", (actor_id,)).fetchone()
        if not actor or actor[0] != "ADMIN":
            raise RoleChangeDenied("Administrator access is required")
        old = self.connection.execute("SELECT role FROM app_user WHERE user_id=%s FOR UPDATE", (target_id,)).fetchone()
        if old is None:
            return None
        if old[0] == "ADMIN" and role != "ADMIN":
            if self.connection.execute("SELECT count(*) FROM app_user WHERE role='ADMIN'").fetchone()[0] <= 1:
                raise LastAdministrator("At least one administrator must remain")
        row = self.connection.execute(f"UPDATE app_user SET role=%s WHERE user_id=%s RETURNING {PUBLIC_COLUMNS}",
                                       (role, target_id)).fetchone()
        return public_user(row)

    def delete_user(self, actor_id, target_id, confirmation_email):
        try:
            return self.connection.execute('SELECT public.delete_unused_account(%s,%s,%s)',
                (actor_id, target_id, confirmation_email)).fetchone()[0]
        except PostgresError as error:
            errors = {
                'P2001': (RoleChangeDenied, 'Administrator access is required'),
                'P2002': (AccountDeletionConflict, 'You cannot delete your signed-in account from administration'),
                'P2003': (LastAdministrator, 'At least one administrator must remain'),
                'P2004': (AccountDeletionConflict, 'This account has saved vehicles, fleets, cases or case history and cannot be deleted'),
                'P2005': (AccountDeletionConflict, 'The confirmation email does not match the current account; refresh and review it'),
            }
            if error.sqlstate not in errors:
                raise
            self.connection.rollback()
            kind, message = errors[error.sqlstate]
            raise kind(message) from None

    def commit(self):
        self.connection.commit()
