import asyncio
import os
import sys

import pytest


BACKEND_ROOT = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(BACKEND_ROOT)
for path in (REPO_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test")


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


def verify_test_user(user_id: str) -> None:
    """Mark a test user's email as verified using a direct synchronous psycopg2 connection.

    Avoids event-loop conflicts with TestClient's internal asyncpg pool.
    """
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test")
    # Strip asyncpg driver prefix if present
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(sync_url)
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email_verified = true WHERE id = %s::uuid", (user_id,))
        conn.commit()
    finally:
        conn.close()
