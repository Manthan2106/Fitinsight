"""Run Phase 5 association rules, anomaly screens, figures, and evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from . import association_rules, anomaly_detection
    from .p5_figures import PALETTE, write_horizontal_bars, write_scatter
    from .phase5_common import (
        DAILY_PATH,
        EVIDENCE_ROOT,
        GENERATED_ROOT,
        ROOT,
        proof,
        runtime_info,
        sha256_file,
        write_json,
    )
except ImportError:  # Running as ``python src/phase5_analysis.py``.
    import association_rules  # type: ignore
    import anomaly_detection  # type: ignore
    from p5_figures import PALETTE, write_horizontal_bars, write_scatter  # type: ignore
    from phase5_common import (  # type: ignore
        DAILY_PATH,
        EVIDENCE_ROOT,
        GENERATED_ROOT,
        ROOT,
        proof,
        runtime_info,
        sha256_file,
        write_json,
    )


FIGURE_INDEX_PATH = EVIDENCE_ROOT / "figures_index.json"
MANIFEST_PATH = EVIDENCE_ROOT / "run_manifest.json"


def _repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve()))


def _write_figures(
    association: dict[str, Any],
    anomaly: dict[str, Any],
) -> list[dict[str, Any]]:
    association_dir = association["generated_dir"] / "figures"
    anomaly_dir = anomaly["generated_dir"] / "figures"
    association_dir.mkdir(parents=True, exist_ok=True)
    anomaly_dir.mkdir(parents=True, exist_ok=True)
    sample_n = len(association["transactions"])
    participant_n = len({row["id"] for row in association["transactions"]})
    figures: list[dict[str, Any]] = []

    def register(meta: dict[str, Any], *, units: str, parameters: str) -> None:
        path = Path(meta.pop("path"))
        meta.update(
            {
                "file": _repo_relative(path),
                "sample": f"{sample_n} participant-days; {participant_n} participants",
                "units": units,
                "parameters": parameters,
            }
        )
        figures.append(meta)

    item_counts = Counter(
        item for row in association["transactions"] for item in row["items"]
    )
    item_labels = sorted(item_counts, key=lambda item: (association["family_by_item"][item], item))
    item_series = {
        "name": "Transactions containing item",
        "color": PALETTE["blue"],
        "values": [item_counts[item] for item in item_labels],
    }
    register(
        write_horizontal_bars(
            association_dir / "01_transaction_item_prevalence.svg",
            title="Participant-day transaction item prevalence",
            description=(
                "Counts of participant-day transactions containing each one "
                "of the prespecified categorical items."
            ),
            subtitle=(
                f"n={sample_n} participant-days; participants={participant_n}; "
                "one item per family per day; zero-step records retained"
            ),
            labels=item_labels,
            series=[item_series],
            axis_label="Participant-day transactions containing item (count)",
            interpretation=(
                "Items occur at different frequencies; counts define the marginal "
                "support used by Apriori."
            ),
            limitation=(
                "These are recorded categories in a small historical sample, not "
                "behavioral or health labels."
            ),
        ),
        units="transaction counts",
        parameters=(
            "Prespecified step/activity bins; calories split at full-cohort "
            "Q1/Q3; weekday/weekend; Phase 2 completeness"
        ),
    )

    association_rules_rows = association["rules"]
    max_support = max(
        (row["support"] for row in association_rules_rows),
        default=association_rules.DEFAULT_MIN_SUPPORT,
    )
    scatter_points = [
        {
            "x": row["support"],
            "y": row["confidence"],
            "eligible": row["eligible"],
        }
        for row in association_rules_rows
    ]
    register(
        write_scatter(
            association_dir / "02_rule_support_confidence.svg",
            title="Association-rule support and confidence",
            description=(
                "Each point is a directed rule generated from a frequent itemset; "
                "green points satisfy every declared rule threshold."
            ),
            subtitle=(
                f"n={sample_n} participant-days; {len(association_rules_rows)} "
                "rules from itemsets of size 2-3; min support 5%, confidence 60%, "
                "lift 1.10, at least 5 participants"
            ),
            points=scatter_points,
            x_label="Joint support (share of participant-day transactions)",
            y_label="Confidence (share of antecedent transactions)",
            x_max=max(0.05, max_support * 1.05),
            interpretation=(
                "Eligibility additionally requires lift and distinct-participant "
                "support; a high confidence alone is insufficient."
            ),
            limitation=(
                "Rules are descriptive co-occurrences, not causal statements; "
                "repeated days from one person are not independent."
            ),
        ),
        units="support and confidence as proportions",
        parameters=(
            "Apriori maximum itemset size 3; support 5%; confidence 60%; "
            "lift 1.10; minimum 5 distinct participants"
        ),
    )

    threshold_rows = association["sensitivity_rows"]
    support_levels = list(association_rules.SUPPORT_SENSITIVITY)
    threshold_labels = [f"support {value:.0%}" for value in support_levels]
    sensitivity_series = []
    for scope, label, color in (
        ("all_days", "All participant-days", PALETTE["blue"]),
        ("complete_days", "Complete days only", PALETTE["orange"]),
    ):
        by_threshold = {
            row["support_threshold"]: row["eligible_rules"]
            for row in threshold_rows
            if row["scope"] == scope
            and row["sensitivity_dimension"] == "minimum_support"
        }
        sensitivity_series.append(
            {
                "name": label,
                "color": color,
                "values": [by_threshold.get(value, 0) for value in support_levels],
            }
        )
    register(
        write_horizontal_bars(
            association_dir / "03_rule_threshold_sensitivity.svg",
            title="Eligible association rules across fixed support thresholds",
            description=(
                "Grouped bars compare the count of rules meeting all thresholds "
                "for the full cohort and complete-day subset."
            ),
            subtitle=(
                f"All-days n={sample_n}; complete-day n="
                f"{len([row for row in association['transactions'] if row['is_complete_day']])}; "
                "confidence 60%, lift 1.10, minimum 5 participants"
            ),
            labels=threshold_labels,
            series=sensitivity_series,
            axis_label="Rules meeting every threshold (count)",
            interpretation=(
                "This prespecified grid shows how rule counts respond to support "
                "threshold changes and complete-day filtering."
            ),
            limitation=(
                "Changing the threshold changes the candidate set; counts are not "
                "a measure of truth or predictive value."
            ),
        ),
        units="qualifying rule counts",
        parameters="Minimum support 3%, 5%, 8%; confidence 60%; lift 1.10; 5 participants",
    )

    fences = anomaly["fences"]
    fields = sorted(fences)
    register(
        write_horizontal_bars(
            anomaly_dir / "04_global_iqr_flags.svg",
            title="Global 1.5×IQR candidate flags by field",
            description=(
                "Counts of low- and high-tail participant-day values beyond the "
                "linear-interpolated 1.5 times interquartile-range fences."
            ),
            subtitle=(
                f"n={len(anomaly['rows'])} participant-days; "
                f"participants={len({row['id'] for row in anomaly['rows']})}; "
                "linear-interpolated quartiles; values retained"
            ),
            labels=fields,
            series=[
                {
                    "name": "Below lower fence",
                    "color": PALETTE["teal"],
                    "values": [fences[field]["low_flags"] for field in fields],
                },
                {
                    "name": "Above upper fence",
                    "color": PALETTE["red"],
                    "values": [fences[field]["high_flags"] for field in fields],
                },
            ],
            axis_label="Flagged participant-days (count)",
            interpretation=(
                "The screen identifies distribution-tail records for review; "
                "different fields flag different rows."
            ),
            limitation=(
                "IQR fences do not establish errors, unusual physiology, or "
                "invalid wearables."
            ),
        ),
        units="participant-day flag counts",
        parameters="Per-field linear Q1/Q3; 1.5×IQR fences",
    )

    detector_rows = sorted(
        anomaly["detector_counts"],
        key=lambda row: (-row["candidate_days"], row["method"]),
    )
    detector_labels = [row["method"] for row in detector_rows]
    detector_values = [row["candidate_days"] for row in detector_rows]
    register(
        write_horizontal_bars(
            anomaly_dir / "05_detector_candidate_counts.svg",
            title="Candidate participant-days by screening method",
            description=(
                "Unique participant-day counts from the existing Phase 3 screen, "
                "new Phase 5 screens, and distinct distance definitions."
            ),
            subtitle=(
                f"n={len(anomaly['rows'])} participant-days; counts are per method; "
                "P1 strict absolute and Phase 2 distance flags remain separate"
            ),
            labels=detector_labels,
            series=[
                {
                    "name": "Candidate participant-days",
                    "color": PALETTE["purple"],
                    "values": detector_values,
                }
            ],
            axis_label="Candidate participant-days (count)",
            interpretation=(
                "Counts vary by method; overlapping methods can flag the same "
                "record and must not be added together."
            ),
            limitation=(
                "Candidate counts are screening output, not counts of confirmed "
                "data errors."
            ),
        ),
        units="unique participant-day counts per detector",
        parameters=(
            "Within-person |score| > 3.5; kNN top 5% with k=5/10; global 1.5×IQR; "
            "existing P3 flags retained"
        ),
    )

    knn_summary = sorted(
        anomaly["knn_summary"],
        key=lambda row: (row["scope"], row["requested_k"]),
    )
    knn_labels = [
        f"{row['scope'].replace('_', ' ')} k={row['requested_k']}"
        for row in knn_summary
    ]
    register(
        write_horizontal_bars(
            anomaly_dir / "06_knn_distance_quantiles.svg",
            title="kNN score distribution summaries by coverage cohort",
            description=(
                "Median and 95th-percentile mean-neighbor distance scores for "
                "pooled and completeness-stratified participant-day cohorts."
            ),
            subtitle=(
                f"Rates standardized within each cohort; top 5% candidates; "
                f"n={len(anomaly['rows'])} overall participant-days; k=5 and 10"
            ),
            labels=knn_labels,
            series=[
                {
                    "name": "Median score",
                    "color": PALETTE["blue"],
                    "values": [row["score_median"] for row in knn_summary],
                },
                {
                    "name": "95th percentile",
                    "color": PALETTE["orange"],
                    "values": [row["score_p95"] for row in knn_summary],
                },
            ],
            axis_label="Mean neighbor distance (standardized Euclidean units)",
            interpretation=(
                "Within-cohort percentiles show the upper score tail under pooled "
                "and coverage-stratified comparisons."
            ),
            limitation=(
                "Each cohort is standardized separately; scores across cohorts "
                "are not directly interchangeable."
            ),
        ),
        units="mean standardized Euclidean neighbor distance",
        parameters=(
            "Features: steps/hour, calories/hour, active share; population-SD "
            "standardization; k=5/10; top 5% by cohort"
        ),
    )

    within_rows = anomaly["within_rows"]
    within_labels = ["total_steps", "active_share"]
    within_counts = [
        len({
            (row["participant_id"], row["date"])
            for row in within_rows
            if row["metric"] == field and row["flagged"]
        })
        for field in within_labels
    ]
    register(
        write_horizontal_bars(
            anomaly_dir / "07_within_person_candidates.svg",
            title="Within-person robust candidate counts",
            description=(
                "Unique participant-days with an extreme within-person daily "
                "steps or active-share modified robust score."
            ),
            subtitle=(
                f"n={len(anomaly['rows'])} participant-days; minimum 5 days per "
                "participant; absolute robust score threshold 3.5"
            ),
            labels=within_labels,
            series=[
                {
                    "name": "Flagged participant-days",
                    "color": PALETTE["teal"],
                    "values": within_counts,
                }
            ],
            axis_label="Flagged participant-days (count)",
            interpretation=(
                "Within-person comparisons identify values unusual relative to "
                "each participant's own observed records."
            ),
            limitation=(
                "Short and uneven observation histories limit each person's "
                "reference distribution; a flag is not an error diagnosis."
            ),
        ),
        units="unique participant-day counts",
        parameters=(
            "Modified MAD score threshold 3.5; at least 5 observed days; "
            "IQR fallback when MAD is zero and IQR positive"
        ),
    )

    boundary_rows = sorted(
        anomaly["boundary_rows"],
        key=lambda row: row["method"],
    )
    boundary_labels = [row["method"] for row in boundary_rows]
    register(
        write_horizontal_bars(
            anomaly_dir / "08_boundary_date_sensitivity.svg",
            title="Last-date sensitivity for anomaly candidate counts",
            description=(
                "Primary full-period candidate counts are compared with a "
                "sensitivity that excludes the last observed date."
            ),
            subtitle=(
                f"Primary n={len(anomaly['rows'])}; final date="
                f"{anomaly['boundary_summary']['boundary_date']}; primary "
                "includes all records; selected screens are recomputed"
            ),
            labels=boundary_labels,
            series=[
                {
                    "name": "Primary, all dates",
                    "color": PALETTE["blue"],
                    "values": [row["primary_candidate_days"] for row in boundary_rows],
                },
                {
                    "name": "Excluding final date",
                    "color": PALETTE["orange"],
                    "values": [
                        row["excluding_last_date_candidate_days"]
                        for row in boundary_rows
                    ],
                },
            ],
            axis_label="Candidate participant-days (count)",
            interpretation=(
                "The all-date screen remains primary; the comparison shows the "
                "effect of omitting only the observed boundary date."
            ),
            limitation=(
                "Phase 3 flags are reused then filtered rather than rerun; all "
                "other displayed screens are recalculated for sensitivity."
            ),
        ),
        units="candidate participant-day counts",
        parameters=(
            "Primary retains April 12, 2016; sensitivity excludes that date; "
            "IQR, within-person, kNN and distance screens recalculated"
        ),
    )

    participant_ids = {str(row["id"]) for row in anomaly["rows"]}
    for figure in figures:
        svg_path = ROOT / figure["file"]
        ET.parse(svg_path)
        contents = svg_path.read_text(encoding="utf-8")
        if any(participant_id in contents for participant_id in participant_ids):
            raise ValueError(f"Participant identifier found in figure: {figure['file']}")
        if not figure.get("units") or not figure.get("parameters"):
            raise ValueError("Figure metadata must state units and parameters")
    return figures


def _git_value(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_phase5() -> dict[str, Any]:
    association = association_rules.run_association_analysis()
    anomaly = anomaly_detection.run_anomaly_analysis()
    figures = _write_figures(association, anomaly)
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(FIGURE_INDEX_PATH, figures)

    project_root = ROOT
    code_paths = [
        project_root / "src" / "phase5_common.py",
        project_root / "src" / "association_rules.py",
        project_root / "src" / "anomaly_detection.py",
        project_root / "src" / "p5_figures.py",
        project_root / "src" / "phase5_analysis.py",
    ]
    inputs = [
        DAILY_PATH,
        anomaly_detection.P3_CANDIDATE_PATH,
        anomaly_detection.P3_METRICS_PATH,
    ]
    generated_paths = sorted(
        list((GENERATED_ROOT / "associations").rglob("*"))
        + list((GENERATED_ROOT / "anomalies").rglob("*"))
        + [
            EVIDENCE_ROOT / "association_metrics.json",
            EVIDENCE_ROOT / "anomaly_metrics.json",
            FIGURE_INDEX_PATH,
        ]
    )
    generated_files = [
        path for path in generated_paths if path.is_file()
    ]
    manifest = {
        "analysis": "FitInsight Phase 5: association rules and anomaly screening",
        "status": "PASS",
        "phase": "P5",
        "branch": _git_value("branch", "--show-current"),
        "git_head_at_generation": _git_value("rev-parse", "HEAD"),
        "baseline_main_ancestor": _git_value("merge-base", "origin/main", "HEAD"),
        "working_tree_clean_at_generation": _git_value("status", "--porcelain") == "",
        "runtime": runtime_info(),
        "paid_resources_used": False,
        "package_installs": 0,
        "external_analysis_services_used": [],
        "inputs": [
            {
                "path": _repo_relative(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in inputs
        ],
        "source_files": [
            {"path": _repo_relative(path), "sha256": sha256_file(path)}
            for path in code_paths
        ],
        "association_summary": {
            "transactions": association["metrics"]["transactions"],
            "participants": association["metrics"]["participants"],
            "itemsets": association["metrics"]["frequent_itemset_count"],
            "rules_examined": association["metrics"]["rules_examined"],
            "eligible_rules": association["metrics"]["eligible_rule_count"],
            "thresholds": association["metrics"]["thresholds"],
        },
        "anomaly_summary": {
            "input_rows": anomaly["metrics"]["input_rows"],
            "participants": anomaly["metrics"]["participants"],
            "phase3_daily_candidates": anomaly["metrics"]["phase3_reuse"]["daily_candidate_rows"],
            "phase3_sleep_episode_candidates": anomaly["metrics"]["phase3_reuse"]["sleep_episode_candidate_rows"],
            "distance_screens": anomaly["metrics"]["distance_screens"],
            "candidate_days_by_method": {
                row["method"]: row["candidate_days"]
                for row in anomaly["detector_counts"]
            },
            "review_cases": anomaly["metrics"]["review_case_count"],
        },
        "figure_validation": {
            "figure_count": len(figures),
            "svg_xml_parse_passed": True,
            "participant_identifiers_in_figures": False,
            "metadata_has_sample_units_parameters_legend_interpretation_and_limitations": True,
            "figures": figures,
        },
        "generated_files": [
            {
                "path": _repo_relative(path),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in generated_files
        ],
        "test_suite": {
            "command": "python -m unittest discover -s tests -v",
            "status": "Run after artifact generation; see test_results.json",
        },
    }
    write_json(MANIFEST_PATH, manifest)
    proof(
        "P5-PIPELINE",
        association_transactions=association["metrics"]["transactions"],
        association_eligible_rules=association["metrics"]["eligible_rule_count"],
        anomaly_daily_rows=anomaly["metrics"]["input_rows"],
        anomaly_methods=len(anomaly["detector_counts"]),
        figures=len(figures),
        svg_parse_checks=len(figures),
        output_files=len(generated_files),
        cost="local Python standard library only; zero installs and paid services",
        manifest=_repo_relative(MANIFEST_PATH),
    )
    return {
        "association": association,
        "anomaly": anomaly,
        "figures": figures,
        "manifest": manifest,
    }


if __name__ == "__main__":
    run_phase5()
