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
  zero row mismatches. The original notebook contents, raw files, and processed
  references were preserved; the three historical notebooks now live in
  `notebooks/archive/`.
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

## P5 — Mine daily co-occurrences and investigate unusual records

- Transaction design: One transaction per participant-day, with one item from
  each of six non-overlapping families: step bins, active-minute share,
  very-active minutes, calories, weekday/weekend, and Phase 2 completeness.
  The full-cohort calorie cutpoints are Q1=1,776 and Q3=2,667. The 457
  transactions preserve participant/date mapping and all 61 zero-step days.
- Association method: Standard-library Apriori uses a maximum itemset size of
  three, 5% support (23/457 days), 60% confidence, lift 1.10, and at least five
  distinct participants. Same-family categories and direct active-share
  numerator/denominator combinations are excluded.
- Association result: 215 itemsets generate 860 directed rules; 89 meet every
  baseline threshold. `steps:zero -> active_share:lower` has 13.1% support,
  98.4% pooled confidence, and lift 3.33; its participant-balanced confidence
  is 98.8% across 14 participants with antecedent records. Another eligible
  rule's pooled confidence is 86.0% and its equal-participant value is 57.1%,
  demonstrating why repeated days should not be read as equal-person evidence.
- Sensitivity: Support, confidence, lift, and distinct-participant thresholds
  are each varied separately. The complete-day subset has 233 days across
  28 participants and yields 108 eligible rules at the same baseline settings.
- Anomaly methods: Preserve 140 Phase 3 participant-day candidates and 111
  separate sleep-episode candidates; add global 1.5×IQR, within-person robust
  scores, and pooled/complete/incomplete kNN rankings. The screens flag
  overlapping sets, so their counts are not additive.
- Quality flags: The strict Phase 1 distance screen flags 104 days; the
  committed Phase 2 flag marks 65, all within the strict set. The 39
  strict-only cases remain distinct rather than being relabeled.
- Result and limits: Ten daily screening sets have a union of 217 unique
  review candidates. Seven selected records are retained for focused review;
  no cause is inferred and no row is removed. Excluding April 12 is a
  sensitivity only; the primary analysis retains all 457 days.
- Reproducibility: The standard-library pipeline emits 21 CSV tables, eight
  SVGs, machine-readable metrics and input/source hashes. The complete
  repository suite passes 89 tests with no failures, errors, or skips.
- Caveat: Association and anomaly screens are descriptive candidates in a
  small historical tracker sample; they are not causal findings, predictive
  validation, device-wear verification, diagnoses, or health advice.
- Evidence: P5-ASSOCIATION-ANOMALIES.

## P6 — Explore the validated evidence without refitting

- Deliverable: An eight-tab Jupyter evidence browser for overview, activity,
  cohort-specific cluster assignments, stored PCA coordinates, DBSCAN
  sensitivity, association rules, anomaly candidates, and sleep/time records.
- Interactive behavior: Activity filters participant and recorded-day
  completeness; cluster choices update when the cohort changes; PCA highlights
  a participant without refitting; DBSCAN controls select saved grid results;
  association filters include support, confidence, lift, eligibility, and
  antecedent/consequent text; anomaly filters distinguish the 217 flagged rows
  from all 457 records; sleep/time exposes 23 activity dates.
- Interpretation: The dashboard reads stored CSV/JSON results and never
  refits models. The all-days K-Means assignments are 35 participants across
  three clusters; complete-day assignments are 24 participants across two
  clusters, excluding blank assignments. Cluster IDs are arbitrary and
  cohort-specific.
- Reproducibility: All six phase notebooks run from fresh kernels without
  importing or launching `src/`; Phase 1–5 evidence is compared with committed
  results. The Phase 3, 4, and 5 notebooks display all 9, 12, and 8 generated
  SVGs from the current notebook computation. Widget observers are tested
  against known row counts.
- Limits: Widgets need a Jupyter frontend. Stored associations, clusters,
  PCA, and anomaly flags remain descriptive; they are not causal, clinical, or
  population-generalizable results. Phase 7 has not started.
- Zero-cost policy: Local files, standard-library analyses, pinned free
  notebook dependencies, and local tests only; no paid APIs, hosted compute,
  or deployment.
