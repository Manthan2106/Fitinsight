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
- `main`: `a6170a2caf64d66b1a622bd50c0b1a69805d34b0`
- `phase-4-activity-clustering`: `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`
- The clustering branch remains separate; it adds `src/activity_clustering.py`,
  `docs/phase-4-clustering.md`, and `requirements.txt`.
- PR #1 merged at `a6170a2`; verified that `9357d85` is in `main` history.
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
history. P2 is implemented and ready for review on
`phase-2-reproducible-preprocessing`, created from that verified main commit.

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

## Next three tasks

1. Push the Phase 2 branch and open a review PR; do not merge it.
2. Address review feedback without changing the raw files, notebooks, or
   separate Phase 4 branch.
3. Start Phase 3 only after the Phase 2 review is accepted.

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
- Python 3.13.11; 355 MiB memory and 800 MiB temporary storage were available
  before P2; no packages were installed.

The prior full raw audit covered 11 files and 7,206,142 rows; its results and
daily-distance/zero-step flags are in the P1 manifest. P2 runs will be logged
in their own evidence records.

## Free-tier status

This session is in Free mode. Remaining account allowance and billing ledger
are not exposed to this workspace. No paid action has been taken; stop before
any action whose cost is not confirmed to be zero.
