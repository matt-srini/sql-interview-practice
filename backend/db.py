from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import get_async_database_url


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
    plan TEXT NOT NULL DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'elite')),
    stripe_customer_id TEXT UNIQUE,
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

CREATE TABLE IF NOT EXISTS stripe_events (
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
    stripe_event_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_progress_user ON user_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_progress_user_topic ON user_progress(user_id, topic);
CREATE INDEX IF NOT EXISTS idx_plan_changes_user ON plan_changes(user_id);
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
        "stripe_customer_id": row.get("stripe_customer_id"),
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


async def init_pool() -> None:
    global _engine, _session_factory

    if _engine is not None:
        return

    _engine = create_async_engine(
        get_async_database_url(),
        future=True,
        pool_pre_ping=True,
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


async def reset_database() -> None:
    if _engine is None:
        raise RuntimeError("Database pool is not initialized")

    async with _engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE plan_changes, stripe_events, user_sample_seen, user_progress, sessions, users RESTART IDENTITY CASCADE"))


async def ensure_schema_admin(database_url: str | None = None) -> None:
    engine = _admin_engine(database_url)
    try:
        async with engine.begin() as conn:
            for statement in [part.strip() for part in _SCHEMA_SQL.split(";") if part.strip()]:
                await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def reset_database_admin(database_url: str | None = None) -> None:
    engine = _admin_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE TABLE plan_changes, stripe_events, user_sample_seen, user_progress, sessions, users RESTART IDENTITY CASCADE"
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
                SELECT id, email, name, plan, stripe_customer_id, created_at, upgraded_at
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
                SELECT id, email, name, plan, stripe_customer_id, created_at, upgraded_at
                FROM users
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        return _user_from_mapping(result.mappings().first())


async def get_user_by_stripe_customer_id(customer_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                SELECT id, email, name, plan, stripe_customer_id, created_at, upgraded_at
                FROM users
                WHERE stripe_customer_id = :customer_id
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
                SELECT id, email, name, plan, pwd_hash, pwd_salt
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
            "pwd_hash": row["pwd_hash"],
            "pwd_salt": row["pwd_salt"],
        }


async def create_anonymous_user() -> dict[str, Any]:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                INSERT INTO users (email, name, pwd_hash, pwd_salt, plan)
                VALUES (NULL, NULL, NULL, NULL, 'free')
                RETURNING id, email, name, plan, stripe_customer_id, created_at, upgraded_at
                """
            )
        )
        await session.commit()
        return _user_from_mapping(result.mappings().one())  # type: ignore[return-value]


async def upgrade_anonymous_to_registered(user_id: str, email: str, name: str, password: str) -> dict[str, Any] | None:
    pwd_hash, pwd_salt = _hash_password(password)
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
                    RETURNING id, email, name, plan, stripe_customer_id, created_at, upgraded_at
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
            return None
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
                SELECT u.id, u.email, u.name, u.plan, u.stripe_customer_id, u.created_at, u.upgraded_at
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


async def clear_seen_samples(user_id: str, difficulty: str | None = None) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        if difficulty is None:
            await session.execute(
                text("DELETE FROM user_sample_seen WHERE user_id = CAST(:user_id AS UUID)"),
                {"user_id": user_id},
            )
        else:
            await session.execute(
                text(
                    """
                    DELETE FROM user_sample_seen
                    WHERE user_id = CAST(:user_id AS UUID)
                      AND difficulty = :difficulty
                    """
                ),
                {
                    "user_id": user_id,
                    "difficulty": difficulty,
                },
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
                RETURNING id, email, name, plan, stripe_customer_id, created_at, upgraded_at
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


async def set_user_stripe_customer_id(user_id: str, customer_id: str) -> dict[str, Any] | None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text(
                """
                UPDATE users
                SET stripe_customer_id = :customer_id
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, stripe_customer_id, created_at, upgraded_at
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


async def is_event_processed(event_id: str) -> bool:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM stripe_events WHERE event_id = :event_id"),
            {"event_id": event_id},
        )
        return result.first() is not None


async def record_stripe_event(
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
                INSERT INTO stripe_events (event_id, event_type, user_id, payload_summary)
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
    stripe_event_id: str | None = None,
) -> None:
    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
        await session.execute(
            text(
                """
                INSERT INTO plan_changes (user_id, old_plan, new_plan, context, stripe_event_id)
                VALUES (CAST(:user_id AS UUID), :old_plan, :new_plan, :context, :stripe_event_id)
                """
            ),
            {
                "user_id": user_id,
                "old_plan": old_plan,
                "new_plan": new_plan,
                "context": context,
                "stripe_event_id": stripe_event_id,
            },
        )
        await session.commit()


async def merge_users(from_user_id: str, to_user_id: str) -> None:
    if from_user_id == to_user_id:
        return

    session_factory = _session_factory_or_raise()
    async with session_factory() as session:
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
        await session.execute(
            text("DELETE FROM users WHERE id = CAST(:from_user_id AS UUID)"),
            {"from_user_id": from_user_id},
        )
        await session.commit()


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
