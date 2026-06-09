from __future__ import annotations

from typing import Any

from tracks import TRACKS, get_track


# ── Lifetime plan normalisation ───────────────────────────────────────────────
#
# Lifetime plans ('lifetime_pro', 'lifetime_elite') grant the same access as
# their base plan but are stored separately so they are never downgraded by a
# subscription-deleted webhook (one-time purchases have no subscription).
# All access-control functions call normalize_plan() first so the rest of the
# logic only needs to handle 'free', 'pro', and 'elite'.

_LIFETIME_PLAN_MAP: dict[str, str] = {
    "lifetime_pro":   "pro",
    "lifetime_elite": "elite",
}


def normalize_plan(plan: str) -> str:
    """Map lifetime plan variants to their base plan for access-control checks."""
    return _LIFETIME_PLAN_MAP.get(plan, plan)


# ── Free-tier threshold tables ────────────────────────────────────────────────
#
# Each entry is (solved_threshold, questions_unlocked | None).
# None means "unlock all". Tables are evaluated top-to-bottom; first match wins.
#
# Route A (raw solves) and Route B (path completion) are two doors to the same
# room: the *higher* limit wins, so a partially-threshold-unlocked user who also
# completes a learning path immediately gets all medium.

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

FREE_HARD_CAP_CODE = 8

# MCQ tracks (PySpark, Data Engineering) — thresholds balanced with option-hiding:
# locked questions show the stem only, so the gap between locked-read and answered
# is smaller than for code tracks (no running, no debugging).
_FREE_MEDIUM_THRESHOLDS_MCQ: list[tuple[int, int | None]] = [
    (25, None),   # 25 easy solved → all medium
    (17, 8),      # 17 easy solved → 8 medium
    (10, 3),      # 10 easy solved → 3 medium
]

_FREE_HARD_THRESHOLDS_MCQ: list[tuple[int, int]] = [
    (12, 5),      # 12 medium solved → 5 hard (= full cap)
]

FREE_HARD_CAP_MCQ = 5


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_mcq_profile(track: str) -> bool:
    """True when this track uses the MCQ unlock thresholds."""
    try:
        return get_track(track).unlock_profile == "mcq"
    except ValueError:
        return False


def _sorted_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        difficulty: sorted(catalog.get(difficulty, []), key=lambda q: int(q.get("order", 0)))
        for difficulty in ("easy", "medium", "hard")
    }


def _free_medium_limit(
    total_medium: int,
    easy_solved: int,
    mcq_profile: bool,
) -> int:
    """Number of medium questions a Free user can access in this track."""
    thresholds = _FREE_MEDIUM_THRESHOLDS_MCQ if mcq_profile else _FREE_MEDIUM_THRESHOLDS_CODE
    for solved_threshold, limit in thresholds:
        if easy_solved >= solved_threshold:
            return total_medium if limit is None else min(limit, total_medium)
    return 0


def _free_hard_limit(
    total_hard: int,
    medium_solved: int,
    mcq_profile: bool,
) -> int:
    """Number of hard questions a Free user can access in this track."""
    cap = FREE_HARD_CAP_MCQ if mcq_profile else FREE_HARD_CAP_CODE

    thresholds = _FREE_HARD_THRESHOLDS_MCQ if mcq_profile else _FREE_HARD_THRESHOLDS_CODE
    for solved_threshold, limit in thresholds:
        if medium_solved >= solved_threshold:
            return min(limit, cap, total_hard)  # cap is always enforced regardless of threshold
    return 0


# ── Core unlock logic ─────────────────────────────────────────────────────────

def compute_unlock_state(
    plan: str,
    solved_ids: set[int],
    catalog: dict[str, list[dict[str, Any]]],
    track: str = "sql",
) -> dict[int, str]:
    """
    Return a mapping of question_id → "unlocked" | "locked" | "solved".

    Args:
        plan: 'free' | 'pro' | 'elite'
        solved_ids: set of question IDs the user has solved in this track
        catalog: {'easy': [...], 'medium': [...], 'hard': [...]}
        track: track slug — 'sql' | 'python' | 'python-data' | 'pyspark'.
               Affects Free-tier thresholds (PySpark uses higher thresholds).
    """
    plan = normalize_plan(plan)
    ordered_catalog = _sorted_catalog(catalog)
    solved_set = {int(qid) for qid in solved_ids}
    mcq_profile = _is_mcq_profile(track)

    easy_questions = ordered_catalog["easy"]
    medium_questions = ordered_catalog["medium"]
    hard_questions = ordered_catalog["hard"]

    easy_solved = sum(1 for q in easy_questions if int(q["id"]) in solved_set)
    medium_solved = sum(1 for q in medium_questions if int(q["id"]) in solved_set)

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
            "medium": _free_medium_limit(len(medium_questions), easy_solved, mcq_profile),
            "hard":   _free_hard_limit(len(hard_questions), medium_solved, mcq_profile),
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


def get_unlock_hint(
    plan: str,
    solved_ids: set[int],
    catalog: dict[str, list[dict[str, Any]]],
    track: str = "sql",
) -> str | None:
    """
    Return a short, personalised next-step unlock message for Free users.
    Returns None for Pro/Elite (no gates to explain).
    """
    plan = normalize_plan(plan)
    if plan in ("pro", "elite"):
        return None

    ordered = _sorted_catalog(catalog)
    solved_set = {int(qid) for qid in solved_ids}
    mcq = _is_mcq_profile(track)

    easy_qs = ordered["easy"]
    medium_qs = ordered["medium"]
    hard_qs = ordered["hard"]

    easy_solved = sum(1 for q in easy_qs if int(q["id"]) in solved_set)
    medium_solved = sum(1 for q in medium_qs if int(q["id"]) in solved_set)

    medium_thresholds = _FREE_MEDIUM_THRESHOLDS_MCQ if mcq else _FREE_MEDIUM_THRESHOLDS_CODE
    hard_thresholds = _FREE_HARD_THRESHOLDS_MCQ if mcq else _FREE_HARD_THRESHOLDS_CODE
    total_medium = len(medium_qs)
    total_hard = len(hard_qs)

    current_medium_limit = _free_medium_limit(total_medium, easy_solved, mcq)
    current_hard_limit = _free_hard_limit(total_hard, medium_solved, mcq)

    # Find the next medium threshold not yet reached
    medium_hint: str | None = None
    if current_medium_limit < total_medium:
        for threshold, unlocks in reversed(medium_thresholds):
            if easy_solved < threshold:
                needed = threshold - easy_solved
                if unlocks is None:
                    medium_hint = f"Solve {needed} more easy question{'s' if needed != 1 else ''} to unlock all medium."
                else:
                    next_limit = min(unlocks, total_medium)
                    medium_hint = f"Solve {needed} more easy question{'s' if needed != 1 else ''} to unlock {next_limit} medium."
                break

    # Find the next hard threshold not yet reached
    hard_hint: str | None = None
    if current_medium_limit == total_medium and current_hard_limit == 0 and len(hard_qs) > 0:
        # All medium unlocked, no hard yet
        first_threshold = hard_thresholds[-1][0]  # lowest threshold
        if medium_solved < first_threshold:
            needed = first_threshold - medium_solved
            hard_hint = f"Solve {needed} more medium question{'s' if needed != 1 else ''} to unlock your first hard questions."
    elif current_hard_limit > 0:
        cap = FREE_HARD_CAP_MCQ if mcq else FREE_HARD_CAP_CODE
        if current_hard_limit < cap:
            for threshold, _ in reversed(hard_thresholds):
                if medium_solved < threshold:
                    needed = threshold - medium_solved
                    hard_hint = f"Solve {needed} more medium question{'s' if needed != 1 else ''} to unlock more hard questions."
                    break

    # Prefer medium hint if medium is still gated; fall back to hard hint
    if medium_hint:
        return medium_hint
    if hard_hint:
        return hard_hint

    # Everything is as unlocked as Free allows
    cap = FREE_HARD_CAP_MCQ if mcq else FREE_HARD_CAP_CODE
    if current_hard_limit > 0 and total_hard > cap:
        return f"Free plan includes up to {cap} hard questions. Upgrade for the full set."
    return None


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

_PLAN_LOCKED: dict[str, Any] = {
    "can_start": False,
    "block_reason": "plan_locked",
    "block_copy": None,
    "needs_upgrade": None,
    "daily_limit": None,
    "daily_used": None,
    "weekly_benchmark_limit": None,
    "weekly_benchmark_used": None,
}


def _plan_locked(copy: str, upgrade: str) -> dict[str, Any]:
    return {**_PLAN_LOCKED, "block_copy": copy, "needs_upgrade": upgrade}


def compute_mock_access(
    plan: str,
    track: str,
    difficulty: str,
    mode: str,
    daily_benchmark_used: int = 0,
    daily_custom_used: int = 0,
    weekly_benchmark_used: int = 0,
) -> dict[str, Any]:
    """
    Return whether a user can start a mock session with these parameters.

    Mode-based access rules (post-Phase-3):
      benchmark + free + easy    → 1 per rolling 7 days (weekly cap)
      benchmark + free + med/hard → plan_locked
      benchmark + pro             → 3/day
      benchmark + elite           → unlimited (soft abuse cap only, not checked here)
      custom + free               → plan_locked
      custom + pro                → 3/day
      custom + elite              → unlimited
      interview_loop + free/pro   → plan_locked
      interview_loop + elite      → unlimited

    Returns a dict with:
      can_start (bool)
      block_reason (str | None): 'plan_locked' | 'daily_cap' | 'weekly_cap'
      block_copy (str | None): human-readable message for the UI
      needs_upgrade (str | None): 'pro' | 'elite'
      daily_limit (int | None)
      daily_used (int | None)
      weekly_benchmark_limit (int | None): only for Free + benchmark
      weekly_benchmark_used (int | None): only for Free + benchmark
    """
    plan = normalize_plan(plan)

    # ── interview_loop ────────────────────────────────────────────────────────
    if mode == "interview_loop":
        if plan != "elite":
            return _plan_locked("Interview Loop is an Elite-only feature.", "elite")
        return {
            "can_start": True,
            "block_reason": None,
            "block_copy": None,
            "needs_upgrade": None,
            "daily_limit": None,
            "daily_used": None,
            "weekly_benchmark_limit": None,
            "weekly_benchmark_used": None,
        }

    # ── custom ────────────────────────────────────────────────────────────────
    if mode == "custom":
        if plan == "free":
            return _plan_locked(
                "Custom drills require a Pro or Elite plan. Upgrade to practise on your own schedule.",
                "pro",
            )
        if plan == "pro":
            daily_limit = 3
            if daily_custom_used >= daily_limit:
                return {
                    "can_start": False,
                    "block_reason": "daily_cap",
                    "block_copy": f"Daily limit reached ({daily_limit} custom drills per day). Upgrade to Elite for unlimited.",
                    "needs_upgrade": "elite",
                    "daily_limit": daily_limit,
                    "daily_used": daily_custom_used,
                    "weekly_benchmark_limit": None,
                    "weekly_benchmark_used": None,
                }
            return {
                "can_start": True,
                "block_reason": None,
                "block_copy": None,
                "needs_upgrade": None,
                "daily_limit": daily_limit,
                "daily_used": daily_custom_used,
                "weekly_benchmark_limit": None,
                "weekly_benchmark_used": None,
            }
        # elite
        return {
            "can_start": True,
            "block_reason": None,
            "block_copy": None,
            "needs_upgrade": None,
            "daily_limit": None,
            "daily_used": None,
            "weekly_benchmark_limit": None,
            "weekly_benchmark_used": None,
        }

    # ── benchmark ─────────────────────────────────────────────────────────────
    # (default branch; unknown modes fall through as benchmark-equivalent)
    if plan == "free":
        # Free: easy only, 1 per rolling 7 days.
        # Guard on != "easy" (not a ("medium","hard") blocklist) so the
        # "mixed" difficulty — which draws medium/hard questions — is also
        # plan-locked, and any future difficulty value defaults to locked.
        if difficulty != "easy":
            return _plan_locked(
                "Medium, hard, and mixed benchmarks require a Pro plan.",
                "pro",
            )
        # easy: weekly cap
        weekly_limit = 1
        if weekly_benchmark_used >= weekly_limit:
            return {
                "can_start": False,
                "block_reason": "weekly_cap",
                "block_copy": "You've used your free benchmark this week. Upgrade to Pro for 3 benchmarks/day, or wait until next week.",
                "needs_upgrade": "pro",
                "daily_limit": None,
                "daily_used": None,
                "weekly_benchmark_limit": weekly_limit,
                "weekly_benchmark_used": weekly_benchmark_used,
            }
        return {
            "can_start": True,
            "block_reason": None,
            "block_copy": None,
            "needs_upgrade": None,
            "daily_limit": None,
            "daily_used": None,
            "weekly_benchmark_limit": weekly_limit,
            "weekly_benchmark_used": weekly_benchmark_used,
        }

    if plan == "pro":
        daily_limit = 3
        if daily_benchmark_used >= daily_limit:
            return {
                "can_start": False,
                "block_reason": "daily_cap",
                "block_copy": f"Daily limit reached ({daily_limit} benchmarks per day). Upgrade to Elite for unlimited.",
                "needs_upgrade": "elite",
                "daily_limit": daily_limit,
                "daily_used": daily_benchmark_used,
                "weekly_benchmark_limit": None,
                "weekly_benchmark_used": None,
            }
        return {
            "can_start": True,
            "block_reason": None,
            "block_copy": None,
            "needs_upgrade": None,
            "daily_limit": daily_limit,
            "daily_used": daily_benchmark_used,
            "weekly_benchmark_limit": None,
            "weekly_benchmark_used": None,
        }

    # elite
    return {
        "can_start": True,
        "block_reason": None,
        "block_copy": None,
        "needs_upgrade": None,
        "daily_limit": None,
        "daily_used": None,
        "weekly_benchmark_limit": None,
        "weekly_benchmark_used": None,
    }
