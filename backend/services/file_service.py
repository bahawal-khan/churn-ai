"""CSV upload validation (`docs/BACKEND_SPEC.md` §6): cheap checks first
(extension, size, a lightweight binary sniff), then the more expensive parse.
Uploads are processed entirely in memory — Phase 7 has no `datasets` table
to persist a stored file against (`docs/DATABASE_SPEC.md` is out of scope
here), so there is no server-generated storage filename to manage; nothing
from the upload ever touches disk.
"""

from __future__ import annotations

import io

import pandas as pd
from werkzeug.datastructures import FileStorage

from ml.data_quality.validator import MalformedCSVError as MLMalformedCSVError, load_csv_safely

from backend.errors.exceptions import FileTooLargeError, MalformedCSVError, ValidationError

ALLOWED_EXTENSIONS = (".csv",)

# A null byte in the first chunk is a strong, cheap signal of a binary file
# (image, archive, spreadsheet binary format) mislabeled/renamed as .csv —
# checked before attempting a full parse.
_SNIFF_CHUNK_SIZE = 4096


def validate_and_parse_csv_upload(file_storage: FileStorage | None, max_size_bytes: int) -> pd.DataFrame:
    if file_storage is None or not file_storage.filename:
        raise ValidationError(
            "No file was uploaded. Attach a CSV file as multipart/form-data field 'file'."
        )

    filename = file_storage.filename
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValidationError(
            f"Unsupported file type for {filename!r}. Only .csv files are accepted.",
            details={"allowed_extensions": list(ALLOWED_EXTENSIONS)},
        )

    raw_bytes = file_storage.read()
    file_storage.stream.seek(0)

    if len(raw_bytes) == 0:
        raise ValidationError("The uploaded file is empty.")

    if len(raw_bytes) > max_size_bytes:
        raise FileTooLargeError(
            f"File exceeds the maximum upload size of {max_size_bytes // (1024 * 1024)} MB.",
            details={"max_size_bytes": max_size_bytes, "received_bytes": len(raw_bytes)},
        )

    if b"\x00" in raw_bytes[:_SNIFF_CHUNK_SIZE]:
        raise ValidationError("The uploaded file does not look like a text CSV file.")

    try:
        df = load_csv_safely(io.BytesIO(raw_bytes))
    except MLMalformedCSVError as exc:
        raise MalformedCSVError(str(exc)) from exc

    if df.shape[0] == 0:
        raise ValidationError("The uploaded CSV has a header row but no data rows.")

    return df
