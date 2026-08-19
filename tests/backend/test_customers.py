from __future__ import annotations

from tests.backend.factories import upload_file


def _rows(sample_customer_payload, n=4):
    rows = []
    for i in range(n):
        row = dict(sample_customer_payload)
        row["CustomerID"] = f"CUST-{i:03d}"
        rows.append(row)
    return rows


def _batch_predict(client, sample_customer_payload, n=4):
    import pandas as pd

    df = pd.DataFrame(_rows(sample_customer_payload, n))
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    resp = upload_file(client, csv_bytes, "/api/predictions/batch", filename="customers.csv")
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["data"]


def test_batch_prediction_populates_customers_list(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=4)

    resp = client.get("/api/customers")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["pagination"]["total"] == 4
    assert all(row["latest_risk_level"] in ("low", "medium", "high") for row in body["data"])


def test_customer_detail_includes_prediction_history_and_explanation(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=2)
    customer_id = client.get("/api/customers").get_json()["data"]["data"][0]["id"]

    resp = client.get(f"/api/customers/{customer_id}")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["customer"]["id"] == customer_id
    assert len(body["predictions"]) == 1
    prediction = body["predictions"][0]
    assert prediction["risk_level"] in ("low", "medium", "high")
    assert prediction["explanation"] is not None
    assert len(prediction["explanation"]["top_factors"]) > 0


def test_customer_risk_level_filter(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=4)
    all_customers = client.get("/api/customers").get_json()["data"]["data"]
    present_level = all_customers[0]["latest_risk_level"]

    resp = client.get("/api/customers", query_string={"risk_level": present_level})
    assert resp.status_code == 200
    body = resp.get_json()["data"]["data"]
    assert all(row["latest_risk_level"] == present_level for row in body)


def test_get_customer_unknown_id_returns_404(client):
    resp = client.get("/api/customers/999999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_cross_tenant_customer_isolation(client, second_client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=2)
    customer_id = client.get("/api/customers").get_json()["data"]["data"][0]["id"]

    resp = second_client.get(f"/api/customers/{customer_id}")
    assert resp.status_code == 404

    resp = second_client.get("/api/customers")
    assert resp.get_json()["data"]["pagination"]["total"] == 0
