# Ten-hour team handoff

The baseline already owns the shared contracts and the executable user journey. Keep API response fields stable while replacing baseline internals.

## Person 1 — data, matching, and ML

Primary files:

- `app/seed.py`
- `app/services/matching.py`
- `app/services/risk.py`

Next deliverables:

1. Generate at least 1,000 reproducible claims with scenario and ground-truth columns.
2. Replace the weighted risk baseline with trained XGBoost inference.
3. Persist model metrics and feature importance.
4. Upgrade member matching to Splink if time allows.

Do not change the existing `risk` and `member_match` response shapes without coordinating with the other owners.

## Person 2 — policy retrieval and agents

Primary files:

- `app/services/policy.py`
- `app/services/agents.py`

Next deliverables:

1. Download and record authoritative public policy sources.
2. Preserve title, URL, effective date, jurisdiction, section, and content hash.
3. Replace keyword overlap with embeddings/pgvector or a tested local vector index.
4. Convert the controlled workflow to LangGraph while keeping structured outputs.
5. Add a provider-backed LLM adapter with an offline fallback.
6. Evaluate citation correctness and unsupported-answer rate.

Never let document text or an LLM directly issue a payment or denial.

## Person 3 — API, database, and experience

Primary files:

- `app/main.py`
- `app/db.py`
- `app/static/index.html`

Next deliverables:

1. Add create-claim and CSV-upload screens.
2. Add authentication and seeded analyst/reviewer/auditor/admin roles.
3. Move persistence from SQLite to PostgreSQL without changing endpoints.
4. Expand the operations, review, audit, and evaluation dashboards.
5. Add Playwright tests for the three seeded scenarios.

## Shared acceptance command

```powershell
python -m unittest discover -s tests -v
python -m uvicorn app.main:app --reload
```

Then demonstrate:

1. `CLM-SAFE-001` → `CLEAR`
2. `CLM-HOLD-001` → `HOLD`
3. `CLM-REVIEW-001` → `HUMAN_REVIEW`

