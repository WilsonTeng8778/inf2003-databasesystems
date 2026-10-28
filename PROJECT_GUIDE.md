# Project guide and progress tracker

**Project:** INF2003 Group 19 — Vehicle Safety Recall & Defect Investigation System

**Guide updated:** 28 October 2026

**Earlier database foundation verification:** 25 October 2026

**Latest workflow verification:** 28 October 2026 — isolated synthetic integration/browser checks and a new real-data import with workflow checks

**Current overall stage:** 8 of 9 — Evaluation and delivery preparation

**Current implementation:** research, analyst cases, small fleets and browser interface are present in this local checkout.

This is our main explanation of what we are building, why each step matters,
what has actually been completed, and what we will do next. Start with sections
1–3. The later sections are references you can return to when needed.

We will update this file as work progresses. It is maintained during project
work; it does not automatically monitor your databases or update in the background.
Recorded results retain their verification dates until we check them again.

## 1. Where we are right now

Research, complaint filtering, analyst cases, fleet recall work orders and a
browser interface are implemented. The interface separates consumer complaints
from recalls and official investigations and lets analysts link reports to cases.

On 28 October, the existing 53-test suite passed in this checkout. A separate
live integration test used isolated PostgreSQL 18 and MongoDB 6.0 databases with
synthetic records. It exercised evidence queries, case document CRUD, permissions,
fleet work orders and retry after a simulated MongoDB outage. A browser walkthrough
also created a synthetic case and fleet work order. These checks do not establish
that every teammate's environment or final presentation is ready.

The official source archives have been downloaded into this checkout's ignored
`data/raw/` folder. A separate isolated import and read-only API check used the
new snapshot; its counts and hashes are in [real data evidence](docs/real_data_verification_2026-10-28.json).
Synthetic case and fleet records were also checked against real public records
and removed afterward; [workflow evidence](docs/real_workflow_verification_2026-10-28.json)
records the cleanup.
The [benchmark evidence](docs/benchmark_2026-10-28.json) records one sampled
before/after run and its limits. These databases are separate from Git and from
the earlier 25 October snapshot. Follow the [user manual](docs/USER_MANUAL.md)
to configure your own databases, apply migration 003 and load data. Final report,
slides, five-member video, team review and submission remain to be completed.

## 2. What are we trying to build?

Someone should be able to search a vehicle, such as a **2022 Honda Civic**, and
see its related official recalls, consumer complaints and official investigations
in one place. An analyst should be able to collect relevant complaints into an
internal case and record findings. A small fleet workflow should let an owner
track vehicles and recall work orders.

Our three areas are:

| Area | Example of what a person will do |
| --- | --- |
| Vehicle research | Search a model year/make/model and explore its safety records. |
| Internal analyst cases | Link complaints, write notes/findings, and change a case's status. |
| Small fleet recall tracking | Add vehicles to a fleet, find model-level recall matches, and track work orders. |

The fleet part is deliberately small. We are not adding workshop bookings,
invoices, parts inventory, or general maintenance management.

For the class, the goal is to demonstrate that we can **design and use both SQL
and NoSQL databases appropriately**, then explain our decisions and results.
The interface will make those database functions usable and easy to demonstrate.

Consumer complaints are reports, not automatically confirmed defects. Our internal
analyst cases are separate from official NHTSA investigations. A make/model/year
recall match also does not establish the recall status of one particular VIN.

## 3. How the parts of the project fit together

A database stores information. A database management system, or **DBMS**, is the
software that manages that storage and answers requests. PostgreSQL and MongoDB
are our two DBMSs. Each contains a project database named `vehicle_safety`.

| Part | Plain explanation | Our choice and current position |
| --- | --- | --- |
| Source data | The original information we start with. | Four NHTSA ZIP files; downloaded and inspected. |
| Import process | Programs that clean and copy source records into our databases. | Python ETL scripts; working. |
| Relational database | Stores information in related tables, with rules about valid data. | PostgreSQL; constructed and populated. |
| Document database | Stores records as documents with nested fields and lists. | MongoDB; constructed and populated. |
| Backend | Receives application requests, checks inputs/permissions, and talks to the databases. | Flask research, auth, saved vehicles, cases, fleet and admin routes are implemented. |
| Frontend / GUI | The pages, buttons, forms and charts a person sees in the browser. | Server-served HTML, CSS and JavaScript at `/app`. |

For example, in the finished application, a vehicle search will follow this path:

```text
Person enters a vehicle in the browser
    -> Flask receives the search
    -> Flask asks PostgreSQL for recalls and official investigations
    -> Flask asks MongoDB for complaints
    -> Flask combines the results
    -> The browser displays the safety profile
```

Both `scripts/safety_profile.py` and the Flask profile route use
`backend/services/research.py`. The browser workspace displays the returned data,
and the JSON endpoints remain available for inspection.

PostgreSQL stores structured records and relationships: vehicle identities,
recalls, investigations, users, saved vehicles, case status, fleets and work orders.
MongoDB stores complaint documents and flexible case content such as notes,
findings, tags and linked complaint IDs. Their different responsibilities are the
reason for using two databases in this application.

Many applications use just one DBMS. This course asks us to use both relational
and non-relational databases, so our design gives each a meaningful responsibility.

pgAdmin and MongoDB Compass are tools for inspecting databases. They are not our
project's frontend. Docker is optional setup software; our current project uses
native Windows database services and does not require it.

You can inspect both databases now, independently of Flask. The
[database browsing walkthrough](docs/INSPECTING_DATABASES.md) shows how to connect,
which tables/collections to open, and a first SQL query and MongoDB filter. A
read-only check recorded on 28 October concerned the earlier machine's database.
It should not be assumed to describe a fresh clone or another teammate's setup.

## 4. How a typical database application project develops

Projects usually move through the stages below, but the process is not strictly
one-way. Inspecting real data can change a design, and testing can send us back to
an earlier step. Testing and documentation happen throughout.

| Stage | What it means and why it matters | Our status |
| --- | --- | --- |
| 1. Define the problem and scope | Decide who will use the system and which tasks it should support. This keeps the project manageable. | **Done:** proposal reviewed and small fleet scope resolved. |
| 2. Find and understand data | Examine actual files, field meanings, repeated records and missing values before designing around assumptions. | **Done:** all four archives and field dictionaries inspected. |
| 3. Design the data model | Decide what to store, how records relate, what belongs in each database, and which rules protect correctness. | **Done for the initial version:** SQL model, ERD and MongoDB models documented. |
| 4. Construct and populate databases | Turn the design into real tables/collections and load cleaned data through repeatable imports. | **Done in the earlier and isolated validation environments:** each fresh team environment needs its own setup/import. |
| 5. Verify the database layer | Check queries, CRUD, relationships, invalid inputs and repeat imports before putting a website on top. | **Done for this milestone:** database checks passed on 25 October. |
| 6. Build the backend | Make database operations available through application code, with login, validation and permissions. | **Implemented:** research, auth, cases and owner-scoped fleet/work-order APIs. |
| 7. Build the frontend | Connect screens and forms to the backend so users can perform the workflows. | **Implemented:** browser workspace; key journeys checked with synthetic data. |
| 8. Analyse, improve and test the whole application | Build analytics, measure query performance, and test complete workflows and failures. | **In progress:** charts, workflow checks and a real-data sample benchmark exist; the team should review them in its final environment. |
| 9. Document and deliver | Make the project reproducible and prepare the report, demonstration and submission package. | **In progress:** setup/design notes exist; final deliverables remain. |

We chose to establish the database foundation before substantial interface work.
That lets us check that the data and relationships support our promised features.
The browser screens connect to the same authenticated APIs as the terminal helpers.

## 5. What we have done, with explanations

### We understood and agreed the scope

We reviewed the course brief, FAQ, submitted proposal and generated blueprint.
The proposal included fleets/work orders, while the blueprint excluded them.
The later greenlight resolved this by keeping a minimal fleet recall workflow.
The agreed scope is recorded in [IMPLEMENTATION_GREENLIGHT.md](docs/IMPLEMENTATION_GREENLIGHT.md).

### We inspected the data before finalizing the model

The ZIP files contain tab-separated records. Their field dictionaries explain
what each column means. We checked the actual contents instead of assuming that
each line represented one complete recall or one complete complaint.

For example, one complaint can appear on two lines because it concerns two
components. We merge those into one document with two component names. Otherwise,
we could accidentally count one complaint or its injuries twice.

A recall can cover many vehicles, and a vehicle can have many recalls. This is
a **many-to-many relationship**. We represent that relationship through a linking
table, `recall_vehicle`, rather than copying a complete campaign into every vehicle.

We also found that some vehicles appear in complaints but not in the selected
recall data. The shared vehicle catalogue therefore uses all three source types.
See [DATA_INSPECTION.md](docs/DATA_INSPECTION.md) for the detailed findings.

### We designed and constructed the storage

A **schema** describes the fields, data types and rules for stored information.
An **entity relationship diagram (ERD)** shows how the main kinds of records link
together. Our SQL construction scripts turn that design into actual tables.

For example, a saved-vehicle record links a user to a vehicle identity. A database
rule prevents that user from saving the same identity twice. Another rule prevents
a work order being attached to a recall for an unrelated vehicle model-year.

The design and diagram are in [DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md).
Workflow records are created by users through the API or browser. A newly created
database starts with no personal saved vehicles, analyst cases or fleets.

### We loaded the selected real data

**ETL** means Extract, Transform and Load: read the source, clean/reshape it, and
write it into the databases. Our imports normalize names, handle dates and missing
values, merge repeated component rows, and log results.

The earlier 25 October verified snapshot contained:

| Stored information | Count |
| --- | ---: |
| Distinct make/model/year vehicle identities | 53,555 |
| Official recall campaigns | 13,600 |
| Official investigations | 3,626 |
| Consumer complaint documents | 428,837 |

The 53,555 identities describe combinations such as “2022 Honda Civic”; they are
not 53,555 individual physical cars. The complaint documents were formed from
617,186 eligible component rows. Counts refer to our imported snapshot, not a
continuously refreshed connection to NHTSA.

### We tested the database operations

Five automated transformation tests passed, followed by live database checks for
CRUD, duplicate prevention, valid relationships, and case-status history.
We reran the complete import and confirmed that it created zero new entities.
That is evidence that importing the same files again does not create duplicates.

The verification scripts used temporary application records and removed or rolled
them back afterward. No login accounts were seeded. See
[MILESTONE_1.md](docs/MILESTONE_1.md) for the summary and
[verification_report.json](docs/verification_report.json) for recorded results.

### We connected the first queries to a web backend

On 28 October we added Flask routes for readiness, vehicle search and the combined
safety profile. These routes validate inputs and return JSON errors when a request
is invalid or required data cannot be reached. A separate SQL reader can access
the public research views, rather than using the setup account for web requests.
That database identity is not a website user account.

The 17 automated tests (12 API tests plus the original 5 ETL tests) passed, along
with 8 real HTTP checks. Checked record counts were unchanged. The details and
dated evidence are in [Backend step 1](docs/BACKEND_STEP_1.md) and
[api_verification_report.json](docs/api_verification_report.json). Full database
CRUD/import verification remains the earlier, separate 25 October result.

### We added sign-in and role checks

Registration now creates a `NORMAL_USER` with a hashed password. A successful
sign-in creates a session in PostgreSQL and gives the client a signed cookie.
Protected requests check that session and read the user's current role. Logout
revokes it, so replaying an old cookie no longer works. Administrators can list
users and assign roles; self-registration cannot choose analyst/admin access.

On 28 October, 34 automated tests and 36 recorded real HTTP checks passed, plus
interactive registration/login and first-admin helper checks. Synthetic accounts
were cleaned up; reference data and checked record counts were preserved. See
[Backend step 2](docs/BACKEND_STEP_2_AUTH.md) and
[auth_verification_report.json](docs/auth_verification_report.json).

These are API features. The reusable analyst role guard is tested, but case/fleet
ownership enforcement still needs the corresponding workflow APIs.

### We connected personal saved vehicles to SQL CRUD

You can now sign in and save a catalogue vehicle, list it, rename its nickname,
and remove it through the API. These actions run INSERT, SELECT/JOIN, UPDATE and
DELETE statements against PostgreSQL's `saved_vehicle` table. Source safety
records are separate from these personal bookmarks.

The server uses the signed-in user ID for every saved-record lookup/change. It
does not accept an owner from the request body. Another user's record returns
404, even for an admin's personal saved-vehicle requests. Different users may
save the same vehicle, but one user cannot save it twice.

On 28 October, 53 automated tests and 37 recorded live HTTP checks passed, plus a
real interactive menu flow. Owned fixtures were removed, and checked reference
and existing account counts matched the baseline. See
[Backend step 3](docs/BACKEND_STEP_3_SAVED_VEHICLES.md) and
[saved_vehicles_verification_report.json](docs/saved_vehicles_verification_report.json).

### New browser and investigation workflows — 28 October 2026

The new workspace adds evidence tabs and complaint filters, component and monthly
charts, a case workspace, small fleet recall matches and work orders, and admin
screens. A case links SQL workflow data to MongoDB details using an ordered,
idempotent outbox. If MongoDB is unavailable, pending creation or deletion can be
retried. The [implementation and evidence map](docs/IMPLEMENTATION_AND_EVIDENCE.md)
distinguishes implemented code from the checks actually performed.

## 6. What is in this repository, and where is the actual data?

| File or folder | Its purpose |
| --- | --- |
| `PROJECT_GUIDE.md` | This explanation and our ongoing progress tracker. |
| `README.md` | Technical setup instructions and commands. |
| `data/raw/` | The original downloaded ZIPs; kept locally and excluded from Git. |
| `data/dictionaries/` | Descriptions of the source file columns. |
| `etl/` | Python code that reads, cleans and imports the records. |
| `backend/` | Flask APIs, the browser workspace, access checks and database services. |
| `sql/` | SQL construction scripts and additive migrations; 002 adds sessions and 003 adds case synchronization. |
| `mongodb/schema.py` | MongoDB document validation and index definitions. |
| `scripts/` | Commands for checking setup, importing, verifying and trying a vehicle query. |
| `tests/` | Automated fake-connection tests and an opt-in isolated live workflow test. |
| `docs/` | Detailed design, inspection, scope and milestone evidence. |
| `.env` | Private database service credentials and Flask signing key; excluded from Git. |
| `.env.example` | A shareable example of the required settings, without your password. |
| `project_config.py` | Reads settings and opens database connections. |
| `requirements.txt` / `.venv/` | The Python dependency list and locally installed project packages. |

The `.sql` files are construction instructions. The imported database contents
live in the PostgreSQL and MongoDB servers on your computer. GitHub shares code
and documentation; committing code does not automatically upload those databases.
A teammate reproduces the setup using the source files and import instructions.

An application account is a row in `app_user`, created during registration.
Its password is one you choose, stored as a hash. The database credentials and
signing key in `.env` are for the software's connections/cookies; they are not
your website login. NORMAL_USER/ANALYST/ADMIN are human application roles, separate
from the SQL reader/auth/workflow accounts used internally by the backend.

Saving files, committing them to Git, and pushing commits to GitHub are separate
steps. This checkout prepares the database foundation, browser workspace and application
workflows for review and eventual sharing through the configured
[GitHub repository](https://github.com/WilsonTeng8778/inf2003-databasesystems).
Credentials, the Python environment and raw archives remain local; teammates
reproduce their databases using the README. A source-code push shares our work
without deploying the application or transferring the running databases.

If you encounter SQLite in the ETL code, it is temporary scratch storage used
while grouping complaint rows. PostgreSQL and MongoDB remain the two application
databases.

## 7. What we will do next

1. Apply the new migration, views and grants in each team environment using the
   [user manual](docs/USER_MANUAL.md). Import the approved source archives if the
   environment has not already been populated.
2. Walk through the research, case and fleet journeys with the team. Confirm each
   member understands the database operations and the limits of the source data.
3. Review the recorded index benchmark and, if needed, rerun it in the team's
   intended demonstration environment. Explain its sample and limitations.
4. Complete and review the final report, slides, five-member video, manual and
   source/data package. Confirm current submission instructions in XSite.

The implementation includes an ordered case synchronization outbox. A pending
case document operation can be retried from the app or the reconciliation script;
it does not imply a distributed transaction across PostgreSQL and MongoDB.

## 8. Try the browser workspace

After preparing your own database services, configuration and data using the
[user manual](docs/USER_MANUAL.md), run this from the repository root:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000/app. Search by year, make and model, then explore the
three evidence categories. Register or sign in to save vehicles and manage a
fleet. An administrator can grant analyst access for investigation cases.
Ctrl+C stops Flask without resetting the databases. The JSON API index at `/`
and the earlier terminal helpers remain available.

## 9. Terms to look up as they appear

| Term | Meaning in our project |
| --- | --- |
| Table / row / column | A SQL structure / one stored record / one field of that record. |
| Collection / document | A MongoDB group of records / one record, which can contain nested fields and arrays. |
| Primary key | The identifier that distinguishes one SQL row from another. |
| Foreign key | A stored reference to another SQL row, checked by the database. |
| Query / join | A request for information / a SQL operation combining related tables. |
| Constraint / validator | A rule rejecting invalid data, such as a duplicate saved vehicle or missing required document fields. |
| Index | An extra lookup structure that can help queries find records faster; it also costs storage and write work. |
| View | A named SQL query that can be read like a table; our safety summary combines related information. |
| Trigger | Database logic run automatically by an event; ours records case-status changes. |
| Transaction | Changes that are committed together or rolled back together within the applicable database boundary. |
| Aggregation | Grouping/summarizing records, such as counting complaints by component. |
| Upsert / idempotent import | Insert or update by an identifier / a repeat import with the same intended final result; our count checks verified no duplicate entities on rerun. |
| Backend / frontend | Application logic and database access / the browser interface. |
| Authentication / authorization | Checking who signed in / checking what actions they are allowed to take. |
| Session / cookie | A stored sign-in record / browser-held data linking requests to that session. Our sessions expire and can be revoked. |
| CSRF token | A token tied to the client session that the server checks before accepting changes; our helper handles it automatically. |

## 10. Remaining course deliverables

The project brief lists the final submission date and XSite group Dropbox; check
XSite for any later announcements. The final report, slides, presentation video
and source/data/manual package still need team review and submission. The report
is limited to 10 main-content pages and the video to 10 minutes; all five members
must present. The project code and manual are inputs, not evidence of submission.

Describe both database designs and operations, the innovation workflow, tested
results, performance measurements and their limitations. Confirm the earlier
progress-report submission separately in XSite. The [report and demo evidence
guide](docs/REPORT_AND_DEMO_EVIDENCE.md) provides a starting outline and preserves
the distinction between real-source measurements and synthetic workflow tests.

## 11. Progress log and how this guide stays current

| Date | What changed | Evidence / next position |
| --- | --- | --- |
| 4 October 2026 (proposal date) | Team proposal describes the application and initial plan. | Proposal submission confirmed by the team; topic and initial scope established. |
| 24 October 2026 | Reviewed project materials and resolved fleet scope through the subsequent greenlight. | Shared core plus a small fleet/work-order module agreed. |
| 25 October 2026 | Constructed/imported both databases and verified the first milestone. | [Milestone 1](docs/MILESTONE_1.md); ready for backend development. |
| 27 October 2026 | Added this beginner guide and progress tracker. | Documentation update only; backend remains the next implementation stage. |
| 28 October 2026 | Clarified first-time setup, imports, queries and test commands, including their effects on stored data. | Documentation clarification; full database verification remains dated 25 October. |
| 28 October 2026 | Implemented read-only Flask research routes, a restricted SQL reader, automated API tests and real HTTP verification. | [Backend step 1](docs/BACKEND_STEP_1.md) verified; registration/login and editable workflows are next. |
| 28 October 2026 | Added registration/login/logout, expiring SQL sessions, CSRF protection, role guards, admin role changes and interactive helpers. | [Backend step 2](docs/BACKEND_STEP_2_AUTH.md) verified; saved-vehicle ownership/CRUD is next. |
| 28 October 2026 | Checked live database connections/counts and added pgAdmin/Compass browsing instructions. | [Inspection walkthrough](docs/INSPECTING_DATABASES.md); read-only inspection, no implementation-stage change. |
| 28 October 2026 | Added personal saved-vehicle CRUD, ownership checks, limited workflow SQL access and an interactive menu. | [Backend step 3](docs/BACKEND_STEP_3_SAVED_VEHICLES.md) verified; complaint browsing and analyst cases are next. |
| 28 October 2026 | Added an explicit overall-stage and backend-substep indicator at the top of this guide. | Tracking clarification only; overall Stage 6 remains in progress. |
| 28 October 2026 | Prepared a versioned GitHub checkpoint of completed database and backend work, excluding credentials, raw archives and local environments. | Source-sharing checkpoint; Stage 6 and the remaining feature plan are unchanged. |
| 28 October 2026 | Implemented complaint exploration, analyst cases, fleet workflows, a browser interface and an index benchmark harness in a new local checkout. | [Implementation and evidence](docs/IMPLEMENTATION_AND_EVIDENCE.md); isolated synthetic database and browser checks completed. |
| 28 October 2026 | Downloaded and inspected updated NHTSA archives, imported them into separate test databases, checked research API counts and measured sampled indexes. | [Real-data verification](docs/real_data_verification_2026-10-28.json) and [benchmark](docs/benchmark_2026-10-28.json); final team review and delivery remain. |

At each meaningful milestone, we will update the date, current-position summary,
stage statuses, next actions and this log. New counts/test claims will include
their actual evidence and verification date. Plans will stay marked as plans until
implemented and checked. Detailed milestone reports preserve what was verified
at that point; this file explains our current position.
