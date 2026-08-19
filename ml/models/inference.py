"""Model artifact loading + inference (`docs/ML_SPEC.md` §14).

Provides the single code path both `train.py`'s post-save sanity check and
`tests/ml/test_models.py` use to confirm a saved artifact bundle
(`model.*` + `pipeline.joblib` + `metadata.json`) loads fresh from disk and
produces a prediction — the same load path a later Flask `services/` layer
would use (`docs/BACKEND_SPEC.md`) to serve predictions, built now so "the
final saved model can be loaded and used for inference" (Phase 5 acceptance
criterion) is exercised by code, not just claimed.

Risk-level bucketing here mirrors `docs/PROJECT_SPEC.md` §18's fixed
thresholds (`ml.config.RISK_THRESHOLDS`) but reads them from the artifact's
own `metadata.json` rather than the config constant directly, since §18
notes thresholds are meant to become per-model-editable in a future phase —
this keeps that door open without doing the Phase 6+ work of building an
editing UI now.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.config import ALGORITHM_ANN, MODELING_COLUMNS, RISK_THRESHOLDS


def _risk_level(probability: float, risk_thresholds: dict[str, float]) -> str:
    if probability < risk_thresholds["low_max"]:
        return "low"
    if probability < risk_thresholds["medium_max"]:
        return "medium"
    return "high"


class ModelBundle:
    """A fitted preprocessing pipeline + fitted model + its metadata, loaded
    together so they can never be mismatched (ML_SPEC §14)."""

    def __init__(self, pipeline: Any, model: Any, metadata: dict[str, Any], algorithm: str):
        self.pipeline = pipeline
        self.model = model
        self.metadata = metadata
        self.algorithm = algorithm

    def predict_proba(self, X_raw: pd.DataFrame) -> np.ndarray:
        """`X_raw` must contain `ml.config.MODELING_COLUMNS` (raw schema
        columns, pre-feature-engineering) — feature engineering and
        preprocessing both happen inside `self.pipeline`."""
        X = self.pipeline.transform(X_raw[MODELING_COLUMNS])
        if self.algorithm == ALGORITHM_ANN:
            return np.asarray(self.model.predict(X, verbose=0)).reshape(-1)
        return self.model.predict_proba(X)[:, 1]

    def predict(self, X_raw: pd.DataFrame) -> pd.DataFrame:
        proba = self.predict_proba(X_raw)
        threshold = float(self.metadata["decision_threshold"])
        risk_thresholds = self.metadata.get("risk_thresholds", RISK_THRESHOLDS)
        predicted_class = (proba >= threshold).astype(int)
        risk_level = [_risk_level(float(p), risk_thresholds) for p in proba]
        return pd.DataFrame(
            {
                "churn_probability": proba,
                "predicted_class": predicted_class,
                "risk_level": risk_level,
            }
        )


def load_model_bundle(model_dir: Path) -> ModelBundle:
    model_dir = Path(model_dir)
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    algorithm = metadata["algorithm"]
    pipeline = joblib.load(model_dir / "pipeline.joblib")

    if algorithm == ALGORITHM_ANN:
        from tensorflow import keras

        model = keras.models.load_model(model_dir / "model.keras")
    else:
        model = joblib.load(model_dir / "model.joblib")

    return ModelBundle(pipeline=pipeline, model=model, metadata=metadata, algorithm=algorithm)
