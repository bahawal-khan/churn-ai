"""`GET /api/health` (`docs/API.md`): unauthenticated, used by deployment
monitoring. `db` is honestly reported as `"not_configured"` — Phase 7 has no
database yet (`docs/PROJECT_SPEC.md` phased plan), so claiming a real DB
health value here would be exactly the kind of presented-as-real-but-fake
value the project's binding no-hard-coded-values rule forbids.
"""

from __future__ import annotations

from flask import Blueprint, current_app

from backend.services import model_registry
from backend.utils import success_response

health_bp = Blueprint("health", __name__)


@health_bp.get("")
def get_health():
    try:
        model_registry.get_active_bundle()
        model_loaded = True
    except Exception:
        model_loaded = False

    return success_response(
        {
            "status": "ok",
            "db": "not_configured",
            "model_loaded": model_loaded,
            "version": current_app.config.get("API_VERSION"),
        }
    )
