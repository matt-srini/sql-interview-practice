"""TC-110 to TC-118 — Sample Mode."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _make_user
from sample_questions import get_sample_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_sql_sample_q = get_sample_questions_by_difficulty()["easy"][0]
_sql_sample_id = _sql_sample_q["id"]
_sql_sample_solution = _sql_sample_q["solution_query"]


def test_tc110_anonymous_user_can_access_sample_questions():
    """TC-110: Anonymous user can GET /api/sample/sql/easy → 200."""
    with TestClient(app) as client:
        r = client.get("/api/sample/sql/easy")
    assert r.status_code == 200
    body = r.json()
    assert "id" in body
    assert "title" in body


def test_tc111_second_call_returns_different_question():
    """TC-111: Two GET /api/sample/sql/easy calls return different questions."""
    with TestClient(app) as client:
        r1 = client.get("/api/sample/sql/easy")
        r2 = client.get("/api/sample/sql/easy")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]


def test_tc112_after_all_3_samples_seen_returns_409():
    """TC-112: After 3 easy SQL samples seen, 4th call → 409."""
    with TestClient(app) as client:
        for _ in range(3):
            r = client.get("/api/sample/sql/easy")
            assert r.status_code == 200
        r4 = client.get("/api/sample/sql/easy")
    assert r4.status_code == 409


def test_tc113_reset_clears_seen_state():
    """TC-113: Exhaust easy SQL samples; POST /reset; GET works again."""
    with TestClient(app) as client:
        # Exhaust 3 samples
        for _ in range(3):
            client.get("/api/sample/sql/easy")
        # Confirm exhausted
        assert client.get("/api/sample/sql/easy").status_code == 409
        # Reset
        r_reset = client.post("/api/sample/sql/easy/reset")
        assert r_reset.status_code == 200
        # Can access again
        r_fresh = client.get("/api/sample/sql/easy")
    assert r_fresh.status_code == 200


def test_tc114_sample_run_query_does_not_record_challenge_progress():
    """TC-114: Sample run-query runs OK, no user_progress row created."""
    with TestClient(app) as client:
        user = _make_user(client)
        r = client.post("/api/sample/sql/run-query", json={
            "query": "SELECT 1 AS x",
            "question_id": _sql_sample_id,
        })
    assert r.status_code == 200

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_progress WHERE user_id = %s::uuid",
                (user["id"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row[0] == 0, "user_progress should be empty after sample run-query"


def test_tc115_sample_submit_does_not_record_challenge_progress():
    """TC-115: Sample submit returns verdict; no user_progress row."""
    with TestClient(app) as client:
        user = _make_user(client)
        r = client.post("/api/sample/sql/submit", json={
            "question_id": _sql_sample_id,
            "query": _sql_sample_solution,
        })
    assert r.status_code == 200
    body = r.json()
    assert "correct" in body or "solution_query" in body

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM user_progress WHERE user_id = %s::uuid",
                (user["id"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row[0] == 0


def test_tc116_sql_seen_does_not_affect_python_pool():
    """TC-116: Exhausting SQL easy samples doesn't affect Python easy pool."""
    with TestClient(app) as client:
        # Exhaust SQL easy
        for _ in range(3):
            client.get("/api/sample/sql/easy")
        assert client.get("/api/sample/sql/easy").status_code == 409
        # Python easy still available
        r_python = client.get("/api/sample/python/easy")
    assert r_python.status_code == 200


def test_tc117_all_4_sample_tracks_accessible():
    """TC-117: All 4 sample tracks return 200."""
    with TestClient(app) as client:
        r_sql = client.get("/api/sample/sql/easy")
        r_python = client.get("/api/sample/python/easy")
        r_pandas = client.get("/api/sample/python-data/easy")
        r_pyspark = client.get("/api/sample/pyspark/easy")

    assert r_sql.status_code == 200
    assert r_python.status_code == 200
    assert r_pandas.status_code == 200
    assert r_pyspark.status_code == 200
    # Each returns different structure appropriate to its track
    assert "id" in r_sql.json()
    assert "id" in r_python.json()
    assert "id" in r_pandas.json()
    assert "id" in r_pyspark.json()


def test_tc118_sample_run_code_for_python_data_executes_pandas():
    """TC-118: Sample run-code for python-data → 200 with test results."""
    from python_data_questions import get_questions_by_difficulty as get_pq
    easy_q = get_pq()["easy"][0]

    code = easy_q["solution_code"]
    with TestClient(app) as client:
        r = client.post("/api/sample/python-data/run-code", json={
            "question_id": easy_q["id"],
            "code": code,
        })
    assert r.status_code == 200
    body = r.json()
    assert "test_results" in body
