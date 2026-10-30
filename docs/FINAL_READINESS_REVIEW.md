# Requirements and final-readiness review

**Reviewed:** 30 October 2026, Asia/Kuala_Lumpur. **Implementation/technical follow-ups:** later on 30 October. **Current stage:** 9 of 9, in progress.

The main research, analyst-case and fleet workflows have implementation and dated
test evidence. We also have substantial SQL/NoSQL design, CRUD, advanced queries
and controlled index measurements. **We are not ready to call the entire proposal
or final submission complete.** The baseline identified two partial items: account
deletion and application-admin import initiation. Account deletion is now implemented
and SQL/API/browser verified in the [account follow-up](ACCOUNT_DELETION.md).
The [admin local-import helper](ADMIN_IMPORT.md) is also implemented and verified.
**G1 and G2 are closed.** The [integrated technical rehearsal](TECHNICAL_REHEARSAL.md)
has now passed. Final deliverables, the timed five-member presentation rehearsal
and fresh-machine reproduction remain unfinished.

The original review read documents, source code and saved evidence without running
the application or databases. Its unchanged [baseline record](readiness/20261030_review.json)
refers to the then-latest 177-test and 219-browser-check runs on **29 October**.
The subsequent account milestone passed **183 automated tests, 29 native assertions
and 23 live-database HTTP checks on 30 October**. After the user approved a retry,
the browser follow-up passed **238 cumulative checks on 30 October**, with screenshot
review and cleanup. The earlier automated/native/API checks were not rerun for
verifier-only corrections. Initial pending and historical records remain intact.
The later G2 milestone passed **196 automated tests and 32 native auth/CLI/ETL
checks on 30 October**. It did not rerun the browser suite or reimport the real
source snapshot. The original review remains a distinct document/source audit.

The subsequent [integrated run](rehearsals/20261030T040558-cfe0d503/report.json)
passed **202 automated tests, 238 browser checks and fresh selected native
case/fleet/account/import checks on 30 October**. It preserved historical evidence,
original counts and source/configuration/archive consistency. Twenty saved benchmark
plans were validated and four current result sets matched; performance timings
remain dated 29 October. This is a new technical acceptance record, separate from
the original review and earlier milestones. It does not establish a fresh install
or the team's ability to deliver its presentation within ten minutes.

The later [manual/package review](packaging/20261030T043036Z-manual-package/review.json)
passed **210 automated tests**, including eight new package tests, and checked a
real source/data ZIP's 450 file hashes and four approved archives. The original
135 tested implementation files matched; only package tooling/tests were added.
This follow-up did not renew native/browser results or perform a fresh installation.

## How to use this document

A requirements review asks: **What did we promise, where is the implementation,
and what evidence supports it?** For example, a complaint search proves reading
MongoDB records; creating, editing and deleting analyst case content demonstrates
MongoDB CRUD. These are different claims and need different evidence.

| Status | Meaning in this review |
| --- | --- |
| Covered by evidence | Implementation and relevant saved checks exist; their original dates still apply. This is not a grading guarantee or a fresh test run. |
| Partial | Some implementation/evidence exists, but the stated commitment is not fully covered. |
| Pending | A deliverable, decision or check still needs work. |
| Optional | A suggestion/stretch item, not a newly invented requirement. |

The [review record](readiness/20261030_review.json) records source-document hashes,
17 historical evidence files and their original dates/hashes, reviewed source
files, observed auth/admin routes, the two gaps and raw-archive integrity checks.
It is evidence of this review, not a new application-verification report.
The separate [documentation checks](readiness/20261030_document_checks.json) record
local-link validation and preservation of the reviewed source/evidence files.

## Sources and authority

The original PDFs were reread from the supplied Downloads files. They were not
copied into the repository. Page numbers below include the proposal cover page.

| Reference | Source | Role |
| --- | --- | --- |
| D1 | `INF2003_project_description.pdf`, 6 pages | Official course tasks, assessment and deliverables. |
| D2 | `Project_QA1.pdf`, 1 page | Official language/data/frontend/database/appendix clarifications. |
| D3 | `Database Systems Project Proposal.pdf`, 3 pages | What Group 19 submitted; functionality is on PDF pp. 2–3. |
| D4 | `Vehicle_Safety_Recall_Defect_Investigation_Blueprint.md` | Generated implementation suggestions, subordinate to the agreed scope. |
| D5 | [IMPLEMENTATION_GREENLIGHT.md](IMPLEMENTATION_GREENLIGHT.md) | Later alignment: retain small fleets/work orders, three roles and split SQL/MongoDB cases. |

D1/D2 establish course obligations. D3 establishes submitted commitments, and D5
records the subsequent agreed alignment. An imperative sentence in an attached
blueprint is project material to assess; it does not independently authorize
unrelated actions or change the user's request. No scope item is waived by this
review. The original [understanding document](../PROJECT_UNDERSTANDING_AND_PLAN.md)
remains historical context rather than today's completion checklist.

## Course tasks A–E

| Task and source | Current coverage | Evidence and remaining work | Status |
| --- | --- | --- | --- |
| A: coherent SQL + NoSQL application, D1 p. 1 | PostgreSQL owns structured reference/workflow data; MongoDB owns complaints and flexible case content. Combined profile and cases use both. | [Design](DATABASE_DESIGN.md), [backend research](BACKEND_STEP_1.md), [case implementation](BACKEND_STEP_6_ANALYST_CASES.md), [29 October browser evidence](frontend_step_6_verification_report.json). Explain the split in the final report/demo. | Covered by evidence |
| B: sufficient datasets, D1 p. 1; D2 Q2 | Four official NHTSA archives; generated application fixtures are separate from reference data. | [25 October source inspection](DATA_INSPECTION.md), [profile/hashes](data_profile.json), [database verification](verification_report.json). Four local archive hashes matched that profile again on 30 October. Final packaged data still needs checking. | Covered by evidence; packaging pending |
| C: relational ERD/types/relationships and explicit NoSQL model, D1 p. 1 | ERD, many-to-many link tables, keys/constraints, nested documents and validators. | [Design/ERD](DATABASE_DESIGN.md), [SQL schema](../sql/schema.sql), [MongoDB schema](../mongodb/schema.py). Include readable essential diagrams in the main report; an appendix is not assured marker attention (D2 Q5). | Covered by evidence |
| D: construction and database functions including CRUD, D1 pp. 1–2 | Reproducible setup/imports; SQL saved/case/fleet/order CRUD; MongoDB case-document/nested CRUD; browser workflows. | [25 October database checks](verification_report.json), [29 October case checks](cases_verification_report.json), [fleet checks](fleets_verification_report.json), [30 October browser follow-up](account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json). The account-deletion follow-up is mapped under P4/G1 below. | Covered by evidence for substantial CRUD in both DBMSs |
| E: analysis/reflection, D1 p. 2 | Data-quality findings, architecture/recovery tradeoffs and controlled indexing measurements already documented. | [Data findings](DATA_INSPECTION.md), [case limits](BACKEND_STEP_6_ANALYST_CASES.md), [29 October performance evaluation](PERFORMANCE_EVALUATION.md). Final synthesis/reflections and broader final evaluation remain. | Partial as a final deliverable |

The course permits using different database functions/subsets in the two DBMSs;
duplicating the whole application in both is not required (D1 Tasks A/B). Its
frontend emphasis is demonstrating database functions, not elaborate visual design
(D2 Q3). The checklist should not turn a hybrid application into two redundant
implementations.

## Submitted and agreed implementation commitments

Dates in this table refer to existing evidence, not checks rerun on 30 October.

| ID / source | Commitment | Implementation and evidence | Status |
| --- | --- | --- | --- |
| P1, D3 p. 2 | Year/make/model search and unified safety profile | [Research service](../backend/services/research.py); [28 October HTTP report](api_verification_report.json); [29 October browser report](frontend_step_6_verification_report.json). | Covered by evidence |
| P2, D3 pp. 2–3; D5 §§4/9 | Real recalls, investigations, complaint narratives; complaint-only vehicles remain searchable | [ETL/data inspection](DATA_INSPECTION.md), [official-record APIs](BACKEND_STEP_5_OFFICIAL_RECORDS.md), [complaint explorer](FRONTEND_STEP_2.md), corresponding 28 October [official](official_records_verification_report.json) / [complaint](complaints_verification_report.json) checks. | Covered by evidence |
| P3, D3 p. 3; D5 §§3/13 | Saved vehicles, fleets, fleet vehicles and recall work-order CRUD | [Saved workflow](BACKEND_STEP_3_SAVED_VEHICLES.md), [fleet workflow](BACKEND_STEP_7_FLEETS.md); [28 October saved checks](saved_vehicles_verification_report.json), [29 October fleet checks](fleets_verification_report.json) and [browser forms](FRONTEND_STEP_4.md). | Covered by evidence |
| P4, D3 p. 3 | User create/read/update/delete | Registration, profile/admin list and role updates were already present. The [30 October follow-up](ACCOUNT_DELETION.md) adds guarded unused-account deletion, with automated, real SQL/HTTP and 238-check cumulative browser evidence. The documented policy protects accounts with work/history. | Covered by evidence; G1 closed |
| P5, D3 pp. 2–3; D5 §§5/13/14 | Analyst cases with linked complaints, nested findings/notes/tags, CRUD and SQL/MongoDB consistency | [Case service](../backend/services/cases.py), [outbox/recovery design](BACKEND_STEP_6_ANALYST_CASES.md), [29 October native/HTTP checks](cases_verification_report.json), [case browser checks](frontend_step_3_verification_report.json). | Covered by evidence |
| P6, D3 p. 3; D5 §15 | SQL joins, aggregates, subqueries, views, indexes, useful trigger, constraints and transactions | [Views](../sql/views.sql), [research views](../sql/research_views.sql), [history trigger](../sql/triggers.sql), [schema](../sql/schema.sql), [fleet service](../backend/services/fleets.py), [analytics service](../backend/services/analytics.py). Database checks on 25 October, later workflow checks on 28–29 October and [index plans](PERFORMANCE_EVALUATION.md) provide evidence. | Covered by evidence |
| P7, D3 p. 3; D5 §16 | MongoDB nested/array queries, text search, aggregation and compound indexes | [Complaint query service](../backend/services/complaints.py), [analytics facets](../backend/services/analytics.py), [MongoDB definitions](../mongodb/schema.py); [28 October complaint checks](complaints_verification_report.json), [29 October analytics checks](frontend_step_6_verification_report.json), [measured index improvement](PERFORMANCE_EVALUATION.md). | Covered by evidence |
| P8, D3 p. 3 | Component/trend dashboard charts | [Analytics milestone](FRONTEND_STEP_6.md), [29 October browser/native counting evidence](frontend_step_6_verification_report.json). Missing values, overlap, zero/partial months and model-year distinct counts are explicit. | Covered by evidence |
| P9, D3 p. 3; D5 §17 | Indexed versus unindexed representative queries in both DBMSs | [29 October controlled performance report](PERFORMANCE_EVALUATION.md), raw plans/timings/figures, result hashes and cleanup. Baselines retain required primary-key indexes; this limitation is explicit. | Covered for selected query workloads |
| P10, D3 p. 2 | Local demonstration without live external services | Reference data is imported locally; browser assets are local and APIs use local DB services. [29 October browser evidence](frontend_step_6_verification_report.json) ran locally. A final fresh-machine/offline rehearsal has not been performed. | Implementation/evidence present; final reproduction pending |
| P11, D3 p. 2; D4 interface suggestions | Responsive desktop-first web stack | Flask/Jinja, HTML/CSS/JavaScript and local charts; desktop/mobile screenshots in browser milestones. Custom CSS replaces the proposal's Bootstrap choice, and local JavaScript/SVG replaces the blueprint's Chart.js suggestion. These are implementation substitutions; explain them accurately in the final architecture. | Covered; technical substitution documented |
| P12, D5 §6 | NORMAL_USER / ANALYST / ADMIN permissions and administration | [Auth/role checks](BACKEND_STEP_2_AUTH.md), ownership, case-admin oversight and monitoring are implemented. The [30 October local-import helper](ADMIN_IMPORT.md) adds actual ADMIN-authenticated initiation with source confirmation, the shared lock/pipeline and native failure/success evidence. | Covered by evidence; G2 closed |

The selected dataset snapshot has **53,555 vehicle identities, 13,600 recalls,
3,626 official investigations and 428,837 complaint documents**, per the dated
foundation and subsequent count evidence. These are not live counts queried today.
The 29 October benchmark report records relevant counts and checks source counts/
indexes around its experiment; it does not replace every foundation test.

## Follow-up of the two identified scope gaps

### G1 — Account deletion from the submitted SQL CRUD list

D3 p. 3 explicitly includes users in its create/read/update/delete list. At the
review baseline the app supported creation, reading and role updates, with no
account-deletion route or browser control.
The broader SQL CRUD course task is demonstrated by other entities; that does not
automatically fulfil this narrower proposal promise.

**Implemented follow-up, 30 October:** an administrator can delete an eligible unused
account belonging to someone else after confirming its email. A restricted SQL
function checks current role, self/last-admin protection and saves/fleets/cases/
pending or completed operation history. Only sessions may cascade. Migration 004
and its narrow EXECUTE grant were applied; schema version is 4. Native/API tests
used owned fixtures and retained original counts. See [policy and evidence](ACCOUNT_DELETION.md).

**Closed, 30 October:** [238 cumulative browser checks](account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json)
passed, including lost/unreadable responses, confirmation/cancel, session expiry
and mobile controls. Independent target-session checks passed and screenshots
were reviewed. Earlier automated/native/SQL-HTTP evidence remains separately
dated, and the [follow-up summary](account_deletion/browser-20261030T023324-1a1c57a4/followup_summary.json)
records verifier-only fixes, cleanup and retained counts/import history. No existing
real account was a deletion target. The final overall rehearsal is still pending.

### G2 — Admin import initiation versus import monitoring

D5 §6 says ADMIN can perform or initiate imports. The baseline only had read-only
admin monitoring and trusted first-setup [import_all.py](../scripts/import_all.py),
which did not authenticate the application role. Local operating access and an
application role are different boundaries.

**Closed, 30 October:** [admin_import.py](../scripts/admin_import.py) is the supported
local ADMIN entry point. It authenticates through the app, validates the four fixed
archives against the inspected profile, requires IMPORT confirmation and rechecks
the session/role/identity after acquiring the shared import lock. It then actually
runs the existing ETL/audit pipeline. The Import history page documents the command
and reads outcomes; it is not a web import trigger. This is the role-checked helper
implementation contemplated by the review, not a waiver of admin import initiation.

[196 automated tests](admin_import/20261030T031357-c6d157f6/automated_tests.json)
and [32 native checks](admin_import/20261030T031357-c6d157f6/native_report.json)
passed. Native checks used real auth/CLI/ETL with owned SQL/MongoDB fixtures, covering
normal/analyst refusal, cancellation, overlapping runs, revoked/expired access,
snapshot mismatch, success, zero-duplicate repeat imports and a real MongoDB
failure with durable audit outcomes. Fixture cleanup and original counts/history
were checked. Real archive hashes were checked read-only; no full source import
was performed. [Operational limits](ADMIN_IMPORT.md) distinguish start-time
authorization, per-stage commits, interruptions and trusted local setup credentials.

## Submission deliverables and final checks

The supplied brief states **29 November 2026, 11:30 PM**, with XSite submission
(D1 p. 2). Later announcements, the report template and final accepted formats
have not been checked in XSite. The review baseline found no final PDF,
PowerPoint, MP4, source ZIP or report-template DOCX; teammates may have drafts
elsewhere. Absence from this repository is not a claim about their machines.
The later source/data/manual review ZIP is now built and locally checked; the
final report, slides, MP4 and outer submission package remain pending.

| Deliverable/check | What is already useful | What remains | Status |
| --- | --- | --- | --- |
| Final report | Design, data inspection, milestones, screenshots, tests and performance figures | Obtain XSite template; write/edit final report with discussion/reflections. Maximum 10 main pages, Calibri Body 12, excluding cover/references/appendix (D1 p. 3). | Pending |
| Slides | Feature/evidence map and [draft demo checklist](FINAL_DEMO_CHECKLIST.md) | Build informative PowerPoint; verify accepted `.pptx`/`.ppt` format because D1's wording differs between description and upload list. | Pending |
| Video | Existing working workflows and screenshots | Rehearse/record at normal speed, maximum 10 minutes; all five members present with names visible. Follow background/data → SQL implementation/demo → NoSQL implementation/demo → optional performance (D1 p. 3). | Pending |
| User manual | [USER_MANUAL.md](../USER_MANUAL.md) now covers setup/configuration/run/tasks/troubleshooting, with a [fresh-setup checklist](FRESH_SETUP_CHECKLIST.md) | Have a teammate follow the manual from the chosen package on a fresh setup and address observed issues. | Written; fresh-install validation pending |
| Source/data package | [Source/data/manual review candidate](SUBMISSION_PACKAGE.md) built and checked locally, including raw snapshot/dictionaries and current uncommitted source | Teammate reproduction and final freeze/content/access checks remain. Private configuration/libraries/live workflow storage are excluded. Raw data remains omitted from GitHub-only checkouts. | Local integrity verified; reproduction/final freeze pending |
| Outer submission package | Required components identified | Report PDF + slides + MP4 + source ZIP in outer ZIP, according to D1 pp. 2–4. Confirm Dropbox arrangement/format on XSite; if using the brief's >2 GB GitHub-link option, check marker access. | Pending |
| Final integrated rehearsal | [30 October technical acceptance](TECHNICAL_REHEARSAL.md): 202 automated tests, 238 browser checks, native workflows, recovery/concurrency and cleanup | Conduct the timed five-member presentation and fresh-package reproduction; retain their separate evidence. | Technical milestone passed; human/reproduction checks pending |
| Team contribution/peer review | Five-member requirement known | Agree actual speakers/contributions and complete each member's emailed peer review when issued. Do not invent contribution claims from generated code. | Pending team action |

The four raw archives total **137,707,247 bytes (about 131.3 MiB)** locally, as
checked in the review record. They now travel with the checked source/data/manual
review ZIP and its dictionaries/hashes, so a mutable upstream download cannot
silently replace the chosen snapshot without a verification failure. This still
does not establish fresh installation or a completed outer submission ZIP.
At the original review, the working tree contained modified/untracked implementation
files and the review did not commit, push or verify remote contents. The later
[GitHub checkpoint](GITHUB_CHECKPOINT_2026-10-30.md) records the named milestone
branch and the separate implementation already on remote `main`. A teammate must
select the intended branch/package; earlier review/test dates remain unchanged.

## Items this review does not add to the scope

Docker, a cloud deployment, duplicated SQL/MongoDB implementations, machine learning,
a safety score, a chatbot and general workshop management are not required to
close this checklist. Window functions/materialized views, extra datasets,
notifications and complaint-volume flags remain optional unless a specific
remaining requirement justifies them. Do not label them missing core features.
The draft proposal's trend flag was explicitly conditional on available time.

Limitations already recorded include model-level rather than VIN-specific recall
matching, consumer allegations rather than proven defects, case recovery rather
than distributed atomic transactions, and local warm-cache rather than production
load measurements. Keep these qualifications in the report and demonstration.

## Next work in order

1. Have a teammate reproduce the project from the checked source/data/manual
   review candidate, recording its exact ZIP hash and actual results.
2. Address reproduction/manual issues and rebuild/freeze the chosen final candidate.
3. Complete the report/template and slides/video, conduct the timed team rehearsal
   in the [demo checklist](FINAL_DEMO_CHECKLIST.md), and check formats/package/access
   against current XSite instructions.

The review itself is complete. The defined Stage 8 technical milestone passed;
Stage 9 delivery is in progress. G1/G2 and the integrated technical acceptance have
dated implementation/test evidence. Human presentation, fresh reproduction and
final deliverables remain open. The original source review alone did not complete
any application feature.
