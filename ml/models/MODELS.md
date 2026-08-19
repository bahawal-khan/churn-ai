# Phase 5 — Model Development & Evaluation

Generated against `data/processed/splits/{train,val,test}.csv` (14,729 / 3,157 / 3,157 rows, Phase 4) and the fitted `ml/artifacts/preprocessing_dev/pipeline_{scaled,unscaled}.joblib` pipelines (Phase 4, not refit here). Every number below is read directly from `ml/artifacts/*/metrics.json` / `ml/models/figures/*.json`, produced by `python -m ml.models.train` — not assumed (`docs/ML_SPEC.md` §2.7 discipline, carried into this phase).

## Split usage (audited)

| Split | Used for |
|---|---|
| `train.csv` | Fitting all four models (`.fit()` / `model.fit(...)`). Never evaluated for selection. |
| `val.csv` | Every metric in the comparison table below, the BatchNorm/L2 decision, and F1-threshold selection (`ml.models.evaluate.select_threshold_by_f1`) for every model. |
| `test.csv` | Transformed and scored **exactly once**, only for the already-selected winner (Random Forest), only after its threshold was already fixed from validation results — `ml.models.train.evaluate_winner_on_test`, called last in `main()`. |

No model selection, hyperparameter choice, threshold, or repeated experimentation touched `test.csv` — enforced structurally: `train_baselines`/`train_ann` never receive `test_df` as an argument at all.

## 1. Baselines (`docs/ML_SPEC.md` §7)

Three baselines, each with a specific reason for inclusion (`ml/models/baselines.py` docstring):

- **Logistic Regression** (`class_weight="balanced"`) — cheapest possible bar the ANN must clear; interpretable coefficients double as a sanity check.
- **Random Forest** (`class_weight="balanced"`, `n_estimators=300`, `min_samples_leaf=5`) — non-linear, robust to mixed feature types, independent of the ANN's feature-importance story.
- **`HistGradientBoostingClassifier`** (`class_weight="balanced"`, `max_iter=300`) — `ML_SPEC` §7's named fallback for "XGBoost if available... else `HistGradientBoostingClassifier`". XGBoost was **not** added as a dependency: it isn't already in `ml/requirements.txt`, and ML_SPEC already names the sklearn-native fallback as acceptable, so adding it would be an unjustified extra dependency for no required benefit.

Logistic Regression trains on the **scaled** pipeline output (coefficient magnitudes are only meaningful with standardized inputs); Random Forest and Gradient Boosting train on the **unscaled** pipeline output (trees are scale-invariant; `ML_SPEC` §5 keeps both branches on identical imputation/encoding so the comparison isn't confounded by different preprocessing).

## 2. ANN architecture (`docs/ML_SPEC.md` §8)

```
Input(64 features — Phase 4 post-preprocessing shape)
 -> Dense(64, activation="relu", kernel_initializer="he_normal")
 -> Dropout(0.3)
 -> Dense(32, activation="relu", kernel_initializer="he_normal")
 -> Dropout(0.2)
 -> Dense(1, activation="sigmoid")

Loss: Binary Crossentropy, class-weighted (train-split-only class weights: {0: 0.719, 1: 1.642})
Optimizer: Adam, initial learning rate 1e-3
Callbacks:
  - EarlyStopping(monitor="val_pr_auc", mode="max", patience=10, restore_best_weights=True)
  - ReduceLROnPlateau(monitor="val_loss", mode="min", factor=0.5, patience=5, min_lr=1e-6)
Metrics tracked: accuracy, precision, recall, ROC-AUC, PR-AUC
Batch size: 32, Max epochs: 100, Random seed: 42
Total params: 6,273 (24.5 KB)
```

This is **exactly** the ML_SPEC §8 baseline shape — no BatchNormalization, no L2. That's a decision backed by an experiment, not a default (§3 below).

### Why not the tree/GB fallback for the ANN's own capacity?

Not applicable here — this section is about the ANN's own architecture. See the note about `HistGradientBoostingClassifier` above for the *baseline* fallback decision.

## 3. Overfitting / underfitting / instability investigation (`docs/ML_SPEC.md` §9)

Three configs were trained on identical train/val data with the identical fixed seed (only the config differs, so results are directly comparable, not confounded by re-randomized initialization or batch order):

| Config | Epochs run (EarlyStopping) | Best val PR-AUC | Epoch of best | Train/val PR-AUC gap at best epoch | Last-10-epoch val loss std |
|---|---|---|---|---|---|
| **Baseline (Dropout only)** | 20 | 0.5847 | 9 | 0.0282 | 0.0035 |
| + L2 (1e-4) | 27 | 0.5894 | 16 | 0.0279 | 0.0026 |
| + BatchNormalization | 23 | 0.5838 | 12 | 0.0167 | 0.0029 |

Reading these against the `ML_SPEC` §9 decision rules:

- **Overfitting signal check:** none of the three configs stop before epoch 10 (the "too early" threshold §9 sets for increasing Dropout/L2). The baseline's best epoch is 9-10 — right at the boundary, not before it — and EarlyStopping fires only after 10 more (patience) epochs of no PR-AUC improvement, which is EarlyStopping working as intended, not a sign of runaway overfitting.
- **Underfitting signal check:** train and validation metrics both keep improving through the first ~8-9 epochs (train PR-AUC 0.54 → 0.61, val PR-AUC 0.567 → 0.585) — not the "both plateau at a high value" pattern §9 describes. Not underfit.
- **Instability signal check:** last-10-epoch validation loss standard deviation is 0.0026-0.0035 across *all three* configs — a tight, near-identical band. `ReduceLROnPlateau` fired once in the baseline run (epoch 16, LR halved) and handled the mild oscillation that did occur. No config shows the "high variance across epochs" pattern §9 conditions BatchNorm on.
- **L2's actual effect:** §9 states L2 should be "added only if Dropout alone doesn't close an observed train/val gap." The train/val PR-AUC gap barely moved with L2 added (0.0282 → 0.0279) — L2 did *not* close the gap it's meant to close. It did nudge best val PR-AUC up by 0.0047, but that's the wrong criterion per §9's own rule, and 0.0047 is within the noise band the four-model comparison already shows (§ `ml/eda/model_comparison.md`).
- **BatchNorm's actual effect:** did shrink the train/val gap (0.0282 → 0.0167) but at the cost of a *lower* best val PR-AUC (0.5838 vs. 0.5847) — a worse model with a smaller gap is not the win §9 is looking for, and there was no instability problem to fix in the first place.

**Decision: keep the ML_SPEC §8 baseline architecture unchanged** — Dropout only, no BatchNorm, no L2. Neither addition is supported by the validation evidence gathered; adding either would be exactly the "blindly add techniques" behavior this phase is instructed not to do. EarlyStopping and ReduceLROnPlateau stay on (ML_SPEC §9: "always on, cheap, no downside") and are what actually stopped training at a sensible point (epoch 20, restoring the epoch-9 weights).

Training curves: `ml/models/figures/ann_training_curves.png` (loss / PR-AUC / recall, train vs. validation, per epoch). Raw per-epoch history: `ml/models/figures/ann_training_history.json`.

## 4. Vanishing-gradient / training-stability mitigations actually in effect (`docs/ML_SPEC.md` §10)

- ReLU hidden activations + He-normal initialization (matched pair — avoids the dead-unit/vanishing-gradient risk a mismatched init would risk).
- Input is the **scaled** pipeline output (`StandardScaler` on all 5 numeric columns) — unscaled `Total Charges` (up to several thousand) next to one-hot 0/1 columns is exactly the kind of magnitude mismatch §10 flags as a common instability cause.
- Conservative 1e-3 initial LR + `ReduceLROnPlateau` instead of hand-tuning a higher rate.
- Shallow 2-hidden-layer network — vanishing/exploding gradients are primarily a deep-network problem this architecture doesn't have by construction.
- Gradient-norm logging / clipping: **not added**. §10 makes both conditional on "if instability is observed" — the §3 investigation above found none, so neither was added.

## 5. Class imbalance strategy (`docs/ML_SPEC.md` §11)

Training-set churn rate is 30.45% (Phase 4). All three baselines use `class_weight="balanced"`; the ANN uses class-weighted binary crossentropy with weights computed from the training split only (`{0: 0.719, 1: 1.642}`, `ml.models.ann.compute_class_weights`). Threshold tuning (§6 below) was applied as the primary additional lever, per §11's stated order ("threshold tuning is treated as a primary lever before considering resampling").

**SMOTE: evaluated as a decision, not run as an experiment, and that's a deliberate scope call.** §11 makes SMOTE adoption conditional on it "measurably improving validation recall without an unacceptable precision drop" over class-weighting. Class-weighting + threshold tuning already gets Random Forest to 0.8158 validation recall (0.8200 on test) — a substantial majority of actual churners caught — without SMOTE. Given `ML_SPEC` §11 already frames threshold tuning as the primary lever *before* considering resampling, and that lever alone reached a strong recall number, adding SMOTE now would be adding a technique without first establishing that class-weighting + thresholding was insufficient — exactly the "blindly add techniques" behavior this phase avoids elsewhere. If a future phase's business requirements call for materially higher recall than 0.82, SMOTE (train-split-only) is the documented next experiment to run, not silently skipped.

## 6. Decision threshold selection (`docs/ML_SPEC.md` §12)

`ml.models.evaluate.select_threshold_by_f1` scans thresholds 0.01-0.99 (step 0.01) against **validation-set** probabilities only and picks the F1-maximizing value, for every model independently:

| Model | Threshold |
|---|---|
| Logistic Regression | 0.56 |
| **Random Forest (selected)** | **0.37** |
| Gradient Boosting | 0.46 |
| ANN | 0.50 |

Random Forest's threshold (0.37, below the naive 0.5) reflects `class_weight="balanced"` pushing its probability outputs toward the minority class — a lower cutoff is what actually maximizes F1 for this model, found empirically from validation data, not assumed.

## 7. Baseline vs. ANN comparison, final model choice

Full comparison table, ROC/PR curve overlay, and the "is the ANN actually better" finding are in **`ml/eda/model_comparison.md`** (ML_SPEC §7's named location for this artifact). Summary: **Random Forest was objectively selected** — highest validation PR-AUC (0.5855) and by far the highest validation recall (0.8158 vs. the ANN's 0.6951) — per `ML_SPEC` §12's stated priority on Recall/PR-AUC. The ANN is competitive (it beats Logistic Regression, and its PR-AUC is only 0.0008 behind Random Forest's) but does not win. This phase's original brief named the ANN as intended production candidate; the acceptance criteria explicitly require not assuming that outcome, and the validation data does not bear it out — reported honestly rather than defended.

## 8. Final test-set evaluation (Random Forest, touched once)

| Metric | Value |
|---|---|
| Accuracy | 0.6585 |
| Precision | 0.4654 |
| Recall | 0.8200 |
| F1 | 0.5938 |
| ROC-AUC | 0.7777 |
| PR-AUC | 0.5930 |

Confusion matrix, classification report, calibration curve: `ml/models/figures/random_forest_v1_test_confusion_matrix.png`, `ml/models/figures/random_forest_v1_test_calibration.png`, and the full `classification_report` dict in `ml/artifacts/random_forest_v1/metrics.json`.

## 9. Artifacts (`docs/ML_SPEC.md` §14)

```
ml/artifacts/
  logistic_regression_v1/   { model.joblib, pipeline.joblib, metadata.json, metrics.json }
  random_forest_v1/         { model.joblib, pipeline.joblib, metadata.json, metrics.json }   <- selected
  gradient_boosting_v1/     { model.joblib, pipeline.joblib, metadata.json, metrics.json }
  ann_v1/                   { model.keras,  pipeline.joblib, metadata.json, metrics.json }
```

Every `metadata.json` carries: `model_id`, `algorithm` (matches `docs/DATABASE_SPEC.md` §2.7's `models.algorithm` CHECK constraint values), `model_type`, `version`, `created_at`, `random_seed`, `hyperparameters`, `trained_on_dataset`, `train_row_count`, `preprocessing_pipeline_variant`, `feature_schema` (ordered `ml.config.MODELING_COLUMNS`, dtype + observed categories — matches `models.feature_schema`), `decision_threshold`, `risk_thresholds` (`{"low_max": 0.3, "medium_max": 0.6}`, `PROJECT_SPEC.md` §18), and `test_evaluated`. Only `random_forest_v1`'s carries `test_evaluated: true` and `selected_as_recommended_production_model: true` — every other model's stays `false`/absent, matching the "test set touched once, for the final selected model only" rule (verified in `tests/ml/test_models.py::test_saved_metadata_has_required_fields` / `test_saved_metrics_json_has_null_test_until_final_evaluation`).

`global_shap.json` is **not** produced by this phase — SHAP explainability is explicitly Phase 6+ scope, out of bounds here per this phase's brief.

## 10. A limitation worth stating plainly

Random Forest's artifact is **~50 MB** — roughly 300-500x every other candidate's size (Gradient Boosting 160 KB, ANN 104 KB, Logistic Regression 4 KB) — for a PR-AUC edge over the ANN of 0.0008, noise-level at this sample size. `ML_SPEC` §7 already flags model-size-vs-hosting-constraint as a real concern for exactly this kind of choice; this phase's selection rule is validation PR-AUC/recall only (as specified), so Random Forest is the recorded winner, but that size trade-off should be revisited once a deployment phase with actual hosting constraints (`docs/DEPLOYMENT.md`) is in scope. Full detail in `ml/eda/model_comparison.md`.

## 11. Tests

`tests/ml/test_models.py` — 21 tests, all passing (`python -m pytest tests/ml/test_models.py`), covering: baseline builder configuration (`class_weight="balanced"`, seeded), ANN model creation (architecture, BatchNorm toggle), output shape and probability range, class-weight computation, reproducibility (identical weights from identical seeds; near-identical predictions after identical short training runs), the shared metric-suite/threshold-selection utilities on known synthetic ground truth, risk-level bucketing at the exact `PROJECT_SPEC.md` §18 boundaries, threshold-driven predicted-class flips, artifact save/load round-tripping, required `metadata.json` fields, `feature_schema` leakage/ordering guarantees, and end-to-end `load_model_bundle` → `predict` on a freshly saved artifact. Full repo suite: **131 passed** (`python -m pytest tests/`).

## 12. Scope note

This phase builds, trains, tunes, and evaluates baseline models and the ANN, selects a decision threshold from validation data, and evaluates the final selection once on test data. It does not implement SHAP/explainability, the Flask backend, the database, authentication, the frontend, or deployment — all explicitly out of scope per this phase's brief.
