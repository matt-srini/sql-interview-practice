"""
Pure plan → access policy.

Free: easy only (all easy questions unlocked, all medium and hard locked).
Pro/Elite: all difficulties unlocked.
No thresholds, no batch unlocks, no caps.

Mock access rules (unchanged) live in compute_mock_access().
"""
from __future__ import annotations

from typing import Any


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sorted_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        difficulty: sorted(catalog.get(difficulty, []), key=lambda q: int(q.get("order", 0)))
        for difficulty in ("easy", "medium", "hard")
    }


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
        track: track slug — one of the 9 track slugs (e.g. 'sql', 'python',
               'statistics', 'ml-fundamentals'). Unused in the flat model but
               kept for call-site compatibility.
    """
    plan = normalize_plan(plan)
    ordered_catalog = _sorted_catalog(catalog)
    solved_set = {int(qid) for qid in solved_ids}

    easy_questions = ordered_catalog["easy"]
    medium_questions = ordered_catalog["medium"]
    hard_questions = ordered_catalog["hard"]

    if plan == "elite":
        limits = {
            "easy":   len(easy_questions),
            "medium": len(medium_questions),
            "hard":   len(hard_questions),
        }
    elif plan == "pro":
        # Pro gets everything — no cap
        limits = {
            "easy":   len(easy_questions),
            "medium": len(medium_questions),
            "hard":   len(hard_questions),
        }
    else:
        # Free: easy only
        limits = {
            "easy":   len(easy_questions),
            "medium": 0,
            "hard":   0,
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
