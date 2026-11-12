import unittest
from pathlib import Path

from src.preprocess import OUTPUTS, OUTPUT_DIR, REFERENCE_DIR, compare_reference


class ProcessedReferenceIntegrationTests(unittest.TestCase):
    def test_generated_exports_match_committed_references(self):
        if not OUTPUT_DIR.is_dir():
            self.skipTest("Run `python src/preprocess.py` before the integration comparison.")

        for name, spec in OUTPUTS.items():
            generated = OUTPUT_DIR / spec["file"]
            reference = REFERENCE_DIR / spec["file"]
            self.assertTrue(generated.is_file(), f"Missing generated {generated.name}")
            result = compare_reference(
                generated,
                reference,
                spec["columns"],
                spec["numeric"],
            )
            self.assertTrue(
                result.get("matches"),
                f"{name} differs from its committed reference: {result}",
            )


if __name__ == "__main__":
    unittest.main()
