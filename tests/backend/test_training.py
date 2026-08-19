from __future__ import annotations

from tests.backend.factories import training_csv_bytes, upload_file

DATASETS_URL = "/api/datasets"
TRAINING_URL = "/api/training/jobs"


def _upload_training_dataset(client, n=220, seed=100, churn_rate=0.35):
    resp = upload_file(
        client,
        training_csv_bytes(n=n, seed=seed, churn_rate=churn_rate),
        DATASETS_URL,
        form_fields={"target_column": "Churn Value"},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["data"]["dataset"]["id"]


def test_training_job_happy_path_completes_and_produces_activatable_model(client):
    dataset_id = _upload_training_dataset(client)

    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    assert resp.status_code == 201, resp.get_json()
    job = resp.get_json()["data"]
    assert job["status"] == "completed", job
    assert job["resulting_model_id"] is not None

    get_resp = client.get(f"{TRAINING_URL}/{job['id']}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["data"]["status"] == "completed"

    model_id = job["resulting_model_id"]
    activate_resp = client.post(f"/api/models/{model_id}/activate")
    assert activate_resp.status_code == 200
    assert activate_resp.get_json()["data"]["is_active"] is True

    models_resp = client.get("/api/models")
    org_models = [m for m in models_resp.get_json()["data"] if m.get("model_id") == model_id]
    assert len(org_models) == 1
    assert org_models[0]["is_active"] is True


def test_training_job_missing_target_column_returns_422(client):
    dataset_id = _upload_training_dataset(client)

    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "NotARealColumn"})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "TRAINING_LABELS_REQUIRED"


def test_training_job_single_class_target_returns_422(client):
    dataset_id = _upload_training_dataset(client, n=20, seed=200, churn_rate=0.0)

    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "TRAINING_LABELS_REQUIRED"


def test_training_job_small_dataset_gets_warning_but_still_completes(client):
    dataset_id = _upload_training_dataset(client, n=60, seed=300, churn_rate=0.4)

    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    assert resp.status_code == 201, resp.get_json()
    job = resp.get_json()["data"]
    assert job["status"] == "completed"
    assert "small" in job["status_message"].lower()


def test_delete_dataset_blocked_after_training(client):
    dataset_id = _upload_training_dataset(client)
    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    assert resp.get_json()["data"]["status"] == "completed"

    delete_resp = client.delete(f"{DATASETS_URL}/{dataset_id}")
    assert delete_resp.status_code == 409
    assert delete_resp.get_json()["error"]["code"] == "DATASET_IN_USE"


def test_cross_tenant_training_job_isolation(client, second_client):
    dataset_id = _upload_training_dataset(client)
    resp = client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    job_id = resp.get_json()["data"]["id"]

    resp = second_client.get(f"{TRAINING_URL}/{job_id}")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    resp = second_client.post(TRAINING_URL, json={"dataset_id": dataset_id, "target_column": "Churn Value"})
    assert resp.status_code == 404
