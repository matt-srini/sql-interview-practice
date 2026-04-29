"""
Tests for Elite focus mode mock sessions.

Pure unit tests verify that _select_questions() correctly filters the pool
to concept-tagged questions and falls back gracefully when the focused pool
is too small.

Integration tests verify the endpoint validation: only Elite users can send
focus_concepts, and >3 concepts is rejected with 422.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import backend.main as main

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_question(
    qid: int,
    difficulty: str = "medium",
    concepts: list[str] | None = None,
    track: str = "sql",
) -> dict:
    """Minimal question dict with optional concept tags."""
    return {
        "id": qid,
        "order": qid,
        "difficulty": difficulty,
        "_track": track,
        "_mock_only": False,
        "concepts": concepts or [],
    }


def _run_select(
    pool: list[dict],
    num_questions: int,
    plan: str = "elite",
    focus_concepts: list[str] | None = None,
    mocked_ids: set[int] | None = None,
) -> tuple[list[dict], bool]:
    """
    Call _select_questions() with a patched pool and return (selected, focus_fallback).
    """
    from routers.mock import _select_questions

    if mocked_ids is None:
        mocked_ids = set()

    with (
        patch("routers.mock._pool_for_track", return_value=pool),
        patch("routers.mock._get_solved_ids_for_track", AsyncMock(return_value=set())),
        patch("routers.mock.get_previously_mocked_ids", AsyncMock(return_value=mocked_ids)),
    ):
        user = {"id": "00000000-0000-0000-0000-000000000001", "plan": plan}
        return asyncio.run(
            _select_questions("sql", "medium", num_questions, user, focus_concepts=focus_concepts)
        )


# ── Focus pool filtering unit tests ──────────────────────────────────────────

class TestFocusPoolFiltering:

    def test_no_focus_concepts_uses_full_pool(self) -> None:
        pool = [
            _make_question(1, concepts=["JOINS"]),
            _make_question(2, concepts=["CTEs"]),
            _make_question(3, concepts=["WINDOW FUNCTIONS"]),
        ]
        selected, fallback = _run_select(pool, num_questions=3, focus_concepts=None)
        assert len(selected) == 3
        assert fallback is False

    def test_focus_concepts_filters_pool_to_matching(self) -> None:
        pool = [
            _make_question(1, concepts=["JOINS"]),
            _make_question(2, concepts=["CTEs"]),
            _make_question(3, concepts=["WINDOW FUNCTIONS"]),
            _make_question(4, concepts=["WINDOW FUNCTIONS"]),
            _make_question(5, concepts=["JOINS"]),
        ]
        selected, fallback = _run_select(
            pool, num_questions=2, focus_concepts=["JOINS"]
        )
        selected_ids = {q["question_id"] for q in selected}
        # Only questions 1 and 5 match "JOINS"
        assert selected_ids.issubset({1, 5}), (
            f"Expected only JOINS questions (1, 5), got: {selected_ids}"
        )
        assert fallback is False

    def test_focus_multi_concept_matches_any(self) -> None:
        """Questions matching ANY of the focus concepts are included."""
        pool = [
            _make_question(1, concepts=["JOINS"]),
            _make_question(2, concepts=["CTEs"]),
            _make_question(3, concepts=["AGGREGATES"]),
        ]
        selected, fallback = _run_select(
            pool, num_questions=2, focus_concepts=["JOINS", "CTEs"]
        )
        selected_ids = {q["question_id"] for q in selected}
        # Questions 1 and 2 match; question 3 does not
        assert selected_ids.issubset({1, 2}), (
            f"Expected only JOINS/CTEs questions (1, 2), got: {selected_ids}"
        )
        assert fallback is False

    def test_focus_concepts_case_insensitive_match(self) -> None:
        """Focus concept matching is case-insensitive."""
        pool = [
            _make_question(1, concepts=["Window Functions"]),   # mixed case in catalog
            _make_question(2, concepts=["CTEs"]),
            _make_question(3, concepts=["joins"]),               # lowercase in catalog
        ]
        # Pass focus concepts in various cases — all should match
        selected, fallback = _run_select(
            pool, num_questions=2, focus_concepts=["WINDOW FUNCTIONS", "JOINS"]
        )
        selected_ids = {q["question_id"] for q in selected}
        assert selected_ids.issubset({1, 3}), (
            f"Case-insensitive match failed. Expected {{1, 3}}, got: {selected_ids}"
        )

    def test_focus_fallback_when_pool_too_small(self) -> None:
        """When focused pool is smaller than num_questions, fallback to full pool."""
        pool = [
            _make_question(1, concepts=["JOINS"]),   # matches focus
            _make_question(2, concepts=["CTEs"]),    # does NOT match focus
            _make_question(3, concepts=["CTEs"]),    # does NOT match focus
        ]
        # Ask for 3 questions but focus only matches 1 — must fall back
        selected, fallback = _run_select(
            pool, num_questions=3, focus_concepts=["JOINS"]
        )
        assert len(selected) == 3
        assert fallback is True

    def test_no_fallback_when_focus_pool_exactly_matches(self) -> None:
        """When focused pool size == num_questions, no fallback needed."""
        pool = [
            _make_question(1, concepts=["JOINS"]),
            _make_question(2, concepts=["JOINS"]),
            _make_question(3, concepts=["CTEs"]),
        ]
        selected, fallback = _run_select(
            pool, num_questions=2, focus_concepts=["JOINS"]
        )
        selected_ids = {q["question_id"] for q in selected}
        assert selected_ids == {1, 2}
        assert fallback is False

    def test_fallback_returns_correct_count(self) -> None:
        """When focus pool is too small, fallback fills the remainder from general pool."""
        pool = [
            _make_question(1, concepts=["JOINS"]),   # only focus match
            _make_question(2, concepts=["CTEs"]),
            _make_question(3, concepts=["CTEs"]),
        ]
        # Focus only matches Q1 (1 question) but we need 2 → fallback
        selected, fallback = _run_select(
            pool, num_questions=2, focus_concepts=["JOINS"]
        )
        # Correct count is returned regardless of which questions were chosen
        assert len(selected) == 2, f"Expected 2 questions in fallback, got {len(selected)}"
        assert fallback is True
        # All selected question IDs must be from the pool
        pool_ids = {1, 2, 3}
        selected_ids = {q["question_id"] for q in selected}
        assert selected_ids.issubset(pool_ids)

    def test_empty_focus_concepts_list_treated_as_no_filter(self) -> None:
        """An empty list for focus_concepts should behave like None (no filtering)."""
        pool = [
            _make_question(i, concepts=["CONCEPT_" + str(i)]) for i in range(1, 4)
        ]
        selected, fallback = _run_select(pool, num_questions=3, focus_concepts=[])
        assert len(selected) == 3
        assert fallback is False


# ── Integration tests — endpoint validation ───────────────────────────────────

_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    global _counter
    _counter += 1
    email = f"focus-test-{_counter}@internal.test"
    client.get("/api/catalog")
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Focus Test", "password": "Password123"},
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


class TestFocusModeEndpointGating:

    def test_non_elite_with_focus_concepts_returns_403(self) -> None:
        """Free and Pro users cannot use focus_concepts."""
        for plan in ("free", "pro"):
            with TestClient(app) as client:
                _make_user(client, plan=plan)
                r = client.post(
                    "/api/mock/start",
                    json={
                        "mode": "30min",
                        "track": "sql",
                        "difficulty": "easy",
                        "focus_concepts": ["JOINS"],
                    },
                )
            assert r.status_code == 403, (
                f"Expected 403 for {plan} user with focus_concepts, got {r.status_code}"
            )

    def test_more_than_3_focus_concepts_returns_422(self) -> None:
        """Elite users sending >3 focus_concepts should get 422."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post(
                "/api/mock/start",
                json={
                    "mode": "30min",
                    "track": "sql",
                    "difficulty": "easy",
                    "focus_concepts": ["JOINS", "CTEs", "WINDOW FUNCTIONS", "AGGREGATES"],
                },
            )
        assert r.status_code == 422

    def test_elite_without_focus_concepts_starts_normally(self) -> None:
        """Elite user with no focus_concepts should start a session normally."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post(
                "/api/mock/start",
                json={"mode": "30min", "track": "sql", "difficulty": "easy"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "session_id" in body
        assert body.get("focus_fallback") is False

    def test_focus_fallback_flag_present_in_start_response(self) -> None:
        """The /start response always contains focus_fallback, defaulting to False."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post(
                "/api/mock/start",
                json={"mode": "30min", "track": "sql", "difficulty": "easy"},
            )
        assert r.status_code == 200, r.text
        assert "focus_fallback" in r.json()

    def test_lifetime_elite_can_use_focus_concepts_with_valid_count(self) -> None:
        """lifetime_elite normalises to elite and should be allowed focus mode."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            # Valid: 1 concept
            r = client.post(
                "/api/mock/start",
                json={
                    "mode": "30min",
                    "track": "sql",
                    "difficulty": "easy",
                    "focus_concepts": ["JOINS"],
                },
            )
        # Should not 403 (may 200 or 400 if no matching questions exist, but not 403)
        assert r.status_code != 403, (
            f"lifetime_elite should not be blocked from focus mode, got {r.status_code}: {r.text}"
        )

    def test_elite_with_exactly_3_focus_concepts_not_rejected(self) -> None:
        """3 focus_concepts is within the limit — should not return 422."""
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post(
                "/api/mock/start",
                json={
                    "mode": "30min",
                    "track": "sql",
                    "difficulty": "easy",
                    "focus_concepts": ["JOINS", "CTEs", "WINDOW FUNCTIONS"],
                },
            )
        # 200 (success) or 400 (not enough questions with those concepts) — not 422
        assert r.status_code != 422, (
            f"3 focus_concepts should not trigger 422 validation error, got {r.status_code}"
        )
