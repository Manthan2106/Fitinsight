# Phase tracker

| Phase | Status | Deliverables | Acceptance test | Evidence | Branch / commit | Next dependency |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | DONE | Current repo baseline and safe local workspace | Live heads, files, PRs/issues, and runtime recorded | `docs/AGENT_CONTEXT.md` | `main` / `2012686` | P1 |
| P1 | REVIEW | Streaming raw-data audit, dictionary, quality memo, logs, README | Audit all 11 files; tests and inventory artifacts exist; docs explain provenance and caveats | `reports/evidence/P1/`; 7 unit tests pass | `phase-1-foundation` / PR #1 | Repository review |
| P2 | NOT_STARTED | Reproducible preprocessing and feature contract | Rebuild exports and validate schema, counts, joins, tests | Not started | Not started | P1 |
| P3 | NOT_STARTED | Activity and coverage-aware sleep EDA | Reproducible findings, matched coverage, saved figures | Not started | Not started | P2 |
| P4 | NOT_STARTED | Validated K-Means, DBSCAN, PCA integration | Tests, actual outputs, sensitivity and cohort evidence | Existing unmerged branch needs review | `phase-4-activity-clustering` / `cdf5c33` | P2, P3 |
| P5 | NOT_STARTED | Association rules and unusual-observation review | Reproducible thresholds, rules or documented absence, anomaly cases | Not started | Not started | P2, P3 |
| P6 | NOT_STARTED | Lightweight Streamlit dashboard | Six analytical areas use validated artifacts and correct filters | Not started | Not started | P2–P5 |
| P7 | NOT_STARTED | Final report, end-to-end verification, presentation outline | Clean-run commands and evidence-linked package | Not started | Not started | P1–P6 |
