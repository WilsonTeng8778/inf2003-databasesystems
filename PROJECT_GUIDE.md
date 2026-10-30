# Project guide and progress tracker

**Project:** INF2003 Group 19 — Vehicle Safety Recall & Defect Investigation System  
**Guide updated:** 30 October 2026\
**Last full database verification:** 25 October 2026  
**Latest backend verification:** 30 October 2026 — integrated run: 202 automated tests and fresh native case/fleet/account/import checks\
**Latest automated suite:** 30 October 2026 — 210 tests, including eight new package-integrity tests; native/browser checks were not rerun for packaging\
**Latest browser verification:** 30 October 2026 — fresh 238-check cumulative run during the integrated rehearsal\
**Latest performance verification:** 29 October 2026 — four controlled query workloads and live complaint index checks\
**Latest requirements review:** 30 October 2026 — G1 account deletion and G2 admin import initiation closed with implementation/evidence\
**Current overall position:** Stage 9 of 9 — Document and deliver (**in progress**)\
**Latest delivery milestone:** User manual and checked local source/data review ZIP prepared on 30 October; teammate fresh installation remains pending\
**Source-sharing checkpoint:** 30 October 2026 — `milestone/recallscope-core-complete-2026-10-30`; GitHub `main` contains a separate implementation awaiting deliberate integration\
**Latest technical milestone:** Integrated acceptance rehearsal passed on 30 October; team presentation/fresh installation remain pending\
**Latest completed frontend substep:** 7 — Confirmed unused-account deletion and uncertain-response review\
**Latest completed backend substep:** 11 — Role-checked local import orchestration using the shared ETL pipeline\
**Latest interactive frontend addition:** Account deletion controls verified on desktop and mobile; screenshots reviewed

This is our main explanation of what we are building, why each step matters,
what has actually been completed, and what we will do next. Start with sections
1–3. The later sections are references you can return to when needed.

We will update this file as work progresses. It is maintained during project
work; it does not automatically monitor your databases or update in the background.
Recorded results retain their verification dates until we check them again.

## 1. Where we are right now

We are in **Stage 9 of the overall roadmap in section 4**. Stages 1–5 established
the database foundation; Stage 6 built the APIs. The seven Stage 7 browser milestones
now cover research, accounts/personal saves, complaints/official records, analyst
cases, fleets/work orders, admin views and analytics. This is the first working
implementation, not final submission readiness. Controlled index experiments are
verified. A 30 October review found account deletion and admin import initiation
incomplete. Both are now implemented and verified: account deletion through the
SQL/API/browser flow, and admin imports through a role-checked local terminal
helper. The integrated technical rehearsal has now passed. We now have a coherent
user manual, a teammate installation checklist and a locally checked source/data
review ZIP. A teammate's fresh setup, final package freeze, report and slides/video remain;
the timed five-member presentation rehearsal has not been performed. Section 11
records the dated history.

The [GitHub checkpoint note](docs/GITHUB_CHECKPOINT_2026-10-30.md) explains the named
milestone branch. GitHub `main` already contains a different implementation from
another line of work. Select the milestone branch to review this verified version;
combining the two versions requires integration and fresh checks. Our current
Stage 9 position and earlier test results are unchanged by sharing the source.

**We now have a real browser interface named RecallScope. You can search vehicles,
view safety profiles, filter complaints, follow official-record relationships,
register/sign in, and save/rename/remove personal vehicle bookmarks. Analysts/admins
can manage internal cases, complaint links, notes/findings, history and saved-update
recovery in the browser. Every signed-in role can also manage its own fleets,
vehicle entries, recall matches and work orders. Admins can manage user roles and
inspect dataset sizes/import history. Public analytics now shows complaint trends,
component counts and model-year comparisons with links to the reports. These
browser journeys and selected index experiments have dated evidence.
Admins can also delete eligible unused accounts through a confirmed browser flow.
Admins can initiate an approved import through the local terminal helper, with
outcomes shown in Import history. The technical journeys have passed together on
the current working code. Next are manual/package/reproduction work and the
team's presentation/submission materials.**

We have installed the database software, examined the source files, designed the
data structures, imported real data, and tested database operations. We can already
search a vehicle using either a Python command or an HTTP request to Flask and
get information from both databases.

Research, complaint filters, record relationships, authentication, personal saves
and analyst cases now have browser pages. Owners can also manage fleets/work orders
through browser forms. Admin role management and dataset/import monitoring also
have pages. Complaint analytics/chart presentation also works. Selected SQL/MongoDB
query plans/timings are recorded, and a measured complaint pagination index is now
installed. The [requirements review](docs/FINAL_READINESS_REVIEW.md) now separates
covered features from unfinished deliverables. Its original document/source review
found G1/G2; subsequent implementation and separate dated tests closed both gaps.

| Already working / verified | Still to finish |
| --- | --- |
| PostgreSQL and MongoDB project databases | Final demonstration and fresh-machine reproduction |
| Real recalls, complaints and investigation data | Reproducibility checks on a teammate's setup |
| Tables, document structures and relationships | Final report's design/relationship explanation |
| Import scripts, database tests and planned browser workflows | Final report, demonstration and packaging |
| Vehicle safety queries and browser case/fleet/admin journeys | Timed five-member presentation rehearsal |
| Initial indexes, SQL views and a history trigger | Final submission materials |
| Registration/login/logout, sessions and browser auth forms | Broader final demonstration journeys |
| Browser admin roles, restricted SQL views and workflow ownership | Final role-specific demonstration journeys |
| Browser personal saves and owner-scoped fleet/work-order forms | Final report/video/package preparation |
| Complaint explorer and vehicle-scoped case complaint picker | Final demonstration journeys and evaluation |
| Complaint monthly/component analytics and model-year comparisons | Final report's evaluation discussion |
| Browser analyst-case CRUD, notes/findings, history and explicit recovery | Optional future reassignment tools, outside the current case milestone |
| Browser fleet recall matching, tracking statuses and dependent-record cleanup | Final demonstration journeys |
| Four measured query workloads, saved plans/figures and a verified complaint index improvement | Wider workload/load testing if required by the final review |
| Restricted unused-account deletion and role-checked local import initiation | Demonstration using the final packaged source/data |
| Integrated technical acceptance with code/data fingerprints and cleanup checks | Final user manual, teammate setup and delivery gates |
| Requirements/evidence map and draft final demo checklist | Execute the final rehearsal and resolve any failures |

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
| Backend | Receives application requests, checks inputs/permissions, and talks to the databases. | Core workflows, monitoring, analytics and selected index measurements verified on 29 October; broader final evaluation remains. |
| Frontend / GUI | The pages, buttons, forms and charts a person sees in the browser. | First planned Flask/Jinja/CSS/JavaScript research/workflow/admin/analytics interface verified on 29 October; evaluation may lead to refinements. |

For example, the current vehicle safety profile follows this path:

```text
Person enters a vehicle in the browser
    -> Flask receives the search
    -> Flask asks PostgreSQL for recalls and official investigations
    -> Flask asks MongoDB for complaints
    -> Flask combines the results
    -> The browser displays the safety profile
```

Today, both `scripts/safety_profile.py` and the Flask profile route use
`backend/services/research.py` for these queries. API URLs still show JSON, while
the new browser pages turn those responses into cards, record lists and forms.
The pages use a local stylesheet rather than downloading Bootstrap; no new
frontend package installation or build step is required to run them.

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
| 6. Build the backend | Make database operations available through application code, with login, validation and permissions. | **Initial agreed implementation verified:** fresh native case/fleet/account/import checks and 202 automated tests passed in the 30 October integrated run. |
| 7. Build the frontend | Connect screens and forms to the backend so users can perform the workflows. | **Current journeys verified on 30 October:** a fresh 238-check cumulative browser run, including the import instructions, plus representative screenshot review. Import initiation itself runs in a local terminal. |
| 8. Analyse, improve and test the whole application | Build analytics, measure query performance, and test complete workflows and failures. | **Defined technical milestone passed on 30 October:** integrated acceptance, failure/concurrency checks and cleanup. The 29 October benchmark evidence was validated and four current result sets matched; timings were not rerun. Wider guarantees beyond the recorded scope are not claimed. |
| 9. Document and deliver | Make the project reproducible and prepare the report, demonstration and submission package. | **Current stage, in progress:** manual and locally verified source/data review candidate prepared on 30 October; teammate reproduction, final freeze, report/slides/video, timed team rehearsal and final submission checks remain. |

We chose to establish the database foundation before substantial interface work.
That lets us check that the data and relationships support our promised features.
The first authenticated application workflow, personal saved vehicles, now works
through HTTP, a terminal menu and browser forms. Browser screens use the same APIs,
so permissions and database operations stay in the backend.

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
users through the API/menu; analyst-case records now have their own API/menu too.
Fleet/work-order records now also have owner-scoped APIs, a terminal client and
browser forms.

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

At that milestone these were API features; browser auth forms were added on
29 October. Case ownership was subsequently connected to its workflow
on 29 October; fleet ownership was subsequently connected and checked that day too.

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

### We added complaint browsing and narrative search

The safety profile gives a summary, such as 885 complaints for a 2022 Honda Civic.
The new complaint API lets you read the individual reports behind that count.
You can filter by vehicle, component, receipt date and reported incident attributes,
search narrative words, and open one complaint's full text and source information.

For example, asking for `component=STEERING` checks whether STEERING is in the
document's component list. Asking for `hasInjuries=false` checks for a reported
count of zero; an unknown count remains unknown. A **page** is a small batch of
matching records, which keeps responses manageable instead of sending every
complaint at once. This is read-only MongoDB access through Flask.

On 28 October, 71 automated tests and 42 live HTTP checks passed. The Civic list
agreed with the existing profile, and checked stored record counts were unchanged.
See [Backend step 4](docs/BACKEND_STEP_4_COMPLAINTS.md) and
[complaints_verification_report.json](docs/complaints_verification_report.json).
The first complaint milestone returned JSON; the profile now presents paginated
complaints/full narratives. The dedicated full-filter explorer remains planned.
Complaint linking to internal cases was subsequently added on 29 October.

### We added recall and official-investigation details

The Civic safety summary's 4 recalls and 2 official investigations can now be
opened as individual records. Recall details include the official summary,
consequence and remedy. Investigation details keep all associated manufacturers,
components and linked campaign numbers, including recalls outside our snapshot.
Related vehicle lists and recall source rows are paginated separately.

A campaign can have several source rows for the same vehicle, so counting a join
directly could count one campaign many times. We use SQL `EXISTS` to ask whether a
matching relationship exists and return each campaign once. New public views let
the restricted SQL reader answer these requests without access to account data.

On 28 October, 92 automated tests and 79 live HTTP checks passed. Lists agreed
with direct SQL and the earlier safety-profile counts. Checked stored counts
remained unchanged. See [Backend step 5](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md)
and [official_records_verification_report.json](docs/official_records_verification_report.json).
This completed the planned core research endpoints at that milestone. Analyst
cases and fleets were added afterward. Analytics, browser pages and broader
application evaluation remain.

### We connected the internal analyst-case workflow across both databases

An ANALYST can create/read/edit/delete their own cases, link complaints for the
same vehicle, write notes/findings, set tags/components and change status/priority.
An ADMIN can inspect/manage other analysts' cases and recover their pending work.
Normal users retain public research/personal saves but cannot use the case workspace.
The server fixes the creator/assignee/vehicle when creating a case; reassignment
is not implemented. Notes and findings retain their original author when edited.

SQL stores the structured case and its status history. MongoDB stores the flexible
content. A SQL **outbox** is a saved to-do record describing the MongoDB change.
For example, if SQL creates a case while MongoDB is unavailable, that request is
reported as PENDING. An authorized retry uses the saved task to finish it after
MongoDB is reachable again. The content is hidden while pending so a reader does
not confuse an older version with the current SQL case.

Each change has a **request ID**. Repeating that same request ID finishes/reports
the original change, rather than creating another case or note. An ordered
**revision** identifies the content version. SQL locks and a pending-operation
rule stop another edit overtaking an unfinished one. An admin can also finish a
pending deletion after its SQL parent has been removed. This is explicit recovery
across two commits; there is no automatic background recovery worker.

On **29 October**, 121 automated tests and 99 recorded live HTTP checks passed,
plus concurrent-request and real terminal-menu flows. SQL-before-commit, MongoDB
write/response and SQL-acknowledgement failures were injected and recovered. A fresh
server instance recovered a saved task. Temporary accounts/cases/content/operations
were cleaned up and checked record counts matched the starting counts. Earlier
full database/import verification remains dated 25 October.

See [Backend step 6](docs/BACKEND_STEP_6_ANALYST_CASES.md) and
[cases_verification_report.json](docs/cases_verification_report.json). This
completed the case substep within Stage 6; the fleet backend followed it.

### We completed the small fleet/recall-work-order backend

Any signed-in user can create/rename/delete their own fleets, add/remove labelled
fleet vehicles, browse matching recalls and maintain work orders. All human roles
follow the same personal fleet ownership rule, including ADMIN. Fleet management
here stays limited to the recall-tracking workflow in our proposal.

One catalogue identity, such as `2022 HONDA CIVIC`, can describe both `Car 1` and
`Car 2` in a fleet. They get different fleet-vehicle IDs and independent orders.
Four Civic campaigns therefore produce eight vehicle–recall matches for those
two vehicles. A personal saved vehicle is a bookmark; a fleet vehicle is an
owner-entered record used for tracking. These IDs answer different questions.

SQL's composite foreign keys prevent an order referring to a recall for another
model-year. Its unique rule prevents two orders for one fleet-vehicle/recall pair.
Transactions and fleet-row locks preserve simultaneous edits. **Cascade deletion**
means deleting a fleet also deletes its contained vehicles/orders; deleting only
an order keeps the vehicle and official recall. COMPLETED is the owner's tracking
status and does not verify VIN applicability or prove a repair.

On **29 October**, 145 automated tests, 110 recorded live HTTP checks, six concurrent
requests and the real terminal flow passed. Foreign/admin access, timestamps,
duplicates, SQL constraints, concurrent writes and cascades were checked. Owned
fixtures were removed and checked existing/reference counts matched the baseline.
See [Backend step 7](docs/BACKEND_STEP_7_FLEETS.md) and
[fleets_verification_report.json](docs/fleets_verification_report.json).

This verified the planned core workflow APIs. Browser workflows, admin monitoring
and descriptive analytics were subsequently added in the milestones below. The
first planned interface is now verified; performance/final evaluation and
submission preparation remain.

### We built and checked the first browser interface

RecallScope now opens at the Flask server's home address. You can search an exact
make/model/year or browse matches, open the safety profile, switch between recall/
complaint/investigation records, and expand full details. The profile also displays
the existing complaint component counts as bars; a complaint can mention more than
one component, so these counts can overlap.

Browser registration/login uses the existing account/session APIs. A signed-in
user can save a vehicle, edit its nickname and confirm or cancel removal. The
browser sends requests to Flask; it does not connect to either database directly
or receive the service credentials. Terminal clients and the browser have their
own cookies, while both use the same stored application account and saved rows.

On **29 October**, 151 automated tests and 32 real-browser checks passed using
Chrome at desktop and an emulated 390px mobile size. Checks included public research,
real registration/login/logout, saved-vehicle CRUD, account isolation, safe display
of nickname markup, unsafe return links, history after logout and error recovery.
Synthetic accounts/saves/sessions were removed and checked stored counts matched
the baseline. The pages were also inspected in desktop/mobile screenshots.

See [Frontend step 1](docs/FRONTEND_STEP_1.md), its
[verification report](docs/frontend_step_1_verification_report.json) and
[search screenshot](docs/screenshots/frontend-step-1/search-desktop.png).
This first milestone began Stage 7. The subsequent research extension is below;
at that point, case/fleet/admin screens were still planned. The later milestones
below record their progress.

### We extended browser research with filters and record relationships

The **Complaints** page now filters reports by vehicle, exact component name,
narrative words, received dates and reported crashes/fires/injuries/fatalities.
Filters and page numbers appear in the URL so a teammate can reopen the same
research view. “No” and “Zero reported” exclude unknown stored values. The selected
vehicle profile's **Filter complaints** link fills its make/model/year for you.

Each record now has a standalone page. A complaint shows its full narrative and
source information. Recall/investigation pages show related vehicle identities;
recalls also expose paginated source rows, and investigations link to available
recall campaigns. For example, one recall campaign can have thousands of source
rows, each describing a component, vehicle or production period. These are not
thousands of separate campaigns. Model-year identities also are not VIN matches.

On **29 October**, **151 automated tests and 71 real-browser checks passed**,
including the earlier browser workflows and new filter/history/error/relationship
journeys. Chrome desktop and 390px mobile output were inspected. Owned test
accounts/saves/sessions were removed and checked database counts were preserved.
No migration or reimport was needed: these pages use our existing read-only APIs.

See [Frontend step 2](docs/FRONTEND_STEP_2.md) and its
[verification report](docs/frontend_step_2_verification_report.json).
The next browser milestone after that research extension is recorded below.

### We built the analyst case workspace and recovery controls

Analysts can now create a case for a selected vehicle, edit its title/priority/status,
organise tags/components, link matching complaints and add/edit/remove notes and
findings in the browser. Status history comes from our SQL trigger. Analysts see
their own cases; admins have explicit case oversight. Normal users see an access
explanation, while the APIs independently enforce those permissions.

A case update spans two databases. A **saved update awaiting completion** means
the instruction is in PostgreSQL but completion with MongoDB is unresolved. The
page hides unsynchronized content, blocks new edits and offers **Retry saved update**.
If a connection error leaves the outcome uncertain instead, **Retry same change**
keeps the original request key and payload, avoiding duplicate work. That local
retry body stays only in memory; a durable pending receipt survives page reload.
The dashboard also retains a deletion receipt after its SQL case has been removed.

On **29 October**, **151 automated tests and 115 real-browser checks passed**,
including prior journeys and the new case lifecycle, role isolation/admin access,
lost-response retry, pending updates, deletion recovery, history and session-expiry
cleanup. Desktop/mobile output was reviewed. Owned fixtures were removed and
checked stored counts were preserved. Existing account roles were retained.

At that case milestone, the access check found one normal user and no admin.
The later fleet milestone's read-only check confirmed that a persistent admin
has since been prepared; see its evidence below. An admin can use cases directly.
Role-management screens were added in the later admin milestone below; ordinary
registration cannot grant itself analyst access. `scripts/create_admin.py` is only for the first admin
on a setup that has none.

See [Frontend step 3](docs/FRONTEND_STEP_3.md) and its
[verification report](docs/frontend_step_3_verification_report.json).
The fleet/work-order browser milestone that followed is recorded below.

### We added personal fleet and work-order browser pages

Every signed-in role can now create/rename fleets, search/select catalogue vehicles,
add or rename labelled entries, view matched recalls and create/edit work orders.
The **My fleets** link uses your existing normal account; you do not need an admin
for this workflow. All fleet/vehicle/order APIs enforce personal ownership, even
for ADMIN. This differs from the explicit admin oversight of internal cases.

The screens distinguish a **catalogue identity** (2022 HONDA CIVIC), a personal
bookmark in **My vehicles**, and a labelled fleet entry such as **Car 1**. Two Civics
can therefore produce eight vehicle–recall pairs for the same four campaigns.
Matches use make/model/year, not a VIN, and work-order statuses are your tracking
record rather than proof of repair completion.

Recall matches can be filtered by tracked status or a selected fleet vehicle;
orders can also be filtered by status. Fleet/vehicle/match/order lists paginate
independently. Cancelled orders stay tracked. Completing records a timestamp,
repeating Completed keeps it, and reopening clears it. Confirmed removals use SQL
cascades: a vehicle's orders go with that vehicle, and a fleet's entries/orders go
with the fleet. Cancelling the confirmation preserves them.

Fleet writes use SQL transactions. If a response is lost or unreadable, **Refresh
and review records** reads the current state before another edit is enabled; it
does not automatically repeat the write. The case retry handler was also hardened
for unreadable successful responses while retaining the original command key.

On **29 October**, **151 automated tests and 163 real-browser checks passed**,
including earlier journeys, normal-user fleet access, duplicates, selected-vehicle/
status filters, timestamps, pagination, deletion/cascades, admin/other-owner denial,
logout/session-expiry cleanup and uncertain-write review. Desktop and 390px mobile
output were reviewed. Owned fixtures were removed and checked stored counts matched
the baseline. No import, migration or new runtime dependency was needed.

See [Frontend step 4](docs/FRONTEND_STEP_4.md) and its
[verification report](docs/frontend_step_4_verification_report.json).
The report's separate read-only account-role check on 29 October records one
ADMIN and one NORMAL_USER. Existing accounts/roles and their records were retained;
the first-admin bootstrap does not need to be repeated on this computer.
The admin monitoring and role-management milestone that followed is recorded below.

### We added admin roles, current dataset sizes and import history

An admin can now open **Admin → User roles**, choose an account's role and review
the before/after change before confirming. Cancelling leaves the account unchanged.
The server protects the last administrator. Losing admin access, signing out or
an expired session clears private admin views; role changes affect later requests
in the existing session. Normal users and analysts cannot read these admin pages'
protected data.

The **Datasets** view answers “what is stored now?” using SQL reference counts and
a MongoDB complaint count. **Import history** answers “what did each past attempt
do?” It shows started/completed times, outcomes, rows read and inserted/updated/
skipped/rejected counts, with filters and pagination. A repeated complaint import
can refresh 428,837 existing documents without inserting another 428,837 copies.
Earlier failed attempts remain in history after later successful loads; they do
not by themselves describe today's database health.

The missing admin read APIs now use two narrow SQL views and the existing reader.
Direct access to raw audit/account/session tables remains ungranted to that SQL
reader. Failure details are limited to approved categories, and invalid source
fingerprints are hidden. The views/grants were applied locally without rebuilding
or reimporting data; the SQL schema version remains 3.

On **29 October**, **159 automated tests and 195 real-browser checks passed**,
including all earlier journeys, admin gates, dataset units, import filters/pages,
confirmed/cancelled/uncertain role changes, self-demotion and private-data cleanup.
The real last-admin SQL was tested using one synthetic account in a temporary SQL
table; an injected browser rejection checked the UI without demoting real admins.
Restricted-reader permissions and sanitized audit projections passed native checks.
Owned fixtures were removed, original import history retained, and checked counts
matched the baseline. Desktop/mobile output was reviewed.

See [Frontend step 5](docs/FRONTEND_STEP_5.md) and its
[verification report](docs/frontend_step_5_verification_report.json).
The analytics milestone that completed the first planned browser implementation
is recorded below.

### We added descriptive analytics and completed the first browser implementation

The public **Analytics** page combines PostgreSQL reference counts with MongoDB
complaint aggregations. Choose an exact make/model, optionally a model year, and
received dates. Monthly points and component bars open the underlying complaints;
exact-value tables and a paginated model-year comparison accompany the charts.
The default dates follow the inspected complaint snapshot, 2020-01-01–2026-10-22.

Received dates filter complaints only; official counts use all stored dates. SQL
counts distinct campaigns/investigations across selected years, since one campaign
can affect several model years. Component labels overlap, and missing received
dates/unknown incident attributes are disclosed separately. Counts are descriptive
reports, not defect rates or safety ratings; no vehicle-population denominator is
available. Recent/partial months and zero-valued months need careful interpretation.

For example, the 2022 Civic gives 885 received complaints, four campaigns, two
investigations and 732 STEERING mentions. All Civic catalogue years together have
44 distinct campaigns, rather than the sum of every year's possibly shared records.
SQL uses canonical identities and distinct counts; a MongoDB facet computes the
complaint panels from one bounded scope.

On **29 October**, **170 automated tests and 219 real-browser checks passed**,
including all earlier journeys, chart/report links, keyboard activation, comparison
pages, zero/partial months, date validation, errors/retry and stale-response handling.
Native queries and an owned temporary collection checked UTC boundaries, unknowns,
overlapping components, missing dates and empty results. Desktop/mobile output was
reviewed, owned fixtures removed, and checked original counts/import history retained.

See [Frontend step 6](docs/FRONTEND_STEP_6.md) and its
[verification report](docs/frontend_step_6_verification_report.json).
This milestone established the first working interface for Stage 8 evaluation.

### We measured selected queries and improved complaint pagination

On **29 October**, four workloads were compared on full-sized temporary copies:
two SQL recall queries and two MongoDB complaint date windows. Each phase has 30
measured fetches, with excluded warmups, saved plans and matching ordered results.
The temporary schema/collection were removed and source counts/indexes checked.

The existing SQL vehicle indexes substantially reduced scan work. For complaints,
adding the ID tie-breaker to the vehicle/date index removed a blocking sort: the
broad-window plan examined 20 documents instead of 885. We then added that index
to the real collection and checked eight service pages plus five native assertions.
It retains all prior indexes and stored records. You do not need to reimport data,
restart Flask or run setup again to benefit from this local index change.

The [performance report](docs/PERFORMANCE_EVALUATION.md) explains query plans,
timing results, figures and limits. **177 automated tests passed** in the
[new dated run](docs/benchmarks/20261029T235059_28426da4/automated_tests.json).
The earlier browser run was not repeated for this change. Stage 8 remains in
progress: selected-query performance is verified; wider final review and
submission readiness are still pending.

### We reviewed requirements against the implementation and saved evidence

On **30 October**, we reread the original course brief, FAQ and submitted proposal,
then checked the agreed greenlight, source code and 17 historical evidence reports.
The four local raw ZIPs still matched the inspected source hashes. This proves
which files/evidence were reviewed; it does not rerun the application or change
the dates of earlier tests.

The [readiness review](docs/FINAL_READINESS_REVIEW.md) is a **requirements-to-evidence
map**: for each promise, it identifies the implementation, dated checks and remaining
work. At that baseline two commitments were partial: user-account deletion and
ADMIN import initiation. Account deletion was subsequently implemented and verified
as described below. Admin pages still only monitor imports, while loading uses a
trusted local command at that point. The later role-checked helper below closes G2.
No repeat import was needed for the document/source review.

We also prepared a [final demo checklist](docs/FINAL_DEMO_CHECKLIST.md) covering the
four user perspectives and the required presentation order. It is a plan that has
not yet been executed as the final rehearsal. Final report/manual/slides/video,
package verification and a teammate's fresh setup are still pending. No account
was deleted, import initiated or application test rerun during this review.

### We added restricted account deletion after finding the proposal gap

On **30 October**, we implemented the account-delete API and admin email-confirmation
dialog. Deletion only accepts an unused account belonging to someone else. Saved
vehicles, fleets, cases or past case operations block deletion, and the last
administrator is protected. Successful deletion revokes the target's sessions.

A **stored database function** packages this operation inside PostgreSQL. Our auth
SQL account can execute that guarded operation, but cannot freely delete user
rows. A shared lock coordinates it with role changes and account references.
**Migration 004 / schema version 4** records this additive installation; a schema
version tracks installed changes and does not mean the data was reset.

The [account-deletion report](docs/ACCOUNT_DELETION.md) links **183 automated tests,
29 native assertions and 23 live-database HTTP checks passed on 30 October**.
Native tests covered dependency guards and concurrent changes; API tests used only
disposable accounts and checked session revocation. Existing account/reference
counts matched after cleanup. No full import or new password entry was needed.

After the user approved a retry, **238 cumulative browser checks passed on 30 October**.
The [final browser report](docs/account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json)
includes the earlier journeys and confirmed/cancelled deletion, protected-account
rejection, lost/unreadable-response review, expiry and mobile layout. Independent
target sessions were revoked; owned fixtures were removed and original counts/
import history retained. Desktop/mobile screenshots were reviewed. The earlier
183-test/native/API results were not rerun during this browser-only follow-up.

G1 is now closed. The verifier needed a readiness wait and an explicit desktop
viewport; application code was unchanged. Initial pending/failed/intermediate
records remain historical evidence. The subsequent local-import milestone below
closes G2. Restart Flask to load the account route/UI if
trying the feature locally.

### We added the admin-authenticated import entry point

On **30 October**, we added `scripts/admin_import.py`. It signs in through Flask
using an existing ADMIN application account, shows the four approved local
archives, requires the word IMPORT, and rechecks the session/role before running.
It rejects missing/changed source snapshots and overlapping imports. The Import
history page documents this terminal workflow and reads the resulting stage logs.

An **upsert** inserts a new identifier or refreshes an existing record. An import
therefore changes reference data intentionally; it is not a health check or a
step needed every time Flask starts. The helper and the trusted first-setup
importer now share one ETL pipeline and one **session lock**, which remains held
across the separate stage commits. This keeps two import processes from running
over each other.

**196 automated tests and 32 native checks passed on 30 October**. The native run
used real app login and real ETL on five synthetic rows in an owned SQL schema
and MongoDB database. It verified role denial, cancellation, a busy lock, revoked
access, success, duplicate-free repeat imports, failure logging and cleanup. When
the complaint stage was deliberately rejected, earlier completed SQL stages
remained committed and the complaint stage was logged FAILED. This is why we
describe per-stage transactions rather than one rollback covering both databases.

All test fixtures were removed, with original counts/import history retained.
The real four source ZIPs were checked read-only; **no full real-data reimport was
performed**. You do not need to run the new import command to continue using the app.
Read [ADMIN_IMPORT.md](docs/ADMIN_IMPORT.md) for the supported command, evidence,
permissions and failure limits. G2 is closed. The earlier 238-check browser run
keeps its own verification time; it was not rerun for this CLI/static-note change.
The subsequent integrated technical run below now covers this workflow alongside
the browser and other native workflows. Delivery/reproduction work remains.

### We completed the integrated technical rehearsal

On **30 October**, `scripts/rehearse_project.py` ran the selected acceptance set
sequentially on the current working code: **202 automated tests, 238 browser
checks, native cases/fleets, account guards/API and admin-import ETL checks all
passed**. Case recovery was checked after recreating an owned API server/app
instance; fleet concurrency, ownership/constraints and terminal flows were checked
too. Test fixtures were removed and original counts/import history retained.

The [technical rehearsal report](docs/TECHNICAL_REHEARSAL.md) links each component
result. It recorded hashes for **135 implementation/test/configuration-template
files** and the four raw archives before/after, plus an unchanged private-config
result without exposing secrets. A **code fingerprint** identifies the file
contents actually tested. This is useful here because the working tree contains
uncommitted changes; the last Git commit alone does not identify the current app.

We also validated 20 saved plans and their timing summaries, then checked that
four current queries return the same ordered results. Those timings remain dated
**29 October**; fetching matching results does not create a new speed benchmark.
Representative import/case/fleet/mobile screenshots were reviewed.

This completes **Stage 8's defined technical acceptance milestone** and moves us
to **Stage 9**. It does not mean the team has rehearsed its ten-minute presentation,
that a new computer can follow the final manual, or that the submission files are
finished. Those are the next concrete tasks. The rehearsal used the existing
installation and owned fixtures, without a full real-source reimport.

### We prepared the manual and a checked source/data review package

The [user manual](USER_MANUAL.md) now separates **daily startup** from **first
installation** and explains research, account/saved/fleet tasks, analyst recovery,
admin operations and troubleshooting. It is written from the current scripts;
the [teammate checklist](docs/FRESH_SETUP_CHECKLIST.md) still needs an actual fresh
installation. A clear set of instructions is useful, but does not prove someone
else can follow it successfully.

A package is a portable collection of files. Our new builder includes the current
source, manual, dictionaries, all four exact raw ZIPs and saved evidence. It keeps
private `.env`, installed libraries, browser profiles and staging/database storage
out. It creates a **manifest**, a list of each included file and its fingerprint,
then reopens the ZIP and checks every member. The initial checked export is about
151 MiB. This is a source/data/manual review candidate, not the outer final
submission containing the report, slides and video.

On **30 October**, [210 automated tests passed](docs/packaging/20261030T043036Z-manual-package/automated_tests.json),
including eight new package tests. The [initial real ZIP check](docs/packaging/20261030T043036Z-manual-package/review.json)
passed all 450 included file hashes and four source archives. All **135 files**
from the earlier technical rehearsal still matched; the new package script/test
are additional files. The original 202-test/238-browser milestone remains dated
as recorded; no native/browser tests or full imports were repeated for packaging.
The final review export is rebuilt after these documentation updates, with its own
sibling `package_report.json`. See [package preparation](docs/SUBMISSION_PACKAGE.md).

**Current position stays Stage 9, in progress:** the manual and local export checks
are done for this review candidate; teammate reproduction, any resulting fixes,
final package freeze, report/slides/video and human rehearsal remain open.

## 6. What is in this repository, and where is the actual data?

| File or folder | Its purpose |
| --- | --- |
| `PROJECT_GUIDE.md` | This explanation and our ongoing progress tracker. |
| `README.md` | Technical setup instructions and commands. |
| `USER_MANUAL.md` | One walkthrough for new installation, everyday use, role-specific tasks and troubleshooting. |
| `docs/FRESH_SETUP_CHECKLIST.md` | Blank teammate reproduction plan; actual installation results remain pending. |
| `docs/SUBMISSION_PACKAGE.md` | Build/verify the source-data-manual ZIP and understand what still needs final delivery checks. |
| `docs/GITHUB_CHECKPOINT_2026-10-30.md` | Named milestone branch, parallel remote work and the scope of this source-sharing checkpoint. |
| `docs/PERFORMANCE_EVALUATION.md` | Selected-query measurements, beginner explanations, standalone figures and reproduction steps. |
| `docs/FINAL_READINESS_REVIEW.md` | Course/proposal/scope coverage, closed G1/G2, dated evidence and remaining final-delivery gates. |
| `docs/FINAL_DEMO_CHECKLIST.md` | Passed technical journeys and proposed five-speaker presentation budget; human rehearsal remains pending. |
| `docs/ACCOUNT_DELETION.md` | Restricted account policy, schema version 4 and native/API/browser evidence. |
| `docs/ADMIN_IMPORT.md` | Admin local-import command, archive/role/lock checks, real fixture-ETL evidence and operational limits. |
| `docs/TECHNICAL_REHEARSAL.md` | Current integrated acceptance results, tested code/data snapshot and remaining Stage 9 gates. |
| `data/raw/` | The original downloaded ZIPs; kept locally and excluded from Git. |
| `data/dictionaries/` | Descriptions of the source file columns. |
| `data/processed/packages/` | Local checked source/data review ZIPs and their reports; Git-ignored, not uploaded. |
| `etl/` | Python code that reads, cleans and imports the records. |
| `backend/` | Flask research, auth/admin, personal saves, cases/recovery and fleet/work-order services. |
| `backend/templates/` / `backend/static/` | Browser page structures, local CSS/JavaScript and the vector brand mark. |
| `sql/` | Construction/migrations/views; migration 002 adds sessions, 003 adds durable case operations/revisions. |
| `mongodb/schema.py` | MongoDB document validation and index definitions. |
| `scripts/` | Setup/import/verification commands and terminal clients for research, saves, cases and fleets. |
| `tests/` | Automated API tests with fake connections and data transformation tests. |
| `docs/` | Detailed design, inspection, scope and milestone evidence. |
| `.env` | Private reader/auth/personal-workflow/case SQL credentials and Flask signing key; excluded from Git. |
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
steps. The database foundation and research, auth/admin and personal saved-vehicle
APIs were pushed on 28 October as [commit 10adb9e](https://github.com/WilsonTeng8778/inf2003-databasesystems/commit/10adb9e5ec642bbe943227a8553bb666a6d3289e)
to the configured
[GitHub repository](https://github.com/WilsonTeng8778/inf2003-databasesystems).
Credentials, the Python environment and raw archives remain local; teammates
reproduce their databases using the README. A source-code push shares our work
without deploying the application or transferring the running databases.
Complaint browsing, official-record details, internal cases, fleet workflows and
the first six browser milestones were added afterward locally; the earlier push does
not include them. The [30 October milestone checkpoint](docs/GITHUB_CHECKPOINT_2026-10-30.md)
collects the completed current implementation and delivery preparation on
`milestone/recallscope-core-complete-2026-10-30`. GitHub `main` has a separate
implementation, so teammates should deliberately select the intended branch.

If you encounter SQLite in the ETL code, it is temporary scratch storage used
while grouping complaint rows. PostgreSQL and MongoDB remain the two application
databases.

## 7. What we will do next, in manageable steps

The **core workflow backend milestone is verified**. Research for all three record
types, authentication, personal saves, analyst cases/recovery and small fleets work.
These functions are now usable through browser screens; the first
research/auth/personal-saves pages, full complaint/record relationship pages and
the analyst case workspace, fleet/work-order screens, admin views and analytics are
verified. The Stage 8 technical evaluation/benchmark milestone has passed;
current work is Stage 9 reproduction and delivery.
Flask is the Python framework receiving web requests. An **API endpoint** is a particular request the backend
accepts, such as “find this vehicle” or “save this vehicle for me.”

| Order | Work | Status / successful result |
| --- | --- | --- |
| 1 | Start Flask and connect the existing databases. | **Done for read-only research:** vehicle search/profile and readiness work through HTTP. |
| 2 | Add registration/login, password hashing and sessions. | **Done through APIs and browser forms:** sessions, expiry/logout and password handling verified; browser registration/login checked on 29 October. |
| 3 | Enforce roles and ownership; configure application database access. | **APIs and browser permissions verified:** auth/admin guards, limited SQL accounts/views, personal ownership, case rules and admin role/data screens checked on 29 October. |
| 4 | Complete research and saved-vehicle operations. | **APIs/browser verified:** search/profile, complaint filters, full records/relationships, personal saves and descriptive analytics. |
| 5 | Add analyst-case operations across both databases. | **Done through APIs/menu and browser workspace:** CRUD, role/ownership/admin scope, complaint links, notes/findings/tags, SQL history and explicit recovery verified on 29 October. |
| 6 | Add the small fleet/work-order workflow. | **Done through APIs/menu and browser forms:** CRUD, recall matching, owner scope, timestamps, dependent-record cleanup and browser journeys verified on 29 October; backend concurrency evidence remains separately dated. |
| 7 | Expose admin dataset/import monitoring. | **Verified on 29 October:** restricted read views/APIs and admin role/data/import browser journeys. |
| 8 | Add descriptive vehicle analytics. | **Verified on 29 October:** distinct SQL totals, MongoDB facets, chart drill-throughs and model-year comparisons. |
| 9 | Close the user-delete API gap from the proposal. | **SQL/API/browser verified on 30 October:** guarded unused-account deletion, session revocation, dependency and concurrency checks. G1 acceptance is complete. |
| 10 | Close the admin import-initiation gap. | **Verified on 30 October:** local ADMIN sign-in, approved-source confirmation, shared lock/pipeline, 196 automated tests and 32 real auth/CLI/ETL checks. G2 is complete. |

Our Stage 7 browser plan is:

| Order | Browser work | Status |
| --- | --- | --- |
| 1 | Shared layout, research/profile/record details, registration/login and personal saves. | **Verified on 29 October:** 32 real-browser checks and reviewed desktop/mobile output. |
| 2 | Dedicated complaint explorer/full filters and additional official-record/relationship pages. | **Verified on 29 October:** 71 browser checks including prior journeys, full filters and record relationships. |
| 3 | Analyst case workspace, content editing and pending-operation recovery. | **Verified on 29 October:** 115 browser checks including prior journeys, case workflows, permissions and recovery. |
| 4 | Fleet vehicle/recall/work-order screens. | **Verified on 29 October:** 163 browser checks including previous journeys, personal ownership, tracking and deletion/cascades. |
| 5 | Admin user/role/data/import-log views. | **Verified on 29 October:** 159 automated tests, 195 browser checks and isolated native SQL monitoring/guard checks. |
| 6 | Analytics/dashboard queries and browser presentation. | **Verified on 29 October:** 170 automated tests, 219 browser checks and native counting edge cases. First planned browser implementation established. |
| 7 | Confirmed unused-account deletion in administration. | **Verified on 30 October:** 238 cumulative browser checks, separate session checks and reviewed desktop/mobile screenshots; owned fixtures removed. |

A full import is not a routine step every time we add a page or restart Flask.

The first Stage 8 performance milestone is **verified on 29 October**. We compared
two SQL recall queries and two MongoDB complaint date windows on full-sized,
temporary copies, with 30 measured fetches per phase, saved query plans and equal
ordered-result checks. The copies were removed; source counts/indexes were
unchanged during the controlled experiments. We then separately added a measured
MongoDB pagination index and verified the real service. Read the beginner
explanation, results and limits in [PERFORMANCE_EVALUATION.md](docs/PERFORMANCE_EVALUATION.md).

An index is like a book's index: it helps locate selected entries. Our existing
complaint index found reports for a vehicle/date window, but still sorted all
885 broad-window matches to choose the first 20. Including the complaint ID in
the index's ordering let MongoDB fetch the first 20 directly. This helps explain
the measured change; it does not mean every website action becomes faster by the
same amount. SQL and MongoDB workloads are evaluated within each DBMS, not ranked
against each other.

**Next planned Stage 9 work:**

1. Give a teammate the checked source/data/manual review ZIP and have them follow
   the [fresh-setup checklist](docs/FRESH_SETUP_CHECKLIST.md). Record actual results;
   ZIP integrity and the existing-machine rehearsal do not establish fresh installation.
2. Correct any reproduction/manual issues and rebuild the chosen candidate. Keep
   the exact ZIP hash with the teammate's results; do not silently replace its data.
3. In parallel, prepare the final report from design, functional and performance evidence;
   obtain/check the current XSite template and submission details.
4. Finish slides/video and conduct the timed five-member presentation rehearsal,
   then check the final report/video/package constraints before submission.

One important backend problem is that a SQL transaction cannot automatically undo
a MongoDB write. Case workflows now have tested pending-operation recovery for
that boundary, including retries after a new server instance starts. Whole-system
evaluation now includes the fresh integrated technical journeys. The dated case
and rehearsal reports describe which faults were simulated; human presentation
and packaged-source reproduction remain Stage 9 work.

## 8. A small way to see the current work yourself

The setup, package installation, database construction and full imports in the
README were already carried out on this computer on 25 October. Those commands
are included so the setup can be reproduced; you do not need to repeat all of
them yourself before continuing. Flask and its SQL reader were prepared here on
28 October too. Session storage and auth credentials have now also been prepared;
there is no need to rerun the large imports.

### Open the browser interface

From a terminal at the repository root, run:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

If Flask was already running, stop the older process with Ctrl+C before starting
the updated code. Keep the new server running and open
[RecallScope](http://127.0.0.1:5000/) in your browser. You should see the vehicle
search page. A JSON response at the home address means the old Flask process is
still running; the JSON discovery response is now at `/api`.

Click **Try 2022 Honda Civic**, then **View safety profile**. You should see 4
recalls, 885 complaints and 2 investigations for the verified snapshot. Switch
the record type and expand one record. Then sign in with your existing application
email/password, save the vehicle and open **My vehicles** to rename/remove a save.
If it was already saved using the terminal helper, the browser shows the same
stored bookmark. Creating a new account is optional if you already registered.

The old [JSON profile API](http://127.0.0.1:5000/api/vehicles/safety-profile?year=2022&make=HONDA&model=CIVIC)
still works for inspecting the response behind the page. The
[browser walkthrough](docs/FRONTEND_STEP_1.md) describes page behavior and verification.

For the newest pages, click **Filter complaints** in the Civic profile. Enter
**STEERING** as the component and apply the filter: our snapshot has 732 matches.
Expand **Dates & incident details** for the remaining filters, then open a full
complaint. From a profile's recall/investigation cards, follow **Related vehicles &
record details** to explore linked vehicles, source rows and recall relationships.
The [research walkthrough](docs/FRONTEND_STEP_2.md) explains these pages and terms.

For analyst cases, sign in as ANALYST/ADMIN and choose **Analyst cases**. Normal
users cannot enter this workspace. If no admin exists yet, run
`.\.venv\Scripts\python.exe scripts/create_admin.py` locally, choose a new email and
password at its hidden prompts, then sign in with that new admin account. The
[case browser walkthrough](docs/FRONTEND_STEP_3.md) covers setup, the first case and
both recovery controls. This does not require rebuilding or reimporting databases.

For fleets, use your existing account and select **My fleets**. Create **Family
cars**, add **2022 HONDA CIVIC** as **Car 1**, and create a work order from one of
its recall matches. Normal users can do this too. The
[fleet browser walkthrough](docs/FRONTEND_STEP_4.md) explains the forms, filters,
statuses and deletion behavior.

For administration, sign in with your existing admin account and choose **Admin**.
Use **Datasets** for current inventory, **Import history** for recorded attempts,
and **User roles** to review/confirm a teammate's access change. To give your normal
account analyst access, change that account to **Analyst** using the admin page,
then sign in with it. The [admin walkthrough](docs/FRONTEND_STEP_5.md) explains the
permissions and the difference between inventory and import counters.

For analytics, choose **Analytics → Try 2022 Honda Civic**. Click a component bar
or a monthly point to open matching complaints, and leave model year blank for a
comparison across the selected make/model's years. The
[analytics walkthrough](docs/FRONTEND_STEP_6.md) explains the units, missing data
and date coverage. No account, reimport or package installation is required.

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

### Browse individual complaints

With the updated Flask server running, open
[five Civic complaints](http://127.0.0.1:5000/api/complaints?year=2022&make=HONDA&model=CIVIC&pageSize=5).
You should see a list with short narrative previews and pagination information.
The `total` is 885 for our verified snapshot; `pageSize=5` shows five at a time.
Add `&page=2` to the address for the next page, or `&component=STEERING` to filter
the component list. Add `&q=steering` to search narrative words instead.

Copy an item's `odiNumber` into the end of
`http://127.0.0.1:5000/api/complaints/ODI_NUMBER` to open its full narrative and
source metadata. These requests do not need login and only read existing data.
The [complaint walkthrough](docs/BACKEND_STEP_4_COMPLAINTS.md) explains all filters,
including date ranges and the difference between zero and unknown injuries.

### Open recalls and official investigations

Restart Flask to load the new routes, then open
[the Civic recall list](http://127.0.0.1:5000/api/recalls?year=2022&make=HONDA&model=CIVIC)
or [its official investigation list](http://127.0.0.1:5000/api/investigations?year=2022&make=HONDA&model=CIVIC).
Each item has a `detailUrl`: append that path to `http://127.0.0.1:5000` to open
the full record. In a detail response, `links.vehicles` shows related make/model/
year identities. Recalls also have `links.records` for their original source rows.

These counts answer different questions. `affectedVehicleCount` counts distinct
vehicle identities such as a 2022 Civic, while `potentiallyAffected` is the source's
reported number of units. Source rows can repeat a vehicle for different components.
The [official-record walkthrough](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md) explains
the filters, pagination and SQL permissions. The required views/grants are already
applied here; you only need the updated Flask process to try the feature.

### Try internal analyst cases

The case schema/role/validator setup was applied on 29 October. Restart Flask,
then run this in another terminal:

```powershell
.\.venv\Scripts\python.exe scripts/try_cases.py
```

Sign in using an ANALYST or ADMIN application account. A normal registered account
will be denied this workspace. If there is still no administrator, the existing
local `scripts/create_admin.py` helper can create the first one with a new email
and hidden password prompt. Administrators can assign analyst roles afterward;
you do not put an application password in `.env`.

Create a case for `2022 HONDA CIVIC`, list/view it, add a note and change its status.
Read status history to see the SQL trigger's entries. You can inspect the case row
in pgAdmin and its `case_details` document in Compass. Your cases persist after
sign-out. The verifier's synthetic cases were removed, so testing did not leave
demonstration accounts/cases for you to log into.

If an operation says PENDING, the helper can list/retry it. If a write's response
was uncertain, option 12 repeats the last command using its original request ID.
The [case walkthrough](docs/BACKEND_STEP_6_ANALYST_CASES.md) explains permissions,
recovery, limits and every menu/API action. The
[browser workspace](docs/FRONTEND_STEP_3.md) now provides those case workflows too.
The fleet terminal workflow is also available below.

### Try fleet recall tracking with your existing account

The workflow permission update was applied on 29 October. Restart Flask, then run
this in another terminal:

```powershell
.\.venv\Scripts\python.exe scripts/try_fleets.py
```

Your existing NORMAL_USER account can use this feature. Create a fleet, add a
2022 Honda Civic labelled `Car 1`, browse recall matches and create an order from
one displayed recall ID. Update its status/notes, then read it again. You can see
the rows in pgAdmin's `fleet`, `fleet_vehicle` and `work_order` tables.

Signing out keeps your records. Deleting a fleet removes its vehicles/orders too;
the menu labels this behavior. The [fleet walkthrough](docs/BACKEND_STEP_7_FLEETS.md)
explains the IDs, ownership rules, matching limitations and available operations.
No reimport, new software or additional password entry in `.env` is needed here.

If the helper reports that the requested URL was not found, the Flask process may
still have an older version of the code loaded. On 29 October, this was confirmed
on the server listening at port 5000. Stop that server with Ctrl+C and restart it
using the Flask command at the start of this section; rerun the helper in a second
terminal. The helper now checks for missing fleet routes before sign-in and gives
these instructions. See [generic 404 troubleshooting](docs/BACKEND_STEP_7_FLEETS.md#troubleshooting-a-generic-404).
The restart reloads application code and retains stored database records.

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
| Outbox / pending operation | A saved SQL to-do record that lets us finish a case's MongoDB change after a failure or server restart. |
| Idempotency key / request ID | A unique ticket for one change; reusing it with the same command avoids duplicate cases or notes. |
| Content revision | A case content version number used to keep SQL metadata, pending tasks and the MongoDB snapshot in order. |
| Cascade deletion | A SQL rule removing related child records, such as a fleet's vehicles/orders when that fleet is deleted. |

## 10. Remaining course deliverables

According to the supplied project brief, final submission is **29 November 2026,
11:30 PM**. Check XSite for any later course announcements.

We still need the finished application, final report, slides, presentation video,
and source/data/user-manual package. The report is limited to 10 main-content pages
and the video to 10 minutes; all five members must present. The existing README
and design notes are useful inputs, but are not the finished submission.

Our report needs to explain the data model, both databases' operations and advanced
features, performance evidence, problems encountered and improvements. Core
backend/interface workflows and selected index experiments have dated evidence.
The [30 October review](docs/FINAL_READINESS_REVIEW.md) records both G1/G2 closures
and the remaining delivery gates. The [integrated technical acceptance](docs/TECHNICAL_REHEARSAL.md)
passed; the manual and local source/data review ZIP are now prepared and checked.
Fresh-setup proof, human rehearsal, report/video and final package checks remain.
Documentation and ZIP validation alone do not complete those gates.

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
| 28 October 2026 | Pushed a GitHub checkpoint of the database foundation and backend through saved vehicles, excluding credentials, raw archives and local environments. | [Commit 10adb9e](https://github.com/WilsonTeng8778/inf2003-databasesystems/commit/10adb9e5ec642bbe943227a8553bb666a6d3289e); source sharing, not application deployment. |
| 28 October 2026 | Added public complaint lists/details, vehicle/component/date/incident filters and indexed narrative search. | [Backend step 4](docs/BACKEND_STEP_4_COMPLAINTS.md): 71 automated tests and 42 live HTTP checks passed; Stage 6 continues with remaining official-record APIs and case/fleet workflows. |
| 28 October 2026 | Added recall/official-investigation lists/details, affected-vehicle/source pages and public SQL research views; applied reader grants locally. | [Backend step 5](docs/BACKEND_STEP_5_OFFICIAL_RECORDS.md): 92 automated tests and 79 live HTTP checks passed; Stage 6 continues with analyst cases, then fleets. |
| 29 October 2026 | Added analyst-case CRUD, role/owner/admin rules, complaint links, nested notes/findings, tags, status history and durable SQL/MongoDB recovery; applied schema 3 and case SQL access. | [Backend step 6](docs/BACKEND_STEP_6_ANALYST_CASES.md): 121 automated tests, 99 recorded HTTP checks and concurrent/interactive flows passed; owned fixtures removed. Stage 6 continues with small fleets/work orders. |
| 29 October 2026 | Added owner-scoped fleet/vehicle/work-order CRUD, model-year recall matching and the terminal menu; updated workflow SQL grants without a schema rebuild/import. | [Backend step 7](docs/BACKEND_STEP_7_FLEETS.md): 145 automated tests, 110 recorded HTTP checks, six concurrent requests and the menu passed; fixtures removed. Core workflow backend verified; browser screens are next, with admin data/analytics integration planned. |
| 29 October 2026 | Diagnosed generic fleet-route 404s from an older running Flask server and added a pre-login route check with restart instructions to the fleet helper. | [Troubleshooting](docs/BACKEND_STEP_7_FLEETS.md#troubleshooting-a-generic-404): anonymous checks against older/fresh servers passed; no database writes or full CRUD rerun. The browser interface remains the next stage. |
| 29 October 2026 | Added the RecallScope browser interface for search/profile/record details, registration/login/logout and personal saved-vehicle CRUD; JSON discovery moved to `/api`. | [Frontend step 1](docs/FRONTEND_STEP_1.md): 151 automated tests and 32 real-browser checks passed; screenshots reviewed and owned fixtures removed. Overall Stage 7 is in progress, with full complaint filters and case/fleet/admin screens next. |
| 29 October 2026 | Added the full complaint explorer, shareable filter/page URLs and standalone complaint/recall/investigation pages with vehicle/source/recall relationships. | [Frontend step 2](docs/FRONTEND_STEP_2.md): 151 automated tests and 71 real-browser checks passed; screenshots reviewed and owned fixtures removed. Stage 7 continues with the analyst case workspace; fleet/admin/analytics work remains. |
| 29 October 2026 | Added browser analyst case files/forms, vehicle-scoped complaint selection, notes/findings, status/history and explicit save/deletion recovery; retained the existing account's normal-user role. | [Frontend step 3](docs/FRONTEND_STEP_3.md): 151 automated tests and 115 real-browser checks passed; controlled failures, permissions, desktop/mobile output and cleanup verified. Stage 7 continues with fleet/work-order screens. First-admin setup is needed locally to try cases. |
| 29 October 2026 | Added personal fleet/vehicle forms, recall matching and work-order browser screens; added read-before-resubmit handling for uncertain fleet writes and hardened case retries for unreadable responses. | [Frontend step 4](docs/FRONTEND_STEP_4.md): 151 automated tests and 163 real-browser checks passed; desktop/mobile output reviewed, ownership/cascades checked and owned fixtures removed. Stage 7 continues with admin user/role/data/import-log views. |
| 29 October 2026 | Added admin user-role confirmations, dataset inventory and filtered import history; implemented protected monitoring read APIs and two narrow SQL views/reader grants. | [Frontend step 5](docs/FRONTEND_STEP_5.md): 159 automated tests and 195 real-browser checks passed, including native permission/projection and isolated last-admin SQL checks. Owned fixtures removed and existing import history/records retained. Stage 7 continues with analytics/dashboard integration. |
| 29 October 2026 | Added bounded public analytics, monthly/component chart drill-throughs, incident-attribute tables and model-year comparisons with distinct official totals. | [Frontend step 6](docs/FRONTEND_STEP_6.md): 170 automated tests and 219 browser checks plus native counting edge cases passed; screenshots reviewed and owned fixtures removed. First planned frontend verified; overall Stage 8 begins with controlled performance evaluation next. |
| 29 October 2026 | Measured four SQL/MongoDB workloads on full-sized disposable copies, saved plans/raw samples/CSV/figures, then added the measured stable-order complaint index to the real collection. | [Performance evaluation](docs/PERFORMANCE_EVALUATION.md): 30 measured samples per controlled phase, ordered results matched, copies removed and source counts/indexes retained. Separate live follow-up passed five checks covering eight service pages; 177 automated tests passed. Browser evidence remains the earlier run. Stage 8 continues with final requirements/evidence review and demonstration/reproducibility checks. |
| 30 October 2026 | Reread the course brief/FAQ/proposal, mapped requirements to implementation and 17 dated evidence reports, checked four local archive hashes and prepared a draft final demo checklist. | [Readiness review](docs/FINAL_READINESS_REVIEW.md) / [review record](docs/readiness/20261030_review.json). G1 account deletion and G2 ADMIN import initiation are partial; final deliverables/reproduction remain pending. Documentation/source review only: no new features, DB operations or application tests. Stage 8 continues with G1, then G2 and final rehearsal. |
| 30 October 2026 | Added confirmed, unused-account deletion, a guarded SQL function/EXECUTE grant and migration 004; added admin controls and verification helpers. | [Account deletion](docs/ACCOUNT_DELETION.md): 183 automated tests, 29 native assertions and 23 live-database HTTP checks passed; owned fixtures removed and original counts retained. Browser launch was not executed because automatic approval review was at capacity. G1 browser acceptance remains pending; next G2 and final rehearsal. |
| 30 October 2026 | Completed the approved account-deletion browser follow-up, corrected verifier readiness/viewport setup and reviewed the new desktop/mobile captures. | [238-check browser report](docs/account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json) / [follow-up summary](docs/account_deletion/browser-20261030T023324-1a1c57a4/followup_summary.json): no uncaught browser exceptions; sessions revoked, owned fixtures removed, original counts/import history retained. Application code and earlier test reports unchanged. G1 closed; G2 admin import initiation is next. |
| 30 October 2026 | Added the ADMIN-authenticated local import helper, shared import pipeline/session lock and operator instructions on Import history. | [Admin import](docs/ADMIN_IMPORT.md): 196 automated tests and 32 native real-auth/CLI/ETL checks passed on isolated fixtures. Success, repeat, refusal, cancellation, access revocation and actual MongoDB failure/audit behaviour verified. Fixtures removed; original counts/history retained; no real snapshot reimport. G2 closed; final integrated rehearsal and manual/reproduction/deliverables are next. |
| 30 October 2026 | Ran the integrated technical acceptance set against a fingerprinted working tree; made case/fleet verifier outputs history-preserving and added six integrity tests. | [Technical rehearsal](docs/TECHNICAL_REHEARSAL.md): 202 automated tests, 238 browser checks and all selected native case/fleet/account/import checks passed. Four current benchmark result sets matched and 20 saved plans were validated without new timings. Code/config/archive/count checks passed; fixtures removed and representative screenshots reviewed. Stage 8 technical milestone complete; current Stage 9 is manual/package/fresh setup/report/slides/video and human rehearsal. |
| 30 October 2026 | Wrote the user manual/fresh-install checklist and added a source/data export tool with manifest and private-file/integrity checks. | [Package review](docs/packaging/20261030T043036Z-manual-package/review.json): 210 automated tests passed, including eight package tests; initial 450-file ZIP/four source hashes verified; earlier 135 implementation files unchanged. Refreshed export follows documentation updates. No app/native/browser rerun or database import; teammate installation, final freeze/report/slides/video/human rehearsal remain Stage 9 work. |
| 30 October 2026 | Prepared the completed local core implementation, delivery documentation and saved evidence as a named GitHub milestone checkpoint. | [Checkpoint scope](docs/GITHUB_CHECKPOINT_2026-10-30.md): `milestone/recallscope-core-complete-2026-10-30` preserves the verified version alongside six newer remote commits implementing overlapping workflows. Credentials/raw/package ZIPs remain excluded; no integration or application-test rerun. Stage 9 delivery and deliberate future integration remain open. |

At each meaningful milestone, we will update the date, current-position summary,
stage statuses, next actions and this log. New counts/test claims will include
their actual evidence and verification date. Plans will stay marked as plans until
implemented and checked. Detailed milestone reports preserve what was verified
at that point; this file explains our current position.
