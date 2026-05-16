"""TC-ST-01 to TC-ST-30 — Statistics & Probability track (dual-subtype)."""
import time

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _make_user
import statistics_questions as st_catalog

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_catalog = st_catalog.get_questions_by_difficulty()
_easy_qs = _catalog["easy"]
_medium_qs = _catalog["medium"]
_hard_qs = _catalog["hard"]

# Pick first conceptual and first numerical easy question for fixtures
_easy_conceptual = next((q for q in _easy_qs if q.get("subtype") == "conceptual"), None)
_easy_numerical = next((q for q in _easy_qs if q.get("subtype") == "numerical"), None)


# ── Catalog ────────────────────────────────────────────────────────────────────

def test_tc_st01_catalog_returns_all_difficulties():
    """TC-ST-01: Catalog endpoint returns easy/medium/hard groups."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/statistics/catalog")
    assert r.status_code == 200
    body = r.json()
    difficulties = {g["difficulty"] for g in body["groups"]}
    assert difficulties == {"easy", "medium", "hard"}


def test_tc_st02_catalog_easy_all_unlocked_for_free():
    """TC-ST-02: Free user — all easy questions are unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/statistics/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    locked = [q for q in easy_group["questions"] if q["state"] == "locked"]
    assert locked == [], f"Easy questions should not be locked for free user, got: {locked}"


def test_tc_st03_catalog_medium_locked_for_fresh_free_user():
    """TC-ST-03: Free user — medium questions are locked without easy solves."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/statistics/catalog")
    body = r.json()
    medium_group = next(g for g in body["groups"] if g["difficulty"] == "medium")
    locked_count = sum(1 for q in medium_group["questions"] if q["state"] == "locked")
    assert locked_count > 0, "Expected some medium questions locked for free user with 0 solves"


def test_tc_st04_catalog_pro_unlocks_all():
    """TC-ST-04: Pro user — all questions unlocked."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/statistics/catalog")
    body = r.json()
    for group in body["groups"]:
        locked = [q for q in group["questions"] if q["state"] == "locked"]
        assert locked == [], f"Pro user should have no locked {group['difficulty']} questions"


def test_tc_st05_catalog_includes_subtype_field():
    """TC-ST-05: Catalog question entries expose subtype field."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/statistics/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    for q in easy_group["questions"]:
        assert "subtype" in q, f"Question {q.get('id')} missing subtype in catalog"
        assert q["subtype"] in ("conceptual", "numerical")


# ── Question detail — conceptual ───────────────────────────────────────────────

def test_tc_st06_conceptual_detail_has_mcq_fields():
    """TC-ST-06: Conceptual question detail includes options and subtype."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{_easy_conceptual['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["subtype"] == "conceptual"
    assert "options" in body
    assert isinstance(body["options"], list)
    assert len(body["options"]) >= 2
    assert "correct_option" not in body, "correct_option must not be exposed before submission"


def test_tc_st07_conceptual_detail_no_code_fields():
    """TC-ST-07: Conceptual question detail does not expose expected_code or test_cases."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{_easy_conceptual['id']}")
    body = r.json()
    assert "expected_code" not in body
    assert "correct_option" not in body


# ── Question detail — numerical ────────────────────────────────────────────────

def test_tc_st08_numerical_detail_has_code_fields():
    """TC-ST-08: Numerical question detail includes starter_code and test_cases."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{_easy_numerical['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body["subtype"] == "numerical"
    assert "starter_code" in body
    assert "test_cases" in body
    assert isinstance(body["test_cases"], list)


def test_tc_st09_numerical_detail_no_expected_outputs_in_test_cases():
    """TC-ST-09: Numerical test_cases in detail don't expose expected outputs."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{_easy_numerical['id']}")
    body = r.json()
    for tc in body.get("test_cases", []):
        assert "expected_output" not in tc, "expected_output must not be exposed in detail endpoint"


def test_tc_st10_numerical_detail_no_expected_code():
    """TC-ST-10: Numerical question detail does not expose expected_code."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{_easy_numerical['id']}")
    body = r.json()
    assert "expected_code" not in body


# ── Submit — conceptual ────────────────────────────────────────────────────────

def test_tc_st11_conceptual_correct_option():
    """TC-ST-11: Correct option → correct: true with explanation."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    correct_option = _easy_conceptual["correct_option"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/submit", json={
            "question_id": _easy_conceptual["id"],
            "selected_option": correct_option,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body["subtype"] == "conceptual"
    assert body.get("explanation")


def test_tc_st12_conceptual_wrong_option():
    """TC-ST-12: Wrong option → correct: false with explanation."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    correct_option = _easy_conceptual["correct_option"]
    wrong = (correct_option + 1) % 4
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/submit", json={
            "question_id": _easy_conceptual["id"],
            "selected_option": wrong,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is False
    assert body["subtype"] == "conceptual"


def test_tc_st13_conceptual_submit_fast():
    """TC-ST-13: Conceptual submit completes in < 1s (no subprocess)."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        start = time.time()
        r = client.post("/api/statistics/submit", json={
            "question_id": _easy_conceptual["id"],
            "selected_option": _easy_conceptual["correct_option"],
        })
        elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"Conceptual submit too slow: {elapsed:.3f}s"


# ── Submit — numerical ─────────────────────────────────────────────────────────

def test_tc_st14_numerical_correct_code():
    """TC-ST-14: Correct code → correct: true with solution_code in response."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    good_code = _easy_numerical["expected_code"]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/submit", json={
            "question_id": _easy_numerical["id"],
            "code": good_code,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body["subtype"] == "numerical"
    assert "solution_code" in body


def test_tc_st15_numerical_wrong_code():
    """TC-ST-15: Wrong code → correct: false."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    bad_code = "def solve():\n    return -999"
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/submit", json={
            "question_id": _easy_numerical["id"],
            "code": bad_code,
        })
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is False
    assert body["subtype"] == "numerical"


# ── Run-code ───────────────────────────────────────────────────────────────────

def test_tc_st16_numerical_run_code_works():
    """TC-ST-16: Run-code returns result for a numerical question."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/run-code", json={
            "question_id": _easy_numerical["id"],
            "code": _easy_numerical["expected_code"],
        })
    assert r.status_code == 200
    body = r.json()
    assert "error" in body or "result" in body


def test_tc_st17_conceptual_run_code_returns_400():
    """TC-ST-17: Run-code for conceptual question → 400."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/run-code", json={
            "question_id": _easy_conceptual["id"],
            "code": "print('hi')",
        })
    assert r.status_code == 400


def test_tc_st18_run_code_blocked_imports():
    """TC-ST-18: Code with disallowed import (pandas) → 400 guard error."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/run-code", json={
            "question_id": _easy_numerical["id"],
            "code": "import pandas as pd\ndef solve(): return 1",
        })
    assert r.status_code == 400
    assert "guard_errors" in r.json()


def test_tc_st19_run_code_allowed_numpy():
    """TC-ST-19: Code using numpy is allowed for numerical questions."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/run-code", json={
            "question_id": _easy_numerical["id"],
            "code": "import numpy as np\ndef solve():\n    return float(np.mean([1, 2, 3]))",
        })
    assert r.status_code == 200


# ── 404 ────────────────────────────────────────────────────────────────────────

def test_tc_st20_unknown_question_returns_404():
    """TC-ST-20: Unknown question ID → 404."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/statistics/questions/99999")
    assert r.status_code == 404


# ── Locked question behavior ───────────────────────────────────────────────────

def test_tc_st21_locked_medium_detail_has_locked_true():
    """TC-ST-21: GET locked medium question → 200 with locked:true."""
    last_medium = _medium_qs[-1]
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/statistics/questions/{last_medium['id']}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("locked") is True
    assert "options" not in body
    assert "correct_option" not in body
    assert "starter_code" not in body or last_medium.get("subtype") == "numerical"


def test_tc_st22_locked_medium_submit_conceptual_returns_403():
    """TC-ST-22: Submit to locked conceptual question → 403."""
    locked_medium_conceptual = next(
        (q for q in _medium_qs if q.get("subtype") == "conceptual"), None
    )
    if locked_medium_conceptual is None:
        pytest.skip("No locked conceptual medium question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/statistics/submit", json={
            "question_id": locked_medium_conceptual["id"],
            "selected_option": 0,
        })
    assert r.status_code == 403


# ── Correct solve marks progress ───────────────────────────────────────────────

def test_tc_st23_correct_conceptual_solve_marks_solved_in_catalog():
    """TC-ST-23: Correct conceptual submission marks question solved in catalog."""
    if _easy_conceptual is None:
        pytest.skip("No easy conceptual question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        client.post("/api/statistics/submit", json={
            "question_id": _easy_conceptual["id"],
            "selected_option": _easy_conceptual["correct_option"],
        })
        r = client.get("/api/statistics/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    solved = next((q for q in easy_group["questions"] if q["id"] == _easy_conceptual["id"]), None)
    assert solved is not None
    assert solved["state"] == "solved"


def test_tc_st24_correct_numerical_solve_marks_solved_in_catalog():
    """TC-ST-24: Correct numerical submission marks question solved in catalog."""
    if _easy_numerical is None:
        pytest.skip("No easy numerical question available")
    with TestClient(app) as client:
        _make_user(client, plan="free")
        client.post("/api/statistics/submit", json={
            "question_id": _easy_numerical["id"],
            "code": _easy_numerical["expected_code"],
        })
        r = client.get("/api/statistics/catalog")
    body = r.json()
    easy_group = next(g for g in body["groups"] if g["difficulty"] == "easy")
    solved = next((q for q in easy_group["questions"] if q["id"] == _easy_numerical["id"]), None)
    assert solved is not None
    assert solved["state"] == "solved"


# ── Catalog loader integrity ───────────────────────────────────────────────────

def test_tc_st25_all_questions_have_required_base_fields():
    """TC-ST-25: Every question has id, title, subtype, difficulty, description, hints, concepts."""
    required = {"id", "title", "subtype", "difficulty", "description", "hints", "concepts"}
    for q in st_catalog._ALL_QUESTIONS:
        missing = required - set(q.keys())
        assert not missing, f"Question {q.get('id')} missing fields: {missing}"


def test_tc_st26_conceptual_questions_have_mcq_fields():
    """TC-ST-26: Conceptual questions have options, correct_option, explanation."""
    for q in st_catalog._ALL_QUESTIONS:
        if q.get("subtype") != "conceptual":
            continue
        assert "options" in q, f"Conceptual {q['id']} missing options"
        assert "correct_option" in q, f"Conceptual {q['id']} missing correct_option"
        assert "explanation" in q, f"Conceptual {q['id']} missing explanation"


def test_tc_st27_numerical_questions_have_code_fields():
    """TC-ST-27: Numerical questions have expected_code and test_cases."""
    for q in st_catalog._ALL_QUESTIONS:
        if q.get("subtype") != "numerical":
            continue
        assert "expected_code" in q, f"Numerical {q['id']} missing expected_code"
        assert "test_cases" in q, f"Numerical {q['id']} missing test_cases"
        assert isinstance(q["test_cases"], list) and len(q["test_cases"]) > 0


def test_tc_st28_question_ids_are_unique():
    """TC-ST-28: No duplicate IDs across the full question bank."""
    all_ids = [int(q["id"]) for q in st_catalog._ALL_QUESTIONS]
    assert len(all_ids) == len(set(all_ids)), "Duplicate question IDs found"


def test_tc_st29_id_ranges_respected():
    """TC-ST-29: All IDs fall within declared ranges per difficulty."""
    ranges = {"easy": (71001, 71999), "medium": (72001, 72999), "hard": (73001, 73999)}
    for q in st_catalog._ALL_QUESTIONS:
        lo, hi = ranges[q["difficulty"]]
        assert lo <= int(q["id"]) <= hi, (
            f"Question {q['id']} ({q['difficulty']}) out of range {lo}-{hi}"
        )


# ── Sample endpoint ────────────────────────────────────────────────────────────

def test_tc_st30_sample_easy_returns_question():
    """TC-ST-30: Sample endpoint returns a statistics question for easy difficulty."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/sample/statistics/easy")
    assert r.status_code == 200
    body = r.json()
    assert body.get("difficulty") == "easy"
    assert "subtype" in body


# ── Track registry ─────────────────────────────────────────────────────────────

def test_tc_st31_track_registry_entry():
    """TC-ST-31: statistics appears in the track registry with correct metadata."""
    from tracks import get_track
    t = get_track("statistics")
    assert t.slug == "statistics"
    assert t.db_topic == "statistics"
    assert t.eval_kind == "mixed"
    assert t.unlock_profile == "code"
    assert t.mixed_subtype is True
    assert t.in_mixed_mock is False
    assert t.label == "Statistics"
