"""Flask-Limiter on `/api/auth/*`, `/api/training/*`, `/api/predictions/*`
(`docs/BACKEND_SPEC.md` §9, Phase 11).

Limits are disabled by default in `TestConfig` (`backend/config.py`) so the
rest of the suite isn't flaky — these tests opt back in per-app with a small,
deliberately low limit so a handful of requests is enough to trip `429`
without slowing the suite down. Each test builds its own app (fresh
`Limiter` storage, see `backend/rate_limit.py`), so limits never leak between
tests or between this file and the rest of the suite.
"""

from __future__ import annotations

import pytest

from backend.app import create_app
from backend.config import TestConfig


def _make_app(tmp_path, **rate_limit_overrides):
    class _Config(TestConfig):
        RATELIMIT_ENABLED = True
        UPLOAD_STORAGE_DIR = tmp_path / "uploads"
        REPORTS_STORAGE_DIR = tmp_path / "reports"
        RATE_LIMIT_AUTH = rate_limit_overrides.get("auth", "1000 per minute")
        RATE_LIMIT_TRAINING = rate_limit_overrides.get("training", "1000 per minute")
        RATE_LIMIT_PREDICTION = rate_limit_overrides.get("prediction", "1000 per minute")

    return create_app(_Config)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_auth_endpoint_returns_429_with_rate_limited_code_after_threshold(tiny_artifacts_dir, test_db_url, tmp_path):
    app = _make_app(tmp_path, auth="3 per minute")
    test_client = app.test_client()

    responses = [
        test_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "WrongPass1!"})
        for _ in range(4)
    ]

    assert [r.status_code for r in responses[:3]] == [401, 401, 401]
    breached = responses[3]
    assert breached.status_code == 429
    assert breached.get_json()["error"]["code"] == "RATE_LIMITED"


def test_auth_rate_limit_applies_to_every_route_in_the_blueprint(tiny_artifacts_dir, test_db_url, tmp_path):
    """Blueprint-wide limit (`backend/app.py`: `limiter.limit(...)(auth_bp)`)
    applies the same configured limit to every route under `/api/auth/*`
    individually (Flask-Limiter's default blueprint semantics: one counter
    per endpoint, not one pooled counter for the whole blueprint) — so a
    route other than `/login` (e.g. `/forgot-password`) is rate limited too."""
    app = _make_app(tmp_path, auth="2 per minute")
    test_client = app.test_client()

    responses = [
        test_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"}) for _ in range(3)
    ]

    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 429
    assert responses[2].get_json()["error"]["code"] == "RATE_LIMITED"


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def test_training_endpoint_returns_429_after_threshold(tiny_artifacts_dir, test_db_url, tmp_path):
    app = _make_app(tmp_path, training="2 per minute")
    test_client = app.test_client()
    signup = test_client.post(
        "/api/auth/signup",
        json={
            "email": "trainer@example.com",
            "password": "StrongPass1!",
            "confirm_password": "StrongPass1!",
            "full_name": "Trainer",
        },
    )
    assert signup.status_code == 201

    responses = [test_client.get("/api/training/jobs") for _ in range(3)]

    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 429
    assert responses[2].get_json()["error"]["code"] == "RATE_LIMITED"


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------


def test_prediction_endpoint_returns_429_after_threshold(tiny_artifacts_dir, test_db_url, tmp_path):
    app = _make_app(tmp_path, prediction="2 per minute")
    test_client = app.test_client()
    signup = test_client.post(
        "/api/auth/signup",
        json={
            "email": "predictor@example.com",
            "password": "StrongPass1!",
            "confirm_password": "StrongPass1!",
            "full_name": "Predictor",
        },
    )
    assert signup.status_code == 201

    responses = [test_client.get("/api/predictions") for _ in range(3)]

    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 429
    assert responses[2].get_json()["error"]["code"] == "RATE_LIMITED"


# ---------------------------------------------------------------------------
# Configurability / dev-test usability
# ---------------------------------------------------------------------------


def test_limit_threshold_is_configurable_per_app(tiny_artifacts_dir, test_db_url, tmp_path):
    """A stricter configured limit trips sooner — proves the threshold is
    actually read from config, not hardcoded in the decorator."""
    app = _make_app(tmp_path, auth="1 per minute")
    test_client = app.test_client()

    first = test_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})
    second = test_client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"})

    assert first.status_code == 401
    assert second.status_code == 429


def test_rate_limiting_disabled_by_default_in_test_config(client):
    """The shared `client`/`app` fixtures (`conftest.py`) use the plain
    `TestConfig`, which sets `RATELIMIT_ENABLED = False` — normal
    development/test workflows are never rate limited unless a test opts in,
    matching every other test file in this suite firing many requests per
    test without hitting a 429."""
    responses = [client.get("/api/models") for _ in range(10)]
    assert all(r.status_code == 200 for r in responses)
