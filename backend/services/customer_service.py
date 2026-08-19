"""`/api/customers` (`docs/API.md`, `docs/DATABASE_SPEC.md` §2.6).

Read-only: `customers` rows are written by `dataset_service`
(ingestion) and never directly through this module.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as DBSession

from backend.db.models import Customer, Explanation, Prediction
from backend.errors.exceptions import NotFoundError

RISK_LEVELS = ("low", "medium", "high")


def _serialize_customer(customer: Customer, *, latest_risk_level: str | None = None) -> dict[str, Any]:
    return {
        "id": customer.id,
        "organization_id": customer.organization_id,
        "dataset_id": customer.dataset_id,
        "external_customer_id": customer.external_customer_id,
        "feature_data": customer.feature_data,
        "actual_churn_label": customer.actual_churn_label,
        "latest_risk_level": latest_risk_level,
        "created_at": customer.created_at.isoformat(),
    }


def _serialize_prediction(prediction: Prediction, explanation: Explanation | None) -> dict[str, Any]:
    return {
        "id": prediction.id,
        "model_id": prediction.model_id,
        "prediction_type": prediction.prediction_type,
        "churn_probability": prediction.churn_probability,
        "predicted_class": prediction.predicted_class,
        "risk_level": prediction.risk_level,
        "batch_job_id": prediction.batch_job_id,
        "created_at": prediction.created_at.isoformat(),
        "explanation": (
            {
                "shap_values": explanation.shap_values,
                "base_value": explanation.base_value,
                "top_factors": explanation.top_factors,
            }
            if explanation is not None
            else None
        ),
    }


def _latest_prediction_by_customer(db: DBSession, *, organization_id: int, customer_ids: list[int]) -> dict[int, Prediction]:
    if not customer_ids:
        return {}
    rows = (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id, Prediction.customer_id.in_(customer_ids))
        .order_by(Prediction.created_at.desc())
        .all()
    )
    latest: dict[int, Prediction] = {}
    for row in rows:
        if row.customer_id not in latest:
            latest[row.customer_id] = row
    return latest


def list_customers(
    db: DBSession,
    *,
    organization_id: int,
    page: int,
    page_size: int,
    search: str | None = None,
    risk_level: str | None = None,
) -> dict[str, Any]:
    query = db.query(Customer).filter(Customer.organization_id == organization_id)
    if search:
        needle = search.strip().lower()
        query = query.filter(Customer.external_customer_id.ilike(f"%{needle}%"))
    query = query.order_by(Customer.created_at.desc())

    all_matching = query.all()
    latest_by_customer = _latest_prediction_by_customer(
        db, organization_id=organization_id, customer_ids=[c.id for c in all_matching]
    )

    rows = []
    for customer in all_matching:
        latest = latest_by_customer.get(customer.id)
        level = latest.risk_level if latest else None
        if risk_level and level != risk_level:
            continue
        rows.append(_serialize_customer(customer, latest_risk_level=level))

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


def get_customer_detail(db: DBSession, *, organization_id: int, customer_id: int) -> dict[str, Any]:
    customer = db.get(Customer, customer_id)
    if customer is None or customer.organization_id != organization_id:
        raise NotFoundError("The requested customer was not found.")

    predictions = (
        db.query(Prediction)
        .filter(Prediction.organization_id == organization_id, Prediction.customer_id == customer_id)
        .order_by(Prediction.created_at.desc())
        .all()
    )
    explanations_by_prediction = {
        e.prediction_id: e
        for e in db.query(Explanation).filter(Explanation.prediction_id.in_([p.id for p in predictions])).all()
    } if predictions else {}

    latest_risk_level = predictions[0].risk_level if predictions else None

    return {
        "customer": _serialize_customer(customer, latest_risk_level=latest_risk_level),
        "predictions": [
            _serialize_prediction(p, explanations_by_prediction.get(p.id)) for p in predictions
        ],
    }
