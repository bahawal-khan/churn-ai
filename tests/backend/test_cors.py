"""CORS allow-list (`docs/BACKEND_SPEC.md` §9, `docs/DEPLOYMENT.md` §2-3,
Phase 11).

`flask-cors` only sets `Access-Control-Allow-Origin` on the response when the
request's `Origin` header is in the configured allow-list, and it never
reflects an arbitrary/wildcard origin when `supports_credentials=True`. These
tests assert that behavior directly against a real app instance rather than
mocking `flask_cors`, so a config regression (e.g. accidentally allowing `*`)
would actually fail the suite.
"""

from __future__ import annotations

import pytest

from backend.app import create_app
from backend.config import TestConfig


class _CorsTestConfig(TestConfig):
    CORS_ALLOWED_ORIGINS = "http://localhost:3000,https://churnai.vercel.app"


@pytest.fixture()
def cors_client(tiny_artifacts_dir, test_db_url, tmp_path):
    class _Config(_CorsTestConfig):
        UPLOAD_STORAGE_DIR = tmp_path / "uploads"
        REPORTS_STORAGE_DIR = tmp_path / "reports"

    app = create_app(_Config)
    return app.test_client()


def test_allowed_localhost_origin_is_echoed_back(cors_client):
    resp = cors_client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"


def test_allowed_production_origin_is_echoed_back(cors_client):
    resp = cors_client.get("/api/health", headers={"Origin": "https://churnai.vercel.app"})
    assert resp.status_code == 200
    assert resp.headers.get("Access-Control-Allow-Origin") == "https://churnai.vercel.app"


def test_non_allowlisted_origin_is_rejected(cors_client):
    resp = cors_client.get("/api/health", headers={"Origin": "https://evil-attacker.example"})
    assert resp.status_code == 200  # same-origin/non-browser callers still get a response...
    # ...but no CORS header is granted to that origin, so a real browser
    # blocks the cross-origin script from reading the response.
    assert resp.headers.get("Access-Control-Allow-Origin") != "https://evil-attacker.example"
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_preflight_for_non_allowlisted_origin_is_rejected(cors_client):
    resp = cors_client.options(
        "/api/auth/login",
        headers={
            "Origin": "https://evil-attacker.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert "Access-Control-Allow-Origin" not in resp.headers


def test_preflight_for_allowlisted_origin_permits_credentials(cors_client):
    resp = cors_client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert resp.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
    assert resp.headers.get("Access-Control-Allow-Credentials") == "true"


def test_no_wildcard_origin_ever_configured():
    """Structural check on the actual default config, independent of the
    fixture override above — `docs/DEPLOYMENT.md` §3: "No wildcard (`*`)
    origin in any environment.\""""
    origins = [o.strip() for o in TestConfig.CORS_ALLOWED_ORIGINS.split(",")]
    assert "*" not in origins
