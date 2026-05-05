"""Test infrastructure per Section 0 of test_guidance.md."""
import asyncio
import itertools
import os
import sys
from unittest.mock import AsyncMock, patch

import psycopg2
import pytest


BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
for path in (REPO_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test")
os.environ["RESEND_API_KEY"] = ""

_counter = itertools.count(1)


def _unique_email() -> str:
    return f"test-{next(_counter)}@internal.test"


def pytest_configure(config: pytest.Config) -> None:
    """Stub out all email sending for the entire test session."""
    patch("email_service.send_verification_email", new=AsyncMock(return_value=True)).start()
    patch("email_service.send_password_reset_email", new=AsyncMock(return_value=True)).start()


@pytest.fixture
def isolated_state(monkeypatch):
    from db import close_pool, ensure_schema_admin, reset_database_admin
    from backend.main import _clear_rate_limit_state

    asyncio.run(close_pool())
    asyncio.run(ensure_schema_admin())
    asyncio.run(reset_database_admin())
    _clear_rate_limit_state()
    yield
    asyncio.run(close_pool())
    asyncio.run(reset_database_admin())
    _clear_rate_limit_state()


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test")
    return url.replace("postgresql+asyncpg://", "postgresql://")


def _db_conn():
    return psycopg2.connect(_db_url())


def verify_test_user(user_id: str) -> None:
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email_verified = true WHERE id = %s::uuid", (user_id,))
        conn.commit()
    finally:
        conn.close()


def _make_user(client, plan="free", email=None, name="Test User", password="Password1", existing_user=None):
    """Seed anon session, register or re-login existing user. Returns user dict."""
    if existing_user is not None:
        # Re-login an existing user into this client session
        client.get("/api/catalog")
        login = client.post("/api/auth/login", json={
            "email": existing_user.get("email", email),
            "password": password,
        })
        if login.status_code == 200:
            return login.json().get("user", existing_user)
        return existing_user
    client.get("/api/catalog")
    reg = client.post("/api/auth/register", json={
        "email": email or _unique_email(),
        "name": name,
        "password": password,
    })
    assert reg.status_code == 201, f"Register failed: {reg.text}"
    user = reg.json()["user"]
    if plan != "free":
        up = client.post("/api/user/plan", json={
            "user_id": user["id"],
            "new_plan": plan,
            "context": "test-setup",
        })
        assert up.status_code == 200, f"Plan upgrade failed: {up.text}"
    return user


def _insert_submission(user_id: str, *, track: str, question_id: int, is_correct: bool, submitted_at=None, duration_ms=None) -> None:
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            if submitted_at:
                cur.execute(
                    """INSERT INTO submissions (user_id, track, question_id, is_correct, code, submitted_at, duration_ms)
                       VALUES (%s::uuid, %s, %s, %s, 'test', %s, %s)""",
                    (user_id, track, question_id, is_correct, submitted_at, duration_ms),
                )
            else:
                cur.execute(
                    """INSERT INTO submissions (user_id, track, question_id, is_correct, code, duration_ms)
                       VALUES (%s::uuid, %s, %s, %s, 'test', %s)""",
                    (user_id, track, question_id, is_correct, duration_ms),
                )
        conn.commit()
    finally:
        conn.close()


def _insert_progress(user_id: str, *, track: str, question_id: int, solved_at=None) -> None:
    # user_progress uses 'topic' column; map track → topic if needed
    topic = track.replace("-", "_")  # python-data → python_data
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            if solved_at:
                cur.execute(
                    """INSERT INTO user_progress (user_id, topic, question_id, solved_at)
                       VALUES (%s::uuid, %s, %s, %s)
                       ON CONFLICT (user_id, question_id, topic) DO NOTHING""",
                    (user_id, topic, question_id, solved_at),
                )
            else:
                cur.execute(
                    """INSERT INTO user_progress (user_id, topic, question_id)
                       VALUES (%s::uuid, %s, %s)
                       ON CONFLICT (user_id, question_id, topic) DO NOTHING""",
                    (user_id, topic, question_id),
                )
        conn.commit()
    finally:
        conn.close()


def _create_email_verification_token(user_id: str) -> str:
    """Directly insert an email verification token via psycopg2."""
    import secrets
    from datetime import datetime, timedelta, timezone
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            # Invalidate existing unused tokens
            cur.execute(
                """UPDATE email_verification_tokens
                   SET used_at = now()
                   WHERE user_id = %s::uuid AND used_at IS NULL AND expires_at > now()""",
                (user_id,),
            )
            cur.execute(
                """INSERT INTO email_verification_tokens (user_id, token, expires_at)
                   VALUES (%s::uuid, %s, %s)""",
                (user_id, token, expires_at),
            )
        conn.commit()
    finally:
        conn.close()
    return token


def _create_password_reset_token(user_id: str) -> str:
    """Directly insert a password reset token via psycopg2."""
    import secrets
    from datetime import datetime, timedelta, timezone
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            # Invalidate existing unused tokens
            cur.execute(
                """UPDATE password_reset_tokens
                   SET used_at = now()
                   WHERE user_id = %s::uuid AND used_at IS NULL AND expires_at > now()""",
                (user_id,),
            )
            cur.execute(
                """INSERT INTO password_reset_tokens (user_id, token, expires_at)
                   VALUES (%s::uuid, %s, %s)""",
                (user_id, token, expires_at),
            )
        conn.commit()
    finally:
        conn.close()
    return token


def _create_oauth_state_token(provider: str = "google") -> str:
    """Directly insert an OAuth state token via psycopg2."""
    import secrets
    from datetime import datetime, timedelta, timezone
    state_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO oauth_states (state_token, expires_at)
                   VALUES (%s, %s)""",
                (state_token, expires_at),
            )
        conn.commit()
    finally:
        conn.close()
    return state_token


def _consume_oauth_state_token(state_token: str) -> None:
    """Mark an OAuth state token as used via psycopg2."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE oauth_states SET used_at = now() WHERE state_token = %s",
                (state_token,),
            )
        conn.commit()
    finally:
        conn.close()
