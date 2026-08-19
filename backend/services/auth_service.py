"""Signup/login/logout/forgot-password/reset-password business logic
(`docs/BACKEND_SPEC.md` §4). Flask-agnostic (no `current_app`/`request`
access) so it's testable without a request context — routes pass plain
values (including config like `session_ttl_days`) in.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from backend.auth import session as session_manager
from backend.auth.password import hash_password, verify_password
from backend.auth.tokens import generate_reset_token, hash_reset_token
from backend.db.models import Organization, PasswordResetToken
from backend.db.models import Session as SessionRecord
from backend.db.models import User
from backend.errors.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidResetTokenError,
)
from backend.services import audit_service

logger = logging.getLogger("churnai.backend.auth")


def _utcnow() -> datetime:
    return datetime.utcnow()


def _find_user_by_email(db: DBSession, email: str) -> User | None:
    return db.query(User).filter(User.email == email).one_or_none()


def signup(
    db: DBSession,
    *,
    email: str,
    password: str,
    full_name: str,
    session_ttl_days: int,
    user_agent: str | None,
) -> tuple[User, SessionRecord]:
    """`docs/BACKEND_SPEC.md` §4: validate email/uniqueness/password (done by
    the route's Pydantic schema before this is called) -> hash password ->
    create `users` row + a default `organizations` row -> issue session."""
    if _find_user_by_email(db, email) is not None:
        raise EmailAlreadyExistsError("An account with this email already exists.")

    organization = Organization(name=f"{full_name}'s workspace")
    db.add(organization)
    db.flush()

    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        organization_id=organization.id,
    )
    db.add(user)
    db.flush()

    session_record = session_manager.create_session(db, user.id, session_ttl_days, user_agent)
    audit_service.write_audit_log(
        db, organization_id=organization.id, user_id=user.id, event_type="signup"
    )
    db.commit()
    return user, session_record


def login(
    db: DBSession,
    *,
    email: str,
    password: str,
    session_ttl_days: int,
    user_agent: str | None,
) -> tuple[User, SessionRecord]:
    """Generic `INVALID_CREDENTIALS` on any failure — no user-enumeration
    hint via error wording (`docs/BACKEND_SPEC.md` §4)."""
    user = _find_user_by_email(db, email)
    if user is None or not verify_password(user.password_hash, password):
        raise InvalidCredentialsError("Invalid email or password.")

    session_record = session_manager.create_session(db, user.id, session_ttl_days, user_agent)
    audit_service.write_audit_log(
        db, organization_id=user.organization_id, user_id=user.id, event_type="login"
    )
    db.commit()
    return user, session_record


def logout(db: DBSession, session_record: SessionRecord, user: User) -> None:
    session_manager.revoke_session(db, session_record)
    audit_service.write_audit_log(
        db, organization_id=user.organization_id, user_id=user.id, event_type="logout"
    )
    db.commit()


def forgot_password(db: DBSession, *, email: str, reset_token_ttl_minutes: int) -> None:
    """Always behaves identically to the caller whether or not the email
    exists (`docs/API.md`: "always 200 ... to avoid enumeration") — the route
    never inspects this function's return value. No transactional email
    provider is wired up yet, so the raw token is logged server-side only
    (`docs/BACKEND_SPEC.md` §4: "logged in local dev if none configured"),
    never returned in the API response."""
    user = _find_user_by_email(db, email)
    if user is None:
        return

    raw_token = generate_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_reset_token(raw_token),
            expires_at=_utcnow() + timedelta(minutes=reset_token_ttl_minutes),
        )
    )
    db.commit()
    logger.info(
        "password_reset_token_issued user_id=%s token=%s "
        "(no email provider configured; logged for local dev per BACKEND_SPEC.md §4)",
        user.id,
        raw_token,
    )


def reset_password(db: DBSession, *, raw_token: str, new_password: str) -> User:
    token_hash = hash_reset_token(raw_token)
    token_record = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == token_hash).one_or_none()
    )
    now = _utcnow()
    if token_record is None or token_record.used_at is not None or token_record.expires_at <= now:
        raise InvalidResetTokenError("This password reset link is invalid or has expired.")

    user = db.get(User, token_record.user_id)
    user.password_hash = hash_password(new_password)
    token_record.used_at = now
    session_manager.revoke_all_sessions_for_user(db, user.id)
    audit_service.write_audit_log(
        db, organization_id=user.organization_id, user_id=user.id, event_type="password_reset"
    )
    db.commit()
    return user
