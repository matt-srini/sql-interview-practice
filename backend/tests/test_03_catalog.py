"""TC-044 to TC-068 — Catalog & Unlock Logic.

Flat free-tier model: Free = all easy unlocked, all medium and hard locked.
No thresholds, no batch unlocks, no caps.
"""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _insert_progress, _make_user
from unlock import (
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
# 3A. Free tier — flat model (easy only)
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


def test_tc045_free_all_easy_unlocked_regardless_of_solves():
    """TC-045: Free user — all easy always unlocked (no threshold needed)."""
    catalog = _make_mock_catalog()
    # Even with no solves, all easy are unlocked
    state = compute_unlock_state("free", set(), catalog, track="sql")

    easy_ids = [q["id"] for q in catalog["easy"]]
    unlocked_easy = [qid for qid in easy_ids if state[qid] == "unlocked"]
    assert len(unlocked_easy) == len(easy_ids)


def test_tc046_free_all_medium_locked():
    """TC-046: Free user — all medium locked regardless of easy solves."""
    catalog = _make_mock_catalog()
    # Solve all easy — medium still locked
    solved = _easy_ids(30, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    medium_ids = [q["id"] for q in catalog["medium"]]
    locked_medium = [qid for qid in medium_ids if state[qid] == "locked"]
    assert len(locked_medium) == len(medium_ids)


def test_tc047_free_all_hard_locked():
    """TC-047: Free user — all hard locked regardless of medium solves."""
    catalog = _make_mock_catalog()
    # Solve all easy + all medium — hard still locked
    solved = _easy_ids(30, catalog) | _medium_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    locked_hard = [qid for qid in hard_ids if state[qid] == "locked"]
    assert len(locked_hard) == len(hard_ids)


def test_tc048_free_medium_locked_even_with_many_easy_solves():
    """TC-048: Free user — medium stays locked even after solving many easy questions."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked_medium = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked_medium) == 0


def test_tc049_free_hard_locked_even_with_many_medium_solves():
    """TC-049: Free user — hard stays locked even after solving many medium questions."""
    catalog = _make_mock_catalog()
    solved = _easy_ids(30, catalog) | _medium_ids(15, catalog)
    state = compute_unlock_state("free", solved, catalog, track="sql")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked_hard = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked_hard) == 0


def test_tc050_free_flat_model_all_tracks():
    """TC-050: Free flat model applies to both code and MCQ tracks."""
    for track in ("sql", "python", "pandas", "pyspark", "data-engineering"):
        catalog = _make_mock_catalog()
        state = compute_unlock_state("free", set(), catalog, track=track)

        easy_ids = [q["id"] for q in catalog["easy"]]
        medium_ids = [q["id"] for q in catalog["medium"]]
        hard_ids = [q["id"] for q in catalog["hard"]]

        unlocked_easy = [qid for qid in easy_ids if state[qid] == "unlocked"]
        locked_medium = [qid for qid in medium_ids if state[qid] == "locked"]
        locked_hard = [qid for qid in hard_ids if state[qid] == "locked"]

        assert len(unlocked_easy) == len(easy_ids), f"{track}: all easy should be unlocked"
        assert len(locked_medium) == len(medium_ids), f"{track}: all medium should be locked"
        assert len(locked_hard) == len(hard_ids), f"{track}: all hard should be locked"


def test_tc051_solved_questions_retain_solved_state():
    """TC-051: Already-solved questions have state 'solved'."""
    catalog = _make_mock_catalog()
    easy_id = catalog["easy"][0]["id"]
    solved = {easy_id}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert state[easy_id] == "solved"


def test_tc052_free_solved_medium_retains_solved_state():
    """TC-052: A medium question solved before downgrade retains 'solved' state."""
    catalog = _make_mock_catalog()
    medium_id = catalog["medium"][0]["id"]
    solved = {medium_id}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    # Medium is locked for free, but solved overrides
    assert state[medium_id] == "solved"


# ---------------------------------------------------------------------------
# 3B. Free tier — zero solves baseline
# ---------------------------------------------------------------------------

def test_tc053_zero_easy_free_all_easy_unlocked():
    """TC-053: 0 easy solved, Free → all easy unlocked (no threshold needed)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="pyspark")

    easy_ids = [q["id"] for q in catalog["easy"]]
    unlocked = [qid for qid in easy_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(easy_ids)


def test_tc054_zero_easy_free_medium_locked():
    """TC-054: 0 easy solved, Free → all medium locked."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    locked = [qid for qid in medium_ids if state[qid] == "locked"]
    assert len(locked) == len(medium_ids)


def test_tc055_zero_easy_free_hard_locked():
    """TC-055: 0 easy solved, Free → all hard locked."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="pyspark")

    hard_ids = [q["id"] for q in catalog["hard"]]
    locked = [qid for qid in hard_ids if state[qid] == "locked"]
    assert len(locked) == len(hard_ids)


def test_tc056_many_easy_pyspark_medium_still_locked():
    """TC-056: Many easy PySpark solved → medium still locked (flat free model)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(25, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    medium_ids = [q["id"] for q in catalog["medium"]]
    unlocked = [qid for qid in medium_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 0


def test_tc057_many_medium_pyspark_hard_still_locked():
    """TC-057: Many medium PySpark solved → hard still locked (flat free model)."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(40, catalog) | _medium_ids(12, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 0


def test_tc058_free_hard_locked_no_cap():
    """TC-058: Free plan has no cap — hard is always locked, not partially accessible."""
    catalog = _make_mock_catalog(easy=40, medium=20, hard=15)
    solved = _easy_ids(40, catalog) | _medium_ids(20, catalog)
    state = compute_unlock_state("free", solved, catalog, track="pyspark")

    hard_ids = [q["id"] for q in catalog["hard"]]
    unlocked = [qid for qid in hard_ids if state[qid] == "unlocked"]
    assert len(unlocked) == 0


# ---------------------------------------------------------------------------
# 3C. Flat model baseline checks
# ---------------------------------------------------------------------------

def test_tc059_free_easy_all_unlocked_zero_solves():
    """TC-059: Free zero solves → all easy unlocked."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="sql")
    easy_ids = [q["id"] for q in catalog["easy"]]
    unlocked = [qid for qid in easy_ids if state[qid] == "unlocked"]
    assert len(unlocked) == len(easy_ids)


def test_tc060_free_medium_locked_zero_solves():
    """TC-060: Free zero solves → all medium locked."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    locked = [qid for qid in medium_ids if state[qid] == "locked"]
    assert len(locked) == len(medium_ids)


def test_tc061_free_hard_locked_zero_solves():
    """TC-061: Free zero solves → all hard locked."""
    catalog = _make_mock_catalog(easy=30, medium=20, hard=15)
    state = compute_unlock_state("free", set(), catalog, track="sql")
    hard_ids = [q["id"] for q in catalog["hard"]]
    locked = [qid for qid in hard_ids if state[qid] == "locked"]
    assert len(locked) == len(hard_ids)


def test_tc062_free_no_medium_hard_unlocked():
    """TC-062: Free plan — medium and hard never unlock regardless of easy/medium solves."""
    catalog = _make_mock_catalog()
    # Solve everything
    all_ids = (
        {q["id"] for q in catalog["easy"]}
        | {q["id"] for q in catalog["medium"]}
        | {q["id"] for q in catalog["hard"]}
    )
    state = compute_unlock_state("free", all_ids, catalog, track="sql")
    medium_ids = [q["id"] for q in catalog["medium"]]
    hard_ids = [q["id"] for q in catalog["hard"]]
    # All should be "solved" (override), not "unlocked"
    # Medium and hard that were NOT solved should be locked
    unsolved_medium = [qid for qid in medium_ids if qid not in all_ids]
    unsolved_hard = [qid for qid in hard_ids if qid not in all_ids]
    # In this test all ids are solved, so verify solved state overrides
    assert all(state[qid] == "solved" for qid in medium_ids)
    assert all(state[qid] == "solved" for qid in hard_ids)
    # Now with zero solves
    state2 = compute_unlock_state("free", set(), catalog, track="sql")
    assert all(state2[qid] == "locked" for qid in medium_ids)
    assert all(state2[qid] == "locked" for qid in hard_ids)


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
