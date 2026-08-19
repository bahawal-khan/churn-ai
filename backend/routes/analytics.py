"""`/api/analytics` (`docs/API.md`, `docs/PROJECT_SPEC.md` §19)."""

from __future__ import annotations

from flask import Blueprint, g

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.services import analytics_service
from backend.utils import success_response

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/dashboard")
@login_required
def get_dashboard():
    db = db_session.get_session()
    return success_response(analytics_service.dashboard_summary(db, g.current_user.organization_id))


@analytics_bp.get("/risk-distribution")
@login_required
def get_risk_distribution():
    db = db_session.get_session()
    return success_response(analytics_service.risk_distribution(db, g.current_user.organization_id))


@analytics_bp.get("/churn-trend")
@login_required
def get_churn_trend():
    db = db_session.get_session()
    return success_response(analytics_service.churn_trend(db, g.current_user.organization_id))


@analytics_bp.get("/top-drivers")
@login_required
def get_top_drivers():
    db = db_session.get_session()
    return success_response(analytics_service.top_drivers(db, g.current_user.organization_id))


@analytics_bp.get("/segments")
@login_required
def get_segments():
    db = db_session.get_session()
    return success_response(analytics_service.segments(db, g.current_user.organization_id))
