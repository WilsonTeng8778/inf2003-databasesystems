-- Narrow monitoring projections. HTTP access is ADMIN-only; the SQL reader
-- receives these views, never direct import-log or account/session table access.
CREATE OR REPLACE VIEW admin_reference_counts AS
SELECT 'vehicle_catalogue'::text AS metric, count(*) AS value FROM model_year
UNION ALL SELECT 'recalls', count(*) FROM recall
UNION ALL SELECT 'recall_vehicle', count(*) FROM recall_vehicle
UNION ALL SELECT 'recall_record', count(*) FROM recall_record
UNION ALL SELECT 'investigations', count(*) FROM official_investigation
UNION ALL SELECT 'investigation_vehicle', count(*) FROM investigation_vehicle
UNION ALL SELECT 'investigation_recall', count(*) FROM investigation_recall
UNION ALL SELECT 'schema_version', max(version)::bigint FROM schema_version;

CREATE OR REPLACE VIEW admin_import_runs AS
SELECT import_id, dataset_name, started_at, completed_at,
       records_read, records_inserted, records_updated, records_skipped, records_rejected, status,
       CASE WHEN source_sha256 ~ '^[0-9a-f]{64}(:[0-9a-f]{64})*$'
            THEN source_sha256 ELSE NULL END AS source_fingerprint,
       (error_summary IS NOT NULL) AS has_error,
       CASE WHEN error_summary IN ('OperationalError', 'IntegrityError', 'UniqueViolation',
                 'ForeignKeyViolation', 'CheckViolation', 'NotNullViolation', 'DataError',
                 'InvalidTextRepresentation', 'ConnectionFailure', 'AutoReconnect',
                 'ServerSelectionTimeoutError', 'BulkWriteError', 'OperationFailure',
                 'DocumentTooLarge', 'ValidationError', 'ValueError', 'TypeError', 'KeyError',
                 'RuntimeError', 'OSError', 'FileNotFoundError', 'BadZipFile', 'UnicodeDecodeError')
            THEN error_summary WHEN error_summary IS NOT NULL THEN 'OTHER_IMPORT_ERROR'
            ELSE NULL END AS failure_category
FROM data_import_log
WHERE dataset_name IN ('vehicle_catalogue', 'recalls', 'investigations', 'complaints');
