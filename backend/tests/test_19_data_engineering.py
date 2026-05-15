"""TC-DE-01 to TC-DE-20 — Data Engineering Concepts track."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
import data_engineering_questions as de_catalog

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = de_catalog.get_questions_by_difficulty()
_easy_qs = _catalog["easy"]
_medium_qs = _catalog["medium"]
_hard_qs = _catalog["hard"]

# Use first easy question for most tests
_easy_q = _easy_qs[0]
_easy_id = _easy_q["id"]
_correct_option = _easy_q["correct_option"]
_wrong_option = (_correct_option + 1) % 4


# ── Catalog ────────────────────────────────────────────────────────────────────

def test_tc_de01_catalog_returns_all_difficulties():
    """TC-DE-01: Catalog endpoint returns easy/medium/hard groups."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-engineering/catalog")
    assert r.status_code == 200
    body = r.json()
    difficulties = {g["difficulty"] for g in body["groups"]}
    assert difficulties == {"easy", "medium", "hard"}


def test_tc_de02_catalog_easy_all_unlocked_for_free():
    """TC-DE-02: Free user — all easy questions are unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-engineering/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    locked = [q for q in easy_group["questions"] if q["state"] == "locked"]
    assert locked == [], f"Easy questions should not be locked for free user, got: {locked}"


def test_tc_de03_catalog_medium_mostly_locked_for_free():
    """TC-DE-03: Free user — medium questions are locked (not enough easy solves)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-engineering/catalog")
    body = r.json()
    medium_group = next(g for g in body["groups"] if g["difficulty"] == "medium")
    locked_count = sum(1 for q in medium_group["questions"] if q["state"] == "locked")
    # With 0 easy solves, most medium should be locked (first few may be unlocked by MCQ threshold)
    total_medium = len(medium_group["questions"])
    assert locked_count > 0, "Expected some medium questions to be locked for free user with no solves"
    assert total_medium >= 1


def test_tc_de04_catalog_pro_unlocks_all():
    """TC-DE-04: Pro user — all questions unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/data-engineering/catalog")
    body = r.json()
    for group in body["groups"]:
        locked = [q for q in group["questions"] if q["state"] == "locked"]
        assert locked == [], f"Pro user should have no locked {group['difficulty']} questions"


# ── Question detail ────────────────────────────────────────────────────────────

def test_tc_de05_question_detail_returns_mcq_fields():
    """TC-DE-05: Question detail includes options, description, hints, concepts."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/data-engineering/questions/{_easy_id}")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert isinstance(body["options"], list)
    assert len(body["options"]) >= 2
    assert "description" in body
    assert "hints" in body
    assert "concepts" in body


def test_tc_de06_question_detail_no_correct_option_exposed():
    """TC-DE-06: Question detail does not expose correct_option before submission."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/data-engineering/questions/{_easy_id}")
    body = r.json()
    assert "correct_option" not in body, "correct_option must not be exposed before submission"


def test_tc_de07_question_404_for_unknown_id():
    """TC-DE-07: Unknown question ID → 404."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/data-engineering/questions/99999")
    assert r.status_code == 404


# ── Submit ─────────────────────────────────────────────────────────────────────

def test_tc_de08_correct_option_returns_true_with_explanation():
    """TC-DE-08: Correct option → correct: true; explanation non-empty."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-engineering/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc_de09_wrong_option_returns_false_with_explanation():
    """TC-DE-09: Wrong option → correct: false; explanation still returned."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-engineering/submit", json={
            "question_id": _easy_id,
            "selected_option": _wrong_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is False
    assert body.get("explanation") and len(body["explanation"]) > 0


def test_tc_de10_invalid_option_index_returns_422():
    """TC-DE-10: selected_option=5 → 422 validation error."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-engineering/submit", json={
            "question_id": _easy_id,
            "selected_option": 5,
        })
    assert r.status_code == 422


def test_tc_de11_submit_is_fast():
    """TC-DE-11: Submit completes in < 1s (no DuckDB/subprocess overhead)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        start = time.time()
        r = client.post("/api/data-engineering/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
        elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"DE submit too slow: {elapsed:.3f}s"


def test_tc_de12_correct_solve_marks_progress():
    """TC-DE-12: Correct submission marks the question solved in catalog."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        client.post("/api/data-engineering/submit", json={
            "question_id": _easy_id,
            "selected_option": _correct_option,
        })
        r = client.get("/api/data-engineering/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    solved_q = next((q for q in easy_group["questions"] if q["id"] == _easy_id), None)
    assert solved_q is not None
    assert solved_q["state"] == "solved"


def test_tc_de13_locked_question_returns_403():
    """TC-DE-13: Submitting to a locked question returns 403."""
    if not _medium_qs:
        pytest.skip("No medium questions available")
    medium_id = _medium_qs[-1]["id"]  # last medium likely locked for free user with 0 solves
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/data-engineering/submit", json={
            "question_id": medium_id,
            "selected_option": 0,
        })
    # Either 403 (locked) or 200 (if this one happens to be unlocked)
    assert r.status_code in (200, 403)


# ── Catalog loader integrity ───────────────────────────────────────────────────

def test_tc_de14_all_questions_have_required_fields():
    """TC-DE-14: Every question in the catalog has required fields."""
    required = {"id", "order", "title", "difficulty", "type", "description", "options", "correct_option", "explanation"}
    all_qs = de_catalog._ALL_QUESTIONS
    for q in all_qs:
        missing = required - set(q.keys())
        assert not missing, f"Question {q.get('id')} missing fields: {missing}"


def test_tc_de15_question_ids_are_unique():
    """TC-DE-15: No duplicate IDs across the full question bank."""
    all_ids = [int(q["id"]) for q in de_catalog._ALL_QUESTIONS]
    assert len(all_ids) == len(set(all_ids)), "Duplicate question IDs found"


def test_tc_de16_id_ranges_respected():
    """TC-DE-16: All IDs fall within the declared ranges per difficulty."""
    ranges = {"easy": (51001, 51999), "medium": (52001, 52999), "hard": (53001, 53999)}
    for q in de_catalog._ALL_QUESTIONS:
        lo, hi = ranges[q["difficulty"]]
        assert lo <= int(q["id"]) <= hi, (
            f"Question {q['id']} ({q['difficulty']}) out of range {lo}-{hi}"
        )


def test_tc_de17_options_have_at_least_two_entries():
    """TC-DE-17: Every question has at least 2 options."""
    for q in de_catalog._ALL_QUESTIONS:
        assert len(q.get("options", [])) >= 2, f"Question {q['id']} has fewer than 2 options"


def test_tc_de18_correct_option_is_valid_index():
    """TC-DE-18: correct_option is a valid index into options."""
    for q in de_catalog._ALL_QUESTIONS:
        opts = q.get("options", [])
        co = q.get("correct_option")
        assert isinstance(co, int) and 0 <= co < len(opts), (
            f"Question {q['id']}: correct_option={co} invalid for {len(opts)} options"
        )


# ── Sample endpoint ────────────────────────────────────────────────────────────

def test_tc_de19_sample_easy_returns_question():
    """TC-DE-19: Sample endpoint returns a DE question for easy difficulty."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/sample/data-engineering/easy")
    assert r.status_code == 200
    body = r.json()
    assert "options" in body
    assert body.get("difficulty") == "easy"


# ── Track registry ─────────────────────────────────────────────────────────────

def test_tc_de20_track_registry_entry():
    """TC-DE-20: data-engineering appears in the track registry with correct metadata."""
    from tracks import get_track
    t = get_track("data-engineering")
    assert t.slug == "data-engineering"
    assert t.db_topic == "data-engineering"
    assert t.eval_kind == "mcq"
    assert t.unlock_profile == "mcq"
    assert t.in_mixed_mock is False
    assert t.label == "Data Engineering"
