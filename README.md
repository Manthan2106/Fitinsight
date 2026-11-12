# FitInsight

FitInsight is an exploratory dashboard and data-mining project built from
historical Fitbit tracker CSV exports. It is not a live wearable service, a
medical classifier, or a source of health recommendations.

## Current state

- The original audit and EDA notebooks are preserved under `notebooks/`.
- The raw archive is in `data/raw/`; existing processed exports are in
  `data/processed/`.
- The Phase 1 streaming audit uses only the Python standard library.
- Phases 1–4 are merged into `main`; Phase 5 association and anomaly analysis
  is underway on `phase-5-association-anomalies`. See `docs/AGENT_CONTEXT.md`.
- Phase 4 produced nine analysis tables, 12 SVG figures, and machine-readable
  validation evidence; its small-sample cluster findings remain exploratory.

## Run the raw-data audit

Use Python 3.12 or newer. From the repository root:

```bash
python src/data_audit.py
python -m unittest discover -s tests -v
```

The audit streams the 11 original CSV files and writes compact inventory and
manifest files under `reports/evidence/P1/`. It reports schemas, lexical type
inference, missing values, participant counts, date coverage, duplicate
composite keys, and input hashes. It does not modify source data.

## Reproduce processed datasets

From the repository root:

```bash
python src/preprocess.py
python -m unittest discover -s tests -v
```

The preprocessing command validates hourly/minute key order before streaming
joins, generates the six CSVs under the ignored
`reports/generated/preprocessed/` directory, and compares each output to its
committed reference in `data/processed/`. It writes compact metrics and a run
manifest under `reports/evidence/P2/`. It uses only the Python standard
library; raw files and committed reference outputs are never overwritten.

## Existing notebooks

The original notebooks contain executed analysis results and are retained as
research artifacts:

- `notebooks/notebook_1.ipynb` — raw-data audit and quality investigation.
- `notebooks/Data_preprocessing.ipynb` — six processed exports.
- `notebooks/EDA_analysis.ipynb` — descriptive activity analysis.

Their original package environment is not pinned; notebook outputs remain
historical. Current reproducible preprocessing, EDA, and clustering commands
run from the processed CSVs rather than notebook state.

## Phase 4 clustering and PCA

From the repository root, run:

```bash
python src/activity_clustering.py
python -m unittest discover -s tests -v
```

This standard-library-only workflow validates the participant cohort, computes
K-Means, DBSCAN, PCA, sensitivity results, evidence JSON, CSV tables, and SVG
figures under `reports/`. The historical implementation on
`phase-4-activity-clustering` is retained as a separate reference branch. See
`docs/CLUSTERING_FINDINGS.md` for the results and caveats and
`docs/handoffs/phase-04.md` for the review handoff.

## Phase 5 association rules and anomaly screening

From the repository root, run:

```bash
python src/preprocess.py
python src/eda_analysis.py
python src/phase5_analysis.py
python src/phase5_validation.py
```

Phase 5 uses Python's standard library only. It builds one categorical
transaction per participant-day, mines bounded Apriori rules, and compares
global IQR, within-participant robust, and coverage-stratified k-nearest-
neighbor screens. Outputs, proof JSON, and eight SVG figures are written under
`reports/generated/associations/`, `reports/generated/anomalies/`, and
`reports/evidence/P5/`. Existing candidate rows are retained; these screens do
not confirm errors or make health claims. See
`docs/ASSOCIATION_FINDINGS.md`, `docs/ANOMALY_FINDINGS.md`, and
`docs/handoffs/phase-05.md`.

## Data and scientific limits

See `docs/DATA_DICTIONARY.md` and `docs/DATA_QUALITY.md`. The observations are
historical (2016), coverage differs by participant and data source, and
unusual or zero-step records are preserved for investigation rather than
automatically rejected. Sleep episode alignment and official field units
require explicit validation before interpretation.

## Cost and privacy

The intended workflow is local and zero-cost: no external AI API, paid
database, hosted compute, or paid deployment is required. Keep credentials in
environment secrets, never in tracked files. Do not add private participant
data beyond the repository's existing research dataset.
