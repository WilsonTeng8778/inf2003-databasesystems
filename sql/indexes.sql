-- PK/UNIQUE constraints already create indexes. These support reverse lookups.
CREATE INDEX IF NOT EXISTS idx_recall_vehicle_model_year
    ON recall_vehicle (model_year_id, recall_id);
CREATE INDEX IF NOT EXISTS idx_investigation_vehicle_model_year
    ON investigation_vehicle (model_year_id, investigation_id);
CREATE INDEX IF NOT EXISTS idx_recall_record_vehicle
    ON recall_record (model_year_id, recall_id);
CREATE INDEX IF NOT EXISTS idx_manufacturer_make_make
    ON manufacturer_make (make_id, manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_analysis_case_assigned
    ON analysis_case (assigned_to, status);
CREATE INDEX IF NOT EXISTS idx_fleet_vehicle_fleet ON fleet_vehicle (fleet_id);

