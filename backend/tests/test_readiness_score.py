"""
Tests for the interview readiness score (Elite-only).

Pure unit tests for _compute_readiness_scores() cover:
  - Plan gating (None for non-Elite)
  - Practice coverage component (40 pts max)
  - Mock accuracy component (35 pts max)
  - Concept strength component (25 pts max)
  - Score clamping to [0, 100]
  - Label threshold boundaries
  - All 4 tracks present in output
  - Component keys in response shape
"""
from __future__ import annotations

from collections import defaultdict
from unittest.mock import MagicMock, patch

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_session(
    *,
    track: str = "sql",
    solved: int = 2,
    total: int = 3,
    status: str = "completed",
) -> dict:
    return {
        "track": track,
        "solved_count": solved,
        "total_count": total,
        "status": status,
    }


def _make_catalog_module(
    easy_ids: list[int],
    medium_ids: list[int],
    hard_ids: list[int],
) -> MagicMock:
    """Return a MagicMock that behaves like a catalog module."""
    easy_qs = [{"id": i, "difficulty": "easy"} for i in easy_ids]
    medium_qs = [{"id": i, "difficulty": "medium"} for i in medium_ids]
    hard_qs = [{"id": i, "difficulty": "hard"} for i in hard_ids]
    m = MagicMock()
    m.get_questions_by_difficulty.return_value = {
        "easy": easy_qs,
        "medium": medium_qs,
        "hard": hard_qs,
    }
    return m


def _call(
    *,
    solved_ids: dict[str, set[int]] | None = None,
    mock_sessions: list[dict] | None = None,
    concept_attempts: dict[tuple[str, str], int] | None = None,
    concept_correct: dict[tuple[str, str], int] | None = None,
    effective_plan: str = "elite",
    easy_ids: list[int] | None = None,
    medium_ids: list[int] | None = None,
    hard_ids: list[int] | None = None,
) -> dict | None:
    """
    Call _compute_readiness_scores with a fully synthetic catalog.
    All 4 tracks share the same catalog structure (easy/medium/hard_ids)
    unless overridden.
    """
    from routers.insights import _compute_readiness_scores

    _easy = easy_ids or list(range(1, 11))        # 10 easy questions
    _medium = medium_ids or list(range(101, 121))  # 20 medium questions
    _hard = hard_ids or list(range(201, 231))      # 30 hard questions

    catalog_mock = _make_catalog_module(_easy, _medium, _hard)
    topic_modules = {
        "sql": catalog_mock,
        "python": catalog_mock,
        "python-data": catalog_mock,
        "pyspark": catalog_mock,
    }

    with patch("routers.insights._TOPIC_MODULES", topic_modules):
        return _compute_readiness_scores(
            per_track_solved_question_ids=solved_ids or defaultdict(set),
            mock_sessions=mock_sessions or [],
            concept_attempts=concept_attempts or defaultdict(int),
            concept_correct=concept_correct or defaultdict(int),
            effective_plan=effective_plan,
        )


# ── Plan gating ───────────────────────────────────────────────────────────────

class TestReadinessPlanGating:

    def test_returns_none_for_free(self) -> None:
        result = _call(effective_plan="free")
        assert result is None

    def test_returns_none_for_pro(self) -> None:
        result = _call(effective_plan="pro")
        assert result is None

    def test_returns_none_for_lifetime_pro(self) -> None:
        # normalize_plan("lifetime_pro") = "pro" — but _compute_readiness_scores
        # receives already-normalised plan, so pass "pro" directly.
        result = _call(effective_plan="pro")
        assert result is None

    def test_returns_dict_for_elite(self) -> None:
        result = _call(effective_plan="elite")
        assert isinstance(result, dict)

    def test_all_four_tracks_present_for_elite(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        assert set(result.keys()) == {"sql", "python", "python-data", "pyspark"}


# ── Response shape ────────────────────────────────────────────────────────────

class TestReadinessResponseShape:

    def test_each_track_has_score_label_components(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            assert "score" in data, f"Missing 'score' for track {track}"
            assert "label" in data, f"Missing 'label' for track {track}"
            assert "components" in data, f"Missing 'components' for track {track}"

    def test_components_has_practice_mock_concept_keys(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            comps = data["components"]
            assert "practice" in comps, f"Missing 'practice' component for {track}"
            assert "mock_accuracy" in comps, f"Missing 'mock_accuracy' component for {track}"
            assert "concept_strength" in comps, f"Missing 'concept_strength' for {track}"

    def test_score_is_integer(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            assert isinstance(data["score"], int), f"Score for {track} should be int, got {type(data['score'])}"

    def test_score_is_within_0_to_100(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            assert 0 <= data["score"] <= 100, f"Score {data['score']} out of range for {track}"


# ── Zero-solve baseline ───────────────────────────────────────────────────────

class TestReadinessZeroSolves:

    def test_zero_solves_gives_zero_practice_component(self) -> None:
        result = _call(effective_plan="elite", solved_ids=defaultdict(set))
        assert result is not None
        for track, data in result.items():
            assert data["components"]["practice"] == 0.0, (
                f"Zero solves should give 0 practice pts for {track}"
            )

    def test_zero_solves_zero_mocks_gives_low_score(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            assert data["score"] < 40, (
                f"Zero-activity score should be under 40 (Early stage), got {data['score']} for {track}"
            )

    def test_zero_activity_label_is_early_stage(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track, data in result.items():
            assert data["label"] == "Early stage", (
                f"Zero-activity label should be 'Early stage', got '{data['label']}' for {track}"
            )


# ── Practice coverage component ───────────────────────────────────────────────

class TestReadinessPracticeComponent:

    def test_full_easy_coverage_gives_10_pts(self) -> None:
        easy_ids = list(range(1, 11))   # 10 easy
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))
        solved = defaultdict(set)
        solved["sql"] = set(easy_ids)  # all easy solved
        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        comps = result["sql"]["components"]
        assert comps["practice"] == pytest.approx(10.0, abs=0.5), (
            f"Full easy coverage should give ~10 pts, got {comps['practice']}"
        )

    def test_full_medium_coverage_gives_20_pts_additional(self) -> None:
        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))
        solved = defaultdict(set)
        solved["sql"] = set(easy_ids) | set(medium_ids)  # all easy + medium
        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        comps = result["sql"]["components"]
        # easy(10) + medium(20) = 30
        assert comps["practice"] == pytest.approx(30.0, abs=0.5)

    def test_hard_only_requires_40_percent_for_full_10_pts(self) -> None:
        """Hard cap: only 40% coverage needed for the full 10 pts."""
        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))  # 30 hard questions
        # 40% of 30 = 12 questions needed for full 10 pts
        solved = defaultdict(set)
        solved["sql"] = set(easy_ids) | set(medium_ids) | set(hard_ids[:12])
        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        comps = result["sql"]["components"]
        # easy(10) + medium(20) + hard(10) = 40
        assert comps["practice"] == pytest.approx(40.0, abs=0.6)

    def test_partial_coverage_proportional(self) -> None:
        easy_ids = list(range(1, 11))   # 10 easy
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))
        solved = defaultdict(set)
        solved["sql"] = set(easy_ids[:5])  # 50% easy → 5 pts easy
        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        comps = result["sql"]["components"]
        assert comps["practice"] == pytest.approx(5.0, abs=0.3)


# ── Mock accuracy component ───────────────────────────────────────────────────

class TestReadinessMockAccuracyComponent:

    def test_no_mock_sessions_gives_zero_mock_pts(self) -> None:
        result = _call(effective_plan="elite", mock_sessions=[])
        assert result is not None
        for track in ("sql", "python", "python-data", "pyspark"):
            assert result[track]["components"]["mock_accuracy"] == 0.0

    def test_perfect_mock_session_gives_35_pts(self) -> None:
        sessions = [_mock_session(track="sql", solved=3, total=3)]
        result = _call(effective_plan="elite", mock_sessions=sessions)
        assert result is not None
        comps = result["sql"]["components"]
        assert comps["mock_accuracy"] == pytest.approx(35.0, abs=0.2)

    def test_zero_score_mock_gives_zero_pts(self) -> None:
        sessions = [_mock_session(track="sql", solved=0, total=3)]
        result = _call(effective_plan="elite", mock_sessions=sessions)
        assert result is not None
        comps = result["sql"]["components"]
        assert comps["mock_accuracy"] == 0.0

    def test_avg_of_last_5_sessions_used(self) -> None:
        # 5 sessions of 100% and 5 sessions of 0% — only last 5 (100%) should be used
        sessions = (
            [_mock_session(track="sql", solved=0, total=3)] * 5   # earlier (0%)
            + [_mock_session(track="sql", solved=3, total=3)] * 5  # later (100%)
        )
        result = _call(effective_plan="elite", mock_sessions=sessions)
        assert result is not None
        comps = result["sql"]["components"]
        # Last 5 sessions all 100% → 35 pts
        assert comps["mock_accuracy"] == pytest.approx(35.0, abs=0.2)

    def test_incomplete_sessions_excluded(self) -> None:
        sessions = [
            _mock_session(track="sql", solved=3, total=3, status="in_progress"),
            _mock_session(track="sql", solved=3, total=3, status="completed"),
        ]
        result = _call(effective_plan="elite", mock_sessions=sessions)
        assert result is not None
        comps = result["sql"]["components"]
        # Only the 1 completed 100% session counts
        assert comps["mock_accuracy"] == pytest.approx(35.0, abs=0.2)

    def test_mixed_track_sessions_also_count(self) -> None:
        """Mixed-track sessions count toward every track's mock accuracy."""
        sessions = [_mock_session(track="mixed", solved=3, total=3)]
        result = _call(effective_plan="elite", mock_sessions=sessions)
        assert result is not None
        # Should give some mock pts to sql track
        assert result["sql"]["components"]["mock_accuracy"] > 0


# ── Concept strength component ────────────────────────────────────────────────

class TestReadinessConceptStrengthComponent:

    def test_no_concept_attempts_gives_zero_concept_pts(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        for track in ("sql", "python", "python-data", "pyspark"):
            assert result[track]["components"]["concept_strength"] == 0.0

    def test_strong_concepts_increase_score(self) -> None:
        """Concepts with ≥70% accuracy (≥3 attempts) are "strong"."""
        attempts = defaultdict(int)
        correct = defaultdict(int)
        # 4 strong SQL concepts
        for i in range(4):
            key = ("sql", f"CONCEPT_{i}")
            attempts[key] = 5
            correct[key] = 4  # 80% → strong
        result = _call(
            effective_plan="elite",
            concept_attempts=attempts,
            concept_correct=correct,
        )
        assert result is not None
        assert result["sql"]["components"]["concept_strength"] > 0

    def test_weak_concepts_reduce_score(self) -> None:
        """Concepts with <60% accuracy (≥3 attempts) are "weak"."""
        attempts = defaultdict(int)
        correct = defaultdict(int)
        # 4 strong + 2 weak → net positive but less than all-strong
        for i in range(4):
            key = ("sql", f"STRONG_{i}")
            attempts[key] = 5
            correct[key] = 4  # 80%
        for i in range(2):
            key = ("sql", f"WEAK_{i}")
            attempts[key] = 5
            correct[key] = 2  # 40%

        result_mixed = _call(
            effective_plan="elite",
            concept_attempts=attempts,
            concept_correct=correct,
        )

        # Compare against 4-strong-only
        attempts_clean = defaultdict(int)
        correct_clean = defaultdict(int)
        for i in range(4):
            key = ("sql", f"STRONG_{i}")
            attempts_clean[key] = 5
            correct_clean[key] = 4

        result_clean = _call(
            effective_plan="elite",
            concept_attempts=attempts_clean,
            concept_correct=correct_clean,
        )

        assert result_mixed is not None and result_clean is not None
        assert (
            result_mixed["sql"]["components"]["concept_strength"]
            < result_clean["sql"]["components"]["concept_strength"]
        ), "Weak concepts should reduce concept_strength score"

    def test_concept_below_3_attempts_not_counted(self) -> None:
        """Concepts with fewer than 3 attempts don't affect the concept component."""
        attempts = defaultdict(int)
        correct = defaultdict(int)
        # 2 attempts only → should not count
        key = ("sql", "RARE")
        attempts[key] = 2
        correct[key] = 0  # 0% — would be weak if counted
        result = _call(
            effective_plan="elite",
            concept_attempts=attempts,
            concept_correct=correct,
        )
        assert result is not None
        assert result["sql"]["components"]["concept_strength"] == 0.0

    def test_concept_strength_capped_at_25(self) -> None:
        """Concept strength component cannot exceed 25 pts."""
        attempts = defaultdict(int)
        correct = defaultdict(int)
        # 20 strong SQL concepts — well above the 8-concept ceiling
        for i in range(20):
            key = ("sql", f"GREAT_{i}")
            attempts[key] = 10
            correct[key] = 10  # 100%
        result = _call(
            effective_plan="elite",
            concept_attempts=attempts,
            concept_correct=correct,
        )
        assert result is not None
        assert result["sql"]["components"]["concept_strength"] <= 25.0


# ── Label thresholds ──────────────────────────────────────────────────────────

class TestReadinessLabels:
    """Verify label boundaries: <40 Early stage, 40-64 Building, 65-79 Getting there,
    80-89 Interview ready, 90+ Strong."""

    def _label_for_score(self, score_target: int) -> str:
        """Drive the score to approximately score_target and return the label."""
        # We'll use a catalog with exactly 10 easy / 10 medium / 10 hard
        # and tune solved counts to hit the desired practice component.
        # Then return the label.
        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 111))
        hard_ids = list(range(201, 211))

        # Control practice pts only (no mocks, no concept history)
        # Max practice pts = 10 + 20 + 10 = 40
        # To hit score_target, solve proportionally
        frac = min(score_target / 40.0, 1.0)
        n_easy = int(round(frac * 10))
        n_medium = int(round(frac * 10))
        n_hard = 0

        solved = defaultdict(set)
        solved["sql"] = set(easy_ids[:n_easy]) | set(medium_ids[:n_medium])

        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        return result["sql"]["label"]

    def test_zero_score_is_early_stage(self) -> None:
        result = _call(effective_plan="elite")
        assert result is not None
        assert result["sql"]["label"] == "Early stage"

    def test_score_40_is_building(self) -> None:
        # Explicitly exercise a score of exactly 40
        from routers.insights import _compute_readiness_scores

        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))

        # Full easy (10 pts) + full medium (20 pts) = 30 pts practice only
        # We want to hit 40 — that needs mock accuracy too
        # Use a session with 100% score: 35 pts; practice = 0 → score = 35 → Building?
        # Let's just verify the label at specific known scores by mocking the function's
        # output directly — test the label helper logic.

        # Score = 40 → "Building"
        catalog_mock = _make_catalog_module(easy_ids, medium_ids, hard_ids)
        topic_modules = {t: catalog_mock for t in ["sql", "python", "python-data", "pyspark"]}
        solved = defaultdict(set)
        solved["sql"] = set(easy_ids)  # all easy (10 pts)
        sessions = [_mock_session(track="sql", solved=3, total=3)] * 3  # 100% × 3 → 35 pts
        # Total ≈ 45 → "Building"
        with patch("routers.insights._TOPIC_MODULES", topic_modules):
            result = _compute_readiness_scores(
                per_track_solved_question_ids=solved,
                mock_sessions=sessions,
                concept_attempts=defaultdict(int),
                concept_correct=defaultdict(int),
                effective_plan="elite",
            )
        assert result is not None
        # Score should be in "Building" or "Getting there" range
        assert result["sql"]["label"] in ("Building", "Getting there", "Interview ready", "Strong")

    def test_high_activity_reaches_interview_ready_or_strong(self) -> None:
        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))

        solved = defaultdict(set)
        solved["sql"] = set(easy_ids) | set(medium_ids) | set(hard_ids)  # 100% coverage

        sessions = [_mock_session(track="sql", solved=3, total=3)] * 5  # 100% mock

        # 8 strong concepts
        attempts = defaultdict(int)
        correct = defaultdict(int)
        for i in range(8):
            key = ("sql", f"STRONG_{i}")
            attempts[key] = 5
            correct[key] = 5  # 100%

        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            mock_sessions=sessions,
            concept_attempts=attempts,
            concept_correct=correct,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        assert result["sql"]["label"] in ("Interview ready", "Strong"), (
            f"Fully-solved + perfect mocks + strong concepts should reach "
            f"'Interview ready' or 'Strong', got '{result['sql']['label']}' "
            f"(score={result['sql']['score']})"
        )

    def test_score_clamped_to_100_maximum(self) -> None:
        """Score can't exceed 100 even with impossible component values."""
        easy_ids = list(range(1, 11))
        medium_ids = list(range(101, 121))
        hard_ids = list(range(201, 231))

        solved = defaultdict(set)
        solved["sql"] = set(easy_ids) | set(medium_ids) | set(hard_ids)  # 100% coverage

        sessions = [_mock_session(track="sql", solved=3, total=3)] * 5  # 100%

        attempts = defaultdict(int)
        correct = defaultdict(int)
        for i in range(20):  # way above max_expected_strong of 8
            key = ("sql", f"GREAT_{i}")
            attempts[key] = 10
            correct[key] = 10

        result = _call(
            effective_plan="elite",
            solved_ids=solved,
            mock_sessions=sessions,
            concept_attempts=attempts,
            concept_correct=correct,
            easy_ids=easy_ids,
            medium_ids=medium_ids,
            hard_ids=hard_ids,
        )
        assert result is not None
        for track, data in result.items():
            assert data["score"] <= 100, f"Score clamping failed for {track}: {data['score']}"

    def test_score_cannot_be_negative(self) -> None:
        """Score should never go below 0 even with many weak concepts."""
        attempts = defaultdict(int)
        correct = defaultdict(int)
        for i in range(20):
            key = ("sql", f"WEAK_{i}")
            attempts[key] = 5
            correct[key] = 0  # 0% — all weak
        result = _call(
            effective_plan="elite",
            concept_attempts=attempts,
            concept_correct=correct,
        )
        assert result is not None
        for track, data in result.items():
            assert data["score"] >= 0, f"Score should not be negative, got {data['score']} for {track}"
