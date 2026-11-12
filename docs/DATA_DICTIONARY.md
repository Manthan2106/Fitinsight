# Raw-data dictionary

This inventory reflects the headers and values in the committed raw CSVs.
`reports/evidence/P1/column_inventory.csv` records the observed lexical type
and missing-value count for every field. It is not an official Fitbit schema:
units, encoding definitions, and device-specific semantics were not supplied
with these files and are not inferred here.

| File | Grain and key checked | Fields / cautious description |
| --- | --- | --- |
| `dailyActivity_merged.csv` | Participant-day; `(Id, ActivityDate)` | `Id`; `ActivityDate`; `TotalSteps`; distance fields `TotalDistance`, `TrackerDistance`, `LoggedActivitiesDistance`, `VeryActiveDistance`, `ModeratelyActiveDistance`, `LightActiveDistance`, `SedentaryActiveDistance`; minute fields `VeryActiveMinutes`, `FairlyActiveMinutes`, `LightlyActiveMinutes`, `SedentaryMinutes`; `Calories`. Exact distance and calorie units are not independently verified. |
| `heartrate_seconds_merged.csv` | Participant-timestamp; `(Id, Time)` | `Id`; `Time`; `Value` (heart-rate measurement; unit not verified from a source specification). |
| `hourlyCalories_merged.csv` | Participant-hour; `(Id, ActivityHour)` | `Id`; `ActivityHour`; `Calories` (unit not independently verified). |
| `hourlyIntensities_merged.csv` | Participant-hour; `(Id, ActivityHour)` | `Id`; `ActivityHour`; `TotalIntensity`; `AverageIntensity` (scale/definition not independently verified). |
| `hourlySteps_merged.csv` | Participant-hour; `(Id, ActivityHour)` | `Id`; `ActivityHour`; `StepTotal`. |
| `minuteCaloriesNarrow_merged.csv` | Participant-minute; `(Id, ActivityMinute)` | `Id`; `ActivityMinute`; `Calories` (unit not independently verified). |
| `minuteIntensitiesNarrow_merged.csv` | Participant-minute; `(Id, ActivityMinute)` | `Id`; `ActivityMinute`; `Intensity` (scale/definition not independently verified). |
| `minuteMETsNarrow_merged.csv` | Participant-minute; `(Id, ActivityMinute)` | `Id`; `ActivityMinute`; `METs` (field label retained; methodology/units not independently verified). |
| `minuteSleep_merged.csv` | Participant sleep-minute entry; `(Id, date, logId)` checked | `Id`; `date`; `value` (encoding not independently verified); `logId` (source session/log identifier). |
| `minuteStepsNarrow_merged.csv` | Participant-minute; `(Id, ActivityMinute)` | `Id`; `ActivityMinute`; `Steps`. |
| `weightLogInfo_merged.csv` | Participant weight-log record; `(Id, LogId)` | `Id`; `Date`; `WeightKg`; `WeightPounds`; `Fat`; `BMI`; `IsManualReport`; `LogId`. `Fat` is mostly missing; the data do not support broad health claims. |

## Cross-file handling

- Preserve participant identifiers as strings in analytical code, even though
  the raw CSV tokens are numeric-looking.
- Daily rows, hours, minutes, sleep entries, heart-rate timestamps, and weight
  logs are different grains. Aggregate deliberately and validate join
  cardinality before combining them.
- `minuteSleep_merged.csv` is present; `sleepDay_merged.csv` is not in this
  archive. Do not assume daily sleep summaries exist.
- `data/processed/` contains six existing outputs; their provenance and exact
  transformations are to be verified in P2.
