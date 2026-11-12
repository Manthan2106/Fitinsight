# Phase 4 handoff — validated clustering and PCA

## Current state

- Phase 4 implementation is complete locally on
  `phase-4-validated-clustering`, created from verified `main` at
  `77abf8354db99cb48e84ff931e335e2ec2f4c73a`.
- PR submission is the next step. Phase 4 must remain unmerged until reviewed.
- Historical `phase-4-activity-clustering` remains separate and unchanged.
- Phases 5–7 have not started.

## Implemented and validated

- Uses `data/processed/daily_activity_clean.csv` only; does not change raw
  data, committed processed references, or original notebooks.
- Preserves the Phase 2 complete-day definition and all 61 positive-duration
  zero-step days.
- Uses four participant features, independently standardized by cohort.
- Runs deterministic K-Means comparisons, the full DBSCAN parameter grid,
  cohort sensitivity checks, and standard-library PCA.
- Produces nine CSV tables, 12 titled and described SVG figures, and
  task-specific machine-readable evidence under
  `reports/generated/activity_clustering/` and `reports/evidence/P4/`.
- Prints computational `FITINSIGHT_PROOF` blocks for each major data and model
  stage. The run manifest hashes the input and source files and lists the
  generated evidence.
- No third-party libraries were available; no packages, paid services, or
  external APIs were used.

## Principal findings and limits

- Baseline: 35 participants from 457 participant-days; complete-day sensitivity
  cohort: 24 participants.
- Selected all-days K=3 sizes are 17/16/2; silhouette is 0.427. The two-person
  group is sensitive to participant exclusion and must remain exploratory.
- Complete-day K=2 has sizes 18/6 and ARI 0.537 against all-days on 24 shared
  participants. The >=10-day and five-seed checks preserve the baseline
  assignment (ARI 1.000).
- DBSCAN at `eps=1.0`, `min_samples=3` finds 3 groups and 8 noise points, but
  the 5-by-3 grid is parameter-sensitive.
- First-two-PC variance is 85.7% for all-days and 88.9% for complete-days.
- The 59-test full regression suite passes with zero failures, errors, or
  skips. Phase 2 generated artifacts and Phase 3 analytical artifacts were
  present for integration checks.
- Findings describe a small historical wearable sample; they are not health,
  fitness, or population-level conclusions. The local algorithms are
  mathematically tested but not claimed as bit-for-bit scikit-learn
  replacements.

## Reproduction

From the repository root:

```bash
python src/activity_clustering.py
python -m unittest discover -s tests -v
```

The full suite expects the documented Phase 2 and Phase 3 generated outputs.

## Next action

Push the Phase 4 branch and open a review-only pull request against `main`.
Verify the pushed head and PR base/state on GitHub. Do not merge it, alter the
historical branch, or start Phase 5/dashboard work.
