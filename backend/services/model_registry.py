"""Loads and caches model artifact bundles from `ml/artifacts/`
(`docs/ML_SPEC.md` §14) for the backend to serve predictions from.

Phase 7 scope (no database): "the org's active model" per
`docs/PROJECT_SPEC.md` §17 collapsed to "the one baseline artifact whose
`metadata.json` has `selected_as_recommended_production_model: true`".

Phase 9 addition: `get_active_bundle_for_org` resolves the real per-org
active model from the `models` table — the org's active `company_specific`
row, else the global active `baseline_global` row, else (only if the DB has
no `models` rows at all yet, e.g. before `scripts/seed_baseline_model.py`
has run) the original Phase 7 filesystem fallback above, preserved
unchanged so existing callers/tests that never touch the DB keep working
exactly as before.

`ml.config` is imported as a module (not `from ml.config import ARTIFACTS_DIR`)
so tests can monkeypatch `ml.config.ARTIFACTS_DIR`/`ml.config.DATA_SPLITS_DIR`
to point at a temporary artifact bundle and have every lookup here honor it —
a module-level constant import would freeze the value at import time instead.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pandas as pd

from ml import config as ml_config
from ml.models.explain import TREE_ALGORITHMS, build_explainer, get_transformed_feature_names
from ml.models.inference import ModelBundle, load_model_bundle

from backend.errors.exceptions import ModelUnavailableError, NotFoundError

# RLock, not Lock: `get_active_explainer()` holds the lock while calling
# `get_active_bundle()`, which acquires it again on the same thread — a
# plain non-reentrant Lock would deadlock on that second acquisition.
_lock = threading.RLock()
_cache: dict[str, Any] = {}

# Phase 9: per-artifact-path cache for DB-resolved (org-specific or
# DB-seeded baseline) bundles — keyed separately from `_cache["bundle"]`
# since more than one such bundle can be active at once (different orgs'
# company models), unlike the single Phase 7 filesystem fallback bundle.
_org_bundle_cache: dict[str, "ModelBundle"] = {}


def reset_cache() -> None:
    """Test-only hook: clears cached bundles/explainers so a test that
    monkeypatches `ml.config.ARTIFACTS_DIR` doesn't see a stale model from a
    previous test."""
    with _lock:
        _cache.clear()
        _org_bundle_cache.clear()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _discover_model_dirs() -> list[Path]:
    artifacts_dir = ml_config.ARTIFACTS_DIR
    if not artifacts_dir.exists():
        return []
    model_dirs = []
    for child in sorted(artifacts_dir.iterdir()):
        if not child.is_dir():
            continue
        metadata_path = child / "metadata.json"
        if not metadata_path.exists():
            continue
        try:
            metadata = _read_json(metadata_path)
        except (OSError, json.JSONDecodeError):
            continue
        # Excludes non-model artifacts sharing the directory (e.g.
        # `preprocessing_dev/`, which has a metadata.json but no
        # `algorithm`/`feature_schema` — it isn't a trained model bundle).
        if "algorithm" in metadata and "feature_schema" in metadata:
            model_dirs.append(child)
    return model_dirs


def _metric_summary(metrics: dict[str, Any] | None, split: str) -> dict[str, Any] | None:
    if not metrics:
        return None
    # `metrics.json` can hold an explicit `"test": null` for a model that
    # hasn't been test-evaluated yet (`metadata.json`'s `test_evaluated`
    # flag) — a present-but-null key, not an absent one.
    split_metrics = metrics.get(split)
    if not split_metrics:
        return None
    return {
        key: split_metrics.get(key)
        for key in ("threshold", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc")
    }


def list_model_summaries() -> list[dict[str, Any]]:
    summaries = []
    for model_dir in _discover_model_dirs():
        metadata = _read_json(model_dir / "metadata.json")
        metrics_path = model_dir / "metrics.json"
        metrics = _read_json(metrics_path) if metrics_path.exists() else None
        summaries.append(
            {
                "model_id": metadata["model_id"],
                "algorithm": metadata["algorithm"],
                "model_type": metadata.get("model_type"),
                "version": metadata.get("version"),
                "created_at": metadata.get("created_at"),
                "trained_on_dataset": metadata.get("trained_on_dataset"),
                "train_row_count": metadata.get("train_row_count"),
                "decision_threshold": metadata.get("decision_threshold"),
                "risk_thresholds": metadata.get("risk_thresholds"),
                "selected_as_recommended_production_model": bool(
                    metadata.get("selected_as_recommended_production_model")
                ),
                "validation_metrics_summary": _metric_summary(metrics, "validation"),
                "test_metrics_summary": _metric_summary(metrics, "test"),
            }
        )
    return summaries


def get_model_detail(model_id: str) -> dict[str, Any]:
    for model_dir in _discover_model_dirs():
        metadata = _read_json(model_dir / "metadata.json")
        if metadata.get("model_id") != model_id:
            continue
        metrics_path = model_dir / "metrics.json"
        global_shap_path = model_dir / "global_shap.json"
        return {
            "metadata": metadata,
            "metrics": _read_json(metrics_path) if metrics_path.exists() else None,
            "global_shap": _read_json(global_shap_path) if global_shap_path.exists() else None,
        }
    raise NotFoundError(f"No model artifact found with id {model_id!r}.")


def _find_active_model_dir() -> Path | None:
    for model_dir in _discover_model_dirs():
        metadata = _read_json(model_dir / "metadata.json")
        if metadata.get("selected_as_recommended_production_model"):
            return model_dir
    return None


def get_active_bundle() -> ModelBundle:
    with _lock:
        if "bundle" in _cache:
            return _cache["bundle"]
        model_dir = _find_active_model_dir()
        if model_dir is None:
            raise ModelUnavailableError(
                "No production model artifact is currently available. Train and mark a "
                "model as the recommended production model before requesting predictions."
            )
        bundle = load_model_bundle(model_dir)
        _cache["bundle"] = bundle
        return bundle


def _load_background_sample(pipeline: Any, n: int) -> Any:
    train_path = ml_config.DATA_SPLITS_DIR / "train.csv"
    if not train_path.exists():
        raise ModelUnavailableError(
            "The training split required to build SHAP explanations for the active "
            "model is unavailable."
        )
    train_df = pd.read_csv(train_path)
    sample = train_df[ml_config.MODELING_COLUMNS].sample(n=min(n, len(train_df)), random_state=ml_config.RANDOM_SEED)
    return pipeline.transform(sample)


def get_active_explainer() -> tuple[Any, float, list[str]]:
    """Returns `(explainer, base_value, feature_names)` for the active model,
    building it once and caching it (`docs/ML_SPEC.md` §13 notes SHAP compute
    cost; explainer construction is reused across requests, per-prediction
    SHAP values are always computed fresh)."""
    with _lock:
        if "explainer" in _cache:
            return _cache["explainer"]
        bundle = get_active_bundle()
        feature_names = get_transformed_feature_names(bundle.pipeline)
        # TreeExplainer (the active random_forest_v1's family) reads its
        # baseline from the fitted trees and ignores `background` entirely —
        # only Linear/Gradient explainers need a real sample.
        background = None if bundle.algorithm in TREE_ALGORITHMS else _load_background_sample(bundle.pipeline, 100)
        explainer, base_value = build_explainer(bundle, background)
        result = (explainer, base_value, feature_names)
        _cache["explainer"] = result
        return result


# --- Phase 9: DB-backed, org-aware model resolution ------------------------


def _load_bundle_for_artifact_path(artifact_path: str) -> ModelBundle:
    with _lock:
        if artifact_path in _org_bundle_cache:
            return _org_bundle_cache[artifact_path]
        model_dir = ml_config.REPO_ROOT / artifact_path
        bundle = load_model_bundle(model_dir)
        _org_bundle_cache[artifact_path] = bundle
        return bundle


def get_active_bundle_for_org(db: Any, organization_id: int) -> tuple[ModelBundle, Any]:
    """Resolves `(bundle, models_row_or_none)` for `organization_id`
    (`docs/API.md`: "the org's active model (falls back to baseline if none
    active)"). Resolution order:

    1. The org's active `company_specific` `models` row.
    2. The active `baseline_global` `models` row (`organization_id IS NULL`).
    3. If the `models` table has no rows at all yet, the original Phase 7
       filesystem-only fallback (`get_active_bundle`) — keeps every
       DB-naive Phase 7/8 caller/test working unchanged.
    """
    from backend.db.models import Model as ModelRow

    company_row = (
        db.query(ModelRow)
        .filter(
            ModelRow.organization_id == organization_id,
            ModelRow.model_type == "company_specific",
            ModelRow.is_active.is_(True),
        )
        .one_or_none()
    )
    if company_row is not None:
        return _load_bundle_for_artifact_path(company_row.artifact_path), company_row

    baseline_row = (
        db.query(ModelRow)
        .filter(
            ModelRow.organization_id.is_(None),
            ModelRow.model_type == "baseline_global",
            ModelRow.is_active.is_(True),
        )
        .one_or_none()
    )
    if baseline_row is not None:
        return _load_bundle_for_artifact_path(baseline_row.artifact_path), baseline_row

    any_model_row_exists = db.query(ModelRow.id).first() is not None
    if any_model_row_exists:
        raise ModelUnavailableError(
            "No active model is available for this organization and no active baseline "
            "model is configured."
        )
    return get_active_bundle(), None


def ensure_baseline_model_row(db: Any) -> Any:
    """Lazily performs what `scripts/seed_baseline_model.py` does, the first
    time a prediction needs a real `models` DB row to attach to but none has
    been seeded yet — idempotent per `artifact_path` (safe to call on every
    request; a second call finds the row the first call created).

    Stores `artifact_path` as an **absolute** path rather than
    `scripts/seed_baseline_model.py`'s repo-relative convention: this also
    has to work when `ml.config.ARTIFACTS_DIR` is monkeypatched to a pytest
    `tmp_path` outside the repo tree (`tests/backend/conftest.py`), where
    `path.relative_to(REPO_ROOT)` would raise. `_load_bundle_for_artifact_path`
    resolves it via `ml_config.REPO_ROOT / artifact_path`, and joining a
    `Path` with an absolute right-hand side simply returns that absolute
    path unchanged, so both conventions load correctly.
    """
    from backend.db.models import Dataset
    from backend.db.models import Model as ModelRow

    model_dir = _find_active_model_dir()
    if model_dir is None:
        raise ModelUnavailableError(
            "No production model artifact is currently available. Train and mark a "
            "model as the recommended production model before requesting predictions."
        )
    artifact_path = str(model_dir.resolve())

    existing = db.query(ModelRow).filter(ModelRow.artifact_path == artifact_path).one_or_none()
    if existing is not None:
        return existing

    metadata = _read_json(model_dir / "metadata.json")
    metrics_path = model_dir / "metrics.json"
    metrics = _read_json(metrics_path) if metrics_path.exists() else {}

    dataset = Dataset(
        organization_id=None,
        original_filename=metadata.get("trained_on_dataset", "combined_development_dataset.csv"),
        storage_path=f"{artifact_path}/__seeded_dev_dataset__",
        source_type="dev_benchmark_ibm",
        row_count=int(metadata.get("train_row_count", 0)),
        column_schema=metadata.get("feature_schema", []),
        column_mapping=None,
        data_quality_report={
            "note": "Lazily seeded at first-prediction time; mirrors scripts/seed_baseline_model.py.",
            "checks": [],
        },
        has_target_column=True,
        target_column_name="Churn Value",
        uploaded_by_user_id=None,
    )
    db.add(dataset)
    db.flush()

    model_row = ModelRow(
        organization_id=None,
        model_type="baseline_global",
        algorithm=metadata["algorithm"],
        version=int(metadata.get("version", 1)),
        artifact_path=artifact_path,
        feature_schema=metadata.get("feature_schema", []),
        metrics=metrics,
        decision_threshold=float(metadata["decision_threshold"]),
        risk_thresholds=metadata.get("risk_thresholds", ml_config.RISK_THRESHOLDS),
        trained_on_dataset_id=dataset.id,
        training_job_id=None,
        is_active=True,
    )
    db.add(model_row)
    db.flush()
    return model_row


def get_explainer_for_bundle(bundle: ModelBundle) -> tuple[Any, float, list[str]]:
    """Same explainer-building logic as `get_active_explainer`, but for an
    arbitrary resolved bundle (org-specific or DB-seeded baseline) rather
    than only the Phase 7 filesystem-fallback bundle. Cached per artifact
    path alongside the bundle cache above."""
    cache_key = f"explainer::{bundle.metadata.get('model_id')}"
    with _lock:
        if cache_key in _cache:
            return _cache[cache_key]
        feature_names = get_transformed_feature_names(bundle.pipeline)
        background = None if bundle.algorithm in TREE_ALGORITHMS else _load_background_sample(bundle.pipeline, 100)
        explainer, base_value = build_explainer(bundle, background)
        result = (explainer, base_value, feature_names)
        _cache[cache_key] = result
        return result


def list_org_model_summaries(db: Any, organization_id: int) -> list[dict[str, Any]]:
    """DB-backed company-specific model summaries for one org, shaped like
    `list_model_summaries()`'s filesystem-based entries so a route can
    concatenate both (`docs/API.md`: "the shared baseline + the org's
    company-specific versions")."""
    from backend.db.models import Model as ModelRow

    rows = (
        db.query(ModelRow)
        .filter(ModelRow.organization_id == organization_id, ModelRow.model_type == "company_specific")
        .order_by(ModelRow.created_at.desc())
        .all()
    )
    summaries = []
    for row in rows:
        summaries.append(
            {
                "model_id": row.id,
                "algorithm": row.algorithm,
                "model_type": row.model_type,
                "version": row.version,
                "created_at": row.created_at.isoformat(),
                "trained_on_dataset_id": row.trained_on_dataset_id,
                "decision_threshold": row.decision_threshold,
                "risk_thresholds": row.risk_thresholds,
                "is_active": row.is_active,
                "validation_metrics_summary": _metric_summary(row.metrics, "validation"),
                "test_metrics_summary": _metric_summary(row.metrics, "test"),
            }
        )
    return summaries


def get_org_model_detail(db: Any, organization_id: int, model_db_id: int) -> dict[str, Any]:
    from backend.db.models import Model as ModelRow

    row = db.get(ModelRow, model_db_id)
    if row is None or row.organization_id != organization_id or row.model_type != "company_specific":
        raise NotFoundError(f"No company-specific model found with id {model_db_id!r}.")

    global_shap_path = ml_config.REPO_ROOT / row.artifact_path / "global_shap.json"
    return {
        "metadata": {
            "model_id": row.id,
            "algorithm": row.algorithm,
            "model_type": row.model_type,
            "version": row.version,
            "feature_schema": row.feature_schema,
            "decision_threshold": row.decision_threshold,
            "risk_thresholds": row.risk_thresholds,
            "trained_on_dataset_id": row.trained_on_dataset_id,
            "training_job_id": row.training_job_id,
            "is_active": row.is_active,
            "created_at": row.created_at.isoformat(),
        },
        "metrics": row.metrics,
        "global_shap": _read_json(global_shap_path) if global_shap_path.exists() else None,
    }


def activate_company_model(db: Any, *, organization_id: int, model_db_id: int, user_id: int | None) -> Any:
    """Activates a company-specific model for `organization_id`, deactivating
    the previous one in the same transaction (`docs/DATABASE_SPEC.md` §2.7:
    "at most one active company_specific model per org", enforced here since
    SQLite can't express it as a partial unique index)."""
    from backend.db.models import Model as ModelRow

    from backend.services import audit_service

    row = db.get(ModelRow, model_db_id)
    if row is None or row.organization_id != organization_id or row.model_type != "company_specific":
        raise NotFoundError(f"No company-specific model found with id {model_db_id!r}.")

    previously_active = (
        db.query(ModelRow)
        .filter(
            ModelRow.organization_id == organization_id,
            ModelRow.model_type == "company_specific",
            ModelRow.is_active.is_(True),
        )
        .all()
    )
    for other in previously_active:
        other.is_active = False
    row.is_active = True
    audit_service.write_audit_log(
        db, organization_id=organization_id, user_id=user_id, event_type="model_activated",
        event_details={"model_id": row.id},
    )
    db.commit()
    reset_cache()
    return row


def deactivate_company_model(db: Any, *, organization_id: int, model_db_id: int, user_id: int | None) -> Any:
    from backend.db.models import Model as ModelRow

    from backend.services import audit_service

    row = db.get(ModelRow, model_db_id)
    if row is None or row.organization_id != organization_id or row.model_type != "company_specific":
        raise NotFoundError(f"No company-specific model found with id {model_db_id!r}.")

    row.is_active = False
    audit_service.write_audit_log(
        db, organization_id=organization_id, user_id=user_id, event_type="model_deactivated",
        event_details={"model_id": row.id},
    )
    db.commit()
    reset_cache()
    return row
