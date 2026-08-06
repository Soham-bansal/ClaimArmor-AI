from __future__ import annotations

from app.ml.runtime import predict


def score_risk(claim: dict, active: list[dict], match_confidence: float) -> dict:
    trained_prediction = predict(claim, active, match_confidence)
    if trained_prediction is not None:
        return trained_prediction
    score = 0.08
    factors = []
    live = [coverage for coverage in active if coverage["active_on_service_date"]]
    if len(live) > 1:
        score += 0.32
        factors.append("Multiple active coverages")
    if claim.get("accident_related"):
        score += 0.28
        factors.append("Accident-related claim")
    if claim["amount"] >= 25_000:
        score += 0.18
        factors.append("High claim amount")
    elif claim["amount"] >= 10_000:
        score += 0.10
        factors.append("Material claim amount")
    if any(item["kind"] == "MEDICARE" for item in live):
        score += 0.12
        factors.append("Medicare coverage active")
    if match_confidence < 0.90:
        score += 0.12
        factors.append("Identity requires additional verification")
    score = min(round(score, 4), 0.99)
    return {
        "probability": score,
        "band": "HIGH" if score >= 0.70 else "MEDIUM" if score >= 0.35 else "LOW",
        "factors": factors or ["Single active coverage and consistent identity"],
        "model_version": "baseline-transparent-v1",
        "model_type": "weighted baseline (replace with trained XGBoost)",
    }
