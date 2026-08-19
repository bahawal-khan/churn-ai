"""`/api/predictions` (`docs/API.md`): single + batch prediction.

Phase 7 simplifications (documented, not silent, still true in Phase 8):
no `datasets`/`customers`/`predictions` tables are written to by these
routes yet, so batch prediction is always processed synchronously in one
request/response (no `batch_job_id` polling) and nothing is persisted —
every input row still appears in the response with its prediction (or its
per-row error), preserving the customer-linkage contract
(`docs/PROJECT_SPEC.md` §17.B) without a database behind it. A client can
request the same result as a downloadable CSV in the same call via
`?format=csv` instead of a separate stored-download endpoint.

Phase 8 addition: both routes now require an authenticated session
(`@login_required`, `docs/BACKEND_SPEC.md` §4 — "every non-auth, non-health
route"). No `@ownership_required` check yet since predictions here are
served from the org-agnostic global baseline artifact, not a stored,
org-owned row.
"""

from __future__ import annotations

import pandas as pd
from flask import Blueprint, Response, request
from pydantic import ValidationError as PydanticValidationError

from ml.data_quality.validator import DataQualityValidator

from backend.auth.decorators import login_required
from backend.errors.exceptions import DataQualityFailedError, SchemaMismatchError, ValidationError
from backend.services import file_service, model_registry, prediction_service
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

    result = prediction_service.predict_single(parsed.customer_data, parsed.customer_id)
    return success_response(result)


@predictions_bp.post("/batch")
@login_required
def post_batch_prediction():
    file_storage = request.files.get("file")
    max_bytes = request.max_content_length or (25 * 1024 * 1024)
    df = file_service.validate_and_parse_csv_upload(file_storage, max_bytes)

    bundle = model_registry.get_active_bundle()
    feature_schema = bundle.metadata["feature_schema"]
    required_columns = [f["name"] for f in feature_schema]
    id_column = "CustomerID" if "CustomerID" in df.columns else None

    validator = DataQualityValidator(
        required_columns=required_columns, target_column=None, id_column=id_column
    )
    quality_report = validator.validate(df)
    _enforce_quality_report(quality_report)

    outcome = prediction_service.predict_batch(df, id_column)

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
        {"summary": outcome["summary"], "quality_report": quality_report, "results": records}
    )


def _enforce_quality_report(quality_report: dict) -> None:
    checks_by_name = {c["name"]: c for c in quality_report["checks"]}

    missing_check = checks_by_name.get("missing_required_columns")
    if missing_check and missing_check["status"] == "fail":
        missing_columns = missing_check["detail"]["missing_columns"]
        raise SchemaMismatchError(
            "The uploaded file is missing required columns: " + ", ".join(missing_columns) + ".",
            details={"missing_columns": missing_columns},
        )

    other_failures = [c["name"] for c in quality_report["checks"] if c["status"] == "fail"]
    if other_failures:
        raise DataQualityFailedError(
            "The uploaded file failed data quality validation: " + ", ".join(other_failures) + ".",
            details={"quality_report": quality_report},
        )
