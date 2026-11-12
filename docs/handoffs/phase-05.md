# Phase 5 handoff: association rules and anomaly screening

## Review state

- Status: IN_REVIEW.
- Pull request: [PR #5 — Phase 5: Apriori association rules and anomaly screening](https://github.com/Manthan2106/Fitinsight/pull/5).
- Base: `main`; source branch: `phase-5-association-anomalies`.
- PR #5 was opened at implementation commit
  `0a2bdc3aaff0f0154c3e939950a88d9f9cf5a3d2`. The PR page is the authoritative
  live source for the latest branch head.
- Do not merge this PR automatically. Phase 6 has not been started.

## Reproducible workflow

Run from the repository root, after generating the Phase 2 and Phase 3
prerequisites:

```bash
python src/preprocess.py
python src/eda_analysis.py
python src/phase5_analysis.py
python src/phase5_validation.py
```

The analysis and validation use Python's standard library only; no packages
were installed and no paid compute or analysis service was used. The validation
script runs `python -m unittest discover -s tests -v`, writes
`reports/evidence/P5/test_results.json`, and updates the run manifest.

## Association results

- All 457 participant-days from 35 participants are kept as transactions. Each
  transaction contains one item from each of six exclusive families; zero-step
  days are retained.
- Calorie bins use cohort Q1/Q3; step, active-share, coverage, activity-minute,
  and day-type rules are recorded in source and evidence.
- The bounded Apriori search finds 215 frequent itemsets, examines 860 directed
  rules, and retains 89 at support 5%, confidence 60%, lift 1.10, and five
  distinct participants. Same-family categories and combinations that reuse
  the active-share numerator or coverage denominator are excluded.
- Sensitivity tables vary support, confidence, lift, and participant-count
  thresholds; they also report equal-participant rates and complete-day rules.
  These are co-occurrence results, not causal effects.

## Anomaly results

- Phase 3's 140 daily candidates and 111 sleep-episode candidates are reused
  without conflating their grains.
- New screens include global 1.5×IQR fences, within-person robust scores with
  zero-MAD handling, and pooled/complete/incomplete kNN rankings.
- The union contains 217 unique daily candidates. No source row is removed.
  Phase 1's strict absolute-distance rule flags 104 days; Phase 2 flags 65,
  all within the 104. The 39 strict-only cases remain separately labeled.
- April 12, 2016 remains in the primary 457-day result; a separate sensitivity
  excludes it and contains 433 days. Selected record examples are documented
  without participant IDs in `docs/ANOMALY_FINDINGS.md`; no causes are inferred.
- These are review candidates, not confirmed errors or health classifications.

## Evidence and files

- 21 CSV analysis tables and eight validated SVG figures are under
  `reports/generated/associations/` and `reports/generated/anomalies/`.
- Proofs, input/source hashes, figure index, and test results are under
  `reports/evidence/P5/`.
- All 89 tests pass with zero failures, errors, or skips.
- Project decisions, challenges, and experiments are appended in
  `docs/DECISION_LOG.md`, `docs/CHALLENGE_LOG.md`, and
  `docs/EXPERIMENT_LOG.csv`; see `docs/EVIDENCE_INDEX.md` for the run record.
- Phase 4 is merged at `8172c55865d7b77d3bf193f541220d4e741ce91d`; its
  historical `phase-4-activity-clustering` branch remains unchanged at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
