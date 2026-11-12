import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.preprocess import (
    RAW_SCHEMAS,
    SleepDeduplicator,
    check_alignment,
    normalize_columns,
    normalized_csv,
    numpy_isclose,
    parse_date,
    parse_timestamp,
    transform_daily,
    transform_weight,
)


def valid_daily_row(**changes):
    row = {
        "id": "00123",
        "activity_date": "3/20/2016",
        "total_steps": "0",
        "total_distance": "1.005",
        "tracker_distance": "1.005",
        "logged_activities_distance": "0",
        "very_active_distance": "0",
        "moderately_active_distance": "0",
        "light_active_distance": "0.5",
        "sedentary_active_distance": "0.5",
        "very_active_minutes": "0",
        "fairly_active_minutes": "0",
        "lightly_active_minutes": "60",
        "sedentary_minutes": "1380",
        "calories": "100",
    }
    row.update(changes)
    return row


class PreprocessUnitTests(unittest.TestCase):
    def test_column_normalization(self):
        self.assertEqual(
            normalize_columns(["AverageIntensity", "LogId", "activity date"]),
            ["average_intensity", "log_id", "activity_date"],
        )

    def test_explicit_date_and_timestamp_formats(self):
        self.assertEqual(parse_date("3/20/2016", "date").date().isoformat(), "2016-03-20")
        self.assertEqual(
            parse_timestamp("3/20/2016 7:08:09 PM", "date").hour,
            19,
        )
        with self.assertRaises(ValueError):
            parse_timestamp("not-a-date", "date")

    def test_daily_transform_is_deterministic_and_keeps_string_id(self):
        row = valid_daily_row()
        first = transform_daily(row.copy())
        second = transform_daily(row.copy())
        self.assertEqual(first, second)
        self.assertEqual(first["id"], "00123")
        self.assertEqual(first["activity_date"], "2016-03-20")
        self.assertEqual(first["total_recorded_minutes"], "1440")
        self.assertEqual(first["is_complete_day"], "True")
        self.assertEqual(first["distance_discrepancy"], "False")

    def test_daily_incomplete_day_and_distance_flag(self):
        row = valid_daily_row(
            total_distance="1.02",
            lightly_active_minutes="59",
        )
        transformed = transform_daily(row)
        self.assertEqual(transformed["is_complete_day"], "False")
        self.assertEqual(transformed["distance_discrepancy"], "True")
        self.assertTrue(numpy_isclose(1.005, 1.0))
        self.assertFalse(numpy_isclose(1.02, 1.0))

    def test_sleep_deduplication_keeps_identical_first_row(self):
        deduplicator = SleepDeduplicator()
        row = {"id": "1", "date": "3/20/2016 1:00:00 AM", "value": "1", "log_id": "99"}
        self.assertTrue(deduplicator.keep(row))
        self.assertFalse(deduplicator.keep(row.copy()))
        self.assertEqual(deduplicator.duplicate_occurrences, 1)
        self.assertEqual(len(deduplicator.conflicting_keys), 0)

    def test_sleep_duplicate_conflict_stops_deduplication(self):
        deduplicator = SleepDeduplicator()
        row = {"id": "1", "date": "3/20/2016 1:00:00 AM", "value": "1", "log_id": "99"}
        deduplicator.keep(row)
        with self.assertRaisesRegex(ValueError, "Conflicting values"):
            deduplicator.keep({**row, "value": "2"})

    def test_sleep_missing_composite_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            SleepDeduplicator().keep(
                {"id": "1", "date": "", "value": "1", "log_id": "99"}
            )

    def test_malformed_csv_row_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dailyActivity_merged.csv"
            header = [
                "Id", "ActivityDate", "TotalSteps", "TotalDistance",
                "TrackerDistance", "LoggedActivitiesDistance", "VeryActiveDistance",
                "ModeratelyActiveDistance", "LightActiveDistance",
                "SedentaryActiveDistance", "VeryActiveMinutes", "FairlyActiveMinutes",
                "LightlyActiveMinutes", "SedentaryMinutes", "Calories",
            ]
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(header)
                writer.writerow(["1", "3/20/2016"])
            with normalized_csv(path) as (_, rows):
                with self.assertRaisesRegex(ValueError, "malformed row"):
                    next(rows)

    def test_weight_transform_drops_fat_and_preserves_string_ids(self):
        row = {
            "id": "00123",
            "date": "3/20/2016 7:08:09 PM",
            "weight_kg": "50.5",
            "weight_pounds": "111.3",
            "fat": "",
            "bmi": "20.1",
            "is_manual_report": "True",
            "log_id": "00099",
        }
        result = transform_weight(row)
        self.assertNotIn("fat", result)
        self.assertEqual(result["id"], "00123")
        self.assertEqual(result["log_id"], "00099")
        self.assertEqual(result["date"], "2016-03-20 19:08:09")


class AlignmentTests(unittest.TestCase):
    def write_hourly_group(self, root, orders):
        filenames = [
            "hourlyCalories_merged.csv",
            "hourlyIntensities_merged.csv",
            "hourlySteps_merged.csv",
        ]
        schemas = [
            RAW_SCHEMAS[filenames[0]],
            RAW_SCHEMAS[filenames[1]],
            RAW_SCHEMAS[filenames[2]],
        ]
        for filename, schema, order in zip(filenames, schemas, orders):
            path = root / filename
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                raw_headers = [
                    {"id": "Id", "activity_hour": "ActivityHour", "calories": "Calories",
                     "total_intensity": "TotalIntensity", "average_intensity": "AverageIntensity",
                     "step_total": "StepTotal"}[column]
                    for column in schema
                ]
                writer.writerow(raw_headers)
                for participant, timestamp in order:
                    values = {
                        "id": participant,
                        "activity_hour": timestamp,
                        "calories": "10",
                        "total_intensity": "2",
                        "average_intensity": "0.5",
                        "step_total": "100",
                    }
                    writer.writerow([values[column] for column in schema])
        return filenames

    def run_alignment(self, root, orders):
        filenames = self.write_hourly_group(root, orders)
        with patch("src.preprocess.RAW_DIR", root):
            return check_alignment("test", filenames, ["id", "activity_hour"])

    def test_hourly_alignment_with_identical_order_passes(self):
        rows = [("1", "3/20/2016 1:00:00 AM"), ("2", "3/20/2016 1:00:00 AM")]
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_alignment(Path(directory), [rows, rows, rows])
        self.assertTrue(result["aligned_and_unique"])
        self.assertEqual(result["rows_compared"], 2)

    def test_unequal_key_order_is_rejected(self):
        first = [("1", "3/20/2016 1:00:00 AM"), ("2", "3/20/2016 1:00:00 AM")]
        reversed_rows = list(reversed(first))
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_alignment(
                Path(directory), [first, reversed_rows, first]
            )
        self.assertFalse(result["aligned_and_unique"])
        self.assertEqual(result["key_order_mismatch_rows"], 2)

    def test_duplicate_join_keys_fail_cardinality_check(self):
        duplicated = [
            ("1", "3/20/2016 1:00:00 AM"),
            ("1", "3/20/2016 1:00:00 AM"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_alignment(
                Path(directory), [duplicated, duplicated, duplicated]
            )
        self.assertFalse(result["aligned_and_unique"])
        self.assertEqual(result["duplicate_key_rows"], 1)

    def test_missing_join_key_is_rejected(self):
        rows = [("", "3/20/2016 1:00:00 AM")]
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_alignment(Path(directory), [rows, rows, rows])
        self.assertFalse(result["aligned_and_unique"])
        self.assertEqual(result["missing_key_rows"], 1)

    def test_unequal_source_lengths_are_rejected(self):
        first = [
            ("1", "3/20/2016 1:00:00 AM"),
            ("2", "3/20/2016 1:00:00 AM"),
        ]
        shorter = first[:1]
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_alignment(
                Path(directory), [first, shorter, first]
            )
        self.assertFalse(result["aligned_and_unique"])
        self.assertEqual(result["length_mismatch_rows"], 1)


if __name__ == "__main__":
    unittest.main()
