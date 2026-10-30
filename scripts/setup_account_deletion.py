"""Apply guarded account deletion and its narrow grant; no reimport or secret writes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from psycopg import sql
from project_config import ROOT, postgres


def apply(connection, role):
    if connection.execute("SELECT to_regclass('public.case_content_operation')").fetchone()[0] is None:
        raise RuntimeError('Apply database/case setup through migration 003 before account deletion setup')
    connection.execute((ROOT / 'sql/migrations/004_account_deletion.sql').read_text(encoding='utf-8'), prepare=False)
    connection.execute(sql.SQL('REVOKE DELETE ON public.app_user FROM {}').format(sql.Identifier(role)))
    connection.execute(sql.SQL('GRANT EXECUTE ON FUNCTION public.delete_unused_account(bigint,bigint,text) TO {}').format(sql.Identifier(role)))


def main():
    role = dotenv_values(ROOT / '.env', interpolate=False).get('AUTH_POSTGRES_USER')
    if not role:
        raise SystemExit('Prepare the separate authentication account with scripts/setup_auth.py first')
    with postgres() as connection:
        flags = connection.execute('SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=%s', (role,)).fetchone()
        if flags is None or any(flags):
            raise RuntimeError('Account deletion requires the existing restricted authentication SQL role')
        apply(connection, role)
    print('Account deletion function and EXECUTE grant ready; schema version 4. Records and local credentials retained.')


if __name__ == '__main__':
    main()
