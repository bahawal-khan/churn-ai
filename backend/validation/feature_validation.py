"""Validates raw customer field values against an active model's recorded
`feature_schema` (`docs/ML_SPEC.md` §14, `docs/PROJECT_SPEC.md` §16.1) —
the dynamic, per-model counterpart to the static Pydantic envelope schemas.

Two entry points share the same per-field logic (`_validate_fields`):

- `validate_customer_record` — single-prediction JSON payloads. Raises on
  any problem (`SchemaMismatchError` for missing fields, `ValidationError`
  for bad values) since a single bad request has nothing else to fall back
  to.
- `validate_fields` — batch CSV rows. Returns errors instead of raising, so
  the caller can keep good rows and flag bad ones individually
  (`docs/PROJECT_SPEC.md` §16.1: "per-row for individual bad values").
"""

from __future__ import annotations

import math
from typing import Any

from backend.errors.exceptions import SchemaMismatchError, ValidationError

# Plausibility bounds mirroring `ml.data_quality.validator`'s
# `_check_invalid_values` (docs/ML_SPEC.md §3), applied here at the API
# boundary so a bad single-prediction value is rejected before it ever
# reaches the model rather than silently producing a low-quality prediction.
NUMERIC_FIELD_BOUNDS: dict[str, tuple[float, float | None]] = {
    "Tenure Months": (0, 1200),
    "Monthly Charges": (0, None),
    "Total Charges": (0, None),
}


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _match_category(raw_value: Any, categories: list[str]) -> str | None:
    normalized = str(raw_value).strip().lower()
    for category in categories:
        if category.strip().lower() == normalized:
            return category
    return None


def validate_fields(
    data: dict[str, Any], feature_schema: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Validates only the fields present in `data`/`feature_schema` pairwise —
    callers decide separately how to handle fields entirely absent from
    `data` (whole-request for single predictions, whole-file for batch,
    per `docs/PROJECT_SPEC.md` §16.1). Returns `(cleaned_values, field_errors)`;
    a field with an error is omitted from `cleaned_values`."""
    cleaned: dict[str, Any] = {}
    field_errors: dict[str, str] = {}

    for field in feature_schema:
        name = field["name"]
        raw_value = data.get(name)

        if _is_blank(raw_value):
            field_errors[name] = "Missing value."
            continue

        if field["dtype"] == "numeric":
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                field_errors[name] = f"Must be a number, got {raw_value!r}."
                continue
            if math.isnan(value) or math.isinf(value):
                field_errors[name] = f"Must be a finite number, got {raw_value!r}."
                continue
            low, high = NUMERIC_FIELD_BOUNDS.get(name, (None, None))
            if low is not None and value < low:
                field_errors[name] = f"Must be >= {low}, got {value}."
                continue
            if high is not None and value > high:
                field_errors[name] = f"Must be <= {high}, got {value}."
                continue
            cleaned[name] = value
        else:
            categories = field.get("categories", [])
            match = _match_category(raw_value, categories)
            if match is None:
                field_errors[name] = f"Must be one of {categories}, got {raw_value!r}."
                continue
            cleaned[name] = match

    return cleaned, field_errors


def validate_customer_record(
    data: dict[str, Any], feature_schema: list[dict[str, Any]]
) -> dict[str, Any]:
    """Full validation for a single-prediction request: missing required
    fields fail the whole request (`SchemaMismatchError`), any remaining
    bad values fail the whole request (`ValidationError`)."""
    if not isinstance(data, dict):
        raise ValidationError("'customer_data' must be a JSON object of field name to value.")

    missing = sorted(f["name"] for f in feature_schema if f["name"] not in data)
    if missing:
        raise SchemaMismatchError(
            "customer_data is missing required field(s): " + ", ".join(missing) + ".",
            details={"missing_fields": missing},
        )

    cleaned, field_errors = validate_fields(data, feature_schema)
    if field_errors:
        raise ValidationError(
            "One or more fields in customer_data failed validation.",
            details={"field_errors": field_errors},
        )
    return cleaned
