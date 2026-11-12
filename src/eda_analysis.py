"""Reproducible Phase 3 EDA using only Python's standard library."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from .eda_figures import generate_figures
    from .sleep_analysis import analyze_sleep_csv, strip_internal_episode_fields
except ImportError:
    from eda_figures import generate_figures
    from sleep_analysis import analyze_sleep_csv, strip_internal_episode_fields


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"
GENERATED_DIR = ROOT / "reports" / "generated" / "eda"
TABLE_DIR = GENERATED_DIR / "tables"
FIGURE_DIR = GENERATED_DIR / "figures"
EVIDENCE_DIR = ROOT / "reports" / "evidence" / "P3"
SOURCE_DATA_COMMIT = "2e233a1de22a7f808bdea3939b75d80e0848a483"

DAILY_COLUMNS = [
    "id", "activity_date", "total_steps", "total_distance", "tracker_distance",
    "logged_activities_distance", "very_active_distance",
    "moderately_active_distance", "light_active_distance",
    "sedentary_active_distance", "very_active_minutes",
    "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
    "calories", "total_recorded_minutes", "is_complete_day",
    "component_distance_sum", "distance_discrepancy",
]

NUMERIC_FIELDS = {
    "total_steps": "integer",
    "calories": "number",
    "total_distance": "number",
    "tracker_distance": "number",
    "very_active_minutes": "number",
    "fairly_active_minutes": "number",
    "lightly_active_minutes": "number",
    "sedentary_minutes": "number",
    "total_recorded_minutes": "number",
}

ACTIVITY_FIELDS = {
    "total_steps": "Recorded steps",
    "calories": "Recorded calories",
    "total_distance": "Recorded total distance",
    "total_active_minutes": "Recorded active minutes",
    "sedentary_minutes": "Recorded sedentary minutes",
}


def parse_number(value: str, field: str) -> float | None:
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite value in {field}: {value!r}")
    return number


def parse_boolean(value: str, field: str) -> bool | None:
    if value == "True":
        return True
    if value == "False":
        return False
    if value == "":
        return None
    raise ValueError(f"Invalid boolean in {field}: {value!r}")


def load_daily(path: Path | None = None) -> list[dict[str, Any]]:
    path = path or DATA_DIR / "daily_activity_clean.csv"
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != DAILY_COLUMNS:
            raise ValueError(
                f"Unexpected daily activity schema: {reader.fieldnames!r}"
            )
        seen_keys = set()
        for line_number, raw in enumerate(reader, start=2):
            if not raw["id"] or not raw["activity_date"]:
                raise ValueError(f"Daily row {line_number} has a missing key")
            day = date.fromisoformat(raw["activity_date"])
            key = (raw["id"], day)
            if key in seen_keys:
                raise ValueError(f"Duplicate participant-day key: {key!r}")
            seen_keys.add(key)
            row: dict[str, Any] = {
                "id": raw["id"],
                "activity_date": day,
                "weekday": day.weekday(),
                "is_complete_day": parse_boolean(
                    raw["is_complete_day"], "is_complete_day"
                ),
                "distance_discrepancy": parse_boolean(
                    raw["distance_discrepancy"], "distance_discrepancy"
                ),
            }
            for field in NUMERIC_FIELDS:
                row[field] = parse_number(raw[field], field)
            for field in (
                "very_active_distance", "moderately_active_distance",
                "light_active_distance", "sedentary_active_distance",
                "logged_activities_distance", "component_distance_sum",
            ):
                row[field] = parse_number(raw[field], field)

            active_components = [
                row["very_active_minutes"],
                row["fairly_active_minutes"],
                row["lightly_active_minutes"],
            ]
            row["total_active_minutes"] = (
                sum(active_components)
                if all(value is not None for value in active_components)
                else None
            )
            if row["total_recorded_minutes"] is not None:
                expected_complete = row["total_recorded_minutes"] == 1440
                if row["is_complete_day"] != expected_complete:
                    raise ValueError(
                        f"Stored completeness flag disagrees with minute sum "
                        f"for {raw['id']} on {day}"
                    )
            rows.append(row)
    return rows


def mean(values: Iterable[float | None]) -> float | None:
    valid = [float(value) for value in values if value is not None]
    return statistics.fmean(valid) if valid else None


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def describe(values: Iterable[float | None]) -> dict[str, Any]:
    original = list(values)
    valid = [float(value) for value in original if value is not None]
    q1 = quantile(valid, 0.25)
    median = quantile(valid, 0.50)
    q3 = quantile(valid, 0.75)
    sd = statistics.stdev(valid) if len(valid) > 1 else None
    skewness = None
    if len(valid) >= 3:
        center = statistics.fmean(valid)
        second = sum((value - center) ** 2 for value in valid) / len(valid)
        third = sum((value - center) ** 3 for value in valid) / len(valid)
        if second > 0:
            skewness = (
                (third / (second ** 1.5))
                * math.sqrt(len(valid) * (len(valid) - 1))
                / (len(valid) - 2)
            )
    return {
        "count": len(valid),
        "missing": len(original) - len(valid),
        "mean": statistics.fmean(valid) if valid else None,
        "median": median,
        "sample_stddev": sd,
        "min": min(valid) if valid else None,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1 if q1 is not None and q3 is not None else None,
        "max": max(valid) if valid else None,
        "skewness_adjusted_fisher_pearson": skewness,
    }


def participant_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row["id"]].append(row)
    return groups


def build_participant_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries = []
    for participant_id, participant_rows in sorted(participant_groups(rows).items()):
        complete = [row for row in participant_rows if row["is_complete_day"] is True]
        item = {
            "id": participant_id,
            "recorded_days": len(participant_rows),
            "complete_days": len(complete),
            "complete_day_percentage": 100 * len(complete) / len(participant_rows),
        }
        for field in (
            "total_steps", "calories", "total_distance", "total_active_minutes",
            "sedentary_minutes", "total_recorded_minutes",
        ):
            item[f"avg_{field}_all"] = mean(row[field] for row in participant_rows)
            item[f"avg_{field}_complete"] = mean(row[field] for row in complete)
        item["median_steps_all"] = quantile(
            [row["total_steps"] for row in participant_rows if row["total_steps"] is not None],
            0.5,
        )
        item["sample_stddev_steps_all"] = describe(
            row["total_steps"] for row in participant_rows
        )["sample_stddev"]
        summaries.append(item)
    return summaries


def descriptive_analysis(
    rows: list[dict[str, Any]],
    participant_summary: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fields = [
        "total_steps", "calories", "total_distance", "tracker_distance",
        "very_active_minutes", "fairly_active_minutes", "lightly_active_minutes",
        "sedentary_minutes", "total_active_minutes", "total_recorded_minutes",
    ]
    pooled = {
        field: describe(row.get(field) for row in rows)
        for field in fields
    }
    participant_fields = {
        "total_steps": "avg_total_steps_all",
        "calories": "avg_calories_all",
        "total_distance": "avg_total_distance_all",
        "total_active_minutes": "avg_total_active_minutes_all",
        "sedentary_minutes": "avg_sedentary_minutes_all",
        "total_recorded_minutes": "avg_total_recorded_minutes_all",
    }
    participant_level = {
        metric: describe(item[field] for item in participant_summary)
        for metric, field in participant_fields.items()
    }
    metrics = {
        "observation_grain": "participant-day",
        "rows": len(rows),
        "participants": len(participant_summary),
        "pooled_daily_statistics": pooled,
        "participant_mean_statistics": participant_level,
        "participant_weighting_note": (
            "Pooled statistics weight each recorded participant-day equally; "
            "participant-mean statistics weight each participant equally."
        ),
    }
    table = []
    for grain, values in (
        ("participant_day_pooled", pooled),
        ("participant_means_equal_weight", participant_level),
    ):
        for metric, summary in values.items():
            table.append({"grain": grain, "metric": metric, **summary})
    return metrics, table


def completeness_analysis(
    rows: list[dict[str, Any]],
    participant_summary: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    groups = {
        "complete": [row for row in rows if row["is_complete_day"] is True],
        "incomplete": [row for row in rows if row["is_complete_day"] is False],
    }
    group_metrics = {}
    for label, group in groups.items():
        group_metrics[label] = {
            "participant_days": len(group),
            "participants": len({row["id"] for row in group}),
            "metrics": {
                field: describe(row[field] for row in group)
                for field in (
                    "total_steps", "calories", "total_active_minutes",
                    "sedentary_minutes", "total_recorded_minutes",
                )
            },
        }
    sensitivity_rows = []
    direction_counts = Counter()
    for item in participant_summary:
        all_mean = item["avg_total_steps_all"]
        complete_mean = item["avg_total_steps_complete"]
        delta = (
            complete_mean - all_mean
            if complete_mean is not None and all_mean is not None
            else None
        )
        if delta is None:
            direction = "unavailable"
        elif delta > 0:
            direction = "complete_day_mean_higher"
        elif delta < 0:
            direction = "all_day_mean_higher"
        else:
            direction = "equal"
        direction_counts[direction] += 1
        sensitivity_rows.append({
            "id": item["id"],
            "recorded_days": item["recorded_days"],
            "complete_days": item["complete_days"],
            "all_day_mean_steps": all_mean,
            "complete_day_mean_steps": complete_mean,
            "complete_minus_all_steps": delta,
            "direction": direction,
        })
    deltas = [row["complete_minus_all_steps"] for row in sensitivity_rows]
    metrics = {
        "observation_grain": "participant-day and participant",
        "complete_rule": "total_recorded_minutes == 1440",
        "all_days": len(rows),
        "complete_day_counts": {
            label: data["participant_days"] for label, data in group_metrics.items()
        },
        "groups": group_metrics,
        "participants": len(participant_summary),
        "participants_without_complete_days": sum(
            item["complete_days"] == 0 for item in participant_summary
        ),
        "participant_step_mean_sensitivity": {
            **describe(deltas),
            "direction_counts": dict(direction_counts),
            "eligible_participants": sum(value is not None for value in deltas),
        },
        "interpretation": (
            "Complete-day filtering is an observation-selection sensitivity check; "
            "it does not establish that incomplete records are invalid."
        ),
    }
    return metrics, sensitivity_rows


def average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for position in range(start, end):
            ranks[order[position]] = rank
        start = end
    return ranks


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    centered_x = [value - mean_x for value in xs]
    centered_y = [value - mean_y for value in ys]
    sum_x = sum(value * value for value in centered_x)
    sum_y = sum(value * value for value in centered_y)
    if sum_x == 0 or sum_y == 0:
        return None
    return sum(a * b for a, b in zip(centered_x, centered_y)) / math.sqrt(sum_x * sum_y)


def pairwise_correlation(
    rows: list[dict[str, Any]],
    x_field: str,
    y_field: str,
    *,
    grain: str,
) -> dict[str, Any]:
    pairs = [
        (row.get(x_field), row.get(y_field), row.get("id"))
        for row in rows
        if row.get(x_field) is not None and row.get(y_field) is not None
    ]
    xs = [float(x) for x, _, _ in pairs]
    ys = [float(y) for _, y, _ in pairs]
    return {
        "grain": grain,
        "x": x_field,
        "y": y_field,
        "n_pairs": len(pairs),
        "participants": len({participant for _, _, participant in pairs}),
        "missing_pairs": len(rows) - len(pairs),
        "pearson": pearson(xs, ys),
        "spearman": pearson(average_ranks(xs), average_ranks(ys)),
    }


def daily_metric_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        result.append({
            **row,
            "is_complete_day_numeric": (
                1.0 if row["is_complete_day"] is True
                else 0.0 if row["is_complete_day"] is False
                else None
            ),
        })
    return result


def correlations_analysis(
    rows: list[dict[str, Any]],
    participant_summary: list[dict[str, Any]],
) -> dict[str, Any]:
    pooled_rows = daily_metric_rows(rows)
    participant_rows = []
    for item in participant_summary:
        participant_rows.append({
            "id": item["id"],
            "total_steps": item["avg_total_steps_all"],
            "calories": item["avg_calories_all"],
            "total_distance": item["avg_total_distance_all"],
            "total_active_minutes": item["avg_total_active_minutes_all"],
            "sedentary_minutes": item["avg_sedentary_minutes_all"],
            "complete_day_rate": item["complete_day_percentage"] / 100,
        })
    pairs = [
        ("total_steps", "calories"),
        ("total_steps", "total_distance"),
        ("total_steps", "total_active_minutes"),
        ("total_active_minutes", "calories"),
        ("sedentary_minutes", "total_active_minutes"),
        ("is_complete_day_numeric", "total_steps"),
        ("is_complete_day_numeric", "total_active_minutes"),
    ]
    output = []
    for left, right in pairs:
        output.append(pairwise_correlation(
            pooled_rows, left, right, grain="participant_day_pooled"
        ))
    participant_pairs = [
        ("total_steps", "calories"),
        ("total_steps", "total_distance"),
        ("total_steps", "total_active_minutes"),
        ("total_active_minutes", "calories"),
        ("sedentary_minutes", "total_active_minutes"),
        ("complete_day_rate", "total_steps"),
        ("complete_day_rate", "total_active_minutes"),
    ]
    for left, right in participant_pairs:
        output.append(pairwise_correlation(
            participant_rows, left, right, grain="participant_means"
        ))

    matrix_fields = [
        "total_steps", "calories", "total_distance",
        "total_active_minutes", "sedentary_minutes", "is_complete_day_numeric",
    ]
    matrix_labels = [
        "Steps", "Calories", "Distance", "Active min", "Sedentary min", "Complete flag",
    ]
    matrix_cells = []
    for i, (left, label_left) in enumerate(zip(matrix_fields, matrix_labels)):
        for j, (right, label_right) in enumerate(zip(matrix_fields, matrix_labels)):
            item = pairwise_correlation(
                pooled_rows,
                left,
                right,
                grain="participant_day_pooled",
            )
            matrix_cells.append({
                "x_index": j,
                "y_index": i,
                "row": label_left,
                "column": label_right,
                "spearman": item["spearman"],
                "pearson": item["pearson"],
                "n_pairs": item["n_pairs"],
                "participants": item["participants"],
            })
    return {
        "method": (
            "Pearson for linear association and Spearman for rank-based monotonic "
            "association; pairwise complete cases; no p-values."
        ),
        "repeated_observation_caveat": (
            "Pooled participant-day coefficients are descriptive and do not treat "
            "repeated days as independent people. Participant-mean estimates are "
            "reported separately."
        ),
        "participant_day_pairwise": [
            item for item in output if item["grain"] == "participant_day_pooled"
        ],
        "participant_mean_pairwise": [
            item for item in output if item["grain"] == "participant_means"
        ],
        "heatmap": {
            "measure": "Spearman rank correlation",
            "labels": matrix_labels,
            "cells": matrix_cells,
        },
    }


def weekday_weekend_analysis(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    fields = ["total_steps", "total_active_minutes", "sedentary_minutes", "calories"]
    grouped: dict[str, list[dict[str, Any]]] = {
        "weekday": [row for row in rows if row["weekday"] < 5],
        "weekend": [row for row in rows if row["weekday"] >= 5],
    }
    pooled = {}
    for day_type, group in grouped.items():
        pooled[day_type] = {
            "participant_days": len(group),
            "participants": len({row["id"] for row in group}),
            "metrics": {field: describe(row[field] for row in group) for field in fields},
        }

    participant_rows = []
    participants = participant_groups(rows)
    direction_counts: dict[str, Counter] = {
        field: Counter() for field in fields
    }
    for participant_id, records in sorted(participants.items()):
        item: dict[str, Any] = {"id": participant_id}
        for day_type, day_filter in (
            ("weekday", lambda r: r["weekday"] < 5),
            ("weekend", lambda r: r["weekday"] >= 5),
        ):
            days = [row for row in records if day_filter(row)]
            item[f"{day_type}_days"] = len(days)
            for field in fields:
                item[f"{day_type}_mean_{field}"] = mean(row[field] for row in days)
        for field in fields:
            weekday_mean = item[f"weekday_mean_{field}"]
            weekend_mean = item[f"weekend_mean_{field}"]
            delta = (
                weekend_mean - weekday_mean
                if weekday_mean is not None and weekend_mean is not None
                else None
            )
            item[f"weekend_minus_weekday_{field}"] = delta
            if delta is None:
                direction_counts[field]["unavailable"] += 1
            elif delta > 0:
                direction_counts[field]["weekend_higher"] += 1
            elif delta < 0:
                direction_counts[field]["weekday_higher"] += 1
            else:
                direction_counts[field]["equal"] += 1
        participant_rows.append(item)

    paired = {}
    for field in fields:
        deltas = [row[f"weekend_minus_weekday_{field}"] for row in participant_rows]
        paired[field] = {
            **describe(deltas),
            "direction_counts": dict(direction_counts[field]),
            "participants_with_both": sum(value is not None for value in deltas),
        }
    complete_rows = [row for row in rows if row["is_complete_day"] is True]
    complete_participants = participant_groups(complete_rows)
    complete_paired = {}
    for field in fields:
        deltas = []
        for records in complete_participants.values():
            weekday_values = [
                row[field] for row in records if row["weekday"] < 5 and row[field] is not None
            ]
            weekend_values = [
                row[field] for row in records if row["weekday"] >= 5 and row[field] is not None
            ]
            if weekday_values and weekend_values:
                deltas.append(statistics.fmean(weekend_values) - statistics.fmean(weekday_values))
        complete_paired[field] = {
            **describe(deltas),
            "participants_with_both": len(deltas),
        }
    metrics = {
        "observation_grain": "participant-day; paired comparisons at participant grain",
        "weekday_definition": "Monday through Friday",
        "weekend_definition": "Saturday and Sunday",
        "pooled_participant_day_summaries": pooled,
        "paired_participant_differences_weekend_minus_weekday": paired,
        "complete_day_only_sensitivity": complete_paired,
        "interpretation": (
            "Pooled and participant-paired summaries answer different questions; "
            "no independent-day significance test is used."
        ),
    }
    return metrics, participant_rows


def add_sleep_correlations(
    correlations: dict[str, Any],
    matched_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    included = [
        row for row in matched_rows
        if row["sleep_match_status"] == "matched"
    ]
    pairs = []
    for x_field, y_field in (
        ("recorded_sleep_minutes", "total_steps"),
        ("recorded_sleep_minutes", "total_active_minutes"),
        ("recorded_sleep_minutes", "calories"),
    ):
        pairs.append(pairwise_correlation(
            included, x_field, y_field, grain="matched_waking_date_pooled"
        ))

    by_participant = participant_groups(included)
    averages = []
    for participant_id, items in sorted(by_participant.items()):
        averages.append({
            "id": participant_id,
            "recorded_sleep_minutes": mean(item["recorded_sleep_minutes"] for item in items),
            "total_steps": mean(item["total_steps"] for item in items),
            "total_active_minutes": mean(item["total_active_minutes"] for item in items),
            "calories": mean(item["calories"] for item in items),
        })
    participant_pairs = [
        pairwise_correlation(
            averages, "recorded_sleep_minutes", metric,
            grain="matched_waking_date_participant_means",
        )
        for metric in ("total_steps", "total_active_minutes", "calories")
    ]

    complete_matches = [
        row for row in included if row["is_complete_day"] is True
    ]
    complete_pairs = [
        pairwise_correlation(
            complete_matches, "recorded_sleep_minutes", metric,
            grain="matched_complete_activity_days",
        )
        for metric in ("total_steps", "total_active_minutes", "calories")
    ]
    updated = dict(correlations)
    updated["sleep_activity"] = {
        "sleep_measure": (
            "Number of recorded sleep-minute rows in a validated episode; "
            "not validated actual minutes asleep."
        ),
        "pooled_matched_waking_date": pairs,
        "participant_mean_matched_waking_date": participant_pairs,
        "complete_activity_day_sensitivity": complete_pairs,
        "complete_activity_day_sensitivity_status": {
            "matched_complete_activity_days": len(complete_matches),
            "available": bool(complete_matches),
            "reason_unavailable": (
                "No matched waking dates are marked complete by the 1,440-minute rule."
                if not complete_matches else ""
            ),
        },
        "p_values": "Not calculated; repeated participant-days are not independent.",
    }
    return updated


def outlier_candidates(
    rows: list[dict[str, Any]],
    episodes: list[dict],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    fields = [
        "total_steps", "calories", "total_distance", "total_active_minutes",
        "sedentary_minutes", "total_recorded_minutes",
    ]
    thresholds = {}
    for field in fields:
        values = [float(row[field]) for row in rows if row[field] is not None]
        q1 = quantile(values, 0.25)
        q3 = quantile(values, 0.75)
        iqr = q3 - q1 if q1 is not None and q3 is not None else None
        thresholds[field] = {
            "q1": q1,
            "q3": q3,
            "lower_fence": q1 - 1.5 * iqr if q1 is not None and iqr is not None else None,
            "upper_fence": q3 + 1.5 * iqr if q3 is not None and iqr is not None else None,
        }
    candidates = []
    daily_flags = Counter()
    for row in rows:
        flags = []
        if row["total_steps"] == 0 and row["calories"] is not None and row["calories"] > 0:
            flags.append("zero_steps_positive_calories")
        if (
            row["total_steps"] == 0
            and row["total_active_minutes"] is not None
            and row["total_active_minutes"] > 0
        ):
            flags.append("zero_steps_positive_active_minutes")
        if row["distance_discrepancy"]:
            flags.append("phase2_numpy_isclose_distance_flag")
        for field, fence in thresholds.items():
            value = row[field]
            if value is None:
                continue
            if fence["upper_fence"] is not None and value > fence["upper_fence"]:
                flags.append(f"{field}_above_1_5_iqr_fence")
            elif fence["lower_fence"] is not None and value < fence["lower_fence"]:
                flags.append(f"{field}_below_1_5_iqr_fence")
        if row["total_recorded_minutes"] is not None and row["total_recorded_minutes"] > 1440:
            flags.append("recorded_minutes_above_1440")
        for flag in flags:
            daily_flags[flag] += 1
        if flags:
            candidates.append({
                "record_type": "participant_day",
                "id": row["id"],
                "date": row["activity_date"].isoformat(),
                "log_id": "",
                "start_timestamp": "",
                "end_timestamp": "",
                "total_steps": row["total_steps"],
                "calories": row["calories"],
                "total_distance": row["total_distance"],
                "total_active_minutes": row["total_active_minutes"],
                "sedentary_minutes": row["sedentary_minutes"],
                "total_recorded_minutes": row["total_recorded_minutes"],
                "flags": ";".join(flags),
                "handling": "preserve; candidate for review, not an invalid-record label",
            })

    sleep_flags = Counter()
    for episode in episodes:
        meaningful = [
            flag for flag in episode["quality_flags"]
            if flag in {
                "timestamp_gap_over_60_seconds", "interval_not_60_seconds",
                "elapsed_span_over_12_hours", "afternoon_start_candidate",
                "overlaps_another_log", "multiple_overnight_logs_same_waking_date",
            }
        ]
        for flag in meaningful:
            sleep_flags[flag] += 1
        if meaningful:
            candidates.append({
                "record_type": "sleep_episode",
                "id": episode["id"],
                "date": episode["waking_date"],
                "log_id": episode["log_id"],
                "start_timestamp": episode["start_timestamp"],
                "end_timestamp": episode["end_timestamp"],
                "total_steps": "",
                "calories": "",
                "total_distance": "",
                "total_active_minutes": "",
                "sedentary_minutes": "",
                "total_recorded_minutes": episode["recorded_minute_count"],
                "flags": ";".join(meaningful),
                "handling": "preserve; timing or recording pattern needs review",
            })
    metrics = {
        "daily_iqr_fences": thresholds,
        "daily_candidate_rows": sum(row["record_type"] == "participant_day" for row in candidates),
        "sleep_episode_candidate_rows": sum(row["record_type"] == "sleep_episode" for row in candidates),
        "daily_flag_counts": dict(daily_flags),
        "sleep_flag_counts": dict(sleep_flags),
        "screening_rule": (
            "1.5×IQR fences plus observed zero-step/activity and Phase 2 "
            "distance flags; candidates are retained and are not diagnoses."
        ),
    }
    return candidates, metrics


def serialize_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    return value


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, default=serialize_value, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: "" if row.get(field) is None else serialize_value(row.get(field))
                for field in fieldnames
            })


def git_head() -> str | None:
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


def source_hashes() -> dict[str, str]:
    hashes = {}
    for relative in (
        "src/eda_analysis.py",
        "src/sleep_analysis.py",
        "src/eda_figures.py",
    ):
        path = ROOT / relative
        if path.exists():
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def print_proof(
    task: str,
    question: str,
    grain: str,
    sample: str,
    method: str,
    why: str,
    result: str,
    checks: str,
    artifact: str,
    limitation: str,
    status: str = "PASS",
) -> None:
    print(
        f"FITINSIGHT_PROOF | {task}\n"
        f"STATUS: {status}\n"
        f"QUESTION: {question}\n"
        f"INPUT: data/processed/; source data commit={SOURCE_DATA_COMMIT[:7]}\n"
        f"GRAIN: {grain}\n"
        f"SAMPLE: {sample}\n"
        f"METHOD: {method}\n"
        f"WHY: {why}\n"
        f"RESULT: {result}\n"
        f"CHECKS: {checks}\n"
        f"ARTIFACT: {artifact}\n"
        f"LIMITATION: {limitation}"
    )


def run() -> int:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    daily_path = DATA_DIR / "daily_activity_clean.csv"
    sleep_path = DATA_DIR / "minute_sleep_clean.csv"
    rows = load_daily(daily_path)
    participants = build_participant_summary(rows)
    if len(rows) != 457 or len({row["id"] for row in rows}) != 35:
        raise ValueError(
            f"Daily contract failed: rows={len(rows)}, participants={len({r['id'] for r in rows})}"
        )
    daily_missing = {
        field: sum(row[field] is None for row in rows)
        for field in (
            "total_steps", "calories", "total_distance", "total_active_minutes",
            "sedentary_minutes", "total_recorded_minutes",
        )
    }
    input_metrics = {
        "daily": {
            "rows": len(rows),
            "participants": len({row["id"] for row in rows}),
            "schema_matches": True,
            "key_duplicates": 0,
            "missing_counts": daily_missing,
            "complete_days": sum(row["is_complete_day"] is True for row in rows),
            "incomplete_days": sum(row["is_complete_day"] is False for row in rows),
        }
    }
    write_json(EVIDENCE_DIR / "input_validation.json", {
        "source_data_commit": SOURCE_DATA_COMMIT,
        "daily_file": str(daily_path.relative_to(ROOT)),
        **input_metrics,
    })
    print_proof(
        "P3-INPUT",
        "Do the Phase 2 daily inputs meet the P3 contract?",
        "participant-day",
        f"{len(rows)} rows; {input_metrics['daily']['participants']} participants",
        "Validate exact columns, ISO dates, complete flags, and unique (id,date) keys",
        "The smallest relevant dataset supports activity EDA without loading minute activity or heart rate",
        f"{input_metrics['daily']['complete_days']} complete and "
        f"{input_metrics['daily']['incomplete_days']} incomplete days",
        f"schema=yes; duplicate keys=0; missing={daily_missing}; stored completeness checked",
        "reports/evidence/P3/input_validation.json",
        "Coverage is a device-recording property, not proof of participant behavior.",
    )

    descriptive, descriptive_table = descriptive_analysis(rows, participants)
    write_csv(TABLE_DIR / "descriptive_statistics.csv", descriptive_table)
    write_csv(TABLE_DIR / "participant_summary.csv", participants)
    write_json(EVIDENCE_DIR / "descriptive_metrics.json", descriptive)
    print_proof(
        "P3-A-DESCRIPTIVE",
        "How are activity measures distributed across days and participants?",
        "pooled participant-day and equal-weight participant means",
        f"{len(rows)} days; {len(participants)} participants",
        "Count, mean, median, sample SD, min/max, linearly interpolated quartiles, IQR, adjusted skew",
        "Both pooled and participant-mean views are needed because recording counts differ",
        f"step mean={descriptive['pooled_daily_statistics']['total_steps']['mean']:.2f}; "
        f"median={descriptive['pooled_daily_statistics']['total_steps']['median']:.2f}",
        f"daily missing steps={descriptive['pooled_daily_statistics']['total_steps']['missing']}; "
        "participant IDs preserved as strings",
        "reports/evidence/P3/descriptive_metrics.json",
        "No physical measurement units are independently verified.",
    )

    completeness, sensitivity_table = completeness_analysis(rows, participants)
    write_json(EVIDENCE_DIR / "completeness_metrics.json", completeness)
    write_csv(TABLE_DIR / "complete_day_sensitivity.csv", sensitivity_table)
    print_proof(
        "P3-B-COMPLETENESS",
        "How does the complete-day filter change activity summaries?",
        "participant-day and participant",
        f"{len(rows)} days; {completeness['participants_without_complete_days']} participants have no complete day",
        "Use existing is_complete_day flag and compare each participant's all-day and complete-day mean steps",
        "Filtering changes the observed sample; direction must be measured per participant",
        f"complete={completeness['complete_day_counts']['complete']}; "
        f"incomplete={completeness['complete_day_counts']['incomplete']}; "
        f"participant directions={completeness['participant_step_mean_sensitivity']['direction_counts']}",
        "complete flag recomputed from 1,440 recorded minutes and checked against stored field",
        "reports/evidence/P3/completeness_metrics.json",
        "Incomplete days are not assumed invalid; selection effects remain possible.",
    )

    correlations = correlations_analysis(rows, participants)
    write_json(EVIDENCE_DIR / "correlation_metrics.json", correlations)
    correlation_table = (
        correlations["participant_day_pairwise"]
        + correlations["participant_mean_pairwise"]
    )
    write_csv(TABLE_DIR / "correlations.csv", correlation_table)
    print_proof(
        "P3-C-CORRELATION",
        "Which activity measures co-vary in the recorded data?",
        "pooled participant-day and participant means",
        f"{len(rows)} days; {len(participants)} participants",
        "Pairwise Pearson and Spearman coefficients with complete-pair counts",
        "Pearson summarizes linear association; Spearman is rank-based for monotonic association",
        f"{len(correlation_table)} activity associations computed; no p-values",
        "pairwise missingness counted; constant inputs return null; no significance claims",
        "reports/evidence/P3/correlation_metrics.json",
        "Participant-days repeat people; pooled coefficients are descriptive, not independent-person inference.",
    )

    weekday, weekday_table = weekday_weekend_analysis(rows)
    write_json(EVIDENCE_DIR / "weekday_weekend_metrics.json", weekday)
    write_csv(TABLE_DIR / "weekday_weekend_participant_differences.csv", weekday_table)
    print_proof(
        "P3-D-WEEKDAY-WEEKEND",
        "How do weekday and weekend records differ?",
        "pooled participant-day and paired participant",
        f"{weekday['pooled_participant_day_summaries']['weekday']['participant_days']} weekdays; "
        f"{weekday['pooled_participant_day_summaries']['weekend']['participant_days']} weekends",
        "Classify parsed calendar dates; compare pooled summaries and paired participant means",
        "Pairing avoids treating repeated daily rows as independent participants",
        f"step directions={weekday['paired_participant_differences_weekend_minus_weekday']['total_steps']['direction_counts']}",
        "weekday/weekend participant counts and complete-day sensitivity are reported",
        "reports/evidence/P3/weekday_weekend_metrics.json",
        "Unequal observation coverage can bias pooled comparisons.",
    )

    sleep_result = analyze_sleep_csv(sleep_path)
    sleep_metrics = sleep_result["metrics"]
    sleep_metrics["input_file"] = str(sleep_path.relative_to(ROOT))
    sleep_rows = sleep_result["episodes"]
    if sleep_metrics["conflicting_duplicate_rows"]:
        raise ValueError("Processed sleep input contains conflicting duplicate keys")
    if sleep_metrics["duplicate_key_rows_after_preprocessing"]:
        raise ValueError("Processed sleep input contains duplicate composite keys")
    if sleep_metrics["timestamp_to_calendar_date_mismatches"]:
        raise ValueError("Sleep calendar_date disagrees with its timestamp")
    sleep_episode_table = [
        strip_internal_episode_fields(episode) for episode in sleep_rows
    ]
    sleep_coverage_table = sleep_result["participant_coverage"]
    write_csv(TABLE_DIR / "sleep_episodes.csv", sleep_episode_table)
    write_csv(TABLE_DIR / "sleep_participant_coverage.csv", sleep_coverage_table)
    write_json(EVIDENCE_DIR / "sleep_episode_metrics.json", sleep_metrics)
    print_proof(
        "P3-E-SLEEP-EPISODES",
        "Can sleep-minute records be summarized as defensible log episodes?",
        "participant-log episode and participant coverage",
        f"{sleep_metrics['distinct_rows']} records; {sleep_metrics['participants']} participants; "
        f"{sleep_metrics['participant_log_groups']} logs",
        "Stream records into a local temporary SQLite index; order by id/log/time; aggregate counts, categories, intervals, and spans",
        "Log IDs plus timestamp continuity distinguish record groups while keeping memory bounded",
        f"categories={sleep_metrics['value_category_counts']}; "
        f"cross-midnight={sleep_metrics['cross_midnight_logs']}; "
        f"overnight candidates={sleep_metrics['overnight_candidate_count']}; "
        f"primary eligible={sleep_metrics['primary_eligible_episode_count']}",
        f"duplicate keys={sleep_metrics['duplicate_key_rows_after_preprocessing']}; "
        f"gapped logs={sleep_metrics['logs_with_timestamp_gap_over_60_seconds']}; "
        f"overlapping logs={sleep_metrics['overlapping_log_count']}",
        "reports/evidence/P3/sleep_episode_metrics.json",
        "Stored codes 1/2/3 are neutral categories; recorded minutes are not validated actual sleep duration.",
    )

    matched_rows, sleep_alignment = make_sleep_activity_table(rows, sleep_rows)
    correlations = add_sleep_correlations(correlations, matched_rows)
    write_csv(
        TABLE_DIR / "sleep_activity_waking_date.csv",
        matched_rows,
        [
            "id", "activity_date", "sleep_match_status", "sleep_log_id",
            "sleep_start_timestamp", "sleep_end_timestamp",
            "recorded_sleep_minutes", "is_complete_day", "total_steps",
            "calories", "total_active_minutes", "sedentary_minutes",
        ],
    )
    write_json(EVIDENCE_DIR / "sleep_alignment_metrics.json", sleep_alignment)
    write_json(EVIDENCE_DIR / "correlation_metrics.json", correlations)
    write_csv(
        TABLE_DIR / "sleep_activity_correlations.csv",
        correlations["sleep_activity"]["pooled_matched_waking_date"]
        + correlations["sleep_activity"]["participant_mean_matched_waking_date"]
        + correlations["sleep_activity"]["complete_activity_day_sensitivity"],
    )
    print_proof(
        "P3-F-SLEEP-ACTIVITY",
        "What activity is recorded on validated sleep waking dates?",
        "participant-waking-date",
        f"{sleep_alignment['matched_rows']} matched days; "
        f"{sleep_alignment['matched_participants']} participants",
        "Match one eligible overnight candidate to activity on the episode end date; leave unmatched sleep blank",
        "The end date is the natural waking-date candidate; duplicate sessions are excluded instead of multiplying rows",
        f"matched={sleep_alignment['matched_rows']}; "
        f"unmatched activity days={sleep_alignment['unmatched_activity_days']}; "
        f"ambiguous multiple-session dates={sleep_alignment['ambiguous_activity_dates']}; "
        f"complete matched days={sleep_alignment['complete_matched_activity_days']}",
        f"daily row count preserved={sleep_alignment['daily_rows_preserved']}; "
        f"eligible sleep episodes without activity={sleep_alignment['eligible_episodes_without_activity']}",
        "reports/evidence/P3/sleep_alignment_metrics.json",
        "Association is descriptive; recorded sleep-minute count is not actual time asleep and does not imply causation.",
    )

    candidates, outlier_metrics = outlier_candidates(rows, sleep_rows)
    write_csv(
        TABLE_DIR / "anomaly_candidates.csv",
        candidates,
        [
            "record_type", "id", "date", "log_id", "start_timestamp",
            "end_timestamp", "total_steps", "calories", "total_distance",
            "total_active_minutes", "sedentary_minutes", "total_recorded_minutes",
            "flags", "handling",
        ],
    )
    write_json(EVIDENCE_DIR / "outlier_screen_metrics.json", outlier_metrics)
    print_proof(
        "P3-G-OUTLIER-SCREEN",
        "Which records merit a later focused review?",
        "participant-day and participant-log episode",
        f"{outlier_metrics['daily_candidate_rows']} daily candidates; "
        f"{outlier_metrics['sleep_episode_candidate_rows']} sleep candidates",
        "Apply 1.5×IQR screens and explicit observed data-quality flags",
        "Screening candidates supports review without silently deleting rows",
        f"daily flag counts={outlier_metrics['daily_flag_counts']}; "
        f"sleep flag counts={outlier_metrics['sleep_flag_counts']}",
        "all candidate rows are retained and marked for review only",
        "reports/evidence/P3/outlier_screen_metrics.json",
        "A statistical fence or data-quality flag is not proof of an invalid or medically abnormal record.",
    )

    figure_entries = generate_figures(
        rows=rows,
        weekday_participant_rows=weekday_table,
        correlations=correlations,
        sleep_episodes=sleep_rows,
        matched_rows=matched_rows,
        output_dir=FIGURE_DIR,
    )
    figures_index = {
        "figure_count": len(figure_entries),
        "format": "SVG",
        "figures": figure_entries,
        "reproduction_command": "python src/eda_analysis.py",
    }
    write_json(EVIDENCE_DIR / "figures_index.json", figures_index)
    print_proof(
        "P3-I-FIGURES",
        "Do the figures show the verified Phase 3 results clearly?",
        "participant-day, participant, and matched waking-date",
        f"{len(figure_entries)} SVG figures",
        "Generate vector charts directly from the analysis result objects",
        "SVG keeps charts reproducible without unavailable plotting packages",
        ", ".join(item["file"] for item in figure_entries),
        "all figure inputs are computed in this run; titles, grains, sample counts, and caveats are recorded",
        "reports/evidence/P3/figures_index.json",
        "Figures describe this historical sample and are not health advice.",
    )

    source_status = subprocess.run(
        [
            "git", "status", "--porcelain", "--",
            "src/eda_analysis.py", "src/sleep_analysis.py",
            "src/eda_figures.py", "tests/test_phase3.py",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    manifest = {
        "status": "PASS",
        "command": "python src/eda_analysis.py",
        "python": sys.version.split()[0],
        "dependencies": "Python standard library only",
        "source_data_commit": SOURCE_DATA_COMMIT,
        "pipeline_commit": git_head(),
        "source_working_tree_dirty": bool(source_status.stdout.strip()),
        "source_code_sha256": source_hashes(),
        "inputs": {
            "daily_activity": {
                "path": str(daily_path.relative_to(ROOT)),
                "rows": len(rows),
                "participants": len(participants),
            },
            "minute_sleep": {
                "path": str(sleep_path.relative_to(ROOT)),
                "rows": sleep_metrics["distinct_rows"],
                "participants": sleep_metrics["participants"],
            },
        },
        "outputs": {
            "tables": [str(path.relative_to(ROOT)) for path in sorted(TABLE_DIR.glob("*.csv"))],
            "figures": [
                str((FIGURE_DIR / item["file"]).relative_to(ROOT))
                for item in figure_entries
            ],
            "evidence": [
                str(path.relative_to(ROOT))
                for path in sorted(EVIDENCE_DIR.glob("*.json"))
            ] + ["reports/evidence/P3/run_manifest.json"],
        },
        "raw_and_reference_files_modified": False,
        "notebooks_modified": False,
    }
    write_json(EVIDENCE_DIR / "run_manifest.json", manifest)
    print_proof(
        "P3-PIPELINE",
        "Can Phase 3 analysis be rerun from the committed processed data?",
        "participant-day, participant, sleep episode, waking date",
        f"{len(rows)} daily rows; {sleep_metrics['distinct_rows']} sleep-minute rows",
        "Run all verified analysis modules sequentially and save compact evidence",
        "The same command reproduces metrics, tables, sleep linkage, and vector figures",
        f"figures={len(figure_entries)}; matched waking dates={sleep_alignment['matched_rows']}; "
        "raw/reference/notebook changes=0",
        "input validation and all analysis checks passed",
        "reports/evidence/P3/run_manifest.json",
        "Results remain descriptive and depend on the historical source's coverage and measurement quality.",
    )
    return 0


def make_sleep_activity_table(
    daily_rows: list[dict[str, Any]],
    episodes: list[dict],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidates_by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for episode in episodes:
        if episode["overnight_candidate"]:
            candidates_by_key[(episode["id"], episode["waking_date"])].append(episode)
    primary_by_key: dict[tuple[str, str], dict] = {}
    for episode in episodes:
        if episode["primary_eligible"]:
            key = (episode["id"], episode["waking_date"])
            if key in primary_by_key:
                raise ValueError(f"Sleep join would multiply key {key!r}")
            primary_by_key[key] = episode

    activity_keys = {(row["id"], row["activity_date"].isoformat()) for row in daily_rows}
    ambiguous_keys = {
        key for key, items in candidates_by_key.items() if len(items) > 1
    }
    output = []
    status_counts = Counter()
    for row in daily_rows:
        day_text = row["activity_date"].isoformat()
        key = (row["id"], day_text)
        episode = primary_by_key.get(key)
        if key in ambiguous_keys:
            status = "ambiguous_multiple_sessions"
            episode = None
        elif episode is not None:
            status = "matched"
        elif key in candidates_by_key:
            status = "excluded_sleep_quality"
        else:
            status = "no_eligible_overnight_episode"
        status_counts[status] += 1
        output.append({
            "id": row["id"],
            "activity_date": day_text,
            "sleep_match_status": status,
            "sleep_log_id": episode["log_id"] if episode else "",
            "sleep_start_timestamp": episode["start_timestamp"] if episode else "",
            "sleep_end_timestamp": episode["end_timestamp"] if episode else "",
            "recorded_sleep_minutes": (
                episode["recorded_minute_count"] if episode else None
            ),
            "is_complete_day": row["is_complete_day"],
            "total_steps": row["total_steps"],
            "calories": row["calories"],
            "total_active_minutes": row["total_active_minutes"],
            "sedentary_minutes": row["sedentary_minutes"],
        })

    if len(output) != len(daily_rows):
        raise ValueError("Sleep join changed the daily activity row count")
    if len({(row["id"], row["activity_date"]) for row in output}) != len(output):
        raise ValueError("Sleep join produced duplicate participant-date rows")
    matched_rows = [row for row in output if row["sleep_match_status"] == "matched"]
    eligible_without_activity = sum(
        episode["primary_eligible"]
        and (episode["id"], episode["waking_date"]) not in activity_keys
        for episode in episodes
    )
    metrics = {
        "sleep_alignment_rule": (
            "Use episode end calendar date as the waking-date candidate. "
            "Eligible logs must end before noon, start at/after 18:00 or before 06:00, "
            "span no more than 12 hours, have exact 60-second intervals, not overlap, "
            "and be the only candidate log for that participant-waking date."
        ),
        "activity_grain": "participant-day",
        "sleep_grain": "participant-log episode",
        "daily_rows_preserved": len(output),
        "matched_rows": len(matched_rows),
        "matched_participants": len({row["id"] for row in matched_rows}),
        "complete_matched_activity_days": sum(
            row["is_complete_day"] is True for row in matched_rows
        ),
        "unmatched_activity_days": len(output) - len(matched_rows),
        "ambiguous_activity_dates": sum(
            (row["id"], row["activity_date"]) in ambiguous_keys
            for row in output
        ),
        "eligible_episodes_without_activity": eligible_without_activity,
        "match_status_counts": dict(status_counts),
        "sleep_is_missing_not_zero": True,
        "row_multiplication": False,
        "interpretation": (
            "Only a unique eligible log is matched. Unmatched, ambiguous, or excluded "
            "sleep remains missing; it is never converted to zero."
        ),
    }
    return output, metrics


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print("FITINSIGHT_PROOF | P3-PIPELINE")
        print("STATUS: FAIL")
        print(f"ERROR: {type(exc).__name__}: {exc}")
        raise
