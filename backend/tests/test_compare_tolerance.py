"""The grading comparator honors a test case's declared numeric `tolerance` (for
statistics Monte-Carlo / numerical-method answers) with a 1e-6 floor, and still
handles infinities, ordering, and exact matches. Phase-4 finding: `tolerance` was
authored on 30 statistics questions but ignored by `_compare`.
"""
import json
from pathlib import Path

import pytest

from python_sandbox_harness import _compare
from python_evaluator import evaluate_python_code

BACKEND = Path(__file__).resolve().parent.parent


# --- unit: _compare ---
def test_large_tolerance_accepts_within_range():
    assert _compare(0.9805, 0.9809, 0.02) is True       # within declared 0.02
    assert _compare(0.95, 0.9809, 0.02) is False         # outside it


def test_tolerance_never_stricter_than_1e6_floor():
    # A tighter declared tolerance must not break a value that the 1e-6 default accepts.
    assert _compare(1.0, 1.0 + 5e-7, 1e-9) is True
    # Genuinely different values still fail.
    assert _compare(1.0, 1.1, 1e-9) is False


def test_infinities_and_exact_match():
    assert _compare(float("inf"), float("inf"), 1e-6) is True           # scalar inf
    assert _compare([0, float("inf"), 5], [0, float("inf"), 5], 1e-6) is True  # list inf (Dijkstra)
    assert _compare([0, float("inf")], [0, 5], 1e-6) is False


def test_numeric_list_tolerance_both_orderings():
    assert _compare([1.0, 2.0, 3.0], [3.0, 2.0, 1.0], 1e-6) is True     # order-insensitive preserved
    assert _compare([1.0, 2.0000001], [1.0, 2.0], 0.001) is True        # element-wise tolerance


def test_default_tolerance_unchanged_for_non_tolerance_cases():
    assert _compare(5, 5, 1e-6) is True
    assert _compare([1, 2, 3], [1, 2, 3], 1e-6) is True
    assert _compare("a", "b", 1e-6) is False


# --- integration: tolerance survives the submit-path test-case expansion ---
def _load(qid, base):
    for diff in ("easy", "medium", "hard"):
        for q in json.loads((BACKEND / "content" / base / f"{diff}.json").read_text()):
            if q.get("id") == qid:
                return q
    raise AssertionError(f"{qid} not found")


def test_monte_carlo_question_grades_within_tolerance():
    # 73047: reference yields 0.9805 vs stored 0.9809 (within 0.02). Was ungradeable
    # before because _expand_test_case dropped tolerance + _compare used 1e-6.
    q = _load(73047, "statistics_questions")
    assert evaluate_python_code(q["expected_code"], q)["correct"] is True


def test_dijkstra_with_inf_still_grades():
    # 23058 returns inf for unreachable nodes — guards the regression the inf fix closed.
    q = _load(23058, "python_questions")
    assert evaluate_python_code(q["expected_code"], q)["correct"] is True
