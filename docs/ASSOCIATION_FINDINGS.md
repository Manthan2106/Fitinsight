# Phase 5 association-rule findings

## Scope and reproduction

Run `python src/phase5_analysis.py` from the repository root after the Phase 2
and Phase 3 generated prerequisites exist. The association stage reads
`data/processed/daily_activity_clean.csv`, creates one transaction for each of
457 participant-days from 35 participants, and writes tables to
`reports/generated/associations/`. The input file and its 61 zero-step rows are
retained. Transaction and participant/date mappings are included in the output
for reproducibility.

The implementation uses the Python standard library only. It does not install
packages or call external analysis services.

## Transaction definitions

Every daily transaction has six items, one from each mutually exclusive family:

| Family | Categories |
| --- | --- |
| Recorded steps | Zero; 1–4,999; 5,000–9,999; 10,000 or more |
| Active-minute share | `<0.10`; `0.10–<0.25`; `>=0.25` of recorded minutes |
| Very-active minutes | Zero; 1–29; 30 or more |
| Calories | Below full-cohort Q1; Q1 to below Q3; Q3 or above |
| Calendar day | Weekday; weekend |
| Coverage | Existing Phase 2 complete-day flag; incomplete day |

The full-cohort calorie cutpoints are Q1 = 1,776 and Q3 = 2,667. The same
cutpoints are retained in the complete-day sensitivity. Step and minute bins
are descriptive categories, not clinical or activity recommendations.

Apriori uses a maximum itemset size of three and the canonical subset-pruning
rule. No itemset can contain two categories from the same family. The pipeline
also excludes combinations of active-share with very-active minutes (a
component of its numerator) and active-share with coverage status (defined
using its denominator). This prevents direct part/whole or denominator-based
patterns from being presented as independent associations.

For an observed transaction count `N`, minimum support count is
`ceil(min_support * N)`. Baseline thresholds are support 5%, confidence 60%,
lift 1.10, and at least five distinct participants supporting the full joint
itemset. Each exported rule includes support, confidence, lift, leverage,
counts, threshold values, distinct-participant count, and a Boolean
`threshold_eligible` field. The complete rule table includes rules that do not
meet every threshold as well as qualifying rules.

## Results

- The 457 transactions contain 2,742 item occurrences across 17 possible
  category items.
- At 5% support, the minimum joint count is 23 participant-days. Apriori
  retained 215 frequent itemsets: 17 singletons, 82 pairs, and 116 triples.
- Those itemsets generate 860 directed rules; 89 meet all four baseline
  thresholds.
- In the all-days example `steps:zero -> active_share:lower`, support is
  60/457 (13.1%), confidence is 98.4%, lift is 3.33, and the joint itemset
  occurs for 14 participants. Its participant-balanced confidence is 98.8%
  across the 14 participants with at least one antecedent day.
- For `coverage:complete` plus `very_active:upper -> steps:upper`, pooled
  confidence is 86.0%, while the equal-participant average is 57.1% among the
  14 participants with antecedent observations. This difference is a reason
  to read pooled day-level confidence alongside participant-balanced results.

The participant-balanced confidence averages each person's conditional
confidence among people with at least one antecedent occurrence. The
participant-balanced itemset prevalence averages each person's prevalence
across their observed days. Both pooled and participant-balanced values are
available in `participant_balanced_sensitivity.csv`.

## Threshold and complete-day sensitivity

Each row below varies one threshold while holding the other baseline settings
fixed. The complete-day cohort contains 233 days from 28 participants with at
least one complete day.

| Sensitivity | Thresholds | All days: qualifying rules | Complete days: qualifying rules |
| --- | --- | --- | --- |
| Minimum support | 3%, 5%, 8% | 97, 89, 69 | 114, 108, 92 |
| Minimum confidence | 50%, 60%, 70% | 140, 89, 46 | 139, 108, 58 |
| Minimum lift | 1.00, 1.10, 1.25 | 109, 89, 68 | 178, 108, 83 |
| Minimum distinct participants | 3, 5, 10 | 89, 89, 62 | 110, 108, 43 |

For support sensitivity, the minimum observed joint counts are 14, 23, and 37
in all days, and 7, 12, and 19 in complete days. These are threshold
sensitivities, not model selection or inferential tests.

## Outputs and limitations

The generated outputs include the transaction-to-participant/date mapping,
long-format transaction items, item definitions, frequent itemsets, all
generated rules, participant-balanced sensitivity, support/confidence/lift/
participant-count grids, and complete-day rules. The three association figures
show item prevalence, rule support versus confidence, and support-threshold
sensitivity.

These rules describe co-occurrences in repeated historical daily records. They
are not causal relationships, validated predictors, or population-level
claims. The sample is small and participant coverage differs. Category
thresholds and cutpoints are explicit analysis choices; changing them may
change the mined patterns. No statistical significance or out-of-sample
predictive performance is claimed.
