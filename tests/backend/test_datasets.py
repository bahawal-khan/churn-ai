from __future__ import annotations

from tests.backend.factories import training_csv_bytes, upload_file

DATASETS_URL = "/api/datasets"


def test_dataset_upload_happy_path_prediction_only(client):
    csv_bytes = training_csv_bytes(n=8, seed=1)
    resp = upload_file(client, csv_bytes, DATASETS_URL)
    assert resp.status_code == 201, resp.get_json()

    body = resp.get_json()["data"]
    assert body["dataset"]["row_count"] == 8
    assert body["dataset"]["source_type"] == "company_upload"
    assert body["dataset"]["has_target_column"] is False
    assert body["quality_report"]["row_count"] == 8
    assert len(body["preview"]) > 0


def test_dataset_upload_with_target_column_sets_has_target_column(client):
    csv_bytes = training_csv_bytes(n=10, seed=2)
    resp = upload_file(client, csv_bytes, DATASETS_URL, form_fields={"target_column": "Churn Value"})
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()["data"]["dataset"]
    assert body["has_target_column"] is True
    assert body["target_column_name"] == "Churn Value"


def test_dataset_upload_creates_customer_records(client):
    csv_bytes = training_csv_bytes(n=5, seed=3)
    upload_resp = upload_file(client, csv_bytes, DATASETS_URL)
    assert upload_resp.status_code == 201

    list_resp = client.get("/api/customers")
    assert list_resp.status_code == 200
    body = list_resp.get_json()["data"]
    assert body["pagination"]["total"] == 5


def test_list_datasets_pagination(client):
    for i in range(3):
        upload_file(client, training_csv_bytes(n=4, seed=10 + i), DATASETS_URL)

    resp = client.get(DATASETS_URL, query_string={"page": 1, "page_size": 2})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert len(body["data"]) == 2
    assert body["pagination"]["total"] == 3
    assert body["pagination"]["total_pages"] == 2


def test_get_dataset_detail(client):
    upload_resp = upload_file(client, training_csv_bytes(n=4, seed=20), DATASETS_URL)
    dataset_id = upload_resp.get_json()["data"]["dataset"]["id"]

    resp = client.get(f"{DATASETS_URL}/{dataset_id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["id"] == dataset_id


def test_get_dataset_unknown_id_returns_404(client):
    resp = client.get(f"{DATASETS_URL}/999999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"


def test_delete_dataset_happy_path(client):
    upload_resp = upload_file(client, training_csv_bytes(n=4, seed=30), DATASETS_URL)
    dataset_id = upload_resp.get_json()["data"]["dataset"]["id"]

    resp = client.delete(f"{DATASETS_URL}/{dataset_id}")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["deleted"] is True

    resp = client.get(f"{DATASETS_URL}/{dataset_id}")
    assert resp.status_code == 404


def test_dataset_upload_rejects_non_csv_extension(client):
    resp = upload_file(client, b"not,a,csv", DATASETS_URL, filename="data.txt")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_cross_tenant_dataset_isolation(client, second_client):
    upload_resp = upload_file(client, training_csv_bytes(n=4, seed=40), DATASETS_URL)
    dataset_id = upload_resp.get_json()["data"]["dataset"]["id"]

    resp = second_client.get(f"{DATASETS_URL}/{dataset_id}")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["code"] == "NOT_FOUND"

    resp = second_client.delete(f"{DATASETS_URL}/{dataset_id}")
    assert resp.status_code == 404

    resp = second_client.get(DATASETS_URL)
    assert resp.get_json()["data"]["pagination"]["total"] == 0
