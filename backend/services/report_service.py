"""`/api/reports` (`docs/API.md`).

No `reports` table exists in `docs/DATABASE_SPEC.md` §2 — a gap in the spec
set (`API.md` defines the endpoint group, the schema document never adds
the backing table). Rather than inventing a new migration for this phase,
reports are persisted as files with a JSON metadata sidecar, scoped per-org
by directory (`{REPORTS_STORAGE_DIR}/{organization_id}/{report_id}.csv` +
`.json`) — this keeps `GET /api/reports` (list) and
`GET /api/reports/:id/download` real and org-isolated without a schema
change. Flagged explicitly in the Phase 9 report rather than silently
worked around, matching this codebase's existing precedent
(`scripts/seed_baseline_model.py`'s documented schema-gap workaround).

**Format:** CSV only in this phase. `docs/API.md` itself says PDF is
"format TBD... based on tooling actually wired up" — no PDF library is in
`requirements.txt`, and adding one isn't justified by this phase's actual
need (`CLAUDE.md`: don't add packages before the phase that needs them).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session as DBSession

from backend.db.models import Customer, Prediction
from backend.errors.exceptions import NotFoundError, ValidationError

REPORT_TYPES = ("predictions_summary", "customers_summary")


def _org_dir(reports_dir: Path, organization_id: int) -> Path:
    return Path(reports_dir) / str(organization_id)


def _predictions_dataframe(db: DBSession, organization_id: int, filters: dict[str, Any]) -> pd.DataFrame:
    query = db.query(Prediction).filter(Prediction.organization_id == organization_id)
    risk_level = filters.get("risk_level")
    if risk_level:
        query = query.filter(Prediction.risk_level == risk_level)
    rows = query.order_by(Prediction.created_at.desc()).all()
    return pd.DataFrame(
        [
            {
                "prediction_id": r.id,
                "customer_id": r.customer_id,
                "model_id": r.model_id,
                "prediction_type": r.prediction_type,
                "churn_probability": r.churn_probability,
                "predicted_class": int(r.predicted_class),
                "risk_level": r.risk_level,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    )


def _customers_dataframe(db: DBSession, organization_id: int) -> pd.DataFrame:
    customers = db.query(Customer).filter(Customer.organization_id == organization_id).all()
    latest_by_customer: dict[int, Prediction] = {}
    predictions = (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id, Prediction.customer_id.isnot(None))
        .order_by(Prediction.created_at.desc())
        .all()
    )
    for p in predictions:
        latest_by_customer.setdefault(p.customer_id, p)

    rows = []
    for c in customers:
        latest = latest_by_customer.get(c.id)
        rows.append(
            {
                "customer_id": c.id,
                "external_customer_id": c.external_customer_id,
                "actual_churn_label": c.actual_churn_label,
                "latest_churn_probability": latest.churn_probability if latest else None,
                "latest_risk_level": latest.risk_level if latest else None,
                "created_at": c.created_at.isoformat(),
            }
        )
    return pd.DataFrame(rows)


def generate_report(
    db: DBSession,
    *,
    organization_id: int,
    user_id: int | None,
    report_type: str,
    filters: dict[str, Any],
    reports_dir: Path,
) -> dict[str, Any]:
    if report_type not in REPORT_TYPES:
        raise ValidationError(f"report_type must be one of {list(REPORT_TYPES)}.")

    df = (
        _predictions_dataframe(db, organization_id, filters)
        if report_type == "predictions_summary"
        else _customers_dataframe(db, organization_id)
    )

    report_id = uuid.uuid4().hex
    org_dir = _org_dir(reports_dir, organization_id)
    org_dir.mkdir(parents=True, exist_ok=True)

    csv_path = org_dir / f"{report_id}.csv"
    df.to_csv(csv_path, index=False)

    metadata = {
        "id": report_id,
        "report_type": report_type,
        "filters": filters,
        "row_count": int(len(df)),
        "created_at": datetime.utcnow().isoformat(),
        "created_by_user_id": user_id,
    }
    (org_dir / f"{report_id}.json").write_text(json.dumps(metadata), encoding="utf-8")
    return metadata


def list_reports(*, organization_id: int, reports_dir: Path, page: int, page_size: int) -> dict[str, Any]:
    org_dir = _org_dir(reports_dir, organization_id)
    if not org_dir.exists():
        rows: list[dict[str, Any]] = []
    else:
        rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(org_dir.glob("*.json"))]
        rows.sort(key=lambda r: r["created_at"], reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    return {
        "data": page_rows,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        },
    }


def get_report_csv_path(*, organization_id: int, reports_dir: Path, report_id: str) -> Path:
    csv_path = _org_dir(reports_dir, organization_id) / f"{report_id}.csv"
    if not csv_path.exists():
        raise NotFoundError(f"No report found with id {report_id!r}.")
    return csv_path
