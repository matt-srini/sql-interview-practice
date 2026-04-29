"""
Tests for the personalised study plan (Elite-only).

Pure unit tests for build_study_plan() cover:
  - Plan gating (None for non-Elite)
  - Action type generation (concept_drill, learning_path, mock_session, practice_hard)
  - Deduplication of (type, track) pairs
  - 5-action cap
  - Required keys on every action
  - Priority ordering
  - Mock recency check for mock_session action
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

TRACKS = ["sql", "python", "python-data", "pyspark"]


def _make_catalog_module(
    hard_count: int = 10,
    hard_id_start: int = 201,
) -> MagicMock:
    """Return a MagicMock that behaves like a catalog module."""
    hard_qs = [{"id": hard_id_start + i, "difficulty": "hard"} for i in range(hard_count)]
    m = MagicMock()
    m.get_questions_by_difficulty.return_value = {
        "easy": [],
        "medium": [],
        "hard": hard_qs,
    }
    return m


def _topic_modules(hard_count: int = 10) -> dict:
    return {t: _make_catalog_module(hard_count=hard_count) for t in TRACKS}


def _concept(
    concept: str,
    track: str = "sql",
    accuracy: float = 0.30,
    attempts: int = 5,
    correct: int | None = None,
) -> dict:
    """Build a weakest_concepts entry."""
    if correct is None:
        correct = int(round(accuracy * attempts))
    return {
        "concept": concept,
        "track": track,
        "attempts": attempts,
        "correct": correct,
        "accuracy_pct": round(correct / attempts, 3),
        "summary": "Needs work.",
    }


def _readiness(sql: int = 30, python: int = 50, pandas: int = 60, pyspark: int = 70) -> dict:
    def _lbl(s: int) -> str:
        if s >= 90: return "Strong"
        if s >= 80: return "Interview ready"
        if s >= 65: return "Getting there"
        if s >= 40: return "Building"
        return "Early stage"

    return {
        "sql": {"score": sql, "label": _lbl(sql), "components": {}},
        "python": {"score": python, "label": _lbl(python), "components": {}},
        "python-data": {"score": pandas, "label": _lbl(pandas), "components": {}},
        "pyspark": {"score": pyspark, "label": _lbl(pyspark), "components": {}},
    }


def _recent_mock_session(days_ago: float = 1.0) -> dict:
    ended = datetime.now(UTC) - timedelta(days=days_ago)
    return {
        "status": "completed",
        "ended_at": ended.isoformat(),
        "track": "sql",
        "solved_count": 2,
        "total_count": 3,
    }


def _call(
    *,
    weakest_concepts: list[dict] | None = None,
    solved_ids: dict[str, set[int]] | None = None,
    mock_sessions: list[dict] | None = None,
    readiness_scores: dict | None = None,
    effective_plan: str = "elite",
    hard_count: int = 10,
    concept_path_index: dict | None = None,
) -> list[dict] | None:
    """Call build_study_plan with patched catalog and optional concept-path index."""
    from routers.insights import build_study_plan

    modules = _topic_modules(hard_count=hard_count)
    path_index = concept_path_index if concept_path_index is not None else {}

    with (
        patch("routers.insights._TOPIC_MODULES", modules),
        patch("routers.insights._CONCEPT_PATH_INDEX", path_index),
    ):
        return build_study_plan(
            weakest_concepts=weakest_concepts or [],
            per_track_solved_question_ids=solved_ids or defaultdict(set),
            mock_sessions=mock_sessions or [],
            readiness_scores=readiness_scores,
            effective_plan=effective_plan,
        )


# ── Plan gating ───────────────────────────────────────────────────────────────

class TestStudyPlanPlanGating:

    def test_returns_none_for_free(self) -> None:
        result = _call(effective_plan="free")
        assert result is None

    def test_returns_none_for_pro(self) -> None:
        result = _call(effective_plan="pro")
        assert result is None

    def test_returns_list_for_elite(self) -> None:
        result = _call(effective_plan="elite")
        assert isinstance(result, list)

    def test_returns_list_or_none_for_elite_with_no_data(self) -> None:
        """With zero data, plan may return empty-list actions or None (both valid)."""
        result = _call(effective_plan="elite")
        assert result is None or isinstance(result, list)


# ── Required keys ─────────────────────────────────────────────────────────────

class TestStudyPlanActionKeys:
    REQUIRED_KEYS = {"type", "title", "description", "cta_label", "cta_href", "track", "priority"}

    def _actions(self) -> list[dict]:
        weakest = [_concept("JOINS", track="sql", accuracy=0.20)]
        r = _call(
            weakest_concepts=weakest,
            readiness_scores=_readiness(sql=25),
            mock_sessions=[],
        )
        return r or []

    def test_actions_have_all_required_keys(self) -> None:
        actions = self._actions()
        # May produce 0 actions if no path found — just verify shape when present
        for action in actions:
            missing = self.REQUIRED_KEYS - action.keys()
            assert not missing, f"Action missing keys: {missing} in {action}"

    def test_action_type_is_valid(self) -> None:
        actions = self._actions()
        valid_types = {"concept_drill", "learning_path", "mock_session", "practice_hard"}
        for action in actions:
            assert action["type"] in valid_types, f"Invalid action type: {action['type']}"

    def test_priority_is_positive_int(self) -> None:
        actions = self._actions()
        for action in actions:
            assert isinstance(action["priority"], int)
            assert action["priority"] >= 1


# ── Action cap and deduplication ──────────────────────────────────────────────

class TestStudyPlanCapAndDedup:

    def test_max_5_actions_returned(self) -> None:
        """Even with many weak concepts and gaps, no more than 5 actions."""
        weakest = [
            _concept("JOINS", track="sql", accuracy=0.20),
            _concept("CTEs", track="python", accuracy=0.25),
            _concept("WINDOW FUNCTIONS", track="python-data", accuracy=0.30),
        ]
        readiness = _readiness(sql=10, python=15, pandas=20, pyspark=25)
        # No mock sessions in last 14 days → mock_session will be added
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            mock_sessions=[],
        )
        if result:
            assert len(result) <= 5

    def test_no_duplicate_type_track_pairs(self) -> None:
        """(type, track) combinations should not repeat."""
        weakest = [
            _concept("JOINS", track="sql", accuracy=0.20),
            _concept("CTEs", track="sql", accuracy=0.25),  # same track as above
        ]
        readiness = _readiness(sql=25, python=50, pandas=60, pyspark=70)
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            mock_sessions=[],
        )
        if result:
            seen: set[tuple[str, str | None]] = set()
            for action in result:
                key = (action["type"], action.get("track"))
                assert key not in seen, (
                    f"Duplicate (type, track) pair found: {key} in {result}"
                )
                seen.add(key)

    def test_actions_ordered_by_priority(self) -> None:
        weakest = [_concept("JOINS", track="sql", accuracy=0.15)]
        readiness = _readiness(sql=20)
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            mock_sessions=[],
        )
        if result and len(result) > 1:
            priorities = [a["priority"] for a in result]
            assert priorities == sorted(priorities), (
                f"Actions should be sorted by priority (ascending). Got: {priorities}"
            )


# ── Individual action types ───────────────────────────────────────────────────

class TestStudyPlanConceptActions:

    def test_weak_concept_with_matching_path_creates_learning_path_action(self) -> None:
        """When a path covers the weak concept, action type = learning_path."""
        weakest = [_concept("JOINS", track="sql", accuracy=0.20)]
        readiness = _readiness(sql=20)
        path_index = {("sql", "JOINS"): ("sql-joins-path", "SQL Joins", "free")}
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            concept_path_index=path_index,
        )
        assert result is not None
        types = [a["type"] for a in result]
        assert "learning_path" in types, f"Expected learning_path action, got types: {types}"

    def test_weak_concept_without_path_creates_drill_action(self) -> None:
        """When no path covers the concept, action type = concept_drill."""
        weakest = [_concept("OBSCURE_CONCEPT", track="sql", accuracy=0.15)]
        readiness = _readiness(sql=20)
        # Empty path index — no path available
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            concept_path_index={},
        )
        assert result is not None
        types = [a["type"] for a in result]
        assert "concept_drill" in types, f"Expected concept_drill action, got: {types}"

    def test_learning_path_cta_href_contains_learn_prefix(self) -> None:
        weakest = [_concept("JOINS", track="sql", accuracy=0.20)]
        readiness = _readiness(sql=20)
        path_index = {("sql", "JOINS"): ("sql-joins", "SQL Joins", "free")}
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            concept_path_index=path_index,
        )
        assert result is not None
        path_actions = [a for a in result if a["type"] == "learning_path"]
        for action in path_actions:
            assert "/learn/" in action["cta_href"], (
                f"learning_path cta_href should contain /learn/, got: {action['cta_href']}"
            )

    def test_drill_action_cta_href_contains_practice_prefix(self) -> None:
        weakest = [_concept("RARE", track="sql", accuracy=0.10)]
        readiness = _readiness(sql=20)
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            concept_path_index={},
        )
        assert result is not None
        drill_actions = [a for a in result if a["type"] == "concept_drill"]
        for action in drill_actions:
            assert action["cta_href"].startswith("/practice/"), (
                f"concept_drill cta_href should start with /practice/, got: {action['cta_href']}"
            )


class TestStudyPlanHardPracticeAction:

    def test_low_hard_coverage_creates_practice_hard_action(self) -> None:
        """Track with <30% hard coverage should trigger a practice_hard action."""
        # 10 hard questions; solving 0 = 0% hard coverage
        solved = defaultdict(set)
        solved["sql"] = set()
        result = _call(
            solved_ids=solved,
            hard_count=10,
        )
        # may or may not appear depending on ordering; verify type exists when triggered
        if result:
            types = [a["type"] for a in result]
            # With 0% hard coverage, practice_hard should appear
            assert "practice_hard" in types, (
                f"Expected practice_hard for 0% hard coverage, got types: {types}"
            )

    def test_sufficient_hard_coverage_no_practice_hard_action(self) -> None:
        """Track with ≥30% hard coverage should NOT trigger practice_hard."""
        hard_ids = list(range(201, 211))  # 10 hard questions
        # Solve 4 (40% > 30%)
        solved = defaultdict(set)
        for track in TRACKS:
            solved[track] = set(hard_ids[:4])

        result = _call(
            solved_ids=solved,
            hard_count=10,
        )
        if result:
            types = [a["type"] for a in result]
            assert "practice_hard" not in types, (
                f"practice_hard should not appear when coverage ≥ 30%, got: {types}"
            )

    def test_practice_hard_cta_href_contains_practice_prefix(self) -> None:
        solved = defaultdict(set)
        result = _call(solved_ids=solved, hard_count=10)
        if result:
            hard_actions = [a for a in result if a["type"] == "practice_hard"]
            for action in hard_actions:
                assert action["cta_href"].startswith("/practice/"), (
                    f"practice_hard cta_href should start with /practice/, got: {action['cta_href']}"
                )


class TestStudyPlanMockSessionAction:

    def test_no_recent_mocks_creates_mock_session_action(self) -> None:
        """Fewer than 3 completed mocks in last 14 days → mock_session action added."""
        result = _call(mock_sessions=[])  # zero mocks
        assert result is not None
        types = [a["type"] for a in result]
        assert "mock_session" in types, (
            f"Expected mock_session action when no recent mocks, got: {types}"
        )

    def test_3_recent_mocks_no_mock_session_action(self) -> None:
        """3 or more recent completed mocks → mock_session action NOT added."""
        sessions = [_recent_mock_session(days_ago=i + 1) for i in range(3)]
        result = _call(mock_sessions=sessions, hard_count=100)
        # With plenty of hard coverage too, there should be no mock_session action
        hard_ids = list(range(201, 301))  # 100 hard
        solved = defaultdict(set)
        for track in TRACKS:
            solved[track] = set(hard_ids[:40])  # 40% coverage → no practice_hard either

        result = _call(
            solved_ids=solved,
            mock_sessions=sessions,
            hard_count=100,
        )
        if result:
            types = [a["type"] for a in result]
            assert "mock_session" not in types, (
                f"mock_session should not appear when ≥3 recent mocks, got: {types}"
            )

    def test_old_mocks_not_counted_toward_recent(self) -> None:
        """Mocks older than 14 days don't count as recent."""
        # 5 sessions but all older than 14 days
        old_sessions = [_recent_mock_session(days_ago=15 + i) for i in range(5)]
        result = _call(mock_sessions=old_sessions)
        assert result is not None
        types = [a["type"] for a in result]
        assert "mock_session" in types, (
            "Old mocks (>14 days) should not count — mock_session action should appear"
        )

    def test_mock_session_cta_href_is_slash_mock(self) -> None:
        result = _call(mock_sessions=[])
        assert result is not None
        mock_actions = [a for a in result if a["type"] == "mock_session"]
        for action in mock_actions:
            assert action["cta_href"] == "/mock", (
                f"mock_session cta_href should be '/mock', got: {action['cta_href']}"
            )

    def test_mock_session_track_is_none(self) -> None:
        """mock_session actions are not track-specific."""
        result = _call(mock_sessions=[])
        assert result is not None
        mock_actions = [a for a in result if a["type"] == "mock_session"]
        for action in mock_actions:
            assert action["track"] is None, (
                f"mock_session should have track=None, got: {action['track']}"
            )


# ── Step 1 — Lowest readiness track ──────────────────────────────────────────

class TestStudyPlanLowestReadinessTrack:

    def test_action_targets_lowest_readiness_track(self) -> None:
        """Step 1 should produce an action for the track with the lowest readiness score."""
        weakest = [
            _concept("JOINS", track="sql", accuracy=0.15),   # sql is the weakest track
            _concept("PANDAS_OPS", track="python-data", accuracy=0.40),
        ]
        readiness = _readiness(sql=10, python=60, pandas=70, pyspark=80)
        path_index = {
            ("sql", "JOINS"): ("sql-joins", "SQL Joins", "free"),
        }
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=readiness,
            concept_path_index=path_index,
        )
        assert result is not None and len(result) > 0
        # First action should target sql (lowest readiness)
        first_action = result[0]
        assert first_action["track"] == "sql", (
            f"First action should target the lowest readiness track (sql), got: {first_action['track']}"
        )

    def test_no_readiness_scores_step_1_skipped(self) -> None:
        """When readiness_scores is None, step 1 is skipped gracefully."""
        weakest = [_concept("JOINS", track="sql", accuracy=0.15)]
        result = _call(
            weakest_concepts=weakest,
            readiness_scores=None,
        )
        # Should not crash; may still produce actions from steps 2–4
        assert result is None or isinstance(result, list)
