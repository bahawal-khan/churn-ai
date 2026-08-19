"""`@login_required` and the ownership-check helper (`docs/BACKEND_SPEC.md`
§4: "every non-auth, non-health route uses it").
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from flask import g, request

from backend.auth.session import SESSION_COOKIE_NAME, get_valid_session
from backend.db import session as db_session
from backend.db.models import User
from backend.errors.exceptions import NotFoundError, SessionExpiredError


def login_required(view: Callable) -> Callable:
    @wraps(view)
    def wrapper(*args, **kwargs):
        db = db_session.get_session()
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        record = get_valid_session(db, session_id)
        if record is None:
            raise SessionExpiredError("Your session has expired. Please log in again.")
        user = db.get(User, record.user_id)
        if user is None:
            raise SessionExpiredError("Your session has expired. Please log in again.")
        g.current_user = user
        g.current_session = record
        return view(*args, **kwargs)

    return wrapper


def ownership_required(resource_organization_id: int | None) -> None:
    """Call after loading a tenant-scoped resource, before returning it.
    Raises `404 NOT_FOUND` (not `403`) on a cross-tenant access attempt so a
    caller can't distinguish "not yours" from "doesn't exist"
    (`docs/DATABASE_SPEC.md` §6 — avoids confirming a resource's existence to
    an unauthorized caller)."""
    current_user = getattr(g, "current_user", None)
    if current_user is None or resource_organization_id != current_user.organization_id:
        raise NotFoundError("The requested resource was not found.")
