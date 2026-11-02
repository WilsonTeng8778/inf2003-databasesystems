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

CREATE OR REPLACE VIEW fleet_recall_matches AS
SELECT f.owner_id, f.fleet_id, fv.fleet_vehicle_id, fv.label,
       v.model_year_id, v.make, v.model, v.year, r.recall_id, r.campaign_number,
       w.work_order_id, w.status AS work_order_status
FROM fleet f
JOIN fleet_vehicle fv USING (fleet_id)
JOIN vehicle_catalogue v USING (model_year_id)
JOIN recall_vehicle rv USING (model_year_id)
JOIN recall r USING (recall_id)
LEFT JOIN work_order w ON w.fleet_vehicle_id = fv.fleet_vehicle_id AND w.recall_id = r.recall_id;

