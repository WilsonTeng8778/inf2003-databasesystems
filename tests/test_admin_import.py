"""Admin import boundaries, confirmation, snapshot integrity and shared lock cleanup."""

import io
import json
import hashlib
import shutil
import unittest
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError
from uuid import uuid4

from etl.runner import ImportBusy, IMPORT_LOCK, run_imports
from etl.source import SOURCES
from project_config import ROOT
from scripts.admin_import import (AdminImportDenied, ImportCancelled, SourceSnapshotMismatch,
                                  approved_sources, main, run_authorized_import)
from scripts.local_api import ApiError


class AdminImportTests(unittest.TestCase):
    def setUp(self):
        self.api=Mock();self.admin={'user':{'userId':7,'role':'ADMIN'}};self.api.request.return_value=self.admin
        self.connection=Mock();self.connection.closed=False
        self.connection.__enter__=Mock(return_value=self.connection);self.connection.__exit__=Mock(return_value=False)
        self.connection.execute.return_value.fetchone.return_value=(True,)
        self.pg=Mock(return_value=self.connection)
        self.mongo=Mock();self.mongo.__enter__=Mock(return_value=self.mongo);self.mongo.__exit__=Mock(return_value=False)
        self.mongo.__getitem__=Mock(return_value=Mock())
        self.mongo_factory=Mock(return_value=self.mongo);self.pipeline=Mock()
        self.sources=[{'filename':name,'sha256':'a'*64,'bytes':2,'dataset':key} for key,(name,_) in SOURCES.items()]
        self.preflight=Mock(return_value=self.sources);self.confirm=Mock(return_value=True)

    def run_import(self):
        return run_authorized_import(self.api,self.confirm,preflight=self.preflight,pg_factory=self.pg,
                                     mongo_factory=self.mongo_factory,pipeline=self.pipeline)

    def test_non_admins_are_denied_before_preflight_connections_and_confirmation(self):
        for role in ('NORMAL_USER','ANALYST',None):
            self.api.request.return_value={'user':{'userId':7,'role':role}}
            with self.assertRaises(AdminImportDenied):self.run_import()
        self.pg.assert_not_called();self.preflight.assert_not_called();self.confirm.assert_not_called()

    def test_cancel_does_not_open_database_or_start_pipeline(self):
        self.confirm.return_value=False
        with self.assertRaises(ImportCancelled):self.run_import()
        self.pg.assert_not_called();self.pipeline.assert_not_called()

    def test_success_rechecks_role_snapshot_and_uses_the_shared_lock(self):
        result=self.run_import()
        self.assertEqual(result['status'],'COMPLETED');self.assertEqual(result['actorId'],7)
        self.assertEqual(self.api.request.call_count,2);self.assertEqual(self.preflight.call_count,2)
        self.pipeline.assert_called_once_with(self.connection,self.mongo.__getitem__.return_value)
        calls=[call.args for call in self.connection.execute.call_args_list]
        self.assertIn(('SELECT pg_try_advisory_lock(%s)',(IMPORT_LOCK,)),calls)
        self.assertIn(('SELECT pg_advisory_unlock(%s)',(IMPORT_LOCK,)),calls)

    def test_revoked_or_switched_account_is_denied_after_confirmation(self):
        for user in ({'userId':7,'role':'NORMAL_USER'},{'userId':8,'role':'ADMIN'}):
            self.api.request.side_effect=[self.admin,{'user':user}]
            with self.assertRaises(AdminImportDenied):self.run_import()
        self.pipeline.assert_not_called();self.mongo_factory.assert_not_called()

    def test_expired_session_is_denied_at_start_gate(self):
        self.api.request.side_effect=[self.admin,ApiError(401,'Expired')]
        with self.assertRaises(AdminImportDenied):self.run_import()
        self.pipeline.assert_not_called()
        self.connection.rollback.assert_called()

    def test_competing_import_is_refused_without_unlocking_its_lock(self):
        self.connection.execute.return_value.fetchone.return_value=(False,)
        with self.assertRaises(ImportBusy):self.run_import()
        self.pipeline.assert_not_called();self.mongo_factory.assert_not_called()
        self.assertEqual(self.connection.execute.call_count,1)

    def test_changed_source_after_confirmation_starts_no_stages(self):
        changed=deepcopy(self.sources);changed[0]['sha256']='b'*64
        self.preflight.side_effect=[self.sources,changed]
        with self.assertRaises(SourceSnapshotMismatch):self.run_import()
        self.pipeline.assert_not_called()

    def test_failure_restores_transaction_and_releases_session_lock(self):
        self.pipeline.side_effect=RuntimeError('PRIVATE_FAILURE_DIAGNOSTIC')
        with self.assertRaises(RuntimeError):self.run_import()
        self.connection.rollback.assert_called()
        self.assertEqual(self.connection.execute.call_args.args,('SELECT pg_advisory_unlock(%s)',(IMPORT_LOCK,)))

    def source_fixture(self):
        directory=ROOT/'data/logs';directory.mkdir(parents=True,exist_ok=True)
        path=(directory/('admin-import-unit-'+uuid4().hex)).resolve();path.mkdir()
        def cleanup():
            if not path.is_relative_to(directory.resolve()) or not path.name.startswith('admin-import-unit-'):
                raise AssertionError('Unexpected fixture cleanup target')
            shutil.rmtree(path)
        self.addCleanup(cleanup)
        sources={}
        for key,(filename,_) in SOURCES.items():
            data=('fixture '+key).encode();(path/filename).write_bytes(data)
            sources[key]={'filename':filename,'sha256':hashlib.sha256(data).hexdigest()}
        profile=path/'profile.json';profile.write_text(json.dumps({'sources':sources}),encoding='utf-8')
        return path,profile

    def test_preflight_requires_every_fixed_file_and_matching_digest(self):
        raw,profile=self.source_fixture()
        self.assertEqual(len(approved_sources(raw=raw,profile_path=profile)),4)
        target=raw/next(iter(SOURCES.values()))[0];target.write_bytes(b'changed')
        with self.assertRaises(SourceSnapshotMismatch):approved_sources(raw=raw,profile_path=profile)
        target.unlink()
        with self.assertRaises(SourceSnapshotMismatch):approved_sources(raw=raw,profile_path=profile)

    def test_preflight_rejects_invalid_profile_and_filename_substitution(self):
        raw,profile=self.source_fixture();content=json.loads(profile.read_text())
        content['sources']['recalls']['filename']='unapproved.zip';profile.write_text(json.dumps(content))
        with self.assertRaises(SourceSnapshotMismatch):approved_sources(raw=raw,profile_path=profile)
        profile.write_text('not json')
        with self.assertRaises(SourceSnapshotMismatch):approved_sources(raw=raw,profile_path=profile)

    def test_cli_checks_server_before_requesting_credentials_and_sanitizes_errors(self):
        client=Mock();client.request.side_effect=URLError('PRIVATE_CONNECTION_DIAGNOSTIC');out=io.StringIO()
        with patch('scripts.admin_import.LocalApi',return_value=client),patch('builtins.input') as ask,patch('getpass.getpass') as password,redirect_stdout(out):
            self.assertEqual(main([]),1)
        ask.assert_not_called();password.assert_not_called();self.assertNotIn('PRIVATE_CONNECTION_DIAGNOSTIC',out.getvalue())

    def test_cli_logs_out_after_cancel_and_does_not_print_password(self):
        client=Mock();out=io.StringIO()
        with patch('scripts.admin_import.LocalApi',return_value=client),patch('builtins.input',return_value='admin@example.invalid'),patch('getpass.getpass',return_value='PRIVATE_PASSWORD_FIXTURE'),patch('scripts.admin_import.run_authorized_import',side_effect=ImportCancelled('Cancelled')),redirect_stdout(out):
            self.assertEqual(main([]),0)
        self.assertEqual(client.request.call_args.args,('/api/auth/logout',{}))
        self.assertNotIn('PRIVATE_PASSWORD_FIXTURE',out.getvalue())

    def test_pipeline_preserves_stage_order_and_targets_statistics_to_import_tables(self):
        order=[]
        with patch('etl.runner.import_catalogue',side_effect=lambda c:order.append('catalogue')),patch('etl.runner.import_recalls',side_effect=lambda c:order.append('recalls')),patch('etl.runner.import_investigations',side_effect=lambda c:order.append('investigations')),patch('etl.runner.import_complaints',side_effect=lambda c,d:order.append('complaints')):
            run_imports(self.connection,Mock())
        self.assertEqual(order,['catalogue','recalls','investigations','complaints'])
        statements=[call.args[0].as_string() for call in self.connection.execute.call_args_list]
        self.assertTrue(statements);self.assertTrue(all(query.startswith('ANALYZE "') for query in statements))
        self.assertTrue(any('"recall"' in query for query in statements))
        self.assertFalse(any('app_user' in query for query in statements))


if __name__=='__main__':unittest.main()
