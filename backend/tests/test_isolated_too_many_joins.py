
import os
import tempfile
import pytest
from exceptions import BadRequestError
from evaluator import run_query
import backend.database as database

Q_MULTI_TABLES = {
    "dataset_files": [
        "users.csv",
        "employees.csv",
        "departments.csv",
        "orders.csv",
        "products.csv",
    ]
}

@pytest.fixture(autouse=True)
def patch_duckdb_path(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.duckdb")
        monkeypatch.setattr(database, "DB_PATH", db_path)
        database.init_user_profile_storage()
        yield

def test_run_query_blocks_too_many_joins():
    try:
        run_query(
            "SELECT 1 "
            "FROM users u "
            "JOIN orders o ON o.user_id = u.user_id "
            "JOIN employees e ON e.country = u.country "
            "JOIN departments d ON d.department_id = e.department_id "
            "JOIN products p ON p.is_active = TRUE "
            "JOIN users u2 ON u2.user_id = u.user_id",
            Q_MULTI_TABLES,
        )
    except BadRequestError as exc:
        assert "Maximum" in str(exc)
        return
    assert False, "Expected BadRequestError for too many joins"
