CREATE OR REPLACE VIEW vehicle_catalogue AS
SELECT y.model_year_id, k.name AS make, m.name AS model, y.year
FROM model_year y
JOIN vehicle_model m USING (model_id)
JOIN vehicle_make k USING (make_id);

-- Aggregate independently to avoid multiplying recall and investigation rows.
CREATE OR REPLACE VIEW vehicle_safety_summary AS
SELECT v.*,
       COALESCE(r.recall_count, 0) AS recall_count,
       COALESCE(i.investigation_count, 0) AS investigation_count
FROM vehicle_catalogue v
LEFT JOIN (SELECT model_year_id, count(*) AS recall_count
           FROM recall_vehicle GROUP BY model_year_id) r USING (model_year_id)
LEFT JOIN (SELECT model_year_id, count(*) AS investigation_count
           FROM investigation_vehicle GROUP BY model_year_id) i USING (model_year_id);

-- These views expose only public reference data to the restricted research role.
CREATE OR REPLACE VIEW vehicle_recall_details AS
SELECT rv.model_year_id, r.recall_id, r.campaign_number, r.report_date,
       r.summary, r.consequence, r.remedy, r.potentially_affected,
       r.do_not_drive, r.park_outside
FROM recall_vehicle rv JOIN recall r USING (recall_id);

CREATE OR REPLACE VIEW vehicle_investigation_details AS
SELECT iv.model_year_id, i.investigation_id, i.investigation_number,
       i.investigation_type, i.subject, i.summary, i.opened_date, i.closed_date, i.status
FROM investigation_vehicle iv JOIN official_investigation i USING (investigation_id);

CREATE OR REPLACE VIEW dataset_snapshot AS
SELECT DISTINCT ON (dataset_name) dataset_name, completed_at, records_read
FROM data_import_log WHERE status='COMPLETED' AND completed_at IS NOT NULL
ORDER BY dataset_name, completed_at DESC, import_id DESC;

CREATE OR REPLACE VIEW fleet_recall_matches AS
SELECT f.owner_id, f.fleet_id, fv.fleet_vehicle_id, fv.label,
       v.model_year_id, v.make, v.model, v.year, r.recall_id, r.campaign_number,
       w.work_order_id, w.status AS work_order_status,
       w.notes AS work_order_notes, w.created_at AS work_order_created_at,
       w.completed_at AS work_order_completed_at
FROM fleet f
JOIN fleet_vehicle fv USING (fleet_id)
JOIN vehicle_catalogue v USING (model_year_id)
JOIN recall_vehicle rv USING (model_year_id)
JOIN recall r USING (recall_id)
LEFT JOIN work_order w ON w.fleet_vehicle_id = fv.fleet_vehicle_id AND w.recall_id = r.recall_id;

