from __future__ import annotations

from app import db
from app.schemas import InvestigationResult
from app.seed import COVERAGES, MEMBERS
from app.services.agents import run_agents, stream_agents
from app.services.matching import active_coverages, match_member
from app.services.risk import score_risk
from app.services.rules import evaluate_rules


def _finalize(claim: dict, match: dict, timeline: list[dict], risk: dict, rules: list[dict], agent_result: dict) -> InvestigationResult:
    limitations = [
        "All claim and member data are synthetic.",
        "The calibrated XGBoost model was trained and evaluated only on synthetic scenarios; real-payer calibration is still required.",
        "Policy snippets are a curated demonstration corpus and require authoritative validation for real use.",
    ]
    result = InvestigationResult(
        claim_id=claim["claim_id"],
        member_match=match,
        coverage_timeline=timeline,
        risk=risk,
        rules=rules,
        evidence=agent_result["evidence"],
        agent_trace=agent_result["trace"],
        recommended_primary_payer=agent_result["payer"],
        route=agent_result["route"],
        confidence=agent_result["confidence"],
        financial_impact=agent_result["financial"],
        explanation=agent_result["explanation"],
        limitations=limitations,
    )
    payload = result.model_dump(mode="json")
    db.put_investigation(claim["claim_id"], payload)
    db.append_audit(claim["claim_id"], "INVESTIGATION_COMPLETED", {"route": result.route.value, "confidence": result.confidence, "risk": result.risk["probability"]})
    return result


def investigate(claim: dict) -> InvestigationResult:
    match = match_member(claim, MEMBERS)
    timeline = active_coverages(match["member_id"], claim["service_date"], COVERAGES)
    risk = score_risk(claim, timeline, match["confidence"])
    rules = evaluate_rules(claim, timeline)
    return _finalize(claim, match, timeline, risk, rules, run_agents(claim, match, timeline, risk, rules))


def investigate_events(claim: dict):
    match = match_member(claim, MEMBERS)
    timeline = active_coverages(match["member_id"], claim["service_date"], COVERAGES)
    risk = score_risk(claim, timeline, match["confidence"])
    rules = evaluate_rules(claim, timeline)
    for event in stream_agents(claim, match, timeline, risk, rules):
        if event["type"] == "agent":
            yield event
        else:
            result = _finalize(claim, match, timeline, risk, rules, event["data"])
            yield {"type": "complete", "data": result.model_dump(mode="json")}
