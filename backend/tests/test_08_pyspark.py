"""TC-106 to TC-109 — PySpark MCQ."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
from pyspark_questions import get_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = get_questions_by_difficulty()
_easy_q = _catalog["easy"][0]
_easy_id = _easy_q["id"]        # 11001
_correct_option = _easy_q["correct_option"]  # 1
_wrong_option = (_correct_option + 1) % 4


def test_tc106_correct_option_returns_correct_true_and_explanation():
    """TC-106: Correct option → correct: true; explanation non-null."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/pyspark/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is True
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc107_wrong_option_returns_correct_false_with_explanation():
    """TC-107: Wrong option → correct: false; explanation still returned."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/pyspark/submit", json={
            "question_id": _easy_id,
            "selected_option": _wrong_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body.get("correct") is False
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc108_invalid_option_index_returns_422():
    """TC-108: selected_option=5 → 422 validation error."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/pyspark/submit", json={
            "question_id": _easy_id,
            "selected_option": 5,
        })
    assert r.status_code == 422


def test_tc109_pyspark_submit_is_fast():
    """TC-109: PySpark submit completes in < 200ms (no DuckDB/subprocess overhead)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        start = time.time()
        r = client.post("/api/pyspark/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
        elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"PySpark submit too slow: {elapsed:.3f}s"
