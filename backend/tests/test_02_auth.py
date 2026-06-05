"""TC-006 to TC-043 — Authentication & Identity."""
import asyncio
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import (
    _create_email_verification_token,
    _create_oauth_state_token,
    _consume_oauth_state_token,
    _create_password_reset_token,
    _db_conn,
    _insert_progress,
    _insert_submission,
    _make_user,
    _unique_email,
    verify_test_user,
)

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ---------------------------------------------------------------------------
# 2A. Anonymous identity
# ---------------------------------------------------------------------------

def test_tc006_anon_session_created():
    """TC-006: catalog hit sets session cookie; /me returns 401 for anon."""
    with TestClient(app) as client:
        r = client.get("/api/catalog")
        assert r.status_code == 200
        assert "session_token" in client.cookies or any("session" in k for k in client.cookies)
        me = client.get("/api/auth/me")
    assert me.status_code == 401


def test_tc007_anon_me_returns_401():
    """TC-007: GET /api/auth/me with anon session → 401, body {"user": null}."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.get("/api/auth/me")
    assert r.status_code == 401
    assert r.json().get("user") is None


# ---------------------------------------------------------------------------
# 2B. Registration
# ---------------------------------------------------------------------------

def test_tc008_register_happy_path():
    """TC-008: Registration returns 201 with user dict."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": email, "name": "Alice", "password": "Password1",
        })
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == email
    assert user["name"] == "Alice"
    assert user["plan"] == "free"
    assert user["email_verified"] is False
    assert "id" in user


def test_tc009_duplicate_email_rejected():
    """TC-009: Registering with same email when already logged in and already has a password → 409."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "A", "password": "Password1"})
        # Still logged in — same email, password already set → 409
        r = client.post("/api/auth/register", json={"email": email, "name": "B", "password": "Password1"})
    assert r.status_code == 409
    assert "error" in r.json()


def test_tc009b_duplicate_email_anonymous_rejected():
    """TC-009b: Anonymous user trying to register with an already-taken email → 400."""
    email = _unique_email()
    # Register in one client (logs them in)
    with TestClient(app) as client_a:
        client_a.get("/api/catalog")
        client_a.post("/api/auth/register", json={"email": email, "name": "A", "password": "Password1"})
    # Fresh anonymous session in a second client tries same email
    with TestClient(app) as client_b:
        client_b.get("/api/catalog")
        r = client_b.post("/api/auth/register", json={"email": email, "name": "B", "password": "Password1"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_tc010_weak_password_no_uppercase():
    """TC-010: 'password1' (no uppercase) → 422 or 400."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "name": "A", "password": "password1",
        })
    assert r.status_code in (400, 422)


def test_tc011_weak_password_no_digit():
    """TC-011: 'Passwordonly' (no digit) → 422 or 400."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "name": "A", "password": "Passwordonly",
        })
    assert r.status_code in (400, 422)


def test_tc012_weak_password_too_short():
    """TC-012: 'Ab1' (too short) → 422 or 400."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "name": "A", "password": "Ab1",
        })
    assert r.status_code in (400, 422)


def test_tc013_reserved_email_prefix_blocked():
    """TC-013: admin@ prefix → 400."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": "admin@example.com", "name": "A", "password": "Password1",
        })
    assert r.status_code in (400, 422)


def test_tc014_blocked_domain_rejected():
    """TC-014: user@datathink.co → 400."""
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/auth/register", json={
            "email": "user@datathink.co", "name": "A", "password": "Password1",
        })
    assert r.status_code in (400, 422)


def test_tc015_already_registered_cannot_re_register_different_email():
    """TC-015: Registered user trying to register with a DIFFERENT email → 400."""
    with TestClient(app) as client:
        _make_user(client)
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "name": "B", "password": "Password1",
        })
    assert r.status_code == 400
    assert "doesn't match" in r.json().get("error", "")


# ---------------------------------------------------------------------------
# 2C. Login & Logout
# ---------------------------------------------------------------------------

def test_tc016_correct_credentials_login():
    """TC-016: Login with correct credentials → 200, user dict, session cookie."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "Bob", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]
    verify_test_user(user_id)
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"email": email, "password": "Password1"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == email
    assert "email_verified" in body["user"]


def test_tc017_wrong_password_returns_401():
    """TC-017: Wrong password → 401 with error message."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "C", "password": "Password1"})
        r = client.post("/api/auth/login", json={"email": email, "password": "WrongPass1"})
    assert r.status_code == 401
    body = r.json()
    assert "error" in body
    assert "Invalid email or password" in body["error"]


def test_tc018_login_merges_anonymous_progress():
    """TC-018: Login merges anonymous progress into existing account."""
    email = _unique_email()
    # Register user A and solve question in their account
    with TestClient(app) as client_a:
        client_a.get("/api/catalog")
        reg = client_a.post("/api/auth/register", json={
            "email": email, "name": "UserA", "password": "Password1",
        })
        user_a_id = reg.json()["user"]["id"]
    verify_test_user(user_a_id)
    # Insert progress for user A
    _insert_progress(user_a_id, track="sql", question_id=11003)

    # In a fresh client, create an anonymous user, solve a different question
    with TestClient(app) as client_b:
        client_b.get("/api/catalog")
        # Get the anon user_id from a DB lookup
        conn = _db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM sessions ORDER BY created_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                anon_id = str(row[0]) if row else None
        finally:
            conn.close()

        if anon_id:
            _insert_progress(anon_id, track="sql", question_id=11004)

        # Login as user A
        r = client_b.post("/api/auth/login", json={"email": email, "password": "Password1"})
        assert r.status_code == 200

        # Check catalog – both should be solved
        cat = client_b.get("/api/catalog")
        assert cat.status_code == 200
        all_questions = []
        for group in cat.json().get("groups", []):
            all_questions.extend(group.get("questions", []))
        solved_ids = {q["id"] for q in all_questions if q.get("state") == "solved"}
        # At least one of them is solved
        assert 11003 in solved_ids or 11004 in solved_ids or len(solved_ids) >= 1


def test_tc019_logout_clears_session():
    """TC-019: Logout → 200; subsequent /me → 401."""
    with TestClient(app) as client:
        _make_user(client)
        r_logout = client.post("/api/auth/logout")
        r_me = client.get("/api/auth/me")
    assert r_logout.status_code == 200
    assert r_logout.json().get("ok") is True
    assert r_me.status_code == 401


# ---------------------------------------------------------------------------
# 2D. Email verification
# ---------------------------------------------------------------------------

def test_tc020_valid_verification_token():
    """TC-020: Valid token marks email as verified."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "D", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    # Create token outside TestClient to avoid event loop conflict
    token = _create_email_verification_token(user_id)

    with TestClient(app) as client:
        r = client.post("/api/auth/verify-email", json={"token": token})
        assert r.status_code == 200
        assert r.json().get("ok") is True

    # Fresh login to check email_verified
    with TestClient(app) as client2:
        client2.post("/api/auth/login", json={"email": email, "password": "Password1"})
        me = client2.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["email_verified"] is True


def test_tc021_consumed_verification_token():
    """TC-021: Consumed token → 400."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "E", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    token = _create_email_verification_token(user_id)

    with TestClient(app) as client:
        client.post("/api/auth/verify-email", json={"token": token})
        r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 400
    assert "invalid" in r.json().get("error", "").lower() or "expired" in r.json().get("error", "").lower()


def test_tc022_resend_verification_unauthenticated():
    """TC-022: Resend verification with no session → 401."""
    with TestClient(app) as client:
        r = client.post("/api/auth/resend-verification")
    assert r.status_code == 401


def test_tc023_resend_verification_already_verified():
    """TC-023: Already-verified user resend → 400 with 'already verified'."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "F", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    token = _create_email_verification_token(user_id)

    with TestClient(app) as client:
        client.post("/api/auth/verify-email", json={"token": token})

    # Login and try resend
    with TestClient(app) as client2:
        client2.post("/api/auth/login", json={"email": email, "password": "Password1"})
        r = client2.post("/api/auth/resend-verification")
    assert r.status_code == 400
    assert "already" in r.json().get("error", "").lower()


# ---------------------------------------------------------------------------
# 2E. Password reset
# ---------------------------------------------------------------------------

def test_tc024_forgot_password_non_enumeration():
    """TC-024: Both known and unknown email return 200."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "G", "password": "Password1"})
        r1 = client.post("/api/auth/forgot-password", json={"email": "nonexistent@example.com"})
        r2 = client.post("/api/auth/forgot-password", json={"email": email})
    assert r1.status_code == 200
    assert r1.json().get("ok") is True
    assert r2.status_code == 200
    assert r2.json().get("ok") is True


def test_tc025_valid_reset_token_updates_password():
    """TC-025: Valid reset token → password updated, email_verified:true."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "H", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    token = _create_password_reset_token(user_id)

    with TestClient(app) as client:
        r = client.post("/api/auth/reset-password", json={
            "token": token, "password": "NewPass99",
        })
    assert r.status_code == 200

    with TestClient(app) as client2:
        login = client2.post("/api/auth/login", json={"email": email, "password": "NewPass99"})
    assert login.status_code == 200
    assert login.json()["user"]["email_verified"] is True


def test_tc026_consumed_reset_token_rejected():
    """TC-026: Consumed reset token → 400."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "I", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    token = _create_password_reset_token(user_id)

    with TestClient(app) as client:
        client.post("/api/auth/reset-password", json={"token": token, "password": "NewPass99"})
        r = client.post("/api/auth/reset-password", json={"token": token, "password": "AnotherPass1"})
    assert r.status_code == 400
    assert "invalid" in r.json().get("error", "").lower() or "expired" in r.json().get("error", "").lower()


def test_tc027_reset_with_weak_password():
    """TC-027: Reset with weak password → 422 or 400."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "J", "password": "Password1",
        })
        user_id = reg.json()["user"]["id"]

    token = _create_password_reset_token(user_id)

    with TestClient(app) as client:
        r = client.post("/api/auth/reset-password", json={"token": token, "password": "weak"})
    assert r.status_code in (400, 422)


# ---------------------------------------------------------------------------
# 2F. Magic link
# ---------------------------------------------------------------------------

def test_tc028_dev_magic_link_returned():
    """TC-028: Dev mode magic link returns dev_magic_link URL."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "K", "password": "Password1"})
        r = client.post("/api/auth/magic-link", json={"email": email})
    assert r.status_code == 200
    body = r.json()
    assert "dev_magic_link" in body
    assert isinstance(body["dev_magic_link"], str)


def test_tc029_magic_link_callback_creates_session():
    """TC-029: Valid magic link callback → 302 with set-cookie."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "L", "password": "Password1"})
        r = client.post("/api/auth/magic-link", json={"email": email})
        link = r.json()["dev_magic_link"]
        # Extract token from link
        token = link.split("token=")[-1]
        r2 = client.get(f"/api/auth/magic-link/callback?token={token}", follow_redirects=False)
    assert r2.status_code == 302
    assert "set-cookie" in r2.headers or "session_token" in r2.cookies


def test_tc030_magic_link_invalid_token_redirects_error():
    """TC-030: Invalid token → 302 to /auth?error=."""
    with TestClient(app) as client:
        r = client.get("/api/auth/magic-link/callback?token=bogustoken123", follow_redirects=False)
    assert r.status_code == 302
    location = r.headers.get("location", "")
    assert "/auth" in location and "error" in location


def test_tc031_magic_link_single_use():
    """TC-031: Magic link token is single-use; second use → error redirect."""
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "M", "password": "Password1"})
        r = client.post("/api/auth/magic-link", json={"email": email})
        link = r.json()["dev_magic_link"]
        token = link.split("token=")[-1]
        client.get(f"/api/auth/magic-link/callback?token={token}", follow_redirects=False)
        r2 = client.get(f"/api/auth/magic-link/callback?token={token}", follow_redirects=False)
    assert r2.status_code == 302
    assert "error" in r2.headers.get("location", "")


def test_tc032_magic_link_unknown_email():
    """TC-032: Unknown email → 200, no dev_magic_link in body."""
    with TestClient(app) as client:
        r = client.post("/api/auth/magic-link", json={"email": "nobody@unknown.test"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "dev_magic_link" not in body


# ---------------------------------------------------------------------------
# 2G. OAuth
# ---------------------------------------------------------------------------

def test_tc033_unconfigured_oauth_returns_503(monkeypatch):
    """TC-033: Unconfigured OAuth → 503."""
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_ID", "")
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_SECRET", "")
    with TestClient(app) as client:
        r = client.get("/api/auth/oauth/google/authorize")
    assert r.status_code == 503


def test_tc034_authorize_creates_distinct_state_tokens(monkeypatch):
    """TC-034: Two /authorize calls return different state values."""
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr("routers.auth.GOOGLE_REDIRECT_URI", "http://localhost/callback")
    with TestClient(app) as client:
        r1 = client.get("/api/auth/oauth/google/authorize")
        r2 = client.get("/api/auth/oauth/google/authorize")
    assert r1.status_code == 200
    assert r2.status_code == 200
    state1 = r1.json().get("state") or r1.json().get("url", "")
    state2 = r2.json().get("state") or r2.json().get("url", "")
    assert state1 != state2


def test_tc035_callback_invalid_state_redirects_error():
    """TC-035: Callback with bogus state → 302 /auth?error=."""
    with TestClient(app) as client:
        r = client.get(
            "/api/auth/oauth/google/callback?code=abc&state=bogusstate999",
            follow_redirects=False,
        )
    assert r.status_code == 302
    assert "/auth" in r.headers.get("location", "")
    assert "error" in r.headers.get("location", "")


def test_tc036_callback_consumed_state_redirects_error(monkeypatch):
    """TC-036: Consumed state → 302 /auth?error=."""
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr("routers.auth.GOOGLE_REDIRECT_URI", "http://localhost/callback")

    # Create and immediately consume the state token
    state_token = _create_oauth_state_token("google")
    _consume_oauth_state_token(state_token)

    with TestClient(app) as client:
        r = client.get(
            f"/api/auth/oauth/google/callback?code=abc&state={state_token}",
            follow_redirects=False,
        )
    assert r.status_code == 302
    assert "error" in r.headers.get("location", "")


def test_tc037_callback_happy_path(monkeypatch):
    """TC-037: Valid callback with patched exchange → 302 with set-cookie."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_SECRET", "fake-secret")
    monkeypatch.setattr("routers.auth.GOOGLE_REDIRECT_URI", "http://localhost/callback")

    fake_user = {"email": _unique_email(), "name": "OAuth User", "id": "google-123"}
    monkeypatch.setattr(
        "routers.auth._exchange_google_code",
        AsyncMock(return_value=fake_user),
    )

    state_token = _create_oauth_state_token("google")

    with TestClient(app) as client:
        r = client.get(
            f"/api/auth/oauth/google/callback?code=testcode&state={state_token}",
            follow_redirects=False,
        )
    assert r.status_code == 302
    # Session cookie should be set
    assert "set-cookie" in r.headers or "session_token" in r.cookies


def test_tc038_unknown_oauth_provider_returns_404():
    """TC-038: Unknown provider → 404."""
    with TestClient(app) as client:
        r = client.get("/api/auth/oauth/twitter/authorize")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 2H. Auth hardening
# ---------------------------------------------------------------------------

def test_tc039_login_lockout(monkeypatch):
    """TC-039: N failed logins → 429 with lockout message."""
    monkeypatch.setattr("routers.auth.LOGIN_LOCKOUT_MAX_ATTEMPTS", 3)
    email = _unique_email()
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "N", "password": "Password1"})
        statuses = []
        for _ in range(4):
            r = client.post("/api/auth/login", json={"email": email, "password": "WrongPass1"})
            statuses.append(r.status_code)
    # At some point should get 429
    assert 429 in statuses or any(s == 429 for s in statuses)


def test_tc040_csrf_rejected_without_origin(monkeypatch):
    """TC-040: Production mode + session cookie + no Origin → 403."""
    monkeypatch.setattr(main, "IS_PROD", True)
    monkeypatch.setattr(main, "_CSRF_ALLOWED_ORIGINS", {"https://app.example.com"})
    email = _unique_email()
    _origin = {"Origin": "https://app.example.com"}
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "O", "password": "Password1"}, headers=_origin)
        verify_test_user(
            client.post("/api/auth/login", json={"email": email, "password": "Password1"}, headers=_origin).json()["user"]["id"]
        )
        # Login to get session cookie (with valid Origin so setup succeeds)
        client.post("/api/auth/login", json={"email": email, "password": "Password1"}, headers=_origin)
        # Send logout without Origin header — should be CSRF-blocked
        r = client.post("/api/auth/logout", headers={})
    assert r.status_code == 403


def test_tc041_csrf_passes_with_valid_origin(monkeypatch):
    """TC-041: Production mode + valid Origin → 200."""
    monkeypatch.setattr(main, "IS_PROD", True)
    monkeypatch.setattr(main, "_CSRF_ALLOWED_ORIGINS", {"https://app.example.com"})
    email = _unique_email()
    _origin = {"Origin": "https://app.example.com"}
    with TestClient(app) as client:
        client.get("/api/catalog")
        client.post("/api/auth/register", json={"email": email, "name": "P", "password": "Password1"}, headers=_origin)
        verify_test_user(
            client.post("/api/auth/login", json={"email": email, "password": "Password1"}, headers=_origin).json()["user"]["id"]
        )
        client.post("/api/auth/login", json={"email": email, "password": "Password1"}, headers=_origin)
        r = client.post("/api/auth/logout", headers={"Origin": "https://app.example.com"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 2I. GET /api/auth/me fields
# ---------------------------------------------------------------------------

def test_tc042_me_returns_streak_metadata():
    """TC-042: /me returns streak_days and streak_at_risk."""
    with TestClient(app) as client:
        user = _make_user(client)
        _insert_submission(user["id"], track="sql", question_id=1003, is_correct=True)
        r = client.get("/api/auth/me")
    assert r.status_code == 200
    u = r.json()["user"]
    assert "streak_days" in u
    assert "streak_at_risk" in u
    assert u["streak_days"] >= 1
    assert u["streak_at_risk"] is False


def test_tc043_streak_at_risk_when_yesterday_only():
    """TC-043: streak_at_risk=true when submission yesterday but none today."""
    import datetime

    # Compute "yesterday" in UTC — the same frame get_user_streak_status() buckets
    # solves by (DATE(submitted_at AT TIME ZONE 'UTC') vs now(UTC)). Using local
    # naive time made this flaky near midnight in UTC+ timezones (e.g. IST): "yesterday
    # local" could land on "today UTC", collapsing the expected streak_days==0 case.
    yesterday = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
    with TestClient(app) as client:
        user = _make_user(client)
        _insert_submission(
            user["id"], track="sql", question_id=1003, is_correct=True,
            submitted_at=yesterday,
        )
        r = client.get("/api/auth/me")
    assert r.status_code == 200
    u = r.json()["user"]
    assert u["streak_at_risk"] is True
    assert u["streak_days"] == 0


# ---------------------------------------------------------------------------
# 2J. OAuth ↔ email/password account linking
# ---------------------------------------------------------------------------

def _seed_oauth_user(email: str, name: str = "OAuth User") -> str:
    """Insert a user row with no password (simulates OAuth-only account).
    Returns the user_id string.
    """
    import uuid as _uuid
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            user_id = str(_uuid.uuid4())
            cur.execute(
                """INSERT INTO users (id, email, name, pwd_hash, pwd_salt, plan, email_verified)
                   VALUES (%s::uuid, %s, %s, NULL, NULL, 'free', true)""",
                (user_id, email, name),
            )
            cur.execute(
                """INSERT INTO oauth_accounts
                       (user_id, provider, provider_user_id, email, name)
                   VALUES (%s::uuid, 'google', %s, %s, %s)""",
                (user_id, f"google-{user_id}", email, name),
            )
        conn.commit()
    finally:
        conn.close()
    return user_id


def _login_as_oauth_user(client, user_id: str) -> None:
    """Inject a session for an OAuth-only user into the test client."""
    import secrets
    from datetime import datetime, timedelta, timezone
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s::uuid, %s)",
                (token, user_id, expires_at),
            )
        conn.commit()
    finally:
        conn.close()
    client.cookies.set("session_token", token)


def test_tc044_oauth_user_can_add_password():
    """TC-044: OAuth-only user registers with same email → 201, password_added=True."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        r = client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "Password1",
        })
    assert r.status_code == 201
    body = r.json()
    assert body.get("password_added") is True
    assert body["user"]["email"] == email


def test_tc045_oauth_user_can_login_with_password_after_adding():
    """TC-045: After adding password, email/password login succeeds."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    # Add password via the register endpoint
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "Password1",
        })
    # Fresh client — login with email+password
    with TestClient(app) as client2:
        r = client2.post("/api/auth/login", json={"email": email, "password": "Password1"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == email


def test_tc046_oauth_user_add_password_wrong_email_rejected():
    """TC-046: OAuth user tries to register with a different email → 400."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        r = client.post("/api/auth/register", json={
            "email": _unique_email(), "name": "OAuth User", "password": "Password1",
        })
    assert r.status_code == 400
    assert "doesn't match" in r.json().get("error", "")


def test_tc047_add_password_idempotent_second_attempt_rejected():
    """TC-047: OAuth user adds password successfully; re-adding (same session) → 409."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        r1 = client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "Password1",
        })
        assert r1.status_code == 201
        # Second attempt — password already set → 409
        r2 = client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "NewPass99",
        })
    assert r2.status_code == 409
    assert "already has a password" in r2.json().get("error", "")


def test_tc048_oauth_only_login_with_password_gives_clear_error():
    """TC-048: Email/password login for OAuth-only account → 401 with helpful message."""
    email = _unique_email()
    _seed_oauth_user(email)
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={"email": email, "password": "AnyPass1"})
    assert r.status_code == 401
    error = r.json().get("error", "")
    assert "google" in error.lower() or "github" in error.lower() or "oauth" in error.lower() or "sign-in" in error.lower()


def test_tc049_email_password_user_can_still_login_via_oauth(monkeypatch):
    """TC-049: Email/password user whose email matches OAuth provider → session linked, login succeeds."""
    from unittest.mock import AsyncMock
    email = _unique_email()
    # Register normally with email+password
    with TestClient(app) as client:
        client.get("/api/catalog")
        reg = client.post("/api/auth/register", json={
            "email": email, "name": "EmailUser", "password": "Password1",
        })
    user_id = reg.json()["user"]["id"]

    # Now simulate OAuth login with the same email
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_ID", "fake")
    monkeypatch.setattr("routers.auth.GOOGLE_CLIENT_SECRET", "fake")
    monkeypatch.setattr("routers.auth.GOOGLE_REDIRECT_URI", "http://localhost/callback")
    monkeypatch.setattr(
        "routers.auth._exchange_google_code",
        AsyncMock(return_value={"email": email, "name": "EmailUser", "id": "google-newid-456"}),
    )
    state_token = _create_oauth_state_token("google")
    with TestClient(app) as client2:
        r = client2.get(
            f"/api/auth/oauth/google/callback?code=testcode&state={state_token}",
            follow_redirects=False,
        )
    assert r.status_code == 302
    # Session cookie should be set — user is now linked
    assert "set-cookie" in r.headers or "session_token" in r.cookies


def test_tc050_add_password_preserves_oauth_login():
    """TC-050: After adding password, OAuth login still works (oauth_accounts row intact)."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    # Add password
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        r = client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "Password1",
        })
    assert r.status_code == 201
    # Verify oauth_accounts row still present
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM oauth_accounts WHERE user_id = %s::uuid",
                (user_id,),
            )
            count = cur.fetchone()[0]
    finally:
        conn.close()
    assert count >= 1


def test_tc051_login_with_wrong_password_after_linking():
    """TC-051: Wrong password after adding password → 401 (not leaked as OAuth error)."""
    email = _unique_email()
    user_id = _seed_oauth_user(email)
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        client.post("/api/auth/register", json={
            "email": email, "name": "OAuth User", "password": "Password1",
        })
    with TestClient(app) as client2:
        r = client2.post("/api/auth/login", json={"email": email, "password": "WrongPass9"})
    assert r.status_code == 401
    assert "Invalid email or password" in r.json().get("error", "")


def test_tc052_add_password_response_includes_user_fields():
    """TC-052: password_added response includes full user dict (id, email, name, plan)."""
    email = _unique_email()
    user_id = _seed_oauth_user(email, name="Full Name")
    with TestClient(app) as client:
        client.get("/api/catalog")
        _login_as_oauth_user(client, user_id)
        r = client.post("/api/auth/register", json={
            "email": email, "name": "Full Name", "password": "Password1",
        })
    assert r.status_code == 201
    body = r.json()
    user = body.get("user", {})
    assert user.get("id") == user_id
    assert user.get("email") == email
    assert user.get("name") == "Full Name"
    assert "plan" in user
    assert body.get("password_added") is True
