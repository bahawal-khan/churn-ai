"""`/api/reports` (`docs/API.md`)."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, g, request
from pydantic import ValidationError as PydanticValidationError

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.errors.exceptions import ValidationError
from backend.services import report_service
from backend.utils import success_response
from backend.validation.schemas import ReportGenerateRequest

reports_bp = Blueprint("reports", __name__)


@reports_bp.post("/generate")
@login_required
def post_generate_report():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    try:
        parsed = ReportGenerateRequest.model_validate(payload)
    except PydanticValidationError as exc:
        # `include_context=False`: this schema's `report_type` validator
        # raises a plain `ValueError`; Pydantic's default `errors()` embeds
        # the raw exception object in `ctx.error`, which `jsonify` can't
        # serialize (`docs/BACKEND_SPEC.md` §5 — mirrors `routes/auth.py`'s
        # `_parse` helper).
        raise ValidationError(
            "Invalid request body.",
            details={"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    db = db_session.get_session()
    metadata = report_service.generate_report(
        db,
        organization_id=g.current_user.organization_id,
        user_id=g.current_user.id,
        report_type=parsed.report_type,
        filters=parsed.filters,
        reports_dir=current_app.config["REPORTS_STORAGE_DIR"],
    )
    return success_response(metadata, status=201)


@reports_bp.get("")
@login_required
def list_reports():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    return success_response(
        report_service.list_reports(
            organization_id=g.current_user.organization_id,
            reports_dir=current_app.config["REPORTS_STORAGE_DIR"],
            page=page,
            page_size=page_size,
        )
    )


@reports_bp.get("/<report_id>/download")
@login_required
def download_report(report_id: str):
    csv_path = report_service.get_report_csv_path(
        organization_id=g.current_user.organization_id,
        reports_dir=current_app.config["REPORTS_STORAGE_DIR"],
        report_id=report_id,
    )
    return Response(
        csv_path.read_text(encoding="utf-8"),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=churnai_report_{report_id}.csv"},
    )
