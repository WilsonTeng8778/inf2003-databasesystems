"""Sign in as an application ADMIN and confirm an import of the approved local ZIPs.

This is an intentional local-operator command. It needs the project's trusted
setup credentials in ignored .env and the existing localhost Flask auth service.
There are no password, arbitrary archive path, download or unattended-import flags.
"""

import argparse
import getpass
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etl.runner import ImportBusy, import_lock, run_imports
from etl.source import RAW, SOURCES
from project_config import ROOT, mongo_client, mongo_database, postgres
from scripts.local_api import ApiError, LocalApi


class AdminImportDenied(ValueError):
    pass


class ImportCancelled(ValueError):
    pass


class SourceSnapshotMismatch(ValueError):
    pass


def approved_sources(*, raw=None, profile_path=None):
    raw = Path(raw) if raw is not None else RAW
    profile_path = Path(profile_path) if profile_path is not None else ROOT / 'docs/data_profile.json'
    try:
        profile = json.loads(profile_path.read_text(encoding='utf-8'))['sources']
        result = []
        for key, (filename, _) in SOURCES.items():
            expected = profile[key]
            if expected['filename'] != filename or not re.fullmatch('[0-9a-f]{64}', expected['sha256']):
                raise SourceSnapshotMismatch('The inspected source profile does not match the approved archive list.')
            path = raw / filename
            if not path.is_file() or not path.resolve().is_relative_to(raw.resolve()):
                raise SourceSnapshotMismatch('An approved local archive is missing or outside the raw-data folder: ' + filename)
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != expected['sha256']:
                raise SourceSnapshotMismatch('The local archive differs from the inspected snapshot: ' + filename)
            result.append({'dataset': key, 'filename': filename, 'sha256': actual, 'bytes': path.stat().st_size})
        return result
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise SourceSnapshotMismatch('The approved source files/profile are unavailable or invalid; review them before importing.') from None


def admin_identity(client):
    try:
        result = client.request('/api/auth/me')
    except ApiError as error:
        if error.status in (401, 403):
            raise AdminImportDenied('Sign in with an active application ADMIN account before importing.') from None
        raise
    user = result.get('user') if isinstance(result, dict) else None
    if not isinstance(user, dict) or user.get('role') != 'ADMIN' or type(user.get('userId')) is not int or user['userId'] <= 0:
        raise AdminImportDenied('This command requires the application ADMIN role.')
    return user['userId']


def run_authorized_import(client, confirm, *, preflight=None, pg_factory=None, mongo_factory=None, pipeline=None):
    """Dependencies can be replaced by isolated verification fixtures, never CLI flags."""
    preflight = preflight or approved_sources
    pg_factory = pg_factory or postgres
    mongo_factory = mongo_factory or mongo_client
    pipeline = pipeline or run_imports
    actor = admin_identity(client)
    reviewed = preflight()
    if not confirm(reviewed):
        raise ImportCancelled('Import cancelled before starting; no import stages were run.')
    with pg_factory() as connection:
        with import_lock(connection):
            # Confirmation and waiting for a lock can take time: use a fresh
            # session/role check and require the same actor immediately before ETL.
            if admin_identity(client) != actor:
                raise AdminImportDenied('The signed-in account changed; review and start again.')
            if preflight() != reviewed:
                raise SourceSnapshotMismatch('The source snapshot changed after confirmation; review and start again.')
            with mongo_factory() as mongo:
                pipeline(connection, mongo_database(mongo))
    return {'status': 'COMPLETED', 'actorId': actor, 'sources': reviewed}


def confirm_import(sources):
    print('Approved local archives (checked against the inspected SHA-256 fingerprints):')
    for source in sources:
        print(f"  {source['filename']} ({source['bytes']:,} bytes)\n    SHA-256: {source['sha256']}")
    print('This refreshes existing reference data using the current import rules. Users, saves, cases and fleets are retained.')
    print('Completed stages and MongoDB batches can remain if a later stage fails. Outcomes appear in Admin > Import history.')
    return input('Type IMPORT to start, or anything else to cancel: ').strip() == 'IMPORT'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5000', help='Localhost Flask origin; credentials are never sent to a remote host.')
    args = parser.parse_args(argv)
    client = None
    signed_in = False
    try:
        client = LocalApi(args.base_url)
        client.request('/api/auth/csrf')  # Check availability before prompting.
        email = input('Application email: ').strip()
        password = getpass.getpass('Application password (hidden): ')
        client.request('/api/auth/login', {'email': email, 'password': password}, method='POST')
        signed_in = True
        password = None
        result = run_authorized_import(client, confirm_import)
        print('Import completed. Review the per-dataset outcomes in Admin > Import history.')
        return 0
    except ImportCancelled as error:
        print(str(error))
        return 0
    except (AdminImportDenied, SourceSnapshotMismatch, ImportBusy) as error:
        print(str(error))
        return 1
    except ApiError as error:
        print('Application sign-in/access failed (HTTP ' + str(error.status) + '). Check the account and local server.')
        return 1
    except KeyboardInterrupt:
        print('Interrupted. Review import history before retrying; earlier committed stages or document batches may remain.')
        return 130
    except Exception as error:
        # Database/HTTP exception messages can contain source content or secrets.
        print('Import command failed (' + type(error).__name__ + '). Check the local services, source files and import history.')
        return 1
    finally:
        if signed_in:
            try:
                client.request('/api/auth/logout', {}, method='POST')
            except Exception:
                print('The helper could not confirm sign-out. Its application session will expire normally.')


if __name__ == '__main__':
    raise SystemExit(main())
