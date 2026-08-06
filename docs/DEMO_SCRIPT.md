# Seven-minute live demo

## 1. Establish scope — 30 seconds

Open the login page and point out `SYNTHETIC DATA ONLY`. Explain that ClaimArmor
checks payer order before a simulated payment and never lets the LLM make the
final payment decision.

## 2. Analyst ingestion — 60 seconds

Sign in as `analyst / Analyst123!`. Upload
`data/samples/claims_upload.csv`. Show created/duplicate/error counts. Select
`CLM-CSV-001` and run the investigation.

## 3. Agentic investigation — 90 seconds

Show the XGBoost risk score, active coverage timeline, triggered accident rule,
CMS evidence with source links and hashes, and the six-stage LangGraph trace.
Emphasize that the verification critic checks for the expected liability
evidence before allowing a hold recommendation.

## 4. Human review — 60 seconds

Sign out and sign in as `reviewer / Review123!`. Open the pending queue, approve
the hold, and show the simulated core-claims writeback. Verify the audit chain.

## 5. Three outcomes — 60 seconds

- `CLM-SAFE-001` → `CLEAR`
- `CLM-HOLD-001` → `HOLD`
- `CLM-REVIEW-001` → `HUMAN_REVIEW`

## 6. Evidence and business value — 90 seconds

Show the held-out approach comparison and explain the precision/coverage
trade-off. Change an ROI assumption and rerun the scenario. Explicitly state
that the output is synthetic and assumption-driven.

## 7. Governance — 30 seconds

Sign in as `auditor / Audit123!`. Show read-only access, diagnostics, model and
retrieval readiness, policy hashes, security headers, and audit verification.

