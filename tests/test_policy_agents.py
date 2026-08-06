from __future__ import annotations

import unittest
from unittest.mock import patch

from app.schemas import ClaimInput
from app.seed import COVERAGES, DEMO_CLAIMS, MEMBERS
from app.services.agents import run_agents
from app.services.matching import active_coverages, match_member
from app.services.policy import evaluate_retrieval, retrieve_evidence
from app.services.risk import score_risk
from app.services.rules import evaluate_rules


class PolicyAndAgentTests(unittest.TestCase):
    def test_accident_retrieval_returns_liability_evidence(self):
        results = retrieve_evidence("car accident with active auto coverage")
        self.assertEqual(results[0]["policy_id"], "CMS-MSP-LIABILITY-001")
        self.assertTrue(results[0]["document_hash"])

    def test_retrieval_evaluation(self):
        metrics = evaluate_retrieval()
        self.assertGreaterEqual(metrics["hit_at_4"], 0.80)
        self.assertGreaterEqual(metrics["mrr"], 0.70)

    def test_langgraph_runs_all_controlled_stages(self):
        claim = ClaimInput.model_validate(DEMO_CLAIMS[1]).model_dump(mode="json")
        match = match_member(claim, MEMBERS)
        timeline = active_coverages(match["member_id"], claim["service_date"], COVERAGES)
        risk = score_risk(claim, timeline, match["confidence"])
        rules = evaluate_rules(claim, timeline)
        with patch.dict("os.environ", {"CLAIMARMOR_LLM_MODE": "offline"}):
            result = run_agents(claim, match, timeline, risk, rules)
        agents = [item["agent"] for item in result["trace"]]
        self.assertEqual(agents, ["identity_investigator", "coverage_investigator", "policy_researcher", "primacy_reasoner", "verification_critic", "financial_impact", "explanation"])
        self.assertEqual(result["route"].value, "HOLD")
        self.assertEqual(result["llm"]["mode"], "offline")

    def test_four_live_provider_stages_are_orchestrated(self):
        claim = ClaimInput.model_validate(DEMO_CLAIMS[1]).model_dump(mode="json")
        match = match_member(claim, MEMBERS)
        timeline = active_coverages(match["member_id"], claim["service_date"], COVERAGES)
        risk = score_risk(claim, timeline, match["confidence"])
        rules = evaluate_rules(claim, timeline)

        def structured(role, _instructions, _context, fallback):
            return fallback, {"mode": "gemini", "used": True, "model": "gemini-test", "role": role, "structured": True}

        with patch("app.services.agents.run_structured_agent", side_effect=structured) as calls, patch("app.services.agents.enhance_explanation", return_value=("Live explanation", {"mode": "gemini", "used": True, "model": "gemini-test"})) as explanation:
            result = run_agents(claim, match, timeline, risk, rules)
        self.assertEqual(calls.call_count, 3)
        explanation.assert_called_once()
        provider_outputs = [item["output"].get("provider", {}) for item in result["trace"] if isinstance(item["output"], dict)]
        self.assertEqual(sum(item.get("used") is True for item in provider_outputs), 4)


if __name__ == "__main__":
    unittest.main()
