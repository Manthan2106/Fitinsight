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

## P3 — Describe activity while respecting coverage and sleep ambiguity

- Method: Recomputed pooled and equal-participant summaries, complete-day
  sensitivity, Pearson/Spearman associations, paired weekday/weekend
  comparisons, sleep-log episodes, waking-date matches, and review candidates
  from the Phase 2 processed files.
- Revalidated results: Daily steps average 6,546.56 (median 5,986; 457 days,
  35 participants). Incomplete days average more steps than complete days
  (7,289.92 versus 5,831.92), while participant-level direction is mixed:
  15 complete-day means are higher, 12 are lower, one is equal, and seven are
  unavailable.
- Paired result: Weekday/weekend pooled step means are similar (6,528.61 and
  6,584.42); 17 participants have higher weekend means, 17 higher weekday
  means, and one is equal. The average participant-level difference is 9.86
  steps; this is descriptive, not a significance test.
- Sleep result: 359 logs pass the explicit overnight eligibility screen, with
  161 unique waking-date matches across 18 participants. Seventeen activity
  dates have ambiguous multiple sessions. The join preserves all 457 daily
  rows and leaves unmatched sleep blank; all 161 matched activity days are
  incomplete, so no complete-day sleep comparison is available.
- New analytical challenge: The four activity-minute fields plus recorded
  sleep-row counts equal 1,440 on 45 of 161 matched dates and fall within
  30 minutes on 91. The relationship varies by participant. April 12, 2016
  has seven matched sums from 607 to 833 minutes, so excluding it is shown only
  as a sensitivity check.
- Interpretation: The arithmetic is compatible with complementary accounting
  for many records, but does not prove complete 24-hour coverage: sleep rows
  are not validated minutes asleep, interval overlap is unknown, and missing
  activity minutes do not prove device non-wear. The original Phase 2
  completeness definition remains unchanged.
- Downstream impact: Keep coverage flags and missingness explicit in clustering
  and participant comparisons; do not turn missing sleep into zero or treat
  combined minutes as a validated coverage feature.
- Outputs: Nine SVG figures, reproducible CSV analysis tables, compact
  evidence JSON, and printed computational proof for each analysis stage.
- Reproducibility: Synthetic boundary, exact-match, positive/negative
  difference, missing-sleep, and ambiguous-session cases pass. Tests compare
  chart point data and labels to the computed time-accounting table.
- Caveat: The categories `1/2/3` are not mapped to sleep stages; recorded
  sleep-row count is not validated time asleep. The historical sample is not
  established as representative, measurement units are not independently
  verified, and no causal or health claims are made.
- Reproducibility: `python src/eda_analysis.py`; only Python's standard library
  and local files are used.
- Evidence: P3-EXPLORATORY-ANALYSIS.
