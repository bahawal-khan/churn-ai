"""Custom exception hierarchy mapped to the standard error envelope
(`docs/BACKEND_SPEC.md` §7). Routes/services raise these; `handlers.py`
turns them into the client-facing `{ "error": {...}, "request_id": ... }`
shape and never lets internal details leak past `message`/`details`.
"""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    """Base class for every application error with a known code/status."""

    code = "INTERNAL_ERROR"
    http_status = 500

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    """Malformed or semantically invalid request data (`docs/BACKEND_SPEC.md` §7)."""

    code = "VALIDATION_ERROR"
    http_status = 422


class SchemaMismatchError(AppError):
    """Input does not match the active model's recorded `feature_schema`
    (`docs/PROJECT_SPEC.md` §16.1)."""

    code = "SCHEMA_MISMATCH"
    http_status = 422


class MalformedCSVError(AppError):
    """CSV could not be parsed (ragged rows, bad encoding)."""

    code = "MALFORMED_CSV"
    http_status = 422


class DataQualityFailedError(AppError):
    """Upload parsed successfully but failed `DataQualityValidator` checks
    other than missing required columns (that case is `SCHEMA_MISMATCH`)."""

    code = "DATA_QUALITY_FAILED"
    http_status = 422


class FileTooLargeError(AppError):
    code = "FILE_TOO_LARGE"
    http_status = 413


class PredictionFailedError(AppError):
    """Model/pipeline raised while scoring valid, schema-conformant input."""

    code = "PREDICTION_FAILED"
    http_status = 500


class ModelUnavailableError(AppError):
    """No production model artifact is available to serve predictions from
    (missing/misconfigured `ml/artifacts/`, not a client input problem)."""

    code = "MODEL_UNAVAILABLE"
    http_status = 503


class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404
