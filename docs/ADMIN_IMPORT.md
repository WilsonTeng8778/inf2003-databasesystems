# Admin-authenticated local imports

**Implemented and verified:** 30 October 2026. **G2:** closed.
**Results:** 196 automated tests and 32 native auth/CLI/ETL checks passed.

An application ADMIN can now perform an intentional import through
`scripts/admin_import.py` on the database computer. It signs in through the
existing Flask authentication service, reviews the approved local source files,
requires confirmation, rechecks access and runs the shared importer. This fulfils
the greenlight's admin import-initiation item using a role-checked local helper.
The Import history page documents the command and displays recorded outcomes.

**Your project data is already loaded. You do not need to run an import now.**
Verification imported only small synthetic files into isolated SQL/MongoDB
fixtures. It did not reimport the real NHTSA snapshot or change existing audit rows.

## Use the supported workflow

Keep both native databases and Flask running. At the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/admin_import.py
```

1. Enter the application email and hidden password you use to sign in to RecallScope.
   Database passwords stay in ignored `.env`; they are not the application login.
2. The helper checks that the current application role is ADMIN. Normal users,
   analysts and expired/signed-out sessions cannot start an import.
3. Review the four archive names, sizes and SHA-256 fingerprints. The files must
   match the inspected snapshot recorded in `docs/data_profile.json`.
4. Type **IMPORT** to start. Any other answer cancels before opening the import
   connection or starting any dataset stage.
5. Read the console outcome and open **Admin → Import history** in the browser.
   Refresh the page to see the new per-dataset attempts. The helper signs out its
   own application session when it finishes or refuses the request.

The command defaults to `http://127.0.0.1:5000`. For another local Flask port,
`--base-url http://127.0.0.1:PORT` is supported. The existing `LocalApi` client only
accepts localhost origins; there are no password, arbitrary ZIP path, download,
dataset-selection or unattended-confirmation flags. `--help` describes the command.

The existing auth server is sufficient for the helper; there is no new HTTP import
endpoint. Restart an older Flask process to display the new instructions panel in
Import history. Opening that page does not start an import. This workflow requires
a local operator with the existing setup credentials as well as an ADMIN application
login; it is not a remote browser job or an upload feature.

## What happens before and during the import

| Step | What it protects |
| --- | --- |
| Fresh `/api/auth/me` check | Requires a valid ADMIN session before source preparation/confirmation. |
| Fixed file/profile validation | Requires all four approved filenames and matching inspected SHA-256 hashes. A changed/missing archive stops the command. |
| Explicit IMPORT confirmation | Lets the operator cancel before starting stages. |
| Shared PostgreSQL session advisory lock | Refuses overlap with either this helper or trusted `scripts/import_all.py`; it survives stage commits. |
| Fresh session/role/identity check after taking the lock | Refuses access revoked during confirmation/waiting, and refuses a switch to a different account. |
| Second source check | Refuses a snapshot changed since the operator reviewed it. |
| Shared pipeline and existing audit records | Runs the same transformations/upserts and records stage outcomes/counters. |
| Lock release and helper sign-out | Restores a failed SQL transaction before unlocking; revokes the helper's session on ordinary completion/refusal/failure. |

A session lock belongs to the open PostgreSQL connection rather than one
transaction. Our stages commit separately, so a transaction-only lock would not
cover the whole import. Both entry points now use `etl.runner.import_lock` with
the same existing lock key. `etl.runner.run_imports` runs:

```text
Vehicle catalogue → Recalls → Official investigations → Complaints
```

There are four stages although complaints use two ZIPs: the catalogue combines
identities from every source, and the complaint stage merges both receipt windows
into documents. Statistics refresh targets the imported tables on that connection;
it no longer runs a database-wide ANALYZE against unrelated workflow tables.

The helper checks authorization at the start boundary; it does not cancel an
already-started import if a role changes or someone signs out afterward. Keep the
source ZIPs unchanged while importing. A newly downloaded/modified snapshot needs
review and inspection before it is approved for this helper. A hash mismatch is
not an invitation to silently replace the expected hash.

## What changes, and what a failed run means

An import **upserts** reference entities: insert a new identifier or refresh an
existing one. It does not reset databases or clear accounts, saved vehicles, cases,
fleets or work orders. Repeating the same approved snapshot should preserve entity
counts; the fixture rerun verified zero new inserts. An "updated/refreshed" counter
is not the count of newly added entities or proof that every value changed.

Actual stages create `data_import_log` rows with source fingerprints, counters,
timestamps and COMPLETED/FAILED outcomes. Refused access, cancellation, a busy lock
or preflight mismatch occurs before any stage; these do not add fake import-attempt
rows. The console explains the refusal. The current audit schema records stage
outcomes, not a new persistent requester/job record.

There is no single all-or-nothing transaction spanning the whole pipeline and both
DBMSs. If complaints fail after the earlier SQL stages complete, those earlier
stages remain committed. Completed MongoDB batches may also remain after a later
batch fails. Review history/counts before retrying; the normal retry uses the same
stable-key upserts. Failure counters do not prove that zero external writes occurred.

Ordinary stage exceptions are logged as FAILED, with an allowed exception category
instead of arbitrary diagnostics. A forced process termination, service loss or
Ctrl+C can leave an unfinished RUNNING audit entry; that entry is not proof a
process is still running. Closing its SQL connection releases the session lock.
The helper reports interruptions without claiming a full rollback. Durable
resumable job scheduling/cancellation is outside this local-helper milestone.

The application SQL roles remain restricted; no new grants, schema migration or
runtime packages were needed. The local helper uses trusted setup credentials to
run ETL. Someone who already possesses database-administrator credentials remains
a trusted operator and can use the bootstrap tools directly. This is not a claim
to sandbox the owner of `.env` or to make PostgreSQL roles equal application roles.
Fresh installation still uses `scripts/import_all.py` before application accounts
are available; intentional subsequent admin operation uses the new helper.

## Dated verification

| Evidence | Verified on 30 October |
| --- | --- |
| [Automated summary](admin_import/20261030T031357-c6d157f6/automated_tests.json) / [full log](admin_import/20261030T031357-c6d157f6/automated_tests.txt) | 196 tests passed, including 13 new controller/CLI/source-integrity/shared-pipeline tests. |
| [Native report](admin_import/20261030T031357-c6d157f6/native_report.json) | 32 checks using real localhost auth, the actual command/controller, real ETL, an owned SQL schema/MongoDB database and five synthetic raw rows. |

The native run used the command's actual `main`, with test-provided input/hidden
password values and fixture-only database/source routing. It verified normal-user/
analyst denial, cancellation, a competing lock, role revocation/sign-out during
confirmation, snapshot mismatch, success, repeat imports, session cleanup and a
real MongoDB validator rejection. First success produced **one vehicle identity,
one recall, one investigation and two merged complaint documents**. The repeat
produced no new entities. The forced complaint failure logged FAILED while the
preceding three SQL stages remained COMPLETED.

All owned accounts, SQL tables, MongoDB collections/database and raw fixtures were
removed. Original project counts and import-history row count matched their
baselines. The real four source archives were checked read-only against their
inspected hashes; no full production-source import was run. The native report
contains safe fixture console examples and per-stage counters.

The static Import history instructions were checked through Flask's rendered page.
There is no new interactive browser import control, so the cumulative browser suite
was not rerun for this CLI/instructions change. Its separate [238-check account
milestone](account_deletion/browser-20261030T023324-1a1c57a4/frontend_report.json)
retains its earlier 30 October verification time; it is not new evidence for this helper.
These tests also do not establish full-volume import throughput or a teammate's
fresh installation, and they do not replace the final whole-project rehearsal.

To reproduce the fixture verification, without importing real source data:

```powershell
.\.venv\Scripts\python.exe scripts/verify_admin_import.py
```

It starts/stops its own temporary localhost server and writes a separate dated
`docs/admin_import/<run>/` report. Your existing Flask server remains available.
The next work is the final integrated rehearsal, manual/fresh-machine reproduction
and report/slides/video/source-data package. G1 and G2 have implementation and
dated acceptance evidence; overall Stage 8 remains in progress.
