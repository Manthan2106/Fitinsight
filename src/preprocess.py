"""Reproducible, streaming preprocessing for the six FitInsight exports."""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import re
import subprocess
import sys
from collections import Counter
from contextlib import ExitStack, contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
REFERENCE_DIR = ROOT / "data" / "processed"
OUTPUT_DIR = ROOT / "reports" / "generated" / "preprocessed"
EVIDENCE_DIR = ROOT / "reports" / "evidence" / "P2"
SENTINEL = object()

DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")
TIMESTAMP_FORMATS = (
    "%m/%d/%Y %I:%M:%S %p",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)

RAW_SCHEMAS = {
    "dailyActivity_merged.csv": [
        "id", "activity_date", "total_steps", "total_distance", "tracker_distance",
        "logged_activities_distance", "very_active_distance",
        "moderately_active_distance", "light_active_distance",
        "sedentary_active_distance", "very_active_minutes",
        "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
        "calories",
    ],
    "minuteSleep_merged.csv": ["id", "date", "value", "log_id"],
    "weightLogInfo_merged.csv": [
        "id", "date", "weight_kg", "weight_pounds", "fat", "bmi",
        "is_manual_report", "log_id",
    ],
    "hourlyCalories_merged.csv": ["id", "activity_hour", "calories"],
    "hourlyIntensities_merged.csv": [
        "id", "activity_hour", "total_intensity", "average_intensity",
    ],
    "hourlySteps_merged.csv": ["id", "activity_hour", "step_total"],
    "minuteCaloriesNarrow_merged.csv": ["id", "activity_minute", "calories"],
    "minuteIntensitiesNarrow_merged.csv": ["id", "activity_minute", "intensity"],
    "minuteMETsNarrow_merged.csv": ["id", "activity_minute", "mets"],
    "minuteStepsNarrow_merged.csv": ["id", "activity_minute", "steps"],
    "heartrate_seconds_merged.csv": ["id", "time", "value"],
}

OUTPUTS = {
    "daily_activity": {
        "file": "daily_activity_clean.csv",
        "raw_files": ["dailyActivity_merged.csv"],
        "columns": RAW_SCHEMAS["dailyActivity_merged.csv"] + [
            "total_recorded_minutes", "is_complete_day", "component_distance_sum",
            "distance_discrepancy",
        ],
        "keys": ["id", "activity_date"],
        "range_field": "activity_date",
        "types": {
            "id": "string", "activity_date": "date", "total_steps": "integer",
            "total_distance": "number", "tracker_distance": "number",
            "logged_activities_distance": "number", "very_active_distance": "number",
            "moderately_active_distance": "number", "light_active_distance": "number",
            "sedentary_active_distance": "number", "very_active_minutes": "integer",
            "fairly_active_minutes": "integer", "lightly_active_minutes": "integer",
            "sedentary_minutes": "integer", "calories": "integer",
            "total_recorded_minutes": "integer", "is_complete_day": "boolean",
            "component_distance_sum": "number", "distance_discrepancy": "boolean",
        },
        "numeric": {
            "total_steps", "total_distance", "tracker_distance",
            "logged_activities_distance", "very_active_distance",
            "moderately_active_distance", "light_active_distance",
            "sedentary_active_distance", "very_active_minutes",
            "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
            "calories", "total_recorded_minutes", "component_distance_sum",
        },
    },
    "minute_sleep": {
        "file": "minute_sleep_clean.csv",
        "raw_files": ["minuteSleep_merged.csv"],
        "columns": ["id", "date", "value", "log_id", "calendar_date"],
        "keys": ["id", "log_id", "date"],
        "range_field": "date",
        "types": {
            "id": "string", "date": "datetime", "value": "integer",
            "log_id": "string", "calendar_date": "date",
        },
        "numeric": {"value"},
    },
    "weight": {
        "file": "weight_clean.csv",
        "raw_files": ["weightLogInfo_merged.csv"],
        "columns": [
            "id", "date", "weight_kg", "weight_pounds", "bmi",
            "is_manual_report", "log_id",
        ],
        "keys": ["id", "log_id"],
        "range_field": "date",
        "types": {
            "id": "string", "date": "datetime", "weight_kg": "number",
            "weight_pounds": "number", "bmi": "number",
            "is_manual_report": "boolean", "log_id": "string",
        },
        "numeric": {"weight_kg", "weight_pounds", "bmi"},
    },
    "hourly_activity": {
        "file": "hourly_activity_clean.csv",
        "raw_files": [
            "hourlyCalories_merged.csv", "hourlyIntensities_merged.csv",
            "hourlySteps_merged.csv",
        ],
        "columns": [
            "id", "activity_hour", "calories", "date", "total_intensity",
            "average_intensity", "step_total",
        ],
        "keys": ["id", "activity_hour"],
        "range_field": "activity_hour",
        "types": {
            "id": "string", "activity_hour": "datetime", "calories": "integer",
            "date": "date", "total_intensity": "integer",
            "average_intensity": "number", "step_total": "integer",
        },
        "numeric": {"calories", "total_intensity", "average_intensity", "step_total"},
    },
    "minute_activity": {
        "file": "minute_activity_clean.csv",
        "raw_files": [
            "minuteCaloriesNarrow_merged.csv", "minuteIntensitiesNarrow_merged.csv",
            "minuteMETsNarrow_merged.csv", "minuteStepsNarrow_merged.csv",
        ],
        "columns": [
            "id", "activity_minute", "calories", "date", "intensity", "mets", "steps",
        ],
        "keys": ["id", "activity_minute"],
        "range_field": "activity_minute",
        "types": {
            "id": "string", "activity_minute": "datetime", "calories": "number",
            "date": "date", "intensity": "integer", "mets": "integer",
            "steps": "integer",
        },
        "numeric": {"calories", "intensity", "mets", "steps"},
    },
    "heartrate": {
        "file": "heartrate_seconds_clean.csv",
        "raw_files": ["heartrate_seconds_merged.csv"],
        "columns": ["id", "time", "heart_rate", "date", "hour"],
        "keys": ["id", "time"],
        "range_field": "time",
        "types": {
            "id": "string", "time": "datetime", "heart_rate": "integer",
            "date": "date", "hour": "integer",
        },
        "numeric": {"heart_rate", "hour"},
    },
}

ALIGNMENT_GROUPS = {
    "hourly": {
        "files": [
            "hourlyCalories_merged.csv",
            "hourlyIntensities_merged.csv",
            "hourlySteps_merged.csv",
        ],
        "keys": ["id", "activity_hour"],
    },
    "minute": {
        "files": [
            "minuteCaloriesNarrow_merged.csv",
            "minuteIntensitiesNarrow_merged.csv",
            "minuteMETsNarrow_merged.csv",
            "minuteStepsNarrow_merged.csv",
        ],
        "keys": ["id", "activity_minute"],
    },
}


def normalize_column(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name.strip())
    name = name.lower()
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def normalize_columns(names: list[str]) -> list[str]:
    normalized = [normalize_column(name) for name in names]
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"Column normalization created duplicate headers: {normalized}")
    return normalized


@contextmanager
def normalized_csv(path: Path) -> Iterator[tuple[list[str], Iterator[dict[str, str]]]]:
    stream = path.open("r", encoding="utf-8-sig", newline="")
    try:
        reader = csv.reader(stream)
        try:
            raw_header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{path}: empty CSV has no header") from exc
        header = normalize_columns(raw_header)

        def rows() -> Iterator[dict[str, str]]:
            for line_number, values in enumerate(reader, start=2):
                if len(values) != len(header):
                    raise ValueError(
                        f"{path}: malformed row at line {line_number}; "
                        f"expected {len(header)} fields, found {len(values)}"
                    )
                yield dict(zip(header, values))

        yield header, rows()
    finally:
        stream.close()


def require_schema(actual: list[str], expected: list[str], path: Path) -> None:
    if actual != expected:
        raise ValueError(
            f"{path}: unexpected normalized schema\n"
            f"expected={expected}\nactual={actual}"
        )


def parse_date(value: str, field: str) -> datetime:
    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format)
        except ValueError:
            continue
    raise ValueError(f"Invalid date in {field}: {value!r}")


def parse_timestamp(value: str, field: str) -> datetime:
    for date_format in TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format)
        except ValueError:
            continue
    raise ValueError(f"Invalid timestamp in {field}: {value!r}")


def parse_number(
    value: str,
    field: str,
    *,
    integer: bool = False,
    nonnegative: bool = True,
) -> Decimal | None:
    if value.strip() == "":
        return None
    try:
        number = Decimal(value.strip())
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value in {field}: {value!r}") from exc
    if not number.is_finite():
        raise ValueError(f"Non-finite numeric value in {field}: {value!r}")
    if integer and number != number.to_integral_value():
        raise ValueError(f"Expected an integer in {field}: {value!r}")
    if nonnegative and number < 0:
        raise ValueError(f"Negative value in {field}: {value!r}")
    return number


def numeric_text(value: Decimal) -> str:
    return str(float(value))


def numpy_isclose(a: float, b: float, *, rtol: float = 1e-5, atol: float = 0.01) -> bool:
    """Match numpy.isclose(a, b, rtol=1e-5, atol=0.01) for finite values."""
    return abs(a - b) <= atol + rtol * abs(b)


def transform_daily(row: dict[str, str]) -> dict[str, str]:
    if not row["id"] or not row["activity_date"]:
        raise ValueError("Daily activity has an empty participant ID or date")
    row["activity_date"] = parse_date(row["activity_date"], "activity_date").date().isoformat()
    minute_fields = [
        "very_active_minutes", "fairly_active_minutes",
        "lightly_active_minutes", "sedentary_minutes",
    ]
    minute_values = [
        parse_number(row[field], field, integer=True) for field in minute_fields
    ]
    if any(value is None for value in minute_values):
        raise ValueError("Daily activity minute fields cannot be missing")
    total_minutes = sum(int(value) for value in minute_values if value is not None)
    distance_fields = [
        "very_active_distance", "moderately_active_distance",
        "light_active_distance", "sedentary_active_distance",
    ]
    distance_values = [
        parse_number(row[field], field) for field in distance_fields
    ]
    if any(value is None for value in distance_values):
        raise ValueError("Daily activity distance components cannot be missing")
    component_sum = sum(float(value) for value in distance_values if value is not None)
    total_distance = parse_number(row["total_distance"], "total_distance")
    if total_distance is None:
        raise ValueError("Daily total_distance cannot be missing")
    for field in (
        "total_steps", "calories", "tracker_distance",
        "logged_activities_distance",
    ):
        parse_number(
            row[field],
            field,
            integer=field in {"total_steps", "calories"},
        )
    return {
        **row,
        "total_recorded_minutes": str(total_minutes),
        "is_complete_day": str(total_minutes == 1440),
        "component_distance_sum": repr(component_sum),
        "distance_discrepancy": str(
            not numpy_isclose(float(total_distance), component_sum)
        ),
    }


class SleepDeduplicator:
    """Keep the first exact duplicate key; refuse conflicting key values."""

    def __init__(self) -> None:
        self.first_value_by_key: dict[tuple[str, str, str], str] = {}
        self.duplicate_occurrences = 0
        self.conflicting_keys: set[tuple[str, str, str]] = set()

    def keep(self, row: dict[str, str]) -> bool:
        key = (row["id"], row["log_id"], row["date"])
        if not all(key):
            raise ValueError("Sleep row has a missing (id, log_id, date) key")
        prior_value = self.first_value_by_key.get(key)
        if prior_value is None:
            self.first_value_by_key[key] = row["value"]
            return True
        self.duplicate_occurrences += 1
        if prior_value != row["value"]:
            self.conflicting_keys.add(key)
            raise ValueError(
                f"Conflicting values for repeated sleep key {key!r}; "
                "deduplication stopped without choosing a value"
            )
        return False


def transform_weight(row: dict[str, str]) -> dict[str, str]:
    if not row["id"] or not row["log_id"]:
        raise ValueError("Weight row has an empty participant or log ID")
    row["date"] = format_timestamp(parse_timestamp(row["date"], "date"))
    for field in ("weight_kg", "weight_pounds", "bmi"):
        parse_number(row[field], field)
    if row["is_manual_report"].strip().lower() not in {"true", "false"}:
        raise ValueError(f"Invalid boolean in is_manual_report: {row['is_manual_report']!r}")
    row["is_manual_report"] = (
        "True" if row["is_manual_report"].strip().lower() == "true" else "False"
    )
    row.pop("fat")
    return row


def format_timestamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S")


def transform_hourly(rows: list[dict[str, str]]) -> dict[str, str]:
    calories, intensities, steps = rows
    key = (calories["id"], calories["activity_hour"])
    if not all(key) or any(
        (row["id"], row["activity_hour"]) != key for row in rows[1:]
    ):
        raise ValueError(f"Hourly source keys do not match: {key!r}")
    timestamp = parse_timestamp(key[1], "activity_hour")
    parse_number(calories["calories"], "calories", integer=True)
    parse_number(intensities["total_intensity"], "total_intensity", integer=True)
    parse_number(intensities["average_intensity"], "average_intensity")
    parse_number(steps["step_total"], "step_total", integer=True)
    return {
        "id": key[0],
        "activity_hour": format_timestamp(timestamp),
        "calories": calories["calories"],
        "date": timestamp.date().isoformat(),
        "total_intensity": intensities["total_intensity"],
        "average_intensity": intensities["average_intensity"],
        "step_total": steps["step_total"],
    }


def transform_minute(rows: list[dict[str, str]]) -> dict[str, str]:
    calories, intensities, mets, steps = rows
    key = (calories["id"], calories["activity_minute"])
    if not all(key) or any(
        (row["id"], row["activity_minute"]) != key for row in rows[1:]
    ):
        raise ValueError(f"Minute source keys do not match: {key!r}")
    timestamp = parse_timestamp(key[1], "activity_minute")
    parse_number(calories["calories"], "calories")
    parse_number(intensities["intensity"], "intensity", integer=True)
    parse_number(mets["mets"], "mets", integer=True)
    parse_number(steps["steps"], "steps", integer=True)
    return {
        "id": key[0],
        "activity_minute": format_timestamp(timestamp),
        "calories": calories["calories"],
        "date": timestamp.date().isoformat(),
        "intensity": intensities["intensity"],
        "mets": mets["mets"],
        "steps": steps["steps"],
    }


def transform_heartrate(row: dict[str, str]) -> dict[str, str]:
    if not row["id"] or not row["time"]:
        raise ValueError("Heart-rate row has an empty participant ID or timestamp")
    timestamp = parse_timestamp(row["time"], "time")
    parse_number(row["value"], "heart_rate", integer=True)
    return {
        "id": row["id"],
        "time": format_timestamp(timestamp),
        "heart_rate": row["value"],
        "date": timestamp.date().isoformat(),
        "hour": str(timestamp.hour),
    }


def key_digest(values: tuple[str, ...]) -> bytes:
    encoded = "\x1f".join(values).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=16).digest()


def check_alignment(name: str, files: list[str], key_fields: list[str]) -> dict[str, Any]:
    input_counts = {filename: 0 for filename in files}
    mismatch_rows = 0
    length_mismatch_rows = 0
    missing_key_rows = 0
    duplicate_key_rows = 0
    seen_reference_keys: set[bytes] = set()
    mismatch_examples: list[dict[str, Any]] = []

    with ExitStack() as stack:
        readers = []
        for filename in files:
            path = RAW_DIR / filename
            if not path.is_file():
                raise FileNotFoundError(f"Missing required source: {path}")
            stream_context = normalized_csv(path)
            header, rows = stack.enter_context(stream_context)
            require_schema(header, RAW_SCHEMAS[filename], path)
            readers.append(rows)

        for position, row_group in enumerate(
            itertools.zip_longest(*readers, fillvalue=SENTINEL),
            start=1,
        ):
            real_rows = []
            for index, row in enumerate(row_group):
                if row is SENTINEL:
                    length_mismatch_rows += 1
                else:
                    input_counts[files[index]] += 1
                    real_rows.append((index, row))
            if len(real_rows) != len(files):
                continue
            keys = [tuple(row[field] for field in key_fields) for _, row in real_rows]
            if any(not all(key) for key in keys):
                missing_key_rows += 1
            if any(key != keys[0] for key in keys[1:]):
                mismatch_rows += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append({"position": position, "keys": keys})
            digest = key_digest(keys[0])
            if digest in seen_reference_keys:
                duplicate_key_rows += 1
            else:
                seen_reference_keys.add(digest)

    aligned = (
        mismatch_rows == 0
        and length_mismatch_rows == 0
        and missing_key_rows == 0
        and duplicate_key_rows == 0
    )
    return {
        "task": f"P2-ALIGN-{name.upper()}",
        "files": files,
        "key_fields": key_fields,
        "input_rows_by_file": input_counts,
        "rows_compared": min(input_counts.values(), default=0),
        "key_order_mismatch_rows": mismatch_rows,
        "length_mismatch_rows": length_mismatch_rows,
        "missing_key_rows": missing_key_rows,
        "duplicate_key_rows": duplicate_key_rows,
        "mismatch_examples": mismatch_examples,
        "aligned_and_unique": aligned,
    }


def aligned_rows(files: list[str], key_fields: list[str]) -> Iterator[list[dict[str, str]]]:
    with ExitStack() as stack:
        readers = []
        for filename in files:
            path = RAW_DIR / filename
            header, rows = stack.enter_context(normalized_csv(path))
            require_schema(header, RAW_SCHEMAS[filename], path)
            readers.append(rows)
        for position, row_group in enumerate(
            itertools.zip_longest(*readers, fillvalue=SENTINEL),
            start=1,
        ):
            if any(row is SENTINEL for row in row_group):
                raise ValueError(f"Source file lengths differ at row {position}")
            keys = [tuple(row[field] for field in key_fields) for row in row_group]
            if any(key != keys[0] for key in keys[1:]):
                raise ValueError(f"Source key order differs at row {position}: {keys!r}")
            yield row_group


def git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


class OutputAudit:
    def __init__(self, columns: list[str], keys: list[str], range_field: str):
        self.columns = columns
        self.keys = keys
        self.range_field = range_field
        self.rows = 0
        self.participants: set[str] = set()
        self.key_digests: set[bytes] = set()
        self.duplicate_key_rows = 0
        self.missing_key_rows = 0
        self.null_counts: Counter[str] = Counter()
        self.range_min: str | None = None
        self.range_max: str | None = None

    def add(self, row: dict[str, str]) -> None:
        self.rows += 1
        for column in self.columns:
            value = row.get(column, "")
            if value == "":
                self.null_counts[column] += 1
        participant = row.get("id", "")
        if participant:
            self.participants.add(participant)
        key = tuple(row.get(column, "") for column in self.keys)
        if not all(key):
            self.missing_key_rows += 1
        else:
            digest = key_digest(key)
            if digest in self.key_digests:
                self.duplicate_key_rows += 1
            else:
                self.key_digests.add(digest)
        date_value = row.get(self.range_field, "")
        if date_value:
            self.range_min = date_value if self.range_min is None else min(
                self.range_min, date_value
            )
            self.range_max = date_value if self.range_max is None else max(
                self.range_max, date_value
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows": self.rows,
            "columns": self.columns,
            "participants": len(self.participants),
            "range_field": self.range_field,
            "date_range": [self.range_min, self.range_max],
            "null_counts": dict(self.null_counts),
            "duplicate_key_rows": self.duplicate_key_rows,
            "missing_key_rows": self.missing_key_rows,
        }


def compare_values(expected: str, actual: str, numeric: bool) -> bool:
    if expected == actual:
        return True
    if not numeric or expected.strip() == "" or actual.strip() == "":
        return False
    try:
        return math.isclose(
            float(expected),
            float(actual),
            rel_tol=1e-12,
            abs_tol=1e-9,
        )
    except ValueError:
        return False


def compare_reference(
    generated_path: Path,
    reference_path: Path,
    columns: list[str],
    numeric_fields: set[str],
) -> dict[str, Any]:
    if not reference_path.is_file():
        return {"exists": False, "matches": False}
    mismatch_rows = 0
    mismatch_fields = 0
    generated_rows = 0
    reference_rows = 0
    examples: list[dict[str, Any]] = []

    with generated_path.open("r", encoding="utf-8-sig", newline="") as generated, \
         reference_path.open("r", encoding="utf-8-sig", newline="") as reference:
        generated_reader = csv.reader(generated)
        reference_reader = csv.reader(reference)
        generated_header = next(generated_reader, [])
        reference_header = next(reference_reader, [])
        schema_matches = generated_header == columns and reference_header == columns
        if not schema_matches:
            return {
                "exists": True,
                "schema_matches": False,
                "generated_columns": generated_header,
                "reference_columns": reference_header,
                "matches": False,
            }

        for row_number, (generated_row, reference_row) in enumerate(
            itertools.zip_longest(
                generated_reader,
                reference_reader,
                fillvalue=SENTINEL,
            ),
            start=1,
        ):
            if generated_row is not SENTINEL:
                generated_rows += 1
            if reference_row is not SENTINEL:
                reference_rows += 1
            if generated_row is SENTINEL or reference_row is SENTINEL:
                mismatch_rows += 1
                if len(examples) < 5:
                    examples.append({"row": row_number, "reason": "row_count"})
                continue

            row_has_mismatch = False
            if len(generated_row) != len(columns) or len(reference_row) != len(columns):
                row_has_mismatch = True
                mismatch_fields += 1
            else:
                for index, column in enumerate(columns):
                    if not compare_values(
                        reference_row[index],
                        generated_row[index],
                        column in numeric_fields,
                    ):
                        row_has_mismatch = True
                        mismatch_fields += 1
                        if len(examples) < 5:
                            examples.append({
                                "row": row_number,
                                "column": column,
                                "generated": generated_row[index],
                                "reference": reference_row[index],
                            })
            if row_has_mismatch:
                mismatch_rows += 1

    matches = (
        schema_matches
        and generated_rows == reference_rows
        and mismatch_rows == 0
    )
    return {
        "exists": True,
        "schema_matches": schema_matches,
        "generated_rows": generated_rows,
        "reference_rows": reference_rows,
        "mismatch_rows": mismatch_rows,
        "mismatch_fields": mismatch_fields,
        "examples": examples,
        "matches": matches,
        "numeric_tolerance": {"relative": 1e-12, "absolute": 1e-9},
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_dataset(
    name: str,
    rows: Iterator[dict[str, str]],
    input_counts: dict[str, int],
    rows_removed: int,
    *,
    sleep_deduplicator: SleepDeduplicator | None = None,
) -> dict[str, Any]:
    spec = OUTPUTS[name]
    output_path = OUTPUT_DIR / spec["file"]
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audit = OutputAudit(spec["columns"], spec["keys"], spec["range_field"])
    try:
        with temp_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=spec["columns"],
                extrasaction="raise",
                lineterminator="\n",
            )
            writer.writeheader()
            for row in rows:
                audit.add(row)
                writer.writerow(row)
        temp_path.replace(output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    reference = REFERENCE_DIR / spec["file"]
    comparison = compare_reference(
        output_path,
        reference,
        spec["columns"],
        spec["numeric"],
    )
    effective_rows_removed = rows_removed
    if sleep_deduplicator is not None:
        effective_rows_removed = sleep_deduplicator.duplicate_occurrences
    checks = {
        "columns_match_contract": audit.columns == spec["columns"],
        "keys_complete": audit.missing_key_rows == 0,
        "unique_output_keys": audit.duplicate_key_rows == 0,
        "reference_schema_matches": comparison.get("schema_matches", False),
        "reference_values_match": comparison.get("matches", False),
    }
    if sleep_deduplicator is not None:
        checks["no_conflicting_sleep_duplicates"] = (
            len(sleep_deduplicator.conflicting_keys) == 0
        )
    status = "PASS" if all(checks.values()) else "FAIL"
    metrics = {
        "task": f"P2-{name.upper()}",
        "status": status,
        "command": "python src/preprocess.py",
        "source_commit": git_revision(),
        "input_files": spec["raw_files"],
        "input_rows_by_file": input_counts,
        "input_rows_total": sum(input_counts.values()),
        "output_file": str(output_path.relative_to(ROOT)),
        "output": audit.as_dict(),
        "rows_removed": effective_rows_removed,
        "column_types": spec["types"],
        "checks": checks,
        "reference_file": str(reference.relative_to(ROOT)),
        "reference_comparison": comparison,
        "limitations": [
            "Source units are not independently verified.",
            "Composite-key uniqueness uses 16-byte BLAKE2b digests; collision risk is extremely small but nonzero.",
        ],
    }
    if sleep_deduplicator is not None:
        metrics["duplicate_occurrences_identical"] = (
            sleep_deduplicator.duplicate_occurrences
        )
        metrics["conflicting_duplicate_keys"] = len(sleep_deduplicator.conflicting_keys)
    evidence_path = EVIDENCE_DIR / name / "metrics.json"
    metrics["evidence_file"] = str(evidence_path.relative_to(ROOT))
    write_json(evidence_path, metrics)
    print_dataset_proof(metrics)
    return metrics


def print_dataset_proof(metrics: dict[str, Any]) -> None:
    output = metrics["output"]
    comparison = metrics["reference_comparison"]
    print(
        f"FITINSIGHT_PROOF | {metrics['task']} | STATUS={metrics['status']}\n"
        f"INPUT: {metrics['input_files']} rows={metrics['input_rows_by_file']}\n"
        f"METHOD: deterministic standard-library transform; sequential streaming\n"
        f"OUTPUT: {metrics['output_file']} rows={output['rows']} "
        f"columns={len(output['columns'])} participants={output['participants']} "
        f"dates={output['date_range']}\n"
        f"CHECKS: {metrics['checks']}; nulls={output['null_counts']}; "
        f"duplicate_keys={output['duplicate_key_rows']}; "
        f"missing_keys={output['missing_key_rows']}\n"
        f"DIFFERENCES: removed_rows={metrics['rows_removed']}; "
        f"reference_mismatch_rows={comparison.get('mismatch_rows', 'unknown')}; "
        f"reference_match={comparison.get('matches', False)}\n"
        f"ARTIFACT: {metrics['evidence_file']}\n"
        f"LIMITATION: source units are not independently verified."
    )


def process_daily() -> dict[str, Any]:
    path = RAW_DIR / "dailyActivity_merged.csv"
    counts = {path.name: 0}

    def rows() -> Iterator[dict[str, str]]:
        with normalized_csv(path) as (header, source_rows):
            require_schema(header, RAW_SCHEMAS[path.name], path)
            for row in source_rows:
                counts[path.name] += 1
                yield transform_daily(row)

    return write_dataset("daily_activity", rows(), counts, rows_removed=0)


def process_sleep() -> dict[str, Any]:
    path = RAW_DIR / "minuteSleep_merged.csv"
    counts = {path.name: 0}
    deduplicator = SleepDeduplicator()

    def rows() -> Iterator[dict[str, str]]:
        with normalized_csv(path) as (header, source_rows):
            require_schema(header, RAW_SCHEMAS[path.name], path)
            for row in source_rows:
                counts[path.name] += 1
                if not row["id"] or not row["log_id"]:
                    raise ValueError("Sleep record is missing id or log_id")
                timestamp = parse_timestamp(row["date"], "date")
                parse_number(row["value"], "value", integer=True)
                if not deduplicator.keep(row):
                    continue
                yield {
                    "id": row["id"],
                    "date": format_timestamp(timestamp),
                    "value": row["value"],
                    "log_id": row["log_id"],
                    "calendar_date": timestamp.date().isoformat(),
                }

    return write_dataset(
        "minute_sleep",
        rows(),
        counts,
        rows_removed=0,
        sleep_deduplicator=deduplicator,
    )


def process_weight() -> dict[str, Any]:
    path = RAW_DIR / "weightLogInfo_merged.csv"
    counts = {path.name: 0}

    def rows() -> Iterator[dict[str, str]]:
        with normalized_csv(path) as (header, source_rows):
            require_schema(header, RAW_SCHEMAS[path.name], path)
            for row in source_rows:
                counts[path.name] += 1
                yield transform_weight(row)

    return write_dataset("weight", rows(), counts, rows_removed=0)


def process_hourly(alignment: dict[str, Any]) -> dict[str, Any]:
    files = ALIGNMENT_GROUPS["hourly"]["files"]
    counts = alignment["input_rows_by_file"]
    return write_dataset(
        "hourly_activity",
        (transform_hourly(rows) for rows in aligned_rows(files, ["id", "activity_hour"])),
        counts,
        rows_removed=0,
    )


def process_minute(alignment: dict[str, Any]) -> dict[str, Any]:
    files = ALIGNMENT_GROUPS["minute"]["files"]
    counts = alignment["input_rows_by_file"]
    return write_dataset(
        "minute_activity",
        (transform_minute(rows) for rows in aligned_rows(files, ["id", "activity_minute"])),
        counts,
        rows_removed=0,
    )


def process_heartrate() -> dict[str, Any]:
    path = RAW_DIR / "heartrate_seconds_merged.csv"
    counts = {path.name: 0}

    def rows() -> Iterator[dict[str, str]]:
        with normalized_csv(path) as (header, source_rows):
            require_schema(header, RAW_SCHEMAS[path.name], path)
            for row in source_rows:
                counts[path.name] += 1
                yield transform_heartrate(row)

    return write_dataset("heartrate", rows(), counts, rows_removed=0)


def print_alignment_proof(metrics: dict[str, Any]) -> None:
    status = "PASS" if metrics["aligned_and_unique"] else "FAIL"
    path = EVIDENCE_DIR / "key_alignment" / f"{metrics['task'].lower()}.json"
    write_json(path, metrics)
    print(
        f"FITINSIGHT_PROOF | {metrics['task']} | STATUS={status}\n"
        f"INPUT: files={metrics['files']} rows={metrics['input_rows_by_file']}\n"
        f"METHOD: streaming key-by-key order and uniqueness validation\n"
        f"OUTPUT: rows_compared={metrics['rows_compared']}; "
        f"mismatched_keys={metrics['key_order_mismatch_rows']}; "
        f"length_mismatches={metrics['length_mismatch_rows']}\n"
        f"CHECKS: missing_keys={metrics['missing_key_rows']}; "
        f"duplicate_keys={metrics['duplicate_key_rows']}; "
        f"aligned_and_unique={metrics['aligned_and_unique']}\n"
        f"ARTIFACT: {path.relative_to(ROOT)}\n"
        f"LIMITATION: row-wise merge is permitted only for these verified source files."
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    alignments: dict[str, dict[str, Any]] = {}
    for name, group in ALIGNMENT_GROUPS.items():
        metrics = check_alignment(name, group["files"], group["keys"])
        alignments[name] = metrics
        print_alignment_proof(metrics)
        if not metrics["aligned_and_unique"]:
            print(f"STOP: {name} source keys are not safely row-alignable.")
            return 1

    processors = [
        process_daily,
        process_sleep,
        process_weight,
        lambda: process_hourly(alignments["hourly"]),
        lambda: process_minute(alignments["minute"]),
        process_heartrate,
    ]
    results = []
    for processor in processors:
        try:
            result = processor()
        except Exception as exc:
            print(f"FITINSIGHT_PROOF | P2-PIPELINE | STATUS=FAIL")
            print(f"ERROR: {type(exc).__name__}: {exc}")
            return 1
        results.append(result)
        if result["status"] != "PASS":
            return 1

    manifest = {
        "command": "python src/preprocess.py",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "source_commit": git_revision(),
        "phase1_merge_commit": "a6170a2caf64d66b1a622bd50c0b1a69805d34b0",
        "alignment": alignments,
        "datasets": results,
        "raw_files_unchanged": True,
        "reference_files_overwritten": False,
    }
    write_json(EVIDENCE_DIR / "run_manifest.json", manifest)
    print(
        "FITINSIGHT_PROOF | P2-PIPELINE | STATUS=PASS\n"
        f"COMMAND: python src/preprocess.py\n"
        f"OUTPUTS: {len(results)} datasets regenerated and compared\n"
        f"CHECKS: all per-dataset proofs passed; originals preserved\n"
        f"ARTIFACT: reports/evidence/P2/run_manifest.json\n"
        f"LIMITATION: generated CSVs are local reproducibility outputs, not committed reference replacements."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
