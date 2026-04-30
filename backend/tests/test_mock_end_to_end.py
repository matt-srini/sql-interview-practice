"""
End-to-end mock interview flow tests.

These tests actually play through a session — submitting correct and wrong
answers via the real API endpoints — and verify that the downstream features
(score, per-question is_solved, debrief, analytics) reflect what was submitted.

PySpark MCQ is used throughout because correct_option is deterministic: we
look it up from the catalog at test time and can submit the exact right answer
or a provably wrong one (any option != correct_option).

Coverage gaps this file fills compared to test_mock.py:
  1. Correct answers actually count in solved_count and is_solved
  2. Wrong answers produce is_solved=False and do not inflate solved_count
  3. Partial sessions (correct Q1, wrong Q2) yield solved_count=1, total=2
  4. Elite debrief present in /finish, Pro/Free debrief=null
  5. Debrief headline reflects actual correct/wrong ratio
  6. Analytics (GET /api/mock/analytics) shows real session data after finishing
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import backend.main as main
import pyspark_questions

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ── Shared helpers ─────────────────────────────────────────────────────────────

_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    global _counter
    _counter += 1
    email = f"e2e-test-{_counter}@internal.test"
    client.get("/api/catalog")  # seed anonymous session cookie
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "E2E Test", "password": "Password123"},
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


def _start_pyspark(client: TestClient, *, num_questions: int = 2) -> dict:
    """Start a custom PySpark easy session and return the session body."""
    r = client.post(
        "/api/mock/start",
        json={
            "mode": "custom",
            "track": "pyspark",
            "difficulty": "easy",
            "num_questions": num_questions,
            "time_minutes": 10,
        },
    )
    assert r.status_code == 200, f"Could not start PySpark session: {r.text}"
    return r.json()


def _correct_option(question_id: int) -> int:
    """Look up the correct option for a PySpark question from the catalog."""
    q = pyspark_questions.get_question(question_id)
    assert q is not None, f"Question {question_id} not found in catalog"
    return int(q["correct_option"])


def _wrong_option(question_id: int) -> int:
    """Return any option that is NOT the correct one (wraps around 4 options)."""
    correct = _correct_option(question_id)
    return (correct + 1) % 4  # options are 0-3


def _submit(client: TestClient, session_id: int, question_id: int, selected_option: int) -> dict:
    r = client.post(
        f"/api/mock/{session_id}/submit",
        json={
            "question_id": question_id,
            "track": "pyspark",
            "selected_option": selected_option,
        },
    )
    assert r.status_code == 200, f"submit failed: {r.text}"
    return r.json()


def _finish(client: TestClient, session_id: int) -> dict:
    r = client.post(f"/api/mock/{session_id}/finish")
    assert r.status_code == 200, f"finish failed: {r.text}"
    return r.json()


# ── 1. Score and is_solved reflect actual submissions ─────────────────────────

class TestEndToEndScoring:

    def test_correct_submission_gives_solved_count_1(self) -> None:
        """Submit the correct MCQ answer for one question → solved_count=1."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            result = _submit(client, session_id, q["id"], _correct_option(q["id"]))
            assert result["correct"] is True, (
                f"Submitting correct_option should mark answer as correct, got: {result}"
            )

            summary = _finish(client, session_id)
            assert summary["solved_count"] == 1, (
                f"solved_count should be 1 after one correct submission, got {summary['solved_count']}"
            )

    def test_wrong_submission_gives_solved_count_0(self) -> None:
        """Submit a wrong MCQ answer → solved_count=0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            result = _submit(client, session_id, q["id"], _wrong_option(q["id"]))
            assert result["correct"] is False, (
                f"Submitting wrong option should mark answer as incorrect, got: {result}"
            )

            summary = _finish(client, session_id)
            assert summary["solved_count"] == 0, (
                f"solved_count should be 0 after one wrong submission, got {summary['solved_count']}"
            )

    def test_partial_session_correct_then_wrong(self) -> None:
        """2-question session: answer Q1 correctly, Q2 wrongly → solved_count=1."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            session_id = session["session_id"]
            qs = session["questions"]
            assert len(qs) == 2, f"Expected 2 questions, got {len(qs)}"

            # Submit Q1 correctly, Q2 wrongly
            r1 = _submit(client, session_id, qs[0]["id"], _correct_option(qs[0]["id"]))
            r2 = _submit(client, session_id, qs[1]["id"], _wrong_option(qs[1]["id"]))

            assert r1["correct"] is True, "Q1 should be correct"
            assert r2["correct"] is False, "Q2 should be wrong"

            summary = _finish(client, session_id)
            assert summary["solved_count"] == 1, (
                f"solved_count should be 1 (Q1 correct, Q2 wrong), got {summary['solved_count']}"
            )
            assert summary["total_count"] == 2

    def test_is_solved_true_for_correctly_answered_question(self) -> None:
        """After finishing, the correctly answered question has is_solved=True."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _correct_option(q["id"]))

            summary = _finish(client, session_id)
            finished_q = next(
                (fq for fq in summary["questions"] if fq["id"] == q["id"]), None
            )
            assert finished_q is not None, "Question not found in finish summary"
            assert finished_q["is_solved"] is True, (
                f"Question answered correctly should have is_solved=True, got {finished_q['is_solved']}"
            )

    def test_is_solved_false_for_wrongly_answered_question(self) -> None:
        """After finishing, the wrongly answered question has is_solved=False."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _wrong_option(q["id"]))

            summary = _finish(client, session_id)
            finished_q = next(
                (fq for fq in summary["questions"] if fq["id"] == q["id"]), None
            )
            assert finished_q is not None
            assert finished_q["is_solved"] is False, (
                f"Question answered wrongly should have is_solved=False, got {finished_q['is_solved']}"
            )

    def test_unanswered_question_has_is_solved_false(self) -> None:
        """Questions not submitted before finishing have is_solved=False."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            session_id = session["session_id"]
            qs = session["questions"]

            # Only submit Q1; leave Q2 unanswered
            _submit(client, session_id, qs[0]["id"], _correct_option(qs[0]["id"]))

            summary = _finish(client, session_id)
            unanswered = next(
                (fq for fq in summary["questions"] if fq["id"] == qs[1]["id"]), None
            )
            assert unanswered is not None
            assert unanswered["is_solved"] is False, (
                f"Unanswered question should have is_solved=False, got {unanswered['is_solved']}"
            )

    def test_no_submissions_gives_all_is_solved_false(self) -> None:
        """Finishing immediately (no submissions) → all questions have is_solved=False."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            summary = _finish(client, session["session_id"])

            for q in summary["questions"]:
                assert q["is_solved"] is False, (
                    f"Unanswered q{q['id']} should be is_solved=False, got {q['is_solved']}"
                )
            assert summary["solved_count"] == 0

    def test_multiple_submissions_only_first_correct_counts(self) -> None:
        """Submitting the same question twice: the second attempt doesn't flip is_solved=False back."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            # First: correct
            r1 = _submit(client, session_id, q["id"], _correct_option(q["id"]))
            assert r1["correct"] is True

            # Second: wrong (resubmit — backend may accept or ignore)
            _submit(client, session_id, q["id"], _wrong_option(q["id"]))

            summary = _finish(client, session_id)
            # solved_count should still be 1 — first correct submission stands
            assert summary["solved_count"] >= 1, (
                f"First correct submission should keep solved_count >= 1, got {summary['solved_count']}"
            )

    def test_total_count_equals_question_count(self) -> None:
        """total_count in finish summary always equals the number of questions started with."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            summary = _finish(client, session["session_id"])

            assert summary["total_count"] == 2, (
                f"total_count should equal question count (2), got {summary['total_count']}"
            )
            assert len(summary["questions"]) == 2

    def test_all_questions_answered_correctly_gives_perfect_score(self) -> None:
        """Answering every question correctly → solved_count == total_count."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=3)
            session_id = session["session_id"]
            qs = session["questions"]
            assert len(qs) == 3

            for q in qs:
                result = _submit(client, session_id, q["id"], _correct_option(q["id"]))
                assert result["correct"] is True, f"Q{q['id']} should be correct"

            summary = _finish(client, session_id)
            assert summary["solved_count"] == summary["total_count"], (
                f"All correct → solved_count ({summary['solved_count']}) "
                f"should equal total_count ({summary['total_count']})"
            )
            assert summary["total_count"] == 3

    def test_all_questions_answered_wrongly_gives_zero_score(self) -> None:
        """Answering every question wrongly → solved_count == 0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=3)
            session_id = session["session_id"]
            qs = session["questions"]

            for q in qs:
                result = _submit(client, session_id, q["id"], _wrong_option(q["id"]))
                assert result["correct"] is False, f"Q{q['id']} should be wrong"

            summary = _finish(client, session_id)
            assert summary["solved_count"] == 0, (
                f"All wrong → solved_count should be 0, got {summary['solved_count']}"
            )
            assert summary["total_count"] == 3

    def test_finish_after_all_questions_answered_has_status_completed(self) -> None:
        """Finishing after all questions are answered returns a completed summary."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            session_id = session["session_id"]
            qs = session["questions"]

            for q in qs:
                _submit(client, session_id, q["id"], _correct_option(q["id"]))

            summary = _finish(client, session_id)
            assert summary.get("status") == "completed", (
                f"Finished session should have status='completed', got: {summary.get('status')!r}"
            )


# ── 2. Elite session debrief (end-to-end) ────────────────────────────────────

class TestEliteSessionDebrief:

    def test_debrief_key_present_in_finish_response(self) -> None:
        """The finish response always includes a 'debrief' key for all plan types."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])
        assert "debrief" in summary, (
            f"finish response must contain 'debrief' key, got keys: {list(summary.keys())}"
        )

    def test_elite_debrief_is_not_null(self) -> None:
        """Elite users always get a non-null debrief after finishing a session."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])
        assert summary["debrief"] is not None, (
            "Elite users must receive a non-null debrief in the finish response"
        )

    def test_pro_debrief_is_null(self) -> None:
        """Pro users do not get a debrief."""
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])
        assert summary.get("debrief") is None, (
            f"Pro users should get debrief=null, got: {summary.get('debrief')}"
        )

    def test_free_debrief_is_null(self) -> None:
        """Free users do not get a debrief."""
        with TestClient(app) as client:
            _make_user(client, plan="free")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])
        assert summary.get("debrief") is None, (
            f"Free users should get debrief=null, got: {summary.get('debrief')}"
        )

    def test_lifetime_elite_debrief_is_not_null(self) -> None:
        """lifetime_elite normalises to elite — debrief must be present."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])
        assert summary["debrief"] is not None, (
            "lifetime_elite must receive a non-null debrief"
        )

    def test_elite_debrief_has_required_keys(self) -> None:
        """Elite debrief must contain headline, patterns, and priority_action."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])

        debrief = summary["debrief"]
        assert debrief is not None
        required = {"headline", "patterns", "priority_action"}
        missing = required - debrief.keys()
        assert not missing, (
            f"Elite debrief missing required keys: {missing}\n"
            f"Got keys: {list(debrief.keys())}"
        )

    def test_debrief_headline_is_non_empty_string(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])

        assert isinstance(summary["debrief"]["headline"], str)
        assert len(summary["debrief"]["headline"]) > 0

    def test_debrief_headline_reflects_perfect_score(self) -> None:
        """Correct answer → debrief headline should mention 'Perfect'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _correct_option(q["id"]))
            summary = _finish(client, session_id)

        headline = summary["debrief"]["headline"].lower()
        assert "perfect" in headline, (
            f"Headline for 1/1 correct should mention 'perfect', got: {summary['debrief']['headline']!r}"
        )

    def test_debrief_headline_reflects_zero_score(self) -> None:
        """Wrong answer → debrief headline should mention 'Tough'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _wrong_option(q["id"]))
            summary = _finish(client, session_id)

        headline = summary["debrief"]["headline"].lower()
        assert "tough" in headline, (
            f"Headline for 0/1 should mention 'Tough', got: {summary['debrief']['headline']!r}"
        )

    def test_debrief_patterns_is_list(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])

        assert isinstance(summary["debrief"]["patterns"], list)

    def test_debrief_does_not_leak_internal_fields(self) -> None:
        """Debrief should not contain internal computation keys."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            summary = _finish(client, session["session_id"])

        debrief = summary["debrief"]
        assert debrief is not None
        internal_keys = {"_weighted_accuracy", "_diff_order", "_mock_only", "_track"}
        assert not internal_keys.intersection(debrief.keys()), (
            f"Internal keys leaked into debrief: {internal_keys.intersection(debrief.keys())}"
        )

    def test_debrief_partial_session_headline_contains_score(self) -> None:
        """2-question session with 1 correct → headline contains '1 of 2'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=2)
            session_id = session["session_id"]
            qs = session["questions"]

            # Q1 correct, Q2 wrong
            _submit(client, session_id, qs[0]["id"], _correct_option(qs[0]["id"]))
            _submit(client, session_id, qs[1]["id"], _wrong_option(qs[1]["id"]))

            summary = _finish(client, session_id)

        headline = summary["debrief"]["headline"]
        assert "1 of 2" in headline, (
            f"Partial session headline should mention '1 of 2', got: {headline!r}"
        )


# ── 3. Analytics after real sessions ─────────────────────────────────────────

class TestAnalyticsAfterRealSessions:

    def test_analytics_shows_one_session_after_completing(self) -> None:
        """After finishing one session, analytics shows total_sessions=1."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")

            session = _start_pyspark(client, num_questions=1)
            _finish(client, session["session_id"])

            r = client.get("/api/mock/analytics")
            assert r.status_code == 200, r.text
            body = r.json()

        assert body["total_sessions"] == 1, (
            f"After completing 1 session, total_sessions should be 1, got {body['total_sessions']}"
        )

    def test_analytics_sessions_last_30d_counts_just_completed(self) -> None:
        """A freshly completed session is included in sessions_last_30d."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            _finish(client, session["session_id"])

            r = client.get("/api/mock/analytics")
        body = r.json()
        assert body["sessions_last_30d"] == 1, (
            f"Fresh completed session should count in sessions_last_30d, got {body['sessions_last_30d']}"
        )

    def test_analytics_avg_score_after_perfect_session(self) -> None:
        """After a 1/1 correct session, avg_score_pct should be 100.0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _correct_option(q["id"]))
            _finish(client, session_id)

            r = client.get("/api/mock/analytics")
        body = r.json()
        assert body["avg_score_pct"] == 100.0, (
            f"1/1 correct → avg_score_pct should be 100.0, got {body['avg_score_pct']}"
        )
        assert body["best_score_pct"] == 100.0

    def test_analytics_avg_score_after_zero_session(self) -> None:
        """After a 0/1 (all wrong) session, avg_score_pct should be 0.0."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            session_id = session["session_id"]
            q = session["questions"][0]

            _submit(client, session_id, q["id"], _wrong_option(q["id"]))
            _finish(client, session_id)

            r = client.get("/api/mock/analytics")
        body = r.json()
        assert body["avg_score_pct"] == 0.0, (
            f"0/1 wrong → avg_score_pct should be 0.0, got {body['avg_score_pct']}"
        )

    def test_analytics_score_trend_has_one_entry_after_one_session(self) -> None:
        """score_trend should have exactly one entry after one completed session."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            _finish(client, session["session_id"])

            r = client.get("/api/mock/analytics")
        assert len(r.json()["score_trend"]) == 1

    def test_analytics_track_breakdown_includes_pyspark(self) -> None:
        """After a PySpark session, track_breakdown should contain 'pyspark'."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            _finish(client, session["session_id"])

            r = client.get("/api/mock/analytics")
        tb = r.json()["track_breakdown"]
        assert "pyspark" in tb, (
            f"pyspark should appear in track_breakdown after a PySpark session, got: {list(tb.keys())}"
        )
        assert tb["pyspark"]["sessions"] == 1

    def test_analytics_two_sessions_accumulate(self) -> None:
        """Completing two sessions → total_sessions=2 and score_trend has 2 entries."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")

            # Session 1: perfect (all correct)
            s1 = _start_pyspark(client, num_questions=1)
            q1 = s1["questions"][0]
            _submit(client, s1["session_id"], q1["id"], _correct_option(q1["id"]))
            _finish(client, s1["session_id"])

            # Session 2: zero (all wrong)
            s2 = _start_pyspark(client, num_questions=1)
            q2 = s2["questions"][0]
            _submit(client, s2["session_id"], q2["id"], _wrong_option(q2["id"]))
            _finish(client, s2["session_id"])

            r = client.get("/api/mock/analytics")

        body = r.json()
        assert body["total_sessions"] == 2, (
            f"Two completed sessions → total_sessions should be 2, got {body['total_sessions']}"
        )
        assert len(body["score_trend"]) == 2, (
            f"Two sessions → score_trend should have 2 entries, got {body['score_trend']}"
        )
        assert body["best_score_pct"] == 100.0, "Best score should be 100%"
        assert body["avg_score_pct"] == 50.0, (
            f"Avg of 100%+0% = 50%, got {body['avg_score_pct']}"
        )

    def test_analytics_difficulty_breakdown_after_easy_session(self) -> None:
        """PySpark easy session → difficulty_breakdown contains 'easy' key."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            session = _start_pyspark(client, num_questions=1)
            _finish(client, session["session_id"])

            r = client.get("/api/mock/analytics")
        db = r.json()["difficulty_breakdown"]
        assert "easy" in db, (
            f"difficulty_breakdown should contain 'easy' after an easy session, got: {list(db.keys())}"
        )
        assert db["easy"]["sessions"] == 1
