import csv
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from src.activity_clustering import (
    EVIDENCE_DIR,
    FIGURE_DIR,
    TABLE_DIR,
    _align_ari,
    _svg_document,
    _write_csv,
    load_daily,
    participant_features,
)
from src.clustering_math import (
    adjusted_rand_index,
    calinski_harabasz_score,
    cluster_scores,
    dbscan,
    davies_bouldin_score,
    kmeans_fit,
    pca,
    sample_standard_deviation,
    silhouette_score,
    standardize,
)


def day(
    participant_id,
    date,
    steps,
    total_minutes,
    active_minutes,
    complete=False,
):
    return {
        "id": participant_id,
        "activity_date": date,
        "total_steps": float(steps),
        "very_active_minutes": float(active_minutes),
        "fairly_active_minutes": 0.0,
        "lightly_active_minutes": 0.0,
        "sedentary_minutes": float(total_minutes - active_minutes),
        "total_recorded_minutes": float(total_minutes),
        "is_complete_day": complete,
    }


class ParticipantFeatureTests(unittest.TestCase):
    def test_features_keep_string_ids_zero_steps_and_mean_daily_shares(self):
        rows = [
            day("0007", "2016-04-01", 0, 100, 10),
            day("0007", "2016-04-02", 100, 200, 100),
            day("0007", "2016-04-03", 200, 100, 30),
            day("0008", "2016-04-01", 10, 60, 10),
            day("0008", "2016-04-02", 20, 90, 45),
            day("0008", "2016-04-03", 30, 0, 0),
        ]
        inventory, features = participant_features(rows)
        self.assertEqual([row["id"] for row in features], ["0007"])
        self.assertEqual(features[0]["recorded_days"], 3)
        self.assertEqual(features[0]["mean_steps"], 100)
        self.assertAlmostEqual(features[0]["mean_active_share"], 0.3)
        self.assertAlmostEqual(features[0]["step_variability"], 100)
        self.assertEqual(features[0]["zero_step_days"], 1)
        self.assertEqual(inventory[1]["positive_recorded_minute_days"], 2)
        self.assertFalse(inventory[1]["eligible"])
        ratio_of_sums = 140 / 400
        self.assertNotAlmostEqual(features[0]["mean_active_share"], ratio_of_sums)

    def test_sample_standard_deviation_uses_n_minus_one(self):
        self.assertAlmostEqual(sample_standard_deviation([0, 100, 200]), 100)
        with self.assertRaises(ValueError):
            sample_standard_deviation([5])

    def test_loader_preserves_leading_zero_ids_and_checks_minute_total(self):
        headers = [
            "id", "activity_date", "total_steps", "very_active_minutes",
            "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
            "total_recorded_minutes", "is_complete_day",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerow(["0009", "2016-04-01", "0", "0", "0", "10", "90", "100", "false"])
            self.assertEqual(load_daily(path)[0]["id"], "0009")
            with path.open("a", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerow(
                    ["0009", "2016-04-01", "1", "0", "0", "10", "90", "100", "false"]
                )
            with self.assertRaisesRegex(ValueError, "duplicate participant-day"):
                load_daily(path)

    def test_loader_rejects_phase_two_completeness_flag_mismatch(self):
        headers = [
            "id", "activity_date", "total_steps", "very_active_minutes",
            "fairly_active_minutes", "lightly_active_minutes", "sedentary_minutes",
            "total_recorded_minutes", "is_complete_day",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerow(["id", "2016-04-01", "0", "0", "0", "600", "840", "1440", "false"])
            with self.assertRaisesRegex(ValueError, "complete-day flag mismatch"):
                load_daily(path)

    def test_zero_duration_day_is_not_eligible_for_active_share(self):
        rows = [
            day("id", "d1", 0, 0, 0),
            day("id", "d2", 10, 100, 50),
            day("id", "d3", 20, 100, 0),
            day("id", "d4", 30, 100, 30),
        ]
        inventory, features = participant_features(rows)
        self.assertEqual(inventory[0]["activity_days"], 4)
        self.assertEqual(inventory[0]["positive_recorded_minute_days"], 3)
        self.assertEqual(features[0]["recorded_days"], 3)


class ScalingAndKMeansTests(unittest.TestCase):
    def test_standardization_has_zero_mean_unit_population_variance_and_constant_policy(self):
        scaled, metadata = standardize([[1, 7], [2, 7], [3, 7]])
        self.assertAlmostEqual(sum(row[0] for row in scaled) / 3, 0)
        self.assertAlmostEqual(sum(row[0] ** 2 for row in scaled) / 3, 1)
        self.assertTrue(metadata[1]["constant"])
        self.assertEqual([row[1] for row in scaled], [0, 0, 0])
        self.assertFalse(metadata[0]["constant"])

    def test_standardize_rejects_ragged_or_nonfinite_matrix(self):
        with self.assertRaisesRegex(ValueError, "equal dimensions"):
            standardize([[1, 2], [3]])
        with self.assertRaisesRegex(ValueError, "finite"):
            standardize([[1, float("nan")], [2, 3]])

    def test_kmeans_recovers_two_separated_groups_deterministically(self):
        points = [
            [-4.0, -4.1], [-3.9, -4.0], [-4.1, -3.8],
            [4.0, 4.1], [3.9, 4.0], [4.1, 3.8],
        ]
        first = kmeans_fit(points, 2, n_init=8, seed=42)
        second = kmeans_fit(points, 2, n_init=8, seed=42)
        self.assertEqual(first["labels"], second["labels"])
        self.assertEqual(first["inertia"], second["inertia"])
        self.assertEqual(sorted(__import__("collections").Counter(first["labels"]).values()), [3, 3])
        self.assertAlmostEqual(first["inertia"], 0.1333333333333333)

    def test_kmeans_empty_cluster_repair_keeps_all_labels_populated(self):
        points = [[0, 0], [0, 0], [1, 1], [1, 1], [5, 5]]
        result = kmeans_fit(points, 4, n_init=4, seed=11)
        self.assertEqual(len(set(result["labels"])), 4)
        self.assertEqual(len(result["labels"]), len(points))

    def test_kmeans_rejects_invalid_k_and_n_init(self):
        with self.assertRaisesRegex(ValueError, "1 <= k"):
            kmeans_fit([[0], [1]], 2)
        with self.assertRaisesRegex(ValueError, "positive"):
            kmeans_fit([[0], [1], [2]], 2, n_init=0)

    def test_silhouette_and_other_scores_require_valid_partitions(self):
        points = [[0], [0.1], [4], [4.1]]
        labels = [0, 0, 1, 1]
        self.assertGreater(silhouette_score(points, labels), 0.9)
        self.assertIsNotNone(davies_bouldin_score(points, labels))
        self.assertIsNotNone(calinski_harabasz_score(points, labels))
        self.assertIsNone(silhouette_score(points, [0, 0, 0, 0]))
        self.assertIsNone(silhouette_score(points[:2], [0, 1]))
        self.assertIsNone(cluster_scores(points, [0, 0, 0, 0])["calinski_harabasz"])


class DensityAndPartitionTests(unittest.TestCase):
    def test_dbscan_labels_two_groups_and_noise_separately(self):
        points = [
            [-0.1, 0], [0, 0], [0.1, 0],
            [5, 5], [5.1, 5],
            [20, 20],
        ]
        labels = dbscan(points, eps=0.25, min_samples=2)
        self.assertEqual(labels[-1], -1)
        self.assertEqual(sum(label == -1 for label in labels), 1)
        self.assertEqual(len(set(label for label in labels if label >= 0)), 2)
        self.assertEqual(sorted(__import__("collections").Counter(
            label for label in labels if label >= 0
        ).values()), [2, 3])

    def test_dbscan_noise_border_points_can_join_a_cluster(self):
        points = [[0], [0.1], [0.2], [4], [4.1], [20]]
        labels = dbscan(points, eps=0.25, min_samples=3)
        self.assertEqual(len(set(label for label in labels if label >= 0)), 1)
        self.assertEqual(sum(label == -1 for label in labels), 3)

    def test_dbscan_rejects_invalid_parameters(self):
        with self.assertRaisesRegex(ValueError, "eps"):
            dbscan([[0], [1]], eps=0, min_samples=2)
        with self.assertRaisesRegex(ValueError, "min_samples"):
            dbscan([[0], [1]], eps=1, min_samples=0)

    def test_ari_is_invariant_to_cluster_label_permutation(self):
        self.assertAlmostEqual(
            adjusted_rand_index([0, 0, 1, 1, 2], [9, 9, 4, 4, 8]),
            1.0,
        )
        self.assertEqual(adjusted_rand_index([0, 0, 0], [4, 4, 4]), 1.0)
        with self.assertRaisesRegex(ValueError, "aligned"):
            adjusted_rand_index([0], [0])

    def test_cohort_ari_aligns_only_shared_participant_ids(self):
        score, count = _align_ari(
            {"a": 0, "b": 0, "c": 1, "d": 1},
            {"a": 8, "b": 8, "c": 4, "extra": 4},
        )
        self.assertEqual(count, 3)
        self.assertAlmostEqual(score, 1.0)


class PcaAndArtifactTests(unittest.TestCase):
    def test_pca_recovers_known_diagonal_covariance(self):
        points = [[-2, 0], [-1, 0], [1, 0], [2, 0], [0, -1], [0, 1]]
        result = pca(points)
        self.assertAlmostEqual(result["variance_ratios"][0], 5 / 6)
        self.assertAlmostEqual(result["variance_ratios"][1], 1 / 6)
        self.assertAlmostEqual(result["components"][0][0], 1.0)
        self.assertLess(result["orthogonality_error"], 1e-12)
        self.assertLess(result["eigen_residual"], 1e-12)

    def test_pca_components_are_orthogonal_and_variance_sums_to_one(self):
        points = [
            [-2, 1, 0], [-1, -1, 2], [0, 0, -1], [1, 2, 0], [2, -2, -1],
        ]
        result = pca(points)
        self.assertAlmostEqual(sum(result["variance_ratios"]), 1.0)
        self.assertEqual(len(result["coordinates"]), len(points))
        self.assertTrue(all(len(row) == 3 for row in result["coordinates"]))
        self.assertLess(result["orthogonality_error"], 1e-10)
        self.assertLess(result["eigen_residual"], 1e-9)

    def test_pca_reconstruction_is_invariant_to_component_sign_flips(self):
        points = [[-2, 1], [-1, -1], [0, 0], [1, 2], [2, -2]]
        result = pca(points)
        flipped_components = [[-value for value in row] for row in result["components"]]
        for row_index, point in enumerate(points):
            original = [
                sum(result["coordinates"][row_index][component] * result["components"][component][column]
                    for component in range(2))
                for column in range(2)
            ]
            flipped = [
                sum(-result["coordinates"][row_index][component] * flipped_components[component][column]
                    for component in range(2))
                for column in range(2)
            ]
            self.assertAlmostEqual(original[0], flipped[0])
            self.assertAlmostEqual(original[1], flipped[1])
            self.assertAlmostEqual(original[0] + result["mean"][0], point[0])
            self.assertAlmostEqual(original[1] + result["mean"][1], point[1])

    def test_pca_rejects_one_row_and_ragged_input(self):
        with self.assertRaisesRegex(ValueError, "at least two"):
            pca([[1, 2]])
        with self.assertRaisesRegex(ValueError, "rectangular"):
            pca([[1, 2], [3]])

    def test_csv_writer_preserves_headers_and_blank_missing_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "small.csv"
            _write_csv(path, [{"id": "0001", "value": None}], ["id", "value"])
            with path.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows, [{"id": "0001", "value": ""}])

    def test_svg_is_well_formed_and_has_accessible_title_and_description(self):
        svg = _svg_document("PCA view", "Four feature coordinates", "<circle cx=\"1\" cy=\"1\" r=\"1\"/>", "Exploratory only.")
        root = ElementTree.fromstring(svg)
        namespace = "{http://www.w3.org/2000/svg}"
        self.assertEqual(root.tag, f"{namespace}svg")
        self.assertEqual(root.find(f"{namespace}title").text, "PCA view")
        self.assertIn("Exploratory only", root.find(f"{namespace}desc").text)

    def test_generated_pipeline_artifacts_and_manifest_are_complete(self):
        manifest_path = EVIDENCE_DIR / "run_manifest.json"
        self.assertTrue(manifest_path.is_file(), "run the documented P4 pipeline before the full suite")
        manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(manifest["table_count"], 9)
        self.assertEqual(manifest["figure_count"], 12)
        self.assertEqual(manifest["all_days"]["participants"], 35)
        self.assertEqual(manifest["all_days"]["cluster_sizes"], {"0": 17, "1": 16, "2": 2})
        for path in manifest["evidence_files"]:
            self.assertTrue((EVIDENCE_DIR.parents[2] / path).is_file(), path)
        self.assertEqual(len(list(TABLE_DIR.glob("*.csv"))), 9)
        self.assertEqual(len(list(FIGURE_DIR.glob("*.svg"))), 12)
        with (TABLE_DIR / "participant_clusters.csv").open(newline="", encoding="utf-8") as stream:
            assignments = list(csv.DictReader(stream))
        self.assertEqual(len(assignments), 35)
        self.assertTrue(all(row["all_days_cluster"] != "" for row in assignments))


if __name__ == "__main__":
    unittest.main()
