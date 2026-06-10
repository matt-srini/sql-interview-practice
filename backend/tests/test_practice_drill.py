"""Tests for GET /api/practice/drill (concept drill endpoint)."""
from urllib.parse import quote

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _insert_progress, _make_user
from concept_families import concept_matches_focus

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_TRACK = "pandas"
_TEST_CONCEPT = "GROUPED AGGREGATION"


def _drill(client, track=_TEST_TRACK, concept=_TEST_CONCEPT):
    return client.get(
        "/api/practice/drill",
        params={"track": track, "concept": concept},
    )


# ---------------------------------------------------------------------------
# TC-D01 — Free user is rejected
# ---------------------------------------------------------------------------

def test_tc_d01_free_user_403():
    """Free users cannot access concept drills (Pro feature gate)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = _drill(client)
    assert r.status_code == 403
    body = r.json()
    assert "error" in body
    assert "Pro" in body["error"]


# ---------------------------------------------------------------------------
# TC-D02 — Pro user gets 200, non-empty results for a known concept
# ---------------------------------------------------------------------------

def test_tc_d02_pro_user_grouped_aggregation_pandas():
    """Pro user receives a non-empty list for GROUPED AGGREGATION in pandas."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = _drill(client)

    assert r.status_code == 200
    body = r.json()

    assert body["track"] == _TEST_TRACK
    assert body["track_label"] == "Pandas"
    assert body["concept"] == _TEST_CONCEPT
    assert body["total"] > 0
    assert len(body["questions"]) == body["total"]

    # Every returned question must have at least one tag in the GROUPED AGGREGATION family
    for q in body["questions"]:
        tags = q["concepts"]
        assert any(concept_matches_focus(tag, _TEST_CONCEPT, _TEST_TRACK) for tag in tags), (
            f"Question {q['id']} matched but has no GROUPED AGGREGATION family tag: {tags}"
        )


# ---------------------------------------------------------------------------
# TC-D03 — Ordering: easy-first, then unsolved-before-solved, then order asc
# ---------------------------------------------------------------------------

def test_tc_d03_ordering_unsolved_first_then_difficulty():
    """Questions are ordered unsolved-before-solved, then easy→medium→hard, then by order."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")

        # Get drill results fresh (no solves yet)
        r = _drill(client)
    assert r.status_code == 200
    questions = r.json()["questions"]
    assert len(questions) > 0

    _diff_rank = {"easy": 0, "medium": 1, "hard": 2}
    _state_rank = {"unlocked": 0, "solved": 1}

    for i in range(len(questions) - 1):
        a, b = questions[i], questions[i + 1]
        key_a = (_state_rank.get(a["state"], 0), _diff_rank.get(a["difficulty"], 99), a["order"])
        key_b = (_state_rank.get(b["state"], 0), _diff_rank.get(b["difficulty"], 99), b["order"])
        assert key_a <= key_b, (
            f"Ordering violated at index {i}: {a} is not <= {b}"
        )


def test_tc_d03b_solved_question_sorts_after_unsolved_within_difficulty():
    """A solved question sorts after unsolved ones of the same difficulty."""
    import pandas_questions as pq

    # Find a GROUPED AGGREGATION easy question to mark solved
    grouped = pq.get_questions_by_difficulty()
    target_q = None
    for q in grouped["easy"]:
        if any(concept_matches_focus(tag, _TEST_CONCEPT, _TEST_TRACK) for tag in q.get("concepts", [])):
            target_q = q
            break

    if target_q is None:
        pytest.skip("No easy GROUPED AGGREGATION question found in pandas")

    target_id = int(target_q["id"])

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")

    # _insert_progress uses psycopg2 (sync) — call between TestClient contexts
    _insert_progress(user["id"], target_id, track=_TEST_TRACK)

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = _drill(client)

    assert r.status_code == 200
    questions = r.json()["questions"]

    # The solved question must not appear before any unsolved easy question
    easy_qs = [q for q in questions if q["difficulty"] == "easy"]
    assert len(easy_qs) > 0

    found_solved = False
    for q in easy_qs:
        if q["id"] == target_id:
            assert q["state"] == "solved"
            found_solved = True
        elif found_solved:
            # A question after the solved one must also be solved (no unsolved after solved)
            assert q["state"] == "solved", (
                f"Unsolved question {q['id']} appears after solved question {target_id} "
                "in the same difficulty bucket"
            )

    assert found_solved, f"Target question {target_id} not found in drill results"


# ---------------------------------------------------------------------------
# TC-D04 — Elite user is allowed
# ---------------------------------------------------------------------------

def test_tc_d04_elite_user_200():
    """Elite users can access concept drills."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = _drill(client)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# TC-D05 — Unknown track returns 404
# ---------------------------------------------------------------------------

def test_tc_d05_unknown_track_404():
    """Unknown track slug returns 404."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = _drill(client, track="nonexistent-track")
    assert r.status_code == 404
    assert "Unknown track" in r.json()["error"]


# ---------------------------------------------------------------------------
# TC-D06 — Concept with no matches returns 200 with empty questions
# ---------------------------------------------------------------------------

def test_tc_d06_no_match_concept_returns_empty():
    """A concept that matches no pandas questions returns 200 with empty questions list."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = _drill(client, concept="TOTALLY NONEXISTENT CONCEPT ZZZZZZ")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["questions"] == []
    assert body["solved_count"] == 0


# ---------------------------------------------------------------------------
# TC-D07 — solved_count is accurate
# ---------------------------------------------------------------------------

def test_tc_d07_solved_count_reflects_progress():
    """solved_count in the response matches how many matching questions are marked solved."""
    import pandas_questions as pq

    grouped = pq.get_questions_by_difficulty()
    match_ids = []
    for difficulty, qs in grouped.items():
        for q in qs:
            if any(concept_matches_focus(tag, _TEST_CONCEPT, _TEST_TRACK) for tag in q.get("concepts", [])):
                match_ids.append(int(q["id"]))

    assert len(match_ids) >= 2, "Need at least 2 matching questions to verify solved_count"

    solve_ids = match_ids[:2]

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")

    # _insert_progress uses psycopg2 (sync) — call between TestClient contexts
    for qid in solve_ids:
        _insert_progress(user["id"], qid, track=_TEST_TRACK)

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = _drill(client)

    assert r.status_code == 200
    body = r.json()
    assert body["solved_count"] == 2

    solved_in_response = [q for q in body["questions"] if q["state"] == "solved"]
    assert len(solved_in_response) == 2
    assert {q["id"] for q in solved_in_response} == set(solve_ids)
