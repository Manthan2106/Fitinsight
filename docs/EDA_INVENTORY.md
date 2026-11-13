# Existing EDA inventory

## Source and execution status

- Historical source: `notebooks/archive/EDA_analysis.ipynb` (74 cells;
  executed outputs are preserved).
- The notebook loads daily, sleep, weight, hourly, minute, and heart-rate
  processed exports. Its analysis cells operate on daily activity only.
- The notebook is preserved as a research artifact. Its saved outputs were
  revalidated from `data/processed/daily_activity_clean.csv` by Phase 3; see
  `docs/EDA_FINDINGS.md` for reproduced values and limitations.
- Five chart outputs are present: daily-step histogram, complete/incomplete
  box plot, daily-step trend with participant coverage, weekday/weekend
  box plot, and complete/incomplete activity composition.

## Existing analyses and reusable calculations

| Area | Existing calculation or visual | Phase 3 action |
| --- | --- | --- |
| Participant profile | Recorded days, complete days, complete-day percentage, average/median/standard deviation of steps, average calories, sedentary/active minutes, and distance | Recompute participant summaries and distinguish participant-weighted from pooled day-level statistics |
| Coverage | Recorded-day counts and complete-day coverage by participant; stored range is 8–32 days | Revalidated: 35 participants, 8–32 recorded days |
| Complete-day sensitivity | Compares all-day and complete-day participant mean steps; stored counts are 15 increased, 12 decreased, 1 unchanged, and 7 without a complete-day mean | Revalidated and exported; direction counts match the stored notebook |
| Daily distribution | Descriptive step statistics, histogram, and skewness | Recompute full metric set for steps, calories, distance, active/sedentary minutes, and recorded time |
| Daily trend | Date-level mean/median steps and participant coverage | Reuse, add an explicit coverage panel and date sample sizes |
| Weekday/weekend | Pooled step summaries and participant-level weekend-minus-weekday step means; stored direction count is 17/17/1 across 35 participants | Recompute for steps, calories, active minutes, sedentary minutes, and paired participant differences |
| Activity intensity | Means of very/fairly/lightly active and sedentary minutes; completeness comparison and per-day percentage composition | Recompute; label percentages as shares of the four recorded activity-minute fields, not all clock time |
| Sleep | Sleep CSV is loaded, but no episode, value-category, or coverage analysis is performed | Add session integrity, coverage, episode reconstruction, and cautious waking-date matching |
| Relationships | No correlation matrix, Pearson/Spearman estimates, sample-size table, or participant-level correlation | Add pairwise estimates with valid-pair and participant counts; no causal or naive independent-day inference |
| Outliers | Some zero-step cases are named narratively; no systematic review table | Produce a compact candidate table with reasons and preserve all source rows |

## Original conclusions revalidated in Phase 3

- Stored daily step mean/median were approximately 6,546.56 / 5,986; the
  distribution was positively skewed.
- Stored incomplete-day mean steps (7,289.92) exceeded complete-day mean steps
  (5,831.92). This is a recording-selection comparison, not evidence that
  incomplete days represent greater activity.
- Stored weekday/weekend pooled mean steps were similar (6,528.61 / 6,584.42),
  while participant-level differences were heterogeneous.
- Incomplete days showed lower sedentary minutes than complete days; recorded
  time differs by construction, so this comparison requires a coverage caveat.
- The notebook reports sedentary time as a large share of complete-day recorded
  activity minutes. Its denominator is the sum of four activity-duration
  fields, not an independently verified measure of waking time.
- Historical findings about the highest-step participants and zero-step
  participants were recalculated: participant `8877689391` has the highest
  mean (about 17,417 steps/day); participant `4388161847` has eight recorded
  days averaging zero steps, including seven complete days.

## Phase 3 revalidation

- The original step mean, median, positive skew, complete/incomplete means,
  participant sensitivity directions, weekday/weekend pooled means, and
  weekday/weekend participant directions all reproduce from the committed
  processed daily file. Exact results and caveats are in
  `docs/EDA_FINDINGS.md`.
- The 61 zero-step observations include 55 complete and six incomplete days.
  The original zero-value handling was retained; completeness is not used to
  infer whether a zero is a true behavioral value.
- The notebook's activity-minute composition remains a share of the four
  duration fields, not a waking-time estimate. Incomplete-day recorded time is
  lower on average, so the composition is coverage-sensitive.
- Phase 3 adds pooled and equal-participant correlations, explicit episode
  reconstruction, cautious waking-date matching, and anomaly candidates. It
  does not relabel stored sleep codes or claim actual sleep duration.

## Gaps and scientific limits

- No sleep episode reconstruction or sleep/activity linkage exists in the
  notebook. Phase 3 must retain neutral value-category names (`1`, `2`, `3`);
  this repository has no trustworthy mapping to sleep stages or states.
- An overnight episode should be linked to its waking date only after inspecting
  actual start/end times, crossing-midnight behavior, daytime sessions,
  duplicate waking dates, and overlaps.
- Recorded sleep-minute count is not necessarily actual time asleep or sleep
  efficiency.
- Daily rows repeat participants. Pooled correlations are descriptive; report
  participant counts and also calculate participant-level aggregates where
  appropriate. Do not treat 457 days as 457 independent people.
- The source is historical and field units are not independently verified.
- No plotting packages are available in the current interpreter. Figures will
  use reproducible standard-library SVG and no package installation.
