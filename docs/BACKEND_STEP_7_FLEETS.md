# Backend step 7 — Small fleets and recall work orders

Implemented and verified on **29 October 2026 (local time)**. Owners can now
create/read/rename/delete fleets and fleet vehicles, browse model-year recall
matches, and create/read/update/delete recall work orders. This is the limited
fleet workflow from the agreed proposal scope.

## Try it

The workflow SQL permissions were updated locally on 29 October. Start/restart
Flask, keeping its terminal open:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

In another terminal:

```powershell
.\.venv\Scripts\python.exe scripts/try_fleets.py
```

Sign in using your existing application email/password. **NORMAL_USER, ANALYST
and ADMIN can all manage their own fleets.** No extra role or new login account
is needed if you already registered. The client keeps its own cookies and logs
out when you exit; it does not sign a separate browser window in.

Try the following using the IDs shown in each response:

1. Create a fleet, such as `My vehicles`.
2. Add `2022 HONDA CIVIC`, labelled `Car 1`.
3. Browse that fleet's recall matches. The current snapshot has four for one Civic.
4. Create a work order using the fleet-vehicle ID and a recall ID from the match list.
5. Set status to IN_PROGRESS or COMPLETED and read it again.

Your changes persist after logout. Removing a fleet vehicle also removes its
orders. Removing a fleet removes all its vehicles and orders. The menu labels
these actions explicitly. Official vehicle/recall data and personal saved-vehicle
bookmarks remain separate from these fleet records. Lists initially show the
first page; the HTTP APIs expose pagination for further pages.

## Troubleshooting a generic 404

On 29 October, the running server on port 5000 answered health checks but returned
the generic “requested URL was not found” message for `/api/fleets` and
`/api/work-orders`. Its home response also lacked the newer feature links. This
confirmed it was still running code loaded before the fleet routes were added.

Saving Python files does not reload our normally started Flask process. In the
terminal running Flask, press **Ctrl+C**, then run the Flask command above again.
Leave it running and rerun `scripts/try_fleets.py` in a second terminal. Restarting
Flask retains your database data; setup/import commands are not part of this fix.

Before signing in, opening `http://127.0.0.1:5000/api/fleets` in a browser should
return **401 “Sign in to continue”**. That shows the protected route exists.
A generic route-level 404 means the route has not loaded; “Fleet not found” for
one particular fleet ID instead means that record is missing or not yours.

The terminal helper now checks for the fleet/work-order routes before prompting
for credentials and prints restart instructions when they are missing. This
diagnostic was checked against the existing older server and a temporary fresh
server on 29 October. Both checks were anonymous and made no database changes;
the earlier complete CRUD/concurrency report was not rerun for this helper change.

## Three different vehicle concepts

| Concept | Example |
| --- | --- |
| Catalogue identity (`modelYearId`) | The shared make/model/year `2022 HONDA CIVIC`. |
| Personal saved vehicle (`savedVehicleId`) | One user's bookmark of that catalogue identity. |
| Fleet vehicle (`fleetVehicleId`) | One owner-entered vehicle labelled `Car 1`, belonging to a fleet and referencing that catalogue identity. |

You can add `Car 1` and `Car 2` with the same model-year identity. They have
different fleet-vehicle IDs and can have separate recall work orders. Two Civics
therefore produce **eight vehicle–recall matches**, not eight distinct campaigns.
Labels are identifiers chosen by the owner; the system does not verify physical
vehicle uniqueness or store/validate VINs.

A match is a model-level research result. OPEN/IN_PROGRESS/COMPLETED/CANCELLED
are owner-maintained tracking states, not evidence of VIN applicability or repair
completion. Recall detail links open the same official records as public research.

## Ownership and input rules

Every fleet/vehicle/order lookup and change is scoped to the signed-in owner.
The server derives the owner from the session. Even ADMIN has no personal fleet
override; this matches personal saves, while internal analyst cases have their
separate admin-oversight policy. Another owner's ID and a missing ID return the
same 404 for the corresponding endpoint. Private responses have no-store headers.

Fleet names and vehicle labels trim whitespace, preserve case, and allow 1–100
printable characters. Fleet names are unique per owner; vehicle labels are unique
per fleet. These database uniqueness comparisons are case sensitive. Different
owners can reuse names, and different fleets can reuse labels.

A fleet vehicle's fleet/model-year identity and a work order's vehicle/recall
identity cannot be changed. Rename a label or update status/notes instead.
Work orders start OPEN and allow notes of up to 2,000 text characters, including
paragraphs; blank notes clear the field. The existing 16 KB JSON-body limit applies.
Closing an order as COMPLETED sets `completedAt`; repeating COMPLETED keeps that
timestamp, and changing to another status clears it. Owners may correct/reopen
tracking statuses. A cancelled order still occupies its vehicle–recall pair;
update it rather than creating a duplicate.

All writes require the existing session cookie/CSRF token. Unknown JSON/query
fields, invalid types/IDs/statuses and oversized text are rejected with 400.
Duplicate names/labels/orders return 409. An unknown catalogue identity or a
recall that does not match the owned fleet vehicle returns 404. Expected SQL
errors are mapped to generic messages; database failures return sanitized 503s.

## API endpoints

| Method/path | Input / result |
| --- | --- |
| `GET /api/fleets` | Paginated owner's fleets with vehicle/order counts. |
| `POST /api/fleets` | JSON `name`; creates a fleet. |
| `GET /api/fleets/{fleetId}` | One owner's fleet and related counts. |
| `PATCH /api/fleets/{fleetId}` | Exactly JSON `name`. |
| `DELETE /api/fleets/{fleetId}` | Delete fleet and dependent fleet vehicles/orders. |
| `GET /api/fleets/{fleetId}/vehicles` | Paginated owner's vehicles in this fleet. |
| `POST /api/fleets/{fleetId}/vehicles` | JSON `modelYearId`, `label`. |
| `GET /api/fleet-vehicles/{fleetVehicleId}` | Vehicle label, catalogue labels and IDs. |
| `PATCH /api/fleet-vehicles/{fleetVehicleId}` | Exactly JSON `label`. |
| `DELETE /api/fleet-vehicles/{fleetVehicleId}` | Remove vehicle and its orders. |
| `GET /api/fleets/{fleetId}/recall-matches` | Paginated matches with recall detail URLs and existing order IDs/statuses. Optional `fleetVehicleId`, `tracked=true/false`. |
| `GET /api/work-orders` | Paginated owner's orders; optional `fleetId`, `fleetVehicleId`, `status`. |
| `POST /api/work-orders` | JSON `fleetVehicleId`, `recallId`; optional `notes`. The server derives `modelYearId` from the matching vehicle/recall. |
| `GET /api/work-orders/{workOrderId}` | One owner's work order. |
| `PATCH /api/work-orders/{workOrderId}` | At least one of JSON `status`, `notes`. Status must be OPEN/IN_PROGRESS/COMPLETED/CANCELLED. |
| `DELETE /api/work-orders/{workOrderId}` | Remove only the personal work order; its recall match becomes untracked again. |

Creates return 201 with Location for the new resource. Updates return 200; deletes
return an empty 204. All list endpoints support `page` (1–10,000) and `pageSize`
(1–100, default 20). Fleets/vehicles/orders sort by creation time then ID descending;
matches sort by fleet-vehicle ID, campaign number and recall ID. Work-order query
status normalizes case; JSON status updates use the uppercase values above.

The match list checks the fleet and any selected vehicle belong to this owner
and to each other. Work-order list filters are owner-scoped: a foreign/nonexistent
filter produces an empty list, not another owner's data. Page counts and rows are
separate reads and can change during a concurrent write.

## How the relational design supports this

This feature uses PostgreSQL because its fleets, vehicles and recall work orders
form structured relationships. It reuses the tables and `fleet_recall_matches`
view built in the foundation milestone. No new schema migration or import was
needed; the SQL schema remains version 3 from case recovery.

The work order's composite foreign keys require its model-year ID to match both
its fleet vehicle and its recall's affected-vehicle relationship. A unique
`(fleet_vehicle_id,recall_id)` constraint prevents duplicate orders, including
concurrent requests. Cascade rules delete dependent personal records together.
See the [PostgreSQL constraint reference](https://www.postgresql.org/docs/18/ddl-constraints.html).

Each mutation uses a SQL transaction and locks its owning fleet first. Concurrent
partial updates read the current order after the lock; a notes-only edit therefore
does not overwrite a concurrent status update. Vehicle creation/deletion and fleet
deletion use the same parent-lock order. The database constraints also protect
relationships if a write bypasses the API. See the
[locking reference](https://www.postgresql.org/docs/18/explicit-locking.html).

The existing workflow SQL role now has SELECT on fleet tables and the recall-match
view, specific insert/update columns, deletes and sequence usage. It cannot read
account/session/case tables or access the official source tables directly, and
cannot update owner/vehicle/recall identity columns. Owner checks are supplied by
the API's SQL predicates; PostgreSQL row-level security is not configured.

On an older/fresh checkout, after normal database setup, apply the grants once:

```powershell
.\.venv\Scripts\python.exe scripts/setup_workflow.py
```

This update already ran here. It preserves the existing workflow password and
stored records. There is no need to rerun imports or enter another password.

## Verification and remaining work

On **29 October 2026**:

- **145 automated tests passed**, including 24 fleet tests and all 121 earlier tests.
- **110 recorded live HTTP checks, six concurrent requests and the actual terminal
  workflow passed** against the native databases.
- Ownership denials covered another normal user and ADMIN. Counts/pages, duplicate
  prevention, unknown/mismatched records, CSRF, immutable fields and limits passed.
- Direct SQL rejected an invalid vehicle/recall INSERT through the composite FK.
- Concurrent order edits retained both changed fields; concurrent duplicate creates
  yielded one 201 and one 409; a fleet-delete/vehicle-create race left no orphan.
- Completion timestamps, tracked/untracked matches and native cascades were checked.
- Owned synthetic accounts/fleets/vehicles/orders/sessions were removed, and checked
  existing/reference record counts matched the baseline. Identity sequences advance
  normally and were not reset. Earlier milestone evidence was preserved.

Evidence: [fleets_verification_report.json](fleets_verification_report.json).
JSON evidence timestamps use UTC; the local date can be one day ahead.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_fleets.py
```

The planned core workflow APIs are now verified through research, authentication,
personal saves, analyst cases and small fleets. Next is the first browser interface;
admin dataset/import-log reads and analytics integration remain planned alongside
their screens. Wider user journeys, performance comparisons, final documentation
and submission materials still remain. This is not a general workshop/maintenance
system: bookings, parts, invoices and repair billing are outside the agreed scope.
