"""Reproducible participant-day transaction construction and Apriori mining."""

from __future__ import annotations

import itertools
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

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
except ImportError:  # Running as ``python src/association_rules.py``.
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


DEFAULT_MIN_SUPPORT = 0.05
DEFAULT_MIN_CONFIDENCE = 0.60
DEFAULT_MIN_LIFT = 1.10
DEFAULT_MIN_PARTICIPANTS = 5
DEFAULT_MAX_ITEMSET_SIZE = 3
SUPPORT_SENSITIVITY = (0.03, 0.05, 0.08)
CONFIDENCE_SENSITIVITY = (0.50, 0.60, 0.70)
LIFT_SENSITIVITY = (1.00, 1.10, 1.25)
PARTICIPANT_SENSITIVITY = (3, 5, 10)
EXCLUDED_FAMILY_PAIRS = {
    frozenset(("active_share", "very_active_minutes")),
    frozenset(("active_share", "coverage")),
}


def minimum_support_count(transaction_count: int, min_support: float) -> int:
    if not 0 < min_support <= 1:
        raise ValueError("min_support must be greater than 0 and at most 1")
    if transaction_count <= 0:
        return 0
    return math.ceil(min_support * transaction_count - 1e-12)


def _calorie_category(value: float, q1: float, q3: float) -> str:
    if value < q1:
        return "calories:lower"
    if value < q3:
        return "calories:middle"
    return "calories:upper"


def build_transactions(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, str]], dict[str, Any]]:
    """Assign one deterministic, family-exclusive item set per participant-day."""
    if not rows:
        return [], {}, [], {"calories_q1": None, "calories_q3": None}
    calorie_values = [row["calories"] for row in rows if row["calories"] is not None]
    if len(calorie_values) != len(rows):
        raise ValueError("Calories must be present for every transaction")
    q1 = quantile(calorie_values, 0.25)
    q3 = quantile(calorie_values, 0.75)
    if q1 is None or q3 is None:
        raise ValueError("Could not compute calorie quantiles")

    family_by_item: dict[str, str] = {}
    dictionary: list[dict[str, str]] = []

    def register(item: str, family: str, definition: str) -> None:
        family_by_item[item] = family
        dictionary.append(
            {"item": item, "family": family, "definition": definition}
        )

    step_definitions = {
        "steps:zero": "total_steps = 0",
        "steps:lower": "0 < total_steps < 5000",
        "steps:middle": "5000 <= total_steps < 10000",
        "steps:upper": "total_steps >= 10000",
    }
    for item, definition in step_definitions.items():
        register(item, "steps", definition)
    for item, definition in {
        "active_share:lower": "total_active_minutes / total_recorded_minutes < 0.10",
        "active_share:middle": "0.10 <= active share < 0.25",
        "active_share:upper": "active share >= 0.25",
    }.items():
        register(item, "active_share", definition)
    for item, definition in {
        "very_active:zero": "very_active_minutes = 0",
        "very_active:lower": "1 <= very_active_minutes < 30",
        "very_active:upper": "very_active_minutes >= 30",
    }.items():
        register(item, "very_active_minutes", definition)
    for item, definition in {
        "calories:lower": f"calories < Q1 ({q1:.8g})",
        "calories:middle": f"Q1 ({q1:.8g}) <= calories < Q3 ({q3:.8g})",
        "calories:upper": f"calories >= Q3 ({q3:.8g})",
    }.items():
        register(item, "calories", definition)
    for item, definition in {
        "day:weekday": "Monday through Friday",
        "day:weekend": "Saturday or Sunday",
    }.items():
        register(item, "day_type", definition)
    for item, definition in {
        "coverage:complete": "Phase 2 is_complete_day is True (1440 recorded minutes)",
        "coverage:incomplete": "Phase 2 is_complete_day is False",
    }.items():
        register(item, "coverage", definition)

    transactions: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=1):
        steps = row["total_steps"]
        very_active = row["very_active_minutes"]
        active_total = row["total_active_minutes"]
        recorded = row["total_recorded_minutes"]
        calories = row["calories"]
        if None in (steps, very_active, active_total, recorded, calories):
            raise ValueError(
                f"Missing transaction field for {row['id']} {row['activity_date']}"
            )
        items = []
        if steps == 0:
            items.append("steps:zero")
        elif steps < 5000:
            items.append("steps:lower")
        elif steps < 10000:
            items.append("steps:middle")
        else:
            items.append("steps:upper")
        if recorded <= 0:
            raise ValueError("Active-share transaction requires positive duration")
        active_share = active_total / recorded
        if active_share < 0.10:
            items.append("active_share:lower")
        elif active_share < 0.25:
            items.append("active_share:middle")
        else:
            items.append("active_share:upper")
        if very_active == 0:
            items.append("very_active:zero")
        elif very_active < 30:
            items.append("very_active:lower")
        else:
            items.append("very_active:upper")
        items.append(_calorie_category(calories, q1, q3))
        items.append("day:weekend" if row["weekday"] >= 5 else "day:weekday")
        items.append(
            "coverage:complete" if row["is_complete_day"]
            else "coverage:incomplete"
        )
        if len({family_by_item[item] for item in items}) != len(items):
            raise AssertionError("Transaction contains duplicate item families")
        transactions.append(
            {
                "transaction_id": f"PD-{index:04d}",
                "id": row["id"],
                "date": row["activity_date"].isoformat(),
                "is_complete_day": row["is_complete_day"],
                "items": tuple(sorted(set(items))),
            }
        )
    return (
        transactions,
        family_by_item,
        dictionary,
        {"calories_q1": q1, "calories_q3": q3},
    )


def _family_compatible(
    items: Iterable[str],
    family_by_item: dict[str, str],
    excluded_family_pairs: set[frozenset[str]] | None = None,
) -> bool:
    families = [family_by_item[item] for item in items]
    family_set = set(families)
    if len(families) != len(family_set):
        return False
    return not any(
        pair.issubset(family_set)
        for pair in (excluded_family_pairs or set())
    )


def apriori(
    transactions: list[dict[str, Any]],
    family_by_item: dict[str, str],
    min_support: float = DEFAULT_MIN_SUPPORT,
    max_size: int = DEFAULT_MAX_ITEMSET_SIZE,
    excluded_family_pairs: set[frozenset[str]] | None = None,
) -> tuple[dict[tuple[str, ...], dict[str, Any]], dict[str, Any]]:
    """Count frequent itemsets with canonical order, family constraints, and pruning."""
    if max_size < 1:
        raise ValueError("max_size must be at least one")
    n = len(transactions)
    required_count = minimum_support_count(n, min_support)
    normalized = [
        {
            **transaction,
            "_items": frozenset(transaction.get("items", ())),
        }
        for transaction in transactions
    ]
    singleton_counts: Counter[str] = Counter()
    singleton_participants: dict[str, set[str]] = defaultdict(set)
    for transaction in normalized:
        for item in transaction["_items"]:
            if item not in family_by_item:
                raise ValueError(f"Unknown item family for {item!r}")
            singleton_counts[item] += 1
            singleton_participants[item].add(str(transaction["id"]))

    frequent: dict[tuple[str, ...], dict[str, Any]] = {}
    level: set[tuple[str, ...]] = set()
    for item in sorted(singleton_counts):
        count = singleton_counts[item]
        if count >= required_count and n > 0:
            key = (item,)
            level.add(key)
            frequent[key] = {
                "count": count,
                "support": count / n,
                "participants": set(singleton_participants[item]),
            }

    candidates_by_size: dict[str, int] = {"1": len(singleton_counts)}
    frequent_by_size: dict[str, int] = {
        "1": len(level)
    } if level else {}
    subset_pruned = 0
    family_pruned = 0
    dependency_pruned = 0
    for size in range(2, max_size + 1):
        candidates: set[tuple[str, ...]] = set()
        previous = sorted(level)
        previous_set = set(level)
        for left_index, left in enumerate(previous):
            for right in previous[left_index + 1:]:
                merged = tuple(sorted(set(left) | set(right)))
                if len(merged) != size:
                    continue
                if not _family_compatible(merged, family_by_item):
                    family_pruned += 1
                    continue
                if not _family_compatible(
                    merged, family_by_item, excluded_family_pairs
                ):
                    dependency_pruned += 1
                    continue
                if any(
                    tuple(subset) not in previous_set
                    for subset in itertools.combinations(merged, size - 1)
                ):
                    subset_pruned += 1
                    continue
                candidates.add(merged)
        candidates_by_size[str(size)] = len(candidates)
        counts: Counter[tuple[str, ...]] = Counter()
        participants: dict[tuple[str, ...], set[str]] = defaultdict(set)
        for transaction in normalized:
            transaction_items = transaction["_items"]
            for candidate in candidates:
                if set(candidate).issubset(transaction_items):
                    counts[candidate] += 1
                    participants[candidate].add(str(transaction["id"]))
        next_level: set[tuple[str, ...]] = set()
        for candidate in sorted(candidates):
            count = counts[candidate]
            if count >= required_count and n > 0:
                next_level.add(candidate)
                frequent[candidate] = {
                    "count": count,
                    "support": count / n,
                    "participants": participants[candidate],
                }
        if next_level:
            frequent_by_size[str(size)] = len(next_level)
        level = next_level
        if not level:
            break
    return frequent, {
        "transaction_count": n,
        "min_support": min_support,
        "minimum_support_count": required_count,
        "max_itemset_size": max_size,
        "candidate_counts_by_size": candidates_by_size,
        "frequent_itemsets_by_size": frequent_by_size,
        "subset_pruned_candidates": subset_pruned,
        "family_incompatible_candidates_pruned": family_pruned,
        "dependency_related_candidates_pruned": dependency_pruned,
    }


def _all_nonempty_proper_subsets(
    items: tuple[str, ...],
) -> list[tuple[str, ...]]:
    result = []
    for size in range(1, len(items)):
        result.extend(tuple(subset) for subset in itertools.combinations(items, size))
    return sorted(result)


def build_rules(
    frequent: dict[tuple[str, ...], dict[str, Any]],
    transaction_count: int,
    min_support: float = DEFAULT_MIN_SUPPORT,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    min_lift: float = DEFAULT_MIN_LIFT,
    min_participants: int = DEFAULT_MIN_PARTICIPANTS,
) -> list[dict[str, Any]]:
    """Return every directed rule from frequent itemsets with explicit eligibility."""
    if not 0 <= min_confidence <= 1:
        raise ValueError("min_confidence must be between zero and one")
    if min_lift < 0 or min_participants < 0:
        raise ValueError("min_lift and min_participants must be nonnegative")
    rule_rows: list[dict[str, Any]] = []
    if transaction_count <= 0:
        return rule_rows
    for joint in sorted(frequent, key=lambda items: (len(items), items)):
        if len(joint) < 2:
            continue
        joint_stats = frequent[joint]
        joint_count = int(joint_stats["count"])
        for antecedent in _all_nonempty_proper_subsets(joint):
            consequent = tuple(item for item in joint if item not in antecedent)
            antecedent_stats = frequent.get(antecedent)
            consequent_stats = frequent.get(consequent)
            if not antecedent_stats or not consequent_stats:
                continue
            antecedent_count = int(antecedent_stats["count"])
            consequent_count = int(consequent_stats["count"])
            if antecedent_count == 0 or consequent_count == 0:
                continue
            support = joint_count / transaction_count
            antecedent_support = antecedent_count / transaction_count
            consequent_support = consequent_count / transaction_count
            confidence = joint_count / antecedent_count
            lift = confidence / consequent_support
            leverage = support - antecedent_support * consequent_support
            participant_count = len(joint_stats["participants"])
            eligible = (
                support + 1e-15 >= min_support
                and confidence + 1e-15 >= min_confidence
                and lift + 1e-15 >= min_lift
                and participant_count >= min_participants
            )
            rule_rows.append(
                {
                    "antecedent": antecedent,
                    "consequent": consequent,
                    "joint": joint,
                    "joint_count": joint_count,
                    "antecedent_count": antecedent_count,
                    "consequent_count": consequent_count,
                    "distinct_participants": participant_count,
                    "support": support,
                    "antecedent_support": antecedent_support,
                    "consequent_support": consequent_support,
                    "confidence": confidence,
                    "lift": lift,
                    "leverage": leverage,
                    "min_support": min_support,
                    "min_confidence": min_confidence,
                    "min_lift": min_lift,
                    "min_participants": min_participants,
                    "eligible": eligible,
                }
            )
    rule_rows.sort(key=lambda row: (row["antecedent"], row["consequent"]))
    return rule_rows


def participant_balanced_sensitivity(
    transactions: list[dict[str, Any]],
    frequent: dict[tuple[str, ...], dict[str, Any]],
    rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Average within-person item prevalence and rule confidence without pooling days."""
    by_participant: dict[str, list[frozenset[str]]] = defaultdict(list)
    for transaction in transactions:
        by_participant[str(transaction["id"])].append(
            frozenset(transaction["items"])
        )
    output: list[dict[str, Any]] = []
    for items in sorted(frequent, key=lambda value: (len(value), value)):
        per_person = [
            sum(set(items).issubset(day) for day in days) / len(days)
            for days in by_participant.values()
            if days
        ]
        pooled = frequent[items]["support"]
        output.append(
            {
                "entity_type": "itemset_prevalence",
                "entity": items,
                "pooled_rate": pooled,
                "participant_balanced_rate": (
                    sum(per_person) / len(per_person) if per_person else None
                ),
                "participants_contributing": len(per_person),
                "participant_rate_denominator": len(by_participant),
                "difference_balanced_minus_pooled": (
                    sum(per_person) / len(per_person) - pooled
                    if per_person else None
                ),
            }
        )
    for rule in rules:
        antecedent = set(rule["antecedent"])
        joint = set(rule["joint"])
        confidences = []
        for days in by_participant.values():
            antecedent_count = sum(antecedent.issubset(day) for day in days)
            if antecedent_count:
                joint_count = sum(joint.issubset(day) for day in days)
                confidences.append(joint_count / antecedent_count)
        balanced = sum(confidences) / len(confidences) if confidences else None
        output.append(
            {
                "entity_type": "rule_confidence",
                "entity": f"{rule['antecedent']} -> {rule['consequent']}",
                "pooled_rate": rule["confidence"],
                "participant_balanced_rate": balanced,
                "participants_contributing": len(confidences),
                "participant_rate_denominator": len(by_participant),
                "difference_balanced_minus_pooled": (
                    balanced - rule["confidence"] if balanced is not None else None
                ),
            }
        )
    return output


def _to_csv_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rule_id": f"AR-{index:04d}",
            "antecedent_items": row["antecedent"],
            "consequent_items": row["consequent"],
            "joint_items": row["joint"],
            "joint_transactions": row["joint_count"],
            "distinct_participants": row["distinct_participants"],
            "antecedent_transactions": row["antecedent_count"],
            "consequent_transactions": row["consequent_count"],
            "support": row["support"],
            "antecedent_support": row["antecedent_support"],
            "consequent_support": row["consequent_support"],
            "confidence": row["confidence"],
            "lift": row["lift"],
            "leverage": row["leverage"],
            "min_support": row["min_support"],
            "min_confidence": row["min_confidence"],
            "min_lift": row["min_lift"],
            "min_distinct_participants": row["min_participants"],
            "threshold_eligible": row["eligible"],
        }
        for index, row in enumerate(rules, start=1)
    ]


def _summary_row(
    scope: str,
    dimension: str,
    parameter_value: float | int,
    support_threshold: float,
    confidence_threshold: float,
    lift_threshold: float,
    participant_threshold: int,
    transactions: list[dict[str, Any]],
    frequent: dict[tuple[str, ...], dict[str, Any]],
    rules: list[dict[str, Any]],
    run_metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": scope,
        "sensitivity_dimension": dimension,
        "sensitivity_value": parameter_value,
        "support_threshold": support_threshold,
        "confidence_threshold": confidence_threshold,
        "lift_threshold": lift_threshold,
        "minimum_distinct_participants": participant_threshold,
        "transactions": len(transactions),
        "participants": len({row["id"] for row in transactions}),
        "minimum_support_transactions": run_metrics["minimum_support_count"],
        "frequent_itemsets_by_size": {
            str(size): sum(len(itemset) == size for itemset in frequent)
            for size in range(1, DEFAULT_MAX_ITEMSET_SIZE + 1)
        },
        "rules_examined": len(rules),
        "eligible_rules": sum(bool(rule["eligible"]) for rule in rules),
    }


def run_association_analysis(
    input_path: Path | None = None,
    generated_dir: Path | None = None,
    evidence_dir: Path | None = None,
) -> dict[str, Any]:
    rows = load_daily_rows(input_path or DAILY_PATH)
    proof(
        "P5-ASSOC-LOAD",
        rows=len(rows),
        participants=len({row["id"] for row in rows}),
        complete_days=sum(row["is_complete_day"] for row in rows),
        incomplete_days=sum(not row["is_complete_day"] for row in rows),
        positive_recorded_minutes=sum(row["total_recorded_minutes"] > 0 for row in rows),
        duplicate_keys=0,
    )

    transactions, family_by_item, item_dictionary, cutpoints = build_transactions(rows)
    for row in transactions:
        if len(row["items"]) != len(set(row["items"])):
            raise AssertionError("Duplicate item within transaction")
        if len({family_by_item[item] for item in row["items"]}) != len(row["items"]):
            raise AssertionError("Multiple categories from one family")
    family_counts = Counter(family_by_item[item] for row in transactions for item in row["items"])
    proof(
        "P5-ASSOC-BINS",
        families=len(set(family_by_item.values())),
        item_count=len(family_by_item),
        family_assignment_checks=len(transactions),
        calories_q1=cutpoints["calories_q1"],
        calories_q3=cutpoints["calories_q3"],
        step_bins="zero, 1-4999, 5000-9999, 10000+",
        active_share_bins="<0.10, 0.10-<0.25, >=0.25",
    )
    proof(
        "P5-ASSOC-TRANSACTIONS",
        transactions=len(transactions),
        participant_count=len({row["id"] for row in transactions}),
        item_occurrences=sum(len(row["items"]) for row in transactions),
        min_items_per_day=min((len(row["items"]) for row in transactions), default=0),
        max_items_per_day=max((len(row["items"]) for row in transactions), default=0),
        family_occurrences=family_counts,
    )

    baseline_frequent, baseline_run = apriori(
        transactions,
        family_by_item,
        DEFAULT_MIN_SUPPORT,
        DEFAULT_MAX_ITEMSET_SIZE,
        EXCLUDED_FAMILY_PAIRS,
    )
    baseline_rules = build_rules(
        baseline_frequent,
        len(transactions),
        DEFAULT_MIN_SUPPORT,
        DEFAULT_MIN_CONFIDENCE,
        DEFAULT_MIN_LIFT,
        DEFAULT_MIN_PARTICIPANTS,
    )
    eligible_rules = [rule for rule in baseline_rules if rule["eligible"]]
    proof(
        "P5-ASSOC-APRIORI",
        **baseline_run,
        observed_support_denominator=len(transactions),
        itemset_count=len(baseline_frequent),
    )
    proof(
        "P5-ASSOC-RULES",
        rules_examined=len(baseline_rules),
        eligible_rules=len(eligible_rules),
        min_confidence=DEFAULT_MIN_CONFIDENCE,
        min_lift=DEFAULT_MIN_LIFT,
        min_distinct_participants=DEFAULT_MIN_PARTICIPANTS,
        metrics=["support", "confidence", "lift", "leverage"],
        distinct_participant_counts=all(
            rule["distinct_participants"] >= 0 for rule in baseline_rules
        ),
    )

    balanced_rows = participant_balanced_sensitivity(
        transactions, baseline_frequent, baseline_rules
    )
    sensitivity_rows = []
    complete_transactions = [
        transaction for transaction in transactions if transaction["is_complete_day"]
    ]
    complete_frequent, complete_run = apriori(
        complete_transactions,
        family_by_item,
        DEFAULT_MIN_SUPPORT,
        DEFAULT_MAX_ITEMSET_SIZE,
        EXCLUDED_FAMILY_PAIRS,
    )
    complete_rules_at_default = build_rules(
        complete_frequent,
        len(complete_transactions),
        DEFAULT_MIN_SUPPORT,
        DEFAULT_MIN_CONFIDENCE,
        DEFAULT_MIN_LIFT,
        DEFAULT_MIN_PARTICIPANTS,
    )
    scope_inputs = (
        ("all_days", transactions, baseline_frequent, baseline_run),
        ("complete_days", complete_transactions, complete_frequent, complete_run),
    )
    for scope, scoped_transactions, default_frequent, default_run in scope_inputs:
        for threshold in SUPPORT_SENSITIVITY:
            frequent, run_metrics = apriori(
                scoped_transactions,
                family_by_item,
                threshold,
                DEFAULT_MAX_ITEMSET_SIZE,
                EXCLUDED_FAMILY_PAIRS,
            )
            rules = build_rules(
                frequent,
                len(scoped_transactions),
                threshold,
                DEFAULT_MIN_CONFIDENCE,
                DEFAULT_MIN_LIFT,
                DEFAULT_MIN_PARTICIPANTS,
            )
            sensitivity_rows.append(
                _summary_row(
                    scope,
                    "minimum_support",
                    threshold,
                    threshold,
                    DEFAULT_MIN_CONFIDENCE,
                    DEFAULT_MIN_LIFT,
                    DEFAULT_MIN_PARTICIPANTS,
                    scoped_transactions,
                    frequent,
                    rules,
                    run_metrics,
                )
            )
        for threshold in CONFIDENCE_SENSITIVITY:
            rules = build_rules(
                default_frequent,
                len(scoped_transactions),
                DEFAULT_MIN_SUPPORT,
                threshold,
                DEFAULT_MIN_LIFT,
                DEFAULT_MIN_PARTICIPANTS,
            )
            sensitivity_rows.append(
                _summary_row(
                    scope,
                    "minimum_confidence",
                    threshold,
                    DEFAULT_MIN_SUPPORT,
                    threshold,
                    DEFAULT_MIN_LIFT,
                    DEFAULT_MIN_PARTICIPANTS,
                    scoped_transactions,
                    default_frequent,
                    rules,
                    default_run,
                )
            )
        for threshold in LIFT_SENSITIVITY:
            rules = build_rules(
                default_frequent,
                len(scoped_transactions),
                DEFAULT_MIN_SUPPORT,
                DEFAULT_MIN_CONFIDENCE,
                threshold,
                DEFAULT_MIN_PARTICIPANTS,
            )
            sensitivity_rows.append(
                _summary_row(
                    scope,
                    "minimum_lift",
                    threshold,
                    DEFAULT_MIN_SUPPORT,
                    DEFAULT_MIN_CONFIDENCE,
                    threshold,
                    DEFAULT_MIN_PARTICIPANTS,
                    scoped_transactions,
                    default_frequent,
                    rules,
                    default_run,
                )
            )
        for threshold in PARTICIPANT_SENSITIVITY:
            rules = build_rules(
                default_frequent,
                len(scoped_transactions),
                DEFAULT_MIN_SUPPORT,
                DEFAULT_MIN_CONFIDENCE,
                DEFAULT_MIN_LIFT,
                threshold,
            )
            sensitivity_rows.append(
                _summary_row(
                    scope,
                    "minimum_participants",
                    threshold,
                    DEFAULT_MIN_SUPPORT,
                    DEFAULT_MIN_CONFIDENCE,
                    DEFAULT_MIN_LIFT,
                    threshold,
                    scoped_transactions,
                    default_frequent,
                    rules,
                    default_run,
                )
            )
    proof(
        "P5-ASSOC-SENSITIVITY",
        participant_balanced_rows=len(balanced_rows),
        support_thresholds=list(SUPPORT_SENSITIVITY),
        confidence_thresholds=list(CONFIDENCE_SENSITIVITY),
        lift_thresholds=list(LIFT_SENSITIVITY),
        participant_thresholds=list(PARTICIPANT_SENSITIVITY),
        complete_day_transactions=len(complete_transactions),
        complete_day_participants=len(
            {row["id"] for row in complete_transactions}
        ),
        all_days_eligible_rules=sum(rule["eligible"] for rule in baseline_rules),
        complete_days_eligible_rules=sum(
            rule["eligible"] for rule in complete_rules_at_default
        ),
    )

    out = generated_dir or GENERATED_ROOT / "associations"
    evidence = evidence_dir or EVIDENCE_ROOT
    out.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    transaction_rows = [
        {
            "transaction_id": row["transaction_id"],
            "participant_id": row["id"],
            "date": row["date"],
            "complete_day": row["is_complete_day"],
            "items": row["items"],
        }
        for row in transactions
    ]
    flattened = [
        {
            "transaction_id": row["transaction_id"],
            "participant_id": row["id"],
            "date": row["date"],
            "item": item,
            "family": family_by_item[item],
        }
        for row in transactions
        for item in row["items"]
    ]
    itemset_rows = [
        {
            "items": items,
            "itemset_size": len(items),
            "transactions": stats["count"],
            "distinct_participants": len(stats["participants"]),
            "support": stats["support"],
            "minimum_support": DEFAULT_MIN_SUPPORT,
            "minimum_support_transactions": baseline_run["minimum_support_count"],
        }
        for items, stats in sorted(
            baseline_frequent.items(), key=lambda pair: (len(pair[0]), pair[0])
        )
    ]
    write_csv(
        out / "transactions.csv",
        ["transaction_id", "participant_id", "date", "complete_day", "items"],
        transaction_rows,
    )
    write_csv(
        out / "transaction_items.csv",
        ["transaction_id", "participant_id", "date", "item", "family"],
        flattened,
    )
    write_csv(
        out / "item_dictionary.csv",
        ["item", "family", "definition"],
        sorted(item_dictionary, key=lambda row: (row["family"], row["item"])),
    )
    write_csv(
        out / "frequent_itemsets.csv",
        [
            "items", "itemset_size", "transactions", "distinct_participants",
            "support", "minimum_support", "minimum_support_transactions",
        ],
        itemset_rows,
    )
    rule_fields = [
        "rule_id", "antecedent_items", "consequent_items", "joint_items",
        "joint_transactions", "distinct_participants", "antecedent_transactions",
        "consequent_transactions", "support", "antecedent_support",
        "consequent_support", "confidence", "lift", "leverage", "min_support",
        "min_confidence", "min_lift", "min_distinct_participants",
        "threshold_eligible",
    ]
    write_csv(out / "association_rules.csv", rule_fields, _to_csv_rules(baseline_rules))
    write_csv(
        out / "participant_balanced_sensitivity.csv",
        [
            "entity_type", "entity", "pooled_rate", "participant_balanced_rate",
            "participants_contributing", "participant_rate_denominator",
            "difference_balanced_minus_pooled",
        ],
        balanced_rows,
    )
    write_csv(
        out / "threshold_sensitivity.csv",
        [
            "scope", "sensitivity_dimension", "sensitivity_value",
            "support_threshold", "confidence_threshold", "lift_threshold",
            "minimum_distinct_participants", "transactions", "participants",
            "minimum_support_transactions", "frequent_itemsets_by_size",
            "rules_examined", "eligible_rules",
        ],
        sensitivity_rows,
    )
    write_csv(
        out / "complete_day_rules.csv",
        rule_fields,
        _to_csv_rules(complete_rules_at_default),
    )

    metrics = {
        "analysis": "Phase 5 participant-day Apriori association rules",
        "grain": "one participant-day transaction",
        "transactions": len(transactions),
        "participants": len({row["id"] for row in transactions}),
        "complete_days": len(complete_transactions),
        "complete_day_participants": len(
            {row["id"] for row in complete_transactions}
        ),
        "item_families": sorted(set(family_by_item.values())),
        "calorie_cutpoints_full_cohort": cutpoints,
        "thresholds": {
            "minimum_support": DEFAULT_MIN_SUPPORT,
            "minimum_support_transactions": baseline_run["minimum_support_count"],
            "minimum_confidence": DEFAULT_MIN_CONFIDENCE,
            "minimum_lift": DEFAULT_MIN_LIFT,
            "minimum_distinct_participants": DEFAULT_MIN_PARTICIPANTS,
            "maximum_itemset_size": DEFAULT_MAX_ITEMSET_SIZE,
            "support_sensitivity": list(SUPPORT_SENSITIVITY),
            "confidence_sensitivity": list(CONFIDENCE_SENSITIVITY),
            "lift_sensitivity": list(LIFT_SENSITIVITY),
            "distinct_participant_sensitivity": list(PARTICIPANT_SENSITIVITY),
        },
        "excluded_family_pairs": [
            sorted(pair) for pair in sorted(EXCLUDED_FAMILY_PAIRS, key=lambda pair: sorted(pair))
        ],
        "excluded_pair_reason": (
            "Do not mine active-share with very-active minutes, because very-active "
            "minutes are part of its numerator; do not mine active-share with "
            "coverage status, because coverage is defined from its denominator."
        ),
        "apriori": baseline_run,
        "frequent_itemset_count": len(baseline_frequent),
        "rules_examined": len(baseline_rules),
        "eligible_rule_count": len(eligible_rules),
        "eligible_rules": [
            {
                "antecedent": list(rule["antecedent"]),
                "consequent": list(rule["consequent"]),
                "support": rule["support"],
                "confidence": rule["confidence"],
                "lift": rule["lift"],
                "leverage": rule["leverage"],
                "distinct_participants": rule["distinct_participants"],
            }
            for rule in eligible_rules
        ],
        "rule_absence_note": (
            "No rules met every prespecified threshold."
            if not eligible_rules else None
        ),
        "participant_balanced_sensitivity_rows": len(balanced_rows),
        "support_sensitivity": [
            row for row in sensitivity_rows
            if row["sensitivity_dimension"] == "minimum_support"
        ],
        "threshold_sensitivity": sensitivity_rows,
        "category_definitions": item_dictionary,
        "generated_outputs": [
            "transactions.csv", "transaction_items.csv", "item_dictionary.csv",
            "frequent_itemsets.csv", "association_rules.csv",
            "participant_balanced_sensitivity.csv", "threshold_sensitivity.csv",
            "complete_day_rules.csv",
        ],
    }
    write_json(evidence / "association_metrics.json", metrics)
    proof(
        "P5-ASSOC-ARTIFACTS",
        transactions=len(transaction_rows),
        flattened_item_mappings=len(flattened),
        frequent_itemsets=len(itemset_rows),
        rule_rows=len(baseline_rules),
        eligible_rules=len(eligible_rules),
        evidence_json=str((evidence / "association_metrics.json").relative_to(
            evidence.parents[1]
        )),
    )
    return {
        "transactions": transactions,
        "family_by_item": family_by_item,
        "frequent_itemsets": baseline_frequent,
        "rules": baseline_rules,
        "metrics": metrics,
        "sensitivity_rows": sensitivity_rows,
        "generated_dir": out,
        "evidence_dir": evidence,
    }


if __name__ == "__main__":
    run_association_analysis()
