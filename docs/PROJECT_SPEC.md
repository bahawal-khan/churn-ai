# ChurnAI — Project Specification (PROJECT_SPEC.md)

**Status:** Specification only. No implementation has started.
**Owner:** Bahawal Khan
**Related documents:** `ML_SPEC.md`, `BACKEND_SPEC.md`, `FRONTEND_SPEC.md`, `DATABASE_SPEC.md`, `DEPLOYMENT.md`, `API.md`

This document is the source of truth for the ChurnAI platform. All later implementation phases must conform to it. Any change to scope, architecture, or data strategy must be reflected here first, then propagated to the supporting specs.

### Binding Cross-Cutting Rules (apply everywhere in this document set)

- **No hard-coded values, anywhere.** No prediction, churn probability, risk level, SHAP value, dashboard KPI, chart data point, or "production metric" is ever hard-coded, templated, or simulated in the application. Every number the user sees is computed at request time from real stored data or a real model inference call. Empty states show an honest "no data yet" message with a next action — never a plausible-looking fake number.
- **`Country`/`Source` is never a production model feature.** It exists solely for EDA, stratified sampling, dataset provenance/labeling, and offline research experiments (§3, §37). No model that is activated for real predictions — baseline or company-specific — is trained with `Country`/`Source` as an input feature. This is enforced structurally in the preprocessing pipeline (`ML_SPEC.md §1, §5`), not just as a convention.
- **Synthetic data is not evidence of real-world accuracy.** The synthetic Pakistani and Indian datasets exist to make the benchmark model's development data more diverse and to exercise the pipeline against non-US-shaped data. They are not a validation study, they do not demonstrate that the model is accurate for real Pakistani or Indian customers, and the product never claims otherwise (§3.1, §3.6).
- **ANN vs. baselines is decided by evidence, not assumption.** Every phase that evaluates models must present the full comparison table (Logistic Regression, Random Forest, Gradient Boosting, ANN) side by side; the "best" model is whichever wins on the agreed metrics, and it is entirely acceptable — expected, even — for a baseline to outperform the ANN.

---

## 1. Product Goal

ChurnAI is an AI-powered customer churn prediction and retention intelligence platform for businesses (initially subscription/telecom-style businesses, generalizable to any recurring-revenue business with customer-level data).

Core capabilities:

1. Understand churn risk at the portfolio level (dashboard/analytics).
2. Upload customer data and validate its quality before use.
3. Train a company-specific churn model when historical churn labels exist.
4. Predict churn probability for a single customer or a batch (CSV).
5. Classify customers into Low / Medium / High risk.
6. Explain *why* a customer is predicted to churn (SHAP, global and local).
7. Analyze churn patterns (drivers, trends, segments).
8. Download prediction results.
9. Maintain a history of uploads, trained models, and predictions.

Non-goal (V1): ChurnAI does not claim a single model that is universally accurate across countries/industries out of the box. It ships with a baseline model trained on benchmark + synthetic data, and its primary product value is letting a company train **its own** model on **its own** historical data.

The product must read as a real SaaS analytics product — consistent design system, real empty/loading/error states, no placeholder numbers presented as if real.

---

## 2. Source Materials Audited

### 2.1 Dataset: IBM Telco Customer Churn (provided CSV)

Actual inspection results (not assumed):

- Shape: **7,043 rows × 33 columns**.
- Columns: `CustomerID, Count, Country, State, City, Zip Code, Lat Long, Latitude, Longitude, Gender, Senior Citizen, Partner, Dependents, Tenure Months, Phone Service, Multiple Lines, Internet Service, Online Security, Online Backup, Device Protection, Tech Support, Streaming TV, Streaming Movies, Contract, Paperless Billing, Payment Method, Monthly Charges, Total Charges, Churn Label, Churn Value, Churn Score, CLTV, Churn Reason`.
- `Country` = `United States` (constant), `State` = `California` (constant) for all 7,043 rows → both are zero-variance and must be dropped for modeling.
- `Total Charges` is stored as **string**, not numeric. 11 rows fail numeric coercion — all 11 have `Tenure Months == 0` (brand-new customers with blank/whitespace Total Charges). Must be coerced with `pd.to_numeric(errors="coerce")` and the resulting 11 NaNs imputed as `0` (consistent with zero tenure).
- No missing values in any column **except** `Churn Reason`, which is null for 5,174 rows (all the non-churned customers — the column is only populated when `Churn Label == "Yes"`). This is expected structurally, not a data quality defect.
- Target: `Churn Label` (Yes/No) and `Churn Value` (1/0) are redundant — use `Churn Value` as the canonical target and drop `Churn Label` before modeling (keep it only for display/EDA).
- Class balance: **73.46% No-churn / 26.54% Churn** (1,869 churned / 5,174 retained). Moderate imbalance — not extreme, but must be handled (see §12 / ML_SPEC).
- Zero duplicate rows; zero duplicate `CustomerID`.
- **Leakage risk columns identified:** `Churn Score` (an IBM-precomputed churn propensity score) and `Churn Reason` (only populated for churners) are direct target leakage and **must be excluded from model features**. `CLTV` is borderline — it is a downstream business metric computed independently of churn, not derived from the label, so it may be used as a feature but must be reviewed in EDA for correlation with the target.
- Identifier/geo columns not useful as raw model features: `CustomerID`, `Count` (always 1), `Zip Code`, `Lat Long`, `Latitude`, `Longitude`, `City` (high cardinality). These are retained in the dataset for record-keeping/joins but excluded from the model's feature set in the baseline pipeline. City-level aggregation may be explored in EDA as an optional engineered feature, not a required one.
- Categorical cardinalities observed directly: `Gender` (2), `Senior Citizen` (2, stored as Yes/No not 0/1), `Partner` (2), `Dependents` (2), `Phone Service` (2), `Multiple Lines` (3: Yes/No/No phone service), `Internet Service` (3: DSL/Fiber optic/No), `Online Security`/`Online Backup`/`Device Protection`/`Tech Support`/`Streaming TV`/`Streaming Movies` (3 each: Yes/No/No internet service), `Contract` (3: Month-to-month/One year/Two year), `Paperless Billing` (2), `Payment Method` (4: Mailed check/Electronic check/Bank transfer (automatic)/Credit card (automatic)).

This audited structure is binding — the synthetic data generators (§3) and the preprocessing pipeline (`ML_SPEC.md`) must conform to this exact schema (minus dropped columns, plus the added `Country`/`Source` provenance column described in §3.0/§3.1, which is metadata only and is never a model input feature).

### 2.2 UI/UX Reference Image

Reviewed. It is a dark-themed SaaS analytics dashboard with: sidebar navigation (Dashboard, Predictions, Upload Data, Train Model, Customers, Analytics, Reports, Model Management, Settings, Help & Support), top KPI cards, churn risk donut, churn trend line chart, SHAP-driven "Top Churn Drivers" bar list, recent predictions table, risk-by-segment radar chart, recent uploads panel, and dedicated Upload → Single Prediction → SHAP Force Plot → Batch Prediction module row, plus a mobile-responsive preview. This is treated as **visual inspiration and an information-architecture reference**, not a pixel-exact spec. §19 and `FRONTEND_SPEC.md` define the improved, implementation-ready UI/UX derived from it (adding light mode, onboarding, accessibility, and real empty/error/loading states that the reference image does not show).

---

## 3. Dataset Strategy

### 3.0 Data Category Definitions (binding terminology)

Three distinct categories of data exist in ChurnAI, and they are never conflated in code, UI copy, or documentation:

| Category | What it is | Where it lives | Used for |
|---|---|---|---|
| **Development / benchmark data** | The IBM Telco dataset (§2.1) — real, public, US-only | `dataset.source_type = 'dev_benchmark_ibm'` | Building and validating the pipeline; part of the shared baseline model's training data |
| **Synthetic regional data** | Generated Pakistan/India records (§3.2–3.5) | `dataset.source_type = 'dev_synthetic_pakistan' / 'dev_synthetic_india'` | Adding feature/behavior diversity to the shared baseline model's training data during development; **never** presented as real observed customers |
| **Real company production data** | A company's own historical/current customer data, uploaded via `/upload` or `/train` | `dataset.source_type = 'company_upload'` | Company-specific model training (§16) and company-specific predictions; fully isolated per organization (`DATABASE_SPEC.md §6`) |

The shared **baseline/global model** is trained only on development + synthetic regional data (categories 1 and 2) and is clearly labeled as such everywhere it is surfaced. A **company-specific model** is trained only on that company's own real production data (category 3) — development and synthetic data are never mixed into a company-specific training run, and one company's production data is never mixed into another company's model or into the shared baseline.

### 3.1 Composition

The **development/benchmarking dataset** is a combination of three sources, clearly labeled by a `Source` (or `Country`) column at all times:

| Source | Records | Nature |
|---|---|---|
| IBM Telco (California, USA) | 7,043 | Real, public benchmark dataset |
| Synthetic — Pakistan | 7,000 | Synthetic, rule-based generation |
| Synthetic — India | 7,000 | Synthetic, rule-based generation |
| **Total** | **~21,043** | Combined development dataset |

This is described everywhere in the product and docs as **"IBM benchmark data + synthetic Pakistan/India development data."** It is never described as "21,000 real customers" or as evidence of real-world Pakistan/India accuracy. A visible disclaimer string is stored as a constant and surfaced in the UI (Model Management, Dashboard "Current Model" panel, About page):

> "This model is trained on the IBM Telco benchmark dataset combined with synthetic Pakistani and Indian customer data generated for development and demonstration purposes. It is not a validated real-world model for any specific country or market, and the synthetic Pakistani/Indian data does not prove real-world accuracy for customers in those countries. For production use, a company should train a company-specific model on its own historical data via the Train Model feature."

`Country`/`Source` is carried as metadata on every record for exactly the uses in §3.0's table (EDA, stratified sampling, provenance, controlled offline experiments) — it is **never** included in the feature set of any model that is trained for real predictions. This restriction is structural: the preprocessing `ColumnTransformer` (`ML_SPEC.md §5`) simply does not include `Country`/`Source` among its numerical or categorical input columns for any production training run. Any research notebook that experiments with `Country`/`Source` as a feature (e.g., to measure how much regional signal exists) is clearly marked as an offline experiment and its output is never promoted to an active model.

### 3.2 Synthetic Data Generation Principles (both countries)

1. **Schema-conformant.** Synthetic records use the same modeling schema as the cleaned IBM data (`Gender, Senior Citizen, Partner, Dependents, Tenure Months, Phone Service, Multiple Lines, Internet Service, Online Security, Online Backup, Device Protection, Tech Support, Streaming TV, Streaming Movies, Contract, Paperless Billing, Payment Method, Monthly Charges, Total Charges, Churn Value`), plus a `Country`/`Source` column and a `CustomerID` with a country-specific prefix (`PK-xxxxx`, `IN-xxxxx`) to keep provenance traceable and to prevent accidental merge collisions with IBM IDs.
2. **Not row duplication.** Records are generated from **customer archetypes / segments**, each with its own feature distributions, not by copying and jittering IBM rows.
3. **Business-rule-driven labels with controlled noise**, not random labels (see §3.4).
4. **Reproducible**: a fixed random seed (`RANDOM_SEED = 42`, defined once in `ml/config.py`) drives every distribution draw and noise injection. Re-running the generator produces byte-identical output.
5. **Documented generation rules** live in `ml/data_generation/pakistan_generator.py` and `ml/data_generation/india_generator.py` (Phase 1), each with a module docstring describing every archetype, its target share of records, and its distributional assumptions.

### 3.3 Pakistan Synthetic Data — Segment Design (7,000 records)

Customer archetypes (illustrative proportions, tunable at generation time, must sum to 100%):

| Archetype | Share | Characteristics |
|---|---|---|
| Urban high-income postpaid-like | 15% | Long tenure skew, two-year contracts, fiber-equivalent internet, low churn base rate |
| Urban middle-income | 25% | Mixed contract types, moderate tenure, moderate monthly spend |
| Urban low-income / price-sensitive | 15% | Month-to-month, DSL or no internet, high price sensitivity → higher churn base rate |
| Semi-urban family/shared plan | 15% | Higher `Dependents`/`Partner` = Yes rate, multiple lines, mid tenure |
| Rural / lower connectivity | 15% | Lower internet penetration, phone-only more common, shorter tenure |
| Young single urban (prepaid-like, high churn) | 15% | Short tenure, month-to-month, electronic payment, highest churn base rate |

Feature-generation notes:
- Tenure, monthly charges, and total charges are drawn from **archetype-specific distributions** (e.g., truncated normal / gamma) rather than one global distribution, so the combined population has realistic overlap and heterogeneity instead of a single clean cluster.
- `Total Charges` is derived from tenure × average monthly charge with added noise, then rounded — not computed as a perfectly deterministic product (to mirror real-world billing variance seen in the IBM data).
- Payment method distribution is skewed toward Electronic check / Mailed check archetype-appropriately (documented assumption, not claimed as real market research).
- `Contract`, `Internet Service`, and add-on service flags (`Online Security`, `Tech Support`, etc.) are sampled with archetype-specific conditional probabilities (e.g., rural archetype has near-zero streaming add-ons).

### 3.4 India Synthetic Data — Segment Design (7,000 records)

Same methodology, distinct archetypes:

| Archetype | Share |
|---|---|
| Metro high-income | 15% |
| Metro middle-income | 25% |
| Metro price-sensitive | 15% |
| Semi-urban family plan | 15% |
| Rural / low connectivity | 15% |
| Young urban single, high-churn segment | 15% |

Same generation discipline: archetype-specific distributions, conditional service/contract sampling, no row duplication.

### 3.5 Synthetic Churn Label Generation (both countries) — Rule-Based, Not Random

Churn is generated as a **latent propensity score → probability → sampled Bernoulli label**, so the relationship between features and churn is real (learnable) but not deterministic (noisy), matching real-world churn behavior:

```
churn_logit =
      w1 * (contract_is_month_to_month)
    + w2 * (normalized_monthly_charges)
    - w3 * (normalized_tenure)
    + w4 * (no_tech_support)
    + w5 * (electronic_check_payment)
    - w6 * (has_dependents_or_partner)
    + w7 * (archetype_base_churn_offset)
    + epsilon   # Gaussian noise, mean 0

churn_probability = sigmoid(churn_logit)
churn_label = Bernoulli(churn_probability)
```

Requirements on this mechanism:
- Weights (`w1..w7`) are fixed constants documented in the generator module, chosen so the **direction** of each effect matches known churn intuition from the IBM EDA (month-to-month, high charges, low tenure, no tech support, electronic check → higher churn; long tenure, family ties, long contracts → lower churn) — this keeps the synthetic relationships plausible without claiming empirical grounding.
- `epsilon` noise is large enough that churn is **not perfectly separable** by any single feature or simple rule — there must be overlapping distributions and borderline/ambiguous cases in the generated data (validated in Phase 1/2 EDA by checking that no single feature achieves near-1.0 AUC alone).
- Per-archetype base churn rates are set so the **overall** synthetic churn rate lands in a realistic band (roughly 20–35%, i.e., broadly consistent with the IBM base rate of 26.5%) while still varying meaningfully by archetype and country — this produces realistic class imbalance, not an artificially balanced 50/50 dataset.
- The generator must be validated (Phase 1 deliverable) with: churn-rate-by-archetype table, churn-rate-by-country table, and a quick logistic-regression sanity check confirming expected feature signs and an AUC well below 1.0 (target ballpark 0.75–0.90, i.e., learnable but not trivial).

### 3.6 Data Integrity Rule (binding)

- Synthetic Pakistani and Indian records are **always** labeled as synthetic in the database (`source_type = 'synthetic'`), in every export, and in every UI surface that displays dataset composition.
- The product never states or implies these are real observed customers.
- Any exported/reported dataset statistic must show the IBM / Pakistan-synthetic / India-synthetic breakdown, not a blended "customers" count without provenance.

---

## 4. EDA Plan

Full detail in `ML_SPEC.md §2`. Summary of required coverage: dataset shape, feature types, numerical distributions, categorical distributions, missing values, duplicates, outliers, cardinality, target distribution and class imbalance, source/country distribution, correlation analysis, feature–target relationships, identifier/leakage-risk column review (explicitly re-verifying `Churn Score`/`Churn Reason` exclusion), and distribution comparison across IBM vs. Pakistan-synthetic vs. India-synthetic. Required visuals: churn distribution, numerical histograms/boxplots, categorical churn-rate bar charts, correlation heatmap, churn-by-contract, churn-by-tenure, churn-by-payment-method, churn-by-monthly-charges, and a source/country comparison panel.

---

## 5. Data Quality Pipeline

Full detail in `ML_SPEC.md §3`. Summary: a `DataQualityValidator` service (built during Phase 2 and used identically for the development dataset and for every company upload in production) checks missing values, duplicates, invalid/impossible values (e.g., negative charges, tenure > plausible max), inconsistent category spellings, wrong dtypes, whitespace, malformed CSV structure, unexpected/missing columns, target column problems (missing, non-binary, single-class), high-cardinality columns, and identifier-like columns. Output is a structured, human-readable **Data Quality Report** (JSON for the API, rendered as a readable panel in the UI) with pass/warn/fail severity per check.

---

## 6. Feature Engineering

Full detail in `ML_SPEC.md §4`. Every engineered feature has a documented business/statistical rationale; no feature is added purely to inflate feature count. Candidates: tenure buckets, average monthly value per active service, total active add-on service count, "has any streaming" / "has any protection" indicators, contract-risk flag, payment-risk flag, and a `has_internet` normalization flag to correctly interpret the "No internet service" categorical value across 6 related columns. All engineering is implemented as a versioned, reproducible pipeline step (never manual/ad hoc), fit only on training data where any statistic (e.g., mean) is involved.

---

## 7. Preprocessing

Full detail in `ML_SPEC.md §5`. A single `sklearn.Pipeline` / `ColumnTransformer` handles numerical imputation (median), categorical imputation (most-frequent or explicit "Unknown"), categorical encoding (one-hot for low-cardinality nominal features), and scaling (StandardScaler for numerical features feeding the ANN and Logistic Regression baseline; tree-based baselines may consume unscaled data through a parallel branch). The fitted pipeline is serialized alongside each trained model so inference uses the exact training-time transformation. Fit strictly on the training split only.

---

## 8. Train / Validation / Test Strategy

Full detail in `ML_SPEC.md §6`. Stratified split on `Churn Value`: 70% train / 15% validation / 15% test, fixed seed. The held-out test set is touched only once, for final reporting. For the combined development dataset, stratification also considers `Source` (IBM/PK/IN) via a two-key stratification (target × source) so all three sources are proportionally represented in every split — this prevents, e.g., the test set from being accidentally IBM-only or synthetic-only.

---

## 9. Baseline Models

Full detail in `ML_SPEC.md §7`. Logistic Regression (interpretable baseline) and Random Forest are mandatory baselines; Gradient Boosting (XGBoost or scikit-learn's `HistGradientBoostingClassifier` if XGBoost is unavailable on the deployment target) is included where deployment size/constraints permit. All baselines and the ANN are compared on the same validation metrics table — ANN is not assumed to win.

---

## 10. ANN Model

Full detail in `ML_SPEC.md §8`. Feed-forward MLP sized for tabular data (not deep): input layer sized to the engineered feature count, 2 hidden layers (e.g., 64 → 32 units) with ReLU, Dropout between layers, sigmoid output for binary churn probability, binary cross-entropy loss, Adam optimizer, small fixed learning rate with `ReduceLROnPlateau`, `EarlyStopping` on validation loss/PR-AUC, batch size and epoch ranges documented with the actual chosen values recorded once training runs (Phase 5).

---

## 11. Overfitting / Underfitting Strategy

Full detail in `ML_SPEC.md §9`. Training/validation loss and metric curves are logged and plotted every run; a documented rule set flags overfitting (validation loss rising while train loss falls), underfitting (both plateau high), and instability (validation metric variance across epochs/folds). Regularization techniques (Dropout, L2, EarlyStopping, ReduceLROnPlateau, BatchNorm) are applied selectively and justified per use, not all at once by default.

---

## 12. Training Stability (Vanishing/Exploding Gradients)

Full detail in `ML_SPEC.md §10`. Mitigations: ReLU activations with He initialization, mandatory feature scaling before the ANN, a conservative learning rate with monitoring, optional gradient-norm logging during Phase 6 experimentation, optional gradient clipping if instability is observed, and a shallow network by design to avoid unnecessary depth.

---

## 13. Class Imbalance Strategy

Full detail in `ML_SPEC.md §11`. Default approach: `class_weight="balanced"` (baselines) / weighted loss (ANN) plus threshold tuning on validation PR-AUC, decided empirically rather than defaulting to SMOTE. SMOTE is evaluated as an experiment during Phase 4/6 and adopted only if it measurably improves validation recall/PR-AUC without materially hurting precision — the decision and its evidence are recorded in `ML_SPEC.md` once experiments run.

---

## 14. Model Evaluation

Full detail in `ML_SPEC.md §12`. Metrics: Accuracy, Precision, Recall, F1, ROC-AUC, PR-AUC, confusion matrix, full classification report, and calibration curve. Recall, F1, and PR-AUC are treated as primary for churn (missing a churner — false negative — is costlier than a false positive retention outreach). Threshold selection is done on the validation set by maximizing F1 (or a business-configurable recall/precision trade-off), then locked and evaluated once on test.

---

## 15. SHAP Explainability

Full detail in `ML_SPEC.md §13`. SHAP values are computed from the actual trained model at inference time — never hard-coded or templated text presented as if model-derived. Global explanations (mean |SHAP| per feature, summary plot data) power the Dashboard's "Top Churn Drivers" and Analytics pages. Local explanations (per-customer SHAP values, force-plot data) power the single-prediction "Why is this customer at risk" panel. All explanation surfaces carry a visible note: **"This shows what the model learned from patterns in the data — it identifies correlation, not proven causation."**

---

## 16. Company-Specific Training

Core differentiating feature. Required workflow, enforced by the backend state machine (`DATABASE_SPEC.md §2.8` `training_jobs` entity):

```
Upload → Validate → Preview → Data Quality Report → Select/Confirm Target Column
   → Preprocess → Train → Evaluate → Review Metrics → Activate Model → Predict
```

Rules:
- Historical churn labels (a binary target column) are **required** to train. If the uploaded dataset has no identifiable/selectable binary target column, training is blocked with a clear explanation: *"Training requires historical outcomes (which customers churned) so the model can learn patterns. Your file doesn't appear to include a churn/outcome column. You can still use the baseline model for predictions, or re-upload a file that includes historical churn results."*
- A trained company model is versioned, stored with its metrics and the preprocessing pipeline it was fit with, and can be activated/deactivated without deleting history.
- Company data is isolated per account/organization — never pooled into another company's training run or into the global benchmark dataset (§3.0), and never pooled into the shared baseline model's development data.
- **Predictions made against a company-specific model must use the same feature schema that model was trained on.** Once a company model is active, both single-prediction input and batch-prediction CSV columns are validated against that model's stored `feature_schema` (recorded at training time, `DATABASE_SPEC.md §2.7`, `models.feature_schema`) before inference runs. A batch file with missing required columns is rejected per-row-or-whole-file (whole-file for missing required columns; per-row for individual bad values) with a specific `SCHEMA_MISMATCH` error explaining exactly which columns are missing or mismatched — it is never silently coerced or guessed.

### 16.1 Schema Mapping & Compatibility (explicit process — no "magic CSV")

ChurnAI does **not** claim that an arbitrary company CSV can be dropped in and automatically produce reliable churn predictions. Every upload — for training or for prediction — goes through an explicit, visible mapping step:

1. **Detection.** On upload, the backend inspects the CSV's columns and attempts to auto-match them against the known schema contract (`ML_SPEC.md §1`) by column name (case/whitespace-insensitive) and, for ambiguous cases, by value-pattern heuristics (e.g., a two-value Yes/No column vs. a numeric column).
2. **Confirmation, not silent assumption.** The Preview step (§16 workflow) shows the user exactly which uploaded columns were matched to which schema fields, which schema fields could not be found, and which uploaded columns were left unmapped/unused. The user must confirm or manually correct this mapping before the workflow proceeds — auto-detection is a convenience, not an unreviewed assumption.
3. **Target column selection** is a separate, explicit step from feature mapping (already required by the workflow diagram above) — the user picks which column represents the historical churn outcome; ChurnAI never guesses this silently.
4. **Compatibility floor.** Training requires that a minimum viable subset of the schema contract's fields be present and mapped (the exact minimum required/optional field list is finalized and pinned in `ML_SPEC.md §1` once Phase 3 preprocessing is built, since it depends on which engineered features can gracefully degrade vs. which cannot). If a file falls short of that floor, training is blocked with a specific, itemized explanation of what's missing — the same honesty standard as the missing-labels case above.
5. **Prediction-time enforcement.** As stated above, any prediction request (single or batch) against a given model is validated against that exact model's recorded feature schema — a model never silently accepts a differently-shaped input and guesses.

This mapping/compatibility step is a core, required part of the Upload → Validate → Preview workflow (§16) for every company upload, not an optional nicety — it is what makes the "no hard-coded, no guessed" guarantee actually true in practice.

---

## 17. Prediction

**A. Individual prediction** — form-driven single-customer input → churn probability, predicted class, risk level, top contributing factors (ranked SHAP), full local SHAP explanation view.

**B. Batch prediction** — CSV upload, ingested through the same dataset pipeline as training uploads (creating a `datasets` row and per-row `customers` records — matched by `external_customer_id` when it identifies an existing org customer, otherwise created — `DATABASE_SPEC.md §2.5–§2.6`), then validated through the same Data Quality pipeline as training uploads, minus the target-column requirement → per-row probability/class/risk level, summary counts (total, low/medium/high risk, predicted churners), downloadable results CSV including original columns + `churn_probability`, `predicted_class`, `risk_level`. Because each batch-predicted row is linked to a stored `customer` record, batch predictions always appear in that customer's history (§ Customers list/detail, `FRONTEND_SPEC.md §13`) — unlike form-driven individual predictions (A), which are not tied to a stored customer unless the user is predicting against an existing customer record.

All displayed values are computed from the active model at request time. No hard-coded or mocked prediction values anywhere in the product, including demo/empty states (empty states show "no predictions yet" + a call to action, never fake numbers).

---

## 18. Risk System

Initial fixed thresholds on predicted probability `p`:

| Risk Level | Range |
|---|---|
| Low | `p < 0.30` |
| Medium | `0.30 ≤ p < 0.60` |
| High | `p ≥ 0.60` |

These are documented as an initial, reasonable default — not claimed as universally optimal. Stored as the `risk_thresholds` JSON column on each `models` row (`DATABASE_SPEC.md §2.7`) so thresholds are editable per model/organization in a future phase without a schema migration. V1 UI exposes them as read-only in Settings with a "coming soon: customize thresholds" note; making them editable is explicitly Future Scope (§ Future Scope below), not V1.

---

## 19. Dashboard

The dashboard must let a user answer, at a glance: how many customers do I have, how many are at risk, what's my predicted churn rate, who are the highest-risk customers, why are customers churning, what patterns exist, and what should I look at next.

Required components: KPI cards (Total Customers, At Risk, Predicted Churn Rate, High Risk Customers, Avg Churn Probability, model status), churn risk distribution (donut), churn trend over time (line — computed from actual stored prediction history, not synthetic-looking mock trend data once real predictions exist; before that, an honest empty state), top churn drivers (global SHAP bar list), recent predictions table (sortable, paginated, linking to customer detail), risk-by-segment view (radar or bar, computed from real segment cuts, e.g., contract type / senior citizen / dependents — chosen because they are meaningful cuts in the actual schema, not because they mirror the reference image's arbitrary categories), recent uploads panel, current active model card (name, version, AUC, trained-on date), filters/search/sort/pagination on all tables.

---

## 20. UI / UX

Full detail in `FRONTEND_SPEC.md`. The provided reference image is used as an information-architecture and visual-density reference; ChurnAI's actual design system defines its own token set (colors, spacing, typography) rather than copying the image pixel-for-pixel, and adds what the image lacks: light mode, accessible contrast/focus states, onboarding, and real empty/loading/error/success states. Pages required: landing, auth (login/signup/forgot/reset), dashboard, upload, training, prediction (single + batch), customer list + customer detail, analytics, model management, reports, settings, help/FAQ. Interaction requirements: skeleton loaders, empty states, error states, success states, confirmation dialogs for destructive/high-impact actions (deleting a dataset, deactivating a model), toast notifications, tooltips explaining domain terms inline, and restrained, professional micro-interactions (no gratuitous animation).

---

## 21. New User Guidance

A first-time user must be able to use the product without external documentation. V1 includes: a short guided walkthrough on first dashboard visit (dismissible, replayable from Help), contextual tooltips on domain terms (churn, probability, risk level, SHAP, company-specific training) the first time each appears, empty states that explain the next action instead of showing blank space, and a Help & FAQ page covering: what churn means, how to upload data, what data is required, what the probability number means, what each risk level means, what SHAP means, what company-specific training requires and why labels are mandatory.

---

## 22. Authentication

Full detail in `BACKEND_SPEC.md §4`. Sign up, login, logout, forgot password, reset password. Email: required, valid-format, uniqueness enforced with a clear "an account with this email already exists" message (no user enumeration beyond that acceptable UX trade-off — see Security §, rate limiting mitigates abuse). Password: minimum 8 characters, at least one uppercase, one lowercase, one number, one special character, shown live via a strength indicator; confirm-password field; show/hide toggle. Passwords are always hashed (bcrypt/argon2 — final choice pinned in `BACKEND_SPEC.md`), never stored or logged in plaintext. Session persistence via secure, HttpOnly cookies carrying a signed session token (or JWT access + refresh pair — decision and rationale pinned in `BACKEND_SPEC.md §4`); an authenticated user who reloads or revisits stays logged in and is redirected away from `/login`/`/signup` to `/dashboard`; dashboard and all data routes are protected server-side, not just hidden client-side.

---

## 23. File Handling

Full detail in `BACKEND_SPEC.md §6`. Every upload is validated for: MIME type and extension (`.csv` only in V1), maximum size (documented limit, e.g., 25 MB, chosen to be safe for PythonAnywhere free tier), safe filename handling (server generates its own storage filename; the original filename is stored as metadata only, never used as a path), encoding detection/handling (UTF-8 required, with a clear error if not), malformed-CSV detection (unparseable rows, ragged rows), duplicate/missing/unexpected column detection, and empty-file detection. Internal storage paths and stack traces are never exposed to the client.

---

## 24. Error Handling

Full detail in `BACKEND_SPEC.md §7`. Standard error envelope for every API error: `{ "error": { "code": "...", "message": "...", "details": {...optional...} } }` with an appropriate HTTP status (400/401/403/404/409/413/422/429/500). Every category listed in the brief (auth failures, invalid data/CSV, missing columns, training failure, prediction failure, DB errors, network errors, unauthorized/expired session, unexpected server errors) maps to a specific code + user-facing message + safe server-side log entry (full detail logged server-side, sanitized message returned to client) + retry/recovery affordance in the UI where applicable (e.g., "re-upload file", "try again", "log in again").

---

## 25. Database

Full detail in `DATABASE_SPEC.md`. SQLite for V1, explicitly designed for a future PostgreSQL migration (standard SQL types, no SQLite-only features, migrations managed via Alembic from day one). Entities: `users`, `organizations` (light-weight, one org per user in V1 to keep company-data isolation clean without building multi-tenant UI yet), `datasets` (uploads, including dev dataset ingestion), `customers` (rows belonging to a dataset), `models` (trained model versions, baseline or company-specific, with metrics + artifact path), `training_jobs` (state machine per §16), `predictions` (individual + batch, linked to the model version used), `explanations` (SHAP values per prediction, global summaries per model), `audit_logs` (auth events, uploads, training runs, model activation, deletions).

---

## 26. Backend

Full detail in `BACKEND_SPEC.md`. Python + Flask, layered architecture: `routes/` (thin HTTP layer) → `services/` (business logic) → `ml/` (model, preprocessing, SHAP) and `db/` (models/queries) as dependencies of services, plus `validation/`, `auth/`, `config.py`, `errors/`. No business logic in route handlers; no direct DB/ML calls from routes.

---

## 27. Frontend

Full detail in `FRONTEND_SPEC.md`. Next.js (App Router) + TypeScript + Tailwind CSS + a small reusable component library (shadcn/ui-style primitives) + Recharts for charts + Framer Motion for restrained micro-interactions. All backend calls go through a single typed API client module (`lib/api/client.ts` and per-resource modules), never `fetch` scattered inside components.

---

## 28. Deployment

Full detail in `DEPLOYMENT.md`. Frontend → Vercel (free tier). Backend → PythonAnywhere (free tier). Database → SQLite file on PythonAnywhere's persistent storage, with a documented, tested path to swap in PostgreSQL later purely via `DATABASE_URL` + Alembic, no code changes. No paid infrastructure or card required for V1. CORS restricted to the deployed frontend origin (+ localhost during development). Model artifacts stored on PythonAnywhere's persistent storage under the top-level `ml/artifacts/` directory (§35 — a sibling of `backend/`, not nested inside it, since `ml/` is a shared package imported by the backend's `services/` layer, `BACKEND_SPEC.md §1`), not served statically; downloadable prediction CSVs are generated on demand and streamed, not persisted indefinitely. Long-running work (training, large batch prediction) uses an async job-status pattern at the API level (`BACKEND_SPEC.md §3`), but the specific PythonAnywhere execution mechanism behind that pattern (scheduled task, always-on task, or simple synchronous processing within free-tier request limits) is intentionally **not pinned here** — it is chosen during Phase 8 implementation once the actual free-tier account's capabilities are verified, keeping the architecture flexible around whatever the simplest supported option turns out to be.

---

## 29. Footer

```
ChurnAI
Predict. Understand. Retain.

Developed by: Bahawal Khan
GitHub:   [GITHUB_URL — to be supplied by Bahawal]
LinkedIn: [LINKEDIN_URL — to be supplied by Bahawal]
Email:    [EMAIL_ADDRESS — to be supplied by Bahawal]

About · Features · FAQ · Privacy · Terms · Contact
```
Placeholders are intentional — real URLs/email must be supplied before Phase 10 (frontend) implementation; nothing is invented.

---

## 30. Testing Strategy

Full detail across `BACKEND_SPEC.md §8` and `FRONTEND_SPEC.md §9`. Coverage required for: data validation rules, preprocessing pipeline determinism, model inference (shape/range checks on output probabilities), SHAP output shape/consistency, auth flows (signup/login/reset, invalid credentials, expired session), API endpoints (happy path + documented error cases per `API.md`), database layer (CRUD + constraints), file upload (valid/invalid/malformed/oversized files), frontend components (key interactive components + protected-route redirect behavior), and error-handling paths. Test types: backend unit tests (pytest) for services/ML/db, backend integration tests for API routes, frontend component tests (React Testing Library) for critical flows, and a manual QA checklist for full user journeys before each deployment (Phase 11/12).

---

## 31. Security

Full detail in `BACKEND_SPEC.md §9`. Password hashing (bcrypt/argon2), authenticated + authorized routes (ownership checks so one user/org can never read another's datasets/models/predictions), input validation on every endpoint (schema-based, e.g., Pydantic/Marshmallow), secure file handling (§23), environment-variable-based configuration with `.env` never committed (enforced via `.gitignore` from the very first commit, prior to Phase 1 of the implementation roadmap), CORS locked to known origins, secure session/token handling (HttpOnly, Secure, SameSite cookies or short-lived JWT + refresh with rotation — decision pinned in `BACKEND_SPEC.md`), sanitized error messages (no stack traces or internal paths returned to clients), and basic rate limiting on auth endpoints and prediction/training endpoints (practical, in-process limiter for V1 given free-tier hosting; documented upgrade path to a shared limiter if scaled).

---

## 32. Documentation Structure

```
docs/
├── PROJECT_SPEC.md      ← this document
├── ML_SPEC.md            ← EDA, data quality, feature engineering, preprocessing,
│                            splits, baselines, ANN, regularization, evaluation, SHAP
├── BACKEND_SPEC.md       ← Flask architecture, routes/services, auth, file handling,
│                            error handling, security, testing
├── FRONTEND_SPEC.md      ← Next.js pages, components, design system, UI states,
│                            onboarding, testing
├── DATABASE_SPEC.md      ← SQLite schema, entities, relationships, migration plan
├── DEPLOYMENT.md         ← Vercel + PythonAnywhere deployment, env vars, CORS,
│                            build process, model/file storage
└── API.md                ← Full REST API contract (endpoints, request/response
                             shapes, error codes)
```

---

## 33. Phased Development Plan

The specification set (this document + its six companions) is the current, pre-Phase-1 deliverable. Once approved, implementation follows this exact roadmap:

| Phase | Scope |
|---|---|
| 1 | Dataset Foundation — IBM Telco audit + synthetic Pakistan/India data generation |
| 2 | EDA & Data Quality — exploratory analysis, `DataQualityValidator` pipeline |
| 3 | Feature Engineering & Preprocessing — engineered features, `ColumnTransformer` pipeline |
| 4 | Baseline ML Models — Logistic Regression, Random Forest, Gradient Boosting |
| 5 | ANN — initial architecture, training loop |
| 6 | ANN Optimization & Evaluation — regularization, training-stability work, threshold tuning, full metric suite |
| 7 | SHAP Explainability — global + local explanations |
| 8 | Flask Backend — routes/services skeleton |
| 9 | Database & Authentication — SQLite schema/migrations, auth flows |
| 10 | Next.js Frontend |
| 11 | Full Integration & Testing — frontend ↔ backend ↔ ML integration, backend/frontend test suites, security hardening |
| 12 | Deployment (Vercel + PythonAnywhere) |

Per `CLAUDE.md`/`skills.md`: each phase is scoped, confirmed with the user before starting, kept in small reviewable commits, and does not scaffold future phases early. No dependencies are added before the phase that needs them.

---

## 34. Final Architecture

```
                         ┌────────────────────────┐
                         │   Next.js Frontend      │
                         │   (Vercel)               │
                         │  - App Router, TS, Tailwind
                         │  - Recharts, Framer Motion
                         └───────────┬─────────────┘
                                     │ HTTPS / REST (JSON)
                                     ▼
                         ┌────────────────────────┐
                         │   Flask Backend          │
                         │   (PythonAnywhere)        │
                         │  routes → services → (ml, db)
                         │  auth, validation, errors │
                         └───────┬───────────┬──────┘
                                 │           │
                     ┌───────────▼───┐   ┌───▼────────────┐
                     │ SQLite DB      │   │ ML Layer        │
                     │ (users, data,  │   │ preprocessing,  │
                     │  models,       │   │ baselines, ANN, │
                     │  predictions,  │   │ SHAP, model     │
                     │  audit logs)   │   │ artifacts on disk│
                     └────────────────┘   └─────────────────┘
```

## 35. Repository Structure

```
churnai/
├── CLAUDE.md
├── skills.md
├── docs/
│   ├── PROJECT_SPEC.md
│   ├── ML_SPEC.md
│   ├── BACKEND_SPEC.md
│   ├── FRONTEND_SPEC.md
│   ├── DATABASE_SPEC.md
│   ├── DEPLOYMENT.md
│   └── API.md
├── data/
│   └── raw/                       (source datasets, e.g. the IBM Telco CSV — real/public,
│                                    small enough to commit for reproducibility; consumed by
│                                    ml/data_generation and ml/eda in Phase 1–2. Distinct from
│                                    ml/artifacts/, which holds trained model output, not input data)
├── backend/
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   ├── services/
│   ├── validation/
│   ├── auth/
│   ├── db/
│   │   ├── models.py
│   │   └── migrations/          (Alembic)
│   └── errors/
├── ml/
│   ├── config.py
│   ├── data_generation/
│   │   ├── pakistan_generator.py
│   │   └── india_generator.py
│   ├── eda/
│   ├── preprocessing/
│   ├── features/
│   ├── models/
│   │   ├── baselines.py
│   │   └── ann.py
│   ├── shap_explain/
│   └── artifacts/                (trained model files, not committed)
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/api/
│   └── styles/
└── tests/
    ├── backend/
    ├── ml/
    └── frontend/
```

## 36. Complete Feature List (V1)

- Auth: signup, login, logout, forgot/reset password, session persistence, protected routes
- Dataset upload (dev-dataset ingestion + company uploads) with validation and data-quality report
- Baseline model (IBM + synthetic PK/IN) available out of the box
- Company-specific model training workflow (upload → validate → preview → quality report → target selection → preprocess → train → evaluate → activate)
- Individual prediction with SHAP local explanation
- Batch prediction (CSV in → results + summary + downloadable CSV out)
- Configurable-in-schema, fixed-in-V1-UI risk thresholds (Low/Medium/High)
- Dashboard: KPIs, risk distribution, churn trend, top drivers, recent predictions, risk-by-segment, recent uploads, active model card
- Analytics page: deeper EDA-style breakdowns of the active dataset/model
- Customers list + customer detail (history of predictions for that customer)
- Model management: list model versions, metrics, activate/deactivate
- Reports: exportable summaries
- Settings: profile, (read-only V1) risk thresholds, org info
- Help & FAQ, onboarding walkthrough, contextual tooltips
- Light/dark mode
- Full error/empty/loading/success state coverage

## 37. ML Pipeline (Summary — see `ML_SPEC.md`)

Raw data → Data Quality validation → Cleaning (dtype fixes, leakage-column drop, geo/ID drop) → Feature engineering → Train/Val/Test stratified split → Preprocessing pipeline (impute/encode/scale), fit on train only → Baseline models (LogReg, RF, GBM) → ANN (with regularization + stability controls) → Evaluation (full metric suite, threshold tuning on validation) → Final test-set evaluation (once) → SHAP explainer built on the winning model → Model + pipeline + SHAP explainer serialized together as one versioned artifact.

## 38. ANN Training Strategy (Summary — see `ML_SPEC.md §8–10`)

Shallow MLP (2 hidden layers, Dropout, He-initialized ReLU, sigmoid output), Adam optimizer, weighted binary cross-entropy (to address class imbalance) or class-weighted training, EarlyStopping + ReduceLROnPlateau on validation loss/PR-AUC, batch size and epoch count tuned empirically and recorded once run, training/validation curves logged every run for overfitting/underfitting/instability review.

## 39. EDA Strategy (Summary — see §4 / `ML_SPEC.md §2`)

Structural audit (shape, types, missingness, duplicates, cardinality) → distribution analysis (numerical + categorical, per source) → target analysis (imbalance, churn rate by source) → relationship analysis (churn by contract/tenure/payment/charges, correlation heatmap) → leakage review (re-confirm `Churn Score`/`Churn Reason` exclusion) → cross-source comparison (IBM vs PK-synthetic vs IN-synthetic distributions) → written findings feeding directly into feature engineering decisions.

## 40. Feature Engineering Strategy (Summary — see §6 / `ML_SPEC.md §4`)

Only features with a documented rationale are added: tenure buckets (captures known non-linear churn-vs-tenure relationship seen in telecom data), active add-on service count and "has any protection/streaming" flags (captures engagement/stickiness), contract-risk and payment-risk flags (directly reflect the top churn drivers observed in the reference dataset/domain literature), `has_internet` normalization (correctly collapses the "No internet service" placeholder category across six dependent columns instead of treating it as an independent category in each).

## 41. Data Generation Strategy (Summary — see §3)

Archetype-based generation (not row duplication) for Pakistan and India, each archetype with its own feature distributions and base churn rate; churn labels generated via a documented logistic latent-propensity model with injected noise (not random or manually authored per row); fixed seed for reproducibility; validated post-generation via churn-rate-by-archetype tables and a sanity-check logistic regression (expected feature signs, AUC well below 1.0).

## 42. Authentication Architecture (Summary — see §22 / `BACKEND_SPEC.md §4`)

Hashed passwords (bcrypt/argon2), HttpOnly secure session cookie or short-lived JWT + rotating refresh token (final pick documented in `BACKEND_SPEC.md`), server-side route protection via an auth-required decorator/middleware, ownership checks on every data-access query, password policy + strength meter + confirm field + show/hide toggle on the client, duplicate-email handling with a clear message, forgot/reset password via a time-limited token (email delivery mechanism documented in `BACKEND_SPEC.md`, may be console/log-based in local dev if no email provider is configured yet).

## 43. Database Architecture (Summary — see §25 / `DATABASE_SPEC.md`)

SQLite V1, PostgreSQL-ready schema, Alembic migrations from day one, entities: `users`, `organizations`, `sessions`, `password_reset_tokens`, `datasets`, `customers`, `models` (including a `feature_schema` column used for prediction-time schema validation, §16.1), `training_jobs`, `predictions`, `explanations`, `audit_logs` — all tenant-scoped tables foreign-keyed to an owning `organization_id`, with composite indexes on the actual query patterns implied by `API.md`, enum-backed `CHECK` constraints on every status/type column, and a documented SQLite → PostgreSQL migration path (`DATABASE_SPEC.md §7–§8`).

## 44. Frontend Pages (Summary — see §20 / `FRONTEND_SPEC.md`)

Landing, Login, Signup, Forgot Password, Reset Password, Dashboard, Upload Data, Train Model, Predictions (Single), Predictions (Batch), Customers (list), Customer Detail, Analytics, Model Management, Reports, Settings, Help & FAQ, About, Privacy, Terms, Contact/Support.

## 45. Backend Modules (Summary — see §26 / `BACKEND_SPEC.md`)

`routes/` (auth, datasets, training, predictions, models, customers, analytics, reports, health), `services/` (mirroring each route group's business logic), `ml/` (shared with the ML layer — preprocessing, inference, SHAP), `db/` (SQLAlchemy models + queries), `validation/` (request/file schema validation), `auth/` (password hashing, token/session logic, decorators), `errors/` (error envelope + exception→response mapping), `config.py` (env-var driven settings per environment).

## 46. Deployment Architecture (Summary — see §28 / `DEPLOYMENT.md`)

Vercel (frontend, `NEXT_PUBLIC_API_BASE_URL` env var) + PythonAnywhere (Flask via WSGI, `.env`-driven config, SQLite file + `models/` artifact directory on persistent storage) + CORS allow-list of the Vercel domain(s) + localhost. No paid tier required.

## 47. Testing Strategy (Summary — see §30)

pytest for backend/ML unit + integration tests; React Testing Library for frontend component/flow tests; a manual pre-deployment QA checklist covering the full user journey (signup → upload → train → predict → dashboard → logout).

## 48. Security Strategy (Summary — see §31)

Hashing, authN/authZ with ownership checks, schema-based input validation, strict file validation, `.env`-only secrets (git-ignored), locked-down CORS, secure cookies/tokens, sanitized errors, basic rate limiting on sensitive endpoints.

## 49. V1 Scope

Everything in §36 Complete Feature List. Single organization per user (no multi-user org invites yet). Fixed (not user-editable) risk thresholds in the UI, though the schema supports future edit. CSV upload only (no XLSX/API ingestion yet). Baseline model = one global model trained on the combined benchmark+synthetic dataset; each company can additionally train one active company-specific model at a time (versions retained in history, only one active).

## 50. Future Scope (explicitly out of V1)

- Multi-user organizations with roles/invites
- User-editable risk thresholds via Settings UI
- XLSX / database / API data ingestion
- Multiple simultaneously-active company models with A/B comparison
- Scheduled/automatic re-training
- PostgreSQL migration (schema is ready; migration itself is a later phase)
- Email/SMS retention-campaign integration
- Real-time streaming predictions / webhook API
- Model monitoring for data/concept drift
- Native mobile app (mobile-responsive web is in V1; native app is not)

## 51. Technical Risks

| Risk | Mitigation |
|---|---|
| PythonAnywhere free tier CPU/time limits during model training | Keep ANN small; document a training time budget; allow training to run as a background/async job with status polling rather than blocking a request |
| SQLite concurrent-write limits under load | Acceptable for V1 single-small-team usage; documented PostgreSQL migration path if this becomes a bottleneck |
| Synthetic data being mistaken for real-world validation | Enforced labeling/disclaimers everywhere (§3.6); never described as "real customers" |
| Class imbalance hurting recall on the minority (churn) class | Explicit imbalance strategy (§13/ML_SPEC §11) evaluated empirically, not assumed |
| SHAP compute cost on every prediction request | Cache/precompute global SHAP per model version; compute local SHAP on-demand per prediction with a fast explainer (e.g., `TreeExplainer` for tree baselines; `KernelExplainer`/`DeepExplainer` sized carefully for the ANN, with a documented latency budget) |
| Free-tier hosting cold starts / sleep | Documented in `DEPLOYMENT.md`; user-facing loading state covers this rather than presenting it as an error |
| CSV files from real companies being messy in ways the dev dataset doesn't cover | Data Quality pipeline (§5) is built generically against the schema contract, tested with deliberately malformed fixtures in Phase 2/11, not just against the clean dev dataset |

---

**This specification set (PROJECT_SPEC.md + the six supporting docs) is the source of truth for all implementation phases. No backend, frontend, or model code is to be written until this is explicitly approved.**
