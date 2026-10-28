"""Profile all source rows without importing private/contact columns."""

from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etl.source import RAW, ROOT, SOURCES, date_value, iter_rows, normalized, source_sha256, vehicle_key


def inspect():
    report = {"inspected_at_utc": datetime.now(timezone.utc).isoformat(), "sources": {}}
    all_vehicles = set()
    vehicles_by_source = {}
    for name, (filename, width) in SOURCES.items():
        widths, products, decoding = Counter(), Counter(), Counter()
        identifiers, vehicles = Counter(), set()
        make_manufacturers = defaultdict(set)
        id_vehicles, id_components, id_manufacturers = defaultdict(set), defaultdict(set), defaultdict(set)
        dates, years = [], Counter()
        invalid_shape = eligible = invalid_dates = replacements = 0
        invalid_examples = []
        sample = []
        for number, row in iter_rows(name, decoding):
            widths[len(row)] += 1
            replacements += sum(value.count("\ufffd") for value in row)
            if len(row) != width:
                invalid_shape += 1
                if len(invalid_examples) < 5:
                    invalid_examples.append({"line": number, "field_count": len(row)})
                continue
            if name == "recalls":
                identifier, component, manufacturer, raw_date = row[1], row[6], row[7], row[15]
                products[row[10]] += 1
            elif name == "investigations":
                identifier, component, manufacturer, raw_date = row[0], row[4], row[5], row[6]
            else:
                identifier, component, manufacturer, raw_date = row[1], row[11], row[2], row[16]
                products[row[45]] += 1
            parsed_date = date_value(raw_date)
            if parsed_date:
                dates.append(parsed_date)
            elif raw_date.strip():
                invalid_dates += 1
            key = vehicle_key(row, name)
            if key is None:
                continue
            eligible += 1
            identifier = identifier.strip()
            identifiers[identifier] += 1
            vehicles.add(key)
            years[key[2]] += 1
            make_manufacturers[key[0]].add(normalized(manufacturer))
            id_vehicles[identifier].add(key)
            id_components[identifier].add(normalized(component))
            id_manufacturers[identifier].add(normalized(manufacturer))
            if len(sample) < 3:
                sample.append({"identifier": identifier, "make": key[0], "model": key[1],
                               "model_year": key[2], "component": component, "manufacturer": manufacturer})
        with zipfile.ZipFile(RAW / filename) as archive:
            members = [{"name": item.filename, "uncompressed_bytes": item.file_size}
                       for item in archive.infolist()]
        result = {
            "filename": filename, "sha256": source_sha256(name),
            "compressed_bytes": (RAW / filename).stat().st_size, "members": members,
            "expected_fields": width, "field_counts": dict(widths), "header": False,
            "delimiter": "TAB", "date_format": "YYYYMMDD", "invalid_shape_rows": invalid_shape,
            "invalid_shape_examples": invalid_examples, "replacement_characters": replacements,
            "decoding": dict(decoding),
            "total_rows": sum(widths.values()), "eligible_vehicle_rows": eligible,
            "excluded_rows": sum(widths.values()) - eligible, "product_types": dict(products),
            "distinct_identifiers": len(identifiers), "repeated_identifier_rows": eligible - len(identifiers),
            "identifiers_with_multiple_vehicles": sum(len(values) > 1 for values in id_vehicles.values()),
            "identifiers_with_multiple_components": sum(len(values) > 1 for values in id_components.values()),
            "identifiers_with_multiple_manufacturers": sum(len(values) > 1 for values in id_manufacturers.values()),
            "distinct_vehicles": len(vehicles), "min_model_year": min(years, default=None),
            "max_model_year": max(years, default=None),
            "min_source_date": str(min(dates)) if dates else None,
            "max_source_date": str(max(dates)) if dates else None,
            "invalid_nonblank_dates": invalid_dates,
            "makes_with_multiple_manufacturers": sum(len(values) > 1 for values in make_manufacturers.values()),
            "safe_samples": sample,
        }
        report["sources"][name] = result
        vehicles_by_source[name] = vehicles
        all_vehicles.update(vehicles)
        print(f"{name}: {result['total_rows']:,} rows; {eligible:,} eligible; "
              f"{len(identifiers):,} identifiers; {len(vehicles):,} vehicles", flush=True)
    recalls = vehicles_by_source["recalls"]
    complaints = vehicles_by_source["complaints_2020_2024"] | vehicles_by_source["complaints_2025_2026"]
    report["catalogue"] = {"distinct_vehicles": len(all_vehicles),
                           "complaint_vehicles_without_recall": len(complaints - recalls)}
    target = ROOT / "docs" / "data_profile.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Profile written to {target.relative_to(ROOT)}")


if __name__ == "__main__":
    inspect()
