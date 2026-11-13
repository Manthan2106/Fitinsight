"""Fresh-kernel reproducibility and dashboard contract checks."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
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
FIGURE_EXPECTATIONS = {
    "03_Exploratory_Data_Analysis.ipynb": {
        "Daily step counts are right-skewed",
        "Step-count distributions differ by completeness",
        "Daily step averages need their coverage context",
        "Weekend and weekday means vary by participant",
        "Recorded-time composition differs by completeness",
        "Activity measures show varied rank associations",
        "Recorded sleep-log sizes vary",
        "Recorded sleep-log rows and waking-day steps",
        "Activity and sleep rows sometimes sum near 1,440",
    },
    "04_Clustering_and_PCA.ipynb": {
        "K-Means inertia by K",
        "K-Means silhouette by K",
        "Davies–Bouldin score by K",
        "Calinski–Harabasz score by K",
        "Selected K-Means cluster sizes",
        "Cluster feature profiles",
        "PCA projection of standardized participant features",
        "PCA explained variance by component",
        "PCA cumulative explained variance",
        "PCA feature loadings",
        "DBSCAN parameter sensitivity",
        "Cohort and eligibility sensitivity",
    },
    "05_Association_and_Anomalies.ipynb": {
        "Participant-day transaction item prevalence",
        "Association rule support and confidence",
        "Eligible association rules across support thresholds",
        "Global 1.5×IQR candidate flags by field",
        "Exploratory detector candidate counts",
        "kNN score summaries by coverage cohort",
        "Within-person robust candidate counts",
        "Last-date sensitivity for candidate counts",
    },
}
KERNEL_PROOFS = {
    "01_Data_Audit.ipynb": "P1-NOTEBOOK | files=11 | total_rows=7206142",
    "02_Data_Preprocessing.ipynb": "P2-NOTEBOOK | six_outputs=6 | reference_parity=PASS",
    "03_Exploratory_Data_Analysis.ipynb": "P3-NOTEBOOK | exact_tables=13 | exact_generated_SVGs=9",
    "04_Clustering_and_PCA.ipynb": "P4-NOTEBOOK | exact_tables=9 | exact_generated_SVGs=12",
    "05_Association_and_Anomalies.ipynb": "P5-NOTEBOOK | exact_association_csvs=8 | exact_anomaly_csvs=13",
    "06_Interactive_Dashboard.ipynb": "P6-INTERACTIVE-NOTEBOOK | panels=8",
}


P6_WIDGET_SMOKE = r"""
candidate_filter.value = 'All flagged candidates'
assert len(panel_state['candidate_rows']) == 217
candidate_filter.value = 'All records'
assert len(panel_state['candidate_rows']) == 457
cluster_cohort.value = 'complete_days'
assert panel_state['cluster_eligible_count'] == 24 and len(cluster_choice.options) == 3
cluster_cohort.value = 'all_days'
assert panel_state['cluster_eligible_count'] == 35 and len(cluster_choice.options) == 4
for cohort, expected in [('all_days', 35), ('complete_days', 24)]:
    pca_cohort.value = cohort
    assert panel_state['pca_point_count'] == expected
    assert len(panel_state['pca_rows']) == expected
    full_bounds = panel_state['pca_bounds']
    first_person = panel_state['pca_rows'][0]['id']
    pca_participant.value = first_person
    assert panel_state['pca_point_count'] == expected
    assert len(panel_state['pca_rows']) == expected
    assert panel_state['pca_bounds'] == full_bounds
    assert panel_state['pca_svg'].count('r="8"') == 1
    second_person = panel_state['pca_rows'][-1]['id']
    pca_participant.value = second_person
    assert panel_state['pca_point_count'] == expected
    assert len(panel_state['pca_rows']) == expected
    assert panel_state['pca_bounds'] == full_bounds
    assert panel_state['pca_svg'].count('r="8"') == 1
    pca_participant.value = 'All participants'
    assert panel_state['pca_point_count'] == expected
    assert len(panel_state['pca_rows']) == expected
    assert panel_state['pca_bounds'] == full_bounds
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
print('FITINSIGHT_PROOF | P6-WIDGET-SMOKE | anomaly_union=217/457 | cohort_assignments=35/24 | PCA_highlight=35/24_points_bounds_stable | DBSCAN_grid_controls=PASS | rule_filters=860/0 | date_and_coverage_filters=PASS')
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


def cell_svg_payloads(cell: dict) -> list[str]:
    payloads: list[str] = []
    for output in cell.get("outputs", []):
        if output.output_type not in {"display_data", "execute_result"}:
            continue
        value = output.data.get("image/svg+xml")
        if value is not None:
            payloads.append("".join(value) if isinstance(value, list) else value)
    return payloads


def svg_payloads(notebook: dict) -> list[str]:
    return [
        payload
        for cell in notebook.cells
        if cell.cell_type == "code"
        for payload in cell_svg_payloads(cell)
    ]


def svg_titles(payloads: list[str]) -> list[str]:
    titles = []
    for payload in payloads:
        root = ET.fromstring(payload)
        if not root.tag.endswith("svg"):
            raise AssertionError(f"expected SVG root, got {root.tag!r}")
        title = next(
            (node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "title"),
            None,
        )
        if title is None or not (title.text or "").strip():
            raise AssertionError("SVG output must contain a non-empty title")
        titles.append(title.text.strip())
    return titles


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tracked_notebook_hashes() -> dict[str, str]:
    return {path.name: file_sha256(path) for path in sorted(PHASE_DIR.glob("*.ipynb"))}


def hardlink_tree(source: Path, destination: Path) -> int:
    """Stage a read-only tree with same-volume hard links; never follow symlinks."""
    linked_bytes = 0
    destination.mkdir(parents=True)
    for source_path in source.rglob("*"):
        relative = source_path.relative_to(source)
        target = destination / relative
        if source_path.is_symlink():
            raise AssertionError(f"Symlinks are not allowed in the test workspace: {source_path}")
        if source_path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(source_path, target)
        except OSError as error:
            if source_path.stat().st_size <= 1024 * 1024:
                shutil.copy2(source_path, target)
            else:
                raise RuntimeError(
                    "Could not create a same-volume hard link for "
                    f"{source_path.relative_to(ROOT)} ({source_path.stat().st_size:,} bytes); "
                    "large datasets are not copied by this test."
                ) from error
        else:
            linked_bytes += source_path.stat().st_size
    return linked_bytes


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

    def test_saved_phase_3_to_5_outputs_contain_exact_validated_svg_figures(self) -> None:
        for filename, expected_titles in FIGURE_EXPECTATIONS.items():
            with self.subTest(notebook=filename):
                notebook = nbformat.read(PHASE_DIR / filename, as_version=4)
                payloads = svg_payloads(notebook)
                self.assertEqual(len(payloads), len(expected_titles))
                self.assertEqual(set(svg_titles(payloads)), expected_titles)

    def test_notebook_scratch_is_outside_the_repository_and_managed(self) -> None:
        for filename in PHASES[:5]:
            with self.subTest(notebook=filename):
                code = notebook_code(nbformat.read(PHASE_DIR / filename, as_version=4))
                self.assertIn("tempfile.mkdtemp(prefix='fitinsight-notebook-", code)
                self.assertNotIn("dir=ROOT", code)
                self.assertIn("shutil.rmtree(scratch)", code)
        self.assertEqual(list(ROOT.glob("_notebook_p[1-5]_*")), [])

    def test_figure_cells_follow_the_analysis_proofs_they_visualize(self) -> None:
        placements = {
            "03_Exploratory_Data_Analysis.ipynb": (
                ("P3-A-DESCRIPTIVE", "render_figure(step_histogram(", {"Daily step counts are right-skewed"}),
                ("P3-B-COMPLETENESS", "render_figure(entry, FIGURE_DIR) for entry in [completeness_histogram", {
                    "Step-count distributions differ by completeness",
                    "Daily step averages need their coverage context",
                }),
                ("P3-D-WEEKDAY-WEEKEND", "paired_weekday_svg(weekday_table", {
                    "Weekend and weekday means vary by participant",
                    "Recorded-time composition differs by completeness",
                    "Activity measures show varied rank associations",
                }),
                ("P3-E-SLEEP-EPISODES", "render_figure(sleep_episode_histogram(", {"Recorded sleep-log sizes vary"}),
                ("P3-F-SLEEP-ACTIVITY", "render_figure(sleep_activity_scatter(", {"Recorded sleep-log rows and waking-day steps"}),
                ("P3-H-TIME-ACCOUNTING", "render_figure(time_accounting_scatter(", {"Activity and sleep rows sometimes sum near 1,440"}),
            ),
            "04_Clustering_and_PCA.ipynb": (
                ("P4-PROFILES", 'figures.extend(_write_figures(baseline, complete, [], [], {}, group="kmeans_metrics")', {
                    "K-Means inertia by K",
                    "K-Means silhouette by K",
                    "Davies–Bouldin score by K",
                    "Calinski–Harabasz score by K",
                }),
                ("P4-PROFILES", 'group="cluster_sizes"', {"Selected K-Means cluster sizes"}),
                ("P4-PROFILES", 'group="cluster_profiles"', {"Cluster feature profiles"}),
                ("P4-STABILITY", 'figures.extend(_write_figures(baseline, complete, [], sensitivity_rows, {}, group="sensitivity")', {"Cohort and eligibility sensitivity"}),
                ("P4-DBSCAN", 'figures.extend(_write_figures(baseline, complete, dbscan_rows, [], {}, group="dbscan")', {"DBSCAN parameter sensitivity"}),
                ("P4-PCA", 'figures.extend(_write_figures(baseline, complete, dbscan_rows, sensitivity_rows, pca_by_cohort, group="pca")', {
                    "PCA projection of standardized participant features",
                    "PCA explained variance by component",
                    "PCA cumulative explained variance",
                    "PCA feature loadings",
                }),
            ),
            "05_Association_and_Anomalies.ipynb": (
                ("P5-ASSOC-TABLE-PATHS", "Participant-day transaction item prevalence", {
                    "Participant-day transaction item prevalence",
                    "Association rule support and confidence",
                    "Eligible association rules across support thresholds",
                }),
                ("P5-ANOMALY-GLOBAL-IQR", "04_global_iqr_flags.svg", {"Global 1.5×IQR candidate flags by field"}),
                ("P5-ANOMALY-WITHIN-PERSON", "07_within_person_candidates.svg", {"Within-person robust candidate counts"}),
                ("P5-ANOMALY-KNN", "06_knn_distance_quantiles.svg", {"kNN score summaries by coverage cohort"}),
                ("P5-ANOMALY-OVERLAP", "05_detector_candidate_counts.svg", {"Exploratory detector candidate counts"}),
                ("P5-ANOMALY-BOUNDARY", "08_boundary_date_sensitivity.svg", {"Last-date sensitivity for candidate counts"}),
            ),
        }
        for filename, pairs in placements.items():
            notebook = nbformat.read(PHASE_DIR / filename, as_version=4)
            code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
            code = ["".join(cell.source) for cell in code_cells]
            for proof, figure, expected_titles in pairs:
                with self.subTest(notebook=filename, proof=proof, figure=figure):
                    proof_index = next(
                        index for index, source in enumerate(code) if proof in source
                    )
                    figure_index = next(
                        index for index, source in enumerate(code) if figure in source
                    )
                    self.assertEqual(
                        figure_index,
                        proof_index + 1,
                        f"{figure} should render immediately after its calculation proof.",
                    )
                    self.assertTrue(
                        expected_titles.issubset(set(svg_titles(cell_svg_payloads(code_cells[figure_index])))),
                        f"Saved figures {sorted(expected_titles)} should appear in their stage cell.",
                    )

    def test_fresh_kernels_run_isolated_without_src_or_tracked_notebook_writes(self) -> None:
        if os.environ.get("FITINSIGHT_RUN_NOTEBOOK_KERNELS") != "1":
            self.skipTest(
                "Run with FITINSIGHT_RUN_NOTEBOOK_KERNELS=1 for the full "
                "isolated fresh-kernel notebook pass."
            )

        before_hashes = tracked_notebook_hashes()
        isolated = Path(tempfile.mkdtemp(prefix="fitinsight-notebook-kernel-", dir=ROOT.parent))
        success = False
        try:
            linked_bytes = 0
            for directory in ("data", "reports", "notebooks"):
                linked_bytes += hardlink_tree(ROOT / directory, isolated / directory)
            self.assertFalse((isolated / "src").exists())

            execution_results = {}
            for filename in PHASES:
                notebook_path = PHASE_DIR / filename
                notebook = nbformat.read(notebook_path, as_version=4)
                if filename == "06_Interactive_Dashboard.ipynb":
                    notebook.cells.append(
                        nbformat.v4.new_code_cell(
                            P6_WIDGET_SMOKE, id="p6-widget-smoke-test"
                        )
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
                self.assertIn(KERNEL_PROOFS[filename], streams)
                if filename in FIGURE_EXPECTATIONS:
                    titles = svg_titles(svg_payloads(notebook))
                    self.assertEqual(set(titles), FIGURE_EXPECTATIONS[filename])
                    self.assertEqual(len(titles), len(FIGURE_EXPECTATIONS[filename]))
                if filename == "06_Interactive_Dashboard.ipynb":
                    self.assertIn("P6-WIDGET-SMOKE", streams)
                    self.assertIn("PCA_highlight=35/24_points_bounds_stable", streams)
                self.assertEqual(
                    list(isolated.glob("_notebook_p[1-5]_*")),
                    [],
                    "Notebook execution left unmanaged repository-style scratch folders.",
                )
                execution_results[filename] = {
                    "proof_lines": [
                        line for line in streams.splitlines()
                        if "FITINSIGHT_PROOF" in line
                    ],
                    "svg_figures": len(svg_payloads(notebook)),
                }

            self.assertEqual(tracked_notebook_hashes(), before_hashes)
            print(
                "FITINSIGHT_PROOF | NOTEBOOK-KERNELS | "
                f"notebooks={len(execution_results)} | hardlinked_bytes={linked_bytes:,} "
                f"| tracked_notebook_hashes_unchanged=true | results={execution_results}"
            )
            success = True
        finally:
            if success:
                shutil.rmtree(isolated)
            else:
                print(f"Notebook test workspace retained for diagnostics: {isolated}")
            self.assertEqual(
                tracked_notebook_hashes(),
                before_hashes,
                "Notebook kernel tests modified tracked notebook contents.",
            )


if __name__ == "__main__":
    unittest.main()
