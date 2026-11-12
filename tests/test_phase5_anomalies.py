import math
import unittest
from datetime import date, timedelta

from src.anomaly_detection import (
    _distance_screens,
    active_share,
    global_iqr_screen,
    knn_screen,
    load_phase3_candidate_flags,
    within_person_robust_screen,
)
from src.phase5_common import load_daily_rows, quantile


def daily_row(
    participant,
    day_index,
    *,
    steps=100,
    minutes=1440,
    active=100,
    calories=2000,
    distance=1.0,
    component_sum=1.0,
    complete=None,
):
    if complete is None:
        complete = minutes == 1440
    return {
        "id": participant,
        "activity_date": date(2016, 3, 1) + timedelta(days=day_index),
        "weekday": (date(2016, 3, 1) + timedelta(days=day_index)).weekday(),
        "total_steps": float(steps),
        "calories": float(calories),
        "total_distance": float(distance),
        "component_distance_sum": float(component_sum),
        "total_recorded_minutes": float(minutes),
        "total_active_minutes": float(active),
        "very_active_minutes": float(active) / 3,
        "is_complete_day": complete,
        "distance_discrepancy": False,
        "sedentary_minutes": float(minutes - active),
    }


class RobustStatisticsTests(unittest.TestCase):
    def test_quantile_matches_phase3_linear_interpolation(self):
        self.assertEqual(quantile([0, 10, 20, 30], 0.25), 7.5)
        self.assertEqual(quantile([], 0.5), None)

    def test_active_share_is_missing_for_zero_recorded_duration(self):
        row = daily_row("p1", 0, minutes=0, active=0, complete=False)
        self.assertIsNone(active_share(row))

    def test_global_iqr_uses_two_sided_fences_and_keeps_rows(self):
        rows = [
            daily_row("p1", i, steps=value)
            for i, value in enumerate([0, 1, 2, 3, 100])
        ]
        fences, flags = global_iqr_screen(rows)
        self.assertEqual(fences["total_steps"]["observed"], 5)
        self.assertIn(("p1", "2016-03-05"), flags)
        self.assertEqual(flags[("p1", "2016-03-05")][0]["tail"], "high")
        self.assertEqual(len(rows), 5)

    def test_zero_mad_uses_iqr_fallback_without_infinite_scores(self):
        values = [0, 0, 0, 10, 100]
        rows = [
            daily_row("p1", i, steps=value, active=10 + value)
            for i, value in enumerate(values)
        ]
        output, flags, summary = within_person_robust_screen(rows)
        step_rows = [row for row in output if row["metric"] == "total_steps"]
        self.assertTrue(all(
            row["score_method"] == "IQR_fallback_zero_MAD"
            for row in step_rows
        ))
        self.assertTrue(all(
            row["score"] is None or math.isfinite(row["score"])
            for row in step_rows
        ))
        self.assertTrue(any(row["flagged"] for row in step_rows))
        self.assertEqual(summary["iqr_fallback_groups"], 2)
        self.assertIn(("p1", "2016-03-05"), flags)

    def test_zero_mad_and_zero_iqr_remain_unscaled_not_infinite(self):
        rows = [
            daily_row("p1", i, steps=5, active=10)
            for i in range(5)
        ]
        output, flags, summary = within_person_robust_screen(rows)
        self.assertTrue(all(row["score"] is None for row in output))
        self.assertTrue(all(
            row["status"] == "not_scored_zero_robust_scale"
            for row in output
        ))
        self.assertEqual(flags, {})
        self.assertEqual(summary["unscalable_groups"], 2)

    def test_within_person_minimum_days_is_enforced(self):
        rows = [
            daily_row("p1", i, steps=i * 10)
            for i in range(4)
        ]
        output, flags, summary = within_person_robust_screen(rows, min_days=5)
        self.assertTrue(all(row["status"] == "insufficient_days" for row in output))
        self.assertEqual(flags, {})
        self.assertEqual(summary["groups_by_status"]["insufficient_days"], 2)


class KnnAndDistanceTests(unittest.TestCase):
    def test_knn_excludes_self_and_uses_deterministic_top_fraction(self):
        rows = [
            daily_row(f"p{i}", 0, steps=100 * i + 100, active=50 + i * 10,
                      calories=1800 + i * 90)
            for i in range(6)
        ]
        scores, flags, summaries = knn_screen(
            rows, k_values=(2,), top_fraction=0.34
        )
        self.assertIn(("pooled", 2), flags)
        self.assertEqual(len(flags[("pooled", 2)]), 3)
        self.assertEqual(len(summaries), 2)  # pooled and complete-day cohorts
        pooled_rows = [row for row in scores if row["scope"] == "pooled"]
        self.assertEqual(len(pooled_rows), 6)
        self.assertTrue(all(row["effective_k"] == 2 for row in pooled_rows))
        self.assertTrue(all(
            math.isfinite(row["neighbor_mean_distance"])
            and row["rank_highest_first"] != 0
            for row in pooled_rows
        ))

    def test_zero_spread_features_are_handled_without_nan(self):
        rows = [
            daily_row(f"p{i}", 0, steps=100, calories=2000, active=100)
            for i in range(4)
        ]
        scores, flags, _ = knn_screen(rows, k_values=(2,), top_fraction=0.25)
        self.assertEqual(len(flags[("pooled", 2)]), 1)
        self.assertTrue(all(
            math.isfinite(row["neighbor_mean_distance"]) for row in scores
        ))

    def test_phase1_and_phase2_distance_definitions_are_distinct(self):
        rows = [
            daily_row(
                "p1", 0, distance=1.02, component_sum=1.0
            ),
            daily_row(
                "p2", 0, distance=1000.015, component_sum=1000.0
            ),
            daily_row(
                "p3", 0, distance=1.0, component_sum=1.0
            ),
        ]
        rows[0]["distance_discrepancy"] = True
        rows[1]["distance_discrepancy"] = False
        p1_keys, p2_keys, summary = _distance_screens(rows)
        self.assertEqual(len(p1_keys), 2)
        self.assertEqual(len(p2_keys), 1)
        self.assertEqual(summary["phase1_only_days"], 1)
        self.assertTrue(summary["not_interchangeable"])

    def test_current_distance_screens_retain_65_and_104_counts(self):
        rows = load_daily_rows()
        p1_keys, p2_keys, summary = _distance_screens(rows)
        self.assertEqual(len(rows), 457)
        self.assertEqual(len(p1_keys), 104)
        self.assertEqual(len(p2_keys), 65)
        self.assertTrue(summary["not_interchangeable"])


class ExistingPhase3EvidenceTests(unittest.TestCase):
    def test_phase3_candidate_flags_are_reused_at_their_original_grain(self):
        rows = load_daily_rows()
        p3 = load_phase3_candidate_flags(rows)
        self.assertEqual(len(p3["daily_rows"]), 140)
        self.assertEqual(len(p3["sleep_rows"]), 111)
        self.assertEqual(p3["metrics"]["daily_candidate_rows"], 140)
        self.assertEqual(p3["metrics"]["sleep_episode_candidate_rows"], 111)
        self.assertEqual(
            p3["metrics"]["daily_flag_counts"][
                "phase2_numpy_isclose_distance_flag"
            ],
            65,
        )
        self.assertTrue(all(
            row["record_type"] == "sleep_episode" for row in p3["sleep_rows"]
        ))


if __name__ == "__main__":
    unittest.main()
