"""
Follow-up injection integration tests for mock sessions.

Covers the follow-up question injection behaviour in POST /api/mock/{id}/submit:

  test_correct_answer_with_follow_up_id_injects
  test_wrong_answer_does_not_inject_follow_up
  test_no_injection_at_last_position
  test_follow_up_injected_flag_in_submit_response
  test_follow_up_does_not_chain

Uses direct psycopg2 DB seeding so tests are deterministic regardless of pool
randomisation.  A synthetic mock session is inserted with specific question IDs
drawn from the mock-only bank (Q2035 has follow_up_id=2050; Q2050 has none).

All tests require a Pro-tier user so the submit endpoint resolves the question
via the catalog _INDEX (which includes mock-only questions).
"""
from __future__ import annotations

import os

import psycopg2
import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# SQL mock-only follow-up pair (seeded in Phase D):
#   Q2035  medium  mock_only=True  follow_up_id=2050
#   Q2050  medium  mock_only=True  (no follow_up_id — chain depth = 1)
#   Q3030  hard    mock_only=True  follow_up_id=3034  (used as a filler)
# ---------------------------------------------------------------------------
PARENT_Q_ID = 2035          # mock-only SQL medium, has follow_up_id=2050
FOLLOW_UP_Q_ID = 2050       # mock-only SQL medium, no follow_up_id
FILLER_Q_ID = 3030          # mock-only SQL hard,   has follow_up_id=3034

_counter = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _db_url() -> str:
    raw = os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/sql_practice_test",
    )
    return raw.replace("postgresql+asyncpg://", "postgresql://")


def _make_user(client: TestClient, plan: str = "pro") -> dict:
    global _counter
    _counter += 1
    email = f"mock-session-test-{_counter}@internal.test"
    client.get("/api/catalog")  # seed anonymous session cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Mock Session Test", "password": "Password123"},
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


def _seed_session(user_id: str, questions: list[tuple[int, str, int]]) -> int:
    """
    Directly insert a mock session with specific questions into the DB.

    questions: list of (question_id, track, position)

    Returns the session_id.
    """
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO mock_sessions
                    (user_id, mode, track, difficulty, time_limit_s, started_at)
                VALUES (%s::uuid, '30min', 'sql', 'medium', 1800, now())
                RETURNING id
                """,
                (user_id,),
            )
            session_id = cur.fetchone()[0]
            for qid, track, pos in questions:
                cur.execute(
                    """
                    INSERT INTO mock_session_questions
                        (session_id, question_id, track, position)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (session_id, qid, track, pos),
                )
        conn.commit()
        return session_id
    finally:
        conn.close()


def _submit(client: TestClient, session_id: int, question_id: int,
            code: str, track: str = "sql") -> dict:
    r = client.post(
        f"/api/mock/{session_id}/submit",
        json={"question_id": question_id, "track": track, "code": code},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _get_session_questions(client: TestClient, session_id: int) -> list[dict]:
    r = client.get(f"/api/mock/{session_id}")
    assert r.status_code == 200, r.text
    return r.json()["questions"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFollowUpInjection:
    """Follow-up question injection triggered by a correct answer."""

    def test_correct_answer_with_follow_up_id_injects(self) -> None:
        """
        Correct answer on a question with follow_up_id causes the follow-up to
        appear in the session immediately after the answered question.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            # Position 1: Q2035 (has follow_up_id=2050), position 2: filler Q3030
            session_id = _seed_session(
                user["id"],
                [(PARENT_Q_ID, "sql", 1), (FILLER_Q_ID, "sql", 2)],
            )

            # Q2035 is mock-only — read the expected_query directly from the content file.
            import json, pathlib
            medium = json.loads(
                (pathlib.Path(__file__).parent.parent / "content/questions/medium.json").read_text()
            )
            parent_q = next(q for q in medium if q["id"] == PARENT_Q_ID)
            correct_code = parent_q["expected_query"]

            result = _submit(client, session_id, PARENT_Q_ID, correct_code)

            assert result.get("correct") is True, f"Expected correct=True, got {result}"
            assert result.get("follow_up_injected") is True, (
                f"Expected follow_up_injected=True after correct answer on Q{PARENT_Q_ID}, got {result}"
            )

            # The follow-up should now appear in the session
            questions = _get_session_questions(client, session_id)
            q_ids = [q["id"] for q in questions]
            assert FOLLOW_UP_Q_ID in q_ids, (
                f"Expected Q{FOLLOW_UP_Q_ID} in session after injection, got ids: {q_ids}"
            )

            # The injected question must carry is_follow_up=True
            follow_up_q = next(q for q in questions if q["id"] == FOLLOW_UP_Q_ID)
            assert follow_up_q.get("is_follow_up") is True, (
                f"Expected is_follow_up=True on Q{FOLLOW_UP_Q_ID}, got: {follow_up_q}"
            )

            # The follow-up should be positioned between the answered Q and the filler
            parent_pos = next(q["position"] for q in questions if q["id"] == PARENT_Q_ID)
            filler_pos = next(q["position"] for q in questions if q["id"] == FILLER_Q_ID)
            follow_up_pos = follow_up_q["position"]
            assert parent_pos < follow_up_pos < filler_pos, (
                f"Follow-up position {follow_up_pos} should be between "
                f"parent {parent_pos} and filler {filler_pos}"
            )

    def test_wrong_answer_does_not_inject_follow_up(self) -> None:
        """A wrong answer must not trigger follow-up injection."""
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            session_id = _seed_session(
                user["id"],
                [(PARENT_Q_ID, "sql", 1), (FILLER_Q_ID, "sql", 2)],
            )

            result = _submit(client, session_id, PARENT_Q_ID, "SELECT 1 AS wrong_answer")

            # The answer should be wrong (almost certainly — a trivially wrong query)
            # Regardless: follow_up_injected must be False
            assert result.get("follow_up_injected") is False, (
                f"follow_up_injected should be False on wrong/non-accepted answer, got: {result}"
            )

            questions = _get_session_questions(client, session_id)
            q_ids = [q["id"] for q in questions]
            assert FOLLOW_UP_Q_ID not in q_ids, (
                f"Q{FOLLOW_UP_Q_ID} must not appear in session after wrong answer, got: {q_ids}"
            )

    def test_no_injection_at_last_position(self) -> None:
        """
        When the answered question is the LAST in the session, no follow-up is
        injected even on a correct answer.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            # Single-question session — Q2035 is both position 1 AND the last position
            session_id = _seed_session(
                user["id"],
                [(PARENT_Q_ID, "sql", 1)],
            )

            import json, pathlib
            medium = json.loads(
                (pathlib.Path(__file__).parent.parent / "content/questions/medium.json").read_text()
            )
            parent_q = next(q for q in medium if q["id"] == PARENT_Q_ID)
            correct_code = parent_q["expected_query"]

            result = _submit(client, session_id, PARENT_Q_ID, correct_code)

            assert result.get("follow_up_injected") is False, (
                f"follow_up_injected must be False when answering the last question, got: {result}"
            )

            questions = _get_session_questions(client, session_id)
            q_ids = [q["id"] for q in questions]
            assert FOLLOW_UP_Q_ID not in q_ids, (
                f"Q{FOLLOW_UP_Q_ID} must not be injected when parent is last question, got: {q_ids}"
            )

    def test_follow_up_injected_flag_in_submit_response(self) -> None:
        """
        The submit response always includes a `follow_up_injected` boolean key,
        regardless of whether injection occurred.
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            # Session with 2 questions so injection is possible
            session_id = _seed_session(
                user["id"],
                [(PARENT_Q_ID, "sql", 1), (FILLER_Q_ID, "sql", 2)],
            )

            import json, pathlib
            medium = json.loads(
                (pathlib.Path(__file__).parent.parent / "content/questions/medium.json").read_text()
            )
            parent_q = next(q for q in medium if q["id"] == PARENT_Q_ID)
            correct_code = parent_q["expected_query"]

            result = _submit(client, session_id, PARENT_Q_ID, correct_code)

            assert "follow_up_injected" in result, (
                f"`follow_up_injected` key must always be present in submit response, "
                f"got keys: {list(result.keys())}"
            )
            assert isinstance(result["follow_up_injected"], bool), (
                f"`follow_up_injected` must be a bool, got: {type(result['follow_up_injected'])}"
            )
            # With a correct answer and a non-last position, it should be True
            assert result["follow_up_injected"] is True

    def test_follow_up_does_not_chain(self) -> None:
        """
        Answering the injected follow-up question correctly must NOT trigger
        another injection (chain depth is capped at 1).

        Q2035 → injects Q2050 (Q2050 has no follow_up_id, so no further injection).
        """
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            # 3-question session: parent → [follow-up injected here] → filler
            session_id = _seed_session(
                user["id"],
                [(PARENT_Q_ID, "sql", 1), (FILLER_Q_ID, "sql", 2)],
            )

            import json, pathlib
            content_dir = pathlib.Path(__file__).parent.parent / "content/questions"
            medium = json.loads((content_dir / "medium.json").read_text())

            parent_q = next(q for q in medium if q["id"] == PARENT_Q_ID)
            follow_up_q = next(q for q in medium if q["id"] == FOLLOW_UP_Q_ID)

            # Step 1: answer Q2035 correctly → Q2050 is injected
            r1 = _submit(client, session_id, PARENT_Q_ID, parent_q["expected_query"])
            assert r1.get("follow_up_injected") is True, (
                f"Step 1: expected injection after Q{PARENT_Q_ID}, got: {r1}"
            )

            # Verify session now has 3 questions
            qs_after_injection = _get_session_questions(client, session_id)
            assert len(qs_after_injection) == 3, (
                f"Session should have 3 questions after injection, got: "
                f"{[q['question_id'] for q in qs_after_injection]}"
            )

            # Step 2: answer Q2050 correctly — it has no follow_up_id → no injection
            r2 = _submit(client, session_id, FOLLOW_UP_Q_ID, follow_up_q["expected_query"])
            assert r2.get("follow_up_injected") is False, (
                f"Step 2: Q{FOLLOW_UP_Q_ID} has no follow_up_id so follow_up_injected "
                f"must be False, got: {r2}"
            )

            # Session question count must still be 3 — no new question was added
            qs_final = _get_session_questions(client, session_id)
            assert len(qs_final) == 3, (
                f"Session should still have 3 questions after answering the follow-up, "
                f"got: {[q['question_id'] for q in qs_final]}"
            )
