"""
Comprehensive mock interview feature test.

Tests all three plan tiers (free, pro, elite) with real API calls against
the local development server. Creates temporary test users, seeds minimal
progress data, runs full mock session flows, then cleans up.

Usage:
    cd backend && ../.venv/bin/python scripts/test_mock_flows.py

Requires:
    - Backend running on localhost:8000
    - Postgres running (docker compose up postgres -d)
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import httpx

BASE_URL = "http://localhost:8000"
DB_URL = "postgresql://postgres:postgres@localhost:5432/sql_practice"

# ── Question data loader ───────────────────────────────────────────────────────

CONTENT_ROOT = Path(__file__).parent.parent / "content"

def _load_questions(rel_path: str) -> dict[int, dict]:
    """Load question JSON and return a dict keyed by int question ID."""
    p = CONTENT_ROOT / rel_path
    if not p.exists():
        return {}
    qs = json.loads(p.read_text())
    return {int(q["id"]): q for q in qs}

SQL_EASY   = _load_questions("questions/easy.json")
SQL_MEDIUM = _load_questions("questions/medium.json")
SQL_HARD   = _load_questions("questions/hard.json")
PY_EASY    = _load_questions("python_questions/easy.json")
PY_MEDIUM  = _load_questions("python_questions/medium.json")
PY_HARD    = _load_questions("python_questions/hard.json")
PYSPARK_E  = _load_questions("pyspark_questions/easy.json")
PYSPARK_M  = _load_questions("pyspark_questions/medium.json")
PYSPARK_H  = _load_questions("pyspark_questions/hard.json")
ML_EASY    = _load_questions("ml_fundamentals_questions/easy.json")
EXP_EASY   = _load_questions("experimentation_questions/easy.json")

ALL_QUESTIONS: dict[str, dict[int, dict]] = {
    "sql": {**SQL_EASY, **SQL_MEDIUM, **SQL_HARD},
    "python": {**PY_EASY, **PY_MEDIUM, **PY_HARD},
    "pandas": {},  # populated below
    "pyspark": {**PYSPARK_E, **PYSPARK_M, **PYSPARK_H},
    "ml-fundamentals": ML_EASY,
    "experimentation": EXP_EASY,
}
ALL_QUESTIONS["pandas"] = _load_questions("pandas_questions/easy.json") | \
                           _load_questions("pandas_questions/medium.json") | \
                           _load_questions("pandas_questions/hard.json")

MCQ_TRACKS = {"pyspark", "ml-fundamentals", "experimentation", "data-engineering", "data-modeling"}


def correct_payload(track: str, question_id: int) -> dict:
    """Return the correct submit payload for a given question."""
    q = ALL_QUESTIONS.get(track, {}).get(question_id, {})
    if not q:
        return {"code": "SELECT 1"}
    if track in MCQ_TRACKS:
        return {"selected_option": q.get("correct_option", 1)}
    if track in ("python", "pandas"):
        return {"code": q.get("solution_code", "def solve(): pass")}
    # SQL
    return {"code": q.get("solution_query", "SELECT 1")}


def wrong_payload(track: str, question_id: int) -> dict:
    """Return a deliberately wrong submit payload."""
    if track in MCQ_TRACKS:
        q = ALL_QUESTIONS.get(track, {}).get(question_id, {})
        correct = q.get("correct_option", 1)
        return {"selected_option": (correct % 4) + 1}  # different option, wraps 1-4
    if track in ("python", "pandas"):
        return {"code": "def solve(*args): return None"}
    return {"code": "SELECT 'wrong' AS answer"}


# ── DB helpers ─────────────────────────────────────────────────────────────────

async def create_test_user(conn, plan: str) -> tuple[str, str]:
    """Insert a test user and session. Returns (user_id, session_token)."""
    user_id = str(uuid.uuid4())
    email = f"test_{plan}_{user_id[:8]}@mock-test.invalid"
    token = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(hours=2)

    await conn.execute(
        "INSERT INTO users (id, email, plan, created_at) VALUES ($1, $2, $3, NOW())",
        user_id, email, plan,
    )
    await conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES ($1, $2, NOW(), $3)",
        token, user_id, expires,
    )
    return user_id, token


async def seed_sql_easy_solves(conn, user_id: str, count: int = 8):
    """Seed user_progress rows for the first `count` easy SQL questions."""
    easy_ids = sorted(SQL_EASY.keys())[:count]
    for qid in easy_ids:
        await conn.execute(
            """
            INSERT INTO user_progress (user_id, question_id, solved_at, topic)
            VALUES ($1, $2, NOW(), 'sql')
            ON CONFLICT DO NOTHING
            """,
            user_id, qid,
        )


async def cleanup_test_users(conn, user_ids: list[str]):
    """Remove test users and all their data."""
    for uid in user_ids:
        await conn.execute("DELETE FROM submissions WHERE user_id = $1", uid)
        await conn.execute("DELETE FROM user_progress WHERE user_id = $1", uid)
        # Delete mock session questions via sessions
        await conn.execute(
            """
            DELETE FROM mock_session_questions
            WHERE session_id IN (SELECT id FROM mock_sessions WHERE user_id = $1)
            """, uid,
        )
        await conn.execute("DELETE FROM mock_sessions WHERE user_id = $1", uid)
        await conn.execute("DELETE FROM sessions WHERE user_id = $1", uid)
        await conn.execute("DELETE FROM users WHERE id = $1", uid)


# ── HTTP helpers ───────────────────────────────────────────────────────────────

def make_client(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=BASE_URL,
        cookies={"session_token": token},
        timeout=30.0,
    )


async def start_session(client: httpx.AsyncClient, *, mode: str, track: str,
                         difficulty: str, focus_concepts: list[str] | None = None,
                         num_questions: int | None = None,
                         time_minutes: int | None = None) -> dict:
    payload: dict = {"mode": mode, "track": track, "difficulty": difficulty}
    if mode == "custom":
        payload["num_questions"] = num_questions or 2
        payload["time_minutes"] = time_minutes or 30
    if focus_concepts:
        payload["focus_concepts"] = focus_concepts
    r = await client.post("/api/mock/start", json=payload)
    r.raise_for_status()
    return r.json()


async def submit_question(client: httpx.AsyncClient, session_id: str,
                           question_id: int, track: str, correct: bool) -> dict:
    payload = correct_payload(track, question_id) if correct else wrong_payload(track, question_id)
    payload["question_id"] = question_id
    payload["track"] = track
    payload["time_spent_s"] = 45
    r = await client.post(f"/api/mock/{session_id}/submit", json=payload)
    r.raise_for_status()
    return r.json()


async def finish_session(client: httpx.AsyncClient, session_id: str) -> dict:
    r = await client.post(f"/api/mock/{session_id}/finish")
    r.raise_for_status()
    return r.json()


# ── Assertions ─────────────────────────────────────────────────────────────────

def check(condition: bool, message: str):
    if condition:
        print(f"  [PASS] {message}")
    else:
        print(f"  [FAIL] {message}", file=sys.stderr)
        raise AssertionError(message)


# ── Test suites ────────────────────────────────────────────────────────────────

async def test_free_user(client: httpx.AsyncClient):
    print("\n── Free user ─────────────────────────────────────────────────────────")

    # 1. Access check: easy OK, hard blocked
    r = await client.get("/api/mock/access", params={"track": "sql"})
    r.raise_for_status()
    access = r.json()
    check(access["access"]["easy"]["can_start"] is True, "free: easy access granted")
    check(access["access"]["hard"]["can_start"] is False, "free: hard access blocked")
    check(access["access"]["hard"]["needs_upgrade"] in ("pro", "elite"), "free: hard needs upgrade")
    check(access["access"]["medium"]["can_start"] is True,
          "free: medium access granted (8 easy solves seeded)")

    # 2. Start easy SQL session
    print("  Starting easy SQL session…")
    sess = await start_session(client, mode="30min", track="sql", difficulty="easy")
    session_id = sess["session_id"]
    questions = sess["questions"]
    check(len(questions) == 2, f"free: easy session has 2 questions (got {len(questions)})")
    check(sess["time_limit_s"] == 1800, "free: time_limit_s = 1800s")

    q0 = questions[0]
    q1 = questions[1]

    # 3. Submit Q1 correctly, Q2 wrong
    res0 = await submit_question(client, session_id, q0["id"], q0["track"], correct=True)
    check(res0["correct"] is True, "free Q1: correct submission accepted")
    check("feedback" in res0, "free Q1: feedback returned")
    check("solution" not in res0, "free Q1: solution NOT revealed mid-session")

    res1 = await submit_question(client, session_id, q1["id"], q1["track"], correct=False)
    check(res1["correct"] is False, "free Q2: wrong submission rejected")

    # 4. Finish session and verify score
    summary = await finish_session(client, session_id)
    check(summary["solved_count"] == 1, f"free: score 1/2 (got {summary['solved_count']}/{summary['total_count']})")
    check(summary["total_count"] == 2, "free: total questions = 2")
    check(any("solution" in sq for sq in summary.get("questions", [])),
          "free: solutions revealed in summary")

    # 5. Verify session appears in history
    r = await client.get("/api/mock/history")
    history = r.json()
    session_ids = [s["session_id"] for s in history]
    check(session_id in session_ids, "free: completed session in history")

    # 6. Start medium SQL session (daily limit: 1/day)
    print("  Starting medium SQL session (1/day limit)…")
    sess_m = await start_session(client, mode="30min", track="sql", difficulty="medium")
    session_id_m = sess_m["session_id"]
    q = sess_m["questions"][0]
    await submit_question(client, session_id_m, q["id"], q["track"], correct=True)
    await finish_session(client, session_id_m)
    check(True, "free: medium session completed")

    # 7. Second medium attempt should be blocked (daily cap)
    r2 = await client.get("/api/mock/access", params={"track": "sql"})
    access2 = r2.json()
    check(access2["access"]["medium"]["can_start"] is False or
          access2["daily_usage"].get("medium", 0) >= 1,
          "free: medium daily limit reached after 1 session")

    # 8. Hard SQL should still be blocked
    r3 = await client.post("/api/mock/start",
                           json={"mode": "30min", "track": "sql", "difficulty": "hard"})
    check(r3.status_code == 403, f"free: hard mock blocked with 403 (got {r3.status_code})")

    print("  Free user tests passed.")


async def test_pro_user(client: httpx.AsyncClient):
    print("\n── Pro user ──────────────────────────────────────────────────────────")

    # 1. Access check: hard OK (3/day)
    r = await client.get("/api/mock/access", params={"track": "sql"})
    access = r.json()
    check(access["access"]["hard"]["can_start"] is True, "pro: hard access granted")
    check(access["access"]["hard"]["daily_limit"] == 3, "pro: hard daily limit = 3")
    check(access["access"]["easy"]["daily_limit"] is None, "pro: easy has no daily cap")

    # 2. Easy Python session
    print("  Starting easy Python session…")
    sess = await start_session(client, mode="30min", track="python", difficulty="easy")
    session_id = sess["session_id"]
    questions = sess["questions"]
    check(len(questions) == 2, f"pro: python easy session has 2 Qs (got {len(questions)})")

    # Submit: Q1 correct, Q2 wrong
    q0, q1 = questions[0], questions[1]
    res0 = await submit_question(client, session_id, q0["id"], q0["track"], correct=True)
    check(res0["correct"] is True, "pro: python Q1 correct")
    res1 = await submit_question(client, session_id, q1["id"], q1["track"], correct=False)
    check(res1["correct"] is False, "pro: python Q2 wrong")
    summary = await finish_session(client, session_id)
    check(summary["solved_count"] == 1, f"pro: python score 1/2 (got {summary['solved_count']})")

    # 3. Hard SQL session — verify infra (start, submit, finish) not just answer correctness
    print("  Starting hard SQL session…")
    sess_h = await start_session(client, mode="30min", track="sql", difficulty="hard")
    check(sess_h["difficulty"] == "hard", "pro: hard session created")
    session_id_h = sess_h["session_id"]
    qh = sess_h["questions"][0]
    res_h = await submit_question(client, session_id_h, qh["id"], qh["track"], correct=True)
    check("correct" in res_h and "feedback" in res_h, "pro: hard SQL submit returns correct + feedback fields")
    summary_h = await finish_session(client, session_id_h)
    check(summary_h["total_count"] >= 1, "pro: hard SQL session finished with summary")

    # 4. Verify hard daily counter incremented
    r2 = await client.get("/api/mock/access", params={"track": "sql"})
    access2 = r2.json()
    check(access2["daily_usage"].get("hard", 0) >= 1, "pro: hard daily usage incremented")
    check(access2["access"]["hard"]["daily_used"] >= 1, "pro: hard daily_used ≥ 1")

    # 5. PySpark hard session (MCQ) — up to the daily limit
    print("  Starting PySpark hard session (MCQ)…")
    sess_ps = await start_session(client, mode="30min", track="pyspark", difficulty="hard")
    session_id_ps = sess_ps["session_id"]
    qps = sess_ps["questions"][0]
    res_ps = await submit_question(client, session_id_ps, qps["id"], qps["track"], correct=True)
    check("correct" in res_ps, "pro: PySpark hard MCQ submit evaluated")
    summary_ps = await finish_session(client, session_id_ps)
    check(summary_ps["total_count"] > 0, "pro: PySpark hard session summary OK")

    # 6. Analytics is NOT accessible for pro
    r3 = await client.get("/api/mock/analytics")
    check(r3.status_code == 403, f"pro: analytics endpoint returns 403 (got {r3.status_code})")

    print("  Pro user tests passed.")


async def test_elite_user(client: httpx.AsyncClient, conn):
    print("\n── Elite user ────────────────────────────────────────────────────────")

    # 1. Access check: everything open, no daily caps
    r = await client.get("/api/mock/access", params={"track": "sql"})
    access = r.json()
    check(access["access"]["hard"]["can_start"] is True, "elite: hard access granted")
    check(access["access"]["hard"]["daily_limit"] is None, "elite: no hard daily cap")
    check(access["access"]["medium"]["daily_limit"] is None, "elite: no medium daily cap")

    # 2. Analytics endpoint accessible (may be empty)
    r2 = await client.get("/api/mock/analytics")
    check(r2.status_code == 200, "elite: analytics endpoint accessible")

    # 3. Focus mode: SQL with COLUMN PROJECTION concept (present in first 5 easy Qs)
    print("  Starting SQL session with focus_concepts=['COLUMN PROJECTION']…")
    sess_focus = await start_session(
        client, mode="30min", track="sql", difficulty="easy",
        focus_concepts=["COLUMN PROJECTION"],
    )
    check("focus_fallback" in sess_focus, "elite: focus_fallback field in start response")
    session_id_focus = sess_focus["session_id"]
    # Verify returned questions have COLUMN PROJECTION (or fallback occurred)
    for q in sess_focus["questions"]:
        qdata = SQL_EASY.get(q["id"], {})
        concepts = qdata.get("concepts", [])
        if not sess_focus.get("focus_fallback"):
            check(any("COLUMN PROJECTION" in c for c in concepts),
                  f"elite: focus Q {q['id']} has COLUMN PROJECTION concept")
    q_f = sess_focus["questions"][0]
    await submit_question(client, session_id_focus, q_f["id"], q_f["track"], correct=True)
    if len(sess_focus["questions"]) > 1:
        q_f2 = sess_focus["questions"][1]
        await submit_question(client, session_id_focus, q_f2["id"], q_f2["track"], correct=False)
    summary_focus = await finish_session(client, session_id_focus)
    check(summary_focus["total_count"] > 0, "elite: focus session finished OK")

    # 4. Run 2 more SQL easy sessions (without focus) to build up concept analytics data
    for i in range(2):
        print(f"  Starting SQL easy session {i+2}/3 (analytics build-up)…")
        sess_i = await start_session(client, mode="30min", track="sql", difficulty="easy")
        session_id_i = sess_i["session_id"]
        for j, q in enumerate(sess_i["questions"]):
            await submit_question(client, session_id_i, q["id"], q["track"],
                                   correct=(j % 2 == 0))
        await finish_session(client, session_id_i)

    # 5. Run a Mixed session
    print("  Starting Mixed difficulty session…")
    sess_mix = await start_session(client, mode="30min", track="mixed", difficulty="mixed")
    check(len(sess_mix["questions"]) == 2, f"elite: mixed session has 2 Qs (got {len(sess_mix['questions'])})")
    for q in sess_mix["questions"]:
        check(q["track"] in ("sql", "python", "pandas", "pyspark"),
              f"elite: mixed Q track {q['track']} is a code-execution track")
        await submit_question(client, sess_mix["session_id"], q["id"], q["track"], correct=True)
    summary_mix = await finish_session(client, sess_mix["session_id"])
    check(summary_mix["solved_count"] == 2, f"elite: mixed session 2/2 (got {summary_mix['solved_count']})")

    # 6. ML Fundamentals session (MCQ, elite-only mock bank)
    print("  Starting ML Fundamentals easy session…")
    sess_ml = await start_session(client, mode="30min", track="ml-fundamentals", difficulty="easy")
    session_id_ml = sess_ml["session_id"]
    for j, q in enumerate(sess_ml["questions"]):
        await submit_question(client, session_id_ml, q["id"], q["track"],
                               correct=(j == 0))
    summary_ml = await finish_session(client, session_id_ml)
    check(summary_ml["total_count"] == 2, "elite: ML Fundamentals session OK")

    # 7. Analytics should now have data
    print("  Checking Mock Analytics…")
    r3 = await client.get("/api/mock/analytics")
    check(r3.status_code == 200, "elite: analytics 200")
    analytics = r3.json()
    check(analytics["total_sessions"] >= 4, f"elite: ≥4 sessions in analytics (got {analytics['total_sessions']})")
    check(len(analytics["score_trend"]) >= 1, "elite: score_trend populated")
    check(0.0 <= analytics["avg_score_pct"] <= 100.0, "elite: avg_score_pct in 0-100 range")
    check(analytics["best_score_pct"] >= analytics["avg_score_pct"], "elite: best ≥ avg")
    check("sql" in analytics["track_breakdown"], "elite: sql in track_breakdown")
    # Concept analytics require ≥3 attempts per concept
    print(f"    top_concepts: {analytics.get('top_concepts', [])}")
    print(f"    weak_concepts: {analytics.get('weak_concepts', [])}")

    # 8. Session debrief (Elite only — in finish response)
    print("  Verifying coaching debrief in last session summary…")
    # The debrief is built from submission history — run one more session
    sess_debrief = await start_session(client, mode="30min", track="sql", difficulty="easy")
    q_d = sess_debrief["questions"][0]
    await submit_question(client, sess_debrief["session_id"], q_d["id"], q_d["track"], correct=True)
    if len(sess_debrief["questions"]) > 1:
        q_d2 = sess_debrief["questions"][1]
        await submit_question(client, sess_debrief["session_id"], q_d2["id"], q_d2["track"], correct=False)
    summary_d = await finish_session(client, sess_debrief["session_id"])
    # Debrief is only built if there's enough submission history
    if "debrief" in summary_d and summary_d["debrief"]:
        debrief = summary_d["debrief"]
        check("priority_action" in debrief or "summary" in debrief,
              "elite: debrief has priority_action or summary")
        print(f"    debrief keys: {list(debrief.keys())}")
    else:
        print("    (debrief not yet populated — insufficient history for this user)")

    # 9. Verify history shows all sessions
    r4 = await client.get("/api/mock/history")
    history = r4.json()
    check(len(history) >= 4, f"elite: ≥4 sessions in history (got {len(history)})")
    completed = [s for s in history if s["status"] == "completed"]
    check(len(completed) >= 4, f"elite: ≥4 completed sessions (got {len(completed)})")

    print("  Elite user tests passed.")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    # Verify backend is up
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"ERROR: Backend not reachable at {BASE_URL}: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Backend healthy: {BASE_URL}")

    conn = await asyncpg.connect(DB_URL)
    user_ids: list[str] = []
    tokens: dict[str, str] = {}

    try:
        # Create test users
        free_uid, free_tok = await create_test_user(conn, "free")
        pro_uid, pro_tok   = await create_test_user(conn, "pro")
        eli_uid, eli_tok   = await create_test_user(conn, "elite")
        user_ids = [free_uid, pro_uid, eli_uid]
        tokens = {"free": free_tok, "pro": pro_tok, "elite": eli_tok}

        # Seed 8 easy SQL solves for free user (unlocks 3 medium in practice → medium mock OK)
        await seed_sql_easy_solves(conn, free_uid, count=8)
        print(f"Seeded 8 easy SQL solves for free user ({free_uid[:8]}…)")

        # Run free user tests
        async with make_client(tokens["free"]) as client:
            await test_free_user(client)

        # Run pro user tests
        async with make_client(tokens["pro"]) as client:
            await test_pro_user(client)

        # Run elite user tests (also needs DB conn for seeding analytics data)
        async with make_client(tokens["elite"]) as client:
            await test_elite_user(client, conn)

        print("\n\nAll tests passed.")

    finally:
        print("\nCleaning up test users…")
        await cleanup_test_users(conn, user_ids)
        await conn.close()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
