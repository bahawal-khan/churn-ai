"""`/api/training` (`docs/API.md`, `docs/PROJECT_SPEC.md` §16)."""

from __future__ import annotations

from flask import Blueprint, g, request
from pydantic import ValidationError as PydanticValidationError

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.db.models import TrainingJob
from backend.errors.exceptions import ValidationError
from backend.services import dataset_service, training_service
from backend.utils import success_response
from backend.validation.schemas import TrainingJobRequest

training_bp = Blueprint("training", __name__)


@training_bp.post("/jobs")
@login_required
def post_training_job():
    payload = request.get_json(silent=True)
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    try:
        parsed = TrainingJobRequest.model_validate(payload)
    except PydanticValidationError as exc:
        # `include_context=False`: see `routes/reports.py`'s identical note —
        # this schema's `target_column` validator also raises a plain
        # `ValueError`.
        raise ValidationError(
            "Invalid request body.",
            details={"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc

    db = db_session.get_session()
    dataset = dataset_service.get_dataset(
        db, organization_id=g.current_user.organization_id, dataset_id=parsed.dataset_id
    )

    training_service.validate_training_preconditions(dataset, parsed.target_column)

    job = TrainingJob(
        organization_id=g.current_user.organization_id,
        dataset_id=dataset.id,
        status="queued",
    )
    db.add(job)
    db.commit()

    training_service.run_training_job(
        db, job=job, dataset=dataset, target_column=parsed.target_column, user_id=g.current_user.id
    )

    return success_response(training_service.serialize_job(job), status=201)


@training_bp.get("/jobs")
@login_required
def list_training_jobs():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    db = db_session.get_session()
    return success_response(
        training_service.list_training_jobs(
            db, organization_id=g.current_user.organization_id, page=page, page_size=page_size
        )
    )


@training_bp.get("/jobs/<int:job_id>")
@login_required
def get_training_job(job_id: int):
    db = db_session.get_session()
    job = training_service.get_training_job(db, organization_id=g.current_user.organization_id, job_id=job_id)
    return success_response(training_service.serialize_job(job))
