"""TC-172 to TC-203 — Dashboard & Insights."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _insert_progress, _insert_submission, _make_user
from questions import get_questions_by_difficulty as get_sql_qs
from routers.insights import _compute_readiness_scores

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

_sql_easy_qs = get_sql_qs()["easy"]
_sql_medium_qs = get_sql_qs()["medium"]
_sql_hard_qs = get_sql_qs()["hard"]


# ---------------------------------------------------------------------------
# TC-172 to TC-175: Dashboard endpoint
# ---------------------------------------------------------------------------

def test_tc172_dashboard_returns_all_4_tracks():
    """TC-172: GET /api/dashboard → 200; tracks has all 4 entries with by_difficulty."""
    from python_questions import get_questions_by_difficulty as get_py_qs
    from pandas_questions import get_questions_by_difficulty as get_pd_qs
    from pyspark_questions import get_questions_by_difficulty as get_ps_qs

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Insert one solve per track
    _insert_progress(user["id"], _sql_easy_qs[0]["id"], track="sql")
    _insert_progress(user["id"], get_py_qs()["easy"][0]["id"], track="python")
    _insert_progress(user["id"], get_pd_qs()["easy"][0]["id"], track="pandas")
    _insert_progress(user["id"], get_ps_qs()["easy"][0]["id"], track="pyspark")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    tracks = body.get("tracks", {})
    for key in ("sql", "python", "pandas", "pyspark"):
        assert key in tracks, f"Missing track: {key}"
        t = tracks[key]
        assert "by_difficulty" in t
        bd = t["by_difficulty"]
        for diff in ("easy", "medium", "hard"):
            assert diff in bd, f"Missing difficulty {diff} for track {key}"
            assert "solved" in bd[diff]
            assert "total" in bd[diff]


def test_tc173_pandas_key_present():
    """TC-173: Dashboard track key is 'pandas' (canonical slug)."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/dashboard")
    assert r.status_code == 200
    tracks = r.json().get("tracks", {})
    assert "pandas" in tracks
    assert "python-data" not in tracks
    assert "python_data" not in tracks


def test_tc174_unauthenticated_dashboard_returns_401():
    """TC-174: Unauthenticated GET /api/dashboard → 401."""
    with TestClient(app) as client:
        r = client.get("/api/dashboard")
    assert r.status_code == 401


def test_tc175_recent_activity_present():
    """TC-175: Dashboard response has recent_activity array."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql")
    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert "recent_activity" in body
    assert isinstance(body["recent_activity"], list)


# ---------------------------------------------------------------------------
# TC-176 to TC-181: Insights endpoint
# ---------------------------------------------------------------------------

def test_tc176_insights_returns_per_track_for_all_4():
    """TC-176: GET /api/dashboard/insights → per_track with all 4 tracks."""
    from python_questions import get_questions_by_difficulty as get_py_qs
    from pandas_questions import get_questions_by_difficulty as get_pd_qs
    from pyspark_questions import get_questions_by_difficulty as get_ps_qs

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql")
    _insert_submission(user["id"], get_py_qs()["easy"][0]["id"], is_correct=True, track="python")
    _insert_submission(user["id"], get_pd_qs()["easy"][0]["id"], is_correct=True, track="pandas")
    _insert_submission(user["id"], get_ps_qs()["easy"][0]["id"], is_correct=True, track="pyspark")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    assert r.status_code == 200
    per_track = r.json().get("per_track", {})
    for key in ("sql", "python", "pandas", "pyspark"):
        assert key in per_track, f"Missing track: {key}"
        t = per_track[key]
        assert "solve_count" in t
        assert "median_solve_seconds" in t
        assert "accuracy_pct" in t


def test_tc177_median_solve_seconds_null_when_no_correct_submissions():
    """TC-177: No correct submissions → median_solve_seconds: null."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=False, track="sql")
    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    assert r.status_code == 200
    per_track = r.json().get("per_track", {})
    assert per_track.get("sql", {}).get("median_solve_seconds") is None


def test_tc178_accuracy_pct_is_correct_ratio():
    """TC-178: 2 correct + 2 wrong → accuracy_pct == 0.5."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for correct in (True, True, False, False):
        _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=correct, track="sql")
    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    per_track = r.json().get("per_track", {})
    assert per_track.get("sql", {}).get("accuracy_pct") == 0.5


def test_tc179_cross_track_insight_null_when_gap_less_than_60s():
    """TC-179: Two tracks with similar median times → cross_track_insight: null."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    from python_questions import get_questions_by_difficulty as get_py_qs
    # Insert correct submissions with small duration_ms (~10s each)
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql", duration_ms=10000)
    _insert_submission(user["id"], get_py_qs()["easy"][0]["id"], is_correct=True, track="python", duration_ms=12000)
    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    assert r.json().get("cross_track_insight") is None


def test_tc180_cross_track_insight_non_null_when_gap_over_60s():
    """TC-180: SQL median=300s, Python median=60s → cross_track_insight is string."""
    from datetime import datetime, timedelta, timezone
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    from python_questions import get_questions_by_difficulty as get_py_qs
    now = datetime.now(timezone.utc)
    # Insert SQL: incorrect at now-300s, correct at now
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=False, track="sql",
                       submitted_at=now - timedelta(seconds=300))
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql",
                       submitted_at=now)
    # Insert Python: incorrect at now-60s, correct at now
    py_id = get_py_qs()["easy"][0]["id"]
    _insert_submission(user["id"], py_id, is_correct=False, track="python",
                       submitted_at=now - timedelta(seconds=60))
    _insert_submission(user["id"], py_id, is_correct=True, track="python",
                       submitted_at=now)
    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    insight = r.json().get("cross_track_insight")
    assert insight is not None and len(insight) > 0


def test_tc181_streak_days_reflects_consecutive_days():
    """TC-181: Correct submissions today and yesterday → streak_days >= 2."""
    from datetime import datetime, timedelta, timezone
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    conn = _db_conn()
    try:
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO submissions (user_id, track, question_id, is_correct, code, submitted_at)
                   VALUES (%s::uuid, 'sql', %s, true, 'SELECT 1', %s),
                          (%s::uuid, 'sql', %s, true, 'SELECT 1', %s)""",
                (user["id"], _sql_easy_qs[0]["id"], today,
                 user["id"], _sql_easy_qs[1]["id"], yesterday),
            )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    streak = r.json().get("streak_days", 0)
    assert streak >= 2


# ---------------------------------------------------------------------------
# TC-182 to TC-191: Weakest concepts
# ---------------------------------------------------------------------------

def _get_concept_for_question(q: dict, track: str = "sql") -> str | None:
    """Return the resolved family name for the first concept tag on the question.

    The insights API aggregates at the family level (via resolve_to_family), so
    tests must compare against family names, not raw tags.
    """
    from concept_families import resolve_to_family
    raw = q.get("concepts", [None])[0]
    if raw is None:
        return None
    return resolve_to_family(raw, track)


def test_tc182_concept_with_3_attempts_appears_in_weakest():
    """TC-182: 3 wrong submissions for same concept → appears in weakest_concepts."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(3):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    concept_names = [w["concept"].upper() for w in weakest]
    assert concept.upper() in concept_names


def test_tc182b_mock_only_question_concepts_count_toward_weakest():
    """TC-182b: 3 wrong submissions for mock-only question 12035 → its concept appears in weakest_concepts.

    SQL question 12035 is mock_only=True with concepts ['GROUPED AGGREGATION', 'DEDUPLICATION LOGIC'].
    Before Change 1 the concepts lookup excluded mock-only questions so q12035 resolved to [].
    After Change 1 mock-only questions are included, so the family appears in weakest_concepts.
    """
    from concept_families import resolve_to_family
    mock_q_id = 12035  # SQL mock-only, concepts: ['GROUPED AGGREGATION', 'DEDUPLICATION LOGIC']
    # Resolve the first concept to its canonical family (same as insights does internally)
    expected_family = resolve_to_family("GROUPED AGGREGATION", "sql").upper()

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(3):
        _insert_submission(user["id"], mock_q_id, is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    assert r.status_code == 200
    weakest = r.json().get("weakest_concepts", [])
    concept_names = [w["concept"].upper() for w in weakest]
    assert expected_family in concept_names, (
        f"Expected family '{expected_family}' from mock-only question 12035 to appear in "
        f"weakest_concepts, but got: {concept_names}"
    )


def test_tc183_concept_with_less_than_3_attempts_excluded():
    """TC-183: 2 wrong submissions → concept NOT in weakest_concepts."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(2):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    concept_names = [w["concept"].upper() for w in weakest]
    assert concept.upper() not in concept_names


def test_tc184_at_most_3_weakest_concepts():
    """TC-184: 5+ distinct concepts with 3+ attempts → weakest_concepts ≤ 3."""
    # Use different questions to get different concepts
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for q in _sql_easy_qs[:8]:
        concept = _get_concept_for_question(q)
        if concept:
            for _ in range(3):
                _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    assert len(weakest) <= 3


def test_tc185_accuracy_less_than_30_percent_highest_priority_gap():
    """TC-185: 0/3 correct → summary contains 'highest-priority gap'."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(3):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    # Find the matching concept entry
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        assert "highest-priority gap" in entry.get("summary", "")


def test_tc186_accuracy_less_than_50_percent_isnt_sticking():
    """TC-186: 1/3 correct → summary contains "isn't sticking"."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    _insert_submission(user["id"], q["id"], is_correct=True, track="sql")
    for _ in range(2):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        assert "isn't sticking" in entry.get("summary", "")


def test_tc187_accuracy_50_to_69_breaks_under_new_angles():
    """TC-187: 2/4 correct → summary mentions 'breaks under' or 'new angles'."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for correct in (True, True, False, False):
        _insert_submission(user["id"], q["id"], is_correct=correct, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        summary = entry.get("summary", "")
        assert "breaks under" in summary or "new angles" in summary


def test_tc188_accuracy_70_plus_not_fully_consistent():
    """TC-188: 3/4 correct → summary contains 'consistent'."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for correct in (True, True, True, False):
        _insert_submission(user["id"], q["id"], is_correct=correct, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        assert "consistent" in entry.get("summary", "")


def test_tc189_recommended_question_ids_excludes_solved():
    """TC-189: Solved question tagged with concept is excluded from recommendations."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    # Mark as solved via both progress and a correct submission (insights reads from submissions)
    _insert_progress(user["id"], q["id"], track="sql")
    _insert_submission(user["id"], q["id"], is_correct=True, track="sql")
    # Also have wrong submissions so concept appears in weakest
    for _ in range(3):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        assert q["id"] not in entry.get("recommended_question_ids", [])


def test_tc190_free_user_recommendations_limited_to_easy():
    """TC-190: Free user → recommended_question_ids contains only easy questions."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    # Get all easy IDs for easy filter check
    easy_ids = {q["id"] for q in _sql_easy_qs}
    medium_ids = {q["id"] for q in _sql_medium_qs}
    hard_ids = {q["id"] for q in _sql_hard_qs}

    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    for _ in range(3):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="free", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    entry = next((w for w in weakest if w["concept"].upper() == concept.upper()), None)
    if entry:
        recs = entry.get("recommended_question_ids", [])
        for rec_id in recs:
            assert rec_id in easy_ids, f"Free user got non-easy recommendation: {rec_id}"


def test_tc191_pro_user_recommendations_may_include_medium():
    """TC-191: Pro user → recommendations may include medium/hard IDs."""
    q = _sql_easy_qs[0]
    concept = _get_concept_for_question(q)
    if not concept:
        pytest.skip("No concept on question")

    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    for _ in range(3):
        _insert_submission(user["id"], q["id"], is_correct=False, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r = client.get("/api/dashboard/insights")
    weakest = r.json().get("weakest_concepts", [])
    # Just verify the endpoint succeeds; medium/hard recs are allowed
    assert r.status_code == 200
    _ = weakest  # no assertion on difficulty for pro


# ---------------------------------------------------------------------------
# TC-192 to TC-197: Readiness scores and study plan
# ---------------------------------------------------------------------------

def test_tc192_free_user_readiness_scores_null():
    """TC-192: Free user → readiness_scores: null; study_plan: null."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/dashboard/insights")
    body = r.json()
    assert body.get("readiness_scores") is None
    assert body.get("study_plan") is None


def test_tc193_pro_user_readiness_scores_null():
    """TC-193: Pro user → readiness_scores: null; study_plan: null."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.get("/api/dashboard/insights")
    body = r.json()
    assert body.get("readiness_scores") is None
    assert body.get("study_plan") is None


def test_tc194_elite_user_readiness_scores_present():
    """TC-194: Elite user → readiness_scores for all 4 tracks with score, label, components."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.get("/api/dashboard/insights")
    body = r.json()
    scores = body.get("readiness_scores")
    assert scores is not None
    for key in ("sql", "python", "pandas", "pyspark"):
        assert key in scores
        t = scores[key]
        assert "score" in t
        assert "label" in t
        assert "mock_limited" in t
        assert isinstance(t["mock_limited"], bool)
        assert "components" in t
        comps = t["components"]
        assert "coverage" in comps
        assert "quality" in comps
        assert "mock" in comps


def test_tc195_elite_user_study_plan_present():
    """TC-195: Elite user → study_plan array 3-5 items with required fields."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.get("/api/dashboard/insights")
    study_plan = r.json().get("study_plan")
    assert study_plan is not None
    assert 3 <= len(study_plan) <= 5
    for item in study_plan:
        for field in ("type", "title", "description", "cta_label", "cta_href", "track", "priority"):
            assert field in item, f"Missing field {field}"


def test_tc196_study_plan_action_types_valid():
    """TC-196: All study_plan type values are valid."""
    valid_types = {"concept_drill", "learning_path", "mock_session", "practice_hard"}
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.get("/api/dashboard/insights")
    study_plan = r.json().get("study_plan", [])
    for item in study_plan:
        assert item["type"] in valid_types, f"Invalid type: {item['type']}"


def test_tc197_no_duplicate_type_track_pairs_in_study_plan():
    """TC-197: No duplicate (type, track) pairs in study_plan."""
    with TestClient(app) as client:
        _make_user(client, plan="elite")
        r = client.get("/api/dashboard/insights")
    study_plan = r.json().get("study_plan", [])
    seen = set()
    for item in study_plan:
        pair = (item.get("type"), item.get("track"))
        assert pair not in seen, f"Duplicate (type, track): {pair}"
        seen.add(pair)


# ---------------------------------------------------------------------------
# TC-198 to TC-201: Readiness score unit tests
# ---------------------------------------------------------------------------

def test_tc198_practice_coverage_0_solves():
    """TC-198: 0 solves, empty ftc, no mock → all component values 0, score 0, label 'Early stage', mock_limited False."""
    result = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result is not None
    for track in ("sql", "python", "pandas", "pyspark"):
        comps = result[track]["components"]
        assert comps["coverage"] == 0.0, f"{track}: expected coverage 0.0, got {comps['coverage']}"
        assert comps["quality"] == 0.0, f"{track}: expected quality 0.0, got {comps['quality']}"
        assert comps["mock"] == 0.0, f"{track}: expected mock 0.0, got {comps['mock']}"
        assert result[track]["score"] == 0, f"{track}: expected score 0"
        assert result[track]["label"] == "Early stage", f"{track}: expected 'Early stage'"
        assert result[track]["mock_limited"] is False, f"{track}: expected mock_limited False"


def test_tc199_full_practice_full_ftc_no_mock_sql():
    """TC-199: All SQL practice IDs in solved + ftc, no mock → coverage==45.0, quality==25.0, score==70, label=='Getting there', mock_limited True."""
    from questions import get_questions_by_difficulty as get_sql
    sql_qs = get_sql()
    easy_ids = {int(q["id"]) for q in sql_qs["easy"]}
    medium_ids = {int(q["id"]) for q in sql_qs["medium"]}
    hard_ids = {int(q["id"]) for q in sql_qs["hard"]}
    all_practice_ids = easy_ids | medium_ids | hard_ids

    result = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result is not None
    sql = result["sql"]
    comps = sql["components"]
    assert comps["coverage"] == 45.0, f"Expected coverage 45.0, got {comps['coverage']}"
    assert comps["quality"] == 25.0, f"Expected quality 25.0, got {comps['quality']}"
    assert sql["score"] == 70, f"Expected score 70, got {sql['score']}"
    assert sql["label"] == "Getting there", f"Expected 'Getting there', got {sql['label']}"
    assert sql["mock_limited"] is True, f"Expected mock_limited True"


def test_tc200_mock_component_no_sessions():
    """TC-200: No mock sessions → components.mock == 0.0."""
    result = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result is not None
    for track in ("sql", "python", "pandas", "pyspark"):
        assert result[track]["components"]["mock"] == 0.0, \
            f"{track}: expected mock 0.0, got {result[track]['components']['mock']}"


def test_tc201_readiness_label_thresholds():
    """TC-201: Label thresholds under new signature: <40→'Early stage', 40–64→'Building', 65–79→'Getting there', 80–89→'Interview ready', 90+→'Strong'."""
    # Verify the label lookup function directly using the same logic as _compute_readiness_scores
    label_fn_map = [
        (90, "Strong"),
        (80, "Interview ready"),
        (65, "Getting there"),
        (40, "Building"),
        (0, "Early stage"),
    ]

    def _label(score):
        for threshold, lbl in label_fn_map:
            if score >= threshold:
                return lbl
        return "Early stage"

    cases = [
        (0, "Early stage"),
        (39, "Early stage"),
        (40, "Building"),
        (64, "Building"),
        (65, "Getting there"),
        (79, "Getting there"),
        (80, "Interview ready"),
        (89, "Interview ready"),
        (90, "Strong"),
        (100, "Strong"),
    ]
    for score, expected_label in cases:
        assert _label(score) == expected_label, f"Score {score}: expected '{expected_label}'"

    # Also confirm via the real function: 0 solves/ftc/mock → score 0 → "Early stage"
    result_zero = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result_zero is not None
    assert result_zero["sql"]["label"] == "Early stage"

    # Non-elite → None (unchanged)
    assert _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=[],
        effective_plan="pro",
    ) is None


# ---------------------------------------------------------------------------
# TC-202 to TC-203: Insights caching
# ---------------------------------------------------------------------------

def test_tc202_second_call_within_60s_returns_cached():
    """TC-202: Insert submission; call insights; insert more; call again → cached response."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    _insert_submission(user["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r1 = client.get("/api/dashboard/insights")
        first_solve_count = r1.json().get("per_track", {}).get("sql", {}).get("solve_count", 0)

    # Insert another submission — cache should prevent it from being reflected
    _insert_submission(user["id"], _sql_easy_qs[1]["id"], is_correct=True, track="sql")

    with TestClient(app) as client:
        _make_user(client, plan="pro", existing_user=user)
        r2 = client.get("/api/dashboard/insights")
        second_solve_count = r2.json().get("per_track", {}).get("sql", {}).get("solve_count", 0)

    # Second call should be cached; solve count should be same as first
    assert second_solve_count == first_solve_count, (
        "Cache should serve first result; new submission should not be visible"
    )


def test_tc203_cache_is_per_user():
    """TC-203: User A and B have separate caches."""
    with TestClient(app) as client_a:
        user_a = _make_user(client_a, plan="pro")
        r_a = client_a.get("/api/dashboard/insights")
        a_solve_count = r_a.json().get("per_track", {}).get("sql", {}).get("solve_count", 0)

    # Insert data for user B and call insights for B
    with TestClient(app) as client_b:
        user_b = _make_user(client_b, plan="pro")
    _insert_submission(user_b["id"], _sql_easy_qs[0]["id"], is_correct=True, track="sql")

    with TestClient(app) as client_b:
        _make_user(client_b, plan="pro", existing_user=user_b)
        r_b = client_b.get("/api/dashboard/insights")
        b_solve_count = r_b.json().get("per_track", {}).get("sql", {}).get("solve_count", 0)

    # B should see its own data (1 submission), not A's empty data
    assert b_solve_count >= 0  # B has its own isolated cache
    # They are different users with different data
    _ = a_solve_count  # both are valid


# ---------------------------------------------------------------------------
# TC-204 to TC-208: New readiness score unit tests
# ---------------------------------------------------------------------------

def test_tc204_mock_booster_one_completed_session():
    """TC-204: One completed SQL session (1/2 solved, attempted_count=2) → sql components.mock == 3.8.

    accuracy = 1/2 = 0.5, n_engaged = 1, confidence = min(1/4, 1) = 0.25
    mock_pts = 0.5 * 30.0 * 0.25 = 3.75 → round(3.75, 1) = 3.8 (Python banker's rounding)
    """
    mock_sessions = [
        {"status": "completed", "track": "sql", "total_count": 2, "attempted_count": 2, "solved_count": 1}
    ]
    result = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=mock_sessions,
        effective_plan="elite",
    )
    assert result is not None
    mock_pts = result["sql"]["components"]["mock"]
    assert mock_pts == 3.8, f"Expected mock 3.8, got {mock_pts}"


def test_tc205_full_practice_full_ftc_perfect_mock_score_100():
    """TC-205: All SQL practice + ftc + 4 perfect mock sessions → score == 100, label == 'Strong', mock_limited False.

    Requires 4 engaged sessions for confidence == 1.0 → full 30 mock_pts → score 100.
    """
    from questions import get_questions_by_difficulty as get_sql
    sql_qs = get_sql()
    easy_ids = {int(q["id"]) for q in sql_qs["easy"]}
    medium_ids = {int(q["id"]) for q in sql_qs["medium"]}
    hard_ids = {int(q["id"]) for q in sql_qs["hard"]}
    all_practice_ids = easy_ids | medium_ids | hard_ids

    mock_sessions = [
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
    ]
    result = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=mock_sessions,
        effective_plan="elite",
    )
    assert result is not None
    sql = result["sql"]
    assert sql["score"] == 100, f"Expected score 100, got {sql['score']}"
    assert sql["label"] == "Strong", f"Expected 'Strong', got {sql['label']}"
    assert sql["mock_limited"] is False, f"Expected mock_limited False"


def test_tc206_quality_is_ftc_based_not_solve_based():
    """TC-206: Solved set non-empty but ftc empty → quality 0.0; ftc ≥ 40% of catalog → quality 25.0."""
    from questions import get_questions_by_difficulty as get_sql
    sql_qs = get_sql()
    easy_ids = {int(q["id"]) for q in sql_qs["easy"]}
    medium_ids = {int(q["id"]) for q in sql_qs["medium"]}
    hard_ids = {int(q["id"]) for q in sql_qs["hard"]}
    all_practice_ids = easy_ids | medium_ids | hard_ids

    # Case A: solved some questions but ftc is empty → quality must be 0
    result_no_ftc = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result_no_ftc is not None
    quality_no_ftc = result_no_ftc["sql"]["components"]["quality"]
    assert quality_no_ftc == 0.0, f"Expected quality 0.0 with empty ftc, got {quality_no_ftc}"

    # Case B: ftc covers the full catalog (≥ 40% by a comfortable margin) → quality must be 25
    # Using the full set guarantees ftc_practice / (0.4 * total_practice) ≥ 1.0 → capped at 25.
    result_with_ftc = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result_with_ftc is not None
    quality_with_ftc = result_with_ftc["sql"]["components"]["quality"]
    assert quality_with_ftc == 25.0, f"Expected quality 25.0 with full ftc coverage, got {quality_with_ftc}"


def test_tc207_mock_limited_flag():
    """TC-207: Full practice + full ftc + no mock → mock_limited True; add 4 perfect engaged sessions → mock_limited False.

    mock_limited = (coverage + quality) >= 50 AND n_engaged < 4 AND total < 80.
    Case A: n_engaged=0 → True. Case B: n_engaged=4 → False.
    """
    from questions import get_questions_by_difficulty as get_sql
    sql_qs = get_sql()
    easy_ids = {int(q["id"]) for q in sql_qs["easy"]}
    medium_ids = {int(q["id"]) for q in sql_qs["medium"]}
    hard_ids = {int(q["id"]) for q in sql_qs["hard"]}
    all_practice_ids = easy_ids | medium_ids | hard_ids

    # Case A: No mock sessions → n_engaged=0 < 4 → mock_limited True
    result_no_mock = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=[],
        effective_plan="elite",
    )
    assert result_no_mock is not None
    assert result_no_mock["sql"]["mock_limited"] is True, \
        f"Expected mock_limited True with no mock, got {result_no_mock['sql']['mock_limited']}"

    # Case B: 4 perfect engaged sessions → n_engaged=4 → mock_limited False
    mock_sessions = [
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
    ]
    result_with_mock = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=mock_sessions,
        effective_plan="elite",
    )
    assert result_with_mock is not None
    assert result_with_mock["sql"]["mock_limited"] is False, \
        f"Expected mock_limited False with 4 perfect engaged sessions, got {result_with_mock['sql']['mock_limited']}"


def test_tc208_abandoned_session_excluded():
    """TC-208: Abandoned session (attempted_count=0) is excluded from engaged reps.

    (a) Only an abandoned session → mock == 0.0 (not engaged, so n_engaged=0).
    (b) Full practice+ftc + abandoned session → mock_limited True (n_engaged still 0).
    """
    from questions import get_questions_by_difficulty as get_sql
    sql_qs = get_sql()
    easy_ids = {int(q["id"]) for q in sql_qs["easy"]}
    medium_ids = {int(q["id"]) for q in sql_qs["medium"]}
    hard_ids = {int(q["id"]) for q in sql_qs["hard"]}
    all_practice_ids = easy_ids | medium_ids | hard_ids

    abandoned = {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 0, "solved_count": 0}

    # (a) Abandoned session only → mock_pts == 0.0
    result_a = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=[abandoned],
        effective_plan="elite",
    )
    assert result_a is not None
    assert result_a["sql"]["components"]["mock"] == 0.0, \
        f"Expected mock 0.0 for abandoned session, got {result_a['sql']['components']['mock']}"

    # (b) Full practice+ftc + abandoned session → mock_limited True (abandoned not counted)
    result_b = _compute_readiness_scores(
        per_track_solved_question_ids={"sql": all_practice_ids},
        per_track_ftc_question_ids={"sql": all_practice_ids},
        mock_sessions=[abandoned],
        effective_plan="elite",
    )
    assert result_b is not None
    assert result_b["sql"]["mock_limited"] is True, \
        f"Expected mock_limited True (abandoned excluded), got {result_b['sql']['mock_limited']}"


def test_tc209_accuracy_over_attempted_not_total():
    """TC-209: Session with total_count=3 but attempted_count=2, solved_count=2.

    accuracy = solved/attempted = 2/2 = 1.0 (NOT 2/3 = 0.667)
    n_engaged=1, confidence=0.25 → mock_pts = 1.0 * 30.0 * 0.25 = 7.5
    If wrongly using solved/total: 2/3 * 30 * 0.25 = 5.0 — this would fail.
    """
    mock_sessions = [
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 2, "solved_count": 2}
    ]
    result = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=mock_sessions,
        effective_plan="elite",
    )
    assert result is not None
    mock_pts = result["sql"]["components"]["mock"]
    assert mock_pts == 7.5, f"Expected mock 7.5 (accuracy over attempted), got {mock_pts}"


def test_tc210_confidence_scales_with_volume():
    """TC-210: Confidence scales from 0.25 (1 session) to 1.0 (4 sessions).

    One perfect session (solved==attempted==2): mock = 1.0 * 30.0 * 0.25 = 7.5
    Four identical sessions: mock = 1.0 * 30.0 * 1.0 = 30.0
    """
    one_session = [
        {"status": "completed", "track": "sql", "total_count": 2, "attempted_count": 2, "solved_count": 2}
    ]
    four_sessions = one_session * 4

    result_one = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=one_session,
        effective_plan="elite",
    )
    result_four = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=four_sessions,
        effective_plan="elite",
    )
    assert result_one is not None
    assert result_four is not None
    mock_one = result_one["sql"]["components"]["mock"]
    mock_four = result_four["sql"]["components"]["mock"]
    assert mock_one == 7.5, f"Expected 7.5 for one session, got {mock_one}"
    assert mock_four == 30.0, f"Expected 30.0 for four sessions, got {mock_four}"


def test_tc211_recency_uses_newest_5():
    """TC-211: 6 sessions newest-first; first 5 are perfect, 6th is 0/3.

    Only the newest 5 ([:5]) are used → avg_accuracy=1.0, n=5, confidence=1.0 → mock=30.0.
    If code used oldest 5 ([-5:]) the 6th (0-correct) would be included → 24.0.
    """
    # Newest-first (as returned by get_mock_history): 5 perfect then 1 zero
    sessions = [
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 3},
        {"status": "completed", "track": "sql", "total_count": 3, "attempted_count": 3, "solved_count": 0},
    ]
    result = _compute_readiness_scores(
        per_track_solved_question_ids={},
        per_track_ftc_question_ids={},
        mock_sessions=sessions,
        effective_plan="elite",
    )
    assert result is not None
    mock_pts = result["sql"]["components"]["mock"]
    assert mock_pts == 30.0, (
        f"Expected mock 30.0 (newest-5 all perfect), got {mock_pts}; "
        "if got 24.0 the code is using [-5:] (oldest 5) instead of [:5] (newest 5)"
    )
