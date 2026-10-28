# Implementation and evidence — 28 October 2026

This document describes the new local implementation. The earlier dated milestone
reports remain historical records of the team's prior environment.

## Feature and assessment map

| Feature | Database contribution | Current evidence |
| --- | --- | --- |
| Evidence profile | PostgreSQL recall/investigation views and MongoDB complaint counts/aggregations, joined by model-year identity | API and browser checked with isolated synthetic records |
| Complaint explorer | MongoDB component, text and date filters; paginated documents | Live integration test against an isolated MongoDB instance |
| Analyst case | SQL case, status history trigger and durable synchronization outbox; MongoDB complaint links, tags, notes and findings | Live integration test covers role/owner checks, document changes and simulated MongoDB failure/retry; synthetic case linked to a real complaint; browser case and note flow checked |
| Small fleet recall workflow | SQL fleet/vehicle/work-order CRUD, owner checks and recall applicability foreign key | Live integration test checks ownership and invalid recall matching; a synthetic fleet created an order for a real recall; browser fleet/match/order flow checked |
| Analytics | MongoDB component and monthly receipt aggregations displayed as charts | Synthetic data checked; component totals can overlap and dates are receipt dates |
| Administration | Existing role management, source availability/import history, explicit import start and outbox retry | Role and sync paths checked in the isolated test; starting a real refresh from the UI was not exercised |
| Index evaluation | Same SQL query and same MongoDB query each measured before/after indexes on separate scratch copies | A 28 October real-data sample was measured; raw plans and results are in [benchmark_2026-10-28.json](benchmark_2026-10-28.json) |

The application does not calculate a safety score or predict a defect. A
complaint is an allegation. A model-year recall match is not a VIN-specific
recall determination. Internal analyst cases are not official NHTSA investigations.

## API and access

- Public research: `/api/vehicles/search`, `/api/vehicles/safety-profile`,
  `/api/vehicles/{modelYearId}/recalls`, `/investigations`, `/complaints`,
  `/insights`, `/api/datasets` and `/api/health`.
- Signed-in users: `/api/saved-vehicles` and `/api/fleets` with vehicle, match
  and work-order subroutes. Fleet and saved records are owner scoped.
- Analysts and administrators: `/api/cases`, case metadata and history,
  complaint links, classification, notes, findings and case sync. Analysts see
  cases they created or are assigned; administrators can inspect all cases.
- Administrators: existing `/api/admin/users` and role changes, plus
  `/api/admin/imports`, `/api/admin/imports/run` and `/api/admin/case-sync`.

Writes require the existing session-bound CSRF token. SQL inputs are parameterized;
the browser inserts source narratives as text rather than HTML. SQL ownership is
enforced by application queries, not PostgreSQL row-level security. MongoDB
authentication and network restrictions depend on the deployment configuration.

## Cross-database recovery

Migration 003 adds `case_sync_outbox`. A SQL transaction records the case and its
pending document operation together. After commit, the application attempts an
idempotent MongoDB insert/delete. If MongoDB is unavailable, the pending job is
retained and a 202 response reports the incomplete synchronization. Jobs for one
case are processed in order; an administrator or `scripts/reconcile_cases.py` can
retry. If MongoDB succeeds but the SQL job update fails, repeating the operation
is safe. This does not claim atomic transactions across the two databases.

## Checks and limits

- The previous 53 automated unit/transformation tests passed on 28 October 2026.
- `tests/test_workflows_live.py` passed against isolated local PostgreSQL 18 and
  MongoDB 6.0 servers using uniquely identified synthetic records. It covers
  research, complaint filters, case synchronization and nested CRUD, cross-user
  denial, fleet matches and work orders. Its outage is simulated; the other
  operations use real database servers.
- A browser walkthrough used labelled synthetic data: vehicle search and profile,
  complaint-to-case linking, a case note, fleet creation, recall match and work
  order creation. Browser console errors were absent during that walkthrough.
- The four official archives downloaded on 28 October differ in checksum from the
  earlier recorded snapshot. Their extracted row widths passed inspection; the
  dated [source profile](data_profile_2026-10-28.json) preserves the new counts.
- A separate isolated real-data import contained **53,560 vehicle identities,
  13,607 recall campaigns, 3,629 investigations and 429,582 complaint documents**.
  Read-only API counts matched independent database queries for the example
  2022 Honda Civic, and import hashes matched the downloaded archives. See
  [real_data_verification_2026-10-28.json](real_data_verification_2026-10-28.json).
- A synthetic analyst account created a case linked to an actual complaint and a
  synthetic fleet created a work order for an actual matching recall in the
  isolated real-data test database. Only the generated workflow records were
  removed afterward; baseline workflow counts were restored. See
  [real_workflow_verification_2026-10-28.json](real_workflow_verification_2026-10-28.json).
- One local before/after index experiment copied 93,797 recall-vehicle rows and
  100,000 complaint documents into separate scratch databases. With one warm-up
  and five timed runs per phase, the SQL query's median changed from 3.249 ms to
  0.090 ms; the MongoDB query's median changed from 64.869 ms to 1.697 ms. Result
  counts were unchanged. MongoDB's plan examined 100,000 documents before the
  index and 0 documents/500 index keys afterward for this covered query. The SQL
  plan changed to an index scan. These are single-machine, ordered-sample results,
  with short timings and a small number of repetitions. The two DBMS workloads
  differ, so these numbers do not compare their overall speed.
- The final report, slides, all members' presentation video, clean-machine team
  review and actual XSite submission require team work. No submission is implied.

Setup, usage, recovery and benchmark commands are in [USER_MANUAL.md](USER_MANUAL.md).
