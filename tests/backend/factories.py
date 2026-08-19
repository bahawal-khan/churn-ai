"""Shared CSV-fixture builders for the Phase 9 backend resource tests
(datasets/training/customers/analytics/reports) — same generation style as
`tests/ml/test_models.py`'s `tiny_dataset` fixture, adapted to produce raw
CSV bytes with an optional target column for upload/training endpoints.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

from ml.config import TARGET_COLUMN


def make_row(rng: np.random.RandomState, index: int, churn: int) -> dict:
    return {
        "CustomerID": f"CUST-{index:04d}",
        "Gender": rng.choice(["Female", "Male"]),
        "Senior Citizen": rng.choice(["No", "Yes"]),
        "Partner": rng.choice(["No", "Yes"]),
        "Dependents": rng.choice(["No", "Yes"]),
        "Tenure Months": int(rng.randint(0, 72)),
        "Phone Service": "Yes",
        "Multiple Lines": rng.choice(["No", "Yes"]),
        "Internet Service": rng.choice(["DSL", "Fiber optic", "No"]),
        "Online Security": rng.choice(["No", "Yes"]),
        "Online Backup": rng.choice(["No", "Yes"]),
        "Device Protection": rng.choice(["No", "Yes"]),
        "Tech Support": rng.choice(["No", "Yes"]),
        "Streaming TV": rng.choice(["No", "Yes"]),
        "Streaming Movies": rng.choice(["No", "Yes"]),
        "Contract": rng.choice(["Month-to-month", "One year", "Two year"]),
        "Paperless Billing": rng.choice(["No", "Yes"]),
        "Payment Method": rng.choice(
            ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"]
        ),
        "Monthly Charges": float(rng.uniform(20, 120)),
        "Total Charges": float(rng.uniform(20, 8000)),
        TARGET_COLUMN: churn,
    }


def training_dataframe(n: int, seed: int, churn_rate: float = 0.35) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    rows = [make_row(rng, i, int(rng.rand() < churn_rate)) for i in range(n)]
    return pd.DataFrame(rows)


def training_csv_bytes(n: int, seed: int, churn_rate: float = 0.35) -> bytes:
    return training_dataframe(n, seed, churn_rate).to_csv(index=False).encode("utf-8")


def upload_file(
    client,
    csv_bytes: bytes,
    url: str,
    filename: str = "customers.csv",
    form_fields: dict | None = None,
    **kwargs,
):
    data = {"file": (io.BytesIO(csv_bytes), filename), **(form_fields or {})}
    return client.post(url, data=data, content_type="multipart/form-data", **kwargs)
