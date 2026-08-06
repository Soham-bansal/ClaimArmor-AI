# ClaimArmor live form test cases

Use these cases with **Ingest claims → Create one claim**. They use only the
three synthetic members and coverages defined in `app/seed.py`.

If a claim ID was already created, change its final number before saving it.

## Recommended demonstration order

1. CLEAR — normal low-risk processing
2. HOLD — auto insurer may be primary
3. HUMAN_REVIEW — employer and Medicare ambiguity
4. UNDETERMINED — no coverage on the service date
5. HUMAN_REVIEW — uncertain member identity

## Case 1 — CLEAR: one active employer plan

| Form field | Value |
|---|---|
| Claim ID | `CLM-LIVE-CLEAR-01` |
| Member name | `Rohan Kapoor` |
| Date of birth | `1988-11-03` |
| Member ID | `MBR-1002` |
| Service date | `2025-06-12` |
| Amount | `1250` |
| Submitted payer | `Employer plan` |
| Claim type | `MEDICAL` |
| Diagnosis group | `GENERAL` |
| Accident related | `No` |

Expected route: **CLEAR**  
Expected primary payer: **EMPLOYER_PLAN**

Show that the employer plan is active, auto coverage has not started yet,
identity confidence is high, and model risk is low.

## Case 2 — HOLD: accident with active auto coverage

| Form field | Value |
|---|---|
| Claim ID | `CLM-LIVE-HOLD-01` |
| Member name | `Rohan Kappor` |
| Date of birth | `1988-11-03` |
| Member ID | Leave blank |
| Service date | `2026-08-07` |
| Amount | `20000` |
| Submitted payer | `Employer plan` |
| Claim type | `TRAUMA` |
| Diagnosis group | `ACCIDENT` |
| Accident related | `Yes` |

Expected route: **HOLD**  
Expected primary payer: **AUTO_INSURER**

Show the spelling-tolerant identity match, employer and auto coverage overlap,
`COB-ACCIDENT-001`, accident-policy evidence, and the proposed payer order.

## Case 3 — HUMAN_REVIEW: employer and Medicare overlap

| Form field | Value |
|---|---|
| Claim ID | `CLM-LIVE-REVIEW-01` |
| Member name | `Maya Iyer` |
| Date of birth | `1961-07-24` |
| Member ID | `MBR-1003` |
| Service date | `2026-08-07` |
| Amount | `50000` |
| Submitted payer | `Employer plan` |
| Claim type | `INPATIENT` |
| Diagnosis group | `GENERAL` |
| Accident related | `No` |

Expected route: **HUMAN_REVIEW**  
Expected primary payer: **Not determined**

Show the employer/Medicare overlap and explain that employment status,
employer size, relationship, and Medicare eligibility facts may be required.

## Case 4 — UNDETERMINED: no active coverage

| Form field | Value |
|---|---|
| Claim ID | `CLM-LIVE-UNKNOWN-01` |
| Member name | `Rohan Kapoor` |
| Date of birth | `1988-11-03` |
| Member ID | `MBR-1002` |
| Service date | `2023-06-12` |
| Amount | `5000` |
| Submitted payer | `Employer plan` |
| Claim type | `MEDICAL` |
| Diagnosis group | `GENERAL` |
| Accident related | `No` |

Expected route: **UNDETERMINED**  
Expected primary payer: **Not determined**

Show that Rohan's employer coverage begins in 2024 and auto coverage begins in
2026, so neither is active on the 2023 service date.

## Case 5 — HUMAN_REVIEW: uncertain identity

| Form field | Value |
|---|---|
| Claim ID | `CLM-LIVE-IDENTITY-01` |
| Member name | `Tom Katin` |
| Date of birth | `2000-12-07` |
| Member ID | Leave blank |
| Service date | `2026-08-07` |
| Amount | `15000` |
| Submitted payer | `Employer plan` |
| Claim type | `MEDICAL` |
| Diagnosis group | `GENERAL` |
| Accident related | `No` |

Expected route: **HUMAN_REVIEW**  
Expected primary payer: **Not safely determined**

Show that no strong identity record exists. The matching service still returns
its best candidate, but confidence is below the automated-decision threshold,
so the safety gate requires a person to verify the member.

## Presenter reminder

For every case, point out this sequence:

`Identity → Coverage → Risk model → Rules → Policy evidence → Primacy → Verification → Final route`

Gemini/OpenAI assists with evidence analysis, payer-order proposals, criticism,
and explanation. Deterministic code owns the final safety gate.
