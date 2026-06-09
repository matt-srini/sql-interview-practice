"""TC-044 to TC-068 — Catalog & Unlock Logic."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _insert_progress, _make_user
from unlock import (
    FREE_HARD_CAP_CODE,
    FREE_HARD_CAP_MCQ,
    compute_unlock_state,
    normalize_plan,
)

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _make_mock_catalog(easy=30, medium=25, hard=20):
    """Build a minimal catalog dict with sequential IDs."""
    catalog = {
        "easy": [{"id": 1000 + i, "order": i} for i in range(easy)],
        "medium": [{"id": 2000 + i, "order": i} for i in range(medium)],
        "hard": [{"id": 3000 + i, "order": i} for i in range(hard)],
    }
    return catalog


def _easy_ids(n, catalog):
    return {q["id"] for q in catalog["easy"][:n]}


def _medium_ids(n, catalog):
    return {q["id"] for q in catalog["medium"][:n]}


# ---------------------------------------------------------------------------
# 3A. Free tier — code tracks
# ---------------------------------------------------------------------------

def test_tc044_fresh_free_user_all_easy_unlocked_no_medium():
    """TC-044: Free user zero solves → all easy unlocked, medium/hard locked."""
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
        r = client.get("/api/catalog")
    assert r.status_code == 200
    questions = r.json().get("questions", [])
    easy = [q for q in questions if q["difficulty"] == "easy"]
    medium = [q for q in questions if q["difficulty"] == "medium"]
    hard = [q for q in questions if q["difficulty"] == "hard"]

    assert all(q["state"] == "unlocked" for q in easy), "All easy should be unlocked"
    assert all(q["state"] == "locked" for q in medium), "All medium should be locked"
    assert all(q["state"] == "locked" for q in hard), "All hard should be locked"


def test_tc045_8_easy_unlocks_3_medium():
    """TC-045: 8 easy solved → 3 medium unlocked."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(8, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked_medium = [qid for qid in medium_ids if state[qid] == "unlocked"]
    locked_medium = [qid for qid in medium_ids if state[qid] == "locked"]
    assert len(unlocked_medium) == 3
    assert len(locked_medium) == len(medium_ids) - 3


def test_tc046_15_easy_unlocks_8_medium():
    """TC-046: 15 easy solved → 8 medium unlocked."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(15, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 8


def test_tc047_25_easy_unlocks_all_medium():
    """TC-047: 25 easy solved → all medium unlocked."""
    catalog = _make_mock_catalog(easy=30, medium=25)
    solved = _easy_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(medium_ids)


def test_tc048_8_medium_unlocks_3_hard():
    """TC-048: 25 easy + 8 medium → 3 hard unlocked."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(25, catalog) | _medium_ids(8, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 3


def test_tc049_15_medium_unlocks_8_hard():
    """TC-049: 25 easy + 15 medium → 8 hard unlocked."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(25, catalog) | _medium_ids(15, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 8


def test_tc050_hard_cap_enforced_at_8():
    """TC-050: Free cap = FREE_HARD_CAP_CODE (8) regardless of threshold table saying 15."""
    catalog = _make_mock_catalog(easy=30, medium=25, hard=20)
    solved = _easy_ids(25, catalog) | _medium_ids(22, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == FREE_HARD_CAP_CODE


def test_tc051_solved_questions_retain_solved_state():
    """TC-051: Already-solved questions have state 'solved'."""
    catalog = _make_mock_catalog()
    easy_id = catalog["easy"][0]["id"]
    solved = {easy_id}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert state[easy_id] == "solved"


def test_tc052_questions_beyond_unlocked_prefix_locked():
    """TC-052: 4th medium (beyond 3 unlocked) stays locked."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(8, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    # 4th medium question (index 3)
    fourth_medium_id = catalog["medium"][3]["id"]
    assert state[fourth_medium_id] == "locked"


# ---------------------------------------------------------------------------
# 3B. Free tier — PySpark higher thresholds
# ---------------------------------------------------------------------------

def test_tc053_9_easy_pyspark_medium_still_locked():
    """TC-053: 9 easy PySpark → medium still locked (threshold is 10)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(9, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 0


def test_tc054_10_easy_pyspark_unlocks_3_medium():
    """TC-054: 10 easy PySpark → 3 medium unlocked."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(10, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 3


def test_tc055_17_easy_pyspark_unlocks_8_medium():
    """TC-055: 17 easy PySpark → 8 medium unlocked."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(17, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 8


def test_tc056_25_easy_pyspark_unlocks_all_medium():
    """TC-056: 25 easy PySpark → all medium unlocked."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(medium_ids)


def test_tc057_12_medium_pyspark_unlocks_5_hard():
    """TC-057: 25 easy + 12 medium PySpark → 5 hard unlocked (= full MCQ cap)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(25, catalog) | _medium_ids(12, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 5


def test_tc058_pyspark_hard_cap_is_5():
    """TC-058: PySpark hard cap = FREE_HARD_CAP_MCQ (5)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(25, catalog) | _medium_ids(15, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == FREE_HARD_CAP_MCQ


# ---------------------------------------------------------------------------
# 3C. Threshold-only unlocks (path shortcuts removed)
# ---------------------------------------------------------------------------

def test_tc059_threshold_unlocks_first_medium_batch():
    """TC-059: 8 easy solved → exactly 3 medium unlocked (first threshold batch)."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    solved = _easy_ids(8, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 3


def test_tc060_threshold_unlocks_second_medium_batch():
    """TC-060: 15 easy solved → exactly 8 medium unlocked (second threshold batch)."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    solved = _easy_ids(15, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 8


def test_tc061_threshold_unlocks_all_medium():
    """TC-061: 25 easy solved → all medium unlocked."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    solved = _easy_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(medium_ids)


def test_tc062_no_path_shortcut_zero_easy_zero_medium():
    """TC-062: 0 easy, 0 medium solved → no medium or hard unlocked (no path shortcut)."""
    catalog = _make_mock_catalog()
    state = compute_unlock_state("free", set(), catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked_medium = [qid for qid in medium_ids if state[qid] == "unlocked"]
    unlocked_hard = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked_medium) == 0
    assert len(unlocked_hard) == 0


# ---------------------------------------------------------------------------
# 3D. Pro and Elite
# ---------------------------------------------------------------------------

def test_tc063_pro_all_unlocked():
    """TC-063: Pro user → all questions unlocked regardless of solves."""
    catalog = _make_mock_catalog()
    state = compute_unlock_state("pro", set(), catalog, track="sql")

    for difficulty in ("easy", "medium", "hard"):
        for q in catalog[difficulty]:
            assert state[q["id"]] == "unlocked", f"{q['id']} should be unlocked for Pro"


def test_tc064_elite_all_tracks_unlocked():
    """TC-064: Elite user → full catalog across all 4 tracks."""
    from python_questions import get_questions_by_difficulty as py_qs
    from pandas_questions import get_questions_by_difficulty as pd_qs
    from pyspark_questions import get_questions_by_difficulty as spark_qs
    from questions import get_questions_by_difficulty as sql_qs

    for track_name, catalog_fn in [
        ("sql", sql_qs),
        ("python", py_qs),
        ("pandas", pd_qs),
        ("pyspark", spark_qs),
    ]:
        catalog = catalog_fn()
        state = compute_unlock_state("elite", set(), catalog, track=track_name)
        for diff in ("easy", "medium", "hard"):
            for q in catalog[diff]:
                assert state[q["id"]] == "unlocked", f"{track_name}:{diff}:{q['id']} should be unlocked for Elite"


def test_tc065_pro_no_hard_cap():
    """TC-065: Pro user gets ALL hard questions (no cap)."""
    from questions import get_questions_by_difficulty
    catalog = get_questions_by_difficulty()
    state = compute_unlock_state("pro", set(), catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(hard_ids)
    assert len(hard_ids) >= 29


# ---------------------------------------------------------------------------
# 3E. Lifetime plan normalization
# ---------------------------------------------------------------------------

def test_tc066_lifetime_pro_normalizes_to_pro():
    """TC-066: lifetime_pro normalizes to pro."""
    assert normalize_plan("lifetime_pro") == "pro"

    catalog = _make_mock_catalog()
    state_lifetime = compute_unlock_state("lifetime_pro", set(), catalog, track="sql")
    state_pro = compute_unlock_state("pro", set(), catalog, track="sql")
    assert state_lifetime == state_pro


def test_tc067_lifetime_elite_normalizes_to_elite():
    """TC-067: lifetime_elite normalizes to elite."""
    assert normalize_plan("lifetime_elite") == "elite"

    catalog = _make_mock_catalog()
    state_lifetime = compute_unlock_state("lifetime_elite", set(), catalog, track="sql")
    state_elite = compute_unlock_state("elite", set(), catalog, track="sql")
    assert state_lifetime == state_elite
