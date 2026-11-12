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
- No open PRs or issues were returned by GitHub at the audit.
- `main` has 11 raw CSVs, six processed CSVs, three executed notebooks, empty
  `app/` and `src/` placeholders, and no README, tests, or dependency file.
- Raw audit: 11 files, 7,206,142 rows, 271,592,676 bytes. Daily activity has
  457 rows / 35 participants; sleep has 198,559 rows / 23 participants and
  525 duplicate `(Id, date, logId)` keys; weight has 33 rows / 11 participants
  and 31 missing `Fat` values. See `reports/evidence/P1/`.
- The three notebooks parse successfully, have executed code cells, and store
  no error outputs. Existing outputs remain historical until rerun.

## Current phase

P1 foundation/audit is in progress. The streaming audit and three unit tests
run successfully. Documentation, final diff review, commit, branch push, and
remote verification are still pending; P1 is not marked done.

## Next three tasks

1. Finish the field dictionary, quality memo, and evidence/context logs.
2. Review the focused Phase 1 diff, create a feature branch, push, and verify
   the remote SHA without touching `main`.
3. Start P2 by inspecting the existing preprocessing notebook and six
   processed exports before proposing any transformation changes.

## Last verified command

`python -m unittest discover -s tests -v && python src/data_audit.py`

Result: 3 unit tests passed; the streaming audit returned PASS for 11 files,
7,206,142 rows, complete composite keys and parseable dates. Only sleep had
duplicate keys (525). Environment: Python 3.13.11; approximately 436 MiB
memory was available at the initial check. No packages were installed.

## Free-tier status

This session is in Free mode. Remaining account allowance and billing ledger
are not exposed to this workspace. No paid action has been taken; stop before
any action whose cost is not confirmed to be zero.
