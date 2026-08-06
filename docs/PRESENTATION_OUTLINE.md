# Presentation outline

1. **Problem:** incorrect payer order creates preventable overpayment leakage.
2. **Users:** claim analyst, COB reviewer, auditor, and platform administrator.
3. **Solution:** pre-payment hybrid control combining identity, timelines,
   XGBoost, deterministic rules, policy retrieval, agents, and human review.
4. **Data:** 3,000 reproducible synthetic claims and source-linked public CMS
   guidance; no real PHI.
5. **Architecture:** authenticated API, portable persistence, risk model,
   LangGraph workflow, review queue, writeback simulator, and audit chain.
6. **Live workflow:** clear, hold, and ambiguous cases.
7. **Evidence:** held-out ML metrics, approach comparison, retrieval benchmark,
   tests, and tamper detection.
8. **Business value:** assumption-driven ROI simulator and value-weighted recall.
9. **Innovation:** evidence hashes, verification critic, temporal coverage,
   hybrid routing, and replayable audit events.
10. **Enterprise path:** PostgreSQL, SSO, queues, complete policy corpus,
    calibration, monitoring, and compliance validation.
11. **Limitations:** synthetic performance and demonstration security.
12. **Ask:** approve a governed historical-data pilot, not immediate production.

## Judging-matrix evidence

| Criterion | Demonstration evidence |
|---|---|
| Technical implementation | Live API, trained model, LangGraph, persistence, RBAC, tests |
| Functional completeness | Ingest through review, writeback, audit, and dashboards |
| Evidence and evaluation | Holdout metrics, baselines, retrieval benchmark, error analysis |
| Business value | Value recall and editable ROI assumptions |
| Innovation | Critic agent, evidence hashing, temporal payer reasoning |
| Enterprise scalability | PostgreSQL path, roles, security headers, diagnostics, versioning |
| Presentation | Seeded cases, seven-minute script, clear limitations |

