"""Coverage-aware, exploratory anomaly screens for Phase 5."""

from __future__ import annotations

import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from .phase5_common import (
        DAILY_PATH,
        EVIDENCE_ROOT,
        GENERATED_ROOT,
        load_daily_rows,
        proof,
        quantile,
        write_csv,
        write_json,
    )
except ImportError:  # Running as ``python src/anomaly_detection.py``.
    from phase5_common import (  # type: ignore
        DAILY_PATH,
        EVIDENCE_ROOT,
        GENERATED_ROOT,
        load_daily_rows,
        proof,
        quantile,
        write_csv,
        write_json,
    )


P3_CANDIDATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports" / "generated" / "eda" / "tables" / "anomaly_candidates.csv"
)
P3_METRICS_PATH = (
    Path(__file__).resolve().parents[1]
    / "reports" / "evidence" / "P3" / "outlier_screen_metrics.json"
)
IQR_MULTIPLIER = 1.5
MIN_WITHIN_PERSON_DAYS = 5
MODIFIED_Z_THRESHOLD = 3.5
KNN_K_VALUES = (5, 10)
KNN_TOP_FRACTION = 0.05
KNN_FEATURES = (
    "steps_per_recorded_hour",
    "calories_per_recorded_hour",
    "active_share",
)


def daily_key(row: dict[str, Any]) -> tuple[str, str]:
    day = row["activity_date"]
    return str(row["id"]), day.isoformat() if hasattr(day, "isoformat") else str(day)


def active_share(row: dict[str, Any]) -> float | None:
    denominator = row["total_recorded_minutes"]
    numerator = row["total_active_minutes"]
    if denominator is None or numerator is None or denominator <= 0:
        return None
    return numerator / denominator


def _metric_value(row: dict[str, Any], field: str) -> float | None:
    if field == "active_share":
        return active_share(row)
    value = row.get(field)
    return float(value) if value is not None else None


def load_phase3_candidate_flags(
    rows: list[dict[str, Any]],
    candidate_path: Path | None = None,
    metrics_path: Path | None = None,
) -> dict[str, Any]:
    """Reuse, validate, and keep the distinct Phase 3 daily and sleep flags."""
    candidate_file = candidate_path or P3_CANDIDATE_PATH
    metrics_file = metrics_path or P3_METRICS_PATH
    if not candidate_file.is_file() or not metrics_file.is_file():
        raise FileNotFoundError(
            "Phase 3 anomaly outputs are required; run python src/eda_analysis.py first"
        )
    known_daily = {daily_key(row) for row in rows}
    daily_flags: dict[tuple[str, str], list[str]] = {}
    daily_rows: list[dict[str, Any]] = []
    sleep_rows: list[dict[str, Any]] = []
    with candidate_file.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"record_type", "id", "date", "log_id", "flags"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("Unexpected Phase 3 anomaly candidate schema")
        for raw in reader:
            if raw["record_type"] == "participant_day":
                key = (raw["id"], raw["date"])
                if key not in known_daily:
                    raise ValueError(f"Phase 3 candidate is absent from daily data: {key}")
                if key in daily_flags:
                    raise ValueError(f"Duplicate Phase 3 daily candidate: {key}")
                flags = [flag.strip() for flag in raw["flags"].split(";") if flag.strip()]
                if not flags:
                    raise ValueError(f"Phase 3 daily candidate has no reason: {key}")
                daily_flags[key] = flags
                daily_rows.append(dict(raw))
            elif raw["record_type"] == "sleep_episode":
                sleep_rows.append(dict(raw))
            else:
                raise ValueError(f"Unknown Phase 3 record grain: {raw['record_type']!r}")
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    if len(daily_rows) != metrics.get("daily_candidate_rows"):
        raise ValueError("Phase 3 daily candidate count does not match its evidence JSON")
    if len(sleep_rows) != metrics.get("sleep_episode_candidate_rows"):
        raise ValueError("Phase 3 sleep candidate count does not match its evidence JSON")
    expected_daily_flags = Counter(metrics.get("daily_flag_counts", {}))
    observed_daily_flags = Counter(
        flag for flags in daily_flags.values() for flag in flags
    )
    if expected_daily_flags != observed_daily_flags:
        raise ValueError("Phase 3 daily flag counts do not match its evidence JSON")
    return {
        "daily_flags": daily_flags,
        "daily_rows": daily_rows,
        "sleep_rows": sleep_rows,
        "metrics": metrics,
        "candidate_path": candidate_file,
        "metrics_path": metrics_file,
    }


def global_iqr_screen(
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]]]:
    """Apply linear-interpolated 1.5×IQR fences to declared daily fields."""
    fields = [
        "total_steps",
        "calories",
        "total_distance",
        "total_active_minutes",
        "sedentary_minutes",
        "total_recorded_minutes",
        "active_share",
    ]
    fences: dict[str, dict[str, Any]] = {}
    flags: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for field in fields:
        values = [
            value for row in rows
            if (value := _metric_value(row, field)) is not None
        ]
        q1 = quantile(values, 0.25)
        q3 = quantile(values, 0.75)
        if q1 is None or q3 is None:
            fences[field] = {
                "q1": None, "q3": None, "iqr": None,
                "lower_fence": None, "upper_fence": None,
                "observed": len(values), "missing": len(rows) - len(values),
                "low_flags": 0, "high_flags": 0, "flagged_rows": 0,
            }
            continue
        spread = q3 - q1
        lower = q1 - IQR_MULTIPLIER * spread
        upper = q3 + IQR_MULTIPLIER * spread
        low_count = 0
        high_count = 0
        for row in rows:
            value = _metric_value(row, field)
            if value is None:
                continue
            tail = "low" if value < lower else "high" if value > upper else None
            if tail:
                low_count += tail == "low"
                high_count += tail == "high"
                flags[daily_key(row)].append(
                    {
                        "field": field,
                        "tail": tail,
                        "value": value,
                        "q1": q1,
                        "q3": q3,
                        "iqr": spread,
                        "lower_fence": lower,
                        "upper_fence": upper,
                    }
                )
        fences[field] = {
            "q1": q1,
            "q3": q3,
            "iqr": spread,
            "lower_fence": lower,
            "upper_fence": upper,
            "observed": len(values),
            "missing": len(rows) - len(values),
            "low_flags": low_count,
            "high_flags": high_count,
            "flagged_rows": low_count + high_count,
        }
    return fences, dict(flags)


def within_person_robust_screen(
    rows: list[dict[str, Any]],
    min_days: int = MIN_WITHIN_PERSON_DAYS,
    threshold: float = MODIFIED_Z_THRESHOLD,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], list[dict[str, Any]]], dict[str, Any]]:
    """Use modified MAD scores, with a finite IQR fallback when MAD is zero."""
    fields = ("total_steps", "active_share")
    by_person: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_person[str(row["id"])].append(row)
    output: list[dict[str, Any]] = []
    flagged: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    summary = {
        "minimum_days": min_days,
        "threshold_absolute_modified_z": threshold,
        "metrics": {},
        "zero_mad_groups": 0,
        "iqr_fallback_groups": 0,
        "unscalable_groups": 0,
    }
    group_status: Counter[str] = Counter()
    for participant in sorted(by_person):
        participant_rows = by_person[participant]
        for field in fields:
            valid = [
                (row, _metric_value(row, field))
                for row in participant_rows
                if _metric_value(row, field) is not None
            ]
            values = [float(value) for _, value in valid]
            median = quantile(values, 0.5)
            mad = quantile([abs(value - median) for value in values], 0.5) if median is not None else None
            q1 = quantile(values, 0.25)
            q3 = quantile(values, 0.75)
            iqr = q3 - q1 if q1 is not None and q3 is not None else None
            score_method = "MAD"
            scale = None
            if len(values) < min_days:
                score_method = "insufficient_days"
                group_status[score_method] += 1
            elif mad is not None and mad > 0:
                scale = mad / 0.6744897501960817
            elif iqr is not None and iqr > 0:
                scale = iqr / 1.3489795003921634
                score_method = "IQR_fallback_zero_MAD"
                summary["zero_mad_groups"] += 1
                summary["iqr_fallback_groups"] += 1
                group_status[score_method] += 1
            else:
                score_method = "zero_MAD_and_IQR"
                summary["zero_mad_groups"] += 1
                summary["unscalable_groups"] += 1
                group_status[score_method] += 1
            for row, raw_value in valid:
                score = (
                    (float(raw_value) - median) / scale
                    if scale is not None and median is not None
                    else None
                )
                is_flagged = score is not None and abs(score) > threshold
                record = {
                    "participant_id": participant,
                    "date": row["activity_date"].isoformat(),
                    "metric": field,
                    "value": raw_value,
                    "participant_days": len(values),
                    "minimum_days": min_days,
                    "median": median,
                    "mad": mad,
                    "iqr": iqr,
                    "score": score,
                    "score_method": score_method,
                    "threshold": threshold,
                    "flagged": is_flagged,
                    "status": (
                        "scored"
                        if score is not None
                        else "not_scored_zero_robust_scale"
                        if score_method == "zero_MAD_and_IQR"
                        else "insufficient_days"
                    ),
                }
                output.append(record)
                if is_flagged:
                    flagged[daily_key(row)].append(
                        {
                            "metric": field,
                            "score": score,
                            "score_method": score_method,
                            "threshold": threshold,
                        }
                    )
    summary["groups_by_status"] = dict(sorted(group_status.items()))
    for field in fields:
        metric_rows = [row for row in output if row["metric"] == field]
        summary["metrics"][field] = {
            "scored_rows": sum(row["score"] is not None for row in metric_rows),
            "flagged_rows": sum(row["flagged"] for row in metric_rows),
            "participants": len({row["participant_id"] for row in metric_rows}),
        }
    return output, dict(flagged), summary


def _knn_features(row: dict[str, Any]) -> tuple[float, float, float]:
    recorded = row["total_recorded_minutes"]
    if recorded is None or recorded <= 0:
        raise ValueError("KNN rate features require positive recorded minutes")
    share = active_share(row)
    if share is None:
        raise ValueError("KNN active-share feature is missing")
    return (
        row["total_steps"] * 60.0 / recorded,
        row["calories"] * 60.0 / recorded,
        share,
    )


def knn_screen(
    rows: list[dict[str, Any]],
    k_values: tuple[int, ...] = KNN_K_VALUES,
    top_fraction: float = KNN_TOP_FRACTION,
) -> tuple[list[dict[str, Any]], dict[tuple[str, int], set[tuple[str, str]]], list[dict[str, Any]]]:
    """Rank standardized participant-days by mean distance to k nearest peers."""
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")
    scopes = [
        ("pooled", rows),
        ("complete_days", [row for row in rows if row["is_complete_day"]]),
        ("incomplete_days", [row for row in rows if not row["is_complete_day"]]),
    ]
    output: list[dict[str, Any]] = []
    candidate_keys: dict[tuple[str, int], set[tuple[str, str]]] = {}
    summaries: list[dict[str, Any]] = []
    for scope, scope_rows in scopes:
        n = len(scope_rows)
        if n == 0:
            continue
        feature_rows = [_knn_features(row) for row in scope_rows]
        means = [
            sum(vector[index] for vector in feature_rows) / n
            for index in range(len(KNN_FEATURES))
        ]
        standard_deviations = [
            math.sqrt(
                sum((vector[index] - means[index]) ** 2 for vector in feature_rows) / n
            )
            for index in range(len(KNN_FEATURES))
        ]
        scaled = [
            tuple(
                (vector[index] - means[index]) / standard_deviations[index]
                if standard_deviations[index] > 0 else 0.0
                for index in range(len(KNN_FEATURES))
            )
            for vector in feature_rows
        ]
        distances: list[list[float]] = []
        for index, vector in enumerate(scaled):
            neighbors = []
            for other_index, other in enumerate(scaled):
                if index == other_index:
                    continue
                distance = math.sqrt(
                    sum((left - right) ** 2 for left, right in zip(vector, other))
                )
                neighbors.append(distance)
            distances.append(sorted(neighbors))
        for requested_k in k_values:
            if requested_k < 1:
                raise ValueError("k must be positive")
            if n < 2:
                continue
            effective_k = min(requested_k, n - 1)
            scores = [
                sum(neighbors[:effective_k]) / effective_k
                for neighbors in distances
            ]
            ranked_indices = sorted(
                range(n),
                key=lambda index: (
                    -scores[index],
                    str(scope_rows[index]["id"]),
                    scope_rows[index]["activity_date"],
                ),
            )
            top_count = max(1, math.ceil(top_fraction * n - 1e-12))
            flagged_indices = set(ranked_indices[:top_count])
            scope_flags = {
                daily_key(scope_rows[index]) for index in flagged_indices
            }
            candidate_keys[(scope, requested_k)] = scope_flags
            threshold_score = scores[ranked_indices[top_count - 1]]
            rank_for_index = {
                row_index: rank
                for rank, row_index in enumerate(ranked_indices, start=1)
            }
            for index, row in enumerate(scope_rows):
                rank = rank_for_index[index]
                output.append(
                    {
                        "scope": scope,
                        "requested_k": requested_k,
                        "effective_k": effective_k,
                        "participant_id": row["id"],
                        "date": row["activity_date"].isoformat(),
                        "neighbor_mean_distance": scores[index],
                        "rank_highest_first": rank,
                        "rank_percentile": (
                            (n - rank) / (n - 1) if n > 1 else 1.0
                        ),
                        "cohort_size": n,
                        "top_fraction": top_fraction,
                        "top_candidate_count": top_count,
                        "cutoff_score": threshold_score,
                        "top_candidate": index in flagged_indices,
                    }
                )
            score_values = scores
            summaries.append(
                {
                    "scope": scope,
                    "requested_k": requested_k,
                    "effective_k": effective_k,
                    "cohort_size": n,
                    "top_fraction": top_fraction,
                    "top_candidate_count": top_count,
                    "score_median": quantile(score_values, 0.5),
                    "score_p90": quantile(score_values, 0.9),
                    "score_p95": quantile(score_values, 0.95),
                    "score_max": max(score_values),
                    "cutoff_score": threshold_score,
                    "feature_names": list(KNN_FEATURES),
                }
            )
    return output, candidate_keys, summaries


def _distance_screens(
    rows: list[dict[str, Any]],
) -> tuple[set[tuple[str, str]], set[tuple[str, str]], dict[str, Any]]:
    p2_keys = {
        daily_key(row) for row in rows if row["distance_discrepancy"]
    }
    p1_keys = set()
    for row in rows:
        component_sum = row["component_distance_sum"]
        total = row["total_distance"]
        if component_sum is not None and total is not None:
            if abs(component_sum - total) > 0.01:
                p1_keys.add(daily_key(row))
    return p1_keys, p2_keys, {
        "phase1_definition": (
            "|component_distance_sum - total_distance| > 0.01 "
            "(plain absolute-difference screen)"
        ),
        "phase1_candidate_days": len(p1_keys),
        "phase2_definition": (
            "committed Phase 2 distance_discrepancy flag using the existing "
            "NumPy-isclose-equivalent tolerance"
        ),
        "phase2_candidate_days": len(p2_keys),
        "intersection_days": len(p1_keys & p2_keys),
        "phase1_only_days": len(p1_keys - p2_keys),
        "phase2_only_days": len(p2_keys - p1_keys),
        "not_interchangeable": True,
    }


def _method_sets(
    rows: list[dict[str, Any]],
    p3_flags: dict[tuple[str, str], list[str]],
    global_flags: dict[tuple[str, str], list[dict[str, Any]]],
    within_flags: dict[tuple[str, str], list[dict[str, Any]]],
    knn_flags: dict[tuple[str, int], set[tuple[str, str]]],
    p1_keys: set[tuple[str, str]],
    p2_keys: set[tuple[str, str]],
) -> dict[str, set[tuple[str, str]]]:
    zero_step_flags = {
        daily_key(row)
        for row in rows
        if row["total_steps"] == 0
        and (
            row["calories"] > 0
            or (row["total_active_minutes"] is not None
                and row["total_active_minutes"] > 0)
        )
    }
    complete_k5 = knn_flags.get(("complete_days", 5), set())
    incomplete_k5 = knn_flags.get(("incomplete_days", 5), set())
    complete_k10 = knn_flags.get(("complete_days", 10), set())
    incomplete_k10 = knn_flags.get(("incomplete_days", 10), set())
    return {
        "phase3_daily_candidates": set(p3_flags),
        "global_iqr_any_field": set(global_flags),
        "within_person_robust": set(within_flags),
        "knn_pooled_k5_top_5pct": set(knn_flags.get(("pooled", 5), set())),
        "knn_pooled_k10_top_5pct": set(knn_flags.get(("pooled", 10), set())),
        "knn_stratified_k5_top_5pct": set(complete_k5 | incomplete_k5),
        "knn_stratified_k10_top_5pct": set(complete_k10 | incomplete_k10),
        "zero_steps_with_positive_calories_or_activity": zero_step_flags,
        "phase1_absolute_distance_gt_0_01": p1_keys,
        "phase2_distance_flag": p2_keys,
    }


def _overlap_tables(
    method_sets: dict[str, set[tuple[str, str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    counts = [
        {
            "method": name,
            "candidate_days": len(values),
            "grain": "participant-day",
        }
        for name, values in sorted(method_sets.items())
    ]
    overlaps = []
    names = sorted(method_sets)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1:]:
            a, b = method_sets[left], method_sets[right]
            intersection = a & b
            union = a | b
            overlaps.append(
                {
                    "method_a": left,
                    "method_b": right,
                    "candidate_days_a": len(a),
                    "candidate_days_b": len(b),
                    "intersection_days": len(intersection),
                    "union_days": len(union),
                    "jaccard": len(intersection) / len(union) if union else None,
                }
            )
    return counts, overlaps


def _candidate_registry(
    rows: list[dict[str, Any]],
    p3_flags: dict[tuple[str, str], list[str]],
    global_flags: dict[tuple[str, str], list[dict[str, Any]]],
    within_flags: dict[tuple[str, str], list[dict[str, Any]]],
    knn_flags: dict[tuple[str, int], set[tuple[str, str]]],
    p1_keys: set[tuple[str, str]],
    p2_keys: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        key = daily_key(row)
        active = active_share(row)
        p3 = p3_flags.get(key, [])
        global_rows = global_flags.get(key, [])
        within_rows = within_flags.get(key, [])
        flags = []
        if p3:
            flags.append("phase3_candidate")
        if global_rows:
            flags.append("global_iqr")
        if within_rows:
            flags.append("within_person_robust")
        if key in knn_flags.get(("pooled", 5), set()):
            flags.append("knn_pooled_k5")
        if key in knn_flags.get(("pooled", 10), set()):
            flags.append("knn_pooled_k10")
        if key in (
            knn_flags.get(("complete_days", 5), set())
            | knn_flags.get(("incomplete_days", 5), set())
        ):
            flags.append("knn_stratified_k5")
        if key in (
            knn_flags.get(("complete_days", 10), set())
            | knn_flags.get(("incomplete_days", 10), set())
        ):
            flags.append("knn_stratified_k10")
        if key in p1_keys:
            flags.append("phase1_absolute_distance_gt_0_01")
        if key in p2_keys:
            flags.append("phase2_distance_flag")
        if row["total_steps"] == 0 and (
            row["calories"] > 0 or (row["total_active_minutes"] or 0) > 0
        ):
            flags.append("zero_steps_positive_calories_or_activity")
        result.append(
            {
                "participant_id": row["id"],
                "date": row["activity_date"].isoformat(),
                "complete_day": row["is_complete_day"],
                "total_steps": row["total_steps"],
                "calories": row["calories"],
                "total_distance": row["total_distance"],
                "component_distance_sum": row["component_distance_sum"],
                "component_distance_absolute_gap": (
                    abs(row["component_distance_sum"] - row["total_distance"])
                    if row["component_distance_sum"] is not None
                    and row["total_distance"] is not None
                    else None
                ),
                "total_active_minutes": row["total_active_minutes"],
                "total_recorded_minutes": row["total_recorded_minutes"],
                "active_share": active,
                "phase3_flags": p3,
                "global_iqr_flags": [
                    f"{entry['field']}:{entry['tail']}" for entry in global_rows
                ],
                "within_person_flags": [
                    {
                        "metric": entry["metric"],
                        "score": entry["score"],
                        "method": entry["score_method"],
                    }
                    for entry in within_rows
                ],
                "knn_pooled_k5": key in knn_flags.get(("pooled", 5), set()),
                "knn_pooled_k10": key in knn_flags.get(("pooled", 10), set()),
                "knn_stratified_k5": key in (
                    knn_flags.get(("complete_days", 5), set())
                    | knn_flags.get(("incomplete_days", 5), set())
                ),
                "knn_stratified_k10": key in (
                    knn_flags.get(("complete_days", 10), set())
                    | knn_flags.get(("incomplete_days", 10), set())
                ),
                "phase1_absolute_distance_gt_0_01": key in p1_keys,
                "phase2_distance_flag": key in p2_keys,
                "candidate_methods": flags,
                "any_candidate": bool(flags),
            }
        )
    return result


def _review_cases(
    rows: list[dict[str, Any]],
    registry: list[dict[str, Any]],
    within_rows: list[dict[str, Any]],
    knn_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    row_by_key = {daily_key(row): row for row in rows}
    registry_by_key = {
        (row["participant_id"], row["date"]): row for row in registry
    }
    roles: dict[tuple[str, str], list[str]] = defaultdict(list)

    def add(role: str, key: tuple[str, str] | None) -> None:
        if key is not None and key in row_by_key and role not in roles[key]:
            roles[key].append(role)

    p3_candidates = sorted(
        (key for key, row in registry_by_key.items() if row["phase3_flags"])
    )
    add("Existing Phase 3 participant-day candidate", p3_candidates[0] if p3_candidates else None)
    p1_only = [
        key for key, row in registry_by_key.items()
        if row["phase1_absolute_distance_gt_0_01"] and not row["phase2_distance_flag"]
    ]
    p1_only.sort(
        key=lambda key: -abs(
            row_by_key[key]["component_distance_sum"]
            - row_by_key[key]["total_distance"]
        )
    )
    add("Strict absolute-distance screen only", p1_only[0] if p1_only else None)
    p2_candidates = [
        key for key, row in registry_by_key.items() if row["phase2_distance_flag"]
    ]
    p2_candidates.sort(
        key=lambda key: -abs(
            row_by_key[key]["component_distance_sum"]
            - row_by_key[key]["total_distance"]
        )
    )
    add("Phase 2 distance-flag example", p2_candidates[0] if p2_candidates else None)
    high_steps = [
        row for row in registry
        if any(flag == "total_steps:high" for flag in row["global_iqr_flags"])
    ]
    high_steps.sort(key=lambda row: (-row["total_steps"], row["date"]))
    add(
        "Global upper IQR step screen",
        (high_steps[0]["participant_id"], high_steps[0]["date"])
        if high_steps else None,
    )
    within_candidates = [row for row in within_rows if row["flagged"]]
    within_candidates.sort(key=lambda row: -abs(row["score"]))
    add(
        "Within-participant robust score",
        (within_candidates[0]["participant_id"], within_candidates[0]["date"])
        if within_candidates else None,
    )
    pooled_k5 = [
        row for row in knn_rows
        if row["scope"] == "pooled"
        and row["requested_k"] == 5 and row["top_candidate"]
    ]
    pooled_k5.sort(key=lambda row: -row["neighbor_mean_distance"])
    add(
        "Pooled kNN top-five-percent score",
        (pooled_k5[0]["participant_id"], pooled_k5[0]["date"])
        if pooled_k5 else None,
    )
    incomplete = [
        row for row in rows
        if not row["is_complete_day"] and row["total_recorded_minutes"] > 0
    ]
    incomplete.sort(key=lambda row: (row["total_recorded_minutes"], row["id"], row["activity_date"]))
    add(
        "Shortest positive-duration incomplete record",
        daily_key(incomplete[0]) if incomplete else None,
    )
    latest_date = max((row["activity_date"] for row in rows), default=None)
    boundary = [
        row for row in rows if row["activity_date"] == latest_date
    ]
    if boundary:
        boundary.sort(key=lambda row: (row["id"], row["activity_date"]))
        add("Last observed date retained in primary screen", daily_key(boundary[0]))

    output = []
    for index, key in enumerate(sorted(roles), start=1):
        source = row_by_key[key]
        reg = registry_by_key[key]
        output.append(
            {
                "case_id": f"CASE-{index:03d}",
                "participant_id": source["id"],
                "date": source["activity_date"].isoformat(),
                "selection_reasons": roles[key],
                "total_steps": source["total_steps"],
                "calories": source["calories"],
                "total_distance": source["total_distance"],
                "component_distance_sum": source["component_distance_sum"],
                "component_distance_absolute_gap": (
                    abs(source["component_distance_sum"] - source["total_distance"])
                    if source["component_distance_sum"] is not None
                    and source["total_distance"] is not None else None
                ),
                "total_active_minutes": source["total_active_minutes"],
                "total_recorded_minutes": source["total_recorded_minutes"],
                "active_share": active_share(source),
                "complete_day": source["is_complete_day"],
                "phase3_flags": reg["phase3_flags"],
                "global_iqr_flags": reg["global_iqr_flags"],
                "within_person_flags": reg["within_person_flags"],
                "candidate_methods": reg["candidate_methods"],
                "phase1_absolute_distance_gt_0_01": reg[
                    "phase1_absolute_distance_gt_0_01"
                ],
                "phase2_distance_flag": reg["phase2_distance_flag"],
                "interpretation": (
                    "Retained observed record selected for focused review; "
                    "a screen is not a confirmed error or an inferred cause."
                ),
            }
        )
    return output


def _date_boundary_rows(
    rows: list[dict[str, Any]],
    p3_flags: dict[tuple[str, str], list[str]],
    primary_sets: dict[str, set[tuple[str, str]]],
    boundary_date: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    without_boundary = [
        row for row in rows if row["activity_date"].isoformat() != boundary_date
    ]
    without_keys = {daily_key(row) for row in without_boundary}
    p3_without = {key for key in p3_flags if key in without_keys}
    global_fences, global_flags = global_iqr_screen(without_boundary)
    within_rows, within_flags, within_summary = within_person_robust_screen(
        without_boundary
    )
    knn_rows, knn_flags, knn_summary = knn_screen(without_boundary)
    p1_without, p2_without, _ = _distance_screens(without_boundary)
    recomputed_sets = _method_sets(
        without_boundary,
        {key: p3_flags[key] for key in p3_without},
        global_flags,
        within_flags,
        knn_flags,
        p1_without,
        p2_without,
    )
    rows_out = []
    for method, primary in sorted(primary_sets.items()):
        sensitivity = recomputed_sets.get(method, set())
        rows_out.append(
            {
                "method": method,
                "primary_candidate_days": len(primary),
                "excluding_last_date_candidate_days": len(sensitivity),
                "change_after_excluding_last_date": len(sensitivity) - len(primary),
                "boundary_date": boundary_date,
                "primary_includes_boundary": True,
                "sensitivity_recomputed": method not in ("phase3_daily_candidates",),
                "note": (
                    "Phase 3 candidate flags are reused from their original run "
                    "and filtered only; other screens are recalculated."
                ),
            }
        )
    return rows_out, {
        "boundary_date": boundary_date,
        "primary_rows": len(rows),
        "sensitivity_rows": len(without_boundary),
        "primary_retains_boundary": True,
        "global_iqr_refit": True,
        "within_person_refit": True,
        "knn_refit": True,
        "phase3_flags_reused_not_refit": True,
        "global_iqr_fences_excluding_boundary": global_fences,
        "within_person_excluding_boundary": within_summary,
        "knn_excluding_boundary": knn_summary,
    }


def run_anomaly_analysis(
    input_path: Path | None = None,
    generated_dir: Path | None = None,
    evidence_dir: Path | None = None,
    p3_candidate_path: Path | None = None,
    p3_metrics_path: Path | None = None,
) -> dict[str, Any]:
    rows = load_daily_rows(input_path or DAILY_PATH)
    proof(
        "P5-ANOMALY-LOAD",
        participant_days=len(rows),
        participants=len({row["id"] for row in rows}),
        complete_days=sum(row["is_complete_day"] for row in rows),
        incomplete_days=sum(not row["is_complete_day"] for row in rows),
        zero_step_days=sum(row["total_steps"] == 0 for row in rows),
        boundary_date=max(row["activity_date"] for row in rows).isoformat(),
        rows_removed=0,
    )
    p3 = load_phase3_candidate_flags(rows, p3_candidate_path, p3_metrics_path)
    p3_flags = p3["daily_flags"]
    p3_flag_counts = Counter(
        flag for flags in p3_flags.values() for flag in flags
    )
    proof(
        "P5-ANOMALY-P3-REUSE",
        daily_candidate_rows=len(p3["daily_rows"]),
        sleep_episode_candidate_rows=len(p3["sleep_rows"]),
        daily_flag_counts=dict(sorted(p3_flag_counts.items())),
        separate_grains=["participant_day", "sleep_episode"],
        phase3_flags_preserved=True,
    )

    fences, global_flags = global_iqr_screen(rows)
    global_keys = set(global_flags)
    global_rows = [
        {
            "participant_id": key[0],
            "date": key[1],
            **entry,
        }
        for key in sorted(global_flags)
        for entry in global_flags[key]
    ]
    proof(
        "P5-ANOMALY-GLOBAL-IQR",
        rows=len(rows),
        fields=list(fences),
        multiplier=IQR_MULTIPLIER,
        flagged_rows=len(global_keys),
        fence_summary={
            field: {
                "lower": value["lower_fence"],
                "upper": value["upper_fence"],
                "low": value["low_flags"],
                "high": value["high_flags"],
            }
            for field, value in fences.items()
        },
        candidates_retained=True,
    )

    within_rows, within_flags, within_summary = within_person_robust_screen(rows)
    proof(
        "P5-ANOMALY-WITHIN-PERSON",
        rows_scored=len(within_rows),
        participant_day_candidates=len(within_flags),
        flagged_metric_rows=sum(row["flagged"] for row in within_rows),
        minimum_days=MIN_WITHIN_PERSON_DAYS,
        threshold_absolute_score=MODIFIED_Z_THRESHOLD,
        zero_mad_groups=within_summary["zero_mad_groups"],
        iqr_fallback_groups=within_summary["iqr_fallback_groups"],
        unscalable_groups=within_summary["unscalable_groups"],
    )

    knn_rows, knn_flags, knn_summary = knn_screen(rows)
    proof(
        "P5-ANOMALY-KNN",
        score_rows=len(knn_rows),
        scopes=sorted({row["scope"] for row in knn_rows}),
        k_values=list(KNN_K_VALUES),
        top_fraction=KNN_TOP_FRACTION,
        features=list(KNN_FEATURES),
        score_summaries=knn_summary,
        features_use_recorded_hour_rates=True,
        coverage_stratified=True,
    )

    p1_keys, p2_keys, distance_summary = _distance_screens(rows)
    method_sets = _method_sets(
        rows, p3_flags, global_flags, within_flags, knn_flags, p1_keys, p2_keys
    )
    detector_counts, overlaps = _overlap_tables(method_sets)
    proof(
        "P5-ANOMALY-OVERLAP",
        detector_counts={row["method"]: row["candidate_days"] for row in detector_counts},
        pairwise_comparisons=len(overlaps),
        phase1_distance_days=distance_summary["phase1_candidate_days"],
        phase2_distance_days=distance_summary["phase2_candidate_days"],
        distance_definitions_kept_separate=True,
    )

    registry = _candidate_registry(
        rows, p3_flags, global_flags, within_flags, knn_flags, p1_keys, p2_keys
    )
    review_cases = _review_cases(rows, registry, within_rows, knn_rows)
    boundary_date = max(row["activity_date"] for row in rows).isoformat()
    boundary_rows, boundary_summary = _date_boundary_rows(
        rows, p3_flags, method_sets, boundary_date
    )
    proof(
        "P5-ANOMALY-BOUNDARY",
        boundary_date=boundary_date,
        primary_rows=len(rows),
        sensitivity_rows=len(rows) - sum(
            row["activity_date"].isoformat() == boundary_date for row in rows
        ),
        primary_retains_boundary=True,
        recomputed_screens=[
            "global_iqr", "within_person_robust", "knn", "distance_screens"
        ],
        reused_phase3_flags=True,
    )
    proof(
        "P5-ANOMALY-CASE-REVIEW",
        selected_cases=len(review_cases),
        case_ids_only_in_machine_evidence=True,
        candidate_rows_removed=0,
        causes_inferred=0,
        sleep_episode_candidates_kept_separate=len(p3["sleep_rows"]),
    )

    out = generated_dir or GENERATED_ROOT / "anomalies"
    evidence = evidence_dir or EVIDENCE_ROOT
    out.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    write_csv(
        out / "global_iqr_metrics.csv",
        [
            "field", "q1", "q3", "iqr", "lower_fence", "upper_fence",
            "observed", "missing", "low_flags", "high_flags", "flagged_rows",
            "multiplier",
        ],
        [
            {"field": field, **values, "multiplier": IQR_MULTIPLIER}
            for field, values in sorted(fences.items())
        ],
    )
    write_csv(
        out / "global_iqr_flags.csv",
        [
            "participant_id", "date", "field", "tail", "value", "q1", "q3",
            "iqr", "lower_fence", "upper_fence",
        ],
        global_rows,
    )
    write_csv(
        out / "within_person_scores.csv",
        [
            "participant_id", "date", "metric", "value", "participant_days",
            "minimum_days", "median", "mad", "iqr", "score", "score_method",
            "threshold", "flagged", "status",
        ],
        within_rows,
    )
    write_csv(
        out / "knn_scores.csv",
        [
            "scope", "requested_k", "effective_k", "participant_id", "date",
            "neighbor_mean_distance", "rank_highest_first", "rank_percentile",
            "cohort_size", "top_fraction", "top_candidate_count", "cutoff_score",
            "top_candidate",
        ],
        knn_rows,
    )
    write_csv(
        out / "knn_summary.csv",
        [
            "scope", "requested_k", "effective_k", "cohort_size", "top_fraction",
            "top_candidate_count", "score_median", "score_p90", "score_p95",
            "score_max", "cutoff_score", "feature_names",
        ],
        knn_summary,
    )
    write_csv(
        out / "phase3_daily_candidate_flags.csv",
        ["participant_id", "date", "flags", "source"],
        [
            {
                "participant_id": key[0],
                "date": key[1],
                "flags": flags,
                "source": "reports/generated/eda/tables/anomaly_candidates.csv",
            }
            for key, flags in sorted(p3_flags.items())
        ],
    )
    p3_sleep_fields = [
        "record_type", "id", "date", "log_id", "start_timestamp",
        "end_timestamp", "total_steps", "calories", "total_distance",
        "total_active_minutes", "sedentary_minutes", "total_recorded_minutes",
        "flags", "handling",
    ]
    write_csv(out / "phase3_sleep_candidates.csv", p3_sleep_fields, p3["sleep_rows"])
    write_csv(
        out / "candidate_registry.csv",
        [
            "participant_id", "date", "complete_day", "total_steps", "calories",
            "total_distance", "component_distance_sum",
            "component_distance_absolute_gap", "total_active_minutes",
            "total_recorded_minutes", "active_share", "phase3_flags",
            "global_iqr_flags", "within_person_flags", "knn_pooled_k5",
            "knn_pooled_k10", "knn_stratified_k5", "knn_stratified_k10",
            "phase1_absolute_distance_gt_0_01", "phase2_distance_flag",
            "candidate_methods", "any_candidate",
        ],
        registry,
    )
    write_csv(
        out / "detector_counts.csv",
        ["method", "candidate_days", "grain"],
        detector_counts,
    )
    write_csv(
        out / "detector_overlaps.csv",
        [
            "method_a", "method_b", "candidate_days_a", "candidate_days_b",
            "intersection_days", "union_days", "jaccard",
        ],
        overlaps,
    )
    write_csv(
        out / "date_boundary_sensitivity.csv",
        [
            "method", "primary_candidate_days", "excluding_last_date_candidate_days",
            "change_after_excluding_last_date", "boundary_date",
            "primary_includes_boundary", "sensitivity_recomputed", "note",
        ],
        boundary_rows,
    )
    write_csv(
        out / "review_cases.csv",
        [
            "case_id", "participant_id", "date", "selection_reasons",
            "total_steps", "calories", "total_distance", "component_distance_sum",
            "component_distance_absolute_gap", "total_active_minutes",
            "total_recorded_minutes", "active_share", "complete_day",
            "phase3_flags", "global_iqr_flags", "within_person_flags",
            "candidate_methods", "phase1_absolute_distance_gt_0_01",
            "phase2_distance_flag", "interpretation",
        ],
        review_cases,
    )

    p3_sleep_flag_counts = Counter(
        flag.strip()
        for row in p3["sleep_rows"]
        for flag in row["flags"].split(";")
        if flag.strip()
    )
    sleep_summary_rows = [
        {
            "record_type": "sleep_episode",
            "candidate_rows": len(p3["sleep_rows"]),
            "flag": flag,
            "flag_rows": count,
            "grain": "participant-log episode; not merged with participant-days",
        }
        for flag, count in sorted(p3_sleep_flag_counts.items())
    ]
    write_csv(
        out / "phase3_sleep_candidate_summary.csv",
        ["record_type", "candidate_rows", "flag", "flag_rows", "grain"],
        sleep_summary_rows,
    )

    boundary_summary["candidate_counts"] = boundary_rows
    metrics = {
        "analysis": "Phase 5 exploratory anomaly screening",
        "grain": "participant-day unless explicitly labelled sleep episode",
        "input_rows": len(rows),
        "participants": len({row["id"] for row in rows}),
        "complete_days": sum(row["is_complete_day"] for row in rows),
        "incomplete_days": sum(not row["is_complete_day"] for row in rows),
        "zero_step_days_retained": sum(row["total_steps"] == 0 for row in rows),
        "phase3_reuse": {
            "daily_candidate_rows": len(p3["daily_rows"]),
            "sleep_episode_candidate_rows": len(p3["sleep_rows"]),
            "daily_flag_counts": dict(sorted(p3_flag_counts.items())),
            "sleep_flag_counts": dict(sorted(p3_sleep_flag_counts.items())),
            "source_candidate_sha256": None,
            "source_metrics_sha256": None,
        },
        "global_iqr": {
            "multiplier": IQR_MULTIPLIER,
            "quantile_convention": "linear interpolation, matching Phase 3",
            "fences": fences,
            "candidate_days_any_field": len(global_keys),
            "flag_rows": len(global_rows),
        },
        "within_person": {
            "minimum_days": MIN_WITHIN_PERSON_DAYS,
            "score_threshold": MODIFIED_Z_THRESHOLD,
            "mad_zero_policy": (
                "Use IQR/1.34898 as a finite fallback when MAD is zero but IQR "
                "is positive; otherwise do not scale or flag."
            ),
            **within_summary,
        },
        "knn": {
            "features": {
                "steps_per_recorded_hour": "total_steps * 60 / total_recorded_minutes",
                "calories_per_recorded_hour": "calories * 60 / total_recorded_minutes",
                "active_share": "total_active_minutes / total_recorded_minutes",
            },
            "standardization": "within each pooled or completeness-defined cohort using population SD",
            "scoring": "mean Euclidean distance to k nearest other participant-days",
            "k_values": list(KNN_K_VALUES),
            "candidate_rule": "top 5 percent by score within each cohort; ceil(n*0.05), deterministic tie order",
            "cohorts": knn_summary,
        },
        "distance_screens": distance_summary,
        "detector_counts": detector_counts,
        "overlap_comparison_count": len(overlaps),
        "date_boundary_sensitivity": boundary_summary,
        "review_case_count": len(review_cases),
        "review_interpretation": (
            "Examples are retained observations for focused review; none is "
            "confirmed erroneous and no cause is inferred."
        ),
        "limitations": [
            "Historical wearable records; population representativeness and units are not established.",
            "Extreme or unusual values are candidate screens, not diagnoses, errors, or health findings.",
            "Incomplete-day status measures recorded minutes and is not device-wear verification.",
            "Pooled kNN ranks may reflect coverage; complete/incomplete stratified scores are separate exploratory comparisons.",
            "The small sample does not support population-level or causal conclusions.",
            "Sleep episodes remain a separate observation grain from participant-days.",
        ],
        "generated_outputs": [
            "global_iqr_metrics.csv", "global_iqr_flags.csv",
            "within_person_scores.csv", "knn_scores.csv", "knn_summary.csv",
            "phase3_daily_candidate_flags.csv", "phase3_sleep_candidates.csv",
            "phase3_sleep_candidate_summary.csv", "candidate_registry.csv",
            "detector_counts.csv", "detector_overlaps.csv",
            "date_boundary_sensitivity.csv", "review_cases.csv",
        ],
    }
    write_json(evidence / "anomaly_metrics.json", metrics)
    proof(
        "P5-ANOMALY-ARTIFACTS",
        daily_registry_rows=len(registry),
        daily_rows_with_any_flag=sum(row["any_candidate"] for row in registry),
        phase3_daily_rows=len(p3["daily_rows"]),
        phase3_sleep_episode_rows=len(p3["sleep_rows"]),
        review_cases=len(review_cases),
        output_tables=len(metrics["generated_outputs"]),
    )
    return {
        "rows": rows,
        "p3": p3,
        "fences": fences,
        "global_flags": global_flags,
        "within_rows": within_rows,
        "within_flags": within_flags,
        "within_summary": within_summary,
        "knn_rows": knn_rows,
        "knn_flags": knn_flags,
        "knn_summary": knn_summary,
        "p1_keys": p1_keys,
        "p2_keys": p2_keys,
        "method_sets": method_sets,
        "detector_counts": detector_counts,
        "overlaps": overlaps,
        "boundary_rows": boundary_rows,
        "boundary_summary": boundary_summary,
        "registry": registry,
        "review_cases": review_cases,
        "metrics": metrics,
        "generated_dir": out,
        "evidence_dir": evidence,
    }


if __name__ == "__main__":
    run_anomaly_analysis()
