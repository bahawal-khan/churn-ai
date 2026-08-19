"""Phase 5 training orchestrator: baselines + ANN, evaluation, threshold
selection, artifact saving (`docs/ML_SPEC.md` §7-14).

Split usage (ML_SPEC §6, enforced structurally, not by convention):
  - `train.csv`  -> `pipeline.fit_transform` was already done in Phase 4;
                     here it is only ever `.transform()`-ed again via the
                     already-fitted `pipeline_scaled`/`pipeline_unscaled`
                     loaded from `ml/artifacts/preprocessing_dev/` — no
                     pipeline is refit in this module. Used to `.fit()`
                     every model (baselines + ANN).
  - `val.csv`    -> used for every baseline/ANN evaluation, the
                     BatchNorm/L2 decision (see `ml/models/MODELS.md`), and
                     `select_threshold_by_f1` (decision-threshold tuning).
                     Never used to fit anything.
  - `test.csv`   -> transformed and scored exactly once, only for the
                     final selected model, only after `WINNING_MODEL_ID`
                     and its threshold are already fixed by validation
                     results above. See `evaluate_winner_on_test`.

ANN architecture decision (ML_SPEC §9): three configs were run as a
Phase 5 exploratory experiment against identical data/seed — baseline
(Dropout only), +L2(1e-4), +BatchNorm. None showed the overfitting/
instability signals ML_SPEC §9 conditions BatchNorm/L2 on (no early
overfitting before epoch 10, no runaway validation loss, last-10-epoch
validation loss std stayed in the same tight 0.0026-0.0035 band across all
three configs). L2 nudged best validation PR-AUC up by 0.0047 without
closing the train/val gap (the actual criterion ML_SPEC §9 sets for
adopting it), and BatchNorm reduced the gap but at the cost of a *lower*
best validation PR-AUC. Neither clears the "must be supported by validation
results" bar, so the ANN below stays exactly the ML_SPEC §8 baseline shape:
Dropout only, no BatchNorm, no L2. Full numbers in `ml/models/MODELS.md`.

Run directly: `python -m ml.models.train`
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from ml.config import (
    ALGORITHM_ANN,
    ARTIFACTS_DIR,
    DATA_SPLITS_DIR,
    MODELING_COLUMNS,
    RANDOM_SEED,
    RISK_THRESHOLDS,
    TARGET_COLUMN,
)
from ml.models.ann import (
    ANN_HYPERPARAMETERS_TEMPLATE,
    build_model as build_ann_model,
    compute_class_weights,
    history_to_dict,
    train_model as train_ann_model,
)
from ml.models.baselines import BASELINE_SPECS, predict_proba_positive
from ml.models.evaluate import (
    compute_metric_suite,
    plot_calibration_curve,
    plot_confusion_matrix,
    plot_roc_pr_curves,
    select_threshold_by_f1,
    write_json,
)
from ml.models.inference import load_model_bundle
from ml.preprocessing.pipeline import RAW_NUMERIC_COLUMNS

PREPROCESSING_ARTIFACT_DIR = ARTIFACTS_DIR / "preprocessing_dev"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"
SOURCE_DATASET = "combined_development_dataset.csv"

# Final architecture decision, per the docstring above and ml/models/MODELS.md.
ANN_MODEL_ID = "ann_v1"
ANN_USE_BATCH_NORM = False
ANN_L2_STRENGTH: float | None = None


def _load_splits() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_SPLITS_DIR / "train.csv")
    val = pd.read_csv(DATA_SPLITS_DIR / "val.csv")
    test = pd.read_csv(DATA_SPLITS_DIR / "test.csv")
    return train, val, test


def build_feature_schema(train_df: pd.DataFrame) -> list[dict[str, Any]]:
    """Ordered `feature_schema` per `docs/DATABASE_SPEC.md` §2.7: the exact
    columns + expected types/categories the fitted pipeline expects, in
    `ml.config.MODELING_COLUMNS` order."""
    schema = []
    for col in MODELING_COLUMNS:
        if col in RAW_NUMERIC_COLUMNS:
            schema.append({"name": col, "dtype": "numeric"})
        else:
            categories = sorted(train_df[col].dropna().astype(str).unique().tolist())
            schema.append({"name": col, "dtype": "categorical", "categories": categories})
    return schema


def _write_metadata_and_metrics(
    model_dir: Path,
    *,
    model_id: str,
    algorithm: str,
    hyperparameters: dict[str, Any],
    preprocessing_variant: str,
    feature_schema: list[dict[str, Any]],
    train_row_count: int,
    decision_threshold: float,
    validation_metrics: dict[str, Any],
    test_metrics: dict[str, Any] | None,
) -> None:
    metadata = {
        "model_id": model_id,
        "algorithm": algorithm,
        "model_type": "baseline_global",
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "hyperparameters": hyperparameters,
        "trained_on_dataset": SOURCE_DATASET,
        "train_row_count": train_row_count,
        "preprocessing_pipeline_variant": preprocessing_variant,
        "feature_schema": feature_schema,
        "decision_threshold": decision_threshold,
        "risk_thresholds": RISK_THRESHOLDS,
        "test_evaluated": test_metrics is not None,
    }
    write_json(metadata, model_dir / "metadata.json")

    metrics = {
        "validation": validation_metrics,
        "test": test_metrics,
    }
    write_json(metrics, model_dir / "metrics.json")


def train_baselines(
    X_train_scaled: np.ndarray,
    X_train_unscaled: np.ndarray,
    y_train: np.ndarray,
    X_val_scaled: np.ndarray,
    X_val_unscaled: np.ndarray,
    y_val: np.ndarray,
    pipeline_scaled: Any,
    pipeline_unscaled: Any,
    feature_schema: list[dict[str, Any]],
    train_row_count: int,
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    for model_id, algorithm, uses_scaled, builder, hyperparameters in BASELINE_SPECS:
        X_train = X_train_scaled if uses_scaled else X_train_unscaled
        X_val = X_val_scaled if uses_scaled else X_val_unscaled
        pipeline = pipeline_scaled if uses_scaled else pipeline_unscaled

        model = builder()
        model.fit(X_train, y_train)
        y_val_prob = predict_proba_positive(model, X_val)

        threshold, val_metrics = select_threshold_by_f1(y_val, y_val_prob)

        model_dir = ARTIFACTS_DIR / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_dir / "model.joblib")
        joblib.dump(pipeline, model_dir / "pipeline.joblib")

        _write_metadata_and_metrics(
            model_dir,
            model_id=model_id,
            algorithm=algorithm,
            hyperparameters=hyperparameters,
            preprocessing_variant="scaled" if uses_scaled else "unscaled",
            feature_schema=feature_schema,
            train_row_count=train_row_count,
            decision_threshold=threshold,
            validation_metrics=val_metrics,
            test_metrics=None,
        )

        results[model_id] = {
            "algorithm": algorithm,
            "model": model,
            "uses_scaled": uses_scaled,
            "threshold": threshold,
            "validation_metrics": val_metrics,
            "y_val_prob": y_val_prob,
        }
        print(
            f"[{model_id}] val pr_auc={val_metrics['pr_auc']:.4f} recall={val_metrics['recall']:.4f} "
            f"f1={val_metrics['f1']:.4f} threshold={threshold:.2f}"
        )

    return results


def train_ann(
    X_train_scaled: np.ndarray,
    y_train: np.ndarray,
    X_val_scaled: np.ndarray,
    y_val: np.ndarray,
    pipeline_scaled: Any,
    feature_schema: list[dict[str, Any]],
    train_row_count: int,
) -> dict[str, Any]:
    class_weight = compute_class_weights(y_train)
    model = build_ann_model(
        input_dim=X_train_scaled.shape[1],
        use_batch_norm=ANN_USE_BATCH_NORM,
        l2_strength=ANN_L2_STRENGTH,
    )
    history = train_ann_model(
        model, X_train_scaled, y_train, X_val_scaled, y_val, class_weight=class_weight, verbose=2
    )
    hist_dict = history_to_dict(history)
    write_json(hist_dict, FIGURES_DIR / "ann_training_history.json")
    _plot_training_curves(hist_dict)

    y_val_prob = model.predict(X_val_scaled, verbose=0).reshape(-1)
    threshold, val_metrics = select_threshold_by_f1(y_val, y_val_prob)

    hyperparameters = dict(ANN_HYPERPARAMETERS_TEMPLATE)
    hyperparameters["use_batch_norm"] = ANN_USE_BATCH_NORM
    hyperparameters["l2_strength"] = ANN_L2_STRENGTH
    hyperparameters["dropout_rates"] = [0.3, 0.2]
    hyperparameters["epochs_run"] = len(hist_dict["loss"])
    hyperparameters["class_weight"] = class_weight

    model_dir = ARTIFACTS_DIR / ANN_MODEL_ID
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(model_dir / "model.keras")
    joblib.dump(pipeline_scaled, model_dir / "pipeline.joblib")

    _write_metadata_and_metrics(
        model_dir,
        model_id=ANN_MODEL_ID,
        algorithm=ALGORITHM_ANN,
        hyperparameters=hyperparameters,
        preprocessing_variant="scaled",
        feature_schema=feature_schema,
        train_row_count=train_row_count,
        decision_threshold=threshold,
        validation_metrics=val_metrics,
        test_metrics=None,
    )

    print(
        f"[{ANN_MODEL_ID}] val pr_auc={val_metrics['pr_auc']:.4f} recall={val_metrics['recall']:.4f} "
        f"f1={val_metrics['f1']:.4f} threshold={threshold:.2f} epochs={len(hist_dict['loss'])}"
    )

    return {
        "algorithm": ALGORITHM_ANN,
        "model": model,
        "uses_scaled": True,
        "threshold": threshold,
        "validation_metrics": val_metrics,
        "y_val_prob": y_val_prob,
        "history": hist_dict,
    }


def _plot_training_curves(hist: dict[str, list[float]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    epochs = range(1, len(hist["loss"]) + 1)

    axes[0].plot(epochs, hist["loss"], label="train")
    axes[0].plot(epochs, hist["val_loss"], label="validation")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()

    axes[1].plot(epochs, hist["pr_auc"], label="train")
    axes[1].plot(epochs, hist["val_pr_auc"], label="validation")
    axes[1].set_title("PR-AUC")
    axes[1].set_xlabel("Epoch")
    axes[1].legend()

    axes[2].plot(epochs, hist["recall"], label="train")
    axes[2].plot(epochs, hist["val_recall"], label="validation")
    axes[2].set_title("Recall")
    axes[2].set_xlabel("Epoch")
    axes[2].legend()

    fig.suptitle("ANN training curves (ml/models/train.py)")
    fig.tight_layout()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES_DIR / "ann_training_curves.png", dpi=120)
    plt.close(fig)


def select_winner(all_results: dict[str, dict[str, Any]]) -> str:
    """Objective selection (ML_SPEC §12): ranked by validation PR-AUC first,
    validation recall as tie-breaker — the two metrics ML_SPEC §12 weighs
    most heavily for this problem. Does not assume the ANN wins."""

    def rank_key(item: tuple[str, dict[str, Any]]) -> tuple[float, float]:
        _, result = item
        return (result["validation_metrics"]["pr_auc"], result["validation_metrics"]["recall"])

    winner_id, _ = max(all_results.items(), key=rank_key)
    return winner_id


def evaluate_winner_on_test(
    winner_id: str,
    winner_result: dict[str, Any],
    test_df: pd.DataFrame,
    pipeline_scaled: Any,
    pipeline_unscaled: Any,
) -> dict[str, Any]:
    """Final, single test-set evaluation (ML_SPEC §6/§12) — called only
    once, only after `winner_id`/its threshold are already fixed from
    validation-only results."""
    pipeline = pipeline_scaled if winner_result["uses_scaled"] else pipeline_unscaled
    X_test = pipeline.transform(test_df[MODELING_COLUMNS])
    y_test = test_df[TARGET_COLUMN].to_numpy()

    if winner_result["algorithm"] == ALGORITHM_ANN:
        y_test_prob = winner_result["model"].predict(X_test, verbose=0).reshape(-1)
    else:
        y_test_prob = predict_proba_positive(winner_result["model"], X_test)

    test_metrics = compute_metric_suite(y_test, y_test_prob, winner_result["threshold"])

    model_dir = ARTIFACTS_DIR / winner_id
    metrics_path = model_dir / "metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    metrics["test"] = test_metrics
    write_json(metrics, metrics_path)

    metadata_path = model_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["test_evaluated"] = True
    metadata["selected_as_recommended_production_model"] = True
    write_json(metadata, metadata_path)

    plot_confusion_matrix(
        test_metrics["confusion_matrix"], f"{winner_id} — test set", FIGURES_DIR / f"{winner_id}_test_confusion_matrix.png"
    )
    plot_calibration_curve(y_test, y_test_prob, f"{winner_id} (test)", FIGURES_DIR / f"{winner_id}_test_calibration.png")

    return test_metrics


def main() -> None:
    train_df, val_df, test_df = _load_splits()

    pipeline_scaled = joblib.load(PREPROCESSING_ARTIFACT_DIR / "pipeline_scaled.joblib")
    pipeline_unscaled = joblib.load(PREPROCESSING_ARTIFACT_DIR / "pipeline_unscaled.joblib")

    X_train_scaled = pipeline_scaled.transform(train_df[MODELING_COLUMNS])
    X_train_unscaled = pipeline_unscaled.transform(train_df[MODELING_COLUMNS])
    X_val_scaled = pipeline_scaled.transform(val_df[MODELING_COLUMNS])
    X_val_unscaled = pipeline_unscaled.transform(val_df[MODELING_COLUMNS])

    y_train = train_df[TARGET_COLUMN].to_numpy()
    y_val = val_df[TARGET_COLUMN].to_numpy()

    feature_schema = build_feature_schema(train_df)
    train_row_count = len(train_df)

    print("=== Training baselines (ML_SPEC §7) ===")
    baseline_results = train_baselines(
        X_train_scaled,
        X_train_unscaled,
        y_train,
        X_val_scaled,
        X_val_unscaled,
        y_val,
        pipeline_scaled,
        pipeline_unscaled,
        feature_schema,
        train_row_count,
    )

    print("=== Training ANN (ML_SPEC §8-10) ===")
    ann_result = train_ann(
        X_train_scaled, y_train, X_val_scaled, y_val, pipeline_scaled, feature_schema, train_row_count
    )

    all_results = {**baseline_results, ANN_MODEL_ID: ann_result}

    print("=== Objective model comparison (validation set) ===")
    comparison_rows = []
    for model_id, result in all_results.items():
        m = result["validation_metrics"]
        comparison_rows.append(
            {
                "model_id": model_id,
                "algorithm": result["algorithm"],
                "threshold": result["threshold"],
                "accuracy": m["accuracy"],
                "precision": m["precision"],
                "recall": m["recall"],
                "f1": m["f1"],
                "roc_auc": m["roc_auc"],
                "pr_auc": m["pr_auc"],
            }
        )
    comparison_df = pd.DataFrame(comparison_rows).sort_values("pr_auc", ascending=False)
    print(comparison_df.to_string(index=False))
    write_json(comparison_rows, FIGURES_DIR / "validation_comparison.json")

    winner_id = select_winner(all_results)
    print(f"=== Winner (validation PR-AUC, recall tie-break): {winner_id} ===")

    roc_pr_input = {
        model_id: {"y_true": y_val, "y_prob": result["y_val_prob"]} for model_id, result in all_results.items()
    }
    plot_roc_pr_curves(roc_pr_input, FIGURES_DIR / "validation_roc_pr_comparison.png")

    print(f"=== Final test-set evaluation for {winner_id} (touched once) ===")
    test_metrics = evaluate_winner_on_test(
        winner_id, all_results[winner_id], test_df, pipeline_scaled, pipeline_unscaled
    )
    print(
        f"[{winner_id}] TEST pr_auc={test_metrics['pr_auc']:.4f} recall={test_metrics['recall']:.4f} "
        f"f1={test_metrics['f1']:.4f} roc_auc={test_metrics['roc_auc']:.4f} accuracy={test_metrics['accuracy']:.4f}"
    )

    # Post-save sanity check (Phase 5 acceptance criterion: "final saved
    # model loads successfully").
    bundle = load_model_bundle(ARTIFACTS_DIR / winner_id)
    sample = test_df[MODELING_COLUMNS].head(5)
    sample_predictions = bundle.predict(sample)
    print("=== Post-save inference sanity check ===")
    print(sample_predictions)

    write_json(
        {"winner_id": winner_id, "validation_comparison": comparison_rows, "test_metrics": test_metrics},
        FIGURES_DIR / "final_selection_summary.json",
    )


if __name__ == "__main__":
    main()
