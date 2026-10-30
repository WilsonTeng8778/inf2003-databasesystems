# Milestone 1 — Database foundation

Completed and verified locally on 25 October 2026.

## Environment and source checks

- Python 3.13.7, PostgreSQL 18.6, MongoDB Community 9.0.4.
- Native Windows database services; no Docker dependency.
- Both database connections checked successfully using local `.env` settings.
- All four source ZIPs and three dictionaries inspected. The ZIP streams were
  read in full; all rows have the documented field widths and decode as UTF-8.
- Raw files, temporary staging, `.venv`, and credentials are excluded from Git.

## Constructed and imported

Both servers contain a dedicated `vehicle_safety` project database. SQL objects
include the normalized catalogue, official records/relationships, user/workflow
tables, fleet/work orders, import logs, constraints, indexes, views and a
case-status trigger. MongoDB has validated `complaints` and `case_details`
collections with the planned indexes.

| Imported entity | Count |
| --- | ---: |
| Canonical make/model/year identities | 53,555 |
| Official recall campaigns | 13,600 |
| Recall-to-vehicle relationships | 93,743 |
| Recall component/source records | 219,728 |
| Official investigations | 3,626 |
| Investigation-to-vehicle relationships | 28,647 |
| Investigation-to-manufacturer relationships | 3,943 |
| Consumer complaint documents | 428,837 |

The complaint documents represent 617,186 in-scope source component rows.
Duplicate components do not multiply complaint or incident counts. The catalogue
includes complaint-only vehicles. Source findings and normalization limitations
are documented in [DATA_INSPECTION.md](../DATA_INSPECTION.md).

## Verification performed

- Five transformation tests passed.
- Schema construction was rerun successfully without dropping/recreating data.
- A complete import rerun inserted **zero** new entities and preserved counts.
- Imported entity counts match the independently inspected source scope.
- Every MongoDB complaint `modelYearId` resolves to the SQL catalogue.
- No conflicting scalar values were found among grouped complaint component rows.
- Saved-vehicle CRUD and duplicate prevention passed.
- Structured case changes, closure constraints and the status-history trigger passed.
- Fleet/vehicle/work-order CRUD and cascade behavior passed. The database rejected
  a work order referencing a recall that does not cover its vehicle model-year.
- MongoDB document/nested CRUD, unique `caseId`, and schema rejection checks passed.
- Synthetic SQL verification records were rolled back and MongoDB test documents
  removed; there are no seeded login accounts at this milestone.

The reproducible machine-readable evidence is in
[verification_report.json](../verification_report.json). Import attempts, including
failures and successful retries, are audited in SQL `data_import_log`.

## Working database-only example

```powershell
.\.venv\Scripts\python.exe scripts/safety_profile.py --make HONDA --model CIVIC --year 2022
```

In the downloaded snapshot this returns **4 recall campaigns, 2 official
investigations, and 885 consumer complaints**. These are snapshot counts, not a
VIN-specific recall determination or a vehicle safety rating.

## Next milestone

Build Flask authentication and services/routes using the verified data model:

1. Registration/login with password hashing, sessions, and server-side role and
   ownership checks. Use a separate database role for the application.
2. Vehicle search/profile and paginated recall, investigation and complaint APIs.
3. Saved vehicles, internal cases and flexible case content, with tested partial-
   failure handling across PostgreSQL and MongoDB.
4. Minimal owner-managed fleet recall/work-order APIs.
5. A small functional GUI connected to those services, followed by analytics and
   repeatable index performance evaluation.

This milestone verifies the database layer. Authentication, API/GUI behavior,
application-level cross-database case recovery, and performance benchmarks have
not yet been implemented or claimed as verified.

