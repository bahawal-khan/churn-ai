from __future__ import annotations

import pandas as pd

from tests.backend.factories import upload_file


def _batch_predict(client, sample_customer_payload, n=4):
    rows = []
    for i in range(n):
        row = dict(sample_customer_payload)
        row["CustomerID"] = f"CUST-{i:03d}"
        rows.append(row)
    csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    resp = upload_file(client, csv_bytes, "/api/predictions/batch", filename="customers.csv")
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]


def test_dashboard_honest_empty_state_before_any_predictions(client):
    resp = client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["total_customers"] == 0
    assert body["scored_customers"] == 0
    assert body["at_risk_customers"] == 0
    assert body["predicted_churn_rate"] is None
    assert body["avg_churn_probability"] is None


def test_dashboard_reflects_real_predictions(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=4)

    resp = client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["total_customers"] == 4
    assert body["scored_customers"] == 4
    assert 0.0 <= body["predicted_churn_rate"] <= 1.0
    assert body["active_model"]["available"] is True


def test_risk_distribution_counts_sum_to_scored_customers(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=5)

    resp = client.get("/api/analytics/risk-distribution")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert sum(body["counts"].values()) == body["scored_customers"] == 5


def test_churn_trend_has_a_point_after_predictions(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=3)

    resp = client.get("/api/analytics/churn-trend")
    assert resp.status_code == 200
    points = resp.get_json()["data"]["points"]
    assert len(points) >= 1
    assert points[0]["prediction_count"] == 3


def test_top_drivers_honest_when_no_global_shap_cached(client, sample_customer_payload):
    """The test fixture model bundle has no `global_shap.json` on disk
    (`docs/ML_SPEC.md` §13 caches this at training time) — the endpoint must
    say so honestly rather than fabricate a driver list."""
    _batch_predict(client, sample_customer_payload, n=2)

    resp = client.get("/api/analytics/top-drivers")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["available"] is False
    assert body["feature_importance"] == []


def test_segments_grouped_by_known_schema_cuts(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=3)

    resp = client.get("/api/analytics/segments")
    assert resp.status_code == 200
    body = resp.get_json()["data"]["segments"]
    assert set(body.keys()) == {"Contract", "Senior Citizen", "Dependents"}
    contract_value = sample_customer_payload["Contract"]
    assert contract_value in body["Contract"]
    assert sum(body["Contract"][contract_value].values()) == 3


def test_cross_tenant_analytics_isolation(client, second_client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=3)

    resp = second_client.get("/api/analytics/dashboard")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["total_customers"] == 0
    assert body["scored_customers"] == 0
