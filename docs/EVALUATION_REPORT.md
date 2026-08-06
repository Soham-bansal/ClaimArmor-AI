# ClaimArmor evaluation report

Generated from the reproducible synthetic dataset and `overpayment-risk-v1`.
The machine-readable source is `artifacts/system_evaluation.json`.

## Evaluation design

- 3,000 total synthetic claims
- 660-claim stratified holdout set
- fixed random seed `42`
- the holdout rows were not used to fit the persisted model
- financial results use explicit costs rather than claimed recoveries

## Comparative results

| Approach | Precision | Recall | F1 | PR-AUC | Value recall | Review rate |
|---|---:|---:|---:|---:|---:|---:|
| Rules only | 72.17% | 96.96% | 82.75% | 71.03% | 98.28% | 46.82% |
| ML only | 82.71% | 76.96% | 79.73% | 90.22% | 83.70% | 32.42% |
| Hybrid rules + ML + review gate | 74.64% | 90.87% | 81.96% | 87.62% | 93.34% | 42.42% |

The comparison demonstrates a real trade-off: rules recover more synthetic
value but produce more reviews; ML is more precise but misses more leakage; the
hybrid reduces missed value relative to ML while keeping the review rate below
the rules-only baseline.

## Retrieval evaluation

- five curated benchmark questions;
- Hit@4: 100%;
- mean reciprocal rank: 80%;
- all evidence records retain source URL, section, verification date, and hash.

Five examples are enough to verify wiring, not enough to claim broad regulatory
coverage. Expanding the benchmark is a production requirement.

## Financial evaluation assumptions

- $35 review cost per flagged claim;
- $75 delay cost per false positive;
- $0.20 processing cost per evaluated claim.

These values can be changed through the ROI simulator. Results are scenario
outputs on synthetic claims, not forecasts, guarantees, or reported savings.

## Error analysis

The most difficult synthetic family contains overlapping employer and
Medicare-like coverage without employer-size or current-employment facts. That
ambiguity is intentional: those claims should be reviewed rather than silently
resolved from age or coverage presence. Identity ambiguity and controlled label
noise also account for part of the remaining error.

