"""`/api/models` (`docs/API.md`).

Phase 7/8: read-only listing of the filesystem model artifacts found under
`ml/artifacts/` — unchanged here, so existing Phase 7/8 callers/tests keep
working exactly as before.

Phase 9 addition: `GET /` and `GET /:id` also merge in the caller's org's
DB-backed `company_specific` models (`docs/API.md`: "the shared baseline +
the org's company-specific versions") — additive only, so an org with no
trained models yet sees identical output to before. `POST /:id/activate`
and `POST /:id/deactivate` operate on those DB-backed company models (the
"Activate Model" step of `docs/PROJECT_SPEC.md` §16's training workflow);
they only apply to models a training job produced, not filesystem-only dev
artifacts, since baseline activation state is global, not per-org.
"""

from __future__ import annotations

from flask import Blueprint, g

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.errors.exceptions import NotFoundError
from backend.services import model_registry
from backend.utils import success_response

models_bp = Blueprint("models", __name__)


@models_bp.get("")
@login_required
def list_models():
    db = db_session.get_session()
    summaries = model_registry.list_model_summaries()
    summaries.extend(model_registry.list_org_model_summaries(db, g.current_user.organization_id))
    return success_response(summaries)


@models_bp.get("/<model_id>")
@login_required
def get_model_detail(model_id: str):
    db = db_session.get_session()
    if model_id.isdigit():
        try:
            return success_response(
                model_registry.get_org_model_detail(db, g.current_user.organization_id, int(model_id))
            )
        except NotFoundError:
            pass
    return success_response(model_registry.get_model_detail(model_id))


@models_bp.post("/<int:model_id>/activate")
@login_required
def activate_model(model_id: int):
    db = db_session.get_session()
    row = model_registry.activate_company_model(
        db, organization_id=g.current_user.organization_id, model_db_id=model_id, user_id=g.current_user.id
    )
    return success_response({"id": row.id, "is_active": row.is_active})


@models_bp.post("/<int:model_id>/deactivate")
@login_required
def deactivate_model(model_id: int):
    db = db_session.get_session()
    row = model_registry.deactivate_company_model(
        db, organization_id=g.current_user.organization_id, model_db_id=model_id, user_id=g.current_user.id
    )
    return success_response({"id": row.id, "is_active": row.is_active})
