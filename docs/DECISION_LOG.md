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

## D-012 — Cluster participant summaries rather than participant-days

- Date: 2026-11-12
- Question: Which observation grain answers whether the dataset contains
  differing participant-level recorded-activity profiles?
- Choices: Treat each of 457 daily rows as an independent clustering sample;
  or aggregate repeated days to one feature row per participant.
- Selected: Cluster one row per participant after requiring at least three
  positive-duration activity days.
- Why: Participant-day clustering would let participants with more recorded
  days dominate the distance geometry and would not answer the participant
  profile question.
- Evidence: 35 eligible participants; the complete-day-only cohort has 24.
  `reports/evidence/P4/cohort_validation.json`.
- Trade-off: Aggregation hides within-person daily variation; the sample
  standard deviation is retained as one feature and coverage is reported.
- Files: `src/activity_clustering.py`, `reports/generated/activity_clustering/`.

## D-013 — Keep four prespecified activity features and standardize by cohort

- Date: 2026-11-12
- Question: Which recorded measures should define Euclidean distance?
- Choices: Include steps, distance, all activity-minute fields, and
  participant-level summaries; or use the four historically specified features.
- Selected: Mean steps, the equal-weight mean of daily active-minute fractions,
  mean very-active minutes, and sample SD of daily steps; z-score each cohort
  independently using population SD.
- Why: Phase 3 found steps and distance highly correlated; sedentary share
  duplicates the active-share denominator. The 4-feature correlation matrix is
  reported before fitting. The maximum off-diagonal absolute correlation is
  0.753.
- Evidence: Feature formulas, ranges, IQR flags, correlations, and scaler
  parameters are in `reports/evidence/P4/feature_validation.json`.
- Trade-off: Correlated features still contribute related information; a
  separate scaler means cohort scores are not on a shared coordinate system.
- Files: `src/activity_clustering.py`,
  `reports/generated/activity_clustering/tables/participant_features.csv`.

## D-014 — Select K with a singleton guard and report its sensitivity

- Date: 2026-11-12
- Question: How many K-Means groups are supportable for 35 participants?
- Choices: Choose K from one metric alone; or compare K=2–6, multiple quality
  measures, minimum cluster size, and cohort sensitivities.
- Selected: Use seed 42 and 20 starts; select the highest silhouette among
  candidates with at least two members per cluster. Treat this as exploratory.
- Why: All-days K=3 has the highest eligible silhouette (0.427 versus 0.409
  for K=2), but its highest-step cluster contains only two participants.
- Evidence: `reports/evidence/P4/kmeans_evaluation.json` and
  `reports/evidence/P4/stability_metrics.json`; 5 seed reruns select K=3 with
  ARI 1.000. Excluding the two highest-step participants changes the selected
  solution to K=2, with ARI 1.000 on the 33 shared participants. Complete-day
  K=2 has ARI 0.537 on 24 shared participants.
- Trade-off: A reproducible scoring rule cannot establish true behavioral
  categories; the two-person group is especially sensitive to cohort choice.
- Files: `src/clustering_math.py`,
  `reports/generated/activity_clustering/tables/kmeans_scores.csv`.

## D-015 — Use validated standard-library DBSCAN and PCA for Phase 4

- Date: 2026-11-12
- Question: Can the historical DBSCAN and PCA analyses be reproduced without
  assuming a package install is free?
- Choices: Install the historical requirements; use a minimal verified-free
  scientific stack; or implement bounded methods and validate them locally.
- Selected: Use deterministic Euclidean DBSCAN, a symmetric Jacobi PCA
  eigensolver, and standard-library SVG generation; install no packages.
- Why: Scientific packages were absent and zero-cost installation was not
  verified. The cohort has only 35 rows, and independent synthetic checks are
  practical.
- Evidence: DBSCAN at `eps=1.0`, `min_samples=3` returns 3 clusters / 8 noise
  points; first-two-PC variance is 85.7% all-days and 88.9% complete-days.
  Synthetic math tests, eigen residuals, orthogonality, and historical
  reference results are recorded under `reports/evidence/P4/`.
- Trade-off: The local K-Means initialization and numerical conventions are
  not claimed to be bit-for-bit scikit-learn behavior; this difference is
  documented and compared with historical reference outcomes.
- Files: `src/clustering_math.py`, `src/activity_clustering.py`,
  `tests/test_activity_clustering.py`.

## D-016 — Keep Phase 4 chart scales and variance stories separate

- Date: 2026-11-12
- Question: How can the model comparisons and PCA outputs remain readable
  without suggesting that unrelated metrics share a scale?
- Choices: Combine multiple diagnostics in a compact multi-panel graphic; or
  use one chart per K-Means metric and separate explained from cumulative PCA
  variance.
- Selected: Generate 12 deterministic SVG figures, with separate zero-based
  columns for inertia, silhouette, Davies–Bouldin, and Calinski–Harabasz;
  separate PCA variance charts; and labeled heatmaps for signed profiles and
  loadings.
- Why: The measures have different ranges and directions; combining them can
  obscure the meaning of their axes. Each plot is also checked for parseable
  SVG markup, accessible title/description, sample context, limitations, and
  absence of participant IDs.
- Evidence: `reports/evidence/P4/figures_index.json`,
  `reports/evidence/P4/run_manifest.json`, and the 59-test full regression run.
- Trade-off: More separate figures are produced, but each has a clearer scale
  and direct interpretation.
- Files: `src/activity_clustering.py`,
  `reports/generated/activity_clustering/figures/`.
