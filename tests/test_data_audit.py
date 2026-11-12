import csv
import tempfile
import unittest
from pathlib import Path

from src.data_audit import audit_file, parse_datetime, value_kind


class DataAuditTests(unittest.TestCase):
    def test_parses_observed_date_and_timestamp_formats(self):
        self.assertEqual(
            parse_datetime("3/25/2016").isoformat(sep=" "),
            "2016-03-25 00:00:00",
        )
        self.assertEqual(
            parse_datetime("4/1/2016 7:54:00 AM").isoformat(sep=" "),
            "2016-04-01 07:54:00",
        )

    def test_invalid_date_is_not_silently_coerced(self):
        self.assertIsNone(parse_datetime("not-a-date"))

    def test_lexical_type_inference(self):
        self.assertEqual(value_kind("True"), "boolean")
        self.assertEqual(value_kind("0"), "integer")
        self.assertEqual(value_kind("0.75"), "number")
        self.assertEqual(value_kind("id-12"), "string")

    def test_daily_key_and_quality_flags(self):
        columns = [
            "Id", "ActivityDate", "TotalSteps", "TotalDistance", "TrackerDistance",
            "LoggedActivitiesDistance", "VeryActiveDistance", "ModeratelyActiveDistance",
            "LightActiveDistance", "SedentaryActiveDistance", "VeryActiveMinutes",
            "FairlyActiveMinutes", "LightlyActiveMinutes", "SedentaryMinutes", "Calories",
        ]
        rows = [
            ["4020332650", "3/20/2016", "0", "4", "4", "0", "0", "0", "0", "0", "1", "0", "0", "100", "10"],
            ["4020332650", "3/20/2016", "100", "2", "2", "0", "0", "0", "2", "0", "0", "0", "10", "100", "100"],
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "dailyActivity_merged.csv"
            with path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream, lineterminator="\n")
                writer.writerow(columns)
                writer.writerows(rows)
            result = audit_file(path)

        self.assertEqual(result["duplicate_key_rows"], 1)
        self.assertEqual(result["quality_flags"]["zero_step_rows"], 1)
        self.assertEqual(result["quality_flags"]["zero_step_positive_calories_rows"], 1)
        self.assertEqual(
            result["quality_flags"]["zero_step_positive_active_minutes_rows"], 1
        )
        self.assertEqual(
            result["quality_flags"]["participant_4020332650_component_mismatch_rows"],
            1,
        )
        self.assertEqual(
            result["quality_flags"]["participant_4020332650_max_component_abs_diff"],
            4.0,
        )


if __name__ == "__main__":
    unittest.main()
