"""Add durable case operations and a limited SQL case-service role; retain data."""

import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values, set_key
from psycopg import sql
from project_config import ROOT, mongo_client, mongo_database, postgres
from mongodb.schema import SCHEMAS


def main():
    path = ROOT / '.env'
    if not path.is_file():
        raise RuntimeError('Configure .env first')
    settings = dotenv_values(path, interpolate=False)
    role = settings.get('CASE_POSTGRES_USER') or 'vehicle_safety_cases'
    if role in {os.getenv('POSTGRES_USER', 'postgres'), 'postgres', 'public',
                *[settings.get(key) for key in ('APP_POSTGRES_USER', 'AUTH_POSTGRES_USER', 'WORKFLOW_POSTGRES_USER')]}:
        raise ValueError('Case access requires a separate non-administrator SQL role')
    password = settings.get('CASE_POSTGRES_PASSWORD')
    with postgres() as connection:
        connection.execute((ROOT / 'sql/migrations/003_case_operations.sql').read_text(encoding='utf-8'), prepare=False)
        exists = connection.execute('''SELECT rolsuper,rolcreatedb,rolcreaterole,rolreplication,rolbypassrls
            FROM pg_roles WHERE rolname=%s''', (role,)).fetchone()
        if exists:
            if any(exists) or not password:
                raise RuntimeError('Case role has unexpected privileges or missing local credentials')
        else:
            password = password or secrets.token_urlsafe(32)
            connection.execute(sql.SQL('''CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB
                NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS''').format(sql.Identifier(role), sql.Literal(password)))
        database = connection.execute('SELECT current_database()').fetchone()[0]
        connection.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(database), sql.Identifier(role)))
        connection.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
        connection.execute(sql.SQL('''GRANT SELECT ON vehicle_catalogue,analysis_case,case_status_history,case_content_operation TO {}''').format(sql.Identifier(role)))
        connection.execute(sql.SQL('''GRANT INSERT(title,model_year_id,created_by,assigned_to,priority,content_revision),
            UPDATE(title,priority,status,closed_at,content_revision),DELETE ON analysis_case TO {}''').format(sql.Identifier(role)))
        # The existing status-history trigger runs as its invoking SQL role.
        connection.execute(sql.SQL('GRANT INSERT(case_id,old_status,new_status) ON case_status_history TO {}').format(sql.Identifier(role)))
        connection.execute(sql.SQL('''GRANT INSERT(operation_id,case_id,owner_id,requested_by,request_hash,revision,action,payload),
            UPDATE(state,payload,last_failure,completed_at) ON case_content_operation TO {}''').format(sql.Identifier(role)))
        connection.execute(sql.SQL('''GRANT USAGE ON SEQUENCE analysis_case_case_id_seq,case_status_history_history_id_seq TO {}''').format(sql.Identifier(role)))
        connection.execute(sql.SQL("ALTER ROLE {} SET statement_timeout='5s'").format(sql.Identifier(role)))
        set_key(str(path), 'CASE_POSTGRES_USER', role)
        set_key(str(path), 'CASE_POSTGRES_PASSWORD', password)
    with mongo_client() as client:
        database = mongo_database(client)
        if database.name in {'admin', 'config', 'local'}:
            raise ValueError('Use the dedicated project MongoDB database')
        options = {'validator': {'$jsonSchema': SCHEMAS['case_details']},
                   'validationLevel': 'strict', 'validationAction': 'error'}
        if 'case_details' in database.list_collection_names():
            database.command({'collMod': 'case_details', **options})
        else:
            database.create_collection('case_details', **options)
        database.case_details.create_index('caseId', unique=True, name='case_id_unique')
    print('Case migration, limited SQL role and MongoDB case validator ready. Credentials kept only in ignored .env; existing records retained.')


if __name__ == '__main__':
    main()
