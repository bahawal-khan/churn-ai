"""Phase 5 tests (`docs/ML_SPEC.md` §7-14): baseline models, the ANN, the
shared evaluation utilities, artifact save/load, and the inference
prediction pipeline.

Fixtures use small in-memory slices rather than the full 14.7k-row training
split so the suite stays fast; this exercises the exact same code paths
(`ml.models.ann.build_model`/`train_model`, `ml.models.train
._write_metadata_and_metrics`, `ml.models.inference.load_model_bundle`) that
`ml/models/train.py` uses against the full dataset, matching this repo's
existing convention (`tests/ml/test_feature_engineering.py`) of recomputing
from small fixtures rather than depending on script-produced files on disk.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from ml.config import MODELING_COLUMNS, RANDOM_SEED, RISK_THRESHOLDS, TARGET_COLUMN
from ml.models.ann import build_model, compute_class_weights, train_model
from ml.models.baselines import (
    BASELINE_SPECS,
    build_gradient_boosting,
    build_logistic_regression,
    build_random_forest,
)
from ml.models.evaluate import compute_metric_suite, select_threshold_by_f1
from ml.models.inference import ModelBundle, load_model_bundle, _risk_level
from ml.preprocessing.pipeline import build_preprocessing_pipeline
from ml.preprocessing.split import LEAKAGE_EXCLUDED_COLUMNS
from ml.models.train import build_feature_schema, _write_metadata_and_metrics

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
    """A small, hand-varied, schema-valid dataset (both classes present,
    enough rows for a stratified-safe fit) — not a real customer sample,
    just enough shape/variety to exercise the pipeline + models."""
    rng = np.random.RandomState(RANDOM_SEED)
    rows = []
    for i in range(120):
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
    train = tiny_dataset.iloc[:90].reset_index(drop=True)
    val = tiny_dataset.iloc[90:].reset_index(drop=True)
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


# --- Baseline models --------------------------------------------------------


def test_all_baseline_specs_use_balanced_class_weight():
    for model_id, algorithm, _, builder, hyperparameters in BASELINE_SPECS:
        assert hyperparameters["class_weight"] == "balanced", model_id
        model = builder()
        assert model.get_params()["class_weight"] == "balanced", model_id


def test_baseline_builders_are_seeded():
    assert build_logistic_regression().get_params()["random_state"] == RANDOM_SEED
    assert build_random_forest().get_params()["random_state"] == RANDOM_SEED
    assert build_gradient_boosting().get_params()["random_state"] == RANDOM_SEED


def test_baseline_fits_and_predicts_probabilities_in_range(tiny_transformed):
    _, X_train, y_train, X_val, _ = tiny_transformed
    model = build_logistic_regression()
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_val)[:, 1]
    assert proba.shape[0] == X_val.shape[0]
    assert np.all(proba >= 0.0) and np.all(proba <= 1.0)


# --- ANN model creation / output shape / probability range -----------------


def test_build_model_default_architecture_has_no_batchnorm_or_l2():
    model = build_model(input_dim=10)
    layer_types = [type(layer).__name__ for layer in model.layers]
    assert "BatchNormalization" not in layer_types
    assert model.layers[-1].units == 1
    assert model.layers[-1].activation.__name__ == "sigmoid"


def test_build_model_batch_norm_toggle_adds_layers():
    model = build_model(input_dim=10, use_batch_norm=True)
    layer_types = [type(layer).__name__ for layer in model.layers]
    assert layer_types.count("BatchNormalization") == 2


def test_build_model_output_shape_and_probability_range():
    model = build_model(input_dim=8)
    X = np.random.RandomState(0).normal(size=(25, 8)).astype("float32")
    preds = model.predict(X, verbose=0)
    assert preds.shape == (25, 1)
    assert np.all(preds >= 0.0) and np.all(preds <= 1.0)


def test_compute_class_weights_upweights_minority_class():
    y = np.array([0] * 80 + [1] * 20)
    weights = compute_class_weights(y)
    assert weights[1] > weights[0]


# --- Reproducibility (where practical, per Phase 5 requirement) ------------


def test_build_model_is_reproducible_with_fixed_seed():
    model_a = build_model(input_dim=6, seed=RANDOM_SEED)
    model_b = build_model(input_dim=6, seed=RANDOM_SEED)
    for w_a, w_b in zip(model_a.get_weights(), model_b.get_weights()):
        np.testing.assert_allclose(w_a, w_b)


def test_training_is_reproducible_with_fixed_seed(tiny_transformed):
    _, X_train, y_train, X_val, y_val = tiny_transformed

    model_a = build_model(input_dim=X_train.shape[1], seed=RANDOM_SEED)
    train_model(model_a, X_train, y_train, X_val, y_val, batch_size=16, max_epochs=3, seed=RANDOM_SEED, verbose=0)

    model_b = build_model(input_dim=X_train.shape[1], seed=RANDOM_SEED)
    train_model(model_b, X_train, y_train, X_val, y_val, batch_size=16, max_epochs=3, seed=RANDOM_SEED, verbose=0)

    preds_a = model_a.predict(X_val, verbose=0)
    preds_b = model_b.predict(X_val, verbose=0)
    np.testing.assert_allclose(preds_a, preds_b, rtol=1e-4, atol=1e-5)


# --- Shared evaluation utilities --------------------------------------------


def test_compute_metric_suite_perfect_separation():
    y_true = np.array([0, 0, 0, 1, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
    metrics = compute_metric_suite(y_true, y_prob, threshold=0.5)
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["confusion_matrix"] == [[3, 0], [0, 3]]
    assert "classification_report" in metrics


def test_select_threshold_by_f1_recovers_known_optimum():
    y_true = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    # A probability vector where 0.5 cleanly separates the classes and any
    # lower/higher threshold strictly hurts F1 (misclassifies a 0 or misses
    # a 1) — a threshold scan over this must land on it exactly.
    y_prob = np.array([0.05, 0.15, 0.25, 0.35, 0.65, 0.75, 0.85, 0.95])
    threshold, metrics = select_threshold_by_f1(y_true, y_prob)
    assert 0.35 < threshold <= 0.65
    assert metrics["f1"] == 1.0


def test_metric_suite_threshold_changes_predicted_class_counts():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.2, 0.4, 0.6, 0.8])
    low = compute_metric_suite(y_true, y_prob, threshold=0.1)
    high = compute_metric_suite(y_true, y_prob, threshold=0.9)
    # threshold=0.1 predicts everyone churns; threshold=0.9 predicts no one does.
    assert low["confusion_matrix"] == [[0, 2], [0, 2]]
    assert high["confusion_matrix"] == [[2, 0], [2, 0]]


# --- Risk-level / threshold behavior (inference layer) ---------------------


def test_risk_level_buckets_match_project_spec_thresholds():
    assert _risk_level(0.10, RISK_THRESHOLDS) == "low"
    assert _risk_level(0.29, RISK_THRESHOLDS) == "low"
    assert _risk_level(0.30, RISK_THRESHOLDS) == "medium"
    assert _risk_level(0.59, RISK_THRESHOLDS) == "medium"
    assert _risk_level(0.60, RISK_THRESHOLDS) == "high"
    assert _risk_level(0.95, RISK_THRESHOLDS) == "high"


class _FakeProbaModel:
    """Stands in for a fitted sklearn-like model so `ModelBundle.predict`'s
    threshold/risk-bucketing logic can be tested without a real fit."""

    def __init__(self, probabilities: np.ndarray):
        self._probabilities = probabilities

    def predict_proba(self, X):
        return np.column_stack([1 - self._probabilities, self._probabilities])


class _FakePipeline:
    def transform(self, X):
        return X


def test_model_bundle_predict_applies_threshold_and_risk_buckets():
    probabilities = np.array([0.1, 0.35, 0.55, 0.65, 0.9])
    bundle = ModelBundle(
        pipeline=_FakePipeline(),
        model=_FakeProbaModel(probabilities),
        metadata={"decision_threshold": 0.5, "risk_thresholds": RISK_THRESHOLDS},
        algorithm="logistic_regression",
    )
    X_raw = pd.DataFrame([make_row() for _ in range(5)])[MODELING_COLUMNS]

    result = bundle.predict(X_raw)

    assert list(result["predicted_class"]) == [0, 0, 1, 1, 1]
    assert list(result["risk_level"]) == ["low", "medium", "medium", "high", "high"]
    np.testing.assert_allclose(result["churn_probability"].to_numpy(), probabilities)


def test_model_bundle_predicted_class_flips_when_threshold_changes():
    probabilities = np.array([0.4, 0.45, 0.5])
    make_bundle = lambda threshold: ModelBundle(
        pipeline=_FakePipeline(),
        model=_FakeProbaModel(probabilities),
        metadata={"decision_threshold": threshold, "risk_thresholds": RISK_THRESHOLDS},
        algorithm="logistic_regression",
    )
    X_raw = pd.DataFrame([make_row() for _ in range(3)])[MODELING_COLUMNS]

    low_threshold_result = make_bundle(0.3).predict(X_raw)
    high_threshold_result = make_bundle(0.6).predict(X_raw)

    assert list(low_threshold_result["predicted_class"]) == [1, 1, 1]
    assert list(high_threshold_result["predicted_class"]) == [0, 0, 0]


# --- Artifact save/load + required metadata + leakage safeguards -----------


@pytest.fixture(scope="module")
def saved_baseline_artifact(tmp_path_factory, tiny_split, tiny_transformed):
    """Trains one real (tiny) baseline and saves it through the exact
    `ml.models.train` save path, into an isolated tmp directory — exercises
    real save code without depending on `ml/artifacts/` already existing on
    disk (that directory is gitignored and only populated by actually
    running `python -m ml.models.train`)."""
    train, _ = tiny_split
    pipeline, X_train, y_train, X_val, y_val = tiny_transformed

    model = build_logistic_regression()
    model.fit(X_train, y_train)
    y_val_prob = model.predict_proba(X_val)[:, 1]
    threshold, val_metrics = select_threshold_by_f1(y_val, y_val_prob)

    model_dir = tmp_path_factory.mktemp("logistic_regression_artifact")
    import joblib

    joblib.dump(model, model_dir / "model.joblib")
    joblib.dump(pipeline, model_dir / "pipeline.joblib")

    feature_schema = build_feature_schema(train)
    _write_metadata_and_metrics(
        model_dir,
        model_id="logistic_regression_test",
        algorithm="logistic_regression",
        hyperparameters={"class_weight": "balanced"},
        preprocessing_variant="scaled",
        feature_schema=feature_schema,
        train_row_count=len(train),
        decision_threshold=threshold,
        validation_metrics=val_metrics,
        test_metrics=None,
    )
    return model_dir


def test_saved_artifact_has_required_files(saved_baseline_artifact):
    files = {p.name for p in saved_baseline_artifact.iterdir()}
    assert {"model.joblib", "pipeline.joblib", "metadata.json", "metrics.json"} <= files


def test_saved_metadata_has_required_fields(saved_baseline_artifact):
    metadata = json.loads((saved_baseline_artifact / "metadata.json").read_text(encoding="utf-8"))
    required_fields = {
        "model_id",
        "algorithm",
        "model_type",
        "version",
        "created_at",
        "random_seed",
        "hyperparameters",
        "trained_on_dataset",
        "train_row_count",
        "feature_schema",
        "decision_threshold",
        "risk_thresholds",
        "test_evaluated",
    }
    assert required_fields <= metadata.keys()
    assert metadata["random_seed"] == RANDOM_SEED
    assert metadata["risk_thresholds"] == RISK_THRESHOLDS
    # Not yet evaluated against test data -- only `evaluate_winner_on_test`
    # (called once, after the model/threshold are already fixed) sets this.
    assert metadata["test_evaluated"] is False


def test_saved_metrics_json_has_null_test_until_final_evaluation(saved_baseline_artifact):
    metrics = json.loads((saved_baseline_artifact / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["test"] is None
    assert metrics["validation"] is not None
    assert "pr_auc" in metrics["validation"]
    assert "confusion_matrix" in metrics["validation"]


def test_feature_schema_excludes_leakage_and_provenance_columns(tiny_split):
    train, _ = tiny_split
    schema = build_feature_schema(train)
    schema_columns = {field["name"] for field in schema}
    assert schema_columns.isdisjoint(LEAKAGE_EXCLUDED_COLUMNS)
    assert schema_columns == set(MODELING_COLUMNS)


def test_feature_schema_is_ordered_per_modeling_columns(tiny_split):
    train, _ = tiny_split
    schema = build_feature_schema(train)
    assert [field["name"] for field in schema] == MODELING_COLUMNS


def test_loaded_model_bundle_predicts_on_saved_artifact(saved_baseline_artifact, tiny_split):
    _, val = tiny_split
    bundle = load_model_bundle(saved_baseline_artifact)

    assert bundle.algorithm == "logistic_regression"
    assert bundle.metadata["model_id"] == "logistic_regression_test"

    predictions = bundle.predict(val[MODELING_COLUMNS])
    assert len(predictions) == len(val)
    assert set(predictions.columns) == {"churn_probability", "predicted_class", "risk_level"}
    assert predictions["churn_probability"].between(0.0, 1.0).all()
    assert set(predictions["predicted_class"].unique()) <= {0, 1}
    assert set(predictions["risk_level"].unique()) <= {"low", "medium", "high"}
