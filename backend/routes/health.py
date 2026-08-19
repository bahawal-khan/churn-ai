"""`GET /api/health` (`docs/API.md`): unauthenticated, used by deployment
monitoring. `db` now runs a real query (`docs/DEPLOYMENT.md` §8: "returns
{ status, db, version }") now that Phase 8 adds the SQLAlchemy DB layer.
"""

from __future__ import annotations

from flask import Blueprint, current_app
from sqlalchemy import text

from backend.db import session as db_session
from backend.services import model_registry
from backend.utils import success_response

health_bp = Blueprint("health", __name__)


def _db_status() -> str:
    try:
        db_session.get_session().execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"


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
            "db": _db_status(),
            "model_loaded": model_loaded,
            "version": current_app.config.get("API_VERSION"),
        }
    )
