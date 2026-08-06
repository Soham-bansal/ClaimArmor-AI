# ClaimArmor overpayment-risk model card

## Purpose

`overpayment-risk-v1` prioritises synthetic health-insurance claims for further COB investigation. It does not determine final payer primacy and cannot release or deny a claim.

## Training data

- 3,000 reproducibly generated synthetic claims
- fixed random seed: `42`
- eight controlled scenario families
- no real member, provider, payer, or patient information
- 78/22 stratified train/test split

Scenario families include single coverage, overlapping Medicare-like and employer coverage, accident/auto coverage, inactive secondary coverage, incorrect submitted payer, and ambiguous identity.

## Algorithm

The preferred implementation is XGBoost. `HistGradientBoostingClassifier` is an explicit offline fallback when XGBoost is unavailable. The API and dashboard identify which algorithm produced the active artifact.

## Features

- logarithmic claim amount;
- number and kinds of active coverage;
- accident indicator;
- member age on service date;
- member-match confidence;
- missing member ID;
- submitted payer type;
- coverage-overlap indicator.

No protected demographic characteristic is used directly. Age is included because Medicare-like eligibility and COB scenarios are time-dependent; its use and performance slices must be reviewed before any real deployment.

## Evaluation

Metrics are generated rather than manually entered. The canonical record is `artifacts/model_metrics.json`, exposed through `/api/model/metrics`.

The evaluation includes precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, detected synthetic overpayment value, and value-weighted recall.

## Limitations

- Synthetic performance does not establish real-world performance.
- The scenario generator encodes assumptions and can introduce synthetic bias.
- Current probability scores are not separately calibrated.
- Drift, fairness slices, and external validation remain future work.
- A risk score must always be combined with rules, evidence, verification, and human review thresholds.

