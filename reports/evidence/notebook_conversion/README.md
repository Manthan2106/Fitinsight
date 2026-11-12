# Notebook conversion and correction verification

## Initial PR #6 conversion snapshot (historical)

The six notebooks in `notebooks/phases/` are the Phase 1–5 reproducibility
workflow and the initial interactive Phase 6 artifact. They were built on the
verified `main` baseline `a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`.
Each notebook was executed in a fresh Python 3.13.11 kernel. Phases 1–5
contain independent, inspectable implementation cells; they do not import or
launch the corresponding analysis scripts. Generated comparison outputs use
scratch directories and do not overwrite committed references.

The three original notebooks, raw and processed datasets, analytical scripts,
and historical Phase 4 branch were preserved. The Phase 6 web dashboard is
paused until this notebook conversion is reviewed.

## Results

| Notebook | Fresh-kernel code cells | Verified result |
| --- | ---: | --- |
| `01_Data_Audit.ipynb` | 9 | All 11 raw CSVs; 7,206,142 rows; per-file row counts and SHA-256 hashes match the baseline. |
| `02_Data_Preprocessing.ipynb` | 37 | All six processed exports regenerate with exact schema/value parity. Hourly and minute source alignment checks cover 24,084 and 1,445,040 rows; 525 identical sleep duplicate occurrences are removed as in the reference. |
| `03_Exploratory_Data_Analysis.ipynb` | 129 | 13 analysis CSVs and nine SVG figures match the committed Phase 3 evidence exactly; 161 waking-date matches; recorded time accounting results are shown in computation cells. |
| `04_Clustering_and_PCA.ipynb` | 140 | Nine analysis CSVs and 12 SVG figures match Phase 4 outputs exactly; baseline cohorts contain 35 all-days and 24 complete-day participants. |
| `05_Association_and_Anomalies.ipynb` | 135 | Eight association CSVs and 13 anomaly CSVs match exactly. Three representative SVGs are generated directly from this notebook run's computed results. |
| `06_Interactive_Dashboard.ipynb` | 7 | Six interactive panels render from stored evidence. A second fresh-kernel smoke test changed activity, cluster, association, candidate, and sleep/time controls; the corrected time selector exposes 23 dates, and the activity chart is generated from filtered rows. No model refitting occurs. |

The full repository test suite passed **89 tests** with no failures, errors,
or skips. `git diff --check` passed. Static notebook checks found valid Python
syntax, stable cell IDs, no cell error outputs, and no `%run`, `subprocess`, or
shell-launch calls.

## Reproducibility notes and limitations

- Phase 5 notebook chart coverage is intentionally not a byte-for-byte
  reproduction of all eight historical Phase 5 SVGs: the notebook creates
  three representative charts from its computed tables. All 21 Phase 5
  analytical CSV outputs represented by the eight association and 13 anomaly
  tables have exact parity.
- Notebook installation adds only the pinned free Jupyter runtime and
  `ipywidgets` packages listed in `notebooks/requirements.txt`. Phase 1–5
  analysis implementations use the Python standard library. No paid API,
  hosted compute, or deployment is required.
- Interactive controls require a Jupyter frontend with widget support.
  Notebook execution and filtering do not validate device wear, measurement
  semantics, clinical meaning, or population generalizability.
- Output parity verifies reproduction of the committed project results; it
  does not establish that historical sensor values are correct.

Machine-readable details for this initial snapshot are in `run_manifest.json`.
[PR #6](https://github.com/Manthan2106/Fitinsight/pull/6) was open when this
record was written and was later merged into `main` at
`b43f0530bab8944b331544cef7dd100b7f5ee87c`. Its initial chart and panel counts
are retained here as historical evidence; the final corrections are recorded
below.

## Final notebook corrections

The correction branch `phase-notebook-final-corrections` starts at the verified
`main` commit `b43f0530bab8944b331544cef7dd100b7f5ee87c`. The separate
historical Phase 4 branch remains at `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
This work changes the independent phase notebooks, tests, and documentation;
the analysis scripts, raw datasets, processed references, generated Phase 1–5
results, archived notebook contents, and historical Phase 4 branch are
preserved.

| Notebook | Final verified output |
| --- | --- |
| `01_Data_Audit.ipynb` | 11 raw CSVs, 7,206,142 rows; all file hashes and row counts match. |
| `02_Data_Preprocessing.ipynb` | Six generated outputs match the committed references. Source alignment and output uniqueness use temporary disk-backed SQLite digests to keep the free local kernel's memory bounded. |
| `03_Exploratory_Data_Analysis.ipynb` | 13 analysis CSV tables and all nine Phase 3 SVG figures; reviewed time-accounting conclusions are shown in notebook cells. |
| `04_Clustering_and_PCA.ipynb` | Nine analysis CSV tables and all 12 Phase 4 SVG figures; the two-person cluster limitation remains explicit. |
| `05_Association_and_Anomalies.ipynb` | Eight association CSVs, 13 anomaly CSVs, and all eight SVG figures generated from computed results. |
| `06_Interactive_Dashboard.ipynb` | Eight panels over stored results; fresh-kernel interaction checks cover the 217/457 anomaly union, 35/24 cohort assignments, PCA/DBSCAN controls, association filters, and 23 dates. No model is refit. |

## Final checks

- `python -m unittest discover -s tests -v`: 92 tests run, 91 passed, one
  intentionally skipped. The skipped check is the separate, expensive
  fresh-kernel notebook run, enabled by `FITINSIGHT_RUN_NOTEBOOK_KERNELS=1`.
- A complete earlier isolated run passed all three notebook-workflow tests and
  executed all six notebooks without `src/`. After the final resource/UI
  refinements, Phase 2 and Phase 6 were rerun separately in isolated fresh
  kernels; both passed, and their latest proof outputs were saved. Static
  self-containment/syntax checks and stored-output checks pass for all six.
- A redundant combined rerun after those refinements was interrupted when the
  workspace restarted during Phase 1's full raw-file scan. It is not counted as
  a completed run; the separate final Phase 2 and Phase 6 reruns and the earlier
  complete six-notebook run are the supporting execution evidence.
- `git diff --check` and staged diff checks pass. The archived originals match
  the Git-baseline SHA-256 hashes byte-for-byte. Only the unnecessary
  `src/.gitkeep` is removed from protected script/data paths; `app/.gitkeep`
  remains.
- All work used the existing Python/Jupyter runtime and local standard-library
  code. No packages were installed for the correction, and no paid API,
  hosted compute, deployment, or Phase 7 work was used.

The current branch is prepared for a review-only pull request against `main`;
it must not be merged automatically. The PR number, remote head, and open/
unmerged verification are recorded in the branch's final update.
