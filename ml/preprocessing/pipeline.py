"""Preprocessing `ColumnTransformer` pipeline (`docs/ML_SPEC.md` §5).

Wraps `ml.features.engineer.FeatureEngineer` (Phase 3) and a
`ColumnTransformer` (numerical impute+scale, categorical impute+one-hot) into
a single `sklearn.Pipeline` per ML_SPEC §5:

    ColumnTransformer(
      numerical:   SimpleImputer(strategy="median") -> StandardScaler
      categorical: SimpleImputer(strategy="most_frequent") -> OneHotEncoder(handle_unknown="ignore")
    )
    -> wrapped in a Pipeline with feature engineering applied first

Two variants are built from the same `ColumnTransformer` definition:
`scale=True` for Logistic Regression / the ANN (both need scaled numeric
inputs), `scale=False` for tree-based baselines (Random Forest / Gradient
Boosting), which don't need scaling but must see identical
imputation/encoding on the same engineered feature set for an apples-to-
apples comparison (ML_SPEC §5). This module only builds and fits the
pipeline — it trains no model (out of this phase's scope).

Leakage/production-feature exclusion is structural, not a naming
convention: `NUMERIC_COLUMNS`/`CATEGORICAL_COLUMNS` below are the *entire*
input-column allowlist passed to `ColumnTransformer`. `Source`, `CustomerID`,
`Churn Label`, `Churn Score`, and `Churn Reason` simply never appear in
either list, so they cannot reach a fitted model even if a caller
accidentally left them in the input DataFrame (`docs/PROJECT_SPEC.md` binding
cross-cutting rule; `docs/ML_SPEC.md` §1, §6).
"""

from __future__ import annotations

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.features.engineer import (
    ENGINEERED_BOOLEAN_COLUMNS,
    ENGINEERED_CATEGORICAL_COLUMNS,
    ENGINEERED_NUMERIC_COLUMNS,
    FeatureEngineer,
)

# Raw modeling columns (ml.config.MODELING_COLUMNS), split by how
# preprocessing treats them.
RAW_NUMERIC_COLUMNS = ["Tenure Months", "Monthly Charges", "Total Charges"]
RAW_CATEGORICAL_COLUMNS = [
    "Gender",
    "Senior Citizen",
    "Partner",
    "Dependents",
    "Phone Service",
    "Multiple Lines",
    "Internet Service",
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
    "Streaming TV",
    "Streaming Movies",
    "Contract",
    "Paperless Billing",
    "Payment Method",
]

# `CLTV` is not part of `ml.config.MODELING_COLUMNS` and is absent from
# `combined_development_dataset.csv` entirely (structurally absent for the
# two synthetic sources, ml/features/FEATURES.md) — there is nothing to
# impute here; it stays excluded, per ML_SPEC §1's "conditional column" rule.
NUMERIC_COLUMNS = RAW_NUMERIC_COLUMNS + ENGINEERED_NUMERIC_COLUMNS
CATEGORICAL_COLUMNS = RAW_CATEGORICAL_COLUMNS + ENGINEERED_BOOLEAN_COLUMNS + ENGINEERED_CATEGORICAL_COLUMNS


def _numeric_branch(scale: bool) -> Pipeline:
    steps: list[tuple[str, object]] = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        steps.append(("scale", StandardScaler()))
    return Pipeline(steps)


def _categorical_branch() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )


def build_column_transformer(scale: bool = True) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("numeric", _numeric_branch(scale), NUMERIC_COLUMNS),
            ("categorical", _categorical_branch(), CATEGORICAL_COLUMNS),
        ]
    )


def build_preprocessing_pipeline(scale: bool = True) -> Pipeline:
    """Full ML_SPEC §5 pipeline: feature engineering (§4), then impute/encode
    (and scale, if `scale=True`). Must be fit on the training split only —
    `fit()`/`fit_transform()` on validation, test, or inference data would
    leak information about their distribution into imputation/scaling
    statistics (ML_SPEC §5's "strict rule")."""
    return Pipeline(
        [
            ("feature_engineering", FeatureEngineer()),
            ("column_transform", build_column_transformer(scale=scale)),
        ]
    )
