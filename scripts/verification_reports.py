"""Select new verification output files without replacing historical evidence."""

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

from project_config import ROOT


def validate_report_path(target, *, root=None):
    root = Path(root or ROOT).resolve()
    docs = (root / 'docs').resolve()
    path = Path(target)
    path = (path if path.is_absolute() else root / path).resolve()
    if not docs.is_relative_to(root) or not path.is_relative_to(docs) or path.suffix.lower() != '.json':
        raise ValueError('Verification output must be a new JSON file inside this repository docs folder')
    if path.exists():
        raise FileExistsError('Retain historical evidence; select a new verification output path')
    return path


def select_report_path(kind, argv=None):
    parser = argparse.ArgumentParser(description='Run native checks and preserve dated verification evidence.')
    parser.add_argument('--report-path', help='A new JSON path under docs; existing files are never overwritten.')
    args = parser.parse_args(argv)
    if args.report_path:
        target = args.report_path
    else:
        run_id = datetime.now(ZoneInfo('Asia/Kuala_Lumpur')).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
        target = ROOT / 'docs/verifications' / kind / run_id / 'report.json'
    path = validate_report_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
