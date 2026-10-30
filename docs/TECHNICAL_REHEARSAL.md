# Integrated technical rehearsal

**Verified:** 30 October 2026, 04:05–04:08 Asia/Kuala_Lumpur.
**Result:** passed. **Current position:** Stage 9 — document and deliver, in progress.

We ran the implemented research, owner, analyst and admin workflows against the
current working code and both native databases. The technical acceptance run
passed, including controlled failures, concurrency, cleanup and consistency checks.
This completes the defined Stage 8 technical evaluation milestone. The five-member
presentation rehearsal, fresh-machine installation and final deliverables remain
pending; passing these software checks does not complete those activities.

The [integrated report](rehearsals/20261030T040558-cfe0d503/report.json) is the evidence
index. JSON timestamps are UTC; the dates/times above use Kuala Lumpur time.

## What passed

These are separate kinds of checks, so their numbers should not be added together
and described as one test count.

| Area | Fresh result | Evidence |
| --- | --- | --- |
| Automated unit/API-contract tests | **202 passed**, including six new verification-tool integrity tests. | [Full runner log](rehearsals/20261030T040558-cfe0d503/automated_tests.txt); integrated report. |
| Analyst cases and recovery | **99 recorded HTTP checks, 9 assertions**, concurrent requests, terminal menu and recovery after an owned API server/app instance was recreated. | [Case report](rehearsals/20261030T040558-cfe0d503/cases_report.json). |
| Fleets and work orders | **110 HTTP checks, 6 concurrent requests, 9 assertions**, composite FK/ownership/cascade checks and terminal menu. | [Fleet report](rehearsals/20261030T040558-cfe0d503/fleets_report.json). |
| Account deletion database guards | **29 checks**, including dependencies, session cascade, revoked access and concurrent changes on owned fixture tables. | [Native account report](account_deletion/20261030T040634/native_report.json). |
| Account deletion through actual SQL-backed HTTP | **23 checks**, including self/role/confirmation/dependency denials, deletion and revoked sessions. | [Account API report](account_deletion/api-20261030T040638-dc44efe0/api_report.json). |
| Admin import initiation | **32 checks**, using real localhost auth, the actual CLI/controller and real ETL on five synthetic rows in isolated SQL/MongoDB fixtures. | [Import report](admin_import/20261030T040641-a122f9db/native_report.json). |
| Browser journeys | **238 checks**, plus 3 native admin assertions, 5 native analytics assertions and an independent target-session check. Chrome 156, desktop and 390px mobile coverage; zero uncaught browser exceptions. | [Browser report](account_deletion/browser-20261030T040648-93e1432a/frontend_report.json). |
| Existing performance evidence | **20 raw plans** matched saved metrics; raw samples matched their summaries; **4 current ordered result sets** matched the benchmark fingerprints. | Integrated report's `performance_evidence`; [original performance analysis](PERFORMANCE_EVALUATION.md). |

The browser journeys include vehicle research, complaint filters/text search,
official-record relationships, analytics, accounts/personal saves, analyst cases,
fleet orders, admin monitoring/roles and unused-account deletion. The native case
run adds server-instance recreation and concurrency checks; browser reload alone
would not establish that result. Database services stayed running during injected
failures. Native import verification covers cancellation, competing locks, source
mismatch, role/session revocation, success, repeat imports and actual MongoDB
validation failure with durable stage outcomes.

The performance **timings were not rerun**. They remain measurements from
**29 October**. We checked the integrity of that evidence and fetched the same
representative results read-only on 30 October. That confirms result relevance,
not that current latency is identical to an earlier median.

## Which version did we test?

The report fingerprints **135 implementation, configuration-template, SQL,
verification and test files** before/after the run. Their aggregate SHA-256 was:

```text
7f1d2fb0854109c725ebc5f615c1b69cdb33fd00bc8b54defe37293663ce088d
```

A fingerprint changes if the selected file contents change. This matters because
the working tree has modified/untracked files: the recorded Git HEAD alone does
not identify the current tested application, and GitHub has not been updated by
this rehearsal. Use the file manifest when freezing/exporting the final source.
Documentation updates after the run are outside this implementation fingerprint.

The environment was Windows 11, Python 3.13.7, PostgreSQL 18.6, MongoDB 9.0.4,
psycopg 3.3.6 and pymongo 4.19.0. The four raw archive names/hashes/sizes matched
the inspected source profile before and after testing. Private `.env` values are
excluded from the manifest; only an unchanged/not-unchanged result is recorded.

## Cleanup and evidence preservation

The run verified that implementation files, private configuration, raw archives
and original stored-record counts remained consistent. That includes the existing
users, saves, sessions, reference records and import-history count. Child verifiers
removed their owned synthetic accounts/content/workflow records and owned import
schemas/databases/files. Generated identity sequences may advance during tests.
Count checks are not a complete content checksum of every stored document/row;
the test mutations are scoped to owned fixtures, and the four representative
reference result sets also matched their earlier fingerprints.

Earlier milestone reports were retained. Case/fleet verifiers now accept
`--report-path` and otherwise write new dated `docs/verifications/<kind>/<run>/`
reports. They refuse an existing output file rather than replacing history.
The integrated runner supplies paths inside its own dated rehearsal directory.
The other native/browser verifiers selected for this rehearsal already use
separate dated output directories.

Representative screenshots were visually reviewed:

- [Import history and the local-admin helper instructions](account_deletion/browser-20261030T040648-93e1432a/screenshots/admin-imports.png).
- [Analyst case content/history](account_deletion/browser-20261030T040648-93e1432a/screenshots/case-detail-desktop.png).
- [Fleet work-order form](account_deletion/browser-20261030T040648-93e1432a/screenshots/work-order-desktop.png).
- [Account confirmation on mobile](account_deletion/browser-20261030T040648-93e1432a/screenshots/account-delete-mobile.png).

This was not a complete accessibility/every-browser audit. Import failure checks
used tiny fixtures; they do not establish full-volume throughput or test stopping
the shared Windows database services. No full real-source reimport was performed.

## Run another technical rehearsal

With the existing local setup ready, from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/rehearse_project.py
```

It runs the selected verifiers sequentially so their record-count baselines do
not overlap, starts/stops its own servers/browser and writes a new dated
`docs/rehearsals/<run>/report.json`. Avoid editing code/configuration or changing
application records during the run; consistency checks deliberately fail if the
tested state changes. It also prevents two instances of this coordinator running
at once. Existing Flask/database services are retained. Ordinary startup does not
require a rehearsal or repeat import.

## Still to do in Stage 9

1. Finish a coherent user manual and export the chosen source/data/evidence package.
   Include the exact raw archives/dictionaries; private `.env` and real personal
   workflow/session data should not travel in the package.
2. Have a teammate follow the manual on a clean setup and record that result.
   This rehearsal used an already-configured computer, not a fresh installation.
3. Prepare the final report in the XSite template, slides and video. The five members
   must agree actual speakers/contributions and rehearse at normal speed within
   the supplied brief's 10-minute limit, with names visible.
4. Check the report page/font/template rules, final file formats, ZIP contents and
   marker access against current XSite instructions before submitting.

The [final demo checklist](FINAL_DEMO_CHECKLIST.md) now distinguishes passed
automated technical journeys from these pending human/delivery checks.
