"""`/api/datasets` (`docs/API.md`)."""

from __future__ import annotations

from flask import Blueprint, current_app, g, request

from backend.auth.decorators import login_required
from backend.db import session as db_session
from backend.services import dataset_service, file_service
from backend.utils import success_response

datasets_bp = Blueprint("datasets", __name__)


@datasets_bp.post("")
@login_required
def post_dataset():
    file_storage = request.files.get("file")
    max_bytes = request.max_content_length or (25 * 1024 * 1024)
    raw_bytes = file_storage.read() if file_storage is not None else b""
    if file_storage is not None:
        file_storage.stream.seek(0)
    df = file_service.validate_and_parse_csv_upload(file_storage, max_bytes)

    target_column = request.form.get("target_column") or None

    db = db_session.get_session()
    result = dataset_service.create_dataset_from_upload(
        db,
        organization_id=g.current_user.organization_id,
        uploaded_by_user_id=g.current_user.id,
        df=df,
        original_filename=file_storage.filename,
        raw_bytes=raw_bytes,
        upload_dir=current_app.config["UPLOAD_STORAGE_DIR"],
        source_type="company_upload",
        target_column=target_column,
    )
    return success_response(
        {
            "dataset": dataset_service.serialize_dataset(result["dataset"]),
            "quality_report": result["quality_report"],
            "preview": result["preview"],
        },
        status=201,
    )


@datasets_bp.get("")
@login_required
def list_datasets():
    page = int(request.args.get("page", 1))
    page_size = min(int(request.args.get("page_size", 20)), 100)
    db = db_session.get_session()
    return success_response(
        dataset_service.list_datasets(db, organization_id=g.current_user.organization_id, page=page, page_size=page_size)
    )


@datasets_bp.get("/<int:dataset_id>")
@login_required
def get_dataset(dataset_id: int):
    db = db_session.get_session()
    dataset = dataset_service.get_dataset(db, organization_id=g.current_user.organization_id, dataset_id=dataset_id)
    return success_response(dataset_service.serialize_dataset(dataset))


@datasets_bp.delete("/<int:dataset_id>")
@login_required
def delete_dataset(dataset_id: int):
    db = db_session.get_session()
    dataset_service.delete_dataset(
        db, organization_id=g.current_user.organization_id, dataset_id=dataset_id, user_id=g.current_user.id
    )
    return success_response({"deleted": True})
