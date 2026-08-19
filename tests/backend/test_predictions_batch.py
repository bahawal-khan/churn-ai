from __future__ import annotations

import io

import pandas as pd

from ml.config import MODELING_COLUMNS


def _rows(sample_customer_payload, n=5, overrides_by_index: dict[int, dict] | None = None):
    overrides_by_index = overrides_by_index or {}
    rows = []
    for i in range(n):
        row = dict(sample_customer_payload)
        row["CustomerID"] = f"CUST-{i:03d}"
        row.update(overrides_by_index.get(i, {}))
        rows.append(row)
    return rows


def _csv_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


def _upload(client, csv_bytes: bytes, filename: str = "customers.csv", **kwargs):
    data = {"file": (io.BytesIO(csv_bytes), filename)}
    return client.post("/api/predictions/batch", data=data, content_type="multipart/form-data", **kwargs)


def test_batch_prediction_happy_path_preserves_every_row(client, sample_customer_payload):
    rows = _rows(sample_customer_payload, n=6)
    resp = _upload(client, _csv_bytes(rows))
    assert resp.status_code == 200

    body = resp.get_json()["data"]
    assert body["summary"]["total_rows"] == 6
    assert body["summary"]["scored_rows"] == 6
    assert body["summary"]["failed_rows"] == 0
    assert body["summary"]["id_column"] == "CustomerID"

    results = body["results"]
    assert len(results) == 6
    assert {r["CustomerID"] for r in results} == {f"CUST-{i:03d}" for i in range(6)}
    for r in results:
        assert r["risk_level"] in ("low", "medium", "high")
        assert r["prediction_error"] is None
        # original columns flow through untouched alongside the new ones
        assert r["Contract"] == sample_customer_payload["Contract"]


def test_batch_prediction_matches_columns_case_and_whitespace_insensitively(client, sample_customer_payload):
    """`docs/PROJECT_SPEC.md` §16.1 step 1 ("Detection") promises column
    matching is case/whitespace-insensitive — a header like "senior citizen"
    or "Customer ID" (space) must still resolve to the schema's "Senior
    Citizen" / "CustomerID", not fail the whole batch as missing columns."""
    rows = _rows(sample_customer_payload, n=3)
    for row in rows:
        row["senior citizen"] = row.pop("Senior Citizen")
        row["Customer ID"] = row.pop("CustomerID")
    resp = _upload(client, _csv_bytes(rows))
    assert resp.status_code == 200

    body = resp.get_json()["data"]
    assert body["summary"]["scored_rows"] == 3
    assert body["summary"]["failed_rows"] == 0
    assert body["summary"]["id_column"] == "CustomerID"
    for r in body["results"]:
        assert r["prediction_error"] is None


def test_batch_prediction_bad_row_is_flagged_not_dropped(client, sample_customer_payload):
    rows = _rows(sample_customer_payload, n=3, overrides_by_index={1: {"Contract": "not-a-real-contract"}})
    resp = _upload(client, _csv_bytes(rows))
    assert resp.status_code == 200

    body = resp.get_json()["data"]
    assert body["summary"]["total_rows"] == 3
    assert body["summary"]["scored_rows"] == 2
    assert body["summary"]["failed_rows"] == 1

    results = sorted(body["results"], key=lambda r: r["CustomerID"])
    bad_row = results[1]
    assert bad_row["CustomerID"] == "CUST-001"
    assert bad_row["churn_probability"] is None
    assert bad_row["prediction_error"] is not None
    assert "Contract" in bad_row["prediction_error"]


def test_batch_prediction_bad_numeric_value_does_not_block_whole_file(client, sample_customer_payload):
    """A single row-level data-quality problem (here: a non-numeric "Total
    Charges") must not reject the entire upload — `predict_batch` already
    handles this per row, so the other rows must still be scored
    (`docs/PROJECT_SPEC.md` §17.B "preserve successful rows")."""
    rows = _rows(sample_customer_payload, n=5, overrides_by_index={2: {"Total Charges": "not-a-number"}})
    resp = _upload(client, _csv_bytes(rows))
    assert resp.status_code == 200

    body = resp.get_json()["data"]
    assert body["summary"]["total_rows"] == 5
    assert body["summary"]["scored_rows"] == 4
    assert body["summary"]["failed_rows"] == 1

    results = sorted(body["results"], key=lambda r: r["CustomerID"])
    bad_row = results[2]
    assert bad_row["CustomerID"] == "CUST-002"
    assert bad_row["churn_probability"] is None
    assert bad_row["prediction_error"] is not None
    assert "Total Charges" in bad_row["prediction_error"]
    for r in results:
        if r["CustomerID"] != "CUST-002":
            assert r["prediction_error"] is None
            assert r["churn_probability"] is not None


def test_batch_prediction_csv_download_format(client, sample_customer_payload):
    rows = _rows(sample_customer_payload, n=2)
    resp = _upload(client, _csv_bytes(rows), query_string={"format": "csv"})
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    body_text = resp.get_data(as_text=True)
    assert "churn_probability" in body_text
    assert "CUST-000" in body_text


def test_batch_prediction_missing_required_column_returns_schema_mismatch(client, sample_customer_payload):
    rows = _rows(sample_customer_payload, n=2)
    for row in rows:
        del row["Contract"]
    resp = _upload(client, _csv_bytes(rows))
    assert resp.status_code == 422
    body = resp.get_json()
    assert body["error"]["code"] == "SCHEMA_MISMATCH"
    assert "Contract" in body["error"]["details"]["missing_columns"]


def test_batch_prediction_rejects_non_csv_extension(client):
    resp = _upload(client, b"col1,col2\n1,2\n", filename="customers.txt")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_batch_prediction_rejects_empty_file(client):
    resp = _upload(client, b"")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_batch_prediction_rejects_header_only_file(client, sample_customer_payload):
    header = ",".join(list(sample_customer_payload.keys()) + ["CustomerID"])
    resp = _upload(client, (header + "\n").encode("utf-8"))
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_batch_prediction_rejects_ragged_rows_as_malformed_csv(client, sample_customer_payload):
    columns = list(sample_customer_payload.keys()) + ["CustomerID"]
    header = ",".join(columns)
    # A well-formed first data row establishes the field count for pandas'
    # C parser; a single malformed row alone doesn't reliably raise (pandas
    # treats an all-rows-agree-except-header mismatch as an implicit index
    # instead) — a *second*, differently-sized row is what triggers a real
    # ParserError ("ragged rows").
    good_row = ",".join(str(sample_customer_payload[c]) if c in sample_customer_payload else "CUST-000" for c in columns)
    ragged_row = ",".join(["1"] * (len(columns) + 5))
    ragged = header + "\n" + good_row + "\n" + ragged_row + "\n"
    resp = _upload(client, ragged.encode("utf-8"))
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "MALFORMED_CSV"


def test_batch_prediction_no_file_field_returns_validation_error(client):
    resp = client.post("/api/predictions/batch", data={}, content_type="multipart/form-data")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_batch_prediction_requires_all_modeling_columns_present(sample_customer_payload):
    # Sanity check on the fixture itself: the sample payload used across
    # tests must actually cover the full raw modeling schema, or the
    # "missing column" tests above wouldn't be exercising the real contract.
    assert set(MODELING_COLUMNS) <= set(sample_customer_payload.keys())
