# Baseline architecture

```mermaid
flowchart LR
    USERS[Analyst / Reviewer / Auditor / Admin] --> UI[Operations dashboard]
    UI --> AUTH[Signed authentication + RBAC]
    AUTH --> API[FastAPI]
    API --> DB[(SQLAlchemy: SQLite / PostgreSQL)]
    API --> PIPE[Investigation pipeline]
    PIPE --> MATCH[Identity matching]
    PIPE --> COVER[Coverage timeline]
    PIPE --> RISK[Risk scoring]
    PIPE --> RULES[COB rules]
    PIPE --> AGENTS[Controlled agent workflow]
    AGENTS --> POLICY[Public-policy retrieval]
    AGENTS --> VERIFY[Verification critic]
    PIPE --> GATE[Confidence gate]
    GATE --> UI
    UI --> REVIEW[Human review]
    REVIEW --> WRITE[Simulated core claims writeback]
    WRITE --> DB
    DB --> AUDIT[Hash-linked audit history]
    DB --> QUEUE[Human review queue]
    API --> EVAL[Holdout evaluation + ROI simulation]
    API --> OPS[Health, security headers, diagnostics]
```

## Production substitutions

| Baseline | Production-oriented replacement |
|---|---|
| SQLite local URL | PostgreSQL/pgvector URL in Compose |
| Keyword retrieval | pgvector embeddings with retrieval evaluation |
| Weighted risk scorer | Calibrated XGBoost model and model registry |
| Fuzzy weighted match | Splink/Fellegi–Sunter entity resolution |
| Python agent state | LangGraph with durable checkpoints |
| Inline processing | Celery/Redis worker with retry and dead-letter policy |
| Static browser UI | React/Next.js application |

The substitutions are behind stable service and API boundaries so the complete
workflow remains operational during the upgrade. The current implementation
already uses SQLAlchemy for both supported database URLs.
