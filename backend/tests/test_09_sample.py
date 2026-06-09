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


def test_tc111_repeated_get_returns_same_question_resume_model():
    """TC-111 (resume model): Two GET /api/sample/sql/easy calls return the
    SAME question — GET is read-only under the resume model. Marking happens
    only on submit or explicit skip."""
    with TestClient(app) as client:
        r1 = client.get("/api/sample/sql/easy")
        r2 = client.get("/api/sample/sql/easy")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both calls should return Q1 (the same question) — viewing does not advance.
    assert r1.json()["id"] == r2.json()["id"]
    # Counters: position=1, attempted=0 — nothing has been committed yet.
    assert r1.json()["sample"]["position"] == 1
    assert r1.json()["sample"]["attempted"] == 0


def test_tc112_after_3_submits_returns_409():
    """TC-112 (resume model): After 3 *submits* (not just views), 4th GET → 409.
    Pure GETs no longer exhaust the pool — only commitment (submit) does."""
    with TestClient(app) as client:
        for _ in range(3):
            r = client.get("/api/sample/sql/easy")
            assert r.status_code == 200
            qid = r.json()["id"]
            # Submit something (correctness doesn't matter for the seen state)
            client.post("/api/sample/sql/submit", json={"question_id": qid, "query": "SELECT 1"})
        r4 = client.get("/api/sample/sql/easy")
    assert r4.status_code == 409


def test_tc113_reset_clears_seen_state():
    """TC-113: Exhaust easy SQL samples via submits; POST /reset; GET works again."""
    with TestClient(app) as client:
        # Exhaust 3 samples by submitting each
        for _ in range(3):
            r = client.get("/api/sample/sql/easy")
            qid = r.json()["id"]
            client.post("/api/sample/sql/submit", json={"question_id": qid, "query": "SELECT 1"})
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
    """TC-116: Exhausting SQL easy samples (via submits) doesn't affect Python easy pool."""
    with TestClient(app) as client:
        # Exhaust SQL easy via submits (not just views)
        for _ in range(3):
            r = client.get("/api/sample/sql/easy")
            qid = r.json()["id"]
            client.post("/api/sample/sql/submit", json={"question_id": qid, "query": "SELECT 1"})
        assert client.get("/api/sample/sql/easy").status_code == 409
        # Python easy still available
        r_python = client.get("/api/sample/python/easy")
    assert r_python.status_code == 200


def test_tc117_all_4_sample_tracks_accessible():
    """TC-117: All 4 sample tracks return 200."""
    with TestClient(app) as client:
        r_sql = client.get("/api/sample/sql/easy")
        r_python = client.get("/api/sample/python/easy")
        r_pandas = client.get("/api/sample/pandas/easy")
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


def test_tc121_submit_marks_question_as_attempted():
    """TC-121 (resume model): Submitting an answer advances the user to the
    next question on the subsequent GET — submit is the commitment event that
    marks the question as attempted."""
    with TestClient(app) as client:
        r1 = client.get("/api/sample/sql/easy")
        qid1 = r1.json()["id"]
        # Submit (correctness doesn't matter; marking happens either way)
        sub = client.post("/api/sample/sql/submit", json={"question_id": qid1, "query": "SELECT 1"})
        assert sub.status_code == 200
        # Next GET returns Q2
        r2 = client.get("/api/sample/sql/easy")
    assert r2.status_code == 200
    assert r2.json()["id"] != qid1
    assert r2.json()["sample"]["position"] == 2
    assert r2.json()["sample"]["attempted"] == 1


def test_tc122_skip_endpoint_marks_seen_and_returns_next():
    """TC-122 (resume model): POST /skip marks the supplied question as
    attempted and returns the next unattempted question in the pool."""
    with TestClient(app) as client:
        r1 = client.get("/api/sample/sql/easy")
        qid1 = r1.json()["id"]
        # Skip Q1
        skip = client.post(
            "/api/sample/sql/easy/skip",
            json={"question_id": qid1},
        )
        assert skip.status_code == 200
        # Response is shaped like a GET — has the next question
        assert skip.json()["id"] != qid1
        assert skip.json()["sample"]["position"] == 2
        assert skip.json()["sample"]["attempted"] == 1
        # Subsequent plain GET also returns Q2 (skip persisted, view did not advance)
        r2 = client.get("/api/sample/sql/easy")
    assert r2.status_code == 200
    assert r2.json()["id"] == skip.json()["id"]


def test_tc123_skip_requires_question_id():
    """TC-123: POST /skip without a question_id payload → 422."""
    with TestClient(app) as client:
        r = client.post("/api/sample/sql/easy/skip", json={})
    assert r.status_code == 422


def test_tc119_sample_summary_returns_all_tracks_with_zero_tried():
    """TC-119: GET /api/sample/summary → 200 with every track + difficulty,
    tried=0 for a fresh anonymous user, totals match catalog shape."""
    with TestClient(app) as client:
        r = client.get("/api/sample/summary")
    assert r.status_code == 200
    body = r.json()
    assert "tracks" in body
    tracks = body["tracks"]

    # Every active track (9) appears with all 3 difficulties.
    expected_slugs = {
        "sql", "python", "pandas", "pyspark",
        "data-engineering", "data-modeling", "statistics",
        "ml-fundamentals", "experimentation",
    }
    assert set(tracks.keys()) >= expected_slugs

    for slug in expected_slugs:
        diffs = tracks[slug]
        for d in ("easy", "medium", "hard"):
            assert d in diffs
            cell = diffs[d]
            assert cell["total"] == 3  # 3 samples per (track, difficulty)
            assert cell["tried"] == 0


def test_tc120_sample_summary_tracks_attempted_count():
    """TC-120 (resume model): summary counts submits/skips as attempted, not
    plain GETs. Two GETs should report 0; one submit then one GET reports 1."""
    with TestClient(app) as client:
        # Two plain GETs — should NOT count as attempted under resume model
        client.get("/api/sample/sql/easy")
        client.get("/api/sample/sql/easy")
        r_before = client.get("/api/sample/summary")
        assert r_before.json()["tracks"]["sql"]["easy"]["tried"] == 0

        # Submit once — now the summary should reflect 1 attempted
        r1 = client.get("/api/sample/sql/easy")
        qid = r1.json()["id"]
        client.post("/api/sample/sql/submit", json={"question_id": qid, "query": "SELECT 1"})
        r_after = client.get("/api/sample/summary")
    assert r_after.status_code == 200
    body = r_after.json()
    assert body["tracks"]["sql"]["easy"]["tried"] == 1
    assert body["tracks"]["sql"]["easy"]["total"] == 3
    # Other tracks still 0
    assert body["tracks"]["python"]["easy"]["tried"] == 0


def test_tc118_sample_run_code_for_pandas_executes():
    """TC-118: Sample run-code for pandas → 200 with test results.
    Uses dedicated sample question 311 (not a practice question).
    """
    import json as _json
    from pathlib import Path
    sample_file = Path(__file__).resolve().parent.parent / "content" / "sample_questions" / "pandas.json"
    sample_qs = _json.loads(sample_file.read_text())
    easy_q = next(q for q in sample_qs if q["difficulty"] == "easy")

    code = easy_q["solution_code"]
    with TestClient(app) as client:
        r = client.post("/api/sample/pandas/run-code", json={
            "question_id": easy_q["id"],
            "code": code,
        })
    assert r.status_code == 200
    body = r.json()
    assert "test_results" in body
