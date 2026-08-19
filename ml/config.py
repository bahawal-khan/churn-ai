"""Shared constants for the ml/ package.

Single source of truth for the random seed and the dataset schema contract
(`docs/ML_SPEC.md` §1), so every generator, audit script, and test imports
the same values instead of redefining them.
"""

from pathlib import Path

# --- Reproducibility -------------------------------------------------------

RANDOM_SEED = 42

# Distinct per-country seeds derived from RANDOM_SEED. Using the same seed
# for both country generators would make identically-shaped draws (e.g. the
# 50/50 Gender split, drawn in the same call order for both) line up
# row-for-row between the two datasets — these offsets avoid that spurious
# cross-country correlation while staying deterministic.
PAKISTAN_SEED = RANDOM_SEED
INDIA_SEED = RANDOM_SEED + 1000

# --- Paths -------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
DATA_SPLITS_DIR = DATA_PROCESSED_DIR / "splits"
IBM_RAW_CSV = DATA_RAW_DIR / "IBM_Telco_customer_churn_IBM_dataset.csv"

ARTIFACTS_DIR = REPO_ROOT / "ml" / "artifacts"

# --- Train / validation / test split (docs/ML_SPEC.md §6) ------------------

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# --- Dataset schema contract (docs/ML_SPEC.md §1) ---------------------------

# Raw modeling columns kept after audit (identifiers/zero-variance/leakage
# columns already excluded). `CLTV` is intentionally excluded here — its
# inclusion is a Phase 2 EDA decision, not assumed in Phase 1.
MODELING_COLUMNS = [
    "Gender",
    "Senior Citizen",
    "Partner",
    "Dependents",
    "Tenure Months",
    "Phone Service",
    "Multiple Lines",
    "Internet Service",
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
    "Streaming TV",
    "Streaming Movies",
    "Contract",
    "Paperless Billing",
    "Payment Method",
    "Monthly Charges",
    "Total Charges",
]

TARGET_COLUMN = "Churn Value"

# Provenance/metadata-only column. Never a production model feature
# (PROJECT_SPEC.md binding cross-cutting rule; ML_SPEC.md §1, §6).
SOURCE_COLUMN = "Source"

# Columns dropped before modeling for the IBM subset (identifiers,
# zero-variance, or direct target leakage). Kept here for reference/tests,
# not imported by the generators (they never produce these columns).
IBM_DROPPED_COLUMNS = [
    "CustomerID",
    "Count",
    "Country",
    "State",
    "City",
    "Zip Code",
    "Lat Long",
    "Latitude",
    "Longitude",
    "Churn Score",
    "Churn Reason",
]

SOURCE_IBM = "IBM"
SOURCE_PAKISTAN_SYNTHETIC = "Pakistan-Synthetic"
SOURCE_INDIA_SYNTHETIC = "India-Synthetic"

IBM_EXPECTED_ROW_COUNT = 7043
SYNTHETIC_RECORDS_PER_COUNTRY = 7000

# --- Model artifacts / metadata (docs/ML_SPEC.md §14, docs/DATABASE_SPEC.md §2.7) ---

# Matches the `models.algorithm` CHECK constraint exactly, so
# `metadata.json["algorithm"]` values are drop-in compatible with the future
# DB seeding script (docs/DATABASE_SPEC.md §2.7).
ALGORITHM_LOGISTIC_REGRESSION = "logistic_regression"
ALGORITHM_RANDOM_FOREST = "random_forest"
ALGORITHM_GRADIENT_BOOSTING = "gradient_boosting"
ALGORITHM_ANN = "ann"

# Initial fixed risk-probability thresholds (docs/PROJECT_SPEC.md §18),
# stored verbatim on every model artifact's metadata.json so a later model
# row can be seeded with `models.risk_thresholds` unchanged.
RISK_THRESHOLDS = {"low_max": 0.3, "medium_max": 0.6}

# --- SHAP explainability (docs/ML_SPEC.md §13, docs/PROJECT_SPEC.md §15) ---

# Fixed disclaimer text, verbatim from PROJECT_SPEC.md §15. Every SHAP
# explanation surface (global or local) carries this exact string — never
# reworded per call site, so the UI's legal/product framing stays consistent
# regardless of which model or explainer produced the values.
SHAP_DISCLAIMER = (
    "This shows what the model learned from patterns in the data — "
    "it identifies correlation, not proven causation."
)
