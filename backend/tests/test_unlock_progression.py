"""End-to-end unlock progression test.

Simulates a free-plan user solving SQL questions in order and verifies that
catalog unlock state transitions fire at *exactly* the right thresholds.

Progression verified (SQL / code-track free plan):
  Easy → Medium:   7 solved → no change
                   8 solved → exactly 3 medium accessible
                  14 solved → still 3 medium
                  15 solved → exactly 8 medium accessible
                  24 solved → still 8 medium
                  25 solved → all medium accessible

  Medium → Hard:   7 solved → no change
                   8 solved → exactly 3 hard accessible
                  14 solved → still 3 hard
                  15 solved → exactly 8 hard accessible
                  21 solved → still 8 hard
                  22 solved → exactly FREE_HARD_CAP_CODE (15) hard accessible
                         and the (cap+1)th hard question stays locked

Each threshold boundary also checks 403 enforcement on the next-locked question
and 200 success on an accessible question via /run-query.
"""
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from questions import get_question, get_questions_by_difficulty
from unlock import FREE_HARD_CAP_CODE

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ordered_ids(difficulty: str) -> list[int]:
    """Return question IDs for a difficulty sorted by their order field."""
    grouped = get_questions_by_difficulty()
    return [
        int(q["id"])
        for q in sorted(grouped[difficulty], key=lambda q: int(q.get("order", 0)))
    ]


def _catalog_states(client: TestClient, difficulty: str) -> list[str]:
    """Fetch /api/catalog and return state list for one difficulty (sorted by order)."""
    resp = client.get("/api/catalog")
    assert resp.status_code == 200, f"Catalog returned {resp.status_code}: {resp.text}"
    groups = {g["difficulty"]: g for g in resp.json()["groups"]}
    return [
        q["state"]
        for q in sorted(groups[difficulty]["questions"], key=lambda q: q["order"])
    ]


def _accessible_count(states: list[str]) -> int:
    """Number of questions a user can actually interact with (unlocked + solved)."""
    return sum(1 for s in states if s in ("unlocked", "solved"))


def _solve(client: TestClient, question_id: int) -> None:
    """Submit the canonical solution for question_id and assert it's accepted."""
    q = get_question(question_id)
    assert q is not None, f"Question {question_id} not found in catalog"
    resp = client.post(
        "/api/submit",
        json={"query": q["solution_query"], "question_id": question_id},
    )
    assert resp.status_code == 200, (
        f"Submit returned {resp.status_code} for Q{question_id}: {resp.text}"
    )
    result = resp.json()
    assert result["correct"] is True, (
        f"Solution for Q{question_id} was not accepted: {result.get('feedback')}"
    )


def _assert_run_blocked(client: TestClient, question_id: int) -> None:
    resp = client.post(
        "/run-query",
        json={"query": "SELECT 1", "question_id": question_id},
    )
    assert resp.status_code == 403, (
        f"Expected 403 for locked Q{question_id}, got {resp.status_code}"
    )


def _assert_run_allowed(client: TestClient, question_id: int) -> None:
    resp = client.post(
        "/run-query",
        json={"query": "SELECT 1", "question_id": question_id},
    )
    assert resp.status_code == 200, (
        f"Expected 200 for accessible Q{question_id}, got {resp.status_code}"
    )


# ── Main progression test ─────────────────────────────────────────────────────

def test_free_plan_full_sql_progression() -> None:
    """
    Walk a free-plan user through the entire SQL unlock ladder.
    Verifies every threshold boundary in both directions (before/after).
    """
    # Raise rate-limit ceiling so the ~100 requests in this test don't trip it.
    limiter = main.rate_limiter
    orig_max = limiter.max_requests
    orig_window = limiter.window_seconds
    limiter.max_requests = 500
    limiter.window_seconds = 3600
    main._clear_rate_limit_state()

    try:
        _run_progression()
    finally:
        limiter.max_requests = orig_max
        limiter.window_seconds = orig_window
        main._clear_rate_limit_state()


def _run_progression() -> None:
    easy_ids   = _ordered_ids("easy")
    medium_ids = _ordered_ids("medium")
    hard_ids   = _ordered_ids("hard")

    total_medium = len(medium_ids)
    total_hard   = len(hard_ids)

    with TestClient(app) as client:

        # ── 0 solved: everything except easy is locked ────────────────────────
        assert all(s == "unlocked" for s in _catalog_states(client, "easy")), \
            "All easy should be unlocked at start"
        assert all(s == "locked" for s in _catalog_states(client, "medium")), \
            "All medium should be locked at start"
        assert all(s == "locked" for s in _catalog_states(client, "hard")), \
            "All hard should be locked at start"

        # run-query on first medium → 403
        _assert_run_blocked(client, medium_ids[0])

        # ── Solve 7 easy — medium threshold NOT yet crossed ───────────────────
        for qid in easy_ids[:7]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "medium")) == 0, \
            "Expected 0 medium accessible after 7 easy"

        # ── Solve 8th easy — first 3 medium unlock ───────────────────────────
        _solve(client, easy_ids[7])

        medium_states = _catalog_states(client, "medium")
        assert _accessible_count(medium_states) == 3, \
            f"Expected 3 medium accessible after 8 easy, got {_accessible_count(medium_states)}"
        assert medium_states[2] in ("unlocked", "solved"), \
            "medium[2] should be accessible after 8 easy"
        assert medium_states[3] == "locked", \
            "medium[3] should still be locked after 8 easy"

        # Boundary enforcement via run-query
        _assert_run_allowed(client, medium_ids[0])
        _assert_run_blocked(client, medium_ids[3])

        # ── Solve to 14 easy — still only 3 medium ───────────────────────────
        for qid in easy_ids[8:14]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "medium")) == 3, \
            "Expected 3 medium accessible after 14 easy"

        # ── Solve 15th easy — 8 medium unlock ────────────────────────────────
        _solve(client, easy_ids[14])

        medium_states = _catalog_states(client, "medium")
        assert _accessible_count(medium_states) == 8, \
            f"Expected 8 medium accessible after 15 easy, got {_accessible_count(medium_states)}"
        assert medium_states[7] in ("unlocked", "solved"), \
            "medium[7] should be accessible after 15 easy"
        assert medium_states[8] == "locked", \
            "medium[8] should still be locked after 15 easy"

        _assert_run_allowed(client, medium_ids[7])
        _assert_run_blocked(client, medium_ids[8])

        # ── Solve to 24 easy — still 8 medium ────────────────────────────────
        for qid in easy_ids[15:24]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "medium")) == 8, \
            "Expected 8 medium accessible after 24 easy"

        # ── Solve 25th easy — all medium unlock ──────────────────────────────
        _solve(client, easy_ids[24])

        medium_states = _catalog_states(client, "medium")
        assert _accessible_count(medium_states) == total_medium, \
            f"Expected all {total_medium} medium accessible after 25 easy, got {_accessible_count(medium_states)}"

        _assert_run_allowed(client, medium_ids[-1])

        # hard still fully locked despite easy solves
        assert all(s == "locked" for s in _catalog_states(client, "hard")), \
            "All hard should still be locked (no medium solved yet)"

        # ── Solve 7 medium — hard threshold NOT yet crossed ──────────────────
        for qid in medium_ids[:7]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "hard")) == 0, \
            "Expected 0 hard accessible after 7 medium"

        _assert_run_blocked(client, hard_ids[0])

        # ── Solve 8th medium — first 3 hard unlock ───────────────────────────
        _solve(client, medium_ids[7])

        hard_states = _catalog_states(client, "hard")
        assert _accessible_count(hard_states) == 3, \
            f"Expected 3 hard accessible after 8 medium, got {_accessible_count(hard_states)}"
        assert hard_states[2] in ("unlocked", "solved"), \
            "hard[2] should be accessible after 8 medium"
        assert hard_states[3] == "locked", \
            "hard[3] should still be locked after 8 medium"

        _assert_run_allowed(client, hard_ids[0])
        _assert_run_blocked(client, hard_ids[3])

        # ── Solve to 14 medium — still 3 hard ────────────────────────────────
        for qid in medium_ids[8:14]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "hard")) == 3, \
            "Expected 3 hard accessible after 14 medium"

        # ── Solve 15th medium — 8 hard unlock ────────────────────────────────
        _solve(client, medium_ids[14])

        hard_states = _catalog_states(client, "hard")
        assert _accessible_count(hard_states) == 8, \
            f"Expected 8 hard accessible after 15 medium, got {_accessible_count(hard_states)}"
        assert hard_states[7] in ("unlocked", "solved"), \
            "hard[7] should be accessible after 15 medium"
        assert hard_states[8] == "locked", \
            "hard[8] should still be locked after 15 medium"

        _assert_run_allowed(client, hard_ids[7])
        _assert_run_blocked(client, hard_ids[8])

        # ── Solve to 21 medium — still 8 hard ────────────────────────────────
        for qid in medium_ids[15:21]:
            _solve(client, qid)

        assert _accessible_count(_catalog_states(client, "hard")) == 8, \
            "Expected 8 hard accessible after 21 medium"

        # ── Solve 22nd medium — full hard cap (15) unlocks ───────────────────
        _solve(client, medium_ids[21])

        hard_states = _catalog_states(client, "hard")
        assert _accessible_count(hard_states) == FREE_HARD_CAP_CODE, \
            f"Expected {FREE_HARD_CAP_CODE} hard accessible after 22 medium, got {_accessible_count(hard_states)}"

        _assert_run_allowed(client, hard_ids[FREE_HARD_CAP_CODE - 1])

        # Questions beyond the cap must remain locked
        if total_hard > FREE_HARD_CAP_CODE:
            assert hard_states[FREE_HARD_CAP_CODE] == "locked", \
                f"hard[{FREE_HARD_CAP_CODE}] (beyond cap) should stay locked on free plan"
            _assert_run_blocked(client, hard_ids[FREE_HARD_CAP_CODE])
