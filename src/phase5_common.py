"""Shared standard-library helpers for the reproducible Phase 5 analyses."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
from datetime import date
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DAILY_PATH = ROOT / "data" / "processed" / "daily_activity_clean.csv"
GENERATED_ROOT = ROOT / "reports" / "generated"
EVIDENCE_ROOT = ROOT / "reports" / "evidence" / "P5"

DAILY_COLUMNS = [
    "id", "activity_date", "total_steps", "total_distance",
    "tracker_distance", "logged_activities_distance",
    "very_active_distance", "moderately_active_distance",
    "light_active_distance", "sedentary_active_distance",
    "very_active_minutes", "fairly_active_minutes", "lightly_active_minutes",
    "sedentary_minutes", "calories", "total_recorded_minutes",
    "is_complete_day", "component_distance_sum", "distance_discrepancy",
]

NUMERIC_COLUMNS = [
    "total_steps", "total_distance", "tracker_distance",
    "logged_activities_distance", "very_active_distance",
    "moderately_active_distance", "light_active_distance",
    "sedentary_active_distance", "very_active_minutes",
    "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
    "calories", "total_recorded_minutes", "component_distance_sum",
]


def parse_bool(value: str, field: str) -> bool:
    if value == "True":
        return True
    if value == "False":
        return False
    raise ValueError(f"Missing or invalid {field}: {value!r}")


def parse_number(value: str, field: str) -> float | None:
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite {field}: {value!r}")
    return number


def load_daily_rows(path: Path | None = None) -> list[dict[str, Any]]:
    """Load and validate the full Phase 2 participant-day table."""
    source = path or DAILY_PATH
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, date]] = set()
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != DAILY_COLUMNS:
            raise ValueError(
                f"Unexpected daily table schema: {reader.fieldnames!r}"
            )
        for line_number, raw in enumerate(reader, start=2):
            participant = raw["id"]
            if not participant:
                raise ValueError(f"Missing participant key on row {line_number}")
            day = date.fromisoformat(raw["activity_date"])
            key = (participant, day)
            if key in seen:
                raise ValueError(f"Duplicate participant-day key: {key!r}")
            seen.add(key)
            row: dict[str, Any] = {
                "id": participant,
                "activity_date": day,
                "weekday": day.weekday(),
                "is_complete_day": parse_bool(
                    raw["is_complete_day"], "is_complete_day"
                ),
                "distance_discrepancy": parse_bool(
                    raw["distance_discrepancy"], "distance_discrepancy"
                ),
            }
            for field in NUMERIC_COLUMNS:
                row[field] = parse_number(raw[field], field)
                if row[field] is not None and row[field] < 0:
                    raise ValueError(
                        f"Negative {field} on row {line_number}"
                    )
            active = [
                row["very_active_minutes"],
                row["fairly_active_minutes"],
                row["lightly_active_minutes"],
            ]
            row["total_active_minutes"] = (
                sum(active) if all(value is not None for value in active) else None
            )
            recorded = row["total_recorded_minutes"]
            if recorded is None:
                raise ValueError(f"Missing recorded minutes on row {line_number}")
            expected_complete = recorded == 1440
            if row["is_complete_day"] != expected_complete:
                raise ValueError(
                    f"Phase 2 completeness mismatch on row {line_number}"
                )
            minute_components = [
                row["very_active_minutes"],
                row["fairly_active_minutes"],
                row["lightly_active_minutes"],
                row["sedentary_minutes"],
            ]
            if all(value is not None for value in minute_components):
                if not math.isclose(
                    sum(minute_components), recorded, rel_tol=0.0, abs_tol=1e-9
                ):
                    raise ValueError(
                        f"Recorded minute total mismatch on row {line_number}"
                    )
            rows.append(row)
    rows.sort(key=lambda row: (row["activity_date"], row["id"]))
    return rows


def quantile(values: Iterable[float], probability: float) -> float | None:
    """Linear-interpolated quantile, matching the Phase 3 convention."""
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    if probability < 0 or probability > 1:
        raise ValueError("Quantile probability must be between zero and one")
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            serialized = {}
            for field in fields:
                value = row.get(field)
                if isinstance(value, (dict, list, tuple)):
                    value = json.dumps(value, sort_keys=True, separators=(",", ":"))
                serialized[field] = "" if value is None else value
            writer.writerow(serialized)
            count += 1
    return count


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def proof(task_id: str, **facts: Any) -> None:
    """Print a concise machine-readable proof line after a completed stage."""
    print(
        "FITINSIGHT_PROOF | "
        + task_id
        + " | "
        + json.dumps(facts, sort_keys=True, separators=(",", ":"), allow_nan=False)
    )


def runtime_info() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "third_party_packages_used": [],
    }
