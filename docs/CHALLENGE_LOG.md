# Challenge log

## C-001 — Audit large raw CSVs under limited memory

- Phase/task: P1 raw-data inventory
- Observable constraint: Raw files total 271,592,676 bytes; only about 436 MiB
  memory was available at the initial environment check.
- Root cause: Loading multiple minute-level or heart-rate tables together
  would needlessly increase peak memory.
- Solution: Stream each source CSV using Python's standard-library `csv`
  reader and fixed-size blocks for SHA-256.
- Verification: `python src/data_audit.py` scanned 7,206,142 rows and passed
  header, row-width, key-completeness, and date-parsing checks.
- Remaining limitation: Audit output infers lexical types and does not confirm
  units or the validity of device measurements.
- Presentation takeaway: The raw-data audit was designed around the actual
  memory constraint rather than loading the minute-level files wholesale.

## C-002 — Daily distance fields do not reconcile consistently

- Phase/task: P1 daily-data quality review
- Observable symptom: The component-distance sum differs from `TotalDistance`
  by more than 0.01 on 104 of 457 participant-days. For participant
  `4020332650`, this occurs on 29 of 32 days; the maximum absolute difference
  is 7.41 on 2016-03-20.
- Root cause: Unknown; source units and field-generation rules are not
  documented in the repository.
- Attempted fix: Compared `TotalDistance` with both `TrackerDistance` and the
  sum of the four activity-distance fields. The two comparisons do not agree
  on which rows differ.
- Implemented solution: Preserve the source values and record separate
  discrepancy counts; do not select a “correct” field or exclude observations.
- Verification: `python src/data_audit.py`; actual counts are saved in
  `reports/evidence/P1/run_manifest.json`.
- Remaining limitation: These are descriptive mismatch flags, not proof of
  which measurement is wrong.
- Presentation takeaway: Field-level consistency checks exposed a measurable
  data-quality question that downstream analysis must not silently normalize.
