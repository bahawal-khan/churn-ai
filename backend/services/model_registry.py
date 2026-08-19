"""Loads and caches model artifact bundles from `ml/artifacts/`
(`docs/ML_SPEC.md` §14) for the backend to serve predictions from.

No database exists yet (Phase 7 scope), so "the org's active model" per
`docs/PROJECT_SPEC.md` §17 collapses to "the one baseline artifact whose
`metadata.json` has `selected_as_recommended_production_model: true`" —
company-specific model selection is DB-backed future work, not built here.

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


def reset_cache() -> None:
    """Test-only hook: clears cached bundles/explainers so a test that
    monkeypatches `ml.config.ARTIFACTS_DIR` doesn't see a stale model from a
    previous test."""
    with _lock:
        _cache.clear()


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
