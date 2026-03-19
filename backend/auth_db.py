"""
Lightweight auth persistence using Python stdlib sqlite3.

Keeps auth state completely separate from the DuckDB SQL-practice database.

Password hashing : PBKDF2-HMAC-SHA256, 260 000 iterations, 32-byte random salt.
Session tokens   : 256-bit URL-safe random tokens, 30-day expiry.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).resolve().parent / "auth.db"
_ITERATIONS = 260_000  # PBKDF2-SHA256; OWASP-recommended range


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_auth_db() -> None:
    logger.info("Initialising auth database at %s", _DB_PATH)
    conn = _connect()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                user_id    TEXT PRIMARY KEY,
                email      TEXT NOT NULL UNIQUE,
                name       TEXT NOT NULL,
                pwd_hash   TEXT NOT NULL,
                pwd_salt   TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token      TEXT PRIMARY KEY,
                user_id    TEXT NOT NULL REFERENCES auth_users(user_id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id)"
        )
    conn.close()


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------

def _hash_password(password: str) -> tuple[str, str]:
    """Return (hash_hex, salt_hex)."""
    salt = secrets.token_hex(32)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return digest.hex(), salt


def _verify_password(password: str, stored_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _ITERATIONS
    )
    return secrets.compare_digest(digest.hex(), stored_hash)


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def create_user(email: str, name: str, password: str) -> dict[str, Any] | None:
    """Create a new user. Returns public user dict on success, None if email exists."""
    pwd_hash, pwd_salt = _hash_password(password)
    user_id = secrets.token_urlsafe(16)
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO auth_users(user_id, email, name, pwd_hash, pwd_salt) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, email, name, pwd_hash, pwd_salt),
            )
        return {"user_id": user_id, "email": email, "name": name}
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def verify_credentials(email: str, password: str) -> dict[str, Any] | None:
    """
    Return public user dict if credentials are valid, else None.

    Always spends comparable time whether the account exists or not,
    preventing timing-based email enumeration (constant-time path via dummy hash).
    """
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT user_id, email, name, pwd_hash, pwd_salt "
            "FROM auth_users WHERE email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        _hash_password(password)  # consume time; discard result
        return None

    row = dict(row)
    if not _verify_password(password, row["pwd_hash"], row["pwd_salt"]):
        return None

    return {"user_id": row["user_id"], "email": row["email"], "name": row["name"]}


# ---------------------------------------------------------------------------
# Session CRUD
# ---------------------------------------------------------------------------

def create_session(user_id: str) -> str:
    """Create a new session and return the opaque token."""
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO auth_sessions(token, user_id, expires_at) VALUES (?, ?, ?)",
                (token, user_id, expires),
            )
    finally:
        conn.close()
    return token


def get_session_user(token: str) -> dict[str, Any] | None:
    """Return public user dict if the session is valid and unexpired, else None."""
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT u.user_id, u.email, u.name, s.expires_at
            FROM auth_sessions s
            JOIN auth_users u ON u.user_id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    row = dict(row)
    expires_str = row["expires_at"]
    # Normalise the ISO string to always carry timezone info.
    if expires_str.endswith("Z"):
        expires_str = expires_str[:-1] + "+00:00"
    elif "+" not in expires_str and not expires_str.endswith("+00:00"):
        expires_str += "+00:00"

    try:
        expires = datetime.fromisoformat(expires_str)
    except ValueError:
        return None

    if expires < datetime.now(timezone.utc):
        return None

    return {"user_id": row["user_id"], "email": row["email"], "name": row["name"]}


def delete_session(token: str) -> None:
    conn = _connect()
    try:
        with conn:
            conn.execute("DELETE FROM auth_sessions WHERE token = ?", (token,))
    finally:
        conn.close()
