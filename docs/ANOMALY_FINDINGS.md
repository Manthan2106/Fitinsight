# Phase 5 anomaly-screen findings

## Scope and reuse

Run `python src/phase5_analysis.py` after the Phase 3 EDA command has generated
`reports/generated/eda/tables/anomaly_candidates.csv`. Phase 5 validates and
reuses those flags and their evidence JSON; it does not overwrite them.

The primary analysis contains all 457 participant-days from 35 participants,
including all 61 zero-step days. It keeps the 140 Phase 3 daily candidates
separate from the 111 Phase 3 sleep-episode candidates. Sleep episodes retain
their own participant-log grain and are not combined with daily records.

## Screening methods and results

### Global IQR screen

The Phase 3 linear-interpolated Q1/Q3 convention is reused with 1.5×IQR fences.
Seven recorded or derived daily fields are screened. This yields 36 unique
participant-days with at least one field outside a fence; the per-field counts
can overlap:

| Field | Below lower fence | Above upper fence |
| --- | ---: | ---: |
| Total steps | 0 | 5 |
| Calories | 10 | 12 |
| Total distance | 0 | 7 |
| Total active minutes | 0 | 2 |
| Sedentary minutes | 0 | 0 |
| Total recorded minutes | 10 | 0 |
| Active-minute share | 0 | 3 |

These are review candidates. An IQR fence does not establish a data error or
invalid observation.

### Within-participant robust screen

For each participant, daily total steps and active-minute share are compared
with that participant's own observed values, requiring at least five days. The
robust score is `0.67449 * (value - median) / MAD`, with an absolute threshold
greater than 3.5. If MAD is zero but IQR is positive, the finite fallback scale
is `IQR / 1.34898`; when both scales are zero, the value is left unscaled and
is not flagged.

The screen has 68 flagged metric rows across 48 unique participant-days. Five
participant/metric groups use the IQR fallback; three have zero MAD and zero
IQR and remain unscaled.

### Coverage-aware multivariate screen

Each day is represented by recorded steps per recorded hour, calories per
recorded hour, and active-minute share. Features are population-SD standardized
within each scored cohort. The score is the mean Euclidean distance to the
nearest `k` other participant-days; the top 5% by deterministic rank are
reported for `k=5` and `k=10`.

The pooled screen marks 23 days at each `k`. Separately scored complete-day
and incomplete-day cohorts each mark 12 days, for 24 unique coverage-stratified
candidates. The `k=5` and `k=10` stratified sets overlap on 23 days; pooled
sets overlap on 20 days. These are ranking sensitivities, not calibrated
probabilities. Per-hour scaling does not establish wear time or make the two
coverage cohorts interchangeable.

## Existing distance flags and detector overlap

Two established distance definitions remain separate:

- Phase 1's plain absolute-difference screen flags 104 days where
  `|component_distance_sum - total_distance| > 0.01`.
- The committed Phase 2/Phase 3 `distance_discrepancy` flag marks 65 days under
  its existing NumPy-isclose-equivalent rule.
- All 65 Phase 2 flags are also among the 104 strict absolute-difference cases;
  39 cases are strict-only. The two counts are not interchangeable.

Phase 3's 140 daily candidates overlap the Phase 1 strict screen on 67 days and
the Phase 2 flag on 65 days. Phase 3's positive-calorie/activity zero-step
flags identify 56 days. Across ten daily screening sets, the union contains
217 unique participant-days. Pairwise intersections and Jaccard values are in
`detector_overlaps.csv`; detector counts must not be added because records
overlap.

Seven deterministically selected records are summarized as case-review
examples with their source values and flags in `review_cases.csv`. The file
retains participant/date keys for auditability; figures and narrative summaries
do not expose participant IDs. No cause is inferred and no observation is
removed.

Selected examples show why a flag is a review prompt rather than a verdict:

| Case | Observed values | Screen evidence |
| --- | --- | --- |
| CASE-002, 2016-04-05 | Component-sum distance gap is 0.0100005 | Just exceeds the strict absolute 0.01 rule; it is not flagged by the Phase 2 rule |
| CASE-003, 2016-04-12 | 41 recorded minutes, 224 steps, 50 calories | Low recorded duration and calories; within-person step score −7.58; retained in the primary boundary date |
| CASE-004, 2016-04-05 | 729 recorded minutes and 86.4% active-minute share | Global active-share fence, within-person IQR fallback, and pooled/stratified kNN ranks |
| CASE-005, 2016-03-20 | 1,440 recorded minutes and component-sum distance gap 7.41 | Both Phase 1 and Phase 2 distance screens; no additional global IQR flag |
| CASE-006, 2016-03-14 | 8,433 steps versus participant median 13 (MAD 13) | Within-person modified robust score 436.9; a very low personal reference scale makes this an extreme relative deviation, not an error confirmation |
| CASE-007, 2016-04-10 | 28,497 steps, 4,526 calories, recorded distance 27.53 | High-tail global IQR flags for steps, calories, and distance; values are retained |

## Last-date sensitivity

The primary result retains April 12, 2016, the final observed date. That date
has 24 rows, three complete days, and median recorded minutes of 426; it is
still part of the source data. The primary result contains 457 days; the
sensitivity excluding that date contains 433. Global IQR,
within-person, kNN, and distance screens are recomputed on the sensitivity
subset. Existing Phase 3 flags are filtered to that subset but are not
re-estimated.

| Screen | Primary days | Excluding April 12 |
| --- | ---: | ---: |
| Phase 3 daily candidates | 140 | 127 |
| Global IQR, any field | 36 | 21 |
| Within-participant robust | 48 | 42 |
| Pooled kNN, k=5 | 23 | 22 |
| Coverage-stratified kNN, k=5 | 24 | 23 |
| Phase 1 strict absolute distance | 104 | 101 |
| Phase 2 distance flag | 65 | 64 |
| Zero steps with positive calories or activity | 56 | 54 |

These are boundary-date sensitivities only; the primary dataset and candidate
registry retain all 457 rows.

## Outputs and limitations

Thirteen generated anomaly tables preserve the Phase 3 daily reasons, sleep
episode candidates, global fences, within-person scores, kNN scores, detector
counts and overlaps, all-row candidate registry, selected review cases, and
date sensitivity. Five SVG figures summarize IQR flags, detector counts, kNN
score quantiles, within-person candidates, and the final-date sensitivity.

All flags are exploratory screens, not diagnoses, error confirmations, or
health findings. The archive is historical, coverage differs, units and device
wear status are not independently verified, and one outlier method can disagree
with another. Candidate rows and source data remain unchanged.
