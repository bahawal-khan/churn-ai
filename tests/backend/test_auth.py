from __future__ import annotations

import logging
import re

from backend.auth.session import SESSION_COOKIE_NAME


def _extract_reset_token(caplog) -> str:
    match = re.search(r"token=(\S+)", caplog.text)
    assert match, f"reset token not found in logs: {caplog.text!r}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------


def test_signup_happy_path_creates_user_and_issues_session(anon_client, signup_payload):
    resp = anon_client.post("/api/auth/signup", json=signup_payload)
    assert resp.status_code == 201
    body = resp.get_json()["data"]
    assert body["email"] == signup_payload["email"]
    assert body["full_name"] == signup_payload["full_name"]
    assert "password" not in body
    assert "password_hash" not in body
    assert SESSION_COOKIE_NAME in resp.headers.get("Set-Cookie", "")


def test_signup_duplicate_email_returns_409(anon_client, signup_payload):
    first = anon_client.post("/api/auth/signup", json=signup_payload)
    assert first.status_code == 201

    second = anon_client.post("/api/auth/signup", json=signup_payload)
    assert second.status_code == 409
    body = second.get_json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_signup_duplicate_email_case_insensitive(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    upper = dict(signup_payload)
    upper["email"] = signup_payload["email"].upper()
    resp = anon_client.post("/api/auth/signup", json=upper)
    assert resp.status_code == 409


def test_signup_weak_password_rejected(anon_client, signup_payload):
    weak = dict(signup_payload, password="weak", confirm_password="weak")
    resp = anon_client.post("/api/auth/signup", json=weak)
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_signup_password_missing_special_char_rejected(anon_client, signup_payload):
    weak = dict(signup_payload, password="Password1", confirm_password="Password1")
    resp = anon_client.post("/api/auth/signup", json=weak)
    assert resp.status_code == 422


def test_signup_password_confirmation_mismatch_rejected(anon_client, signup_payload):
    mismatched = dict(signup_payload, confirm_password="Different1!")
    resp = anon_client.post("/api/auth/signup", json=mismatched)
    assert resp.status_code == 422


def test_signup_invalid_email_format_rejected(anon_client, signup_payload):
    bad = dict(signup_payload, email="not-an-email")
    resp = anon_client.post("/api/auth/signup", json=bad)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_happy_path(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    resp = anon_client.post(
        "/api/auth/login", json={"email": signup_payload["email"], "password": signup_payload["password"]}
    )
    assert resp.status_code == 200
    assert resp.get_json()["data"]["email"] == signup_payload["email"]


def test_login_wrong_password_returns_401_generic_message(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    resp = anon_client.post(
        "/api/auth/login", json={"email": signup_payload["email"], "password": "WrongPass1!"}
    )
    assert resp.status_code == 401
    body = resp.get_json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert "invalid" in body["error"]["message"].lower()


def test_login_unknown_email_returns_same_generic_401(anon_client):
    resp = anon_client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "WhoKnows1!"}
    )
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "INVALID_CREDENTIALS"


# ---------------------------------------------------------------------------
# Session persistence / protected-route rejection
# ---------------------------------------------------------------------------


def test_session_endpoint_returns_current_user_when_authenticated(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    resp = anon_client.get("/api/auth/session")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["email"] == signup_payload["email"]


def test_session_endpoint_returns_401_when_not_authenticated(anon_client):
    resp = anon_client.get("/api/auth/session")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_protected_route_rejects_missing_session(anon_client):
    resp = anon_client.get("/api/models")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_protected_route_rejects_garbage_session_cookie(anon_client):
    anon_client.set_cookie(SESSION_COOKIE_NAME, "not-a-real-session-id", domain="localhost")
    resp = anon_client.get("/api/models")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_reload_after_login_stays_authenticated(anon_client, signup_payload):
    """`docs/BACKEND_SPEC.md` §4: "the frontend calls GET /api/auth/session on
    app load; a valid cookie returns the current user" — simulated here as
    two independent requests on the same client (shared cookie jar)."""
    anon_client.post("/api/auth/signup", json=signup_payload)
    first = anon_client.get("/api/auth/session")
    second = anon_client.get("/api/auth/session")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.get_json()["data"]["id"] == second.get_json()["data"]["id"]


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_revokes_session(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    logout_resp = anon_client.post("/api/auth/logout")
    assert logout_resp.status_code == 200

    resp = anon_client.get("/api/auth/session")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_logout_without_session_is_rejected(anon_client):
    resp = anon_client.post("/api/auth/logout")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Session expiration
# ---------------------------------------------------------------------------


def test_expired_session_is_rejected(anon_client, signup_payload, monkeypatch):
    import backend.routes.auth as auth_route

    monkeypatch.setattr(auth_route, "_session_ttl_days", lambda: 0)
    resp = anon_client.post("/api/auth/signup", json=signup_payload)
    assert resp.status_code == 201

    # TTL of 0 days means `expires_at == created_at`; the very next request
    # is already at/after expiry, matching `docs/DATABASE_SPEC.md` §2.3's
    # `expires_at > now()` validity condition.
    resp = anon_client.get("/api/auth/session")
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------


def test_forgot_password_always_returns_200_for_unknown_email(anon_client):
    resp = anon_client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert resp.status_code == 200


def test_forgot_password_returns_200_for_known_email(anon_client, signup_payload):
    anon_client.post("/api/auth/signup", json=signup_payload)
    resp = anon_client.post("/api/auth/forgot-password", json={"email": signup_payload["email"]})
    assert resp.status_code == 200


def test_reset_password_happy_path_and_revokes_existing_sessions(anon_client, signup_payload, caplog):
    caplog.set_level(logging.INFO, logger="churnai.backend.auth")
    anon_client.post("/api/auth/signup", json=signup_payload)

    # The signup session should be revoked once reset succeeds.
    anon_client.post("/api/auth/forgot-password", json={"email": signup_payload["email"]})
    raw_token = _extract_reset_token(caplog)

    new_password = "NewStrongPass1!"
    reset_resp = anon_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": new_password, "confirm_password": new_password},
    )
    assert reset_resp.status_code == 200

    # Old session (from signup) must now be invalid.
    stale_check = anon_client.get("/api/auth/session")
    assert stale_check.status_code == 401

    # New password logs in; old password no longer works.
    login_new = anon_client.post(
        "/api/auth/login", json={"email": signup_payload["email"], "password": new_password}
    )
    assert login_new.status_code == 200

    login_old = anon_client.post(
        "/api/auth/login", json={"email": signup_payload["email"], "password": signup_payload["password"]}
    )
    assert login_old.status_code == 401


def test_reset_password_rejects_invalid_token(anon_client):
    resp = anon_client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token", "new_password": "NewStrongPass1!", "confirm_password": "NewStrongPass1!"},
    )
    assert resp.status_code == 422


def test_reset_password_rejects_reused_token(anon_client, signup_payload, caplog):
    caplog.set_level(logging.INFO, logger="churnai.backend.auth")
    anon_client.post("/api/auth/signup", json=signup_payload)
    anon_client.post("/api/auth/forgot-password", json={"email": signup_payload["email"]})
    raw_token = _extract_reset_token(caplog)

    new_password = "NewStrongPass1!"
    first = anon_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": new_password, "confirm_password": new_password},
    )
    assert first.status_code == 200

    second = anon_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": "AnotherPass1!", "confirm_password": "AnotherPass1!"},
    )
    assert second.status_code == 422
    assert "invalid" in second.get_json()["error"]["message"].lower() or "expired" in second.get_json()["error"]["message"].lower()


# ---------------------------------------------------------------------------
# Profile update (theme preference / onboarding completion)
# ---------------------------------------------------------------------------


def test_update_profile_theme_preference(client):
    resp = client.patch("/api/auth/profile", json={"theme_preference": "light"})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["theme_preference"] == "light"


def test_update_profile_onboarding_completed(client):
    resp = client.patch("/api/auth/profile", json={"onboarding_completed": True})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["onboarding_completed_at"] is not None


def test_update_profile_includes_organization_name(client):
    resp = client.patch("/api/auth/profile", json={"theme_preference": "dark"})
    assert resp.status_code == 200
    body = resp.get_json()["data"]
    assert body["organization_name"]


def test_session_response_includes_organization_name(client):
    resp = client.get("/api/auth/session")
    assert resp.status_code == 200
    assert resp.get_json()["data"]["organization_name"]


def test_update_profile_rejects_unauthenticated(anon_client):
    resp = anon_client.patch("/api/auth/profile", json={"theme_preference": "light"})
    assert resp.status_code == 401
    assert resp.get_json()["error"]["code"] == "SESSION_EXPIRED"


def test_update_profile_rejects_invalid_theme_value(client):
    resp = client.patch("/api/auth/profile", json={"theme_preference": "blue"})
    assert resp.status_code == 422
    assert resp.get_json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_profile_rejects_empty_body(client):
    resp = client.patch("/api/auth/profile", json={})
    assert resp.status_code == 422


def test_reset_password_rejects_expired_token(app, signup_payload, caplog):
    caplog.set_level(logging.INFO, logger="churnai.backend.auth")
    anon_client = app.test_client()
    anon_client.post("/api/auth/signup", json=signup_payload)

    # A TTL of 0 minutes means the token is already expired by the time the
    # reset request is made (`expires_at <= now()`).
    app.config["PASSWORD_RESET_TOKEN_TTL_MINUTES"] = 0
    anon_client.post("/api/auth/forgot-password", json={"email": signup_payload["email"]})
    raw_token = _extract_reset_token(caplog)

    new_password = "NewStrongPass1!"
    resp = anon_client.post(
        "/api/auth/reset-password",
        json={"token": raw_token, "new_password": new_password, "confirm_password": new_password},
    )
    assert resp.status_code == 422
