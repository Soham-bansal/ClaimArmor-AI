from __future__ import annotations

import math
from datetime import date


FEATURE_NAMES = [
    "claim_amount_log",
    "active_coverage_count",
    "has_medicare",
    "has_employer",
    "has_auto",
    "accident_related",
    "age_on_service",
    "match_confidence",
    "missing_member_id",
    "submitted_is_employer",
    "submitted_is_medicare",
    "submitted_is_auto",
    "coverage_overlap",
]


def age_on(dob: str | date, service_date: str | date) -> int:
    born = date.fromisoformat(str(dob))
    serviced = date.fromisoformat(str(service_date))
    return serviced.year - born.year - ((serviced.month, serviced.day) < (born.month, born.day))


def build_features(claim: dict, timeline: list[dict], match_confidence: float) -> dict[str, float]:
    active = [item for item in timeline if item.get("active_on_service_date", True)]
    kinds = {item["kind"] for item in active}
    submitted = claim["submitted_payer"].upper()
    return {
        "claim_amount_log": math.log1p(float(claim["amount"])),
        "active_coverage_count": float(len(active)),
        "has_medicare": float("MEDICARE" in kinds),
        "has_employer": float("EMPLOYER" in kinds),
        "has_auto": float("AUTO" in kinds),
        "accident_related": float(bool(claim.get("accident_related"))),
        "age_on_service": float(age_on(claim["member_dob"], claim["service_date"])),
        "match_confidence": float(match_confidence),
        "missing_member_id": float(not bool(claim.get("member_id"))),
        "submitted_is_employer": float("EMPLOYER" in submitted),
        "submitted_is_medicare": float("MEDICARE" in submitted),
        "submitted_is_auto": float("AUTO" in submitted),
        "coverage_overlap": float(len(active) > 1),
    }

