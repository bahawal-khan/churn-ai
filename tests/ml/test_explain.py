"""Phase 6 tests (`docs/ML_SPEC.md` §13): SHAP explainer dispatch, global
and local explanation construction, and the additivity property that
verifies explanations are real SHAP library output against the real fitted
model — not hard-coded or templated (ML_SPEC §13's "never hard-coded" rule).

Fixtures reuse `tests/ml/test_models.py`'s small-in-memory-dataset
convention (not the full 14.7k-row split) so the suite stays fast while
exercising the exact same code paths `ml/models/explain.py` uses.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import shap

from ml.config import (
    ALGORITHM_ANN,
    ALGORITHM_GRADIENT_BOOSTING,
    ALGORITHM_LOGISTIC_REGRESSION,
    ALGORITHM_RANDOM_FOREST,
    MODELING_COLUMNS,
    RANDOM_SEED,
    RISK_THRESHOLDS,
    SHAP_DISCLAIMER,
    TARGET_COLUMN,
)
from ml.models.ann import build_model as build_ann_model, train_model as train_ann_model
from ml.models.baselines import build_gradient_boosting, build_logistic_regression, build_random_forest
from ml.models.explain import (
    TOP_K_LOCAL_FACTORS,
    _positive_class_shap_values,
    build_explainer,
    compute_global_explanation,
    compute_local_explanation,
    get_transformed_feature_names,
    verify_additivity,
)
from ml.models.inference import ModelBundle
from ml.preprocessing.pipeline import build_preprocessing_pipeline

pytestmark = pytest.mark.filterwarnings("ignore::UserWarning")


def make_row(**overrides) -> dict:
    row = {
        "Gender": "Female",
        "Senior Citizen": "No",
        "Partner": "Yes",
        "Dependents": "No",
        "Tenure Months": 12,
        "Phone Service": "Yes",
        "Multiple Lines": "No",
        "Internet Service": "DSL",
        "Online Security": "No",
        "Online Backup": "No",
        "Device Protection": "No",
        "Tech Support": "No",
        "Streaming TV": "No",
        "Streaming Movies": "No",
        "Contract": "Month-to-month",
        "Paperless Billing": "Yes",
        "Payment Method": "Mailed check",
        "Monthly Charges": 50.0,
        "Total Charges": 600.0,
    }
    row.update(overrides)
    return row


@pytest.fixture(scope="module")
def tiny_dataset() -> pd.DataFrame:
    rng = np.random.RandomState(RANDOM_SEED)
    rows = []
    for _ in range(150):
        churn = int(rng.rand() < 0.35)
        rows.append(
            make_row(
                **{
                    "Tenure Months": int(rng.randint(1, 72)),
                    "Monthly Charges": float(rng.uniform(20, 120)),
                    "Total Charges": float(rng.uniform(20, 8000)),
                    "Contract": rng.choice(["Month-to-month", "One year", "Two year"]),
                    "Payment Method": rng.choice(
                        ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
                    ),
                    "Internet Service": rng.choice(["DSL", "Fiber optic", "No"]),
                    TARGET_COLUMN: churn,
                }
            )
        )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def tiny_split(tiny_dataset):
    train = tiny_dataset.iloc[:110].reset_index(drop=True)
    val = tiny_dataset.iloc[110:].reset_index(drop=True)
    return train, val


@pytest.fixture(scope="module")
def tiny_transformed(tiny_split):
    train, val = tiny_split
    pipeline = build_preprocessing_pipeline(scale=True)
    X_train = pipeline.fit_transform(train[MODELING_COLUMNS], train[TARGET_COLUMN])
    X_val = pipeline.transform(val[MODELING_COLUMNS])
    y_train = train[TARGET_COLUMN].to_numpy()
    y_val = val[TARGET_COLUMN].to_numpy()
    return pipeline, X_train, y_train, X_val, y_val


@pytest.fixture(scope="module")
def feature_names(tiny_transformed):
    pipeline, *_ = tiny_transformed
    return get_transformed_feature_names(pipeline)


def _bundle(pipeline, model, algorithm: str) -> ModelBundle:
    return ModelBundle(
        pipeline=pipeline,
        model=model,
        metadata={"model_id": f"{algorithm}_test", "decision_threshold": 0.5, "risk_thresholds": RISK_THRESHOLDS},
        algorithm=algorithm,
    )


@pytest.fixture(scope="module")
def rf_bundle(tiny_transformed):
    pipeline, X_train, y_train, _, _ = tiny_transformed
    model = build_random_forest()
    model.fit(X_train, y_train)
    return _bundle(pipeline, model, ALGORITHM_RANDOM_FOREST)


@pytest.fixture(scope="module")
def gb_bundle(tiny_transformed):
    pipeline, X_train, y_train, _, _ = tiny_transformed
    model = build_gradient_boosting()
    model.fit(X_train, y_train)
    return _bundle(pipeline, model, ALGORITHM_GRADIENT_BOOSTING)


@pytest.fixture(scope="module")
def lr_bundle(tiny_transformed):
    pipeline, X_train, y_train, _, _ = tiny_transformed
    model = build_logistic_regression()
    model.fit(X_train, y_train)
    return _bundle(pipeline, model, ALGORITHM_LOGISTIC_REGRESSION)


@pytest.fixture(scope="module")
def ann_bundle(tiny_transformed):
    pipeline, X_train, y_train, X_val, y_val = tiny_transformed
    model = build_ann_model(input_dim=X_train.shape[1], seed=RANDOM_SEED)
    train_ann_model(model, X_train, y_train, X_val, y_val, batch_size=16, max_epochs=3, seed=RANDOM_SEED, verbose=0)
    return _bundle(pipeline, model, ALGORITHM_ANN)


# --- get_transformed_feature_names ------------------------------------------


def test_feature_names_length_matches_transformed_columns(tiny_transformed, feature_names):
    _, X_train, *_ = tiny_transformed
    assert len(feature_names) == X_train.shape[1]


def test_feature_names_have_no_columntransformer_prefix(feature_names):
    assert all("__" not in name or name.count("__") == 0 for name in feature_names)
    assert not any(name.startswith("numeric__") or name.startswith("categorical__") for name in feature_names)


# --- build_explainer dispatch (ML_SPEC §13: per-algorithm explainer choice) -


def test_build_explainer_uses_tree_explainer_for_random_forest(rf_bundle, tiny_transformed):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(rf_bundle, X_train[:20])
    assert isinstance(explainer, shap.TreeExplainer)
    assert 0.0 <= base_value <= 1.0


def test_build_explainer_uses_tree_explainer_for_gradient_boosting(gb_bundle, tiny_transformed):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(gb_bundle, X_train[:20])
    assert isinstance(explainer, shap.TreeExplainer)
    assert isinstance(base_value, float)


def test_build_explainer_uses_linear_explainer_for_logistic_regression(lr_bundle, tiny_transformed):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(lr_bundle, X_train[:20])
    assert isinstance(explainer, shap.LinearExplainer)
    assert isinstance(base_value, float)


def test_build_explainer_uses_gradient_explainer_for_ann(ann_bundle, tiny_transformed):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(ann_bundle, X_train[:20])
    assert isinstance(explainer, shap.GradientExplainer)
    assert 0.0 <= base_value <= 1.0


def test_build_explainer_raises_for_unknown_algorithm(tiny_transformed):
    pipeline, X_train, *_ = tiny_transformed
    bundle = _bundle(pipeline, None, "unknown_algorithm")
    with pytest.raises(ValueError):
        build_explainer(bundle, X_train[:5])


# --- _positive_class_shap_values normalization ------------------------------


def test_positive_class_shap_values_slices_last_channel_for_3d():
    raw = np.zeros((4, 3, 2))
    raw[:, :, 1] = 7.0
    out = _positive_class_shap_values(raw, ALGORITHM_RANDOM_FOREST)
    assert out.shape == (4, 3)
    assert np.all(out == 7.0)


def test_positive_class_shap_values_passes_through_2d():
    raw = np.arange(12).reshape(4, 3).astype(float)
    out = _positive_class_shap_values(raw, ALGORITHM_GRADIENT_BOOSTING)
    np.testing.assert_array_equal(out, raw)


# --- verify_additivity -------------------------------------------------------


def test_verify_additivity_passes_within_tolerance():
    shap_row = np.array([0.1, -0.05, 0.02])
    base_value = 0.3
    model_output = float(shap_row.sum() + base_value)
    passed, diff = verify_additivity(shap_row, base_value, model_output, tol=1e-9)
    assert passed
    assert diff < 1e-9


def test_verify_additivity_fails_outside_tolerance():
    shap_row = np.array([0.1, -0.05, 0.02])
    passed, diff = verify_additivity(shap_row, base_value=0.3, model_output=0.9, tol=1e-3)
    assert not passed
    assert diff > 1e-3


# --- compute_global_explanation ---------------------------------------------


def test_global_explanation_random_forest_is_ranked_and_covers_all_features(rf_bundle, tiny_transformed, feature_names):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(rf_bundle, X_train)
    result = compute_global_explanation(rf_bundle, explainer, base_value, X_train, feature_names)

    assert result["disclaimer"] == SHAP_DISCLAIMER
    assert result["additivity_space"] == "probability"
    assert result["sample_size"] == X_train.shape[0]
    ranked = result["feature_importance"]
    assert len(ranked) == len(feature_names)
    assert {row["feature"] for row in ranked} == set(feature_names)
    mean_abs_values = [row["mean_abs_shap"] for row in ranked]
    assert mean_abs_values == sorted(mean_abs_values, reverse=True)
    assert [row["rank"] for row in ranked] == list(range(1, len(ranked) + 1))
    assert all(v >= 0.0 for v in mean_abs_values)


def test_global_explanation_gradient_boosting_marks_log_odds_space(gb_bundle, tiny_transformed, feature_names):
    _, X_train, *_ = tiny_transformed
    explainer, base_value = build_explainer(gb_bundle, X_train)
    result = compute_global_explanation(gb_bundle, explainer, base_value, X_train, feature_names)
    assert result["additivity_space"] == "log_odds"


# --- compute_local_explanation + real additivity check ----------------------


def test_local_explanation_random_forest_additivity_matches_predict_proba(rf_bundle, tiny_transformed, feature_names):
    _, X_train, _, X_val, _ = tiny_transformed
    explainer, base_value = build_explainer(rf_bundle, X_train)
    x_row = X_val[:1]
    model_output = float(rf_bundle.model.predict_proba(x_row)[0, 1])

    result = compute_local_explanation(
        rf_bundle, explainer, base_value, x_row, feature_names, model_output, additivity_tol=1e-6
    )

    assert result["additivity_check_passed"]
    assert result["additivity_diff"] < 1e-6
    assert result["disclaimer"] == SHAP_DISCLAIMER
    assert set(result["shap_values"].keys()) == set(feature_names)
    assert len(result["top_factors"]) == min(TOP_K_LOCAL_FACTORS, len(feature_names))

    # top_factors is ranked by |shap_value| descending and direction matches sign.
    abs_values = [abs(row["shap_value"]) for row in result["top_factors"]]
    assert abs_values == sorted(abs_values, reverse=True)
    for row in result["top_factors"]:
        if row["shap_value"] > 0:
            assert row["direction"] == "increases_risk"
        elif row["shap_value"] < 0:
            assert row["direction"] == "decreases_risk"
        else:
            assert row["direction"] == "neutral"


def test_local_explanation_random_forest_not_hardcoded_across_different_inputs(rf_bundle, tiny_transformed, feature_names):
    """Two different customers must get different SHAP explanations —
    guards against the explanation surface silently degrading into a
    templated/static value (ML_SPEC §13's "never hard-coded" rule)."""
    _, X_train, _, X_val, _ = tiny_transformed
    explainer, base_value = build_explainer(rf_bundle, X_train)

    row_a, row_b = X_val[0:1], X_val[1:2]
    out_a = float(rf_bundle.model.predict_proba(row_a)[0, 1])
    out_b = float(rf_bundle.model.predict_proba(row_b)[0, 1])

    result_a = compute_local_explanation(rf_bundle, explainer, base_value, row_a, feature_names, out_a)
    result_b = compute_local_explanation(rf_bundle, explainer, base_value, row_b, feature_names, out_b)

    assert result_a["shap_values"] != result_b["shap_values"]


def test_local_explanation_ann_additivity_is_approximately_correct(ann_bundle, tiny_transformed, feature_names):
    """GradientExplainer's expected-gradients approximation is not exactly
    additive (unlike TreeExplainer) — this only checks it lands in a
    plausible range, not exact equality (`ml/models/explain.py` module
    docstring)."""
    _, X_train, _, X_val, _ = tiny_transformed
    background = X_train[:30]
    explainer, base_value = build_explainer(ann_bundle, background)
    x_row = X_val[:1]
    model_output = float(ann_bundle.model.predict(x_row, verbose=0).reshape(-1)[0])

    result = compute_local_explanation(
        ann_bundle, explainer, base_value, x_row, feature_names, model_output, additivity_tol=0.25
    )
    assert result["additivity_diff"] < 0.25
    assert result["disclaimer"] == SHAP_DISCLAIMER


def test_shap_disclaimer_matches_project_spec_text_verbatim():
    assert SHAP_DISCLAIMER == (
        "This shows what the model learned from patterns in the data — "
        "it identifies correlation, not proven causation."
    )
