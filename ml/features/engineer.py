"""Feature engineering for the churn modeling schema (`docs/ML_SPEC.md` §4).

Implements `FeatureEngineer`, an `sklearn`-compatible transformer that adds
the documented engineered features from ML_SPEC §4 / `docs/PROJECT_SPEC.md`
§6/§40 to a DataFrame already conforming to the modeling schema contract
(`ml.config.MODELING_COLUMNS`). Every feature here is a per-row derivation —
none involve a dataset-level aggregate statistic (mean, rate, etc.) — so
`fit` is stateless and `fit`/`transform` are safe to call identically on
train, validation, test, or single-row inference data without any
train/test-only fitting step or leakage risk (ML_SPEC §4: "any feature whose
computation involves an aggregate statistic must be fit on the training
split only"; none of these do). `fit` is retained only to satisfy the
sklearn Transformer interface so this class composes into the preprocessing
`Pipeline` that a later phase builds (ML_SPEC §4/§5) — this module does not
itself build that `ColumnTransformer`, perform imputation/encoding/scaling,
or run a train/test split (out of Phase 3 scope).

`CLTV` is intentionally not engineered here. Per `ml/eda/FINDINGS.md`, it
exists only on the IBM source and is structurally absent for the two
synthetic sources — folding it in requires an imputation strategy, which is
a preprocessing (ML_SPEC §5) decision, not a feature-engineering one. It
remains excluded from `ml.config.MODELING_COLUMNS` and out of scope here;
the decision is deferred to whichever phase builds the preprocessing
pipeline.

Run directly: `python -m ml.features.engineer`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from ml.config import DATA_PROCESSED_DIR, TARGET_COLUMN

# The six columns that share the "No internet service" placeholder value
# when `Internet Service == "No"` (ML_SPEC §4: `has_internet` rationale).
INTERNET_ADDON_COLUMNS = [
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
    "Streaming TV",
    "Streaming Movies",
]

# Risk-reducing add-ons, grouped separately from entertainment add-ons
# (ML_SPEC §4: `has_protection_addon` rationale).
PROTECTION_ADDON_COLUMNS = ["Online Security", "Device Protection", "Tech Support"]

# Entertainment add-ons (ML_SPEC §4: `has_streaming_addon` rationale).
STREAMING_ADDON_COLUMNS = ["Streaming TV", "Streaming Movies"]

# Matches the bucketing used in `ml/eda/full_eda.py`'s relationship analysis
# (§2.4), so `tenure_group` reproduces the same non-linear churn-vs-tenure
# buckets already validated against real data in Phase 2. The top edge is
# open-ended (not a fixed number like full_eda.py's 1000) so any tenure
# value that passes the data quality validator's plausibility check (up to
# `MAX_PLAUSIBLE_TENURE_MONTHS = 1200`, `ml/data_quality/validator.py`)
# still lands in a bucket instead of silently becoming NaN.
TENURE_BUCKET_BINS = [-1, 12, 24, 48, float("inf")]
TENURE_BUCKET_LABELS = ["0-12", "13-24", "25-48", "49+"]

# Columns this transformer reads. A subset of `ml.config.MODELING_COLUMNS` —
# only the ones the ML_SPEC §4 feature set actually derives from.
REQUIRED_INPUT_COLUMNS = sorted(
    {
        "Tenure Months",
        "Internet Service",
        "Total Charges",
        "Contract",
        "Payment Method",
        "Partner",
        "Dependents",
        *INTERNET_ADDON_COLUMNS,
    }
)

# Engineered columns this transformer adds, split by kind so a later
# preprocessing phase knows how each should be treated (numeric vs.
# boolean/categorical) without this module performing that treatment itself.
ENGINEERED_NUMERIC_COLUMNS = ["active_addon_count", "avg_monthly_value"]
ENGINEERED_BOOLEAN_COLUMNS = [
    "has_internet",
    "has_protection_addon",
    "has_streaming_addon",
    "contract_risk_flag",
    "payment_risk_flag",
    "family_flag",
]
ENGINEERED_CATEGORICAL_COLUMNS = ["tenure_group"]
ENGINEERED_COLUMNS = ENGINEERED_NUMERIC_COLUMNS + ENGINEERED_BOOLEAN_COLUMNS + ENGINEERED_CATEGORICAL_COLUMNS


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Adds the ML_SPEC §4 engineered features to a modeling-schema DataFrame.

    Stateless: `fit` does nothing and returns `self`; all output columns are
    computed row-wise from the input columns alone.
    """

    def fit(self, X: pd.DataFrame, y: Any = None) -> "FeatureEngineer":
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        missing = [c for c in REQUIRED_INPUT_COLUMNS if c not in X.columns]
        if missing:
            raise ValueError(f"Missing required columns for feature engineering: {missing}")

        df = X.copy()

        df["tenure_group"] = pd.cut(
            df["Tenure Months"], bins=TENURE_BUCKET_BINS, labels=TENURE_BUCKET_LABELS
        ).astype(str)

        df["has_internet"] = df["Internet Service"] != "No"

        addon_is_active = df[INTERNET_ADDON_COLUMNS] == "Yes"
        df["active_addon_count"] = addon_is_active.sum(axis=1)

        df["has_protection_addon"] = (df[PROTECTION_ADDON_COLUMNS] == "Yes").any(axis=1)
        df["has_streaming_addon"] = (df[STREAMING_ADDON_COLUMNS] == "Yes").any(axis=1)

        df["avg_monthly_value"] = df["Total Charges"] / df["Tenure Months"].clip(lower=1)

        df["contract_risk_flag"] = df["Contract"] == "Month-to-month"
        df["payment_risk_flag"] = df["Payment Method"] == "Electronic check"
        df["family_flag"] = (df["Partner"] == "Yes") | (df["Dependents"] == "Yes")

        return df


def _build_report(df: pd.DataFrame) -> dict[str, Any]:
    """Computes actual distributions of the engineered features (and, where
    the target is available, churn rate by feature) so Phase 3's findings
    reference real computed numbers rather than assumed ones, matching the
    Phase 2 EDA discipline (ML_SPEC §2.7)."""
    has_target = TARGET_COLUMN in df.columns
    report: dict[str, Any] = {
        "row_count": int(df.shape[0]),
        "engineered_columns": ENGINEERED_COLUMNS,
        "tenure_group_distribution": df["tenure_group"].value_counts().to_dict(),
        "has_internet_rate": round(float(df["has_internet"].mean()), 4),
        "active_addon_count_distribution": {
            str(k): int(v) for k, v in df["active_addon_count"].value_counts().sort_index().items()
        },
        "has_protection_addon_rate": round(float(df["has_protection_addon"].mean()), 4),
        "has_streaming_addon_rate": round(float(df["has_streaming_addon"].mean()), 4),
        "avg_monthly_value_stats": {
            "mean": round(float(df["avg_monthly_value"].mean()), 2),
            "std": round(float(df["avg_monthly_value"].std()), 2),
            "min": round(float(df["avg_monthly_value"].min()), 2),
            "max": round(float(df["avg_monthly_value"].max()), 2),
        },
        "contract_risk_flag_rate": round(float(df["contract_risk_flag"].mean()), 4),
        "payment_risk_flag_rate": round(float(df["payment_risk_flag"].mean()), 4),
        "family_flag_rate": round(float(df["family_flag"].mean()), 4),
        "engineered_columns_null_count": int(df[ENGINEERED_COLUMNS].isna().sum().sum()),
    }

    if has_target:
        report["churn_rate_by_tenure_group"] = {
            str(k): round(float(v), 4) for k, v in df.groupby("tenure_group", observed=True)[TARGET_COLUMN].mean().items()
        }
        for flag in (
            "has_protection_addon",
            "has_streaming_addon",
            "contract_risk_flag",
            "payment_risk_flag",
            "family_flag",
        ):
            report[f"churn_rate_by_{flag}"] = {
                str(k): round(float(v), 4) for k, v in df.groupby(flag, observed=True)[TARGET_COLUMN].mean().items()
            }

    return report


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    engineered = FeatureEngineer().fit_transform(df)
    report = _build_report(engineered)

    report_path = Path(__file__).resolve().parent / "feature_engineering_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Feature engineering report written to {report_path}")
    print(f"Engineered columns: {ENGINEERED_COLUMNS}")
    print(f"Null count across engineered columns: {report['engineered_columns_null_count']}")


if __name__ == "__main__":
    main()
