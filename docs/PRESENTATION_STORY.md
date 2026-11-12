# Presentation story

## P1 — Establish what the tracker archive can support

- Problem: The source archive has daily, hourly, minute, sleep, heart-rate,
  and weight files with different observation grains and participant coverage.
- Method: A standard-library streaming inventory counted rows, schema,
  missing values, dates, participants, composite-key repeats, and file hashes.
- Observed result: The 11 files contain 7,206,142 rows. Daily activity covers
  35 participants; sleep covers 23 and has 525 repeated keys; weight has
  31 missing `Fat` entries among 33 rows.
- Data challenge found: For participant `4020332650`, the activity-distance
  component sum differs from `TotalDistance` on 29 of 32 days (maximum
  absolute difference 7.41); the total and tracker distance fields agree.
- Why this matters: Later merges and methods must state their grain and handle
  coverage differences rather than treating all data as one complete panel.
- Caveat: The data are historical, field units are not independently verified,
  and these counts do not establish population representativeness.
- Evidence: P1-DATA-AUDIT.

## P2 — Rebuild the six tables without changing the source archive

- Method: Recreated daily, sleep, weight, hourly activity, minute activity, and
  heart-rate exports with sequential Python standard-library processing.
- Join check: Proved exact key order and uniqueness across 24,084 hourly rows
  and 1,445,040 minute rows before row-wise merging.
- Duplicate check: Confirmed all 525 repeated sleep keys have identical values;
  removed those repeats to reproduce the existing 198,034-row reference.
- Result: All six generated outputs matched their committed references with
  zero row mismatches. The original notebooks, raw files, and processed
  references were not modified.
- Reproducibility: 22 automated tests passed, including full generated-output
  comparisons against all six references. No packages or paid services were
  used.
- Caveat: These validations reproduce the repository's prior transformation
  behavior; they do not independently establish device units or measurement
  validity.
- Evidence: P2-REPRODUCIBLE-PREPROCESSING.
