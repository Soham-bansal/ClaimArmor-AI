from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import DecisionRoute
from app.services.llm import enhance_explanation, run_structured_agent
from app.services.policy import retrieve_evidence


class InvestigationState(TypedDict, total=False):
    claim: dict[str, Any]
    match: dict[str, Any]
    timeline: list[dict[str, Any]]
    risk: dict[str, Any]
    rules: list[dict[str, Any]]
    trace: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    route: DecisionRoute
    payer: str | None
    confidence: float
    contradictions: list[str]
    financial: dict[str, Any]
    explanation: str
    llm: dict[str, Any]
    policy_analysis: dict[str, Any]
    ai_primacy: dict[str, Any]
    ai_critique: dict[str, Any]


def _trace(state: InvestigationState, agent: str, output: Any) -> list[dict]:
    return [*state.get("trace", []), {"agent": agent, "status": "complete", "output": output}]


def identity_node(state: InvestigationState) -> dict:
    output = {
        "member_id": state["match"]["member_id"],
        "confidence": state["match"]["confidence"],
        "status": state["match"]["status"],
        "method": state["match"].get("method", "unknown"),
    }
    return {"trace": _trace(state, "identity_investigator", output)}


def coverage_node(state: InvestigationState) -> dict:
    active = [item for item in state["timeline"] if item["active_on_service_date"]]
    summary = ", ".join(f"{item['payer']} ({item['kind']})" for item in active) or "no active coverage"
    return {"trace": _trace(state, "coverage_investigator", f"Active coverage: {summary}.")}


def research_node(state: InvestigationState) -> dict:
    active = [item for item in state["timeline"] if item["active_on_service_date"]]
    query = "coordination of benefits payer order"
    if state["claim"].get("accident_related"):
        query += " auto car accident liability no-fault"
    if any(item["kind"] == "MEDICARE" for item in active):
        query += " Medicare employer plan working aged provider missing facts"
    evidence = retrieve_evidence(query)
    fallback = {"applicable_policy_ids": [item["policy_id"] for item in evidence], "findings": ["Offline retrieval completed; provider analysis unavailable."], "missing_facts": [], "confidence": 0.0}
    analysis, provider = run_structured_agent(
        "Policy Analyst Agent",
        "Identify which retrieved policies apply. Return keys applicable_policy_ids (array), findings (array), missing_facts (array), confidence (0 to 1). Cite only supplied policy IDs.",
        {"claim": state["claim"], "coverage_timeline": state["timeline"], "retrieved_evidence": [{"policy_id": item["policy_id"], "section": item["section"], "text": item["text"]} for item in evidence]},
        fallback,
    )
    output = {"query": query, "policy_ids": [item["policy_id"] for item in evidence], "analysis": analysis, "provider": provider}
    return {"evidence": evidence, "policy_analysis": analysis, "trace": _trace(state, "policy_researcher", output)}


def reasoning_node(state: InvestigationState) -> dict:
    hold = next((rule for rule in state["rules"] if rule["outcome"] == "HOLD"), None)
    review = next((rule for rule in state["rules"] if rule["outcome"] == "REVIEW"), None)
    clear = next((rule for rule in state["rules"] if rule["outcome"] == "CLEAR"), None)
    if hold:
        route, payer, confidence = DecisionRoute.HOLD, hold["payer"], 0.93
    elif review or state["match"]["status"] == "REVIEW":
        route, payer, confidence = DecisionRoute.HUMAN_REVIEW, None, 0.68
    elif clear and state["risk"]["probability"] < 0.35:
        route, payer, confidence = DecisionRoute.CLEAR, clear["payer"], 0.95
    else:
        route, payer, confidence = DecisionRoute.UNDETERMINED, None, 0.45
    fallback = {"proposed_route": route.value, "primary_payer": payer, "secondary_payer": None, "reason_codes": [], "cited_policy_ids": [], "confidence": 0.0, "missing_facts": []}
    proposal, provider = run_structured_agent(
        "Primacy Reasoning Agent",
        "Independently propose payer order. Return proposed_route (CLEAR, HOLD, HUMAN_REVIEW, or UNDETERMINED), primary_payer, secondary_payer, reason_codes, cited_policy_ids, confidence, and missing_facts. Never invent coverage or policy IDs.",
        {"claim": state["claim"], "member_match": state["match"], "coverage_timeline": state["timeline"], "deterministic_rules": state["rules"], "policy_analysis": state.get("policy_analysis", {}), "available_policy_ids": [item["policy_id"] for item in state.get("evidence", [])]},
        fallback,
    )
    output = {"deterministic_gate": {"route": route.value, "recommended_primary_payer": payer, "confidence": confidence}, "ai_proposal": proposal, "provider": provider}
    return {"route": route, "payer": payer, "confidence": confidence, "ai_primacy": {"proposal": proposal, "provider": provider}, "trace": _trace(state, "primacy_reasoner", output)}


def verify_node(state: InvestigationState) -> dict:
    contradictions = []
    evidence_ids = {item["policy_id"] for item in state.get("evidence", [])}
    if state["route"] == DecisionRoute.HOLD and not evidence_ids:
        contradictions.append("No policy evidence supports the hold recommendation.")
    if state["claim"].get("accident_related") and state["route"] == DecisionRoute.HOLD and "CMS-MSP-LIABILITY-001" not in evidence_ids:
        contradictions.append("The accident decision lacks the expected liability/no-fault evidence.")
    if state["match"]["confidence"] < 0.85:
        contradictions.append("Member identity confidence is below the automated-decision threshold.")
    fallback = {"citation_supported": bool(evidence_ids), "validated_policy_ids": [], "contradictions": [], "missing_facts": [], "requires_human_review": False, "confidence": 0.0}
    critique, provider = run_structured_agent(
        "Independent Verification Critic Agent",
        "Challenge the proposed decision. Return citation_supported (boolean), validated_policy_ids, contradictions, missing_facts, requires_human_review (boolean), and confidence. A disagreement must reference supplied facts or policy IDs.",
        {"claim": state["claim"], "coverage_timeline": state["timeline"], "deterministic_route": state["route"].value, "deterministic_payer": state.get("payer"), "ai_primacy": state.get("ai_primacy", {}), "evidence": [{"policy_id": item["policy_id"], "text": item["text"]} for item in state.get("evidence", [])]},
        fallback,
    )
    if provider.get("used"):
        proposed_payer = state.get("ai_primacy", {}).get("proposal", {}).get("primary_payer")
        if proposed_payer and state.get("payer") and proposed_payer != state.get("payer"):
            contradictions.append(f"AI primacy proposal ({proposed_payer}) conflicts with the deterministic payer ({state.get('payer')}).")
        invalid_ids = set(critique.get("validated_policy_ids", [])) - evidence_ids
        if invalid_ids:
            contradictions.append("Verifier cited policy IDs that were not retrieved; human review is required.")
        contradictions.extend(f"AI critic: {item}" for item in critique.get("contradictions", [])[:5] if isinstance(item, str))
        if critique.get("requires_human_review") and not critique.get("contradictions"):
            contradictions.append("AI critic requested human review because evidence or claim facts remain incomplete.")
    route = DecisionRoute.HUMAN_REVIEW if contradictions else state["route"]
    confidence = min(state["confidence"], 0.60) if contradictions else state["confidence"]
    output = {"passed": not contradictions, "contradictions": contradictions, "checked_policy_ids": sorted(evidence_ids), "ai_critique": critique, "provider": provider}
    return {"route": route, "confidence": confidence, "contradictions": contradictions, "ai_critique": {"critique": critique, "provider": provider}, "trace": _trace(state, "verification_critic", output)}


def financial_node(state: InvestigationState) -> dict:
    amount_at_risk = round(state["claim"]["amount"] * state["risk"]["probability"], 2)
    financial = {"claim_amount": state["claim"]["amount"], "amount_at_risk": amount_at_risk, "estimated_review_cost": 35.0, "expected_net_value": round(max(amount_at_risk - 35, 0), 2)}
    return {"financial": financial, "trace": _trace(state, "financial_impact", financial)}


def explanation_node(state: InvestigationState) -> dict:
    payer = state.get("payer")
    if state["route"] == DecisionRoute.CLEAR:
        fallback = f"The claim can continue because {payer} is the only supported active primary payer and model risk is low."
    elif state["route"] == DecisionRoute.HOLD:
        fallback = f"Hold before payment: {payer} may be responsible first. The triggered COB rule and cited CMS evidence support further coordination."
    elif state["route"] == DecisionRoute.HUMAN_REVIEW:
        fallback = "Human review is required because payer order cannot be resolved safely from the available coverage, identity, and policy facts."
    else:
        fallback = "The system cannot determine payer primacy because required coverage evidence is unavailable."
    context = {"route": state["route"].value, "payer": payer, "rules": state["rules"], "policy_analysis": state.get("policy_analysis", {}), "ai_primacy": state.get("ai_primacy", {}), "ai_critique": state.get("ai_critique", {}), "evidence": [{"policy_id": item["policy_id"], "text": item["text"]} for item in state.get("evidence", [])], "contradictions": state.get("contradictions", [])}
    explanation, llm = enhance_explanation(context, fallback)
    return {"explanation": explanation, "llm": llm, "trace": _trace(state, "explanation", {"text": explanation, "provider": llm})}


def build_graph():
    builder = StateGraph(InvestigationState)
    builder.add_node("identity", identity_node)
    builder.add_node("coverage", coverage_node)
    builder.add_node("research", research_node)
    builder.add_node("reason", reasoning_node)
    builder.add_node("verify", verify_node)
    builder.add_node("financial", financial_node)
    builder.add_node("explain", explanation_node)
    builder.add_edge(START, "identity")
    builder.add_edge("identity", "coverage")
    builder.add_edge("coverage", "research")
    builder.add_edge("research", "reason")
    builder.add_edge("reason", "verify")
    builder.add_edge("verify", "financial")
    builder.add_edge("financial", "explain")
    builder.add_edge("explain", END)
    return builder.compile()


GRAPH = build_graph()


def _agent_result(state: InvestigationState) -> dict:
    return {"evidence": state["evidence"], "trace": state["trace"], "route": state["route"], "payer": state.get("payer"), "confidence": state["confidence"], "financial": state["financial"], "explanation": state["explanation"], "contradictions": state.get("contradictions", []), "llm": state.get("llm", {})}


def run_agents(claim: dict, match: dict, timeline: list[dict], risk: dict, rules: list[dict]) -> dict:
    state = GRAPH.invoke({"claim": claim, "match": match, "timeline": timeline, "risk": risk, "rules": rules, "trace": []})
    return _agent_result(state)


def stream_agents(claim: dict, match: dict, timeline: list[dict], risk: dict, rules: list[dict]):
    """Yield each real LangGraph node update as soon as that node completes."""
    state: InvestigationState = {"claim": claim, "match": match, "timeline": timeline, "risk": risk, "rules": rules, "trace": []}
    for chunk in GRAPH.stream(state, stream_mode="updates"):
        for node, update in chunk.items():
            state.update(update)
            trace = update.get("trace", [])
            if trace:
                yield {"type": "agent", "node": node, "data": trace[-1]}
    yield {"type": "agents_complete", "data": _agent_result(state)}
