import json
import unittest
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
    weekday_weekend_analysis,
)
from src.sleep_analysis import (
    assign_primary_eligibility,
    identify_overlaps,
    iter_episodes,
)


ROOT = Path(__file__).resolve().parents[1]


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
        self.assertEqual(len(index["figures"]), 8)
        self.assertEqual(len(manifest["outputs"]["figures"]), 8)
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


if __name__ == "__main__":
    unittest.main()
