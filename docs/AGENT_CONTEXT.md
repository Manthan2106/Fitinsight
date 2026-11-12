# FitInsight agent context

Updated: 2026-11-12

## Goal and constraints

Build an evidence-backed academic dashboard for historical Fitbit activity
data. Preserve raw CSVs and notebooks. Keep analyses reproducible, describe
the observation grain, retain zero-step records, avoid causal/clinical claims,
and use only verified outputs. Work in Free mode with zero-cost local tools;
no paid model, API, add-on, deployment, or compute.

## Verified repository state

- Remote: `https://github.com/Manthan2106/Fitinsight.git`
- `main`: `2e233a1de22a7f808bdea3939b75d80e0848a483`
- `phase-4-activity-clustering`: `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`
- The clustering branch remains separate; it adds `src/activity_clustering.py`,
  `docs/phase-4-clustering.md`, and `requirements.txt`.
- PR #1 merged at `a6170a2`; verified that `9357d85` is in `main` history.
- PR #2 merged at `2e233a1`; its Phase 2 head was `ede8fa3`.
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

P1 is DONE. PR #1 was merged into `main` at
`a6170a2caf64d66b1a622bd50c0b1a69805d34b0`; commit `9357d85` is in its
history. P2 is DONE. PR #2 was merged into `main` at
`2e233a1de22a7f808bdea3939b75d80e0848a483`; Phase 2 head
`ede8fa3e4e94453e8cf5a519653eac4b29b706da` is in its history. P3 is
IN_PROGRESS on `phase-3-exploratory-analysis`, based on that verified main.

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

- `notebooks/EDA_analysis.ipynb` covers participant profiles and coverage,
  complete-day sensitivity, daily step distributions and trends,
  weekday/weekend patterns, and activity-duration composition. It has no
  correlation analysis or sleep episode/alignment analysis.
- Revalidated the notebook's core findings: daily steps mean/median
  6,546.56/5,986; 233 complete and 224 incomplete days; participant complete-
  versus all-day means direction 15/12/1, with seven unavailable. Weekday and
  weekend pooled means are 6,528.61/6,584.42; paired directions are 17/17/1.
- Added pooled and equal-participant descriptives, Pearson/Spearman estimates,
  weekday/weekend paired comparisons, sleep-episode review, waking-date
  matching, candidate anomaly screening, and eight deterministic SVG figures.
- Sleep data have 198,034 rows, 23 participants, and 556 participant-log
  groups. There are 263 cross-midnight logs, 29 afternoon-start logs, six
  longer-than-12-hour logs, and no gaps or overlaps. Stored codes `1/2/3`
  remain neutral categories.
- The explicit overnight screen yields 359 eligible episodes and 161 unique
  activity waking-date matches across 18 participants. The join preserves all
  457 activity rows; 17 activity dates are ambiguous, and none of the matched
  days is complete. Unmatched sleep remains missing, not zero.
- Reproducible CSVs, SVGs, and compact evidence are in
  `reports/generated/eda/` and `reports/evidence/P3/`. Run
  `python src/eda_analysis.py`; the full repository suite passes 32 tests.
- Current interpreter has no NumPy, pandas, SciPy, Matplotlib, or Seaborn.
  Prefer standard-library analysis and SVG output; do not install packages.
- The Phase 3 branch starts at `2e233a1de22a7f808bdea3939b75d80e0848a483`.
- Analysis code is committed at `0438560f60723fdc0229f350cc4583b36dc15138`.

## Next three tasks

1. Commit the validated findings, evidence, project logs, and generated tables
   and figures.
2. Push `phase-3-exploratory-analysis` and open a review PR without merging.
3. Keep the separate Phase 4 clustering branch untouched while awaiting review.

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
- GitHub now confirms PR #2 is merged at `2e233a1`; main includes its head.
- `git fetch origin main && git merge --ff-only origin/main` advanced the
  workspace from `a6170a2` to `2e233a1`; the P3 branch is based there.
- Working tree was clean at branch creation; starting commit is
  `2e233a1de22a7f808bdea3939b75d80e0848a483`.
- Existing EDA notebook inventory: participant profiles, completeness,
  distributions, temporal/weekday comparisons, intensity composition; no sleep
  or correlation implementation.
- `python src/eda_analysis.py` — PASS; 457 daily rows, 198,034 sleep rows,
  eight SVGs, 10 analysis CSVs, and 10 unique evidence paths.
- `python -m unittest discover -s tests -v` — 32 PASS, including P1/P2
  regressions, Phase 3 edge cases, join cardinality, and SVG parsing.
- Run manifest records pipeline commit `0438560f60723fdc0229f350cc4583b36dc15138`,
  clean analysis source files, and no raw/reference/notebook modifications.
- Python 3.13.11; 355 MiB memory and 800 MiB temporary storage were available
  before P2; no packages were installed.

The prior full raw audit covered 11 files and 7,206,142 rows; its results and
daily-distance/zero-step flags are in the P1 manifest. P2 runs will be logged
in their own evidence records.

## Free-tier status

This session is in Free mode. Remaining account allowance and billing ledger
are not exposed to this workspace. No paid action has been taken; stop before
any action whose cost is not confirmed to be zero.
