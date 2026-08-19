"""`/api/models` (`docs/API.md`): read-only listing of the model artifacts
found under `ml/artifacts/`. No `POST /:id/activate|deactivate` in this
phase — activation is per-organization state that requires the `models` DB
table (`docs/DATABASE_SPEC.md` §2.7), out of scope until the DB phase.
"""

from __future__ import annotations

from flask import Blueprint

from backend.services import model_registry
from backend.utils import success_response

models_bp = Blueprint("models", __name__)


@models_bp.get("")
def list_models():
    return success_response(model_registry.list_model_summaries())


@models_bp.get("/<model_id>")
def get_model_detail(model_id: str):
    return success_response(model_registry.get_model_detail(model_id))
