"""`/api/predictions` (`docs/API.md`): single + batch prediction, plus batch
retrieval (`GET /batch/:batch_job_id`, `GET /batch/:batch_job_id/download`)
and prediction history (`GET /`).

Phase 7: synchronous batch scoring, nothing persisted.
Phase 8: both routes require an authenticated session.
Phase 9: batch upload is ingested through the same dataset pipeline as
training uploads (`dataset_service.create_dataset_from_upload`, per
`docs/API.md` — creates a `datasets` row + per-row `customers` records), and
every prediction (single or batch) is persisted (`prediction_service`),
resolved against the caller's org-specific active model with a baseline
fallback (`docs/API.md`: "using the org's active model (falls back to
baseline if none active)").
"""

from __future__ import annotations

import pandas as pd
from flask import Blueprint, Response, g, request
from pydantic import ValidationError as PydanticValidationError

from ml.data_quality.validator import DataQualityValidator

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.errors.exceptions import (
    NotFoundError,
    SchemaMismatchError,
    ValidationError,
)
from backend.services import dataset_service, file_service, prediction_service
from backend.utils import success_response
from backend.validation.schemas import SinglePredictionRequest

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.post("/single")
@login_required
def post_single_prediction():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")

    try:
        parsed = SinglePredictionRequest.model_validate(payload)
    except PydanticValidationError as exc:
        raise ValidationError(
            "Invalid request body.", details={"errors": exc.errors(include_url=False)}
        ) from exc

    db = db_session.get_session()
    result = prediction_service.predict_single(
        db,
        organization_id=g.current_user.organization_id,
        user_id=g.current_user.id,
        customer_data=parsed.customer_data,
        customer_id=parsed.customer_id,
    )
    return success_response(result)


@predictions_bp.post("/batch")
@login_required
def post_batch_prediction():
    file_storage = request.files.get("file")
    max_bytes = request.max_content_length or (25 * 1024 * 1024)
    raw_bytes = file_storage.read() if file_storage is not None else b""
    if file_storage is not None:
        file_storage.stream.seek(0)
    df = file_service.validate_and_parse_csv_upload(file_storage, max_bytes)

    db = db_session.get_session()
    organization_id = g.current_user.organization_id

    bundle, model_row = prediction_service.resolve_bundle(db, organization_id)
    feature_schema = bundle.metadata["feature_schema"]
    required_columns = [f["name"] for f in feature_schema]

    # Case/whitespace-insensitive column detection (`docs/PROJECT_SPEC.md`
    # §16.1 step 1): rename matched upload columns to their canonical schema
    # names (including the id column) *before* quality validation/scoring,
    # so a header like "senior citizen" or "Customer ID" is recognized
    # rather than failing the whole batch as missing columns. Values are
    # never touched here — a wrong *value* (e.g. "0"/"1" for Senior Citizen)
    # still fails per-row validation in `prediction_service.predict_batch`.
    column_mapping = dataset_service.match_columns_to_schema(df.columns.tolist(), required_columns)
    column_mapping.update(dataset_service.match_columns_to_schema(df.columns.tolist(), ["CustomerID"]))
    df = df.rename(columns={actual: schema_col for schema_col, actual in column_mapping.items()})
    id_column = "CustomerID" if "CustomerID" in df.columns else None

    validator = DataQualityValidator(
        required_columns=required_columns, target_column=None, id_column=id_column
    )
    quality_report = validator.validate(df)
    _enforce_quality_report(quality_report)

    ingestion = dataset_service.create_dataset_from_upload(
        db,
        organization_id=organization_id,
        uploaded_by_user_id=g.current_user.id,
        df=df,
        original_filename=file_storage.filename,
        raw_bytes=raw_bytes,
        upload_dir=_upload_dir(),
        source_type="company_upload",
        target_column=None,
        id_column=id_column,
    )
    customer_ids = _customer_ids_for_rows(db, organization_id, ingestion["dataset"].id, df, id_column)

    outcome = prediction_service.predict_batch(
        db,
        organization_id=organization_id,
        user_id=g.current_user.id,
        df=df,
        id_column=id_column,
        customer_ids=customer_ids,
    )

    wants_csv = request.args.get("format", "").lower() == "csv" or "text/csv" in (
        request.headers.get("Accept") or ""
    )
    if wants_csv:
        csv_body = outcome["results"].to_csv(index=False)
        return Response(
            csv_body,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=churnai_batch_predictions.csv"},
        )

    results_df = outcome["results"]
    records = results_df.astype(object).where(pd.notnull(results_df), None).to_dict(orient="records")
    return success_response(
        {
            "batch_job_id": outcome["batch_job_id"],
            "dataset_id": ingestion["dataset"].id,
            "summary": outcome["summary"],
            "quality_report": quality_report,
            "results": records,
        }
    )


@predictions_bp.get("/batch/<batch_job_id>")
@login_required
def get_batch_status(batch_job_id: str):
    """Retrieval-after-the-fact for a completed batch run (Phase 9 processes
    batches synchronously at POST time, so this always reflects a terminal
    `completed` state — the polling contract still holds for a later phase
    that makes this genuinely async). Only rows that were successfully
    scored are persisted (`docs/DATABASE_SPEC.md` §2.9), so failed rows from
    the original upload aren't reconstructable here — that detail is only
    available in the original synchronous POST response."""
    db = db_session.get_session()
    rows = prediction_service.get_predictions_by_batch_job_id(
        db, organization_id=g.current_user.organization_id, batch_job_id=batch_job_id
    )
    if not rows:
        raise NotFoundError(f"No batch prediction run found with id {batch_job_id!r}.")

    risk_level_counts = {"low": 0, "medium": 0, "high": 0}
    for row in rows:
        risk_level_counts[row.risk_level] += 1

    return success_response(
        {
            "batch_job_id": batch_job_id,
            "status": "completed",
            "scored_rows": len(rows),
            "predicted_churners": sum(1 for r in rows if r.predicted_class),
            "risk_level_counts": risk_level_counts,
            "results": [
                {
                    "prediction_id": r.id,
                    "customer_id": r.customer_id,
                    **r.input_data,
                    "churn_probability": r.churn_probability,
                    "predicted_class": int(r.predicted_class),
                    "risk_level": r.risk_level,
                }
                for r in rows
            ],
        }
    )


@predictions_bp.get("/batch/<batch_job_id>/download")
@login_required
def download_batch_results(batch_job_id: str):
    db = db_session.get_session()
    rows = prediction_service.get_predictions_by_batch_job_id(
        db, organization_id=g.current_user.organization_id, batch_job_id=batch_job_id
    )
    if not rows:
        raise NotFoundError(f"No batch prediction run found with id {batch_job_id!r}.")

    records = [
        {**r.input_data, "churn_probability": r.churn_probability, "predicted_class": int(r.predicted_class), "risk_level": r.risk_level}
        for r in rows
    ]
    csv_body = pd.DataFrame(records).to_csv(index=False)
    return Response(
        csv_body,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=churnai_batch_{batch_job_id}.csv"},
    )


@predictions_bp.get("")
@login_required
def get_prediction_history():
    from backend.db.models import Prediction

    db = db_session.get_session()
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    risk_level = request.args.get("risk_level")

    query = db.query(Prediction).filter(Prediction.organization_id == g.current_user.organization_id)
    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level)
    query = query.order_by(Prediction.created_at.desc())

    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    return success_response(
        {
            "data": [
                {
                    "id": r.id,
                    "model_id": r.model_id,
                    "prediction_type": r.prediction_type,
                    "customer_id": r.customer_id,
                    "churn_probability": r.churn_probability,
                    "predicted_class": int(r.predicted_class),
                    "risk_level": r.risk_level,
                    "batch_job_id": r.batch_job_id,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if page_size else 0,
            },
        }
    )


def _upload_dir():
    from flask import current_app

    return current_app.config["UPLOAD_STORAGE_DIR"]


def _customer_ids_for_rows(db, organization_id, dataset_id, df, id_column):
    from backend.db.models import Customer

    if id_column is None or id_column not in df.columns:
        rows = (
            db.query(Customer)
            .filter(Customer.organization_id == organization_id, Customer.dataset_id == dataset_id)
            .order_by(Customer.id.asc())
            .all()
        )
        return [c.id for c in rows]

    by_external_id = {
        c.external_customer_id: c.id
        for c in db.query(Customer).filter(Customer.organization_id == organization_id).all()
        if c.external_customer_id
    }
    return [by_external_id.get(str(v)) for v in df[id_column]]


def _enforce_quality_report(quality_report: dict) -> None:
    """Only `missing_required_columns` blocks the whole batch — a feature the
    model needs isn't present in the file at all, so no row can be scored.
    Every other "fail"-status check (bad numeric values, duplicate rows,
    inconsistent category casing, ...) is a per-row/per-value problem that
    `prediction_service.predict_batch` already handles by flagging just the
    offending rows and scoring the rest — blocking the whole upload for
    those would contradict "preserve successful rows" (`docs/PROJECT_SPEC.md`
    §17.B). The full `quality_report`, fails included, is still returned to
    the caller for visibility either way."""
    missing_check = next((c for c in quality_report["checks"] if c["name"] == "missing_required_columns"), None)
    if missing_check and missing_check["status"] == "fail":
        missing_columns = missing_check["detail"]["missing_columns"]
        raise SchemaMismatchError(
            "The uploaded file is missing required columns: " + ", ".join(missing_columns) + ".",
            details={"missing_columns": missing_columns},
        )
