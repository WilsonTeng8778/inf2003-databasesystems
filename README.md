# INF2003 Group 19 — Vehicle Safety Recall & Defect Investigation System

A hybrid PostgreSQL + MongoDB application for NHTSA vehicle research, internal
analyst cases, and a small fleet recall/work-order workflow.

**New to the project? Start with [PROJECT_GUIDE.md](PROJECT_GUIDE.md).** It explains
the development stages, what each part does, completed work, and our next steps.
We maintain it as the project progresses; this README is the technical setup guide.
The [user manual](USER_MANUAL.md) separates daily startup from first installation
and explains the application tasks. Use the [fresh-setup checklist](docs/FRESH_SETUP_CHECKLIST.md)
when a teammate reproduces the source/data package on another computer.

**Source checkpoint:** use `milestone/recallscope-core-complete-2026-10-30` for the
verified implementation described here. GitHub `main` contains a separate workflow
implementation. See the [checkpoint note](docs/GITHUB_CHECKPOINT_2026-10-30.md)
before combining versions; the existing evidence does not verify a merged version.

The [30 October requirements/readiness review](docs/FINAL_READINESS_REVIEW.md)
maps the course/proposal commitments to dated evidence. Its baseline identified two partial
items: account deletion and ADMIN-authenticated import initiation. Current admin
pages monitor imports; loading remains a trusted local CLI operation. The
[final demo checklist](docs/FINAL_DEMO_CHECKLIST.md) records passed technical checks
and the pending timed team presentation.
That review itself did not rerun application tests or add features. A subsequent
[30 October account-deletion milestone](docs/ACCOUNT_DELETION.md) implemented the
restricted API and browser controls: **183 automated tests, 29 native assertions
and 23 live-database HTTP checks passed**. The approved browser follow-up then
passed **238 cumulative checks on 30 October**, with reviewed desktop/mobile
screenshots and fixture cleanup. The later [admin local-import milestone](docs/ADMIN_IMPORT.md)
passed **196 automated tests and 32 native auth/CLI/ETL checks** on isolated fixtures.
G1/G2 are closed. The [integrated technical rehearsal](docs/TECHNICAL_REHEARSAL.md)
then passed **202 automated tests, 238 browser checks and all selected native
case/fleet/account/import checks** on 30 October. We are now in Stage 9: manual,
source/data packaging, fresh-machine reproduction and report/slides/video work.
The manual and first source/data review candidate are now prepared; **210 automated
tests passed on 30 October**, including eight package-tool tests. The actual ZIP
contents/hashes passed local verification. Fresh installation remains pending.
The timed five-member presentation rehearsal is still pending.

The first implementation milestone is the database foundation: full raw-source
inspection, SQL schema/constraints/views/trigger, MongoDB validation/indexes,
repeatable imports, and database-only verification. Flask now provides research,
registration/login/logout, sessions and guarded admin role management. Personal
saved vehicles now have owner-scoped CRUD APIs, and MongoDB complaints have public
list/detail endpoints with filters and narrative search. Internal analyst cases
now support CRUD, complaint links, notes/findings, status history and durable
SQL/MongoDB recovery. Small fleets now have owner-scoped vehicle/recall-work-order
CRUD too. Recalls and official investigations have lists, full details and
paginated related records. The core workflow backend milestone is verified.
RecallScope now provides browser research/profile/record details, registration/
login/logout and personal saved-vehicle CRUD. The complaint explorer now exposes
full research filters, and standalone records show related vehicles, source rows
and linked recalls. Analysts/admins now have browser case CRUD, complaint selection,
notes/findings, status history and explicit save/deletion recovery. Personal fleets,
vehicle labels, recall matching and work-order tracking also have browser screens.
Admins now have user-role confirmations, current dataset inventory and filtered
import history backed by restricted read views/APIs. Public analytics now combines
monthly/component complaint charts, report links and model-year comparisons with
distinct SQL official totals. The first planned browser implementation is verified;
selected index experiments are also verified. Broader final evaluation and
delivery materials remain.
Docker is not required;
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

Complaint browsing and filtering were verified on 28 October. See
[Backend step 4](docs/BACKEND_STEP_4_COMPLAINTS.md) and its
[live verification results](docs/complaints_verification_report.json).

Recall/investigation research and SQL reader permissions were verified on
28 October. See [Backend step 5](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md) and its
[live verification results](docs/official_records_verification_report.json).

Internal analyst cases and recovery were verified on **29 October**. See
[Backend step 6](docs/BACKEND_STEP_6_ANALYST_CASES.md) and
[case verification results](docs/cases_verification_report.json).

Fleet/vehicle/work-order CRUD and concurrency were verified on **29 October**.
See [Backend step 7](docs/BACKEND_STEP_7_FLEETS.md) and
[fleet verification results](docs/fleets_verification_report.json).

The first browser interface was verified on **29 October**. See
[Frontend step 1](docs/FRONTEND_STEP_1.md) and its
[real-browser verification results](docs/frontend_step_1_verification_report.json).

The complaint explorer and standalone record relationships were verified on
**29 October**. See [Frontend step 2](docs/FRONTEND_STEP_2.md) and its
[71 real-browser checks](docs/frontend_step_2_verification_report.json), including
the earlier research/auth/saved journeys.

The analyst workspace was verified on **29 October**. See
[Frontend step 3](docs/FRONTEND_STEP_3.md) and its
[115 real-browser checks](docs/frontend_step_3_verification_report.json), including
the earlier journeys and controlled case recovery failures.

Fleet/work-order browser workflows were verified on **29 October**. See
[Frontend step 4](docs/FRONTEND_STEP_4.md) and its
[163 real-browser checks](docs/frontend_step_4_verification_report.json), including
the earlier journeys, personal owner boundaries, deletion/cascades and uncertain
write handling.

Admin roles/dataset/import views and monitoring read APIs were verified on
**29 October**. See [Frontend step 5](docs/FRONTEND_STEP_5.md) and its
[195 browser checks and native admin assertions](docs/frontend_step_5_verification_report.json).
That milestone passed 159 automated tests.

The analytics dashboard/counting rules were verified on **29 October**. See
[Frontend step 6](docs/FRONTEND_STEP_6.md) and its
[219 browser checks and native analytical assertions](docs/frontend_step_6_verification_report.json).
That milestone passed 170 automated tests. A subsequent **29 October** performance
milestone compared four query workloads with 30 measured samples per phase and
added a verified complaint pagination index. The automated suite then passed
**177 tests**; browser checks were not rerun for this index-only application change.
See [performance results, plans and figures](docs/PERFORMANCE_EVALUATION.md).
The later integrated rehearsal completed the defined Stage 8 technical milestone;
Stage 9 delivery remains in progress.

## What should I run now?

**The setup and full imports were already run on this computer on 25 October
2026. You do not need to repeat the entire setup sequence.** The instructions
below also let a teammate reproduce the project on a new computer. Flask and its
SQL reader were also installed/configured here on 28 October. Authentication
storage and credentials have now been prepared here too.
Saved-vehicle workflow access has also been prepared; no reimport is needed.
Case migration 003, a separate case SQL role and the MongoDB case validator were
applied locally on 29 October. Restart Flask for the updated case routes.
The workflow role's fleet/work-order grants were also updated here on 29 October.
No schema rebuild, new credentials or reimport is needed for this fleet milestone.
The complaint pagination index was also added here on 29 October; no restart or
reimport is needed for that change. An existing teammate installation can add/check
it with `scripts/setup_complaint_order_index.py`; new database setup includes it.
Restricted account deletion was applied locally on 30 October through migration
004 (schema version 4). Restart Flask for its new route/UI; no reimport or credential
change is needed. For an existing teammate setup, run
`scripts/setup_account_deletion.py` once; fresh database/auth setup includes it.

To open the application, stop an older Flask process with Ctrl+C, then run:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Keep that terminal running and open [RecallScope](http://127.0.0.1:5000/) in your
browser. Click **Try 2022 Honda Civic**, then **View safety profile**. You can browse
record categories/full details, sign in with your existing application account,
save the vehicle, and open **My vehicles** to rename or remove bookmarks. Browser
registration is available if you have not created an account. Database credentials
from `.env` are separate from that application email/password.

Click **Complaints** for the full explorer, or **Filter complaints** in a selected
vehicle profile to carry its vehicle fields over. Individual record pages expose
full complaint text/provenance, related vehicles, recall source rows and linked
recall campaigns. See the [research walkthrough](docs/FRONTEND_STEP_2.md).

To use **Analyst cases**, sign in as ANALYST or ADMIN. Ordinary registration stays
NORMAL_USER. A later read-only check on 29 October confirmed that one ADMIN and
one NORMAL_USER are now stored here; use your existing admin account for cases.
On a fresh setup with no admin, create the first one with a new email and hidden
password prompts:

```powershell
.\.venv\Scripts\python.exe scripts/create_admin.py
```

The helper refuses if an admin already exists. Sign in with that new admin account
to use cases directly. Existing admins can assign analyst roles through the admin
API or **Admin → User roles**. See the
[case browser walkthrough](docs/FRONTEND_STEP_3.md) for the forms and recovery controls.

For **My fleets**, use any existing application account, including NORMAL_USER.
Create a fleet, search/select a catalogue vehicle, give it a label and create a
work order from its recall matches. The
[fleet browser walkthrough](docs/FRONTEND_STEP_4.md) explains filters, timestamps,
ownership and confirmed removal of dependent records.

For **Admin**, sign in with the existing administrator account. **Datasets** shows
current stored counts, **Import history** shows recorded attempts and **User roles**
lets you review/confirm a teammate's role change. Normal users and analysts cannot
read those protected views. The existing reader received the new monitoring views/
SELECT grants locally on 29 October; no rebuild/reimport or new password is needed.

For public charts, choose **Analytics → Try 2022 Honda Civic**, or open analytics
from a vehicle profile. Select exact make/model, optional year and inclusive UTC
received dates. Component bars and monthly points open their complaint evidence.
Complaint date filters do not filter the all-stored-date recall/investigation
counts. See [counting rules and coverage](docs/FRONTEND_STEP_6.md).

The [JSON profile](http://127.0.0.1:5000/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC)
is still available for API inspection. The root `/` now shows HTML; JSON discovery
moved to `/api`. If the home address still shows JSON, restart the older Flask
process and reload the browser. Press Ctrl+C to stop Flask; stored data remains.

Runtime uses the existing Flask/Python packages and local CSS/JavaScript, with no
frontend installation/build step. Node/Chrome are used only by the optional browser
verifier. The terminal clients below also remain available; browser and terminal
clients maintain separate sign-in cookies.

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

To browse complaints without signing in, open
[the Civic complaint list](http://127.0.0.1:5000/api/complaints?year=2022&make=HONDA&model=CIVIC&pageSize=5)
in the browser. Add `&component=STEERING` for a component filter or `&q=steering`
for narrative text search. Open `/api/complaints/{odiNumber}` using an ID from the
list for the full narrative. Restart Flask to load the new routes; no setup or
reimport is needed. See [all filters and examples](docs/BACKEND_STEP_4_COMPLAINTS.md).

For official records, open [Civic recalls](http://127.0.0.1:5000/api/recalls?year=2022&make=HONDA&model=CIVIC)
or [Civic investigations](http://127.0.0.1:5000/api/investigations?year=2022&make=HONDA&model=CIVIC).
Follow an item's `detailUrl`, then the detail's `links.vehicles` or `links.records`
paths. New research views/reader grants are already applied on this computer;
restart Flask to load the routes. See [Backend step 5](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md).

To try internal cases, use an ANALYST or ADMIN application account and run:

```powershell
.\.venv\Scripts\python.exe scripts/try_cases.py
```

The menu manages cases, linked complaints, notes/findings, tags, status history
and pending operation retries. It retains changes after logout. Normal registered
accounts need an administrator to assign analyst access; if none exists, use the
existing local `scripts/create_admin.py` helper to bootstrap the first admin with
a new email/password. No default analyst/admin account is seeded. See
[the full case walkthrough](docs/BACKEND_STEP_6_ANALYST_CASES.md).

To try personal fleet recall tracking with your existing account:

```powershell
.\.venv\Scripts\python.exe scripts/try_fleets.py
```

All human roles can manage their own fleets, including NORMAL_USER. The menu
creates/renames/deletes fleets and labelled fleet vehicles, lists recall matches,
and creates/updates/removes work orders. Records persist after logout. Fleet/vehicle
deletions include their dependent orders, as labelled in the menu. See
[the fleet walkthrough](docs/BACKEND_STEP_7_FLEETS.md) for IDs, matching and ownership.

If the helper reports missing fleet routes, stop the older Flask server with
Ctrl+C and run the startup command above again. Keep that server terminal open
and rerun the helper in a second terminal. The helper checks these routes before
sign-in; [generic 404 troubleshooting](docs/BACKEND_STEP_7_FLEETS.md#troubleshooting-a-generic-404)
explains how to distinguish a missing route from a missing record. Restarting
Flask retains database records and does not require setup/import commands.

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
| `setup_readonly_user.py` | Prepare the restricted SQL reader, research views and admin monitoring projections. | Creates/reuses a role, applies views and SELECT grants; retains records and an existing reader password in ignored `.env`. | Initial API setup or intentional view/grant update; monitoring views/grants applied here on 29 October. |
| `setup_auth.py` | Apply session storage and prepare auth credentials/signing key in ignored `.env`. | Adds the session table and restricted SQL role; retains existing data. | Once before authentication on a fresh setup; already run here. |
| `setup_workflow.py` | Prepare limited personal saved-vehicle/fleet/work-order SQL access. | Adds specific grants and preserves local credentials/records. | Initial personal-workflow setup or an intentional grant update; fleet grants already applied here on 29 October. |
| `setup_cases.py` | Apply case revisions/outbox, limited SQL access and the MongoDB case validator/index. | Additive schema/permissions; generates case credentials in ignored `.env`, retains records. | Once before case use on a fresh/older checkout; already applied here on 29 October. |
| `python.exe -m flask --app backend:create_app run` | Start the backend server for research and authentication requests. | Keeps running; startup does not reset/import data. Authentication requests can create users/sessions or change roles. | When using the web API. |
| `try_auth.py --register` | Try local registration, current-user lookup and logout through the running API. | Creates a persistent normal account; the demo logs its session out. | To create/try your own application account. |
| `try_auth.py` | Try an existing account's login/current-user/logout flow. | Opens then revokes the demo's session; retains the account. | To try login. |
| `try_saved_vehicles.py` | Sign in and manage your personal saved vehicles through a menu. | Saves/renames/removes only records you choose; retains them on logout. | When trying the saved-vehicle workflow. |
| `try_cases.py` | Sign in as analyst/admin and manage cases/content or retry pending changes. | Persists the actions you choose; sign-out retains cases. A case delete reconciles SQL and MongoDB through an operation task. | When trying internal analyst cases. |
| `try_fleets.py` | Sign in and manage personal fleets, fleet vehicles, recall matches and work orders. | Persists chosen changes; fleet/vehicle deletion cascades to their dependent records. | When trying fleet recall tracking. |
| `create_admin.py` | Prompt locally for the first administrator's email/password. | Creates a persistent ADMIN; refuses if an administrator already exists. | When bootstrapping the first administrator. |
| `admin_import.py` | Sign in as an application ADMIN, review approved source hashes and confirm the shared import pipeline. | Intentional reference-data upserts with per-stage audit rows; no reset. Earlier stages/MongoDB batches may remain after a later failure. | Only when deliberately refreshing the approved snapshot; not ordinary app startup. |
| `verify_api.py` | Test HTTP requests against a temporary local server and the live databases. | Reads project records; replaces `docs/api_verification_report.json`; stops its server afterward. | After relevant API changes or to reproduce its evidence. |
| `verify_auth.py` | Verify auth/role behavior over real HTTP and check local helper flows. | Creates/removes owned synthetic accounts/sessions; replaces `docs/auth_verification_report.json`. | After authentication changes or to reproduce its evidence. |
| `verify_saved_vehicles.py` | Verify owner CRUD, cross-user denials and the saved-vehicle menu over HTTP. | Creates/removes owned synthetic accounts/saves; replaces its evidence report. | After saved-vehicle changes. |
| `verify_complaints.py` | Compare complaint lists, details and combined filters with real MongoDB queries over HTTP. | Reads existing data; replaces `docs/complaints_verification_report.json`; stops its temporary server. | After complaint API changes. |
| `verify_official_records.py` | Verify recall/investigation HTTP requests, relationships and SQL reader permissions. | Reads data/grants and uses inline SQL edge cases; replaces its report and stops its server; inserts no stored fixtures. | After official-record API/view/grant changes. |
| `verify_cases.py` | Verify role/owner/admin case CRUD, concurrency, failure recovery and the terminal helper. | Creates/removes owned synthetic accounts/cases/content/tasks; writes a new dated report; leaves existing records alone. | After case/recovery changes. |
| `verify_fleets.py` | Verify fleet/vehicle/order ownership, SQL constraints/cascades, concurrent writes and the menu. | Creates/removes owned synthetic accounts/workflow rows; records its report and retains existing data. | After fleet/work-order changes. |
| `verify_frontend.py` | Check browser journeys; `--research`, `--cases`, `--fleets`, `--admin`, `--analytics` progressively include later workflows. | Owns/stops its server/browser, cleans synthetic data and records separate milestone evidence. Native admin checks use isolated/rolled-back SQL fixtures; native analytics uses an owned temporary MongoDB collection. | After relevant changes; optional verification tooling, not application setup. |
| `safety_profile.py` | Look up a vehicle using both databases. | Reads existing data and prints the result. | Whenever you want to try the current vehicle query. |
| `package_project.py` | Export the current source, approved data, dictionaries, manual and evidence into a checked review ZIP. | Reads files, writes a new ignored dated package; no database connections/import/reset. `--verify <zip>` checks an existing archive. | To prepare/recheck the source/data/manual candidate. |
| `python.exe -m unittest discover -s tests -v` | Test API behavior with fake connections and transformations with made-up records. | Does not connect to or change the databases. | After relevant code changes, or to see the automated tests run. |

The import uses **upserts**: update an imported record if its identifier already
exists, otherwise insert it. Rerunning the same files was verified to preserve
entity counts, although it still performs writes and adds log entries. It can
replace imported reference-field values with the source-file values; it is not
just a test. It does not clear users, saved vehicles, analyst cases, fleets or work
orders. There is no need to run it as part of an ordinary query or testing session.

## Documents

- [Beginner guide and living progress tracker](PROJECT_GUIDE.md)
- [User manual: first install, daily use and troubleshooting](USER_MANUAL.md)
- [Teammate fresh-install checklist, still pending execution](docs/FRESH_SETUP_CHECKLIST.md)
- [Source/data/manual packaging and verification](docs/SUBMISSION_PACKAGE.md)
- [Read-only backend step, endpoints and walkthrough](docs/BACKEND_STEP_1.md)
- [Authentication, roles and interactive walkthrough](docs/BACKEND_STEP_2_AUTH.md)
- [Saved-vehicle CRUD, ownership and interactive menu](docs/BACKEND_STEP_3_SAVED_VEHICLES.md)
- [Complaint browsing, filters, narrative search and details](docs/BACKEND_STEP_4_COMPLAINTS.md)
- [Recall/investigation details, related records and SQL reader views](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md)
- [Internal analyst cases, content, roles and cross-database recovery](docs/BACKEND_STEP_6_ANALYST_CASES.md)
- [Small fleets, recall matching, work orders and ownership](docs/BACKEND_STEP_7_FLEETS.md)
- [Browser research, sign-in, personal saves and screenshots](docs/FRONTEND_STEP_1.md)
- [Complaint explorer and official-record relationships](docs/FRONTEND_STEP_2.md)
- [Analyst case workspace, access setup and recovery controls](docs/FRONTEND_STEP_3.md)
- [Personal fleet vehicles, recall matching and work-order browser screens](docs/FRONTEND_STEP_4.md)
- [Admin roles, dataset inventory and import history](docs/FRONTEND_STEP_5.md)
- [Complaint analytics, model-year comparisons and counting rules](docs/FRONTEND_STEP_6.md)
- [Inspect the stored databases in pgAdmin and MongoDB Compass](docs/INSPECTING_DATABASES.md)
- [Approved implementation scope](docs/IMPLEMENTATION_GREENLIGHT.md)
- [Source-data findings and import scope](docs/DATA_INSPECTION.md)
- [Physical data model and ERD](docs/DATABASE_DESIGN.md)
- [Machine-readable source profile](docs/data_profile.json)
- [Original understanding/handoff](PROJECT_UNDERSTANDING_AND_PLAN.md)

## First-time setup on a new machine (Windows PowerShell)

For a complete linear walkthrough through application credentials and browser
checks, use [section 2 of the manual](USER_MANUAL.md#2-first-installation-on-another-windows-computer).
These technical sections remain references for the individual scripts.

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
.\.venv\Scripts\python.exe scripts/setup_cases.py
```

This has already been done here. Its password is generated into ignored `.env`;
you do not need to send it in chat. Research uses `APP_POSTGRES_*`, authentication
uses `AUTH_POSTGRES_*`, personal workflow requests use `WORKFLOW_POSTGRES_*`, and
case requests use `CASE_POSTGRES_*`. Construction/import scripts use `POSTGRES_*`.
The signing key is generated locally; preserve it across normal server restarts.
If updating a checkout from before backend step 5, rerun only
`scripts/setup_readonly_user.py` to apply the public research views and reader
grants. This update is already applied here; no import or table reconstruction
is needed.
For an existing pre-case checkout, `scripts/setup_cases.py` adds migration 003,
case-role grants and the case validator while retaining stored records. This
upgrade is also already applied here.
For a checkout from before the fleet milestone, rerun `scripts/setup_workflow.py`
once to add fleet/vehicle/order grants to the existing workflow role. This leaves
its password and data intact and is already applied here.

Start Flask with the command near the top of this README. API routes are:

- `GET /` and `/vehicles` — HTML search interface.
- `GET /vehicles/profile`, `/login`, `/register`, `/saved-vehicles` — browser page shells using the API routes below.
- `GET /complaints`, `/complaints/{odiNumber}`, `/recalls/{campaignNumber}`, `/investigations/{investigationNumber}` — research/explorer/detail page shells.
- `GET /cases`, `/cases/new`, `/cases/{caseId}` — internal analyst workspace shells; private data/actions require the ANALYST/ADMIN APIs.
- `GET /fleets`, `/fleets/{fleetId}`, `/work-orders/{workOrderId}` — personal fleet/order page shells using owner-scoped APIs; available to all signed-in roles.
- `GET /admin`, `/admin/users`, `/admin/imports` — admin shells; stored account/inventory/import data comes from ADMIN-only APIs.
- `GET /analytics` — public complaint charts, incident attributes and model-year comparison.
- `GET /api/analytics/vehicle` — public read-only aggregate; required exact `make`, `model`, inclusive `receivedFrom`/`receivedTo`; optional `year`. The date window spans at most 120 calendar months. See [the analytics API contract](docs/FRONTEND_STEP_6.md#new-read-only-api-and-queries).
- `GET /api` — JSON service/discovery links (formerly at `/`).
- `GET /api/health` — readiness of both databases.
- `GET /api/vehicles/search?year=2022&make=HONDA&model=CIVIC` — exact-filter vehicle search; optional bounded pagination.
- `GET /api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC` — combined vehicle safety profile.
- `GET /api/complaints?year=2022&make=HONDA&model=CIVIC&pageSize=5` — paginated complaints; vehicle/component/receipt-date/incident filters and `q` narrative search.
- `GET /api/complaints/{odiNumber}` — full complaint narrative and selected source provenance.
- `GET /api/recalls` — paginated recall campaigns, optionally filtered by vehicle, component, manufacturer, report dates or flags.
- `GET /api/recalls/{campaignNumber}` — full recall details, component names and related-record counts/links.
- `GET /api/recalls/{campaignNumber}/vehicles` and `/records` — paginated vehicle identities and component/source records.
- `GET /api/investigations` — paginated official investigations, optionally filtered by vehicle, component, manufacturer, opening dates, status or type.
- `GET /api/investigations/{investigationNumber}` and `/vehicles` — official investigation details and paginated related vehicles.

Those research endpoints remain read-only and public. Authentication also provides:

- `GET /api/auth/csrf` — request-protection token; keep the returned cookie.
- `POST /api/auth/register` and `POST /api/auth/login` — JSON email/password, CSRF header and matching cookie.
- `GET /api/auth/me` and `POST /api/auth/logout` — current account and session revocation.
- `GET /api/admin/users` and `PATCH /api/admin/users/{userId}/role` — ADMIN only.
- `GET /api/admin/datasets` — ADMIN-only current reference counts, source archive names and latest import attempts.
- `GET /api/admin/import-runs` — ADMIN-only paginated audit attempts; optional `dataset`, `status`, `page`, `pageSize` filters. Monitoring methods are read-only.

Supported state-changing requests require `X-CSRF-Token`. Successful sign-in
rotates it; retain the returned token/cookie. [Backend step 2](docs/BACKEND_STEP_2_AUTH.md)
explains requests, role rules, the first-admin bootstrap and the local demo.
Signed-in personal CRUD is now available through `GET/POST /api/saved-vehicles`
and `GET/PATCH/DELETE /api/saved-vehicles/{savedVehicleId}`. The owner is derived
from the session; foreign records return 404. See
[Backend step 3](docs/BACKEND_STEP_3_SAVED_VEHICLES.md).

Case APIs are restricted to ANALYST/ADMIN and live under `/api/analysis-cases`:

- `GET/POST /api/analysis-cases` and `GET/PATCH/DELETE /api/analysis-cases/{caseId}`.
- Complaint link/unlink, note/finding CRUD, tags/components and paginated status history under the case ID.
- `GET /api/analysis-cases/operations` and `GET /operations/{operationId}` under the same prefix.
- `POST /api/analysis-cases/operations/{operationId}/retry`, JSON `{}`, to finish a pending change.

Case changes require a UUID `Idempotency-Key` as well as CSRF and session cookies.
The helper handles these. Completed writes return an operation receipt (201 for
create, 200 for other changes); 202 means SQL saved the intent and synchronization
or acknowledgement is still pending. Retry that operation, or repeat an uncertain
command using the original request key, rather than making a duplicate request.
Analysts manage cases they created; admins can inspect/manage/recover all cases.
This override applies to cases, while personal saves remain strictly owner-scoped.
See [Backend step 6](docs/BACKEND_STEP_6_ANALYST_CASES.md) for exact routes/limits,
durable outbox behavior and deletion recovery.

Personal fleet APIs share the existing limited workflow SQL role:

- `GET/POST /api/fleets` and `GET/PATCH/DELETE /api/fleets/{fleetId}`.
- `GET/POST /api/fleets/{fleetId}/vehicles` and `GET/PATCH/DELETE /api/fleet-vehicles/{fleetVehicleId}`.
- `GET /api/fleets/{fleetId}/recall-matches` with optional vehicle/tracked filters.
- `GET/POST /api/work-orders` and `GET/PATCH/DELETE /api/work-orders/{workOrderId}`.

Every signed-in role manages only its own fleet data; ADMIN has no personal
override. Orders derive their model-year from the owned vehicle/matching recall.
SQL uniqueness/composite foreign keys protect that pairing. All writes require
CSRF/session cookies. See [Backend step 7](docs/BACKEND_STEP_7_FLEETS.md) for exact
inputs, pagination, status timestamps and deletion cascades.

## Automated API and transformation tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The 202 current tests cover page/API boundaries and headers, research/admin/analytics APIs and counting rules, authentication/account deletion, admin import controls, personal/case/fleet
ownership, case content/recovery, fleet/order lifecycle and validation, filters,
SQL parameters, CSRF/cookies, role changes, ETL rules and benchmark measurement
integrity (warmup exclusion, result hashes, ownership guards and plan counters).
They do not connect to
local databases.

To reproduce actual HTTP checks using both live databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_api.py
```

For live authentication and permission checks:

```powershell
.\.venv\Scripts\python.exe scripts/verify_auth.py
```

These verifiers start/stop their own servers and record results. The auth verifier
creates/removes synthetic users/sessions. Neither reruns imports. Broader user
journeys, broader final evaluation and final submission artifacts remain.
Controlled index experiments have separate evidence below. Case/fleet behavior has separate verifiers
below, preserving each milestone's recorded evidence.

To reproduce saved-vehicle CRUD/ownership checks against live databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_saved_vehicles.py
```

This verifier also tests the interactive saved-vehicle menu and cleans up only
its generated accounts/records. Existing personal saves and source data remain.

To reproduce complaint API checks against the imported data:

```powershell
.\.venv\Scripts\python.exe scripts/verify_complaints.py
```

This uses a temporary local server and read-only requests, checks stored counts
before/after, and records `docs/complaints_verification_report.json`. It does not
insert fixtures, change credentials, or rerun imports. Its report preserves the
complaint milestone's verification date.

To reproduce recall/investigation checks against PostgreSQL and check reader grants:

```powershell
.\.venv\Scripts\python.exe scripts/verify_official_records.py
```

This starts/stops a temporary local server, checks read-only requests and SQL
permissions, and records `docs/official_records_verification_report.json`. It
inserts no stored fixtures or imports. Its historical report records that milestone.

To reproduce internal-case and recovery checks using both actual databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_cases.py
```

The verifier creates temporary synthetic accounts and case records, tests
cross-user denials/admin access, MongoDB content CRUD, SQL history, concurrent
requests, failure injection and fresh-server recovery, then removes only its own
fixtures. It now records a new dated `docs/verifications/cases/<run>/report.json`,
retaining the historical milestone report. Native database services
stay running; injected failures are controlled at the service boundary.

To reproduce personal fleet/work-order checks using the native databases:

```powershell
.\.venv\Scripts\python.exe scripts/verify_fleets.py
```

This checks owned CRUD, foreign-user/admin denials, model-year matching, native
constraints/cascades, completion timestamps, concurrent writes and the real menu.
It removes its generated fixtures and records a new dated
`docs/verifications/fleets/<run>/report.json`, retaining the historical milestone.
The first planned research/auth/saved/case/fleet/admin/analytics interface is
verified. Selected-query performance evaluation is also verified; broader final
evaluation, refinements and deliverables remain planned.

To reproduce the real browser journeys, with Node.js 22+ and installed Chrome/Edge:

```powershell
.\.venv\Scripts\python.exe scripts/verify_frontend.py
.\.venv\Scripts\python.exe scripts/verify_frontend.py --research
.\.venv\Scripts\python.exe scripts/verify_frontend.py --cases
.\.venv\Scripts\python.exe scripts/verify_frontend.py --fleets
.\.venv\Scripts\python.exe scripts/verify_frontend.py --admin
.\.venv\Scripts\python.exe scripts/verify_frontend.py --analytics
```

This uses local DevTools automation, real APIs and the native databases. It creates
owned synthetic accounts and personal saves, removes its fixtures, and records
`docs/frontend_step_1_verification_report.json` plus public-page screenshots for the
first command. The `--research` command includes those checks and the new research
journeys, writing `docs/frontend_step_2_verification_report.json` and separate
screenshots so the first milestone's historical evidence remains intact.
The `--cases` command includes those journeys and analyst cases/content/history/
receipts. It uses temporary analyst/admin accounts and controlled recovery faults
only in its owned server, then removes those fixtures. Its evidence is
`docs/frontend_step_3_verification_report.json` with separate screenshots.
The `--fleets` command adds personal fleet/vehicle/match/order journeys, account
boundaries, dependent-record deletion and uncertain-write review. It writes
`docs/frontend_step_4_verification_report.json` and separate screenshots. Earlier
milestone reports/screenshots are preserved when this option is used.
The `--admin` command includes all previous journeys plus protected admin data,
role confirmations, uncertain-response review, self-demotion and session cleanup.
Native checks cover view-only SQL access, sanitized audit projections and the
last-admin guard using rolled-back/temporary SQL fixtures. Existing user roles and
import history are retained. Evidence is `docs/frontend_step_5_verification_report.json`.
The `--analytics` command adds chart/report links, keyboard drill-throughs,
comparison/coverage checks, zero/partial months and stale-response handling. Native
queries independently check counts; a validator-backed temporary complaint
collection checks unknown/missing/boundary cases and is removed. Evidence is
`docs/frontend_step_6_verification_report.json`; earlier evidence stays intact.
It does not stop your separate Flask terminal or change/import source records.
Selected-query performance results have [separate evidence](docs/PERFORMANCE_EVALUATION.md).
Broader final evaluation and submission materials remain. See
[Frontend step 1](docs/FRONTEND_STEP_1.md) and
[Frontend step 2](docs/FRONTEND_STEP_2.md) and
[Frontend step 3](docs/FRONTEND_STEP_3.md) and
[Frontend step 4](docs/FRONTEND_STEP_4.md) and
[Frontend step 5](docs/FRONTEND_STEP_5.md) and
[Frontend step 6](docs/FRONTEND_STEP_6.md) for tested scope and verification limits.

## Controlled index performance evaluation

The 29 October run measured two PostgreSQL recall queries and two MongoDB complaint
date windows on full-sized copies, preserving the app's data/indexes throughout
the comparisons. It retained every raw sample and query plan, removed its owned
copies and checked original counts/index definitions. A separate live follow-up
then added `vehicle_received_ordered(modelYearId:1, receivedDate:-1, _id:-1)`,
checked real complaint pages/counts/order and retained every prior index.

To reproduce the copy experiment (not needed for normal app use):

```powershell
.\.venv\Scripts\python.exe scripts/benchmark_databases.py
```

To add/check that index on an existing installation, without resetting/importing:

```powershell
.\.venv\Scripts\python.exe scripts/setup_complaint_order_index.py
```

Both commands create new dated evidence directories. The benchmark can temporarily
use several hundred MB of disk for the copied tables/collection and normally removes
its copies in `finally`. A forced process kill/power loss can leave its unique
`bench_<uuid>` namespace; identify ownership from its report before manual cleanup.
Do not run imports/concurrent writes during measurement. This uses the trusted
local setup credentials for temporary DDL; web roles are unchanged.

Optional standalone PNG/SVG figures and CSV require extra evaluation packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-evaluation.txt
.\.venv\Scripts\python.exe scripts/plot_benchmarks.py docs/benchmarks/<run_id>/report.json
```

Replace `<run_id>` with the printed run directory. The app's runtime requirements
do not include plotting packages. The [performance report](docs/PERFORMANCE_EVALUATION.md)
links the saved figures and explains warm-cache timings, plan counters, index
storage cost, measured scope and remaining evaluation limits.

## Restricted account deletion

Admins can delete another unused account after confirming its email. Any saved
vehicles, fleets, cases or operation history block deletion. Self/last-admin
protection applies; successful deletion revokes all target sessions. There is no
force-delete option and no direct auth-role DELETE grant on `app_user`.
See the [policy, API, migration and dated evidence](docs/ACCOUNT_DELETION.md).

```powershell
# Existing installation only; already applied here on 30 October. No import/reset.
.\.venv\Scripts\python.exe scripts/setup_account_deletion.py
# Native guard/concurrency and actual SQL-backed HTTP checks; owned fixtures only.
.\.venv\Scripts\python.exe scripts/verify_account_deletion.py
.\.venv\Scripts\python.exe scripts/verify_account_api.py
# Cumulative browser acceptance, verified on 30 October; owned fixtures only.
.\.venv\Scripts\python.exe scripts/verify_frontend.py --accounts
```

The account helpers write separate dated evidence; `--accounts` includes all prior
journeys and saves screenshots/report under a new `docs/account_deletion/browser-<run>/`
directory. It preserves earlier milestone reports. It starts/stops only its own
temporary server/browser, cleans its synthetic accounts and checks original counts.
The [30 October browser report](docs/account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json)
records 238 checks, no uncaught browser exceptions and retained original counts/
import history. Earlier pending/failed runs are preserved, and verifier-only
readiness/viewport corrections are documented in the
[follow-up summary](docs/account_deletion/browser-20261030T023324-1a1c57a4/followup_summary.json).
Earlier automated/native/API checks were not repeated for those verifier changes.
Restart your own Flask process before trying the new route and controls.
The [subsequent admin-import milestone](docs/ADMIN_IMPORT.md) closes G2 through a
role-checked local helper; final overall evaluation and deliverables remain.

## Admin-authenticated local import

For an intentional refresh after setup, keep Flask and both databases running:

```powershell
.\.venv\Scripts\python.exe scripts/admin_import.py
```

Use an existing ADMIN application's email/hidden password, review the four approved
local ZIPs and type `IMPORT` to start. Any other confirmation cancels. The helper
rechecks current access and inspected archive hashes, then takes the same session
lock/pipeline as the trusted first-setup importer. Normal users/analysts cannot
initiate this workflow. Import history documents the terminal command and reads
per-stage outcomes; the page itself does not start a web job.

This is not needed for normal app startup or to continue development. Data is
already loaded here. A requested import upserts reference records, and a later
failure can leave earlier stages or MongoDB batches committed. There is no single
rollback covering both DBMSs. Local trusted setup credentials remain required;
application SQL grants/schema version/runtime requirements are unchanged.
Fresh installation still follows the earlier `import_all.py` setup sequence before
application accounts are available.

See [the policy, workflow, failure limits and evidence](docs/ADMIN_IMPORT.md).
The 30 October milestone passed 196 automated tests and 32 native real-auth/CLI/ETL
checks. It verified success, repeat imports, role/session refusal, cancellation,
locking and actual MongoDB failure/audit behaviour using five synthetic rows in
owned databases. The real source ZIPs were only hashed; existing project records
and audit history were retained. No production-source reimport was run.

To reproduce its isolated checks:

```powershell
.\.venv\Scripts\python.exe scripts/verify_admin_import.py
```

This creates/removes owned fixtures and writes new dated `docs/admin_import/<run>/`
evidence. It uses its own localhost server, retaining your Flask process. The
cumulative browser verifier was not rerun for this CLI/static-instructions change;
the earlier 238-check evidence keeps its original timestamp.

## Integrated technical rehearsal

To run the current acceptance set with owned fixtures and a new evidence index:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_project.py
```

This sequentially runs the current unit suite, native case/fleet checks, account
database/API guards, isolated admin-import ETL and the cumulative browser journeys.
It records code/data fingerprints, configuration consistency and original record
counts around the run. It checks saved performance-plan/sample integrity and current
result equivalence without rerunning benchmark timings or a full real-data import.
Existing servers/data are retained; child verifiers stop their owned servers/browser
and remove synthetic records. Avoid editing code/config or changing app records
during the run. Evidence goes into a new `docs/rehearsals/<run>/report.json`.

The **30 October** run passed 202 automated tests, 238 browser checks, native case
recovery after API-server recreation, fleet concurrency/constraints, account guards
and real fixture-ETL success/failure paths. All four representative benchmark result
sets still matched their stored hashes, and 20 saved plans matched their metrics.
See [results, source snapshot, limits and next delivery work](docs/TECHNICAL_REHEARSAL.md).
This does not establish a teammate's fresh installation or a timed team presentation.

Case/fleet native verifiers accept `--report-path docs/<new-path>.json` for a
specific output destination and reject existing files. Their defaults are now
dated directories rather than overwriting the old fixed milestone JSON files.
