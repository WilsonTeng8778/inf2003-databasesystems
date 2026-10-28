# INF2003 Group 19 — Vehicle Safety Recall & Defect Investigation System

A hybrid PostgreSQL + MongoDB application for NHTSA vehicle research, internal
analyst cases, and a small fleet recall/work-order workflow.

**New to the project? Start with [PROJECT_GUIDE.md](PROJECT_GUIDE.md).** It explains
the development stages, what each part does, completed work, and our next steps.
We maintain it as the project progresses; this README is the technical setup guide.

The first implementation milestone is the database foundation: full raw-source
inspection, SQL schema/constraints/views/trigger, MongoDB validation/indexes,
repeatable imports, and database-only verification. Flask now provides research,
registration/login/logout, sessions and guarded admin role management. Personal
saved vehicles now have owner-scoped CRUD APIs. Analyst-case/fleet
workflows and the GUI follow. Docker is not required;
development uses native Windows services.

The foundation was completed and verified on 25 October 2026. See the
[milestone summary](docs/MILESTONE_1.md) and
[live verification results](docs/verification_report.json).

The first backend step was verified on 28 October. See
[Backend step 1](docs/BACKEND_STEP_1.md) and its
[HTTP verification results](docs/api_verification_report.json).

Authentication and role checks were verified later on 28 October. See
[Backend step 2](docs/BACKEND_STEP_2_AUTH.md) and
[authentication verification results](docs/auth_verification_report.json).

Saved-vehicle ownership and CRUD were also verified on 28 October. See
[Backend step 3](docs/BACKEND_STEP_3_SAVED_VEHICLES.md) and its
[live verification results](docs/saved_vehicles_verification_report.json).

## What should I run now?

**The setup and full imports were already run on this computer on 25 October
2026. You do not need to repeat the entire setup sequence.** The instructions
below also let a teammate reproduce the project on a new computer. Flask and its
SQL reader were also installed/configured here on 28 October. Authentication
storage and credentials have now been prepared here too.
Saved-vehicle workflow access has also been prepared; no reimport is needed.

To try the new backend, run:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Keep that terminal running and open
[the example vehicle profile](http://127.0.0.1:5000/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC)
in your browser. It displays JSON; the visual website is still to build. Press
**Ctrl+C** to stop Flask. Starting/stopping it does not reset database contents.

To try registration, restart Flask if it was already running before the auth
change, then open a **second terminal** and run:

```powershell
.\.venv\Scripts\python.exe scripts/try_auth.py --register
```

It prompts locally for email/password, creates a normal account, checks the
signed-in identity, then logs out. The account persists. Password input is hidden.
To test an existing account, run the helper without `--register`. These are
application credentials you choose, separate from the database passwords in `.env`.

To manage saved vehicles with your existing account, run this in the second
terminal instead:

```powershell
.\.venv\Scripts\python.exe scripts/try_saved_vehicles.py
```

The menu lists, saves, renames and removes your own records. They persist after
logout unless you remove them. Restart an older Flask process to load new routes.

For connection checks or the original terminal query, run these commands **one
at a time** at the repository root (use another terminal if Flask is running):

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
```

The first checks connections and source-file availability. The second actually
queries the stored data and displays a vehicle safety profile. Both are read-only
with respect to the databases. The transformation test command at the end of this
README is another optional check; the automated API/transformation tests use
fake connections or made-up inputs, not the live databases.

**Each line in a code block is a separate command.** Keep the line breaks; do not
combine multiple commands into one line by putting spaces between them. The
`.\.venv\Scripts\python.exe` prefix chooses this project's Python environment;
it does not restart or reset a database.

The databases keep their data after a script exits, VS Code closes, or the computer
restarts. Their Windows services must be running for connections to work. Starting
a service again does not require recreating the databases or reimporting data.

## What each command does

Script names in this table refer to files under `scripts/`; the executable command
examples below include the full Python invocation.

| Command or script | Purpose | Effect on data | When to use it |
| --- | --- | --- | --- |
| `python -m venv .venv` | Prepare the project's isolated Python environment. | Creates/reuses `.venv`; does not touch database contents. | First setup, or when `.venv` is missing. |
| `python.exe -m pip install -r requirements.txt` | Install the required Python packages into that environment. | Changes Python packages, not database contents. | First setup, or after dependency requirements change. |
| `check_environment.py` | Check tools, source-file presence and database connections. | Reads connection/version information. | Whenever you want a setup check. |
| `inspect_data.py` | Examine the raw files and summarize their structure/counts. | Leaves databases untouched; replaces `docs/data_profile.json`. | When inspecting or changing source files. |
| `setup_databases.py` | Create missing project databases/objects and apply views, trigger, validators and indexes. | Changes database definitions while retaining stored records. | First construction, or an intentional reapplication of the current setup scripts. |
| `import_all.py` | Load or refresh official records from the local ZIPs. | Inserts/updates imported records and adds import-log entries; does not empty the databases. | First load, or an intentional data refresh. |
| `verify_databases.py` | Test real database CRUD, constraints and relationships. | Creates temporary test records, then rolls back/removes them; replaces `docs/verification_report.json`. | To verify the database layer after relevant changes. |
| `setup_readonly_user.py` | Prepare a restricted SQL reader for the web API and save its credentials in ignored `.env`. | Creates/reuses a role and grants view access; does not change stored project records. | Once before the first API startup on a fresh setup. |
| `setup_auth.py` | Apply session storage and prepare auth credentials/signing key in ignored `.env`. | Adds the session table and restricted SQL role; retains existing data. | Once before authentication on a fresh setup; already run here. |
| `setup_workflow.py` | Prepare limited saved-vehicle SQL access and local credentials. | Grants saved-record operations; retains stored data. | Once before saved-vehicle use on a fresh setup; already run here. |
| `python.exe -m flask --app backend:create_app run` | Start the backend server for research and authentication requests. | Keeps running; startup does not reset/import data. Authentication requests can create users/sessions or change roles. | When using the web API. |
| `try_auth.py --register` | Try local registration, current-user lookup and logout through the running API. | Creates a persistent normal account; the demo logs its session out. | To create/try your own application account. |
| `try_auth.py` | Try an existing account's login/current-user/logout flow. | Opens then revokes the demo's session; retains the account. | To try login. |
| `try_saved_vehicles.py` | Sign in and manage your personal saved vehicles through a menu. | Saves/renames/removes only records you choose; retains them on logout. | When trying the saved-vehicle workflow. |
| `create_admin.py` | Prompt locally for the first administrator's email/password. | Creates a persistent ADMIN; refuses if an administrator already exists. | When bootstrapping the first administrator. |
| `verify_api.py` | Test HTTP requests against a temporary local server and the live databases. | Reads project records; replaces `docs/api_verification_report.json`; stops its server afterward. | After relevant API changes or to reproduce its evidence. |
| `verify_auth.py` | Verify auth/role behavior over real HTTP and check local helper flows. | Creates/removes owned synthetic accounts/sessions; replaces `docs/auth_verification_report.json`. | After authentication changes or to reproduce its evidence. |
| `verify_saved_vehicles.py` | Verify owner CRUD, cross-user denials and the saved-vehicle menu over HTTP. | Creates/removes owned synthetic accounts/saves; replaces its evidence report. | After saved-vehicle changes. |
| `safety_profile.py` | Look up a vehicle using both databases. | Reads existing data and prints the result. | Whenever you want to try the current vehicle query. |
| `python.exe -m unittest discover -s tests -v` | Test API behavior with fake connections and transformations with made-up records. | Does not connect to or change the databases. | After relevant code changes, or to see the automated tests run. |

The import uses **upserts**: update an imported record if its identifier already
exists, otherwise insert it. Rerunning the same files was verified to preserve
entity counts, although it still performs writes and adds log entries. It can
replace imported reference-field values with the source-file values; it is not
just a test. It does not clear users, saved vehicles, analyst cases, fleets or work
orders. There is no need to run it as part of an ordinary query or testing session.

## Documents

- [Beginner guide and living progress tracker](PROJECT_GUIDE.md)
- [Read-only backend step, endpoints and walkthrough](docs/BACKEND_STEP_1.md)
- [Authentication, roles and interactive walkthrough](docs/BACKEND_STEP_2_AUTH.md)
- [Saved-vehicle CRUD, ownership and interactive menu](docs/BACKEND_STEP_3_SAVED_VEHICLES.md)
- [Inspect the stored databases in pgAdmin and MongoDB Compass](docs/INSPECTING_DATABASES.md)
- [Approved implementation scope](docs/IMPLEMENTATION_GREENLIGHT.md)
- [Source-data findings and import scope](docs/DATA_INSPECTION.md)
- [Physical data model and ERD](docs/DATABASE_DESIGN.md)
- [Machine-readable source profile](docs/data_profile.json)
- [Original understanding/handoff](PROJECT_UNDERSTANDING_AND_PLAN.md)

## First-time setup on a new machine (Windows PowerShell)

The current machine has Python 3.13.7, PostgreSQL 18, and MongoDB Community 9.0.4.
The Python dependencies are pinned to the versions installed for this milestone.
Teammates should record their actual database versions when reproducing results.

1. Install Python and the two database servers, and start their Windows services.
   `psql`/`mongosh` are useful but the Python drivers do not require them on PATH.
2. Create a project environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Create `.env` only if it does not already exist:

   ```powershell
   if (-not (Test-Path .env)) { Copy-Item .env.example .env }
   ```

   Edit `.env` locally. Set `POSTGRES_PASSWORD` to the installation password.
   For literal special characters, use a single-quoted value, for example
   `POSTGRES_PASSWORD='your local password'`. Interpolation is disabled. Do not
   send credentials in chat or commit `.env`. Defaults connect to localhost and
   use a dedicated `vehicle_safety` database in each server.

4. Put the unmodified approved ZIPs in `data/raw/`:

   ```text
   FLAT_RCL_POST_2010.zip
   FLAT_INV.zip
   COMPLAINTS_RECEIVED_2020-2024.zip
   COMPLAINTS_RECEIVED_2025-2026.zip
   ```

   The corresponding `RCL.txt`, `INV.txt`, and `CMPL.txt` dictionaries belong in
   `data/dictionaries/`. Raw archives, staging files, `.env`, and `.venv` are
   excluded from Git. Keep live PostgreSQL/MongoDB storage outside this OneDrive
   repository. Download links are recorded in the approved scope document.

## Construct and import for first setup or an intentional refresh

Run from the repository root. The inspector needs only Python's standard library;
the other commands use the installed drivers and `.env`.

This block constructs and loads databases. It is already complete on the current
computer; it is not a daily startup sequence or a list of read-only tests.

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
.\.venv\Scripts\python.exe scripts/inspect_data.py
.\.venv\Scripts\python.exe scripts/setup_databases.py
.\.venv\Scripts\python.exe scripts/import_all.py
.\.venv\Scripts\python.exe scripts/verify_databases.py
```

Setup creates the dedicated databases if needed and applies additive schema,
validators, views, triggers and indexes. It does not drop existing databases.
Imports stream all selected source files, build the catalogue from all sources,
and upsert stable identifiers. Complaint grouping uses disposable SQLite disk
staging to bound memory; SQLite is not an application database. Allow disk space
for staged narratives as well as the final PostgreSQL/MongoDB databases.

Rerunning the same import must preserve entity counts. Each run is audited in
PostgreSQL `data_import_log`, including source hashes, timing, row counts, logical
entity insert/refresh counts, skips/rejections and completion/failure status.
The combined complaint hash field contains both archive hashes separated by `:`.
MongoDB batches can survive a failed import; rerunning completes their stable-key
upserts. Deletion reconciliation between different snapshots is not implemented.

`verify_databases.py` checks imported relationships, SQL constraints and trigger,
SQL workflow CRUD, and MongoDB document/nested CRUD. Synthetic verification SQL
records are rolled back; its MongoDB case document is removed in `finally`.
Successful results are saved in `docs/verification_report.json`. This is not yet
authentication, API or GUI testing.

For a MongoDB-only validator/CRUD check before PostgreSQL is configured, run
`.\.venv\Scripts\python.exe scripts/verify_mongo_schema.py`. This uses temporary
synthetic reference IDs and does not test SQL/MongoDB referential consistency.

## Try a combined vehicle query

```powershell
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
```

This reads official recall/investigation counts from SQL and complaint counts and
component aggregation from MongoDB. Complaints are allegations. Recall matches
are by normalized model year/make/model, not VIN-specific recall applicability or
proof of repair completion.

The CLI and web profile use the same query in `backend/services/research.py`.

## Backend setup and endpoints

On a fresh machine, install the current requirements and construct/import the
databases first. Then prepare the web account once:

```powershell
.\.venv\Scripts\python.exe scripts/setup_readonly_user.py
.\.venv\Scripts\python.exe scripts/setup_auth.py
.\.venv\Scripts\python.exe scripts/setup_workflow.py
```

This has already been done here. Its password is generated into ignored `.env`;
you do not need to send it in chat. Research uses `APP_POSTGRES_*`, authentication
uses `AUTH_POSTGRES_*`, personal workflow requests use `WORKFLOW_POSTGRES_*`, and
construction/import scripts use `POSTGRES_*`.
The signing key is generated locally; preserve it across normal server restarts.

Start Flask with the command near the top of this README. API routes are:

- `GET /` — example links.
- `GET /api/health` — readiness of both databases.
- `GET /api/vehicles/search?year=2022&make=HONDA&model=CIVIC` — exact-filter vehicle search; optional bounded pagination.
- `GET /api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC` — combined vehicle safety profile.

Those research endpoints remain read-only and public. Authentication also provides:

- `GET /api/auth/csrf` — request-protection token; keep the returned cookie.
- `POST /api/auth/register` and `POST /api/auth/login` — JSON email/password, CSRF header and matching cookie.
- `GET /api/auth/me` and `POST /api/auth/logout` — current account and session revocation.
- `GET /api/admin/users` and `PATCH /api/admin/users/{userId}/role` — ADMIN only.

Supported state-changing requests require `X-CSRF-Token`. Successful sign-in
rotates it; retain the returned token/cookie. [Backend step 2](docs/BACKEND_STEP_2_AUTH.md)
explains requests, role rules, the first-admin bootstrap and the local demo.
Signed-in personal CRUD is now available through `GET/POST /api/saved-vehicles`
and `GET/PATCH/DELETE /api/saved-vehicles/{savedVehicleId}`. The owner is derived
from the session; foreign records return 404. See
[Backend step 3](docs/BACKEND_STEP_3_SAVED_VEHICLES.md). Case/fleet editing and
browser forms remain subsequent work.

## Automated API and transformation tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The 53 current tests cover research APIs, authentication, saved-vehicle ownership,
CRUD/validation, CSRF/cookies, role changes and the existing ETL rules. They do
not connect to the local databases.

To reproduce actual HTTP checks using both live databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_api.py
```

For live authentication and permission checks:

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

These verifiers start/stop their own servers and record results. The auth verifier
creates/removes synthetic users/sessions. Neither reruns imports. Workflow-specific
ownership for cases/fleets, case failure recovery, their editable routes, performance
benchmarks, the GUI and final submission artifacts remain to implement.

To reproduce saved-vehicle CRUD/ownership checks against live databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_saved_vehicles.py
```

This verifier also tests the interactive saved-vehicle menu and cleans up only
its generated accounts/records. Existing personal saves and source data remain.
