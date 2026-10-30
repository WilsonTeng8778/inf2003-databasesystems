"""Native guards/concurrency on an owned schema copy of the deletion function.

Existing accounts are never deletion targets. Browser verification separately
uses the real HTTP/function path with its own synthetic accounts.
"""

import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic, sleep
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import dotenv_values
from psycopg import Error, sql
from project_config import ROOT, app_postgres, auth_postgres, postgres
from scripts.benchmark_databases import owned_namespace
from scripts.verify_cases import snapshot


def main():
    namespace = 'bench_' + uuid4().hex
    owned_namespace(namespace, namespace)
    directory = ROOT / 'docs/account_deletion' / datetime.now().strftime('%Y%m%dT%H%M%S')
    directory.mkdir(parents=True, exist_ok=False)
    report = {'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'successful': False,
              'checks': [], 'fixture_schema': namespace, 'fixture_schema_removed': False,
              'scope': 'Native auth-role function checks and concurrency on minimal owned fixture tables; no existing account is a deletion target.'}
    before = snapshot()
    created = False
    q = lambda name: sql.Identifier(namespace, name)
    auth_role = dotenv_values(ROOT / '.env', interpolate=False)['AUTH_POSTGRES_USER']

    def check(value, message):
        if not value:
            raise AssertionError(message)
        report['checks'].append(message)

    def call(actor, target, email):
        try:
            with auth_postgres() as c:
                removed = c.execute(sql.SQL('SELECT {}(%s,%s,%s)').format(q('delete_unused_account')),
                                    (actor, target, email)).fetchone()[0]
            return {'removed': removed}
        except Error as error:
            return {'sqlstate': error.sqlstate}

    def blocked(code, actor, target, email):
        check(call(actor, target, email) == {'sqlstate': code}, 'Guard rejects ' + code)

    def seed(role='NORMAL_USER'):
        email = uuid4().hex + '@example.invalid'
        with postgres() as c:
            user_id = c.execute(sql.SQL('INSERT INTO {}(email,role) VALUES (%s,%s) RETURNING user_id').format(q('app_user')),
                                (email, role)).fetchone()[0]
        return user_id, email

    def edit(query, values=()):
        with postgres() as c:
            return c.execute(query, values)

    def async_call(details, actor, target, email, barrier=None):
        try:
            with auth_postgres() as c:
                details['pid'] = c.info.backend_pid
                details['ready'].set()
                if barrier is not None:
                    barrier.wait(timeout=5)
                value = c.execute(sql.SQL('SELECT {}(%s,%s,%s)').format(q('delete_unused_account')),
                                  (actor, target, email)).fetchone()[0]
            return {'removed': value}
        except Error as error:
            return {'sqlstate': error.sqlstate}

    def wait_blocked(details, blocker):
        assert details['ready'].wait(3), 'Native worker did not start'
        deadline = monotonic() + 3
        with postgres(autocommit=True) as c:
            while monotonic() < deadline:
                if c.execute('SELECT %s=ANY(pg_blocking_pids(%s))', (blocker, details['pid'])).fetchone()[0]:
                    return
                sleep(0.02)
        raise AssertionError('Expected native lock wait was not observed')

    try:
        with auth_postgres() as c:
            check(not c.execute("SELECT has_table_privilege(current_user,'public.app_user','DELETE')").fetchone()[0],
                  'Auth SQL role has no direct DELETE on public accounts')
            check(c.execute("SELECT has_function_privilege(current_user,'public.delete_unused_account(bigint,bigint,text)','EXECUTE')").fetchone()[0],
                  'Auth SQL role can execute only the granted guarded deletion capability')
            for table in ('saved_vehicle', 'fleet', 'analysis_case', 'case_content_operation'):
                check(not c.execute('SELECT has_table_privilege(current_user,%s,\'SELECT\')', ('public.'+table,)).fetchone()[0],
                      'Auth SQL role cannot directly read ' + table)
        with app_postgres() as c:
            check(not c.execute("SELECT has_function_privilege(current_user,'public.delete_unused_account(bigint,bigint,text)','EXECUTE')").fetchone()[0],
                  'Research SQL reader cannot execute account deletion')
        with postgres() as c:
            config = c.execute("SELECT prosecdef,proconfig FROM pg_proc WHERE oid='public.delete_unused_account(bigint,bigint,text)'::regprocedure").fetchone()
            check(config[0] and 'search_path=pg_catalog, pg_temp' in config[1], 'Definer function uses its fixed safe search path')
            check(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a WHERE p.oid='public.delete_unused_account(bigint,bigint,text)'::regprocedure AND a.grantee=0 AND a.privilege_type='EXECUTE')").fetchone()[0],
                  'PUBLIC has no default EXECUTE grant')
            c.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(namespace)))
            created = True
            # Minimal tables preserve exactly the fields/FKs used by the guard.
            # No public table/data/role is copied or rewritten for isolation.
            definitions = {
                'app_user': 'user_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,email text UNIQUE NOT NULL,role text NOT NULL',
                'schema_version': 'version integer PRIMARY KEY',
                'app_session': f'token_hash text PRIMARY KEY,user_id bigint REFERENCES {namespace}.app_user ON DELETE CASCADE',
                'saved_vehicle': f'user_id bigint REFERENCES {namespace}.app_user ON DELETE CASCADE',
                'fleet': f'owner_id bigint REFERENCES {namespace}.app_user ON DELETE CASCADE',
                'analysis_case': f'created_by bigint REFERENCES {namespace}.app_user,assigned_to bigint REFERENCES {namespace}.app_user',
                'case_content_operation': f'owner_id bigint REFERENCES {namespace}.app_user,requested_by bigint REFERENCES {namespace}.app_user,state text',
            }
            for name, definition in definitions.items():
                c.execute(sql.SQL('CREATE TABLE {} ({})').format(q(name), sql.SQL(definition)))
            migration = (ROOT / 'sql/migrations/004_account_deletion.sql').read_text(encoding='utf-8')
            c.execute(migration.replace('public.', namespace + '.'), prepare=False)
            c.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(namespace), sql.Identifier(auth_role)))
            c.execute(sql.SQL('GRANT EXECUTE ON FUNCTION {}(bigint,bigint,text) TO {}').format(q('delete_unused_account'), sql.Identifier(auth_role)))
        admin, admin_email = seed('ADMIN')
        blocked('P2003', admin, admin, admin_email)
        other, other_email = seed('ADMIN')
        target, target_email = seed()
        normal, _ = seed()
        blocked('P2002', admin, admin, admin_email)
        blocked('P2001', normal, target, target_email)
        blocked('P2005', admin, target, 'wrong@example.invalid')
        check(call(admin, 9223372036854775807, target_email) == {'removed': None}, 'Missing account returns no deletion')
        for table, columns, values in [
            ('saved_vehicle', 'user_id', (target,)), ('fleet', 'owner_id', (target,)),
            ('analysis_case', 'created_by,assigned_to', (target, admin)),
            ('analysis_case', 'created_by,assigned_to', (admin, target)),
            *[('case_content_operation', 'owner_id,requested_by,state', (*pair, state))
              for pair in ((target, admin), (admin, target)) for state in ('PENDING', 'APPLIED')],
        ]:
            placeholders = sql.SQL(',').join(sql.Placeholder() for _ in values)
            edit(sql.SQL('INSERT INTO {} ({}) VALUES ({})').format(q(table), sql.SQL(columns), placeholders), values)
            blocked('P2004', admin, target, target_email)
            edit(sql.SQL('DELETE FROM {}').format(q(table)))
        check(True, 'Saves, fleets, case creator/assignee and pending/applied owner/requester history all block deletion')
        edit(sql.SQL('INSERT INTO {}(user_id,token_hash) VALUES (%s,%s),(%s,%s)').format(q('app_session')),
             (target, uuid4().hex, target, uuid4().hex))
        check(call(admin, target, target_email) == {'removed': target}, 'Unused account is removed through the actual auth SQL role')
        with postgres() as c:
            check(c.execute(sql.SQL('SELECT count(*) FROM {} WHERE user_id=%s').format(q('app_session')), (target,)).fetchone()[0] == 0,
                  'Deletion cascades all target sessions')

        target, target_email = seed()
        with ThreadPoolExecutor(max_workers=2) as pool:
            with postgres() as holder:
                holder.execute(sql.SQL('INSERT INTO {}(user_id) VALUES (%s)').format(q('saved_vehicle')), (target,))
                details = {'ready': threading.Event()}
                future = pool.submit(async_call, details, admin, target, target_email)
                wait_blocked(details, holder.info.backend_pid)
                holder.commit()
                check(future.result(timeout=6) == {'sqlstate': 'P2004'}, 'Deletion waits for an in-flight FK insert and then retains the new save/account')
            edit(sql.SQL('DELETE FROM {}').format(q('saved_vehicle')))
            with postgres() as holder:
                holder.execute('SELECT pg_advisory_xact_lock(2003,19)')
                details = {'ready': threading.Event()}
                future = pool.submit(async_call, details, admin, target, target_email)
                wait_blocked(details, holder.info.backend_pid)
                holder.execute(sql.SQL("UPDATE {} SET role='NORMAL_USER' WHERE user_id=%s").format(q('app_user')), (admin,))
                holder.commit()
                check(future.result(timeout=6) == {'sqlstate': 'P2001'}, 'Actor role is rechecked after waiting for the shared role/delete lock')
            edit(sql.SQL("UPDATE {} SET role='ADMIN' WHERE user_id=%s").format(q('app_user')), (admin,))
            barrier = threading.Barrier(2)
            first = pool.submit(async_call, {'ready': threading.Event()}, admin, other, other_email, barrier)
            second = pool.submit(async_call, {'ready': threading.Event()}, other, admin, admin_email, barrier)
            results = [first.result(timeout=7), second.result(timeout=7)]
            check(sum('removed' in result for result in results) == 1 and sum(result.get('sqlstate') == 'P2001' for result in results) == 1,
                  'Concurrent cross-deletion allows one admin removal and rejects the now-deleted actor')
        with postgres() as c:
            check(c.execute(sql.SQL("SELECT count(*) FROM {} WHERE role='ADMIN'").format(q('app_user'))).fetchone()[0] == 1,
                  'Concurrent deletion leaves one administrator')
        report['native_checks_passed'] = True
    except Exception as error:
        report['failure_type'] = type(error).__name__
    finally:
        if created:
            owned_namespace(namespace, namespace)
            with postgres() as c:
                c.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(namespace)))
                report['fixture_schema_removed'] = not c.execute('SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname=%s)', (namespace,)).fetchone()[0]
        after = snapshot()
        report['existing_record_counts_unchanged'] = before == after
        report['record_counts'] = after
        report['successful'] = bool(report.get('native_checks_passed') and report['fixture_schema_removed'] and report['existing_record_counts_unchanged'])
        report['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        (directory / 'native_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('Native account checks passed:', len(report['checks']), 'successful:', report['successful'])
    print('Evidence:', directory.relative_to(ROOT).as_posix())
    if not report['successful']:
        print('Failure type:', report.get('failure_type', 'cleanup/count check'))
    return 0 if report['successful'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
