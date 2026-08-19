"""Session issuance/verification/revocation backing the cookie-based session
mechanism (`docs/BACKEND_SPEC.md` §4, `docs/DATABASE_SPEC.md` §2.3).

All datetimes are naive UTC, matching `backend/db/models.py`'s `_utcnow()`
convention (see that module's docstring for why — SQLite round-trips
tz-aware datetimes back as naive, so mixing the two raises on comparison).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from flask import Response
from sqlalchemy import update
from sqlalchemy.orm import Session as DBSession

from backend.db.models import Session as SessionRecord

SESSION_COOKIE_NAME = "churnai_session"
_SESSION_ID_BYTES = 32


def _utcnow() -> datetime:
    return datetime.utcnow()


def generate_session_id() -> str:
    return secrets.token_urlsafe(_SESSION_ID_BYTES)


def create_session(
    db: DBSession, user_id: int, ttl_days: int, user_agent: str | None
) -> SessionRecord:
    now = _utcnow()
    record = SessionRecord(
        id=generate_session_id(),
        user_id=user_id,
        created_at=now,
        expires_at=now + timedelta(days=ttl_days),
        user_agent=user_agent,
    )
    db.add(record)
    db.flush()
    return record


def get_valid_session(db: DBSession, session_id: str | None) -> SessionRecord | None:
    """A session is valid only if `revoked_at IS NULL AND expires_at > now()`
    (`docs/DATABASE_SPEC.md` §2.3) — the exact condition `GET /api/auth/session`
    checks."""
    if not session_id:
        return None
    record = db.get(SessionRecord, session_id)
    if record is None:
        return None
    if record.revoked_at is not None:
        return None
    if record.expires_at <= _utcnow():
        return None
    return record


def revoke_session(db: DBSession, record: SessionRecord) -> None:
    record.revoked_at = _utcnow()


def revoke_all_sessions_for_user(db: DBSession, user_id: int) -> None:
    """Used on password reset (`docs/BACKEND_SPEC.md` §4: "invalidates ...
    all existing sessions for that user")."""
    db.execute(
        update(SessionRecord)
        .where(SessionRecord.user_id == user_id, SessionRecord.revoked_at.is_(None))
        .values(revoked_at=_utcnow())
    )


def set_session_cookie(response: Response, session_id: str, ttl_days: int, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        max_age=ttl_days * 24 * 3600,
        httponly=True,
        secure=secure,
        samesite="Lax",
        path="/",
    )


def clear_session_cookie(response: Response, secure: bool) -> None:
    response.delete_cookie(
        SESSION_COOKIE_NAME, path="/", httponly=True, secure=secure, samesite="Lax"
    )
