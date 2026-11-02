-- Durable intent for cross-database case changes; no distributed transaction.
ALTER TABLE analysis_case ADD COLUMN IF NOT EXISTS content_revision bigint NOT NULL DEFAULT 0
    CHECK (content_revision >= 0);

CREATE TABLE IF NOT EXISTS case_content_operation (
    operation_id uuid PRIMARY KEY,
    case_id bigint NOT NULL,
    owner_id bigint NOT NULL REFERENCES app_user,
    requested_by bigint NOT NULL REFERENCES app_user,
    request_hash text NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    action text NOT NULL CHECK (action IN ('REPLACE', 'DELETE')),
    state text NOT NULL DEFAULT 'PENDING' CHECK (state IN ('PENDING', 'APPLIED')),
    payload jsonb,
    last_failure text CHECK (last_failure IN ('MONGODB_UNAVAILABLE', 'SQL_ACKNOWLEDGEMENT_PENDING', 'CONTENT_CONFLICT')),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE (case_id, revision),
    CHECK ((state='APPLIED') = (completed_at IS NOT NULL)),
    CHECK ((state='PENDING' AND action='REPLACE') = (payload IS NOT NULL))
);
-- Deliberately no case FK: a deletion's recovery task must survive its SQL case.
CREATE UNIQUE INDEX IF NOT EXISTS idx_case_operation_pending
    ON case_content_operation(case_id) WHERE state='PENDING';
CREATE INDEX IF NOT EXISTS idx_case_operation_owner ON case_content_operation(owner_id,state,created_at);
INSERT INTO schema_version(version) VALUES (3) ON CONFLICT DO NOTHING;
