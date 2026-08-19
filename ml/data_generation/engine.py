"""Shared archetype-based generation engine used by both country generators.

`pakistan_generator.py` and `india_generator.py` each define their own list
of `Archetype` records (distributions + conditional probabilities) and call
`generate_country_dataset()` here to turn those archetypes into a schema-
conformant DataFrame. Sharing this engine keeps the two countries' output
mechanically identical (`docs/PROJECT_SPEC.md` §3.2: "same methodology,
distinct archetypes") while each generator file still documents its own
archetypes, shares, and distributional assumptions per §3.2 point 5.

Nothing here is fit to or copied from IBM rows (§3.2 point 2: "not row
duplication") — every value is drawn from an archetype-specific distribution
or conditional-probability table, and churn labels are produced by the
latent-propensity mechanism in `docs/PROJECT_SPEC.md` §3.5, not sampled
from IBM's observed churn rate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import truncnorm

MAX_TENURE_MONTHS = 72
MIN_MONTHLY_CHARGES = 18.25
MAX_MONTHLY_CHARGES = 118.75

# --- Churn latent-propensity model (docs/PROJECT_SPEC.md §3.5) -------------
#
#   churn_logit = BASE_BIAS
#               + W_CONTRACT_M2M       * contract_is_month_to_month
#               + W_MONTHLY_CHARGES    * normalized_monthly_charges
#               - W_TENURE             * normalized_tenure
#               + W_NO_TECH_SUPPORT    * no_tech_support
#               + W_ELECTRONIC_CHECK   * electronic_check_payment
#               - W_FAMILY             * has_dependents_or_partner
#               + W_ARCHETYPE_OFFSET   * archetype_base_churn_offset
#               + epsilon
#   churn_probability = sigmoid(churn_logit)
#   churn_label = Bernoulli(churn_probability)
#
# Weight signs match the churn intuition confirmed in the IBM EDA
# (`docs/PROJECT_SPEC.md` §2.1, §3.5): month-to-month contracts, higher
# charges, no tech support, and electronic-check payment push churn up;
# longer tenure and family ties (partner/dependents) push it down.
# `epsilon` (mean-zero Gaussian noise) keeps churn non-deterministic —
# validated in `validate.py` by confirming no single feature reaches a
# near-1.0 standalone AUC.
BASE_BIAS = -1.70
W_CONTRACT_M2M = 1.05
W_MONTHLY_CHARGES = 0.85
W_TENURE = 1.35
W_NO_TECH_SUPPORT = 0.45
W_ELECTRONIC_CHECK = 0.5
W_FAMILY = 0.55
W_ARCHETYPE_OFFSET = 1.0
EPSILON_STD = 1.15

_INTERNET_DEPENDENT_ADDONS = (
    "Online Security",
    "Online Backup",
    "Device Protection",
    "Tech Support",
    "Streaming TV",
    "Streaming Movies",
)
_PROTECTION_ADDONS = ("Online Security", "Online Backup", "Device Protection", "Tech Support")
_STREAMING_ADDONS = ("Streaming TV", "Streaming Movies")


@dataclass(frozen=True)
class Archetype:
    """One customer segment's feature distributions and conditional
    probabilities. Shares across an archetype list must sum to 1.0."""

    name: str
    share: float

    # Tenure Months: truncated-normal(mean, std) clipped to [0, MAX_TENURE_MONTHS]
    tenure_mean: float
    tenure_std: float

    # Monthly Charges: truncated-normal(mean, std) clipped to the observed IBM range
    monthly_charges_mean: float
    monthly_charges_std: float

    senior_citizen_prob: float
    partner_prob: float
    dependents_prob: float
    phone_service_prob: float

    # Internet Service categorical distribution, must sum to 1.0
    internet_service_probs: dict[str, float]

    # P(add-on = Yes | has internet), split protection vs. streaming per
    # docs/ML_SPEC.md §4 (they behave differently in churn literature)
    protection_addon_prob: float
    streaming_addon_prob: float

    multiple_lines_prob: float  # P(Multiple Lines = Yes | has phone service)

    # Contract categorical distribution, must sum to 1.0
    contract_probs: dict[str, float]

    paperless_billing_prob: float

    # Payment Method categorical distribution, must sum to 1.0
    payment_method_probs: dict[str, float]

    # w7 term: negative = below-average churn propensity, positive = above-average
    churn_base_offset: float

    extra: dict = field(default_factory=dict)


def _truncated_normal_draw(rng: np.random.Generator, mean: float, std: float, low: float, high: float, size: int) -> np.ndarray:
    a, b = (low - mean) / std, (high - mean) / std
    return truncnorm.rvs(a, b, loc=mean, scale=std, size=size, random_state=rng)


def _categorical_draw(rng: np.random.Generator, probs: dict[str, float], size: int) -> np.ndarray:
    labels = list(probs.keys())
    weights = np.array(list(probs.values()), dtype=float)
    weights = weights / weights.sum()
    return rng.choice(labels, size=size, p=weights)


def _bernoulli_draw(rng: np.random.Generator, prob: float, size: int) -> np.ndarray:
    return rng.random(size) < prob


def _yes_no(mask: np.ndarray) -> np.ndarray:
    return np.where(mask, "Yes", "No")


def _generate_archetype_rows(rng: np.random.Generator, archetype: Archetype, n: int) -> pd.DataFrame:
    tenure = _truncated_normal_draw(
        rng, archetype.tenure_mean, archetype.tenure_std, 0, MAX_TENURE_MONTHS, n
    )
    tenure_months = np.round(tenure).astype(int)

    monthly_charges = _truncated_normal_draw(
        rng,
        archetype.monthly_charges_mean,
        archetype.monthly_charges_std,
        MIN_MONTHLY_CHARGES,
        MAX_MONTHLY_CHARGES,
        n,
    )
    monthly_charges = np.round(monthly_charges, 2)

    # Total Charges = tenure * monthly charge + billing-variance noise,
    # never a perfectly deterministic product (docs/PROJECT_SPEC.md §3.3).
    billing_noise = rng.normal(loc=0.0, scale=np.maximum(tenure_months * monthly_charges * 0.03, 1.0))
    total_charges = np.where(
        tenure_months == 0,
        0.0,
        np.clip(tenure_months * monthly_charges + billing_noise, 0.0, None),
    )
    total_charges = np.round(total_charges, 2)

    gender = _categorical_draw(rng, {"Male": 0.5, "Female": 0.5}, n)
    senior_citizen = _yes_no(_bernoulli_draw(rng, archetype.senior_citizen_prob, n))
    partner = _bernoulli_draw(rng, archetype.partner_prob, n)
    dependents = _bernoulli_draw(rng, archetype.dependents_prob, n)

    phone_service = _bernoulli_draw(rng, archetype.phone_service_prob, n)
    multiple_lines = np.where(
        ~phone_service,
        "No phone service",
        _yes_no(_bernoulli_draw(rng, archetype.multiple_lines_prob, n)),
    )

    internet_service = _categorical_draw(rng, archetype.internet_service_probs, n)
    has_internet = internet_service != "No"

    def addon_column(prob: float) -> np.ndarray:
        yes = _bernoulli_draw(rng, prob, n)
        return np.where(~has_internet, "No internet service", _yes_no(yes & has_internet))

    online_security = addon_column(archetype.protection_addon_prob)
    online_backup = addon_column(archetype.protection_addon_prob)
    device_protection = addon_column(archetype.protection_addon_prob)
    tech_support = addon_column(archetype.protection_addon_prob)
    streaming_tv = addon_column(archetype.streaming_addon_prob)
    streaming_movies = addon_column(archetype.streaming_addon_prob)

    contract = _categorical_draw(rng, archetype.contract_probs, n)
    paperless_billing = _yes_no(_bernoulli_draw(rng, archetype.paperless_billing_prob, n))
    payment_method = _categorical_draw(rng, archetype.payment_method_probs, n)

    df = pd.DataFrame(
        {
            "Gender": gender,
            "Senior Citizen": senior_citizen,
            "Partner": _yes_no(partner),
            "Dependents": _yes_no(dependents),
            "Tenure Months": tenure_months,
            "Phone Service": _yes_no(phone_service),
            "Multiple Lines": multiple_lines,
            "Internet Service": internet_service,
            "Online Security": online_security,
            "Online Backup": online_backup,
            "Device Protection": device_protection,
            "Tech Support": tech_support,
            "Streaming TV": streaming_tv,
            "Streaming Movies": streaming_movies,
            "Contract": contract,
            "Paperless Billing": paperless_billing,
            "Payment Method": payment_method,
            "Monthly Charges": monthly_charges,
            "Total Charges": total_charges,
        }
    )
    df["_archetype"] = archetype.name
    df["_partner_bool"] = partner
    df["_dependents_bool"] = dependents
    df["_churn_base_offset"] = archetype.churn_base_offset
    return df


def _assign_churn_labels(rng: np.random.Generator, df: pd.DataFrame) -> pd.DataFrame:
    contract_is_m2m = (df["Contract"] == "Month-to-month").astype(float)
    normalized_monthly_charges = (df["Monthly Charges"] - MIN_MONTHLY_CHARGES) / (
        MAX_MONTHLY_CHARGES - MIN_MONTHLY_CHARGES
    )
    normalized_tenure = df["Tenure Months"] / MAX_TENURE_MONTHS
    no_tech_support = (df["Tech Support"] != "Yes").astype(float)
    electronic_check = (df["Payment Method"] == "Electronic check").astype(float)
    has_family = (df["_partner_bool"] | df["_dependents_bool"]).astype(float)

    epsilon = rng.normal(loc=0.0, scale=EPSILON_STD, size=len(df))

    logit = (
        BASE_BIAS
        + W_CONTRACT_M2M * contract_is_m2m
        + W_MONTHLY_CHARGES * normalized_monthly_charges
        - W_TENURE * normalized_tenure
        + W_NO_TECH_SUPPORT * no_tech_support
        + W_ELECTRONIC_CHECK * electronic_check
        - W_FAMILY * has_family
        + W_ARCHETYPE_OFFSET * df["_churn_base_offset"]
        + epsilon
    )
    probability = 1.0 / (1.0 + np.exp(-logit))
    churn_value = (rng.random(len(df)) < probability).astype(int)

    df = df.copy()
    df["Churn Value"] = churn_value
    df = df.drop(columns=["_partner_bool", "_dependents_bool", "_churn_base_offset"])
    return df


def generate_country_dataset(
    archetypes: list[Archetype],
    total_records: int,
    country_source_label: str,
    id_prefix: str,
    seed: int,
) -> pd.DataFrame:
    """Generate `total_records` schema-conformant synthetic rows from the
    given archetype list. Deterministic: identical `seed` -> identical
    output (byte-for-byte), per docs/PROJECT_SPEC.md §3.2 point 4."""

    total_share = sum(a.share for a in archetypes)
    if not np.isclose(total_share, 1.0, atol=1e-6):
        raise ValueError(f"Archetype shares must sum to 1.0, got {total_share}")

    rng = np.random.default_rng(seed)

    counts = [round(a.share * total_records) for a in archetypes]
    counts[-1] += total_records - sum(counts)  # absorb rounding remainder

    frames = [
        _generate_archetype_rows(rng, archetype, n)
        for archetype, n in zip(archetypes, counts)
        if n > 0
    ]
    df = pd.concat(frames, ignore_index=True)

    # Shuffle so archetypes aren't grouped in contiguous blocks (mirrors a
    # real customer file, and avoids order-dependent downstream splitting).
    df = df.iloc[rng.permutation(len(df))].reset_index(drop=True)

    df = _assign_churn_labels(rng, df)

    df.insert(0, "CustomerID", [f"{id_prefix}-{i:05d}" for i in range(1, len(df) + 1)])
    df["Source"] = country_source_label

    return df
