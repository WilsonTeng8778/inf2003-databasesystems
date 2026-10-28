# Project guide and progress tracker

**Project:** INF2003 Group 19 — Vehicle Safety Recall & Defect Investigation System  
**Guide updated:** 28 October 2026  
**Last full database verification:** 25 October 2026  
**Latest backend verification:** 28 October 2026 — saved-vehicle CRUD and ownership  
**Current overall stage:** 6 of 9 — Build the backend (**in progress**)  
**Latest completed backend substep:** 3 — Personal saved vehicles and ownership

This is our main explanation of what we are building, why each step matters,
what has actually been completed, and what we will do next. Start with sections
1–3. The later sections are references you can return to when needed.

We will update this file as work progresses. It is maintained during project
work; it does not automatically monitor your databases or update in the background.
Recorded results retain their verification dates until we check them again.

## 1. Where we are right now

We are in **Stage 6 of the overall roadmap in section 4**. Stages 1–5 established
and verified the initial database foundation. The current backend is the
application logic that will sit behind the browser pages; the visual interface
is Stage 7. “Backend step 3” is a completed substep within Stage 6, not overall
Stage 3. Section 11 records the dated progress history.

**Research, authentication and personal saved-vehicle CRUD APIs work. A signed-in
user can save, list, rename and remove their own vehicles. Next is complaint
browsing/filtering, then analyst cases and the small fleet workflow.**

We have installed the database software, examined the source files, designed the
data structures, imported real data, and tested database operations. We can already
search a vehicle using either a Python command or an HTTP request to Flask and
get information from both databases.

Research, authentication and saved vehicles work through APIs, but the visual
website and editable case/fleet workflows are not built yet. For example, we have tested
creating an analysis case directly in the databases, but an analyst cannot yet
create one through an API or browser form.

| Already working | Still to build |
| --- | --- |
| PostgreSQL and MongoDB project databases | Complaint browsing/filtering and remaining detail APIs |
| Real recalls, complaints and investigation data | Analyst-case and fleet/work-order APIs |
| Tables, document structures and relationships | Remaining record lists/filters and editable workflow APIs |
| Import scripts and database tests | Browser pages, forms and charts |
| Terminal and browser-requested vehicle safety queries | Cross-database workflow recovery and end-to-end tests |
| Initial indexes, SQL views and a history trigger | Performance experiments and final submission materials |
| Registration/login/logout and expiring SQL sessions | Browser login/registration forms |
| Admin user listing/role changes and restricted service accounts | Ownership checks wired to each editable workflow |
| Personal saved-vehicle CRUD and owner checks | Case/fleet ownership and multi-database case recovery |

“Database CRUD passed” means direct database operations were tested. It does not
mean the same feature is already available through a website. CRUD means
**Create, Read, Update and Delete**.

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
| Backend | Receives application requests, checks inputs/permissions, and talks to the databases. | Research/auth/admin and saved-vehicle routes work; complaint explorer and case/fleet workflows remain. |
| Frontend / GUI | The pages, buttons, forms and charts a person sees in the browser. | HTML, Bootstrap and JavaScript; planned. |

For example, in the finished application, a vehicle search will follow this path:

```text
Person enters a vehicle in the browser
    -> Flask receives the search
    -> Flask asks PostgreSQL for recalls and official investigations
    -> Flask asks MongoDB for complaints
    -> Flask combines the results
    -> The browser displays the safety profile
```

Today, both `scripts/safety_profile.py` and the Flask profile route use
`backend/services/research.py` for these queries. The browser can show the JSON
response now. Later, frontend code will display it as a designed page.

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
read-only check on 28 October confirmed both databases are accessible; one
application account is currently stored. This is separate from the earlier full
database test result and does not mark a new application feature complete.

## 4. How a typical database application project develops

Projects usually move through the stages below, but the process is not strictly
one-way. Inspecting real data can change a design, and testing can send us back to
an earlier step. Testing and documentation happen throughout.

| Stage | What it means and why it matters | Our status |
| --- | --- | --- |
| 1. Define the problem and scope | Decide who will use the system and which tasks it should support. This keeps the project manageable. | **Done:** proposal reviewed and small fleet scope resolved. |
| 2. Find and understand data | Examine actual files, field meanings, repeated records and missing values before designing around assumptions. | **Done:** all four archives and field dictionaries inspected. |
| 3. Design the data model | Decide what to store, how records relate, what belongs in each database, and which rules protect correctness. | **Done for the initial version:** SQL model, ERD and MongoDB models documented. |
| 4. Construct and populate databases | Turn the design into real tables/collections and load cleaned data through repeatable imports. | **Done:** both project databases populated. |
| 5. Verify the database layer | Check queries, CRUD, relationships, invalid inputs and repeat imports before putting a website on top. | **Done for this milestone:** database checks passed on 25 October. |
| 6. Build the backend | Make database operations available through application code, with login, validation and permissions. | **In progress:** research, auth/admin and owner-scoped saved-vehicle CRUD verified on 28 October; complaint explorer and case/fleet workflows remain. |
| 7. Build the frontend | Connect screens and forms to the backend so users can perform the workflows. | **Planned:** not started. |
| 8. Analyse, improve and test the whole application | Build analytics, measure query performance, and test complete workflows and failures. | **Partly prepared:** basic aggregation/indexes exist; dashboards, benchmarks and application testing remain. |
| 9. Document and deliver | Make the project reproducible and prepare the report, demonstration and submission package. | **In progress:** setup/design notes exist; final deliverables remain. |

We chose to establish the database foundation before substantial interface work.
That lets us check that the data and relationships support our promised features.
The first authenticated application workflow, personal saved vehicles, now works
through HTTP and a terminal menu. Browser screens will connect to these same APIs.

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
Some workflow tables are currently empty. Saved records can now be created by
users through the API/menu; case and fleet workflow APIs are still planned.

### We loaded the selected real data

**ETL** means Extract, Transform and Load: read the source, clean/reshape it, and
write it into the databases. Our imports normalize names, handle dates and missing
values, merge repeated component rows, and log results.

The last verified import contains:

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

## 6. What is in this repository, and where is the actual data?

| File or folder | Its purpose |
| --- | --- |
| `PROJECT_GUIDE.md` | This explanation and our ongoing progress tracker. |
| `README.md` | Technical setup instructions and commands. |
| `data/raw/` | The original downloaded ZIPs; kept locally and excluded from Git. |
| `data/dictionaries/` | Descriptions of the source file columns. |
| `etl/` | Python code that reads, cleans and imports the records. |
| `backend/` | Flask research/auth/admin/saved-vehicle requests, ownership checks and database services. |
| `sql/` | SQL construction scripts and additive migrations; migration 002 adds sign-in sessions. |
| `mongodb/schema.py` | MongoDB document validation and index definitions. |
| `scripts/` | Commands for checking setup, importing, verifying and trying a vehicle query. |
| `tests/` | Automated API tests with fake connections and data transformation tests. |
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
steps. This checkpoint prepares the database foundation and research, auth/admin
and personal saved-vehicle APIs for sharing through the configured
[GitHub repository](https://github.com/WilsonTeng8778/inf2003-databasesystems).
Credentials, the Python environment and raw archives remain local; teammates
reproduce their databases using the README. A source-code push shares our work
without deploying the application or transferring the running databases.

If you encounter SQLite in the ETL code, it is temporary scratch storage used
while grouping complaint rows. PostgreSQL and MongoDB remain the two application
databases.

## 7. What we will do next, in manageable steps

We are working toward **a complete backend**. Research, authentication and personal
saved-vehicle CRUD are working.
Flask is the Python framework receiving web requests. An **API endpoint** is a particular request the backend
accepts, such as “find this vehicle” or “save this vehicle for me.”

| Order | Work | Status / successful result |
| --- | --- | --- |
| 1 | Start Flask and connect the existing databases. | **Done for read-only research:** vehicle search/profile and readiness work through HTTP. |
| 2 | Add registration/login, password hashing and sessions. | **Done through APIs:** eight-hour sessions, expiry, logout and old-cookie revocation verified. Browser forms remain. |
| 3 | Enforce roles and ownership; configure application database access. | **Partly done:** role guards, admin management, limited SQL accounts and saved-vehicle ownership work. Case/fleet ownership remains. |
| 4 | Complete research and saved-vehicle operations. | **Partly done:** saved-vehicle CRUD is verified. **Next:** detailed safety-record lists and complaint browsing/filtering. |
| 5 | Add analyst-case operations across both databases. | **Planned:** manage status/notes/findings and recover from partial failures. |
| 6 | Add the small fleet/work-order workflow. | **Planned:** maintain an owner's fleet and its recall work orders. |

We will build and check these incrementally. The browser interface follows the
first usable backend operations and will grow alongside them. A full import is
not a routine step every time we add an endpoint or restart the computer.

After that, we will complete the analytics screens, benchmark queries before and
after indexing, test complete user journeys, and prepare the submission materials.
Documentation and evidence collection continue during each stage.

One important backend problem is that a SQL transaction cannot automatically undo
a MongoDB write. For a case stored across both databases, we need to test what
happens if one write succeeds and the other fails. That application-level handling
is still to build; direct CRUD checks do not establish it.

## 8. A small way to see the current work yourself

The setup, package installation, database construction and full imports in the
README were already carried out on this computer on 25 October. Those commands
are included so the setup can be reproduced; you do not need to repeat all of
them yourself before continuing. Flask and its SQL reader were prepared here on
28 October too. Session storage and auth credentials have now also been prepared;
there is no need to rerun the large imports.

### Try the browser request

From a terminal at the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Keep that terminal running and open
[the vehicle profile](http://127.0.0.1:5000/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC)
in your browser. You should see JSON with 4 recall campaigns, 2 investigations
and 885 complaints for the verified snapshot. This proves the browser can send
a request to Flask and receive a combined database answer. The visual page is
still to build.

Press **Ctrl+C** in the terminal to stop the web server. This does not reset or
stop the database services. The server keeps listening while it runs, whereas the
earlier query scripts print one result and finish.

### Try registration and login

If Flask was started before the authentication changes, restart it first. With
Flask running, use a second terminal at the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/try_auth.py --register
```

Choose an email and a password of 12–128 characters at the prompts. Password input
is hidden. The helper registers a normal account, shows its signed-in identity,
then logs out. The account persists. For later login, run the command without
`--register`. This helper uses its own cookies; it does not also sign in a separate
browser window. No default login account was seeded during verification.

The first administrator can be created with the interactive local command
`scripts/create_admin.py`, using an unused email. After that, administrators assign
analyst/admin roles through protected requests. Normal registration always stays
NORMAL_USER. The [auth walkthrough](docs/BACKEND_STEP_2_AUTH.md) explains the full
flow. A 401 from `/api/auth/me` is expected when that client is not signed in.

### Try your first saved-vehicle workflow

Restart Flask to load the saved-vehicle routes. With it running, open a second
terminal and run:

```powershell
.\.venv\Scripts\python.exe scripts/try_saved_vehicles.py
```

Sign in with your application email/password. The menu can list, save, rename or
remove your own vehicles. Try saving `2022 HONDA CIVIC` with a nickname, then list
your records and use the displayed saved-record ID to rename/remove it. Exiting
logs out but keeps saves you did not remove. You can see those rows in pgAdmin's
`saved_vehicle` table. This is real application CRUD, not a fixture test or reimport.

The [saved-vehicle walkthrough](docs/BACKEND_STEP_3_SAVED_VEHICLES.md) explains the
API, the two different vehicle IDs, and how ownership is enforced.

### Optional terminal query

With the database services running, open a PowerShell terminal in this repository
and run this connection check first:

```powershell
.\.venv\Scripts\python.exe scripts/check_environment.py
```

Then run this **read-only query**:

```powershell
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
```

It prints structured text called JSON. In the snapshot verified on 25 October,
the result includes **4 recall campaigns, 2 official investigations and 885
complaints**, plus complaint component counts. It uses the same query as the
HTTP route. Use another terminal for these commands if Flask is already running.

Run each command on its own line, one at a time. The long path ending in
`python.exe` selects our project's Python interpreter. It does not recreate the
database. The stored data remains after commands finish or VS Code closes.

Start by understanding what the command returns, then follow
`scripts/safety_profile.py`: it asks SQL for official records and MongoDB for
complaints. You do not need to understand every file at once or rerun the large
imports to try this query. If it fails to connect, first check the services and
local configuration; a connection error does not by itself mean the data is gone.

The README contains several kinds of commands: environment setup, source
inspection, database construction/import, an actual vehicle query, and tests.
They are not all tests. The import updates stored reference data, while the
vehicle query only reads it. The full database verifier briefly creates test
records and cleans them up; the unit tests use made-up inputs without connecting
to the servers. See the [command reference](README.md#what-each-command-does) for
each command's purpose, side effects and intended frequency. None of these current
commands empties and rebuilds the complete databases each time it runs.

Useful questions for the next walkthrough are: What is one vehicle identity?
Why is one complaint sometimes several source rows? Which database answers each
part of the search? How will the backend check who is allowed to change a case?

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

According to the supplied project brief, final submission is **29 November 2026,
11:30 PM**. Check XSite for any later course announcements.

We still need the finished application, final report, slides, presentation video,
and source/data/user-manual package. The report is limited to 10 main-content pages
and the video to 10 minutes; all five members must present. The existing README
and design notes are useful inputs, but are not the finished submission.

Our report needs to explain the data model, both databases' operations and advanced
features, performance evidence, problems encountered and improvements. The main
remaining work is the backend and interface, followed by evaluation and packaging.

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

At each meaningful milestone, we will update the date, current-position summary,
stage statuses, next actions and this log. New counts/test claims will include
their actual evidence and verification date. Plans will stay marked as plans until
implemented and checked. Detailed milestone reports preserve what was verified
at that point; this file explains our current position.
