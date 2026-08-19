from __future__ import annotations


def test_health_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["model_loaded"] is True
    assert body["data"]["db"] == "ok"
    assert "request_id" in body and body["request_id"]


def test_health_reports_model_unavailable_when_no_artifact(app, monkeypatch, tmp_path):
    from ml import config as ml_config
    from backend.services import model_registry

    monkeypatch.setattr(ml_config, "ARTIFACTS_DIR", tmp_path / "empty")
    model_registry.reset_cache()

    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["model_loaded"] is False
