"""Administrator-only import status and an explicit, fixed-command refresh."""

import subprocess
import sys
import threading

from flask import Blueprint, abort, jsonify

from backend.auth import json_fields, requires_roles
from backend.cases import pg
from backend.routes import query_fields
from etl.source import RAW, SOURCES
from project_config import ROOT

imports = Blueprint("imports", __name__, url_prefix="/api/admin/imports")
_lock = threading.Lock()
_process = None


@imports.get("")
@requires_roles("ADMIN")
def status():
    query_fields(set())
    rows = pg().execute("""SELECT dataset_name,started_at,completed_at,records_read,records_inserted,
        records_updated,records_skipped,records_rejected,status FROM data_import_log
        ORDER BY import_id DESC LIMIT 30""").fetchall()
    entries = [{"dataset": row[0], "startedAt": row[1].isoformat(),
                "completedAt": row[2].isoformat() if row[2] else None, "read": row[3],
                "inserted": row[4], "updated": row[5], "skipped": row[6], "rejected": row[7],
                "status": row[8]} for row in rows]
    return jsonify({"sources": [{"dataset": key, "filename": item[0], "available": (RAW / item[0]).is_file()}
                                 for key, item in SOURCES.items()],
                    "recentImports": entries,
                    "startedByThisServer": _process is not None and _process.poll() is None})


@imports.post("/run")
@requires_roles("ADMIN")
def run():
    global _process
    json_fields(set())
    missing = [item[0] for item in SOURCES.values() if not (RAW / item[0]).is_file()]
    if missing:
        abort(409, description="All four approved source archives must be present before importing")
    with _lock:
        if _process is not None and _process.poll() is None:
            abort(409, description="An import started by this server is still running")
        log_dir = ROOT / "data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        # The importer takes a PostgreSQL advisory lock, including across server processes.
        with (log_dir / "web-import.log").open("ab") as log:
            _process = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "import_all.py")],
                cwd=str(ROOT), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
    return jsonify({"message": "Import started. Refresh import status for the recorded result."}), 202
