# Backend step 6 — Internal analyst cases and recovery

Implemented and verified on **29 October 2026 (local time)**. This milestone adds
authenticated case CRUD across PostgreSQL and MongoDB, including complaint links,
notes/findings, tags, priority/status, SQL history and retryable partial failures.
These are internal application cases, separate from official NHTSA investigations.

## Try the workflow

Case schema version 3, the limited case-service SQL account and the MongoDB case
validator were already applied on this computer. Restart Flask:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

In another terminal:

```powershell
.\.venv\Scripts\python.exe scripts/try_cases.py
```

Sign in with an **ANALYST or ADMIN application account**. Ordinary registration
creates NORMAL_USER accounts and cannot grant these roles. If the project still
has no administrator, the existing local `scripts/create_admin.py` helper prompts
for a new first-admin email/password. Run it with the project Python interpreter;
it refuses to create another bootstrap administrator once one exists. An admin
can then assign analyst roles through the existing role API. No permanent demo
administrator or default password was left by verification.

The case menu can create/list/read cases, update title/priority/status, link/unlink
complaints, add/edit/remove notes/findings, set tags/components, read history and
delete cases. It can also list pending operations, retry one, and repeat the last
change using its original request ID. Actions persist after sign-out unless you
delete them; the helper is a real client rather than an automatic test.

For a first walkthrough, create a case for `2022 HONDA CIVIC`, list it, then view
its case ID. Add a note and a suspected component such as STEERING. Change status
to REVIEWING, then read the history. Get an ODI number from the complaint explorer
to link a complaint for that same vehicle. JSON responses are available now;
browser forms and the graphical case workspace remain planned.

## Roles and ownership

| Role | Case permissions |
| --- | --- |
| Anonymous | 401: sign-in required. |
| NORMAL_USER | 403: case workspace is restricted. Public research and personal saves remain available. |
| ANALYST | Create cases; list/read/change/delete cases they created, including content and recovery operations. |
| ADMIN | Create cases and inspect/manage/recover cases belonging to any analyst. This is an explicit case-workspace override. |

The server sets `createdBy` and `assignedTo` to the creator when creating a case.
The case vehicle, creator and assignee cannot be changed through these APIs.
Reassignment is not implemented. Foreign/missing cases and operations return the
same 404 within each endpoint. Note/finding IDs, original author and creation time
are server-generated; editing the text keeps the original authorship.

Roles are read from the current SQL-backed sign-in session on each request.
Demotion prevents later analyst operations; an admin can recover a demoted user's
pending work. Private responses use `Cache-Control: no-store`. Case service SQL
permissions do not expose password/session tables or permit changes to ownership
columns. API predicates enforce ownership; database row-level security is not used.
This admin override does not change the stricter personal saved-vehicle policy.

## Endpoints

All paths below start with `/api/analysis-cases`. Writes require the existing
CSRF header/cookie. Every new case/content change also needs an
`Idempotency-Key` header containing a UUID with hyphens. The helper generates it.
Retries of the same command reuse the same key and normalized payload. Reusing a
key for a different actor/action/body returns 409.

| Method/path | Accepted input / behavior |
| --- | --- |
| `GET /api/analysis-cases` | Paginated cases visible to the actor; includes sync state. |
| `POST /api/analysis-cases` | JSON `title`, `modelYearId`; optional `priority` (default MEDIUM). |
| `GET /{caseId}` | SQL `analysisCase`, MongoDB `content` and `sync`. Pending content is null, rather than a stale snapshot. |
| `PATCH /{caseId}` | At least one of `title`, `priority`, `status`. |
| `DELETE /{caseId}` | Delete SQL case/history and queue MongoDB content deletion. Returns an operation receipt. |
| `PATCH /{caseId}/content` | At least one of `tags`, `suspectedComponents`; arrays replace those fields, including clearing with `[]`. |
| `POST /{caseId}/complaints` | JSON `odiNumber` string. Complaint must exist for this case's vehicle; linking twice does not duplicate it. |
| `DELETE /{caseId}/complaints/{odiNumber}` | Remove a link; the imported complaint remains. |
| `POST /{caseId}/notes` | JSON `text`; create a note. Its `noteId` equals this operation's UUID. |
| `PATCH /{caseId}/notes/{noteId}` | JSON `text`; edit the nested note. |
| `DELETE /{caseId}/notes/{noteId}` | Remove a nested note. |
| `POST /{caseId}/findings` | JSON `observation`; create a finding. |
| `PATCH /{caseId}/findings/{findingId}` | JSON `observation`; edit a finding. |
| `DELETE /{caseId}/findings/{findingId}` | Remove a finding. |
| `GET /{caseId}/history` | Paginated SQL-triggered status changes. |
| `GET /operations` | Paginated visible operation receipts; `state=PENDING` by default, optionally APPLIED. |
| `GET /operations/{operationId}` | One visible operation receipt; excludes pending content payload and request fingerprint. |
| `POST /operations/{operationId}/retry` | JSON `{}` plus CSRF. Uses the existing operation ID; no new idempotency key is needed. |

List/history/operation queries support `page` (1–10,000) and `pageSize` (1–100,
default 20). Unknown/duplicate query fields are rejected. Title is 1–200 printable
characters; notes/findings are 1–4,000 text characters and may have paragraphs.
Priorities are LOW/MEDIUM/HIGH; statuses are OPEN/REVIEWING/CLOSED. Closing sets a
SQL timestamp; reopening clears it; repeating CLOSED preserves its timestamp.
Only actual status changes create history rows.

Tags and components allow at most 20 strings of 1–100 printable characters.
Duplicates are removed; suspected components also normalize case/whitespace.
Each case allows 200 linked complaints, 100 notes and 100 findings, with a 512 KB
serialized content limit. Unknown JSON fields, invalid types/IDs/values and
attempts to supply owner/author/vehicle changes are rejected.
The existing 16 KB JSON request-body limit also applies.

## What a successful or pending write means

The response contains `operation`: its UUID, case ID, revision, REPLACE/DELETE
action, state, timestamps and a generic failure category when applicable. The
Location header points to that receipt, not directly to the case. Use its `caseId`
for the case detail URL. Completed creates return 201; other completed changes,
including deletion, return 200 with the receipt.

A **202 PENDING** means the SQL change and recovery task were saved, but MongoDB
completion or its SQL acknowledgement is unresolved. It does not mean both stores
have completed the change. Read/retry the existing operation instead of creating a
second command. Another edit to that case returns 409 until the pending task is
acknowledged. A failed SQL commit can instead return 503 with an uncertain outcome;
repeat the exact command with its original request key. Menu option 12 does this
for the last change in the current helper session.

For deletion, the SQL parent/history can already be gone while its MongoDB delete
is pending. The operation table deliberately has no case foreign key, so the owner
or an admin can still list and retry that task. The case detail returns 404 after
SQL deletion. An already applied operation is safe to retry and cannot replay an
older snapshot over newer case content.

## How recovery works

1. SQL transaction: lock the case/request ID, validate ownership and content, change
   metadata/revision and insert `case_content_operation` with the intended MongoDB
   snapshot or deletion. Commit them together.
2. Lock the operation, then apply its MongoDB replacement/deletion. Replacement is
   keyed by `caseId` and guarded by content revision. One case document is written
   atomically; this does not make the SQL write atomic with it.
3. Acknowledge the operation in SQL. Only then mark it APPLIED and clear its pending
   payload. Completed receipts retain identifiers/fingerprints/timestamps, not a
   duplicate archive of notes/findings.
4. On failure, keep the task for retry. A retry repeats the intended snapshot or
   deletion, so an ambiguous MongoDB response does not append another note. Row
   locks and the unique pending-operation index stop new edits overtaking it.

This pattern is a **transactional outbox**: a durable SQL to-do record bridges two
separate commits. SQL owns case workflow and pending delivery instructions;
MongoDB owns completed flexible case content. This is explicit recovery, not a
distributed transaction or an automatic background worker. Normal SQL/MongoDB
backups and database administration remain necessary if data is manually removed
or corrupted after synchronization. A missing/mismatched document returns 503
instead of silently recreating empty content. A newer projection conflict remains
pending for inspection rather than being overwritten.

The application uses SQL row/request locks and a five-second MongoDB operation
deadline, requires acknowledged MongoDB writes, and returns generic failure
categories without exposing connection details. See the official
[PostgreSQL locking reference](https://www.postgresql.org/docs/18/explicit-locking.html),
[MongoDB single-document atomicity](https://www.mongodb.com/docs/manual/core/write-operations-atomicity/)
and [PyMongo deadlines](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/csot/).

## Setup and verification

Fresh teammates apply the normal construction/import/auth setup, then:

```powershell
.\.venv\Scripts\python.exe scripts/setup_cases.py
```

This applies migration 003, creates/reuses a separate SQL role, updates the case
validator/index, and saves generated credentials in ignored `.env`. It retains
existing records. It has already run here; no reimport is needed.

On **29 October 2026**:

- **121 automated tests passed**, including 29 case tests for ownership, input
  limits, real orchestration with simulated stores, transaction rollback, ambiguous
  commits, pending tasks, retry safety, stale revisions and deletion recovery.
- **99 recorded live HTTP checks passed**, plus concurrent-request and real
  interactive-menu flows using both native databases.
- Native checks covered account-role changes, owner/admin boundaries, complaint
  vehicle validation, MongoDB nested CRUD, close/reopen history and service grants.
- Injected SQL-before-commit, MongoDB-before/after-write and SQL-acknowledgement
  failures recovered. A fresh application/server instance recovered a pending
  create from SQL; a demoted owner was denied while an admin recovered deletion.
- Concurrent same-key creates produced one case. Concurrent notes serialized or
  received 409 and were retried, preserving both edits.
- Synthetic accounts, cases, content, receipts and sessions were removed; checked
  source/existing-user/saved-record counts matched the baseline. Identity sequence
  counters advance normally during such tests and are not reset.

Evidence: [cases_verification_report.json](cases_verification_report.json). JSON
evidence timestamps use UTC, which can be the previous calendar date relative to
our local verification date. Earlier milestone reports were not overwritten.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_cases.py
```

The live verifier uses owned synthetic fixtures and fault wrappers while both
database services remain running; it does not simulate a real power failure or
network outage. The next backend milestone is the small fleet/work-order module.
Browser screens, broader application journeys, analytics, performance benchmarks
and final deliverables remain.
