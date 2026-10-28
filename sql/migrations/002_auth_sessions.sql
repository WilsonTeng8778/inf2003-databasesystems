-- Additive upgrade: keep all existing reference and application records.
CREATE TABLE IF NOT EXISTS app_session (
    token_hash text PRIMARY KEY CHECK (length(token_hash) = 64),
    user_id bigint NOT NULL REFERENCES app_user ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_app_session_user ON app_session (user_id);
CREATE INDEX IF NOT EXISTS idx_app_session_expiry ON app_session (expires_at);
INSERT INTO schema_version (version) VALUES (2) ON CONFLICT DO NOTHING;
