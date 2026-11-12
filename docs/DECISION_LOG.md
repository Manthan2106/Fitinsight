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

## D-007 — Analyze Phase 3 with standard-library tools

- Date: 2026-11-12
- Question: How to reproduce expanded EDA and figures without installing
  unavailable plotting or statistics packages?
- Selected: Use standard-library calculations, a temporary SQLite index for
  sleep records, and deterministic local SVG generation.
- Why: Keeps the work reproducible on the verified zero-cost local toolchain
  without downloads, paid services, or external compute.
- Evidence: `python src/eda_analysis.py` validates the 457 daily rows and
  198,034 processed sleep rows, writes analysis artifacts, and prints proof
  blocks for each analysis stage.
- Trade-off: Custom SVG charts require maintenance in this repository.
- Files: `src/eda_analysis.py`, `src/sleep_analysis.py`, `src/eda_figures.py`.

## D-008 — Keep sleep value categories neutral

- Date: 2026-11-12
- Question: Should stored values `1`, `2`, and `3` be interpreted as sleep
  stages or physiological states?
- Selected: Preserve the stored codes and report their counts only.
- Why: No trustworthy category mapping is documented in the repository.
- Evidence: 198,034 processed sleep rows have category counts of 183,038,
  12,983, and 2,013 for codes `1`, `2`, and `3`.
- Trade-off: The analysis does not label time asleep, sleep efficiency, or
  sleep stages.
- Files: `src/sleep_analysis.py`, `docs/EDA_FINDINGS.md`.

## D-009 — Match only unique, quality-screened waking dates

- Date: 2026-11-12
- Question: How should participant-log sleep episodes align with daily activity?
- Selected: Use episode end date as a waking-date candidate; require overnight
  timing, at most 12 elapsed hours, exact minute intervals, no overlap, and one
  candidate per participant-date.
- Why: This avoids assigning ambiguous logs or multiplying participant-day
  activity rows; unmatched sleep remains missing rather than zero.
- Evidence: 359 eligible logs yield 161 unique matches across 18 participants;
  17 activity dates have multiple candidate sessions, and all matched activity
  days are incomplete by the 1,440-minute rule.
- Trade-off: Strict eligibility excludes ambiguous dates; no complete-day
  sleep/activity sensitivity can be computed in this sample.
- Files: `src/sleep_analysis.py`, `src/eda_analysis.py`,
  `reports/evidence/P3/sleep_alignment_metrics.json`.

## D-010 — Keep anomaly screens as review candidates

- Date: 2026-11-12
- Question: Should IQR fences and observed data-quality flags remove rows?
- Selected: Export candidate rows with explicit reasons and retain every source
  observation.
- Why: A fence or device-field discrepancy does not establish that a record is
  invalid.
- Evidence: 140 daily rows and 111 sleep episodes are marked for possible
  review; source inputs remain unchanged.
- Trade-off: Candidate counts are not counts of confirmed errors or clinical
  anomalies.
- Files: `src/eda_analysis.py`,
  `reports/generated/eda/tables/anomaly_candidates.csv`.

## D-011 — Treat activity-plus-sleep totals as an accounting diagnostic

- Date: 2026-11-12
- Question: Does adding the four recorded activity-minute fields to matched
  sleep-log row counts establish a complete 24-hour day?
- Choices: Redefine Phase 2 completeness; infer device non-wear from a short
  activity total; or report the arithmetic as a sensitivity diagnostic while
  preserving source fields and the existing flag.
- Selected: Keep the Phase 2 completeness rule unchanged and compare the
  combined count with 1,440 minutes only as descriptive evidence.
- Why: The arithmetic frequently approaches 1,440, but the repository does not
  establish whether the fields describe disjoint intervals or actual sleep
  duration.
- Evidence: 45/161 exact sums; 91/161 within 30 minutes; all 161 retain the
  original incomplete flag. April 12 has seven matched sums from 607 to 833
  minutes. Boundary-date results are reported as sensitivity checks.
- Trade-off: This identifies a meaningful data-definition question without
  treating arithmetic agreement as validated 24-hour coverage or treating
  missing activity as device non-wear.
- Files: `src/eda_analysis.py`, `src/eda_figures.py`,
  `reports/evidence/P3/time_accounting_metrics.json`,
  `docs/EDA_FINDINGS.md`.
