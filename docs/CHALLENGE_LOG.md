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

## C-003 — Prove multi-file row alignment before merging

- Phase/task: P2 hourly and minute activity integration
- Observable constraint: The notebook merges several full participant-hour
  and participant-minute tables; equal lengths alone cannot ensure matching
  keys or order, and available RAM is limited.
- Root cause: A misordered row-wise merge would assign measurements to the
  wrong participant-time without necessarily changing row count.
- Solution: Stream key tuples from each source in lockstep, compare every key
  and its order, and count duplicates before permitting a row-wise merge.
- Verification: All 24,084 hourly keys and 1,445,040 minute keys matched in
  order across their source files; both reference keys were unique. The
  generated hourly and minute outputs also match their processed references.
  Negative tests reject missing keys, duplicate join keys, unequal row counts,
  and changed key order.
- Remaining limitation: The verification covers the committed files; future
  input revisions must rerun the alignment check.
- Presentation takeaway: A cheap streaming key proof made a low-memory join
  defensible rather than relying on matching row counts.

## C-004 — Sleep logs do not form a complete matched panel

- Phase/task: P3 sleep episode reconstruction and waking-date alignment
- Observable symptom: Only 161 daily activity rows have a unique eligible
  overnight log; 17 activity dates have multiple candidate sessions, and none
  of the matched activity days meet the 1,440-minute complete-day rule.
- Root cause: The sleep file has 556 participant-log groups, varying session
  times, and repeated candidate logs on some waking dates; activity coverage
  is incomplete across the same dates.
- Solution: Keep sleep codes neutral; screen overnight timing and intervals;
  exclude ambiguous dates; match the episode end date; preserve unmatched sleep
  as missing and maintain one row per activity participant-day.
- Verification: 359 individually eligible episodes, 161 matched days across
  18 participants, 17 ambiguous activity dates, 198 eligible episodes without
  an activity row, and 457 unique output activity rows.
- Remaining limitation: All 161 matched days are incomplete, so the
  complete-day sleep/activity sensitivity has no observations. Recorded log
  rows are not validated actual sleep duration.
- Presentation takeaway: The join is cardinality-safe, but its strict coverage
  leaves no matched complete-day sample for a sleep sensitivity comparison.

## C-005 — Build interpretable figures without a plotting dependency

- Phase/task: P3 reproducible visualization
- Observable constraint: The available Python environment has no Matplotlib,
  Seaborn, NumPy, pandas, or SciPy.
- Root cause: A package-based chart pipeline would require installation and
  would no longer use only already-verified local resources.
- Solution: Generate eight accessible, deterministic SVG figures using Python
  standard-library string and XML-compatible output.
- Verification: The analysis emits the same eight named figures and sample
  counts in `reports/evidence/P3/figures_index.json`; tests parse each SVG.
- Remaining limitation: Charts are static and need maintenance alongside the
  analysis code.
- Presentation takeaway: The EDA figures can be regenerated locally without
  paid tools or external services.
