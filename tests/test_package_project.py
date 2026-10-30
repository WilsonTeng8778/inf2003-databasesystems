"""Exercise exported ZIP contents, private-file exclusion and integrity failures."""

import io
import json
import shutil
import unittest
import zipfile
from unittest.mock import patch
from uuid import uuid4

from scripts import package_project as package


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.parent = (package.ROOT / 'data/logs' / ('package-unit-' + uuid4().hex)).resolve()
        self.root = self.parent / 'repo'
        self.root.mkdir(parents=True)
        for name in package.REQUIRED:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('fixture\n', encoding='utf-8')
        (self.root / '.env.example').write_text('POSTGRES_PASSWORD=\nFLASK_SECRET_KEY=\n')
        profile = {'sources': {str(index): {'filename': name, 'sha256': package.file_digest(self.root / 'data/raw' / name)}
                               for index, name in enumerate(sorted(package.RAW_FILES))}}
        (self.root / 'docs/data_profile.json').write_text(json.dumps(profile))
        self.evidence = self.root / package.REFERENCE
        self.evidence.parent.mkdir(parents=True)
        self.evidence.write_text(json.dumps({'successful': True, 'tested_source_unchanged': True,
            'source_before': {'files_sha256': {'backend/__init__.py': package.file_digest(self.root / 'backend/__init__.py')}}}))

    def tearDown(self):
        expected = (package.ROOT / 'data/logs').resolve()
        if not self.parent.is_relative_to(expected) or not self.parent.name.startswith('package-unit-'):
            raise AssertionError('Unexpected package fixture cleanup target')
        shutil.rmtree(self.parent)

    def build(self, run_id='fixture'):
        return package.build_package(root=self.root, run_id=run_id)

    def test_round_trip_includes_required_data_and_untracked_code_but_excludes_private_files(self):
        for name in ['.env', '.git/config', '.venv/secret.py', 'data/staging/database.sqlite',
                     'data/logs/browser-profile/cookies', 'backend/.env', 'docs/private/.env.json',
                     'backend/__pycache__/app.pyc']:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('PRIVATE_FIXTURE')
        extra = self.root / 'backend/new_feature.py'; extra.write_text('feature = 1\n')
        with patch.object(package, 'private_values', return_value=()):
            result = self.build()
        path = self.root / result['archive']
        checked = package.verify_archive(path)
        self.assertTrue(checked['successful'])
        with zipfile.ZipFile(path) as archive:
            members = set(archive.namelist())
            self.assertIn(package.PACKAGE_ROOT + '/backend/new_feature.py', members)
            self.assertIn(package.PACKAGE_ROOT + '/USER_MANUAL.md', members)
            self.assertFalse(any('PRIVATE_FIXTURE' in archive.read(name).decode(errors='ignore') for name in members))
        self.assertFalse(result['fresh_installation_verified'])
        self.assertEqual(result['raw_archives_verified'], 4)

    def test_unlisted_member_and_modified_content_are_rejected(self):
        result = self.build(); path = self.root / result['archive']
        with zipfile.ZipFile(path, 'a') as archive:
            archive.writestr(package.PACKAGE_ROOT + '/.env', 'DO_NOT_SHARE')
        with self.assertRaisesRegex(ValueError, 'exactly match'):
            package.verify_archive(path)
        result = self.build('second'); original = self.root / result['archive']
        tampered = self.parent / 'changed.zip'
        with zipfile.ZipFile(original) as source, zipfile.ZipFile(tampered, 'x') as target:
            for info in source.infolist():
                data = source.read(info)
                if info.filename.endswith('/README.md'): data = b'changed\n'
                target.writestr(info.filename, data)
        with self.assertRaises(ValueError): package.verify_archive(tampered)

    def test_changed_raw_snapshot_or_tested_source_blocks_export(self):
        raw = self.root / 'data/raw/FLAT_INV.zip'; original = raw.read_bytes()
        raw.write_bytes(b'different snapshot')
        with self.assertRaisesRegex(ValueError, 'approved snapshot'): self.build()
        raw.write_bytes(original)
        (self.root / 'backend/__init__.py').write_text('changed application')
        with self.assertRaisesRegex(ValueError, 'Previously tested implementation changed'): self.build()

    def test_missing_dictionary_blocks_export(self):
        (self.root / 'data/dictionaries/CMPL.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'Required package files missing'): self.build()

    def test_filled_template_and_configured_secret_in_document_block_export(self):
        template = self.root / '.env.example'
        template.write_text('POSTGRES_PASSWORD=fixture-do-not-share\n')
        with self.assertRaisesRegex(ValueError, 'empty passwords'): self.build()
        template.write_text('POSTGRES_PASSWORD=\n')
        value = b'UNIQUE_PRIVATE_FIXTURE_TOKEN'
        (self.root / 'docs/accidental.txt').write_bytes(value)
        with patch.object(package, 'private_values', return_value=(value,)):
            with self.assertRaisesRegex(ValueError, 'private value detected'): self.build()

    def test_no_existing_package_is_overwritten(self):
        result = self.build(); path = self.root / result['archive']; expected = package.file_digest(path)
        with self.assertRaises(FileExistsError): self.build()
        self.assertEqual(package.file_digest(path), expected)

    def test_secret_spanning_stream_chunks_is_detected(self):
        value = b'PRIVATE_FIXTURE_TOKEN'
        content = b'x' * (1024 * 1024 - 4) + value + b'y'
        self.assertTrue(package.contains_private_value(io.BytesIO(content), (value,)))

    def test_paths_reject_traversal_runtime_and_private_configuration(self):
        for name in ['../README.md', '/README.md', 'C:/README.md', 'docs/../.env',
                     'docs\\README.md', 'backend/.env.py', 'backend/.venv/code.py',
                     'data/logs/profile.json', 'data/raw/unapproved.zip']:
            self.assertFalse(package.allowed(name), name)


if __name__ == '__main__':
    unittest.main()
