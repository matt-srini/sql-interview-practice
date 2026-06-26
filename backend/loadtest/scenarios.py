"""Weighted virtual-user journeys for the load harness.

Each journey is an ``async`` function ``run(vu) -> None`` that performs a realistic
sequence of requests using the virtual user's own ``httpx.AsyncClient`` (so each
VU carries its own session cookie == its own backend user). Journeys record every
HTTP call through ``vu.record(...)`` and must never raise: a transport error or a
non-2xx status is *data*, not a crash — the driver classifies it.

Traffic is deliberately **read-heavy**, mirroring real usage: most learners browse
and read; a minority execute code (the expensive path); a smaller minority run a
mock session or open the dashboard.

    WEIGHTS (relative):
      anon_browse_sample            50   land → catalog → open a sample → submit a sample (1 cheap SQL exec)
      browse_only                   25   pure catalog / question-detail reads (no execution)
      practice_execute              12   register → solve a practice question WITH code execution (subprocess — expensive)
      pandas_execute                 8   register → submit a CORRECT pandas solution (numpy/pandas sandbox path)
      statistics_numerical_execute   5   register → submit a CORRECT statistics-numerical solution (numpy sandbox path)
      mock_session                   5   start → fetch → submit → finish a mock (DB-heavy, no code exec via PySpark MCQ)
      dashboard_read                 5   dashboard + coaching insights reads

The driver runs a continuous /health + /api/catalog *probe* alongside these,
independent of the weights, to measure head-of-line blocking (a cheap endpoint's
latency while heavy executions are in flight).

The ``pandas_execute`` and ``statistics_numerical_execute`` journeys close the
blind spot the 2026-06-08 load test had: the original harness only submitted a
trivial Python-algorithm ``def solve(): return None`` and never exercised the
numpy/pandas import path (the OpenBLAS path).  They also use a **correctness
oracle**: the submitted code is the known-correct solution so ``body.correct``
must be ``True`` on a healthy server.  A 200-with-{error} body (e.g. the
OpenBLAS RLIMIT_AS abort that silently returns HTTP 200) is caught here because
the driver scores it "ok" on status code alone — the oracle catches it.
"""
from __future__ import annotations

import random

# A trivial-but-valid answer per executable track. Correctness does not matter for
# load — what matters is that the full evaluation path runs (SQL: user+expected
# queries both execute on DuckDB; Python: a subprocess is spawned and test cases
# run). These deliberately exercise the expensive code path without depending on
# per-question solutions.
_SQL_ANSWER = "SELECT 1"
_PY_ANSWER = "def solve(*args, **kwargs):\n    return None\n"

# --------------------------------------------------------------------------- #
# Correct solutions for the correctness-oracle journeys (A1)
#
# Pandas easy #31001 — "Select Columns and Drop Nulls"
# Practice question (not mock_only); uses df_users DataFrame.
# --------------------------------------------------------------------------- #
_PANDAS_ID = 31001
_PANDAS_ANSWER = """\
import pandas as pd

def solve(df_users):
    return df_users[['name', 'email']].dropna(subset=['email']).reset_index(drop=True)
"""

# Statistics easy #71002 — "Computing the Sample Mean"
# Practice question (not mock_only); subtype="numerical" (code execution path).
# --------------------------------------------------------------------------- #
_STATS_ID = 71002
_STATS_ANSWER = """\
def solve(data: list[float]) -> float:
    return round(sum(data) / len(data), 4)
"""


# --------------------------------------------------------------------------- #
# Journeys
# --------------------------------------------------------------------------- #
async def anon_browse_sample(vu) -> None:
    """Anonymous: land → browse catalog → open a sample question → submit a sample.

    Needs no login (the anonymous-first identity model auto-creates a user row on
    the first catalog hit). Ends with one *cheap* SQL execution (sample submit),
    which on the unfixed server runs the DuckDB evaluator directly on the event
    loop.
    """
    await vu.get("/api/catalog/counts", name="catalog_counts")
    await vu.get("/api/catalog", name="catalog_sql")
    # Open the next SQL sample (read-only — marks nothing).
    sample = await vu.get("/api/sample/sql/easy", name="sample_open")
    qid = _sample_id(sample)
    if qid is not None:
        await vu.post(
            "/api/sample/sql/submit",
            json={"question_id": qid, "query": _SQL_ANSWER},
            name="sample_submit_sql",
        )


async def browse_only(vu) -> None:
    """Pure reads — the cheapest, most common traffic. No execution, no writes."""
    await vu.get("/api/catalog", name="catalog_sql")
    await vu.get("/api/python/catalog", name="catalog_python")
    track, qid = await _first_unlocked(vu, "/api/python/catalog", "/api/python/questions")
    if qid is not None:
        await vu.get(f"/api/python/questions/{qid}", name="question_detail_python")


async def practice_execute(vu) -> None:
    """Register in place → solve a practice question WITH code execution.

    This is the expensive path: a Python submit spawns an OS subprocess sandbox.
    On the unfixed server the blocking ``communicate()`` runs directly on the
    event loop, so this journey is what makes the head-of-line probe spike.
    """
    await vu.ensure_registered()
    cat = await vu.get("/api/python/catalog", name="catalog_python")
    qid = _first_unlocked_from_catalog(cat)
    if qid is None:
        return
    await vu.get(f"/api/python/questions/{qid}", name="question_detail_python")
    await vu.post(
        "/api/python/submit",
        json={"question_id": qid, "code": _PY_ANSWER, "duration_ms": 4200},
        name="submit_python_exec",
    )


async def pandas_execute(vu) -> None:
    """Register → submit a CORRECT pandas solution → assert body.correct is True.

    This is the path that imports numpy/pandas in the sandbox (the OpenBLAS path
    the 2026-06-08 load harness never exercised — its only code-exec journey used
    a Python-algorithm stub that never touched numpy).

    The correctness oracle catches the silent 200-{error} OpenBLAS-abort failure
    that a status-code-only check cannot see: if the sandbox aborts due to
    RLIMIT_AS exhaustion the body comes back as ``{"error": "..."}`` with HTTP 200
    — the driver classifies it "ok" but ``body.correct`` is absent/False, so the
    oracle records a FAIL.
    """
    await vu.ensure_registered()
    payload = await vu.post(
        "/api/pandas/submit",
        json={"question_id": _PANDAS_ID, "code": _PANDAS_ANSWER, "duration_ms": 5000},
        name="submit_pandas_exec",
    )
    vu.recorder.add_correctness_check(
        "pandas_correct",
        isinstance(payload, dict) and payload.get("correct") is True,
    )


async def statistics_numerical_execute(vu) -> None:
    """Register → submit a CORRECT statistics-numerical solution → assert correct is True.

    Also a numpy-importing sandbox path (statistics numerical questions run through
    ``python_evaluator.evaluate_python_code`` in a subprocess).  The correctness
    oracle serves the same purpose as in ``pandas_execute``: a sandbox abort or
    eval error returns HTTP 200 with ``{"error": ...}`` — caught here because
    ``body.correct`` will not be ``True``.
    """
    await vu.ensure_registered()
    payload = await vu.post(
        "/api/statistics/submit",
        json={"question_id": _STATS_ID, "code": _STATS_ANSWER, "duration_ms": 3000},
        name="submit_stats_numerical_exec",
    )
    vu.recorder.add_correctness_check(
        "stats_numerical_correct",
        isinstance(payload, dict) and payload.get("correct") is True,
    )


async def mock_session(vu) -> None:
    """Start → fetch → submit → finish a mock session (DB-heavy).

    Uses a PySpark benchmark (MCQ, no code execution) so this journey stresses the
    Postgres/session path rather than the sandbox. Upgrades the VU to Pro first
    (dev-only ``/api/user/plan``) so the per-plan mock limits don't reject it.
    """
    await vu.ensure_registered()
    await vu.ensure_pro()
    started = await vu.post(
        "/api/mock/start",
        json={"mode": "benchmark", "track": "pyspark", "difficulty": "medium"},
        name="mock_start",
    )
    if not isinstance(started, dict):
        return
    session_id = started.get("session_id") or started.get("id")
    questions = started.get("questions") or []
    if session_id is None:
        return
    await vu.get(f"/api/mock/{session_id}", name="mock_load")
    for q in questions[:2]:
        await vu.post(
            f"/api/mock/{session_id}/submit",
            json={
                "question_id": q.get("id"),
                "track": "pyspark",
                "selected_option": random.randint(0, 3),
                "time_spent_s": 30,
            },
            name="mock_submit",
        )
    await vu.post(f"/api/mock/{session_id}/finish", json={}, name="mock_finish")


async def dashboard_read(vu) -> None:
    """Dashboard + coaching insights reads (Postgres aggregation, cached 60s)."""
    await vu.ensure_registered()
    await vu.get("/api/dashboard", name="dashboard")
    await vu.get("/api/dashboard/insights", name="dashboard_insights")


# Relative weights — see module docstring.
WEIGHTED_JOURNEYS = [
    (anon_browse_sample, 50),
    (browse_only, 25),
    (practice_execute, 12),
    (pandas_execute, 8),
    (statistics_numerical_execute, 5),
    (mock_session, 5),
    (dashboard_read, 5),
]


def pick_journey(rng: random.Random):
    total = sum(w for _, w in WEIGHTED_JOURNEYS)
    r = rng.uniform(0, total)
    upto = 0.0
    for journey, weight in WEIGHTED_JOURNEYS:
        upto += weight
        if r <= upto:
            return journey
    return WEIGHTED_JOURNEYS[-1][0]


# --------------------------------------------------------------------------- #
# Discovery helpers
# --------------------------------------------------------------------------- #
def _sample_id(sample_response):
    if not isinstance(sample_response, dict):
        return None
    block = sample_response.get("sample") or sample_response
    if isinstance(block, dict):
        return block.get("id") or block.get("question_id")
    return None


def _first_unlocked_from_catalog(catalog_response):
    """Return the id of the first non-locked question in a {groups:[...]} catalog."""
    if not isinstance(catalog_response, dict):
        return None
    for group in catalog_response.get("groups", []):
        for q in group.get("questions", []):
            if q.get("state") != "locked":
                return q.get("id")
    return None


async def _first_unlocked(vu, catalog_path, _detail_prefix):
    cat = await vu.get(catalog_path, name="catalog_python")
    return catalog_path, _first_unlocked_from_catalog(cat)
