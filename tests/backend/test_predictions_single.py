from __future__ import annotations

import pytest


def test_single_prediction_happy_path(client, sample_customer_payload):
    resp = client.post(
        "/api/predictions/single",
        json={"customer_data": sample_customer_payload, "customer_id": "cust-123"},
    )
    assert resp.status_code == 200
    data = resp.get_json()["data"]

    assert data["customer_id"] == "cust-123"
    assert 0.0 <= data["churn_probability"] <= 1.0
    assert data["predicted_class"] in (0, 1)
    assert data["risk_level"] in ("low", "medium", "high")
    assert data["algorithm"] == "random_forest"

    explanation = data["explanation"]
    assert explanation["additivity_check_passed"] is True
    assert len(explanation["top_factors"]) > 0
    assert "correlation, not proven causation" in explanation["disclaimer"]


def test_single_prediction_is_deterministic(client, sample_customer_payload):
    first = client.post("/api/predictions/single", json={"customer_data": sample_customer_payload}).get_json()
    second = client.post("/api/predictions/single", json={"customer_data": sample_customer_payload}).get_json()
    # RandomForestClassifier(n_jobs=-1) averages trees across threads, so the
    # summation order (and therefore the last float ULPs) can vary call to
    # call — real-world determinism only holds to float tolerance, not bit-
    # for-bit equality.
    assert first["data"]["churn_probability"] == pytest.approx(second["data"]["churn_probability"])
    assert first["data"]["predicted_class"] == second["data"]["predicted_class"]
    assert first["data"]["risk_level"] == second["data"]["risk_level"]
    assert first["data"]["customer_id"] is None


def test_single_prediction_missing_fields_returns_schema_mismatch(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    del payload["Contract"]
    del payload["Tenure Months"]

    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"]["code"] == "SCHEMA_MISMATCH"
    assert set(body["error"]["details"]["missing_fields"]) == {"Contract", "Tenure Months"}


def test_single_prediction_bad_category_returns_validation_error(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    payload["Contract"] = "Whenever I feel like it"

    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "Contract" in body["error"]["details"]["field_errors"]


def test_single_prediction_category_is_case_and_whitespace_insensitive(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    payload["Contract"] = "  month-TO-month  "

    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    assert resp.status_code == 200


def test_single_prediction_negative_numeric_rejected(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    payload["Monthly Charges"] = -10

    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_single_prediction_non_numeric_string_rejected(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    payload["Tenure Months"] = "twelve"

    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    assert resp.status_code == 422
    assert "Tenure Months" in resp.get_json()["error"]["details"]["field_errors"]


def test_single_prediction_missing_customer_data_key(client):
    resp = client.post("/api/predictions/single", json={"customer_id": "x"})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_single_prediction_non_json_body_rejected(client):
    resp = client.post("/api/predictions/single", data="not json", content_type="text/plain")
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


def test_single_prediction_response_never_reveals_internal_paths(client, sample_customer_payload):
    payload = dict(sample_customer_payload)
    payload["Tenure Months"] = "not-a-number"
    resp = client.post("/api/predictions/single", json={"customer_data": payload})
    body_text = resp.get_data(as_text=True)
    assert "Traceback" not in body_text
    assert ".py" not in body_text
