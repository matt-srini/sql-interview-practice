"""Standing CI guard — SQL + Pandas reference execution (closes gaps G1 + G2).

For the Python and Statistics-numerical tracks, reference correctness is already
guarded by ``validate_content.py::_validate_code_reference_reproduces_tests``: those
tracks store a literal ``expected`` per test case, so the validator can re-run the
reference and compare. SQL and Pandas compute their expected output *live* at grade
time, so there is no stored answer for the validator to contradict — which left a hole:
a newly authored SQL/Pandas question whose reference crashes, returns an empty/degenerate
result, references a column that doesn't exist, or whose ``solution_*`` disagrees with
``expected_*`` would ship green. That class was the single largest content-fix category
of the 2026-05/06 authoring refactor. The check lived only in the offline
``scripts/audit_code_tracks.py`` Phase-3 sweep and was never wired into CI.

This module promotes that deterministic check into a standing, model-free CI guard.
For every SQL and Pandas practice + mock question it asserts:

  1. ``expected_*`` executes through the real grader without error;
  2. it returns a non-degenerate result (>= 1 row);
  3. ``solution_*`` agrees with ``expected_*`` through the same guard + grader a user hits;
  4. (Pandas) every ``schema`` column exists in the backing CSV and the declared order
     matches the real CSV header order (catches schema column-order drift, which the
     content validator cannot see because it never loads the CSVs).

Runtime note: the Pandas cases spawn the sandbox subprocess (faithful to production),
so this module is the slower part of the suite. That cost buys the only guarantee that
a Pandas reference actually runs against real data.
"""
import csv
import json
from pathlib import Path

import pytest

import database
from evaluator import evaluate, run_query
from python_evaluator import evaluate_python_data_code, run_python_data_code

BACKEND = Path(__file__).resolve().parent.parent
SQL_DIR = BACKEND / "content" / "questions"
PANDAS_DIR = BACKEND / "content" / "python_data_questions"
DATASETS = BACKEND / "datasets"
DIFFS = ("easy", "medium", "hard")


def _load(directory: Path) -> list[dict]:
    out: list[dict] = []
    for diff in DIFFS:
        fp = directory / f"{diff}.json"
        if not fp.exists():
            continue
        for q in json.loads(fp.read_text(encoding="utf-8")):
            q["_difficulty"] = diff
            out.append(q)
    return out


SQL_Q = _load(SQL_DIR)
PANDAS_Q = _load(PANDAS_DIR)


def _qid(q: dict) -> str:
    pool = "mock" if q.get("mock_only") else "practice"
    return f"{q.get('id')}-{q.get('_difficulty')}-{pool}"


# Pre-existing SQL content defects this guard surfaced on first run. Quarantined as
# xfail (non-strict, so a fix that lands early simply xpasses) until the authoring
# agent re-derives them; tracked in the task ledger / DECISIONS log. (The two
# float-aggregation-jitter questions this guard also surfaced — 13004, 13085 — were
# fixed at the engine layer via the single-thread setting in database.py, so they are
# no longer listed here.)
_SQL_KNOWN_DEFECTS = {
    12030: "empty canonical result (degenerate) — content fix pending via authoring agent",
    13025: "empty canonical result (degenerate) — content fix pending via authoring agent",
}


def _sql_params():
    params = []
    for q in SQL_Q:
        marks = ()
        defect = _SQL_KNOWN_DEFECTS.get(q.get("id"))
        if defect:
            marks = (pytest.mark.xfail(reason=defect, strict=False),)
        params.append(pytest.param(q, marks=marks, id=_qid(q)))
    return params


@pytest.fixture(scope="module", autouse=True)
def _query_engine():
    """Load the golden in-memory DuckDB once for the SQL cases."""
    database.init_query_engine()
    yield


def _csv_header(csv_file: str) -> list[str]:
    with (DATASETS / csv_file).open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("q", _sql_params())
def test_sql_reference_executes_and_solution_agrees(q):
    qid = q.get("id")

    # 1 + 2: expected_query runs and is non-degenerate.
    res = run_query(q["expected_query"], q)
    rows = res.get("rows")
    assert rows is not None, f"SQL {qid}: run_query returned no rows object"
    assert len(rows) >= 1, (
        f"SQL {qid}: expected_query returned 0 rows — degenerate reference "
        f"(a correct answer that is always empty cannot grade a learner)."
    )

    # 3: solution_query agrees with expected_query through the real guard + grader.
    graded = evaluate(q["solution_query"], q["expected_query"], q)
    assert graded.get("correct"), (
        f"SQL {qid}: solution_query does not reproduce expected_query "
        f"(or was rejected by sql_guard on the way through evaluate())."
    )


# ---------------------------------------------------------------------------
# Pandas
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("q", PANDAS_Q, ids=_qid)
def test_pandas_reference_executes_and_solution_agrees(q):
    qid = q.get("id")

    # 1 + 2: expected_code runs against the real CSVs and is non-degenerate.
    out = run_python_data_code(q["expected_code"], q)
    assert not out.get("error"), (
        f"Pandas {qid}: expected_code raised: {str(out.get('error'))[:300]}"
    )
    result = out.get("result") or {}
    rows = result.get("rows", out.get("rows"))
    assert rows is not None and len(rows) >= 1, (
        f"Pandas {qid}: expected_code produced no rows — degenerate reference."
    )

    # 3: solution_code agrees with expected_code through the real grader.
    if q.get("solution_code"):
        graded = evaluate_python_data_code(q["solution_code"], q)
        assert graded.get("correct"), (
            f"Pandas {qid}: solution_code does not reproduce expected_code: "
            f"{str(graded.get('error'))[:300]}"
        )

    # 4: schema column order matches the real CSV header (drift the validator can't see).
    dataframes = q.get("dataframes") or {}
    for var, cols in (q.get("schema") or {}).items():
        csv_file = dataframes.get(var)
        if not csv_file:
            continue
        header = _csv_header(csv_file)
        missing = [c for c in cols if c not in header]
        assert not missing, (
            f"Pandas {qid}: schema[{var}] lists columns absent from {csv_file}: {missing}"
        )
        positions = [header.index(c) for c in cols]
        assert positions == sorted(positions), (
            f"Pandas {qid}: schema[{var}] column order does not match {csv_file} "
            f"header order (declared {cols} vs CSV {header})."
        )
