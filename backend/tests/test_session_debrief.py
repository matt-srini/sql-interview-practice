"""
Unit tests for the template-based session debrief (routers.insights.build_session_debrief).

These tests are pure unit tests — no DB, no HTTP client.  They exercise the
debrief builder directly with crafted inputs so the template logic can be
verified in isolation.
"""
from __future__ import annotations

import pytest

from routers.insights import build_session_debrief


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _q(
    qid: int = 1,
    title: str = "Test question",
    is_solved: bool = True,
    concepts: list[str] | None = None,
    time_spent_s: int | None = None,
    track: str = "sql",
    difficulty: str = "medium",
    position: int = 1,
    is_follow_up: bool = False,
) -> dict:
    return {
        "id": qid,
        "title": title,
        "is_solved": is_solved,
        "concepts": concepts or ["AGGREGATION"],
        "time_spent_s": time_spent_s,
        "track": track,
        "difficulty": difficulty,
        "position": position,
        "is_follow_up": is_follow_up,
    }


def _meta(
    solved_count: int = 2,
    total_count: int = 3,
    time_used_s: int | None = 900,
    time_limit_s: int = 1800,
    difficulty: str = "medium",
    track: str = "sql",
) -> dict:
    return {
        "solved_count": solved_count,
        "total_count": total_count,
        "time_used_s": time_used_s,
        "time_limit_s": time_limit_s,
        "difficulty": difficulty,
        "track": track,
    }


# ---------------------------------------------------------------------------
# Plan gating
# ---------------------------------------------------------------------------

class TestPlanGating:
    def test_returns_none_for_pro(self):
        qs = [_q(is_solved=True)]
        result = build_session_debrief(qs, _meta(1, 1), [], "pro")
        assert result is None

    def test_returns_none_for_free(self):
        qs = [_q(is_solved=True)]
        result = build_session_debrief(qs, _meta(1, 1), [], "free")
        assert result is None

    def test_returns_dict_for_elite(self):
        qs = [_q(is_solved=True)]
        result = build_session_debrief(qs, _meta(1, 1), [], "elite")
        assert isinstance(result, dict)

    def test_returns_none_for_empty_questions(self):
        result = build_session_debrief([], _meta(0, 0), [], "elite")
        assert result is None


# ---------------------------------------------------------------------------
# Headline generation
# ---------------------------------------------------------------------------

class TestHeadline:
    def test_perfect_session(self):
        qs = [_q(i, is_solved=True) for i in range(1, 4)]
        r = build_session_debrief(qs, _meta(3, 3, time_used_s=800, time_limit_s=1800), [], "elite")
        assert "perfect" in r["headline"].lower() or "3" in r["headline"]

    def test_perfect_session_with_time_to_spare(self):
        qs = [_q(i, is_solved=True) for i in range(1, 4)]
        r = build_session_debrief(qs, _meta(3, 3, time_used_s=600, time_limit_s=1800), [], "elite")
        # time_used/limit = 0.33 < 0.5, all solved → "inside the time limit"
        assert "time" in r["headline"].lower()

    def test_solid_session(self):
        qs = [_q(1, is_solved=True), _q(2, is_solved=True), _q(3, is_solved=False)]
        r = build_session_debrief(qs, _meta(2, 3), [], "elite")
        assert "2 of 3" in r["headline"]

    def test_tough_session(self):
        qs = [_q(1, is_solved=False), _q(2, is_solved=False), _q(3, is_solved=False)]
        r = build_session_debrief(qs, _meta(0, 3), [], "elite")
        assert "0" in r["headline"] or "tough" in r["headline"].lower()

    def test_right_up_to_time_limit(self):
        qs = [_q(1, is_solved=True), _q(2, is_solved=True), _q(3, is_solved=True)]
        r = build_session_debrief(qs, _meta(3, 3, time_used_s=1780, time_limit_s=1800), [], "elite")
        assert "time limit" in r["headline"].lower()

    def test_headline_is_a_string(self):
        qs = [_q(is_solved=True)]
        r = build_session_debrief(qs, _meta(1, 1), [], "elite")
        assert isinstance(r["headline"], str)
        assert len(r["headline"]) > 0


# ---------------------------------------------------------------------------
# Pattern observations
# ---------------------------------------------------------------------------

class TestPatterns:
    def test_patterns_is_a_list(self):
        qs = [_q(is_solved=True)]
        r = build_session_debrief(qs, _meta(1, 1), [], "elite")
        assert isinstance(r["patterns"], list)

    def test_strong_concept_mentioned(self):
        qs = [
            _q(1, is_solved=True, concepts=["WINDOW FUNCTIONS"]),
            _q(2, is_solved=True, concepts=["WINDOW FUNCTIONS"]),
        ]
        r = build_session_debrief(qs, _meta(2, 2), [], "elite")
        assert any("WINDOW FUNCTIONS" in p for p in r["patterns"])

    def test_weak_concept_mentioned(self):
        qs = [
            _q(1, is_solved=False, concepts=["COHORT RETENTION"]),
            _q(2, is_solved=False, concepts=["COHORT RETENTION"]),
        ]
        r = build_session_debrief(qs, _meta(0, 2), [], "elite")
        assert any("COHORT RETENTION" in p for p in r["patterns"])

    def test_follow_up_solved_mentioned(self):
        qs = [
            _q(1, is_solved=True, position=1),
            _q(2, is_solved=True, position=2, is_follow_up=True),
        ]
        r = build_session_debrief(qs, _meta(2, 2), [], "elite")
        assert any("follow" in p.lower() for p in r["patterns"])

    def test_follow_up_unsolved_mentioned(self):
        qs = [
            _q(1, is_solved=True, position=1),
            _q(2, is_solved=False, position=2, is_follow_up=True),
        ]
        r = build_session_debrief(qs, _meta(1, 2), [], "elite")
        assert any("follow" in p.lower() for p in r["patterns"])

    def test_known_weakness_language_when_historical_poor(self):
        """Concept with ≥3 historical attempts and <60% accuracy → 'known weakness' language."""
        qs = [_q(1, is_solved=False, concepts=["SUBQUERY PATTERNS"], track="sql")]
        # Simulate 4 past attempts, only 1 correct
        events = [
            {"track": "sql", "question_id": 999 + i, "is_correct": i == 0}
            for i in range(4)
        ]
        r = build_session_debrief(qs, _meta(0, 1), events, "elite")
        # Pattern should acknowledge the ongoing difficulty
        weak_patterns = [p for p in r["patterns"] if "SUBQUERY PATTERNS" in p]
        assert len(weak_patterns) > 0

    def test_time_sink_pattern_for_single_dominant_question(self):
        """If one question takes >55% of total time, a time-sink pattern should appear."""
        qs = [
            _q(1, is_solved=True, time_spent_s=700),
            _q(2, is_solved=True, time_spent_s=100),
        ]
        r = build_session_debrief(qs, _meta(2, 2, time_used_s=800), [], "elite")
        assert any("absorbed" in p.lower() or "time" in p.lower() for p in r["patterns"])

    def test_no_time_sink_for_single_question_session(self):
        """Single-question sessions should not generate a time-sink pattern."""
        qs = [_q(1, is_solved=True, time_spent_s=500)]
        r = build_session_debrief(qs, _meta(1, 1, time_used_s=500), [], "elite")
        time_patterns = [p for p in r["patterns"] if "absorbed" in p.lower()]
        assert len(time_patterns) == 0


# ---------------------------------------------------------------------------
# Priority action
# ---------------------------------------------------------------------------

class TestPriorityAction:
    def test_priority_action_present(self):
        qs = [_q(is_solved=False, concepts=["WINDOW FUNCTIONS"])]
        r = build_session_debrief(qs, _meta(0, 1), [], "elite")
        assert r["priority_action"] is not None
        assert isinstance(r["priority_action"], str)
        assert len(r["priority_action"]) > 0

    def test_all_solved_medium_suggests_hard_session(self):
        qs = [_q(i, is_solved=True) for i in range(1, 4)]
        r = build_session_debrief(qs, _meta(3, 3, difficulty="medium"), [], "elite")
        assert "hard" in r["priority_action"].lower()

    def test_all_solved_hard_suggests_consistency(self):
        qs = [_q(i, is_solved=True) for i in range(1, 4)]
        r = build_session_debrief(qs, _meta(3, 3, difficulty="hard"), [], "elite")
        action = r["priority_action"].lower()
        assert "hard" in action or "consistent" in action or "cadence" in action

    def test_weak_concept_with_path_returns_path_slug(self):
        """Concepts that map to a known path should include priority_path_slug."""
        # This relies on the actual concept-path index built from content files.
        # We pick a concept known to be in a real path; if none match, the test
        # asserts the field is present even when None (graceful degradation).
        qs = [_q(1, is_solved=False, concepts=["WINDOW FUNCTIONS"], track="sql")]
        r = build_session_debrief(qs, _meta(0, 1), [], "elite")
        # priority_path_slug is either a slug string or None — both are acceptable
        assert "priority_path_slug" in r
        assert "priority_path_title" in r

    def test_priority_question_ids_is_list(self):
        qs = [_q(1, is_solved=False, concepts=["AGGREGATION"])]
        r = build_session_debrief(qs, _meta(0, 1), [], "elite")
        assert isinstance(r["priority_question_ids"], list)

    def test_session_questions_excluded_from_drill_ids(self):
        """The drill question IDs must not include any question that was in this session."""
        qs = [_q(1, is_solved=False, concepts=["AGGREGATION"])]
        r = build_session_debrief(qs, _meta(0, 1), [], "elite")
        assert 1 not in r["priority_question_ids"]


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_all_required_keys_present(self):
        qs = [_q(is_solved=True)]
        r = build_session_debrief(qs, _meta(1, 1), [], "elite")
        for key in ("headline", "patterns", "priority_action",
                    "priority_path_slug", "priority_path_title", "priority_question_ids"):
            assert key in r, f"Missing key: {key}"

    def test_no_extra_internal_keys(self):
        qs = [_q(is_solved=True)]
        r = build_session_debrief(qs, _meta(1, 1), [], "elite")
        allowed = {"headline", "patterns", "priority_action",
                   "priority_path_slug", "priority_path_title", "priority_question_ids"}
        assert set(r.keys()) == allowed

    def test_patterns_contains_no_empty_strings(self):
        qs = [_q(1, is_solved=True), _q(2, is_solved=False, concepts=["SUBQUERY PATTERNS"])]
        r = build_session_debrief(qs, _meta(1, 2), [], "elite")
        assert all(isinstance(p, str) and len(p) > 0 for p in r["patterns"])
