"""Shared response envelope helper (`docs/API.md`: `{ "data": ..., "request_id": ... }`)."""

from __future__ import annotations

from typing import Any

from flask import g, jsonify


def success_response(data: Any, status: int = 200):
    return jsonify({"data": data, "request_id": getattr(g, "request_id", None)}), status
