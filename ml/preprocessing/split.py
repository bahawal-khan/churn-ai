"""Train / validation / test split + fitted preprocessing artifacts
(`docs/ML_SPEC.md` §5, §6).

Stratified two-key split on `(Churn Value, Source)` so IBM / Pakistan-
Synthetic / India-Synthetic are proportionally represented in every split,
not just churn/no-churn (`docs/ML_SPEC.md` §6: "jointly stratified on
(Churn Value, Source)"). Ratio 70/15/15, fixed seed (`ml.config.RANDOM_SEED`).

The held-out test split is produced here but is not touched again until
final reporting (ML_SPEC §6/§12) — this phase does not evaluate anything
against it.

This module also builds and fits the two preprocessing pipeline variants
(`ml.preprocessing.pipeline`) on the training split only, and serializes
them for reuse by whichever later phase trains models. No model is trained
here.

Run directly: `python -m ml.preprocessing.split`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.config import (
    ARTIFACTS_DIR,
    DATA_PROCESSED_DIR,
    DATA_SPLITS_DIR,
    MODELING_COLUMNS,
    RANDOM_SEED,
    SOURCE_COLUMN,
    TARGET_COLUMN,
    TEST_RATIO,
    TRAIN_RATIO,
    VAL_RATIO,
)
from ml.preprocessing.pipeline import (
    CATEGORICAL_COLUMNS,
    NUMERIC_COLUMNS,
    build_preprocessing_pipeline,
)

PREPROCESSING_ARTIFACT_DIR = ARTIFACTS_DIR / "preprocessing_dev"

# Columns that must never reach the ColumnTransformer as an input feature
# (PROJECT_SPEC.md binding cross-cutting rule; ML_SPEC §1, §6). `Source` is
# provenance-only, `CustomerID` is an identifier, and the rest are the
# target/leakage columns already dropped before the combined dataset was
# built (kept here for the leakage-check report, not because they're
# present in `combined_development_dataset.csv`).
LEAKAGE_EXCLUDED_COLUMNS = {
    SOURCE_COLUMN,
    "CustomerID",
    TARGET_COLUMN,
    "Churn Label",
    "Churn Score",
    "Churn Reason",
}


def _strata_key(df: pd.DataFrame) -> pd.Series:
    return df[SOURCE_COLUMN].astype(str) + "|" + df[TARGET_COLUMN].astype(str)


def stratified_split(
    df: pd.DataFrame, seed: int = RANDOM_SEED
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """70/15/15 split, jointly stratified on `(Source, Churn Value)`."""
    train_val, test = train_test_split(
        df, test_size=TEST_RATIO, stratify=_strata_key(df), random_state=seed
    )
    val_share_of_train_val = VAL_RATIO / (TRAIN_RATIO + VAL_RATIO)
    train, val = train_test_split(
        train_val,
        test_size=val_share_of_train_val,
        stratify=_strata_key(train_val),
        random_state=seed,
    )
    return (
        train.reset_index(drop=True),
        val.reset_index(drop=True),
        test.reset_index(drop=True),
    )


def _split_stats(name: str, split_df: pd.DataFrame, full_len: int) -> dict[str, Any]:
    return {
        "row_count": int(len(split_df)),
        "share_of_total": round(len(split_df) / full_len, 4),
        "churn_rate": round(float(split_df[TARGET_COLUMN].mean()), 4),
        "source_distribution": {
            k: int(v) for k, v in split_df[SOURCE_COLUMN].value_counts().to_dict().items()
        },
        "source_share": {
            k: round(float(v), 4)
            for k, v in split_df[SOURCE_COLUMN].value_counts(normalize=True).to_dict().items()
        },
    }


def _leakage_checks(df: pd.DataFrame) -> dict[str, Any]:
    pipeline_input_columns = set(NUMERIC_COLUMNS) | set(CATEGORICAL_COLUMNS)
    overlap = pipeline_input_columns & LEAKAGE_EXCLUDED_COLUMNS
    present_leakage_columns_in_dataset = [
        c for c in ("Churn Score", "Churn Reason", "Churn Label") if c in df.columns
    ]
    return {
        "excluded_columns": sorted(LEAKAGE_EXCLUDED_COLUMNS),
        "excluded_columns_in_pipeline_input": sorted(overlap),
        "excluded_columns_check_passed": len(overlap) == 0,
        "leakage_columns_present_in_combined_dataset": present_leakage_columns_in_dataset,
        "leakage_columns_absent_check_passed": len(present_leakage_columns_in_dataset) == 0,
        "source_used_only_for_stratification_not_as_feature": SOURCE_COLUMN not in pipeline_input_columns,
    }


def main() -> None:
    df = pd.read_csv(DATA_PROCESSED_DIR / "combined_development_dataset.csv")
    train, val, test = stratified_split(df)

    DATA_SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    train.to_csv(DATA_SPLITS_DIR / "train.csv", index=False)
    val.to_csv(DATA_SPLITS_DIR / "val.csv", index=False)
    test.to_csv(DATA_SPLITS_DIR / "test.csv", index=False)

    X_train = train[MODELING_COLUMNS]
    y_train = train[TARGET_COLUMN]

    pipeline_scaled = build_preprocessing_pipeline(scale=True)
    pipeline_unscaled = build_preprocessing_pipeline(scale=False)

    X_train_scaled = pipeline_scaled.fit_transform(X_train, y_train)
    X_train_unscaled = pipeline_unscaled.fit_transform(X_train, y_train)

    # Validation/test are only ever *transformed*, never fit on (ML_SPEC §5's
    # "strict rule") — exercised here to confirm the fitted pipeline applies
    # cleanly (e.g. handle_unknown="ignore" covers any unseen category) and
    # to report post-preprocessing shapes for all three splits.
    X_val_scaled = pipeline_scaled.transform(val[MODELING_COLUMNS])
    X_test_scaled = pipeline_scaled.transform(test[MODELING_COLUMNS])

    PREPROCESSING_ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline_scaled, PREPROCESSING_ARTIFACT_DIR / "pipeline_scaled.joblib")
    joblib.dump(pipeline_unscaled, PREPROCESSING_ARTIFACT_DIR / "pipeline_unscaled.joblib")

    metadata: dict[str, Any] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "source_dataset": "combined_development_dataset.csv",
        "source_dataset_row_count": int(len(df)),
        "split_ratios": {"train": TRAIN_RATIO, "val": VAL_RATIO, "test": TEST_RATIO},
        "stratification_key": f"({SOURCE_COLUMN}, {TARGET_COLUMN})",
        "splits": {
            "train": _split_stats("train", train, len(df)),
            "val": _split_stats("val", val, len(df)),
            "test": _split_stats("test", test, len(df)),
        },
        "overall_churn_rate": round(float(df[TARGET_COLUMN].mean()), 4),
        "overall_source_share": {
            k: round(float(v), 4)
            for k, v in df[SOURCE_COLUMN].value_counts(normalize=True).to_dict().items()
        },
        "feature_counts": {
            "raw_modeling_columns": len(MODELING_COLUMNS),
            "post_feature_engineering_columns": len(NUMERIC_COLUMNS) + len(CATEGORICAL_COLUMNS),
            "numeric_columns": len(NUMERIC_COLUMNS),
            "categorical_columns": len(CATEGORICAL_COLUMNS),
            "post_preprocessing_features_scaled_pipeline": int(X_train_scaled.shape[1]),
            "post_preprocessing_features_unscaled_pipeline": int(X_train_unscaled.shape[1]),
        },
        "preprocessing_shapes": {
            "X_train": list(X_train_scaled.shape),
            "X_val": list(X_val_scaled.shape),
            "X_test": list(X_test_scaled.shape),
        },
        "numeric_columns_list": NUMERIC_COLUMNS,
        "categorical_columns_list": CATEGORICAL_COLUMNS,
        "leakage_checks": _leakage_checks(df),
        "fit_only_on_train": True,
        "notes": (
            "Two pipeline variants serialized: pipeline_scaled.joblib "
            "(StandardScaler on numeric branch, for Logistic Regression / "
            "ANN) and pipeline_unscaled.joblib (no scaling, for tree-based "
            "baselines), sharing identical imputation/encoding so baseline "
            "comparisons are apples-to-apples (ML_SPEC §5). No model is "
            "trained by this script."
        ),
    }

    metadata_path = PREPROCESSING_ARTIFACT_DIR / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Splits written to {DATA_SPLITS_DIR}")
    print(f"  train: {len(train)} rows, val: {len(val)} rows, test: {len(test)} rows")
    print(f"Pipelines + metadata written to {PREPROCESSING_ARTIFACT_DIR}")
    print(f"Post-preprocessing feature count (scaled pipeline): {X_train_scaled.shape[1]}")


if __name__ == "__main__":
    main()
