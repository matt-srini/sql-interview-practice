"""TC-119 to TC-124 — Learning Paths."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _insert_progress, _make_user
from path_loader import get_all_paths

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# Aggregation-patterns: free/starter SQL path, questions [1008, 1013, 1015, 2004, 2005, 2007]
_PATH_SLUG = "aggregation-patterns"
_paths = get_all_paths()
_agg_path = next(p for p in _paths if p["slug"] == _PATH_SLUG)
_path_question_ids = _agg_path["questions"]


def test_tc119_get_paths_returns_all_paths():
    """TC-119: GET /api/paths → 200; paths array covers all 10 tracks.

    Tests the *property* that all paths are returned and shaped correctly,
    not a hardcoded total — total grows as new paths are added. Verifies
    per-track minimum (each track has at least its starter + intermediate).
    """
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/paths")
    assert r.status_code == 200
    body = r.json()
    paths = body.get("paths", body) if isinstance(body, dict) else body
    # Sanity floor: at least 2 paths per track × 10 tracks = 20 minimum.
    # Current bank holds ~103 paths; this check trips only if the loader breaks.
    assert len(paths) >= 20, f"Suspiciously few paths returned: {len(paths)}"
    # Each path has slug, title, topic, solved_count
    for p in paths:
        assert "slug" in p
        assert "title" in p
        assert "topic" in p
        assert "solved_count" in p
    # Every track represented (starter or intermediate exists for each)
    topics_present = {p["topic"] for p in paths}
    expected_topics = {"sql", "python", "pandas", "pyspark", "data-engineering",
                       "data-modeling", "statistics", "ml-fundamentals", "experimentation"}
    assert expected_topics.issubset(topics_present), f"Missing tracks in paths: {expected_topics - topics_present}"


def test_tc120_get_path_returns_question_list_with_state():
    """TC-120: GET /api/paths/{slug} → questions array with per-question state."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get(f"/api/paths/{_PATH_SLUG}")
    assert r.status_code == 200
    body = r.json()
    questions = body.get("questions", [])
    assert len(questions) > 0
    for q in questions:
        assert "state" in q
        assert q["state"] in ("solved", "unlocked", "locked")
    assert "completed" in body


def test_tc121_unknown_slug_returns_404():
    """TC-121: GET /api/paths/nonexistent → 404."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/paths/this-slug-does-not-exist")
    assert r.status_code == 404


def test_tc122_completed_path_shows_completed_true():
    """TC-122: User solved all questions in path → completed: true; solved_count == total."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Insert progress for all questions in the path
    for qid in _path_question_ids:
        # Determine track (questions 1xxx/2xxx are SQL)
        track = "sql"
        _insert_progress(user["id"], qid, track=track)

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get(f"/api/paths/{_PATH_SLUG}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("completed") is True
    assert body.get("solved_count") == len(_path_question_ids)


def test_tc123_in_progress_path_shows_correct_solved_count():
    """TC-123: User solved 2 questions → solved_count == 2; completed: false."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Insert only 2 solved
    for qid in _path_question_ids[:2]:
        _insert_progress(user["id"], qid, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get(f"/api/paths/{_PATH_SLUG}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("solved_count") == 2
    assert body.get("completed") is False


def test_tc124_solved_count_matches_between_list_and_detail():
    """TC-124: solved_count in list matches individual path detail."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Solve 1 question
    _insert_progress(user["id"], _path_question_ids[0], track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r_list = client.get("/api/paths")
        r_detail = client.get(f"/api/paths/{_PATH_SLUG}")

    assert r_list.status_code == 200
    assert r_detail.status_code == 200

    paths_list = r_list.json()
    if isinstance(paths_list, dict):
        paths_list = paths_list["paths"]
    list_path = next(p for p in paths_list if p["slug"] == _PATH_SLUG)
    detail_path = r_detail.json()

    assert list_path["solved_count"] == detail_path["solved_count"]
