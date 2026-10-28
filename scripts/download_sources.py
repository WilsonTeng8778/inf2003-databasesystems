"""Download the four approved NHTSA archives without replacing existing files."""
import argparse
import hashlib
import json
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etl.source import RAW, SOURCES

URLS = {
    "recalls": "https://static.nhtsa.gov/odi/ffdd/rcl/FLAT_RCL_POST_2010.zip",
    "investigations": "https://static.nhtsa.gov/odi/ffdd/inv/FLAT_INV.zip",
    "complaints_2020_2024": "https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2020-2024.zip",
    "complaints_2025_2026": "https://static.nhtsa.gov/odi/ffdd/cmpl/COMPLAINTS_RECEIVED_2025-2026.zip",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(key, url):
    name = SOURCES[key][0]
    destination = RAW / name
    if destination.exists():
        print(f"Keeping existing {name}", flush=True)
        return {"dataset": key, "filename": name, "url": url, "bytes": destination.stat().st_size,
                "sha256": digest(destination), "action": "existing"}
    temporary = RAW / f".{name}.{uuid4().hex}.part"
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "INF2003-VehicleSafety/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("xb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        with zipfile.ZipFile(temporary) as archive:
            members = [info for info in archive.infolist() if info.filename.lower().endswith(".txt")]
            if len(members) != 1:
                raise ValueError(f"{name} must contain exactly one text file")
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Integrity check failed for {name}")
        # A hard link is created only if the destination does not already exist.
        # It cannot replace a file another process created during the download.
        os.link(temporary, destination)
        entry = {"dataset": key, "filename": name, "url": url, "bytes": destination.stat().st_size,
                 "sha256": digest(destination), "action": "downloaded"}
        print(f"Downloaded and checked {name} ({entry['bytes']:,} bytes)", flush=True)
        return entry
    finally:
        if temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check source availability without downloading")
    args = parser.parse_args()
    if args.check:
        for key, url in URLS.items():
            request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "INF2003-VehicleSafety/1.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                print(f"{key}: HTTP {response.status}, content length {response.headers.get('Content-Length', 'unknown')}")
        return
    RAW.mkdir(parents=True, exist_ok=True)
    entries = [download(key, url) for key, url in URLS.items()]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest = RAW / f"download-manifest-{stamp}-{uuid4().hex[:8]}.json"
    manifest.write_text(json.dumps({"observedAtUtc": datetime.now(timezone.utc).isoformat(), "sources": entries}, indent=2), encoding="utf-8")
    print(f"Source manifest saved to {manifest.relative_to(RAW.parent.parent)}")


if __name__ == "__main__":
    main()
