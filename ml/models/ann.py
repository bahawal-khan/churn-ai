"""ANN churn classifier (`docs/ML_SPEC.md` §8, §9, §10).

Architecture is the ML_SPEC §8 baseline shape:

    Input(N engineered features)
     -> Dense(64, relu, he_normal)
     -> [BatchNormalization()]   -- included only if `use_batch_norm=True`
     -> Dropout(dropout_rates[0])
     -> Dense(32, relu, he_normal)
     -> [BatchNormalization()]
     -> Dropout(dropout_rates[1])
     -> Dense(1, sigmoid)

`build_model` takes `use_batch_norm`/`l2_strength` as explicit toggles rather
than hard-coding them on, because ML_SPEC §9 requires each to be justified
by observed training curves, not enabled by default:

- Dropout: on by default (ML_SPEC §9 — "cheap to include", moderate feature
  count benefits from regularization).
- L2: off by default; `train.py` turns it on only if Dropout alone doesn't
  close an observed train/val gap.
- BatchNormalization: off by default; `train.py` turns it on only if
  training curves show instability without it.
- EarlyStopping / ReduceLROnPlateau: always on (ML_SPEC §9 — cheap, no
  downside), configured in `build_callbacks`.

Training stability (ML_SPEC §10): ReLU + He-initialization (matched to
ReLU, avoids the vanishing-gradient risk sigmoid/tanh hidden layers would
have), mandatory pre-scaled numeric input (`pipeline_scaled`, Phase 4 — this
module assumes its input `X` is already through that pipeline), a
conservative 1e-3 initial learning rate with `ReduceLROnPlateau` instead of
manual LR tuning, and a shallow 2-hidden-layer network (vanishing/exploding
gradients are primarily a deep-network problem this architecture doesn't
have).
"""

from __future__ import annotations

import os
import random
from typing import Any

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight
from tensorflow import keras
from tensorflow.keras import layers, regularizers

from ml.config import ALGORITHM_ANN, RANDOM_SEED

HIDDEN_UNITS: tuple[int, int] = (64, 32)
DEFAULT_DROPOUT_RATES: tuple[float, float] = (0.3, 0.2)
DEFAULT_LEARNING_RATE = 1e-3
DEFAULT_BATCH_SIZE = 32
DEFAULT_MAX_EPOCHS = 100
EARLY_STOPPING_PATIENCE = 10
REDUCE_LR_PATIENCE = 5
REDUCE_LR_FACTOR = 0.5
MIN_LEARNING_RATE = 1e-6


def set_seeds(seed: int = RANDOM_SEED) -> None:
    """Reproducibility (ML_SPEC §8 requires fixed random seeds). TensorFlow
    on CPU with the default multi-threaded ops is not bitwise-deterministic
    across runs even with a fixed seed; `tf.config.experimental
    .enable_op_determinism()` trades a little throughput for run-to-run
    determinism, which is worth it here given the training set is small
    (~14.7k rows) and speed is not a constraint."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.random.set_seed(seed)
    tf.config.experimental.enable_op_determinism()


def build_model(
    input_dim: int,
    hidden_units: tuple[int, int] = HIDDEN_UNITS,
    dropout_rates: tuple[float, float] = DEFAULT_DROPOUT_RATES,
    use_batch_norm: bool = False,
    l2_strength: float | None = None,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    seed: int = RANDOM_SEED,
) -> keras.Model:
    set_seeds(seed)
    regularizer = regularizers.l2(l2_strength) if l2_strength else None

    model = keras.Sequential(name="churn_ann")
    model.add(keras.Input(shape=(input_dim,)))

    model.add(
        layers.Dense(
            hidden_units[0],
            activation="relu",
            kernel_initializer="he_normal",
            kernel_regularizer=regularizer,
            name="hidden_1",
        )
    )
    if use_batch_norm:
        model.add(layers.BatchNormalization(name="batch_norm_1"))
    model.add(layers.Dropout(dropout_rates[0], name="dropout_1"))

    model.add(
        layers.Dense(
            hidden_units[1],
            activation="relu",
            kernel_initializer="he_normal",
            kernel_regularizer=regularizer,
            name="hidden_2",
        )
    )
    if use_batch_norm:
        model.add(layers.BatchNormalization(name="batch_norm_2"))
    model.add(layers.Dropout(dropout_rates[1], name="dropout_2"))

    model.add(layers.Dense(1, activation="sigmoid", name="output"))

    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
        loss="binary_crossentropy",
        metrics=[
            keras.metrics.BinaryAccuracy(name="accuracy"),
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.AUC(name="auc", curve="ROC"),
            keras.metrics.AUC(name="pr_auc", curve="PR"),
        ],
    )
    return model


def compute_class_weights(y_train: np.ndarray) -> dict[int, float]:
    """Class-weighted loss (ML_SPEC §11), the ANN equivalent of the
    baselines' `class_weight="balanced"` — computed from the training split
    only, per the same fit-on-train-only discipline as everything else in
    this pipeline."""
    classes = np.unique(y_train)
    weights = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    return {int(c): float(w) for c, w in zip(classes, weights)}


def build_callbacks(
    early_stopping_patience: int = EARLY_STOPPING_PATIENCE,
    reduce_lr_patience: int = REDUCE_LR_PATIENCE,
    reduce_lr_factor: float = REDUCE_LR_FACTOR,
) -> list[keras.callbacks.Callback]:
    return [
        keras.callbacks.EarlyStopping(
            monitor="val_pr_auc",
            mode="max",
            patience=early_stopping_patience,
            restore_best_weights=True,
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=reduce_lr_factor,
            patience=reduce_lr_patience,
            min_lr=MIN_LEARNING_RATE,
        ),
    ]


def train_model(
    model: keras.Model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    class_weight: dict[int, float] | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    max_epochs: int = DEFAULT_MAX_EPOCHS,
    seed: int = RANDOM_SEED,
    verbose: int = 2,
) -> keras.callbacks.History:
    set_seeds(seed)
    return model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=max_epochs,
        batch_size=batch_size,
        class_weight=class_weight,
        callbacks=build_callbacks(),
        verbose=verbose,
    )


def history_to_dict(history: keras.callbacks.History) -> dict[str, list[float]]:
    return {k: [float(v) for v in vals] for k, vals in history.history.items()}


ANN_HYPERPARAMETERS_TEMPLATE: dict[str, Any] = {
    "algorithm": ALGORITHM_ANN,
    "hidden_units": list(HIDDEN_UNITS),
    "hidden_activation": "relu",
    "kernel_initializer": "he_normal",
    "output_activation": "sigmoid",
    "loss": "binary_crossentropy",
    "optimizer": "adam",
    "initial_learning_rate": DEFAULT_LEARNING_RATE,
    "batch_size": DEFAULT_BATCH_SIZE,
    "max_epochs": DEFAULT_MAX_EPOCHS,
    "early_stopping_monitor": "val_pr_auc",
    "early_stopping_patience": EARLY_STOPPING_PATIENCE,
    "reduce_lr_on_plateau_monitor": "val_loss",
    "reduce_lr_on_plateau_factor": REDUCE_LR_FACTOR,
    "reduce_lr_on_plateau_patience": REDUCE_LR_PATIENCE,
    "random_seed": RANDOM_SEED,
}
