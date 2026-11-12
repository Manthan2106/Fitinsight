"""Fresh-kernel reproducibility and dashboard contract checks."""

from __future__ import annotations

import ast
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

import nbformat
from nbclient import NotebookClient


ROOT = Path(__file__).resolve().parents[1]
PHASE_DIR = ROOT / "notebooks" / "phases"
PHASES = [
    "01_Data_Audit.ipynb",
    "02_Data_Preprocessing.ipynb",
    "03_Exploratory_Data_Analysis.ipynb",
    "04_Clustering_and_PCA.ipynb",
    "05_Association_and_Anomalies.ipynb",
    "06_Interactive_Dashboard.ipynb",
]


P6_WIDGET_SMOKE = r"""
candidate_filter.value = 'All flagged candidates'
assert len(panel_state['candidate_rows']) == 217
candidate_filter.value = 'All records'
assert len(panel_state['candidate_rows']) == 457
cluster_cohort.value = 'complete_days'
assert panel_state['cluster_eligible_count'] == 24 and len(cluster_choice.options) == 3
cluster_cohort.value = 'all_days'
assert panel_state['cluster_eligible_count'] == 35 and len(cluster_choice.options) == 4
pca_cohort.value = 'complete_days'
assert len(panel_state['pca_rows']) == 24
pca_participant.value = next(row['id'] for row in panel_state['pca_rows'])
assert len(panel_state['pca_rows']) == 1
dbscan_min_samples.value = 4
assert len(panel_state['dbscan_rows']) == 5
dbscan_eps.value = dbscan_eps.options[1]
assert len(panel_state['dbscan_rows']) == 1
eligible_only.value = False
min_support.value = 0
min_confidence.value = 0
min_lift.value = 0
assert len(panel_state['rule_rows']) == 860
antecedent_search.value = 'no-such-item'
assert len(panel_state['rule_rows']) == 0
sleep_date.value = time_dates[0]
assert panel_state['time_rows'] and all(row['activity_date'] == time_dates[0] for row in panel_state['time_rows'])
complete_participant = next(row['id'] for row in activity if bool_value(row['is_complete_day']))
participant.value = complete_participant
coverage.value = 'Complete only'
assert panel_state['activity_rows'] and all(bool_value(row['is_complete_day']) for row in panel_state['activity_rows'])
print('FITINSIGHT_PROOF | P6-WIDGET-SMOKE | anomaly_union=217/457 | cohort_assignments=35/24 | PCA_highlight=PASS | DBSCAN_grid_controls=PASS | rule_filters=860/0 | date_and_coverage_filters=PASS')
"""


def notebook_code(notebook: dict) -> str:
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook.cells
        if cell.cell_type == "code"
    )


def collected_streams(notebook: dict) -> str:
    return "\n".join(
        output.text
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type == "stream"
    )


def svg_output_count(notebook: dict) -> int:
    return sum(
        1
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.output_type in {"display_data", "execute_result"}
        and "image/svg+xml" in output.data
    )


class NotebookWorkflowTests(unittest.TestCase):
    def test_notebooks_are_self_contained_and_syntax_valid(self) -> None:
        self.assertEqual([path.name for path in sorted(PHASE_DIR.glob("*.ipynb"))], PHASES)
        for filename in PHASES:
            with self.subTest(notebook=filename):
                notebook = nbformat.read(PHASE_DIR / filename, as_version=4)
                all_source = "\n".join(
                    "".join(cell.get("source", [])) for cell in notebook.cells
                )
                code = notebook_code(notebook)
                self.assertNotRegex(all_source, re.compile(r"\bsrc(?:/|\b)|python\s+src/", re.I))
                self.assertNotRegex(code, re.compile(r"^\s*!\w|%run\s+src", re.M))
                code_ids = [
                    cell.id for cell in notebook.cells if cell.cell_type == "code"
                ]
                self.assertEqual(len(code_ids), len(set(code_ids)))
                for cell in notebook.cells:
                    if cell.cell_type == "code":
                        ast.parse("".join(cell.source), filename=f"{filename}:{cell.id}")
                self.assertTrue(
                    any(
                        cell.cell_type == "markdown"
                        and (
                            "Research objective" in "".join(cell.source)
                            or "Research question" in "".join(cell.source)
                        )
                        for cell in notebook.cells
                    ),
                    f"{filename} needs an explicit research objective or question",
                )
                self.assertTrue(
                    any(
                        cell.cell_type == "markdown"
                        and any(
                            term in "".join(cell.source).casefold()
                            for term in ("conclusion", "interpretation", "findings")
                        )
                        for cell in notebook.cells
                    ),
                    f"{filename} needs a conclusion or interpretation section",
                )

    def test_p3_p4_p5_generate_all_expected_inline_svg(self) -> None:
        expected = {
            "03_Exploratory_Data_Analysis.ipynb": 9,
            "04_Clustering_and_PCA.ipynb": 12,
            "05_Association_and_Anomalies.ipynb": 8,
        }
        for filename, count in expected.items():
            notebook = nbformat.read(PHASE_DIR / filename, as_version=4)
            code = notebook_code(notebook)
            if filename.startswith("03_"):
                self.assertIn("All nine generated SVG figures", code)
            elif filename.startswith("04_"):
                self.assertIn("All twelve generated SVG figures", code)
            self.assertIn(f"=={count}", code)

    def test_fresh_kernels_run_without_src_and_save_outputs(self) -> None:
        if os.environ.get("FITINSIGHT_RUN_NOTEBOOK_KERNELS") != "1":
            self.skipTest(
                "Run with FITINSIGHT_RUN_NOTEBOOK_KERNELS=1 for the full "
                "isolated fresh-kernel notebook pass."
            )
        with tempfile.TemporaryDirectory(prefix="fitinsight-notebooks-") as temp:
            isolated = Path(temp)
            for directory in ("data", "reports", "notebooks"):
                (isolated / directory).symlink_to(ROOT / directory, target_is_directory=True)
            self.assertFalse((isolated / "src").exists())

            for filename in PHASES:
                with self.subTest(notebook=filename):
                    path = PHASE_DIR / filename
                    notebook = nbformat.read(path, as_version=4)
                    if filename == "06_Interactive_Dashboard.ipynb":
                        notebook.cells.append(
                            nbformat.v4.new_code_cell(P6_WIDGET_SMOKE, id="p6-widget-smoke-test")
                        )
                    NotebookClient(
                        notebook,
                        timeout=900,
                        kernel_name="python3",
                        resources={"metadata": {"path": str(isolated)}},
                    ).execute()

                    errors = [
                        (cell.id, output.ename, output.evalue)
                        for cell in notebook.cells
                        if cell.cell_type == "code"
                        for output in cell.get("outputs", [])
                        if output.output_type == "error"
                    ]
                    self.assertEqual(errors, [])
                    streams = collected_streams(notebook)
                    self.assertIn("FITINSIGHT_PROOF", streams)
                    if filename.startswith("03_"):
                        self.assertGreaterEqual(svg_output_count(notebook), 9)
                    elif filename.startswith("04_"):
                        self.assertGreaterEqual(svg_output_count(notebook), 12)
                    elif filename.startswith("05_"):
                        self.assertGreaterEqual(svg_output_count(notebook), 8)
                    elif filename.startswith("06_"):
                        self.assertIn("P6-WIDGET-SMOKE", streams)
                        self.assertIn("anomaly_union=217/457", streams)
                        notebook.cells.pop()
                    nbformat.write(notebook, path)


if __name__ == "__main__":
    unittest.main()
