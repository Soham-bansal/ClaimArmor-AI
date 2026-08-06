from __future__ import annotations


def simulate_roi(assumptions: dict) -> dict:
    annual_claims = int(assumptions["annual_claims"])
    average_claim_amount = float(assumptions["average_claim_amount"])
    leakage_rate = float(assumptions["leakage_rate"])
    value_detection_rate = float(assumptions["value_detection_rate"])
    review_rate = float(assumptions["review_rate"])
    review_cost = float(assumptions["review_cost"])
    false_positive_rate = float(assumptions["false_positive_rate"])
    false_positive_cost = float(assumptions["false_positive_cost"])
    platform_cost = float(assumptions["annual_platform_cost"])

    processed_value = annual_claims * average_claim_amount
    gross_leakage = processed_value * leakage_rate
    prevented_leakage = gross_leakage * value_detection_rate
    reviews = annual_claims * review_rate
    manual_review_cost = reviews * review_cost
    delay_cost = annual_claims * false_positive_rate * false_positive_cost
    net_benefit = prevented_leakage - manual_review_cost - delay_cost - platform_cost
    roi = net_benefit / platform_cost if platform_cost else 0
    return {
        "annual_claims": annual_claims,
        "processed_claim_value": round(processed_value, 2),
        "estimated_gross_leakage": round(gross_leakage, 2),
        "estimated_prevented_leakage": round(prevented_leakage, 2),
        "estimated_reviews": round(reviews),
        "manual_review_cost": round(manual_review_cost, 2),
        "false_positive_delay_cost": round(delay_cost, 2),
        "annual_platform_cost": round(platform_cost, 2),
        "estimated_net_benefit": round(net_benefit, 2),
        "estimated_roi_ratio": round(roi, 3),
        "estimated_roi_percent": round(roi * 100, 1),
        "basis": "Scenario simulation using user-visible assumptions; not a forecast or guarantee.",
    }

