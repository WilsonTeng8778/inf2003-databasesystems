# Backend step 3 — Personal saved vehicles

Implemented and verified on 28 October 2026. This is the first complete
authenticated application CRUD workflow exposed through our API.

## What can a user do?

Sign in, save a vehicle identity from the catalogue, list saved vehicles, give one
a nickname, read it again, and remove it. All three human roles use the same
personal ownership rule. Even an ADMIN cannot use these endpoints to read or
change another user's personal records.

The application derives the owner from the validated sign-in session. It never
accepts a client-selected owner ID. Another user's saved-record ID returns the
same 404 as a nonexistent record. The SQL lookup/update/delete predicates all
include `user_id`, and private responses have `Cache-Control: no-store`.

## Try it using your account

Workflow SQL access is already configured on the current computer. Restart Flask
if it was running before these changes:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend:create_app run --host 127.0.0.1 --port 5000
```

In a second terminal at the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/try_saved_vehicles.py
```

Use the **application email/password** created during registration. The password
prompt is hidden. The menu offers:

```text
1 List my saved vehicles
2 Save a vehicle
3 Rename a saved vehicle
4 Remove a saved vehicle
0 Sign out and exit
```

For a first example, choose 2 and enter `2022`, `HONDA`, `CIVIC`, and a nickname.
Choose 1 to see its saved-vehicle ID. Use that ID with 3 or 4. The helper finds the
catalogue identifier through the search API, so you do not have to guess it.

Choosing 0 logs out but **retains saved records**. You can inspect them in
PostgreSQL's `saved_vehicle` table or list them after your next sign-in. Choosing
4 deletes only the selected personal saved record; the underlying official
vehicle/recall/complaint data remains. The terminal client uses its own cookies;
a separate browser window is not automatically signed in.

If you have not registered yet, use `scripts/try_auth.py --register` first. The
browser GUI is still planned; this menu is a client for exercising the real APIs.

## Endpoints

All endpoints require a valid signed-in session. POST/PATCH/DELETE also require
the current CSRF token and cookie as described in the auth walkthrough.

| Endpoint | Input | Result |
| --- | --- | --- |
| `GET /api/saved-vehicles` | Optional `page` and `pageSize`; default 20, maximum 100. | 200, owner's paginated `items` and pagination metadata. |
| `POST /api/saved-vehicles` | JSON `modelYearId`; optional `nickname`. | 201, `savedVehicle` and Location header for its detail URL. |
| `GET /api/saved-vehicles/{savedVehicleId}` | Saved-record ID. | 200 with the owner's record, otherwise 404. |
| `PATCH /api/saved-vehicles/{savedVehicleId}` | Exactly JSON `nickname`. | 200 with renamed owner record, otherwise 404. |
| `DELETE /api/saved-vehicles/{savedVehicleId}` | Saved-record ID. | 204 with no response body, otherwise 404. |

The public vehicle search/profile returns `modelYearId`, which identifies a
make/model/year combination. A saved record has a different `savedVehicleId`,
which identifies one user's bookmark of that vehicle. Use the saved-record ID
for detail/rename/delete.

Nickname defaults to an empty string, preserves case, trims surrounding
whitespace, and allows at most 100 printable characters. A blank nickname clears
it. Vehicle identifiers must be positive JSON integers. PATCH cannot change the
owner or vehicle identity. Unknown POST/PATCH JSON fields and unsupported query
parameters are rejected with 400.

Saving the same vehicle twice for the same user returns 409. Different users can
save the same vehicle independently. Unknown catalogue vehicles return 404.
The owner ID is intentionally not part of the accepted input or public DTO.

## How this demonstrates SQL CRUD

| Action | Database operation |
| --- | --- |
| Save | INSERT a row linked to the user and catalogue identity. |
| List/read | SELECT the owner's rows and JOIN the catalogue for make/model/year labels. |
| Rename | UPDATE nickname with both owner and saved-record ID in the condition. |
| Remove | DELETE with both owner and saved-record ID in the condition. |

Foreign keys keep the referenced user and vehicle valid. The existing unique
constraint on `(user_id, model_year_id)` prevents duplicates, including concurrent
attempts. SQL values remain parameterized. A write commits before a successful
response is returned; expected duplicate writes are rolled back and mapped to 409.

This feature uses PostgreSQL only because it is a structured relationship between
users and vehicles. MongoDB's complaint data is not changed by personal saves.
The later analyst-case workflow supplies application-owned MongoDB CRUD.

## Limited workflow SQL access

On a fresh setup, after the earlier database/reader/auth setup:

```powershell
.\.venv\Scripts\python.exe scripts/setup_workflow.py
```

This generates `WORKFLOW_POSTGRES_*` credentials into ignored `.env`. It grants
catalogue/saved-record reads, saved-record inserts/deletes and nickname updates.
It cannot read account credentials, modify official reference tables or update
the owner/model-year columns. No data import or table reconstruction is needed.

The application enforces per-user ownership through its SQL predicates; PostgreSQL
row-level security is not configured. Administrative pgAdmin access has broader
database permissions than an ordinary application request.

## Verification

- **53 automated tests passed:** 19 new saved-vehicle tests and the previous 34.
- **37 recorded live HTTP checks passed**, plus an actual interactive menu flow.
- Two generated accounts demonstrated owner CRUD, owner-filtered lists, per-user
  duplicate prevention and cross-user denials. Promoting the second fixture to
  ADMIN did not bypass personal ownership.
- The native SQL role's restricted privileges were checked. A committed rename
  was read back directly from SQL with the original owner unchanged.
- Invalid IDs/payloads/nicknames, CSRF checks, pagination, missing records and
  204 delete responses were checked.
- Owned synthetic users/saves/sessions were removed afterward. Checked record
  counts matched the baseline, including the existing user's account and NHTSA data.

Evidence: [saved_vehicles_verification_report.json](../saved_vehicles_verification_report.json).
Earlier full database and auth milestone evidence is preserved separately.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/verify_saved_vehicles.py
```

The live verifier starts/stops a temporary local server and only cleans up its
own synthetic accounts. It does not clear your saved records or run imports.

Next: complete complaint browsing/filtering, then analyst-case workflows and the
small fleet/work-order module. The browser GUI and performance evaluation remain.
