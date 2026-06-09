from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import (
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE_SECONDS,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
    MAGIC_LINK_TTL_MINUTES,
    OAUTH_STATE_TTL_MINUTES,
    get_async_database_url,
)


logger = logging.getLogger(__name__)

_ITERATIONS = 260_000
SESSION_COOKIE_NAME = "session_token"
SESSION_TTL = timedelta(days=30)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

_SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    name TEXT,
    pwd_hash TEXT,
    pwd_salt TEXT,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    login_locked_until TIMESTAMPTZ,
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'elite', 'lifetime_pro', 'lifetime_elite')),
    razorpay_customer_id TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    upgraded_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS user_progress (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    topic TEXT NOT NULL DEFAULT 'sql',
    solved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, question_id, topic)
);

CREATE TABLE IF NOT EXISTS user_sample_seen (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    difficulty TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    topic TEXT NOT NULL DEFAULT 'sql',
    seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, difficulty, question_id, topic)
);

CREATE TABLE IF NOT EXISTS payment_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    user_id UUID REFERENCES users(id),
    processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_summary JSONB
);

CREATE TABLE IF NOT EXISTS plan_changes (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    old_plan TEXT NOT NULL,
    new_plan TEXT NOT NULL,
    context TEXT,
    payment_event_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS submissions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    code TEXT,
    duration_ms INTEGER,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user_topic ON user_progress(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_plan_changes_user ON plan_changes(user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_user_question ON submissions(user_id, question_id, track);
CREATE INDEX IF NOT EXISTS idx_submissions_user_recent ON submissions(user_id, submitted_at DESC);

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    email TEXT,
    name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS password_reset_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user ON oauth_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_user ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_reset_tokens_expires ON password_reset_tokens(expires_at);

ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS login_locked_until TIMESTAMPTZ;
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user ON email_verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_expires ON email_verification_tokens(expires_at);

CREATE TABLE IF NOT EXISTS oauth_states (
    state_token TEXT PRIMARY KEY,
    user_agent_hash TEXT,
    ip_prefix TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states(expires_at);

CREATE TABLE IF NOT EXISTS magic_link_tokens (
    token TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_user ON magic_link_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_magic_link_tokens_expires ON magic_link_tokens(expires_at);

CREATE TABLE IF NOT EXISTS mock_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode TEXT NOT NULL,
    track TEXT NOT NULL,
    difficulty TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    time_limit_s INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    focus_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    role TEXT
);

CREATE INDEX IF NOT EXISTS idx_mock_sessions_user_started ON mock_sessions(user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS mock_session_questions (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES mock_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL,
    track TEXT NOT NULL,
    position INTEGER NOT NULL,
    is_solved BOOLEAN NOT NULL DEFAULT false,
    submitted_at TIMESTAMPTZ,
    final_code TEXT,
    time_spent_s INTEGER,
    is_follow_up BOOLEAN NOT NULL DEFAULT false,
    follow_up_dimension TEXT
);

CREATE INDEX IF NOT EXISTS idx_mock_session_questions_session ON mock_session_questions(session_id);

CREATE TABLE IF NOT EXISTS mock_chain_consumption (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    parent_id INTEGER NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_id BIGINT REFERENCES mock_sessions(id) ON DELETE SET NULL,
    reclaimed BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (user_id, parent_id)
);

CREATE INDEX IF NOT EXISTS idx_mcc_user_active ON mock_chain_consumption(user_id) WHERE NOT reclaimed;

ALTER TABLE mock_session_questions ADD COLUMN IF NOT EXISTS is_follow_up BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE mock_session_questions ADD COLUMN IF NOT EXISTS follow_up_dimension TEXT;
ALTER TABLE mock_sessions ADD COLUMN IF NOT EXISTS focus_fallback BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE mock_sessions ADD COLUMN IF NOT EXISTS role TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS razorpay_subscription_id TEXT;
"""


def _session_factory_or_raise() -> async_sessionmaker[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("Database pool is not initialized")
    return _session_factory


def _normalize_async_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def _admin_engine(database_url: str | None = None) -> AsyncEngine:
    target = database_url or get_async_database_url()
    return create_async_engine(
        _normalize_async_database_url(target),
        future=True,
        poolclass=NullPool,
    )


def _user_from_mapping(row: RowMapping | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "id": str(row["id"]),
        "email": row["email"],
        "name": row["name"],
        "plan": row["plan"],
        "email_verified": bool(row.get("email_verified", False)),
        "razorpay_customer_id": row.get("razorpay_customer_id"),
        "razorpay_subscription_id": row.get("razorpay_subscription_id"),
        "created_at": row.get("created_at"),
        "upgraded_at": row.get("upgraded_at"),
    }


def _hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    return digest.hex(), salt


def _normalize_uuid_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        _ITERATIONS,
    )
    return secrets.compare_digest(digest.hex(), stored_hash)


# PBKDF2 (260k iterations) is ~22 ms of synchronous CPU per call. The sync helpers
# above stay the implementation (and are reused by offline scripts + seeding), but
# every request-path caller MUST go through these async wrappers so the hash runs in
# a worker thread instead of blocking the single event loop. See
# offload.run_blocking_hash.
async def hash_password(password: str) -> tuple[str, str]:
    """Async PBKDF2 hash — runs the blocking hash off the event loop."""
    from offload import run_blocking_hash

    return await run_blocking_hash(_hash_password, password)


async def verify_password_async(password: str, stored_hash: str, salt: str) -> bool:
    """Async PBKDF2 verify — runs the blocking verify off the event loop."""
    from offload import run_blocking_hash

    return await run_blocking_hash(verify_password, password, stored_hash, salt)


async def init_pool() -> None:
    global _engine, _session_factory

    if _engine is not None:
        return

    _engine = create_async_engine(
        get_async_database_url(),
        future=True,
        pool_pre_ping=True,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE_SECONDS,
        connect_args={"timeout": 5},  # fail fast; health endpoint reports 503 otherwise
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_pool() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def ensure_schema() -> None:
    if _engine is None:
        raise RuntimeError("Database pool is not initialized")

    async with _engine.begin() as conn:
        for statement in [part.strip() for part in _SCHEMA_SQL.split(";") if part.strip()]:
            await conn.execute(text(statement))


def _assert_test_db(url: str, fn_name: str) -> None:
    """Refuse to run destructive operations against a non-test database."""
    try:
        db_name = urlparse(url).path.lstrip("/")
    except Exception:
        db_name = url
    if not db_name.endswith("_test"):
        raise RuntimeError(
            f"{fn_name}() refused: the target database '{db_name}' does not end in "
            "'_test'. This function must only run against test databases. "
            "Set DATABASE_URL to a *_test database before running tests."
        )


async def reset_database() -> None:
    if _engine is None:
        raise RuntimeError("Database pool is not initialized")

    _assert_test_db(get_async_database_url(), "reset_database")
    async with _engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE mock_session_questions, mock_sessions, submissions, plan_changes, payment_events, user_sample_seen, user_progress, sessions, users RESTART IDENTITY CASCADE"))


async def ensure_schema_admin(database_url: str | None = None) -> None:
    engine = _admin_engine(database_url)
    try:
        async with engine.begin() as conn:
            for statement in [part.strip() for part in _SCHEMA_SQL.split(";") if part.strip()]:
                await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def reset_database_admin(database_url: str | None = None) -> None:
    target = database_url or get_async_database_url()
    _assert_test_db(target, "reset_database_admin")
    engine = _admin_engine(target)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE TABLE mock_session_questions, mock_sessions, submissions, plan_changes, payment_events, user_sample_seen, user_progress, sessions, users RESTART IDENTITY CASCADE"
                )
            )
    finally:
        await engine.dispose()


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                FROM users
                WHERE id = CAST(:user_id AS UUID)
                """
            ),
            {"user_id": user_id},
        )
        return _user_from_mapping(result.mappings().first())


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                FROM users
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        return _user_from_mapping(result.mappings().first())


async def get_user_by_razorpay_customer_id(customer_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                FROM users
                WHERE razorpay_customer_id = :customer_id
                """
            ),
            {"customer_id": customer_id},
        )
        return _user_from_mapping(result.mappings().first())


async def get_user_credentials_by_email(email: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, email, name, plan, email_verified, pwd_hash, pwd_salt, failed_login_attempts, login_locked_until
                FROM users
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return {
            "id": str(row["id"]),
            "email": row["email"],
            "name": row["name"],
            "plan": row["plan"],
            "email_verified": bool(row["email_verified"]),
            "pwd_hash": row["pwd_hash"],
            "pwd_salt": row["pwd_salt"],
            "failed_login_attempts": int(row.get("failed_login_attempts") or 0),
            "login_locked_until": row.get("login_locked_until"),
        }


async def clear_login_lock_state(user_id: str) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE users
                SET failed_login_attempts = 0,
                    login_locked_until = NULL
                WHERE id = CAST(:user_id AS UUID)
                """
            ),
            {"user_id": user_id},
        )
        await session.commit()


async def register_failed_login_attempt(
    user_id: str,
    *,
    current_failed_attempts: int,
    max_attempts: int,
    lockout_window_minutes: int,
) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        should_lock = int(current_failed_attempts) + 1 >= int(max_attempts)
        if should_lock:
            statement = text(
                """
                UPDATE users
                SET failed_login_attempts = 0,
                    login_locked_until = now() + make_interval(mins => :lockout_window_minutes)
                WHERE id = CAST(:user_id AS UUID)
                RETURNING failed_login_attempts, login_locked_until
                """
            )
            params = {
                "user_id": user_id,
                "lockout_window_minutes": lockout_window_minutes,
            }
        else:
            statement = text(
                """
                UPDATE users
                SET failed_login_attempts = failed_login_attempts + 1,
                    login_locked_until = NULL
                WHERE id = CAST(:user_id AS UUID)
                RETURNING failed_login_attempts, login_locked_until
                """
            )
            params = {"user_id": user_id}

        result = await session.execute(
            statement,
            params,
        )
        await session.commit()
        row = result.mappings().first()
        if row is None:
            return None
        return {
            "failed_login_attempts": int(row.get("failed_login_attempts") or 0),
            "login_locked_until": row.get("login_locked_until"),
        }


async def create_anonymous_user() -> dict[str, Any]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO users (email, name, pwd_hash, pwd_salt, plan)
                VALUES (NULL, NULL, NULL, NULL, 'free')
                RETURNING id, email, name, plan, razorpay_customer_id, created_at, upgraded_at
                """
            )
        )
        await session.commit()
        return _user_from_mapping(result.mappings().one())  # type: ignore[return-value]


async def upgrade_anonymous_to_registered(user_id: str, email: str, name: str, password: str) -> dict[str, Any] | None | str:
    pwd_hash, pwd_salt = await hash_password(password)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        try:
            result = await session.execute(
                text(
                    """
                    UPDATE users
                    SET email = :email,
                        name = :name,
                        pwd_hash = :pwd_hash,
                        pwd_salt = :pwd_salt,
                        upgraded_at = now()
                    WHERE id = CAST(:user_id AS UUID)
                      AND email IS NULL
                    RETURNING id, email, name, plan, email_verified, razorpay_customer_id, created_at, upgraded_at
                    """
                ),
                {
                    "user_id": user_id,
                    "email": email,
                    "name": name,
                    "pwd_hash": pwd_hash,
                    "pwd_salt": pwd_salt,
                },
            )
        except IntegrityError:
            await session.rollback()
            return "duplicate_email"
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return _user_from_mapping(row)


async def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + SESSION_TTL
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO sessions (token, user_id, expires_at)
                VALUES (:token, CAST(:user_id AS UUID), :expires_at)
                """
            ),
            {
                "token": token,
                "user_id": user_id,
                "expires_at": expires_at,
            },
        )
        await session.commit()
    return token


async def get_session_user(token: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT u.id, u.email, u.name, u.plan, u.email_verified, u.razorpay_customer_id, u.razorpay_subscription_id, u.created_at, u.upgraded_at
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token = :token
                  AND s.expires_at > now()
                """
            ),
            {"token": token},
        )
        return _user_from_mapping(result.mappings().first())


async def delete_session(token: str) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM sessions WHERE token = :token"),
            {"token": token},
        )
        await session.commit()


async def delete_user(user_id: str) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM users WHERE id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.commit()


async def delete_user_account(user_id: str) -> None:
    """Delete a registered user and all associated data in a single transaction.

    Order matters:
    1. plan_changes — NOT NULL FK, no cascade; must be removed before the user row.
    2. payment_events — nullable FK; anonymised rather than deleted to preserve the
       financial audit trail.
    3. users — CASCADE wipes sessions, user_progress, user_sample_seen, submissions,
       oauth_accounts, password_reset_tokens, email_verification_tokens,
       magic_link_tokens, mock_sessions, and mock_session_questions automatically.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM plan_changes WHERE user_id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.execute(
            text("UPDATE payment_events SET user_id = NULL WHERE user_id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.execute(
            text("DELETE FROM users WHERE id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.commit()


async def get_solved_ids(user_id: str, topic: str = "sql") -> set[int]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT question_id
                FROM user_progress
                WHERE user_id = CAST(:user_id AS UUID)
                  AND topic = :topic
                """
            ),
            {"user_id": user_id, "topic": topic},
        )
        return {int(row[0]) for row in result.fetchall()}


async def mark_solved(user_id: str, question_id: int, topic: str = "sql") -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO user_progress (user_id, question_id, topic, solved_at)
                VALUES (CAST(:user_id AS UUID), :question_id, :topic, now())
                ON CONFLICT (user_id, question_id, topic)
                DO UPDATE SET solved_at = EXCLUDED.solved_at
                """
            ),
            {
                "user_id": user_id,
                "question_id": int(question_id),
                "topic": topic,
            },
        )
        await session.commit()


async def clear_progress(user_id: str) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text("DELETE FROM user_progress WHERE user_id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.commit()


async def get_seen_sample_counts(user_id: str) -> dict[tuple[str, str], int]:
    """Aggregate seen-sample counts grouped by (topic, difficulty) for one user.

    Returns a mapping {(topic, difficulty): count}. Used by the sample summary
    endpoint to mark which (track, difficulty) tiles the user has tried.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT topic, difficulty, COUNT(*) AS n
                FROM user_sample_seen
                WHERE user_id = CAST(:user_id AS UUID)
                GROUP BY topic, difficulty
                """
            ),
            {"user_id": user_id},
        )
        return {(str(row[0]), str(row[1])): int(row[2]) for row in result.fetchall()}


async def get_seen_sample_ids(user_id: str, difficulty: str, topic: str = "sql") -> set[int]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT question_id
                FROM user_sample_seen
                WHERE user_id = CAST(:user_id AS UUID)
                  AND difficulty = :difficulty
                  AND topic = :topic
                """
            ),
            {
                "user_id": user_id,
                "difficulty": difficulty,
                "topic": topic,
            },
        )
        return {int(row[0]) for row in result.fetchall()}


async def mark_sample_seen(user_id: str, difficulty: str, question_id: int, topic: str = "sql") -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO user_sample_seen (user_id, difficulty, question_id, topic, seen_at)
                VALUES (CAST(:user_id AS UUID), :difficulty, :question_id, :topic, now())
                ON CONFLICT (user_id, difficulty, question_id, topic)
                DO UPDATE SET seen_at = EXCLUDED.seen_at
                """
            ),
            {
                "user_id": user_id,
                "difficulty": difficulty,
                "question_id": int(question_id),
                "topic": topic,
            },
        )
        await session.commit()


async def clear_seen_samples(user_id: str, difficulty: str | None = None, topic: str | None = None) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        if difficulty is None and topic is None:
            await session.execute(
                text("DELETE FROM user_sample_seen WHERE user_id = CAST(:user_id AS UUID)"),
                {"user_id": user_id},
            )
        else:
            clauses = ["user_id = CAST(:user_id AS UUID)"]
            params: dict[str, object] = {"user_id": user_id}
            if difficulty is not None:
                clauses.append("difficulty = :difficulty")
                params["difficulty"] = difficulty
            if topic is not None:
                clauses.append("topic = :topic")
                params["topic"] = topic
            await session.execute(
                text(
                    f"""
                    DELETE FROM user_sample_seen
                    WHERE {" AND ".join(clauses)}
                    """
                ),
                params,
            )
        await session.commit()


async def get_user_plan(user_id: str) -> str | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT plan FROM users WHERE id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        row = result.first()
        return None if row is None else str(row[0])


async def set_user_plan(user_id: str, new_plan: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE users
                SET plan = :new_plan
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                """
            ),
            {
                "user_id": user_id,
                "new_plan": new_plan,
            },
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return _user_from_mapping(row)


async def set_user_razorpay_customer_id(user_id: str, customer_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE users
                SET razorpay_customer_id = :customer_id
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                """
            ),
            {
                "user_id": user_id,
                "customer_id": customer_id,
            },
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return _user_from_mapping(row)


async def set_user_subscription_id(user_id: str, subscription_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE users
                SET razorpay_subscription_id = :subscription_id
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, razorpay_customer_id, razorpay_subscription_id, created_at, upgraded_at
                """
            ),
            {
                "user_id": user_id,
                "subscription_id": subscription_id,
            },
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return _user_from_mapping(row)


async def clear_user_subscription_id(user_id: str) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE users
                SET razorpay_subscription_id = NULL
                WHERE id = CAST(:user_id AS UUID)
                """
            ),
            {"user_id": user_id},
        )
        await session.commit()


async def is_event_processed(event_id: str) -> bool:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM payment_events WHERE event_id = :event_id"),
            {"event_id": event_id},
        )
        return result.first() is not None


async def record_payment_event(
    event_id: str,
    event_type: str,
    *,
    user_id: str | None = None,
    payload_summary: Any = None,
) -> None:
    normalized_user_id = _normalize_uuid_or_none(user_id)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO payment_events (event_id, event_type, user_id, payload_summary)
                VALUES (:event_id, :event_type, CAST(:user_id AS UUID), CAST(:payload_summary AS JSONB))
                ON CONFLICT (event_id) DO NOTHING
                """
            ),
            {
                "event_id": event_id,
                "event_type": event_type,
                "user_id": normalized_user_id,
                "payload_summary": json.dumps(payload_summary) if payload_summary is not None else None,
            },
        )
        await session.commit()


async def ping() -> bool:
    if _engine is None:
        return False

    try:
        async with _engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar_one() == 1
    except Exception:
        logger.exception("Database ping failed")
        return False


async def cleanup_stale_anonymous_users(older_than_days: int = 30) -> dict[str, int]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        expired_sessions_result = await session.execute(
            text("DELETE FROM sessions WHERE expires_at <= now()")
        )
        stale_users_result = await session.execute(
            text(
                """
                DELETE FROM users u
                WHERE u.email IS NULL
                  AND u.created_at < now() - make_interval(days => :older_than_days)
                  AND NOT EXISTS (
                      SELECT 1
                      FROM user_progress up
                      WHERE up.user_id = u.id
                  )
                """
            ),
            {"older_than_days": int(older_than_days)},
        )
        await session.commit()
        return {
            "deleted_expired_sessions": expired_sessions_result.rowcount or 0,
            "deleted_stale_anonymous_users": stale_users_result.rowcount or 0,
        }


async def record_plan_change(
    user_id: str,
    old_plan: str,
    new_plan: str,
    *,
    context: str | None = None,
    payment_event_id: str | None = None,
) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO plan_changes (user_id, old_plan, new_plan, context, payment_event_id)
                VALUES (CAST(:user_id AS UUID), :old_plan, :new_plan, :context, :payment_event_id)
                """
            ),
            {
                "user_id": user_id,
                "old_plan": old_plan,
                "new_plan": new_plan,
                "context": context,
                "payment_event_id": payment_event_id,
            },
        )
        await session.commit()


async def merge_users(from_user_id: str, to_user_id: str) -> int:
    """Merge anonymous user into a registered account.

    Copies user_progress, user_sample_seen, and submissions rows from
    *from_user_id* into *to_user_id*, then deletes the anonymous user row.
    Returns the number of distinct solve rows that were merged (for UI feedback).
    """
    if from_user_id == to_user_id:
        return 0

    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Count how many unique solves are being merged (for UI feedback).
        count_result = await session.execute(
            text("SELECT COUNT(*) FROM user_progress WHERE user_id = CAST(:from_user_id AS UUID)"),
            {"from_user_id": from_user_id},
        )
        merged_count: int = count_result.scalar() or 0

        await session.execute(
            text(
                """
                INSERT INTO user_progress (user_id, question_id, topic, solved_at)
                SELECT CAST(:to_user_id AS UUID), question_id, topic, solved_at
                FROM user_progress
                WHERE user_id = CAST(:from_user_id AS UUID)
                ON CONFLICT (user_id, question_id, topic)
                DO UPDATE SET solved_at = EXCLUDED.solved_at
                """
            ),
            {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO user_sample_seen (user_id, difficulty, question_id, topic, seen_at)
                SELECT CAST(:to_user_id AS UUID), difficulty, question_id, topic, seen_at
                FROM user_sample_seen
                WHERE user_id = CAST(:from_user_id AS UUID)
                ON CONFLICT (user_id, difficulty, question_id, topic)
                DO UPDATE SET seen_at = EXCLUDED.seen_at
                """
            ),
            {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
            },
        )
        # Reassign submission history rows so the history panel stays intact.
        await session.execute(
            text(
                "UPDATE submissions SET user_id = CAST(:to_user_id AS UUID) "
                "WHERE user_id = CAST(:from_user_id AS UUID)"
            ),
            {
                "from_user_id": from_user_id,
                "to_user_id": to_user_id,
            },
        )
        await session.execute(
            text("DELETE FROM users WHERE id = CAST(:from_user_id AS UUID)"),
            {"from_user_id": from_user_id},
        )
        await session.commit()
        return merged_count


async def get_recent_activity(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT question_id, topic, solved_at
                FROM user_progress
                WHERE user_id = CAST(:user_id AS UUID)
                ORDER BY solved_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        return [
            {
                "question_id": row[0],
                "topic": row[1],
                "solved_at": row[2].isoformat() if row[2] else None,
            }
            for row in result.fetchall()
        ]


async def get_progress_by_topic(user_id: str) -> dict[str, dict[str, int]]:
    """Returns solved count per topic."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT topic, COUNT(*) as solved_count
                FROM user_progress
                WHERE user_id = CAST(:user_id AS UUID)
                GROUP BY topic
                """
            ),
            {"user_id": user_id},
        )
        return {row[0]: {"solved": row[1]} for row in result.fetchall()}


async def record_submission(
    user_id: str,
    track: str,
    question_id: int,
    is_correct: bool,
    code: str | None = None,
    duration_ms: int | None = None,
) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO submissions (user_id, track, question_id, is_correct, code, duration_ms)
                VALUES (CAST(:user_id AS UUID), :track, :question_id, :is_correct, :code, :duration_ms)
                """
            ),
            {
                "user_id": user_id,
                "track": track,
                "question_id": question_id,
                "is_correct": is_correct,
                "code": code,
                "duration_ms": duration_ms,
            },
        )
        await session.commit()


async def get_latest_submission(
    user_id: str,
    track: str,
    question_id: int,
) -> dict[str, Any] | None:
    """Fetch the most recent submission for a user+question+track, used for repeat-attempt detection."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, code, is_correct
                FROM submissions
                WHERE user_id = CAST(:user_id AS UUID) AND track = :track AND question_id = :question_id
                ORDER BY submitted_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id, "track": track, "question_id": question_id},
        )
        row = result.fetchone()
        if row is None:
            return None
        return {"id": row[0], "code": row[1], "is_correct": row[2]}


# ── Mock interview ────────────────────────────────────────────────────────────

async def create_mock_session(
    user_id: str,
    mode: str,
    track: str,
    difficulty: str | None,
    time_limit_s: int,
    questions: list[dict],  # [{"question_id": int, "track": str, "position": int, "follow_up_dimension": str|None}]
    focus_fallback: bool = False,
    role: str | None = None,
    chain_parent_id: int | None = None,
) -> dict[str, Any]:
    """
    Persist a new mock session.

    For interview_loop sessions, chain_parent_id marks the chain consumed atomically
    within the same transaction. questions may carry follow_up_dimension for follow-up rows.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, focus_fallback, role)
                VALUES (CAST(:user_id AS UUID), :mode, :track, :difficulty, :time_limit_s, :focus_fallback, :role)
                RETURNING id, user_id, mode, track, difficulty, started_at, time_limit_s, status, focus_fallback, role
                """
            ),
            {
                "user_id": user_id,
                "mode": mode,
                "track": track,
                "difficulty": difficulty,
                "time_limit_s": time_limit_s,
                "focus_fallback": focus_fallback,
                "role": role,
            },
        )
        session_row = result.mappings().first()
        session_id = session_row["id"]
        for q in questions:
            await session.execute(
                text(
                    """
                    INSERT INTO mock_session_questions
                        (session_id, question_id, track, position, follow_up_dimension, is_follow_up)
                    VALUES (:session_id, :question_id, :track, :position, :follow_up_dimension, :is_follow_up)
                    """
                ),
                {
                    "session_id": session_id,
                    "question_id": q["question_id"],
                    "track": q["track"],
                    "position": q["position"],
                    "follow_up_dimension": q.get("follow_up_dimension"),
                    "is_follow_up": bool(q.get("is_follow_up", False)),
                },
            )
        # Atomically mark chain consumed for interview_loop sessions
        if chain_parent_id is not None:
            await session.execute(
                text(
                    """
                    INSERT INTO mock_chain_consumption (user_id, parent_id, session_id)
                    VALUES (CAST(:user_id AS UUID), :parent_id, :session_id)
                    ON CONFLICT (user_id, parent_id) DO UPDATE
                        SET reclaimed = false, session_id = EXCLUDED.session_id,
                            consumed_at = now()
                    """
                ),
                {"user_id": user_id, "parent_id": chain_parent_id, "session_id": session_id},
            )
        await session.commit()
        return {
            "session_id": session_id,
            "mode": session_row["mode"],
            "track": session_row["track"],
            "difficulty": session_row["difficulty"],
            "started_at": session_row["started_at"].isoformat(),
            "time_limit_s": session_row["time_limit_s"],
            "status": session_row["status"],
            "focus_fallback": bool(session_row["focus_fallback"]),
            "role": session_row["role"],
        }



async def get_mock_session(session_id: int, user_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    ms.id AS session_id,
                    ms.mode, ms.track, ms.difficulty, ms.role,
                    ms.started_at, ms.ended_at, ms.time_limit_s, ms.status,
                    ms.focus_fallback,
                    msq.id AS msq_id,
                    msq.question_id, msq.track AS q_track, msq.position,
                    msq.is_solved, msq.submitted_at, msq.final_code, msq.time_spent_s,
                    msq.is_follow_up, msq.follow_up_dimension
                FROM mock_sessions ms
                LEFT JOIN mock_session_questions msq ON msq.session_id = ms.id
                WHERE ms.id = :session_id AND ms.user_id = CAST(:user_id AS UUID)
                ORDER BY msq.position
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        rows = result.mappings().all()
        if not rows:
            return None
        first = rows[0]
        session_data = {
            "session_id": first["session_id"],
            "mode": first["mode"],
            "track": first["track"],
            "difficulty": first["difficulty"],
            "role": first["role"],
            "started_at": first["started_at"].isoformat() if first["started_at"] else None,
            "ended_at": first["ended_at"].isoformat() if first["ended_at"] else None,
            "time_limit_s": first["time_limit_s"],
            "status": first["status"],
            "focus_fallback": bool(first["focus_fallback"]) if first["focus_fallback"] is not None else False,
        }
        question_rows = []
        for row in rows:
            if row["msq_id"] is not None:
                question_rows.append({
                    "question_id": row["question_id"],
                    "track": row["q_track"],
                    "position": row["position"],
                    "is_solved": row["is_solved"],
                    "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
                    "final_code": row["final_code"],
                    "time_spent_s": row["time_spent_s"],
                    "is_follow_up": bool(row.get("is_follow_up", False)),
                    "follow_up_dimension": row.get("follow_up_dimension"),
                })
        session_data["questions"] = question_rows
        return session_data


async def discard_mock_session(session_id: int, user_id: str) -> bool:
    """
    Delete a mock session and its questions within the 2-minute discard window.

    For interview_loop sessions, also reclaims the chain (deletes the row from
    mock_chain_consumption, making the chain available again).

    Returns True on success; 404/403 handling is done by the caller.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Look up mode and first question's ID (parent chain) before deleting
        mode_result = await session.execute(
            text(
                """
                SELECT ms.mode, msq.question_id AS parent_id
                FROM mock_sessions ms
                LEFT JOIN mock_session_questions msq
                    ON msq.session_id = ms.id AND msq.position = 1
                WHERE ms.id = :session_id
                  AND ms.user_id = CAST(:user_id AS UUID)
                  AND ms.status = 'active'
                  AND ms.started_at >= now() - interval '2 minutes'
                LIMIT 1
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        mode_row = mode_result.mappings().first()
        session_mode = mode_row["mode"] if mode_row else None
        chain_parent_id = mode_row["parent_id"] if mode_row else None

        result = await session.execute(
            text(
                """
                DELETE FROM mock_session_questions
                WHERE session_id = :session_id
                  AND EXISTS (
                      SELECT 1 FROM mock_sessions
                      WHERE id = :session_id
                        AND user_id = CAST(:user_id AS UUID)
                        AND status = 'active'
                        AND started_at >= now() - interval '2 minutes'
                  )
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        await session.execute(
            text(
                """
                DELETE FROM mock_sessions
                WHERE id = :session_id
                  AND user_id = CAST(:user_id AS UUID)
                  AND status = 'active'
                  AND started_at >= now() - interval '2 minutes'
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        # Reclaim chain for interview_loop sessions
        if session_mode == "interview_loop" and chain_parent_id is not None:
            await session.execute(
                text(
                    """
                    DELETE FROM mock_chain_consumption
                    WHERE user_id = CAST(:user_id AS UUID)
                      AND parent_id = :parent_id
                    """
                ),
                {"user_id": user_id, "parent_id": chain_parent_id},
            )
        await session.commit()
        return result.rowcount > 0 or True  # treat as success; 404 handled by caller


async def submit_mock_question(
    session_id: int,
    question_id: int,
    user_id: str,
    is_solved: bool,
    code: str | None,
    time_spent_s: int | None,
) -> bool:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE mock_session_questions
                SET is_solved = is_solved OR :is_solved,
                    final_code = :code,
                    submitted_at = now(),
                    time_spent_s = :time_spent_s
                WHERE session_id = :session_id
                  AND question_id = :question_id
                                    AND submitted_at IS NULL
                  AND EXISTS (
                      SELECT 1 FROM mock_sessions
                      WHERE id = :session_id
                        AND user_id = CAST(:user_id AS UUID)
                        AND status = 'active'
                  )
                """
            ),
            {
                "session_id": session_id,
                "question_id": question_id,
                "user_id": user_id,
                "is_solved": is_solved,
                "code": code,
                "time_spent_s": time_spent_s,
            },
        )
        await session.commit()
        return (result.rowcount or 0) > 0


async def finish_mock_session(session_id: int, user_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Try to mark as completed (no-op if already completed)
        await session.execute(
            text(
                """
                UPDATE mock_sessions
                SET ended_at = now(), status = 'completed'
                WHERE id = :session_id
                  AND user_id = CAST(:user_id AS UUID)
                  AND status = 'active'
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        await session.commit()

        # Return full session state regardless (idempotent)
        result = await session.execute(
            text(
                """
                SELECT
                    ms.id AS session_id,
                    ms.mode, ms.track, ms.difficulty, ms.role,
                    ms.started_at, ms.ended_at, ms.time_limit_s, ms.status,
                    msq.question_id, msq.track AS q_track, msq.position,
                    msq.is_solved, msq.submitted_at, msq.final_code, msq.time_spent_s,
                    msq.is_follow_up, msq.follow_up_dimension
                FROM mock_sessions ms
                LEFT JOIN mock_session_questions msq ON msq.session_id = ms.id
                WHERE ms.id = :session_id AND ms.user_id = CAST(:user_id AS UUID)
                ORDER BY msq.position
                """
            ),
            {"session_id": session_id, "user_id": user_id},
        )
        rows = result.mappings().all()
        if not rows:
            return None
        first = rows[0]
        started = first["started_at"]
        ended = first["ended_at"]
        time_used_s = int((ended - started).total_seconds()) if started and ended else None
        session_out = {
            "session_id": first["session_id"],
            "mode": first["mode"],
            "track": first["track"],
            "difficulty": first["difficulty"],
            "started_at": started.isoformat() if started else None,
            "ended_at": ended.isoformat() if ended else None,
            "time_limit_s": first["time_limit_s"],
            "time_used_s": time_used_s,
            "status": first["status"],
        }
        question_rows = []
        for row in rows:
            if row["question_id"] is not None:
                question_rows.append({
                    "question_id": row["question_id"],
                    "track": row["q_track"],
                    "position": row["position"],
                    "is_solved": row["is_solved"],
                    "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
                    "final_code": row["final_code"],
                    "time_spent_s": row["time_spent_s"],
                    "is_follow_up": bool(row.get("is_follow_up", False)),
                    "follow_up_dimension": row.get("follow_up_dimension"),
                })
        session_out["questions"] = question_rows
        solved_count = sum(1 for q in question_rows if q["is_solved"])
        session_out["solved_count"] = solved_count
        session_out["total_count"] = len(question_rows)
        return session_out


async def get_previously_mocked_ids(user_id: str) -> set[int]:
    """Return all question IDs this user has ever seen across all mock sessions."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT DISTINCT msq.question_id
                FROM mock_session_questions msq
                JOIN mock_sessions ms ON ms.id = msq.session_id
                WHERE ms.user_id = CAST(:user_id AS UUID)
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()
        return {row["question_id"] for row in rows}


async def inject_follow_up_question(
    session_id: int,
    follow_up_question_id: int,
    after_position: int,
) -> None:
    """
    Insert a follow-up question immediately after `after_position` in a mock session.
    Shifts all subsequent positions by 1 to make room.
    The follow-up is marked is_follow_up=true.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Get the track from the parent question row
        result = await session.execute(
            text(
                """
                SELECT track FROM mock_session_questions
                WHERE session_id = :session_id AND position = :position
                """
            ),
            {"session_id": session_id, "position": after_position},
        )
        row = result.mappings().first()
        track = row["track"] if row else "sql"

        # Shift existing positions after the insertion point
        await session.execute(
            text(
                """
                UPDATE mock_session_questions
                SET position = position + 1
                WHERE session_id = :session_id AND position > :after_position
                """
            ),
            {"session_id": session_id, "after_position": after_position},
        )

        # Insert the follow-up question
        await session.execute(
            text(
                """
                INSERT INTO mock_session_questions
                  (session_id, question_id, track, position, is_follow_up)
                VALUES (:session_id, :question_id, :track, :position, true)
                """
            ),
            {
                "session_id": session_id,
                "question_id": follow_up_question_id,
                "track": track,
                "position": after_position + 1,
            },
        )
        await session.commit()


async def get_active_mock_session(user_id: str) -> dict[str, Any] | None:
    """Return the most recent active mock session for a user, or None."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id AS session_id, mode, track, difficulty, started_at, time_limit_s
                FROM mock_sessions
                WHERE user_id = CAST(:user_id AS UUID) AND status = 'active'
                ORDER BY started_at DESC
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return {
            "session_id": row["session_id"],
            "mode": row["mode"],
            "track": row["track"],
            "difficulty": row["difficulty"],
            "started_at": row["started_at"].isoformat() if row["started_at"] else None,
            "time_limit_s": row["time_limit_s"],
        }


async def get_mock_history(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT
                    ms.id AS session_id,
                    ms.mode, ms.track, ms.difficulty, ms.role,
                    ms.started_at, ms.ended_at, ms.time_limit_s,
                    EXTRACT(EPOCH FROM (ms.ended_at - ms.started_at))::int AS time_used_s,
                    ms.status,
                    COUNT(msq.id) AS total_count,
                    COUNT(CASE WHEN msq.is_solved THEN 1 END) AS solved_count
                FROM mock_sessions ms
                LEFT JOIN mock_session_questions msq ON msq.session_id = ms.id
                WHERE ms.user_id = CAST(:user_id AS UUID)
                GROUP BY ms.id
                ORDER BY ms.started_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "limit": limit},
        )
        rows = result.mappings().all()
        return [
            {
                "session_id": row["session_id"],
                "mode": row["mode"],
                "track": row["track"],
                "difficulty": row["difficulty"],
                "role": row["role"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "ended_at": row["ended_at"].isoformat() if row["ended_at"] else None,
                "time_limit_s": row["time_limit_s"],
                "time_used_s": row["time_used_s"],
                "status": row["status"],
                "total_count": row["total_count"],
                "solved_count": row["solved_count"],
            }
            for row in rows
        ]


# ── Submissions ────────────────────────────────────────────────────────────────

async def get_submissions(
    user_id: str,
    track: str,
    question_id: int,
    limit: int = 5,
) -> list[dict[str, Any]]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                                SELECT id, track, question_id, is_correct, code, duration_ms, submitted_at
                FROM submissions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND track = :track
                  AND question_id = :question_id
                ORDER BY submitted_at DESC
                LIMIT :limit
                """
            ),
            {"user_id": user_id, "track": track, "question_id": question_id, "limit": limit},
        )
        rows = result.mappings().all()
        return [
            {
                "id": row["id"],
                "track": row["track"],
                "question_id": row["question_id"],
                "is_correct": row["is_correct"],
                "code": row["code"],
                "duration_ms": row["duration_ms"],
                "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
            }
            for row in rows
        ]


async def get_submission_events(user_id: str) -> list[dict[str, Any]]:
    """Return all submission events for a user ordered oldest-first."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT track, question_id, is_correct, submitted_at
                FROM submissions
                WHERE user_id = CAST(:user_id AS UUID)
                ORDER BY submitted_at ASC, id ASC
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()
        return [
            {
                "track": row["track"],
                "question_id": row["question_id"],
                "is_correct": bool(row["is_correct"]),
                "submitted_at": row["submitted_at"],
            }
            for row in rows
        ]


async def get_loop_question_events(user_id: str) -> list[dict[str, Any]]:
    """
    Return Interview Loop question rows with follow_up_dimension and is_solved.
    Used for per-dimension analytics in the Elite dashboard.
    Only returns rows from completed interview_loop sessions where follow_up_dimension is set.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT msq.follow_up_dimension, msq.is_solved,
                       ms.id AS session_id, ms.status
                FROM mock_session_questions msq
                JOIN mock_sessions ms ON ms.id = msq.session_id
                WHERE ms.user_id = CAST(:user_id AS UUID)
                  AND ms.mode = 'interview_loop'
                  AND ms.status = 'completed'
                  AND msq.follow_up_dimension IS NOT NULL
                ORDER BY ms.started_at ASC
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()
        return [
            {
                "follow_up_dimension": row["follow_up_dimension"],
                "is_solved": bool(row["is_solved"]),
                "session_id": row["session_id"],
            }
            for row in rows
        ]


async def get_user_streak_status(user_id: str) -> dict[str, Any]:
    """Return streak metadata for auth/me payloads."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT DISTINCT DATE(submitted_at AT TIME ZONE 'UTC') AS solve_date
                FROM submissions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND is_correct = TRUE
                ORDER BY solve_date DESC
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()

    solve_dates = {
        row["solve_date"]
        for row in rows
        if row.get("solve_date") is not None
    }

    today = datetime.now(timezone.utc).date()
    cursor = today
    streak_days = 0
    while cursor in solve_dates:
        streak_days += 1
        cursor -= timedelta(days=1)

    streak_at_risk = False
    if streak_days == 0 and (today - timedelta(days=1)) in solve_dates:
        streak_at_risk = True

    return {
        "streak_days": streak_days,
        "streak_at_risk": streak_at_risk,
    }


# ── OAuth accounts ────────────────────────────────────────────────────────────

async def get_or_create_oauth_user(
    provider: str,
    provider_user_id: str,
    email: str | None,
    name: str | None,
) -> dict[str, Any]:
    """Find or create a user for an OAuth login. Returns the user dict."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Try to find existing OAuth account
        result = await session.execute(
            text(
                """
                SELECT u.id, u.email, u.name, u.plan, u.email_verified, u.razorpay_customer_id, u.created_at, u.upgraded_at
                FROM oauth_accounts oa
                JOIN users u ON u.id = oa.user_id
                WHERE oa.provider = :provider
                  AND oa.provider_user_id = :provider_user_id
                """
            ),
            {"provider": provider, "provider_user_id": provider_user_id},
        )
        row = result.mappings().first()
        if row:
            # Ensure email_verified = true for OAuth users (OAuth proves email ownership)
            if not row.get("email_verified"):
                await session.execute(
                    text("UPDATE users SET email_verified = true WHERE id = CAST(:uid AS UUID)"),
                    {"uid": str(row["id"])},
                )
                await session.commit()
            user = _user_from_mapping(row)  # type: ignore[return-value]
            if user:
                user["email_verified"] = True
            return user  # type: ignore[return-value]

        # If email provided, check for existing user with that email
        user_id: str | None = None
        if email:
            result2 = await session.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            )
            existing = result2.mappings().first()
            if existing:
                user_id = str(existing["id"])

        # Create a new user if none found
        if user_id is None:
            result3 = await session.execute(
                text(
                    """
                    INSERT INTO users (email, name, pwd_hash, pwd_salt, plan, email_verified)
                    VALUES (:email, :name, NULL, NULL, 'free', true)
                    RETURNING id, email, name, plan, email_verified, razorpay_customer_id, created_at, upgraded_at
                    """
                ),
                {"email": email, "name": name or email},
            )
            user_row = result3.mappings().one()
            user_id = str(user_row["id"])
            user_dict = _user_from_mapping(user_row)  # type: ignore[arg-type]
        else:
            result4 = await session.execute(
                text(
                    """
                    SELECT id, email, name, plan, email_verified, razorpay_customer_id, created_at, upgraded_at
                    FROM users WHERE id = CAST(:user_id AS UUID)
                    """
                ),
                {"user_id": user_id},
            )
            user_dict = _user_from_mapping(result4.mappings().first())  # type: ignore[arg-type]

        # Link OAuth account
        await session.execute(
            text(
                """
                INSERT INTO oauth_accounts (user_id, provider, provider_user_id, email, name)
                VALUES (CAST(:user_id AS UUID), :provider, :provider_user_id, :email, :name)
                ON CONFLICT (provider, provider_user_id) DO NOTHING
                """
            ),
            {"user_id": user_id, "provider": provider, "provider_user_id": provider_user_id, "email": email, "name": name},
        )
        await session.commit()
        return user_dict  # type: ignore[return-value]


# ── Password reset tokens ─────────────────────────────────────────────────────

async def create_password_reset_token(user_id: str) -> str:
    """Generate a password reset token valid for 1 hour."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Invalidate any existing unused tokens for this user
        await session.execute(
            text(
                """
                UPDATE password_reset_tokens
                SET used_at = now()
                WHERE user_id = CAST(:user_id AS UUID)
                  AND used_at IS NULL
                  AND expires_at > now()
                """
            ),
            {"user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO password_reset_tokens (token, user_id, expires_at)
                VALUES (:token, CAST(:user_id AS UUID), :expires_at)
                """
            ),
            {"token": token, "user_id": user_id, "expires_at": expires_at},
        )
        await session.commit()
    return token


async def consume_password_reset_token(token: str) -> str | None:
    """Validate and consume a reset token. Returns user_id or None if invalid."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE password_reset_tokens
                SET used_at = now()
                WHERE token = :token
                  AND used_at IS NULL
                  AND expires_at > now()
                RETURNING user_id
                """
            ),
            {"token": token},
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return str(row["user_id"])


async def add_password_to_existing_user(user_id: str, password: str) -> dict[str, Any] | None:
    """Add email/password credentials to an existing user that currently has no password (e.g. OAuth-only).

    Only updates if pwd_hash IS NULL — safe to call concurrently.
    Returns the updated user dict, or None if the user already has a password (or is not found).
    """
    pwd_hash, pwd_salt = await hash_password(password)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE users
                SET pwd_hash = :pwd_hash,
                    pwd_salt = :pwd_salt
                WHERE id = CAST(:user_id AS UUID)
                  AND pwd_hash IS NULL
                RETURNING id, email, name, plan, email_verified, razorpay_customer_id, created_at, upgraded_at
                """
            ),
            {"user_id": user_id, "pwd_hash": pwd_hash, "pwd_salt": pwd_salt},
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return _user_from_mapping(row)


async def update_password(user_id: str, new_password: str) -> None:
    """Update a user's password hash."""
    pwd_hash, pwd_salt = await hash_password(new_password)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE users
                SET pwd_hash = :pwd_hash, pwd_salt = :pwd_salt
                WHERE id = CAST(:user_id AS UUID)
                """
            ),
            {"pwd_hash": pwd_hash, "pwd_salt": pwd_salt, "user_id": user_id},
        )
        await session.commit()


# ── Email verification tokens ─────────────────────────────────────────────────

async def create_email_verification_token(user_id: str) -> str:
    """Generate an email verification token valid for 24 hours."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        # Invalidate any existing unused tokens for this user
        await session.execute(
            text(
                """
                UPDATE email_verification_tokens
                SET used_at = now()
                WHERE user_id = CAST(:user_id AS UUID)
                  AND used_at IS NULL
                  AND expires_at > now()
                """
            ),
            {"user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO email_verification_tokens (token, user_id, expires_at)
                VALUES (:token, CAST(:user_id AS UUID), :expires_at)
                """
            ),
            {"token": token, "user_id": user_id, "expires_at": expires_at},
        )
        await session.commit()
    return token


async def consume_email_verification_token(token: str) -> str | None:
    """Validate and consume a verification token. Returns user_id or None if invalid."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE email_verification_tokens
                SET used_at = now()
                WHERE token = :token
                  AND used_at IS NULL
                  AND expires_at > now()
                RETURNING user_id
                """
            ),
            {"token": token},
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return str(row["user_id"])


async def mark_email_verified(user_id: str) -> None:
    """Mark a user's email address as verified."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text("UPDATE users SET email_verified = true WHERE id = CAST(:user_id AS UUID)"),
            {"user_id": user_id},
        )
        await session.commit()


# ── OAuth state tokens ───────────────────────────────────────────────────────

async def create_oauth_state_token(
    *,
    user_agent_hash: str | None = None,
    ip_prefix: str | None = None,
) -> str:
    """Generate an OAuth state token valid for a short window."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, OAUTH_STATE_TTL_MINUTES))
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO oauth_states (state_token, user_agent_hash, ip_prefix, expires_at)
                VALUES (:token, :user_agent_hash, :ip_prefix, :expires_at)
                """
            ),
            {
                "token": token,
                "user_agent_hash": user_agent_hash,
                "ip_prefix": ip_prefix,
                "expires_at": expires_at,
            },
        )
        await session.commit()
    return token


async def consume_oauth_state_token(
    token: str,
    *,
    user_agent_hash: str | None = None,
    ip_prefix: str | None = None,
) -> dict[str, bool]:
    """Consume an OAuth state token once and surface mismatch signals.

    Returns a dictionary containing:
    - valid: token existed, not expired, and not previously used
    - user_agent_mismatch: best-effort signal only (never blocks)
    - ip_prefix_mismatch: best-effort signal only (never blocks)
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE oauth_states
                SET used_at = now()
                WHERE state_token = :token
                  AND used_at IS NULL
                  AND expires_at > now()
                RETURNING user_agent_hash, ip_prefix
                """
            ),
            {"token": token},
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return {
                "valid": False,
                "user_agent_mismatch": False,
                "ip_prefix_mismatch": False,
            }

        expected_ua = row.get("user_agent_hash")
        expected_ip_prefix = row.get("ip_prefix")
        user_agent_mismatch = bool(expected_ua and user_agent_hash and expected_ua != user_agent_hash)
        ip_prefix_mismatch = bool(expected_ip_prefix and ip_prefix and expected_ip_prefix != ip_prefix)

        await session.commit()
        return {
            "valid": True,
            "user_agent_mismatch": user_agent_mismatch,
            "ip_prefix_mismatch": ip_prefix_mismatch,
        }


# ── Magic-link tokens ────────────────────────────────────────────────────────

async def create_magic_link_token(user_id: str) -> str:
    """Generate a magic-link token valid for a short window."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, MAGIC_LINK_TTL_MINUTES))
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                UPDATE magic_link_tokens
                SET used_at = now()
                WHERE user_id = CAST(:user_id AS UUID)
                  AND used_at IS NULL
                  AND expires_at > now()
                """
            ),
            {"user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO magic_link_tokens (token, user_id, expires_at)
                VALUES (:token, CAST(:user_id AS UUID), :expires_at)
                """
            ),
            {"token": token, "user_id": user_id, "expires_at": expires_at},
        )
        await session.commit()
    return token


async def consume_magic_link_token(token: str) -> str | None:
    """Validate and consume a magic-link token. Returns user_id or None if invalid."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE magic_link_tokens
                SET used_at = now()
                WHERE token = :token
                  AND used_at IS NULL
                  AND expires_at > now()
                RETURNING user_id
                """
            ),
            {"token": token},
        )
        row = result.mappings().first()
        if row is None:
            await session.rollback()
            return None
        await session.commit()
        return str(row["user_id"])


async def prune_expired_auth_tokens() -> dict[str, int]:
    """Delete expired/used auth tokens to keep token tables small."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        oauth_deleted = await session.execute(
            text(
                """
                DELETE FROM oauth_states
                WHERE expires_at <= now()
                   OR used_at IS NOT NULL
                """
            )
        )
        magic_deleted = await session.execute(
            text(
                """
                DELETE FROM magic_link_tokens
                WHERE expires_at <= now()
                   OR used_at IS NOT NULL
                """
            )
        )
        await session.commit()

    return {
        "oauth_states": int(oauth_deleted.rowcount or 0),
        "magic_link_tokens": int(magic_deleted.rowcount or 0),
    }


# ── Path completion state ──────────────────────────────────────────────────────

# ── Daily / weekly mock usage ──────────────────────────────────────────────────

async def get_daily_mock_usage(user_id: str) -> dict[str, int]:
    """
    Return how many mock sessions the user has started today per difficulty.
    'Today' is calendar-day in the database server timezone (UTC).
    Kept for backwards-compat with any callers that still use it.
    """
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT difficulty, COUNT(*) AS cnt
                FROM mock_sessions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND started_at >= CURRENT_DATE
                  AND difficulty IN ('medium', 'hard')
                GROUP BY difficulty
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()

    usage: dict[str, int] = {"medium": 0, "hard": 0}
    for row in rows:
        if row["difficulty"] in usage:
            usage[row["difficulty"]] = int(row["cnt"])
    return usage


async def get_daily_benchmark_usage(user_id: str) -> int:
    """Count benchmark sessions started today (UTC). Used for Pro 3/day cap."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM mock_sessions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND mode = 'benchmark'
                  AND started_at >= CURRENT_DATE
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().first()
    return int(row["cnt"]) if row else 0


async def get_daily_custom_usage(user_id: str) -> int:
    """Count custom sessions started today (UTC). Used for Pro 3/day cap."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM mock_sessions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND mode = 'custom'
                  AND started_at >= CURRENT_DATE
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().first()
    return int(row["cnt"]) if row else 0


async def get_weekly_benchmark_usage(user_id: str) -> int:
    """Count benchmark sessions started in the last 7 rolling days. Used for Free 1/7-day cap."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM mock_sessions
                WHERE user_id = CAST(:user_id AS UUID)
                  AND mode = 'benchmark'
                  AND started_at >= now() - interval '7 days'
                """
            ),
            {"user_id": user_id},
        )
        row = result.mappings().first()
    return int(row["cnt"]) if row else 0


# ── Chain consumption ──────────────────────────────────────────────────────────

async def mark_chain_consumed(user_id: str, parent_id: int, session_id: int) -> None:
    """Mark a chain as consumed for a user. Idempotent via ON CONFLICT."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO mock_chain_consumption (user_id, parent_id, session_id)
                VALUES (CAST(:user_id AS UUID), :parent_id, :session_id)
                ON CONFLICT (user_id, parent_id) DO UPDATE
                    SET reclaimed = false,
                        session_id = EXCLUDED.session_id,
                        consumed_at = now()
                """
            ),
            {"user_id": user_id, "parent_id": parent_id, "session_id": session_id},
        )
        await session.commit()


async def reclaim_chain(user_id: str, parent_id: int) -> None:
    """Reclaim a chain — delete the consumption record so it can be drawn again."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                DELETE FROM mock_chain_consumption
                WHERE user_id = CAST(:user_id AS UUID) AND parent_id = :parent_id
                """
            ),
            {"user_id": user_id, "parent_id": parent_id},
        )
        await session.commit()


async def get_consumed_chain_parent_ids(user_id: str) -> set[int]:
    """Return parent_ids of chains consumed by this user (reclaimed=false)."""
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT parent_id
                FROM mock_chain_consumption
                WHERE user_id = CAST(:user_id AS UUID)
                  AND NOT reclaimed
                """
            ),
            {"user_id": user_id},
        )
        rows = result.mappings().all()
    return {row["parent_id"] for row in rows}
