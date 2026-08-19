import numpy as np
import pandas as pd
import pytest

from ml.config import DATA_PROCESSED_DIR, RANDOM_SEED, SOURCE_COLUMN, TARGET_COLUMN, TEST_RATIO, TRAIN_RATIO, VAL_RATIO
from ml.preprocessing.pipeline import (
    CATEGORICAL_COLUMNS,
    NUMERIC_COLUMNS,
    build_preprocessing_pipeline,
)
from ml.preprocessing.split import LEAKAGE_EXCLUDED_COLUMNS, stratified_split

TOLERANCE = 0.02


@pytest.fixture(scope="module")
def combined_df():
    return pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")


@pytest.fixture(scope="module")
def split(combined_df):
    return stratified_split(combined_df)


def test_split_sizes_match_70_15_15(split, combined_df):
    train, val, test = split
    n = len(combined_df)
    assert train["Churn Value"].count() and abs(len(train) / n - TRAIN_RATIO) < 0.005
    assert abs(len(val) / n - VAL_RATIO) < 0.005
    assert abs(len(test) / n - TEST_RATIO) < 0.005


def test_splits_are_disjoint_and_reconstruct_full_dataset(split, combined_df):
    train, val, test = split
    train_ids = set(train["CustomerID"])
    val_ids = set(val["CustomerID"])
    test_ids = set(test["CustomerID"])

    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)
    assert train_ids | val_ids | test_ids == set(combined_df["CustomerID"])
    assert len(train) + len(val) + len(test) == len(combined_df)


def test_split_is_reproducible_with_fixed_seed(combined_df):
    train_a, val_a, test_a = stratified_split(combined_df, seed=RANDOM_SEED)
    train_b, val_b, test_b = stratified_split(combined_df, seed=RANDOM_SEED)

    assert list(train_a["CustomerID"]) == list(train_b["CustomerID"])
    assert list(val_a["CustomerID"]) == list(val_b["CustomerID"])
    assert list(test_a["CustomerID"]) == list(test_b["CustomerID"])


def test_churn_rate_stratified_across_splits(split, combined_df):
    train, val, test = split
    overall_rate = combined_df[TARGET_COLUMN].mean()

    for name, part in (("train", train), ("val", val), ("test", test)):
        assert abs(part[TARGET_COLUMN].mean() - overall_rate) < TOLERANCE, name


def test_source_distribution_stratified_across_splits(split, combined_df):
    train, val, test = split
    overall_share = combined_df[SOURCE_COLUMN].value_counts(normalize=True)

    for name, part in (("train", train), ("val", val), ("test", test)):
        part_share = part[SOURCE_COLUMN].value_counts(normalize=True)
        for source in overall_share.index:
            assert abs(part_share[source] - overall_share[source]) < TOLERANCE, (name, source)


def test_pipeline_input_columns_exclude_leakage_and_provenance_columns():
    pipeline_input_columns = set(NUMERIC_COLUMNS) | set(CATEGORICAL_COLUMNS)
    assert pipeline_input_columns.isdisjoint(LEAKAGE_EXCLUDED_COLUMNS)
    assert SOURCE_COLUMN not in pipeline_input_columns
    assert "CustomerID" not in pipeline_input_columns
    assert TARGET_COLUMN not in pipeline_input_columns


def test_numeric_and_categorical_columns_partition_post_feature_engineering_set():
    assert set(NUMERIC_COLUMNS).isdisjoint(set(CATEGORICAL_COLUMNS))
    assert len(NUMERIC_COLUMNS) == 5
    assert len(CATEGORICAL_COLUMNS) == 23


def test_pipeline_fit_on_train_transform_on_val_no_leakage(split):
    from ml.config import MODELING_COLUMNS

    train, val, _ = split
    pipeline = build_preprocessing_pipeline(scale=True)

    X_train = pipeline.fit_transform(train[MODELING_COLUMNS], train[TARGET_COLUMN])
    X_val = pipeline.transform(val[MODELING_COLUMNS])

    assert X_train.shape[1] == X_val.shape[1]
    assert not np.isnan(X_train).any()
    assert not np.isnan(X_val).any()


def test_pipeline_handles_unseen_category_gracefully():
    from ml.config import MODELING_COLUMNS

    train_row = {
        "Gender": "Female",
        "Senior Citizen": "No",
        "Partner": "Yes",
        "Dependents": "No",
        "Tenure Months": 12,
        "Phone Service": "Yes",
        "Multiple Lines": "No",
        "Internet Service": "DSL",
        "Online Security": "No",
        "Online Backup": "No",
        "Device Protection": "No",
        "Tech Support": "No",
        "Streaming TV": "No",
        "Streaming Movies": "No",
        "Contract": "Month-to-month",
        "Paperless Billing": "Yes",
        "Payment Method": "Mailed check",
        "Monthly Charges": 50.0,
        "Total Charges": 600.0,
    }
    train_df = pd.DataFrame([train_row, train_row])
    unseen_row = dict(train_row, **{"Payment Method": "Crypto (new)"})
    unseen_df = pd.DataFrame([unseen_row])

    pipeline = build_preprocessing_pipeline(scale=False)
    pipeline.fit(train_df[MODELING_COLUMNS])
    # Must not raise despite "Crypto (new)" never having been seen at fit time.
    out = pipeline.transform(unseen_df[MODELING_COLUMNS])
    assert out.shape[0] == 1


def test_scaled_and_unscaled_pipelines_produce_same_feature_count(split):
    from ml.config import MODELING_COLUMNS

    train, _, _ = split
    scaled = build_preprocessing_pipeline(scale=True)
    unscaled = build_preprocessing_pipeline(scale=False)

    X_scaled = scaled.fit_transform(train[MODELING_COLUMNS], train[TARGET_COLUMN])
    X_unscaled = unscaled.fit_transform(train[MODELING_COLUMNS], train[TARGET_COLUMN])

    assert X_scaled.shape == X_unscaled.shape
    # Scaled numeric columns should be ~standardized (mean ~0); unscaled should not be.
    assert abs(X_scaled[:, 0].mean()) < 0.01
    assert abs(X_unscaled[:, 0].mean()) > 1.0
