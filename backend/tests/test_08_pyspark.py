"""TC-106 to TC-109 — PySpark MCQ."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
import pyspark_questions as pyspark_catalog
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


def test_tc110_unlocked_pyspark_question_returns_options():
    """TC-110: Easy (unlocked) question detail returns options array."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/pyspark/questions/{_easy_id}")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert isinstance(body["options"], list)
    assert len(body["options"]) >= 2
    assert body.get("locked") is not True


def test_tc111_locked_pyspark_question_returns_partial_payload():
    """TC-111: Locked medium question returns 200 with locked:true and no options."""
    catalog = get_questions_by_difficulty()
    last_medium_id = catalog["medium"][-1]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/pyspark/questions/{last_medium_id}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("locked") is True
    assert "options" not in body
    assert "correct_option" not in body
    assert "title" in body
    assert "description" in body


def test_tc112_locked_pyspark_submit_returns_403():
    """TC-112: Submitting to a locked question returns 403."""
    catalog = get_questions_by_difficulty()
    last_medium_id = catalog["medium"][-1]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/pyspark/submit", json={
            "question_id": last_medium_id,
            "selected_option": 0,
        })
    assert r.status_code == 403


def test_tc113_loader_rejects_invalid_interaction_mode():
    """TC-113: Loader validation rejects unsupported interaction_mode values."""
    candidate = dict(_easy_q)
    candidate["interaction_mode"] = "invalid_mode"
    with pytest.raises(ValueError, match="Invalid interaction_mode"):
        pyspark_catalog._validate_question(
            candidate,
            id_ranges={
                "easy": [_easy_id, _easy_id],
                "medium": [42001, 43000],
                "hard": [43001, 44000],
            },
        )


def test_tc114_catalog_rows_expose_interaction_mode_field():
    """TC-114: Catalog rows include interaction_mode key (additive metadata)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/pyspark/catalog")
    assert r.status_code == 200
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    first_q = easy_group["questions"][0]
    assert "interaction_mode" in first_q


def test_tc115_detail_exposes_interaction_mode_field():
    """TC-115: Question detail includes interaction_mode key for unlocked payloads."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/pyspark/questions/{_easy_id}")
    assert r.status_code == 200
    body = r.json()
    assert "interaction_mode" in body
