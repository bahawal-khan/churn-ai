"""Company-specific training orchestration (`docs/PROJECT_SPEC.md` §16,
`docs/BACKEND_SPEC.md` §3, `docs/ML_SPEC.md` §6-14).

Reuses the same modeling building blocks the dev pipeline uses
(`ml.preprocessing.pipeline`, `ml.models.baselines`, `ml.models.ann`,
`ml.models.evaluate`, `ml.models.explain`, and the pure/reusable
`ml.models.train.build_feature_schema`/`select_winner` helpers) but writes
to a per-job artifact directory under `ml/artifacts/company_{org}_{job}_*`
— never the shared dev-pipeline paths (`ml/artifacts/random_forest_v1`
etc.) — and drives a `training_jobs` DB row's state machine instead of a
one-off script.

**Execution model:** synchronous, within the `POST /api/training/jobs`
request (`docs/BACKEND_SPEC.md` §3's sanctioned fallback: "keeping work
synchronous within request-time limits ... if [scheduled/always-on tasks
are] not available" — chosen since no PythonAnywhere account is provisioned
yet to verify those options against). `training_jobs.status` is still
written to the DB at every step, so `GET /api/training/jobs/:id` is a
correct polling contract a later phase can point at real background
execution without an API change — recorded here as this section's required
addendum.

**Algorithm scope:** all 4 algorithms (Logistic Regression, Random Forest,
Gradient Boosting, ANN) are trained and compared, winner picked by the same
validation PR-AUC/recall rule as the dev pipeline (`ml.models.train
.select_winner`) — required by `PROJECT_SPEC.md`'s binding cross-cutting
rule ("every phase that evaluates models must present the full comparison
table... a baseline outperforming the ANN is expected, not a bug").

**Schema-mapping limitation (documented, not silently worked around):**
same as `dataset_service` — the dataset must already contain
`ml.config.MODELING_COLUMNS` under their exact schema-contract names. The
column-mapping UI that lets a user reconcile differently-named columns is
Phase 10 (frontend) work.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session as DBSession

from ml import config as ml_config
from ml.config import ALGORITHM_ANN, MODELING_COLUMNS, RANDOM_SEED, RISK_THRESHOLDS, TEST_RATIO, VAL_RATIO
from ml.models.ann import build_model as build_ann_model, compute_class_weights, train_model as train_ann_model
from ml.models.baselines import BASELINE_SPECS, predict_proba_positive
from ml.models.evaluate import compute_metric_suite, select_threshold_by_f1
from ml.models.explain import (
    TREE_ALGORITHMS,
    build_explainer,
    compute_global_explanation,
    get_transformed_feature_names,
)
from ml.models.inference import load_model_bundle
from ml.models.train import build_feature_schema, select_winner
from ml.preprocessing.pipeline import build_preprocessing_pipeline

from backend.db.models import Dataset, Model, TrainingJob
from backend.errors.exceptions import TrainingLabelsRequiredError
from backend.services import audit_service

# `docs/ML_SPEC.md` §6: "if a company's dataset is too small to stratify
# safely (e.g., fewer than ~200 rows or a target class with fewer than ~20
# positive examples), the UI surfaces a clear warning ... rather than
# silently training an unreliable model."
MIN_ROWS_FOR_SPLIT = 200
MIN_POSITIVE_CLASS_COUNT = 20


def load_dataset_dataframe(dataset: Dataset) -> pd.DataFrame:
    return pd.read_csv(dataset.storage_path)


def _binarize_target(df: pd.DataFrame, target_column: str) -> pd.Series:
    """Mirrors `ml.data_quality.validator.DataQualityValidator`'s own binary
    target check (0/1 only, `ml.config.TARGET_COLUMN` convention) — raises
    `TrainingLabelsRequiredError` with the exact blocking message
    `docs/PROJECT_SPEC.md` §16 specifies."""
    if target_column not in df.columns:
        raise TrainingLabelsRequiredError(
            "Training requires historical outcomes (which customers churned) so the model "
            "can learn patterns. Your file doesn't appear to include a churn/outcome column. "
            "You can still use the baseline model for predictions, or re-upload a file that "
            "includes historical churn results.",
            details={"reason": "target_column_not_found", "target_column": target_column},
        )

    numeric = pd.to_numeric(df[target_column].astype(str).str.strip(), errors="coerce")
    if numeric.isna().any() or not set(numeric.dropna().unique()) <= {0.0, 1.0}:
        raise TrainingLabelsRequiredError(
            "Training requires historical outcomes (which customers churned) so the model "
            "can learn patterns. The selected column must contain only 0/1 values indicating "
            "whether each customer churned. You can still use the baseline model for "
            "predictions, or re-upload a file that includes historical churn results.",
            details={"reason": "target_column_not_binary", "target_column": target_column},
        )
    if numeric.nunique() < 2:
        raise TrainingLabelsRequiredError(
            "Training requires historical outcomes (which customers churned) so the model "
            "can learn patterns. The selected column only has one outcome value in this file "
            "(no churned or no retained examples). You can still use the baseline model for "
            "predictions, or re-upload a file with both outcomes represented.",
            details={"reason": "target_column_single_class", "target_column": target_column},
        )
    return numeric.astype(int)


def validate_training_preconditions(dataset: Dataset, target_column: str) -> None:
    """`POST /api/training/jobs` (`docs/API.md`): "validates target column
    exists & is binary ... before any `training_jobs` row is created."""
    df = load_dataset_dataframe(dataset)
    _binarize_target(df, target_column)
    missing_columns = [c for c in MODELING_COLUMNS if c not in df.columns]
    if missing_columns:
        raise TrainingLabelsRequiredError(
            "This dataset is missing column(s) required for training: "
            + ", ".join(missing_columns)
            + ". Re-upload a file that includes the full schema, or use the baseline model "
            "for predictions instead.",
            details={"reason": "missing_modeling_columns", "missing_columns": missing_columns},
        )


def _next_version(db: DBSession, organization_id: int) -> int:
    existing = (
        db.query(Model)
        .filter(Model.organization_id == organization_id, Model.model_type == "company_specific")
        .all()
    )
    return (max((m.version for m in existing), default=0)) + 1


def run_training_job(db: DBSession, *, job: TrainingJob, dataset: Dataset, target_column: str, user_id: int | None) -> None:
    """Advances `job` through the full state machine
    (`docs/DATABASE_SPEC.md` §2.8) synchronously. Never raises — any
    failure is captured into `job.status = 'failed'` /
    `job.status_message` (`docs/BACKEND_SPEC.md` §7's `TRAINING_FAILED`
    category maps to this terminal job state, not an HTTP error, since the
    job resource itself is what the polling contract represents)."""
    try:
        job.status = "validating"
        job.started_at = datetime.utcnow()
        db.commit()

        df = load_dataset_dataframe(dataset)
        target = _binarize_target(df, target_column)

        row_count = len(df)
        positive_count = int(target.sum())
        small_dataset_warning = None
        if row_count < MIN_ROWS_FOR_SPLIT or positive_count < MIN_POSITIVE_CLASS_COUNT:
            small_dataset_warning = (
                f"This dataset ({row_count} rows, {positive_count} positive examples) is small "
                "for a reliable train/validation/test split; treat this model's metrics with "
                "caution (docs/ML_SPEC.md §6)."
            )

        missing_columns = [c for c in MODELING_COLUMNS if c not in df.columns]
        if missing_columns:
            raise ValueError("Missing required modeling column(s): " + ", ".join(missing_columns))

        job.status = "preprocessing"
        db.commit()

        model_df = df[MODELING_COLUMNS].copy()
        model_df["__target__"] = target.to_numpy()

        train_df, temp_df = train_test_split(
            model_df, test_size=(VAL_RATIO + TEST_RATIO), stratify=model_df["__target__"], random_state=RANDOM_SEED
        )
        val_share = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
        val_df, test_df = train_test_split(
            temp_df, test_size=val_share, stratify=temp_df["__target__"], random_state=RANDOM_SEED
        )

        pipeline_scaled = build_preprocessing_pipeline(scale=True)
        pipeline_unscaled = build_preprocessing_pipeline(scale=False)
        y_train = train_df["__target__"].to_numpy()
        y_val = val_df["__target__"].to_numpy()

        X_train_scaled = pipeline_scaled.fit_transform(train_df[MODELING_COLUMNS], y_train)
        X_train_unscaled = pipeline_unscaled.fit_transform(train_df[MODELING_COLUMNS], y_train)
        X_val_scaled = pipeline_scaled.transform(val_df[MODELING_COLUMNS])
        X_val_unscaled = pipeline_unscaled.transform(val_df[MODELING_COLUMNS])

        feature_schema = build_feature_schema(train_df)

        job.status = "training"
        db.commit()

        results: dict[str, dict[str, Any]] = {}
        for _model_id, algorithm, uses_scaled, builder, _hyperparameters in BASELINE_SPECS:
            X_train = X_train_scaled if uses_scaled else X_train_unscaled
            X_val = X_val_scaled if uses_scaled else X_val_unscaled
            model = builder()
            model.fit(X_train, y_train)
            y_val_prob = predict_proba_positive(model, X_val)
            threshold, val_metrics = select_threshold_by_f1(y_val, y_val_prob)
            results[algorithm] = {
                "algorithm": algorithm,
                "model": model,
                "uses_scaled": uses_scaled,
                "threshold": threshold,
                "validation_metrics": val_metrics,
            }

        class_weight = compute_class_weights(y_train)
        ann_model = build_ann_model(input_dim=X_train_scaled.shape[1])
        train_ann_model(
            ann_model, X_train_scaled, y_train, X_val_scaled, y_val, class_weight=class_weight, verbose=0
        )
        y_val_prob_ann = ann_model.predict(X_val_scaled, verbose=0).reshape(-1)
        threshold_ann, val_metrics_ann = select_threshold_by_f1(y_val, y_val_prob_ann)
        results[ALGORITHM_ANN] = {
            "algorithm": ALGORITHM_ANN,
            "model": ann_model,
            "uses_scaled": True,
            "threshold": threshold_ann,
            "validation_metrics": val_metrics_ann,
        }

        job.status = "evaluating"
        db.commit()

        winner_algorithm = select_winner(results)
        winner = results[winner_algorithm]
        pipeline = pipeline_scaled if winner["uses_scaled"] else pipeline_unscaled

        X_test = pipeline.transform(test_df[MODELING_COLUMNS])
        y_test = test_df["__target__"].to_numpy()
        if winner_algorithm == ALGORITHM_ANN:
            y_test_prob = winner["model"].predict(X_test, verbose=0).reshape(-1)
        else:
            y_test_prob = predict_proba_positive(winner["model"], X_test)
        test_metrics = compute_metric_suite(y_test, y_test_prob, winner["threshold"])

        model_id = f"company_{dataset.organization_id}_{job.id}_{winner_algorithm}"
        model_dir = ml_config.ARTIFACTS_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        if winner_algorithm == ALGORITHM_ANN:
            winner["model"].save(model_dir / "model.keras")
        else:
            joblib.dump(winner["model"], model_dir / "model.joblib")
        joblib.dump(pipeline, model_dir / "pipeline.joblib")

        version = _next_version(db, dataset.organization_id)
        metadata = {
            "model_id": model_id,
            "algorithm": winner_algorithm,
            "model_type": "company_specific",
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "random_seed": RANDOM_SEED,
            "trained_on_dataset": dataset.original_filename,
            "train_row_count": int(len(train_df)),
            "preprocessing_pipeline_variant": "scaled" if winner["uses_scaled"] else "unscaled",
            "feature_schema": feature_schema,
            "decision_threshold": winner["threshold"],
            "risk_thresholds": RISK_THRESHOLDS,
            "test_evaluated": True,
            "selected_as_recommended_production_model": False,
        }
        (model_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        metrics_payload = {"validation": winner["validation_metrics"], "test": test_metrics}
        (model_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

        bundle = load_model_bundle(model_dir)
        feature_names = get_transformed_feature_names(bundle.pipeline)
        background = (
            None
            if winner_algorithm in TREE_ALGORITHMS
            else pipeline.transform(
                train_df[MODELING_COLUMNS].sample(n=min(100, len(train_df)), random_state=RANDOM_SEED)
            )
        )
        explainer, base_value = build_explainer(bundle, background)
        combined = pd.concat([train_df, val_df], ignore_index=True)
        sample_df = combined.sample(n=min(500, len(combined)), random_state=RANDOM_SEED)
        X_sample = pipeline.transform(sample_df[MODELING_COLUMNS])
        global_shap = compute_global_explanation(bundle, explainer, base_value, X_sample, feature_names)
        (model_dir / "global_shap.json").write_text(json.dumps(global_shap, indent=2), encoding="utf-8")

        model_row = Model(
            organization_id=dataset.organization_id,
            model_type="company_specific",
            algorithm=winner_algorithm,
            version=version,
            artifact_path=str(model_dir.resolve()),
            feature_schema=feature_schema,
            metrics=metrics_payload,
            decision_threshold=winner["threshold"],
            risk_thresholds=RISK_THRESHOLDS,
            trained_on_dataset_id=dataset.id,
            training_job_id=job.id,
            is_active=False,
        )
        db.add(model_row)
        db.flush()

        job.status = "completed"
        job.resulting_model_id = model_row.id
        job.completed_at = datetime.utcnow()
        summary = (
            f"Winning model: {winner_algorithm} "
            f"(validation PR-AUC={winner['validation_metrics']['pr_auc']:.3f}, "
            f"recall={winner['validation_metrics']['recall']:.3f})."
        )
        if small_dataset_warning:
            summary += " " + small_dataset_warning
        job.status_message = summary

        audit_service.write_audit_log(
            db, organization_id=dataset.organization_id, user_id=user_id, event_type="training_completed",
            event_details={"training_job_id": job.id, "model_id": model_row.id, "algorithm": winner_algorithm},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - captured into the job's terminal state, not re-raised
        db.rollback()
        job.status = "failed"
        job.status_message = str(exc)[:1000]
        job.completed_at = datetime.utcnow()
        audit_service.write_audit_log(
            db, organization_id=dataset.organization_id, user_id=user_id, event_type="training_failed",
            event_details={"training_job_id": job.id, "error": str(exc)[:500]},
        )
        db.commit()


def serialize_job(job: TrainingJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "dataset_id": job.dataset_id,
        "status": job.status,
        "status_message": job.status_message,
        "resulting_model_id": job.resulting_model_id,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat(),
    }


def list_training_jobs(db: DBSession, *, organization_id: int, page: int, page_size: int) -> dict[str, Any]:
    query = (
        db.query(TrainingJob)
        .filter(TrainingJob.organization_id == organization_id)
        .order_by(TrainingJob.created_at.desc())
    )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "data": [serialize_job(j) for j in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        },
    }


def get_training_job(db: DBSession, *, organization_id: int, job_id: int) -> TrainingJob:
    from backend.errors.exceptions import NotFoundError

    job = db.get(TrainingJob, job_id)
    if job is None or job.organization_id != organization_id:
        raise NotFoundError("The requested training job was not found.")
    return job
