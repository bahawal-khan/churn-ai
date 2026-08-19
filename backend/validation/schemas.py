"""Pydantic request-envelope schemas (`docs/BACKEND_SPEC.md` §5: "every route
with a request body ... validates it against a Pydantic model before calling
its service"). These validate request *shape* only — the ML feature values
inside `customer_data` are dynamic per active model and are validated
separately against that model's `feature_schema`
(`backend/validation/feature_validation.py`), since no static Pydantic model
can know a schema that changes with which model is active.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class SinglePredictionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    customer_data: dict[str, Any]
    customer_id: str | None = None
