# FitInsight

FitInsight is an exploratory dashboard and data-mining project built from
historical Fitbit tracker CSV exports. It is not a live wearable service, a
medical classifier, or a source of health recommendations.

## Current state

- The original audit and EDA notebooks are preserved under `notebooks/`.
- The raw archive is in `data/raw/`; existing processed exports are in
  `data/processed/`.
- The Phase 1 streaming audit uses only the Python standard library.
- Current verified repository phase and next steps: `docs/AGENT_CONTEXT.md`.

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

## Existing notebooks

The original notebooks contain executed analysis results and are retained as
research artifacts:

- `notebooks/notebook_1.ipynb` — raw-data audit and quality investigation.
- `notebooks/Data_preprocessing.ipynb` — six processed exports.
- `notebooks/EDA_analysis.ipynb` — descriptive activity analysis.

Their package environment is not yet pinned on `main`; reproducible
preprocessing is a later phase. Do not treat an executed notebook output as a
substitute for rerunning the workflow.

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
