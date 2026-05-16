"""TC-DM-01 to TC-DM-20 — Data Modeling track."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
import data_modeling_questions as dm_catalog

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = dm_catalog.get_questions_by_difficulty()
_easy_qs = _catalog["easy"]
_medium_qs = _catalog["medium"]
_hard_qs = _catalog["hard"]

# Use first easy question for most tests
_easy_q = _easy_qs[0]
_easy_id = _easy_q["id"]
_correct_option = _easy_q["correct_option"]
_wrong_option = (_correct_option + 1) % 4


# ── Catalog ────────────────────────────────────────────────────────────────────

def test_tc_dm01_catalog_returns_all_difficulties():
    """TC-DM-01: Catalog endpoint returns easy/medium/hard groups."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-modeling/catalog")
    assert r.status_code == 200
    body = r.json()
    difficulties = {g["difficulty"] for g in body["groups"]}
    assert difficulties == {"easy", "medium", "hard"}


def test_tc_dm02_catalog_easy_all_unlocked_for_free():
    """TC-DM-02: Free user — all easy questions are unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-modeling/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    locked = [q for q in easy_group["questions"] if q["state"] == "locked"]
    assert locked == [], f"Easy questions should not be locked for free user, got: {locked}"


def test_tc_dm03_catalog_medium_mostly_locked_for_free():
    """TC-DM-03: Free user — medium questions are locked without easy solves."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-modeling/catalog")
    body = r.json()
    medium_group = next(g for g in body["groups"] if g["difficulty"] == "medium")
    locked_count = sum(1 for q in medium_group["questions"] if q["state"] == "locked")
    total_medium = len(medium_group["questions"])
    assert locked_count > 0, "Expected some medium questions to be locked for free user with no solves"
    assert total_medium >= 1


def test_tc_dm04_catalog_pro_unlocks_all():
    """TC-DM-04: Pro user — all questions unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/data-modeling/catalog")
    body = r.json()
    for group in body["groups"]:
        locked = [q for q in group["questions"] if q["state"] == "locked"]
        assert locked == [], f"Pro user should have no locked {group['difficulty']} questions"


# ── Question detail ────────────────────────────────────────────────────────────

def test_tc_dm05_question_detail_returns_mcq_fields():
    """TC-DM-05: Question detail includes options, description, hints, concepts."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/data-modeling/questions/{_easy_id}")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert isinstance(body["options"], list)
    assert len(body["options"]) >= 2
    assert "description" in body
    assert "hints" in body
    assert "concepts" in body


def test_tc_dm06_question_detail_no_correct_option_exposed():
    """TC-DM-06: Question detail does not expose correct_option before submission."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/data-modeling/questions/{_easy_id}")
    body = r.json()
    assert "correct_option" not in body, "correct_option must not be exposed before submission"


def test_tc_dm07_question_404_for_unknown_id():
    """TC-DM-07: Unknown question ID → 404."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-modeling/questions/99999")
    assert r.status_code == 404


# ── Submit ─────────────────────────────────────────────────────────────────────

def test_tc_dm08_correct_option_returns_true_with_explanation():
    """TC-DM-08: Correct option → correct: true; explanation non-empty."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-modeling/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc_dm09_wrong_option_returns_false_with_explanation():
    """TC-DM-09: Wrong option → correct: false; explanation still returned."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-modeling/submit", json={
            "question_id": _easy_id,
            "selected_option": _wrong_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is False
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc_dm10_invalid_option_index_returns_422():
    """TC-DM-10: selected_option=5 → 422 validation error."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-modeling/submit", json={
            "question_id": _easy_id,
            "selected_option": 5,
        })
    assert r.status_code == 422


def test_tc_dm11_submit_is_fast():
    """TC-DM-11: Submit completes in < 1s (no DuckDB/subprocess overhead)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        start = time.time()
        r = client.post("/api/data-modeling/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
        elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"DM submit too slow: {elapsed:.3f}s"


def test_tc_dm12_correct_solve_marks_progress():
    """TC-DM-12: Correct submission marks the question solved in catalog."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        client.post("/api/data-modeling/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
        r = client.get("/api/data-modeling/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    solved_q = next((q for q in easy_group["questions"] if q["id"] == _easy_id), None)
    assert solved_q is not None
    assert solved_q["state"] == "solved"


def test_tc_dm13_locked_question_submit_returns_403():
    """TC-DM-13: Submitting to a locked question returns 403."""
    if not _medium_qs:
        pytest.skip("No medium questions available")
    medium_id = _medium_qs[-1]["id"]  # last medium locked for free user with 0 solves
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-modeling/submit", json={
            "question_id": medium_id,
            "selected_option": 0,
        })
    assert r.status_code == 403


def test_tc_dm13b_locked_question_detail_returns_partial_payload():
    """TC-DM-13b: GET detail for a locked question returns 200 with locked:true and no options."""
    if not _medium_qs:
        pytest.skip("No medium questions available")
    medium_id = _medium_qs[-1]["id"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/data-modeling/questions/{medium_id}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("locked") is True
    assert "options" not in body
    assert "correct_option" not in body
    assert "title" in body
    assert "description" in body


# ── Catalog loader integrity ───────────────────────────────────────────────────

def test_tc_dm14_all_questions_have_required_fields():
    """TC-DM-14: Every question in the catalog has required fields."""
    required = {"id", "order", "title", "difficulty", "type", "description", "options", "correct_option", "explanation"}
    all_qs = dm_catalog._ALL_QUESTIONS
    for q in all_qs:
        missing = required - set(q.keys())
        assert not missing, f"Question {q.get('id')} missing fields: {missing}"


def test_tc_dm15_question_ids_are_unique():
    """TC-DM-15: No duplicate IDs across the full question bank."""
    all_ids = [int(q["id"]) for q in dm_catalog._ALL_QUESTIONS]
    assert len(all_ids) == len(set(all_ids)), "Duplicate question IDs found"


def test_tc_dm16_id_ranges_respected():
    """TC-DM-16: All IDs fall within the declared ranges per difficulty."""
    ranges = {"easy": (61001, 61999), "medium": (62001, 62999), "hard": (63001, 63999)}
    for q in dm_catalog._ALL_QUESTIONS:
        lo, hi = ranges[q["difficulty"]]
        assert lo <= int(q["id"]) <= hi, (
            f"Question {q['id']} ({q['difficulty']}) out of range {lo}-{hi}"
        )


def test_tc_dm17_options_have_at_least_two_entries():
    """TC-DM-17: Every question has at least 2 options."""
    for q in dm_catalog._ALL_QUESTIONS:
        assert len(q.get("options", [])) >= 2, f"Question {q['id']} has fewer than 2 options"


def test_tc_dm18_correct_option_is_valid_index():
    """TC-DM-18: correct_option is a valid index into options."""
    for q in dm_catalog._ALL_QUESTIONS:
        opts = q.get("options", [])
        co = q.get("correct_option")
        assert isinstance(co, int) and 0 <= co < len(opts), (
            f"Question {q['id']}: correct_option={co} invalid for {len(opts)} options"
        )


# ── Sample endpoint ────────────────────────────────────────────────────────────

def test_tc_dm19_sample_easy_returns_question():
    """TC-DM-19: Sample endpoint returns a DM question for easy difficulty."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/sample/data-modeling/easy")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert body.get("difficulty") == "easy"


# ── Track registry ─────────────────────────────────────────────────────────────

def test_tc_dm20_track_registry_entry():
    """TC-DM-20: data-modeling appears in the track registry with correct metadata."""
    from tracks import get_track
    t = get_track("data-modeling")
    assert t.slug == "data-modeling"
    assert t.db_topic == "data-modeling"
    assert t.eval_kind == "mcq"
    assert t.unlock_profile == "mcq"
    assert t.in_mixed_mock is False
    assert t.label == "Data Modeling"
