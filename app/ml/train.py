from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from app.ml.features import FEATURE_NAMES
from app.ml.generate import write_dataset


def create_model(seed: int):
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=220,
            max_depth=4,
            learning_rate=0.055,
            subsample=0.85,
            colsample_bytree=0.9,
            eval_metric="logloss",
            random_state=seed,
            n_jobs=2,
        ), "XGBoost"
    except ImportError:
        return HistGradientBoostingClassifier(max_iter=180, learning_rate=0.07, max_depth=5, random_state=seed), "HistGradientBoosting fallback"


def train(dataset: Path, model_path: Path, metrics_path: Path, seed: int = 42) -> dict:
    frame = pd.read_csv(dataset)
    train_frame, test_frame = train_test_split(
        frame, test_size=0.22, random_state=seed, stratify=frame["overpayment_label"]
    )
    base_model, base_type = create_model(seed)
    model = CalibratedClassifierCV(base_model, method="sigmoid", cv=3, n_jobs=2)
    model_type = f"Calibrated {base_type}"
    model.fit(train_frame[FEATURE_NAMES], train_frame["overpayment_label"])
    probabilities = model.predict_proba(test_frame[FEATURE_NAMES])[:, 1]
    predictions = (probabilities >= 0.50).astype(int)
    tn, fp, fn, tp = confusion_matrix(test_frame["overpayment_label"], predictions).ravel()
    detected_value = float(test_frame.loc[predictions == 1, "potential_overpayment_amount"].sum())
    total_value = float(test_frame["potential_overpayment_amount"].sum())
    metrics = {
        "model_type": model_type,
        "model_version": "overpayment-risk-v2-calibrated",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": int(len(frame)),
        "training_rows": int(len(train_frame)),
        "test_rows": int(len(test_frame)),
        "positive_rate": round(float(frame["overpayment_label"].mean()), 4),
        "threshold": 0.50,
        "accuracy": round(float(accuracy_score(test_frame["overpayment_label"], predictions)), 4),
        "precision": round(float(precision_score(test_frame["overpayment_label"], predictions, zero_division=0)), 4),
        "recall": round(float(recall_score(test_frame["overpayment_label"], predictions, zero_division=0)), 4),
        "f1": round(float(f1_score(test_frame["overpayment_label"], predictions, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(test_frame["overpayment_label"], probabilities)), 4),
        "pr_auc": round(float(average_precision_score(test_frame["overpayment_label"], probabilities)), 4),
        "brier_score": round(float(brier_score_loss(test_frame["overpayment_label"], probabilities)), 4),
        "calibration": "3-fold sigmoid calibration on synthetic training data",
        "confusion_matrix": {"true_negative": int(tn), "false_positive": int(fp), "false_negative": int(fn), "true_positive": int(tp)},
        "total_test_overpayment_value": round(total_value, 2),
        "detected_test_overpayment_value": round(detected_value, 2),
        "value_weighted_recall": round(detected_value / total_value, 4) if total_value else 0.0,
        "features": FEATURE_NAMES,
        "data_statement": "Trained and evaluated only on reproducible synthetic ClaimArmor scenarios.",
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "features": FEATURE_NAMES, "metrics": metrics}, model_path)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the ClaimArmor overpayment-risk model")
    parser.add_argument("--rows", type=int, default=3000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dataset", type=Path, default=Path("artifacts/synthetic_claims.csv"))
    parser.add_argument("--model", type=Path, default=Path("artifacts/risk_model.joblib"))
    parser.add_argument("--metrics", type=Path, default=Path("artifacts/model_metrics.json"))
    parser.add_argument("--regenerate", action="store_true")
    args = parser.parse_args()
    if args.regenerate or not args.dataset.exists():
        write_dataset(args.dataset, args.rows, args.seed)
    metrics = train(args.dataset, args.model, args.metrics, args.seed)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
