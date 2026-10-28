"""Create a new source/data/manual ZIP without credentials or local environments."""
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etl.source import RAW, SOURCES
from project_config import ROOT


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def safe_project_file(relative):
    name = PurePosixPath(relative)
    parts = tuple(part.lower() for part in name.parts)
    if (name.is_absolute() or ".." in name.parts or
            any(part in {".git", ".venv", "__pycache__", ".env"} for part in parts) or
            (name.name.lower().startswith(".env") and name.name.lower() != ".env.example") or
            (len(parts) > 1 and parts[0] == "data" and parts[1] in {"runtime", "logs", "staging", "processed"}) or
            name.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}):
        raise ValueError(f"Unsafe package path: {relative}")
    path = ROOT.joinpath(*name.parts)
    if path.is_symlink() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError(f"External or linked path cannot be packaged: {relative}")
    return path


def main():
    # Include tracked and non-ignored untracked code, so an uncommitted review
    # checkout can be packaged without adding secrets or environments to Git.
    listing = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                             cwd=ROOT, check=True, capture_output=True).stdout.decode("utf-8")
    names = {name.replace("\\", "/") for name in listing.split("\0") if name}
    for filename, _width in SOURCES.values():
        path = RAW / filename
        if not path.is_file():
            raise RuntimeError(f"Missing required source archive: {filename}")
        names.add(path.relative_to(ROOT).as_posix())
    names.update(path.relative_to(ROOT).as_posix() for path in RAW.glob("download-manifest-*.json"))
    results = ROOT / "benchmarks" / "results"
    if results.exists():
        names.update(path.relative_to(ROOT).as_posix() for path in results.glob("*.json"))
    verification = ROOT / "verification" / "results"
    if verification.exists():
        names.update(path.relative_to(ROOT).as_posix() for path in verification.glob("*.json"))
    files = [(name, safe_project_file(name)) for name in sorted(names)]
    files = [(name, path) for name, path in files if path.is_file()]
    if "docs/USER_MANUAL.md" not in {name for name, _ in files}:
        raise RuntimeError("The user manual is missing from the package")
    output = ROOT / "submission"
    output.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    archive_path = output / f"vehicle-safety-source-{stamp}-{uuid4().hex[:8]}.zip"
    manifest = {"createdAtUtc": datetime.now(timezone.utc).isoformat(), "files": []}
    with zipfile.ZipFile(archive_path, "x", allowZip64=True) as archive:
        for name, path in files:
            manifest["files"].append({"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)})
            method = zipfile.ZIP_STORED if name.lower().endswith(".zip") else zipfile.ZIP_DEFLATED
            archive.write(path, name, compress_type=method)
        archive.writestr("PACKAGE_MANIFEST.json", json.dumps(manifest, indent=2), compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(archive_path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"Archive validation failed for {bad}; inspect {archive_path}")
    print(f"Created and checked {archive_path.relative_to(ROOT)} ({len(files)} files, {archive_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
