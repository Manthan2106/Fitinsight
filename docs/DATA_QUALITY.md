# Raw-data quality and feasibility

## Verified inventory

The source archive was streamed without modifying it. The audit command is
`python src/data_audit.py`; machine-readable results and SHA-256 hashes are in
`reports/evidence/P1/`. Counts below are computed from the current `main`
source tree, not copied from the earlier project snapshot.
The supplied project brief identifies the source archive as
`mturkfitbit_export_3.12.16-4.11.16.zip`. That archive, a source license, and
an upstream provenance record are not present in this repository, so those
items have not been independently verified.

| File | Rows | Participants | Observed time range | Missing values | Duplicate key rows |
| --- | ---: | ---: | --- | ---: | ---: |
| `dailyActivity_merged.csv` | 457 | 35 | 2016-03-12 to 2016-04-12 | 0 | 0 |
| `heartrate_seconds_merged.csv` | 1,154,681 | 14 | 2016-03-29 00:00:05 to 2016-04-12 11:03:15 | 0 | 0 |
| `hourlyCalories_merged.csv` | 24,084 | 34 | 2016-03-12 00:00 to 2016-04-12 10:00 | 0 | 0 |
| `hourlyIntensities_merged.csv` | 24,084 | 34 | 2016-03-12 00:00 to 2016-04-12 10:00 | 0 | 0 |
| `hourlySteps_merged.csv` | 24,084 | 34 | 2016-03-12 00:00 to 2016-04-12 10:00 | 0 | 0 |
| `minuteCaloriesNarrow_merged.csv` | 1,445,040 | 34 | 2016-03-12 00:00 to 2016-04-12 10:59 | 0 | 0 |
| `minuteIntensitiesNarrow_merged.csv` | 1,445,040 | 34 | 2016-03-12 00:00 to 2016-04-12 10:59 | 0 | 0 |
| `minuteMETsNarrow_merged.csv` | 1,445,040 | 34 | 2016-03-12 00:00 to 2016-04-12 10:59 | 0 | 0 |
| `minuteSleep_merged.csv` | 198,559 | 23 | 2016-03-11 21:19:30 to 2016-04-12 08:35 | 0 | 525 |
| `minuteStepsNarrow_merged.csv` | 1,445,040 | 34 | 2016-03-12 00:00 to 2016-04-12 10:59 | 0 | 0 |
| `weightLogInfo_merged.csv` | 33 | 11 | 2016-03-30 23:59:59 to 2016-04-12 23:59:59 | 31 | 0 |

Across all 11 files: 7,206,142 rows and 271,592,676 bytes. In the daily table,
61 of 457 observations have zero steps, across 14 participants. They remain
in the source and should be flagged for investigation, not silently removed.
Of those 61 rows, 56 also record positive calories and 3 have positive active
minutes. These combinations are flags for review, not proof of an invalid
record.
The sleep key repeats correspond to 525 rows; retain the source and make any
deduplication a documented preprocessing choice.

The audit compares distance values at an absolute difference threshold of
0.01 in the stored units. `TotalDistance` differs from `TrackerDistance` on
16/457 participant-days. The sum of `VeryActiveDistance`,
`ModeratelyActiveDistance`, `LightActiveDistance`, and
`SedentaryActiveDistance` differs from `TotalDistance` on 104/457 days. For
participant `4020332650`, the latter comparison differs on 29/32 days; 11
differences exceed 1 stored unit, with a maximum absolute difference of 7.41
on 2016-03-20. `TotalDistance` and `TrackerDistance` match within the stated
threshold for this participant. These comparisons identify inconsistencies;
they do not establish which field is correct.

## Feasibility and caveats

- Activity coverage varies: daily activity has 35 participants; hourly and
  narrow-minute activity have 34; heart-rate data have 14; sleep has 23; and
  weight logs have 11. Analyses and joins must report matched coverage.
- Weight `Fat` is missing in 31/33 rows. This dataset is too sparse for broad
  claims.
- The observation period is in 2016. The archive does not establish current
  behavior or population representativeness.
- No `sleepDay_merged.csv` is present. Sleep episodes need explicit
  reconstruction and calendar/next-day alignment before joining.
- This audit verifies parseability, row width, populated key fields, duplicate
  composite keys, counts, and date ranges. It does not validate physical
  plausibility, official units, or whether missing time means inactivity.
- Reported distance inconsistencies and suspicious active-minute combinations
  have been quantified above and remain questions for downstream review; the
  audit does not alter or reject those observations.

## Method note

The audit uses Python's standard library, streams one CSV at a time, and stores
16-byte BLAKE2b digests of composite keys. A digest collision is theoretically
possible and could make distinct keys look like a duplicate; at these dataset
sizes the risk is extremely small but nonzero. The audit is a memory-conscious
key screen, not a mathematical proof of uniqueness. Type labels are lexical
(`integer`, `number`, `boolean`, `string`, `datetime`, `mixed`, or `empty`), not
a replacement for an authoritative data specification. There are no package
installations or external services in this audit.
