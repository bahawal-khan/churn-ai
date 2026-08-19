"""Phase 1 validation of the synthetic generators (`docs/PROJECT_SPEC.md`
§3.5): churn-rate-by-archetype and churn-rate-by-country tables, plus a
quick logistic-regression sanity check confirming expected feature signs
and an AUC well below 1.0 (target band 0.75-0.90 combined; also checks that
no single feature reaches a near-1.0 standalone AUC, i.e. churn is not
trivially separable by any one column).

This is a generator-validation sanity check, not the full Phase 2 EDA
(`docs/ML_SPEC.md` §2) — no visuals, no cross-source distribution study.

Run directly: `python -m ml.data_generation.validate`
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

from ml.config import RANDOM_SEED
from ml.data_generation import india_generator, pakistan_generator

REPORT_PATH = Path(__file__).resolve().parent / "validation_report.json"

# Overall synthetic churn rate must land in this band (docs/PROJECT_SPEC.md
# §3.5), broadly consistent with the IBM base rate of 26.54% while still
# varying meaningfully by archetype/country.
OVERALL_CHURN_RATE_BAND = (0.20, 0.35)

# Sanity-check logistic regression AUC must be learnable but not trivial.
SANITY_CHECK_AUC_BAND = (0.75, 0.90)

# No single raw/derived feature should come close to perfectly separating
# churn on its own.
SINGLE_FEATURE_AUC_CEILING = 0.95

# Expected coefficient sign per feature (docs/PROJECT_SPEC.md §3.5): +1 means
# the feature should increase churn probability, -1 means decrease it.
EXPECTED_FEATURE_SIGNS = {
    "contract_is_month_to_month": 1,
    "monthly_charges": 1,
    "tenure_months": -1,
    "no_tech_support": 1,
    "electronic_check_payment": 1,
    "has_family": -1,
}


def build_sanity_check_features(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "contract_is_month_to_month": (df["Contract"] == "Month-to-month").astype(int),
            "monthly_charges": df["Monthly Charges"],
            "tenure_months": df["Tenure Months"],
            "no_tech_support": (df["Tech Support"] != "Yes").astype(int),
            "electronic_check_payment": (df["Payment Method"] == "Electronic check").astype(int),
            "has_family": ((df["Partner"] == "Yes") | (df["Dependents"] == "Yes")).astype(int),
        }
    )


def churn_rate_by(df: pd.DataFrame, group_col: str) -> dict[str, float]:
    rates = df.groupby(group_col)["Churn Value"].mean()
    return {str(k): round(float(v), 4) for k, v in rates.items()}


def single_feature_aucs(features: pd.DataFrame, target: np.ndarray) -> dict[str, float]:
    aucs = {}
    for col in features.columns:
        try:
            aucs[col] = round(float(roc_auc_score(target, features[col])), 4)
        except ValueError:
            aucs[col] = None
    return aucs


def sanity_check_logistic_regression(features: pd.DataFrame, target: np.ndarray) -> dict:
    scaler = StandardScaler()
    x = scaler.fit_transform(features)
    model = LogisticRegression(max_iter=1000, random_state=RANDOM_SEED)
    model.fit(x, target)

    probs = model.predict_proba(x)[:, 1]
    auc = float(roc_auc_score(target, probs))

    coefficients = dict(zip(features.columns, model.coef_[0]))
    sign_matches = {
        feature: bool(np.sign(coefficients[feature]) == EXPECTED_FEATURE_SIGNS[feature])
        for feature in EXPECTED_FEATURE_SIGNS
    }

    return {
        "auc": round(auc, 4),
        "coefficients": {k: round(float(v), 4) for k, v in coefficients.items()},
        "expected_signs": EXPECTED_FEATURE_SIGNS,
        "sign_matches": sign_matches,
        "all_signs_match": all(sign_matches.values()),
    }


def validate() -> dict:
    pk = pakistan_generator.generate()
    ind = india_generator.generate()
    combined = pd.concat([pk, ind], ignore_index=True)

    report: dict = {}

    report["record_counts"] = {
        "pakistan": len(pk),
        "india": len(ind),
        "combined_synthetic": len(combined),
    }

    report["overall_churn_rate"] = {
        "pakistan": round(float(pk["Churn Value"].mean()), 4),
        "india": round(float(ind["Churn Value"].mean()), 4),
        "combined_synthetic": round(float(combined["Churn Value"].mean()), 4),
    }

    report["churn_rate_by_country"] = churn_rate_by(combined, "Source")
    report["churn_rate_by_archetype"] = {
        "pakistan": churn_rate_by(pk, "_archetype"),
        "india": churn_rate_by(ind, "_archetype"),
    }

    features = build_sanity_check_features(combined)
    target = combined["Churn Value"].to_numpy()

    report["single_feature_auc"] = single_feature_aucs(features, target)
    report["sanity_check_logistic_regression"] = sanity_check_logistic_regression(features, target)

    # --- Pass/fail gates -----------------------------------------------
    checks = {}

    overall_rate = report["overall_churn_rate"]["combined_synthetic"]
    checks["overall_churn_rate_in_band"] = OVERALL_CHURN_RATE_BAND[0] <= overall_rate <= OVERALL_CHURN_RATE_BAND[1]
    checks["pakistan_churn_rate_in_band"] = (
        OVERALL_CHURN_RATE_BAND[0] <= report["overall_churn_rate"]["pakistan"] <= OVERALL_CHURN_RATE_BAND[1]
    )
    checks["india_churn_rate_in_band"] = (
        OVERALL_CHURN_RATE_BAND[0] <= report["overall_churn_rate"]["india"] <= OVERALL_CHURN_RATE_BAND[1]
    )

    sanity_auc = report["sanity_check_logistic_regression"]["auc"]
    checks["sanity_check_auc_in_band"] = SANITY_CHECK_AUC_BAND[0] <= sanity_auc <= SANITY_CHECK_AUC_BAND[1]

    checks["all_expected_signs_match"] = report["sanity_check_logistic_regression"]["all_signs_match"]

    max_single_feature_auc = max(v for v in report["single_feature_auc"].values() if v is not None)
    checks["no_single_feature_near_perfect_auc"] = max_single_feature_auc < SINGLE_FEATURE_AUC_CEILING

    report["checks"] = checks
    report["all_checks_passed"] = all(checks.values())

    return report


def main() -> None:
    report = validate()
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Validation report written to {REPORT_PATH}")
    print(json.dumps(report["checks"], indent=2))
    if not report["all_checks_passed"]:
        raise SystemExit("Generator validation FAILED — see validation_report.json")
    print("All generator validation checks PASSED.")


if __name__ == "__main__":
    main()
