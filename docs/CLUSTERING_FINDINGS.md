# Phase 4 clustering findings

## Scope and reproducibility

Phase 4 describes participant-level patterns in the committed
`data/processed/daily_activity_clean.csv`. It does not change raw data,
processed references, original notebooks, or the historical
`phase-4-activity-clustering` branch. The implementation uses Python's standard
library only; no packages, services, or paid resources were used.

Run from the repository root:

```bash
python src/activity_clustering.py
python -m unittest discover -s tests -v
```

The Phase 2 and Phase 3 generated artifacts must be present before running the
full regression suite. The pipeline prints `FITINSIGHT_PROOF` blocks for each
cohort, feature/scaling, model, sensitivity, PCA, and artifact-validation stage.
Each block records its question, sample, method, parameters, result, checks,
artifact, and limitation.

The baseline contains 457 participant-days from 35 participants. The baseline
includes each participant with at least three days having positive recorded
minutes; all 61 zero-step days are retained because they have positive recorded
duration. A separate complete-day cohort has 24 participants. The stored
Phase 2 definition (`total_recorded_minutes == 1440`) is retained unchanged.

## Participant features

Each person contributes one row, so people with more recorded days do not
contribute more rows to the clustering. The four features are:

- Mean daily steps.
- The equal-weight mean of each eligible day's
  `(very + fairly + lightly active minutes) / total recorded minutes`.
- Mean daily very-active minutes.
- Sample standard deviation of daily steps.

Distance is excluded because Phase 3 found it closely tracks steps; sedentary
share is complementary to active share under the same recorded-minute
denominator. The largest off-diagonal absolute Pearson correlation among the
four retained features is 0.753.

| Feature pair | Pearson r |
| --- | ---: |
| Mean steps / mean active share | 0.705 |
| Mean steps / mean very-active minutes | 0.753 |
| Mean steps / step variability | 0.634 |
| Mean active share / mean very-active minutes | 0.419 |
| Mean active share / step variability | 0.271 |
| Mean very-active minutes / step variability | 0.518 |

Each cohort is standardized independently with population standard deviation.
All four features are nonconstant in both cohorts. The sample is small, and the
standard deviation feature can be unstable near the three-day eligibility
threshold.

## K-Means comparison

The deterministic standard-library implementation evaluates K=2–6 with seed
42, 20 starts per K, and up to 300 Lloyd iterations. The selection rule takes
the highest silhouette among partitions with at least two people in each
cluster. It is a transparent exploratory rule, not proof that the selected K
is a true number of behavioral groups.

| K | Silhouette | Davies–Bouldin | Calinski–Harabasz | Cluster sizes | Selection |
| ---: | ---: | ---: | ---: | --- | --- |
| 2 | 0.409 | 0.909 | 31.492 | 17 / 18 | Eligible |
| 3 | **0.427** | **0.793** | 28.203 | 17 / 16 / 2 | Selected |
| 4 | 0.397 | 0.853 | 28.342 | 17 / 10 / 6 / 2 | Eligible |
| 5 | 0.361 | 0.838 | 29.716 | 12 / 5 / 10 / 6 / 2 | Eligible |
| 6 | 0.371 | 0.736 | 28.681 | 1 / 6 / 10 / 10 / 6 / 2 | Excluded: singleton |

The metrics do not unanimously favor K=3: K=2 has the higher
Calinski–Harabasz score. K=3's silhouette advantage over K=2 is small, and its
highest-mean-step cluster contains only two participants. Five independent
seed reruns (1, 7, 19, 42, 123), each using 20 starts, select K=3 and yield ARI
1.000 versus the baseline. That demonstrates reproducibility for this sample
and implementation, not external validity.

All-days cluster summaries (labels are arbitrary and ordered by mean steps):

| Cluster | People | Eligible days | Mean steps | Mean active share | Mean very-active min/day | Step SD | Complete-day share |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 17 | 235 | 3,100 | 11.5% | 2.9 | 2,437 | 67.7% |
| 1 | 16 | 199 | 8,992 | 25.2% | 26.0 | 4,055 | 29.3% |
| 2 | 2 | 23 | 16,131 | 20.2% | 75.8 | 7,195 | 91.3% |

The two-person cluster has the highest mean steps and very-active minutes but
not the highest active share. Its high step variability and coverage profile
are part of the description; they do not establish a meaningful fitness type.

## Cohort sensitivity

| Cohort | People | Selected K and sizes | ARI vs all-days on shared people |
| --- | ---: | --- | ---: |
| All-days baseline | 35 | K=3; 17 / 16 / 2 | 1.000 |
| Complete days, at least 3 | 24 | K=2; 18 / 6 | 0.537 |
| At least 10 positive-duration days | 30 | K=3; 13 / 15 / 2 | 1.000 |
| Excluding two highest-mean-step people | 33 | K=2; 17 / 16 | 1.000 |

The complete-day partition differs materially from the all-days partition.
Excluding the two highest-step participants removes the two-person group and
selects K=2, while the remaining assignments agree perfectly with the
corresponding baseline subset. ARI is a label-invariant partition-agreement
measure, not accuracy. The sensitivity supports describing K=3 as exploratory
and the two-person group as especially cohort-sensitive.

## DBSCAN

Euclidean DBSCAN is evaluated over five `eps` values (0.75, 1.0, 1.25, 1.5,
2.0) and three `min_samples` values (3, 4, 5). Noise keeps label `-1`;
silhouette, Davies–Bouldin, and Calinski–Harabasz scores are calculated only
on assigned participants when at least two clusters remain.

At `eps=1.0`, `min_samples=3`, the run finds three clusters of 3, 16, and 8
people plus 8 noise points. The assigned-point silhouette is 0.446,
Davies–Bouldin is 0.743, and Calinski–Harabasz is 23.357. Nearby parameter
choices frequently collapse to one cluster or mark many participants as
noise. Because scores exclude noise and the outcome is parameter-sensitive,
DBSCAN is a comparison rather than a preferred segmentation.

## PCA

PCA uses the sample covariance matrix (`n-1`) of the standardized features and
a symmetric Jacobi eigensolver. Checks include eigen residual, orthogonality,
unit-norm loadings, coordinate dimensions, and explained-variance sum.

| Cohort | PC1 | PC2 | First two cumulative |
| --- | ---: | ---: | ---: |
| All-days, n=35 | 67.1% | 18.7% | 85.7% |
| Complete-days, n=24 | 67.7% | 21.2% | 88.9% |

For all-days PC1, all four loadings are positive; mean steps (0.584), very
active minutes (0.510), and step variability (0.449) contribute most. PC2
contrasts active share (0.741) with step variability (-0.639). PCA directions
are summaries of variance, not causal effects or evidence of valid clusters.
Component signs may flip together without changing the solution.

## Outputs and validation

The pipeline writes nine CSV tables and 12 titled, described SVG figures under
`reports/generated/activity_clustering/`, plus task evidence and a run manifest
under `reports/evidence/P4/`. Figures omit individual participant IDs and state
the sample and key limitation. Four K-Means diagnostics use separate
zero-based scales; explained and cumulative PCA variance are separate charts.
Signed heatmaps use a zero-centered diverging key.

The final full test run passed **59 tests**, with zero failures, errors, or
skips. Phase 2 generated prerequisites and Phase 3 tables/figures were present.
The standard-library clustering and PCA routines are validated by synthetic
cases and internal mathematical checks, but their initialization, tie
handling, and floating-point conventions are not claimed to be bit-for-bit
equivalent to scikit-learn.

**Interpretation limit:** These clusters describe recorded fields from a small,
historical wearable sample. They are not health, fitness, or behavior labels,
and no population-level conclusion is supported.
