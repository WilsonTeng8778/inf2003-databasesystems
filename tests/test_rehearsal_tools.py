"""Protect historical reports and the reproducibility/secret-exclusion boundary."""

import shutil
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from project_config import ROOT
from scripts.rehearse_project import performance_evidence, source_snapshot
from scripts.support.verification_reports import select_report_path, validate_report_path


class RehearsalToolsTests(unittest.TestCase):
    def setUp(self):
        self.parent = (ROOT / 'data/logs' / ('rehearsal-unit-' + uuid4().hex)).resolve()
        self.parent.mkdir(parents=True)
        self.root = self.parent / 'repo';self.root.mkdir()
        (self.root / 'local/docs').mkdir(parents=True);(self.root / 'backend').mkdir()

    def tearDown(self):
        if not self.parent.is_relative_to((ROOT / 'data/logs').resolve()) or not self.parent.name.startswith('rehearsal-unit-'):
            raise AssertionError('Unexpected fixture cleanup target')
        shutil.rmtree(self.parent)

    def test_output_refuses_to_replace_historical_report(self):
        target = self.root / 'local/docs/milestone.json';target.write_text('historical')
        with self.assertRaises(FileExistsError):validate_report_path(target, root=self.root)
        self.assertEqual(target.read_text(), 'historical')

    def test_report_output_requires_json_under_docs(self):
        for target in (self.root / '.env', self.root / 'backend/new.json', self.parent / 'escape.json', self.root / 'local/docs/new.py'):
            with self.assertRaises(ValueError):validate_report_path(target, root=self.root)
        self.assertEqual(validate_report_path('local/docs/new/report.json', root=self.root), self.root / 'local/docs/new/report.json')

    def test_default_output_paths_are_distinct_and_do_not_replace_legacy(self):
        legacy = self.root / 'local/docs/cases_verification_report.json';legacy.write_text('legacy')
        with patch('scripts.support.verification_reports.ROOT', self.root):
            first = select_report_path('cases', []);second = select_report_path('cases', [])
        self.assertNotEqual(first, second)
        self.assertTrue(first.parent.is_dir());self.assertEqual(legacy.read_text(), 'legacy')

    def test_snapshot_excludes_secrets_runtime_data_and_reports(self):
        (self.root / '.env').write_text('PRIVATE_FIXTURE_ONLY')
        (self.root / 'backend/app.py').write_text('app = 1')
        (self.root / 'backend/.env').write_text('PRIVATE_NESTED_FIXTURE_ONLY')
        (self.root / 'local/docs/result.json').write_text('{}')
        result = source_snapshot(root=self.root, paths=['.env', 'backend/.env', 'backend/app.py', 'local/docs/result.json', 'data/raw/source.zip'])
        self.assertEqual(set(result['files_sha256']), {'backend/app.py'})

    def test_snapshot_is_order_independent_and_changes_with_code(self):
        a = self.root / 'backend/a.py';b = self.root / 'backend/b.py'
        a.write_text('a=1');b.write_text('b=2')
        first = source_snapshot(root=self.root, paths=['backend/a.py', 'backend/b.py'])
        second = source_snapshot(root=self.root, paths=['backend/b.py', 'backend/a.py'])
        self.assertEqual(first['snapshot_sha256'], second['snapshot_sha256'])
        b.write_text('b=3')
        self.assertNotEqual(first['snapshot_sha256'], source_snapshot(root=self.root, paths=['backend/a.py', 'backend/b.py'])['snapshot_sha256'])

    def test_snapshot_can_run_from_extracted_source_without_git(self):
        (self.root / 'backend/app.py').write_text('app = 1')
        (self.root / 'local/docs/private.json').write_text('{}')
        result = source_snapshot(root=self.root)
        self.assertEqual(set(result['files_sha256']), {'backend/app.py'})

    def test_missing_internal_benchmark_is_explicitly_skipped_without_database_access(self):
        with patch('scripts.rehearse_project.ROOT', self.root):
            result = performance_evidence()
        self.assertTrue(result['skipped'])
        self.assertFalse(result['timings_rerun'])
        self.assertEqual(result['current_result_checks'], [])

    def test_snapshot_refuses_selected_path_escape(self):
        (self.parent / 'outside.py').write_text('outside=1')
        with self.assertRaises(ValueError):source_snapshot(root=self.root, paths=['backend/../../outside.py'])


if __name__ == '__main__':unittest.main()
