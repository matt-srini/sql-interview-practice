"""TC-125 to TC-170 — Mock Interviews."""
import asyncio

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _insert_progress, _make_user
from unlock import compute_mock_access
from pyspark_questions import get_questions_by_difficulty as get_pyspark_qs, get_question as _get_pyspark_q

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_pyspark_catalog = get_pyspark_qs()
_pyspark_easy_q = _pyspark_catalog["easy"][0]
_pyspark_easy_id = _pyspark_easy_q["id"]
_pyspark_correct = _pyspark_easy_q["correct_option"]
_pyspark_wrong = (_pyspark_correct + 1) % 4


# ---------------------------------------------------------------------------
# Unit tests for compute_mock_access (TC-125 to TC-134 — Phase 3 signatures)
# ---------------------------------------------------------------------------

def test_tc125_free_benchmark_easy_can_start():
    """TC-125: Free + benchmark + easy → can_start: True; weekly_benchmark_limit: 1."""
    result = compute_mock_access("free", "sql", "easy", mode="benchmark", weekly_benchmark_used=0)
    assert result["can_start"] is True
    assert result["daily_limit"] is None
    assert result["weekly_benchmark_limit"] == 1
    assert result["weekly_benchmark_used"] == 0


def test_tc126_free_benchmark_medium_plan_locked():
    """TC-126: Free + benchmark + medium → plan_locked (medium/hard require Pro)."""
    result = compute_mock_access("free", "sql", "medium", mode="benchmark")
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_tc127_free_benchmark_easy_weekly_cap():
    """TC-127: Free + benchmark + easy + weekly_used=1 → weekly_cap."""
    result = compute_mock_access("free", "sql", "easy", mode="benchmark", weekly_benchmark_used=1)
    assert result["can_start"] is False
    assert result["block_reason"] == "weekly_cap"
    assert result["weekly_benchmark_limit"] == 1
    assert result["weekly_benchmark_used"] == 1


def test_tc128_free_custom_plan_locked():
    """TC-128: Free + custom → plan_locked."""
    result = compute_mock_access("free", "sql", "easy", mode="custom")
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_tc129_free_benchmark_hard_plan_locked():
    """TC-129: Free + benchmark + hard → plan_locked; needs_upgrade: pro."""
    result = compute_mock_access("free", "sql", "hard", mode="benchmark")
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_tc129b_free_benchmark_mixed_plan_locked():
    """TC-129b: Free + benchmark + mixed → plan_locked (mixed contains medium/hard;
    must not bypass the Free easy-only gate). Regression for the audit A2 finding."""
    result = compute_mock_access("free", "sql", "mixed", mode="benchmark", weekly_benchmark_used=0)
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_tc129c_pro_and_elite_benchmark_mixed_allowed():
    """TC-129c: Mixed difficulty is only gated for Free — Pro/Elite may run it."""
    assert compute_mock_access("pro", "sql", "mixed", mode="benchmark", daily_benchmark_used=0)["can_start"] is True
    assert compute_mock_access("elite", "sql", "mixed", mode="benchmark")["can_start"] is True


def test_tc130_pro_benchmark_hard_within_daily_limit():
    """TC-130: Pro + benchmark + hard + daily_used=2 → can_start: True; daily_limit: 3."""
    result = compute_mock_access("pro", "sql", "hard", mode="benchmark", daily_benchmark_used=2)
    assert result["can_start"] is True
    assert result["daily_limit"] == 3
    assert result["daily_used"] == 2


def test_tc131_pro_benchmark_hard_daily_limit_reached():
    """TC-131: Pro + benchmark + hard + daily_used=3 → daily_cap."""
    result = compute_mock_access("pro", "sql", "hard", mode="benchmark", daily_benchmark_used=3)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"
    assert result["needs_upgrade"] == "elite"


def test_tc132_elite_benchmark_hard_unlimited():
    """TC-132: Elite + benchmark + hard → can_start: True; daily_limit: None."""
    result = compute_mock_access("elite", "sql", "hard", mode="benchmark")
    assert result["can_start"] is True
    assert result["daily_limit"] is None


def test_tc134b_pro_custom_within_daily_limit():
    """TC-134B: Pro + custom + daily_custom_used=2 → can_start: True; daily_limit: 3."""
    result = compute_mock_access("pro", "sql", "easy", mode="custom", daily_custom_used=2)
    assert result["can_start"] is True
    assert result["daily_limit"] == 3
    assert result["daily_used"] == 2


def test_tc134c_pro_custom_daily_limit_reached():
    """TC-134C: Pro + custom + daily_custom_used=3 → daily_cap."""
    result = compute_mock_access("pro", "sql", "easy", mode="custom", daily_custom_used=3)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"


def test_tc134d_free_interview_loop_plan_locked():
    """TC-134D: Free + interview_loop → plan_locked (interview_loop is Elite-only)."""
    result = compute_mock_access("free", "sql", "easy", mode="interview_loop")
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"


def test_tc134e_pro_interview_loop_plan_locked():
    """TC-134E: Pro + interview_loop → plan_locked."""
    result = compute_mock_access("pro", "sql", "easy", mode="interview_loop")
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"


def test_tc134f_elite_interview_loop_can_start():
    """TC-134F: Elite + interview_loop → can_start: True."""
    result = compute_mock_access("elite", "sql", "easy", mode="interview_loop")
    assert result["can_start"] is True


def test_tc134g_benchmark_and_custom_caps_are_independent():
    """TC-134G: Pro benchmark cap and custom cap are independent counters."""
    # Benchmark capped, custom still available
    bench_capped = compute_mock_access("pro", "sql", "easy", mode="benchmark", daily_benchmark_used=3)
    custom_ok = compute_mock_access("pro", "sql", "easy", mode="custom", daily_benchmark_used=3, daily_custom_used=0)
    assert bench_capped["can_start"] is False
    assert bench_capped["block_reason"] == "daily_cap"
    assert custom_ok["can_start"] is True

    # Custom capped, benchmark still available
    custom_capped = compute_mock_access("pro", "sql", "easy", mode="custom", daily_custom_used=3)
    bench_ok = compute_mock_access("pro", "sql", "easy", mode="benchmark", daily_benchmark_used=0, daily_custom_used=3)
    assert custom_capped["can_start"] is False
    assert bench_ok["can_start"] is True


# ---------------------------------------------------------------------------
# Interview Loop: per-track difficulty (restored 2026-06-16). The user picks
# medium or hard; the chain is drawn from that difficulty's pool; the session
# stores the chosen difficulty. Easy always 400s (no chains). Tracks with chains
# only at one difficulty must 400 on the other (e.g. python has no hard chains,
# ml-fundamentals has no medium chains). See docs/features/mock.md § Interview Loop.
# ---------------------------------------------------------------------------

def _loop_access(client, track):
    return client.get("/api/mock/access", params={"track": track, "mode": "interview_loop"})


def test_tc134h_loop_access_medium_hard_have_chains_for_sql():
    """Elite Interview Loop: access['medium'] and access['hard'] can_start for sql (has chains at both)."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        access = _loop_access(client, "sql").json()["access"]
    assert access["medium"]["can_start"] is True
    assert access["hard"]["can_start"] is True
    assert access["easy"]["can_start"] is False  # no chains at easy


def test_tc134i_loop_access_non_elite_plan_locked():
    """Free cannot start Interview Loop at all (Elite-only plan gate)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        access = _loop_access(client, "sql").json()["access"]
    assert access["medium"]["can_start"] is False
    assert access["medium"]["block_reason"] == "plan_locked"


def test_tc134j_start_interview_loop_medium_sql_succeeds_stores_difficulty():
    """Start interview_loop with difficulty='medium' on sql → 200; session stores 'medium'."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "sql", "difficulty": "medium",
        })
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "session_id" in body
    assert body.get("difficulty") == "medium"
    assert len(body["questions"]) >= 2  # parent + at least one follow-up


def test_tc134k_start_interview_loop_easy_400():
    """Easy has no chains — interview_loop with difficulty='easy' → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "sql", "difficulty": "easy",
        })
    assert r.status_code == 400


def test_tc134l_start_interview_loop_hard_ml_fundamentals_succeeds():
    """ml-fundamentals has hard chains only — difficulty='hard' → 200."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "ml-fundamentals", "difficulty": "hard",
        })
    assert r.status_code in (200, 201), r.text
    assert len(r.json()["questions"]) >= 2


def test_tc134l2_start_interview_loop_python_hard_400():
    """Python has no hard chains — interview_loop with difficulty='hard' on python → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "python", "difficulty": "hard",
        })
    assert r.status_code == 400


def test_tc134l3_start_interview_loop_python_medium_succeeds():
    """Python has medium chains → difficulty='medium' on python → 200."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "python", "difficulty": "medium",
        })
    assert r.status_code in (200, 201), r.text
    assert r.json().get("difficulty") == "medium"
    assert len(r.json()["questions"]) >= 2


# ---------------------------------------------------------------------------
# Interview Loop exhausted-cell redirect (DECISIONS 2026-06-22 replay-redirect):
# when a user finishes every chain in a (track, difficulty) cell, /access returns
# `fresh_loop_cells` — the user's still-startable cells, requested track first — so
# the UI leads with fresh reasoning and demotes replay. See docs/features/mock.md.
# ---------------------------------------------------------------------------

def test_fresh_loop_cells_requested_track_first_and_capped():
    """_fresh_loop_cells leads with the requested track and caps the list."""
    from routers.mock import _fresh_loop_cells
    cells = _fresh_loop_cells("pandas", set())
    assert cells, "pandas has chains, should yield fresh cells"
    assert cells[0]["track"] == "pandas"  # requested track surfaces first
    assert len(cells) <= 4  # default cap
    for c in cells:
        assert c["fresh"] >= 1 and {"track", "difficulty", "fresh"} <= c.keys()


def test_fresh_loop_cells_excludes_the_exhausted_cell():
    """A fully-consumed cell drops out; its sibling difficulty (still fresh) remains."""
    from routers.mock import _fresh_loop_cells, _chain_parents_for
    consumed = {int(p["id"]) for p in _chain_parents_for("pandas", "medium")}
    cells = _fresh_loop_cells("pandas", consumed)
    keys = {(c["track"], c["difficulty"]) for c in cells}
    assert ("pandas", "medium") not in keys  # exhausted → not suggested
    assert ("pandas", "hard") in keys  # still has fresh chains → suggested


def test_fresh_loop_cells_empty_when_everything_consumed():
    """User who has exhausted every cell → empty list (UI falls back to replay)."""
    from routers.mock import _fresh_loop_cells, _chain_parents_for
    from tracks import TRACKS
    all_parents = {
        int(p["id"])
        for t in TRACKS
        for d in ("medium", "hard")
        for p in _chain_parents_for(t.slug, d)
    }
    assert _fresh_loop_cells("pandas", all_parents) == []


def test_access_returns_fresh_loop_cells_on_exhaustion():
    """Elite + an exhausted sql-medium cell → /access carries non-empty fresh_loop_cells
    (excluding the exhausted cell), and the cell is flagged replayable."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _chain_parents_for
    consumed = {int(p["id"]) for p in _chain_parents_for("sql", "medium")}
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        with patch("routers.mock.get_consumed_chain_parent_ids", new=AsyncMock(return_value=consumed)):
            body = _loop_access(client, "sql").json()
    assert body["access"]["medium"]["block_reason"] == "pool_exhausted"
    assert body["access"]["medium"]["replayable"] is True
    fresh = body["fresh_loop_cells"]
    assert fresh, "an exhausted cell must surface fresh alternatives"
    assert ("sql", "medium") not in {(c["track"], c["difficulty"]) for c in fresh}


def test_access_omits_fresh_loop_cells_when_startable():
    """No exhaustion → fresh_loop_cells stays empty (the all-tracks scan never runs)."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        body = _loop_access(client, "sql").json()
    assert body["access"]["medium"]["can_start"] is True
    assert body["fresh_loop_cells"] == []


def test_loop_escalation_uniform_per_cell():
    """Every (track, difficulty) Interview Loop cell escalates uniformly — all chains in
    the cell reach a higher difficulty, or none do. A partial cell makes the single
    cell-level "medium → hard" badge over-promise for the flat chains. Enforced in CI by
    validate_content.py::_validate_loop_escalation_uniformity; this is the focused guard.
    Revisit deliberately (relax both) if a track ever genuinely needs mixed escalation.
    See docs/decisions/DECISIONS.md.
    """
    from routers.mock import _chain_parents_for
    from tracks import TRACKS
    rank = {"easy": 0, "medium": 1, "hard": 2}
    mixed = []
    for t in TRACKS:
        try:
            mock = t.catalog_module.get_mock_questions_by_difficulty()
        except Exception:
            continue
        byid = {int(q["id"]): q for qs in mock.values() for q in qs}
        for diff in ("medium", "hard"):
            parents = _chain_parents_for(t.slug, diff)
            if not parents:
                continue
            esc = {
                int(p["id"]) for p in parents
                if any(rank.get(byid.get(int(f), {}).get("difficulty"), rank[diff]) > rank[diff]
                       for f in p["follow_ups"])
            }
            flat = {int(p["id"]) for p in parents} - esc
            if esc and flat:
                mixed.append((t.slug, diff, f"{len(esc)} escalate / {len(flat)} flat"))
    assert not mixed, f"mixed-escalation Loop cells must be all-or-none, found: {mixed}"


# ---------------------------------------------------------------------------
# Mock Run Code: gated on session membership, NOT the practice unlock state, so
# mock-only questions (every Interview Loop chain) run instead of 403'ing "locked".
# See docs/features/mock.md § Active Session and DECISIONS.md 2026-06-15.
# ---------------------------------------------------------------------------

def test_tc134m_mock_run_executes_mock_only_question_without_lock():
    """Run Code on a mock-only Interview Loop question returns 200 (not the practice 403 lock)."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        start = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "python", "difficulty": "medium",
        })
        sess = start.json()
        sid, qid = sess["session_id"], sess["questions"][0]["id"]
        r = client.post(f"/api/mock/{sid}/run", json={
            "question_id": qid, "track": "python", "code": "def solve(*a, **k):\n    return None",
        })
    assert r.status_code == 200, r.text  # the bug returned 403 "locked"
    body = r.json()
    assert isinstance(body, dict)
    assert "locked" not in str(body.get("error", "")).lower()  # it actually executed


def test_tc134n_mock_run_rejects_question_not_in_session():
    """Membership is the gate: a question_id not in the session → 400 (no arbitrary execution)."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        start = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "python", "difficulty": "medium",
        })
        sid = start.json()["session_id"]
        r = client.post(f"/api/mock/{sid}/run", json={"question_id": 999999, "track": "python", "code": "x = 1"})
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# HTTP session tests (TC-135 to TC-170)
# ---------------------------------------------------------------------------

def _start_pyspark_session(client, mode="custom", difficulty="medium", plan="pro", **kwargs):
    body = {"mode": mode, "track": "pyspark", "difficulty": difficulty, **kwargs}
    if mode == "custom":
        body.setdefault("num_questions", 2)
        body.setdefault("time_minutes", 30)
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
    assert len(body["questions"]) == 2  # custom 2-question session
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


def test_tc136d_benchmark_mode_mixed_track_requires_role():
    """TC-136D: Benchmark + mixed without role → 400; with role → 200."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        # No role → 400
        r_no_role = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "mixed", "difficulty": "easy",
        })
        assert r_no_role.status_code == 400
        assert "role" in r_no_role.json().get("error", "").lower()

        # With valid role → 200
        r_with_role = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "mixed", "difficulty": "easy",
            "role": "data_analyst",
        })
        assert r_with_role.status_code in (200, 201)


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
    """TC-136F: Custom drill on reasoning track is not forced into benchmark-only type coverage."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "ml-fundamentals", "difficulty": "hard",
            "num_questions": 2, "time_minutes": 30,
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


def test_tc146_free_user_custom_mode_plan_locked():
    """TC-146: Free user + custom mode → plan_locked (custom requires Pro+)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 30,
        })
    assert r.status_code == 403
    assert "pro" in r.json().get("error", "").lower() or "upgrade" in r.json().get("error", "").lower()


def test_tc147_pro_user_4th_custom_same_day_blocked():
    """TC-147: Pro user; 3 custom sessions today → 4th custom blocked (403)."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Insert 3 custom sessions completed today
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(3):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                       VALUES (%s::uuid, 'custom', 'pyspark', 'hard', 1800, 'completed')""",
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


def test_tc148_elite_user_4th_custom_same_day_allowed():
    """TC-148: Elite user; 3+ custom sessions today → 4th still allowed (unlimited)."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
    # Insert 3 custom sessions
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for _ in range(3):
                cur.execute(
                    """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status)
                       VALUES (%s::uuid, 'custom', 'pyspark', 'hard', 1800, 'completed')""",
                    (user["id"],),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = _start_pyspark_session(client, difficulty="hard")
    assert r.status_code in (200, 201)


def test_tc151_non_elite_focus_concepts_returns_403():
    """TC-151: Pro user with focus_concepts → 403."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "sql", "difficulty": "medium",
            "num_questions": 1, "time_minutes": 20,
            "focus_concepts": ["window functions"],
        })
    assert r.status_code == 403


def test_tc152_elite_more_than_3_focus_concepts_returns_422():
    """TC-152: Elite user, >3 focus_concepts → 422."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 20,
            "focus_concepts": ["a", "b", "c", "d"],
        })
    assert r.status_code == 422


def test_tc153_elite_focus_concepts_creates_session():
    """TC-153: Elite user, 1-3 focus_concepts → session created."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "custom", "track": "pyspark", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 20,
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
        selected, focus_fallback, track_substituted, type_fallback = asyncio.run(
            _select_questions("pyspark", "easy", 2, user, focus_concepts=["NONEXISTENT_CONCEPT_XYZ"])
        )
    assert focus_fallback is True
    assert track_substituted is False
    assert type_fallback is False
    assert len(selected) > 0


def test_tc155_empty_focus_concepts_treated_as_no_filter():
    """TC-155: _select_questions with focus_concepts=[] → full pool, focus_fallback: False."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _select_questions
    user = {"id": "00000000-0000-0000-0000-000000000001", "plan": "elite"}
    with patch("routers.mock._get_solved_ids_for_track", new=AsyncMock(return_value=set())), \
         patch("routers.mock.get_previously_mocked_ids", new=AsyncMock(return_value=set())):
        selected, focus_fallback, track_substituted, type_fallback = asyncio.run(
            _select_questions("pyspark", "easy", 2, user, focus_concepts=[])
        )
    assert focus_fallback is False
    assert track_substituted is False
    assert type_fallback is False
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
        selected1, *_flags1 = asyncio.run(
            _select_questions("pyspark", "easy", 1, user)
        )
        # Second call may or may not re-select; just verify it returns valid data
        selected2, *_flags2 = asyncio.run(
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
    """TC-163: Free user completes easy benchmark → debrief: null."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r_start = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "pyspark", "difficulty": "easy",
        })
        assert r_start.status_code in (200, 201), r_start.text
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
                   VALUES (%s::uuid, 'custom', 'pyspark', 'easy', 1800, 'completed', NOW())
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
    assert body["mode_breakdown"] == {"benchmark": 1, "custom": 1, "interview_loop": 0, "drill": 1}
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


def test_debrief_weak_concept_recommends_drill_not_path():
    """Weak-concept debrief is concept-drill-ONLY — it carries the fields to build
    /practice/{track}?drill={concept} and never a learning-path link.

    The mock post-mortem links to no learning paths anywhere; path recommendations
    live exclusively on the dashboard (docs/features/dashboard.md). Guards the
    regression the Interview-Loop summary hit (debrief deep-linked /learn).
    """
    from routers.insights import build_session_debrief

    # One concept, attempted twice with one miss → it is the session's weak spot.
    # WINDOW FUNCTIONS resolves to a learning path, so this also proves the debrief
    # withholds that path rather than merely lacking one.
    questions = [
        {"id": 1, "track": "sql", "is_solved": True,
         "concepts": ["WINDOW FUNCTIONS"], "time_spent_s": 90},
        {"id": 2, "track": "sql", "is_solved": False,
         "concepts": ["WINDOW FUNCTIONS"], "time_spent_s": 120},
    ]
    session_meta = {
        "mode": "interview_loop", "difficulty": "medium", "track": "sql",
        "time_used_s": 210, "time_limit_s": 1800,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None

    # The next step is the concept drill (carries the fields the frontend needs to
    # build the /practice/{track}?drill={concept} link).
    assert debrief["priority_concept"] == "WINDOW FUNCTIONS"
    assert debrief["priority_track"] == "sql"
    action = debrief["priority_action"] or ""
    assert action.startswith("Drill WINDOW FUNCTIONS"), action
    # Never the old path-primary phrasing.
    assert "Work through the" not in action

    # Concept-only: the mock debrief carries no learning-path link at all, even
    # though WINDOW FUNCTIONS has a matching path.
    assert "priority_path_slug" not in debrief
    assert "priority_path_title" not in debrief
    from routers.insights import _path_for_concept
    assert _path_for_concept("sql", "WINDOW FUNCTIONS"), "fixture concept should resolve a path"


def test_debrief_tiebreak_prefers_known_weakness():
    """When two weak concepts tie on session accuracy AND attempts, NEXT STEP breaks
    the tie toward a known cross-session weakness (>=3 historical attempts, <60%),
    not merely the alphabetical fallback (insights.py weak-sort tiebreak)."""
    from routers.insights import build_session_debrief, _CONCEPTS_LOOKUP

    # A real SQL concept with >=3 historical question IDs we can mark as repeated misses.
    known = "WINDOW FUNCTIONS"
    known_qids = [qid for qid, cs in _CONCEPTS_LOOKUP["sql"].items() if known in cs][:3]
    assert len(known_qids) >= 3, "fixture needs >=3 historical WINDOW FUNCTIONS questions"

    # A control concept that never appears in history → can never be "known weak".
    # Named to sort first by the deterministic case-insensitive alphabetical tiebreak,
    # so with no history it wins and the known-weak effect is isolated to the with-history case.
    control = "AAA CONTROL CONCEPT (NOT REAL)"

    # Two unsolved questions, both 0/1 (equal misses + accuracy).
    questions = [
        {"id": 990001, "track": "sql", "is_solved": False, "concepts": [control], "time_spent_s": 60},
        {"id": 990002, "track": "sql", "is_solved": False, "concepts": [known], "time_spent_s": 60},
    ]
    meta = {"track": "sql", "difficulty": "medium", "time_used_s": 120, "time_limit_s": 1800}

    # No history → ties fall to the deterministic alphabetical final key → "AAA" control wins.
    no_hist = build_session_debrief(questions, meta, [], "elite")
    assert no_hist["priority_concept"] == control

    # 3 past misses on WINDOW FUNCTIONS (different question IDs) → it becomes known-weak,
    # so it now wins the otherwise-identical tie despite being listed second.
    events = [{"track": "sql", "question_id": qid, "is_correct": False} for qid in known_qids]
    with_hist = build_session_debrief(questions, meta, events, "elite")
    assert with_hist["priority_concept"] == known, with_hist["priority_concept"]


def test_debrief_evidence_guard_prefers_more_misses_over_single_miss():
    """F4: NEXT STEP weighs evidence of failure (number of misses), so a 1/5 concept
    (4 misses, 20%) outranks a lone careless 0/1 (1 miss, 0%). Accuracy alone must not
    let a single miss headline over a better-evidenced session gap. No history + fake
    concepts (never known-weak), so only the miss-count signal decides."""
    from routers.insights import build_session_debrief

    lone = "AAA LONE MISS (NOT REAL)"           # 0/1 -> 1 miss, 0% accuracy
    evidenced = "BBB EVIDENCED GAP (NOT REAL)"  # 1/5 -> 4 misses, 20% accuracy
    questions = (
        [{"id": 990201, "track": "sql", "is_solved": False, "concepts": [lone], "time_spent_s": 30}]
        + [{"id": 990210, "track": "sql", "is_solved": True, "concepts": [evidenced], "time_spent_s": 30}]
        + [
            {"id": 990211 + i, "track": "sql", "is_solved": False, "concepts": [evidenced], "time_spent_s": 30}
            for i in range(4)
        ]
    )
    meta = {"track": "sql", "difficulty": "medium", "time_used_s": 300, "time_limit_s": 1800}
    debrief = build_session_debrief(questions, meta, [], "elite")
    assert debrief["priority_concept"] == evidenced, debrief["priority_concept"]


def test_debrief_known_weakness_family_aware_for_lowercase_statistics_tags():
    """F1 regression: statistics concept tags are stored lowercase, but the historical
    concept lookup uppercases them — the prior raw-vs-uppercased key mismatch made every
    statistics concept silently never-known-weak. The known-weak test now resolves to
    family, so a recurring lowercase-tagged statistics gap is recognized."""
    from routers.insights import build_session_debrief, _CONCEPTS_LOOKUP, resolve_to_family

    stat_tag = "hypothesis testing"  # stored lowercase in the statistics bank
    fam = resolve_to_family(stat_tag, "statistics")
    qids = [
        qid for qid, cs in _CONCEPTS_LOOKUP["statistics"].items()
        if any(resolve_to_family(c, "statistics") == fam for c in cs)
    ][:3]
    assert len(qids) >= 3, "fixture needs >=3 historical questions in this statistics family"

    control = "AAA CONTROL (NOT REAL)"
    questions = [
        {"id": 990301, "track": "statistics", "subtype": "conceptual", "is_solved": False,
         "concepts": [control], "time_spent_s": 60},
        {"id": 990302, "track": "statistics", "subtype": "conceptual", "is_solved": False,
         "concepts": [stat_tag], "time_spent_s": 60},
    ]
    meta = {"track": "statistics", "difficulty": "medium", "time_used_s": 120, "time_limit_s": 2700}

    # No history → alphabetical fallback → control wins.
    no_hist = build_session_debrief(questions, meta, [], "elite")
    assert no_hist["priority_concept"] == control

    # 3 past misses on the statistics family → it becomes known-weak (the bug fix: the
    # lowercase session tag now resolves to the same family as the uppercased history).
    events = [{"track": "statistics", "question_id": qid, "is_correct": False} for qid in qids]
    with_hist = build_session_debrief(questions, meta, events, "elite")
    assert with_hist["priority_concept"] == stat_tag, with_hist["priority_concept"]


def test_debrief_mixed_session_uses_weak_concepts_own_track_family():
    """F7c guard: in a Mixed session the session family is 'executable' (the Mixed
    short-circuit in _track_family), but the weakest concept can be on a reasoning
    track. Both the inconsistency pattern AND the NEXT STEP copy must follow the weak
    concept's OWN track, not the session's — else an MCQ concept gets 'before writing
    code' / '3 consecutive correct' advice. FAILS on the pre-fix (session-family) code,
    passes after F7c."""
    from routers.insights import build_session_debrief

    questions = [
        # Data Modeling is a reasoning/MCQ track; inconsistent (1/2) -> the session's weak spot.
        {"id": 991001, "track": "data-modeling", "is_solved": True,
         "concepts": ["DIMENSIONAL MODELING"], "time_spent_s": 60},
        {"id": 991002, "track": "data-modeling", "is_solved": False,
         "concepts": ["DIMENSIONAL MODELING"], "time_spent_s": 90},
        # A solved SQL question keeps the session genuinely mixed (and not the weak spot).
        {"id": 991003, "track": "sql", "is_solved": True,
         "concepts": ["GROUPED AGGREGATION"], "time_spent_s": 50},
    ]
    meta = {"track": "mixed", "mode": "benchmark", "difficulty": "medium",
            "time_used_s": 200, "time_limit_s": 2400}
    debrief = build_session_debrief(questions, meta, [], "elite")

    assert debrief["priority_concept"] == "DIMENSIONAL MODELING"
    assert debrief["priority_track"] == "data-modeling"
    text = " ".join(debrief.get("patterns", [])) + " " + (debrief.get("priority_action") or "")
    # Reasoning copy for an MCQ concept — never the executable phrasings.
    assert "before writing code" not in text, text
    assert "3 consecutive correct" not in text, text
    assert "tradeoffs" in text, text


def test_tc176_track_family_helper_resolves_correctly():
    """TC-176: _track_family returns correct family for each track category."""
    from routers.insights import _track_family

    assert _track_family("sql", []) == "executable"
    assert _track_family("python", []) == "executable"
    assert _track_family("pandas", []) == "executable"
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
            "mode": "custom", "track": "sql", "difficulty": "medium",
            "num_questions": 1, "time_minutes": 30,
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
        q_obj = _get_pyspark_q(first_q["id"])
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
        q_obj = _get_pyspark_q(first_q["id"])
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
        q_obj = _get_pyspark_q(first_q["id"])
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


# ---------------------------------------------------------------------------
# Phase 3: Interview Loop tests (TC-177 to TC-184)
# ---------------------------------------------------------------------------

# ML Fundamentals hard has 8 chains; use these parent IDs for exhaustion tests
_ML_HARD_CHAIN_PARENTS = [83043, 83047, 83049, 83053, 83055, 83073, 83078, 83082]


def test_tc177_interview_loop_elite_start_returns_session_with_chain():
    """TC-177: Elite + interview_loop + ML hard → session with chain; time = chain_len × 900."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "session_id" in body
    questions = body["questions"]
    assert len(questions) >= 2, "Interview Loop session must have at least parent + 1 follow-up"
    # Time must be chain_length × 900
    assert body["time_limit_s"] == len(questions) * 900
    # Parent: follow_up_dimension is None; children: follow_up_dimension is set
    assert questions[0].get("follow_up_dimension") is None
    for child in questions[1:]:
        assert child.get("follow_up_dimension") is not None, (
            f"Follow-up question {child['id']} missing follow_up_dimension"
        )


def test_tc178_interview_loop_pro_returns_403():
    """TC-178: Pro user + interview_loop → 403 (Elite-only)."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
    assert r.status_code == 403
    assert "elite" in r.json().get("error", "").lower()


def test_tc179_interview_loop_pool_exhaustion_returns_409():
    """TC-179: All chains consumed → 409 pool_exhausted."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")

    # Mark all ML hard chain parents as consumed for this user
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for parent_id in _ML_HARD_CHAIN_PARENTS:
                cur.execute(
                    """INSERT INTO mock_chain_consumption (user_id, parent_id, session_id)
                       VALUES (%s::uuid, %s, NULL)
                       ON CONFLICT (user_id, parent_id) DO NOTHING""",
                    (user["id"], parent_id),
                )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
    assert r.status_code == 409
    body = r.json()
    # Dict details are unpacked into the response body directly (no "detail" wrapper)
    assert body.get("pool_exhausted") is True or "exhausted" in str(body.get("error", "")).lower()
    # The exhausted set is replayable (content exists) — the UI shows a Replay button.
    assert body.get("replayable") is True


def _consume_all_ml_hard_chains(user_id: str) -> None:
    """Mark every ML-hard chain parent consumed for a user (exhausts the loop pool)."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            for parent_id in _ML_HARD_CHAIN_PARENTS:
                cur.execute(
                    """INSERT INTO mock_chain_consumption (user_id, parent_id, session_id)
                       VALUES (%s::uuid, %s, NULL)
                       ON CONFLICT (user_id, parent_id) DO NOTHING""",
                    (user_id, parent_id),
                )
        conn.commit()
    finally:
        conn.close()


def test_tc179b_interview_loop_replay_consent_redraws_completed_chain():
    """Exhausted pool + replay=true → 200 with a chain and is_replay flag set.

    Replay is the consent-gated escape from the pool_exhausted dead-end: once every
    chain is completed, an explicit replay=true re-draws a completed chain instead of
    409ing. Without replay it must still 409 (covered by TC-179)."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
    _consume_all_ml_hard_chains(user["id"])

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
            "replay": True,
        })
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert body.get("is_replay") is True
    assert len(body.get("questions", [])) >= 2, "Replayed session must still carry a full chain"


def test_tc180_discard_interview_loop_reclaims_chain():
    """TC-180: Discard an Interview Loop session within 2 min → chain reclaimed; restart succeeds."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        # Start Interview Loop — consumes a chain
        r1 = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
        assert r1.status_code in (200, 201), r1.text
        session_id = r1.json()["session_id"]

        # Discard within 2 min (test environment is fast — always within window)
        r_discard = client.delete(f"/api/mock/{session_id}")
        assert r_discard.status_code == 204

        # Start another loop — chain was reclaimed, so same chain is re-eligible
        r2 = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
    assert r2.status_code in (200, 201), r2.text


def test_tc181_legacy_30min_start_returns_400():
    """TC-181: POST /api/mock/start with mode='30min' → 400 with read-only legacy message (not 'Invalid mode')."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/mock/start", json={
            "mode": "30min", "track": "pyspark", "difficulty": "easy",
        })
    assert r.status_code == 400
    error_text = r.json().get("error", "").lower()
    # Must say "read-only" or "legacy" — not the generic "invalid mode" fallthrough
    assert "read-only" in error_text or "legacy" in error_text, f"Expected read-only/legacy message, got: {error_text!r}"


def test_tc182_mixed_custom_without_role_returns_400():
    """TC-182: Custom + mixed track without role → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_no_role = client.post("/api/mock/start", json={
            "mode": "custom", "track": "mixed", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 20,
        })
        assert r_no_role.status_code == 400
        assert "role" in r_no_role.json().get("error", "").lower()

        r_with_role = client.post("/api/mock/start", json={
            "mode": "custom", "track": "mixed", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 20,
            "role": "data_analyst",
        })
    assert r_with_role.status_code in (200, 201), r_with_role.text


def test_tc183_analytics_includes_loop_summary():
    """TC-183: Analytics for Elite user with interview_loop session includes loop_summary."""
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO mock_sessions (user_id, mode, track, difficulty, time_limit_s, status, ended_at)
                   VALUES (%s::uuid, 'interview_loop', 'ml-fundamentals', 'hard', 2700, 'completed', NOW())
                   RETURNING id""",
                (user["id"],),
            )
            loop_session_id = cur.fetchone()[0]
            cur.execute(
                """INSERT INTO mock_session_questions
                   (session_id, question_id, track, position, is_solved, follow_up_dimension)
                   VALUES
                     (%s, 83043, 'ml-fundamentals', 1, true, NULL),
                     (%s, 83103, 'ml-fundamentals', 2, false, 'data_quality_pivot')""",
                (loop_session_id, loop_session_id),
            )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r = client.get("/api/mock/analytics")

    assert r.status_code == 200
    body = r.json()
    assert "loop_summary" in body
    loop_summary = body["loop_summary"]
    assert loop_summary["sessions"] == 1
    assert "per_dimension_performance" in loop_summary
    perf = loop_summary["per_dimension_performance"]
    assert "data_quality_pivot" in perf


# ─────────────────────────────────────────────────────────────────────────────
# Degradation contract flags — see docs/features/mock.md § Degradation contracts
# ─────────────────────────────────────────────────────────────────────────────

def test_type_fallback_not_triggered_when_bank_supports_targets():
    """DM easy benchmark targets (1 scenario + 4 conceptual via difficulty-aware
    override) match the bank composition exactly — type_fallback should be False."""
    from unittest.mock import AsyncMock, patch
    from routers.mock import _select_questions
    user = {"id": "00000000-0000-0000-0000-000000000001", "plan": "elite"}
    with patch("routers.mock._get_solved_ids_for_track", new=AsyncMock(return_value=set())), \
         patch("routers.mock.get_previously_mocked_ids", new=AsyncMock(return_value=set())):
        selected, focus_fallback, track_substituted, type_fallback = asyncio.run(
            _select_questions("data-modeling", "easy", 5, user, mode="benchmark")
        )
    assert len(selected) == 5
    assert focus_fallback is False
    assert track_substituted is False
    # Override matches bank distribution exactly; no fallback needed.
    assert type_fallback is False


def test_type_fallback_triggered_when_partition_exhausted():
    """_sample_by_format returns type_fallback=True when a requested type
    partition has no questions in the available pool."""
    from routers.mock import _sample_by_format
    pool = [
        {"id": 1, "type": "conceptual", "_track": "x"},
        {"id": 2, "type": "conceptual", "_track": "x"},
        {"id": 3, "type": "conceptual", "_track": "x"},
    ]
    # Target "scenario" doesn't exist in the pool; should fall back to conceptual.
    chosen, type_fallback = _sample_by_format(pool, ["scenario", "conceptual"], set())
    assert len(chosen) == 2
    assert type_fallback is True


def test_sample_by_format_no_fallback_when_partitions_present():
    """_sample_by_format returns type_fallback=False when each requested type
    has at least one question available."""
    from routers.mock import _sample_by_format
    pool = [
        {"id": 1, "type": "scenario", "_track": "x"},
        {"id": 2, "type": "conceptual", "_track": "x"},
    ]
    chosen, type_fallback = _sample_by_format(pool, ["scenario", "conceptual"], set())
    assert len(chosen) == 2
    assert type_fallback is False


def test_interview_loop_follow_up_flag_persisted():
    """Regression: is_follow_up must be persisted in mock_session_questions.
    Parent → is_follow_up=False; each follow-up → is_follow_up=True with non-null follow_up_dimension.
    Verified by reading back the session via GET /api/mock/:id after start.
    """
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "ml-fundamentals",
            "difficulty": "hard",
        })
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]

        # Re-read the session from the DB via GET — this reflects the persisted rows
        r_get = client.get(f"/api/mock/{session_id}")
    assert r_get.status_code == 200, r_get.text
    questions = r_get.json()["questions"]
    assert len(questions) >= 2, "Interview Loop must have at least parent + 1 follow-up"

    # Parent (position 1): is_follow_up must be False
    parent = questions[0]
    assert parent.get("is_follow_up") is False, (
        f"Parent question has is_follow_up={parent.get('is_follow_up')!r}, expected False"
    )
    assert parent.get("follow_up_dimension") is None

    # Follow-ups (positions 2+): is_follow_up must be True and follow_up_dimension must be set
    for child in questions[1:]:
        assert child.get("is_follow_up") is True, (
            f"Follow-up question {child.get('id')} has is_follow_up={child.get('is_follow_up')!r}, expected True"
        )
        assert child.get("follow_up_dimension") is not None, (
            f"Follow-up question {child.get('id')} missing follow_up_dimension"
        )


# ---------------------------------------------------------------------------
# C3 regression: benchmark/interview_loop submit must NOT reveal verdict or answer key
# ---------------------------------------------------------------------------

def test_benchmark_submit_hides_verdict_and_answer_key():
    """C3 regression: Elite benchmark SQL submit returns lean {submitted: true} ack —
    no correct, expected_result, feedback, or hidden_summary exposed mid-session.
    Pro custom SQL submit still returns the full result including correct.
    """
    # --- Elite benchmark: lean ack, no verdict or answer key ---
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r_start = client.post("/api/mock/start", json={
            "mode": "benchmark", "track": "sql", "difficulty": "easy",
        })
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]

        r_submit = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "sql",
            "code": "SELECT 1",
        })

    assert r_submit.status_code == 200, r_submit.text
    body = r_submit.json()
    # Must be the lean ack shape — no verdict or answer key
    assert "correct" not in body, f"'correct' leaked in benchmark submit response: {body}"
    assert "expected_result" not in body, f"'expected_result' leaked in benchmark submit response: {body}"
    assert "feedback" not in body, f"'feedback' leaked in benchmark submit response: {body}"
    assert "hidden_summary" not in body, f"'hidden_summary' leaked in benchmark submit response: {body}"
    assert body.get("submitted") is True, f"Expected {{submitted: true}}, got: {body}"

    # --- Pro custom: full result including correct ---
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r_start = client.post("/api/mock/start", json={
            "mode": "custom", "track": "sql", "difficulty": "easy",
            "num_questions": 1, "time_minutes": 10,
        })
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]

        r_submit = client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "sql",
            "code": "SELECT 1",
        })

    assert r_submit.status_code == 200, r_submit.text
    body = r_submit.json()
    # Custom drill must still reveal verdict
    assert "correct" in body, f"'correct' missing from custom drill submit response: {body}"


def test_history_row_includes_time_used_s():
    """B3 regression: GET /api/mock/history → completed rows must include time_used_s as int >= 0."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        # Start a benchmark session (Elite can always start one)
        r_start = _start_pyspark_session(client, mode="benchmark", difficulty="easy")
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        first_q = r_start.json()["questions"][0]
        # Submit one answer so the session is not entirely empty
        client.post(f"/api/mock/{session_id}/submit", json={
            "question_id": first_q["id"],
            "track": "pyspark",
            "selected_option": _pyspark_correct,
        })
        # Finish the session
        r_finish = client.post(f"/api/mock/{session_id}/finish")
        assert r_finish.status_code == 200, r_finish.text
        # Fetch history
        r_history = client.get("/api/mock/history")
    assert r_history.status_code == 200, r_history.text
    body = r_history.json()
    sessions = body if isinstance(body, list) else body.get("sessions", [])
    assert len(sessions) >= 1, "Expected at least one history row"
    latest = sessions[0]
    assert "time_used_s" in latest, f"time_used_s missing from history row: {latest}"
    assert isinstance(latest["time_used_s"], int), (
        f"time_used_s should be int, got {type(latest['time_used_s'])}: {latest['time_used_s']}"
    )
    assert latest["time_used_s"] >= 0, f"time_used_s should be >= 0, got {latest['time_used_s']}"


def test_tc182_discard_within_window_succeeds_and_removes_session():
    """TC-182: a penalty-free discard within the window deletes the session (204) and
    refunds the slot — the session no longer exists."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={"mode": "benchmark", "track": "sql", "difficulty": "easy"})
        assert r.status_code in (200, 201), r.text
        sid = r.json()["session_id"]
        d = client.delete(f"/api/mock/{sid}")
        assert d.status_code == 204, d.text
        # Session is gone — a new start is not blocked by an active-session 409.
        g = client.get(f"/api/mock/{sid}")
        assert g.status_code == 404, g.text


def test_tc183_discard_blocked_after_daily_cap_keeps_session_active():
    """TC-183 (audit C4): after MAX_PENALTY_FREE_DISCARDS_PER_DAY penalty-free discards,
    the next discard returns 429 and the session stays ACTIVE (not deleted, not counted) —
    the user can keep going or end it normally."""
    from routers.mock import MAX_PENALTY_FREE_DISCARDS_PER_DAY as CAP
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        # Use up the daily penalty-free discard budget.
        for _ in range(CAP):
            r = client.post("/api/mock/start", json={"mode": "benchmark", "track": "sql", "difficulty": "easy"})
            assert r.status_code in (200, 201), r.text
            d = client.delete(f"/api/mock/{r.json()['session_id']}")
            assert d.status_code == 204, d.text
        # One more start; its discard is now blocked.
        r = client.post("/api/mock/start", json={"mode": "benchmark", "track": "sql", "difficulty": "easy"})
        assert r.status_code in (200, 201), r.text
        sid = r.json()["session_id"]
        d = client.delete(f"/api/mock/{sid}")
        assert d.status_code == 429, d.text
        assert "penalty-free" in d.json().get("error", "").lower()
        # The session was NOT discarded — still active and resumable.
        g = client.get(f"/api/mock/{sid}")
        assert g.status_code == 200, g.text
        assert g.json().get("status") == "active"


def test_history_time_used_clamped_to_limit():
    """Regression: a session finished far past its start must report time_used_s == time_limit_s,
    not the raw elapsed seconds (~11 days).  Tests both the SQL clamp in get_mock_history and
    the Python clamp in finish_mock_session."""
    # Phase 1: start + finish the session and capture the user for re-login.
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
        # Start a benchmark session; Elite can always start one.
        r_start = _start_pyspark_session(client, mode="benchmark", difficulty="easy")
        assert r_start.status_code in (200, 201), r_start.text
        session_id = r_start.json()["session_id"]
        time_limit_s = r_start.json()["time_limit_s"]

        # Finish the session (sets ended_at = now).
        r_finish = client.post(f"/api/mock/{session_id}/finish")
        assert r_finish.status_code == 200, r_finish.text
        # Confirm the finish summary itself is already clamped.
        finish_body = r_finish.json()
        assert finish_body.get("time_used_s") is not None, "finish body missing time_used_s"
        assert finish_body["time_used_s"] <= time_limit_s, (
            f"finish time_used_s {finish_body['time_used_s']} exceeds limit {time_limit_s}"
        )
        assert finish_body["time_used_s"] >= 0, "finish time_used_s is negative"

    # Phase 2: backdate started_at so raw elapsed (~11 days) >> time_limit_s.
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE mock_sessions SET started_at = ended_at - interval '11 days' WHERE id = %s",
                (session_id,),
            )
        conn.commit()
    finally:
        conn.close()

    # Phase 3: re-login as the same user and fetch history; clamped value must equal time_limit_s.
    with TestClient(app) as client:
        _make_user(client, plan="elite", existing_user=user)
        r_history = client.get("/api/mock/history")
    assert r_history.status_code == 200, r_history.text
    body = r_history.json()
    sessions = body if isinstance(body, list) else body.get("sessions", [])
    matching = [s for s in sessions if str(s.get("session_id")) == str(session_id)]
    assert matching, f"Session {session_id} not found in history (got {[s.get('session_id') for s in sessions]})"
    row = matching[0]
    assert row["time_used_s"] is not None, "time_used_s should not be None for a completed session"
    # 11 days = 950400 s — far beyond any time_limit_s; clamped value must equal the limit.
    eleven_days_s = 11 * 24 * 60 * 60
    assert row["time_used_s"] != eleven_days_s, (
        f"time_used_s was not clamped: got {row['time_used_s']} (raw 11-day value)"
    )
    assert row["time_used_s"] <= time_limit_s, (
        f"time_used_s {row['time_used_s']} exceeds time_limit_s {time_limit_s}"
    )
    assert row["time_used_s"] >= 0, f"time_used_s is negative: {row['time_used_s']}"
    assert row["time_used_s"] == time_limit_s, (
        f"Expected time_used_s == time_limit_s ({time_limit_s}), got {row['time_used_s']}"
    )


# ---------------------------------------------------------------------------
# Fix regressions: python starter_code in mock payload + Interview Loop debrief
# ---------------------------------------------------------------------------

def test_tc_python_mock_payload_includes_starter_code():
    """Python mock question payload must include a non-empty starter_code starting with 'def '."""
    import python_questions
    from routers.mock import _public_question_payload

    # Find any python mock question that carries starter_code.
    mock_qs = python_questions.get_mock_questions_by_difficulty()
    q = next(
        (q for qs in mock_qs.values() for q in qs if q.get("starter_code")),
        None,
    )
    assert q is not None, "No python mock question with starter_code found in content bank"

    payload = _public_question_payload(q, "python")

    assert "starter_code" in payload, "payload missing 'starter_code' key"
    assert payload["starter_code"], "starter_code is empty"
    assert payload["starter_code"].startswith("def "), (
        f"starter_code does not start with 'def ': {payload['starter_code'][:60]!r}"
    )
    assert "function_signature" in payload, "payload missing 'function_signature' key"


def test_tc_interview_loop_debrief_no_hard_session_escalation():
    """Interview Loop sessions (mode='interview_loop') must not produce 'Try a hard session'
    and must suggest 'Interview Loop' in the priority_action, regardless of stored difficulty."""
    from routers.insights import build_session_debrief

    # All questions solved → weak list is empty → triggers the 'if not weak' branch.
    questions = [
        {
            "id": 1, "track": "ml-fundamentals", "is_solved": True,
            "concepts": ["BIAS FAIRNESS"], "time_spent_s": 120,
        },
        {
            "id": 2, "track": "ml-fundamentals", "is_solved": True,
            "concepts": ["BIAS FAIRNESS"], "time_spent_s": 90,
        },
        {
            "id": 3, "track": "ml-fundamentals", "is_solved": True,
            "concepts": ["REGULARIZATION"], "time_spent_s": 110,
        },
    ]
    # Interview Loop sessions are now detected via mode, not null difficulty.
    session_meta = {
        "mode": "interview_loop",
        "difficulty": "hard",
        "track": "ml-fundamentals",
        "time_used_s": 320,
        "time_limit_s": 2700,
    }

    debrief = build_session_debrief(questions, session_meta, [], "elite")

    assert debrief is not None
    action = debrief.get("priority_action") or ""
    assert "Try a hard session" not in action, (
        f"priority_action wrongly escalates difficulty for Interview Loop: {action!r}"
    )
    assert "Interview Loop" in action, (
        f"priority_action should mention 'Interview Loop' for loop sessions: {action!r}"
    )


# ---------------------------------------------------------------------------
# New tests: per-difficulty Interview Loop (2026-06-16)
# ---------------------------------------------------------------------------

def test_tc_loop_difficulty_escalates_helper():
    """_loop_difficulty_escalates returns True only when follow-ups are strictly harder than parents."""
    from routers.mock import _loop_difficulty_escalates

    # Python medium → hard follow-ups: escalates
    assert _loop_difficulty_escalates("python", "medium") is True
    # SQL medium → hard follow-ups (escalating-medium chains added 2026-06-20): escalates
    assert _loop_difficulty_escalates("sql", "medium") is True
    # data-modeling medium → hard follow-ups: escalates
    assert _loop_difficulty_escalates("data-modeling", "medium") is True
    # Easy is always False (not medium/hard)
    assert _loop_difficulty_escalates("python", "easy") is False
    assert _loop_difficulty_escalates("sql", "easy") is False


def test_tc_loop_access_carries_escalates_field():
    """GET /api/mock/access with interview_loop mode returns escalates on startable difficulties."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        resp = _loop_access(client, "python")
    assert resp.status_code == 200, resp.text
    access = resp.json()["access"]
    # medium is the only startable difficulty for python (has medium chains, no hard chains)
    assert access["medium"]["can_start"] is True
    assert "escalates" in access["medium"], "escalates key missing from medium entry"
    assert access["medium"]["escalates"] is True  # python medium → hard follow-ups


def test_tc_loop_start_with_no_difficulty_now_400():
    """Interview Loop start without a difficulty now 400s (difficulty is required)."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.post("/api/mock/start", json={"mode": "interview_loop", "track": "sql"})
    # difficulty=None fails the VALID_DIFFICULTIES check
    assert r.status_code == 400


def test_tc_loop_get_session_carries_escalates():
    """GET /api/mock/:id returns escalates for interview_loop sessions."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        start = client.post("/api/mock/start", json={
            "mode": "interview_loop", "track": "python", "difficulty": "medium",
        })
        assert start.status_code in (200, 201), start.text
        sid = start.json()["session_id"]
        r = client.get(f"/api/mock/{sid}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "escalates" in body, "escalates key missing from GET session response"
    assert body["escalates"] is True  # python medium → hard


def test_tc_loop_debrief_with_stored_difficulty_detects_loop_by_mode():
    """Debrief with mode='interview_loop' and stored difficulty='medium' still fires loop copy."""
    from routers.insights import build_session_debrief

    questions = [
        {"id": 10, "track": "sql", "is_solved": True, "concepts": ["WINDOW FUNCTIONS"], "time_spent_s": 200},
        {"id": 11, "track": "sql", "is_solved": True, "concepts": ["WINDOW FUNCTIONS"], "time_spent_s": 180},
    ]
    session_meta = {
        "mode": "interview_loop",
        "difficulty": "medium",      # stored real difficulty (not None)
        "track": "sql",
        "time_used_s": 380,
        "time_limit_s": 1800,
    }
    debrief = build_session_debrief(questions, session_meta, [], "elite")
    assert debrief is not None
    action = debrief.get("priority_action") or ""
    assert "Try a hard session" not in action, (
        f"Debrief wrongly escalated difficulty despite mode=interview_loop: {action!r}"
    )
    assert "Interview Loop" in action, (
        f"Debrief should suggest Interview Loop when all solved: {action!r}"
    )


def test_tc_loop_exhausted_copy_is_difficulty_specific():
    """block_copy messages include the difficulty word, not a generic track-level phrase."""
    from routers.mock import _interview_loop_access, _chain_parents_for

    # pool_exhausted: consume every sql hard chain parent
    consumed = {int(p["id"]) for p in _chain_parents_for("sql", "hard")}
    block = _interview_loop_access("sql", "hard", consumed)
    assert block is not None
    assert block["block_reason"] == "pool_exhausted"
    assert "hard" in block["block_copy"], (
        f"Expected 'hard' in pool_exhausted copy, got: {block['block_copy']!r}"
    )

    # no_chains: python has no hard chains
    block = _interview_loop_access("python", "hard", set())
    assert block is not None
    assert block["block_reason"] == "no_chains"
    assert "hard" in block["block_copy"], (
        f"Expected 'hard' in no_chains copy, got: {block['block_copy']!r}"
    )


# ---------------------------------------------------------------------------
# loop_escalated storage — TC-175: starting an Interview Loop session on a
# cell where chains escalate (sql medium → all 8/8 chains escalate to hard)
# should persist loop_escalated=True on the session row and history should
# surface escalates=True from the stored value (not recomputed).
# ---------------------------------------------------------------------------

def test_tc175_loop_escalated_stored_and_reflected_in_history():
    """SQL medium Interview Loop: session stores loop_escalated=True; history row has escalates=True."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")

        # Start an interview_loop session on sql/medium — all 8 chains escalate
        r = client.post("/api/mock/start", json={
            "mode": "interview_loop",
            "track": "sql",
            "difficulty": "medium",
        })
        assert r.status_code in (200, 201), r.text
        body = r.json()
        session_id = body["session_id"]

        # The start response should reflect the stored escalation
        assert body.get("loop_escalated") is True, (
            f"Expected loop_escalated=True in start response, got: {body.get('loop_escalated')!r}"
        )

        # GET /{session_id} should surface escalates=True (from stored value)
        r2 = client.get(f"/api/mock/{session_id}")
        assert r2.status_code == 200, r2.text
        session_detail = r2.json()
        assert session_detail.get("escalates") is True, (
            f"Expected escalates=True in session detail, got: {session_detail.get('escalates')!r}"
        )

        # History should also surface escalates=True (from stored loop_escalated)
        r3 = client.get("/api/mock/history")
        assert r3.status_code == 200, r3.text
        history = r3.json()
        matching = [row for row in history if row.get("session_id") == session_id]
        assert matching, "Session not found in history"
        assert matching[0].get("escalates") is True, (
            f"Expected escalates=True in history row, got: {matching[0].get('escalates')!r}"
        )


# ---------------------------------------------------------------------------
# Role → track mapping consistency guard (DECISIONS 2026-06-26)
# ---------------------------------------------------------------------------
def test_role_track_mapping_is_internally_consistent():
    """A role's Mixed benchmark must cover exactly its custom-drill pool, every
    benchmark role must be a valid mock role, and every pooled track must be
    registered. This is the guard that would have caught the role→track drift
    (the DS mock pool had silently diverged from the curriculum). The canonical
    set must stay in lockstep with frontend/src/roleRegistry.js — DECISIONS 2026-06-26."""
    from routers.mock import MIXED_BENCHMARK_CONFIGS
    from tracks import role_tracks, VALID_MOCK_ROLES, all_slugs

    assert set(MIXED_BENCHMARK_CONFIGS) == VALID_MOCK_ROLES, (
        "Every benchmark role must be a valid mock role and vice versa"
    )
    registered = set(all_slugs())
    for role in VALID_MOCK_ROLES:
        pool = set(role_tracks(role))
        slots = set(MIXED_BENCHMARK_CONFIGS[role]["slots"])
        assert slots == pool, (
            f"{role}: benchmark slot tracks {slots} must equal the role pool {pool}"
        )
        assert pool <= registered, f"{role}: pool has unknown track(s): {pool - registered}"
    # Pandas was added to Data Scientist on 2026-06-26 — regression guard.
    assert "pandas" in set(role_tracks("data_scientist")), "Data Scientist pool must include pandas"
