import pandas as pd
import pytest

from ml.config import DATA_PROCESSED_DIR, MODELING_COLUMNS, TARGET_COLUMN
from ml.data_quality.validator import DataQualityValidator, MalformedCSVError, load_csv_safely

REQUIRED = ["Gender", "Tenure Months", "Monthly Charges", "Contract"]


def make_validator(target_column=None, id_column=None):
    return DataQualityValidator(required_columns=REQUIRED, target_column=target_column, id_column=id_column)


def valid_df(n=10):
    return pd.DataFrame(
        {
            "Gender": ["Male", "Female"] * (n // 2),
            "Tenure Months": [i for i in range(n)],
            "Monthly Charges": [50.0 + i for i in range(n)],
            "Contract": ["Month-to-month", "One year"] * (n // 2),
            "Churn Value": [0, 1] * (n // 2),
            "CustomerID": [f"ID-{i}" for i in range(n)],
        }
    )


def test_report_shape():
    report = make_validator().validate(valid_df())
    assert set(report.keys()) == {"checks", "overall_status", "row_count", "issues_found"}
    assert report["row_count"] == 10
    for check in report["checks"]:
        assert set(check.keys()) == {"name", "status", "detail"}
        assert check["status"] in {"pass", "warn", "fail"}


def test_clean_data_passes_all_checks():
    report = make_validator(target_column="Churn Value", id_column="CustomerID").validate(valid_df())
    assert report["overall_status"] == "pass"
    assert report["issues_found"] == 0


def test_missing_required_columns_fails():
    df = valid_df().drop(columns=["Contract"])
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "missing_required_columns")
    assert check["status"] == "fail"
    assert check["detail"]["missing_columns"] == ["Contract"]
    assert report["overall_status"] == "fail"


def test_unexpected_columns_is_warn_not_fail():
    df = valid_df()
    df["Extra Metadata Column"] = "x"
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "unexpected_columns")
    assert check["status"] == "warn"
    assert "Extra Metadata Column" in check["detail"]["unexpected_columns"]


def test_missing_values_below_threshold_warns_above_threshold_fails():
    # 1/20 = 5% missing on Gender -> at fail threshold.
    df = valid_df(20)
    df.loc[0, "Gender"] = None
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "missing_values")
    assert check["status"] == "fail"
    assert check["detail"]["columns_with_missing_share"]["Gender"] == 0.05

    # 1/200 = 0.5% missing -> below threshold, warn only.
    df2 = valid_df(200)
    df2.loc[0, "Gender"] = None
    report2 = make_validator().validate(df2)
    check2 = next(c for c in report2["checks"] if c["name"] == "missing_values")
    assert check2["status"] == "warn"


def test_duplicate_rows_fail():
    df = pd.concat([valid_df(4), valid_df(4)], ignore_index=True)
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "duplicates")
    assert check["status"] == "fail"
    assert check["detail"]["duplicate_rows"] > 0


def test_duplicate_id_column_fails():
    df = valid_df()
    df.loc[1, "CustomerID"] = df.loc[0, "CustomerID"]
    report = make_validator(id_column="CustomerID").validate(df)
    check = next(c for c in report["checks"] if c["name"] == "duplicates")
    assert check["status"] == "fail"
    assert check["detail"]["duplicate_id_values"] == 1


def test_wrong_dtype_non_coercible_fails():
    df = valid_df()
    df["Monthly Charges"] = df["Monthly Charges"].astype(object)
    df.loc[0, "Monthly Charges"] = "not-a-number"
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "wrong_dtypes")
    assert check["status"] == "fail"
    assert check["detail"]["non_coercible_value_counts"]["Monthly Charges"] == 1


def test_negative_monthly_charges_fails():
    df = valid_df()
    df.loc[0, "Monthly Charges"] = -10.0
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "invalid_values")
    assert check["status"] == "fail"
    assert check["detail"]["negative_monthly_charges"] == 1


def test_implausible_tenure_fails():
    df = valid_df()
    df.loc[0, "Tenure Months"] = 5000
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "invalid_values")
    assert check["status"] == "fail"
    assert check["detail"]["implausible_tenure_months"] == 1


def test_inconsistent_categories_fails():
    df = valid_df()
    df.loc[0, "Gender"] = "male"
    df.loc[1, "Gender"] = " Male"
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "inconsistent_categories")
    assert check["status"] == "fail"
    assert "Gender" in check["detail"]["columns_with_case_or_whitespace_variants"]


def test_high_cardinality_warns():
    df = valid_df(20)
    df["Contract"] = [f"unique-value-{i}" for i in range(20)]
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "high_cardinality")
    assert check["status"] == "warn"
    assert "Contract" in check["detail"]["columns_unique_ratio"]


def test_identifier_like_column_name_warns():
    df = valid_df()
    report = make_validator().validate(df)
    check = next(c for c in report["checks"] if c["name"] == "identifier_columns")
    assert check["status"] == "warn"
    assert "CustomerID" in check["detail"]["identifier_like_columns"]


def test_target_column_missing_fails():
    report = make_validator(target_column="Churn Value").validate(valid_df().drop(columns=["Churn Value"]))
    check = next(c for c in report["checks"] if c["name"] == "target_column")
    assert check["status"] == "fail"
    assert check["detail"]["reason"] == "missing"


def test_target_column_single_class_fails():
    df = valid_df()
    df["Churn Value"] = 0
    report = make_validator(target_column="Churn Value").validate(df)
    check = next(c for c in report["checks"] if c["name"] == "target_column")
    assert check["status"] == "fail"
    assert check["detail"]["reason"] == "single_class"


def test_target_column_non_binary_fails():
    df = valid_df()
    df["Churn Value"] = [0, 1, 2] * (len(df) // 3) + [0] * (len(df) % 3)
    report = make_validator(target_column="Churn Value").validate(df)
    check = next(c for c in report["checks"] if c["name"] == "target_column")
    assert check["status"] == "fail"
    assert check["detail"]["reason"] == "non_binary"


def test_target_column_omitted_when_not_configured():
    report = make_validator().validate(valid_df())
    assert all(c["name"] != "target_column" for c in report["checks"])


def test_load_csv_safely_raises_on_malformed_file(tmp_path):
    bad_csv = tmp_path / "ragged.csv"
    bad_csv.write_text("a,b,c\n1,2\n3,4,5,6\n", encoding="utf-8")
    with pytest.raises(MalformedCSVError):
        load_csv_safely(bad_csv)


def test_load_csv_safely_reads_valid_file(tmp_path):
    good_csv = tmp_path / "good.csv"
    good_csv.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    df = load_csv_safely(good_csv)
    assert df.shape == (2, 2)


def test_combined_development_dataset_overall_status_not_fail():
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    validator = DataQualityValidator(
        required_columns=MODELING_COLUMNS,
        target_column=TARGET_COLUMN,
        id_column="CustomerID",
    )
    report = validator.validate(df)
    assert report["overall_status"] in {"pass", "warn"}
    assert report["row_count"] == 21043
