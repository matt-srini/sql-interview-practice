"""Pandas grading decouples a sound full-result comparison from a capped display
preview (Phase-3 row-cap fix). A correct answer over a large dataset grades correct
and the client receives only a ~200-row preview with the true total; an answer that
diverges only beyond the preview window still grades incorrect.
"""
import json
from pathlib import Path

import pytest

from python_evaluator import (
    DATA_PREVIEW_ROWS, evaluate_pandas_code, run_pandas_code_checked,
)

BACKEND = Path(__file__).resolve().parent.parent


def _load_q(qid: int):
    for diff in ("easy", "medium", "hard"):
        for q in json.loads((BACKEND / "content/pandas_questions" / f"{diff}.json").read_text()):
            if q.get("id") == qid:
                return q
    raise AssertionError(f"question {qid} not found")


def test_large_result_grades_correct_and_preview_capped():
    # 31024 "Drop Events Without a Product" → ~43k correct rows (was ungradeable).
    q = _load_q(31024)
    res = evaluate_pandas_code(q["expected_code"], q)
    assert res["correct"] is True, res.get("error")
    ur = res["user_result"]
    assert ur["total_rows"] > DATA_PREVIEW_ROWS          # truly large
    assert len(ur["rows"]) == DATA_PREVIEW_ROWS          # but only a preview is returned
    assert ur["truncated"] is True
    assert ur["row_limit"] == DATA_PREVIEW_ROWS


def test_grading_uses_full_result_not_preview():
    # A submission identical to the key for the first 200 rows but missing the rest
    # must be graded INCORRECT — proving the comparison sees the full result.
    q = _load_q(31024)
    head_only = (
        "import pandas as pd\n"
        "def solve(df_events):\n"
        "    r = df_events.dropna(subset=['product_id'])[['event_id','user_id','event_name','product_id']]"
        ".sort_values('event_id').reset_index(drop=True)\n"
        "    return r.head(200)\n"
    )
    res = evaluate_pandas_code(head_only, q)
    assert res["correct"] is False


def test_small_result_not_truncated():
    # 31002 aggregates to a handful of rows — well under the preview window.
    q = _load_q(31002)
    res = evaluate_pandas_code(q["expected_code"], q)
    assert res["correct"] is True
    ur = res["user_result"]
    assert ur["total_rows"] < DATA_PREVIEW_ROWS
    assert ur["truncated"] is False
    assert len(ur["rows"]) == ur["total_rows"]


def test_run_code_checked_returns_preview_and_pass():
    q = _load_q(31024)
    out = run_pandas_code_checked(q["expected_code"], q)
    tr = out["test_results"][0]
    assert tr["passed"] is True
    assert tr["actual"]["total_rows"] > DATA_PREVIEW_ROWS
    assert len(tr["actual"]["rows"]) == DATA_PREVIEW_ROWS
    assert len(out["rows"]) == DATA_PREVIEW_ROWS  # top-level display also capped
