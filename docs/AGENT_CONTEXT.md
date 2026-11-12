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
- `main`: `201268635a04a7fee03a00cb7030e8106f6d13ec`
- `phase-4-activity-clustering`: `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`
- The clustering branch remains separate; it adds `src/activity_clustering.py`,
  `docs/phase-4-clustering.md`, and `requirements.txt`.
- No PRs or issues were returned by GitHub at the initial audit; Phase 1 is
  now available for review in PR #1.
- `main` has 11 raw CSVs, six processed CSVs, three executed notebooks, empty
  `app/` and `src/` placeholders, and no README, tests, or dependency file.
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

P1 foundation/audit is in review. The streaming audit and seven unit tests run
successfully. The branch `phase-1-foundation` is pushed; PR #1 is open against
`main` and has not been merged.

## Next three tasks

1. Review PR #1; keep `main` unchanged until the repository owner decides.
2. After Phase 1 integration, inspect the preprocessing notebook and six
   processed exports before proposing transformation changes.
3. Start P2 only after checking reproducibility requirements and memory cost.

## Last verified commands

- `python -m unittest discover -s tests -v` — 7 tests passed on the current
  local changes.
- `git diff --check` — PASS.
- `python src/data_audit.py` — latest full scan PASS at the source revision
  recorded in `reports/evidence/P1/run_manifest.json`. The audit code is
  unchanged in this review follow-up, so the large raw scan was not repeated.

The full scan covered 11 files and 7,206,142 rows, with complete composite
keys and parseable dates; sleep had 525 duplicate keys. Daily-distance and
zero-step flags are in the manifest. Environment: Python 3.13.11; about 436
MiB memory was available at the initial check. No packages were installed.

## Free-tier status

This session is in Free mode. Remaining account allowance and billing ledger
are not exposed to this workspace. No paid action has been taken; stop before
any action whose cost is not confirmed to be zero.
