# Inspecting PostgreSQL and MongoDB

Connection names and counts checked on 28 October 2026 using read-only queries.
This was a browsing/readiness check, not a rerun of the full database test suite.

Both project databases already exist and contain imported data. You can inspect
them directly now. Their Windows database services must be running; Flask does
not need to be running for pgAdmin or Compass.

## PostgreSQL: open pgAdmin 4

If your local PostgreSQL server is already listed under **Servers**, connect to
it. Otherwise, right-click **Servers → Register → Server**. Give it a descriptive
name such as `INF2003 Local`, then use these connection settings:

| Setting | Value for this computer |
| --- | --- |
| Host name/address | `127.0.0.1` |
| Port | `5432` |
| Maintenance database | `postgres` |
| Username | `postgres` |
| Password | Your PostgreSQL installation password, stored locally as `POSTGRES_PASSWORD` in `.env`. |

The connection name is just a label in pgAdmin. The maintenance database is the
initial connection database; our actual project data is in `vehicle_safety`.
If pgAdmin prompts for a master password, that protects its saved connections and
is separate from the PostgreSQL server's password.

Expand the browser tree:

```text
Servers
  -> your local PostgreSQL server
     -> Databases
        -> vehicle_safety
           -> Schemas
              -> public
                 -> Tables
                 -> Views
```

Right-click a table or view and choose **View/Edit Data → First 100 Rows** to see
a small result grid. Start with `vehicle_make` or `recall` under Tables. For a
human-readable combination of make/model/year, open `vehicle_catalogue` under
Views. Raw tables deliberately separate related information.

Useful objects to explore:

| Object | What you will see |
| --- | --- |
| `vehicle_make`, `vehicle_model`, `model_year` | The normalized vehicle catalogue split into related tables. |
| `recall`, `recall_vehicle`, `recall_record` | Campaigns, affected vehicles, and source component records. |
| `official_investigation`, `investigation_vehicle` | Official investigation records and their affected vehicles. |
| `app_user` | Accounts registered through our application; passwords are stored as hashes. |
| `app_session` | Active/stored sign-in sessions; logout removes the corresponding session. |
| `data_import_log` | Audited import attempts, counts and outcomes. |
| `saved_vehicle`, `analysis_case`, `fleet`, `work_order` | Application workflow storage; it can be empty before those records are created. |
| View: `vehicle_catalogue` | Make/model/year labels together, with the shared vehicle identifier. |
| View: `vehicle_safety_summary` | Catalogue labels plus SQL recall/investigation counts. |

### Run a first SELECT query

Select **vehicle_safety** before opening **Tools → Query Tool**, so the query runs
in the project database. Paste and execute:

```sql
SELECT *
FROM public.vehicle_safety_summary
WHERE make = 'HONDA'
  AND model = 'CIVIC'
  AND year = 2022;
```

This returns the vehicle identity and its SQL recall/investigation counts.
Complaint counts come from MongoDB, so they are not a column in this SQL view.

To view public account fields without selecting credential hashes:

```sql
SELECT user_id, email, role, created_at
FROM public.app_user
ORDER BY user_id;
```

These SELECT statements only read records. The GUI also has editing tools;
browsing results does not require changing or saving any values.

## MongoDB: open MongoDB Compass

Choose **Add New Connection**, enter this local connection string, then choose
**Connect** or **Save & Connect**:

```text
mongodb://127.0.0.1:27017/
```

Our current local MongoDB connection does not require an application login.
Choose **vehicle_safety → complaints → Documents**. Each record is a document
with expandable fields, including `vehicle`, `incident`, `components`, `narrative`
and `source`. Arrays such as `components` can contain several entries.

Enter this in the **Filter** field and click **Find**:

```json
{
  "vehicle.make": "HONDA",
  "vehicle.model": "CIVIC",
  "vehicle.year": 2022
}
```

The current snapshot contains 885 matching complaint documents. The dotted names
refer to fields inside the nested `vehicle` object; `year` is a number.

The database also has a **case_details** collection for internal analyst content.
It is currently empty. We created its structure and tested temporary documents,
then removed those test documents. The editable case workflow is still to build.

Compass also exposes collection indexes and validation settings for inspecting
the definitions in `mongodb/schema.py`. Finding/filtering documents reads data;
you do not need to import or recreate the database to browse it.

## What was present when checked?

| Database object | Count on 28 October |
| --- | ---: |
| PostgreSQL `model_year` | 53,555 |
| PostgreSQL `recall` | 13,600 |
| PostgreSQL `official_investigation` | 3,626 |
| PostgreSQL `app_user` | 1 |
| PostgreSQL `app_session` | 0 |
| PostgreSQL `saved_vehicle` | 0 |
| MongoDB `complaints` | 428,837 |
| MongoDB `case_details` | 0 |

The account table stores application registrations. A zero session count is
consistent with clients having logged out. Empty workflow storage does not mean
the reference import failed. The saved-vehicle API/menu can now populate personal
records; its tests clean up their fixtures. The analyst-case workflow is still
planned. Counts can change as you use the app.

Connecting with pgAdmin or Compass does not start our Flask application or reset
the databases. It is another way to inspect the same stored records used by our
Python scripts and APIs.

Official tool references: [pgAdmin connections](https://www.pgadmin.org/docs/pgadmin4/latest/connecting.html),
[pgAdmin data grid](https://www.pgadmin.org/docs/pgadmin4/latest/editgrid.html),
[pgAdmin Query Tool](https://www.pgadmin.org/docs/pgadmin4/latest/query_tool.html),
[Compass connections](https://www.mongodb.com/docs/compass/connect/),
[Compass query filters](https://www.mongodb.com/docs/compass/query/filter/).
