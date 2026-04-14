from __future__ import annotations

from typing import Any


# ── Free-tier threshold tables ────────────────────────────────────────────────
#
# Each entry is (solved_threshold, questions_unlocked | None).
# None means "unlock all". Tables are evaluated top-to-bottom; first match wins.
#
# Route A (raw solves) and Route B (path completion) are two doors to the same
# room: the *higher* limit wins, so a partially-threshold-unlocked user who also
# completes the starter path immediately gets all medium.

# Code tracks: SQL, Python, Pandas
_FREE_MEDIUM_THRESHOLDS_CODE: list[tuple[int, int | None]] = [
    (25, None),   # 25 easy solved → all medium
    (15, 8),      # 15 easy solved → 8 medium
    (8, 3),       # 8 easy solved → 3 medium
]

_FREE_HARD_THRESHOLDS_CODE: list[tuple[int, int]] = [
    (22, 15),     # 22 medium solved → 15 hard (= full cap)
    (15, 8),      # 15 medium solved → 8 hard
    (8, 3),       # 8 medium solved → 3 hard
]

FREE_HARD_CAP_CODE = 15

# PySpark (MCQ-only) — higher thresholds because MCQ recognition is lower-effort
_FREE_MEDIUM_THRESHOLDS_PYSPARK: list[tuple[int, int | None]] = [
    (30, None),   # 30 easy solved → all medium
    (20, 8),      # 20 easy solved → 8 medium
    (12, 3),      # 12 easy solved → 3 medium
]

_FREE_HARD_THRESHOLDS_PYSPARK: list[tuple[int, int]] = [
    (22, 10),     # 22 medium solved → 10 hard (= full cap)
    (15, 5),      # 15 medium solved → 5 hard
]

FREE_HARD_CAP_PYSPARK = 10

# Daily mock session limits per plan × difficulty (None = unlimited)
MOCK_DAILY_LIMITS: dict[str, dict[str, int | None]] = {
    "free":  {"easy": None, "medium": 1,    "hard": None, "mixed": None},
    "pro":   {"easy": None, "medium": None, "hard": 3,    "mixed": None},
    "elite": {"easy": None, "medium": None, "hard": None, "mixed": None},
}

# Company-filtered mocks require Elite
MOCK_COMPANY_FILTER_TIERS = {"elite"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_pyspark(track: str) -> bool:
    return track == "pyspark"


def _sorted_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        difficulty: sorted(catalog.get(difficulty, []), key=lambda q: int(q.get("order", 0)))
        for difficulty in ("easy", "medium", "hard")
    }


def _free_medium_limit(
    total_medium: int,
    easy_solved: int,
    pyspark: bool,
    starter_done: bool,
) -> int:
    """Number of medium questions a Free user can access in this track."""
    if starter_done:
        return total_medium  # path completion = full medium access

    thresholds = _FREE_MEDIUM_THRESHOLDS_PYSPARK if pyspark else _FREE_MEDIUM_THRESHOLDS_CODE
    for solved_threshold, limit in thresholds:
        if easy_solved >= solved_threshold:
            return total_medium if limit is None else min(limit, total_medium)
    return 0


def _free_hard_limit(
    total_hard: int,
    medium_solved: int,
    pyspark: bool,
    intermediate_done: bool,
) -> int:
    """Number of hard questions a Free user can access in this track."""
    cap = FREE_HARD_CAP_PYSPARK if pyspark else FREE_HARD_CAP_CODE

    if intermediate_done:
        return min(cap, total_hard)  # path completion = full hard cap

    thresholds = _FREE_HARD_THRESHOLDS_PYSPARK if pyspark else _FREE_HARD_THRESHOLDS_CODE
    for solved_threshold, limit in thresholds:
        if medium_solved >= solved_threshold:
            return min(limit, total_hard)
    return 0


# ── Core unlock logic ─────────────────────────────────────────────────────────

def compute_unlock_state(
    plan: str,
    solved_ids: set[int],
    catalog: dict[str, list[dict[str, Any]]],
    track: str = "sql",
    path_state: dict[str, bool] | None = None,
) -> dict[int, str]:
    """
    Return a mapping of question_id → "unlocked" | "locked" | "solved".

    Args:
        plan: 'free' | 'pro' | 'elite'
        solved_ids: set of question IDs the user has solved in this track
        catalog: {'easy': [...], 'medium': [...], 'hard': [...]}
        track: track slug — 'sql' | 'python' | 'python-data' | 'pyspark'.
               Affects Free-tier thresholds (PySpark uses higher thresholds).
        path_state: optional dict {'starter_done': bool, 'intermediate_done': bool}.
               starter_done=True → all medium unlocked (same ceiling as max threshold).
               intermediate_done=True → full hard cap unlocked.
               Either acts as an express-lane alternative to threshold grinding.
    """
    ordered_catalog = _sorted_catalog(catalog)
    solved_set = {int(qid) for qid in solved_ids}
    pyspark = _is_pyspark(track)

    easy_questions = ordered_catalog["easy"]
    medium_questions = ordered_catalog["medium"]
    hard_questions = ordered_catalog["hard"]

    easy_solved = sum(1 for q in easy_questions if int(q["id"]) in solved_set)
    medium_solved = sum(1 for q in medium_questions if int(q["id"]) in solved_set)

    ps = path_state or {}
    starter_done = bool(ps.get("starter_done", False))
    intermediate_done = bool(ps.get("intermediate_done", False))

    if plan == "elite":
        limits = {
            "easy":   len(easy_questions),
            "medium": len(medium_questions),
            "hard":   len(hard_questions),
        }
    elif plan == "pro":
        # Pro gets everything — no hard cap
        limits = {
            "easy":   len(easy_questions),
            "medium": len(medium_questions),
            "hard":   len(hard_questions),
        }
    else:
        limits = {
            "easy":   len(easy_questions),
            "medium": _free_medium_limit(len(medium_questions), easy_solved, pyspark, starter_done),
            "hard":   _free_hard_limit(len(hard_questions), medium_solved, pyspark, intermediate_done),
        }

    unlock_state: dict[int, str] = {}
    for difficulty, questions in ordered_catalog.items():
        unlocked_prefix = limits[difficulty]
        for index, question in enumerate(questions):
            qid = int(question["id"])
            unlock_state[qid] = "unlocked" if index < unlocked_prefix else "locked"

    # Solved questions override their computed state (persists through downgrades)
    for qid in solved_set:
        unlock_state[qid] = "solved"

    return unlock_state


def get_next_questions(
    unlock_state: dict[int, str],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int | None]:
    ordered_catalog = _sorted_catalog(catalog)
    next_questions: dict[str, int | None] = {}

    for difficulty, questions in ordered_catalog.items():
        next_question_id = next(
            (
                int(q["id"])
                for q in questions
                if unlock_state.get(int(q["id"])) == "unlocked"
            ),
            None,
        )
        next_questions[difficulty] = next_question_id

    return next_questions


# ── Mock access check ─────────────────────────────────────────────────────────

def compute_mock_access(
    plan: str,
    track: str,
    difficulty: str,
    medium_unlocked: bool,
    daily_medium_used: int = 0,
    daily_hard_used: int = 0,
    company_filter: bool = False,
) -> dict[str, Any]:
    """
    Return whether a user can start a mock session with these parameters.

    Returns a dict with:
      can_start (bool)
      block_reason (str | None): 'plan_locked' | 'not_unlocked' | 'daily_cap'
      block_copy (str | None): human-readable message for the UI
      needs_upgrade (str | None): 'pro' | 'elite' — upgrade that would fix it
      daily_limit (int | None)
      daily_used (int | None)
    """
    _track_label = {
        "sql": "SQL", "python": "Python",
        "python-data": "Pandas", "pyspark": "PySpark",
    }.get(track, track.upper())

    # Company-filtered mocks: Elite only
    if company_filter and plan not in MOCK_COMPANY_FILTER_TIERS:
        return {
            "can_start": False,
            "block_reason": "plan_locked",
            "block_copy": "Company-filtered mocks are an Elite feature.",
            "needs_upgrade": "elite",
            "daily_limit": None,
            "daily_used": None,
        }

    # Hard mocks: Free users are plan-locked
    if difficulty == "hard" and plan == "free":
        return {
            "can_start": False,
            "block_reason": "plan_locked",
            "block_copy": "Hard mock interviews are a Pro feature.",
            "needs_upgrade": "pro",
            "daily_limit": None,
            "daily_used": None,
        }

    # Medium mocks: Free users must have medium unlocked in this track first
    if difficulty == "medium" and plan == "free" and not medium_unlocked:
        return {
            "can_start": False,
            "block_reason": "not_unlocked",
            "block_copy": f"Unlock {_track_label} medium questions first — solve 8 easy or complete the starter path.",
            "needs_upgrade": "pro",
            "daily_limit": None,
            "daily_used": None,
        }

    # Check daily limits
    daily_limit = MOCK_DAILY_LIMITS.get(plan, {}).get(difficulty)
    daily_used = (
        daily_medium_used if difficulty == "medium"
        else daily_hard_used if difficulty == "hard"
        else 0
    )

    if daily_limit is not None and daily_used >= daily_limit:
        next_upgrade = "elite" if plan == "pro" else "pro"
        label = f"{daily_limit} {difficulty} mock{'s' if daily_limit != 1 else ''} per day"
        return {
            "can_start": False,
            "block_reason": "daily_cap",
            "block_copy": f"Daily limit reached ({label}).",
            "needs_upgrade": next_upgrade,
            "daily_limit": daily_limit,
            "daily_used": daily_used,
        }

    return {
        "can_start": True,
        "block_reason": None,
        "block_copy": None,
        "needs_upgrade": None,
        "daily_limit": daily_limit,
        "daily_used": daily_used if daily_limit is not None else None,
    }
