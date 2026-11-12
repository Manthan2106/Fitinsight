import unittest

from src.data_audit import parse_datetime, value_kind


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


if __name__ == "__main__":
    unittest.main()
