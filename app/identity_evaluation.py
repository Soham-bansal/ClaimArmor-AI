from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.data_generation import generate_entity_bundle
from app.services.matching import match_member


def evaluate_identity(sample_size: int = 40, seed: int = 42, output: Path | None = Path("artifacts/identity_metrics.json")) -> dict:
    bundle = generate_entity_bundle(max(sample_size, 60), seed)
    members = bundle["members"]
    variants = bundle["identity_variants"][:sample_size]
    cases = []
    for variant in variants:
        claim = {"member_name": variant["name"], "member_dob": variant["dob"], "member_id": None, "member_email": variant.get("email"), "member_phone": variant.get("phone"), "member_address": variant.get("address")}
        result = match_member(claim, members)
        predicted = result["member_id"] if result["status"] == "MATCHED" else None
        cases.append({"expected": variant["true_member_id"], "predicted": predicted, "confidence": result["confidence"], "method": result["method"]})
    # Add explicit non-match cases to measure false-link behaviour.
    for index in range(max(5, sample_size // 5)):
        result = match_member({"member_name": f"Unknown Person {index}", "member_dob": "1910-01-01", "member_id": None, "member_email": f"unknown{index}@invalid.test", "member_phone": "", "member_address": ""}, members)
        predicted = result["member_id"] if result["status"] == "MATCHED" else None
        cases.append({"expected": None, "predicted": predicted, "confidence": result["confidence"], "method": result["method"]})
    tp = sum(item["expected"] is not None and item["predicted"] == item["expected"] for item in cases)
    fp = sum(item["predicted"] is not None and item["predicted"] != item["expected"] for item in cases)
    fn = sum(item["expected"] is not None and item["predicted"] != item["expected"] for item in cases)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
    metrics = {"generated_at": datetime.now(timezone.utc).isoformat(), "cases": len(cases), "true_positive": tp, "false_positive": fp, "false_negative": fn, "precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "splink_cases": sum(item["method"] == "splink_fellegi_sunter" for item in cases), "statement": "Evaluated only on synthetic linked identities and explicit non-match controls."}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--output", type=Path, default=Path("artifacts/identity_metrics.json"))
    args = parser.parse_args()
    print(json.dumps(evaluate_identity(args.sample_size, output=args.output), indent=2))


if __name__ == "__main__":
    main()

