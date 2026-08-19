"""Flask error handler registration (`docs/BACKEND_SPEC.md` §7): maps every
`AppError`, standard HTTP exception, and unexpected exception to the fixed
error envelope. Full detail (stack trace, code, message) is always logged
server-side; only the sanitized envelope ever reaches the client.
"""

from __future__ import annotations

import logging

from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException

from backend.errors.exceptions import AppError

logger = logging.getLogger("churnai.backend")

# Fallback codes for HTTP errors Flask/Werkzeug raises itself (routing,
# method mismatch, body-too-large) that never pass through an `AppError`.
_CODE_BY_HTTP_STATUS = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    429: "RATE_LIMITED",
}


def _error_envelope(code: str, message: str, details: dict, status: int):
    body = {
        "error": {"code": code, "message": message, "details": details or {}},
        "request_id": getattr(g, "request_id", None),
    }
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def _handle_app_error(err: AppError):
        logger.warning(
            "app_error request_id=%s code=%s status=%s message=%s details=%s",
            getattr(g, "request_id", None), err.code, err.http_status, err.message, err.details,
        )
        return _error_envelope(err.code, err.message, err.details, err.http_status)

    @app.errorhandler(HTTPException)
    def _handle_http_exception(err: HTTPException):
        status = err.code or 500
        code = _CODE_BY_HTTP_STATUS.get(status, "INTERNAL_ERROR")
        logger.warning(
            "http_exception request_id=%s status=%s description=%s",
            getattr(g, "request_id", None), status, err.description,
        )
        # Werkzeug's own descriptions for 4xx are safe, generic client-facing
        # text (e.g. "Request Entity Too Large") — never a stack trace/path.
        message = err.description if status < 500 else "An unexpected error occurred."
        return _error_envelope(code, message, {}, status)

    @app.errorhandler(Exception)
    def _handle_unexpected(err: Exception):
        logger.exception("unhandled_exception request_id=%s", getattr(g, "request_id", None))
        return _error_envelope("INTERNAL_ERROR", "An unexpected error occurred.", {}, 500)
