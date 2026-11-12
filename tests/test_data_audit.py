import csv
import tempfile
import unittest
from pathlib import Path

from src.data_audit import audit_file, parse_datetime, value_kind


DAILY_COLUMNS = [
    "Id", "ActivityDate", "TotalSteps", "TotalDistance", "TrackerDistance",
    "LoggedActivitiesDistance", "VeryActiveDistance", "ModeratelyActiveDistance",
    "LightActiveDistance", "SedentaryActiveDistance", "VeryActiveMinutes",
    "FairlyActiveMinutes", "LightlyActiveMinutes", "SedentaryMinutes", "Calories",
]


def daily_row(
    participant="4020332650",
    date="3/20/2016",
    steps="10",
    total_distance="1",
    tracker_distance="1",
    light_distance="1",
    very_active_minutes="0",
    lightly_active_minutes="10",
    calories="10",
):
    return [
        participant, date, steps, total_distance, tracker_distance, "0",
        "0", "0", light_distance, "0", very_active_minutes, "0",
        lightly_active_minutes, "100", calories,
    ]


def audit_daily_rows(rows):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dailyActivity_merged.csv"
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(DAILY_COLUMNS)
            writer.writerows(rows)
        return audit_file(path)


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
        rows = [
            daily_row(
                steps="0",
                total_distance="4",
                tracker_distance="4",
                light_distance="0",
                very_active_minutes="1",
            ),
            daily_row(
                date="3/21/2016",
                steps="100",
                total_distance="2",
                tracker_distance="2",
                light_distance="2",
                calories="100",
            ),
        ]
        result = audit_daily_rows(rows)

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

    def test_malformed_short_and_extra_rows_are_reported(self):
        row = daily_row(participant="1")
        result = audit_daily_rows([row[:-1], row + ["unexpected"]])

        self.assertEqual(result["malformed_rows"], 2)
        self.assertFalse(result["checks"]["row_width"])
        self.assertEqual(result["schema"][-1]["null_count"], 1)

    def test_missing_composite_key_field_is_reported(self):
        result = audit_daily_rows([daily_row(participant="")])

        self.assertEqual(result["missing_key_rows"], 1)
        self.assertFalse(result["checks"]["keys_complete"])

    def test_duplicate_composite_key_is_counted_without_dropping_rows(self):
        rows = [
            daily_row(participant="1", total_distance="1", light_distance="1"),
            daily_row(participant="1", total_distance="2", light_distance="2"),
        ]
        result = audit_daily_rows(rows)

        self.assertEqual(result["rows"], 2)
        self.assertEqual(result["duplicate_key_rows"], 1)


if __name__ == "__main__":
    unittest.main()
