"""TC-204 to TC-207 — Submission History."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _insert_submission, _make_user
from questions import get_questions_by_difficulty

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_sql_easy_qs = get_questions_by_difficulty()["easy"]
_q_id = _sql_easy_qs[0]["id"]


def test_tc204_get_submissions_returns_history():
    """TC-204: User with 3 submissions → GET /api/submissions returns 3 items."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for i in range(3):
        _insert_submission(user["id"], _q_id, is_correct=(i == 0), track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get(f"/api/submissions?track=sql&question_id={_q_id}")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 3
    for item in body:
        assert "is_correct" in item
        assert "submitted_at" in item


def test_tc205_limit_param_restricts_records():
    """TC-205: User with 5 submissions + limit=2 → returns 2 items."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(5):
        _insert_submission(user["id"], _q_id, is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get(f"/api/submissions?track=sql&question_id={_q_id}&limit=2")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_tc206_empty_history_returns_empty_array():
    """TC-206: No submissions for question → GET returns 200 with []."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get(f"/api/submissions?track=sql&question_id={_q_id}")
    assert r.status_code == 200
    assert r.json() == []


def test_tc207_unauthenticated_returns_401():
    """TC-207: Unauthenticated GET /api/submissions → 401."""
    with TestClient(app) as client:
        r = client.get(f"/api/submissions?track=sql&question_id={_q_id}")
    assert r.status_code == 401
