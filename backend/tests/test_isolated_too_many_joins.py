from exceptions import BadRequestError
from evaluator import run_query

Q_MULTI_TABLES = {
    "dataset_files": [
        "users.csv",
        "employees.csv",
        "departments.csv",
        "orders.csv",
        "products.csv",
    ]
}

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
