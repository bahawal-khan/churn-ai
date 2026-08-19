from __future__ import annotations


def test_unknown_route_returns_standard_envelope(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body


def test_predictions_return_model_unavailable_when_no_artifact_present(
    client, monkeypatch, tmp_path, sample_customer_payload
):
    from ml import config as ml_config
    from backend.services import model_registry

    monkeypatch.setattr(ml_config, "ARTIFACTS_DIR", tmp_path / "empty")
    model_registry.reset_cache()

    resp = client.post("/api/predictions/single", json={"customer_data": sample_customer_payload})
    assert resp.status_code == 503
    body = resp.get_json()
    assert body["error"]["code"] == "MODEL_UNAVAILABLE"
    assert "request_id" in body


def test_every_response_includes_a_request_id(client, sample_customer_payload):
    ok = client.get("/api/models")
    err = client.post("/api/predictions/single", json={"customer_data": {}})
    assert ok.get_json()["request_id"]
    assert err.get_json()["request_id"]
    assert ok.get_json()["request_id"] != err.get_json()["request_id"]


def test_request_id_is_unique_per_request(client):
    first = client.get("/api/health").get_json()["request_id"]
    second = client.get("/api/health").get_json()["request_id"]
    assert first != second
