from __future__ import annotations

from copy import deepcopy


MEMBERS = [
    {"member_id": "MBR-1001", "name": "Asha Mehta", "dob": "1958-04-12", "address": "14 Lake Road", "email": "asha.mehta@example.test", "phone": "+1-555-0101"},
    {"member_id": "MBR-1002", "name": "Rohan Kapoor", "dob": "1988-11-03", "address": "21 Park Street", "email": "rohan.kapoor@example.test", "phone": "+1-555-0102"},
    {"member_id": "MBR-1003", "name": "Maya Iyer", "dob": "1961-07-24", "address": "8 Hill Avenue", "email": "maya.iyer@example.test", "phone": "+1-555-0103"},
]

COVERAGES = [
    {"coverage_id": "COV-1", "member_id": "MBR-1001", "payer": "EMPLOYER_PLAN", "kind": "EMPLOYER", "start": "2025-01-01", "end": "2026-12-31", "priority_hint": 2},
    {"coverage_id": "COV-2", "member_id": "MBR-1001", "payer": "MEDICARE", "kind": "MEDICARE", "start": "2025-07-01", "end": None, "priority_hint": 1},
    {"coverage_id": "COV-3", "member_id": "MBR-1002", "payer": "EMPLOYER_PLAN", "kind": "EMPLOYER", "start": "2024-01-01", "end": None, "priority_hint": 1},
    {"coverage_id": "COV-4", "member_id": "MBR-1002", "payer": "AUTO_INSURER", "kind": "AUTO", "start": "2026-01-01", "end": "2026-12-31", "priority_hint": 0},
    {"coverage_id": "COV-5", "member_id": "MBR-1003", "payer": "EMPLOYER_PLAN", "kind": "EMPLOYER", "start": "2025-01-01", "end": None, "priority_hint": 1},
    {"coverage_id": "COV-6", "member_id": "MBR-1003", "payer": "MEDICARE", "kind": "MEDICARE", "start": "2026-06-01", "end": None, "priority_hint": 1},
]

DEMO_CLAIMS = [
    {"claim_id": "CLM-SAFE-001", "member_name": "Rohan Kapoor", "member_dob": "1988-11-03", "member_id": "MBR-1002", "service_date": "2025-06-12", "amount": 1250, "submitted_payer": "EMPLOYER_PLAN", "claim_type": "MEDICAL", "accident_related": False, "diagnosis_group": "GENERAL"},
    {"claim_id": "CLM-HOLD-001", "member_name": "Rohan Kappor", "member_dob": "1988-11-03", "member_id": None, "service_date": "2026-08-01", "amount": 20000, "submitted_payer": "EMPLOYER_PLAN", "claim_type": "TRAUMA", "accident_related": True, "diagnosis_group": "ACCIDENT"},
    {"claim_id": "CLM-REVIEW-001", "member_name": "Maya Iyer", "member_dob": "1961-07-24", "member_id": "MBR-1003", "service_date": "2026-08-02", "amount": 50000, "submitted_payer": "EMPLOYER_PLAN", "claim_type": "INPATIENT", "accident_related": False, "diagnosis_group": "GENERAL"},
]


def seed_payload() -> dict:
    return deepcopy({"members": MEMBERS, "coverages": COVERAGES, "claims": DEMO_CLAIMS})
