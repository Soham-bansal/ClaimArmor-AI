from __future__ import annotations

import argparse
import json
import random
from datetime import date, timedelta
from pathlib import Path


FIRST = ("Aarav", "Asha", "Diya", "Ishaan", "Maya", "Neha", "Rohan", "Sara", "Vikram", "Zoya")
LAST = ("Gupta", "Iyer", "Kapoor", "Mehta", "Nair", "Patel", "Rao", "Shah", "Sharma", "Singh")
STREETS = ("Lake Road", "Park Street", "Hill Avenue", "River Drive", "Maple Lane")


def generate_entity_bundle(member_count: int = 250, seed: int = 42) -> dict:
    rng = random.Random(seed)
    employers = [{"employer_id": f"EMP-{i:03d}", "name": f"Synthetic Employer {i}", "employee_count": rng.choice([8, 16, 24, 75, 120, 800])} for i in range(1, 31)]
    providers = [{"provider_id": f"PRV-{i:03d}", "name": f"Synthetic {'Hospital' if i % 3 == 0 else 'Clinic'} {i}", "kind": "HOSPITAL" if i % 3 == 0 else "CLINIC"} for i in range(1, 26)]
    members, dependants, coverages, eligibility, claims, identity_variants = [], [], [], [], [], []
    for index in range(1, member_count + 1):
        member_id = f"MBR-{index:06d}"
        first, last = rng.choice(FIRST), rng.choice(LAST)
        name = f"{first} {last}"
        dob = date(1940, 1, 1) + timedelta(days=rng.randint(0, 65 * 365))
        employer = rng.choice(employers)
        member = {"member_id": member_id, "name": name, "dob": dob.isoformat(), "address": f"{rng.randint(1, 300)} {rng.choice(STREETS)}", "email": f"{first}.{last}.{index}@example.test".lower(), "phone": f"+1-555-{index:04d}", "employer_id": employer["employer_id"], "employment_active": rng.random() > 0.12, "disability": rng.random() < 0.08}
        members.append(member)
        if rng.random() < 0.35:
            dependent_id = f"DEP-{index:06d}"
            dependants.append({"dependent_id": dependent_id, "subscriber_member_id": member_id, "name": f"{rng.choice(FIRST)} {last}", "relationship": rng.choice(["SPOUSE", "CHILD"]), "dob": (dob + timedelta(days=rng.randint(6500, 13000))).isoformat()})
        employer_coverage = {"coverage_id": f"COV-E-{index:06d}", "member_id": member_id, "payer": "EMPLOYER_PLAN", "kind": "EMPLOYER", "start": "2025-01-01", "end": None}
        coverages.append(employer_coverage)
        age_2026 = 2026 - dob.year
        medicare = age_2026 >= 65 or member["disability"]
        if medicare:
            coverages.append({"coverage_id": f"COV-M-{index:06d}", "member_id": member_id, "payer": "MEDICARE", "kind": "MEDICARE", "start": "2025-07-01", "end": None})
        eligibility.append({"member_id": member_id, "coverage_eligible": True, "medicare_eligible": medicare, "effective_date": "2025-01-01", "termination_date": None})
        accident = rng.random() < 0.12
        if accident:
            coverages.append({"coverage_id": f"COV-A-{index:06d}", "member_id": member_id, "payer": "AUTO_INSURER", "kind": "AUTO", "start": "2026-01-01", "end": "2026-12-31"})
        if accident:
            primary = "AUTO_INSURER"
        elif medicare and member["employment_active"] and employer["employee_count"] < 20:
            primary = "MEDICARE"
        else:
            primary = "EMPLOYER_PLAN"
        claim = {"claim_id": f"ENT-CLM-{index:06d}", "member_name": name, "member_dob": dob.isoformat(), "member_id": member_id, "member_email": member["email"], "member_phone": member["phone"], "member_address": member["address"], "service_date": "2026-08-01", "amount": round(rng.uniform(250, 75000), 2), "submitted_payer": "EMPLOYER_PLAN", "claim_type": "TRAUMA" if accident else "MEDICAL", "accident_related": accident, "diagnosis_group": "ACCIDENT" if accident else "GENERAL", "provider_id": rng.choice(providers)["provider_id"], "employer_id": employer["employer_id"], "employment_active": member["employment_active"], "employer_size": employer["employee_count"], "disability": member["disability"], "relationship": "SELF", "expected_primary_payer": primary, "overpayment_label": int(primary != "EMPLOYER_PLAN")}
        claims.append(claim)
        corrupted = dict(member)
        corrupted["record_id"] = f"VAR-{index:06d}"
        corrupted["true_member_id"] = member_id
        corrupted["name"] = name[:-1] if index % 3 == 0 else name
        corrupted["email"] = "" if index % 4 == 0 else member["email"]
        corrupted["phone"] = "" if index % 5 == 0 else member["phone"]
        identity_variants.append(corrupted)
    return {"metadata": {"synthetic": True, "seed": seed, "member_count": member_count}, "employers": employers, "providers": providers, "members": members, "dependants": dependants, "coverages": coverages, "eligibility": eligibility, "claims": claims, "identity_variants": identity_variants}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--members", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/synthetic_entities.json"))
    args = parser.parse_args()
    bundle = generate_entity_bundle(args.members, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"Generated entity bundle with {args.members} members at {args.output}")


if __name__ == "__main__":
    main()

