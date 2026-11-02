-- Public reference data only. Grant the web reader SELECT on these views,
-- without granting access to source tables or private application workflows.
CREATE OR REPLACE VIEW research_recall AS
SELECT r.recall_id, r.campaign_number, m.name AS manufacturer, r.report_date,
       r.summary, r.consequence, r.remedy, r.potentially_affected, r.do_not_drive, r.park_outside
FROM recall r LEFT JOIN manufacturer m ON m.manufacturer_id = r.reporting_manufacturer_id;

CREATE OR REPLACE VIEW research_recall_vehicle AS
SELECT rv.recall_id, v.model_year_id, v.make, v.model, v.year
FROM recall_vehicle rv JOIN vehicle_catalogue v USING (model_year_id);

CREATE OR REPLACE VIEW research_recall_record AS
SELECT rr.source_record_id, rr.recall_id, v.model_year_id, v.make, v.model, v.year,
       rr.component, rr.manufacturing_started, rr.manufacturing_ended,
       rr.source_archive, rr.source_line
FROM recall_record rr JOIN vehicle_catalogue v USING (model_year_id);

CREATE OR REPLACE VIEW research_investigation AS
SELECT investigation_id, investigation_number, investigation_type, subject, summary,
       opened_date, closed_date, status FROM official_investigation;

CREATE OR REPLACE VIEW research_investigation_vehicle AS
SELECT iv.investigation_id, v.model_year_id, v.make, v.model, v.year
FROM investigation_vehicle iv JOIN vehicle_catalogue v USING (model_year_id);

CREATE OR REPLACE VIEW research_investigation_component AS
SELECT investigation_id, component FROM investigation_component;

CREATE OR REPLACE VIEW research_investigation_manufacturer AS
SELECT im.investigation_id, m.name AS manufacturer
FROM investigation_manufacturer im JOIN manufacturer m USING (manufacturer_id);

-- A referenced campaign may be outside the selected recall snapshot.
CREATE OR REPLACE VIEW research_investigation_recall AS
SELECT ir.investigation_id, ir.campaign_number, r.recall_id
FROM investigation_recall ir LEFT JOIN recall r USING (campaign_number);
