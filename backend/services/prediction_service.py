"""Prediction orchestration (`docs/PROJECT_SPEC.md` §17): wires the
org-resolved active model bundle + SHAP explainer (`model_registry`) to
validated input (`backend.validation.feature_validation`) and returns
API-shaped results.

Phase 9 addition: every prediction is now persisted to `predictions`/
`explanations` (`docs/DATABASE_SPEC.md` §2.9-§2.10) — required so
`customers`/`analytics` have real stored data to compute from, per
`docs/PROJECT_SPEC.md`'s binding "no hard-coded/mocked prediction values"
rule (an analytics endpoint with nothing persisted would otherwise have
nothing real to ever show). The returned response shape is unchanged from
Phase 7/8 (same keys, same values) with new keys added additively
(`prediction_id`) so existing callers/tests are unaffected.
"""

from __future__ import annotations

import uuid
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session as DBSession

from ml.config import MODELING_COLUMNS
from ml.models.explain import compute_local_explanation

from backend.db.models import Customer, Explanation, Prediction
from backend.errors.exceptions import PredictionFailedError
from backend.services import audit_service, model_registry
from backend.validation.feature_validation import validate_customer_record, validate_fields

RISK_LEVELS = ("low", "medium", "high")


def resolve_bundle(db: DBSession, organization_id: int) -> tuple[Any, Any]:
    bundle, model_row = model_registry.get_active_bundle_for_org(db, organization_id)
    if model_row is None:
        model_row = model_registry.ensure_baseline_model_row(db)
    return bundle, model_row


def _find_customer_by_external_id(db: DBSession, organization_id: int, external_id: str | None) -> Customer | None:
    if not external_id:
        return None
    return (
        db.query(Customer)
        .filter(Customer.organization_id == organization_id, Customer.external_customer_id == external_id)
        .one_or_none()
    )


def predict_single(
    db: DBSession,
    *,
    organization_id: int,
    user_id: int | None,
    customer_data: dict[str, Any],
    customer_id: str | None = None,
) -> dict[str, Any]:
    bundle, model_row = resolve_bundle(db, organization_id)
    feature_schema = bundle.metadata["feature_schema"]

    cleaned = validate_customer_record(customer_data, feature_schema)
    row_df = pd.DataFrame([cleaned])[MODELING_COLUMNS]

    try:
        result_df = bundle.predict(row_df)
        transformed = bundle.pipeline.transform(row_df)
    except Exception as exc:  # defensive: a valid, schema-conformant row should never reach here
        raise PredictionFailedError("Prediction failed while scoring the customer record.") from exc

    probability = float(result_df.loc[0, "churn_probability"])
    predicted_class = int(result_df.loc[0, "predicted_class"])
    risk_level = str(result_df.loc[0, "risk_level"])

    explainer, base_value, feature_names = model_registry.get_explainer_for_bundle(bundle)
    explanation = compute_local_explanation(
        bundle, explainer, base_value, transformed, feature_names, probability
    )

    linked_customer = _find_customer_by_external_id(db, organization_id, customer_id)

    prediction_row = Prediction(
        organization_id=organization_id,
        model_id=model_row.id,
        prediction_type="single",
        customer_id=linked_customer.id if linked_customer else None,
        input_data=cleaned,
        churn_probability=probability,
        predicted_class=bool(predicted_class),
        risk_level=risk_level,
    )
    db.add(prediction_row)
    db.flush()
    db.add(
        Explanation(
            prediction_id=prediction_row.id,
            shap_values=explanation["shap_values"],
            base_value=explanation["base_value"],
            top_factors=explanation["top_factors"],
        )
    )
    audit_service.write_audit_log(
        db, organization_id=organization_id, user_id=user_id, event_type="prediction_made",
        event_details={"prediction_id": prediction_row.id, "prediction_type": "single"},
    )
    db.commit()

    return {
        "prediction_id": prediction_row.id,
        "customer_id": customer_id,
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "decision_threshold": float(bundle.metadata["decision_threshold"]),
        "churn_probability": probability,
        "predicted_class": predicted_class,
        "risk_level": risk_level,
        "explanation": explanation,
    }


def predict_batch(
    db: DBSession,
    *,
    organization_id: int,
    user_id: int | None,
    df: pd.DataFrame,
    id_column: str | None,
    customer_ids: list[int | None] | None = None,
) -> dict[str, Any]:
    """Scores every row of `df`. Every input row appears in the output
    (`docs/PROJECT_SPEC.md` §17.B customer-linkage contract) — rows that fail
    per-field validation get null prediction columns plus a `prediction_error`
    explaining why, rather than being silently dropped. Successfully scored
    rows are persisted as `predictions`/`explanations` rows, linked to
    `customer_ids[i]` when provided (the dataset-ingestion step's per-row
    customer match, `docs/API.md` batch prediction contract)."""
    bundle, model_row = resolve_bundle(db, organization_id)
    feature_schema = bundle.metadata["feature_schema"]
    batch_job_id = uuid.uuid4().hex
    customer_ids = customer_ids or [None] * len(df)

    cleaned_rows: list[dict[str, Any] | None] = []
    row_errors: list[str | None] = []
    for _, row in df.iterrows():
        cleaned, field_errors = validate_fields(row.to_dict(), feature_schema)
        if field_errors:
            cleaned_rows.append(None)
            row_errors.append("; ".join(f"{k}: {v}" for k, v in sorted(field_errors.items())))
        else:
            cleaned_rows.append(cleaned)
            row_errors.append(None)

    valid_indices = [i for i, c in enumerate(cleaned_rows) if c is not None]

    probabilities: list[float | None] = [None] * len(df)
    predicted_classes: list[int | None] = [None] * len(df)
    risk_levels: list[str | None] = [None] * len(df)
    prediction_ids: list[int | None] = [None] * len(df)

    if valid_indices:
        valid_df = pd.DataFrame([cleaned_rows[i] for i in valid_indices])[MODELING_COLUMNS]
        try:
            predicted = bundle.predict(valid_df)
            transformed = bundle.pipeline.transform(valid_df)
        except Exception as exc:  # defensive: rows here already passed field validation
            raise PredictionFailedError("Prediction failed while scoring the uploaded batch.") from exc

        explainer, base_value, feature_names = model_registry.get_explainer_for_bundle(bundle)

        for pos, row_idx in enumerate(valid_indices):
            probability = float(predicted.loc[pos, "churn_probability"])
            predicted_class = int(predicted.loc[pos, "predicted_class"])
            risk_level = str(predicted.loc[pos, "risk_level"])
            probabilities[row_idx] = probability
            predicted_classes[row_idx] = predicted_class
            risk_levels[row_idx] = risk_level

            prediction_row = Prediction(
                organization_id=organization_id,
                model_id=model_row.id,
                prediction_type="batch",
                customer_id=customer_ids[row_idx] if row_idx < len(customer_ids) else None,
                input_data=cleaned_rows[row_idx],
                churn_probability=probability,
                predicted_class=bool(predicted_class),
                risk_level=risk_level,
                batch_job_id=batch_job_id,
            )
            db.add(prediction_row)
            db.flush()
            prediction_ids[row_idx] = prediction_row.id

            explanation = compute_local_explanation(
                bundle, explainer, base_value, transformed[pos : pos + 1], feature_names, probability
            )
            db.add(
                Explanation(
                    prediction_id=prediction_row.id,
                    shap_values=explanation["shap_values"],
                    base_value=explanation["base_value"],
                    top_factors=explanation["top_factors"],
                )
            )

        audit_service.write_audit_log(
            db, organization_id=organization_id, user_id=user_id, event_type="prediction_made",
            event_details={"batch_job_id": batch_job_id, "prediction_type": "batch", "scored_rows": len(valid_indices)},
        )
        db.commit()

    output_df = df.copy()
    output_df["churn_probability"] = probabilities
    output_df["predicted_class"] = predicted_classes
    output_df["risk_level"] = risk_levels
    output_df["prediction_error"] = row_errors

    risk_level_counts = {level: risk_levels.count(level) for level in RISK_LEVELS}
    predicted_churners = sum(1 for c in predicted_classes if c == 1)

    summary = {
        "batch_job_id": batch_job_id,
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "id_column": id_column,
        "total_rows": int(len(df)),
        "scored_rows": len(valid_indices),
        "failed_rows": int(len(df) - len(valid_indices)),
        "predicted_churners": predicted_churners,
        "risk_level_counts": risk_level_counts,
    }

    return {"summary": summary, "results": output_df, "batch_job_id": batch_job_id}


def get_predictions_by_batch_job_id(db: DBSession, *, organization_id: int, batch_job_id: str) -> list[Prediction]:
    return (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id, Prediction.batch_job_id == batch_job_id)
        .order_by(Prediction.id.asc())
        .all()
    )
