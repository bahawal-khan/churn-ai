"""Prediction orchestration (`docs/PROJECT_SPEC.md` §17): wires the active
model bundle + SHAP explainer (`model_registry`) to validated input
(`backend.validation.feature_validation`) and returns API-shaped results.

No `predictions`/`customers` tables exist yet (Phase 7 scope) — nothing here
is persisted; every value returned is computed fresh from the real model at
request time (`docs/PROJECT_SPEC.md` binding rule: no hard-coded predictions).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from ml.config import MODELING_COLUMNS
from ml.models.explain import compute_local_explanation

from backend.errors.exceptions import PredictionFailedError
from backend.services import model_registry
from backend.validation.feature_validation import validate_customer_record, validate_fields

RISK_LEVELS = ("low", "medium", "high")


def predict_single(customer_data: dict[str, Any], customer_id: str | None = None) -> dict[str, Any]:
    bundle = model_registry.get_active_bundle()
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

    explainer, base_value, feature_names = model_registry.get_active_explainer()
    explanation = compute_local_explanation(
        bundle, explainer, base_value, transformed, feature_names, probability
    )

    return {
        "customer_id": customer_id,
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "decision_threshold": float(bundle.metadata["decision_threshold"]),
        "churn_probability": probability,
        "predicted_class": predicted_class,
        "risk_level": risk_level,
        "explanation": explanation,
    }


def predict_batch(df: pd.DataFrame, id_column: str | None) -> dict[str, Any]:
    """Scores every row of `df`. Every input row appears in the output
    (`docs/PROJECT_SPEC.md` §17.B customer-linkage contract) — rows that fail
    per-field validation get null prediction columns plus a `prediction_error`
    explaining why, rather than being silently dropped
    (`docs/PROJECT_SPEC.md` §16.1: bad values are handled per-row, not by
    failing the whole file)."""
    bundle = model_registry.get_active_bundle()
    feature_schema = bundle.metadata["feature_schema"]

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

    if valid_indices:
        valid_df = pd.DataFrame([cleaned_rows[i] for i in valid_indices])[MODELING_COLUMNS]
        try:
            predicted = bundle.predict(valid_df)
        except Exception as exc:  # defensive: rows here already passed field validation
            raise PredictionFailedError("Prediction failed while scoring the uploaded batch.") from exc
        for pos, row_idx in enumerate(valid_indices):
            probabilities[row_idx] = float(predicted.loc[pos, "churn_probability"])
            predicted_classes[row_idx] = int(predicted.loc[pos, "predicted_class"])
            risk_levels[row_idx] = str(predicted.loc[pos, "risk_level"])

    output_df = df.copy()
    output_df["churn_probability"] = probabilities
    output_df["predicted_class"] = predicted_classes
    output_df["risk_level"] = risk_levels
    output_df["prediction_error"] = row_errors

    risk_level_counts = {level: risk_levels.count(level) for level in RISK_LEVELS}
    predicted_churners = sum(1 for c in predicted_classes if c == 1)

    summary = {
        "model_id": bundle.metadata["model_id"],
        "algorithm": bundle.algorithm,
        "id_column": id_column,
        "total_rows": int(len(df)),
        "scored_rows": len(valid_indices),
        "failed_rows": int(len(df) - len(valid_indices)),
        "predicted_churners": predicted_churners,
        "risk_level_counts": risk_level_counts,
    }

    return {"summary": summary, "results": output_df}
