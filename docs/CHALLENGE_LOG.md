# Challenge log

## C-001 — Audit large raw CSVs under limited memory

- Phase/task: P1 raw-data inventory
- Observable constraint: Raw files total 271,592,676 bytes; only about 436 MiB
  memory was available at the initial environment check.
- Root cause: Loading multiple minute-level or heart-rate tables together
  would needlessly increase peak memory.
- Solution: Stream each source CSV using Python's standard-library `csv`
  reader and fixed-size blocks for SHA-256.
- Verification: `python src/data_audit.py` scanned 7,206,142 rows and passed
  header, row-width, key-completeness, and date-parsing checks.
- Remaining limitation: Audit output infers lexical types and does not confirm
  units or the validity of device measurements.
- Presentation takeaway: The raw-data audit was designed around the actual
  memory constraint rather than loading the minute-level files wholesale.
