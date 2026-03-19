import pandas as pd

from database import load_datasets
from exceptions import BadRequestError
from evaluator import MAX_RESULT_ROWS, evaluate, normalize_dataframe, run_query
from questions import get_question
from questions import QUESTIONS
from sample_questions import SAMPLE_QUESTIONS


Q_USERS_ONLY = get_question(1001)
Q_MULTI_TABLES = {
    "dataset_files": [
        "users.csv",
        "employees.csv",
        "departments.csv",
        "orders.csv",
        "products.csv",
    ]
}


def setup_module() -> None:
    load_datasets()


def test_run_query_returns_rows() -> None:
    assert Q_USERS_ONLY is not None
    result = run_query(
        "SELECT user_id, name FROM users ORDER BY user_id LIMIT 2",
        Q_USERS_ONLY,
    )
    assert result["columns"] == ["user_id", "name"]
    assert len(result["rows"]) == 2


def test_run_query_blocks_non_select() -> None:
    try:
        run_query("DROP TABLE users", Q_USERS_ONLY)
    except BadRequestError as exc:
        assert "Only SELECT queries are allowed" in str(exc)
        return
    assert False, "Expected ValueError for disallowed query"


def test_run_query_allows_with_cte() -> None:
    result = run_query(
        "WITH recent AS (SELECT * FROM users WHERE signup_date >= DATE '2023-01-01') "
        "SELECT COUNT(*) AS cnt FROM recent",
        Q_USERS_ONLY,
    )
    assert result["columns"] == ["cnt"]
    assert result["rows"][0][0] >= 1


def test_run_query_blocks_multi_statement() -> None:
    try:
        run_query("SELECT 1; SELECT 2;", Q_USERS_ONLY)
    except BadRequestError as exc:
        assert "single SQL statement" in str(exc)
        return
    assert False, "Expected ValueError for multi-statement query"


def test_run_query_blocks_cartesian_join() -> None:
    try:
        run_query("SELECT * FROM users CROSS JOIN orders", Q_MULTI_TABLES)
    except BadRequestError as exc:
        assert "Cartesian join" in str(exc)
        return
    assert False, "Expected ValueError for Cartesian join"


def test_run_query_blocks_too_many_joins() -> None:
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
    assert False, "Expected ValueError for too many joins"


def test_run_query_enforces_row_limit() -> None:
    result = run_query(
        "SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders "
        "UNION ALL SELECT * FROM orders",
        {"dataset_files": ["orders.csv"]},
    )
    assert len(result["rows"]) <= MAX_RESULT_ROWS


def test_run_query_blocks_unrelated_table_access() -> None:
    try:
        run_query("SELECT * FROM orders LIMIT 1", Q_USERS_ONLY)
    except BadRequestError as exc:
        assert "orders" in str(exc).lower() or "catalog" in str(exc).lower() or "table" in str(exc).lower()
        return
    assert False, "Expected failure when querying table outside question datasets"


def test_evaluate_correct_solution() -> None:
    q1 = get_question(1001)
    assert q1 is not None
    result = evaluate(q1["solution_query"], q1["expected_query"], q1)
    assert result["correct"] is True


def test_evaluate_respects_order_by_direction() -> None:
    # Easy question 1016 orders by u.user_id ascending. A descending answer must fail.
    q1016 = get_question(1016)
    assert q1016 is not None

    wrong_order_query = (
        "SELECT u.user_id, u.name, COUNT(o.order_id) AS order_count "
        "FROM users u "
        "LEFT JOIN orders o ON u.user_id = o.user_id "
        "GROUP BY u.user_id, u.name "
        "ORDER BY u.user_id DESC"
    )
    result = evaluate(wrong_order_query, q1016["expected_query"], q1016)
    assert result["correct"] is False


def test_all_challenge_queries_execute_against_current_datasets() -> None:
    for question in QUESTIONS:
        result = run_query(question["expected_query"], question)
        assert "columns" in result
        assert "rows" in result


def test_all_sample_queries_execute_against_current_datasets() -> None:
    for question in SAMPLE_QUESTIONS:
        result = run_query(question["expected_query"], question)
        assert "columns" in result
        assert "rows" in result


# ---------------------------------------------------------------------------
# normalize_dataframe unit tests
# ---------------------------------------------------------------------------

def test_normalize_lowercases_columns() -> None:
    df = pd.DataFrame([[1, 2]], columns=["Name", "SALARY"])
    out = normalize_dataframe(df)
    assert list(out.columns) == ["name", "salary"]


def test_normalize_sorts_columns() -> None:
    df = pd.DataFrame([[1, 2, 3]], columns=["z_col", "a_col", "m_col"])
    out = normalize_dataframe(df)
    assert list(out.columns) == ["a_col", "m_col", "z_col"]


def test_normalize_sorts_rows() -> None:
    df = pd.DataFrame([["b"], ["a"], ["c"]], columns=["v"])
    out = normalize_dataframe(df)
    assert list(out["v"]) == ["a", "b", "c"]


def test_normalize_resets_index() -> None:
    df = pd.DataFrame([["x"], ["y"]], columns=["v"], index=[5, 10])
    out = normalize_dataframe(df)
    assert list(out.index) == [0, 1]


def test_normalize_null_none_becomes_NULL_string() -> None:
    df = pd.DataFrame([[None], [1]], columns=["v"])
    out = normalize_dataframe(df)
    assert "NULL" in out["v"].values


def test_normalize_float_nan_becomes_NULL_string() -> None:
    df = pd.DataFrame([[float("nan")], [1.0]], columns=["v"])
    out = normalize_dataframe(df)
    assert "NULL" in out["v"].values


def test_normalize_pd_NA_becomes_NULL_string() -> None:
    # Nullable integer series uses pd.NA for missing values
    s = pd.array([1, pd.NA, 3], dtype="Int64")
    df = pd.DataFrame({"v": s})
    out = normalize_dataframe(df)
    assert "NULL" in out["v"].values


def test_normalize_float_rounds_to_5dp() -> None:
    # Two values that differ only beyond 5 decimal places must compare equal
    df1 = pd.DataFrame([[1.123456789]], columns=["v"])
    df2 = pd.DataFrame([[1.123460000]], columns=["v"])
    assert normalize_dataframe(df1).equals(normalize_dataframe(df2))


def test_normalize_distinct_floats_not_equal() -> None:
    df1 = pd.DataFrame([[1.10000]], columns=["v"])
    df2 = pd.DataFrame([[1.20000]], columns=["v"])
    assert not normalize_dataframe(df1).equals(normalize_dataframe(df2))


def test_normalize_int_float_parity() -> None:
    # An INTEGER 5 and a FLOAT 5.0 represent the same answer
    df_int = pd.DataFrame([[5]], columns=["v"])         # int64 column
    df_float = pd.DataFrame([[5.0]], columns=["v"])     # float64 column
    assert normalize_dataframe(df_int).equals(normalize_dataframe(df_float))


def test_normalize_preserves_duplicate_rows() -> None:
    # Duplicates must not be silently dropped — COUNT(*) correctness depends on this
    df1 = pd.DataFrame([["a"], ["a"], ["b"]], columns=["v"])
    df2 = pd.DataFrame([["a"], ["b"]], columns=["v"])
    assert not normalize_dataframe(df1).equals(normalize_dataframe(df2))


def test_normalize_column_order_independence() -> None:
    # Same data, different column order — should be equal after normalisation
    df1 = pd.DataFrame([[1, 2]], columns=["a", "b"])
    df2 = pd.DataFrame([[2, 1]], columns=["b", "a"])
    assert normalize_dataframe(df1).equals(normalize_dataframe(df2))


def test_normalize_row_order_independence() -> None:
    df1 = pd.DataFrame([[1, "x"], [2, "y"]], columns=["id", "label"])
    df2 = pd.DataFrame([[2, "y"], [1, "x"]], columns=["id", "label"])
    assert normalize_dataframe(df1).equals(normalize_dataframe(df2))

