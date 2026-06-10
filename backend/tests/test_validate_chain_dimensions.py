"""Tests for follow_up_dimension validation rules added to validate_content.py.

Three rule areas covered:
  1. canonical_dimension() normaliser — accept/reject cases (unit test, no file I/O).
  2. Full validator run on the real content bank — must pass with zero errors (guards that
     every canonical and alias-spelled dimension in the bank canonicalises, and that no
     chain has consecutive identical pivots).
  3. Focused synthetic-chain tests for the two new rules inside _validate_chain_integrity:
     - unknown dimension token → "not a canonical dimension" error
     - alias token (no _pivot suffix) → no dimension error
     - two consecutive follow-ups sharing the same canonical dimension → "consecutive pivots
       must differ" error
     - two consecutive follow-ups with DIFFERENT canonical dimensions → no error
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from follow_up_dimensions import CANONICAL_FOLLOW_UP_DIMENSIONS, canonical_dimension


# ──────────────────────────────────────────────────────────────────────────────
# 1. canonical_dimension() unit tests
# ──────────────────────────────────────────────────────────────────────────────


class TestCanonicalDimension:
    def test_canonical_tokens_resolve_to_themselves(self):
        for token in CANONICAL_FOLLOW_UP_DIMENSIONS:
            assert canonical_dimension(token) == token

    def test_alias_without_pivot_resolves_to_canonical(self):
        assert canonical_dimension("data_quality") == "data_quality_pivot"
        assert canonical_dimension("abstraction") == "abstraction_pivot"
        assert canonical_dimension("scale") == "scale_pivot"
        assert canonical_dimension("performance") == "performance_pivot"
        assert canonical_dimension("edge_case") == "edge_case_pivot"
        assert canonical_dimension("stakeholder") == "stakeholder_pivot"
        assert canonical_dimension("ambiguity") == "ambiguity_pivot"
        assert canonical_dimension("business_rule") == "business_rule_pivot"

    def test_garbage_token_returns_none(self):
        assert canonical_dimension("garbage_pivot") is None
        assert canonical_dimension("unknown") is None
        assert canonical_dimension("foobar_pivot") is None

    def test_empty_and_none_return_none(self):
        assert canonical_dimension(None) is None
        assert canonical_dimension("") is None

    def test_partial_match_not_accepted(self):
        # "scale_piv" is not canonical and not an alias
        assert canonical_dimension("scale_piv") is None


# ──────────────────────────────────────────────────────────────────────────────
# 2. Full validator run on real content — must pass (zero errors, exit 0)
# ──────────────────────────────────────────────────────────────────────────────


def test_full_validator_passes_on_real_content():
    """Running main() on the real bank must not raise."""
    import importlib
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "validate_content",
        BACKEND / "scripts" / "validate_content.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    # main() prints "Content validation passed" on success and raises on failure
    module.main()  # must not raise


# ──────────────────────────────────────────────────────────────────────────────
# 3. Synthetic chain tests for the two new rules
# ──────────────────────────────────────────────────────────────────────────────
#
# _validate_chain_integrity() reads from disk (via _iter_question_files), so we
# patch _iter_question_files and json.load to inject synthetic question dicts.


def _make_parent(qid: int, follow_ups: list[int]) -> dict:
    return {
        "id": qid,
        "title": f"Parent {qid}",
        "mock_only": True,
    } | ({"follow_ups": follow_ups} if follow_ups else {})


def _make_child(qid: int, parent_id: int, dimension: str) -> dict:
    return {
        "id": qid,
        "title": f"Child {qid}",
        "mock_only": True,
        "parent_id": parent_id,
        "follow_up_dimension": dimension,
    }


def _run_chain_validation_with(questions_hard: list[dict]) -> list[str]:
    """Run _validate_chain_integrity with only the supplied hard questions,
    returning collected errors (without raising)."""
    import importlib.util
    import types

    spec = importlib.util.spec_from_file_location(
        "validate_content_synth",
        BACKEND / "scripts" / "validate_content.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]

    # A synthetic track file list: one "hard" file for track "ml-fundamentals"
    fake_path = BACKEND / "content" / "ml_fundamentals_questions" / "hard.json"
    track = "ml-fundamentals"

    # Patch _iter_question_files to return only our synthetic file entry
    with patch.object(module, "_iter_question_files", return_value=[(track, fake_path)]):
        # Patch json.load to return our synthetic questions
        import json as _json_mod
        original_load = _json_mod.load

        def fake_load(fp, **kw):
            # Only intercept opens for our synthetic path
            try:
                name = fp.name
            except AttributeError:
                name = ""
            if "hard" in str(name) and "ml_fundamentals" in str(name):
                return questions_hard
            return original_load(fp, **kw)

        with patch("json.load", side_effect=fake_load):
            # Collect errors without raising by temporarily replacing raise
            errors_out: list[str] = []
            original_fn = module._validate_chain_integrity

            def capturing_validate():
                try:
                    original_fn()
                except ValueError as exc:
                    # Parse the error lines out of the message
                    for line in str(exc).splitlines():
                        if line.startswith("- "):
                            errors_out.append(line[2:])

            capturing_validate()

    return errors_out


class TestChainDimensionValidationRules:
    def test_unknown_dimension_produces_error(self):
        parent = _make_parent(99001, [99002])
        child = _make_child(99002, 99001, "garbage_pivot")
        errors = _run_chain_validation_with([parent, child])
        assert any("not a canonical dimension" in e for e in errors), errors

    def test_alias_dimension_produces_no_error(self):
        parent = _make_parent(99001, [99002])
        child = _make_child(99002, 99001, "data_quality")  # alias, no _pivot suffix
        errors = _run_chain_validation_with([parent, child])
        assert not any("not a canonical dimension" in e for e in errors), errors
        assert not any("follow_up_dimension" in e and "must have" in e for e in errors), errors

    def test_canonical_dimension_produces_no_error(self):
        parent = _make_parent(99001, [99002])
        child = _make_child(99002, 99001, "abstraction_pivot")
        errors = _run_chain_validation_with([parent, child])
        assert not any("not a canonical dimension" in e for e in errors), errors

    def test_consecutive_same_dimension_produces_error(self):
        parent = _make_parent(99001, [99002, 99003])
        child1 = _make_child(99002, 99001, "scale_pivot")
        child2 = _make_child(99003, 99001, "scale_pivot")
        errors = _run_chain_validation_with([parent, child1, child2])
        assert any("consecutive pivots must differ" in e for e in errors), errors

    def test_consecutive_different_dimensions_no_error(self):
        parent = _make_parent(99001, [99002, 99003])
        child1 = _make_child(99002, 99001, "scale_pivot")
        child2 = _make_child(99003, 99001, "performance_pivot")
        errors = _run_chain_validation_with([parent, child1, child2])
        assert not any("consecutive pivots must differ" in e for e in errors), errors

    def test_alias_then_canonical_same_family_triggers_consecutive_error(self):
        # "scale" alias + "scale_pivot" canonical both resolve to "scale_pivot"
        parent = _make_parent(99001, [99002, 99003])
        child1 = _make_child(99002, 99001, "scale")        # alias
        child2 = _make_child(99003, 99001, "scale_pivot")  # canonical
        errors = _run_chain_validation_with([parent, child1, child2])
        assert any("consecutive pivots must differ" in e for e in errors), errors
