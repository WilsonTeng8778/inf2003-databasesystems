# RecallScope user manual

**Project:** INF2003 Group 19, Vehicle Safety Recall & Defect Investigation System.  
**Prepared:** 30 October 2026. **Scope:** native Windows/local classroom demonstration.  
**Installation status:** instructions checked against the scripts; a teammate's
fresh installation from the exported package is still pending.

RecallScope combines official recall/investigation records in PostgreSQL with
complaint documents in MongoDB. It also supports personal saved vehicles, small
fleets/work orders and internal analyst cases. It is a model-level research and
tracking tool; complaint allegations and model matches do not establish a defect,
VIN-specific applicability or repair completion.

Use the path that matches your situation:

- **Already working on this computer:** use section 1. No repeat import is needed.
- **New teammate/marker installation:** follow section 2, in order, then section 3.
- **Using the application:** sections 4–7. Troubleshooting is in section 8.
- **Preparing a source/data ZIP:** section 9. The report/video submission is separate.

Each line in a PowerShell code block is a separate command. Wait for it to finish
successfully before running the next line. Commands run from the project root,
the folder containing this manual, `project_config.py` and `requirements.txt`.

## 1. Start or stop an existing installation

Ensure the PostgreSQL and MongoDB Windows services are running, then open a terminal
in the project root:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Leave that terminal open. Visit [RecallScope](http://127.0.0.1:5000/). Use your
application email/password to sign in, rather than the database password in `.env`.
To stop Flask, press **Ctrl+C in that terminal**. Stored records remain in the
database services when Flask/VS Code closes or Windows restarts.

If you changed Python/routes/templates, stop your older Flask process and start it
again. This command does not reload code automatically. There is no frontend build
or Node installation needed for ordinary use. Docker is not required.

## 2. First installation on another Windows computer

Do this once on a dedicated project setup. Existing users should use section 1;
setup/import commands perform real writes and are not a daily startup checklist.

### 2.1 Prepare servers, Python and the extracted project

The verified existing-machine environment on 30 October was Windows 11, Python
3.13.7, PostgreSQL 18.6 and MongoDB Community 9.0.4. These are the tested versions,
not proof of compatibility with every other version. Python packages are pinned
in `requirements.txt`; record your actual versions during reproduction.

Install Python and the PostgreSQL/MongoDB **servers**, and start their Windows
services. pgAdmin and MongoDB Compass are optional inspection tools. `psql` and
`mongosh` on PATH are useful but are not required by the Python drivers.
The default connections use localhost ports **5432** and **27017**. Keep live
database storage outside the project/OneDrive folder. Use this application on the
local machine; the provided Flask server/configuration is for the class demo.

Extract `INF2003_Group19_Source_Data.zip` into a new folder. Open the included
`INF2003_Group19` folder as the project root. The package contains source, manual,
four raw archives, three dictionaries and saved evidence; installed libraries and
private configuration are deliberately generated separately on each machine.
The public raw ZIPs are unmodified sources and can contain fields that the app's
ETL does not retain/display. The ZIP is not a dump of the original developer's
users, sessions or workflow data.

After Python is available, check the ZIP using the included standard-library tool.
Replace the example path with the actual ZIP location:

```powershell
python scripts/package_project.py --verify 'C:\path\to\INF2003_Group19_Source_Data.zip'
```

Expect `"successful": true` and four verified raw archives. This reads every ZIP
member and checks its hash/manifest; it does not import data, extract files or
prove installation. Keep the original ZIP until the fresh-setup check is recorded.
A GitHub-only checkout omits `data/raw/`; use the supplied package snapshot rather
than silently replacing its sources with a newer download.

### 2.2 Create the project's Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`.venv` is a local folder of this project's Python packages. Using its explicit
`python.exe` avoids requiring PowerShell activation or changing execution policy.
Initial package installation normally needs an internet connection. Once installed
and populated, app startup/research uses local assets and databases.

### 2.3 Configure private local connections

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Open `.env` locally. Enter your PostgreSQL installation password after
`POSTGRES_PASSWORD=`. Keep the default dedicated `vehicle_safety` database names
for an otherwise fresh server. Change the connection port/user only if your own
installation differs. A single-quoted value can preserve literal special characters.
Do not send passwords in chat, screenshots or the project package.

Leave the `APP_POSTGRES_PASSWORD`, `AUTH_POSTGRES_PASSWORD`,
`WORKFLOW_POSTGRES_PASSWORD`, `CASE_POSTGRES_PASSWORD` and `FLASK_SECRET_KEY` fields
empty initially: the later setup helpers generate them locally. These restricted
SQL accounts divide research/auth/workflow/case access. They are separate from
application NORMAL_USER/ANALYST/ADMIN roles and from your browser login.

Preserve the generated `.env` across ordinary restarts. If this server already has
project databases or the named SQL roles, it is not a clean installation; do not
replace its `.env` or try to reset it to make the checklist pass.

### 2.4 Check the source snapshot and server connections

The package should contain these exact files:

| Location | Contents |
| --- | --- |
| `data/raw/` | `FLAT_RCL_POST_2010.zip`, `FLAT_INV.zip`, `COMPLAINTS_RECEIVED_2020-2024.zip`, `COMPLAINTS_RECEIVED_2025-2026.zip` |
| `data/dictionaries/` | `RCL.txt`, `INV.txt`, `CMPL.txt` field definitions |
| `docs/data_profile.json` | Inspected source hashes, layouts and counts |

Leave the ZIPs compressed; the importer reads them directly. Together they are
137,707,247 bytes, about 131.3 MiB. Allow additional disk space for Python,
uncompressed/staged complaint narratives and both databases. No fixed fresh-machine
disk/time requirement has yet been measured.

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
```

All four files should say `present`; both servers should report successful
connections. A missing `psql`/`mongosh` PATH entry alone is not a failure if those
connections succeed. Resolve connection failures before continuing.

### 2.5 Create the databases and import the supplied data

```powershell
.\.venv\Scripts\python.exe scripts/setup_databases.py
.\.venv\Scripts\python.exe scripts/import_all.py
```

Setup creates missing dedicated databases, tables/collections, constraints, views,
triggers, validators and indexes; it applies SQL migrations through version 4.
Import streams the selected records, groups repeated complaint-component rows,
and records stage outcomes in PostgreSQL `data_import_log`. Wait for completion;
this is the large first load, not a quick connection test.

The first setup uses trusted local database credentials before any application
administrator exists. Later intentional refreshes use the ADMIN helper in section 7.
Imports use **upserts**: existing source identifiers are updated and new ones are
inserted. Repeating an import performs writes and adds audit rows even when entity
counts stay the same. Earlier stages and MongoDB batches can survive a later
failure; inspect the failure and rerun the approved snapshot to complete those
upserts. Automatic removal of records absent from a different snapshot is not
implemented.

The supplied profile is already inspected. `scripts/inspect_data.py` is optional
source-analysis work and rewrites `docs/data_profile.json`; it is not required for
daily use or for importing this unchanged approved package.

### 2.6 Prepare application access and the first administrator

Run in this order, after schema/import completion:

```powershell
.\.venv\Scripts\python.exe scripts/setup_readonly_user.py
.\.venv\Scripts\python.exe scripts/setup_auth.py
.\.venv\Scripts\python.exe scripts/setup_workflow.py
.\.venv\Scripts\python.exe scripts/setup_cases.py
.\.venv\Scripts\python.exe scripts/create_admin.py
```

The first four scripts apply narrow SQL grants and store generated credentials in
your local `.env`; they retain records. Auth setup includes the guarded account
deletion function. Case setup includes its MongoDB validator/index. Fresh setup
already includes the complaint ordering index and account migration, so separate
upgrade helpers are unnecessary here.

The final command prompts for a new administrator email and hidden password
(12–128 characters), then confirmation. Choose your own application credentials.
It refuses if an administrator already exists. Regular browser registration creates
NORMAL_USER accounts; only an existing ADMIN can assign an ANALYST/ADMIN role.

Start Flask with section 1's command. Complete section 3 before claiming a successful
fresh installation.

## 3. Check the installed result

In another terminal at the project root:

```powershell
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The profile reads both databases. For the supplied snapshot, 2022 HONDA CIVIC has
**4 recalls, 2 official investigations and 885 complaints**. The automated tests
check transformations/contracts and verification/package tools using made-up inputs;
they do not replace a real database or browser check. Use the package's own dated
test evidence rather than treating an old test count as a new result.

Visit [database readiness](http://127.0.0.1:5000/api/health) and the home page.
Check research, sign-in, a saved vehicle, an analyst case and a fleet/work order
as described below. Record the actual result in
[FRESH_SETUP_CHECKLIST.md](docs/FRESH_SETUP_CHECKLIST.md), including failures and
cleanup. A check performed on the already configured developer computer does not
complete that teammate checklist.

Optional full technical acceptance is `scripts/rehearse_project.py`. It needs the
existing native servers, current setup credentials, Node.js 22+ on PATH and an
installed Chrome/Edge in the verifier's supported Windows locations. It creates
and removes owned synthetic fixtures, starts its own servers/browser and records
new dated evidence. Run it without concurrent code/data edits. It does not perform
a full real-source import. See [technical rehearsal](docs/TECHNICAL_REHEARSAL.md).

Some older individual verification scripts replace their legacy report files;
preserve packaged evidence before using them. Case/fleet and the selected account/
import/browser verifiers use new dated paths. The combined rehearsal retains its
own index. See the [README command table](README.md#what-each-command-does).

## 4. Public research and analytics

1. On the home page choose **Try 2022 Honda Civic**, then view the safety profile.
   Search uses normalized year/make/model identities, including complaint-only vehicles.
2. Open a recall, official investigation or complaint. Follow related vehicles,
   source rows and linked recalls; these are different record types.
3. Use **Complaints** or the profile's filter link. Try component STEERING, receipt
   dates, incident flags and narrative text. Open an item's full details/provenance.
4. Open **Analytics**, select exact make/model and optional year/date window.
   Component/monthly chart links lead to the underlying filtered complaints.

Complaints can mention several components, so component totals overlap. Unknown
incident/date values are not the same as false/zero. Complaint receipt-date filters
do not restrict the displayed all-stored-date recall/investigation totals. Vehicle
comparisons count distinct official campaigns/actions. These are descriptions of
the stored snapshot, not a safety ranking. See [analytics rules](docs/FRONTEND_STEP_6.md).

## 5. Accounts, saved vehicles and fleets

**Register/sign in:** register a normal account or use your chosen existing login.
Sessions expire after eight hours; sign in again when prompted. Sign out when done.
Changing an account's role takes effect on the next authenticated request.

**My vehicles:** sign in, open a profile and save it. In My vehicles rename its
nickname or remove the bookmark. Removal affects your bookmark, not official data.
Each account sees its own saves, including when the other account is an admin.

**My fleets:** any signed-in role can create its own fleet. Add a catalogue vehicle,
give the entry a physical-vehicle label, view recall matches and create a work order.
Change order status/notes and complete it. Labels distinguish entries; they are not
VIN validation. A model-level recall match is not proof a particular car needs or
has received a repair. Confirmed fleet/vehicle removal also removes dependent orders;
use disposable demo records when rehearsing deletion. Admin roles do not grant
access to another person's fleet. See [fleet walkthrough](docs/FRONTEND_STEP_4.md).

## 6. Analyst cases and saved-update recovery

Sign in as ANALYST/ADMIN and open **Analyst cases**. Create a titled case, select its
vehicle/scope, link complaints and add findings, notes, tags/components. Edit/remove
content, change status, inspect SQL status history, then close/delete a demo case
when appropriate. Analysts manage their own cases; admins have explicit case
oversight. Official complaint documents remain reference material; case content
provides the flexible MongoDB CRUD demonstration.

Case metadata/history is in PostgreSQL; flexible content is in MongoDB. A SQL
transaction cannot commit both servers together. The app records an operation and
shows pending/recovery controls when synchronization or its acknowledgement needs
another attempt. Use the displayed retry/recovery action for the same operation;
avoid submitting a new duplicate case/note after an uncertain response. A deleted
case can still have cleanup pending until its content projection is applied.
This is recoverable coordination, not a distributed atomic transaction.
See [case workflow and recovery](docs/FRONTEND_STEP_3.md).

## 7. Administrator tasks

**Datasets / Import history:** inspect stored inventory and stage outcomes. These
pages monitor imports; they do not launch a background web import job.

**User roles:** locate an account, choose its role and confirm. Keep at least one
administrator. Normal/analyst accounts cannot use admin operations. The admin
role does not remove personal save/fleet ownership boundaries.

**Delete an unused account:** review the target, enter its exact displayed email
and confirm. Self-deletion, last-admin removal and accounts with saves, fleets,
cases or operation history are blocked. Successful deletion revokes target sessions.
If the response is uncertain, inspect/reload the list before another action.
This is a guarded unused-account deletion policy; retained work/history is not
silently removed. See [account deletion](docs/ACCOUNT_DELETION.md).

**Intentional data refresh:** with Flask running, open a second terminal:

```powershell
.\.venv\Scripts\python.exe scripts/admin_import.py
```

Sign in through its hidden prompts as an application ADMIN, review the four source
fingerprints and type `IMPORT` only when you intend actual writes. Anything else
cancels before stages run. This trusted local helper also needs setup credentials
in `.env`. It rechecks authorization/source files before the shared locked pipeline.
Concurrent runs are refused; normal/analyst roles are refused. Stage commits and
MongoDB batches can remain after failure; abrupt interruption may leave a RUNNING
audit row. The helper checks permission at the start boundary, not continuously
per row. See [operator contract](docs/ADMIN_IMPORT.md).

## 8. Troubleshooting and inspection

| Symptom | Check / action |
| --- | --- |
| Python/venv executable missing | Use the project root; install Python/create `.venv` as in section 2.2. Do not paste multiple commands onto one line. |
| PostgreSQL/MongoDB connection failure | Check Windows services, ports and private local configuration; rerun `check_environment.py`. A server restart retains stored data. |
| PostgreSQL password authentication fails | Enter this machine's installation password in `.env`; do not copy another developer's private values. |
| Role exists but setup reports missing credentials | Preserve/recover the matching local `.env` for that installation. Do not drop accounts/tables as a routine fix; record the conflict for review. |
| Source missing/hash mismatch | Use all four unmodified ZIPs from the chosen package. Do not regenerate the approved profile just to accept a different download. |
| Restricted reader/auth/workflow/case not configured | Finish the corresponding section 2.6 helper, then restart Flask. |
| Home page is JSON, routes give generic 404, or new controls are missing | Stop your older server with Ctrl+C, restart the current checkout, reload. `/` is HTML; `/api` is discovery. No reimport is required. |
| Port 5000 already in use | Stop your own older Flask terminal, or deliberately choose another port and use its URL. Do not terminate unrelated processes. |
| Sign-in required / role denied | Check the application account/role and session expiry. New registration remains NORMAL_USER; an existing ADMIN assigns elevated roles. |
| A case reports pending/uncertain synchronization | Follow its operation retry/recovery controls after connections recover; do not manufacture a new duplicate request. |
| Import failed or looks interrupted | Review stage outcomes; earlier commits can remain. Resolve the cause before an intentional repeat; retain failure evidence. |

For direct read inspection, follow [pgAdmin and MongoDB Compass instructions](docs/INSPECTING_DATABASES.md).
Credentials stay local. `postgres` construction access, restricted SQL app accounts
and browser app roles serve different purposes. Database resets, deleting storage
folders and editing reference records are not ordinary troubleshooting steps.

## 9. Build or check a source/data package

From a prepared checkout, without starting Flask or changing database contents:

```powershell
.\.venv\Scripts\python.exe scripts/package_project.py
```

The builder reads current working files, including source not yet committed, and
writes a new dated directory below `data/processed/packages/`. It includes this
manual, source/SQL/ETL/tests, dictionaries, all four approved raw ZIPs and saved
documentation/evidence. It checks that the 135 files from the referenced technical
rehearsal still match, and records additional packaging-tool/test files separately.
If previously tested implementation changes, supply a successful matching new run
through `--rehearsal docs/rehearsals/<run>/report.json` after retesting.

The ZIP contains `PACKAGE_MANIFEST.json` with each included file's size/hash. The
builder reopens it and verifies all members before publishing the `.zip` filename.
The sibling `package_report.json` records its SHA-256/size and qualification that
fresh installation remains pending. Repeated builds get new directories and keep
earlier packages. Interrupted/failed exports may retain a `.partial` file; use only
a completed ZIP with a successful report. Builds are repeatable procedures; their
timestamps/manifests mean the ZIP bytes need not be identical between runs.

`.env`, installed environments, Git internals, database dumps/storage, browser
profiles and staging/log directories are excluded. Configured private passwords/
keys of at least 12 characters are also checked for accidental exact matches;
short ordinary-word passwords cannot reliably be detected by substring scanning.
This is not a general secret-detection audit. Verify the empty `.env.example`,
the included file manifest and package contents before sharing.

This is the **source/data/manual review candidate**, not the complete submission.
The report PDF, accepted slide format and normal-speed video must still be added
to the outer submission package after the course/XSite checks. See
[package preparation](docs/SUBMISSION_PACKAGE.md),
[final-readiness review](docs/FINAL_READINESS_REVIEW.md) and
[presentation checklist](docs/FINAL_DEMO_CHECKLIST.md).
