"""Dataset ingestion (`docs/API.md` `/api/datasets`, `docs/PROJECT_SPEC.md`
§16/§16.1, `docs/DATABASE_SPEC.md` §2.5-§2.6).

`create_dataset_from_upload` is the single ingestion path shared by
`POST /api/datasets` (training-bound uploads) and `POST /api/predictions/batch`
(`docs/API.md`: batch prediction "ingested through the same dataset pipeline
as training uploads") — one code path, not duplicated logic, matching the
project's existing `DataQualityValidator` precedent (`ml/data_quality/validator.py`).

**Schema-mapping limitation (documented, not silently worked around):**
`docs/PROJECT_SPEC.md` §16.1 describes an explicit, user-reviewed
upload-to-schema column-mapping UI step. That UI is Next.js Frontend (Phase
10) work. This phase implements the backend contract without it: an upload
is matched against `ml.config.MODELING_COLUMNS` by exact column name
(case/whitespace-insensitive), and `datasets.column_mapping` is left `NULL`
until the mapping-confirmation UI exists to populate it — the same "flagged,
not hidden" pattern `scripts/seed_baseline_model.py` uses for its own
documented schema gap.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session as DBSession

from ml.config import MODELING_COLUMNS
from ml.data_quality.validator import DataQualityValidator

from backend.db.models import Customer, Dataset
from backend.errors.exceptions import DatasetInUseError, NotFoundError, SchemaMismatchError
from backend.services import audit_service

PREVIEW_ROW_COUNT = 10


def _normalize(name: str) -> str:
    return name.strip().lower()


def _match_modeling_columns(df: pd.DataFrame) -> dict[str, str]:
    """Case/whitespace-insensitive match of `df` columns to
    `ml.config.MODELING_COLUMNS` (`docs/PROJECT_SPEC.md` §16.1 step 1,
    "Detection"). Returns `{schema_column: actual_df_column}`."""
    by_normalized = {_normalize(c): c for c in df.columns}
    matched = {}
    for schema_col in MODELING_COLUMNS:
        actual = by_normalized.get(_normalize(schema_col))
        if actual is not None:
            matched[schema_col] = actual
    return matched


def _infer_column_schema(df: pd.DataFrame) -> list[dict[str, Any]]:
    """`datasets.column_schema` (`docs/DATABASE_SPEC.md` §2.5): "detected
    columns + inferred types". A column is numeric if every non-null value
    coerces cleanly, categorical otherwise."""
    schema = []
    for col in df.columns:
        non_null = df[col].replace(r"^\s*$", pd.NA, regex=True).dropna()
        is_numeric = not non_null.empty and pd.to_numeric(non_null, errors="coerce").notna().all()
        schema.append({"name": col, "dtype": "numeric" if is_numeric else "categorical"})
    return schema


def _store_file(upload_dir: Path, original_filename: str, raw_bytes: bytes) -> str:
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix or ".csv"
    storage_filename = f"{uuid.uuid4().hex}{suffix}"
    storage_path = upload_dir / storage_filename
    storage_path.write_bytes(raw_bytes)
    return str(storage_path)


def ingest_customers_from_dataframe(
    db: DBSession, *, organization_id: int, dataset: Dataset, df: pd.DataFrame, id_column: str | None
) -> int:
    """Creates/matches `customers` rows for every row of `df`
    (`docs/DATABASE_SPEC.md` §2.6). Matched by `external_customer_id` when it
    identifies an existing org customer, otherwise created
    (`docs/PROJECT_SPEC.md` §17.B). Returns the number of rows ingested."""
    matched = _match_modeling_columns(df)
    existing_by_external_id: dict[str, Customer] = {}
    if id_column and id_column in df.columns:
        existing = (
            db.query(Customer)
            .filter(Customer.organization_id == organization_id, Customer.external_customer_id.isnot(None))
            .all()
        )
        existing_by_external_id = {c.external_customer_id: c for c in existing}

    count = 0
    for _, row in df.iterrows():
        feature_data = {schema_col: row[actual_col] for schema_col, actual_col in matched.items()}
        feature_data = {
            k: (None if pd.isna(v) else (float(v) if isinstance(v, (int, float)) else str(v)))
            for k, v in feature_data.items()
        }
        external_id = str(row[id_column]) if id_column and id_column in df.columns and pd.notna(row[id_column]) else None

        actual_churn_label = None
        if dataset.target_column_name and dataset.target_column_name in df.columns:
            raw_label = row[dataset.target_column_name]
            if pd.notna(raw_label):
                actual_churn_label = str(raw_label).strip() in ("1", "1.0", "true", "True", "Yes", "yes")

        if external_id and external_id in existing_by_external_id:
            customer = existing_by_external_id[external_id]
            customer.feature_data = feature_data
            if actual_churn_label is not None:
                customer.actual_churn_label = actual_churn_label
        else:
            customer = Customer(
                organization_id=organization_id,
                dataset_id=dataset.id,
                external_customer_id=external_id,
                feature_data=feature_data,
                actual_churn_label=actual_churn_label,
            )
            db.add(customer)
            db.flush()
            if external_id:
                existing_by_external_id[external_id] = customer
        count += 1
    return count


def create_dataset_from_upload(
    db: DBSession,
    *,
    organization_id: int,
    uploaded_by_user_id: int | None,
    df: pd.DataFrame,
    original_filename: str,
    raw_bytes: bytes,
    upload_dir: Path,
    source_type: str = "company_upload",
    target_column: str | None = None,
    id_column: str | None = None,
    ingest_customers: bool = True,
) -> dict[str, Any]:
    """Full ingestion pipeline for one uploaded CSV. Returns
    `{"dataset": Dataset, "quality_report": {...}, "preview": [...]}`."""
    if id_column is None and "CustomerID" in df.columns:
        id_column = "CustomerID"

    validator = DataQualityValidator(
        required_columns=MODELING_COLUMNS, target_column=target_column, id_column=id_column
    )
    quality_report = validator.validate(df)

    has_target_column = False
    if target_column:
        target_check = next((c for c in quality_report["checks"] if c["name"] == "target_column"), None)
        has_target_column = bool(target_check and target_check["status"] == "pass")

    storage_path = _store_file(upload_dir, original_filename, raw_bytes)

    dataset = Dataset(
        organization_id=organization_id,
        original_filename=original_filename,
        storage_path=storage_path,
        source_type=source_type,
        row_count=int(len(df)),
        column_schema=_infer_column_schema(df),
        column_mapping=None,
        data_quality_report=quality_report,
        has_target_column=has_target_column,
        target_column_name=target_column if has_target_column else None,
        uploaded_by_user_id=uploaded_by_user_id,
    )
    db.add(dataset)
    db.flush()

    if ingest_customers:
        ingest_customers_from_dataframe(
            db, organization_id=organization_id, dataset=dataset, df=df, id_column=id_column
        )

    audit_service.write_audit_log(
        db,
        organization_id=organization_id,
        user_id=uploaded_by_user_id,
        event_type="dataset_upload",
        event_details={"dataset_id": dataset.id, "row_count": dataset.row_count, "source_type": source_type},
    )
    db.commit()

    preview = df.head(PREVIEW_ROW_COUNT).astype(object).where(pd.notnull(df.head(PREVIEW_ROW_COUNT)), None).to_dict(
        orient="records"
    )
    return {"dataset": dataset, "quality_report": quality_report, "preview": preview}


def serialize_dataset(dataset: Dataset) -> dict[str, Any]:
    return {
        "id": dataset.id,
        "organization_id": dataset.organization_id,
        "original_filename": dataset.original_filename,
        "source_type": dataset.source_type,
        "row_count": dataset.row_count,
        "column_schema": dataset.column_schema,
        "column_mapping": dataset.column_mapping,
        "data_quality_report": dataset.data_quality_report,
        "has_target_column": dataset.has_target_column,
        "target_column_name": dataset.target_column_name,
        "created_at": dataset.created_at.isoformat(),
    }


def list_datasets(db: DBSession, *, organization_id: int, page: int, page_size: int) -> dict[str, Any]:
    query = db.query(Dataset).filter(Dataset.organization_id == organization_id).order_by(Dataset.created_at.desc())
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "data": [serialize_dataset(d) for d in rows],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if page_size else 0,
        },
    }


def get_dataset(db: DBSession, *, organization_id: int, dataset_id: int) -> Dataset:
    dataset = db.get(Dataset, dataset_id)
    if dataset is None or dataset.organization_id != organization_id:
        raise NotFoundError("The requested dataset was not found.")
    return dataset


def delete_dataset(db: DBSession, *, organization_id: int, dataset_id: int, user_id: int) -> None:
    from sqlalchemy.exc import IntegrityError

    dataset = get_dataset(db, organization_id=organization_id, dataset_id=dataset_id)
    storage_path = Path(dataset.storage_path)
    db.delete(dataset)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise DatasetInUseError(
            "This dataset can't be deleted because a trained model still references it. "
            "Delete the dependent model first, or keep the dataset."
        ) from exc

    audit_service.write_audit_log(
        db, organization_id=organization_id, user_id=user_id, event_type="dataset_delete",
        event_details={"dataset_id": dataset_id},
    )
    db.commit()
    if storage_path.exists():
        storage_path.unlink()
