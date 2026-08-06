from __future__ import annotations


def evaluate_rules(claim: dict, coverage_timeline: list[dict]) -> list[dict]:
    live = [coverage for coverage in coverage_timeline if coverage["active_on_service_date"]]
    results = []
    if len(live) == 1:
        results.append({"rule_id": "COB-SINGLE-001", "outcome": "CLEAR", "payer": live[0]["payer"], "reason": "Only one coverage is active on the service date."})
    if claim.get("accident_related") and any(item["kind"] == "AUTO" for item in live):
        payer = next(item["payer"] for item in live if item["kind"] == "AUTO")
        results.append({"rule_id": "COB-ACCIDENT-001", "outcome": "HOLD", "payer": payer, "reason": "Accident-related claim has active auto coverage; investigate auto payer primacy."})
    if any(item["kind"] == "MEDICARE" for item in live) and any(item["kind"] == "EMPLOYER" for item in live):
        results.append({"rule_id": "MSP-DUAL-001", "outcome": "REVIEW", "payer": None, "reason": "Employer and Medicare coverages overlap; employment and beneficiary facts are required."})
    if not live:
        results.append({"rule_id": "COB-NO-COVERAGE-001", "outcome": "UNDETERMINED", "payer": None, "reason": "No coverage is active on the service date."})
    return results

