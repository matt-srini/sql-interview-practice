"""SQL grading is sound on the FULL result, with a capped display preview
(Phase-3 follow-up to the pandas row-cap fix). Previously evaluate() compared only
head(200) of each query, so a query that matched on the first 200 rows but diverged
beyond them was mis-graded as correct.
"""
import pytest

import database
from evaluator import evaluate, run_query, MAX_RESULT_ROWS


@pytest.fixture(autouse=True)
def _ensure_query_engine():
    # Other test modules' TestClient lifespans close the shared DuckDB engine on
    # teardown, so re-init before each test here (idempotent when already open).
    database.init_query_engine()
    yield


EVENTS = {
    "id": 99001,
    "dataset_files": ["events.csv"],
    "expected_query": "SELECT event_id FROM events ORDER BY event_id",
}


def test_grading_uses_full_result_not_head_200():
    # User returns only the first 500 ordered rows. The first 200 are identical to
    # the expected result (so the old head(200) grading mis-accepted it), but the
    # full result differs (500 vs all rows) — full grading must reject it.
    wrong = "SELECT event_id FROM events ORDER BY event_id LIMIT 500"
    res = evaluate(wrong, EVENTS["expected_query"], EVENTS)
    assert res["correct"] is False


def test_correct_large_query_grades_correct_and_preview_capped():
    res = evaluate(EVENTS["expected_query"], EVENTS["expected_query"], EVENTS)
    assert res["correct"] is True
    ur = res["user_result"]
    assert ur["total_rows"] > MAX_RESULT_ROWS         # genuinely large
    assert len(ur["rows"]) == MAX_RESULT_ROWS         # but only a preview is returned
    assert ur["truncated"] is True
    assert res["expected_result"]["truncated"] is True


def test_run_query_preview_default_caps_display():
    out = run_query("SELECT event_id FROM events ORDER BY event_id", EVENTS)  # preview=True
    assert len(out["rows"]) == MAX_RESULT_ROWS
    assert out["total_rows"] > MAX_RESULT_ROWS
    assert out["truncated"] is True


def test_run_query_full_returns_all_rows():
    out = run_query("SELECT event_id FROM events", EVENTS, preview=False)
    assert len(out["rows"]) == out["total_rows"] > MAX_RESULT_ROWS


def test_small_result_not_truncated():
    out = run_query("SELECT DISTINCT status FROM orders", {"dataset_files": ["orders.csv"]})
    assert out["truncated"] is False
    assert len(out["rows"]) == out["total_rows"]
    assert out["total_rows"] < MAX_RESULT_ROWS
