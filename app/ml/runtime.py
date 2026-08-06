from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from app.ml.features import FEATURE_NAMES, build_features


MODEL_PATH = Path(os.getenv("CLAIMARMOR_MODEL", "artifacts/risk_model.joblib"))
METRICS_PATH = Path(os.getenv("CLAIMARMOR_MODEL_METRICS", "artifacts/model_metrics.json"))


@lru_cache(maxsize=1)
def load_bundle():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def predict(claim: dict, timeline: list[dict], match_confidence: float) -> dict | None:
    bundle = load_bundle()
    if bundle is None:
        return None
    features = build_features(claim, timeline, match_confidence)
    frame = pd.DataFrame([[features[name] for name in FEATURE_NAMES]], columns=FEATURE_NAMES)
    probability = float(bundle["model"].predict_proba(frame)[0, 1])
    contributions = sorted(
        ((name, features[name]) for name in FEATURE_NAMES), key=lambda item: abs(item[1]), reverse=True
    )[:5]
    return {
        "probability": round(probability, 4),
        "band": "HIGH" if probability >= 0.70 else "MEDIUM" if probability >= 0.35 else "LOW",
        "factors": [name.replace("_", " ").title() for name, value in contributions if value],
        "model_version": bundle["metrics"]["model_version"],
        "model_type": bundle["metrics"]["model_type"],
    }


def metrics() -> dict | None:
    if not METRICS_PATH.exists():
        return None
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))

