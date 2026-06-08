"""Regression guard — every SQL reference query must be value-deterministic.

DuckDB parallelises aggregation and float addition is non-associative, so a
multi-threaded ``avg()``/``sum()`` can differ in its last bits between runs; a
downstream ``ROUND(..., 2)`` near a boundary then flips the displayed value,
making grading non-deterministic — a correct answer is marked wrong on the
unlucky run. ``database.init_query_engine()`` pins the grading connection to a
single thread to remove this (verified to stabilise the two questions, 13004 and
13085, that exhibited the jitter).

This test asserts no SQL reference produces a different result *set* across repeated
runs, so the determinism setting cannot silently regress and a newly authored query
with a non-deterministic construct is caught.
"""
import json
from pathlib import Path

import pytest

import database
from evaluator import _execute_limited_query, _validate_query, normalize_dataframe

BACKEND = Path(__file__).resolve().parent.parent
RUNS = 5


def _load_sql():
    out = []
    for diff in ("easy", "medium", "hard"):
        fp = BACKEND / "content" / "questions" / f"{diff}.json"
        out.extend(json.loads(fp.read_text(encoding="utf-8")))
    return out


SQL_Q = _load_sql()


@pytest.fixture(scope="module", autouse=True)
def _engine():
    database.init_query_engine()
    yield


def _multiset_signature(q):
    df = _execute_limited_query(_validate_query(q["expected_query"]), q)
    return normalize_dataframe(df, sort_rows=True).to_csv(index=False)


def test_all_sql_references_are_value_deterministic():
    nondeterministic = []
    for q in SQL_Q:
        signatures = {_multiset_signature(q) for _ in range(RUNS)}
        if len(signatures) > 1:
            nondeterministic.append(q["id"])
    assert not nondeterministic, (
        "SQL references produced different result sets across runs (value jitter — "
        f"the single-thread determinism setting may have regressed): {nondeterministic}"
    )
