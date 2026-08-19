"""Baseline models (`docs/ML_SPEC.md` §7).

Three baselines are trained before the ANN, per `ML_SPEC.md` §7 and the
Phase 5 requirement that reproducible baselines exist prior to the ANN:

- Logistic Regression (`class_weight="balanced"`) — fast, interpretable;
  coefficient signs are checkable against `ml/eda/FINDINGS.md`'s known churn
  drivers as a sanity check. Included because it is the cheapest possible
  bar the ANN must clear, and its interpretability makes it a useful
  sanity-check reference even after a stronger model is selected.
- Random Forest (`class_weight="balanced"`) — non-linear, robust to mixed
  feature types, gives a feature-importance cross-check independent of the
  ANN. Included because tabular churn data commonly has non-linear/
  interaction effects a linear model can't capture, without the training
  instability risk of a neural net.
- `HistGradientBoostingClassifier` (`class_weight="balanced"`) — ML_SPEC §7
  specifies "XGBoost if available in the deployment environment, else
  HistGradientBoostingClassifier". XGBoost is not part of this project's
  dependency set (`ml/requirements.txt`) and adding it would cost a new,
  unjustified dependency for a benefit sklearn's native gradient-boosting
  implementation already covers; `HistGradientBoostingClassifier` is used
  directly rather than treating this as a Phase 6+ decision, since ML_SPEC
  already names it as the acceptable fallback. Included as the strongest
  tabular-data baseline the ANN has to beat.

Each baseline is fit on the *already preprocessed* training arrays (the
Phase 4 `pipeline_scaled`/`pipeline_unscaled` fitted `Pipeline`, transformed
by `train.py`) — this module trains models only, it does not touch
preprocessing or splitting.

Logistic Regression uses the scaled feature set (unregularized-magnitude
coefficients are only meaningful with standardized inputs); Random Forest
and Gradient Boosting use the unscaled set (trees are scale-invariant, and
ML_SPEC §5 keeps them on the identical imputation/encoding as the scaled
branch so the baseline comparison is apples-to-apples on the same engineered
feature set, not an artifact of different preprocessing).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from ml.config import (
    ALGORITHM_GRADIENT_BOOSTING,
    ALGORITHM_LOGISTIC_REGRESSION,
    ALGORITHM_RANDOM_FOREST,
    RANDOM_SEED,
)

LOGISTIC_REGRESSION_PARAMS: dict[str, Any] = {
    "class_weight": "balanced",
    "max_iter": 1000,
    "random_state": RANDOM_SEED,
}

RANDOM_FOREST_PARAMS: dict[str, Any] = {
    "class_weight": "balanced",
    "n_estimators": 300,
    "max_depth": None,
    "min_samples_leaf": 5,
    "n_jobs": -1,
    "random_state": RANDOM_SEED,
}

GRADIENT_BOOSTING_PARAMS: dict[str, Any] = {
    "class_weight": "balanced",
    "max_iter": 300,
    "learning_rate": 0.1,
    "random_state": RANDOM_SEED,
}


def build_logistic_regression() -> LogisticRegression:
    return LogisticRegression(**LOGISTIC_REGRESSION_PARAMS)


def build_random_forest() -> RandomForestClassifier:
    return RandomForestClassifier(**RANDOM_FOREST_PARAMS)


def build_gradient_boosting() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(**GRADIENT_BOOSTING_PARAMS)


# Registry driving `train.py`'s baseline loop: (model_id, algorithm constant,
# uses_scaled_pipeline, builder, hyperparameters-for-metadata).
BASELINE_SPECS: list[tuple[str, str, bool, Any, dict[str, Any]]] = [
    (
        "logistic_regression_v1",
        ALGORITHM_LOGISTIC_REGRESSION,
        True,
        build_logistic_regression,
        LOGISTIC_REGRESSION_PARAMS,
    ),
    (
        "random_forest_v1",
        ALGORITHM_RANDOM_FOREST,
        False,
        build_random_forest,
        RANDOM_FOREST_PARAMS,
    ),
    (
        "gradient_boosting_v1",
        ALGORITHM_GRADIENT_BOOSTING,
        False,
        build_gradient_boosting,
        GRADIENT_BOOSTING_PARAMS,
    ),
]


def predict_proba_positive(model: Any, X: np.ndarray) -> np.ndarray:
    return model.predict_proba(X)[:, 1]
