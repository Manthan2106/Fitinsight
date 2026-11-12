"""Stream and validate the original FitInsight CSV files using the stdlib."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
EVIDENCE_DIR = ROOT / "reports" / "evidence" / "P1"

SPECS = {
    "dailyActivity_merged.csv": (["Id", "ActivityDate"], "ActivityDate"),
    "heartrate_seconds_merged.csv": (["Id", "Time"], "Time"),
    "hourlyCalories_merged.csv": (["Id", "ActivityHour"], "ActivityHour"),
    "hourlyIntensities_merged.csv": (["Id", "ActivityHour"], "ActivityHour"),
    "hourlySteps_merged.csv": (["Id", "ActivityHour"], "ActivityHour"),
    "minuteCaloriesNarrow_merged.csv": (["Id", "ActivityMinute"], "ActivityMinute"),
    "minuteIntensitiesNarrow_merged.csv": (["Id", "ActivityMinute"], "ActivityMinute"),
    "minuteMETsNarrow_merged.csv": (["Id", "ActivityMinute"], "ActivityMinute"),
    "minuteSleep_merged.csv": (["Id", "date", "logId"], "date"),
    "minuteStepsNarrow_merged.csv": (["Id", "ActivityMinute"], "ActivityMinute"),
    "weightLogInfo_merged.csv": (["Id", "LogId"], "Date"),
}

DATE_FORMATS = (
    "%m/%d/%Y",
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
)


def parse_datetime(value: str) -> datetime | None:
    """Parse the observed Fitbit date/time formats without guessing locale."""
    value = value.strip()
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format)
        except ValueError:
            continue
    return None


def value_kind(value: str) -> str:
    """Infer a simple storage kind for one non-empty CSV value."""
    text = value.strip()
    if text.lower() in {"true", "false"}:
        return "boolean"
    try:
        int(text)
        return "integer"
    except ValueError:
        pass
    try:
        float(text)
        return "number"
    except ValueError:
        return "string"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_file(path: Path) -> dict[str, Any]:
    key_fields, date_field = SPECS[path.name]
    type_counts: dict[str, Counter[str]] = {}
    null_counts: Counter[str] = Counter()
    participants: set[str] = set()
    seen_keys: set[bytes] = set()
    duplicate_keys = 0
    missing_key_rows = 0
    malformed_rows = 0
    date_min: datetime | None = None
    date_max: datetime | None = None
    invalid_dates = 0
    rows = 0

    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError(f"{path.name}: missing CSV header")
        if not set(key_fields).issubset(columns):
            raise ValueError(f"{path.name}: key fields absent: {key_fields}")
        if date_field not in columns:
            raise ValueError(f"{path.name}: date field absent: {date_field}")

        for row in reader:
            rows += 1
            if None in row or any(value is None for value in row.values()):
                malformed_rows += 1
            for column in columns:
                value = row.get(column)
                if value is None or not value.strip():
                    null_counts[column] += 1
                    continue
                type_counts.setdefault(column, Counter())[value_kind(value)] += 1
            participant = row.get("Id")
            if participant:
                participants.add(participant.strip())

            key_values = [row.get(field, "").strip() for field in key_fields]
            if not all(key_values):
                missing_key_rows += 1
            else:
                encoded = "\x1f".join(key_values).encode("utf-8")
                key = hashlib.blake2b(encoded, digest_size=16).digest()
                if key in seen_keys:
                    duplicate_keys += 1
                else:
                    seen_keys.add(key)

            raw_date = row.get(date_field, "")
            parsed_date = parse_datetime(raw_date) if raw_date else None
            if parsed_date is None:
                invalid_dates += 1
            else:
                date_min = parsed_date if date_min is None else min(date_min, parsed_date)
                date_max = parsed_date if date_max is None else max(date_max, parsed_date)

    schema = []
    for column in columns:
        kinds = type_counts.get(column, Counter())
        if column == date_field:
            inferred = "datetime"
        elif not kinds:
            inferred = "empty"
        elif set(kinds).issubset({"integer", "number"}):
            inferred = "number" if "number" in kinds else "integer"
        elif len(kinds) == 1:
            inferred = next(iter(kinds))
        else:
            inferred = "mixed"
        schema.append({"column": column, "inferred_type": inferred, "null_count": null_counts[column]})

    return {
        "file": f"data/raw/{path.name}",
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "rows": rows,
        "columns": len(columns),
        "schema": schema,
        "participant_count": len(participants),
        "date_column": date_field,
        "date_min": date_min.isoformat(sep=" ") if date_min else None,
        "date_max": date_max.isoformat(sep=" ") if date_max else None,
        "invalid_date_rows": invalid_dates,
        "key_fields": key_fields,
        "duplicate_key_rows": duplicate_keys,
        "missing_key_rows": missing_key_rows,
        "malformed_rows": malformed_rows,
        "checks": {
            "header_present": bool(columns),
            "key_fields_present": set(key_fields).issubset(columns),
            "row_width": malformed_rows == 0,
            "keys_complete": missing_key_rows == 0,
            "dates_parse": invalid_dates == 0,
        },
    }


def main() -> int:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for filename in SPECS:
        path = RAW_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Required raw CSV is missing: {path}")
        result = audit_file(path)
        results.append(result)
        print(
            f"Audited {filename}: {result['rows']:,} rows, "
            f"{result['participant_count']} participants, "
            f"{result['duplicate_key_rows']:,} duplicate keys"
        )

    inventory_path = EVIDENCE_DIR / "dataset_audit.csv"
    with inventory_path.open("w", encoding="utf-8", newline="") as stream:
        fields = [
            "file", "bytes", "sha256", "rows", "columns", "participant_count",
            "date_column", "date_min", "date_max", "invalid_date_rows",
            "key_fields", "duplicate_key_rows", "missing_key_rows",
            "malformed_rows", "checks",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for result in results:
            writer.writerow({
                **{key: result[key] for key in fields if key in result},
                "key_fields": "|".join(result["key_fields"]),
                "checks": json.dumps(result["checks"], sort_keys=True),
            })

    columns_path = EVIDENCE_DIR / "column_inventory.csv"
    with columns_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["file", "column", "inferred_type", "null_count", "rows"],
            lineterminator="\n",
        )
        writer.writeheader()
        for result in results:
            for column in result["schema"]:
                writer.writerow({
                    "file": result["file"],
                    **column,
                    "rows": result["rows"],
                })

    manifest = {
        "command": "python src/data_audit.py",
        "python": __import__("sys").version.split()[0],
        "input_files": [result["file"] for result in results],
        "results": results,
        "inventory": "reports/evidence/P1/dataset_audit.csv",
        "column_inventory": "reports/evidence/P1/column_inventory.csv",
    }
    manifest_path = EVIDENCE_DIR / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    all_checks = all(all(result["checks"].values()) for result in results)
    total_rows = sum(result["rows"] for result in results)
    total_bytes = sum(result["bytes"] for result in results)
    print(
        f"FITINSIGHT_PROOF | P1-DATA-AUDIT | STATUS={'PASS' if all_checks else 'FAIL'}\n"
        f"COMMAND: python src/data_audit.py\n"
        f"INPUT: {len(results)} raw CSVs; {total_rows:,} rows; {total_bytes:,} bytes\n"
        f"OUTPUT: per-file schemas, types, null counts, participant counts, date coverage, "
        f"key duplicates, and SHA-256 hashes\n"
        f"CHECKS: headers/key fields/row widths/key completeness/date parsing="
        f"{'PASS' if all_checks else 'FAIL'}\n"
        f"ARTIFACTS: {inventory_path.relative_to(ROOT)}; "
        f"{columns_path.relative_to(ROOT)}; {manifest_path.relative_to(ROOT)}\n"
        f"LIMITATION: type inference is lexical; field units and source semantics require "
        f"documentation review."
    )
    return 0 if all_checks else 1


if __name__ == "__main__":
    raise SystemExit(main())
