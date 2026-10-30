# Code map: where each part lives

**Updated:** 30 October 2026. This is a navigation guide, not a new feature milestone.
Use [the manual](../USER_MANUAL.md) to run the application and
[the technical reference](TECHNICAL_REFERENCE.md) for command/API details.

## Follow one request

When a user opens a vehicle profile, Flask serves a template; local JavaScript
requests an API; Python queries PostgreSQL/MongoDB and returns JSON. Templates
describe the page, JavaScript handles interaction, and services perform database
work. Each is a different responsibility, so related files are grouped by feature
rather than combined into one large program.

| Folder/file | Responsibility |
| --- | --- |
| [backend/__init__.py](../backend/__init__.py) | Create/configure Flask; register routes, request protection, cleanup and error handling. |
| [backend/pages.py](../backend/pages.py) | Serve the browser page templates. |
| [project_config.py](../project_config.py) | Load private local settings and provide database connections. |
| `backend/templates/` | HTML page structures and shared layouts. |
| `backend/static/` | Local CSS, JavaScript and the SVG brand mark; no frontend build step. |
| `backend/services/` | Queries, persistence and business rules used by route handlers. |

## Find an application feature

Paths below are relative to `backend/`. Route modules validate requests and enforce
permissions; service modules perform their database work. `routes.py` contains the
original vehicle/health endpoints and shared query validation.

| Feature | Python route / service | Browser files |
| --- | --- | --- |
| Vehicle search/profile, health | `routes.py` / `services/research.py` | `templates/search.html`, `templates/profile.html`, `static/app.js` |
| Sign-in, registration, sessions, role changes, account deletion | `auth.py` / `services/auth.py` | `templates/auth.html`, `templates/admin_users.html`, `static/app.js`, `static/admin.js` |
| Personal saved vehicles | `saved_vehicles.py` / `services/saved_vehicles.py` | `templates/saved.html`, `static/app.js` |
| Complaint explorer and full narratives | `complaints.py` / `services/complaints.py` | `templates/complaints.html`, `templates/record.html`, `static/research.js` |
| Recalls/investigations and their relationships | `official_records.py` / `services/official_records.py` | `templates/record.html`, `static/research.js` |
| Analyst cases, nested content and recovery | `cases.py` / `services/cases.py` | `templates/case_base.html`, `cases.html`, `case_new.html`, `case_detail.html`, `static/cases.js` |
| Personal fleets, vehicle entries and work orders | `fleets.py` / `services/fleets.py` | `templates/fleet_base.html`, `fleets.html`, `fleet_detail.html`, `work_order.html`, `static/fleets.js` |
| Admin dataset/import monitoring | `administration.py` / `services/administration.py` | `templates/admin_base.html`, `admin_overview.html`, `admin_imports.html`, `static/admin.js` |
| Complaint charts/model-year comparisons | `analytics.py` / `services/analytics.py` | `templates/analytics.html`, `static/analytics.js` |
| Shared request/UI behavior | Page modules above | `templates/base.html`, `static/api.js`, `static/ui.js`, `static/app.css`, `static/mark.svg` |

## Database definitions and import pipeline

| File | What it does |
| --- | --- |
| [sql/schema.sql](../sql/schema.sql) | Initial PostgreSQL tables, keys and constraints. |
| [sql/migrations/](../sql/migrations/) | Ordered additive changes: sessions (002), case operations/revisions (003), guarded account deletion (004). |
| [sql/indexes.sql](../sql/indexes.sql) | PostgreSQL query indexes. |
| [sql/views.sql](../sql/views.sql) | Shared catalogue/summary/fleet views. |
| [sql/research_views.sql](../sql/research_views.sql) | Read-only official-record relationship views. |
| [sql/admin_views.sql](../sql/admin_views.sql) | Restricted monitoring projections. |
| [sql/triggers.sql](../sql/triggers.sql) | Record case status changes in history. |
| [mongodb/schema.py](../mongodb/schema.py) | MongoDB validators and indexes. |
| [etl/source.py](../etl/source.py) | Read the four compressed official sources and normalize values. |
| [etl/common.py](../etl/common.py) | Shared import/audit utilities. |
| [etl/catalogue.py](../etl/catalogue.py) | Build normalized make/model/year identities across sources. |
| `etl/import_recalls.py`, `import_investigations.py`, `import_complaints.py` | Load each record family; complaints merge repeated component rows into documents. |
| [etl/runner.py](../etl/runner.py) | Order the real import stages and coordinate the shared import lock. |
| `data/raw/`, `data/dictionaries/` | Approved source ZIPs and column definitions. Raw ZIPs remain local/Git-ignored. |

## Runnable Python commands

Run these from the repository root with `.\.venv\Scripts\python.exe scripts/<name>.py`.
The top-level command names are retained. Start with the manual rather than running
every command; imports/setup perform real writes and are not daily tests.

| Group | Files under `scripts/` | Purpose |
| --- | --- | --- |
| Connection check | `check_environment.py` | Check source availability and native server connections. |
| First construction | `setup_databases.py` | Apply the schema/migrations, validators, views and indexes. |
| Restricted app access | `setup_readonly_user.py`, `setup_auth.py`, `setup_workflow.py`, `setup_cases.py` | Prepare the separate SQL reader/auth/workflow/case accounts and local generated credentials. |
| Existing-install upgrades | `setup_account_deletion.py`, `setup_complaint_order_index.py` | Apply/check the specific later changes without rebuilding/importing data. |
| First admin | `create_admin.py` | Hidden-prompt bootstrap when no application administrator exists. |
| Source inspection/load | `inspect_data.py`, `import_all.py`, `admin_import.py` | Inspect files, do trusted first load, or initiate a deliberate role-checked refresh. |
| Query / interactive clients | `safety_profile.py`, `try_auth.py`, `try_saved_vehicles.py`, `try_cases.py`, `try_fleets.py` | Read a combined profile or perform real chosen account/workflow actions. |
| Native/API verification | `verify_databases.py`, `verify_mongo_schema.py`, `verify_api.py`, `verify_auth.py`, `verify_saved_vehicles.py`, `verify_complaints.py`, `verify_official_records.py`, `verify_cases.py`, `verify_fleets.py`, `verify_account_deletion.py`, `verify_account_api.py`, `verify_admin_import.py` | Verify the relevant stored data, requests, permissions and controlled failures. Some older commands replace legacy evidence files; check the technical reference first. |
| Browser verification | `verify_frontend.py` | Start owned local servers/browser and exercise synthetic user journeys; `--accounts` includes the cumulative flow. |
| Whole technical acceptance | `rehearse_project.py` | Run the selected verifiers sequentially, preserve history and record source/data consistency. |
| Index evaluation | `benchmark_databases.py`, `plot_benchmarks.py` | Measure controlled query workloads and produce saved figures. |
| Source/data delivery | `package_project.py` | Build or verify a source/data/manual ZIP against matching successful rehearsal evidence. |

## Helpers you do not run directly

| Location | Contents / purpose |
| --- | --- |
| [scripts/support/local_api.py](../scripts/support/local_api.py) | Shared localhost cookie/CSRF client for terminal demos/verifiers. |
| [scripts/support/frontend_case_fixtures.py](../scripts/support/frontend_case_fixtures.py) | Owned browser-test actors and controlled case faults. |
| [scripts/support/frontend_admin_fixtures.py](../scripts/support/frontend_admin_fixtures.py) | Owned admin actors and isolated permission/SQL assertions. |
| [scripts/support/analytics_checks.py](../scripts/support/analytics_checks.py) | Native counting checks using an owned temporary collection. |
| [scripts/support/verification_reports.py](../scripts/support/verification_reports.py) | Select new dated case/fleet evidence paths without overwriting history. |
| [scripts/browser/](../scripts/browser/) | Node/Chrome driver `browser_frontend_checks.mjs` plus research, case, fleet, admin, analytics and account check modules. Python passes fixture configuration on stdin. |
| `__init__.py` files | Mark Python packages and document their role; they are not standalone commands. |

## Tests and generated files

`tests/test_<feature>.py` contains the corresponding automated checks. Case tests
include memory-backed orchestration/faults; package/rehearsal-tool tests guard
file integrity and evidence preservation. These are different from the native/API/
browser verifiers under `scripts/`.

`docs/` is indexed [here](README.md). Historical narrative milestones are under
`docs/milestones/`; machine evidence stays at its original paths. `.venv`, Python
caches, `data/staging`, `data/logs` and `data/processed/packages` are generated/local
working material. Source ZIPs and `.env` remain private/local inputs. None of these
folders is the live PostgreSQL/MongoDB server storage.
