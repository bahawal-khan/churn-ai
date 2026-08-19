"""Phase 6 SHAP explainability (`docs/ML_SPEC.md` §13, `docs/PROJECT_SPEC.md`
§15): global (per-model) and local (per-prediction) SHAP explanations for
the artifact bundles built in `ml/models/train.py`.

Explainer type is chosen per algorithm family, not fixed in advance
(ML_SPEC §13): `shap.TreeExplainer` for Random Forest/Gradient Boosting,
`shap.LinearExplainer` for Logistic Regression, `shap.GradientExplainer`
for the ANN. `shap.GradientExplainer` (rather than `DeepExplainer`) is used
for the ANN because it is the explainer that actually runs cleanly against
this repo's TF 2.21/Keras 3 `ann_v1` artifact — verified directly against
the real saved model before writing this module, not assumed.

**Output-space caveat, verified empirically per algorithm and worth stating
plainly (mirrors the honesty standard `ml/models/MODELS.md` §10 sets for
the Random Forest artifact-size tradeoff):** SHAP values are only exactly
additive (`sum(shap_values) + base_value == model_output`) in the space the
underlying explainer natively operates in.
  - `TreeExplainer` on `RandomForestClassifier` (`random_forest_v1`, the
    actual selected/active model, `docs/ML_SPEC.md` §7/§12): additive
    directly in **predicted-probability** space. Verified to match
    `predict_proba` to floating-point precision.
  - `TreeExplainer` on `HistGradientBoostingClassifier`
    (`gradient_boosting_v1`): additive in **raw decision/log-odds** space —
    `sigmoid(sum(shap_values) + base_value) == predict_proba`, not the sum
    directly.
  - `LinearExplainer` on `LogisticRegression` (`logistic_regression_v1`):
    same log-odds-space additivity as above (`decision_function`, not
    `predict_proba`, is what's additive).
  - `GradientExplainer` on the ANN (`ann_v1`): additive only
    *approximately* (expected-gradients sampling approximation over the
    background set) even though the model's own output is already a
    probability — verified empirically to be within a few percentage
    points, not exact like the tree/linear cases.
This module does not attempt to force every algorithm's output into a
single normalized probability-contribution space (that would misrepresent
individual feature contributions for the log-odds-additive models); each
`global_shap.json`/local-explanation payload carries `additivity_space` so
a consumer knows which space its numbers are in. Only `random_forest_v1` is
actually the selected production model right now, so this caveat is latent
except for `additivity_diff`/`additivity_check_passed`, exercised for real
against the real artifact.

Run directly: `python -m ml.models.explain`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

from ml.config import (
    ALGORITHM_ANN,
    ALGORITHM_GRADIENT_BOOSTING,
    ALGORITHM_LOGISTIC_REGRESSION,
    ALGORITHM_RANDOM_FOREST,
    ARTIFACTS_DIR,
    DATA_SPLITS_DIR,
    MODELING_COLUMNS,
    RANDOM_SEED,
    SHAP_DISCLAIMER,
    TARGET_COLUMN,
)
from ml.models.evaluate import write_json
from ml.models.inference import ModelBundle, load_model_bundle

# Algorithms whose winning artifact would use shap.TreeExplainer (ML_SPEC §13).
TREE_ALGORITHMS = {ALGORITHM_RANDOM_FOREST, ALGORITHM_GRADIENT_BOOSTING}

# Algorithms whose explainer is exactly additive in predicted-probability
# space (module docstring above) vs. only in raw/log-odds space or only
# approximately. Used to pick a realistic additivity tolerance and to
# stamp the payload with which space its numbers are in.
PROBABILITY_ADDITIVE_ALGORITHMS = {ALGORITHM_RANDOM_FOREST}
LOGIT_ADDITIVE_ALGORITHMS = {ALGORITHM_GRADIENT_BOOSTING, ALGORITHM_LOGISTIC_REGRESSION}

# Representative sample size for the global summary — not the full
# train+val set, for compute-cost reasons on free-tier hosting (ML_SPEC §13).
GLOBAL_SAMPLE_SIZE = 2000
# Background/reference distribution size for LinearExplainer/GradientExplainer.
BACKGROUND_SAMPLE_SIZE = 100
# How many ranked features a local explanation's `top_factors` carries.
TOP_K_LOCAL_FACTORS = 10


def get_transformed_feature_names(pipeline: Any) -> list[str]:
    """Human-readable post-transform feature names, in the exact order the
    fitted `ColumnTransformer` emits columns. The already-fitted production
    `pipeline.joblib` was built with sklearn's default
    `verbose_feature_names_out=True`, so raw names are prefixed
    `numeric__`/`categorical__` — stripped here for display rather than by
    reaching into and refitting the pipeline (`ml/preprocessing/pipeline.py`
    is out of this phase's scope)."""
    raw_names = pipeline.named_steps["column_transform"].get_feature_names_out()
    return [name.split("__", 1)[1] if "__" in name else name for name in raw_names]


def build_explainer(bundle: ModelBundle, background: np.ndarray) -> tuple[Any, float]:
    """Returns `(explainer, base_value)` for `bundle.algorithm`
    (ML_SPEC §13's per-family explainer choice). `base_value` is the
    explainer's expected/baseline output — read from `explainer.expected_value`
    where the explainer provides one (Tree/Linear); `shap.GradientExplainer`
    does not expose one, so it's approximated as the model's mean predicted
    output over `background` (the standard expected-gradients baseline)."""
    if bundle.algorithm in TREE_ALGORITHMS:
        explainer = shap.TreeExplainer(bundle.model)
        base_value = float(np.asarray(explainer.expected_value).ravel()[-1])
    elif bundle.algorithm == ALGORITHM_LOGISTIC_REGRESSION:
        masker = shap.maskers.Independent(background)
        explainer = shap.LinearExplainer(bundle.model, masker)
        base_value = float(np.asarray(explainer.expected_value).ravel()[-1])
    elif bundle.algorithm == ALGORITHM_ANN:
        explainer = shap.GradientExplainer(bundle.model, background)
        base_value = float(np.mean(bundle.model.predict(background, verbose=0)))
    else:
        raise ValueError(f"No SHAP explainer mapping for algorithm: {bundle.algorithm!r}")
    return explainer, base_value


def _positive_class_shap_values(raw_sv: Any, algorithm: str) -> np.ndarray:
    """Normalizes each explainer family's raw `shap_values` output — shape
    verified empirically per algorithm (module docstring) — down to a
    single `(n_samples, n_features)` array of the positive ("churn")
    class's contribution.

    - `RandomForestClassifier` via `TreeExplainer`: `(n, features, 2)` —
      one channel per class; take the churn (last) channel.
    - The ANN via `GradientExplainer`: `(n, features, 1)` — single sigmoid
      output; the same last-channel slice degenerately selects it.
    - `HistGradientBoostingClassifier` via `TreeExplainer` and
      `LogisticRegression` via `LinearExplainer`: already `(n, features)`.
    """
    arr = np.asarray(raw_sv)
    if arr.ndim == 3:
        return arr[:, :, -1]
    return arr


def verify_additivity(
    shap_row: np.ndarray, base_value: float, model_output: float, tol: float
) -> tuple[bool, float]:
    """Confirms a local explanation is the actual SHAP library output
    against the actual model/input, not a hard-coded or approximated
    stand-in (ML_SPEC §13's "never hard-coded" rule): SHAP's defining
    property is that per-feature contributions sum to
    `model_output - base_value`. Returns `(passed, absolute_diff)`."""
    diff = float(abs((float(np.sum(shap_row)) + base_value) - model_output))
    return diff <= tol, diff


def compute_global_explanation(
    bundle: ModelBundle,
    explainer: Any,
    base_value: float,
    X_sample: np.ndarray,
    feature_names: list[str],
) -> dict[str, Any]:
    """Global SHAP summary (ML_SPEC §13): mean(|SHAP|) per feature over a
    representative sample, ranked descending — powers the Dashboard's "Top
    Churn Drivers" and the Analytics page."""
    raw_sv = explainer.shap_values(X_sample)
    class_sv = _positive_class_shap_values(raw_sv, bundle.algorithm)

    mean_abs = np.abs(class_sv).mean(axis=0)
    mean_signed = class_sv.mean(axis=0)

    ranked = sorted(
        (
            {
                "feature": name,
                "mean_abs_shap": float(mean_abs[i]),
                "mean_signed_shap": float(mean_signed[i]),
            }
            for i, name in enumerate(feature_names)
        ),
        key=lambda row: row["mean_abs_shap"],
        reverse=True,
    )
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank

    additivity_space = (
        "probability"
        if bundle.algorithm in PROBABILITY_ADDITIVE_ALGORITHMS
        else "log_odds" if bundle.algorithm in LOGIT_ADDITIVE_ALGORITHMS else "approximate_probability"
    )

    return {
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "explainer_type": type(explainer).__name__,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": int(X_sample.shape[0]),
        "base_value": base_value,
        "additivity_space": additivity_space,
        "feature_importance": ranked,
        "disclaimer": SHAP_DISCLAIMER,
    }


def compute_local_explanation(
    bundle: ModelBundle,
    explainer: Any,
    base_value: float,
    x_row: np.ndarray,
    feature_names: list[str],
    model_output: float,
    additivity_tol: float = 1e-3,
) -> dict[str, Any]:
    """Single-prediction local SHAP explanation (ML_SPEC §13), shaped to
    match `docs/DATABASE_SPEC.md` §2.10 `explanations` columns directly:
    `shap_values` (per-feature), `base_value`, `top_factors` (ranked,
    precomputed for fast UI rendering)."""
    raw_sv = explainer.shap_values(x_row)
    class_sv = _positive_class_shap_values(raw_sv, bundle.algorithm)[0]

    passed, diff = verify_additivity(class_sv, base_value, model_output, additivity_tol)

    shap_values_map = {name: float(value) for name, value in zip(feature_names, class_sv)}
    ranked = sorted(
        (
            {
                "feature": name,
                "shap_value": float(value),
                "direction": "increases_risk" if value > 0 else "decreases_risk" if value < 0 else "neutral",
            }
            for name, value in zip(feature_names, class_sv)
        ),
        key=lambda row: abs(row["shap_value"]),
        reverse=True,
    )

    return {
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "model_output": float(model_output),
        "base_value": base_value,
        "shap_values": shap_values_map,
        "top_factors": ranked[:TOP_K_LOCAL_FACTORS],
        "additivity_check_passed": passed,
        "additivity_diff": diff,
        "disclaimer": SHAP_DISCLAIMER,
    }


def _load_splits() -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_SPLITS_DIR / "train.csv")
    val = pd.read_csv(DATA_SPLITS_DIR / "val.csv")
    return train, val


def main() -> None:
    train_df, val_df = _load_splits()

    metadata_path = ARTIFACTS_DIR / "random_forest_v1" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if not metadata.get("selected_as_recommended_production_model"):
        raise RuntimeError(
            "random_forest_v1 is not marked as the selected production model in its "
            "metadata.json — refusing to build the SHAP artifact for a stale assumption "
            "about which model won (ML_SPEC §13: explainer choice tracks the actual "
            "promoted model, not a fixed guess)."
        )

    model_id = "random_forest_v1"
    bundle = load_model_bundle(ARTIFACTS_DIR / model_id)
    feature_names = get_transformed_feature_names(bundle.pipeline)

    background_df = train_df[MODELING_COLUMNS].sample(n=BACKGROUND_SAMPLE_SIZE, random_state=RANDOM_SEED)
    background = bundle.pipeline.transform(background_df)

    combined = pd.concat([train_df, val_df], ignore_index=True)
    sample_df = combined.sample(n=min(GLOBAL_SAMPLE_SIZE, len(combined)), random_state=RANDOM_SEED)
    X_sample = bundle.pipeline.transform(sample_df[MODELING_COLUMNS])

    explainer, base_value = build_explainer(bundle, background)

    print(f"=== Global SHAP summary ({model_id}, {type(explainer).__name__}, n={len(sample_df)}) ===")
    global_result = compute_global_explanation(bundle, explainer, base_value, X_sample, feature_names)
    write_json(global_result, ARTIFACTS_DIR / model_id / "global_shap.json")
    top5 = global_result["feature_importance"][:5]
    for row in top5:
        print(f"  #{row['rank']} {row['feature']}: mean|SHAP|={row['mean_abs_shap']:.4f}")

    print("=== Example local SHAP explanation (a validation-set churner) ===")
    churner = val_df[val_df[TARGET_COLUMN] == 1].iloc[[0]]
    x_row = bundle.pipeline.transform(churner[MODELING_COLUMNS])
    model_output = float(bundle.predict_proba(churner[MODELING_COLUMNS])[0])
    local_result = compute_local_explanation(
        bundle, explainer, base_value, x_row, feature_names, model_output, additivity_tol=1e-3
    )
    print(f"  churn_probability={model_output:.4f} base_value={base_value:.4f}")
    print(f"  additivity_check_passed={local_result['additivity_check_passed']} diff={local_result['additivity_diff']:.6f}")
    for row in local_result["top_factors"][:5]:
        print(f"  {row['feature']}: shap={row['shap_value']:+.4f} ({row['direction']})")

    write_json(
        local_result,
        Path(__file__).resolve().parent / "figures" / "example_local_shap.json",
    )


if __name__ == "__main__":
    main()
