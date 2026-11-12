import csv
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from src.phase5_common import ROOT, load_daily_rows


ASSOCIATION_DIR = ROOT / "reports" / "generated" / "associations"
ANOMALY_DIR = ROOT / "reports" / "generated" / "anomalies"
EVIDENCE_DIR = ROOT / "reports" / "evidence" / "P5"


class Phase5GeneratedArtifactTests(unittest.TestCase):
    def test_transactions_preserve_participant_day_mapping_and_family_exclusivity(self):
        with (ASSOCIATION_DIR / "transactions.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            transactions = list(csv.DictReader(stream))
        with (ASSOCIATION_DIR / "item_dictionary.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            dictionary = {
                row["item"]: row["family"] for row in csv.DictReader(stream)
            }
        rows = load_daily_rows()
        self.assertEqual(len(transactions), len(rows))
        self.assertEqual(len({row["transaction_id"] for row in transactions}), 457)
        self.assertEqual(
            len({(row["participant_id"], row["date"]) for row in transactions}),
            457,
        )
        self.assertEqual(
            {(row["participant_id"], row["date"]) for row in transactions},
            {
                (row["id"], row["activity_date"].isoformat())
                for row in rows
            },
        )
        for row in transactions:
            items = json.loads(row["items"])
            self.assertEqual(len(items), 6)
            self.assertEqual(
                len({dictionary[item] for item in items}),
                len(items),
            )

    def test_rules_contain_metrics_and_every_eligible_rule_meets_thresholds(self):
        with (ASSOCIATION_DIR / "association_rules.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rules = list(csv.DictReader(stream))
        self.assertEqual(len(rules), 860)
        eligible = [row for row in rules if row["threshold_eligible"] == "True"]
        self.assertEqual(len(eligible), 89)
        for row in eligible:
            self.assertGreaterEqual(float(row["support"]), 0.05)
            self.assertGreaterEqual(float(row["confidence"]), 0.60)
            self.assertGreaterEqual(float(row["lift"]), 1.10)
            self.assertGreaterEqual(int(row["distinct_participants"]), 5)
            self.assertTrue(row["leverage"] != "")
            self.assertTrue(row["min_support"] != "")

    def test_threshold_sensitivity_includes_support_confidence_lift_and_people(self):
        with (ASSOCIATION_DIR / "threshold_sensitivity.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        dimensions = {row["sensitivity_dimension"] for row in rows}
        self.assertEqual(
            dimensions,
            {
                "minimum_support",
                "minimum_confidence",
                "minimum_lift",
                "minimum_participants",
            },
        )
        self.assertEqual(len(rows), 24)
        by_key = {
            (
                row["scope"],
                row["sensitivity_dimension"],
                float(row["sensitivity_value"]),
            ): int(row["eligible_rules"])
            for row in rows
        }
        self.assertEqual(
            by_key[("all_days", "minimum_confidence", 0.6)], 89
        )
        self.assertEqual(
            by_key[("complete_days", "minimum_support", 0.05)], 108
        )

    def test_candidate_registry_keeps_all_457_daily_rows(self):
        with (ANOMALY_DIR / "candidate_registry.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 457)
        self.assertEqual(
            len({(row["participant_id"], row["date"]) for row in rows}),
            457,
        )
        self.assertEqual(
            sum(row["any_candidate"] == "True" for row in rows), 217
        )
        self.assertEqual(
            sum(float(row["total_steps"]) == 0 for row in rows), 61
        )

    def test_phase3_daily_and_sleep_candidates_remain_separate(self):
        with (ANOMALY_DIR / "phase3_daily_candidate_flags.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            daily = list(csv.DictReader(stream))
        with (ANOMALY_DIR / "phase3_sleep_candidates.csv").open(
            newline="", encoding="utf-8"
        ) as stream:
            sleep = list(csv.DictReader(stream))
        self.assertEqual(len(daily), 140)
        self.assertEqual(len(sleep), 111)
        self.assertTrue(all(row["record_type"] == "sleep_episode" for row in sleep))

    def test_distance_screens_and_boundary_sensitivity_are_explicit(self):
        metrics = json.loads(
            (EVIDENCE_DIR / "anomaly_metrics.json").read_text(encoding="utf-8")
        )
        distance = metrics["distance_screens"]
        self.assertEqual(distance["phase1_candidate_days"], 104)
        self.assertEqual(distance["phase2_candidate_days"], 65)
        self.assertEqual(distance["phase1_only_days"], 39)
        self.assertTrue(distance["not_interchangeable"])
        boundary = metrics["date_boundary_sensitivity"]
        self.assertEqual(boundary["boundary_date"], "2016-04-12")
        self.assertTrue(boundary["primary_retains_boundary"])
        self.assertEqual(boundary["primary_rows"], 457)
        self.assertEqual(boundary["sensitivity_rows"], 433)

    def test_svg_figures_are_valid_accessible_and_do_not_show_participant_ids(self):
        figures = json.loads(
            (EVIDENCE_DIR / "figures_index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(figures), 8)
        ids = {str(row["id"]) for row in load_daily_rows()}
        for figure in figures:
            path = ROOT / figure["file"]
            self.assertTrue(path.is_file())
            root = ET.parse(path).getroot()
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertTrue(root.find("{http://www.w3.org/2000/svg}title").text)
            self.assertTrue(root.find("{http://www.w3.org/2000/svg}desc").text)
            self.assertTrue(figure["sample"])
            self.assertTrue(figure["units"])
            self.assertTrue(figure["parameters"])
            self.assertTrue(figure["legend"])
            self.assertTrue(figure["interpretation"])
            self.assertTrue(figure["limitation"])
            contents = path.read_text(encoding="utf-8")
            self.assertFalse(any(participant_id in contents for participant_id in ids))

    def test_run_manifest_records_only_zero_cost_local_analysis(self):
        manifest = json.loads(
            (EVIDENCE_DIR / "run_manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["status"], "PASS")
        self.assertFalse(manifest["paid_resources_used"])
        self.assertEqual(manifest["package_installs"], 0)
        self.assertEqual(manifest["runtime"]["third_party_packages_used"], [])
        self.assertEqual(len(manifest["figure_validation"]["figures"]), 8)


if __name__ == "__main__":
    unittest.main()
