"""`/api/analytics` (`docs/API.md`, `docs/PROJECT_SPEC.md` §19).

Every number here is computed at request time from stored `customers`/
`predictions` rows — never hard-coded or templated (binding rule,
`docs/PROJECT_SPEC.md` top of document). An org with no data yet gets
honest zero/empty results, not a plausible-looking placeholder.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session as DBSession

from ml import config as ml_config

from backend.db.models import Customer, Model, Prediction
from backend.services import model_registry

RISK_LEVELS = ("low", "medium", "high")
SEGMENT_FIELDS = ("Contract", "Senior Citizen", "Dependents")


def _latest_prediction_per_customer(db: DBSession, organization_id: int) -> dict[int, Prediction]:
    rows = (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id, Prediction.customer_id.isnot(None))
        .order_by(Prediction.created_at.desc())
        .all()
    )
    latest: dict[int, Prediction] = {}
    for row in rows:
        if row.customer_id not in latest:
            latest[row.customer_id] = row
    return latest


def active_model_status(db: DBSession, organization_id: int) -> dict[str, Any]:
    try:
        _bundle, model_row = model_registry.get_active_bundle_for_org(db, organization_id)
    except Exception:
        return {"available": False}

    if model_row is not None:
        return {
            "available": True,
            "model_id": model_row.id,
            "algorithm": model_row.algorithm,
            "model_type": model_row.model_type,
            "version": model_row.version,
            "is_baseline": model_row.model_type == "baseline_global",
        }
    return {"available": True, "model_id": None, "algorithm": None, "model_type": None, "is_baseline": True}


def dashboard_summary(db: DBSession, organization_id: int) -> dict[str, Any]:
    total_customers = db.query(Customer).filter(Customer.organization_id == organization_id).count()
    latest = _latest_prediction_per_customer(db, organization_id)

    at_risk = sum(1 for p in latest.values() if p.risk_level in ("medium", "high"))
    high_risk = sum(1 for p in latest.values() if p.risk_level == "high")
    scored = len(latest)
    predicted_churn_rate = (sum(1 for p in latest.values() if p.predicted_class) / scored) if scored else None
    avg_churn_probability = (sum(p.churn_probability for p in latest.values()) / scored) if scored else None

    return {
        "total_customers": total_customers,
        "scored_customers": scored,
        "at_risk_customers": at_risk,
        "high_risk_customers": high_risk,
        "predicted_churn_rate": predicted_churn_rate,
        "avg_churn_probability": avg_churn_probability,
        "active_model": active_model_status(db, organization_id),
    }


def risk_distribution(db: DBSession, organization_id: int) -> dict[str, Any]:
    latest = _latest_prediction_per_customer(db, organization_id)
    counts = {level: 0 for level in RISK_LEVELS}
    for p in latest.values():
        counts[p.risk_level] += 1
    return {"counts": counts, "scored_customers": len(latest)}


def churn_trend(db: DBSession, organization_id: int) -> dict[str, Any]:
    rows = (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id)
        .order_by(Prediction.created_at.asc())
        .all()
    )
    by_date: dict[str, list[Prediction]] = defaultdict(list)
    for row in rows:
        by_date[row.created_at.date().isoformat()].append(row)

    points = [
        {
            "date": date,
            "prediction_count": len(preds),
            "predicted_churn_rate": sum(1 for p in preds if p.predicted_class) / len(preds),
            "avg_churn_probability": sum(p.churn_probability for p in preds) / len(preds),
        }
        for date, preds in sorted(by_date.items())
    ]
    return {"points": points}


def top_drivers(db: DBSession, organization_id: int) -> dict[str, Any]:
    try:
        _bundle, model_row = model_registry.get_active_bundle_for_org(db, organization_id)
    except Exception:
        return {"available": False, "feature_importance": []}

    artifact_path = model_row.artifact_path if model_row is not None else None
    if artifact_path is None:
        return {"available": False, "feature_importance": []}

    global_shap_path = Path(artifact_path) if Path(artifact_path).is_absolute() else ml_config.REPO_ROOT / artifact_path
    global_shap_path = global_shap_path / "global_shap.json"
    if not global_shap_path.exists():
        return {"available": False, "feature_importance": []}

    payload = json.loads(global_shap_path.read_text(encoding="utf-8"))
    return {"available": True, **payload}


def segments(db: DBSession, organization_id: int) -> dict[str, Any]:
    latest = _latest_prediction_per_customer(db, organization_id)
    customers = {
        c.id: c
        for c in db.query(Customer).filter(Customer.organization_id == organization_id).all()
    }

    result: dict[str, dict[str, dict[str, int]]] = {}
    for field in SEGMENT_FIELDS:
        by_value: dict[str, dict[str, int]] = defaultdict(lambda: {level: 0 for level in RISK_LEVELS})
        for customer_id, prediction in latest.items():
            customer = customers.get(customer_id)
            if customer is None:
                continue
            value = customer.feature_data.get(field)
            if value is None:
                continue
            by_value[str(value)][prediction.risk_level] += 1
        result[field] = dict(by_value)
    return {"segments": result}
