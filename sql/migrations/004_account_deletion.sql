-- The auth role receives EXECUTE on this guarded operation, never raw user DELETE.
CREATE OR REPLACE FUNCTION public.delete_unused_account(
    actor_id bigint, target_id bigint, confirmation_email text
) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    actor_role text;
    target public.app_user%ROWTYPE;
    removed_id bigint;
BEGIN
    -- Shared with role changes: concurrent role/delete operations cannot remove
    -- the final admin or act using an admin privilege that was just revoked.
    PERFORM pg_catalog.pg_advisory_xact_lock(2003, 19);
    SELECT u.role INTO actor_role FROM public.app_user u WHERE u.user_id=actor_id FOR UPDATE;
    IF actor_role IS DISTINCT FROM 'ADMIN' THEN
        RAISE EXCEPTION USING ERRCODE='P2001', MESSAGE='ADMIN_REQUIRED';
    END IF;
    SELECT u.* INTO target FROM public.app_user u WHERE u.user_id=target_id FOR UPDATE;
    IF NOT FOUND THEN
        RETURN NULL;
    END IF;
    IF target.role='ADMIN' AND (SELECT count(*) FROM public.app_user WHERE role='ADMIN') <= 1 THEN
        RAISE EXCEPTION USING ERRCODE='P2003', MESSAGE='LAST_ADMINISTRATOR';
    END IF;
    IF actor_id=target_id THEN
        RAISE EXCEPTION USING ERRCODE='P2002', MESSAGE='SELF_DELETION';
    END IF;
    IF confirmation_email IS DISTINCT FROM target.email THEN
        RAISE EXCEPTION USING ERRCODE='P2005', MESSAGE='CONFIRMATION_MISMATCH';
    END IF;
    -- FOR UPDATE also blocks new FK references to the target while these checks
    -- run. Existing work is retained even where the underlying FK would cascade.
    IF EXISTS (SELECT 1 FROM public.saved_vehicle WHERE user_id=target_id)
       OR EXISTS (SELECT 1 FROM public.fleet WHERE owner_id=target_id)
       OR EXISTS (SELECT 1 FROM public.analysis_case WHERE created_by=target_id OR assigned_to=target_id)
       OR EXISTS (SELECT 1 FROM public.case_content_operation WHERE owner_id=target_id OR requested_by=target_id)
    THEN
        RAISE EXCEPTION USING ERRCODE='P2004', MESSAGE='ACCOUNT_IN_USE';
    END IF;
    -- Only sessions may cascade. No MongoDB write is required for an unused user.
    DELETE FROM public.app_user WHERE user_id=target_id RETURNING user_id INTO removed_id;
    RETURN removed_id;
END;
$$;
REVOKE ALL ON FUNCTION public.delete_unused_account(bigint,bigint,text) FROM PUBLIC;
INSERT INTO public.schema_version(version) VALUES (4) ON CONFLICT DO NOTHING;
