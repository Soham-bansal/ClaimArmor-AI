from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, average_precision_score, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from app.ml.features import FEATURE_NAMES
from app.services.policy import evaluate_retrieval


DEFAULT_DATASET = Path("artifacts/synthetic_claims.csv")
DEFAULT_MODEL = Path("artifacts/risk_model.joblib")
DEFAULT_OUTPUT = Path("artifacts/system_evaluation.json")


def _score(name: str, labels, predictions, probabilities, amounts) -> dict:
    tn, fp, fn, tp = confusion_matrix(labels, predictions).ravel()
    prevented = float(amounts[(predictions == 1) & (labels == 1)].sum())
    total_leakage = float(amounts[labels == 1].sum())
    reviews = int(predictions.sum())
    false_positive_cost = float(fp * 75)
    review_cost = float(reviews * 35)
    operating_cost = float(len(labels) * 0.20)
    return {
        "approach": name,
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision_score(labels, predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(labels, predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(labels, predictions, zero_division=0)), 4),
        "pr_auc": round(float(average_precision_score(labels, probabilities)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "review_rate": round(reviews / len(labels), 4),
        "detected_synthetic_leakage": round(prevented, 2),
        "total_synthetic_leakage": round(total_leakage, 2),
        "value_weighted_recall": round(prevented / total_leakage, 4) if total_leakage else 0,
        "simulated_review_cost": round(review_cost, 2),
        "simulated_false_positive_cost": round(false_positive_cost, 2),
        "simulated_net_benefit": round(prevented - review_cost - false_positive_cost - operating_cost, 2),
    }


def evaluate(dataset_path: Path = DEFAULT_DATASET, model_path: Path = DEFAULT_MODEL, output_path: Path | None = DEFAULT_OUTPUT) -> dict:
    complete_frame = pd.read_csv(dataset_path)
    _, frame = train_test_split(
        complete_frame,
        test_size=0.22,
        random_state=42,
        stratify=complete_frame["overpayment_label"],
    )
    bundle = joblib.load(model_path)
    probabilities = bundle["model"].predict_proba(frame[FEATURE_NAMES])[:, 1]
    labels = frame["overpayment_label"].astype(int).to_numpy()
    amounts = frame["potential_overpayment_amount"]

    definite_rule = (
        ((frame["accident_related"] == 1) & (frame["has_auto"] == 1))
        | ((frame["has_medicare"] == 1) & (frame["has_employer"] == 0) & (frame["submitted_is_employer"] == 1))
    )
    overlap_rule = (frame["coverage_overlap"] == 1) & (frame["has_medicare"] == 1) & (frame["has_employer"] == 1)
    rules_predictions = (definite_rule | overlap_rule).astype(int).to_numpy()
    rules_probability = rules_predictions * 0.85 + (1 - rules_predictions) * 0.10
    ml_predictions = (probabilities >= 0.50).astype(int)
    hybrid_predictions = (definite_rule | (overlap_rule & (probabilities >= 0.35)) | (probabilities >= 0.72)).astype(int).to_numpy()
    hybrid_probability = probabilities.copy()
    hybrid_probability[definite_rule.to_numpy()] = 0.99
    hybrid_probability[overlap_rule.to_numpy()] = hybrid_probability[overlap_rule.to_numpy()].clip(min=0.65)

    approaches = [
        _score("Rules only", labels, rules_predictions, rules_probability, amounts),
        _score("ML only", labels, ml_predictions, probabilities, amounts),
        _score("Hybrid rules + ML + review gate", labels, hybrid_predictions, hybrid_probability, amounts),
    ]
    retrieval = evaluate_retrieval()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": int(len(complete_frame)),
        "evaluation_rows": int(len(frame)),
        "evaluation_split": "Reproduced 22% stratified holdout (random seed 42); these rows were not used to fit the persisted model.",
        "dataset": str(dataset_path),
        "model_version": bundle["metrics"]["model_version"],
        "approaches": approaches,
        "retrieval": {"hit_at_4": retrieval["hit_at_4"], "mrr": retrieval["mrr"], "cases": retrieval["cases"]},
        "assumptions": {"review_cost_per_flag": 35, "false_positive_delay_cost": 75, "processing_cost_per_claim": 0.20},
        "statement": "All performance and financial results are measured on synthetic scenarios and documented assumptions, not real payer outcomes.",
    }
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def load_evaluation(path: Path = DEFAULT_OUTPUT) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ClaimArmor decision approaches")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.dataset, args.model, args.output), indent=2))


if __name__ == "__main__":
    main()
