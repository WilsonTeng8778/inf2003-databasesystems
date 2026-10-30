"""Build/verify a local source + approved raw data + manual review ZIP.

Verification uses only Python's standard library and never extracts the archive.
Building reads the working files, not Git HEAD, and never connects to a database.
"""

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = 'INF2003_Group19'
ROOT_FILES = {'.env.example', '.gitignore', 'AGENTS.md', 'README.md',
              'PROJECT_GUIDE.md', 'PROJECT_UNDERSTANDING_AND_PLAN.md', 'USER_MANUAL.md',
              'project_config.py', 'requirements.txt', 'requirements-evaluation.txt'}
SOURCE_DIRS = {'backend', 'etl', 'mongodb', 'sql', 'scripts', 'tests'}
CODE_SUFFIXES = {'.py', '.sql', '.mjs', '.js', '.css', '.html', '.svg'}
DOC_SUFFIXES = {'.md', '.json', '.txt', '.csv', '.png', '.svg'}
RAW_FILES = {'FLAT_RCL_POST_2010.zip', 'FLAT_INV.zip',
             'COMPLAINTS_RECEIVED_2020-2024.zip', 'COMPLAINTS_RECEIVED_2025-2026.zip'}
DICTIONARIES = {'RCL.txt', 'INV.txt', 'CMPL.txt'}
REQUIRED = ROOT_FILES | {'data/raw/' + name for name in RAW_FILES} | {
    'data/dictionaries/' + name for name in DICTIONARIES} | {
    'backend/__init__.py', 'etl/source.py', 'mongodb/schema.py', 'sql/schema.sql',
    'scripts/package_project.py', 'scripts/check_environment.py', 'docs/data_profile.json'}


def digest(stream):
    return hashlib.file_digest(stream, 'sha256').hexdigest()


def file_digest(path):
    with path.open('rb') as stream:
        return digest(stream)


def allowed(name):
    path = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or path.is_absolute() or path.as_posix() != name:
        return False
    if any(part in {'.', '..', '.git', '.venv', '__pycache__', 'node_modules'} for part in path.parts):
        return False
    if any(part.lower().startswith('.env') for part in path.parts):
        return name == '.env.example'
    if name in ROOT_FILES:
        return True
    if len(path.parts) < 2:
        return False
    if path.parts[0] in SOURCE_DIRS:
        return path.suffix in CODE_SUFFIXES
    if path.parts[0] == 'docs':
        return path.suffix in DOC_SUFFIXES
    return (name in {'data/raw/' + value for value in RAW_FILES}
            or name in {'data/dictionaries/' + value for value in DICTIONARIES})


def blank_template(content):
    for line in content.decode('utf-8-sig').splitlines():
        match = re.match(r'\s*([A-Z_]+)\s*=\s*(.*?)\s*$', line)
        if match and ('PASSWORD' in match[1] or 'SECRET' in match[1]):
            if match[2] not in {'', "''", '""'}:
                raise ValueError('The shareable configuration template must have empty passwords/signing key')


def private_values(root):
    # dotenv is needed only for building from an already configured checkout.
    if not (root / '.env').exists():
        return ()
    from dotenv import dotenv_values
    settings = dotenv_values(root / '.env', interpolate=False)
    return tuple(value.encode('utf-8') for key, value in settings.items()
                 if value and len(value) >= 12 and ('PASSWORD' in key or 'SECRET' in key))


def contains_private_value(stream, values):
    overlap = max(map(len, values), default=1) - 1
    tail = b''
    while chunk := stream.read(1024 * 1024):
        data = tail + chunk
        if any(value in data for value in values):
            return True
        tail = data[-overlap:] if overlap else b''
    return False


def collect_files(root):
    names = set(ROOT_FILES)
    for directory in sorted(SOURCE_DIRS | {'docs', 'data/raw', 'data/dictionaries'}):
        for path in (root / directory).rglob('*'):
            name = path.relative_to(root).as_posix()
            if path.is_file() and allowed(name):
                names.add(name)
    if missing := REQUIRED - names:
        raise ValueError('Required package files missing: ' + ', '.join(sorted(missing)))
    result = {}
    for name in sorted(names):
        path = root / name
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing or external package file: ' + name)
        if any(part.is_symlink() for part in [path, *path.parents] if part.is_relative_to(root)):
            raise ValueError('Package inputs must be ordinary files/directories: ' + name)
        result[name] = {'bytes': path.stat().st_size, 'sha256': file_digest(path)}
    return result


def validate_sources(files, profile):
    sources = profile['sources']
    if {value['filename'] for value in sources.values()} != RAW_FILES:
        raise ValueError('The data profile must identify the four approved archives')
    for value in sources.values():
        actual = files['data/raw/' + value['filename']]
        if actual['sha256'] != value['sha256']:
            raise ValueError('Raw archive differs from the approved snapshot: ' + value['filename'])


def validate_rehearsal(files, rehearsal, evidence_name):
    if not rehearsal.get('successful') or not rehearsal.get('tested_source_unchanged'):
        raise ValueError('A successful technical rehearsal is required')
    manifest = rehearsal['source_before']['files_sha256']
    changes = [name for name, expected in manifest.items()
               if name not in files or files[name]['sha256'] != expected]
    if changes:
        raise ValueError('Previously tested implementation changed; run a new rehearsal: ' + ', '.join(changes))
    added = sorted(name for name in files if PurePosixPath(name).parts[0] in SOURCE_DIRS and name not in manifest)
    return {'evidence': evidence_name, 'previously_tested_files_checked': len(manifest),
            'previously_tested_files_unchanged': True, 'additional_source_files': added,
            'qualification': 'Additional packaging tools/tests are checked separately; this does not renew the earlier application/browser run.'}


def select_rehearsal(root, files, requested=None):
    """Use explicit evidence or the newest successful run matching current source.

    Keeping a timestamp in the command's default would break packaging after a
    legitimate refactor, even once that new layout has passed its own rehearsal.
    No candidate is accepted by date alone: its recorded source must still match.
    """
    if requested is not None:
        candidates = [requested]
    else:
        candidates = sorted((path.relative_to(root).as_posix()
                             for path in (root / 'docs/rehearsals').glob('*/report.json')), reverse=True)
    for name in candidates:
        if not allowed(name) or not name.startswith('docs/rehearsals/') or name not in files:
            if requested is not None:
                raise ValueError('Choose an included rehearsal report under docs/rehearsals')
            continue
        try:
            report = json.loads((root / name).read_text(encoding='utf-8'))
            return validate_rehearsal(files, report, name)
        except (ValueError, KeyError, TypeError):
            if requested is not None:
                raise
    raise ValueError('No successful rehearsal matches the current source; run scripts/rehearse_project.py before exporting')


def verify_archive(path, *, secrets=()):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if len({entry.filename.casefold() for entry in entries}) != len(entries):
            raise ValueError('Duplicate or case-colliding ZIP members')
        manifest_name = PACKAGE_ROOT + '/PACKAGE_MANIFEST.json'
        manifest = json.loads(archive.read(manifest_name))
        if manifest['format_version'] != 1:
            raise ValueError('Unsupported package manifest version')
        files = manifest['files']
        if REQUIRED - files.keys() or any(not allowed(name) for name in files):
            raise ValueError('Missing required or forbidden package files')
        expected = {PACKAGE_ROOT + '/' + name for name in files} | {manifest_name}
        if {entry.filename for entry in entries} != expected:
            raise ValueError('ZIP members do not exactly match the manifest')
        for name, item in files.items():
            entry = archive.getinfo(PACKAGE_ROOT + '/' + name)
            if entry.is_dir() or entry.flag_bits & 1 or entry.file_size != item['bytes']:
                raise ValueError('Unexpected ZIP member metadata: ' + name)
            with archive.open(entry) as stream:
                if digest(stream) != item['sha256']:
                    raise ValueError('ZIP content hash mismatch: ' + name)
            if secrets:
                with archive.open(entry) as stream:
                    if contains_private_value(stream, secrets):
                        raise ValueError('Configured private value detected in a package file: ' + name)
        blank_template(archive.read(PACKAGE_ROOT + '/.env.example'))
        profile = json.loads(archive.read(PACKAGE_ROOT + '/docs/data_profile.json'))
        validate_sources(files, profile)
        evidence_name = manifest['technical_rehearsal']['evidence']
        if evidence_name not in files or not evidence_name.startswith('docs/rehearsals/'):
            raise ValueError('Missing technical evidence in the package')
        rehearsal = json.loads(archive.read(PACKAGE_ROOT + '/' + evidence_name))
        comparison = validate_rehearsal(files, rehearsal, evidence_name)
        if comparison != manifest['technical_rehearsal']:
            raise ValueError('Technical evidence comparison does not match the package')
    return {'successful': True, 'files_verified': len(files), 'raw_archives_verified': 4,
            'uncompressed_bytes': sum(item['bytes'] for item in files.values()),
            'sha256': file_digest(path), 'bytes': path.stat().st_size,
            'technical_rehearsal': comparison,
            'qualification': 'ZIP content/hash validation only; no fresh installation, import or browser run.'}


def build_package(*, root=ROOT, rehearsal=None, run_id=None):
    root = root.resolve()
    if rehearsal is not None and (not allowed(rehearsal) or not rehearsal.startswith('docs/rehearsals/')):
        raise ValueError('Choose a rehearsal report under docs/rehearsals')
    files = collect_files(root)
    profile = json.loads((root / 'docs/data_profile.json').read_text(encoding='utf-8'))
    validate_sources(files, profile)
    comparison = select_rehearsal(root, files, rehearsal)
    blank_template((root / '.env.example').read_bytes())
    secrets = private_values(root)
    for name in files:
        with (root / name).open('rb') as stream:
            if contains_private_value(stream, secrets):
                raise ValueError('Configured private value detected in a package file: ' + name)
    run_id = run_id or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid4().hex[:8]
    if not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Invalid package run ID')
    directory = root / 'data/processed/packages' / run_id
    if not directory.resolve().is_relative_to(root):
        raise ValueError('Package output must stay inside the workspace')
    directory.mkdir(parents=True, exist_ok=False)
    partial = directory / 'INF2003_Group19_Source_Data.zip.partial'
    manifest = {'format_version': 1, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'Local review candidate: source, approved raw data, dictionaries, manual and saved evidence. Not the outer final submission.',
                'files': files, 'technical_rehearsal': comparison}
    with zipfile.ZipFile(partial, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in files:
            archive.write(root / name, PACKAGE_ROOT + '/' + name,
                          compress_type=zipfile.ZIP_STORED if name.startswith('data/raw/') else zipfile.ZIP_DEFLATED)
        archive.writestr(PACKAGE_ROOT + '/PACKAGE_MANIFEST.json', json.dumps(manifest, indent=2) + '\n')
    result = verify_archive(partial, secrets=secrets)
    destination = partial.with_suffix('')
    partial.rename(destination)
    result.update({'created_at_utc': datetime.now(timezone.utc).isoformat(),
                   'archive': destination.relative_to(root).as_posix(),
                   'configured_long_secret_scan': {'minimum_characters': 12, 'values_checked': len(secrets), 'matches': 0},
                   'fresh_installation_verified': False, 'final_submission_complete': False})
    (directory / 'package_report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', type=Path, help='Read/verify an existing ZIP without extracting or using databases')
    parser.add_argument('--rehearsal', help='Explicit source-matching report; default selects the newest successful matching run')
    args = parser.parse_args(argv)
    try:
        result = verify_archive(args.verify) if args.verify else build_package(rehearsal=args.rehearsal)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print('Package check failed:', str(error))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
