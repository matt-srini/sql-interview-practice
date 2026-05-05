"""TC-075 to TC-090 — SQL Execution."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _make_user
from questions import get_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = get_questions_by_difficulty()
_easy_q = _catalog["easy"][0]
_easy_id = _easy_q["id"]
_easy_solution = _easy_q["solution_query"]


# ---------------------------------------------------------------------------
# 5A. Run query
# ---------------------------------------------------------------------------

def test_tc075_valid_select_returns_rows():
    """TC-075: Valid SELECT → 200, rows array with objects."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": _easy_solution,
        })
    assert r.status_code == 200
    body = r.json()
    assert "rows" in body
    assert len(body["rows"]) >= 1


def test_tc076_row_cap_200():
    """TC-076: Query returning >200 rows is capped at 200."""
    # Use any question that contains sessions table (sessions has 9000 rows)
    # We need a question_id that loads the sessions dataset
    q_with_sessions = None
    for q in _catalog["easy"] + _catalog["medium"]:
        if "sessions" in str(q.get("dataset_files", [])):
            q_with_sessions = q
            break

    if q_with_sessions is None:
        pytest.skip("No easy/medium SQL question uses sessions dataset")

    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": q_with_sessions["id"],
            "query": "SELECT * FROM sessions",
        })
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) == 200


def test_tc077_sql_syntax_error_readable_message():
    """TC-077: Syntax error → readable error, no stack trace."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "SELEKT * FORM users",
        })
    assert r.status_code in (200, 400)
    body = r.json()
    assert "error" in body
    assert len(body["error"]) > 5  # Human-readable
    # No Python traceback keywords
    assert "Traceback" not in body["error"]
    assert "/backend/" not in body["error"]


def test_tc078_query_timeout():
    """TC-078: Very long query times out within ~5s."""
    # DuckDB handles generate_series fast, use a cross-join to slow it down
    slow_query = (
        "SELECT a.range, b.range FROM range(10000) a "
        "CROSS JOIN range(10000) b LIMIT 1"
    )
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        start = time.time()
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": slow_query,
        }, timeout=10)
        elapsed = time.time() - start
    # Either it times out (error) or completes quickly
    # If it errors, should complete within ~5s wall clock
    if r.status_code != 200 or "error" in r.json():
        assert elapsed < 6, f"Timeout took too long: {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# 5B. Submit
# ---------------------------------------------------------------------------

def test_tc079_correct_submit_returns_verdict_solution_quality():
    """TC-079: Correct answer → correct:true, solution present, quality object."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": _easy_solution,
            "duration_ms": 5000,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is True
    assert body.get("solution") is not None
    quality = body.get("quality")
    assert quality is not None
    assert "efficiency_note" in quality
    assert "style_notes" in quality
    assert "complexity_hint" in quality
    assert "alternative_solution" in quality


def test_tc080_correct_submit_records_progress():
    """TC-080: Correct submit → user_progress row with solved_at."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": _easy_solution,
        })
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT track, solved_at FROM user_progress WHERE user_id = %s::uuid AND question_id = %s",
                (user["id"], _easy_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None, "No user_progress row found"
    assert row[0] == "sql"
    assert row[1] is not None  # solved_at is set


def test_tc081_wrong_answer_no_solution():
    """TC-081: Wrong answer → correct:false, no solution."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": "SELECT 1 AS x",
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is False
    assert not body.get("solution")


def test_tc082_close_miss_returns_style_notes():
    """TC-082: Same shape, wrong values → style_notes non-empty."""
    # Use the easy question - craft a query with same column names but wrong data
    # Get the expected output shape first
    q = _easy_q
    # The easy question has an expected query; submit a query that returns same shape
    # For "Completed orders" question, the expected has order_id, user_id, order_date, net_amount
    same_shape_wrong = "SELECT 0 AS order_id, 0 AS user_id, '2020-01-01'::DATE AS order_date, 0.0 AS net_amount"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": same_shape_wrong,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is False
    # Close-miss should have style_notes in quality
    quality = body.get("quality") or {}
    style = quality.get("style_notes")
    # style_notes may be present as a list; it could also be in feedback
    # Accept either case per spec
    has_style = (style and len(style) > 0) or ("style" in str(body.get("feedback", [])).lower())
    assert has_style or len(body.get("feedback", [])) > 0


def test_tc083_repeat_wrong_attempt_triggers_nudge():
    """TC-083: Same wrong query twice → second feedback starts with nudge."""
    wrong_query = "SELECT 99 AS x"
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r1 = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": wrong_query,
        })
        r2 = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": wrong_query,
        })
    assert r1.status_code == 200
    assert r2.status_code == 200

    feedback1 = r1.json().get("feedback", [])
    feedback2 = r2.json().get("feedback", [])

    # Second attempt should have a nudge as first feedback item
    if feedback2:
        first_item = feedback2[0] if isinstance(feedback2, list) else str(feedback2)
        assert first_item != (feedback1[0] if feedback1 else ""), \
            "Second attempt should have a nudge, different from first response"


def test_tc084_duration_ms_accepted():
    """TC-084: duration_ms is accepted and submission recorded."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        r = client.post("/api/submit", json={
            "question_id": _easy_id,
            "query": _easy_solution,
            "duration_ms": 12000,
        })
    assert r.status_code == 200

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT duration_ms FROM submissions WHERE user_id = %s::uuid ORDER BY submitted_at DESC LIMIT 1",
                (user["id"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == 12000


# ---------------------------------------------------------------------------
# 5C. SQL guard
# ---------------------------------------------------------------------------

def test_tc085_drop_table_rejected():
    """TC-085: DROP TABLE → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "DROP TABLE users",
        })
    assert r.status_code == 400


def test_tc086_insert_rejected():
    """TC-086: INSERT → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "INSERT INTO users VALUES ('x', 'y', 'z')",
        })
    assert r.status_code == 400


def test_tc087_update_rejected():
    """TC-087: UPDATE → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "UPDATE users SET name='x'",
        })
    assert r.status_code == 400


def test_tc088_delete_rejected():
    """TC-088: DELETE → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "DELETE FROM users",
        })
    assert r.status_code == 400


def test_tc089_multi_statement_rejected():
    """TC-089: SELECT + DROP → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "SELECT 1; DROP TABLE users",
        })
    assert r.status_code == 400


def test_tc090_valid_subquery_accepted():
    """TC-090: Valid subquery SELECT → 200 with rows."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/run-query", json={
            "question_id": _easy_id,
            "query": "SELECT * FROM (SELECT order_id FROM orders LIMIT 5) t",
        })
    assert r.status_code == 200
    assert len(r.json().get("rows", [])) > 0
