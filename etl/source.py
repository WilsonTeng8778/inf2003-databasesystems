"""Read unmodified NHTSA ZIPs; no contact, VIN or operator fields are emitted."""

from __future__ import annotations

import hashlib
import re
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SOURCES = {
    "recalls": ("FLAT_RCL_POST_2010.zip", 29),
    "investigations": ("FLAT_INV.zip", 11),
    "complaints_2020_2024": ("COMPLAINTS_RECEIVED_2020-2024.zip", 51),
    "complaints_2025_2026": ("COMPLAINTS_RECEIVED_2025-2026.zip", 51),
}


def normalized(value: str) -> str:
    """Conservative matching: uppercase and collapse whitespace, retain punctuation."""
    return " ".join(value.strip().upper().split())


def model_year(value: str) -> int | None:
    try:
        year = int(value)
        return year if 1900 <= year <= 2100 else None
    except ValueError:
        return None


def integer(value: str) -> int | None:
    try:
        number = int(value.strip())
        return number if number >= 0 else None
    except ValueError:
        return None


def date_value(value: str):
    value = value.strip()
    if not re.fullmatch(r"\d{8}", value):
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def flag(value: str) -> bool | None:
    return {"Y": True, "YES": True, "N": False, "NO": False}.get(normalized(value))


def vehicle_key(row: list[str], kind: str):
    if kind == "recalls":
        make, model, year = row[2], row[3], row[4]
        is_vehicle = normalized(row[10]) == "V"
    elif kind == "investigations":
        make, model, year = row[1], row[2], row[3]
        is_vehicle = True  # This layout has no product-type column.
    else:
        make, model, year = row[3], row[4], row[5]
        is_vehicle = normalized(row[45]) == "V"
    year = model_year(year)
    make, model = normalized(make), normalized(model)
    if not is_vehicle or year is None or not make or not model:
        return None
    return make, model, year


def iter_rows(source: str, decode_stats=None):
    """Yield (physical line number, fields). Source files are unquoted, headerless TSV.

    Decode as UTF-8 strictly first. A legacy Windows-1252 fallback is explicit
    per row; undefined CP1252 bytes are replaced and counted by the inspector.
    No CSV quote handling: quotation marks are literal narrative characters.
    """
    filename, _ = SOURCES[source]
    with zipfile.ZipFile(RAW / filename) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".txt")]
        if len(members) != 1:
            raise ValueError(f"Expected one .txt member in {filename}, found {members}")
        with archive.open(members[0]) as stream:
            for line_number, raw in enumerate(stream, 1):
                try:
                    line = raw.decode("utf-8")
                    if decode_stats is not None:
                        decode_stats["utf8_rows"] += 1
                except UnicodeDecodeError:
                    line = raw.decode("cp1252", errors="replace")
                    if decode_stats is not None:
                        decode_stats["cp1252_fallback_rows"] += 1
                yield line_number, line.rstrip("\r\n").split("\t")


def source_sha256(source: str) -> str:
    path = RAW / SOURCES[source][0]
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

