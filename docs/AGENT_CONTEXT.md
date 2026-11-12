# FitInsight agent context

Updated: 2026-11-13

## Goal and constraints

Build an evidence-backed academic dashboard for historical Fitbit activity
data. Preserve raw CSVs and notebooks. Keep analyses reproducible, describe
the observation grain, retain zero-step records, avoid causal/clinical claims,
and use only verified outputs. Work in Free mode with zero-cost local tools;
no paid model, API, add-on, deployment, or compute.

## Current verified repository state (2026-11-13)

- GitHub `main` is at `b43f0530bab8944b331544cef7dd100b7f5ee87c`; PR #6 is
  merged.
- The current correction branch, `phase-notebook-final-corrections`, was
  created directly from that verified `main` commit.
- The historical Phase 4 branch remains
  `phase-4-activity-clustering` at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`; it is not the branch being
  changed.
- Raw datasets, processed references, analytical source files, generated
  results, and original notebook contents are preserved. The three original
  notebooks are now located in `notebooks/archive/`.
- The notebooks under `notebooks/phases/` are the independent reproducible
  workflow. The optional web app is still paused; `app/.gitkeep` remains as its
  placeholder, while `src/.gitkeep` was unnecessary and removed.

## Prior verified repository checkpoints

- Remote: `https://github.com/Manthan2106/Fitinsight.git`
- `main`: `8172c55865d7b77d3bf193f541220d4e741ce91d`
- `phase-4-validated-clustering` was created from the previous verified main
  commit `77abf8354db99cb48e84ff931e335e2ec2f4c73a`; PR #4 is now merged.
- `phase-5-association-anomalies` starts from the latest verified `main`
  commit `8172c55865d7b77d3bf193f541220d4e741ce91d`.
- The historical `phase-4-activity-clustering` remains unchanged at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`; it has one branch-only code
  commit and main has 17 commits not on that branch.
- PR #1 merged at `a6170a2`; verified that `9357d85` is in `main` history.
- PR #2 merged at `2e233a1`; its Phase 2 head was `ede8fa3`.
- PR #3 merged at `77abf8354db99cb48e84ff931e335e2ec2f4c73a`; Phase 3 head
  `6f1777d6bcacb8e4a380546c91ec2cd57f31fbbe` is its second parent.
- `main` has 11 raw CSVs, six processed CSVs, three executed notebooks, a
  README, seven audit tests, and Phase 1 evidence under `reports/evidence/P1/`.
- Raw audit: 11 files, 7,206,142 rows, 271,592,676 bytes. Daily activity has
  457 rows / 35 participants; sleep has 198,559 rows / 23 participants and
  525 duplicate `(Id, date, logId)` keys; weight has 33 rows / 11 participants
  and 31 missing `Fat` values. Daily distance comparisons found 104 rows where
  the component sum differs from `TotalDistance` by >0.01; participant
  `4020332650` has 29/32 such rows and a 7.41 maximum difference. See
  `reports/evidence/P1/`.
- The three notebooks parse successfully, have executed code cells, and store
  no error outputs. Existing outputs remain historical until rerun.

## Current phase

P1–P5 are DONE. PR #1 was merged into `main` at
`a6170a2caf64d66b1a622bd50c0b1a69805d34b0`; commit `9357d85` is in its
history. PR #2 was merged into `main` at
`2e233a1de22a7f808bdea3939b75d80e0848a483`; Phase 2 head
`ede8fa3e4e94453e8cf5a519653eac4b29b706da` is in its history. P3 is DONE:
[PR #3](https://github.com/Manthan2106/Fitinsight/pull/3) merged at
`77abf8354db99cb48e84ff931e335e2ec2f4c73a`. PR #4 merged into `main` at
`8172c55865d7b77d3bf193f541220d4e741ce91d`; its reviewed head
`440f93b9a12d019a6db26005e269bc7161641cad` is in main's history. The separate
historical `phase-4-activity-clustering` branch remains at
`cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`. PR #5 was merged at
`a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`; P5 is complete.

## Initial notebook conversion snapshot (before final corrections)

- The `phase-notebook-conversion` branch was created from verified `main`
  `a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`.
- At this snapshot, [PR #6](https://github.com/Manthan2106/Fitinsight/pull/6)
  was open against `main`; it was later merged at the current baseline
  `b43f0530bab8944b331544cef7dd100b7f5ee87c`.
- It adds six notebooks under `notebooks/phases/`: independent Phase 1–5
  reproductions and the interactive Phase 6 notebook. The three original
  notebooks' contents remain preserved unchanged under `notebooks/archive/`.
- Phase 1 validates all 11 raw-file hashes and row counts (7,206,142 rows);
  Phase 2 regenerates and compares all six processed references; Phase 3
  matches 13 analysis CSVs and nine SVG figures; Phase 4 matches nine CSVs
  and 12 SVG figures; Phase 5 matches eight association and 13 anomaly CSVs.
  Phase 5's notebook also generates three representative SVGs from computed
  notebook results; it did not reproduce all eight historical Phase 5
  figures. The current correction generates and displays all eight.
- Phase 6 initially provided six interactive panels over stored evidence. The
  current correction expands this to eight. A fresh
  kernel exposed 23 date options, and widget smoke checks exercised activity,
  cluster, rule, candidate, and sleep/time observers. No model is refit by a
  filter.
- All notebook kernels completed without cell errors. Full repository test
  and diff checks are recorded in
  `reports/evidence/notebook_conversion/README.md`.
- Phase 6's separate web dashboard remains paused pending notebook review.
  The historical Phase 4 branch and the local Phase 6 planning WIP remain
  unchanged.

## Final notebook correction snapshot (current)

- The correction branch `phase-notebook-final-corrections` starts at verified
  `main` commit `b43f0530bab8944b331544cef7dd100b7f5ee87c`; the separate
  historical Phase 4 branch remains at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
- The Phase 1–5 notebooks run independently of `src/`. Phase 3 has 13 analysis
  CSV tables and nine inline SVGs; Phase 4 has nine CSV tables and 12 inline
  SVGs; Phase 5 has eight association CSVs, 13 anomaly CSVs, and eight inline
  SVGs generated from its computed results.
- Phase 3's reviewed time-accounting remains descriptive: 45/161 matched days
  sum to 1,440 minutes, 91/161 are within 30 minutes, and the mean gap is
  −58.48 minutes. It does not change the Phase 2 completeness flag or establish
  true 24-hour coverage.
- Phase 4's two-person cluster remains explicitly exploratory. Phase 6 now
  has eight panels over stored evidence, with 217/457 flagged days, 35
  all-days assignments versus 24 complete-day assignments, and 23 dates; its
  filters do not refit models.
- Phase 2's final notebook uses temporary disk-backed SQLite tables for
  high-volume key-uniqueness checks, avoiding large in-memory digest sets while
  retaining exact reference comparisons.
- The standard repository suite passes 92 tests (91 passed, one intentionally
  skipped opt-in fresh-kernel test). The earlier complete isolated
  notebook-workflow run passed 3/3. After final notebook refinements, Phase 2
  and Phase 6 each passed a separate isolated fresh-kernel run and their latest
  proof outputs were saved. A redundant combined rerun was interrupted by a
  workspace restart during Phase 1's full raw-file scan; it is not counted as
  complete.
- The three archived original notebooks match their baseline SHA-256 hashes.
  Raw datasets, processed references, analysis scripts, generated analysis
  results, and the historical Phase 4 branch remain unchanged. `src/.gitkeep`
  was removed; `app/.gitkeep` remains.
- No paid services, hosted compute, deployment, or package installation was
  used. The review PR is not yet open; do not merge this branch or begin Phase
  7.
- Full results and the precise verification caveat are recorded in
  `reports/evidence/notebook_conversion/final_corrections_report.md` and
  `final_corrections_manifest.json`.

## Phase 2 findings so far

- The six existing processed CSVs match the expected reference row/column
  counts. Detailed schemas, grains, and transformation rules are in
  `docs/RAW_TO_PROCESSED_SPEC.md`.
- Hourly source keys and order match across all 24,084 rows; the four
  minute-level sources match across all 1,445,040 rows. Both source key sets
  are unique.
- All 525 repeated sleep keys have identical raw row values; no conflicting
  duplicates were found.
- The notebook's daily distance flag uses NumPy `isclose` defaults with
  `atol=0.01`, yielding 65 flagged days. This differs from P1's plain
  absolute-difference screen (104 rows); reproduce the notebook rule for the
  reference export and keep both definitions distinct.
- Initial workspace check: Python 3.13.11, about 355 MiB available RAM,
  800 MiB free temporary storage, and ample local disk. Use sequential
  streaming; do not install packages.
- `src/preprocess.py` regenerates all six references using the Python standard
  library. All six schemas and every row match their reference with zero
  mismatched rows; outputs are kept under the ignored
  `reports/generated/preprocessed/` path.
- The 198,559 sleep records yield 198,034 rows after removing 525 identical
  duplicate occurrences; no conflicting duplicate key was found.
- The hourly (24,084 rows) and minute (1,445,040 rows) input keys align exactly
  across all sources, with no missing or duplicate keys.
- `python -m unittest discover -s tests -v`: 22 tests pass, including the
  full generated-to-reference integration comparison.
- The pipeline implementation is commit
  `c9c5f3e4eae89ab460ef360a9300d7705554c4d5`; its clean-run metrics are under
  `reports/evidence/P2/`.

## Phase 3 implementation

- `notebooks/archive/EDA_analysis.ipynb` covers participant profiles and coverage,
  complete-day sensitivity, daily step distributions and trends,
  weekday/weekend patterns, and activity-duration composition. It has no
  correlation analysis or sleep episode/alignment analysis.
- Revalidated the notebook's core findings: daily steps mean/median
  6,546.56/5,986; 233 complete and 224 incomplete days; participant complete-
  versus all-day means direction 15/12/1, with seven unavailable. Weekday and
  weekend pooled means are 6,528.61/6,584.42; paired directions are 17/17/1.
- Added pooled and equal-participant descriptives, Pearson/Spearman estimates,
  weekday/weekend paired comparisons, sleep-episode review, waking-date
  matching, candidate anomaly screening, and an initial set of eight
  deterministic SVG figures. The analytical-review follow-up added a ninth
  time-accounting figure.
- Sleep data have 198,034 rows, 23 participants, and 556 participant-log
  groups. There are 263 cross-midnight logs, 29 afternoon-start logs, six
  longer-than-12-hour logs, and no gaps or overlaps. Stored codes `1/2/3`
  remain neutral categories.
- The explicit overnight screen yields 359 eligible episodes and 161 unique
  activity waking-date matches across 18 participants. The join preserves all
  457 activity rows; 17 activity dates are ambiguous, and none of the matched
  days is complete. Unmatched sleep remains missing, not zero.
- Initial PR #3 results were eight SVG figures, 10 analysis CSV tables, 10
  evidence JSON paths, and 32 passing tests. The final reviewed results are
  nine SVG figures, 13 analysis CSV tables, 11 evidence JSON paths, and 36
  passing tests. The initial counts are retained as historical results.
- Time accounting sums the four Phase 2 activity-minute fields and the
  recorded row count of a unique matched sleep log, without changing the
  Phase 2 completeness flag. Among 161 matched days, 45 sums equal 1,440
  minutes, 74 are within 15 minutes, 91 within 30, and 110 within 60; the
  median gap is 0 and the mean gap is −58.48 minutes (range −847 to +138).
- April 12, 2016 has seven matched sums from 607 to 833 minutes. Excluding
  April 12 leaves 154 days with mean gap −25.96; excluding April 11–12 leaves
  143 days with mean gap −21.72. These are sensitivity checks only.
- This arithmetic does not establish verified, non-overlapping 24-hour
  coverage. Sleep-row counts are not validated sleep duration, and missing
  activity minutes do not prove device non-wear.
- Reproducible CSVs, SVGs, and compact evidence are in
  `reports/generated/eda/` and `reports/evidence/P3/`. Run
  `python src/eda_analysis.py` to regenerate them.
- Current interpreter has no NumPy, pandas, SciPy, Matplotlib, or Seaborn.
  Prefer standard-library analysis and SVG output; do not install packages.
- The Phase 3 branch starts at `2e233a1de22a7f808bdea3939b75d80e0848a483`.
- Analysis code is committed at `0438560f60723fdc0229f350cc4583b36dc15138`.

## Phase 4 implementation and findings

- The active branch starts at the verified Phase 3 merge
  `77abf8354db99cb48e84ff931e335e2ec2f4c73a`. The original
  `phase-4-activity-clustering` branch remains untouched.
- The old analysis' four features, K=2–6 model comparison, DBSCAN grid, PCA,
  and complete-day comparison were retained conceptually. Reimplemented with
  tested standard-library algorithms because NumPy, scikit-learn, SciPy,
  pandas, Matplotlib, and Seaborn are unavailable; no packages were installed.
- Baseline input: 457 participant-days, 35 participants, 233 complete and
  224 incomplete days, 61 zero-step days. The 61 zero-step days have positive
  recorded duration and remain included. All 35 meet the at-least-3-day rule;
  the complete-day cohort has 24 participants.
- Four features: mean daily steps, mean of daily active-minute shares, mean
  very-active minutes, and sample SD of daily steps. Maximum off-diagonal
  absolute feature correlation is 0.753; distance and sedentary share are
  excluded to avoid duplicating correlated measures.
- K-Means baseline: seed 42, 20 starts, K=2–6; highest silhouette among
  candidates without singleton clusters selects K=3 (17/16/2), silhouette
  0.427, Davies–Bouldin 0.793, Calinski–Harabasz 28.203. The two-person
  highest-step group disappears when those two participants are excluded;
  the remaining 33 assignments retain ARI 1.000. Treat K=3 as exploratory.
- Complete-day fit selects K=2 (18/6); ARI versus the all-days partition on
  24 shared participants is 0.537. A 10-day threshold leaves 30 participants
  and ARI 1.000. Five 20-start seed reruns select K=3 with ARI 1.000.
- DBSCAN reproduces 3 clusters / 8 noise points at `eps=1.0`,
  `min_samples=3`; the wider parameter grid is radius-sensitive and often
  yields one group or substantial noise.
- PCA's first two components explain 85.7% (all days) and 88.9% (complete
  days). A symmetric Jacobi eigensolver passed eigen-residual, orthogonality,
  unit-norm loading, coordinate-shape, and variance-sum checks.
- The final run generated nine CSV tables and 12 SVGs; plots use individual
  scales for each model metric, separate explained/cumulative PCA variance,
  and omit participant IDs.
- The full regression suite passed 59 tests, zero failures/errors/skips,
  including Phase 2 generated-reference checks and Phase 3 analysis tests.
- Generated tables, figures, and machine-readable proofs are under
  `reports/generated/activity_clustering/` and `reports/evidence/P4/`.
- PR #4 merged into `main` at `8172c55865d7b77d3bf193f541220d4e741ce91d`;
  its head `440f93b9a12d019a6db26005e269bc7161641cad` is an ancestor of main.
- At the time this Phase 4 handoff was written, Phase 5 was under review in
  [PR #5](https://github.com/Manthan2106/Fitinsight/pull/5). PR #5 later merged
  at `a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`. Keep the historical Phase 4
  branch unchanged; the Phase 6 web dashboard is paused pending notebook review.

## Phase 5 implementation and findings

- Phase 5 branch: `phase-5-association-anomalies`, created from verified
  `main` at `8172c55865d7b77d3bf193f541220d4e741ce91d` after confirming PR #4
  merged and its head `440f93b9a12d019a6db26005e269bc7161641cad` is in main's
  history. Historical `phase-4-activity-clustering` remains unchanged at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
- Input: all 457 participant-days from 35 people; 233 complete, 224
  incomplete, and 61 zero-step days. The transaction pipeline keeps every row
  and stores participant/date-to-transaction mappings.
- Apriori: six non-overlapping item families; maximum itemset size three;
  5% support (23/457), 60% confidence, lift 1.10, and at least five distinct
  participants. Structural same-family, active-share/very-active, and
  active-share/coverage combinations are excluded. Baseline result: 215
  frequent itemsets, 860 directed rules, 89 eligible rules. Support,
  confidence, lift, participant-count, equal-participant, and complete-day
  sensitivities are recorded.
- Anomaly screens: reuse 140 Phase 3 daily candidates and keep 111 sleep
  candidates separate; add global 1.5×IQR fences, within-person robust scores,
  and pooled/complete/incomplete kNN rankings. The candidate union is 217
  unique participant-days; no rows are removed.
- Distance definitions remain distinct: Phase 1's strict absolute screen
  flags 104 days; Phase 2 flags 65 (all within the 104), leaving 39
  strict-only. April 12 remains in the primary analysis; the sensitivity
  cohort has 433 days.
- Outputs: 21 CSV tables, eight SVG figures, proof lines, metrics, and
  source/input hashes under `reports/generated/associations/`,
  `reports/generated/anomalies/`, and `reports/evidence/P5/`.
- Full regression suite: 89 tests pass with zero failures, errors, or skips.
  Python standard library only; zero package installs or paid analysis
  services. Run `python src/phase5_analysis.py` followed by
  `python src/phase5_validation.py`.
- Historical review state: PR #5 was opened against `main` at the
  implementation commit `0a2bdc3aaff0f0154c3e939950a88d9f9cf5a3d2`; it was
  subsequently merged at `a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`.

## Historical next tasks at the Phase 5 handoff

1. Review PR #5 and address any requested revisions.
2. Keep the P5 PR open and unmerged until review is complete.
3. Keep the historical Phase 4 branch unchanged and do not start the dashboard.

These were the next steps at that handoff and are superseded by the merge and
the notebook-conversion work recorded above.

## Last verified commands

- `git merge-base --is-ancestor 9357d85 HEAD` — PASS after fast-forwarding
  local `main` to the GitHub merge commit.
- Reference CSV inspection streamed all six existing processed exports;
  notebook source and stored validation outputs were summarized.
- `zip_longest` key checks found identical input keys/order for both join
  families; sleep duplicate review found 525 identical repeats and no conflicts.
- `python src/preprocess.py` — PASS for all six generated exports; exact
  reference match, 525 sleep duplicates removed, and per-transform proof saved.
- `python -m unittest discover -s tests -v` — 22 PASS, including integration.
- Final Phase 4 pipeline run — PASS; 9 CSV tables, 12 SVGs, and staged
  computational proof blocks generated with Python 3.13.11 and no third-party
  packages.
- Final full-suite regression run — 59 PASS, zero failures/errors/skips; Phase 2
  and Phase 3 generated integration artifacts were present.
- `python src/phase5_analysis.py` — PASS; 457 transactions, 89 eligible
  association rules, 217 unique daily candidates, 21 CSV tables, and eight
  validated SVGs. No packages or paid analysis services used.
- `python -m unittest discover -s tests -v` — 89 PASS, zero failures, errors,
  or skips; synthetic Apriori, MAD/IQR, kNN, distance-definition, and generated
  artifact checks included.
- GitHub confirmed PR #5 was opened against `main` at implementation commit
  `0a2bdc3aaff0f0154c3e939950a88d9f9cf5a3d2`; it later merged at
  `a52cbaaf4d447ef36013b1cb343a1af1cdafa7ba`.
- GitHub confirms [PR #4](https://github.com/Manthan2106/Fitinsight/pull/4)
  merged into `main` at `8172c55865d7b77d3bf193f541220d4e741ce91d`; its head
  `440f93b9a12d019a6db26005e269bc7161641cad` is in main's history.
- GitHub now confirms PR #2 is merged at `2e233a1`; main includes its head.
- `git fetch origin main && git merge --ff-only origin/main` advanced the
  workspace from `a6170a2` to `2e233a1`; the P3 branch is based there.
- Working tree was clean at branch creation; starting commit is
  `2e233a1de22a7f808bdea3939b75d80e0848a483`.
- Existing EDA notebook inventory: participant profiles, completeness,
  distributions, temporal/weekday comparisons, intensity composition; no sleep
  or correlation implementation.
- Initial PR #3 run, before the time-accounting review follow-up:
  `python src/eda_analysis.py` — PASS; 457 daily rows, 198,034 sleep rows,
  eight SVGs, 10 analysis CSVs, and 10 unique evidence paths. The then-current
  `python -m unittest discover -s tests -v` run passed 32 tests. These are
  historical baseline results; the later review follow-up passed 36 tests.
- Final reviewed run: the Phase 3 pipeline passed with 13 analysis CSV tables,
  nine SVG figures, and 11 evidence JSON paths; all 36 tests passed, including
  time-accounting synthetic cases and chart-point checks against the CSV.
  `python src/preprocess.py` also matched all six generated outputs to their
  committed references. PR #3 was subsequently merged at `77abf8354`.
- The initial run manifest recorded analysis commit
  `0438560f60723fdc0229f350cc4583b36dc15138`; the final reviewed run manifest
  records pipeline commit `a6ec4265deb8ef3778fe27e841cfb30916a96e6a`, clean
  analysis source files, and no raw/reference/notebook modifications.
- At the reviewed analytical head `28f240f23339427cf1c18dd42a7643cb789a3480`,
  GitHub confirmed PR #3 was open; it was later merged at `77abf8354`. The
  separate Phase 4 branch remains at `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
- Python 3.13.11; 355 MiB memory and 800 MiB temporary storage were available
  before P2; no packages were installed.

The prior full raw audit covered 11 files and 7,206,142 rows; its results and
daily-distance/zero-step flags are in the P1 manifest. P2 and P3 records remain
historical; Phase 4 run evidence is in `reports/evidence/P4/`.

## Free-tier status

This session is in Free mode. Remaining account allowance and billing ledger
are not exposed to this workspace. No paid action has been taken; stop before
any action whose cost is not confirmed to be zero.
