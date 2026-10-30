# Restricted account deletion

**Implemented:** 30 October 2026. **Verified:** 183 automated tests, 29 native
database assertions and 23 live-database HTTP checks passed on 30 October.
**Browser verification:** 238 cumulative real-browser checks passed on 30 October;
desktop/mobile screenshots reviewed and owned fixtures removed.

This addresses the missing account-delete operation identified as G1 in the
[requirements review](FINAL_READINESS_REVIEW.md). The API/database operation is
implemented and checked, and the approved browser follow-up now completes G1's
planned acceptance evidence. Admin import initiation (G2) remains unfinished.

## What an admin can delete

Only an **unused account belonging to someone else** can be deleted through this
flow. The administrator must confirm its current email. The server rejects:

- Signed-out, normal-user and analyst requests.
- Deletion of the administrator's own signed-in account.
- Removal of the last administrator.
- A mismatched confirmation email or unexpected request fields.
- Accounts with saved vehicles, fleets, created/assigned cases, or case operation
  history as owner/requester. Both pending tasks and completed receipts count.

Sessions do not make an account ineligible: successful deletion removes its active
session rows, so existing cookies stop authenticating. An unused account may have
any of the three application roles. This is account deletion rather than
deactivation; it cannot be undone through the app. There is no force-delete option.

The conservative policy matters because SQL currently cascades some owned records
when a user is deleted. The new operation deliberately checks for those records
and refuses deletion. It does not erase an owner's saved vehicles/fleets or remove
case authorship/history to make an account eligible. No existing real account was
a deletion target in verification.

## Try the implemented interface

The additive setup was applied locally on 30 October. Restart the older Flask
process to load the new route/templates/JavaScript; stored data is retained:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

Sign in as ADMIN and open **Admin → User roles**. Other users' cards now offer
**Delete unused account**. The dialog explains the policy and requires the target
email. Cancel leaves the account unchanged; the server rechecks eligibility after
confirmation. Your own account has no delete action.

Use a deliberately created, unused test account when trying this. Do not choose
an existing teammate or real account simply to demonstrate deletion. An account
with saved work receives a conflict message and remains stored. These browser
behaviours were checked in the 30 October run linked below.

If a response is lost or unreadable after submission, the controls require
**Refresh and review accounts**. They do not automatically repeat DELETE. Refresh
reads current account records and access before enabling another change. Session
expiry clears the private list and confirmation. The browser run checked both
lost and unreadable successful deletion responses, with one DELETE and a fresh
account read rather than an automatic repeat.

## API and database boundary

`DELETE /api/admin/users/{userId}` requires ADMIN authentication, the existing
CSRF protection and JSON with exactly:

```json
{"confirmEmail": "unused@example.invalid"}
```

The actor ID comes from the current SQL-backed session, never a request field.
Success returns HTTP 200 with `{"deletedUserId":123}` for the actual deleted ID.
Missing accounts return 404; invalid input returns 400; policy/confirmation
conflicts return 409. Authentication/authorization failures return 401/403. Private
responses keep `Cache-Control: no-store`. Neither response nor error includes
password hashes, session tokens or raw SQL diagnostics.

[Migration 004](../sql/migrations/004_account_deletion.sql) adds
`public.delete_unused_account(actor_id,target_id,confirmation_email)` and advances
construction metadata to **SQL schema version 4**. It does not rebuild tables or
reimport source records. The function runs with its trusted creator's database
permissions (`SECURITY DEFINER`), uses a fixed safe search path and fully qualified
table names. PUBLIC execution is revoked; the authentication SQL role receives
EXECUTE on this operation and retains **no direct DELETE on `app_user`**. It does
not gain direct reads of saves, fleets, cases or operation content.

Think of EXECUTE as permission to use one controlled operation: it checks the
policy before performing a deletion. It is narrower than granting general access
to delete account rows. The Flask session identifies the human actor; the database
function then verifies that actor's current role. Possession of server-side SQL
credentials remains a trusted application boundary, not independent end-user identity.

The operation shares advisory lock `(2003,19)` with role changes, rechecks/locks
the actor, locks the target and checks dependencies before deleting. The target
lock coordinates with concurrent foreign-key inserts. Native tests exercised a
new save committing while deletion waits and a demotion committing before the
actor recheck. All work stays inside one PostgreSQL transaction; MongoDB is not
modified. If new account-owned SQL entities are added later, review this explicit
dependency policy alongside their foreign keys.

For an existing teammate installation:

```powershell
.\.venv\Scripts\python.exe scripts/setup_account_deletion.py
```

This applies the function and narrow grant without changing credentials or
existing records. Fresh `setup_databases.py` includes migration 004, and
`setup_auth.py` grants the capability to its separate role. Migration 003/case
tables must already exist; no full import is required for this update.

## Verification and limits

| Evidence | What was checked on 30 October |
| --- | --- |
| [Earlier verification summary](account_deletion/20261030T010122/verification_summary.json) | The successful 183-test CLI result, JS syntax checks and source hashes. Its initial pending browser status is preserved as history; the follow-up below supersedes that status. |
| [29 native assertions](account_deletion/20261030T010122/native_report.json) | Production function permissions/configuration; guard logic through the real auth SQL role against owned fixture tables; sessions; dependency cases; role/FK/concurrent-delete races; cleanup and unchanged original counts. |
| [23 HTTP checks](account_deletion/api-20261030T010707-3f7c8a09/api_report.json) | Actual Flask routes and actual PostgreSQL auth/function calls: registration, role denials, CSRF, confirmation, self/dependency conflicts, successful normal/analyst deletion, session/login revocation, repeated-request 404 and cleanup. |
| [238 browser checks](account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json) / [follow-up summary](account_deletion/browser-20261030T023324-1a1c57a4/followup_summary.json) | Earlier application journeys plus confirmation/cancel, self/role/CSRF/dependency denials, deletion, uncertain-response review, expiry and mobile layout. Independent signed-in target sessions were revoked; original counts/import history retained. |

The native guard/concurrency tests use the same migration function with its table
references rebound to a unique owned schema containing minimal dependency/FK
fixtures. They never attempt to delete the existing last administrator to test a
guard. The API run uses disposable accounts in the actual project schema, including
an owned saved vehicle, and removes its fixtures afterward. Both reports confirm
original record counts after cleanup. Sequence counters can advance during tests.

```powershell
.\.venv\Scripts\python.exe scripts/verify_account_deletion.py
.\.venv\Scripts\python.exe scripts/verify_account_api.py
.\.venv\Scripts\python.exe scripts/verify_frontend.py --accounts
```

Each account verifier writes separate dated evidence. The browser option includes
earlier research/case/fleet/admin/analytics journeys and account checks:
email confirmation/cancel, protected account rejection, successful deletion,
lost/unreadable responses, session expiry, mobile layout and independently signed-in
target-session revocation. It uses only owned synthetic targets and its own temporary
server/browser; your port-5000 server is not stopped. Screenshots/reports go into a
new `docs/account_deletion/browser-<run>/` directory, preserving milestones 1–6.

The initial approval-service capacity issue was resolved after the user approved
retrying. An early run exposed a verifier readiness race: it inspected the old list
before identity/list refresh finished. The verifier now waits for enabled controls.
It also explicitly resets the inherited mobile viewport before desktop captures.
No application code changed in this browser follow-up. The [failed-run note](account_deletion/browser-20261030T022808-035fc56b/failure_note.json)
and [intermediate capture note](account_deletion/browser-20261030T023110-62a4a84c/capture_note.json)
are retained alongside the final successful run. Earlier milestone reports remain
unchanged, including the [29 October, 219-check run](frontend_step_6_verification_report.json).
The earlier 183-test/native/API checks were not rerun for verifier-only changes.

The final run used Chrome 156 at 1440px desktop and 390px mobile sizes, recorded
zero uncaught browser exceptions, and passed the independent target-session check.
The new desktop dialog capture is 440px wide and the mobile dialog 358px wide.
Reviewed screenshots: [desktop confirmation](account_deletion/browser-20261030T023324-1a1c57a4/screenshots/account-delete-dialog.png),
[mobile confirmation](account_deletion/browser-20261030T023324-1a1c57a4/screenshots/account-delete-mobile.png),
[uncertain deletion](account_deletion/browser-20261030T023324-1a1c57a4/screenshots/account-delete-uncertain.png)
and [refreshed account list](account_deletion/browser-20261030T023324-1a1c57a4/screenshots/account-delete-result.png).
These checks do not establish every-browser compatibility or a full accessibility audit.

Next: complete G2's admin import-entry workflow, then the broader final
rehearsal/manual/report/package work. G1 is closed against implementation and
dated verification evidence; the overall project remains in Stage 8.
