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

    # Phase 11 (`docs/DEPLOYMENT.md` §2-3, `docs/BACKEND_SPEC.md` §9): exact
    # env var name pinned in DEPLOYMENT.md — comma-separated allow-list, never
    # a wildcard. Defaults to local dev only; production sets this to the
    # real Vercel domain(s) via env var, no code change required.
    CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000")

    # Phase 11 (`docs/BACKEND_SPEC.md` §9): Flask-Limiter, in-process/memory
    # storage — suitable for the free-tier single-worker deployment target
    # (`docs/DEPLOYMENT.md` §1), documented upgrade path to a shared/Redis
    # backend if the app ever scales beyond one worker. Limit strings use
    # Flask-Limiter's own syntax (e.g. "20 per minute") and are read fresh
    # per-request via a callable, so they're configurable without a restart
    # surviving a code change.
    RATELIMIT_ENABLED = os.environ.get("CHURNAI_RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_STORAGE_URI = os.environ.get("CHURNAI_RATE_LIMIT_STORAGE_URI", "memory://")
    RATE_LIMIT_AUTH = os.environ.get("CHURNAI_RATE_LIMIT_AUTH", "20 per minute")
    RATE_LIMIT_TRAINING = os.environ.get("CHURNAI_RATE_LIMIT_TRAINING", "10 per minute")
    RATE_LIMIT_PREDICTION = os.environ.get("CHURNAI_RATE_LIMIT_PREDICTION", "60 per minute")


class TestConfig(Config):
    TESTING = True
    ENV = "testing"
    DEBUG = False
    SESSION_COOKIE_SECURE = False
    # Rate limiting is real production behavior (`BACKEND_SPEC.md` §9) but
    # would make the rest of the suite flaky — most tests fire many requests
    # from the same test-client "IP" in a tight loop. Disabled by default
    # here so existing Phase 7-10 tests stay deterministic; `test_rate_limiting.py`
    # opts back in per-app via its own config subclass.
    RATELIMIT_ENABLED = False
