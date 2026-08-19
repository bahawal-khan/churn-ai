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


class InvalidCredentialsError(AppError):
    """Bad email/password on login (`docs/BACKEND_SPEC.md` §4: generic
    message on any failure, no user-enumeration hint via wording)."""

    code = "INVALID_CREDENTIALS"
    http_status = 401


class SessionExpiredError(AppError):
    """Missing, expired, or revoked session cookie."""

    code = "SESSION_EXPIRED"
    http_status = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    http_status = 403


class EmailAlreadyExistsError(AppError):
    """Signup with an email already in use (`docs/API.md` auth table)."""

    code = "EMAIL_ALREADY_EXISTS"
    http_status = 409


class InvalidResetTokenError(AppError):
    """Reset token missing, expired, already used, or malformed."""

    code = "VALIDATION_ERROR"
    http_status = 422


class TrainingLabelsRequiredError(AppError):
    """No valid binary target column available on the dataset
    (`docs/PROJECT_SPEC.md` §16 — blocks `POST /api/training/jobs`)."""

    code = "TRAINING_LABELS_REQUIRED"
    http_status = 422


class TrainingFailedError(AppError):
    """Training pipeline raised while fitting/evaluating a company-specific
    model (`docs/BACKEND_SPEC.md` §7)."""

    code = "TRAINING_FAILED"
    http_status = 500


class DatasetInUseError(AppError):
    """Dataset delete blocked because a model still references it
    (`models.trained_on_dataset_id` is `RESTRICT`, `docs/API.md` datasets
    table, `docs/DATABASE_SPEC.md` §3)."""

    code = "DATASET_IN_USE"
    http_status = 409
