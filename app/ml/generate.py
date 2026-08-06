from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

from app.ml.features import build_features


SCENARIOS = (
    "single_employer",
    "single_medicare",
    "accident_auto",
    "dual_medicare_primary",
    "dual_employer_primary",
    "inactive_secondary",
    "wrong_submitted_payer",
    "identity_ambiguity",
)

FIRST_NAMES = ("Aarav", "Asha", "Diya", "Ishaan", "Maya", "Neha", "Rohan", "Sara", "Vikram", "Zoya")
LAST_NAMES = ("Gupta", "Iyer", "Kapoor", "Mehta", "Nair", "Patel", "Rao", "Shah", "Sharma", "Singh")


def _random_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def _coverage(payer: str, kind: str, active: bool = True) -> dict:
    return {
        "payer": payer,
        "kind": kind,
        "active_on_service_date": active,
        "start": "2025-01-01",
        "end": None if active else "2025-12-31",
    }


def generate_record(index: int, rng: random.Random) -> dict:
    scenario = rng.choices(SCENARIOS, weights=(24, 10, 13, 13, 13, 9, 10, 8), k=1)[0]
    service = _random_date(rng, date(2026, 1, 1), date(2026, 12, 31))
    age = rng.randint(18, 90)
    dob = service.replace(year=service.year - age)
    amount = round(min(max(rng.lognormvariate(8.3, 1.05), 100), 250_000), 2)
    name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    claim = {
        "claim_id": f"SYN-{index:06d}",
        "member_name": name,
        "member_dob": dob.isoformat(),
        "member_id": f"MBR-{index:06d}",
        "service_date": service.isoformat(),
        "amount": amount,
        "submitted_payer": "EMPLOYER_PLAN",
        "claim_type": "MEDICAL",
        "accident_related": False,
        "diagnosis_group": "GENERAL",
    }
    timeline = [_coverage("EMPLOYER_PLAN", "EMPLOYER")]
    primary = "EMPLOYER_PLAN"
    overpayment = 0
    match_confidence = round(rng.uniform(0.94, 1.0), 4)

    if scenario == "single_medicare":
        timeline = [_coverage("MEDICARE", "MEDICARE")]
        claim["submitted_payer"] = "MEDICARE"
        primary = "MEDICARE"
    elif scenario == "accident_auto":
        timeline.append(_coverage("AUTO_INSURER", "AUTO"))
        claim["accident_related"] = True
        claim["claim_type"] = "TRAUMA"
        claim["diagnosis_group"] = "ACCIDENT"
        primary = "AUTO_INSURER"
        overpayment = 1
    elif scenario == "dual_medicare_primary":
        timeline.append(_coverage("MEDICARE", "MEDICARE"))
        primary = "MEDICARE"
        overpayment = 1
    elif scenario == "dual_employer_primary":
        timeline.append(_coverage("MEDICARE", "MEDICARE"))
        primary = "EMPLOYER_PLAN"
    elif scenario == "inactive_secondary":
        timeline.append(_coverage("MEDICARE", "MEDICARE", active=False))
    elif scenario == "wrong_submitted_payer":
        timeline = [_coverage("MEDICARE", "MEDICARE")]
        claim["submitted_payer"] = "EMPLOYER_PLAN"
        primary = "MEDICARE"
        overpayment = 1
    elif scenario == "identity_ambiguity":
        claim["member_id"] = None
        match_confidence = round(rng.uniform(0.62, 0.84), 4)

    # Controlled label noise prevents the model from merely memorising scenario rules.
    if rng.random() < 0.025:
        overpayment = 1 - overpayment
    expected_route = "HOLD" if overpayment else ("HUMAN_REVIEW" if scenario in {"dual_employer_primary", "identity_ambiguity"} else "CLEAR")
    features = build_features(claim, timeline, match_confidence)
    return {
        **claim,
        **features,
        "scenario": scenario,
        "expected_primary_payer": primary,
        "expected_route": expected_route,
        "overpayment_label": overpayment,
        "potential_overpayment_amount": round(amount * (rng.uniform(0.35, 0.95) if overpayment else 0), 2),
    }


def generate_dataset(rows: int = 3000, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    return [generate_record(index, rng) for index in range(1, rows + 1)]


def write_dataset(output: Path, rows: int = 3000, seed: int = 42) -> Path:
    records = generate_dataset(rows, seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic ClaimArmor COB training data")
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("artifacts/synthetic_claims.csv"))
    args = parser.parse_args()
    path = write_dataset(args.output, args.rows, args.seed)
    print(f"Generated {args.rows} synthetic claims at {path}")


if __name__ == "__main__":
    main()

