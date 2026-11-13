# Final notebook polish verification

**Date:** 2026-11-13 · **Branch:** `phase-notebook-final-polish` · **Base:**
verified `main` at `4ddd796ed60e275b057ce11267f986d5859987dd` · **Implementation
commit:** `82b6bee1bf27eaeaed23025787cd406e8bba1d61`

## Outcome

The six phase notebooks now place Phase 3–5 figures next to the analysis
proofs that generate them. Existing saved SVG payloads were moved by title
without changing their bytes. Phase 5 sorts a chart-only copy of the kNN
summary, so presentation order no longer changes the reference CSV's row
order. Scratch outputs are created outside the checkout, removed only after
all parity and figure checks pass, and retained on failure for diagnosis.

The Phase 6 PCA plot always shows all eligible participants in the selected
cohort. Choosing a participant changes its highlight only; it does not zoom
out or remove the other points.

## Verified results

| Notebook | Fresh-kernel result |
| --- | --- |
| Phase 1 — data audit | All 11 raw CSVs and 7,206,142 rows matched saved SHA-256 hashes and row counts. |
| Phase 2 — preprocessing | All six generated processed outputs matched committed references; high-volume key checks used temporary disk-backed SQLite tables. |
| Phase 3 — exploratory analysis | 13 analysis CSVs and nine SVG figures matched. Of 161 matched days, 45 sums equal 1,440 minutes, 91 are within 30 minutes, and the mean gap is −58.48 minutes. These remain descriptive checks, not proof of complete 24-hour coverage. |
| Phase 4 — clustering and PCA | Nine analysis CSVs and 12 SVG figures matched. The two-person cluster remains exploratory and unstable when those two participants are excluded. |
| Phase 5 — associations and anomalies | Eight association CSVs, 13 anomaly CSVs, and eight SVG figures matched exactly; all candidate rows and separate sleep-episode grain were retained. |
| Phase 6 — interactive notebook | Eight panels passed interaction smoke tests. The PCA view retains 35 all-days or 24 complete-days points while highlighting a selection. |

## Checks

- The isolated fresh-kernel workflow executed all six notebooks without `src/`;
  all five workflow tests passed. Its same-volume hard-link staging covered
  603,575,668 logical bytes, and tracked notebook hashes were unchanged.
- `python -m unittest discover -s tests -v`: **94 tests**, 93 passed, one
  intentionally skipped opt-in fresh-kernel test.
- `git diff --check`, notebook JSON/schema validation, and AST parsing of every
  notebook code cell passed. Existing Phase 3–5 SVG payload SHA-256 hashes by
  title are unchanged after relocation.
- Only the six phase notebooks, notebook workflow tests, and project records
  changed. Raw datasets, processed references, analytical source scripts,
  generated reference results, archived original notebook contents, and the
  separate historical Phase 4 branch remain unchanged.
- No package was installed; no paid API, hosted compute, deployment, automatic
  merge, or Phase 7 work was used.

## Review status

[PR #8](https://github.com/Manthan2106/Fitinsight/pull/8) is open against
`main` for review and remains unmerged.
