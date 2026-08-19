"""`/api/models` (`docs/API.md`): read-only listing of the model artifacts
found under `ml/artifacts/`. No `POST /:id/activate|deactivate` in Phase 8
either — real per-organization activation state requires the company-model
training workflow (`docs/PROJECT_SPEC.md` §16), which doesn't exist yet;
Phase 8 only seeds the one baseline `models` row (`scripts/seed_baseline_model.py`)
for provenance/FK purposes, it does not wire these routes to the DB.

Both routes require an authenticated session (`@login_required`,
`docs/BACKEND_SPEC.md` §4).
"""

from __future__ import annotations

from flask import Blueprint

from backend.auth.decorators import login_required
from backend.services import model_registry
from backend.utils import success_response

models_bp = Blueprint("models", __name__)


@models_bp.get("")
@login_required
def list_models():
    return success_response(model_registry.list_model_summaries())


@models_bp.get("/<model_id>")
@login_required
def get_model_detail(model_id: str):
    return success_response(model_registry.get_model_detail(model_id))
