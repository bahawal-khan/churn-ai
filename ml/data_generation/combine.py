"""Combine the IBM benchmark dataset with the Pakistan/India synthetic
datasets into the single development/benchmark dataset (`docs/PROJECT_SPEC.md`
§3.1): ~21,043 records total, every row carrying a `Source` provenance
column (`IBM` / `Pakistan-Synthetic` / `India-Synthetic`) per the binding
data-integrity rule (§3.6) — synthetic records are never merged in without
a label identifying them as synthetic.

The IBM subset is reduced to the modeling schema contract (`docs/ML_SPEC.md`
§1) plus `CustomerID`/`Source` here, so all three sources share one
column layout. `Total Charges` is coerced to numeric and the 11 known
blank-value rows (`docs/PROJECT_SPEC.md` §2.1) are imputed as 0, matching
their zero-tenure status.

Run directly: `python -m ml.data_generation.combine`
"""

from __future__ import annotations

import pandas as pd

from ml.config import (
    DATA_PROCESSED_DIR,
    IBM_RAW_CSV,
    MODELING_COLUMNS,
    SOURCE_IBM,
    TARGET_COLUMN,
)
from ml.data_generation import india_generator, pakistan_generator

OUTPUT_PATH = DATA_PROCESSED_DIR / "combined_development_dataset.csv"


def load_ibm_subset() -> pd.DataFrame:
    df = pd.read_csv(IBM_RAW_CSV, dtype=str)

    total_charges = pd.to_numeric(df["Total Charges"], errors="coerce").fillna(0.0)
    monthly_charges = pd.to_numeric(df["Monthly Charges"], errors="coerce")
    tenure_months = pd.to_numeric(df["Tenure Months"], errors="coerce").astype(int)
    churn_value = pd.to_numeric(df["Churn Value"], errors="coerce").astype(int)

    subset = df[[c for c in MODELING_COLUMNS if c not in {"Tenure Months", "Monthly Charges", "Total Charges"}]].copy()
    subset["Tenure Months"] = tenure_months
    subset["Monthly Charges"] = monthly_charges
    subset["Total Charges"] = total_charges
    subset = subset[MODELING_COLUMNS]

    subset.insert(0, "CustomerID", df["CustomerID"])
    subset[TARGET_COLUMN] = churn_value
    subset["Source"] = SOURCE_IBM
    return subset


def combine() -> pd.DataFrame:
    ibm = load_ibm_subset()
    pk = pakistan_generator.generate().drop(columns=["_archetype"])
    ind = india_generator.generate().drop(columns=["_archetype"])

    combined = pd.concat([ibm, pk, ind], ignore_index=True)
    return combined


def main() -> None:
    combined = combine()
    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(combined)} combined development records to {OUTPUT_PATH}")
    print(combined["Source"].value_counts().to_string())


if __name__ == "__main__":
    main()
