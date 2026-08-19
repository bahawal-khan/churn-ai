import pandas as pd
import pytest

from ml.config import DATA_PROCESSED_DIR, TARGET_COLUMN
from ml.features.engineer import (
    ENGINEERED_BOOLEAN_COLUMNS,
    ENGINEERED_CATEGORICAL_COLUMNS,
    ENGINEERED_COLUMNS,
    ENGINEERED_NUMERIC_COLUMNS,
    FeatureEngineer,
    REQUIRED_INPUT_COLUMNS,
)


def make_row(**overrides):
    row = {
        "Tenure Months": 10,
        "Internet Service": "Fiber optic",
        "Online Security": "No",
        "Online Backup": "No",
        "Device Protection": "No",
        "Tech Support": "No",
        "Streaming TV": "No",
        "Streaming Movies": "No",
        "Total Charges": 500.0,
        "Contract": "Month-to-month",
        "Payment Method": "Electronic check",
        "Partner": "No",
        "Dependents": "No",
    }
    row.update(overrides)
    return row


def df_of(*rows):
    return pd.DataFrame(list(rows))


def test_transform_adds_all_engineered_columns():
    out = FeatureEngineer().fit_transform(df_of(make_row()))
    for col in ENGINEERED_COLUMNS:
        assert col in out.columns


def test_fit_is_stateless_and_returns_self():
    engineer = FeatureEngineer()
    fitted = engineer.fit(df_of(make_row()))
    assert fitted is engineer
    assert engineer.get_params() == {}


def test_transform_output_independent_of_fit_data():
    row = make_row(**{"Tenure Months": 5})
    out_a = FeatureEngineer().fit(df_of(make_row())).transform(df_of(row))
    out_b = FeatureEngineer().fit(df_of(make_row(), make_row(), make_row())).transform(df_of(row))
    pd.testing.assert_frame_equal(out_a, out_b)


def test_missing_required_column_raises():
    df = df_of(make_row()).drop(columns=["Contract"])
    with pytest.raises(ValueError, match="Contract"):
        FeatureEngineer().transform(df)


@pytest.mark.parametrize(
    "tenure,expected_bucket",
    [
        (0, "0-12"),
        (12, "0-12"),
        (13, "13-24"),
        (24, "13-24"),
        (25, "25-48"),
        (48, "25-48"),
        (49, "49+"),
        (200, "49+"),
        (1199, "49+"),  # just under the data-quality validator's implausible-tenure cutoff
    ],
)
def test_tenure_group_bucket_boundaries(tenure, expected_bucket):
    out = FeatureEngineer().fit_transform(df_of(make_row(**{"Tenure Months": tenure})))
    assert out.loc[0, "tenure_group"] == expected_bucket


def test_has_internet_false_when_no_internet_service():
    out = FeatureEngineer().fit_transform(df_of(make_row(**{"Internet Service": "No"})))
    assert out.loc[0, "has_internet"] == False  # noqa: E712


def test_has_internet_true_when_internet_present():
    out = FeatureEngineer().fit_transform(df_of(make_row(**{"Internet Service": "DSL"})))
    assert out.loc[0, "has_internet"] == True  # noqa: E712


def test_active_addon_count_counts_yes_values_only():
    row = make_row(
        **{
            "Online Security": "Yes",
            "Online Backup": "Yes",
            "Device Protection": "No",
            "Tech Support": "No internet service",
            "Streaming TV": "Yes",
            "Streaming Movies": "No",
        }
    )
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "active_addon_count"] == 3


def test_active_addon_count_treats_no_internet_service_as_inactive():
    row = make_row(
        **{
            "Internet Service": "No",
            "Online Security": "No internet service",
            "Online Backup": "No internet service",
            "Device Protection": "No internet service",
            "Tech Support": "No internet service",
            "Streaming TV": "No internet service",
            "Streaming Movies": "No internet service",
        }
    )
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "active_addon_count"] == 0
    assert out.loc[0, "has_protection_addon"] == False  # noqa: E712
    assert out.loc[0, "has_streaming_addon"] == False  # noqa: E712


def test_has_protection_addon_true_if_any_protection_service_active():
    row = make_row(**{"Tech Support": "Yes"})
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "has_protection_addon"] == True  # noqa: E712
    assert out.loc[0, "has_streaming_addon"] == False  # noqa: E712


def test_has_streaming_addon_true_if_any_streaming_service_active():
    row = make_row(**{"Streaming Movies": "Yes"})
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "has_streaming_addon"] == True  # noqa: E712
    assert out.loc[0, "has_protection_addon"] == False  # noqa: E712


def test_avg_monthly_value_divides_by_tenure():
    row = make_row(**{"Total Charges": 500.0, "Tenure Months": 10})
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "avg_monthly_value"] == pytest.approx(50.0)


def test_avg_monthly_value_avoids_division_by_zero_at_zero_tenure():
    row = make_row(**{"Total Charges": 0.0, "Tenure Months": 0})
    out = FeatureEngineer().fit_transform(df_of(row))
    assert out.loc[0, "avg_monthly_value"] == pytest.approx(0.0)


def test_contract_risk_flag_true_only_for_month_to_month():
    m2m = FeatureEngineer().fit_transform(df_of(make_row(**{"Contract": "Month-to-month"})))
    one_yr = FeatureEngineer().fit_transform(df_of(make_row(**{"Contract": "One year"})))
    assert m2m.loc[0, "contract_risk_flag"] == True  # noqa: E712
    assert one_yr.loc[0, "contract_risk_flag"] == False  # noqa: E712


def test_payment_risk_flag_true_only_for_electronic_check():
    ec = FeatureEngineer().fit_transform(df_of(make_row(**{"Payment Method": "Electronic check"})))
    mailed = FeatureEngineer().fit_transform(df_of(make_row(**{"Payment Method": "Mailed check"})))
    assert ec.loc[0, "payment_risk_flag"] == True  # noqa: E712
    assert mailed.loc[0, "payment_risk_flag"] == False  # noqa: E712


@pytest.mark.parametrize(
    "partner,dependents,expected",
    [
        ("No", "No", False),
        ("Yes", "No", True),
        ("No", "Yes", True),
        ("Yes", "Yes", True),
    ],
)
def test_family_flag(partner, dependents, expected):
    row = make_row(**{"Partner": partner, "Dependents": dependents})
    out = FeatureEngineer().fit_transform(df_of(row))
    assert bool(out.loc[0, "family_flag"]) == expected


def test_engineered_columns_partition_matches_full_list():
    assert set(ENGINEERED_NUMERIC_COLUMNS) | set(ENGINEERED_BOOLEAN_COLUMNS) | set(
        ENGINEERED_CATEGORICAL_COLUMNS
    ) == set(ENGINEERED_COLUMNS)
    assert len(ENGINEERED_NUMERIC_COLUMNS) + len(ENGINEERED_BOOLEAN_COLUMNS) + len(
        ENGINEERED_CATEGORICAL_COLUMNS
    ) == len(ENGINEERED_COLUMNS)


def test_required_input_columns_are_subset_of_combined_dataset_columns():
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv", nrows=1)
    assert set(REQUIRED_INPUT_COLUMNS) <= set(df.columns)


def test_combined_development_dataset_transforms_without_nulls():
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    out = FeatureEngineer().fit_transform(df)
    assert len(out) == 21043
    assert out[ENGINEERED_COLUMNS].isna().sum().sum() == 0
    assert out["active_addon_count"].between(0, 6).all()
    assert set(out["tenure_group"].unique()) <= {"0-12", "13-24", "25-48", "49+"}


def test_combined_development_dataset_original_columns_preserved():
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    out = FeatureEngineer().fit_transform(df)
    for col in df.columns:
        assert col in out.columns


def test_engineered_features_correlate_with_churn_direction():
    # Cross-check against ml/eda/FINDINGS.md's documented churn intuition
    # (month-to-month, electronic check, no protection add-ons -> higher
    # churn) so the engineered flags aren't arbitrary (ML_SPEC §4 rationale).
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    out = FeatureEngineer().fit_transform(df)

    churn_by_contract_flag = out.groupby("contract_risk_flag", observed=True)[TARGET_COLUMN].mean()
    assert churn_by_contract_flag[True] > churn_by_contract_flag[False]

    churn_by_payment_flag = out.groupby("payment_risk_flag", observed=True)[TARGET_COLUMN].mean()
    assert churn_by_payment_flag[True] > churn_by_payment_flag[False]

    churn_by_family_flag = out.groupby("family_flag", observed=True)[TARGET_COLUMN].mean()
    assert churn_by_family_flag[True] < churn_by_family_flag[False]

    churn_by_protection = out.groupby("has_protection_addon", observed=True)[TARGET_COLUMN].mean()
    assert churn_by_protection[True] < churn_by_protection[False]
