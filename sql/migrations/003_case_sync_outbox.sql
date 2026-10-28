-- Durable, idempotent work for synchronising SQL cases with MongoDB documents.
-- No foreign key: a DELETE job must survive deletion of its SQL case.
CREATE TABLE IF NOT EXISTS case_sync_outbox (
    job_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id bigint NOT NULL,
    operation text NOT NULL CHECK (operation IN ('CREATE', 'DELETE')),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE (case_id, operation)
);
CREATE INDEX IF NOT EXISTS idx_case_sync_pending
    ON case_sync_outbox (case_id, job_id) WHERE completed_at IS NULL;
INSERT INTO schema_version (version) VALUES (3) ON CONFLICT DO NOTHING;
