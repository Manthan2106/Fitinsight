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

## P4 — Test whether recorded activity supports participant profiles

- Problem: The dataset has 35 participants with unequal and incomplete daily
  coverage; repeated days must not let better-recorded participants dominate
  the participant comparison.
- Feature choice: Aggregate to one participant row using mean steps, mean
  daily active share, mean very-active minutes, and sample SD of daily steps.
  Exclude distance because Phase 3 shows it closely tracks steps; exclude
  sedentary share because it is complementary to active share under the same
  recorded-minute denominator.
- Algorithm choice: Standardize each cohort; compare K-Means candidates
  K=2–6 using inertia, silhouette, Davies–Bouldin, Calinski–Harabasz, and
  cluster size. Evaluate DBSCAN as a parameter sensitivity and use PCA to
  summarize feature variance.
- Experiment: With 35 all-days participants, K=3 has sizes 17/16/2 and
  silhouette 0.427, slightly above K=2's 0.409. The complete-day cohort has
  24 participants and selects K=2 (18/6); its shared-participant ARI is 0.537.
  Five 20-start seed reruns reproduce all-days K=3 with ARI 1.000.
- Challenge: The K=3 two-person high-step group disappears when those two
  participants are excluded; the other 33 assignments retain ARI 1.000. The
  stronger silhouette therefore does not establish a stable real subgroup.
  DBSCAN at eps=1.0 / min_samples=3 finds 3 groups and 8 noise points, while
  many nearby settings collapse to one group or substantial noise.
- Evidence: First-two-PC variance is 85.7% for all-days and 88.9% for
  complete-days. Synthetic tests validate the custom standard-library
  clustering and Jacobi PCA calculations; historical reference counts are
  reproduced without installing packages.
- Interpretation and limitation: The grouping is an exploratory description
  of recorded participant summaries, not a health or fitness classification.
  The sample is small, coverage is uneven, DBSCAN can reject participants, and
  PCA variance does not prove cluster validity.
- Reproducibility: `python src/activity_clustering.py`; run the full test suite
  after the Phase 2 and Phase 3 generated artifacts are available.
- Outputs: Participant feature/assignment/profile tables, candidate metrics,
  DBSCAN grid, PCA scores/loadings/variance, cohort sensitivity, 12 SVGs,
  and task-specific JSON proofs under `reports/generated/activity_clustering/`
  and `reports/evidence/P4/`.
