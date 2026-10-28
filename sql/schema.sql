-- PostgreSQL 18. Re-running creates missing objects without dropping user data.
CREATE TABLE IF NOT EXISTS schema_version (
    version integer PRIMARY KEY,
    installed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS manufacturer (
    manufacturer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE CHECK (length(btrim(name)) > 0)
);
CREATE TABLE IF NOT EXISTS vehicle_make (
    make_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name text NOT NULL UNIQUE CHECK (length(btrim(name)) > 0)
);
-- Source names include historical names and suppliers: make is not owned by
-- exactly one manufacturer in these files. Associations are not corporate ownership.
CREATE TABLE IF NOT EXISTS manufacturer_make (
    manufacturer_id bigint NOT NULL REFERENCES manufacturer,
    make_id bigint NOT NULL REFERENCES vehicle_make,
    PRIMARY KEY (manufacturer_id, make_id)
);
CREATE TABLE IF NOT EXISTS vehicle_model (
    model_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    make_id bigint NOT NULL REFERENCES vehicle_make,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    UNIQUE (make_id, name)
);
CREATE TABLE IF NOT EXISTS model_year (
    model_year_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    model_id bigint NOT NULL REFERENCES vehicle_model,
    year integer NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    UNIQUE (model_id, year)
);
CREATE TABLE IF NOT EXISTS vehicle_source (
    model_year_id bigint NOT NULL REFERENCES model_year,
    source_name text NOT NULL,
    PRIMARY KEY (model_year_id, source_name)
);

CREATE TABLE IF NOT EXISTS recall (
    recall_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_number text NOT NULL UNIQUE,
    reporting_manufacturer_id bigint REFERENCES manufacturer,
    report_date date,
    summary text,
    consequence text,
    remedy text,
    potentially_affected bigint CHECK (potentially_affected >= 0),
    do_not_drive boolean,
    park_outside boolean
);
CREATE TABLE IF NOT EXISTS recall_vehicle (
    recall_id bigint NOT NULL REFERENCES recall ON DELETE CASCADE,
    model_year_id bigint NOT NULL REFERENCES model_year,
    PRIMARY KEY (recall_id, model_year_id)
);
-- Retain the source component/vehicle grain rather than replacing a campaign
-- repeatedly with each affected vehicle row.
CREATE TABLE IF NOT EXISTS recall_record (
    source_record_id text PRIMARY KEY,
    recall_id bigint NOT NULL,
    model_year_id bigint NOT NULL,
    component text NOT NULL,
    manufacturing_started date,
    manufacturing_ended date,
    source_archive text NOT NULL,
    source_line bigint NOT NULL CHECK (source_line > 0),
    FOREIGN KEY (recall_id, model_year_id)
        REFERENCES recall_vehicle ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS official_investigation (
    investigation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_number text NOT NULL UNIQUE,
    investigation_type text NOT NULL,
    subject text,
    summary text,
    opened_date date,
    closed_date date,
    status text GENERATED ALWAYS AS
        (CASE WHEN closed_date IS NULL THEN 'OPEN' ELSE 'CLOSED' END) STORED
);
CREATE TABLE IF NOT EXISTS investigation_vehicle (
    investigation_id bigint NOT NULL REFERENCES official_investigation ON DELETE CASCADE,
    model_year_id bigint NOT NULL REFERENCES model_year,
    PRIMARY KEY (investigation_id, model_year_id)
);
CREATE TABLE IF NOT EXISTS investigation_manufacturer (
    investigation_id bigint NOT NULL REFERENCES official_investigation ON DELETE CASCADE,
    manufacturer_id bigint NOT NULL REFERENCES manufacturer,
    PRIMARY KEY (investigation_id, manufacturer_id)
);
CREATE TABLE IF NOT EXISTS investigation_component (
    investigation_id bigint NOT NULL REFERENCES official_investigation ON DELETE CASCADE,
    component text NOT NULL,
    PRIMARY KEY (investigation_id, component)
);
-- An investigation may reference a recall outside the post-2010 snapshot.
-- Preserve the external identifier without requiring a local recall FK.
CREATE TABLE IF NOT EXISTS investigation_recall (
    investigation_id bigint NOT NULL REFERENCES official_investigation ON DELETE CASCADE,
    campaign_number text NOT NULL,
    PRIMARY KEY (investigation_id, campaign_number)
);

CREATE TABLE IF NOT EXISTS app_user (
    user_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE CHECK (email = lower(btrim(email))),
    password_hash text NOT NULL,
    role text NOT NULL DEFAULT 'NORMAL_USER'
        CHECK (role IN ('NORMAL_USER', 'ANALYST', 'ADMIN')),
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS saved_vehicle (
    saved_vehicle_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id bigint NOT NULL REFERENCES app_user ON DELETE CASCADE,
    model_year_id bigint NOT NULL REFERENCES model_year,
    nickname text NOT NULL DEFAULT '',
    saved_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id, model_year_id)
);
CREATE TABLE IF NOT EXISTS analysis_case (
    case_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title text NOT NULL CHECK (length(btrim(title)) > 0),
    model_year_id bigint NOT NULL REFERENCES model_year,
    created_by bigint NOT NULL REFERENCES app_user,
    assigned_to bigint REFERENCES app_user,
    priority text NOT NULL DEFAULT 'MEDIUM' CHECK (priority IN ('LOW', 'MEDIUM', 'HIGH')),
    status text NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'REVIEWING', 'CLOSED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    closed_at timestamptz,
    CHECK ((status = 'CLOSED') = (closed_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS case_status_history (
    history_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id bigint NOT NULL REFERENCES analysis_case ON DELETE CASCADE,
    old_status text NOT NULL,
    new_status text NOT NULL,
    changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS fleet (
    fleet_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_id bigint NOT NULL REFERENCES app_user ON DELETE CASCADE,
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (owner_id, name)
);
CREATE TABLE IF NOT EXISTS fleet_vehicle (
    fleet_vehicle_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fleet_id bigint NOT NULL REFERENCES fleet ON DELETE CASCADE,
    model_year_id bigint NOT NULL REFERENCES model_year,
    label text NOT NULL CHECK (length(btrim(label)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (fleet_id, label),
    UNIQUE (fleet_vehicle_id, model_year_id)
);
CREATE TABLE IF NOT EXISTS work_order (
    work_order_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    fleet_vehicle_id bigint NOT NULL,
    model_year_id bigint NOT NULL,
    recall_id bigint NOT NULL,
    status text NOT NULL DEFAULT 'OPEN'
        CHECK (status IN ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    notes text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE (fleet_vehicle_id, recall_id),
    FOREIGN KEY (fleet_vehicle_id, model_year_id)
        REFERENCES fleet_vehicle (fleet_vehicle_id, model_year_id) ON DELETE CASCADE,
    FOREIGN KEY (recall_id, model_year_id) REFERENCES recall_vehicle,
    CHECK ((status = 'COMPLETED') = (completed_at IS NOT NULL))
);
CREATE TABLE IF NOT EXISTS data_import_log (
    import_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_name text NOT NULL,
    source_sha256 text,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    records_read bigint NOT NULL DEFAULT 0,
    records_inserted bigint NOT NULL DEFAULT 0,
    records_updated bigint NOT NULL DEFAULT 0,
    records_skipped bigint NOT NULL DEFAULT 0,
    records_rejected bigint NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'RUNNING' CHECK (status IN ('RUNNING', 'COMPLETED', 'FAILED')),
    error_summary text
);

INSERT INTO schema_version (version) VALUES (1) ON CONFLICT DO NOTHING;

