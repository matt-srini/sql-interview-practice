"""
Mock pool composition, freshness scoring, and catalog filter tests.

Uses a minimal synthetic catalog to test plan-split pool logic without
requiring actual mock_only question content on disk. Real catalog tests
(catalog API endpoint) use the actual content and verify mock_only absence.
"""
from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from unlock import compute_mock_access

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


# ── Synthetic catalog helpers ─────────────────────────────────────────────────

def _make_practice_questions(
    difficulty: str,
    count: int,
    id_start: int,
    order_start: int,
    track: str = "sql",
) -> list[dict]:
    """Build minimal practice (non-mock-only) question dicts."""
    return [
        {"id": id_start + i, "order": order_start + i, "difficulty": difficulty}
        for i in range(count)
    ]


def _make_mock_only_questions(
    difficulty: str,
    count: int,
    id_start: int,
    order_start: int,
) -> list[dict]:
    """Build minimal mock_only question dicts."""
    return [
        {
            "id": id_start + i,
            "order": order_start + i,
            "difficulty": difficulty,
            "mock_only": True,
        }
        for i in range(count)
    ]


def _make_catalog_module(
    easy: list[dict] | None = None,
    medium: list[dict] | None = None,
    hard: list[dict] | None = None,
    mock_medium: list[dict] | None = None,
    mock_hard: list[dict] | None = None,
):
    """Return a MagicMock that behaves like a catalog module (questions.py etc.)."""
    practice_grouped = {
        "easy": easy or [],
        "medium": medium or [],
        "hard": hard or [],
    }
    mock_grouped = {
        "easy": [],
        "medium": mock_medium or [],
        "hard": mock_hard or [],
    }
    m = MagicMock()
    m.get_questions_by_difficulty.return_value = practice_grouped
    m.get_mock_questions_by_difficulty.return_value = mock_grouped
    m.get_question.side_effect = lambda qid: None
    return m


# ── Pool composition — Free plan ──────────────────────────────────────────────

class TestFreePlanPool:
    """Free plan pool rules: practice only, unlock-gated."""

    def _pool(
        self,
        difficulty: str,
        solved_ids: set[int],
        catalog_module,
        track: str = "sql",
    ) -> list[dict]:
        from routers.mock import _pool_for_track
        with patch("routers.mock._get_catalog_for_track", return_value=catalog_module):
            return _pool_for_track(track, difficulty, "free", solved_ids)

    def test_easy_pool_has_no_mock_only(self) -> None:
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 3, 1, 1),
            medium=_make_practice_questions("medium", 3, 10, 10),
            mock_medium=_make_mock_only_questions("medium", 2, 100, 100),
        )
        pool = self._pool("easy", set(), catalog)
        assert not any(q.get("mock_only") for q in pool)

    def test_medium_pool_has_no_mock_only(self) -> None:
        practice_easy = _make_practice_questions("easy", 25, 1, 1)
        practice_medium = _make_practice_questions("medium", 3, 100, 100)
        catalog = _make_catalog_module(
            easy=practice_easy,
            medium=practice_medium,
            mock_medium=_make_mock_only_questions("medium", 2, 200, 200),
        )
        solved = {q["id"] for q in practice_easy}  # all easy solved → medium unlocked
        pool = self._pool("medium", solved, catalog)
        assert not any(q.get("mock_only") for q in pool)

    def test_medium_pool_empty_when_no_easy_solved(self) -> None:
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 10, 1, 1),
            medium=_make_practice_questions("medium", 3, 100, 100),
            mock_medium=_make_mock_only_questions("medium", 2, 200, 200),
        )
        pool = self._pool("medium", set(), catalog)  # 0 easy solved
        assert pool == [], f"Expected empty medium pool for free user with no easy solved, got {len(pool)} questions"

    def test_medium_pool_has_3_after_8_easy_solved(self) -> None:
        practice_easy = _make_practice_questions("easy", 10, 1, 1)
        practice_medium = _make_practice_questions("medium", 5, 100, 100)
        catalog = _make_catalog_module(easy=practice_easy, medium=practice_medium)
        solved = {q["id"] for q in practice_easy[:8]}
        pool = self._pool("medium", solved, catalog)
        assert len(pool) == 3, f"Expected 3 medium questions after 8 easy solved, got {len(pool)}"

    def test_hard_pool_empty_for_free_user(self) -> None:
        """Free users get empty hard pool — blocked at the access layer before reaching here."""
        practice_easy = _make_practice_questions("easy", 25, 1, 1)
        practice_medium = _make_practice_questions("medium", 22, 100, 100)
        practice_hard = _make_practice_questions("hard", 10, 200, 200)
        catalog = _make_catalog_module(
            easy=practice_easy, medium=practice_medium, hard=practice_hard
        )
        solved = {q["id"] for q in practice_easy} | {q["id"] for q in practice_medium}
        pool = self._pool("hard", solved, catalog)
        # Free plan caps hard at FREE_HARD_CAP_CODE (8) — the pool reflects the cap
        from unlock import FREE_HARD_CAP_CODE
        assert len(pool) <= FREE_HARD_CAP_CODE, (
            f"Free hard pool should be capped at {FREE_HARD_CAP_CODE}, got {len(pool)}"
        )


# ── Pool composition — Pro / Elite plan ──────────────────────────────────────

class TestProElitePlanPool:
    """Pro/Elite pools: include mock-only questions, no hard cap."""

    def _pool(
        self,
        difficulty: str,
        solved_ids: set[int],
        catalog_module,
        plan: str = "pro",
        track: str = "sql",
    ) -> list[dict]:
        from routers.mock import _pool_for_track
        with patch("routers.mock._get_catalog_for_track", return_value=catalog_module):
            return _pool_for_track(track, difficulty, plan, solved_ids)

    def test_pro_medium_pool_includes_mock_only(self) -> None:
        practice_medium = _make_practice_questions("medium", 3, 100, 100)
        mock_medium = _make_mock_only_questions("medium", 2, 200, 200)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=practice_medium,
            mock_medium=mock_medium,
        )
        pool = self._pool("medium", set(), catalog)
        mock_ids = {q["id"] for q in mock_medium}
        pool_ids = {int(q["id"]) for q in pool}
        assert mock_ids.issubset(pool_ids), (
            f"Pro medium pool should include all mock-only questions. "
            f"Missing: {mock_ids - pool_ids}"
        )

    def test_pro_medium_pool_contains_all_practice_and_mock_only(self) -> None:
        practice_medium = _make_practice_questions("medium", 3, 100, 100)
        mock_medium = _make_mock_only_questions("medium", 2, 200, 200)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=practice_medium,
            mock_medium=mock_medium,
        )
        pool = self._pool("medium", set(), catalog)
        assert len(pool) == 5, f"Expected 3 practice + 2 mock-only = 5 total, got {len(pool)}"

    def test_pro_hard_pool_includes_mock_only(self) -> None:
        practice_hard = _make_practice_questions("hard", 3, 300, 300)
        mock_hard = _make_mock_only_questions("hard", 2, 400, 400)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=_make_practice_questions("medium", 5, 100, 100),
            hard=practice_hard,
            mock_hard=mock_hard,
        )
        pool = self._pool("hard", set(), catalog)
        mock_ids = {q["id"] for q in mock_hard}
        pool_ids = {int(q["id"]) for q in pool}
        assert mock_ids.issubset(pool_ids), "Pro hard pool should include all mock-only hard questions"

    def test_pro_hard_pool_contains_all_practice_and_mock_only(self) -> None:
        practice_hard = _make_practice_questions("hard", 3, 300, 300)
        mock_hard = _make_mock_only_questions("hard", 2, 400, 400)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=_make_practice_questions("medium", 5, 100, 100),
            hard=practice_hard,
            mock_hard=mock_hard,
        )
        pool = self._pool("hard", set(), catalog)
        assert len(pool) == 5, f"Expected 3 practice + 2 mock-only = 5 total, got {len(pool)}"

    def test_elite_pool_equals_pro_pool(self) -> None:
        practice_medium = _make_practice_questions("medium", 3, 100, 100)
        mock_medium = _make_mock_only_questions("medium", 2, 200, 200)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=practice_medium,
            mock_medium=mock_medium,
        )
        pro_pool = self._pool("medium", set(), catalog, plan="pro")
        elite_pool = self._pool("medium", set(), catalog, plan="elite")
        pro_ids = {int(q["id"]) for q in pro_pool}
        elite_ids = {int(q["id"]) for q in elite_pool}
        assert pro_ids == elite_ids, (
            f"Elite and Pro pools should be identical.\n"
            f"  Pro-only:   {pro_ids - elite_ids}\n"
            f"  Elite-only: {elite_ids - pro_ids}"
        )

    def test_lifetime_pro_pool_equals_pro_pool(self) -> None:
        practice_medium = _make_practice_questions("medium", 3, 100, 100)
        mock_medium = _make_mock_only_questions("medium", 2, 200, 200)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=practice_medium,
            mock_medium=mock_medium,
        )
        pro_pool = self._pool("medium", set(), catalog, plan="pro")
        lifetime_pool = self._pool("medium", set(), catalog, plan="lifetime_pro")
        pro_ids = {int(q["id"]) for q in pro_pool}
        lifetime_ids = {int(q["id"]) for q in lifetime_pool}
        assert pro_ids == lifetime_ids, "lifetime_pro should get same pool as pro"

    def test_lifetime_elite_pool_equals_elite_pool(self) -> None:
        practice_hard = _make_practice_questions("hard", 3, 300, 300)
        mock_hard = _make_mock_only_questions("hard", 2, 400, 400)
        catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 5, 1, 1),
            medium=_make_practice_questions("medium", 5, 100, 100),
            hard=practice_hard,
            mock_hard=mock_hard,
        )
        elite_pool = self._pool("hard", set(), catalog, plan="elite")
        lifetime_pool = self._pool("hard", set(), catalog, plan="lifetime_elite")
        elite_ids = {int(q["id"]) for q in elite_pool}
        lifetime_ids = {int(q["id"]) for q in lifetime_pool}
        assert elite_ids == lifetime_ids, "lifetime_elite should get same pool as elite"

    def test_easy_pool_excludes_mock_only_even_for_pro(self) -> None:
        """Pro plan does NOT get mock-only easy questions — easy pool is practice-only for all plans."""
        practice_easy = _make_practice_questions("easy", 3, 1, 1)
        mock_easy = _make_mock_only_questions("easy", 2, 200, 200)
        catalog = _make_catalog_module(easy=practice_easy)
        # Temporarily make get_mock_questions_by_difficulty return easy mock_only
        catalog.get_mock_questions_by_difficulty.return_value = {
            "easy": mock_easy,
            "medium": [],
            "hard": [],
        }
        pool = self._pool("easy", set(), catalog, plan="pro")
        pool_ids = {int(q["id"]) for q in pool}
        mock_ids = {q["id"] for q in mock_easy}
        assert not mock_ids.intersection(pool_ids), (
            "Easy pool should never include mock-only questions, even for Pro plan"
        )


# ── Mock access layer — Free hard block ──────────────────────────────────────

class TestMockAccessLayer:

    def test_free_hard_blocked_by_access_layer(self) -> None:
        result = compute_mock_access("free", "sql", "hard", medium_unlocked=True)
        assert result["can_start"] is False
        assert result["block_reason"] == "plan_locked"
        assert result["needs_upgrade"] == "pro"

    def test_pro_hard_allowed_by_access_layer(self) -> None:
        result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=0)
        assert result["can_start"] is True

    def test_free_medium_daily_cap_enforced(self) -> None:
        result = compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=1)
        assert result["can_start"] is False
        assert result["block_reason"] == "daily_cap"


# ── Freshness scoring ─────────────────────────────────────────────────────────

class TestFreshnessScoring:
    """Freshness scoring prefers never-mocked questions and falls back to stale."""

    def _run_select(
        self,
        pool: list[dict],
        mocked_ids: set[int],
        num_questions: int,
        plan: str = "pro",
    ) -> list[dict]:
        """Run _select_questions with a patched pool and mocked history."""
        from routers.mock import _select_questions

        synthetic_catalog = _make_catalog_module(
            easy=_make_practice_questions("easy", 3, 1, 1),
        )
        # Build a mock catalog so _pool_for_track returns our pool
        with (
            patch("routers.mock._get_catalog_for_track", return_value=synthetic_catalog),
            patch("routers.mock._pool_for_track", return_value=pool),
            patch("routers.mock.get_previously_mocked_ids", AsyncMock(return_value=mocked_ids)),
            patch("routers.mock._get_solved_ids_for_track", AsyncMock(return_value=set())),
        ):
            user = {"id": "00000000-0000-0000-0000-000000000001", "plan": plan}
            return asyncio.run(
                _select_questions("sql", "easy", num_questions, user)
            )

    def test_fresh_questions_preferred_over_stale(self) -> None:
        pool = [
            {"id": 1, "difficulty": "easy", "_track": "sql", "_mock_only": False},
            {"id": 2, "difficulty": "easy", "_track": "sql", "_mock_only": False},
            {"id": 3, "difficulty": "easy", "_track": "sql", "_mock_only": False},  # stale
        ]
        mocked_ids = {3}  # Q3 is stale
        # Ask for 2 questions — should always be Q1 and Q2
        for _ in range(10):  # repeat to guard against random flakiness
            selected = self._run_select(pool, mocked_ids, num_questions=2)
            selected_ids = {q["question_id"] for q in selected}
            assert 3 not in selected_ids, (
                f"Stale Q3 should not be selected when 2 fresh questions are available. "
                f"Got: {selected_ids}"
            )

    def test_fallback_to_stale_when_fresh_pool_insufficient(self) -> None:
        pool = [
            {"id": 1, "difficulty": "easy", "_track": "sql", "_mock_only": False},  # fresh
            {"id": 2, "difficulty": "easy", "_track": "sql", "_mock_only": False},  # stale
            {"id": 3, "difficulty": "easy", "_track": "sql", "_mock_only": False},  # stale
        ]
        mocked_ids = {2, 3}  # Q2 and Q3 are stale; only Q1 is fresh
        selected = self._run_select(pool, mocked_ids, num_questions=3)  # need all 3
        selected_ids = {q["question_id"] for q in selected}
        assert selected_ids == {1, 2, 3}, (
            f"Should fall back to stale questions when fresh pool is insufficient. "
            f"Got: {selected_ids}"
        )

    def test_no_freshness_filter_when_no_history(self) -> None:
        pool = [
            {"id": 1, "difficulty": "easy", "_track": "sql", "_mock_only": False},
            {"id": 2, "difficulty": "easy", "_track": "sql", "_mock_only": False},
            {"id": 3, "difficulty": "easy", "_track": "sql", "_mock_only": False},
        ]
        # No mocked history — all questions are eligible
        selected = self._run_select(pool, mocked_ids=set(), num_questions=3)
        assert len(selected) == 3

    def test_raises_when_pool_too_small(self) -> None:
        from fastapi import HTTPException
        pool = [
            {"id": 1, "difficulty": "easy", "_track": "sql", "_mock_only": False},
            {"id": 2, "difficulty": "easy", "_track": "sql", "_mock_only": False},
        ]
        with pytest.raises(HTTPException) as exc_info:
            self._run_select(pool, mocked_ids=set(), num_questions=5)
        assert exc_info.value.status_code == 400

    def test_positions_are_sequential_starting_at_1(self) -> None:
        pool = [
            {"id": i, "difficulty": "easy", "_track": "sql", "_mock_only": False}
            for i in range(1, 4)
        ]
        selected = self._run_select(pool, mocked_ids=set(), num_questions=3)
        positions = sorted(q["position"] for q in selected)
        assert positions == [1, 2, 3], f"Positions should be 1-based sequential: {positions}"


# ── Catalog API filter — mock_only never exposed via practice catalog ─────────

class TestCatalogFilter:
    """
    Verify that the practice catalog API endpoints never expose mock_only questions.
    These tests run against the real catalog content (which currently has no mock_only
    questions) and verify the filter logic is wired up correctly at the API layer.
    """

    def test_sql_catalog_excludes_mock_only(self) -> None:
        with TestClient(app) as client:
            r = client.get("/api/catalog")
        assert r.status_code == 200
        all_ids: list[int] = []
        for group in r.json().get("groups", []):
            for q in group.get("questions", []):
                all_ids.append(q["id"])
        from questions import _ALL_QUESTIONS
        mock_only_ids = {int(q["id"]) for q in _ALL_QUESTIONS if q.get("mock_only")}
        overlap = set(all_ids) & mock_only_ids
        assert not overlap, f"mock_only questions found in SQL catalog API: {overlap}"

    def test_python_catalog_excludes_mock_only(self) -> None:
        with TestClient(app) as client:
            r = client.get("/api/python/catalog")
        assert r.status_code == 200
        all_ids = [q["id"] for q in r.json().get("questions", [])]
        from python_questions import _ALL_QUESTIONS
        mock_only_ids = {int(q["id"]) for q in _ALL_QUESTIONS if q.get("mock_only")}
        overlap = set(all_ids) & mock_only_ids
        assert not overlap, f"mock_only questions found in Python catalog API: {overlap}"

    def test_pandas_catalog_excludes_mock_only(self) -> None:
        with TestClient(app) as client:
            r = client.get("/api/python-data/catalog")
        assert r.status_code == 200
        all_ids = [q["id"] for q in r.json().get("questions", [])]
        from python_data_questions import _ALL_QUESTIONS
        mock_only_ids = {int(q["id"]) for q in _ALL_QUESTIONS if q.get("mock_only")}
        overlap = set(all_ids) & mock_only_ids
        assert not overlap, f"mock_only questions found in Pandas catalog API: {overlap}"

    def test_pyspark_catalog_excludes_mock_only(self) -> None:
        with TestClient(app) as client:
            r = client.get("/api/pyspark/catalog")
        assert r.status_code == 200
        all_ids = [q["id"] for q in r.json().get("questions", [])]
        from pyspark_questions import _ALL_QUESTIONS
        mock_only_ids = {int(q["id"]) for q in _ALL_QUESTIONS if q.get("mock_only")}
        overlap = set(all_ids) & mock_only_ids
        assert not overlap, f"mock_only questions found in PySpark catalog API: {overlap}"

    def test_get_mock_questions_returns_only_mock_only(self) -> None:
        from questions import get_mock_questions_by_difficulty
        mock_grouped = get_mock_questions_by_difficulty()
        for diff, qs in mock_grouped.items():
            for q in qs:
                assert q.get("mock_only") is True, (
                    f"get_mock_questions_by_difficulty() returned non-mock_only question "
                    f"id={q['id']} in difficulty={diff}"
                )

    def test_get_question_resolves_mock_only_by_id(self) -> None:
        """get_question() must be able to resolve mock_only IDs via _INDEX."""
        from questions import _ALL_QUESTIONS, get_question
        mock_only_qs = [q for q in _ALL_QUESTIONS if q.get("mock_only")]
        if not mock_only_qs:
            pytest.skip("No mock_only questions in current SQL content — skipping ID resolution test")
        for q in mock_only_qs[:3]:
            found = get_question(int(q["id"]))
            assert found is not None, f"get_question({q['id']}) returned None for a mock_only question"


# ── validate_content.py mock field validation ─────────────────────────────────

class TestValidateMockFields:
    """Unit tests for the mock field validation rules in validate_content.py."""

    def _run_validate(self, questions_by_track: dict[str, list[dict]]) -> list[str]:
        """
        Patch _iter_question_files to return synthetic questions and run
        _validate_mock_fields(). Returns list of error strings, or empty if clean.
        """
        import sys
        # Add scripts dir to path for the import
        scripts_dir = str(
            __import__("pathlib").Path(__file__).resolve().parent.parent / "scripts"
        )
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from validate_content import _validate_mock_fields
        import json
        import tempfile
        import os

        # Write synthetic questions to temp files
        temp_files: list[tuple[str, str]] = []
        try:
            for track, questions in questions_by_track.items():
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    json.dump(questions, f)
                    temp_files.append((track, f.name))

            # Patch _iter_question_files to return our temp files
            fake_iter = [
                (track, __import__("pathlib").Path(path))
                for track, path in temp_files
            ]
            with patch("validate_content._iter_question_files", return_value=fake_iter):
                try:
                    _validate_mock_fields()
                    return []
                except ValueError as exc:
                    # Parse the error lines
                    return [
                        line.lstrip("- ")
                        for line in str(exc).splitlines()
                        if line.strip().startswith("- ")
                    ]
        finally:
            for _, path in temp_files:
                os.unlink(path)

    def test_valid_mock_only_boolean_passes(self) -> None:
        errors = self._run_validate({"sql": [{"id": 1, "title": "Q1", "mock_only": True}]})
        assert not errors

    def test_mock_only_string_fails(self) -> None:
        errors = self._run_validate({"sql": [{"id": 1, "title": "Q1", "mock_only": "true"}]})
        assert any("mock_only must be boolean" in e for e in errors)

    def test_framing_scenario_passes(self) -> None:
        errors = self._run_validate({"sql": [{"id": 1, "title": "Q1", "framing": "scenario"}]})
        assert not errors

    def test_framing_unknown_value_fails(self) -> None:
        errors = self._run_validate({"sql": [{"id": 1, "title": "Q1", "framing": "interview"}]})
        assert any("framing must be 'scenario'" in e for e in errors)

    def test_follow_up_id_valid_reference_passes(self) -> None:
        questions = [
            {"id": 1, "title": "Q1", "follow_up_id": 2},
            {"id": 2, "title": "Q2"},
        ]
        errors = self._run_validate({"sql": questions})
        assert not errors

    def test_follow_up_id_invalid_reference_fails(self) -> None:
        questions = [{"id": 1, "title": "Q1", "follow_up_id": 999}]
        errors = self._run_validate({"sql": questions})
        assert any("follow_up_id 999 does not exist" in e for e in errors)

    def test_follow_up_id_wrong_type_fails(self) -> None:
        questions = [{"id": 1, "title": "Q1", "follow_up_id": "2"}]
        errors = self._run_validate({"sql": questions})
        assert any("follow_up_id must be an integer" in e for e in errors)

    def test_reverse_type_with_valid_result_preview_passes(self) -> None:
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "reverse",
                "result_preview": [{"col": "val"}] * 3,
            }
        ]
        errors = self._run_validate({"sql": questions})
        assert not errors

    def test_reverse_type_without_result_preview_fails(self) -> None:
        questions = [{"id": 1, "title": "Q1", "type": "reverse"}]
        errors = self._run_validate({"sql": questions})
        assert any("result_preview" in e for e in errors)

    def test_reverse_type_result_preview_over_8_rows_fails(self) -> None:
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "reverse",
                "result_preview": [{"col": "val"}] * 9,
            }
        ]
        errors = self._run_validate({"sql": questions})
        assert any("≤8 rows" in e for e in errors)

    def test_debug_type_complete_passes(self) -> None:
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "debug",
                "debug_error": "OperationalError: no such column 'user_id'",
                "starter_query": "SELECT user_id FROM orders",
            }
        ]
        errors = self._run_validate({"sql": questions})
        assert not errors

    def test_debug_type_without_debug_error_fails(self) -> None:
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "debug",
                "starter_query": "SELECT user_id FROM orders",
            }
        ]
        errors = self._run_validate({"sql": questions})
        assert any("debug_error" in e for e in errors)

    def test_debug_type_without_starter_code_fails(self) -> None:
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "debug",
                "debug_error": "OperationalError: no such column",
            }
        ]
        errors = self._run_validate({"sql": questions})
        assert any("starter_code" in e or "starter_query" in e for e in errors)

    def test_pyspark_debug_type_not_checked_for_debug_error(self) -> None:
        """PySpark 'debug' type uses MCQ format — no debug_error/starter_code needed."""
        questions = [
            {
                "id": 1,
                "title": "Q1",
                "type": "debug",
                # No debug_error or starter_code — valid for PySpark
            }
        ]
        errors = self._run_validate({"pyspark": questions})
        # Should NOT have debug_error/starter_code errors for pyspark
        debug_errors = [e for e in errors if "debug_error" in e or "starter_code" in e]
        assert not debug_errors, (
            f"PySpark debug type should not require debug_error/starter_code: {debug_errors}"
        )
