# Decision log

## D-001 — Stream the raw audit with the Python standard library

- Date: 2026-11-12
- Question: How to audit 11 CSVs totaling 271,592,676 bytes in a workspace
  with approximately 436 MiB initially available?
- Choices: Load tables into pandas; install dependencies; stream with `csv`.
- Selected: Stream one file at a time with `csv`, hashing in fixed-size blocks.
- Why: Bounds memory use and requires no package installation or paid service.
- Evidence: `python src/data_audit.py` scanned 7,206,142 rows and wrote the
  P1 inventory and manifest.
- Trade-off: Type inference is lexical and is not an authoritative schema.
- Files: `src/data_audit.py`, `reports/evidence/P1/`.

## D-002 — Validate source keys without dropping duplicate rows

- Date: 2026-11-12
- Question: How should row identity and duplicate observations be represented?
- Selected: Check natural composite keys per file; report duplicate counts and
  preserve every original row.
- Why: Sleep duplicates are an observed data-quality issue, not permission to
  rewrite the research source.
- Evidence: 525 repeated `(Id, date, logId)` keys in the 198,559-row sleep file;
  zero repeated keys in the other 10 source files.
- Trade-off: Composite-key choices need to remain aligned with each table's
  documented grain; key uniqueness does not establish measurement validity.
- Files: `src/data_audit.py`, `docs/DATA_QUALITY.md`.
