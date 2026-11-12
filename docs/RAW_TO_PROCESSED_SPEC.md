# Raw-to-processed transformation specification

Source reviewed: `notebooks/Data_preprocessing.ipynb`, its stored validation
outputs, all six committed processed CSVs, and the raw input headers. Notebook
outputs are historical; the new pipeline must regenerate and compare them.

| Output | Raw inputs | Grain / key | Transformation from notebook | Verified reference |
| --- | --- | --- | --- | --- |
| `daily_activity_clean.csv` | `dailyActivity_merged.csv` | Participant-day; `(id, activity_date)` | Normalize headers to snake case; keep `id` as string; parse `%m/%d/%Y`; sum four minute fields into `total_recorded_minutes`; `is_complete_day` iff total is 1,440; sum four distance components; `distance_discrepancy = not np.isclose(total_distance, component_distance_sum, atol=0.01)` using NumPy default `rtol=1e-5`. Keep every row, including zero-step days. | 457 × 19; 233 complete days; 65 discrepancy flags |
| `minute_sleep_clean.csv` | `minuteSleep_merged.csv` | Participant sleep-minute; `(id, log_id, date)` | Normalize headers; `id` string; parse `%m/%d/%Y %I:%M:%S %p`; remove duplicate keys, keep first; derive `calendar_date` from timestamp date. | 198,034 × 5; 525 repeated raw keys, all identical |
| `weight_clean.csv` | `weightLogInfo_merged.csv` | Participant weight log; `(id, log_id)` | Normalize headers; `id` and `log_id` strings; parse timestamp; drop `fat` (31/33 missing). Preserve other measurements and rows. | 33 × 7 |
| `hourly_activity_clean.csv` | `hourlyCalories_merged.csv`, `hourlyIntensities_merged.csv`, `hourlySteps_merged.csv` | Participant-hour; `(id, activity_hour)` | Normalize headers; `id` string; parse `%m/%d/%Y %I:%M:%S %p`; derive `date`; inner-join on `(id, activity_hour, date)` in calories-led column order. | 24,084 × 7; keys align in identical order across all three files |
| `minute_activity_clean.csv` | `minuteCaloriesNarrow_merged.csv`, `minuteIntensitiesNarrow_merged.csv`, `minuteMETsNarrow_merged.csv`, `minuteStepsNarrow_merged.csv` | Participant-minute; `(id, activity_minute)` | Normalize headers; `id` string; parse `%m/%d/%Y %I:%M:%S %p`; derive `date`; inner-join on `(id, activity_minute, date)` in calories-led column order. | 1,445,040 × 7; keys align in identical order across all four files |
| `heartrate_seconds_clean.csv` | `heartrate_seconds_merged.csv` | Participant timestamp; `(id, time)` | Normalize headers; `id` string; parse `%m/%d/%Y %I:%M:%S %p`; rename `value` to `heart_rate`; derive date and integer hour. | 1,154,681 × 5 |

## Reference column order

- Daily: `id, activity_date, total_steps, total_distance, tracker_distance,
  logged_activities_distance, very_active_distance, moderately_active_distance,
  light_active_distance, sedentary_active_distance, very_active_minutes,
  fairly_active_minutes, lightly_active_minutes, sedentary_minutes, calories,
  total_recorded_minutes, is_complete_day, component_distance_sum,
  distance_discrepancy`
- Sleep: `id, date, value, log_id, calendar_date`
- Weight: `id, date, weight_kg, weight_pounds, bmi, is_manual_report, log_id`
- Hourly: `id, activity_hour, calories, date, total_intensity,
  average_intensity, step_total`
- Minute: `id, activity_minute, calories, date, intensity, mets, steps`
- Heart rate: `id, time, heart_rate, date, hour`

## Validation and serialization policy

- Paths resolve from the repository location, not `Path.cwd().parent`.
- Raw and reference files are read-only inputs. Regenerated outputs go under
  `reports/generated/preprocessed/`, never over `data/processed/`.
- Dates use explicit formats and are written as ISO date/timestamp text. IDs
  remain strings. Missing keys, invalid dates, unexpected headers, malformed
  rows, key/order mismatches, and join-cardinality surprises are errors.
- Compare every generated row to its reference sequentially. Compare
  identifiers, categories, and dates exactly; compare numeric values with an
  explicit small tolerance and record mismatch counts/examples.
- The notebook's 65 distance flags use NumPy's `isclose` relation. The P1
  104-row count uses the stricter plain `abs(diff) > 0.01` screen; they answer
  different tolerance definitions and must not be conflated.
- The sleep deduplication choice is supported by the raw scan: all 525
  repeated-key rows are identical, with zero conflicting duplicate groups.
- Exact physical units are not established by the repository; do not infer
  additional scientific meaning from column labels.

## Phase 2 run result

`python src/preprocess.py` passed on implementation commit
`c9c5f3e4eae89ab460ef360a9300d7705554c4d5`. All six generated outputs matched
the committed references with zero mismatched rows. The sleep transformation
removed 525 identical duplicate occurrences; hourly and minute key-order proofs
passed. Per-dataset metrics, alignment proofs, and the run manifest are stored
in `reports/evidence/P2/`.
