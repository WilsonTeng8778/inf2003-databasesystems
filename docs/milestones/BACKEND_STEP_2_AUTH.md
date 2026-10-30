# Backend step 2 — Sign-in sessions and role checks

Implemented and verified on 28 October 2026. Authentication works through JSON
APIs. Visual login forms and saved-vehicle/case/fleet editing are later steps.

## What is now working?

- Register a normal account, sign in, read the current account and sign out.
- Store passwords as salted Werkzeug scrypt hashes rather than entered passwords.
- Maintain an eight-hour server-side session, identified by an opaque token in a
  signed, HttpOnly, SameSite=Lax cookie. SQL stores only the token's SHA-256 hash.
- Reject expired sessions, deleted users, and captured cookies replayed after logout.
- Require a session-bound CSRF token on supported POST/PUT/PATCH/DELETE routes,
  including registration/login/logout. Reject a supplied foreign Origin.
- Allow administrators to list public user information and change roles. Never
  accept a role during self-registration. Keep at least one administrator.
- Check a protected request's role from SQL, so changes apply to existing sessions.

Public vehicle research remains available without signing in. A reusable analyst
role guard is unit-tested; it will be connected to the case APIs when those are
implemented. This step does not claim saved-vehicle/fleet/case ownership checks
are complete.

## Try it without building a browser form

Authentication setup has already been applied to the current computer. If Flask
is running from the previous step, stop it with **Ctrl+C**, then start it again:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Keep that terminal open. In a **second terminal** at the repository root, register
an account:

```powershell
.\.venv\Scripts\python.exe scripts/try_auth.py --register
```

The helper asks for an email and a password (12–128 characters). Password input
is hidden. It obtains the CSRF token, registers/signs in, requests the current
user, displays their public identity/role, and logs out. The account stays in
`app_user` for future login. Its role will be `NORMAL_USER`.

To test the same account's login later:

```powershell
.\.venv\Scripts\python.exe scripts/try_auth.py
```

The helper has its own cookies. Its sign-in does not also sign your browser in.
Opening `/api/auth/me` in an unsigned-in browser therefore returns 401 normally.
Browser forms will eventually perform this same request flow for you.

Your application password is one you choose during registration. It is separate
from the PostgreSQL installation password and generated database credentials in
`.env`. No email verification messages are sent by these local endpoints.

## API request flow

1. `GET /api/auth/csrf` gets a `csrfToken` and a cookie. Keep both.
2. Send JSON `email` and `password` to registration or login, with
   `X-CSRF-Token` containing that token and the same cookie.
3. Successful registration/login returns the public `user`, a rotated `csrfToken`,
   and a new cookie. Keep the updated cookie/token for later requests.
4. `GET /api/auth/me` reads your current identity using that cookie.
5. `POST /api/auth/logout` with the current token revokes the server session.

Registration signs the new user in automatically. Password whitespace is
significant; registration requires 12–128 characters. User responses never include
passwords, password hashes or session-token hashes. Login gives the same error
for an unknown email and a wrong password.

| Endpoint | Access and effect |
| --- | --- |
| `GET /api/auth/csrf` | Public; issues/returns a session-bound request-protection token. |
| `POST /api/auth/register` | Valid CSRF; exactly `email`, `password`; creates `NORMAL_USER`, signs in, returns 201. |
| `POST /api/auth/login` | Valid CSRF; exactly `email`, `password`; signs in, returns 200. |
| `GET /api/auth/me` | Signed-in user; returns only that account's public identity. |
| `POST /api/auth/logout` | Signed-in user and valid CSRF; revokes the current session. |
| `GET /api/admin/users?page=1&pageSize=20` | ADMIN only; bounded pagination, no credential fields. |
| `PATCH /api/admin/users/{userId}/role` | ADMIN and valid CSRF; JSON `role` is NORMAL_USER, ANALYST or ADMIN. |

401 means sign-in is needed or credentials are invalid. 403 means a permission or
CSRF/origin check denied the request. Duplicate emails and a last-admin demotion
return 409. Role changes are serialized in a SQL transaction, and the actor's
administrator role is checked again after taking that lock.

## First administrator

No permanent administrator or default-password account was seeded. When ready to
use admin functions, create the first administrator locally with:

```powershell
.\.venv\Scripts\python.exe scripts/create_admin.py
```

Choose an unused email and enter/confirm its password at the hidden prompts. This
trusted local command uses construction credentials and refuses to bootstrap
another account if an administrator already exists. Further analyst/admin roles
are assigned through the authenticated admin API. Registration cannot choose them.

## Storage, configuration and fresh setup

`sql/migrations/002_auth_sessions.sql` adds `app_session` and records schema
version 2. It retains existing data. `scripts/setup_databases.py` now includes
additive migration files when constructing a fresh database.

On a fresh setup, complete the earlier database/import and SQL-reader setup, then:

```powershell
.\.venv\Scripts\python.exe scripts/setup_auth.py
```

This applies the session migration, provisions `vehicle_safety_auth`, and generates
`AUTH_POSTGRES_*` credentials and `FLASK_SECRET_KEY` into ignored `.env` without
printing them. Reruns retain existing credentials/signing key. No reimport is
required. Restart Flask to load changed settings.

The SQL auth account can read users, insert only email/password-hash columns,
update the role column for the guarded admin service, and manage session rows.
It cannot insert a chosen user role or modify official reference records. The
research reader remains separate and cannot read the user table. Application
role checks decide which signed-in human may request a privileged operation.

Cookies use local HTTP settings; `SESSION_COOKIE_SECURE` is false for localhost
and can be configured true for HTTPS. Session data persists in PostgreSQL across
Flask restarts. Expired sessions are rejected on lookup and cleaned for that user
on their next sign-in. Logout can leave an anonymous CSRF cookie; that is not an
authenticated session.

## Verification

- **34 automated tests passed:** 12 research API tests, 17 authentication tests,
  and 5 ETL transformation tests. Fake stores/connections keep these off live DBs.
- **36 recorded real HTTP checks passed**, plus two interactive-helper flows
  (registration and later login), against a temporary server and real PostgreSQL.
- The first-admin interactive bootstrap and refusal of a second bootstrap were
  checked. The last-admin guard was checked live while the synthetic administrator
  was the only administrator.
- Hash storage, cookie revocation, expiration, role changes/revocation, SQL column
  privileges and the continuing public vehicle query were verified.
- Temporary fixture accounts/sessions were deleted. Checked project record counts
  matched their pre-test counts, including the existing NHTSA data.

Evidence: [auth_verification_report.json](../auth_verification_report.json).
Earlier milestone reports remain dated evidence for those stages.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

The live verifier creates and removes owned synthetic accounts. It does not
create your personal account, leave a default administrator, reset the database
or import data. If a real administrator already exists, its first-admin/last-admin
fixture checks are recorded as not applicable; it never demotes existing users.

Next: authenticated saved-vehicle CRUD with ownership checks, then analyst-case
and small fleet/work-order APIs. The complete backend and GUI remain unfinished.

Implementation references: [Flask request and cookie security](https://flask.palletsprojects.com/en/stable/web-security/),
[Flask session settings](https://flask.palletsprojects.com/en/stable/config/),
[Werkzeug password hashing](https://werkzeug.palletsprojects.com/en/stable/utils/#werkzeug.security.generate_password_hash),
[PostgreSQL column privileges](https://www.postgresql.org/docs/18/sql-grant.html).
