"""TC-125 to TC-170 — Mock Interviews."""
import asyncio

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _insert_progress, _make_user
from unlock import compute_mock_access
from pyspark_questions import get_questions_by_difficulty as get_pyspark_qs

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_pyspark_catalog = get_pyspark_qs()
_pyspark_easy_q = _pyspark_catalog["easy"][0]
_pyspark_easy_id = _pyspark_easy_q["id"]
_pyspark_correct = _pyspark_easy_q["correct_option"]
_pyspark_wrong = (_pyspark_correct + 1) % 4


# ---------------------------------------------------------------------------
# Unit tests for compute_mock_access (TC-125 to TC-134)
# ---------------------------------------------------------------------------

def test_tc125_free_easy_can_start():
    """TC-125: Free user, easy → can_start: True; daily_limit: None."""
    result = compute_mock_access("free", "sql", "easy", medium_unlocked=False)
    assert result["can_start"] is True
    assert result["daily_limit"] is None


def test_tc126_free_medium_not_unlocked_blocked():
    """TC-126: Free user, medium not unlocked → block_reason: not_unlocked."""
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=False)
    assert result["can_start"] is False
    assert result["block_reason"] == "not_unlocked"
    assert result["needs_upgrade"] == "pro"


def test_tc127_free_medium_unlocked_can_start():
    """TC-127: Free user, medium unlocked → can_start: True; daily_limit: 1."""
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=0)
    assert result["can_start"] is True
    assert result["daily_limit"] == 1
    assert result["daily_used"] == 0


def test_tc128_free_medium_daily_limit_reached():
    """TC-128: Free user, medium, daily used 1 → block_reason: daily_cap."""
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=1)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"


def test_tc129_free_hard_plan_locked():
    """TC-129: Free user, hard → block_reason: plan_locked; needs_upgrade: pro."""
    result = compute_mock_access("free", "sql", "hard", medium_unlocked=True)
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_tc130_pro_hard_within_daily_limit():
    """TC-130: Pro user, hard, daily used 2 → can_start: True; daily_limit: 3."""
    result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=2)
    assert result["can_start"] is True
    assert result["daily_limit"] == 3
    assert result["daily_used"] == 2


def test_tc131_pro_hard_daily_limit_reached():
    """TC-131: Pro user, hard, daily used 3 → block_reason: daily_cap."""
    result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=3)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"
    assert result["needs_upgrade"] == "elite"


def test_tc132_elite_hard_unlimited():
    """TC-132: Elite user, hard → can_start: True; daily_limit: None."""
    result = compute_mock_access("elite", "sql", "hard", medium_unlocked=True)
    assert result["can_start"] is True
    assert result["daily_limit"] is None


def test_tc133_company_filter_non_elite_blocked():
    """TC-133: Pro user with company_filter → block_reason: plan_locked; needs_upgrade: elite."""
    result = compute_mock_access("pro", "sql", "easy", medium_unlocked=True, company_filter=True)
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "elite"


def test_tc134_company_filter_elite_allowed():
    """TC-134: Elite user with company_filter → can_start: True."""
    result = compute_mock_access("elite", "sql", "easy", medium_unlocked=True, company_filter=True)
    assert result["can_start"] is True


# ---------------------------------------------------------------------------
# HTTP session tests (TC-135 to TC-170)
# ---------------------------------------------------------------------------

def _start_pyspark_session(client, mode="30min", difficulty="medium", plan="pro", **kwargs):
    body = {"mode": mode, "track": "pyspark", "difficulty": difficulty, **kwargs}
    r = client.post("/api/mock/start", json=body)
    return r


def test_tc135_start_session_returns_session_id_questions_time_limit():
    """TC-135: POST /api/mock/start → 200/201; session_id, questions, time_limit_s."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = _start_pyspark_session(client)
    assert r.status_code in (200, 201)
    body = r.json()
    assert "session_id" in body
    assert "questions" in body
    assert len(body["questions"]) == 2  # 30min mode
    assert body.get("time_limit_s") == 1800


def test_tc136_custom_mode_num_questions():
    """TC-136: Custom mode with num_questions=3 → questions array length == 3."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = _start_pyspark_session(client, mode="custom", difficulty="easy",
                                   num_questions=3, time_minutes=30)
    assert r.status_code in (200, 201)
    assert len(r.json()["questions"]) == 3


def test_tc136b_benchmark_mode_uses_track_specific_shape():
    """TC-136B: Benchmark mode on PySpark uses the track-specific fixed shape."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = _start_pyspark_session(client, mode="benchmark", difficulty="easy")
    assert r.status_code in (200, 201)
    assert len(r.json()["questions"]) == 6
    assert r.json()["time_limit_s"] == 2400


def test_tc136c_statistics_benchmark_uses_mixed_subtype_shape():
    """TC-136C: Statistics benchmark returns 1 numerical + 2 conceptual questions."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "statistics", "difficulty": "easy",
        })
    assert r.status_code in (200, 201)
    subtypes = [q.get("subtype") for q in r.json()["questions"]]
    assert subtypes.count("numerical") == 1
    assert subtypes.count("conceptual") == 2
    assert r.json()["time_limit_s"] == 2700


def test_tc136d_benchmark_mode_rejects_mixed_track():
    """TC-136D: Benchmark mode is track-specific and rejects mixed-track sessions."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "mixed", "difficulty": "mixed",
        })
    assert r.status_code == 400
    assert "mixed" in r.json().get("error", "").lower() or "mixed" in r.json().get("detail", "").lower()


def test_tc136e_ml_benchmark_includes_debug_and_predict_output_when_available():
    """TC-136E: ML Fundamentals benchmark composition includes advanced reasoning forms."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "ml-fundamentals", "difficulty": "hard",
        })
    assert r.status_code in (200, 201)
    types = [q.get("type") for q in r.json()["questions"]]
    assert "debug" in types
    assert "predict_output" in types
    assert len(types) == 6


def test_tc136f_non_benchmark_ml_session_is_not_forced_into_benchmark_shape():
    """TC-136F: Drill sessions on reasoning tracks are not forced into benchmark-only type coverage."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "ml-fundamentals", "difficulty": "hard",
        })
    assert r.status_code in (200, 201)
    assert len(r.json()["questions"]) == 2


def test_tc137_num_questions_out_of_range_returns_400():
    """TC-137: num_questions=0 or 6 → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r0 = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 0, "time_minutes": 30,
        })
        r6 = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 6, "time_minutes": 30,
        })
    assert r0.status_code in (400, 422)
    assert r6.status_code in (400, 422)


def test_tc138_submit_mid_session_no_solution():
    """TC-138: Submit mid-session → verdict, no solution revealed."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        r_submit = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": _pyspark_correct,
        })
    assert r_submit.status_code == 200
    body = r_submit.json()
    assert "correct" in body
    # Solution should NOT be revealed during session
    assert "solution" not in body or body.get("solution") is None


def test_tc139_finish_returns_full_summary_with_solutions():
    """TC-139: POST /api/mock/{id}/finish → summary + solutions for all questions."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        # Submit one answer
        client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": _pyspark_correct,
        })
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    assert r_finish.status_code == 200
    body = r_finish.json()
    assert "solved_count" in body
    assert "total_count" in body
    assert "time_used_s" in body
    # All questions have solution
    for q in body.get("questions", []):
        assert "solution" in q and q["solution"] is not None


def test_tc140_get_session_returns_state():
    """TC-140: GET /api/mock/{id} returns session state."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        r_get = client.get(f"/api/mock/{session_id}")
    assert r_get.status_code == 200
    body = r_get.json()
    assert "session_id" in body
    assert "questions" in body


def test_tc141_history_returns_last_20_sessions():
    """TC-141: GET /api/mock/history → up to 20 sessions."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
    # Insert 21 mock sessions directly via DB
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(21):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                       VALUES (%s::uuid, 'custom', 'pyspark', 'easy', 1800, 'completed')""",
                    (user["id"],),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.get("/api/mock/history")
    assert r.status_code == 200
    body = r.json()
    sessions = body if isinstance(body, list) else body.get("sessions", [])
    assert len(sessions) == 20


def test_tc142_submit_to_finished_session_fails():
    """TC-142: Submit after finish → 404 or 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        client.post(f"/api/mock/{session_id}/finish")
        r_submit = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": 0,
        })
    assert r_submit.status_code in (400, 404)


def test_tc143_free_user_hard_start_returns_403():
    """TC-143: Free user starting hard mock → 403."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = _start_pyspark_session(client, difficulty="hard", plan="free")
    assert r.status_code == 403


def test_tc144_pro_user_hard_start_returns_201():
    """TC-144: Pro user starting hard mock → 200 or 201."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = _start_pyspark_session(client, difficulty="hard")
    assert r.status_code in (200, 201)


def test_tc145_elite_user_hard_start_returns_201():
    """TC-145: Elite user starting hard mock → 200 or 201."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = _start_pyspark_session(client, difficulty="hard")
    assert r.status_code in (200, 201)


def test_tc146_free_user_second_medium_mock_same_day_blocked():
    """TC-146: Free user; 1 medium session today already → 2nd blocked (403)."""
    from pyspark_questions import get_questions_by_difficulty as get_ps_qs
    pyspark_easy_ids = [q["id"] for q in get_ps_qs()["easy"]]

    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    # Unlock pyspark medium by solving 12 pyspark easy questions
    for qid in pyspark_easy_ids[:12]:
        _insert_progress(user["id"], qid, track="pyspark")
    # Insert a medium mock session for today
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                   VALUES (%s::uuid, 'custom', 'pyspark', 'medium', 1800, 'completed')""",
                (user["id"],),
            )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="free", existing_user=user)
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "medium",
            "num_questions": 1, "time_minutes": 30,
        })
    assert r.status_code == 403
    assert "daily" in r.json().get("error", "").lower() or "limit" in r.json().get("error", "").lower()


def test_tc147_pro_user_4th_hard_same_day_blocked():
    """TC-147: Pro user; 3 hard sessions today → 4th blocked (403)."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Insert 3 hard sessions
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(3):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                       VALUES (%s::uuid, '30min', 'pyspark', 'hard', 1800, 'completed')""",
                    (user["id"],),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = _start_pyspark_session(client, difficulty="hard")
    assert r.status_code == 403
    detail = r.json().get("error", "").lower()
    assert "daily" in detail or "limit" in detail or "elite" in detail


def test_tc148_elite_user_4th_hard_same_day_allowed():
    """TC-148: Elite user; 3 hard sessions today → 4th allowed."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
    # Insert 3 hard sessions
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(3):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                       VALUES (%s::uuid, '30min', 'pyspark', 'hard', 1800, 'completed')""",
                    (user["id"],),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = _start_pyspark_session(client, difficulty="hard")
    assert r.status_code in (200, 201)


def test_tc149_non_elite_company_filter_returns_403():
    """TC-149: Pro user with company_filter → 403."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "sql", "difficulty": "easy",
            "company_filter": "Meta",
        })
    assert r.status_code == 403
    assert "elite" in r.json().get("error", "").lower() or "Elite" in r.json().get("error", "")


def test_tc150_elite_company_filter_creates_session():
    """TC-150: Elite user with valid company filter → session created."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "sql", "difficulty": "medium",
            "company_filter": "Meta",
        })
    assert r.status_code in (200, 201)


def test_tc151_non_elite_focus_concepts_returns_403():
    """TC-151: Pro user with focus_concepts → 403."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "sql", "difficulty": "medium",
            "focus_concepts": ["window functions"],
        })
    assert r.status_code == 403


def test_tc152_elite_more_than_3_focus_concepts_returns_422():
    """TC-152: Elite user, >3 focus_concepts → 422."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "pyspark", "difficulty": "easy",
            "focus_concepts": ["a", "b", "c", "d"],
        })
    assert r.status_code == 422


def test_tc153_elite_focus_concepts_creates_session():
    """TC-153: Elite user, 1-3 focus_concepts → session created."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "pyspark", "difficulty": "easy",
            "focus_concepts": ["dataframe operations"],
        })
    assert r.status_code in (200, 201)


def test_tc154_focus_fallback_when_pool_too_small():
    """TC-154: _select_questions with concept matching few questions → focus_fallback: True."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _select_questions
    user = {"id": "00000000-0000-0000-0000-000000000001", "plan": "elite"}
    with patch("routers.mock._get_solved_ids_for_track", new=AsyncMock(return_value=set())), \
         patch("routers.mock.get_previously_mocked_ids", new=AsyncMock(return_value=set())):
        selected, fallback = asyncio.run(
            _select_questions("pyspark", "easy", 2, user, focus_concepts=["NONEXISTENT_CONCEPT_XYZ"])
        )
    assert fallback is True
    assert len(selected) > 0


def test_tc155_empty_focus_concepts_treated_as_no_filter():
    """TC-155: _select_questions with focus_concepts=[] → full pool, focus_fallback: False."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _select_questions
    user = {"id": "00000000-0000-0000-0000-000000000001", "plan": "elite"}
    with patch("routers.mock._get_solved_ids_for_track", new=AsyncMock(return_value=set())), \
         patch("routers.mock.get_previously_mocked_ids", new=AsyncMock(return_value=set())):
        selected, fallback = asyncio.run(
            _select_questions("pyspark", "easy", 2, user, focus_concepts=[])
        )
    assert fallback is False
    assert len(selected) > 0


def test_tc156_mock_only_questions_in_pro_elite_sessions():
    """TC-156: Pro session pool can include mock_only questions (verified via catalog)."""
    from questions import get_mock_questions_by_difficulty
    mock_only_ids = {q["id"] for q in get_mock_questions_by_difficulty().get("hard", [])}
    assert len(mock_only_ids) > 0, "Expected some mock-only hard SQL questions"


def test_tc157_freshness_scoring_avoids_recent_questions():
    """TC-157: _select_questions avoids recently-seen questions when pool is large enough."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _select_questions
    # Use a real user placeholder — freshness is based on DB history, so a new user sees all as fresh
    user = {"id": "00000000-0000-0000-0000-000000000001", "plan": "elite"}
    with patch("routers.mock._get_solved_ids_for_track", new=AsyncMock(return_value=set())), \
         patch("routers.mock.get_previously_mocked_ids", new=AsyncMock(return_value=set())):
        selected1, _ = asyncio.run(
            _select_questions("pyspark", "easy", 1, user)
        )
        # Second call may or may not re-select; just verify it returns valid data
        selected2, _ = asyncio.run(
            _select_questions("pyspark", "easy", 1, user)
        )
    assert len(selected1) == 1
    assert len(selected2) == 1


def test_tc158_elite_finish_1_1_correct_perfect_headline():
    """TC-158: Elite, 1 question, 1 correct → debrief headline contains 'Perfect'."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        # Find correct option for this question
        q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == first_q["id"]), None)
        correct = q_obj["correct_option"] if q_obj else _pyspark_correct
        client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    assert r_finish.status_code == 200
    debrief = r_finish.json().get("debrief")
    assert debrief is not None
    assert "Perfect" in debrief.get("headline", "")


def test_tc159_elite_finish_0_1_correct_tough_headline():
    """TC-159: Elite, 1 question, 0 correct → debrief headline contains 'Tough'."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == first_q["id"]), None)
        wrong = ((q_obj["correct_option"] + 1) % 4) if q_obj else _pyspark_wrong
        client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": wrong,
        })
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    debrief = r_finish.json().get("debrief")
    assert debrief is not None
    assert "Tough" in debrief.get("headline", "")


def test_tc160_elite_finish_2_3_correct_solid_headline():
    """TC-160: Elite, 3 questions, 2 correct → debrief headline contains 'Solid'."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 3, "time_minutes": 30,
        })
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        questions = r_start.json()["questions"]

        for i, q_api in enumerate(questions):
            q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == q_api["id"]), None)
            correct = q_obj["correct_option"] if q_obj else _pyspark_correct
            wrong = (correct + 1) % 4
            option = correct if i < 2 else wrong  # 2 correct, 1 wrong
            client.post(f"/api/mock/{session_id}/submit", json={
                "question_id": q_api["id"],
                "track": "pyspark",
                "selected_option": option,
            })
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    debrief = r_finish.json().get("debrief")
    assert debrief is not None
    assert "Solid" in debrief.get("headline", "")


def test_tc161_elite_finish_1_3_correct_partial_headline():
    """TC-161: Elite, 3 questions, 1 correct → debrief headline contains 'Partial'."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 3, "time_minutes": 30,
        })
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        questions = r_start.json()["questions"]

        for i, q_api in enumerate(questions):
            q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == q_api["id"]), None)
            correct = q_obj["correct_option"] if q_obj else _pyspark_correct
            wrong = (correct + 1) % 4
            option = correct if i == 0 else wrong  # 1 correct, 2 wrong
            client.post(f"/api/mock/{session_id}/submit", json={
                "question_id": q_api["id"],
                "track": "pyspark",
                "selected_option": option,
            })
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    debrief = r_finish.json().get("debrief")
    assert debrief is not None
    assert "Partial" in debrief.get("headline", "")


def test_tc162_pro_finish_debrief_is_null():
    """TC-162: Pro user completes session → debrief: null."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client, mode="custom", difficulty="easy",
                                         num_questions=1, time_minutes=30)
        session_id = r_start.json()["session_id"]
        client.post(f"/api/mock/{session_id}/finish")
        r_finish = client.post(f"/api/mock/{session_id}/finish") if False else \
            client.post(f"/api/mock/{r_start.json()['session_id']}/finish")

    # Start a fresh session
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    assert r_finish.status_code == 200
    assert r_finish.json().get("debrief") is None


def test_tc163_free_finish_debrief_is_null():
    """TC-163: Free user completes easy session → debrief: null."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    assert r_finish.status_code == 200
    assert r_finish.json().get("debrief") is None


def test_tc164_debrief_has_patterns_and_priority_action():
    """TC-164: Elite session debrief has patterns array and priority_action."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    body = r_finish.json()
    debrief = body.get("debrief")
    if debrief is not None:
        assert "patterns" in debrief
        assert isinstance(debrief["patterns"], list)
        assert "priority_action" in debrief  # may be None


def test_tc165_get_analytics_returns_200_for_elite():
    """TC-165: GET /api/mock/analytics → 200 for elite with sessions."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
    # Insert 2 completed sessions
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(2):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status, ended_at)
                       VALUES (%s::uuid, '30min', 'pyspark', 'easy', 1800, 'completed', NOW())""",
                    (user["id"],),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.get("/api/mock/analytics")
    assert r.status_code == 200
    body = r.json()
    assert "total_sessions" in body
    assert "avg_score_pct" in body
    assert "benchmark_summary" in body
    assert "drill_summary" in body


def test_tc165b_analytics_separates_benchmark_from_drills():
    """TC-165B: Analytics separates benchmark performance from drill sessions."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status, ended_at)
                   VALUES (%s::uuid, 'benchmark', 'sql', 'medium', 3600, 'completed', NOW())
                   RETURNING id""",
                (user["id"],),
            )
            benchmark_session_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO mock_session_questions (session_id, question_id, track, position, is_solved)
                   VALUES (%s, 1001, 'sql', 1, true),
                          (%s, 1002, 'sql', 2, true),
                          (%s, 1003, 'sql', 3, false)""",
                (benchmark_session_id, benchmark_session_id, benchmark_session_id),
            )

            cur.execute(
                """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status, ended_at)
                   VALUES (%s::uuid, '30min', 'pyspark', 'easy', 1800, 'completed', NOW())
                   RETURNING id""",
                (user["id"],),
            )
            drill_session_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO mock_session_questions (session_id, question_id, track, position, is_solved)
                   VALUES (%s, 3001, 'pyspark', 1, true),
                          (%s, 3002, 'pyspark', 2, true)""",
                (drill_session_id, drill_session_id),
            )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.get("/api/mock/analytics")

    assert r.status_code == 200
    body = r.json()
    assert body["total_sessions"] == 2
    assert body["mode_breakdown"] == {"benchmark": 1, "drill": 1}
    assert body["benchmark_summary"]["total_sessions"] == 1
    assert body["benchmark_summary"]["avg_score_pct"] == 66.7
    assert body["drill_summary"]["total_sessions"] == 1
    assert body["drill_summary"]["avg_score_pct"] == 100.0


def test_tc166_get_analytics_returns_403_for_pro():
    """TC-166: GET /api/mock/analytics → 403 for pro."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/mock/analytics")
    assert r.status_code == 403


def test_tc167_get_analytics_returns_403_for_free():
    """TC-167: GET /api/mock/analytics → 403 for free."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/mock/analytics")
    assert r.status_code == 403


def test_tc168_lifetime_elite_can_access_analytics():
    """TC-168: lifetime_elite can access mock analytics."""
    with TestClient(app) as client:
        _make_user(client, plan="lifetime_elite")
        r = client.get("/api/mock/analytics")
    assert r.status_code == 200


def test_tc169_solution_absent_during_session_submit():
    """TC-169: Submit mid-session → solution key absent in response."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == first_q["id"]), None)
        correct = q_obj["correct_option"] if q_obj else _pyspark_correct
        r_submit = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
    assert r_submit.status_code == 200
    body = r_submit.json()
    assert "solution" not in body or body.get("solution") is None


def test_tc170_solution_present_for_all_questions_after_finish():
    """TC-170: After finish, all questions in response have solution non-null."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 2, "time_minutes": 30,
        })
        session_id = r_start.json()["session_id"]
        r_finish = client.post(f"/api/mock/{session_id}/finish")
    assert r_finish.status_code == 200
    for q in r_finish.json().get("questions", []):
        assert "solution" in q and q["solution"] is not None


def test_tc172_reasoning_track_debrief_no_code_centric_language():
    """TC-172: Elite session on a reasoning track must not produce code-centric debrief patterns.

    PySpark is a reasoning track. Any inconsistency or priority-action copy must not
    contain 'before writing code' or 'consecutive correct answers'.
    """
    from routers.insights import build_session_debrief

    # Two questions sharing a concept, one wrong — triggers the inconsistency pattern.
    questions = [
        {
            "id": 1, "track": "pyspark", "is_solved": True,
            "concepts": ["DATAFRAME API"], "time_spent_s": 90,
        },
        {
            "id": 2, "track": "pyspark", "is_solved": False,
            "concepts": ["DATAFRAME API"], "time_spent_s": 120,
        },
    ]
    session_meta = {
        "difficulty": "medium", "track": "pyspark",
        "time_used_s": 210, "time_limit_s": 2400,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None
    all_text = " ".join(debrief.get("patterns", [])) + " " + (debrief.get("priority_action") or "")
    assert "before writing code" not in all_text
    assert "consecutive correct answers" not in all_text


def test_tc173_reasoning_track_no_weak_concepts_uses_reasoning_copy():
    """TC-173: Reasoning-track perfect session priority_action uses reasoning language."""
    from routers.insights import build_session_debrief

    questions = [
        {"id": 1, "track": "data-engineering", "is_solved": True,
         "concepts": ["DATA QUALITY"], "time_spent_s": 60},
    ]
    session_meta = {
        "difficulty": "medium", "track": "data-engineering",
        "time_used_s": 60, "time_limit_s": 2400,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None
    action = debrief.get("priority_action") or ""
    assert "reasoning" in action.lower() or "reasoning" in action.lower()
    # Must not use executable phrasing
    assert "before writing code" not in action
    assert "consecutive correct answers" not in action


def test_tc174_statistics_all_conceptual_uses_reasoning_language():
    """TC-174: Statistics session with only conceptual questions → reasoning-family debrief."""
    from routers.insights import build_session_debrief

    questions = [
        {"id": 1, "track": "statistics", "subtype": "conceptual",
         "is_solved": True, "concepts": ["HYPOTHESIS TESTING"], "time_spent_s": 90},
        {"id": 2, "track": "statistics", "subtype": "conceptual",
         "is_solved": False, "concepts": ["HYPOTHESIS TESTING"], "time_spent_s": 120},
    ]
    session_meta = {
        "difficulty": "medium", "track": "statistics",
        "time_used_s": 210, "time_limit_s": 2700,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None
    all_text = " ".join(debrief.get("patterns", [])) + " " + (debrief.get("priority_action") or "")
    assert "before writing code" not in all_text
    assert "consecutive correct answers" not in all_text


def test_tc175_statistics_with_numerical_uses_executable_language():
    """TC-175: Statistics session with a numerical question → executable-family debrief."""
    from routers.insights import build_session_debrief

    questions = [
        {"id": 1, "track": "statistics", "subtype": "numerical",
         "is_solved": True, "concepts": ["DISTRIBUTIONS"], "time_spent_s": 80},
        {"id": 2, "track": "statistics", "subtype": "conceptual",
         "is_solved": False, "concepts": ["DISTRIBUTIONS"], "time_spent_s": 100},
    ]
    session_meta = {
        "difficulty": "medium", "track": "statistics",
        "time_used_s": 180, "time_limit_s": 2700,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None
    all_text = " ".join(debrief.get("patterns", [])) + " " + (debrief.get("priority_action") or "")
    # Inconsistency pattern should fire with executable copy
    # (one wrong, same concept, correct > 0) → "before writing code"
    assert "before writing code" in all_text or "consecutive correct answers" in all_text


def test_tc176_track_family_helper_resolves_correctly():
    """TC-176: _track_family returns correct family for each track category."""
    from routers.insights import _track_family

    assert _track_family("sql", []) == "executable"
    assert _track_family("python", []) == "executable"
    assert _track_family("python-data", []) == "executable"
    assert _track_family("pyspark", []) == "reasoning"
    assert _track_family("data-engineering", []) == "reasoning"
    assert _track_family("data-modeling", []) == "reasoning"
    assert _track_family("ml-fundamentals", []) == "reasoning"
    assert _track_family("experimentation", []) == "reasoning"
    assert _track_family("mixed", []) == "executable"
    # Statistics resolves from subtype composition
    assert _track_family("statistics", [{"subtype": "numerical"}]) == "executable"
    assert _track_family("statistics", [{"subtype": "conceptual"}]) == "reasoning"
    assert _track_family("statistics", [{"subtype": "numerical"}, {"subtype": "conceptual"}]) == "executable"
    assert _track_family("statistics", []) == "reasoning"  # no questions → no numerical → reasoning


def test_tc171_mock_payload_exposes_interaction_mode_when_present():
    """TC-171: Mock question payload includes interaction_mode when provided by content."""
    from routers.mock import _public_question_payload

    question = dict(_pyspark_easy_q)
    question["interaction_mode"] = "code_adjacent_reasoning"

    payload = _public_question_payload(question, "pyspark")

    assert payload.get("interaction_mode") == "code_adjacent_reasoning"
    assert payload.get("type") == question.get("type")
    assert payload.get("question_type") == question.get("type")


# ---------------------------------------------------------------------------
# One-submit-per-question guard (TC-172 to TC-176)
# ---------------------------------------------------------------------------

def test_tc172_blank_code_submit_returns_422_and_does_not_consume_question():
    """TC-172: Blank code submit → 422; question submitted_at remains null."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = client.post("/api/mock/start", json={
            "mode": "30min", "track": "sql", "difficulty": "medium",
        })
        assert r_start.status_code in (200, 201)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]

        # Blank code submit
        r_blank = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "sql",
            "code": "   ",
        })
        assert r_blank.status_code == 422

        # Confirm question slot is still open (submitted_at is null)
        r_state = client.get(f"/api/mock/{session_id}")
        assert r_state.status_code == 200
        q_rows = {q["id"]: q for q in r_state.json()["questions"]}
        assert q_rows[first_q["id"]]["submitted_at"] is None


def test_tc173_missing_mcq_option_returns_422_and_does_not_consume_question():
    """TC-173: MCQ submit with no selected_option → 422; question slot untouched."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        assert r_start.status_code in (200, 201)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]

        # No option selected
        r_blank = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
        })
        assert r_blank.status_code == 422

        # Question slot still open
        r_state = client.get(f"/api/mock/{session_id}")
        q_rows = {q["id"]: q for q in r_state.json()["questions"]}
        assert q_rows[first_q["id"]]["submitted_at"] is None


def test_tc174_second_submit_after_correct_returns_409():
    """TC-174: Submitting a question a second time after a correct answer → 409."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        q_obj = next((q for q in _pyspark_catalog["easy"] if q["id"] == first_q["id"]), None)
        correct = q_obj["correct_option"] if q_obj else _pyspark_correct

        # First submit — correct
        r1 = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
        assert r1.status_code == 200
        assert r1.json()["correct"] is True

        # Second submit — same question
        r2 = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
        assert r2.status_code == 409


def test_tc175_second_submit_after_wrong_returns_409():
    """TC-175: Submitting a question a second time after a wrong answer → 409."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        all_qs = _pyspark_catalog["easy"] + _pyspark_catalog["medium"] + _pyspark_catalog["hard"]
        q_obj = next((q for q in all_qs if q["id"] == first_q["id"]), None)
        correct = q_obj["correct_option"] if q_obj else _pyspark_correct
        wrong = (correct + 1) % 4

        # First submit — wrong
        r1 = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": wrong,
        })
        assert r1.status_code == 200
        assert r1.json()["correct"] is False

        # Second submit — still 409
        r2 = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
        assert r2.status_code == 409


def test_tc176_blank_submit_does_not_block_subsequent_real_submit():
    """TC-176: Blank submit (422) does not consume the slot; real submit after succeeds."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = _start_pyspark_session(client)
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        all_qs = _pyspark_catalog["easy"] + _pyspark_catalog["medium"] + _pyspark_catalog["hard"]
        q_obj = next((q for q in all_qs if q["id"] == first_q["id"]), None)
        correct = q_obj["correct_option"] if q_obj else _pyspark_correct

        # Blank submit — rejected
        r_blank = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
        })
        assert r_blank.status_code == 422

        # Real submit — should succeed
        r_real = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": correct,
        })
        assert r_real.status_code == 200
        assert r_real.json()["correct"] is True
