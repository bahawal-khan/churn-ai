# ChurnAI — ML Specification (ML_SPEC.md)

Companion to `PROJECT_SPEC.md`. Covers the full data-to-model pipeline for the development/benchmark model (Phase 1–7). The same preprocessing/feature/data-quality contracts are reused verbatim for company-specific training (Phase 8+, §16 of PROJECT_SPEC).

---

## 1. Dataset Schema Contract (binding)

**Raw modeling columns kept** (from IBM schema, after audit — see PROJECT_SPEC §2.1):

`Gender, Senior Citizen, Partner, Dependents, Tenure Months, Phone Service, Multiple Lines, Internet Service, Online Security, Online Backup, Device Protection, Tech Support, Streaming TV, Streaming Movies, Contract, Paperless Billing, Payment Method, Monthly Charges, Total Charges`

**Conditional column:** `CLTV` is **not** unconditionally part of this contract. Its inclusion is decided by the §2.5 EDA correlation review (retained only if that review finds it is not a target-leakage/business-metric confound) — the same "if retained" condition already stated in §5's preprocessing column list. Until that review runs, pipelines must treat `CLTV` as optional/excluded by default, not assume inclusion.

**Target:** `Churn Value` (0/1). `Churn Label` kept for display only, dropped before modeling.

**Dropped before modeling (identifiers/zero-variance/leakage):** `CustomerID`, `Count`, `Country`\* , `State`, `City`, `Zip Code`, `Lat Long`, `Latitude`, `Longitude`, `Churn Score` (leakage), `Churn Reason` (leakage — only populated for churners).

\*`Country` is dropped as a *raw model feature* for the IBM subset (constant = USA). The **combined development dataset** reintroduces a `Source` column (`IBM` / `Pakistan-Synthetic` / `India-Synthetic`) but it is used **only** for EDA, stratified sampling (§6), and dataset provenance tracking — it is **never** included in the `ColumnTransformer`'s input columns (§5) for any model that gets promoted to baseline/active status. `Source` may appear as an input in a standalone offline research notebook that specifically measures how much regional signal exists in the data, but that experiment's model is never serialized as a production artifact (`§14`) or activated — this is a structural rule, not a per-run judgment call.

**Added for company uploads:** any additional columns beyond this contract are preserved for display but excluded from modeling unless the user explicitly maps them during target/feature selection (V1: automatic — only columns matching the known schema pattern are used; unmapped columns are shown in the preview but excluded from training with a visible note).

---

## 2. EDA Plan

### 2.1 Structural audit
- `.shape`, `.dtypes`, memory footprint
- Missing-value count/percentage per column
- Duplicate row count, duplicate `CustomerID` count
- Cardinality per categorical column
- Identification of identifier-like / zero-variance / leakage columns (cross-check against §1 drop list)

### 2.2 Distribution analysis
- Numerical: histograms + boxplots for `Tenure Months`, `Monthly Charges`, `Total Charges`, `CLTV`
- Categorical: bar charts of value counts for every categorical column
- Repeated per `Source` (IBM / PK-synthetic / IN-synthetic) to visually confirm the synthetic generators produce plausible, non-identical, non-duplicated distributions

### 2.3 Target analysis
- Overall churn rate (documented actual value: **26.54%** on IBM alone; recomputed on the combined dataset once synthetic data is generated)
- Churn rate by `Source`
- Churn rate by archetype (Pakistan/India generators only)

### 2.4 Relationship analysis (required visuals)
- Churn rate by `Contract`
- Churn rate by `Tenure Months` (binned)
- Churn rate by `Payment Method`
- Churn distribution vs. `Monthly Charges` (boxplot, churned vs not)
- Correlation heatmap (numerical features + target)
- Categorical churn-rate bar charts for each service/add-on column

### 2.5 Leakage & suspicious-feature review
- Explicit written confirmation that `Churn Score` and `Churn Reason` are excluded and why
- Check `CLTV`'s correlation with target; document the finding and the modeling decision (include vs. exclude) based on that finding, not assumption

### 2.6 Cross-source comparison
- Side-by-side distribution comparison (IBM vs PK-synthetic vs IN-synthetic) for tenure, monthly charges, contract mix, churn rate
- Purpose: confirm synthetic data is *distinct but plausible*, not a copy of IBM and not wildly unrealistic

### 2.7 Deliverable
A Jupyter notebook (or equivalent script producing saved figures) under `ml/eda/`, plus a written findings summary (`ml/eda/FINDINGS.md`) that directly informs §4 Feature Engineering decisions. Findings must reference actual computed numbers, not assumed ones.

---

## 3. Data Quality Pipeline

Implemented once as `DataQualityValidator` (built during Phase 2 for dev-dataset ingestion **and** reused unchanged for every company upload in production — same code path).

Checks performed, each yielding `pass` / `warn` / `fail`:

| Check | Fail condition (example) |
|---|---|
| Missing values | Required column has nulls beyond an acceptable threshold |
| Duplicates | Duplicate rows or duplicate ID column |
| Invalid/impossible values | Negative `Monthly Charges`/`Tenure`, tenure > plausible max (e.g., >100 years in months) |
| Inconsistent categories | Case/whitespace variants of the same category (`"yes"`, `"Yes "`, `"YES"`) |
| Wrong dtypes | Numeric column stored as text and not coercible (mirrors the real `Total Charges` issue found in the IBM data) |
| Malformed CSV | Ragged rows, unparseable encoding |
| Missing required columns | Expected schema columns absent |
| Unexpected columns | Extra columns present (warn, not fail — shown in preview, excluded from modeling) |
| Target problems | For training uploads: target column missing, non-binary, or single-class |
| High cardinality | A categorical column with near-unique values per row (likely an identifier) |
| Identifier columns | Column name/pattern matches ID-like conventions |

**Output:** structured JSON report (`{ "checks": [...], "overall_status": "pass|warn|fail", "row_count": ..., "issues_found": ... }`) rendered in the UI as a human-readable Data Quality Report panel (§ PROJECT_SPEC §16 workflow step).

---

## 4. Feature Engineering (documented rationale per feature)

| Feature | Rationale |
|---|---|
| `tenure_group` (bucketed: 0–12, 13–24, 25–48, 49+ months) | Churn-vs-tenure relationship is known to be non-linear (new customers churn disproportionately); buckets let simpler models capture this without manual polynomial terms |
| `has_internet` (bool, derived) | Normalizes the "No internet service" placeholder value shared across 6 dependent columns so downstream encoding doesn't treat it as 6 independent redundant categories |
| `active_addon_count` (0–6) | Count of active add-on services (Online Security, Backup, Device Protection, Tech Support, Streaming TV, Streaming Movies); a direct, interpretable stickiness/engagement proxy |
| `has_protection_addon` (bool) | Online Security OR Device Protection OR Tech Support active — groups "risk-reducing" add-ons distinctly from entertainment add-ons |
| `has_streaming_addon` (bool) | Streaming TV OR Streaming Movies active — entertainment add-ons behave differently from protection add-ons in churn literature |
| `avg_monthly_value` (`Total Charges / max(Tenure Months, 1)`) | Cross-checks `Monthly Charges` against realized billing history; discrepancies can flag pricing changes/promotions ending, a known churn trigger |
| `contract_risk_flag` (bool: Month-to-month) | Directly encodes the single strongest known churn driver in the reference domain; kept as an explicit flag in addition to the one-hot encoded `Contract` for interpretability in SHAP summaries |
| `payment_risk_flag` (bool: Electronic check) | Electronic check is consistently associated with higher churn in the IBM dataset (confirmed in EDA, not assumed) |
| `family_flag` (bool: Partner OR Dependents = Yes) | Proxy for account stickiness / switching cost |

No feature is added without one of the above documented reasons. Any feature considered and **rejected** (e.g., raw `CustomerID` hashing, raw lat/long) is also recorded in `ml/eda/FINDINGS.md` with the reason for rejection (identifier leakage risk, no plausible causal/statistical link, or redundant with an existing feature).

**Leakage prevention:** any feature whose computation involves an aggregate statistic (e.g., a mean/rate) must be fit on the training split only and applied to validation/test/inference via the fitted transformer — never computed globally before the split.

**Reproducibility:** all feature engineering is implemented as `sklearn`-compatible custom transformers (`FunctionTransformer` / small custom `TransformerMixin` classes) composed into the same pipeline as preprocessing, versioned with the model artifact.

---

## 5. Preprocessing Pipeline

```
ColumnTransformer(
  numerical:   SimpleImputer(strategy="median") → StandardScaler
  categorical: SimpleImputer(strategy="most_frequent") → OneHotEncoder(handle_unknown="ignore")
)
→ wrapped in a Pipeline with the feature-engineering transformers (§4) applied first
```

- Numerical columns: `Tenure Months`, `Monthly Charges`, `Total Charges`, `CLTV` (if retained), plus engineered numerics (`active_addon_count`, `avg_monthly_value`).
- Categorical columns: all remaining Yes/No and multi-category columns, one-hot encoded with `handle_unknown="ignore"` so inference never breaks on an unseen category (e.g., a company upload with a payment method not seen in training — it degrades gracefully to an all-zero encoding rather than erroring).
- Tree-based baselines (Random Forest, Gradient Boosting) use a parallel branch without scaling (unnecessary for trees) but with the same imputation/encoding, to keep evaluation apples-to-apples on the same engineered feature set.
- The fitted `Pipeline` object is pickled/joblib-serialized and stored alongside the model artifact (`ml/artifacts/{model_id}/pipeline.joblib`, `ml/artifacts/{model_id}/model.*`), so a given model version is never applied with a mismatched preprocessing state.
- **Strict rule:** `pipeline.fit()` is called only on the training split. Validation/test/inference always use `pipeline.transform()`.

---

## 6. Train / Validation / Test Split

- Stratified split on `Churn Value`, and for the combined development dataset, jointly stratified on `(Churn Value, Source)` using a two-column stratification key so IBM/PK-synthetic/IN-synthetic are proportionally represented in train/val/test.
- Ratio: 70% train / 15% validation / 15% test.
- Fixed seed (`RANDOM_SEED = 42`) for reproducibility.
- Test set is used exactly once, for final reported metrics (§8/§9). All iteration (baseline comparison, ANN tuning, threshold selection) happens against the validation set only.
- For company-specific training on smaller uploaded datasets, the same split logic applies; if a company's dataset is too small to stratify safely (e.g., fewer than ~200 rows or a target class with fewer than ~20 positive examples), the UI surfaces a clear warning about statistical reliability rather than silently training an unreliable model.

---

## 7. Baseline Models

| Model | Purpose |
|---|---|
| Logistic Regression (`class_weight="balanced"`) | Fast, interpretable baseline; coefficient signs cross-checked against EDA findings as a sanity check |
| Random Forest (`class_weight="balanced"`) | Non-linear baseline, robust to mixed feature types, provides a feature-importance cross-check against SHAP |
| Gradient Boosting (XGBoost if available in the deployment environment, else `HistGradientBoostingClassifier`) | Strong tabular-data baseline; included only if it fits within PythonAnywhere free-tier constraints (model size/inference latency) — this fit check is a Phase 4 deliverable, not assumed up front |

All three are evaluated on the identical validation metric suite (§12) as the ANN. The winning model for the "baseline (global) model" slot is chosen by validation PR-AUC/F1, not by assuming the ANN wins — the comparison table itself is a required Phase 4/6 deliverable artifact (`ml/eda/model_comparison.md` or notebook output).

---

## 8. ANN Architecture

```
Input (N engineered features after preprocessing)
 → Dense(64, activation="relu", kernel_initializer="he_normal")
 → BatchNormalization()            [included only if Phase 6 experiments show it helps stability/convergence]
 → Dropout(0.3)
 → Dense(32, activation="relu", kernel_initializer="he_normal")
 → Dropout(0.2)
 → Dense(1, activation="sigmoid")

Loss: Binary Crossentropy (optionally class-weighted per §11)
Optimizer: Adam, initial learning rate 1e-3
Callbacks:
  - EarlyStopping(monitor="val_pr_auc" or "val_loss", patience=10, restore_best_weights=True)
  - ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5)
Metrics tracked: accuracy, precision, recall, AUC, PR-AUC
Batch size: 32 (starting point, tuned empirically)
Max epochs: 100 (EarlyStopping expected to halt earlier)
```

The exact final architecture/hyperparameters, once Phase 5/6 experimentation runs, are recorded in this section with the actual chosen values and the experiment evidence that justified them (this section is updated post-Phase-6, not left as a plan forever).

---

## 9. Overfitting / Underfitting Detection

- Every training run logs and plots train vs. validation loss and train vs. validation PR-AUC per epoch.
- **Overfitting signal:** validation loss increases (or validation PR-AUC decreases) for several consecutive epochs while training loss keeps decreasing → EarlyStopping triggers; Dropout/L2 strength increased if this happens too early (e.g., before epoch 10) across multiple seeds.
- **Underfitting signal:** both train and validation loss plateau at a high value / both metrics stay poor → architecture is judged too small or learning rate too low; addressed by a modest capacity increase or a longer warmup, not by removing regularization first.
- **Instability signal:** validation metric oscillates with high variance across epochs → learning rate reduced (`ReduceLROnPlateau`) and/or BatchNorm added.
- Techniques applied **selectively, with justification recorded per run**, not all enabled by default:
  - Dropout: default on (churn tabular data with a moderate feature count benefits from regularization; cheap to include).
  - L2 weight regularization: added only if Dropout alone doesn't close an observed train/val gap.
  - EarlyStopping: always on (cheap, no downside).
  - ReduceLROnPlateau: always on (cheap, no downside).
  - BatchNormalization: added only if training curves show notable instability without it — not included by default in a small 2-hidden-layer network where it often adds little value and some overhead.

---

## 10. Training Stability (Vanishing / Exploding Gradients)

- ReLU activations (do not saturate like sigmoid/tanh in hidden layers) + He initialization (matched to ReLU).
- Mandatory `StandardScaler` on numerical inputs before the ANN (unscaled high-magnitude features like `Total Charges` are a common cause of early instability).
- Conservative initial learning rate (1e-3) with `ReduceLROnPlateau` rather than a high LR needing manual tuning.
- Shallow network (2 hidden layers) — vanishing/exploding gradients are primarily a deep-network problem; this architecture is intentionally not deep.
- Gradient-norm logging is added as an optional diagnostic during Phase 6 experimentation if any instability is observed; gradient clipping (`clipnorm`) is added only if logging confirms exploding gradients — not applied preemptively without evidence.

---

## 11. Class Imbalance Strategy

- Baseline: `class_weight="balanced"` for Logistic Regression/Random Forest/XGBoost; equivalent class-weighted loss for the ANN.
- Threshold tuning (§12) is treated as a primary lever before considering resampling.
- SMOTE is **evaluated, not assumed**: a Phase 4/6 experiment compares class-weighting vs. SMOTE (applied only to the training split, never validation/test) on validation PR-AUC/recall/precision. SMOTE is adopted only if it measurably improves validation recall without an unacceptable precision drop; the result and decision are recorded here once the experiment runs.
- PR-AUC is treated as at least as important as ROC-AUC given the moderate positive-class imbalance (~26–30% churn rate).

---

## 12. Model Evaluation

Full metric suite computed on validation (for model selection/threshold tuning) and once on test (final report): Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, confusion matrix, full `classification_report`, and a calibration curve (reliability diagram) since predicted probabilities are shown directly to end users and should be reasonably well-calibrated, not just well-ranked.

**Threshold selection:** default decision threshold is chosen by maximizing F1 on the validation set (balances the cost of missed churners against false-alarm outreach); the chosen threshold and the reasoning are recorded per model version. This is distinct from the **risk-level thresholds** (Low/Medium/High, PROJECT_SPEC §18), which are a separate, coarser business-facing bucketing of the raw probability and are not tied to the binary decision threshold.

**Primary metrics for this problem:** Recall and PR-AUC are weighted most heavily in model selection (a missed churner is more costly than an unnecessary retention touchpoint), with Precision and F1 reported alongside to avoid a recall-only model that floods the business with false positives.

---

## 13. SHAP Explainability

- Explainer type chosen per winning model family: `shap.TreeExplainer` for Random Forest/Gradient Boosting, `shap.LinearExplainer` for Logistic Regression, `shap.DeepExplainer` or `shap.GradientExplainer` for the ANN (Keras/TF) — selected based on which model is actually promoted to "active" per §7/§12, not fixed in advance.
- **Global explanations:** computed once per trained model version over a representative sample of the training/validation set (not the full set, for compute-cost reasons on free-tier hosting), cached as `ml/artifacts/{model_id}/global_shap.json`, and served directly to the Dashboard's "Top Churn Drivers" and to the Analytics page.
- **Local explanations:** computed on-demand per prediction request (single prediction) and per row for batch prediction (with a documented performance budget — e.g., local SHAP may be computed synchronously for single predictions but deferred/sampled for very large batch files, with the summary still fully computed and per-row SHAP available for download or lookup).
- Every explanation surface in the UI includes the fixed disclaimer text defined in PROJECT_SPEC §15: SHAP values reflect model-learned correlation, not proven causation.
- SHAP values are never hard-coded, templated, or approximated with static rules — every displayed value is the actual output of the SHAP library against the actual trained model and the actual input.

---

## 14. Artifact Versioning

Each trained model (baseline or company-specific) is stored as a versioned artifact bundle under the top-level `ml/artifacts/` directory (`PROJECT_SPEC.md §35`) — a sibling of `backend/`, not nested inside it, since `ml/` is a shared package imported by the backend's `services/` layer (`BACKEND_SPEC.md §1`):

```
ml/artifacts/{model_id}/
  ├── model.<ext>            (joblib for sklearn models, .keras/.h5 for ANN)
  ├── pipeline.joblib         (fitted preprocessing pipeline)
  ├── metadata.json           (algorithm, hyperparameters, training date, dataset id,
  │                            row count, decision threshold, risk thresholds used)
  ├── metrics.json             (full validation + test metric suite)
  └── global_shap.json         (cached global SHAP summary)
```

In production, this directory is what `MODEL_ARTIFACT_DIR` (`DEPLOYMENT.md §2`) points at.

`metadata.json` is the record that answers "what was this model trained on, when, and how" — surfaced in the Model Management UI (`FRONTEND_SPEC.md §15`) and required by PROJECT_SPEC §25 (`models` DB entity, fully defined in `DATABASE_SPEC.md §2.7`, mirrors this metadata for querying). `metadata.json` includes a `feature_schema` field (the exact ordered list of input columns and their expected types/categories the fitted pipeline expects) — this is the artifact that PROJECT_SPEC §16's prediction-time schema validation checks incoming data against, so a model is never fed a differently-shaped input.

---

## 15. Coverage Checklist (traceability)

Every topic required of this ML specification is addressed at the section noted — kept here as a single traceable index rather than trusting it's "covered somewhere":

| Required topic | Section |
|---|---|
| EDA | §2 |
| Data quality | §3 |
| Feature engineering | §4 |
| Preprocessing | §5 |
| Train/validation/test strategy | §6 |
| Baseline models (Logistic Regression, Random Forest, Gradient Boosting) | §7 |
| ANN architecture | §8 |
| Overfitting / underfitting detection & response | §9 |
| Vanishing / exploding gradients | §10 |
| Dropout | §8, §9 |
| Batch normalization | §8, §9 (applied conditionally, not by default) |
| Early stopping | §8, §9 |
| Learning-rate scheduling (`ReduceLROnPlateau`) | §8, §9, §10 |
| Class imbalance strategy | §11 |
| Model evaluation metrics | §12 |
| Decision-threshold tuning | §12 |
| SHAP explainability (global + local) | §13 |
| Model/artifact versioning + feature-schema recording | §14 |
| Objective ANN-vs-baseline comparison (no assumed winner) | §7, §12, and the binding rule in `PROJECT_SPEC.md` |
| `Country`/`Source` restricted to non-production uses | §1, §6 |
