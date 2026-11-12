# Phase 3 exploratory findings

## Reproduction and scope

Run `python src/eda_analysis.py` from the repository root with Python's standard
library. The analysis reads the committed Phase 2 files
`data/processed/daily_activity_clean.csv` and
`data/processed/minute_sleep_clean.csv`; it does not modify raw data, processed
references, or notebooks. CSV tables and eight vector figures are written under
`reports/generated/eda/`; compact metrics and run evidence are under
`reports/evidence/P3/`.

The run validated 457 participant-days from 35 participants and 198,034 cleaned
sleep-minute records from 23 participants. Daily observation coverage ranges
from 8 to 32 days per participant. All reported fields are retained as recorded;
units and device measurement validity are not independently established.

## Activity profile and notebook revalidation

- Daily recorded steps average 6,546.56 (median 5,986; sample SD 5,398.49;
  adjusted skewness 0.803; range 0–28,497). The distribution is positively
  skewed, as described in the original notebook.
- The complete-day rule is 1,440 recorded minutes: 233 complete and 224
  incomplete participant-days. Mean steps are 5,831.92 on complete days and
  7,289.92 on incomplete days. This is an observation-coverage sensitivity
  comparison, not evidence that incomplete days reflect greater activity.
- Per-participant complete-day mean steps exceed all-day means for 15
  participants, are lower for 12, equal for one, and unavailable for seven
  participants with no complete day. The prior notebook's direction counts
  were reproduced.
- There are 61 zero-step participant-days: 55 are complete days and six are
  incomplete. Participant `4388161847` has seven complete days with zero
  recorded steps. Completeness does not establish that a recorded value is
  behaviorally valid or invalid; zero values remain in the analysis.
- The original notebook's daily coverage range (8–32 days), pooled weekday and
  weekend mean steps (6,528.61 and 6,584.42), and participant directions
  (17 weekend-higher, 17 weekday-higher, one equal) were also reproduced.
  Across 35 paired participants, the mean weekend-minus-weekday step
  difference is 9.86. The complete-day-only sensitivity has 24 paired
  participants and mean difference −13.59; neither is an inferential test.
- The mean per-day composition of the four recorded activity-minute fields is:
  complete days — 1.0% very active, 0.8% fairly active, 10.1% lightly active,
  and 88.1% sedentary; incomplete days — 2.1%, 1.5%, 20.5%, and 75.9%,
  respectively. The denominator is the sum of those four fields, not verified
  waking time. Average recorded time is 1,440 minutes on complete days and
  940.25 minutes on incomplete days.

## Associations

Pearson and Spearman coefficients use pairwise complete cases. Pooled daily
rows repeat participants, so coefficients describe these recorded rows; no
p-values or independent-person inference are reported. Equal-weight
participant-mean coefficients are also available in
`reports/generated/eda/tables/correlations.csv`.

| Pooled participant-day pair | Pearson r | Spearman rho | Pairs / participants |
| --- | ---: | ---: | ---: |
| Steps and calories | 0.581 | 0.584 | 457 / 35 |
| Steps and total distance | 0.987 | 0.996 | 457 / 35 |
| Steps and active minutes | 0.776 | 0.859 | 457 / 35 |
| Active and sedentary minutes | −0.416 | −0.511 | 457 / 35 |

These are descriptive associations only. High association does not establish
that one field is an independent or validated measure of another.

## Sleep episode and waking-date analysis

Processed sleep rows were grouped by participant and log ID, ordered by
timestamp, and checked for value categories, crossing midnight, elapsed span,
interval gaps, overlaps, and candidate waking dates. The stored categories
remain codes `1`, `2`, and `3`; no sleep-stage interpretation is supported by
the repository.

- The 198,034 rows form 556 participant-log groups. Category counts are
  `1`: 183,038; `2`: 12,983; `3`: 2,013.
- 263 logs cross midnight, 29 begin between 12:00 and 17:59, and six exceed
  12 elapsed hours. No gaps over 60 seconds, non-60-second intervals, or
  overlapping logs were found.
- The explicit overnight screen yields 437 candidate logs and 359 individually
  eligible logs. Thirty-seven participant-waking dates contain multiple
  overnight candidate logs (78 sessions); matching excludes those ambiguous
  dates rather than multiplying rows.
- Matching a unique eligible session's end date to the daily activity date
  produces 161 waking-date matches across 18 participants. The activity table
  remains at 457 unique participant-days; 17 activity dates are ambiguous,
  279 have no eligible overnight log, and 198 eligible sleep logs have no
  activity row on their waking date. Unmatched sleep is blank, never zero.
- All 161 matched activity days are marked incomplete; there are zero matched
  complete activity days. Therefore a complete-day-only sleep/activity
  sensitivity is unavailable for this alignment. This is a coverage result,
  not a zero-valued sleep measurement.
- The pooled Spearman association between recorded sleep-log rows and waking
  day steps is −0.054 (161 matched days; 18 participants). The
  equal-weight participant-mean coefficient is 0.218 (18 participants).
  Recorded row count is not validated actual time asleep; this contrast is
  descriptive and does not imply causation.

## Time-accounting challenge: activity plus sleep rows

To investigate why all 161 matched waking dates remain incomplete under the
Phase 2 rule, the four recorded activity-minute fields were summed and checked
against the stored `total_recorded_minutes`. They agree on all 161 matched
participant-days. That activity total was then added to the recorded row count
in the one uniquely eligible sleep log; the difference is combined minutes
minus 1,440. The Phase 2 completeness flag and its definition were not changed.

- Across 161 matched days from 18 participants on 23 dates, 45 sums are exactly
  1,440 minutes; 74 are within 15 minutes, 91 within 30, and 110 within 60.
  The median difference is 0 minutes, the mean is −58.48, the mean absolute
  difference is 80.17, and the range is −847 to +138 minutes.
- Activity minutes and recorded sleep-row counts have pooled Pearson
  correlation −0.358 and Spearman correlation −0.637. Equal-weight
  participant-mean correlations are −0.622 and −0.635 across 18 participants.
  These are descriptive repeated-observation summaries, not inferential tests.
- The pattern differs across participants: nine of 18 participants have at
  least one exact sum, and nine have none. One participant has exact sums on
  all 11 matched days; participant-level mean differences range from −142.64
  to +87.00 minutes. Counts and per-person estimates are in
  `time_accounting_by_participant.csv`.
- The 23-date summaries are in `time_accounting_by_date.csv`. On April 11,
  2016, 2 of 11 matched sums are exact (mean difference −81.09; range −695 to
  +117). On April 12, seven matched sums range from 607 to 833 minutes
  (differences −847 to −607); none is within 60 minutes of 1,440.
- Sensitivity checks retain the primary 161-day result and only omit boundary
  dates for comparison. Excluding April 12 leaves 154 days / 18 participants
  / 22 dates: 45 exact, 74 within 15, 91 within 30, 110 within 60; mean
  difference −25.96, median 0, Pearson −0.607, Spearman −0.688. Excluding
  April 11 and 12 leaves 143 days / 18 participants / 21 dates: 43 exact,
  69 within 15, 85 within 30, 104 within 60; mean difference −21.72, median
  0, Pearson −0.710, Spearman −0.701. These are sensitivity checks, not a
  reason to remove dates from the primary analysis.

The arithmetic is compatible with complementary time accounting for many
participant-days, but it does not prove that the fields partition one
non-overlapping 24-hour period. Sleep values are counts of stored minute rows,
not verified minutes asleep; interval definitions, timezone/date assignment,
overlap with the activity fields, and the reason for incomplete activity
coverage are undocumented. A matched sleep log does not make its waking-day
activity record complete: Phase 2 completeness still evaluates only the four
activity-minute fields. Missing recorded activity minutes therefore cannot be
called device non-wear without independent wear-status evidence.

For downstream clustering and participant comparisons, keep the Phase 2 flag
and source fields as recorded. Do not label a combined sum as verified daily
coverage, convert missing sleep to zero, or interpret an incomplete flag as
non-wear. If sleep features are later explored, state the matched-subset
selection, use an explicit missingness strategy, and compare activity-only
results with any sleep-informed sensitivity. The separate Phase 4 branch was
not changed. The added compact table, per-participant/per-date summaries,
evidence JSON, and computed-versus-plotted figure checks are listed in
`reports/evidence/P3/time_accounting_metrics.json` and the generated EDA
artifacts.

## Review candidates and figures

The 1.5×IQR screen plus explicit Phase 2 distance and zero-step co-occurrence
flags identifies 140 daily rows and 111 sleep episodes for possible review.
Rows are retained; neither a statistical fence nor a quality flag proves that
an observation is invalid or medically abnormal. See
`reports/generated/eda/tables/anomaly_candidates.csv`.

Nine SVG figures are indexed in `reports/evidence/P3/figures_index.json`.
They cover daily step distribution, completeness sensitivity, daily trend and
coverage, paired weekday/weekend means, activity-minute composition, activity
correlations, sleep-log size, and sleep-log rows versus waking-day steps.
The ninth plots combined recorded minutes against the 1,440-minute reference;
tests compare each plotted point's date and value against the time-accounting
CSV rather than checking SVG syntax alone.

## Reproducibility and limits

`reports/evidence/P3/run_manifest.json` records the source-data commit,
Python version, input counts, code hashes, outputs, and validation status.
The tests exercise statistics, tie handling, participant pairing, irregular
and ambiguous sleep episodes, missing-value treatment, join cardinality,
time-accounting boundary cases, and chart data against computed statistics.
The work uses only Python's standard library and local files. The sample is
historical and not established as representative; field units, device wear,
and physiological meaning are unknown. No causal, clinical, or health advice
follows from these results.
