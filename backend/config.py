"""Environment-driven Flask configuration (`docs/BACKEND_SPEC.md` §1, §9).

`SECRET_KEY`/`DATABASE_URL`/session settings are sourced only from
environment variables (`docs/DEPLOYMENT.md` §2) and never hardcoded; the
defaults below are safe, documented local-dev fallbacks, not production
values — production always sets these via real env vars.
"""

from __future__ import annotations

import os
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent


class Config:
    ENV = os.environ.get("FLASK_ENV", "development")
    DEBUG = ENV == "development"
    TESTING = False

    # File upload limits (`docs/BACKEND_SPEC.md` §6): 25 MB default, override
    # via env var without a code change.
    MAX_UPLOAD_SIZE_MB = int(os.environ.get("CHURNAI_MAX_UPLOAD_SIZE_MB", "25"))
    MAX_CONTENT_LENGTH = MAX_UPLOAD_SIZE_MB * 1024 * 1024

    API_VERSION = os.environ.get("CHURNAI_API_VERSION", "0.1.0-phase8")

    JSON_SORT_KEYS = False

    # Flask's own session/cookie signing key (`docs/BACKEND_SPEC.md` §9).
    # ChurnAI's own session cookie (`backend/auth/session.py`) carries an
    # opaque server-side session id, not a signed Flask session, but
    # `SECRET_KEY` is still required by Flask itself and is a documented
    # env var regardless (`docs/DEPLOYMENT.md` §2).
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")

    DATABASE_URL = os.environ.get("DATABASE_URL")  # None -> db/session.py's own default path

    # `docs/DATABASE_SPEC.md` §2.3 / `docs/DEPLOYMENT.md` §2: fixed absolute
    # session TTL from issuance, default 7 days.
    SESSION_TTL_DAYS = int(os.environ.get("SESSION_TTL_DAYS", "7"))
    # `docs/BACKEND_SPEC.md` §4: e.g. 30 minutes.
    PASSWORD_RESET_TOKEN_TTL_MINUTES = int(
        os.environ.get("PASSWORD_RESET_TOKEN_TTL_MINUTES", "30")
    )
    # `docs/DEPLOYMENT.md` §2: true in production; local HTTP dev needs it
    # off or browsers silently refuse to store the cookie.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    # `docs/BACKEND_SPEC.md` §6: uploaded CSVs are stored under a
    # server-generated UUID filename, outside any statically-served path.
    # Separate from `ml/artifacts/` (model output, `docs/DATABASE_SPEC.md`
    # §2.7) — this directory holds dataset *input* files (§2.5).
    UPLOAD_STORAGE_DIR = Path(
        os.environ.get("CHURNAI_UPLOAD_DIR", str(_BACKEND_DIR / "storage" / "uploads"))
    )
    # Generated report exports (`docs/API.md` `/api/reports`). No `reports`
    # table exists in `docs/DATABASE_SPEC.md` §2 — a gap in the spec set, not
    # an oversight here (flagged in the Phase 9 report). Reports are
    # persisted as files with a JSON metadata sidecar, scoped per-org by
    # directory, rather than inventing a new migration for this phase.
    REPORTS_STORAGE_DIR = Path(
        os.environ.get("CHURNAI_REPORTS_DIR", str(_BACKEND_DIR / "storage" / "reports"))
    )


class TestConfig(Config):
    TESTING = True
    ENV = "testing"
    DEBUG = False
    SESSION_COOKIE_SECURE = False
