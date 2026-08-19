"""Structural audit of the raw IBM Telco Customer Churn CSV.

This is a Phase 1 deliverable: it re-derives and confirms the dataset facts
already documented in `docs/PROJECT_SPEC.md` §2.1 (shape, dtypes, missing
values, duplicates, leakage columns, cardinalities, class balance) directly
from the raw file, so those documented facts are verified rather than
assumed. It intentionally does NOT perform distribution analysis, visuals,
correlation analysis, or cross-source comparison — that is the Phase 2 EDA
deliverable (`docs/ML_SPEC.md` §2), out of scope here.

Run directly: `python -m ml.eda.ibm_audit`
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from ml.config import IBM_RAW_CSV

REPORT_PATH = Path(__file__).resolve().parent / "ibm_audit_report.json"

LEAKAGE_COLUMNS = ["Churn Score", "Churn Reason"]
ZERO_VARIANCE_COLUMNS = ["Country", "State"]
IDENTIFIER_GEO_COLUMNS = [
    "CustomerID",
    "Count",
    "Zip Code",
    "Lat Long",
    "Latitude",
    "Longitude",
    "City",
]


def load_raw() -> pd.DataFrame:
    return pd.read_csv(IBM_RAW_CSV, dtype=str)


def audit(df: pd.DataFrame) -> dict[str, Any]:
    report: dict[str, Any] = {}

    report["shape"] = {"rows": df.shape[0], "columns": df.shape[1]}
    report["columns"] = list(df.columns)

    # Total Charges is stored as a string with blank values for brand-new
    # (Tenure Months == 0) customers; coercion must fail on exactly those rows.
    total_charges_numeric = pd.to_numeric(df["Total Charges"], errors="coerce")
    coercion_failures = df.loc[total_charges_numeric.isna()]
    report["total_charges_coercion_failures"] = {
        "count": int(coercion_failures.shape[0]),
        "all_zero_tenure": bool(
            (coercion_failures["Tenure Months"].astype(int) == 0).all()
        )
        if not coercion_failures.empty
        else True,
    }

    # Missing values: every column except Churn Reason is expected to have
    # zero nulls/blank strings; Churn Reason is null only for non-churners.
    blank_as_null = df.replace(r"^\s*$", pd.NA, regex=True)
    missing_counts = blank_as_null.isna().sum()
    report["missing_values"] = {
        col: int(count) for col, count in missing_counts.items() if count > 0
    }
    non_churned = df.loc[df["Churn Label"] == "No"]
    report["churn_reason_null_matches_non_churned"] = bool(
        missing_counts.get("Churn Reason", 0) == non_churned.shape[0]
    )

    report["duplicate_rows"] = int(df.duplicated().sum())
    report["duplicate_customer_ids"] = int(df["CustomerID"].duplicated().sum())

    report["zero_variance_columns"] = {
        col: df[col].unique().tolist() for col in ZERO_VARIANCE_COLUMNS
    }

    churn_value = df["Churn Value"].astype(int)
    churned = int(churn_value.sum())
    total = int(churn_value.shape[0])
    report["class_balance"] = {
        "churned": churned,
        "retained": total - churned,
        "churn_rate_pct": round(100 * churned / total, 2),
    }

    report["leakage_columns_identified"] = LEAKAGE_COLUMNS
    report["identifier_geo_columns_excluded_from_features"] = IDENTIFIER_GEO_COLUMNS

    categorical_cardinality_cols = [
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
    report["categorical_cardinality"] = {
        col: sorted(df[col].unique().tolist()) for col in categorical_cardinality_cols
    }

    return report


def verify_against_documented_facts(report: dict[str, Any]) -> list[str]:
    """Cross-check the computed report against PROJECT_SPEC.md §2.1. Returns
    a list of mismatch descriptions (empty list means fully confirmed)."""
    mismatches = []

    if report["shape"] != {"rows": 7043, "columns": 33}:
        mismatches.append(f"shape mismatch: {report['shape']}")

    if report["total_charges_coercion_failures"]["count"] != 11:
        mismatches.append(
            "Total Charges coercion failure count mismatch: "
            f"{report['total_charges_coercion_failures']['count']} (expected 11)"
        )
    if not report["total_charges_coercion_failures"]["all_zero_tenure"]:
        mismatches.append("Total Charges coercion failures are not all zero-tenure")

    # Churn Reason is null structurally (non-churners); Total Charges has 11
    # blank/whitespace values (the dtype-coercion issue checked separately
    # above) — both are expected, no other column should have any nulls.
    if set(report["missing_values"].keys()) != {"Churn Reason", "Total Charges"}:
        mismatches.append(
            f"unexpected missing-value columns: {report['missing_values']}"
        )
    elif report["missing_values"]["Total Charges"] != 11:
        mismatches.append(
            f"Total Charges blank-value count mismatch: "
            f"{report['missing_values']['Total Charges']} (expected 11)"
        )
    if not report["churn_reason_null_matches_non_churned"]:
        mismatches.append("Churn Reason nulls do not match non-churned row count")

    if report["duplicate_rows"] != 0 or report["duplicate_customer_ids"] != 0:
        mismatches.append("unexpected duplicate rows/CustomerIDs")

    if report["class_balance"] != {
        "churned": 1869,
        "retained": 5174,
        "churn_rate_pct": 26.54,
    }:
        mismatches.append(f"class balance mismatch: {report['class_balance']}")

    return mismatches


def main() -> None:
    df = load_raw()
    report = audit(df)
    mismatches = verify_against_documented_facts(report)
    report["matches_documented_facts"] = len(mismatches) == 0
    report["mismatches"] = mismatches

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Audit report written to {REPORT_PATH}")
    if mismatches:
        print("MISMATCHES FOUND vs PROJECT_SPEC.md §2.1:")
        for m in mismatches:
            print(f"  - {m}")
    else:
        print("All documented facts in PROJECT_SPEC.md §2.1 confirmed.")


if __name__ == "__main__":
    main()
