from __future__ import annotations

import json

from tests.backend.conftest import MODEL_ID


def test_list_models_returns_the_fixture_model(client):
    resp = client.get("/api/models")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body) == 1
    entry = body[0]
    assert entry["model_id"] == MODEL_ID
    assert entry["algorithm"] == "random_forest"
    assert entry["selected_as_recommended_production_model"] is True
    assert entry["validation_metrics_summary"]["accuracy"] == 0.7


def test_get_model_detail(client):
    resp = client.get(f"/api/models/{MODEL_ID}")
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["metadata"]["model_id"] == MODEL_ID
    assert body["metrics"]["validation"]["accuracy"] == 0.7
    assert body["global_shap"] is None


def test_get_model_detail_unknown_id_returns_404(client):
    resp = client.get("/api/models/does-not-exist")
    assert resp.status_code == 404
    body = resp.get_json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert "request_id" in body


def test_list_models_handles_a_not_yet_test_evaluated_model(client, tiny_artifacts_dir):
    """Regression test: real artifacts (e.g. `logistic_regression_v1`) store
    `metrics.json` with an explicit `"test": null` before that model has been
    test-evaluated — a present-but-null key, not an absent one. A naive
    `split not in metrics` check misses this and crashes the whole listing."""
    other_dir = tiny_artifacts_dir / "not_test_evaluated_v1"
    other_dir.mkdir()
    (other_dir / "metadata.json").write_text(
        json.dumps(
            {
                "model_id": "not_test_evaluated_v1",
                "algorithm": "logistic_regression",
                "feature_schema": [{"name": "Tenure Months", "dtype": "numeric"}],
                "decision_threshold": 0.5,
                "selected_as_recommended_production_model": False,
            }
        ),
        encoding="utf-8",
    )
    (other_dir / "metrics.json").write_text(
        json.dumps({"validation": {"accuracy": 0.6}, "test": None}), encoding="utf-8"
    )

    resp = client.get("/api/models")
    assert resp.status_code == 200
    by_id = {entry["model_id"]: entry for entry in resp.get_json()["data"]}
    assert by_id["not_test_evaluated_v1"]["test_metrics_summary"] is None
    assert by_id["not_test_evaluated_v1"]["validation_metrics_summary"]["accuracy"] == 0.6
