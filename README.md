# ClaimArmor AI

ClaimArmor AI is a complete demo-grade proof of concept for pre-payment Coordination of Benefits (COB) auditing. It is runnable without private health data, paid services, or an LLM key. It is not represented as a production claims adjudicator.

## What works now

- seeded synthetic members, coverages, and claims;
- claim ingestion and validation;
- actual Splink/Fellegi-Sunter probabilistic member matching and a dated coverage timeline;
- calibrated XGBoost overpayment-risk scoring trained on 3,000 labeled synthetic claims;
- deterministic COB rules;
- public-policy evidence retrieval from a small curated corpus;
- a controlled seven-stage LangGraph workflow: identity, coverage, policy research, primacy reasoning, verification, financial impact, and explanation;
- confidence routing to `CLEAR`, `HOLD`, `HUMAN_REVIEW`, or `UNDETERMINED`;
- reviewer approval/override and simulated claims writeback;
- hash-linked audit events and basic business metrics;
- classic and React browser dashboards plus a REST API;
- citation-preserving CMS policy corpus and evaluated hybrid retrieval;
- a real LangGraph state machine for coverage, research, reasoning, verification,
  financial impact, and explanation;
- optional OpenAI or OpenRouter Responses API explanation enhancement with an offline fallback;
- four live evidence-grounded provider stages (policy analyst, primacy reasoner,
  independent verification critic, and explanation) selectable between Gemini,
  OpenAI, and OpenRouter, each with a deterministic offline fallback;
- synthetic EDI-like ingestion, stream simulation, investigation replay, and expanded reviewer actions;
- versioned text/PDF policy ingestion, trusted-source allowlisting, and prompt-injection rejection;
- OpenTelemetry hooks, Prometheus metrics, and optional Prometheus/Grafana containers.

The policy corpus and rules remain demonstration subsets. Every automated outcome is gated by deterministic checks and the LLM can never release or deny payment.

## Run locally

### Clone and start

```powershell
git clone https://github.com/Soham-bansal/ClaimArmor-AI.git
cd ClaimArmor-AI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. The repository includes the trained synthetic
XGBoost artifact and evaluation evidence, so offline mode works immediately.
An API key is optional. To enable a provider, edit only your local `.env`; it is
ignored by Git and must never be committed.

### Start an existing checkout

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. API documentation is available at <http://127.0.0.1:8000/docs>.
The built React console is available at <http://127.0.0.1:8000/react/>.

Seeded demonstration accounts:

| Role | Username | Password |
|---|---|---|
| Analyst | `analyst` | `Analyst123!` |
| Reviewer | `reviewer` | `Review123!` |
| Auditor | `auditor` | `Audit123!` |
| Administrator | `admin` | `Admin123!` |

These credentials are local demonstration fixtures and must never be used in a
deployed environment.

The database is automatically created and three demo claims are seeded:

- `CLM-SAFE-001`: low-risk single-payer claim;
- `CLM-HOLD-001`: accident claim with active auto coverage;
- `CLM-REVIEW-001`: ambiguous employer/Medicare scenario.

## Generate data and train the risk model

The application safely falls back to its transparent baseline when a trained
artifact is unavailable. Generate reproducible synthetic data and activate the
trained model with:

```powershell
python -m app.ml.train --regenerate --rows 3000
```

This creates a synthetic CSV, a persisted model, and `artifacts/model_metrics.json`.
Restart the API after training so the cached model bundle is reloaded. Metrics
are exposed at `GET /api/model/metrics` and inside `GET /api/metrics`.

## Policy retrieval and optional LLM mode

The application ships with a curated, source-linked CMS MSP corpus in
`data/policies/cms_msp_chunks.json`. Retrieval evaluation is exposed at
`GET /api/retrieval/metrics`.

Offline mode is the safe default. For the Gemini free tier, set
`CLAIMARMOR_LLM_MODE=gemini`, `GEMINI_API_KEY`, and optionally `GEMINI_MODEL`
in `.env`. For OpenRouter, revoke any key ever pasted
into chat, create a fresh key, set `CLAIMARMOR_LLM_MODE=openrouter`,
`OPENROUTER_API_KEY`, and `OPENROUTER_MODEL` in your local environment. For
OpenAI use `CLAIMARMOR_LLM_MODE=openai` and `OPENAI_API_KEY`. Never commit a
real key. The deterministic rules and verification gate remain authoritative.
Free-tier provider requests must contain only synthetic/public data; never send
real member or claims data to a consumer/free-tier model endpoint.

Provider selection is one environment setting:

```env
# Free-tier testing
CLAIMARMOR_LLM_MODE=gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.5-flash
GEMINI_STRUCTURED_MODEL=gemini-3.5-flash-lite
GEMINI_EXPLANATION_MODEL=gemini-3.5-flash-lite

# Final direct OpenAI checking (use instead of the three lines above)
CLAIMARMOR_LLM_MODE=openai
OPENAI_API_KEY=...
CLAIMARMOR_LLM_MODEL=gpt-5.6-sol
```

Each investigation makes four provider calls when a provider is enabled. The
provider proposes analysis, but deterministic code owns the final route and can
only accept the proposal or escalate it to human review.

## Claim ingestion

Analysts can create a claim in the browser or upload CSV text through
`POST /api/claims/upload-csv`. A sample is available at
`data/samples/claims_upload.csv`. Batches are limited to 500 rows and return
separate created, duplicate, and validation-error results.

The system also accepts the clearly labeled, non-certified EDI-like demo format
through `POST /api/claims/upload-edi`, and can process selected claims as a
simulated ordered stream through `POST /api/stream/simulate`.

## Generate the richer entity dataset and evaluation evidence

```powershell
python -m app.data_generation --members 250
python -m app.identity_evaluation
python -m app.full_evaluation
```

These commands create members, dependants, employers, providers, eligibility,
coverage, identity variants, labeled claims, and the consolidated evidence
artifact in `artifacts/full_system_evaluation.json`.

## Build the React console

```powershell
cd frontend
npm install
npm run build
cd ..
```

The built assets are emitted to `app/static/react` and served by FastAPI.

## PostgreSQL

Local execution defaults to SQLite. Set `CLAIMARMOR_DATABASE_URL` to a
SQLAlchemy PostgreSQL URL to switch storage without changing application code.
`compose.yaml` contains a PostgreSQL/pgvector service and configures the app to
use it. Docker is not installed in the current development environment, so the
container path is provided but not locally verified.

## Test

The baseline tests use Python's standard library, so they work before optional
development dependencies are installed:

```powershell
python -m unittest discover -s tests -v
```

Run the complete reproducible verification, including comparative evaluation:

```powershell
.\verify.ps1
```

Final project evidence is collected in:

- `docs/EVALUATION_REPORT.md`
- `docs/LIMITATIONS.md`
- `docs/DEMO_SCRIPT.md`
- `docs/PRESENTATION_OUTLINE.md`
- `docs/RUNBOOK.md`
- `docs/FINAL_CHECKLIST.md`
- `docs/SCREENSHOTS.md`

## Structure

```text
app/
  main.py            API and dashboard hosting
  schemas.py         shared data contracts
  db.py              SQLite persistence and hash-linked audit log
  seed.py            reproducible synthetic demonstration data
  services/
    matching.py      Splink/Fellegi-Sunter identity matching
    risk.py          calibrated model runtime and fallback
    rules.py         deterministic COB rules
    policy.py        cited policy retrieval
    agents.py        controlled agent workflow
    pipeline.py      end-to-end orchestration
  static/            classic and built React dashboards
frontend/            React/Vite reviewer console source
monitoring/          Prometheus and Grafana provisioning
tests/               critical workflow tests
```

## Safety and scope

All records are synthetic. Policy snippets are demonstrative summaries and must be replaced or validated against authoritative current sources before any real use. The application provides decision support; an LLM never releases or denies a claim.
