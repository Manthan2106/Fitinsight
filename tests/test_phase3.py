import csv
import json
import unittest
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

from src.eda_analysis import (
    average_ranks,
    build_participant_summary,
    completeness_analysis,
    describe,
    make_sleep_activity_table,
    pearson,
    quantile,
    time_accounting_analysis,
    weekday_weekend_analysis,
)
from src.sleep_analysis import (
    assign_primary_eligibility,
    identify_overlaps,
    iter_episodes,
)


ROOT = Path(__file__).resolve().parents[1]


def activity_day(participant, day, activity_minutes, complete=False):
    return {
        "id": participant,
        "activity_date": datetime.strptime(day, "%Y-%m-%d").date(),
        "very_active_minutes": 0.0,
        "fairly_active_minutes": 0.0,
        "lightly_active_minutes": float(activity_minutes) / 2,
        "sedentary_minutes": float(activity_minutes) / 2,
        "total_recorded_minutes": float(activity_minutes),
        "is_complete_day": complete,
    }


def sleep_match(participant, day, sleep_minutes, status="matched"):
    return {
        "id": participant,
        "activity_date": day,
        "sleep_match_status": status,
        "sleep_log_id": "log-" + day,
        "recorded_sleep_minutes": sleep_minutes,
    }


def sleep_records(participant, log_id, start, offsets, values=None):
    values = values or ["1"] * len(offsets)
    return [
        (
            participant,
            log_id,
            (start + timedelta(minutes=offset)).strftime("%Y-%m-%d %H:%M:%S"),
            value,
        )
        for offset, value in zip(offsets, values)
    ]


class StatisticsTests(unittest.TestCase):
    def test_quantile_uses_linear_interpolation(self):
        self.assertEqual(quantile([0, 10, 20, 30], 0.25), 7.5)

    def test_describe_reports_missing_and_sample_standard_deviation(self):
        result = describe([1, 3, None])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["missing"], 1)
        self.assertEqual(result["mean"], 2)
        self.assertAlmostEqual(result["sample_stddev"], 2 ** 0.5)

    def test_rank_ties_are_averaged_and_constant_correlation_is_missing(self):
        self.assertEqual(average_ranks([4, 9, 9, 12]), [1.0, 2.5, 2.5, 4.0])
        self.assertIsNone(pearson([3, 3, 3], [1, 2, 3]))
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)

    def test_participant_summaries_and_complete_day_sensitivity(self):
        rows = [
            {
                "id": "01",
                "total_steps": 10,
                "calories": 4,
                "total_distance": 1,
                "total_active_minutes": 2,
                "sedentary_minutes": 3,
                "total_recorded_minutes": 1440 if index == 0 else 900,
                "is_complete_day": index == 0,
            }
            for index in range(2)
        ] + [
            {
                "id": "02",
                "total_steps": 7,
                "calories": 3,
                "total_distance": 2,
                "total_active_minutes": 1,
                "sedentary_minutes": 4,
                "total_recorded_minutes": 600,
                "is_complete_day": False,
            }
        ]
        summary = build_participant_summary(rows)
        self.assertEqual(summary[0]["id"], "01")
        self.assertEqual(summary[0]["avg_total_steps_all"], 10)
        self.assertIsNone(summary[1]["avg_total_steps_complete"])
        metrics, table = completeness_analysis(rows, summary)
        self.assertEqual(metrics["participants_without_complete_days"], 1)
        self.assertEqual(
            metrics["participant_step_mean_sensitivity"]["direction_counts"],
            {"equal": 1, "unavailable": 1},
        )
        self.assertEqual(len(table), 2)

    def test_weekday_weekend_comparison_pairs_at_participant_grain(self):
        rows = []
        for participant, offset in (("01", 0), ("02", 100)):
            rows.extend([
                {
                    "id": participant,
                    "weekday": 0,
                    "total_steps": 1000 + offset,
                    "total_active_minutes": 10,
                    "sedentary_minutes": 800,
                    "calories": 1500,
                    "is_complete_day": True,
                },
                {
                    "id": participant,
                    "weekday": 6,
                    "total_steps": 2000 + offset,
                    "total_active_minutes": 20,
                    "sedentary_minutes": 700,
                    "calories": 1600,
                    "is_complete_day": True,
                },
            ])
        metrics, paired = weekday_weekend_analysis(rows)
        self.assertEqual(len(paired), 2)
        self.assertEqual(
            metrics["paired_participant_differences_weekend_minus_weekday"]
            ["total_steps"]["direction_counts"],
            {"weekend_higher": 2},
        )
        self.assertEqual(
            metrics["complete_day_only_sensitivity"]["total_steps"]["participants_with_both"],
            2,
        )

    def test_time_accounting_exact_and_small_positive_negative_differences(self):
        days = [
            activity_day("01", "2016-04-01", 900, complete=False),
            activity_day("02", "2016-04-02", 900, complete=False),
            activity_day("03", "2016-04-03", 900, complete=False),
        ]
        matches = [
            sleep_match("01", "2016-04-01", 540),
            sleep_match("02", "2016-04-02", 555),
            sleep_match("03", "2016-04-03", 525),
        ]
        rows, metrics, participants, dates = time_accounting_analysis(days, matches)
        self.assertEqual([row["difference_from_1440_minutes"] for row in rows], [0, 15, -15])
        self.assertEqual([row["combined_equals_1440"] for row in rows], [True, False, False])
        self.assertTrue(all(row["within_15_minutes"] for row in rows))
        self.assertTrue(all(row["within_30_minutes"] for row in rows))
        self.assertTrue(all(row["within_60_minutes"] for row in rows))
        self.assertTrue(all(row["phase2_is_complete_day"] is False for row in rows))
        self.assertEqual(metrics["primary_summary"]["exact_1440_count"], 1)
        self.assertEqual(len(participants), 3)
        self.assertEqual(len(dates), 3)

    def test_time_accounting_missing_and_ambiguous_sleep_is_never_imputed(self):
        days = [
            activity_day("01", "2016-04-01", 900),
            activity_day("02", "2016-04-01", 900),
        ]
        matches = [
            sleep_match("01", "2016-04-01", None, status="no_eligible_overnight_episode"),
            # Even a malformed non-null value on an ambiguous row is not accepted.
            sleep_match("02", "2016-04-01", 540, status="ambiguous_multiple_sessions"),
        ]
        rows, metrics, participants, dates = time_accounting_analysis(days, matches)
        self.assertEqual(rows, [])
        self.assertEqual(participants, [])
        self.assertEqual(dates, [])
        self.assertEqual(metrics["input_counts"]["unmatched_or_ambiguous_rows_not_accounted"], 2)
        self.assertEqual(
            metrics["input_counts"]["nonmatched_status_counts"],
            {"no_eligible_overnight_episode": 1, "ambiguous_multiple_sessions": 1},
        )

    def test_time_accounting_boundary_date_sensitivity_preserves_primary_rows(self):
        days = [
            activity_day("01", "2016-04-11", 900),
            activity_day("01", "2016-04-12", 100),
        ]
        matches = [
            sleep_match("01", "2016-04-11", 540),
            sleep_match("01", "2016-04-12", 500),
        ]
        rows, metrics, _, _ = time_accounting_analysis(days, matches)
        self.assertEqual(len(rows), 2)
        self.assertEqual(metrics["primary_summary"]["participant_days"], 2)
        self.assertEqual(
            metrics["boundary_sensitivity"]["exclude_2016_04_12"]["participant_days"], 1
        )
        self.assertEqual(
            metrics["boundary_sensitivity"]["exclude_2016_04_11_and_2016_04_12"]
            ["participant_days"],
            0,
        )
        self.assertEqual(rows[1]["difference_from_1440_minutes"], -840)

    def test_matched_status_without_sleep_duration_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no recorded row count"):
            time_accounting_analysis(
                [activity_day("01", "2016-04-01", 900)],
                [sleep_match("01", "2016-04-01", None)],
            )


class SleepEpisodeTests(unittest.TestCase):
    def test_episode_reconstruction_keeps_categories_neutral(self):
        rows = sleep_records(
            "p1",
            "overnight",
            datetime(2026, 3, 1, 23, 58),
            [0, 1, 2, 3],
            ["1", "2", "2", "3"],
        )
        episodes = list(iter_episodes(rows))
        self.assertEqual(len(episodes), 1)
        episode = episodes[0]
        self.assertEqual(episode["waking_date"], "2026-03-02")
        self.assertTrue(episode["crosses_midnight"])
        self.assertEqual(episode["recorded_minute_count"], 4)
        self.assertEqual(episode["category_counts"], {"1": 1, "2": 2, "3": 1})
        self.assertEqual(episode["category_shares"]["2"], 0.5)

    def test_eligibility_flags_daytime_long_gapped_and_ambiguous_sessions(self):
        rows = []
        rows += sleep_records(
            "p1", "afternoon", datetime(2026, 3, 1, 14, 0), [0, 1]
        )
        rows += sleep_records(
            "p1", "long", datetime(2026, 3, 2, 18, 0), [0, 721]
        )
        rows += sleep_records(
            "p1", "gapped", datetime(2026, 3, 3, 22, 0), [0, 2]
        )
        rows += sleep_records(
            "p1", "multi-a", datetime(2026, 3, 4, 23, 58), [0, 1, 2, 3]
        )
        rows += sleep_records(
            "p1", "multi-b", datetime(2026, 3, 4, 23, 57), [0, 1, 2, 3]
        )
        rows.sort(key=lambda row: (row[0], row[1], row[2]))
        episodes = list(iter_episodes(rows))
        summary = assign_primary_eligibility(episodes)
        by_log = {episode["log_id"]: episode for episode in episodes}
        self.assertEqual(by_log["afternoon"]["primary_exclusion_reason"], "potential_daytime_or_afternoon_session")
        self.assertIn("elapsed_span_over_12_hours", by_log["long"]["quality_flags"])
        self.assertIn("timestamp_gap_over_60_seconds", by_log["gapped"]["quality_flags"])
        self.assertEqual(summary["multiple_overnight_waking_dates"], 1)
        self.assertFalse(by_log["multi-a"]["primary_eligible"])
        self.assertFalse(by_log["multi-b"]["primary_eligible"])

    def test_overlapping_logs_are_flagged_for_both_sessions(self):
        rows = []
        rows += sleep_records(
            "p1", "first", datetime(2026, 3, 5, 22, 0), [0, 1, 2, 3]
        )
        rows += sleep_records(
            "p1", "second", datetime(2026, 3, 5, 22, 2), [0, 1, 2]
        )
        rows.sort(key=lambda row: (row[0], row[1], row[2]))
        episodes = list(iter_episodes(rows))
        identify_overlaps(episodes)
        self.assertTrue(all("overlaps_another_log" in item["quality_flags"] for item in episodes))

    def test_sleep_join_preserves_rows_and_keeps_missing_values_blank(self):
        def episode(log_id, waking_date, eligible=True):
            return {
                "id": "p1",
                "log_id": log_id,
                "waking_date": waking_date,
                "overnight_candidate": True,
                "primary_eligible": eligible,
                "start_timestamp": f"{waking_date} 00:00:00",
                "end_timestamp": f"{waking_date} 06:00:00",
                "recorded_minute_count": 360,
            }

        daily = [
            {"id": "p1", "activity_date": datetime(2026, 3, 2).date(), "is_complete_day": True, "total_steps": 100, "calories": 10, "total_active_minutes": 20, "sedentary_minutes": 30},
            {"id": "p1", "activity_date": datetime(2026, 3, 3).date(), "is_complete_day": False, "total_steps": 200, "calories": 20, "total_active_minutes": 30, "sedentary_minutes": 40},
            {"id": "p2", "activity_date": datetime(2026, 3, 2).date(), "is_complete_day": False, "total_steps": 300, "calories": 30, "total_active_minutes": 40, "sedentary_minutes": 50},
        ]
        matched, metrics = make_sleep_activity_table(
            daily,
            [
                episode("unique", "2026-03-02"),
                episode("ambiguous-a", "2026-03-03", False),
                episode("ambiguous-b", "2026-03-03", False),
            ],
        )
        self.assertEqual(len(matched), len(daily))
        self.assertEqual(matched[0]["sleep_match_status"], "matched")
        self.assertEqual(matched[0]["recorded_sleep_minutes"], 360)
        self.assertEqual(matched[1]["sleep_match_status"], "ambiguous_multiple_sessions")
        self.assertIsNone(matched[1]["recorded_sleep_minutes"])
        self.assertIsNone(matched[2]["recorded_sleep_minutes"])
        self.assertEqual(metrics["daily_rows_preserved"], 3)
        self.assertEqual(metrics["complete_matched_activity_days"], 1)
        self.assertFalse(metrics["row_multiplication"])
        self.assertTrue(metrics["sleep_is_missing_not_zero"])


class Phase3OutputTests(unittest.TestCase):
    def test_reproducibility_manifest_and_all_figures_exist(self):
        evidence = ROOT / "reports" / "evidence" / "P3"
        manifest_path = evidence / "run_manifest.json"
        index_path = evidence / "figures_index.json"
        self.assertTrue(manifest_path.is_file(), "Run python src/eda_analysis.py first")
        self.assertTrue(index_path.is_file(), "The figure index is part of the Phase 3 run")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        index = json.loads(index_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "PASS")
        self.assertFalse(manifest["source_working_tree_dirty"])
        self.assertEqual(len(index["figures"]), 9)
        self.assertEqual(len(manifest["outputs"]["figures"]), 9)
        self.assertEqual(
            len(manifest["outputs"]["evidence"]),
            len(set(manifest["outputs"]["evidence"])),
        )
        self.assertIn("reports/evidence/P3/run_manifest.json", manifest["outputs"]["evidence"])
        for item in index["figures"]:
            figure = ROOT / "reports" / "generated" / "eda" / "figures" / item["file"]
            self.assertTrue(figure.is_file(), item["file"])
            parsed = ElementTree.parse(figure)
            self.assertTrue(parsed.getroot().tag.endswith("svg"))
        alignment = json.loads((evidence / "sleep_alignment_metrics.json").read_text())
        self.assertTrue(alignment["sleep_is_missing_not_zero"])
        self.assertFalse(alignment["row_multiplication"])
        self.assertEqual(alignment["daily_rows_preserved"], 457)
        self.assertEqual(alignment["complete_matched_activity_days"], 0)
        time_metrics = json.loads((evidence / "time_accounting_metrics.json").read_text())
        primary = time_metrics["primary_summary"]
        self.assertEqual(primary["participant_days"], 161)
        self.assertEqual(primary["exact_1440_count"], 45)
        self.assertEqual(primary["within_thresholds"]["15"]["count"], 74)
        self.assertEqual(primary["within_thresholds"]["30"]["count"], 91)
        self.assertEqual(primary["within_thresholds"]["60"]["count"], 110)
        self.assertEqual(
            time_metrics["participant_mean_activity_vs_recorded_sleep_correlation"]["n_pairs"],
            18,
        )
        self.assertEqual(
            time_metrics["boundary_sensitivity"]["exclude_2016_04_12"]
            ["participant_days"],
            154,
        )
        self.assertEqual(
            time_metrics["boundary_sensitivity"]
            ["exclude_2016_04_11_and_2016_04_12"]["participant_days"],
            143,
        )
        accounting_csv = ROOT / "reports/generated/eda/tables/time_accounting.csv"
        with accounting_csv.open(newline="", encoding="utf-8") as stream:
            accounting = list(csv.DictReader(stream))
        self.assertEqual(len(accounting), 161)
        participant_csv = ROOT / "reports/generated/eda/tables/time_accounting_by_participant.csv"
        date_csv = ROOT / "reports/generated/eda/tables/time_accounting_by_date.csv"
        with participant_csv.open(encoding="utf-8") as stream:
            self.assertEqual(sum(1 for _ in stream) - 1, 18)
        with date_csv.open(encoding="utf-8") as stream:
            self.assertEqual(sum(1 for _ in stream) - 1, 23)
        figure = ROOT / "reports/generated/eda/figures/09_time_accounting_by_date.svg"
        tree = ElementTree.parse(figure)
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        plotted = tree.findall(".//svg:circle", namespace)
        self.assertEqual(len(plotted), len(accounting))
        chart_counts = Counter(
            (point.attrib["data-date"], point.attrib["data-combined-minutes"])
            for point in plotted
        )
        table_counts = Counter(
            (row["activity_date"], str(round(float(row["combined_recorded_minutes"]))))
            for row in accounting
        )
        self.assertEqual(chart_counts, table_counts)
        self.assertIn(
            "Activity + recorded sleep minutes",
            "".join(tree.getroot().itertext()),
        )
        reference_lines = [
            item for item in tree.findall(".//svg:line", namespace)
            if item.attrib.get("data-reference-minutes") == "1440"
        ]
        self.assertEqual(len(reference_lines), 1)
        self.assertIn("2016-04-12", "".join(tree.getroot().itertext()))


if __name__ == "__main__":
    unittest.main()
