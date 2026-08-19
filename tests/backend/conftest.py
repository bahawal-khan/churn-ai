"""Shared fixtures for `tests/backend/`.

Rather than depending on the real (gitignored, locally-trained)
`ml/artifacts/random_forest_v1/`, tests build a tiny real random-forest
artifact bundle from scratch — same code path (`build_preprocessing_pipeline`,
`build_random_forest`, `build_feature_schema`) `ml/models/train.py` uses —
and point `ml.config.ARTIFACTS_DIR` at it. This mirrors
`tests/ml/test_models.py`'s "small in-memory slices, real code paths"
convention and keeps the backend test suite independent of whether a real
training run has happened on this machine.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from alembic import command
from alembic.config import Config as AlembicConfig

from ml import config as ml_config
from ml.config import ALGORITHM_RANDOM_FOREST, MODELING_COLUMNS, RANDOM_SEED, RISK_THRESHOLDS, TARGET_COLUMN
from ml.models.baselines import build_random_forest
from ml.models.evaluate import select_threshold_by_f1
from ml.models.train import build_feature_schema
from ml.preprocessing.pipeline import build_preprocessing_pipeline

from backend.app import create_app
from backend.config import TestConfig
from backend.services import model_registry

MODEL_ID = "test_random_forest_v1"
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"

DEFAULT_SIGNUP_PAYLOAD = {
    "email": "test.user@example.com",
    "password": "StrongPass1!",
    "confirm_password": "StrongPass1!",
    "full_name": "Test User",
}


def _make_row(rng: np.random.RandomState, churn: int) -> dict:
    return {
        "Gender": rng.choice(["Female", "Male"]),
        "Senior Citizen": rng.choice(["No", "Yes"]),
        "Partner": rng.choice(["No", "Yes"]),
        "Dependents": rng.choice(["No", "Yes"]),
        "Tenure Months": int(rng.randint(0, 72)),
        "Phone Service": "Yes",
        "Multiple Lines": rng.choice(["No", "Yes"]),
        "Internet Service": rng.choice(["DSL", "Fiber optic", "No"]),
        "Online Security": rng.choice(["No", "Yes"]),
        "Online Backup": rng.choice(["No", "Yes"]),
        "Device Protection": rng.choice(["No", "Yes"]),
        "Tech Support": rng.choice(["No", "Yes"]),
        "Streaming TV": rng.choice(["No", "Yes"]),
        "Streaming Movies": rng.choice(["No", "Yes"]),
        "Contract": rng.choice(["Month-to-month", "One year", "Two year"]),
        "Paperless Billing": rng.choice(["No", "Yes"]),
        "Payment Method": rng.choice(
            ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
        ),
        "Monthly Charges": float(rng.uniform(20, 120)),
        "Total Charges": float(rng.uniform(20, 8000)),
        TARGET_COLUMN: churn,
    }


def _tiny_dataset(n: int, seed: int) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    rows = [_make_row(rng, int(rng.rand() < 0.35)) for _ in range(n)]
    return pd.DataFrame(rows)


@pytest.fixture()
def tiny_artifacts_dir(tmp_path, monkeypatch):
    """Builds one real, tiny `random_forest`-algorithm artifact bundle on
    disk and points `ml.config.ARTIFACTS_DIR` (read fresh by
    `backend.services.model_registry`, docs/note in that module) at it, so
    the API under test loads a real fitted pipeline+model, not a mock."""
    train_df = _tiny_dataset(140, RANDOM_SEED)
    val_df = _tiny_dataset(40, RANDOM_SEED + 1)

    pipeline = build_preprocessing_pipeline(scale=False)
    X_train = pipeline.fit_transform(train_df[MODELING_COLUMNS], train_df[TARGET_COLUMN])
    X_val = pipeline.transform(val_df[MODELING_COLUMNS])

    model = build_random_forest()
    model.fit(X_train, train_df[TARGET_COLUMN])

    val_proba = model.predict_proba(X_val)[:, 1]
    threshold, _ = select_threshold_by_f1(val_df[TARGET_COLUMN].to_numpy(), val_proba)

    feature_schema = build_feature_schema(train_df)

    model_dir = tmp_path / MODEL_ID
    model_dir.mkdir(parents=True)
    joblib.dump(model, model_dir / "model.joblib")
    joblib.dump(pipeline, model_dir / "pipeline.joblib")

    metadata = {
        "model_id": MODEL_ID,
        "algorithm": ALGORITHM_RANDOM_FOREST,
        "model_type": "baseline_global",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "hyperparameters": model.get_params(),
        "trained_on_dataset": "tiny_test_fixture",
        "train_row_count": len(train_df),
        "preprocessing_pipeline_variant": "unscaled",
        "feature_schema": feature_schema,
        "decision_threshold": float(threshold),
        "risk_thresholds": RISK_THRESHOLDS,
        "test_evaluated": False,
        "selected_as_recommended_production_model": True,
    }
    (model_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    metrics = {
        "validation": {"threshold": float(threshold), "accuracy": 0.7, "precision": 0.5, "recall": 0.6, "f1": 0.55, "roc_auc": 0.7, "pr_auc": 0.5},
        "test": {"threshold": float(threshold), "accuracy": 0.7, "precision": 0.5, "recall": 0.6, "f1": 0.55, "roc_auc": 0.7, "pr_auc": 0.5},
    }
    (model_dir / "metrics.json").write_text(json.dumps(metrics), encoding="utf-8")

    monkeypatch.setattr(ml_config, "ARTIFACTS_DIR", tmp_path)
    model_registry.reset_cache()
    yield tmp_path
    model_registry.reset_cache()


@pytest.fixture()
def test_db_url(tmp_path, monkeypatch):
    """Runs the real `alembic upgrade head` chain (`backend/db/migrations/`)
    against a fresh per-test SQLite file, so the test suite proves the
    migration actually builds a working schema — not just that the ORM
    models are internally consistent (`docs/DATABASE_SPEC.md` §7-8,
    "Migrations" in the Phase 8 acceptance criteria)."""
    db_path = tmp_path / "test_churnai.db"
    url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)

    alembic_cfg = AlembicConfig(str(BACKEND_DIR / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_DIR / "db" / "migrations"))
    alembic_cfg.set_main_option("path_separator", "os")
    command.upgrade(alembic_cfg, "head")

    return url


@pytest.fixture()
def app(tiny_artifacts_dir, test_db_url, tmp_path):
    class _IsolatedTestConfig(TestConfig):
        # Phase 9: uploaded datasets/generated reports are written to disk —
        # isolated per test so the suite never touches the real
        # `backend/storage/` directory or leaks files between tests.
        UPLOAD_STORAGE_DIR = tmp_path / "uploads"
        REPORTS_STORAGE_DIR = tmp_path / "reports"

    return create_app(_IsolatedTestConfig)


@pytest.fixture()
def anon_client(app):
    """An unauthenticated test client — for auth-flow tests and for
    asserting protected routes reject a missing/invalid session
    (`docs/BACKEND_SPEC.md` §4)."""
    return app.test_client()


@pytest.fixture()
def signup_payload() -> dict:
    return dict(DEFAULT_SIGNUP_PAYLOAD)


@pytest.fixture()
def client(app, signup_payload):
    """An authenticated test client (session cookie carried automatically by
    the Flask test client's cookie jar across requests). Most of this
    module's tests exercise `predictions`/`models`, which now require
    `@login_required` (Phase 8) — signing up here once, rather than in every
    test, keeps the Phase 7 tests unchanged in intent."""
    test_client = app.test_client()
    resp = test_client.post("/api/auth/signup", json=signup_payload)
    assert resp.status_code == 201, resp.get_json()
    return test_client


@pytest.fixture()
def second_client(app):
    """A second, independently-authenticated org — for cross-tenant
    isolation tests (`docs/DATABASE_SPEC.md` §6: a second org must never be
    able to read the first org's rows, including by guessing sequential
    ids)."""
    test_client = app.test_client()
    payload = {
        "email": "second.user@example.com",
        "password": "StrongPass1!",
        "confirm_password": "StrongPass1!",
        "full_name": "Second User",
    }
    resp = test_client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 201, resp.get_json()
    return test_client


@pytest.fixture()
def sample_customer_payload() -> dict:
    return {
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
