import pandas as pd

from database import close_query_engine, init_query_engine
from exceptions import BadRequestError
from evaluator import MAX_RESULT_ROWS, evaluate, normalize_dataframe, run_query
from questions import get_question
from questions import QUESTIONS
from sample_questions import SAMPLE_QUESTIONS
from sql_analyzer import extract_query_features


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
    init_query_engine()


def teardown_module() -> None:
    close_query_engine()


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
    assert False, "Expected BadRequestError for too many joins"


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


def test_run_query_allows_other_loaded_tables() -> None:
    result = run_query("SELECT * FROM orders LIMIT 1", Q_USERS_ONLY)
    assert result["columns"]
    assert len(result["rows"]) == 1


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
        try:
            result = run_query(question["expected_query"], question)
            assert "columns" in result
            assert "rows" in result
        except BadRequestError as exc:
            # Allow failure for too many joins or cartesian join
            if "Maximum" in str(exc) or "Cartesian join" in str(exc):
                continue
            raise


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


# ---------------------------------------------------------------------------
# sql_analyzer — extract_query_features unit tests
# ---------------------------------------------------------------------------

def test_extract_features_group_by() -> None:
    f = extract_query_features("SELECT user_id, COUNT(*) FROM orders GROUP BY user_id")
    assert f["has_group_by"] is True
    assert f["has_aggregation"] is True
    assert f["has_join"] is False


def test_extract_features_left_join() -> None:
    f = extract_query_features("SELECT u.name, o.order_id FROM users u LEFT JOIN orders o ON u.user_id = o.user_id")
    assert f["has_left_join"] is True
    assert f["has_join"] is True


def test_extract_features_inner_join_not_left() -> None:
    f = extract_query_features("SELECT u.name FROM users u JOIN orders o ON u.user_id = o.user_id")
    assert f["has_join"] is True
    assert f["has_left_join"] is False


def test_extract_features_subquery() -> None:
    f = extract_query_features("SELECT * FROM (SELECT user_id FROM users) sub")
    assert f["has_subquery"] is True


def test_extract_features_window_function() -> None:
    f = extract_query_features("SELECT user_id, ROW_NUMBER() OVER (ORDER BY user_id) FROM users")
    assert f["has_window_function"] is True


def test_extract_features_where_and_order_by() -> None:
    f = extract_query_features("SELECT name FROM users WHERE country = 'US' ORDER BY name")
    assert f["has_where"] is True
    assert f["has_order_by"] is True
    assert f["has_group_by"] is False


def test_extract_features_distinct() -> None:
    f = extract_query_features("SELECT DISTINCT country FROM users")
    assert f["has_distinct"] is True


def test_extract_features_having() -> None:
    f = extract_query_features("SELECT user_id, COUNT(*) FROM orders GROUP BY user_id HAVING COUNT(*) > 5")
    assert f["has_having"] is True
    assert f["has_group_by"] is True


def test_extract_features_no_features() -> None:
    f = extract_query_features("SELECT user_id, name FROM users")
    assert f["has_group_by"] is False
    assert f["has_join"] is False
    assert f["has_subquery"] is False
    assert f["has_window_function"] is False


# ---------------------------------------------------------------------------
# evaluate() — hybrid evaluation (result + concept-aware feedback)
# ---------------------------------------------------------------------------

# Minimal question fixture with required_concepts and enforce_concepts
_Q_CONCEPTS_ENFORCED = {
    **get_question(1001),  # type: ignore[arg-type]
    "required_concepts": ["group_by"],
    "enforce_concepts": True,
}

_Q_CONCEPTS_SOFT = {
    **get_question(1001),  # type: ignore[arg-type]
    "required_concepts": ["group_by"],
    "enforce_concepts": False,
}


def test_evaluate_returns_new_fields() -> None:
    """evaluate() must always return structure_correct and feedback."""
    q = get_question(1001)
    result = evaluate(q["solution_query"], q["expected_query"], q)
    assert "structure_correct" in result
    assert "feedback" in result
    assert isinstance(result["feedback"], list)


def test_evaluate_no_concepts_defined_is_always_structure_correct() -> None:
    q = get_question(1003)
    assert not q.get("required_concepts")
    result = evaluate(q["solution_query"], q["expected_query"], q)
    assert result["structure_correct"] is True
    assert result["feedback"] == ["Your solution is correct and follows the intended approach."]


def test_evaluate_correct_result_correct_structure() -> None:
    """Correct result + required concept used → both flags True with positive feedback."""
    q = get_question(1016)  # order count per user — uses GROUP BY
    assert q is not None
    q_with_concepts = {**q, "required_concepts": ["group_by"], "enforce_concepts": True}
    result = evaluate(q["solution_query"], q["expected_query"], q_with_concepts)
    assert result["correct"] is True
    assert result["structure_correct"] is True
    assert result["feedback"] == ["Your solution is correct and follows the intended approach."]


def test_evaluate_correct_result_wrong_structure_enforced() -> None:
    """Solution is correct but required concept missing + enforced → structure_correct=False."""
    q = get_question(1001)  # simple SELECT, no GROUP BY
    result = evaluate(q["solution_query"], q["expected_query"], _Q_CONCEPTS_ENFORCED)
    assert result["correct"] is True           # result still correct
    assert result["structure_correct"] is False  # concept enforced and missing
    assert len(result["feedback"]) > 0
    assert result["feedback"][0] == "Your result is correct, but the required approach was not followed."
    assert any("GROUP BY" in message for message in result["feedback"])


def test_evaluate_correct_result_wrong_structure_soft() -> None:
    """Solution is correct but required concept missing, not enforced → soft feedback only."""
    q = get_question(1001)
    result = evaluate(q["solution_query"], q["expected_query"], _Q_CONCEPTS_SOFT)
    assert result["correct"] is True
    assert result["structure_correct"] is True   # not enforced → still True
    assert len(result["feedback"]) > 0
    assert "consider using" in result["feedback"][0].lower()


def test_evaluate_wrong_result() -> None:
    """Wrong result → correct=False regardless of concept state."""
    q = get_question(1001)
    result = evaluate("SELECT user_id FROM users LIMIT 1", q["expected_query"], q)
    assert result["correct"] is False
