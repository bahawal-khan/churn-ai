"""`/api/customers` (`docs/API.md`, `docs/DATABASE_SPEC.md` §2.6)."""

from __future__ import annotations

from flask import Blueprint, g, request

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.services import customer_service
from backend.utils import success_response

customers_bp = Blueprint("customers", __name__)


@customers_bp.get("")
@login_required
def list_customers():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    search = request.args.get("search")
    risk_level = request.args.get("risk_level")
    db = db_session.get_session()
    return success_response(
        customer_service.list_customers(
            db,
            organization_id=g.current_user.organization_id,
            page=page,
            page_size=page_size,
            search=search,
            risk_level=risk_level,
        )
    )


@customers_bp.get("/<int:customer_id>")
@login_required
def get_customer_detail(customer_id: int):
    db = db_session.get_session()
    return success_response(
        customer_service.get_customer_detail(
            db, organization_id=g.current_user.organization_id, customer_id=customer_id
        )
    )
