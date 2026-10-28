# Initial physical database design

This design follows the [approved scope](IMPLEMENTATION_GREENLIGHT.md) and
[actual source inspection](DATA_INSPECTION.md). The initial model is in `sql/` and
`mongodb/schema.py`; additive migration `sql/migrations/002_auth_sessions.sql`
brings SQL construction to schema version 2.

## Relational model

```mermaid
erDiagram
    MANUFACTURER ||--o{ MANUFACTURER_MAKE : associated
    VEHICLE_MAKE ||--o{ MANUFACTURER_MAKE : associated
    VEHICLE_MAKE ||--o{ VEHICLE_MODEL : contains
    VEHICLE_MODEL ||--o{ MODEL_YEAR : has
    MODEL_YEAR ||--o{ VEHICLE_SOURCE : observed_in
    MANUFACTURER ||--o{ RECALL : reported_by
    RECALL ||--o{ RECALL_VEHICLE : affects
    MODEL_YEAR ||--o{ RECALL_VEHICLE : covered_by
    RECALL_VEHICLE ||--o{ RECALL_RECORD : has_component_rows
    OFFICIAL_INVESTIGATION ||--o{ INVESTIGATION_VEHICLE : affects
    MODEL_YEAR ||--o{ INVESTIGATION_VEHICLE : investigated
    OFFICIAL_INVESTIGATION ||--o{ INVESTIGATION_MANUFACTURER : involves
    MANUFACTURER ||--o{ INVESTIGATION_MANUFACTURER : involved_in
    OFFICIAL_INVESTIGATION ||--o{ INVESTIGATION_COMPONENT : covers
    OFFICIAL_INVESTIGATION ||--o{ INVESTIGATION_RECALL : references
    APP_USER ||--o{ SAVED_VEHICLE : saves
    APP_USER ||--o{ APP_SESSION : signs_in
    MODEL_YEAR ||--o{ SAVED_VEHICLE : saved_as
    APP_USER ||--o{ ANALYSIS_CASE : creates
    MODEL_YEAR ||--o{ ANALYSIS_CASE : concerns
    ANALYSIS_CASE ||--o{ CASE_STATUS_HISTORY : records
    APP_USER ||--o{ FLEET : owns
    FLEET ||--o{ FLEET_VEHICLE : contains
    MODEL_YEAR ||--o{ FLEET_VEHICLE : identifies
    FLEET_VEHICLE ||--o{ WORK_ORDER : tracks
    RECALL_VEHICLE ||--o{ WORK_ORDER : permits

    MANUFACTURER {
        bigint manufacturer_id PK
        text name UK
    }
    VEHICLE_MAKE {
        bigint make_id PK
        text name UK
    }
    MANUFACTURER_MAKE {
        bigint manufacturer_id FK
        bigint make_id FK
    }
    VEHICLE_MODEL {
        bigint model_id PK
        bigint make_id FK
        text name
    }
    MODEL_YEAR {
        bigint model_year_id PK
        bigint model_id FK
        integer year
    }
    VEHICLE_SOURCE {
        bigint model_year_id FK
        text source_name
    }
    RECALL {
        bigint recall_id PK
        text campaign_number UK
        bigint reporting_manufacturer_id FK
        date report_date
        text summary
        text consequence
        text remedy
    }
    RECALL_VEHICLE {
        bigint recall_id FK
        bigint model_year_id FK
    }
    RECALL_RECORD {
        text source_record_id PK
        bigint recall_id FK
        bigint model_year_id FK
        text component
        date manufacturing_started
        date manufacturing_ended
    }
    OFFICIAL_INVESTIGATION {
        bigint investigation_id PK
        text investigation_number UK
        text investigation_type
        date opened_date
        date closed_date
        text status
        text summary
    }
    INVESTIGATION_VEHICLE {
        bigint investigation_id FK
        bigint model_year_id FK
    }
    INVESTIGATION_MANUFACTURER {
        bigint investigation_id FK
        bigint manufacturer_id FK
    }
    INVESTIGATION_COMPONENT {
        bigint investigation_id FK
        text component
    }
    INVESTIGATION_RECALL {
        bigint investigation_id FK
        text campaign_number
    }
    APP_USER {
        bigint user_id PK
        text email UK
        text password_hash
        text role
        timestamptz created_at
    }
    SAVED_VEHICLE {
        bigint saved_vehicle_id PK
        bigint user_id FK
        bigint model_year_id FK
        text nickname
        timestamptz saved_at
    }
    APP_SESSION {
        text token_hash PK
        bigint user_id FK
        timestamptz created_at
        timestamptz expires_at
    }
    ANALYSIS_CASE {
        bigint case_id PK
        bigint model_year_id FK
        bigint created_by FK
        bigint assigned_to FK
        text title
        text priority
        text status
        timestamptz created_at
        timestamptz closed_at
    }
    CASE_STATUS_HISTORY {
        bigint history_id PK
        bigint case_id FK
        text old_status
        text new_status
        timestamptz changed_at
    }
    FLEET {
        bigint fleet_id PK
        bigint owner_id FK
        text name
    }
    FLEET_VEHICLE {
        bigint fleet_vehicle_id PK
        bigint fleet_id FK
        bigint model_year_id FK
        text label
    }
    WORK_ORDER {
        bigint work_order_id PK
        bigint fleet_vehicle_id FK
        bigint model_year_id FK
        bigint recall_id FK
        text status
        text notes
        timestamptz completed_at
    }
```

`analysis_case.assigned_to` is a second nullable relationship to `app_user`.
`data_import_log` audits import runs. `schema_version` identifies construction
version. See `sql/schema.sql` for every column, data type and constraint.

Important integrity rules:

- Make names, model names within a make, and model years within a model are unique.
- Campaign numbers and action numbers identify official records; affected vehicles
  are many-to-many. Imported official records are intended as reference data.
- One user can save a model-year identity once. A fleet can contain several physical
  vehicles of the same model-year, distinguished by user-supplied labels.
- A work order references both the specific fleet vehicle and an applicable
  `recall_vehicle` pair through composite foreign keys. This prevents a work order
  being attached to a recall for an unrelated model-year.
- Case priority/status and user role are constrained to the agreed values. Closed
  cases require `closed_at`; completed work orders require `completed_at`.
- A status-change trigger records case history. Deleting a case removes its SQL
  history; deleting a fleet cascades its local vehicles/orders.
- Manufacturer relationships reflect observed source associations, not an assumed
  single corporate parent. Investigations have many-to-many manufacturer links.

`vehicle_catalogue`, `vehicle_safety_summary`, and `fleet_recall_matches` are useful
SQL views. The safety summary aggregates recalls and investigations separately
before joining them, preventing a many-to-many join from multiplying counts.

## MongoDB model

`complaints` holds one document per verified ODI identifier, with:

```text
_id / odiNumber: string
modelYearId: SQL external reference
vehicle: { make, model, year }
manufacturer: normalized source name
components: unique string array
incident: { crash, fire, injuries, fatalities }
mileage / occurrences: integer or null
receivedDate / incidentDate: BSON UTC date or null
narrative: public source text
source: { archives[], rowIds[], componentRowCount, conflictingScalarColumns[] }
```

`case_details` holds application-owned flexible content:

```text
caseId: unique SQL analysis_case external reference
linkedComplaints: ODI identifier strings[]
suspectedComponents: string[]
findings: [{ findingId, authorId, createdAt, observation }]
notes: [{ noteId, authorId, createdAt, text }]
tags: unique string[]
```

MongoDB JSON Schema validators check required fields and types. Indexes cover
vehicle/date, vehicle/component, narrative text, and unique case identifiers.
Component arrays are deduplicated. Component-group counts can overlap because one
complaint can concern several components; overall complaint counts use documents.

## Application responsibilities for the next stage

SQL foreign keys cannot validate MongoDB references. The backend must validate
case/author/complaint references and ensure linked complaints match the case's
vehicle. Case creation must handle a MongoDB failure with rollback or explicit
compensation; case deletion must reconcile both stores. No distributed transaction
system is planned.

The initial verification script exercises direct database operations. Read-only
research uses a SQL reader restricted to research views. Authentication now uses
a separate account with limited user-column/session permissions, signed cookies,
hashed server-side session tokens, role guards and guarded administrator changes;
see [Backend step 2](BACKEND_STEP_2_AUTH.md).

`app_session` references users with delete cascade. Its opaque token's SHA-256
hash is the primary key; raw tokens are not stored in SQL. Expiration is checked
on lookup. Logout deletes the row, and role checks join the current `app_user`
record rather than trusting a role cached in a cookie. Schema migration 002 adds
this table without replacing reference data.

Saved-vehicle CRUD now uses owner-scoped SQL predicates and a limited workflow
account; see [Backend step 3](BACKEND_STEP_3_SAVED_VEHICLES.md). The owner comes
from the authenticated session and cannot be changed by a request payload.
Only nickname updates are granted for saved records. Database row-level security
is not configured; the API supplies the ownership conditions.

Case/fleet ownership, their editable APIs and the cross-database case service
remain backend work. A role column alone does not enforce application permissions.
The `postgres` account remains for trusted construction/imports and first-admin
bootstrap.

