# Backend step 1 — Read-only vehicle research

Implemented and verified on 28 October 2026. This completes the first small
backend step; the complete backend milestone remains in progress.

## What changed

The terminal's vehicle query can now be requested through HTTP, the protocol used
by browsers. Flask receives a request, validates its parameters, calls the shared
database query, and returns JSON. The same query function still serves the CLI.

```text
Browser request -> backend/routes.py -> backend/services/research.py
                                      -> PostgreSQL official records
                                      -> MongoDB complaints
                <- JSON response      <- combined result
```

This is a working API, with JSON output. The visual website, login and editable
workflows are subsequent steps.

## Run it locally

Flask and the SQL reader have already been prepared on the current computer.
From the repository root, start:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Leave the terminal running, then open:

- API links: <http://127.0.0.1:5000/>
- Database readiness: <http://127.0.0.1:5000/api/health>
- Vehicle search: <http://127.0.0.1:5000/api/vehicles/search?year=2022&make=HONDA&model=CIVIC>
- Combined profile: <http://127.0.0.1:5000/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC>

Press **Ctrl+C** in the terminal to stop this local development server. The
database services and stored records remain independent of the Flask process.
Server startup does not construct databases, run imports, or reset data.

## Endpoints and behavior

| GET endpoint | Behavior |
| --- | --- |
| `/` | Returns links to the API examples. |
| `/api/health` | Checks both databases; returns 200 when ready, 503 if a required database is unavailable. |
| `/api/vehicles/search` | Searches normalized vehicle identities; optional exact `year`, `make`, `model` filters; `page` defaults to 1 and `pageSize` to 20, capped at 100. |
| `/api/vehicles/safety-profile` | Requires `year`, `make`, `model`; returns the combined SQL/MongoDB profile or 404 if no vehicle matches. |

Invalid, duplicated or unknown query parameters return JSON errors with status
400. Unsupported write methods return 405. Required database errors return 503
without returning raw exception text or connection settings. Unexpected failures
return a generic JSON 500 response. SQL values are parameterized.

## SQL application account

`scripts/setup_readonly_user.py` creates/reuses a separate SQL account and writes
its generated password into ignored `.env`. It is granted access to the vehicle
catalogue and safety-summary views. It is not granted access to the user table or
permission to modify reference records. Its default transactions are read-only.

The `APP_POSTGRES_*` settings are for the web reader. `POSTGRES_*` remain the
construction/import credentials. This database account is separate from the
future NORMAL_USER/ANALYST/ADMIN application roles; it is not a website login.

For a fresh teammate setup, install the updated requirements, construct/import
the databases as documented, and then run this once before starting Flask:

```powershell
.\.venv\Scripts\python.exe scripts/setup_readonly_user.py
```

MongoDB access currently uses the existing local connection configuration. The
implemented request handlers issue only reads/aggregations; this step does not
claim MongoDB account-level authorization has been configured.

## Verification evidence

- **17 automated tests passed:** 12 API tests with fake connections and 5 existing
  transformation tests. The API tests include validation, pagination, parameterized
  SQL, missing vehicles, blocked write methods, connection cleanup and sanitized
  database-error responses.
- **8 real HTTP checks passed** against a temporary loopback server and the live
  local databases. These include successful requests, invalid input, missing
  vehicles and a rejected POST request.
- The SQL reader's identity/read-only setting and restricted privileges were checked.
- Checked reference/application record counts before and after HTTP verification
  were unchanged.
- The sample 2022 Honda Civic response matches the previously verified snapshot:
  4 recall campaigns, 2 official investigations, and 885 complaints.

Evidence: [api_verification_report.json](api_verification_report.json).
The full database CRUD/import verification remains separately dated 25 October
in [verification_report.json](verification_report.json).

Reproduce this step's checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_api.py
```

The HTTP verifier starts and stops its own server on a free local port. It does
not need the manually started Flask server, recreate databases, or rerun imports.
It replaces only its API evidence report. Database-outage responses were tested
with fake connections; no live service was stopped.

## Next step

Add registration/login, password hashing, sessions and application permissions.
Then implement saved vehicles, editable analyst cases with cross-database failure
handling, and the small owner-managed fleet/work-order workflow. The GUI and
performance experiments remain planned.

Implementation references: [Flask application factories](https://flask.palletsprojects.com/en/stable/patterns/appfactories/),
[Flask test client](https://flask.palletsprojects.com/en/stable/testing/),
[Psycopg query parameters](https://www.psycopg.org/psycopg3/docs/basic/params.html),
[PostgreSQL privileges](https://www.postgresql.org/docs/18/sql-grant.html).
