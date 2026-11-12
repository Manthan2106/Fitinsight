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

## D-004 — Stream merged activity after proving key order

- Date: 2026-11-12
- Question: Can the three hourly and four minute-level sources be combined
  row-by-row without an in-memory join?
- Choices: Load and key-join complete tables; stream-join only after verifying
  keys and order; stop if the source order differs.
- Selected: Verify the keys and order as a streaming pass, then perform a
  row-wise streaming join with per-row key checks.
- Why: The workspace had about 355 MiB available RAM while the minute inputs
  total over 200 MB. Equal row counts alone would not prove a safe join.
- Evidence: 24,084 hourly rows and 1,445,040 minute rows checked; zero key or
  order mismatches and zero duplicate keys.
- Trade-off: A validation pass plus generation pass rereads the inputs, but
  keeps peak memory bounded and prevents row misalignment.
- Files: `src/preprocess.py`, `reports/evidence/P2/`.

## D-005 — Keep-first sleep deduplication is valid for these repeated keys

- Date: 2026-11-12
- Question: Are the 525 repeated sleep keys exact duplicates or conflicting
  measurements?
- Choices: Remove repeated keys as in the notebook; select among conflicting
  records; stop and investigate.
- Selected: Apply the existing keep-first rule only after exact row equality
  is checked for each repeated `(Id, date, logId)` key.
- Why: All 525 repeated key occurrences have identical raw row values; there
  are no conflicting duplicate groups.
- Evidence: 198,559 raw records; 198,034 unique keys; 525 identical repeats.
- Trade-off: The dedup rule is specific to this verified source; future files
  should repeat the conflict check.
- Files: `src/preprocess.py`, `docs/RAW_TO_PROCESSED_SPEC.md`.

## D-006 — Generate reproducible outputs outside committed references

- Date: 2026-11-12
- Question: Where should regenerated Phase 2 CSVs be written?
- Choices: Replace `data/processed/`; add generated tables to the raw-data
  directory; write to a separate generated-output directory.
- Selected: Write to ignored `reports/generated/preprocessed/` and compare
  against the committed references without modifying them.
- Why: The references are an acceptance baseline, while raw sources and
  notebooks must remain preserved.
- Evidence: All six local outputs matched their reference with zero row
  mismatches; raw, processed, and notebook paths are unchanged from `main`.
- Trade-off: A clean checkout must run `python src/preprocess.py` before the
  optional generated-output integration test can run.
- Files: `src/preprocess.py`, `tests/test_preprocess_integration.py`.

## D-003 — Keep distance mismatches as flags

- Date: 2026-11-12
- Question: Should distance values that disagree be corrected or excluded?
- Choices: Choose one field as authoritative; drop mismatched days; preserve
  values and report the comparisons.
- Selected: Preserve all values and report differences greater than 0.01.
- Why: No field specification establishes which value is authoritative; the
  mismatch itself is the supported finding.
- Evidence: 104/457 component-sum differences; 16/457 `TotalDistance` versus
  `TrackerDistance` differences; 29/32 component mismatches for participant
  `4020332650`.
- Trade-off: Downstream analyses need a deliberate feature choice and should
  disclose this uncertainty.
- Files: `src/data_audit.py`, `docs/DATA_QUALITY.md`.
