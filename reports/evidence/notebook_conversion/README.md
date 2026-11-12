# Notebook conversion verification

## Scope and baseline

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

Machine-readable details are in `run_manifest.json`. The conversion remains a
review branch and is not merged.
