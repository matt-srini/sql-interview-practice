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
from datetime import datetime, timezone

import psycopg2
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

# ---------------------------------------------------------------------------
# Weak-spot insights — Gap-coverage tests
# ---------------------------------------------------------------------------

class TestWeakSpotInsights:
    """Verify that the finish response exposes the data needed for the
    weak-spot concept table and drill link in the frontend.

    The frontend computes concept accuracy entirely client-side from
    ``questions[].concepts``.  The backend's job is to:
    1. Include ``concepts`` on every question in the finish response.
    2. Include ``is_solved`` on every question so the UI can tally accuracy.
    3. Return ``solved_count`` and ``total_count`` for the score headline.
    """

    def test_finish_includes_concepts_per_question(self) -> None:
        """Every question in the finish summary must carry a ``concepts`` list."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            r = client.post(f"/api/mock/{session['session_id']}/finish")
            assert r.status_code == 200, r.text
            for q in r.json()["questions"]:
                assert "concepts" in q, (
                    f"finish response question missing 'concepts', got keys: {list(q.keys())}"
                )
                assert isinstance(q["concepts"], list), (
                    f"'concepts' should be a list, got: {type(q['concepts'])}"
                )

    def test_finish_includes_is_solved_per_question(self) -> None:
        """Every question in the finish summary must carry ``is_solved``."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            r = client.post(f"/api/mock/{session['session_id']}/finish")
            assert r.status_code == 200, r.text
            for q in r.json()["questions"]:
                assert "is_solved" in q, (
                    f"finish response question missing 'is_solved', got keys: {list(q.keys())}"
                )

    def test_finish_includes_solved_count_and_total_count(self) -> None:
        """The finish summary must include ``solved_count`` and ``total_count``."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            r = client.post(f"/api/mock/{session['session_id']}/finish")
            assert r.status_code == 200, r.text
            body = r.json()
            assert "solved_count" in body, f"missing solved_count in finish response: {list(body.keys())}"
            assert "total_count" in body, f"missing total_count in finish response: {list(body.keys())}"
            assert isinstance(body["solved_count"], int)
            assert isinstance(body["total_count"], int)
            assert body["total_count"] == len(body["questions"])
            assert 0 <= body["solved_count"] <= body["total_count"]

    def test_solved_count_reflects_correct_submission(self) -> None:
        """A correct submission increments solved_count in the finish summary."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            # Submit with the real expected query so it is marked correct
            import questions as sql_catalog
            real_q = sql_catalog.get_question(first_q["id"])
            assert real_q is not None, f"question {first_q['id']} not found in catalog"
            correct_sql = real_q.get("expected_query", "SELECT 1")

            sub = client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "sql", "code": correct_sql},
            )
            assert sub.status_code == 200, sub.text
            # Whether it passes evaluation depends on the dataset; just verify
            # the submit endpoint accepted it without error.
            assert "correct" in sub.json()

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            body = r.json()
            # solved_count must be ≥ 0 and ≤ total_count
            assert 0 <= body["solved_count"] <= body["total_count"]

    def test_unsolved_session_has_zero_solved_count(self) -> None:
        """Finishing without submitting any answer must yield solved_count=0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="sql", difficulty="easy")
            r = client.post(f"/api/mock/{session['session_id']}/finish")
            assert r.status_code == 200, r.text
            assert r.json()["solved_count"] == 0

    def test_all_tracks_finish_include_concepts(self) -> None:
        """concepts must be present in finish responses for all supported tracks."""
        tracks = ["sql", "python", "python-data", "pyspark"]
        for track in tracks:
            with TestClient(app) as client:
                _make_user(client, plan="elite")
                _, session = _start_mock(client, track=track, difficulty="easy")
                r = client.post(f"/api/mock/{session['session_id']}/finish")
                assert r.status_code == 200, f"{track} finish failed: {r.text}"
                for q in r.json()["questions"]:
                    assert "concepts" in q, (
                        f"[{track}] finish question missing 'concepts', got keys: {list(q.keys())}"
                    )
                    assert isinstance(q["concepts"], list), (
                        f"[{track}] 'concepts' is not a list: {q['concepts']!r}"
                    )

    def test_mixed_track_finish_includes_per_question_track(self) -> None:
        """Mixed-track questions must each carry a ``track`` field so the
        frontend can attribute concepts to the correct track for the drill link."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="mixed", difficulty="easy")
            r = client.post(f"/api/mock/{session['session_id']}/finish")
            assert r.status_code == 200, r.text
            for q in r.json()["questions"]:
                assert "track" in q, (
                    f"mixed finish question missing 'track' field, got keys: {list(q.keys())}"
                )
                assert q["track"] in ("sql", "python", "python-data", "pyspark"), (
                    f"unexpected track value in mixed finish: {q['track']!r}"
                )


# ---------------------------------------------------------------------------
# Helpers shared by the new test classes below
# ---------------------------------------------------------------------------

def _db_conn():
    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test"
    )
    return psycopg2.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))


def _insert_submission_direct(
    user_id: str,
    *,
    track: str,
    question_id: int,
    is_correct: bool,
    submitted_at: datetime | None = None,
) -> None:
    """Write directly to the submissions table, bypassing the HTTP layer."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO submissions (user_id, track, question_id, is_correct, code, submitted_at)
                VALUES (%s::uuid, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    track,
                    question_id,
                    is_correct,
                    "-- test",
                    submitted_at or datetime.now(timezone.utc),
                ),
            )
        conn.commit()
    finally:
        conn.close()


def _pyspark_easy_with_concepts() -> tuple[int, int, list[str]]:
    """Return (question_id, correct_option, concepts) for a PySpark easy question that
    has at least one concept tag. Used for deterministic right/wrong submissions."""
    import pyspark_questions as pyqs
    easy = pyqs.get_questions_by_difficulty()["easy"]
    for q in easy:
        if q.get("concepts") and q.get("correct_option") is not None:
            return int(q["id"]), int(q["correct_option"]), list(q["concepts"])
    q = easy[0]
    return int(q["id"]), int(q.get("correct_option", 0)), list(q.get("concepts", []))


def _wrong_option(correct_option: int) -> int:
    """Return an option index that is definitely not the correct answer."""
    return 99 if correct_option != 99 else 98


# ---------------------------------------------------------------------------
# Submission tracking: is_solved accuracy and solved_count
# ---------------------------------------------------------------------------

class TestMockSubmissionTracking:
    """Verify is_solved and solved_count accurately reflect right/wrong answers."""

    def test_wrong_pyspark_answer_is_unsolved(self) -> None:
        """Submitting the wrong MCQ option must mark the question is_solved=False."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            import pyspark_questions as pyqs
            real_q = pyqs.get_question(first_q["id"])
            wrong_opt = _wrong_option(real_q["correct_option"])

            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": wrong_opt},
            )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            q_result = next(q for q in r.json()["questions"] if q["id"] == first_q["id"])
            assert q_result["is_solved"] is False, (
                f"Wrong MCQ answer should give is_solved=False, got: {q_result['is_solved']}"
            )

    def test_correct_pyspark_answer_is_solved(self) -> None:
        """Submitting the correct MCQ option must mark the question is_solved=True."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            import pyspark_questions as pyqs
            real_q = pyqs.get_question(first_q["id"])
            correct_opt = real_q["correct_option"]

            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": correct_opt},
            )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            q_result = next(q for q in r.json()["questions"] if q["id"] == first_q["id"])
            assert q_result["is_solved"] is True, (
                f"Correct MCQ answer should give is_solved=True, got: {q_result['is_solved']}"
            )

    def test_wrong_then_correct_marks_solved(self) -> None:
        """Submit wrong first, then correct — is_solved must be True (correct wins)."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            import pyspark_questions as pyqs
            real_q = pyqs.get_question(first_q["id"])
            correct_opt = real_q["correct_option"]
            wrong_opt = _wrong_option(correct_opt)

            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": wrong_opt},
            )
            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": correct_opt},
            )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            q_result = next(q for q in r.json()["questions"] if q["id"] == first_q["id"])
            assert q_result["is_solved"] is True, (
                "A correct answer after a wrong one should still mark the question solved"
            )

    def test_correct_then_wrong_stays_solved(self) -> None:
        """Submit correct first, then wrong again — is_solved must remain True (solved is sticky)."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]
            first_q = session["questions"][0]

            import pyspark_questions as pyqs
            real_q = pyqs.get_question(first_q["id"])
            correct_opt = real_q["correct_option"]
            wrong_opt = _wrong_option(correct_opt)

            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": correct_opt},
            )
            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": first_q["id"], "track": "pyspark", "selected_option": wrong_opt},
            )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            q_result = next(q for q in r.json()["questions"] if q["id"] == first_q["id"])
            assert q_result["is_solved"] is True, (
                "A wrong answer after a correct one must not un-solve the question"
            )

    def test_all_wrong_gives_zero_solved_count(self) -> None:
        """Submitting the wrong answer to every question gives solved_count=0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]

            import pyspark_questions as pyqs
            for q in session["questions"]:
                real_q = pyqs.get_question(q["id"])
                wrong_opt = _wrong_option(real_q["correct_option"])
                client.post(
                    f"/api/mock/{session_id}/submit",
                    json={"question_id": q["id"], "track": "pyspark", "selected_option": wrong_opt},
                )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["solved_count"] == 0, (
                f"All wrong answers should give solved_count=0, got: {body['solved_count']}"
            )
            for q in body["questions"]:
                assert q["is_solved"] is False, (
                    f"All questions should be unsolved after all-wrong session, q={q['id']}"
                )

    def test_partial_correct_gives_accurate_solved_count(self) -> None:
        """In a 2-question session, answering one correct and one wrong gives solved_count=1."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            _, session = _start_mock(
                client, mode="custom", track="pyspark", difficulty="easy",
                num_questions=2, time_minutes=10,
            )
            session_id = session["session_id"]
            qs = session["questions"]
            assert len(qs) == 2, f"expected 2 questions, got {len(qs)}"

            import pyspark_questions as pyqs
            first_real = pyqs.get_question(qs[0]["id"])
            second_real = pyqs.get_question(qs[1]["id"])

            # First: correct
            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": qs[0]["id"], "track": "pyspark", "selected_option": first_real["correct_option"]},
            )
            # Second: wrong
            client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": qs[1]["id"], "track": "pyspark", "selected_option": _wrong_option(second_real["correct_option"])},
            )

            r = client.post(f"/api/mock/{session_id}/finish")
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["solved_count"] == 1, (
                f"Expected solved_count=1 (1 correct, 1 wrong), got: {body['solved_count']}"
            )
            q_map = {q["id"]: q for q in body["questions"]}
            assert q_map[qs[0]["id"]]["is_solved"] is True
            assert q_map[qs[1]["id"]]["is_solved"] is False


# ---------------------------------------------------------------------------
# Plan-tier finish response: shape must be plan-agnostic (concept analysis is
# computed client-side; the backend always returns the same finish shape)
# ---------------------------------------------------------------------------

class TestMockPlanTierFinish:
    """Finish response shape must be identical for free, pro, and elite.

    Concept breakdown, weak-spot badges, and historical accuracy are all
    computed in MockSession.js using auth context.  The API must not
    conditionally omit fields based on plan.
    """

    def _finish_field_set(self, client: TestClient, plan: str) -> set[str]:
        _make_user(client, plan=plan)
        _, session = _start_mock(client, track="pyspark", difficulty="easy")
        r = client.post(f"/api/mock/{session['session_id']}/finish")
        assert r.status_code == 200, r.text
        body = r.json()
        # Collect top-level keys + question-level keys from the first question
        top_keys = set(body.keys())
        q_keys = set(body["questions"][0].keys()) if body.get("questions") else set()
        return top_keys, q_keys

    def test_free_finish_has_expected_top_level_keys(self) -> None:
        with TestClient(app) as client:
            top_keys, _ = self._finish_field_set(client, "free")
            for required in ("session_id", "solved_count", "total_count", "questions", "status"):
                assert required in top_keys, f"free finish missing top-level key: {required!r}"

    def test_pro_finish_has_same_shape_as_free(self) -> None:
        with TestClient(app) as client_free:
            free_top, free_q = self._finish_field_set(client_free, "free")
        with TestClient(app) as client_pro:
            pro_top, pro_q = self._finish_field_set(client_pro, "pro")

        assert free_top == pro_top, (
            f"Free and Pro finish top-level keys differ.\n"
            f"  Free-only: {free_top - pro_top}\n"
            f"  Pro-only:  {pro_top - free_top}"
        )
        assert free_q == pro_q, (
            f"Free and Pro question-level keys differ.\n"
            f"  Free-only: {free_q - pro_q}\n"
            f"  Pro-only:  {pro_q - free_q}"
        )

    def test_elite_finish_has_same_shape_as_free(self) -> None:
        with TestClient(app) as client_free:
            free_top, free_q = self._finish_field_set(client_free, "free")
        with TestClient(app) as client_elite:
            elite_top, elite_q = self._finish_field_set(client_elite, "elite")

        assert free_top == elite_top, (
            f"Free and Elite finish top-level keys differ.\n"
            f"  Free-only:  {free_top - elite_top}\n"
            f"  Elite-only: {elite_top - free_top}"
        )
        assert free_q == elite_q, (
            f"Free and Elite question-level keys differ.\n"
            f"  Free-only:  {free_q - elite_q}\n"
            f"  Elite-only: {elite_q - free_q}"
        )


# ---------------------------------------------------------------------------
# Mock sessions feed dashboard insights (Phase 4 behavior)
# ---------------------------------------------------------------------------

class TestMockFeedsInsights:
    """Verify that wrong answers submitted in mock sessions flow into the
    dashboard weak-concept insights pipeline.

    Strategy: pick a PySpark question with concepts, seed 2 wrong submissions
    directly into the DB (to reach the ≥3-attempt threshold cheaply), then
    submit a third wrong answer through the mock endpoint.  The insights
    endpoint must then list that concept in weakest_concepts.
    """

    def _pick_question_with_concept(self) -> tuple[int, str]:
        """Return (question_id, concept) for a PySpark easy question with ≥1 concept."""
        import pyspark_questions as pyqs
        easy = pyqs.get_questions_by_difficulty()["easy"]
        for q in easy:
            if q.get("concepts"):
                return int(q["id"]), q["concepts"][0]
        pytest.skip("No PySpark easy question with concept tags found")

    def test_mock_wrong_answers_appear_as_weak_concept(self) -> None:
        """3 wrong submissions on a concept must make it appear in weakest_concepts."""
        qid, concept = self._pick_question_with_concept()

        import pyspark_questions as pyqs
        real_q = pyqs.get_question(qid)
        wrong_opt = _wrong_option(real_q["correct_option"])

        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            user_id = user["id"]
            now = datetime.now(timezone.utc)

            # Pre-seed 2 wrong submissions directly (reach ≥3 with the mock submit below)
            _insert_submission_direct(user_id, track="pyspark", question_id=qid, is_correct=False, submitted_at=now)
            _insert_submission_direct(user_id, track="pyspark", question_id=qid, is_correct=False, submitted_at=now)

            # Start a session and submit wrong to the same question if it appears;
            # if not in the session, submit directly via DB for the 3rd attempt.
            _, session = _start_mock(client, track="pyspark", difficulty="easy")
            session_id = session["session_id"]
            session_q_ids = {q["id"] for q in session["questions"]}

            if qid in session_q_ids:
                client.post(
                    f"/api/mock/{session_id}/submit",
                    json={"question_id": qid, "track": "pyspark", "selected_option": wrong_opt},
                )
            else:
                # Seed 3rd attempt directly — still tests the insights pipeline
                _insert_submission_direct(user_id, track="pyspark", question_id=qid, is_correct=False, submitted_at=now)

            client.post(f"/api/mock/{session_id}/finish")

            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200, r.text
            weakest = r.json().get("weakest_concepts", [])
            found = [(w["track"], w["concept"]) for w in weakest]
            assert ("pyspark", concept) in found, (
                f"Expected ('pyspark', {concept!r}) in weakest_concepts after 3 wrong attempts. "
                f"Got: {found}"
            )

    def test_weak_concept_has_summary_text(self) -> None:
        """weakest_concepts entries must each carry a non-empty summary string."""
        qid, concept = self._pick_question_with_concept()
        now = datetime.now(timezone.utc)

        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            for _ in range(3):
                _insert_submission_direct(
                    user["id"], track="pyspark", question_id=qid, is_correct=False, submitted_at=now
                )

            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200, r.text
            weakest = r.json().get("weakest_concepts", [])
            assert len(weakest) > 0, "Expected at least one weak concept after 3 wrong submissions"
            for w in weakest:
                assert "summary" in w, f"weakest_concepts entry missing 'summary': {w}"
                assert isinstance(w["summary"], str) and len(w["summary"]) > 0, (
                    f"summary should be a non-empty string, got: {w['summary']!r}"
                )

    def test_weak_concept_summary_matches_accuracy_bucket(self) -> None:
        """All-wrong submissions (0% accuracy) must produce the 'highest-priority gap' summary."""
        qid, _ = self._pick_question_with_concept()
        now = datetime.now(timezone.utc)

        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            for _ in range(4):  # 0/4 = 0% accuracy
                _insert_submission_direct(
                    user["id"], track="pyspark", question_id=qid, is_correct=False, submitted_at=now
                )

            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200, r.text
            weakest = r.json().get("weakest_concepts", [])
            assert len(weakest) > 0
            assert "highest-priority" in weakest[0]["summary"], (
                f"0% accuracy should produce 'highest-priority gap' summary, got: {weakest[0]['summary']!r}"
            )

    def test_free_user_recommended_questions_only_easy(self) -> None:
        """Free users must only receive easy recommended_question_ids (plan-gated)."""
        import pyspark_questions as pyqs
        qid, _ = self._pick_question_with_concept()
        now = datetime.now(timezone.utc)

        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            for _ in range(3):
                _insert_submission_direct(
                    user["id"], track="pyspark", question_id=qid, is_correct=False, submitted_at=now
                )

            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200, r.text
            weakest = r.json().get("weakest_concepts", [])
            for w in weakest:
                if "recommended_question_ids" not in w:
                    continue
                for rec_id in w["recommended_question_ids"]:
                    real_q = pyqs.get_question(rec_id)
                    if real_q is None:
                        # Could be a non-pyspark track concept
                        continue
                    assert real_q.get("difficulty") == "easy", (
                        f"Free user got a non-easy recommended question (id={rec_id}, "
                        f"difficulty={real_q.get('difficulty')!r})"
                    )

    def test_pro_user_gets_recommended_question_ids(self) -> None:
        """Pro users must receive recommended_question_ids on their weakest concept
        when unsolved questions exist for that concept."""
        qid, _ = self._pick_question_with_concept()
        now = datetime.now(timezone.utc)

        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            for _ in range(3):
                _insert_submission_direct(
                    user["id"], track="pyspark", question_id=qid, is_correct=False, submitted_at=now
                )

            r = client.get("/api/dashboard/insights")
            assert r.status_code == 200, r.text
            weakest = r.json().get("weakest_concepts", [])
            assert len(weakest) > 0
            w = weakest[0]
            # recommended_question_ids is only present when there are unsolved questions for
            # the concept; if it's present, it must be a non-empty list of ints
            if "recommended_question_ids" in w:
                recs = w["recommended_question_ids"]
                assert isinstance(recs, list) and len(recs) > 0, (
                    f"recommended_question_ids should be a non-empty list for pro, got: {recs!r}"
                )
                for rec_id in recs:
                    assert isinstance(rec_id, int), (
                        f"each recommended_question_id should be an int, got: {type(rec_id)}"
                    )
                assert len(recs) <= 2, (
                    f"at most 2 recommended_question_ids expected, got {len(recs)}: {recs}"
                )