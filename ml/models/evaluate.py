"""Shared evaluation utilities for baseline models and the ANN
(`docs/ML_SPEC.md` §12).

Every model (Logistic Regression, Random Forest, Gradient Boosting, ANN) is
scored through the exact same functions here so the comparison in
`ml/eda/model_comparison.md` is apples-to-apples: same metric definitions,
same threshold-selection procedure, same plotting code.

Threshold selection (`compute_metric_suite`'s `threshold` argument,
`select_threshold_by_f1`) is only ever called by `train.py` against
validation-set probabilities — this module has no knowledge of which split
a given `y_true`/`y_prob` pair came from, so the "validation only" rule
(ML_SPEC §12, PROJECT_SPEC binding rule) is enforced by the caller, not
here. See `ml/models/train.py` for where that boundary is actually held.

`matplotlib` is imported lazily, inside each `plot_*` function, rather than
at module scope (Phase 12 deployment finding, same pattern as
`ml/models/ann.py`'s tensorflow fix): `compute_metric_suite` and
`select_threshold_by_f1` — the only two functions this module exports to
`backend/services/training_service.py`'s production training path — never
touch `plt`, so the backend shouldn't have to carry matplotlib/Pillow/
fontTools (~69 MB) just to boot on a disk-constrained host. The `plot_*`
functions (dev/EDA figure generation, never called from `backend/`) are
unchanged in behavior when matplotlib is installed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    classification_report,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

# Candidate thresholds scanned when selecting the F1-maximizing decision
# threshold on validation data (ML_SPEC §12). Step of 0.01 across the full
# (0, 1) range is fine-grained enough for a probability-based decision and
# cheap to scan (100 points x O(n) metric computation).
THRESHOLD_CANDIDATES = np.round(np.arange(0.01, 1.00, 0.01), 2)


def compute_metric_suite(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict[str, Any]:
    """Full ML_SPEC §12 metric suite at a given decision threshold.

    ROC-AUC/PR-AUC are threshold-independent (rank-based over `y_prob`) and
    are included alongside the threshold-dependent metrics so a caller gets
    the complete required suite from one call.
    """
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)
    y_pred = (y_prob >= threshold).astype(int)

    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "classification_report": classification_report(
            y_true, y_pred, labels=[0, 1], target_names=["no_churn", "churn"], output_dict=True, zero_division=0
        ),
    }


def select_threshold_by_f1(y_true: np.ndarray, y_prob: np.ndarray) -> tuple[float, dict[str, Any]]:
    """Scans `THRESHOLD_CANDIDATES` and returns the threshold maximizing F1
    on the given (validation-only, per caller contract) probabilities, plus
    the full metric suite at that threshold (ML_SPEC §12: "default decision
    threshold is chosen by maximizing F1 on the validation set")."""
    y_true = np.asarray(y_true).astype(int)
    y_prob = np.asarray(y_prob).astype(float)

    f1_scores = [
        f1_score(y_true, (y_prob >= t).astype(int), zero_division=0) for t in THRESHOLD_CANDIDATES
    ]
    best_idx = int(np.argmax(f1_scores))
    best_threshold = float(THRESHOLD_CANDIDATES[best_idx])
    return best_threshold, compute_metric_suite(y_true, y_prob, best_threshold)


def plot_confusion_matrix(cm: list[list[int]], title: str, path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cm_arr = np.array(cm)
    fig, ax = plt.subplots(figsize=(4, 4))
    im = ax.imshow(cm_arr, cmap="Blues")
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["no_churn", "churn"])
    ax.set_yticklabels(["no_churn", "churn"])
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title(title)
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm_arr[i, j]), ha="center", va="center", color="black")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_roc_pr_curves(results: dict[str, dict[str, np.ndarray]], path: Path) -> None:
    """`results`: {model_label: {"y_true": arr, "y_prob": arr}} — overlays
    every model's ROC and PR curve on validation data for a single
    side-by-side comparison figure."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax_roc, ax_pr) = plt.subplots(1, 2, figsize=(11, 5))
    for label, data in results.items():
        y_true, y_prob = data["y_true"], data["y_prob"]
        fpr, tpr, _ = roc_curve(y_true, y_prob)
        ax_roc.plot(fpr, tpr, label=f"{label} (AUC={roc_auc_score(y_true, y_prob):.3f})")

        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        ax_pr.plot(recall, precision, label=f"{label} (AP={average_precision_score(y_true, y_prob):.3f})")

    ax_roc.plot([0, 1], [0, 1], "k--", linewidth=0.8)
    ax_roc.set_xlabel("False Positive Rate")
    ax_roc.set_ylabel("True Positive Rate")
    ax_roc.set_title("ROC Curve (validation)")
    ax_roc.legend(fontsize=8)

    ax_pr.set_xlabel("Recall")
    ax_pr.set_ylabel("Precision")
    ax_pr.set_title("Precision-Recall Curve (validation)")
    ax_pr.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def plot_calibration_curve(y_true: np.ndarray, y_prob: np.ndarray, title: str, path: Path) -> None:
    """Reliability diagram (ML_SPEC §12: predicted probabilities are shown
    directly to end users and should be reasonably well-calibrated)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="quantile")
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(mean_pred, frac_pos, marker="o", label=title)
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="Perfectly calibrated")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives")
    ax.set_title(f"Calibration curve — {title}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
