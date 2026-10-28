CREATE OR REPLACE FUNCTION record_case_status_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO case_status_history (case_id, old_status, new_status)
        VALUES (NEW.case_id, OLD.status, NEW.status);
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER analysis_case_status_history
AFTER UPDATE OF status ON analysis_case
FOR EACH ROW EXECUTE FUNCTION record_case_status_change();

