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

    asyncio.run(close_pool())
    asyncio.run(ensure_schema_admin())
    asyncio.run(reset_database_admin())
    yield
    asyncio.run(close_pool())
    asyncio.run(reset_database_admin())
