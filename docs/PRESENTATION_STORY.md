# Presentation story

## P1 — Establish what the tracker archive can support

- Problem: The source archive has daily, hourly, minute, sleep, heart-rate,
  and weight files with different observation grains and participant coverage.
- Method: A standard-library streaming inventory counted rows, schema,
  missing values, dates, participants, composite-key repeats, and file hashes.
- Observed result: The 11 files contain 7,206,142 rows. Daily activity covers
  35 participants; sleep covers 23 and has 525 repeated keys; weight has
  31 missing `Fat` entries among 33 rows.
- Data challenge found: For participant `4020332650`, the activity-distance
  component sum differs from `TotalDistance` on 29 of 32 days (maximum
  absolute difference 7.41); the total and tracker distance fields agree.
- Why this matters: Later merges and methods must state their grain and handle
  coverage differences rather than treating all data as one complete panel.
- Caveat: The data are historical, field units are not independently verified,
  and these counts do not establish population representativeness.
- Evidence: P1-DATA-AUDIT.
