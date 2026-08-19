"""`/api/auth` (`docs/API.md`): signup, login, logout, session check,
forgot/reset password.
"""

from __future__ import annotations

from typing import Any

from flask import Blueprint, current_app, g, request
from pydantic import ValidationError as PydanticValidationError

from backend.auth.decorators import login_required
from backend.auth.session import clear_session_cookie, set_session_cookie
from backend.db import session as db_session
from backend.db.models import Organization, User
from backend.errors.exceptions import ValidationError
from backend.services import auth_service
from backend.utils import success_response
from backend.validation.schemas import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SignupRequest,
    UpdateProfileRequest,
)

auth_bp = Blueprint("auth", __name__)


def _parse(schema_cls, payload: Any):
    if payload is None:
        raise ValidationError("Request body must be valid JSON.")
    try:
        return schema_cls.model_validate(payload)
    except PydanticValidationError as exc:
        # `include_context=False`: this module's schemas raise plain
        # `ValueError`s from custom `field_validator`/`model_validator`
        # methods (password policy, email format, confirm-password match).
        # Pydantic's default `errors()` puts the raw exception *object* in
        # `ctx.error` for those, which `jsonify` cannot serialize — dropping
        # `ctx` is safe since `msg` already carries the human-readable text.
        raise ValidationError(
            "Invalid request body.",
            details={"errors": exc.errors(include_url=False, include_context=False)},
        ) from exc


def _user_profile(user: User, db: Any = None) -> dict[str, Any]:
    """Never includes `password_hash` (`docs/BACKEND_SPEC.md` §4).
    `organization_name` is an additive field (Phase 10: Settings/Topbar need
    it to display something more human than a bare `organization_id`) —
    looked up separately since no ORM relationship is declared on `User`
    (`docs/DATABASE_SPEC.md` querying convention throughout this codebase is
    explicit `db.query`/`db.get`, not relationship traversal)."""
    organization_name = None
    if db is not None:
        organization = db.get(Organization, user.organization_id)
        organization_name = organization.name if organization else None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.organization_id,
        "organization_name": organization_name,
        "theme_preference": user.theme_preference,
        "onboarding_completed_at": (
            user.onboarding_completed_at.isoformat() if user.onboarding_completed_at else None
        ),
        "created_at": user.created_at.isoformat(),
    }


def _cookie_secure() -> bool:
    return bool(current_app.config.get("SESSION_COOKIE_SECURE"))


def _session_ttl_days() -> int:
    return int(current_app.config.get("SESSION_TTL_DAYS"))


@auth_bp.post("/signup")
def post_signup():
    parsed = _parse(SignupRequest, request.get_json(silent=True))
    db = db_session.get_session()
    user, session_record = auth_service.signup(
        db,
        email=parsed.email,
        password=parsed.password,
        full_name=parsed.full_name,
        session_ttl_days=_session_ttl_days(),
        user_agent=request.headers.get("User-Agent"),
    )
    response, status = success_response(_user_profile(user, db), status=201)
    set_session_cookie(response, session_record.id, _session_ttl_days(), _cookie_secure())
    return response, status


@auth_bp.post("/login")
def post_login():
    parsed = _parse(LoginRequest, request.get_json(silent=True))
    db = db_session.get_session()
    user, session_record = auth_service.login(
        db,
        email=parsed.email,
        password=parsed.password,
        session_ttl_days=_session_ttl_days(),
        user_agent=request.headers.get("User-Agent"),
    )
    response, status = success_response(_user_profile(user, db))
    set_session_cookie(response, session_record.id, _session_ttl_days(), _cookie_secure())
    return response, status


@auth_bp.post("/logout")
@login_required
def post_logout():
    db = db_session.get_session()
    auth_service.logout(db, g.current_session, g.current_user)
    response, status = success_response({"logged_out": True})
    clear_session_cookie(response, _cookie_secure())
    return response, status


@auth_bp.get("/session")
@login_required
def get_session_route():
    db = db_session.get_session()
    return success_response(_user_profile(g.current_user, db))


@auth_bp.patch("/profile")
@login_required
def patch_profile():
    parsed = _parse(UpdateProfileRequest, request.get_json(silent=True))
    db = db_session.get_session()
    user = auth_service.update_profile(
        db,
        user=g.current_user,
        theme_preference=parsed.theme_preference,
        onboarding_completed=parsed.onboarding_completed,
    )
    return success_response(_user_profile(user, db))


@auth_bp.post("/forgot-password")
def post_forgot_password():
    parsed = _parse(ForgotPasswordRequest, request.get_json(silent=True))
    db = db_session.get_session()
    auth_service.forgot_password(
        db,
        email=parsed.email,
        reset_token_ttl_minutes=int(current_app.config.get("PASSWORD_RESET_TOKEN_TTL_MINUTES")),
    )
    return success_response(
        {"message": "If an account exists for that email, a password reset link has been sent."}
    )


@auth_bp.post("/reset-password")
def post_reset_password():
    parsed = _parse(ResetPasswordRequest, request.get_json(silent=True))
    db = db_session.get_session()
    auth_service.reset_password(db, raw_token=parsed.token, new_password=parsed.new_password)
    return success_response({"message": "Your password has been reset. Please log in again."})
