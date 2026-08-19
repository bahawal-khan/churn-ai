"""Environment-driven Flask configuration (`docs/BACKEND_SPEC.md` §1, §9).

Phase 7 scope note: no auth/session work exists yet, so no `SECRET_KEY` (or
any other secret) is defined here — one will be added, sourced only from an
environment variable and never hardcoded, when the auth phase needs it.
"""

from __future__ import annotations

import os


class Config:
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = ENV == "development"
    TESTING = False

    # File upload limits (`docs/BACKEND_SPEC.md` §6): 25 MB default, override
    # via env var without a code change.
    MAX_UPLOAD_SIZE_MB = int(os.environ.get("CHURNAI_MAX_UPLOAD_SIZE_MB", "25"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    API_VERSION = os.environ.get("CHURNAI_API_VERSION", "0.1.0-phase7")

    JSON_SORT_KEYS = False


class TestConfig(Config):
    TESTING = True
    ENV = "testing"
    DEBUG = False
