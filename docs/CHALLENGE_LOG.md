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

## C-002 — Daily distance fields do not reconcile consistently

- Phase/task: P1 daily-data quality review
- Observable symptom: The component-distance sum differs from `TotalDistance`
  by more than 0.01 on 104 of 457 participant-days. For participant
  `4020332650`, this occurs on 29 of 32 days; the maximum absolute difference
  is 7.41 on 2016-03-20.
- Root cause: Unknown; source units and field-generation rules are not
  documented in the repository.
- Attempted fix: Compared `TotalDistance` with both `TrackerDistance` and the
  sum of the four activity-distance fields. The two comparisons do not agree
  on which rows differ.
- Implemented solution: Preserve the source values and record separate
  discrepancy counts; do not select a “correct” field or exclude observations.
- Verification: `python src/data_audit.py`; actual counts are saved in
  `reports/evidence/P1/run_manifest.json`.
- Remaining limitation: These are descriptive mismatch flags, not proof of
  which measurement is wrong.
- Presentation takeaway: Field-level consistency checks exposed a measurable
  data-quality question that downstream analysis must not silently normalize.

## C-003 — Prove multi-file row alignment before merging

- Phase/task: P2 hourly and minute activity integration
- Observable constraint: The notebook merges several full participant-hour
  and participant-minute tables; equal lengths alone cannot ensure matching
  keys or order, and available RAM is limited.
- Root cause: A misordered row-wise merge would assign measurements to the
  wrong participant-time without necessarily changing row count.
- Solution: Stream key tuples from each source in lockstep, compare every key
  and its order, and count duplicates before permitting a row-wise merge.
- Verification: All 24,084 hourly keys and 1,445,040 minute keys matched in
  order across their source files; both reference keys were unique. The
  generated hourly and minute outputs also match their processed references.
  Negative tests reject missing keys, duplicate join keys, unequal row counts,
  and changed key order.
- Remaining limitation: The verification covers the committed files; future
  input revisions must rerun the alignment check.
- Presentation takeaway: A cheap streaming key proof made a low-memory join
  defensible rather than relying on matching row counts.

## C-004 — Sleep logs do not form a complete matched panel

- Phase/task: P3 sleep episode reconstruction and waking-date alignment
- Observable symptom: Only 161 daily activity rows have a unique eligible
  overnight log; 17 activity dates have multiple candidate sessions, and none
  of the matched activity days meet the 1,440-minute complete-day rule.
- Root cause: The sleep file has 556 participant-log groups, varying session
  times, and repeated candidate logs on some waking dates; activity coverage
  is incomplete across the same dates.
- Solution: Keep sleep codes neutral; screen overnight timing and intervals;
  exclude ambiguous dates; match the episode end date; preserve unmatched sleep
  as missing and maintain one row per activity participant-day.
- Verification: 359 individually eligible episodes, 161 matched days across
  18 participants, 17 ambiguous activity dates, 198 eligible episodes without
  an activity row, and 457 unique output activity rows.
- Remaining limitation: All 161 matched days are incomplete, so the
  complete-day sleep/activity sensitivity has no observations. Recorded log
  rows are not validated actual sleep duration.
- Presentation takeaway: The join is cardinality-safe, but its strict coverage
  leaves no matched complete-day sample for a sleep sensitivity comparison.

## C-005 — Build interpretable figures without a plotting dependency

- Phase/task: P3 reproducible visualization
- Observable constraint: The available Python environment has no Matplotlib,
  Seaborn, NumPy, pandas, or SciPy.
- Root cause: A package-based chart pipeline would require installation and
  would no longer use only already-verified local resources.
- Solution: The initial Phase 3 analysis generated eight accessible,
  deterministic SVG figures using Python standard-library string and
  XML-compatible output. The later time-accounting review added a ninth figure
  for combined activity and recorded sleep-row minutes by date.
- Verification: The initial figure index recorded eight figures; the final
  index records nine. Tests parse all SVGs and compare the ninth figure's
  plotted date/value points with the computed time-accounting CSV.
- Remaining limitation: Charts are static and need maintenance alongside the
  analysis code.
- Presentation takeaway: The EDA figures can be regenerated locally without
  paid tools or external services.

## C-006 — Determine whether activity and sleep rows complement each other

- Phase/task: P3 analytical review
- Observable symptom: Every one of the 161 unique sleep-matched waking dates is
  incomplete under Phase 2, while an independent arithmetic check suggested
  activity minutes plus recorded sleep rows may approach 1,440.
- Root cause: Unverified. The repository does not define whether activity and
  sleep fields cover the same or separate intervals, or whether their
  timestamps overlap.
- Investigation: Sum all four recorded activity-minute fields, verify that
  total against the Phase 2 stored total, then add minute rows from only a
  unique eligible sleep log. Preserve the original 1,440-minute completeness
  flag and compare all dates with April 12 and April 11–12 sensitivity windows.
- Evidence: 45/161 sums equal 1,440; 74/161 are within 15 minutes; 91/161
  within 30; 110/161 within 60. April 12 has seven matched dates, each 607–833
  combined minutes. Excluding April 12 gives n=154 and mean difference −25.96;
  excluding April 11–12 gives n=143 and mean difference −21.72.
- Resolution: Arithmetic supports a complementary-accounting possibility for
  many rows, not verified 24-hour coverage. Sleep counts remain recorded-row
  counts; ambiguous or unmatched sleep is not assigned a duration.
- Remaining limitation: Measurement semantics, interval overlap, device wear,
  and the meaning of missing activity minutes are unverified. Sensitivity
  exclusions do not replace the all-date primary analysis.
- Presentation takeaway: Many activity-plus-sleep totals approach a day, but
  the sum is a diagnostic clue—not evidence of full coverage or non-wear.
- Artifacts: `reports/evidence/P3/time_accounting_metrics.json`;
  `reports/generated/eda/tables/time_accounting*.csv`.

## C-007 — Integrate historical clustering without losing merged Phase 1–3 work

- Phase/task: P4 safe branch integration
- Observable constraint: The existing
  `phase-4-activity-clustering` branch is based on the original project commit
  `201268635a04a7fee03a00cb7030e8106f6d13ec`. Verified current `main` has 17
  commits not on that branch; its single clustering commit is not in `main`.
- Root cause: The old work predates the Phase 1–3 merge chain.
- Attempted fix: Do not merge or reset the historical branch.
- Implemented solution: Create `phase-4-validated-clustering` from the verified
  Phase 3 merge `77abf8354db99cb48e84ff931e335e2ec2f4c73a`; inspect the
  historical source and carry forward its feature, candidate-K, DBSCAN, PCA,
  and complete-day analysis design, without importing its dependency file.
- Verification: The new branch starts at the current `main` commit. The
  historical branch remains at
  `cdf5c33502cbe08a4885a9f4bd7de4cad19c24ad`.
- Remaining limitation: Historical and current analysis code use different
  numerical implementations; comparisons are evidence, not a claim of
  bit-for-bit code reuse.
- Presentation takeaway: Reuse the prior research questions while keeping the
  merged audit, preprocessing, and EDA history intact.
- Artifacts: `reports/evidence/P4/run_manifest.json`.

## C-008 — Scientific Python packages are unavailable at verified zero cost

- Phase/task: P4 reproducible algorithms
- Observable constraint: NumPy, SciPy, scikit-learn, pandas, Matplotlib, and
  Seaborn are not installed; no package-install cost was verified.
- Root cause: The historical Phase 4 script imports these packages and its
  `requirements.txt` includes a broader analysis environment.
- Implemented solution: Install nothing. Use small standard-library
  implementations of K-Means, DBSCAN, partition metrics, PCA, CSV output, and
  SVG figures.
- Verification: Synthetic expected-output tests cover clustering, noise,
  metrics, PCA variance and orthogonality. Recomputed all-days and complete-day
  K-Means sizes, ARI, DBSCAN reference settings, and PCA variance agree with
  the documented historical values within the reported precision.
- Remaining limitation: Initialization, tie handling, and numerical details
  differ from scikit-learn; this is disclosed rather than presented as an
  exact library replacement.
- Presentation takeaway: The analysis remains reproducible locally without
  assuming a paid or unverified dependency.
- Artifacts: `src/clustering_math.py`, `tests/test_activity_clustering.py`,
  and `reports/evidence/P4/`.

## C-009 — A two-person group is too small for a strong behavioral claim

- Phase/task: P4 K-Means interpretation and stability
- Observable symptom: The all-days silhouette rule selects K=3 with cluster
  sizes 17, 16, and 2; the two-person group has the highest mean recorded steps.
- Root cause: The sample has only 35 participants, and recorded-day coverage
  differs by person.
- Investigation: Refit complete-day and >=10-day cohorts; rerun five seeds;
  exclude the two highest mean-step participants as an explicitly labeled
  sensitivity.
- Resolution: Five 20-start reruns select K=3 with ARI 1.000. The complete-day
  K=2 partition has ARI 0.537 on 24 shared participants. Excluding the two
  highest-step participants yields K=2 for the remaining 33, with ARI 1.000
  on those shared participants; the two-member group disappears.
- Remaining limitation: ARI is partition agreement, not prediction accuracy;
  clusters do not support lifestyle, health, or fitness labels.
- Presentation takeaway: Report the two-person group as a sensitive
  exploratory pattern, not a confirmed subgroup.
- Artifacts: `reports/evidence/P4/stability_metrics.json`;
  `reports/generated/activity_clustering/tables/cohort_sensitivity.csv`.

## C-010 — Small-sample DBSCAN depends on the radius and noise threshold

- Phase/task: P4 density-based sensitivity
- Observable symptom: Some parameter settings produce multiple small groups;
  nearby settings produce one group or classify many people as noise.
- Root cause: Density connectivity is sensitive to eps and min_samples in a
  four-dimensional sample of 35 participants.
- Implemented solution: Evaluate the full 5-by-3 historical parameter grid;
  keep noise labeled `-1` and calculate quality scores only on assigned points
  when at least two clusters are mathematically valid.
- Verification: `eps=1.0`, `min_samples=3` reproduces 3 groups and 8 noise
  points. Across the grid, many settings produce one group or substantial
  noise.
- Remaining limitation: Scores exclude noise and therefore describe a smaller
  population; a favorable score is not evidence the density model is superior.
- Presentation takeaway: DBSCAN is a parameter-sensitive comparison, not a
  forced match to K-Means.
- Artifacts: `reports/evidence/P4/dbscan_evaluation.json`;
  `reports/generated/activity_clustering/tables/dbscan_scores.csv`.

## C-011 — Mixed chart scales can hide model trade-offs

- Phase/task: P4 model diagnostics and PCA figures
- Observable symptom: K-Means scores have different units and preferred
  directions; combining them in one small graphic makes comparisons easy to
  misread. Explained and cumulative PCA variance are also distinct quantities.
- Root cause: The candidate scores use unrelated scales, and a combined chart
  can visually imply a shared axis or direct magnitude comparison.
- Implemented solution: Publish one zero-based column chart for each K-Means
  metric, separate PCA explained and cumulative variance, and use explicit
  diverging or sequential keys for feature/profile heatmaps.
- Verification: The pipeline regenerates exactly 12 indexed SVGs, parses each
  as XML, checks its title, sample and limitation text, and rejects
  participant-ID labels. The full 59-test suite passes.
- Remaining limitation: Static vector charts do not make the underlying
  sample or exploratory results more representative.
- Presentation takeaway: Read each metric using its own scale and direction;
  do not treat a single score as definitive model validation.
- Artifacts: `reports/evidence/P4/figures_index.json`,
  `reports/evidence/P4/run_manifest.json`, and
  `reports/generated/activity_clustering/figures/`.

## C-012 — Some association pairs would repeat their own definitions

- Phase/task: P5 transaction construction and Apriori
- Observable constraint: Active-minute share uses total active minutes over
  recorded minutes; very-active minutes are part of the numerator, and the
  Phase 2 coverage category is determined from recorded minutes.
- Root cause: Directly combining these categories can reflect a shared
  numerator or denominator rather than an independent co-occurrence.
- Investigation: Defined six mutually exclusive item families, reviewed their
  calculation dependencies, and tested family and subset pruning on synthetic
  transactions.
- Resolution: Mine no same-family category pairs; exclude active-share with
  very-active minutes and active-share with coverage status. Limit itemsets to
  three items.
- Verification: The complete 457-day transaction map has six distinct
  families per day; synthetic tests confirm incompatible pairs and
  unsupported-subset candidates are pruned.
- Remaining limitation: Other categories can still be correlated because they
  describe the same recorded day.
- Presentation takeaway: Read mined associations as co-occurrence patterns,
  not independent behavioral mechanisms.
- Artifacts: `src/association_rules.py`,
  `reports/evidence/P5/association_metrics.json`,
  `tests/test_phase5_associations.py`.

## C-013 — Unequal participant-day counts can change pooled confidence

- Phase/task: P5 participant-balanced association sensitivity
- Observable symptom: An eligible pooled rule's confidence is 86.0%, while the
  equal-participant mean confidence is 57.1%.
- Root cause: Daily pooling weights people according to their number of
  antecedent observations and conditional rule occurrences.
- Investigation: Calculated each participant's conditional confidence among
  people with at least one antecedent day; also computed equal-participant
  prevalence for frequent itemsets.
- Resolution: Export pooled and participant-balanced values together, and
  compare rules across support, confidence, lift, participant-count, and
  complete-day sensitivities.
- Verification: The cited rule has 14 participants with antecedent days; the
  all-days baseline has 89 threshold-qualified rules, compared with 108 in the
  complete-day subset.
- Remaining limitation: Participant-level summaries are still based on a
  small historical sample and do not establish future predictive performance.
- Presentation takeaway: Do not treat pooled day-level confidence as
  equal-person confidence.
- Artifacts: `reports/generated/associations/participant_balanced_sensitivity.csv`,
  `reports/generated/associations/threshold_sensitivity.csv`.

## C-014 — Historical distance flags count different tolerance rules

- Phase/task: P5 reuse of Phase 1/2 data-quality flags
- Observable symptom: The strict absolute-difference screen marks 104 days;
  the Phase 2 `distance_discrepancy` flag marks 65.
- Root cause: Phase 1 applies a plain absolute threshold, while the committed
  Phase 2 flag reproduces the existing NumPy-isclose-equivalent rule.
- Investigation: Recomputed the strict component-sum comparison from the
  processed fields and separately counted the stored Phase 2 flag.
- Resolution: Preserve both flags and their definitions in separate columns
  and detector sets.
- Verification: All 65 Phase 2 days occur in the strict 104; 39 are strict-only.
- Remaining limitation: Neither comparison establishes which distance field
  is correct.
- Presentation takeaway: Keep the two counts separate when discussing
  distance inconsistencies.
- Artifacts: `reports/evidence/P5/anomaly_metrics.json`,
  `reports/generated/anomalies/candidate_registry.csv`.

## C-015 — Different anomaly screens flag overlapping records

- Phase/task: P5 anomaly comparison and case review
- Observable symptom: Ten daily candidate sets have different sizes and
  substantial intersections; their counts cannot be summed.
- Root cause: Global tails, within-person deviations, multivariate neighbor
  distances, and existing quality flags answer different screening questions.
- Investigation: Calculated pairwise participant-day intersections and
  Jaccard values; retained the 140 Phase 3 daily candidates and 111 separate
  sleep-episode candidates.
- Resolution: Publish per-method counts, overlap tables, and a 457-row
  candidate registry; selected seven review examples without deleting rows
  or assigning causes.
- Verification: The union of daily flags contains 217 unique participant-days;
  every source day and all 61 zero-step rows remain in the registry.
- Remaining limitation: No candidate screen confirms an error, a device-wear
  failure, or a medical condition.
- Presentation takeaway: Treat flags as prompts for record review, not a
  verdict about the source.
- Artifacts: `reports/generated/anomalies/detector_counts.csv`,
  `reports/generated/anomalies/detector_overlaps.csv`,
  `reports/generated/anomalies/candidate_registry.csv`.

## C-016 — The last observed date affects candidate counts

- Phase/task: P5 date-boundary sensitivity
- Observable symptom: April 12, 2016 contributes 24 of the 457 participant-day
  rows; only three are complete, and median recorded time is 426 minutes.
- Root cause: The observation window ends mid-period; the boundary date is
  not a complete panel across participants.
- Investigation: Retained all dates for primary results, then excluded only
  April 12 and recalculated Phase 5 screens; Phase 3 flags were filtered rather
  than re-estimated.
- Resolution: Report the exclusion as sensitivity only and preserve the final
  date in the transaction and anomaly outputs.
- Verification: The sensitivity cohort has 433 days; Phase 3 candidates
  change from 140 to 127 and global IQR candidates from 36 to 21.
- Remaining limitation: The sensitivity cannot explain the difference or
  validate whether a missing value is device non-wear.
- Presentation takeaway: Keep the boundary date in the primary analysis and
  show its effect explicitly.
- Artifacts: `reports/generated/anomalies/date_boundary_sensitivity.csv`,
  `reports/evidence/P5/anomaly_metrics.json`.

## C-017 — Notebook conversions can hide expensive intermediate materialization

- Phase/task: Notebook conversion and clean-kernel validation
- Observable symptom: An initial Phase 2 notebook preview attempted to
  materialize a 1.4-million-row CSV merely to display two sample rows, causing
  the kernel to exit under the available memory limit.
- Root cause: A convenience list conversion read the entire file before
  slicing the first two records.
- Investigation: Executed each notebook in an isolated fresh kernel, traced
  the failed preview to the sample-display code, then replaced it with a
  two-row streaming read. A later Phase 6 smoke test also found a date-filter
  field mismatch that hid all date choices.
- Resolution: Keep high-volume output reads streaming, generate notebook
  figures from in-memory computed analysis results, and bind the time filter
  to the verified `activity_date` column.
- Verification: The six notebooks execute without cell errors; Phase 2
  reproduces all six processed references, and the Phase 6 date selector
  exposes its stored date choices.
- Remaining limitation: Clean-kernel success cannot validate measurement
  semantics or device wear; interactive widget behavior still depends on a
  Jupyter frontend with widget support.
- Presentation takeaway: Notebook output previews must be designed for data
  scale, and displayed results should be tied to the exact computed inputs.
- Artifacts: `notebooks/phases/02_Data_Preprocessing.ipynb`,
  `notebooks/phases/06_Interactive_Dashboard.ipynb`,
  `reports/evidence/notebook_conversion/`.

## C-018 — Make notebook outputs independently reviewable

- Phase/task: Final notebook correction and Phase 6 evidence browser
- Observable symptom: The initial conversion still tied several notebooks to
  the presence of `src/`, showed only three of eight Phase 5 figures, and
  exposed six Phase 6 panels with candidate/assignment counts that could be
  misread across scopes.
- Root cause: The first conversion prioritized wrapping the verified pipelines;
  it did not finish transferring all figure rendering or the Phase 6 cohort
  and candidate controls into the notebooks.
- Implemented solution: Use notebook-local code and notebook-specific hashes,
  generate and display all 9 Phase 3, 12 Phase 4, and 8 Phase 5 SVGs inline,
  and make Phase 6 filter stored records through eight panels. Cohort options
  update with the selected model, blank assignments are excluded, and flagged
  candidates are counted using the union field. Archive the original notebooks
  without changing their content.
- Verification: All six notebooks passed fresh-kernel execution from an
  isolated project tree without `src/`. Phase 1 matched 11 raw-file hashes and
  row counts; Phase 2 matched all six processed references; Phase 3 and Phase 4
  outputs matched 13/9 and 9/12 table/figure references; Phase 5 matched all
  21 CSV tables and produced eight parseable inline SVGs. Phase 6 interaction
  checks confirmed 217 flagged rows of 457, 35 all-days assignments, 24
  complete-day assignments, and 23 activity dates.
- Remaining limitation: Interactive controls require a widget-enabled Jupyter
  frontend. The dashboard filters stored analysis and does not refit models;
  the two-person Phase 4 group and all other findings remain exploratory.
- Presentation takeaway: Review the sample, cohort, and stored result behind
  each view; chart count or filter output does not make a small observational
  sample more representative.
- Artifacts: `reports/evidence/notebook_conversion/`,
  `notebooks/phases/`, and `tests/test_notebook_workflow.py`.

## C-019 — Keep notebook validation within local memory limits

- Phase/task: Final fresh-kernel notebook validation
- Observable symptom: A six-notebook run's Phase 2 kernel died during its
  minute-level uniqueness audit; Phase 6 output-widget smoke checks also
  stalled in a headless kernel.
- Root cause: Phase 2 retained millions of key digests in in-memory sets, and
  Phase 6 relied on output comms that do not complete reliably without a live
  notebook frontend.
- Investigation: The kernel reported `DeadKernelError` and the cgroup recorded
  an OOM kill. The Phase 2 validation path uses in-memory sets for both source
  alignment and generated-output uniqueness; the Phase 6 smoke test isolated
  the output-widget waits.
- Resolution: Move only temporary key digests to local disk-backed SQLite
  tables with bounded cache, and return panel markup through `widgets.HTML`
  values. Raw data, processed references, and analytical outputs are unchanged.
- Verification: The standalone Phase 2 fresh-kernel run completed with all six
  references matching; the Phase 6 eight-panel interaction smoke test passed.
  The final six-notebook and standard-suite results are recorded in the final
  correction report.
- Remaining limitation: Temporary SQLite checks add local disk I/O; actual
  interactive controls still require a widget-enabled Jupyter frontend.
- Presentation takeaway: Reproducibility checks should fit the same resource
  limits as the workflow and must fail closed if interrupted.
- Artifacts: `notebooks/phases/02_Data_Preprocessing.ipynb`,
  `notebooks/phases/06_Interactive_Dashboard.ipynb`,
  `reports/evidence/notebook_conversion/`.
