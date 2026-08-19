import pandas as pd
import pytest

from ml.config import SYNTHETIC_RECORDS_PER_COUNTRY
from ml.data_generation import india_generator, pakistan_generator

GENERATORS = [
    pytest.param(pakistan_generator, "PK", "Pakistan-Synthetic", id="pakistan"),
    pytest.param(india_generator, "IN", "India-Synthetic", id="india"),
]

SCHEMA_COLUMNS = [
    "CustomerID",
    "Gender",
    "Senior Citizen",
    "Partner",
    "Dependents",
    "Tenure Months",
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
    "Monthly Charges",
    "Total Charges",
    "Churn Value",
    "Source",
]

ADDON_COLUMNS = [
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
    "Streaming TV",
    "Streaming Movies",
]


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_record_count(module, prefix, source_label):
    df = module.generate()
    assert len(df) == SYNTHETIC_RECORDS_PER_COUNTRY == 7000


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_deterministic_same_seed_byte_identical(module, prefix, source_label):
    df1 = module.generate()
    df2 = module.generate()
    pd.testing.assert_frame_equal(df1, df2)


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_schema_columns_present(module, prefix, source_label):
    df = module.generate().drop(columns=["_archetype"])
    assert list(df.columns) == SCHEMA_COLUMNS


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_customer_id_prefix_and_uniqueness(module, prefix, source_label):
    df = module.generate()
    assert df["CustomerID"].is_unique
    assert df["CustomerID"].str.startswith(f"{prefix}-").all()


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_source_label(module, prefix, source_label):
    df = module.generate()
    assert (df["Source"] == source_label).all()


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_no_missing_values(module, prefix, source_label):
    df = module.generate().drop(columns=["_archetype"])
    assert df.isna().sum().sum() == 0


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_churn_value_is_binary(module, prefix, source_label):
    df = module.generate()
    assert set(df["Churn Value"].unique()) <= {0, 1}


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_numeric_ranges_plausible(module, prefix, source_label):
    df = module.generate()
    assert df["Tenure Months"].between(0, 72).all()
    assert df["Monthly Charges"].between(18.25, 118.75).all()
    assert (df["Total Charges"] >= 0).all()


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_categorical_domains(module, prefix, source_label):
    df = module.generate()
    assert set(df["Gender"].unique()) <= {"Male", "Female"}
    assert set(df["Contract"].unique()) <= {"Month-to-month", "One year", "Two year"}
    assert set(df["Internet Service"].unique()) <= {"DSL", "Fiber optic", "No"}
    assert set(df["Payment Method"].unique()) <= {
        "Bank transfer (automatic)",
        "Credit card (automatic)",
        "Electronic check",
        "Mailed check",
    }
    for col in ADDON_COLUMNS:
        assert set(df[col].unique()) <= {"Yes", "No", "No internet service"}


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_no_internet_service_consistency(module, prefix, source_label):
    """If Internet Service == 'No', all 6 dependent add-on columns must be
    'No internet service', and never that value otherwise (docs/ML_SPEC.md §4
    has_internet rationale)."""
    df = module.generate()
    no_internet = df["Internet Service"] == "No"
    for col in ADDON_COLUMNS:
        assert (df.loc[no_internet, col] == "No internet service").all()
        assert (df.loc[~no_internet, col] != "No internet service").all()


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_no_phone_service_consistency(module, prefix, source_label):
    df = module.generate()
    no_phone = df["Phone Service"] == "No"
    assert (df.loc[no_phone, "Multiple Lines"] == "No phone service").all()
    assert (df.loc[~no_phone, "Multiple Lines"] != "No phone service").all()


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_archetype_counts_match_documented_shares(module, prefix, source_label):
    df = module.generate()
    counts = df["_archetype"].value_counts().to_dict()
    expected = {a.name: round(a.share * SYNTHETIC_RECORDS_PER_COUNTRY) for a in module.ARCHETYPES}
    # last archetype absorbs the rounding remainder (engine.py)
    total = sum(expected.values())
    if total != SYNTHETIC_RECORDS_PER_COUNTRY:
        last = module.ARCHETYPES[-1].name
        expected[last] += SYNTHETIC_RECORDS_PER_COUNTRY - total
    assert counts == expected


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_churn_rate_in_realistic_band(module, prefix, source_label):
    df = module.generate()
    rate = df["Churn Value"].mean()
    assert 0.20 <= rate <= 0.35


@pytest.mark.parametrize("module, prefix, source_label", GENERATORS)
def test_not_perfectly_separable_by_churn_rate_spread(module, prefix, source_label):
    """No archetype should be a pure 0% or 100% churn bucket -- churn must
    stay probabilistic even for the lowest/highest-propensity archetypes
    (docs/PROJECT_SPEC.md §3.5: not perfectly separable)."""
    df = module.generate()
    rates = df.groupby("_archetype")["Churn Value"].mean()
    assert (rates > 0.0).all()
    assert (rates < 1.0).all()


def test_pakistan_and_india_datasets_are_not_identical():
    pk = pakistan_generator.generate().drop(columns=["_archetype"])
    ind = india_generator.generate().drop(columns=["_archetype"])
    assert not pk.drop(columns=["CustomerID", "Source"]).equals(
        ind.drop(columns=["CustomerID", "Source"])
    )


def test_archetype_shares_sum_to_one():
    for module in (pakistan_generator, india_generator):
        total_share = sum(a.share for a in module.ARCHETYPES)
        assert total_share == pytest.approx(1.0, abs=1e-6)
