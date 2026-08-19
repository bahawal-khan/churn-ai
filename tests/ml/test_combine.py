from ml.data_generation.combine import combine


def test_combined_dataset_total_row_count():
    df = combine()
    assert len(df) == 21043


def test_combined_dataset_source_breakdown():
    df = combine()
    counts = df["Source"].value_counts().to_dict()
    assert counts == {
        "IBM": 7043,
        "Pakistan-Synthetic": 7000,
        "India-Synthetic": 7000,
    }


def test_combined_dataset_no_missing_values():
    df = combine()
    assert df.isna().sum().sum() == 0


def test_combined_dataset_customer_ids_unique_across_sources():
    df = combine()
    assert df["CustomerID"].is_unique


def test_combined_dataset_churn_value_binary():
    df = combine()
    assert set(df["Churn Value"].unique()) <= {0, 1}


def test_combined_dataset_no_leakage_columns():
    df = combine()
    for leaked in ("Churn Score", "Churn Reason", "Churn Label"):
        assert leaked not in df.columns


def test_combined_dataset_no_zero_variance_geo_columns():
    df = combine()
    for dropped in ("Country", "State", "City", "Count", "Zip Code"):
        assert dropped not in df.columns
