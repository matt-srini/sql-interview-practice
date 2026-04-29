"""Tests for the unlock model — thresholds, path routes, PySpark, and mock access."""
from unlock import (
    FREE_HARD_CAP_CODE,
    FREE_HARD_CAP_PYSPARK,
    compute_mock_access,
    compute_unlock_state,
    get_next_questions,
    normalize_plan,
)
from questions import get_questions_by_difficulty


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ids(difficulty: str, count: int) -> set[int]:
    questions = get_questions_by_difficulty()[difficulty]
    return {int(question["id"]) for question in questions[:count]}


def _make_mock_catalog(easy: int = 30, medium: int = 25, hard: int = 20) -> dict:
    """Build a minimal catalog dict with sequential IDs for threshold testing."""
    return {
        "easy":   [{"id": i, "order": i} for i in range(1, easy + 1)],
        "medium": [{"id": i, "order": i} for i in range(easy + 1, easy + medium + 1)],
        "hard":   [{"id": i, "order": i} for i in range(easy + medium + 1, easy + medium + hard + 1)],
    }


# ── Free plan — code track thresholds (SQL/Python/Pandas) ────────────────────

def test_free_unlocks_only_easy_at_start() -> None:
    catalog = _make_mock_catalog()
    state = compute_unlock_state("free", set(), catalog, track="sql")
    assert all(state[q["id"]] == "unlocked" for q in catalog["easy"])
    assert all(state[q["id"]] == "locked"   for q in catalog["medium"])
    assert all(state[q["id"]] == "locked"   for q in catalog["hard"])


def test_free_unlocks_3_medium_after_8_easy() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:8]}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert [state[q["id"]] for q in catalog["medium"][:3]] == ["unlocked"] * 3
    assert state[catalog["medium"][3]["id"]] == "locked"


def test_free_unlocks_8_medium_after_15_easy() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:15]}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert [state[q["id"]] for q in catalog["medium"][:8]] == ["unlocked"] * 8
    assert state[catalog["medium"][8]["id"]] == "locked"


def test_free_unlocks_all_medium_after_25_easy() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:25]}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert all(state[q["id"]] == "unlocked" for q in catalog["medium"])


def test_free_unlocks_3_hard_after_8_medium() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:25]} | {q["id"] for q in catalog["medium"][:8]}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert [state[q["id"]] for q in catalog["hard"][:3]] == ["unlocked"] * 3
    assert state[catalog["hard"][3]["id"]] == "locked"


def test_free_caps_hard_at_cap_code_track() -> None:
    catalog = _make_mock_catalog(easy=30, medium=25, hard=20)
    solved = {q["id"] for q in catalog["easy"][:25]} | {q["id"] for q in catalog["medium"][:22]}
    state = compute_unlock_state("free", solved, catalog, track="sql")
    assert [state[q["id"]] for q in catalog["hard"][:FREE_HARD_CAP_CODE]] == ["unlocked"] * FREE_HARD_CAP_CODE
    assert state[catalog["hard"][FREE_HARD_CAP_CODE]["id"]] == "locked"


# ── Free plan — PySpark higher thresholds ─────────────────────────────────────

def test_free_pyspark_no_medium_at_11_easy() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:11]}
    state = compute_unlock_state("free", solved, catalog, track="pyspark")
    assert all(state[q["id"]] == "locked" for q in catalog["medium"])


def test_free_pyspark_unlocks_3_medium_at_12_easy() -> None:
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:12]}
    state = compute_unlock_state("free", solved, catalog, track="pyspark")
    assert [state[q["id"]] for q in catalog["medium"][:3]] == ["unlocked"] * 3
    assert state[catalog["medium"][3]["id"]] == "locked"


def test_free_pyspark_caps_hard_at_cap() -> None:
    catalog = _make_mock_catalog(easy=30, medium=25, hard=15)
    solved = {q["id"] for q in catalog["easy"][:30]} | {q["id"] for q in catalog["medium"][:22]}
    state = compute_unlock_state("free", solved, catalog, track="pyspark")
    assert [state[q["id"]] for q in catalog["hard"][:FREE_HARD_CAP_PYSPARK]] == ["unlocked"] * FREE_HARD_CAP_PYSPARK
    assert state[catalog["hard"][FREE_HARD_CAP_PYSPARK]["id"]] == "locked"


# ── Path-based unlock routes ──────────────────────────────────────────────────

def test_starter_path_done_unlocks_all_medium() -> None:
    catalog = _make_mock_catalog()
    # No easy solved — but learning path completed
    state = compute_unlock_state(
        "free", set(), catalog, track="sql",
        path_state={"starter_done": True, "intermediate_done": False},
    )
    assert all(state[q["id"]] == "unlocked" for q in catalog["medium"])
    assert all(state[q["id"]] == "locked"   for q in catalog["hard"])


def test_intermediate_path_done_unlocks_full_hard_cap() -> None:
    catalog = _make_mock_catalog(easy=30, medium=25, hard=20)
    # Starter also done so medium is open; intermediate unlocks hard cap
    state = compute_unlock_state(
        "free", set(), catalog, track="sql",
        path_state={"starter_done": True, "intermediate_done": True},
    )
    unlocked_hard = [q for q in catalog["hard"] if state[q["id"]] == "unlocked"]
    assert len(unlocked_hard) == FREE_HARD_CAP_CODE


def test_path_and_threshold_take_higher_limit() -> None:
    """User solved 15 easy (→ 8 medium by threshold) and also completed a learning path (→ all medium).
    The higher limit (all medium) should win."""
    catalog = _make_mock_catalog()
    solved = {q["id"] for q in catalog["easy"][:15]}
    state = compute_unlock_state(
        "free", solved, catalog, track="sql",
        path_state={"starter_done": True, "intermediate_done": False},
    )
    assert all(state[q["id"]] == "unlocked" for q in catalog["medium"])


# ── Pro plan — no hard cap ────────────────────────────────────────────────────

def test_pro_unlocks_all_including_hard() -> None:
    catalog = _make_mock_catalog(easy=30, medium=25, hard=20)
    state = compute_unlock_state("pro", set(), catalog, track="sql")
    for diff in ("easy", "medium", "hard"):
        assert all(state[q["id"]] == "unlocked" for q in catalog[diff])


# ── Elite plan ────────────────────────────────────────────────────────────────

def test_elite_unlocks_everything() -> None:
    catalog = get_questions_by_difficulty()
    state = compute_unlock_state("elite", set(), catalog, track="sql")
    for diff in ("easy", "medium", "hard"):
        assert all(state[int(q["id"])] == "unlocked" for q in catalog[diff])


# ── Solved questions persist through downgrades ───────────────────────────────

def test_solved_questions_always_show_as_solved() -> None:
    catalog = _make_mock_catalog(easy=30, medium=25, hard=20)
    hard_q_id = catalog["hard"][18]["id"]
    state = compute_unlock_state("free", {hard_q_id}, catalog, track="sql")
    assert state[hard_q_id] == "solved"


# ── get_next_questions ────────────────────────────────────────────────────────

def test_get_next_questions_returns_first_unlocked() -> None:
    catalog = _make_mock_catalog()
    state = compute_unlock_state("free", set(), catalog, track="sql")
    next_qs = get_next_questions(state, catalog)
    assert next_qs["easy"] == catalog["easy"][0]["id"]
    assert next_qs["medium"] is None
    assert next_qs["hard"] is None


# ── compute_mock_access ───────────────────────────────────────────────────────

def test_mock_access_free_easy_always_allowed() -> None:
    result = compute_mock_access("free", "sql", "easy", medium_unlocked=False)
    assert result["can_start"] is True


def test_mock_access_free_hard_blocked() -> None:
    result = compute_mock_access("free", "sql", "hard", medium_unlocked=True)
    assert result["can_start"] is False
    assert result["block_reason"] == "plan_locked"
    assert result["needs_upgrade"] == "pro"


def test_mock_access_free_medium_blocked_if_not_unlocked() -> None:
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=False)
    assert result["can_start"] is False
    assert result["block_reason"] == "not_unlocked"


def test_mock_access_free_medium_allowed_if_unlocked() -> None:
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=0)
    assert result["can_start"] is True
    assert result["daily_limit"] == 1


def test_mock_access_free_medium_daily_cap() -> None:
    result = compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=1)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"
    assert result["needs_upgrade"] == "pro"


def test_mock_access_pro_hard_within_daily_limit() -> None:
    result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=2)
    assert result["can_start"] is True
    assert result["daily_limit"] == 3
    assert result["daily_used"] == 2


def test_mock_access_pro_hard_daily_cap() -> None:
    result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=3)
    assert result["can_start"] is False
    assert result["block_reason"] == "daily_cap"
    assert result["needs_upgrade"] == "elite"


def test_mock_access_elite_hard_unlimited() -> None:
    result = compute_mock_access("elite", "sql", "hard", medium_unlocked=True, daily_hard_used=99)
    assert result["can_start"] is True
    assert result["daily_limit"] is None


def test_mock_access_company_filter_requires_elite() -> None:
    result = compute_mock_access("pro", "sql", "hard", medium_unlocked=True, company_filter=True)
    assert result["can_start"] is False
    assert result["needs_upgrade"] == "elite"


# ── normalize_plan ────────────────────────────────────────────────────────────

def test_normalize_plan_returns_pro_for_lifetime_pro() -> None:
    assert normalize_plan("lifetime_pro") == "pro"


def test_normalize_plan_returns_elite_for_lifetime_elite() -> None:
    assert normalize_plan("lifetime_elite") == "elite"


def test_normalize_plan_passes_through_base_plans() -> None:
    for plan in ("free", "pro", "elite"):
        assert normalize_plan(plan) == plan, f"normalize_plan({plan!r}) should be a no-op"


def test_normalize_plan_passes_through_unknown_values() -> None:
    # Unknown plan names must not blow up — they pass through unchanged.
    assert normalize_plan("enterprise") == "enterprise"


# ── lifetime plan — unlock state (identical access to base plan) ──────────────

def test_lifetime_pro_unlock_state_matches_pro() -> None:
    """lifetime_pro must grant the same catalog access as pro — all medium + hard."""
    catalog = _make_mock_catalog()
    solved: set[int] = set()

    pro_state      = compute_unlock_state("pro",          solved, catalog)
    lifetime_state = compute_unlock_state("lifetime_pro", solved, catalog)

    assert pro_state == lifetime_state, (
        "lifetime_pro must grant exactly the same unlock state as pro"
    )


def test_lifetime_elite_unlock_state_matches_elite() -> None:
    """lifetime_elite must grant full catalog access identical to elite."""
    catalog = _make_mock_catalog()
    solved: set[int] = set()

    elite_state    = compute_unlock_state("elite",          solved, catalog)
    lifetime_state = compute_unlock_state("lifetime_elite", solved, catalog)

    assert elite_state == lifetime_state, (
        "lifetime_elite must grant exactly the same unlock state as elite"
    )


# ── lifetime plan — mock access (CRITICAL: must not be blocked or downgraded) ─

def test_lifetime_pro_mock_hard_within_daily_limit() -> None:
    """lifetime_pro users get the same hard-mock daily budget as pro (3/day)."""
    result = compute_mock_access("lifetime_pro", "sql", "hard", medium_unlocked=True, daily_hard_used=2)
    assert result["can_start"] is True
    assert result["daily_limit"] == 3


def test_lifetime_pro_mock_hard_daily_cap() -> None:
    """lifetime_pro daily hard cap is 3, same as pro."""
    result = compute_mock_access("lifetime_pro", "sql", "hard", medium_unlocked=True, daily_hard_used=3)
    assert result["can_start"] is False
    assert result["needs_upgrade"] == "elite"


def test_lifetime_elite_mock_hard_unlimited() -> None:
    """lifetime_elite users have no daily cap on hard mocks, same as elite."""
    result = compute_mock_access("lifetime_elite", "sql", "hard", medium_unlocked=True, daily_hard_used=99)
    assert result["can_start"] is True
    assert result["daily_limit"] is None


def test_lifetime_elite_mock_company_filter_allowed() -> None:
    """Company-filtered mocks require elite (or lifetime_elite) — must not be blocked."""
    result = compute_mock_access(
        "lifetime_elite", "sql", "hard",
        medium_unlocked=True, company_filter=True,
    )
    assert result["can_start"] is True, (
        "lifetime_elite must be allowed to use company-filtered mock interviews"
    )


def test_lifetime_pro_mock_company_filter_blocked() -> None:
    """Company-filtered mocks must still be blocked for lifetime_pro (not elite tier)."""
    result = compute_mock_access(
        "lifetime_pro", "sql", "hard",
        medium_unlocked=True, company_filter=True,
    )
    assert result["can_start"] is False
    assert result["needs_upgrade"] == "elite"
