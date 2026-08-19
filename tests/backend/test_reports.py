from __future__ import annotations

import pandas as pd

from tests.backend.factories import upload_file


def _batch_predict(client, sample_customer_payload, n=3):
    rows = []
    for i in range(n):
        row = dict(sample_customer_payload)
        row["CustomerID"] = f"CUST-{i:03d}"
        rows.append(row)
    csv_bytes = pd.DataFrame(rows).to_csv(index=False).encode("utf-8")
    resp = upload_file(client, csv_bytes, "/api/predictions/batch", filename="customers.csv")
    assert resp.status_code == 200, resp.get_json()


def test_generate_predictions_summary_report(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=3)

    resp = client.post("/api/reports/generate", json={"report_type": "predictions_summary", "filters": {}})
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()["data"]
    assert body["report_type"] == "predictions_summary"
    assert body["row_count"] == 3

    list_resp = client.get("/api/reports")
    assert list_resp.status_code == 200
    assert list_resp.get_json()["data"]["pagination"]["total"] == 1

    download_resp = client.get(f"/api/reports/{body['id']}/download")
    assert download_resp.status_code == 200
    assert download_resp.mimetype == "text/csv"
    assert "churn_probability" in download_resp.get_data(as_text=True)


def test_generate_customers_summary_report(client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=2)

    resp = client.post("/api/reports/generate", json={"report_type": "customers_summary"})
    assert resp.status_code == 201
    assert resp.get_json()["data"]["row_count"] == 2


def test_generate_report_with_invalid_type_returns_422(client):
    resp = client.post("/api/reports/generate", json={"report_type": "not_a_real_type"})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_download_unknown_report_returns_404(client):
    resp = client.get("/api/reports/does-not-exist/download")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_cross_tenant_report_isolation(client, second_client, sample_customer_payload):
    _batch_predict(client, sample_customer_payload, n=2)
    resp = client.post("/api/reports/generate", json={"report_type": "predictions_summary"})
    report_id = resp.get_json()["data"]["id"]

    resp = second_client.get(f"/api/reports/{report_id}/download")
    assert resp.status_code == 404

    resp = second_client.get("/api/reports")
    assert resp.get_json()["data"]["pagination"]["total"] == 0
