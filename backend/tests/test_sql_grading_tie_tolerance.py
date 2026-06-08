"""Regression guard — SQL grading must tolerate ORDER BY ties without becoming
nondeterministic, while still rejecting genuinely misordered answers.

Background: the grader compares result rows positionally whenever the expected
query contains ORDER BY (so an unsorted answer to an ordered question is rejected).
That assumed the ORDER BY was a *total* order. When the sort key has ties, DuckDB
returns tied rows in unstable order, so a correct answer — including the reference
query graded against itself — was marked wrong a large fraction of the time. 18 SQL
practice/mock questions were affected (live user-facing false negatives).

Fix (evaluator.py): for order-sensitive questions, require the same row multiset AND
that the user's rows appear in the same sequence of ORDER BY *key* values as the
reference. Tied rows may appear in any internal order; genuine misorder still fails.

These tests pin both the unit behaviour of the comparison/parser and the end-to-end
determinism on the real affected questions.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

import database
from evaluator import _parse_order_by_columns, _results_match, evaluate

BACKEND = Path(__file__).resolve().parent.parent


def _df(rows, cols):
    return pd.DataFrame(rows, columns=cols)


# ---------------------------------------------------------------------------
# Unit: ORDER BY key parser
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("query,expected", [
    ("SELECT x FROM t ORDER BY x DESC", ["x"]),
    ("SELECT a,b FROM t ORDER BY month ASC, cnt DESC", ["month", "cnt"]),
    ("SELECT * FROM t ORDER BY d.department_name, e.salary DESC", ["department_name", "salary"]),
    # An upstream window ORDER BY must be ignored; the trailing one wins.
    ("SELECT ROW_NUMBER() OVER (ORDER BY ts) rn FROM t ORDER BY rn DESC", ["rn"]),
    # Expression / ordinal keys cannot map to an output column → bail to [].
    ("SELECT x, COUNT(*) c FROM t GROUP BY x ORDER BY COUNT(*) DESC", []),
    ("SELECT x FROM t ORDER BY 2 DESC", []),
    # Trailing LIMIT/OFFSET stripped.
    ("SELECT x FROM t ORDER BY freq DESC LIMIT 10", ["freq"]),
    ("SELECT x FROM t ORDER BY freq DESC LIMIT 10 OFFSET 5", ["freq"]),
    # No ORDER BY at all.
    ("SELECT x FROM t", []),
])
def test_parse_order_by_columns(query, expected):
    assert _parse_order_by_columns(query) == expected


# ---------------------------------------------------------------------------
# Unit: comparison semantics
# ---------------------------------------------------------------------------
def test_unordered_compares_as_multiset():
    e = _df([[1, "a"], [2, "b"]], ["x", "label"])
    u = _df([[2, "b"], [1, "a"]], ["x", "label"])  # different order, no ORDER BY
    assert _results_match(u, e, "SELECT x, label FROM t")


def test_ordered_tie_permutation_accepted():
    # ORDER BY x DESC; the two rows tied at x=5 may appear in either order.
    e = _df([[5, "a"], [5, "b"], [3, "c"]], ["x", "label"])
    u = _df([[5, "b"], [5, "a"], [3, "c"]], ["x", "label"])
    assert _results_match(u, e, "SELECT x, label FROM t ORDER BY x DESC")


def test_ordered_genuine_misorder_rejected():
    e = _df([[5, "a"], [3, "c"]], ["x", "label"])
    u = _df([[3, "c"], [5, "a"]], ["x", "label"])  # ascending — violates DESC
    assert not _results_match(u, e, "SELECT x, label FROM t ORDER BY x DESC")


def test_ordered_secondary_key_misorder_rejected():
    # ORDER BY x DESC, label ASC — ignoring the secondary key is wrong.
    e = _df([[5, "a"], [5, "b"], [3, "c"]], ["x", "label"])
    u = _df([[5, "b"], [5, "a"], [3, "c"]], ["x", "label"])  # label not ascending within x=5
    assert not _results_match(u, e, "SELECT x, label FROM t ORDER BY x DESC, label ASC")


def test_ordered_wrong_rows_rejected():
    e = _df([[5, "a"], [3, "c"]], ["x", "label"])
    u = _df([[5, "a"], [4, "c"]], ["x", "label"])  # wrong value
    assert not _results_match(u, e, "SELECT x, label FROM t ORDER BY x DESC")


def test_unordered_wrong_rows_rejected():
    e = _df([[1, "a"], [2, "b"]], ["x", "label"])
    u = _df([[1, "a"], [2, "z"]], ["x", "label"])
    assert not _results_match(u, e, "SELECT x, label FROM t")


# ---------------------------------------------------------------------------
# Integration: the real affected questions now grade deterministically
# ---------------------------------------------------------------------------
# 17 of the 18 originally-affected IDs. 13085 is excluded: its residual
# nondeterminism is a *different* defect (DuckDB parallel float-aggregation crossing
# a ROUND(,2) boundary, not ordering) and is tracked as a content fix.
_TIE_AFFECTED_IDS = [
    12037, 12039, 12048, 12097, 12106, 13030, 13031, 13035,
    13054, 13063, 13071, 13076, 13083, 13084, 13088, 13098, 13134,
]


def _load_sql_questions():
    out = {}
    for diff in ("easy", "medium", "hard"):
        fp = BACKEND / "content" / "questions" / f"{diff}.json"
        for q in json.loads(fp.read_text(encoding="utf-8")):
            out[q["id"]] = q
    return out


_SQL = _load_sql_questions()


@pytest.fixture(scope="module", autouse=True)
def _engine():
    database.init_query_engine()
    yield


@pytest.mark.parametrize("qid", _TIE_AFFECTED_IDS)
def test_affected_question_grades_deterministically(qid):
    q = _SQL[qid]
    eq = q["expected_query"]
    # The reference graded against itself must be correct on every run.
    verdicts = [evaluate(eq, eq, q)["correct"] for _ in range(8)]
    assert all(verdicts), (
        f"SQL {qid}: expected_query graded against itself was not always correct "
        f"({sum(verdicts)}/8) — ORDER BY tie tolerance regressed."
    )
