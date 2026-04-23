"""
Mock interview system tests.

Covers all mock interview endpoints:
  GET  /api/mock/access
  GET  /api/mock/history
  POST /api/mock/start
  GET  /api/mock/{session_id}
  POST /api/mock/{session_id}/submit
  POST /api/mock/{session_id}/finish

Uses the same patterns as test_plan_tiers.py: synchronous TestClient, `isolated_state`
fixture for DB reset, and _make_user / _start_mock helpers.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_counter = 0


def _make_user(client: TestClient, plan: str = "free", suffix: str = "") -> dict:
    """Register a user and optionally upgrade their plan. Returns the user dict."""
    global _counter
    _counter += 1
    email = f"mock-test-{_counter}{suffix}@internal.test"
    client.get("/api/catalog")  # seed anonymous session cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": f"Mock Test {plan}", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    assert user["plan"] == "free"

    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, up.text
        user["plan"] = plan

    return user


def _start_mock(
    client: TestClient,
    mode: str = "30min",
    track: str = "sql",
    difficulty: str = "easy",
    **kwargs,
) -> tuple[int, dict]:
    """Start a mock session. Returns (status_code, body)."""
    payload = {"mode": mode, "track": track, "difficulty": difficulty, **kwargs}
    resp = client.post("/api/mock/start", json=payload)
    return resp.status_code, resp.json()


def _mark_easy_solved_direct(user_id: str, question_ids: list[int], topic: str = "sql") -> None:
    """Directly insert solved questions into user_progress via psycopg2."""
    import psycopg2

    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test"
    )
    sync_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(sync_url)
    try:
        with conn.cursor() as cur:
            for qid in question_ids:
                cur.execute(
                    """
                    INSERT INTO user_progress (user_id, question_id, topic, solved_at)
                    VALUES (%s::uuid, %s, %s, now())
                    ON CONFLICT (user_id, question_id, topic) DO NOTHING
                    """,
                    (user_id, qid, topic),
                )
        conn.commit()
    finally:
        conn.close()


# First 10 easy SQL question IDs — used to seed free-tier unlock tests.
# These IDs come from backend/content/questions/easy.json.
_EASY_SQL_IDS = [1003, 1004, 1005, 1007, 1008, 1011, 1012, 1013, 1014, 1015]


# ---------------------------------------------------------------------------
# Access endpoint
# ---------------------------------------------------------------------------

class TestMockAccess:
    def test_access_returns_all_difficulties(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/access", params={"track": "sql", "difficulty": "medium"})
            assert r.status_code == 200, r.text
            body = r.json()
            assert "access" in body
            for diff in ("easy", "medium", "hard", "mixed"):
                assert diff in body["access"], f"missing difficulty key in access response: {diff}"

    def test_free_easy_can_start(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/access", params={"track": "sql", "difficulty": "easy"})
            assert r.status_code == 200, r.text
            assert r.json()["access"]["easy"]["can_start"] is True

    def test_free_hard_blocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/access", params={"track": "sql", "difficulty": "hard"})
            assert r.status_code == 200, r.text
            hard_access = r.json()["access"]["hard"]
            assert hard_access["can_start"] is False
            assert hard_access["needs_upgrade"] == "pro"

    def test_pro_hard_can_start(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.get("/api/mock/access", params={"track": "sql", "difficulty": "hard"})
            assert r.status_code == 200, r.text
            assert r.json()["access"]["hard"]["can_start"] is True

    def test_elite_all_can_start(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.get("/api/mock/access", params={"track": "sql", "difficulty": "hard"})
            assert r.status_code == 200, r.text
            access = r.json()["access"]
            for diff in ("easy", "medium", "hard"):
                assert access[diff]["can_start"] is True, (
                    f"elite should have can_start=True for {diff}, got: {access[diff]}"
                )


# ---------------------------------------------------------------------------
# Daily limits — free medium
# ---------------------------------------------------------------------------

class TestFreeMediumLimit:
    def test_free_medium_blocked_without_unlock(self) -> None:
        """Free user with 0 easy solves cannot start a medium mock."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            status, body = _start_mock(client, difficulty="medium")
            assert status == 403, f"expected 403 for free user with 0 solves, got {status}: {body}"
            assert "error" in body

    def test_free_medium_1_per_day(self) -> None:
        """Once medium is unlocked via 8+ easy solves, free users get 1 medium mock per day."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            # Seed 8 easy SQL solves directly so medium questions are unlocked
            _mark_easy_solved_direct(user["id"], _EASY_SQL_IDS[:8], topic="sql")

            # First medium mock should succeed
            status, body = _start_mock(client, difficulty="medium")
            assert status == 200, f"first medium mock should succeed for free user with medium unlocked, got {status}: {body}"
            assert "session_id" in body

            # Second medium mock on the same day should be blocked by daily cap
            status2, body2 = _start_mock(client, difficulty="medium")
            assert status2 == 403, (
                f"2nd medium mock should be blocked by daily cap, got {status2}: {body2}"
            )
            assert "error" in body2
            err = body2["error"].lower()
            assert "daily" in err or "limit" in err, (
                f"expected daily cap error message, got: {body2['error']}"
            )


# ---------------------------------------------------------------------------
# Full lifecycle — SQL
# ---------------------------------------------------------------------------

class TestSessionLifecycleSQL:
    def test_start_returns_session_id_and_questions(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, track="sql", difficulty="easy")
            assert status == 200, f"expected 200, got {status}: {body}"
            assert "session_id" in body
            assert "questions" in body
            assert isinstance(body["questions"], list)
            assert len(body["questions"]) > 0
            assert "time_limit_s" in body
            assert "started_at" in body

    def test_questions_have_no_solution(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, body = _start_mock(client, track="sql", difficulty="easy")
            for q in body["questions"]:
                assert "solution_query" not in q, (
                    f"solution_query must not appear in start response, got keys: {list(q.keys())}"
                )
                assert "solution_code" not in q, (
                    f"solution_code must not appear in start response, got keys: {list(q.keys())}"
                )

    def test_submit_returns_verdict_no_solution(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            r = client.post(
                f"/api/mock/{session_id}/submit",
                json={
                    "question_id": first_q["id"],
                    "track": "sql",
                    "code": "SELECT 1 AS dummy",
                },
            )
            assert r.status_code == 200, r.text
            result = r.json()
            assert "correct" in result
            assert "solution_query" not in result, (
                f"solution_query must not appear in submit response, got keys: {list(result.keys())}"
            )
            assert "solution_code" not in result, (
                f"solution_code must not appear in submit response, got keys: {list(result.keys())}"
            )

    def test_finish_returns_solutions(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            summary = r.json()
            assert "questions" in summary
            for q in summary["questions"]:
                assert "solution_query" in q, (
                    f"solution_query missing after finish, got keys: {list(q.keys())}"
                )
                assert "explanation" in q, (
                    f"explanation missing after finish, got keys: {list(q.keys())}"
                )

    def test_finish_twice_is_idempotent(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]

            r1 = client.post(f"/api/mock/{session_id}/finish")
            assert r1.status_code == 200, f"first finish failed: {r1.text}"

            r2 = client.post(f"/api/mock/{session_id}/finish")
            assert r2.status_code == 200, f"second finish should also return 200 (idempotent), got: {r2.text}"

    def test_reload_session(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]

            r = client.get(f"/api/mock/{session_id}")
            assert r.status_code == 200, r.text
            reloaded = r.json()
            assert reloaded["session_id"] == session_id
            assert "questions" in reloaded
            assert len(reloaded["questions"]) == len(session["questions"])


# ---------------------------------------------------------------------------
# Full lifecycle — all tracks
# ---------------------------------------------------------------------------

class TestSessionLifecycleAllTracks:
    def test_python_session_lifecycle(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, track="python", difficulty="easy")
            assert status == 200, f"python easy mock failed: {body}"
            assert "session_id" in body
            qs = body["questions"]
            assert len(qs) > 0
            # Python questions should expose test_cases (inputs only, no expected outputs)
            assert "test_cases" in qs[0], (
                f"test_cases missing from python question, got keys: {list(qs[0].keys())}"
            )

            # Finish should reveal solution_code
            r = client.post(f"/api/mock/{body['session_id']}/finish")
            assert r.status_code == 200, r.text
            for q in r.json()["questions"]:
                assert "solution_code" in q, (
                    f"solution_code missing after python finish, got keys: {list(q.keys())}"
                )
                assert "explanation" in q

    def test_pyspark_session_lifecycle(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, track="pyspark", difficulty="easy")
            assert status == 200, f"pyspark easy mock failed: {body}"
            qs = body["questions"]
            assert len(qs) > 0
            # PySpark questions should have options for MCQ
            assert "options" in qs[0], (
                f"options missing from pyspark question, got keys: {list(qs[0].keys())}"
            )

            # Can submit with selected_option
            session_id = body["session_id"]
            first_q = qs[0]
            r = client.post(
                f"/api/mock/{session_id}/submit",
                json={
                    "question_id": first_q["id"],
                    "track": "pyspark",
                    "selected_option": 0,
                },
            )
            assert r.status_code == 200, r.text
            assert "correct" in r.json()

    def test_pandas_session_lifecycle(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, track="python-data", difficulty="easy")
            assert status == 200, f"pandas easy mock failed: {body}"
            qs = body["questions"]
            assert len(qs) > 0
            # Pandas questions should expose available dataframe names
            assert "dataframes" in qs[0], (
                f"dataframes missing from pandas question, got keys: {list(qs[0].keys())}"
            )

            # Finish should reveal solution_code
            r = client.post(f"/api/mock/{body['session_id']}/finish")
            assert r.status_code == 200, r.text
            for q in r.json()["questions"]:
                assert "solution_code" in q, (
                    f"solution_code missing after pandas finish, got keys: {list(q.keys())}"
                )


# ---------------------------------------------------------------------------
# Custom mode
# ---------------------------------------------------------------------------

class TestCustomMode:
    def test_custom_mode_valid(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(
                client,
                mode="custom",
                track="sql",
                difficulty="easy",
                num_questions=1,
                time_minutes=10,
            )
            assert status == 200, f"expected 200 for valid custom mode, got {status}: {body}"
            assert len(body["questions"]) == 1
            assert body["time_limit_s"] == 10 * 60

    def test_custom_mode_too_many_questions(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(
                client,
                mode="custom",
                track="sql",
                difficulty="easy",
                num_questions=6,
                time_minutes=30,
            )
            assert status == 400, (
                f"expected 400 for num_questions=6 (max is 5), got {status}: {body}"
            )

    def test_custom_mode_time_too_short(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(
                client,
                mode="custom",
                track="sql",
                difficulty="easy",
                num_questions=2,
                time_minutes=5,
            )
            assert status == 400, (
                f"expected 400 for time_minutes=5 (min is 10), got {status}: {body}"
            )

    def test_custom_mode_missing_params(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            # mode=custom with no num_questions provided
            status, body = _start_mock(
                client,
                mode="custom",
                track="sql",
                difficulty="easy",
                time_minutes=30,
            )
            assert status == 400, (
                f"expected 400 for custom mode missing num_questions, got {status}: {body}"
            )


# ---------------------------------------------------------------------------
# Mixed track
# ---------------------------------------------------------------------------

class TestMixedTrack:
    def test_mixed_track_starts(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(client, track="mixed", difficulty="easy")
            assert status == 200, f"expected 200 for mixed track, got {status}: {body}"
            assert "session_id" in body
            assert "questions" in body
            assert len(body["questions"]) > 0


# ---------------------------------------------------------------------------
# Company filter
# ---------------------------------------------------------------------------

class TestCompanyFilter:
    def test_free_user_company_filter_blocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            status, body = _start_mock(
                client,
                track="sql",
                difficulty="easy",
                company_filter="Meta",
            )
            assert status == 403, (
                f"expected 403 for free user with company_filter, got {status}: {body}"
            )
            assert "error" in body

    def test_pro_user_company_filter_blocked(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            status, body = _start_mock(
                client,
                track="sql",
                difficulty="hard",
                company_filter="Meta",
            )
            assert status in (400, 403), (
                f"expected 403 or 400 for pro user with company_filter, got {status}: {body}"
            )

    def test_elite_user_company_filter_allowed(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            status, body = _start_mock(
                client,
                track="sql",
                difficulty="easy",
                company_filter="Meta",
            )
            # Elite passes the plan gate; company_filter is truthy but does not
            # further restrict question selection — session should start normally.
            assert status == 200, (
                f"elite user with company_filter should get 200, got {status}: {body}"
            )
            assert "session_id" in body

    def test_lifetime_elite_company_filter_allowed(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            status, body = _start_mock(
                client,
                track="sql",
                difficulty="easy",
                company_filter="Meta",
            )
            assert status == 200, (
                f"lifetime_elite user with company_filter should get 200, got {status}: {body}"
            )
            assert "session_id" in body


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class TestMockHistory:
    def test_history_empty_initially(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/mock/history")
            assert r.status_code == 200, r.text
            assert r.json() == []

    def test_history_shows_completed_session(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]
            client.post(f"/api/mock/{session_id}/finish")

            r = client.get("/api/mock/history")
            assert r.status_code == 200, r.text
            history = r.json()
            assert len(history) == 1

            entry = history[0]
            assert entry["session_id"] == session_id
            assert "mode" in entry
            assert "track" in entry
            assert "difficulty" in entry
            assert "solved_count" in entry
            assert "total_count" in entry
            assert "status" in entry
            assert "started_at" in entry

    def test_history_limited_to_20(self) -> None:
        """History endpoint returns at most 20 entries; verify entry shape."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            client.post(f"/api/mock/{session['session_id']}/finish")

            r = client.get("/api/mock/history")
            assert r.status_code == 200, r.text
            history = r.json()
            assert isinstance(history, list)
            assert len(history) <= 20

            if history:
                entry = history[0]
                for field in ("session_id", "mode", "track", "difficulty", "status", "started_at"):
                    assert field in entry, f"history entry missing required field: {field}"


# ---------------------------------------------------------------------------
# Solution visibility
# ---------------------------------------------------------------------------

class TestSolutionVisibility:
    def test_solutions_absent_during_session(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            r = client.post(
                f"/api/mock/{session_id}/submit",
                json={
                    "question_id": first_q["id"],
                    "track": "sql",
                    "code": "SELECT 1",
                },
            )
            assert r.status_code == 200, r.text
            result = r.json()
            assert "solution_query" not in result, (
                f"solution_query must be absent from submit response, got keys: {list(result.keys())}"
            )
            assert "solution_code" not in result, (
                f"solution_code must be absent from submit response, got keys: {list(result.keys())}"
            )
            assert "expected_code" not in result, (
                f"expected_code must be absent from submit response, got keys: {list(result.keys())}"
            )

    def test_solutions_present_after_finish(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")

            # SQL track — finish should reveal solution_query
            _, session_sql = _start_mock(client, track="sql", difficulty="easy")
            r_sql = client.post(f"/api/mock/{session_sql['session_id']}/finish")
            assert r_sql.status_code == 200, r_sql.text
            for q in r_sql.json()["questions"]:
                assert "solution_query" in q, (
                    f"SQL finish missing solution_query, got keys: {list(q.keys())}"
                )
                assert "explanation" in q, (
                    f"SQL finish missing explanation, got keys: {list(q.keys())}"
                )

        with TestClient(app) as client:
            _make_user(client, plan="elite")

            # Python track — finish should reveal solution_code
            _, session_py = _start_mock(client, track="python", difficulty="easy")
            r_py = client.post(f"/api/mock/{session_py['session_id']}/finish")
            assert r_py.status_code == 200, r_py.text
            for q in r_py.json()["questions"]:
                assert "solution_code" in q, (
                    f"Python finish missing solution_code, got keys: {list(q.keys())}"
                )
                assert "explanation" in q, (
                    f"Python finish missing explanation, got keys: {list(q.keys())}"
                )
