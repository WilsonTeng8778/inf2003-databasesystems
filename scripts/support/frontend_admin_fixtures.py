"""Owned admin-verification fixtures and isolated native SQL guard/projection checks."""

from backend.services.auth import LastAdministrator, PostgresAuthStore
from project_config import app_postgres, postgres
from scripts.support.local_api import LocalApi


def prepare_admin_fixtures(base_url, emails, password, admin_id):
    for email in emails[5:]:
        client=LocalApi(base_url);client.request('/api/auth/csrf')
        client.request('/api/auth/register',{'email':email,'password':password},method='POST')
        client.request('/api/auth/logout',{},method='POST')
    assertions=[]
    with app_postgres() as connection:
        for table in ['data_import_log','schema_version','app_user','app_session']:
            assert not connection.execute("SELECT has_table_privilege(current_user,%s,'SELECT,INSERT,UPDATE,DELETE')",(table,)).fetchone()[0]
        for name in ['admin_reference_counts','admin_import_runs']:
            assert connection.execute("SELECT has_table_privilege(current_user,%s,'SELECT')",(name,)).fetchone()[0]
            assert not connection.execute("SELECT has_table_privilege(current_user,%s,'INSERT,UPDATE,DELETE')",(name,)).fetchone()[0]
        connection.execute('SELECT * FROM admin_reference_counts').fetchall()
        connection.execute('SELECT * FROM admin_import_runs LIMIT 1').fetchall()
    assertions.append('Restricted SQL reader can read only monitoring views and cannot read/write raw audit, account or session tables.')
    with postgres() as connection:
        # This owned row is visible only within this transaction, then rolled back.
        identifier=connection.execute("""INSERT INTO data_import_log(dataset_name,status,error_summary,source_sha256)
            VALUES ('complaints','FAILED','password=PRIVATE_FIXTURE_DIAGNOSTIC','INVALID_FINGERPRINT') RETURNING import_id""").fetchone()[0]
        result=connection.execute('SELECT source_fingerprint,has_error,failure_category FROM admin_import_runs WHERE import_id=%s',(identifier,)).fetchone()
        assert result==(None,True,'OTHER_IMPORT_ERROR')
        connection.execute('UPDATE data_import_log SET error_summary=%s,source_sha256=%s WHERE import_id=%s',('OperationalError','a'*64+':'+ 'b'*64,identifier))
        result=connection.execute('SELECT source_fingerprint,failure_category FROM admin_import_runs WHERE import_id=%s',(identifier,)).fetchone()
        assert result==('a'*64+':'+ 'b'*64,'OperationalError')
        connection.rollback()
    assertions.append('Monitoring view hides arbitrary diagnostics/invalid fingerprints and retains allowed exception categories and paired archive hashes; fixture transaction rolled back.')
    with postgres() as connection:
        # Exercise the real repository SQL against one synthetic admin in a
        # temporary table. Existing public.app_user rows are never changed.
        connection.execute('CREATE TEMP TABLE app_user ON COMMIT DROP AS SELECT * FROM public.app_user WHERE user_id=%s',(admin_id,))
        try:
            PostgresAuthStore(connection).change_role(admin_id,admin_id,'NORMAL_USER')
        except LastAdministrator:
            pass
        else:
            raise AssertionError('The native last-administrator guard should reject demotion')
        assert connection.execute('SELECT role FROM pg_temp.app_user').fetchone()[0]=='ADMIN'
        connection.rollback()
    assertions.append('Real role-mutation SQL rejects the last-admin demotion in an isolated temporary table containing only the synthetic admin.')
    return assertions
