"""Test infrastructure per Section 0 of test_guidance.md."""
import asyncio
import itertools
import os
import sys
from unittest.mock import AsyncMock, patch
from urllib.parse import urlparse

import psycopg2
import pytest


BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
for path in (REPO_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TESTING", "1")
os.environ["RESEND_API_KEY"] = ""

# Always point at the test database.
# If DATABASE_URL is already set in the shell but does NOT end in '_test',
# override it — a shell-exported main-DB URL must never reach the reset fixture.
_DEFAULT_TEST_DB = "postgresql://postgres:postgres@localhost:5432/sql_practice_test"
_db_url_from_env = os.environ.get("DATABASE_URL", "")
if not urlparse(_db_url_from_env).path.lstrip("/").endswith("_test"):
    os.environ["DATABASE_URL"] = _DEFAULT_TEST_DB
del _db_url_from_env, _DEFAULT_TEST_DB

_counter = itertools.count(1)


def _unique_email() -> str:
    return f"test-{next(_counter)}@internal.test"


def pytest_configure(config: pytest.Config) -> None:
    """Stub out all email sending for the entire test session."""
    patch("email_service.send_verification_email", new=AsyncMock(return_value=True)).start()
    patch("email_service.send_password_reset_email", new=AsyncMock(return_value=True)).start()


@pytest.fixture(scope="session", autouse=True)
def _test_db_schema():
    """Run schema DDL once per test session — tables and indexes don't change between tests."""
    from db import ensure_schema_admin
    asyncio.run(ensure_schema_admin())


def _reset_db_sync() -> None:
    """Truncate user-facing tables using synchronous psycopg2.

    Using asyncio.run() for TRUNCATE created a race condition: asyncpg connections
    from the previous TestClient's event loop could still be open (in OS cleanup)
    when the next asyncio.run() created new connections, causing intermittent deadlocks
    between TRUNCATE and CREATE INDEX.  A synchronous psycopg2 call reduces that race,
    but the deadlock can still occur if asyncpg GC hasn't released its connections yet.
    Retry logic handles the remaining intermittent cases.
    """
    import time

    _active_url = os.environ.get("DATABASE_URL", "")
    _db_name = urlparse(_active_url).path.lstrip("/")
    assert _db_name.endswith("_test"), (
        f"_reset_db_sync refused: DATABASE_URL targets '{_db_name}', "
        "which is not a test database."
    )
    last_err: Exception | None = None
    for attempt in range(5):
        if attempt > 0:
            time.sleep(0.1 * attempt)  # 0.1 s, 0.2 s, 0.3 s, 0.4 s
        conn = _db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "TRUNCATE TABLE mock_session_questions, mock_sessions, submissions, "
                    "plan_changes, payment_events, user_sample_seen, user_progress, "
                    "sessions, users RESTART IDENTITY CASCADE"
                )
            conn.commit()
            return
        except psycopg2.errors.DeadlockDetected as exc:
            conn.rollback()
            last_err = exc
        finally:
            conn.close()
    raise last_err  # type: ignore[misc]


@pytest.fixture
def isolated_state(monkeypatch):
    from db import close_pool
    from backend.main import _clear_rate_limit_state

    # Tripwire: if DATABASE_URL somehow still points at a non-test DB, abort
    # immediately before touching any data.
    _active_url = os.environ.get("DATABASE_URL", "")
    _db_name = urlparse(_active_url).path.lstrip("/")
    assert _db_name.endswith("_test"), (
        f"isolated_state refused: DATABASE_URL targets '{_db_name}', which does not "
        "end in '_test'. Tests must not run against the main database. "
        f"Full URL: {_active_url!r}"
    )

    # The app lifespan calls ensure_schema() on every TestClient start (non-PROD path),
    # which runs CREATE INDEX IF NOT EXISTS.  _reset_db_sync() runs TRUNCATE, which takes
    # AccessExclusiveLock on all listed tables.  When a TestClient teardown overlaps with
    # the next TestClient's startup, TRUNCATE and CREATE INDEX deadlock on the same table.
    # _test_db_schema (scope="session") already created all indexes once, so it is safe to
    # no-op ensure_schema() for the duration of each test.
    import main as _main_module
    monkeypatch.setattr(_main_module, "ensure_schema", AsyncMock(return_value=None))

    asyncio.run(close_pool())
    _reset_db_sync()
    _clear_rate_limit_state()
    yield
    asyncio.run(close_pool())
    _reset_db_sync()
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


def _insert_submission(user_id: str, question_id: int, *, track: str, is_correct: bool, submitted_at=None, duration_ms=None) -> None:
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


def _insert_progress(user_id: str, question_id: int, *, track: str, solved_at=None) -> None:
    # user_progress uses 'topic' column; topic == track slug directly
    topic = track
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
