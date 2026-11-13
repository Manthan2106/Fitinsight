# Final notebook correction report (historical PR #7 snapshot)

**Date:** 2026-11-13 · **Branch:** `phase-notebook-final-corrections` · **Base:** verified `main` at `b43f0530bab8944b331544cef7dd100b7f5ee87c`

This report records PR #7's review-time state. PR #7 later merged into `main`
at `4ddd796ed60e275b057ce11267f986d5859987dd`. The subsequent notebook polish
and current verification are recorded in
`final_notebook_polish_report.md`.

## Outcome

The six phase notebooks are self-contained and use their own implementation
cells rather than importing or launching `src/`. Phases 3–5 display every
reviewed figure inline: 9, 12, and 8 SVGs, respectively. Phase 6 provides eight
interactive panels over saved evidence and does not refit models. The three
original notebooks were archived byte-for-byte; raw data, processed
references, analysis scripts, generated analysis results, and the historical
Phase 4 branch were preserved. `src/.gitkeep` was removed; `app/.gitkeep`
remains.

## Phase evidence

- **Phase 1:** all 11 raw CSVs, 7,206,142 rows, hashes and row counts matched.
- **Phase 2:** all six generated outputs matched the committed references.
  The final notebook's large source-alignment and output-key uniqueness
  checks use temporary disk-backed SQLite tables with a bounded cache, rather
  than retaining millions of key digests in memory.
- **Phase 3:** 13 analysis CSV tables and nine inline figures. The time
  accounting remains a descriptive diagnostic, not proof of a complete
  24-hour day: 45 of 161 matched days sum to exactly 1,440 minutes; 91 are
  within 30 minutes; the median gap is zero and the mean is −58.48 minutes.
  The original Phase 2 completeness flags were not changed.
- **Phase 4:** nine analysis CSV tables and 12 inline figures. The two-person
  cluster remains too small for a stable profile and is explicitly described
  as exploratory.
- **Phase 5:** eight association tables, 13 anomaly tables, and eight inline
  figures computed from notebook results.
- **Phase 6:** eight panels. The saved evidence and interaction checks show
  217 flagged days out of 457, 35 all-days assignments versus 24 complete-day
  assignments, and 23 activity dates. The notebook filters existing outputs
  rather than refitting models.

## Verification

- `python -m unittest discover -s tests -v`: **92 tests**, 91 passed, one
  intentionally skipped. The skip is the longer fresh-kernel workflow, which
  is opt-in via `FITINSIGHT_RUN_NOTEBOOK_KERNELS=1`.
- A complete earlier isolated run passed all three notebook-workflow tests,
  executing all six notebooks without `src/`. After the final resource/UI
  refinements, Phase 2 and Phase 6 each passed a separate isolated fresh-kernel
  run, and their latest proof outputs were saved. Static syntax,
  self-containment, inline-figure, and stored-output checks pass.
- One redundant combined rerun after the final refinements was interrupted by
  a workspace restart during Phase 1's full raw-file scan. It did not complete
  and is not counted as a successful run.
- `git diff --check` and `git diff --cached --check` pass. Archived notebook
  hashes match their original Git versions. No paid API, hosted compute,
  deployment, or package installation was used.

## Review status

The review-only [PR #7](https://github.com/Manthan2106/Fitinsight/pull/7) is
open against `main` and remains unmerged. Its latest remote head and base were
verified after the final documentation update. Do not merge automatically or
start Phase 7.
