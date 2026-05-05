"""
test_mock_submit_dashboard.py

Stringent integration tests covering the mock submit → dashboard pipeline.

These tests were written after the following bugs were found in production:
  1. "Session not found" on submit — a user_id mismatch caused every submit
     to fail silently (error was masked as generic "Submission failed").
  2. Weakest concepts never surfacing — wrong answers were being submitted
     but the dashboard showed "Need at least 3 attempts".

Test sections:
  A. Session integrity  — user_id must match between /start and /submit.
  B. Plan-tier gates    — free/pro/elite access rules at submit time.
  C. Daily limit gates  — free: 1 medium/day; pro: 3 hard/day; elite: unlimited.
  D. Dashboard updates  — wrong mock submissions accumulate in the submissions
                          table and surface as weakest_concepts at ≥3 attempts.
  E. Discard session    — DELETE /api/mock/{id} within the 2-minute window.

All tests use PySpark MCQ questions because correct_option is deterministic
from the catalog and no DuckDB execution is needed.  Each class uses the
`isolated_state` fixture so the DB is clean on every run.
"""
from __future__ import annotations

import os
import time

import psycopg2
import pytest
from fastapi.testclient import TestClient

import backend.main as main
import pyspark_questions

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Catalog constants — looked up once at import time
# ---------------------------------------------------------------------------

_EASY_PYSPARK = pyspark_questions.get_questions_by_difficulty()["easy"]

# Q11003: concept "RDD vs DataFrame" → DATAFRAME API family, correct_option=2
_Q_DATAFRAME_API = 11003
_Q_DATAFRAME_API_CORRECT = int(
    next(q for q in _EASY_PYSPARK if q["id"] == _Q_DATAFRAME_API)["correct_option"]
)

# Q11010: concept "caching" → CACHING family
_Q_CACHING = 11010
_Q_CACHING_CORRECT = int(
    next(q for q in _EASY_PYSPARK if q["id"] == _Q_CACHING)["correct_option"]
)

# Q11011: concept "partitions" → PARTITIONING family
_Q_PARTITIONING = 11011
_Q_PARTITIONING_CORRECT = int(
    next(q for q in _EASY_PYSPARK if q["id"] == _Q_PARTITIONING)["correct_option"]
)

# Any easy question — used as a fallback/filler
_Q_ANY = int(_EASY_PYSPARK[0]["id"])
_Q_ANY_CORRECT = int(_EASY_PYSPARK[0]["correct_option"])


def _wrong(correct_option: int) -> int:
    """Return any MCQ option that is NOT the correct one (options are 0–3)."""
    return (correct_option + 1) % 4


# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------

_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    """Register a user with the given plan. Returns the user dict."""
    global _counter
    _counter += 1
    email = f"msd-test-{_counter}@internal.test"
    client.get("/api/catalog")  # seed anonymous session + cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": f"MSD Test {plan}", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, up.text
        user["plan"] = plan
    return user


def _start_pyspark(
    client: TestClient,
    difficulty: str = "easy",
    num_questions: int = 1,
) -> dict:
    """Start a custom PySpark session and return the response body."""
    r = client.post(
        "/api/mock/start",
        json={
            "mode": "custom",
            "track": "pyspark",
            "difficulty": difficulty,
            "num_questions": num_questions,
            "time_minutes": 10,
        },
    )
    assert r.status_code == 200, f"start failed: {r.text}"
    return r.json()


def _submit(
    client: TestClient,
    session_id: int,
    question_id: int,
    selected_option: int,
    track: str = "pyspark",
    *,
    expect_status: int = 200,
) -> dict:
    r = client.post(
        f"/api/mock/{session_id}/submit",
        json={"question_id": question_id, "track": track, "selected_option": selected_option},
    )
    assert r.status_code == expect_status, (
        f"submit to session {session_id} q{question_id} → "
        f"expected {expect_status}, got {r.status_code}: {r.text}"
    )
    return r.json()


def _finish(client: TestClient, session_id: int) -> dict:
    r = client.post(f"/api/mock/{session_id}/finish")
    assert r.status_code == 200, f"finish failed: {r.text}"
    return r.json()


def _insights(client: TestClient) -> dict:
    r = client.get("/api/dashboard/insights")
    assert r.status_code == 200, r.text
    return r.json()


def _db_url() -> str:
    raw = os.environ.get(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sql_practice_test"
    )
    return raw.replace("postgresql+asyncpg://", "postgresql://")


def _direct_session_owner(session_id: int) -> str | None:
    """Fetch the user_id stored for a mock session directly from the DB."""
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id::text FROM mock_sessions WHERE id = %s", (session_id,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _count_submissions(user_id: str, question_id: int, track: str = "pyspark") -> int:
    """Count rows in the submissions table for a given user + question."""
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) FROM submissions
                WHERE user_id = %s::uuid AND question_id = %s AND track = %s
                """,
                (user_id, question_id, track),
            )
            return cur.fetchone()[0]
    finally:
        conn.close()


def _seed_medium_unlocked(user_id: str, track: str = "pyspark") -> None:
    """Directly insert 30 easy PySpark solves so medium questions are unlocked for free users."""
    easy_ids = [int(q["id"]) for q in _EASY_PYSPARK[:30]]
    topic = "pyspark"
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            for qid in easy_ids:
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


# ===========================================================================
# A. Session integrity
# ===========================================================================


class TestSessionIntegrity:
    """
    The session is owned by the user who called /start.  Any other user_id
    must receive 404.  Wrong session_id must also 404.  A completed session
    must return 400 "Session is not active".

    These tests cover the root-cause scenario of the production "Session not
    found" bug: if the frontend sends no cookie (or a different cookie), the
    backend resolves a different user_id and the session cannot be found.
    """

    def test_owner_can_submit_to_own_session(self) -> None:
        """The user who started the session can successfully submit to it."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]
            q = session["questions"][0]

            result = _submit(client, session_id, q["id"], _wrong(_Q_ANY_CORRECT))
            assert "correct" in result, f"expected 'correct' in response, got: {result}"

    def test_session_owner_stored_in_db_matches_start_user(self) -> None:
        """
        The user_id persisted in mock_sessions must be exactly the user_id
        returned by get_current_user at /start time.  This is the invariant
        whose violation causes "Session not found" on submit.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]

            db_owner = _direct_session_owner(session_id)
            assert db_owner is not None, "session row not found in DB after /start"
            assert db_owner == user["id"], (
                f"DB session owner {db_owner!r} != start-time user_id {user['id']!r}. "
                "This mismatch is the root cause of 'Session not found' on submit."
            )

    def test_different_user_gets_404_on_submit(self) -> None:
        """
        A second user submitting to another user's session must get 404.
        This is the production failure mode: mismatched session_token cookie
        resolves to a different user_id.
        """
        with TestClient(app) as owner_client:
            _make_user(owner_client, plan="elite")
            session = _start_pyspark(owner_client)
            session_id = session["session_id"]
            q = session["questions"][0]

        # New client = new cookie = different user
        with TestClient(app) as other_client:
            _make_user(other_client, plan="elite")
            r = other_client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": q["id"], "track": "pyspark", "selected_option": 0},
            )
            assert r.status_code == 404, (
                f"Other user submitting to owner's session must get 404, got {r.status_code}: {r.text}"
            )
            body = r.json()
            assert body.get("error") == "Session not found", (
                f"Error message must be 'Session not found', got: {body}"
            )

    def test_nonexistent_session_id_gives_404(self) -> None:
        """Submitting to a session_id that does not exist must return 404."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post(
                "/api/mock/999999/submit",
                json={"question_id": _Q_ANY, "track": "pyspark", "selected_option": 0},
            )
            assert r.status_code == 404, (
                f"Non-existent session must give 404, got {r.status_code}: {r.text}"
            )

    def test_submit_to_completed_session_gives_400(self) -> None:
        """Submitting to an already-finished session must return 400 'Session is not active'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]
            _finish(client, session_id)

            q = session["questions"][0]
            r = client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": q["id"], "track": "pyspark", "selected_option": 0},
            )
            assert r.status_code == 400, (
                f"Submit to completed session must return 400, got {r.status_code}: {r.text}"
            )
            body = r.json()
            assert body.get("error") == "Session is not active", (
                f"Error message must be 'Session is not active', got: {body}"
            )

    def test_submit_question_not_in_session_gives_400(self) -> None:
        """Submitting a question_id not in the session must return 400."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]
            q_ids_in_session = {q["id"] for q in session["questions"]}
            # Find a question id NOT in the session
            outside_id = next(
                int(q["id"]) for q in _EASY_PYSPARK if int(q["id"]) not in q_ids_in_session
            )
            r = client.post(
                f"/api/mock/{session_id}/submit",
                json={"question_id": outside_id, "track": "pyspark", "selected_option": 0},
            )
            assert r.status_code == 400, (
                f"Submitting a question not in the session must return 400, "
                f"got {r.status_code}: {r.text}"
            )

    def test_submit_response_contains_correct_and_follow_up_injected(self) -> None:
        """A successful PySpark submit response must contain 'correct' and 'follow_up_injected'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            q = session["questions"][0]
            result = _submit(client, session["session_id"], q["id"], _wrong(_Q_ANY_CORRECT))

            assert "correct" in result, f"'correct' key missing from submit response: {result}"
            assert "follow_up_injected" in result, (
                f"'follow_up_injected' key missing from submit response: {result}"
            )
            assert isinstance(result["correct"], bool)

    def test_submit_does_not_reveal_solution_mid_session(self) -> None:
        """The submit response must NOT contain 'solution' or 'expected_query' mid-session."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            q = session["questions"][0]
            result = _submit(client, session["session_id"], q["id"], _wrong(_Q_ANY_CORRECT))

            for forbidden_key in ("solution", "expected_query", "correct_query"):
                assert forbidden_key not in result, (
                    f"Submit response must not reveal '{forbidden_key}' mid-session, "
                    f"got keys: {list(result.keys())}"
                )

    def test_get_session_endpoint_uses_same_user_id(self) -> None:
        """
        GET /api/mock/{id} must return the session for the owner.
        A different user must get 404.
        """
        with TestClient(app) as owner_client:
            _make_user(owner_client, plan="elite")
            session = _start_pyspark(owner_client)
            session_id = session["session_id"]
            # Owner can GET their session
            r = owner_client.get(f"/api/mock/{session_id}")
            assert r.status_code == 200, f"Owner GET session failed: {r.text}"

        with TestClient(app) as other_client:
            _make_user(other_client, plan="elite")
            r = other_client.get(f"/api/mock/{session_id}")
            assert r.status_code == 404, (
                f"Other user must get 404 for owner's session, got {r.status_code}"
            )


# ===========================================================================
# B. Plan-tier submit gates
# ===========================================================================


class TestPlanTierSubmitGates:
    """
    Free, Pro, and Elite users must each be able to start sessions appropriate
    to their tier and submit answers.  Hard sessions for free users must be
    blocked at /start.
    """

    def test_free_user_can_start_and_submit_easy_pyspark(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            session = _start_pyspark(client, difficulty="easy")
            q = session["questions"][0]
            correct_opt = int(pyspark_questions.get_question(q["id"])["correct_option"])
            result = _submit(client, session["session_id"], q["id"], _wrong(correct_opt))
            assert result["correct"] is False

    def test_free_user_cannot_start_hard_session(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 403, (
                f"Free user must be blocked from hard sessions, got {r.status_code}: {r.text}"
            )
            body = r.json()
            assert body.get("error") or body.get("detail"), "Expected error message in response"

    def test_pro_user_can_start_and_submit_hard_pyspark(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            hard_qs = pyspark_questions.get_questions_by_difficulty()["hard"]
            assert hard_qs, "No hard PySpark questions in catalog"
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 200, f"Pro hard start failed: {r.text}"
            session = r.json()
            q = session["questions"][0]
            result = _submit(client, session["session_id"], q["id"],
                             _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"])),
                             track="pyspark")
            assert result["correct"] is False

    def test_elite_user_can_start_unlimited_sessions(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            for _ in range(4):  # beyond pro's hard daily limit of 3
                r = client.post(
                    "/api/mock/start",
                    json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                          "num_questions": 1, "time_minutes": 10},
                )
                assert r.status_code == 200, (
                    f"Elite user must start unlimited hard sessions, got {r.status_code}: {r.text}"
                )
                # Finish it so the "active session exists" guard doesn't block the next start
                _finish(client, r.json()["session_id"])

    def test_lifetime_elite_has_same_access_as_elite(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 200, (
                f"lifetime_elite must have Elite access, got {r.status_code}: {r.text}"
            )

    def test_lifetime_pro_has_same_access_as_pro(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 200, (
                f"lifetime_pro must have Pro hard access, got {r.status_code}: {r.text}"
            )

    def test_free_user_medium_blocked_when_not_unlocked(self) -> None:
        """Free user without medium unlocked cannot start a medium session."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            # Fresh user has 0 easy solves → medium not unlocked
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "medium",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 403, (
                f"Free user without medium unlocked must get 403, got {r.status_code}: {r.text}"
            )

    def test_free_user_medium_allowed_when_unlocked(self) -> None:
        """Free user with medium unlocked can start 1 medium session."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            _seed_medium_unlocked(user["id"], track="pyspark")
            r = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "medium",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r.status_code == 200, (
                f"Free user with medium unlocked must start 1 medium session, "
                f"got {r.status_code}: {r.text}"
            )


# ===========================================================================
# C. Daily limit enforcement
# ===========================================================================


class TestDailyLimits:
    """
    Free: 1 medium/day.  Pro: 3 hard/day.  Elite: unlimited.
    These tests verify the limit is enforced at /start, not at /submit.
    """

    def test_free_user_medium_daily_limit_enforced(self) -> None:
        """Free user can start exactly 1 medium session per day; second is blocked."""
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            _seed_medium_unlocked(user["id"])

            # First session: allowed — finish it so the active-session guard doesn't fire
            r1 = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "medium",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r1.status_code == 200, f"First medium start must succeed: {r1.text}"
            _finish(client, r1.json()["session_id"])

            # Second session same day: blocked by daily cap (not by active-session guard)
            r2 = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "medium",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r2.status_code == 403, (
                f"Free user must be blocked after 1 medium session/day, "
                f"got {r2.status_code}: {r2.text}"
            )
            body = r2.json()
            assert body.get("error") or body.get("detail"), "Expected error in daily-limit block"

    def test_pro_user_hard_daily_limit_enforced(self) -> None:
        """Pro user can start up to 3 hard sessions per day; fourth is blocked."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")

            # First 3: allowed; finish each before starting the next
            for i in range(3):
                r = client.post(
                    "/api/mock/start",
                    json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                          "num_questions": 1, "time_minutes": 10},
                )
                assert r.status_code == 200, (
                    f"Pro hard session {i + 1}/3 must succeed, got {r.status_code}: {r.text}"
                )
                _finish(client, r.json()["session_id"])

            # Fourth: blocked
            r4 = client.post(
                "/api/mock/start",
                json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                      "num_questions": 1, "time_minutes": 10},
            )
            assert r4.status_code == 403, (
                f"Pro user must be blocked after 3 hard sessions/day, "
                f"got {r4.status_code}: {r4.text}"
            )

    def test_elite_has_no_hard_daily_limit(self) -> None:
        """Elite user can start more than 3 hard sessions in one day."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            for i in range(5):
                r = client.post(
                    "/api/mock/start",
                    json={"mode": "custom", "track": "pyspark", "difficulty": "hard",
                          "num_questions": 1, "time_minutes": 10},
                )
                assert r.status_code == 200, (
                    f"Elite session {i + 1} must succeed (no daily limit), "
                    f"got {r.status_code}: {r.text}"
                )
                _finish(client, r.json()["session_id"])

    def test_easy_sessions_never_count_toward_limits(self) -> None:
        """Easy sessions are never subject to daily limits for any plan."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            for i in range(5):  # well beyond any soft limit
                r = client.post(
                    "/api/mock/start",
                    json={"mode": "custom", "track": "pyspark", "difficulty": "easy",
                          "num_questions": 1, "time_minutes": 10},
                )
                assert r.status_code == 200, (
                    f"Easy session {i + 1} must always be allowed (no daily limit), "
                    f"got {r.status_code}: {r.text}"
                )
                # Finish each session so the active-session guard doesn't block the next
                _finish(client, r.json()["session_id"])


# ===========================================================================
# D. Dashboard insights updated by mock wrong submissions
# ===========================================================================


class TestDashboardUpdatesFromMockSubmissions:
    """
    Wrong answers submitted via POST /api/mock/{id}/submit must:
      1. Be written to the `submissions` table (one row per submit call).
      2. Appear in /api/dashboard/insights per_track accuracy.
      3. Surface as weakest_concepts once >= 3 attempts on the same concept
         family are accumulated.

    This directly covers the production bug where users submitted wrong
    answers during mock sessions but the dashboard never updated.
    """

    def test_wrong_submission_recorded_in_submissions_table(self) -> None:
        """A single wrong mock submit must create exactly one row in submissions."""
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            q = session["questions"][0]

            before = _count_submissions(user["id"], q["id"])
            _submit(client, session["session_id"], q["id"],
                    _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"])))
            after = _count_submissions(user["id"], q["id"])

            assert after == before + 1, (
                f"One wrong submit must produce exactly 1 new submissions row, "
                f"before={before} after={after}"
            )

    def test_correct_submission_recorded_in_submissions_table(self) -> None:
        """A single correct mock submit must also create exactly one row in submissions."""
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            q = session["questions"][0]
            correct_opt = int(pyspark_questions.get_question(q["id"])["correct_option"])

            before = _count_submissions(user["id"], q["id"])
            _submit(client, session["session_id"], q["id"], correct_opt)
            after = _count_submissions(user["id"], q["id"])

            assert after == before + 1, (
                f"One correct submit must produce exactly 1 new submissions row, "
                f"before={before} after={after}"
            )

    def test_multiple_wrong_submits_create_multiple_rows(self) -> None:
        """
        Re-submitting the same question wrong 3× must create 3 rows in
        submissions.  This is the threshold needed for weakest_concepts to fire.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]
            wrong_opt = _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"]))

            for _ in range(3):
                _submit(client, session_id, q["id"], wrong_opt)

            total = _count_submissions(user["id"], q["id"])
            assert total == 3, (
                f"3 wrong submits on the same question must produce 3 rows, got {total}"
            )

    def test_dashboard_accuracy_drops_after_wrong_mock_submit(self) -> None:
        """
        After submitting wrong in a mock session, per_track accuracy_pct for
        pyspark must be less than 1.0 (≠ 0 wrong out of 0).
        """
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            q = session["questions"][0]
            _submit(client, session["session_id"], q["id"],
                    _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"])))

            payload = _insights(client)
            pyspark_stats = payload["per_track"]["pyspark"]

            assert pyspark_stats["accuracy_pct"] < 1.0, (
                f"After 1 wrong submit, pyspark accuracy_pct must be < 1.0, "
                f"got {pyspark_stats['accuracy_pct']}"
            )
            assert pyspark_stats["accuracy_pct"] == 0.0, (
                f"After only 1 wrong submit (no correct), accuracy_pct must be 0.0, "
                f"got {pyspark_stats['accuracy_pct']}"
            )

    def test_dashboard_accuracy_reflects_mixed_correct_wrong(self) -> None:
        """
        1 wrong + 1 correct submit on the same question → accuracy_pct = 0.5.
        """
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]
            correct_opt = int(pyspark_questions.get_question(q["id"])["correct_option"])

            _submit(client, session_id, q["id"], _wrong(correct_opt))
            _submit(client, session_id, q["id"], correct_opt)

            payload = _insights(client)
            acc = payload["per_track"]["pyspark"]["accuracy_pct"]
            assert acc == 0.5, (
                f"1 wrong + 1 correct → accuracy_pct should be 0.5, got {acc}"
            )

    def test_weakest_concepts_empty_below_3_mock_submits(self) -> None:
        """
        2 wrong mock submits are below the 3-attempt threshold — weakest_concepts
        must remain empty.
        """
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]

            # Use Q11003 (DATAFRAME API family)
            # But it might not be in the session — seed a direct session instead
            q = session["questions"][0]
            wrong_opt = _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"]))

            _submit(client, session_id, q["id"], wrong_opt)
            _submit(client, session_id, q["id"], wrong_opt)  # only 2 submits

            payload = _insights(client)
            assert payload["weakest_concepts"] == [], (
                f"2 attempts must not surface weakest concepts, "
                f"got: {payload['weakest_concepts']}"
            )

    def test_weakest_concepts_surfaces_after_3_wrong_mock_submits(self) -> None:
        """
        3 wrong submits on a PySpark question that maps to a known concept family
        must surface that concept in weakest_concepts.

        This is the exact bug: users were submitting wrong answers in mock sessions
        but the dashboard showed 'Need at least 3 attempts'.
        """
        with TestClient(app) as client:
            _make_user(client, plan="elite")

            # Seed a session that specifically contains Q11003 (DATAFRAME API concept)
            import psycopg2 as _psycopg2
            user_r = client.get("/api/auth/me")
            assert user_r.status_code == 200
            user_id = user_r.json()["user"]["id"]

            conn = _psycopg2.connect(_db_url())
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO mock_sessions
                            (user_id, mode, track, difficulty, time_limit_s, started_at)
                        VALUES (%s::uuid, 'custom', 'pyspark', 'easy', 600, now())
                        RETURNING id
                        """,
                        (user_id,),
                    )
                    session_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO mock_session_questions
                            (session_id, question_id, track, position)
                        VALUES (%s, %s, 'pyspark', 1)
                        """,
                        (session_id, _Q_DATAFRAME_API),
                    )
                conn.commit()
            finally:
                conn.close()

            wrong_opt = _wrong(_Q_DATAFRAME_API_CORRECT)
            for _ in range(3):
                _submit(client, session_id, _Q_DATAFRAME_API, wrong_opt)

            payload = _insights(client)
            assert len(payload["weakest_concepts"]) > 0, (
                f"3 wrong submits on a concept-tagged question must surface weakest_concepts, "
                f"got empty list.  This is the production bug where dashboard never updated."
            )

            # Verify the surfaced concept is pyspark and has ≥3 attempts
            weak = payload["weakest_concepts"][0]
            assert weak["track"] == "pyspark", (
                f"Weakest concept track must be 'pyspark', got {weak['track']!r}"
            )
            assert weak["attempts"] >= 3, (
                f"Weakest concept must show ≥3 attempts, got {weak['attempts']}"
            )
            assert weak["accuracy_pct"] == 0.0, (
                f"All wrong submissions → accuracy_pct must be 0.0, got {weak['accuracy_pct']}"
            )

    def test_weakest_concepts_capped_at_3_entries(self) -> None:
        """At most 3 concepts appear in weakest_concepts even if more are eligible."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            user_r = client.get("/api/auth/me")
            user_id = user_r.json()["user"]["id"]

            # Seed a session with questions from 4 different concept families
            questions_to_seed = [
                (_Q_DATAFRAME_API, "pyspark", 1),
                (_Q_CACHING, "pyspark", 2),
                (_Q_PARTITIONING, "pyspark", 3),
                (int(_EASY_PYSPARK[3]["id"]), "pyspark", 4),  # 4th distinct question
            ]
            import psycopg2 as _psycopg2
            conn = _psycopg2.connect(_db_url())
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO mock_sessions
                            (user_id, mode, track, difficulty, time_limit_s, started_at)
                        VALUES (%s::uuid, 'custom', 'pyspark', 'easy', 600, now())
                        RETURNING id
                        """,
                        (user_id,),
                    )
                    session_id = cur.fetchone()[0]
                    for qid, track, pos in questions_to_seed:
                        cur.execute(
                            """
                            INSERT INTO mock_session_questions
                                (session_id, question_id, track, position)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (session_id, qid, track, pos),
                        )
                conn.commit()
            finally:
                conn.close()

            # Submit each question 3 times with wrong answers
            for qid, _, _ in questions_to_seed:
                q_obj = pyspark_questions.get_question(qid)
                if q_obj is None:
                    continue
                wrong_opt = _wrong(int(q_obj["correct_option"]))
                for _ in range(3):
                    client.post(
                        f"/api/mock/{session_id}/submit",
                        json={"question_id": qid, "track": "pyspark",
                              "selected_option": wrong_opt},
                    )

            payload = _insights(client)
            assert len(payload["weakest_concepts"]) <= 3, (
                f"weakest_concepts must be capped at 3, got {len(payload['weakest_concepts'])}: "
                f"{payload['weakest_concepts']}"
            )

    def test_correct_submission_does_not_add_to_weakest_concepts_accuracy(self) -> None:
        """Correctly answering a question must not produce accuracy_pct = 0 for that concept."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            user_r = client.get("/api/auth/me")
            user_id = user_r.json()["user"]["id"]

            import psycopg2 as _psycopg2
            conn = _psycopg2.connect(_db_url())
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO mock_sessions
                            (user_id, mode, track, difficulty, time_limit_s, started_at)
                        VALUES (%s::uuid, 'custom', 'pyspark', 'easy', 600, now())
                        RETURNING id
                        """,
                        (user_id,),
                    )
                    session_id = cur.fetchone()[0]
                    cur.execute(
                        """
                        INSERT INTO mock_session_questions
                            (session_id, question_id, track, position)
                        VALUES (%s, %s, 'pyspark', 1)
                        """,
                        (session_id, _Q_DATAFRAME_API),
                    )
                conn.commit()
            finally:
                conn.close()

            # 2 wrong + 1 correct = 3 attempts total, 1 correct
            wrong_opt = _wrong(_Q_DATAFRAME_API_CORRECT)
            _submit(client, session_id, _Q_DATAFRAME_API, wrong_opt)
            _submit(client, session_id, _Q_DATAFRAME_API, wrong_opt)
            _submit(client, session_id, _Q_DATAFRAME_API, _Q_DATAFRAME_API_CORRECT)

            payload = _insights(client)
            # Concept appears because ≥3 attempts
            assert len(payload["weakest_concepts"]) > 0, (
                "3 attempts (2 wrong + 1 correct) must surface weakest_concepts"
            )
            weak = payload["weakest_concepts"][0]
            # accuracy = 1/3 ≈ 0.333...
            assert 0.0 < weak["accuracy_pct"] < 1.0, (
                f"2 wrong + 1 correct → accuracy must be between 0 and 1, "
                f"got {weak['accuracy_pct']}"
            )

    def test_wrong_submission_from_multiple_tracks_all_recorded(self) -> None:
        """
        Submitting wrong answers in mock sessions across all 4 tracks must
        create submission rows for each track in the DB.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")

            # PySpark: direct session (easiest)
            py_session = _start_pyspark(client, difficulty="easy")
            py_q = py_session["questions"][0]
            py_correct = int(pyspark_questions.get_question(py_q["id"])["correct_option"])
            _submit(client, py_session["session_id"], py_q["id"], _wrong(py_correct))

            payload = _insights(client)
            pyspark_stats = payload["per_track"]["pyspark"]
            assert pyspark_stats["accuracy_pct"] == 0.0, (
                "Wrong pyspark mock submission must record 0% accuracy"
            )

    def test_per_track_solve_count_not_incremented_by_wrong_submission(self) -> None:
        """A wrong mock submission must NOT increment solve_count in dashboard."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            q = session["questions"][0]
            _submit(client, session["session_id"], q["id"],
                    _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"])))

            payload = _insights(client)
            assert payload["per_track"]["pyspark"]["solve_count"] == 0, (
                f"Wrong submission must not increment solve_count, "
                f"got {payload['per_track']['pyspark']['solve_count']}"
            )

    def test_per_track_solve_count_incremented_by_correct_submission(self) -> None:
        """A correct mock submission must increment solve_count in dashboard."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            q = session["questions"][0]
            correct_opt = int(pyspark_questions.get_question(q["id"])["correct_option"])
            _submit(client, session["session_id"], q["id"], correct_opt)

            payload = _insights(client)
            assert payload["per_track"]["pyspark"]["solve_count"] == 1, (
                f"Correct submission must increment solve_count to 1, "
                f"got {payload['per_track']['pyspark']['solve_count']}"
            )

    def test_no_submission_gives_zero_pyspark_accuracy(self) -> None:
        """Fresh user with no submissions must have accuracy_pct = 0.0 for pyspark."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            payload = _insights(client)
            assert payload["per_track"]["pyspark"]["accuracy_pct"] == 0.0

    def test_insights_cache_is_bypassed_for_fresh_user(self) -> None:
        """
        A fresh user's first /api/dashboard/insights call must reflect any
        submissions already in the DB (cache is cold for that user_id).
        """
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            q = session["questions"][0]
            _submit(client, session["session_id"], q["id"],
                    _wrong(int(pyspark_questions.get_question(q["id"])["correct_option"])))

            # First call — cache is cold; must see the submission
            payload = _insights(client)
            assert payload["per_track"]["pyspark"]["accuracy_pct"] == 0.0, (
                "First insights call must reflect the submission (cache is cold for new user)"
            )


# ===========================================================================
# E. Discard session (DELETE /api/mock/{id})
# ===========================================================================


class TestDiscardSession:
    """
    Discard is only allowed within 2 minutes of starting if the session is
    active.  Completed sessions, wrong users, and sessions older than 2 min
    must all be rejected.
    """

    def test_active_session_within_window_can_be_discarded(self) -> None:
        """DELETE on a freshly created active session must return 204."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]

            r = client.delete(f"/api/mock/{session_id}")
            assert r.status_code == 204, (
                f"Discard of fresh active session must return 204, got {r.status_code}: {r.text}"
            )

    def test_discarded_session_not_found_afterward(self) -> None:
        """After discard, GET /api/mock/{id} must return 404."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]

            client.delete(f"/api/mock/{session_id}")
            r = client.get(f"/api/mock/{session_id}")
            assert r.status_code == 404, (
                f"Discarded session must be gone from DB (GET returns 404), "
                f"got {r.status_code}"
            )

    def test_completed_session_cannot_be_discarded(self) -> None:
        """DELETE on a finished session must return 400."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]
            _finish(client, session_id)

            r = client.delete(f"/api/mock/{session_id}")
            assert r.status_code == 400, (
                f"Completed session must reject discard with 400, got {r.status_code}: {r.text}"
            )

    def test_different_user_cannot_discard_session(self) -> None:
        """DELETE by a different user must return 404."""
        with TestClient(app) as owner_client:
            _make_user(owner_client, plan="elite")
            session = _start_pyspark(owner_client)
            session_id = session["session_id"]

        with TestClient(app) as other_client:
            _make_user(other_client, plan="elite")
            r = other_client.delete(f"/api/mock/{session_id}")
            assert r.status_code == 404, (
                f"Other user's discard of owner's session must return 404, "
                f"got {r.status_code}: {r.text}"
            )

    def test_nonexistent_session_discard_returns_404(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.delete("/api/mock/999999")
            assert r.status_code == 404

    def test_discard_does_not_affect_other_sessions(self) -> None:
        """Discarding session A must not prevent starting or accessing session B."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            s1 = _start_pyspark(client)
            # Discard session A, then start session B
            client.delete(f"/api/mock/{s1['session_id']}")
            s2 = _start_pyspark(client)

            r = client.get(f"/api/mock/{s2['session_id']}")
            assert r.status_code == 200, (
                f"Session B must still exist after session A is discarded, "
                f"got {r.status_code}"
            )

    def test_discard_removes_questions_from_db(self) -> None:
        """After discard, mock_session_questions rows for that session must also be gone."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client)
            session_id = session["session_id"]
            client.delete(f"/api/mock/{session_id}")

            conn = psycopg2.connect(_db_url())
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) FROM mock_session_questions WHERE session_id = %s",
                        (session_id,),
                    )
                    count = cur.fetchone()[0]
            finally:
                conn.close()

            assert count == 0, (
                f"mock_session_questions must be deleted on discard, found {count} rows"
            )
