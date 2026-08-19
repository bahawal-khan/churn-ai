"""Writes `audit_logs` rows (`docs/DATABASE_SPEC.md` §2.11). Append-only —
no update/delete path exists anywhere in the service layer, matching
`API.md`'s cross-cutting notes (no audit-log routes at all).

Phase 8 scope: only the four auth event types this phase produces
(`login`, `logout`, `signup`, `password_reset`) are written here. The
remaining `event_type` values in the schema's `CHECK` constraint
(`dataset_upload`, `training_started`, `model_activated`, ...) are written
by the services that produce those events once those phases exist.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from backend.db.models import AuditLog


def write_audit_log(
    db: DBSession,
    *,
    organization_id: int | None,
    user_id: int | None,
    event_type: str,
    event_details: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            user_id=user_id,
            event_type=event_type,
            event_details=event_details,
        )
    )
