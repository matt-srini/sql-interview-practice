"""
Mock interview router.

Endpoints:
  GET  /api/mock/history
  POST /api/mock/start
  GET  /api/mock/{session_id}
  POST /api/mock/{session_id}/submit
  POST /api/mock/{session_id}/finish

NOTE: /history must be registered before /{session_id} to avoid FastAPI
interpreting the string "history" as an integer session ID.
"""
from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from concept_families import CONCEPT_FAMILIES, concept_matches_focus
from mcq import is_mcq_correct

from db import (
    create_mock_session,
    discard_mock_session,
    finish_mock_session,
    get_active_mock_session,
    get_consumed_chain_parent_ids,
    get_daily_benchmark_usage,
    get_daily_custom_usage,
    get_loop_question_events,
    get_mock_history,
    get_mock_session,
    get_previously_mocked_ids,
    get_submission_events,
    get_weekly_benchmark_usage,
    mark_solved,
    record_submission,
    submit_mock_question,
)
from deps import get_current_user
from evaluator import evaluate
from exceptions import BadRequestError
from python_evaluator import evaluate_python_code, evaluate_python_data_code
from routers.insights import _CONCEPTS_LOOKUP, build_session_debrief
from tracks import TRACKS, VALID_MOCK_ROLES, get_track, mixed_mock_slugs, role_tracks
from unlock import compute_mock_access, compute_unlock_state, normalize_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mock")

# ── Constants ──────────────────────────────────────────────────────────────────

# Legacy read-only modes — still appear in session history but cannot be started new.
MODE_CONFIGS: dict[str, dict[str, int]] = {
    "60min": {"num_questions": 3, "time_limit_s": 3600},
}

BENCHMARK_CONFIGS: dict[str, dict[str, int]] = {
    "sql": {"num_questions": 3, "time_limit_s": 3600},
    "python": {"num_questions": 2, "time_limit_s": 3000},
    "python-data": {"num_questions": 2, "time_limit_s": 3000},
    "statistics": {"num_questions": 3, "time_limit_s": 2700},
    "pyspark": {"num_questions": 6, "time_limit_s": 2400},
    "data-engineering": {"num_questions": 6, "time_limit_s": 2400},
    "data-modeling": {"num_questions": 5, "time_limit_s": 2400},
    "ml-fundamentals": {"num_questions": 6, "time_limit_s": 2400},
    "experimentation": {"num_questions": 6, "time_limit_s": 2400},
}

# Mixed benchmark blueprints: role → {track: slot_count, ...} + time_limit_s
# Each role maps to a fixed per-track slot allocation for benchmark sessions.
MIXED_BENCHMARK_CONFIGS: dict[str, dict] = {
    "data_analyst": {
        "slots": {"sql": 2, "python-data": 1, "statistics": 1},
        "time_limit_s": 3300,  # 55 min
    },
    "data_engineer": {
        "slots": {"sql": 1, "python": 1, "pyspark": 1, "data-engineering": 1},
        "time_limit_s": 3300,
    },
    "analytics_engineer": {
        "slots": {"sql": 2, "data-modeling": 1, "python-data": 1},
        "time_limit_s": 3300,
    },
    "data_scientist": {
        "slots": {"python": 1, "python-data": 1, "statistics": 1, "ml-fundamentals": 1},
        "time_limit_s": 3300,
    },
}

VALID_TRACKS = {t.slug for t in TRACKS} | {"mixed"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "mixed"}

# Maps URL-style track slug → topic string used in mark_solved / get_solved_ids
TRACK_TO_TOPIC: dict[str, str] = {t.slug: t.db_topic for t in TRACKS}


# ── Request models ─────────────────────────────────────────────────────────────

class MockStartRequest(BaseModel):
    mode: str           # 'benchmark' | 'custom' | 'interview_loop'
    track: str          # 'sql' | 'python' | 'python-data' | 'pyspark' | 'mixed' | ...
    difficulty: str     # 'easy' | 'medium' | 'hard' | 'mixed'
    role: str | None = None            # required when track='mixed'
    num_questions: int | None = None   # custom mode only, 1–5
    time_minutes: int | None = None    # custom mode only, 10–90
    company_filter: str | None = None  # elite-only; e.g. "Meta", "Stripe"
    focus_concepts: list[str] | None = None  # elite-only; up to 3 concept names


class MockSubmitRequest(BaseModel):
    question_id: int
    track: str
    code: str | None = None
    selected_option: int | None = None  # PySpark MCQ
    time_spent_s: int | None = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_catalog_for_track(track: str):
    """Return the catalog module for a single (non-mixed) track."""
    return get_track(track).catalog_module


async def _get_solved_ids_for_track(user_id: str, track: str) -> set[int]:
    from db import get_solved_ids
    topic = TRACK_TO_TOPIC[track]
    return await get_solved_ids(user_id, topic)


def _is_chain_question(q: dict) -> bool:
    """
    Return True if a question is part of a chain (parent or child).

    Chain parents have a non-empty follow_ups[] list.
    Chain children have a follow_up_parent or follow_up_dimension field set.

    Chain questions must only appear in interview_loop sessions via _select_chain().
    They are excluded from benchmark and custom pools to avoid standalone use.
    """
    if q.get("follow_ups"):
        return True
    if q.get("follow_up_parent") is not None:
        return True
    if q.get("follow_up_dimension") is not None:
        return True
    return False


def _pool_for_track(
    track: str,
    difficulty: str,
    user_plan: str,
    solved_ids: set[int],
) -> list[dict]:
    """
    Build the mock question pool for a given track/difficulty/plan combination.

    Pool rules:
      Easy:   practice catalog only (all plans)
      Medium: Free      → practice catalog, filtered to unlocked questions only
              Pro/Elite → practice catalog (all medium) + mock-only medium bank
      Hard:   Free      → caller blocks this before reaching here (plan_locked)
              Pro/Elite → practice catalog (all hard) + mock-only hard bank

    Mock-only questions bypass the unlock gate entirely — they are always included
    for Pro/Elite users and are never shown in the practice catalog.

    Chain questions (parents with follow_ups[] or children with follow_up_parent /
    follow_up_dimension) are excluded from this pool. They are reserved exclusively
    for interview_loop sessions via _select_chain().
    """
    effective_plan = normalize_plan(user_plan)
    include_mock_only = effective_plan in ("pro", "elite") and difficulty != "easy"

    catalog = _get_catalog_for_track(track)
    grouped = catalog.get_questions_by_difficulty()
    unlock_state = compute_unlock_state(user_plan, solved_ids, grouped, track=track)

    pool: list[dict] = []

    # Standard practice questions — filtered to unlocked/solved state, chains excluded
    for diff, qs in grouped.items():
        if difficulty != "mixed" and diff != difficulty:
            continue
        for q in qs:
            if unlock_state.get(int(q["id"]), "locked") != "locked" and not _is_chain_question(q):
                pool.append({**q, "_track": track, "_mock_only": False})

    # Mock-only questions — bypass unlock gate entirely, chains excluded
    if include_mock_only:
        mock_grouped = catalog.get_mock_questions_by_difficulty()
        for diff, qs in mock_grouped.items():
            if difficulty != "mixed" and diff != difficulty:
                continue
            for q in qs:
                if not _is_chain_question(q):
                    pool.append({**q, "_track": track, "_mock_only": True})

    return pool


def _match_focus_concepts(
    pool: list[dict],
    focus_concepts: list[str],
    track: str,
) -> list[dict]:
    """
    Return questions from pool whose concept tags match at least one focus concept.
    For mixed-track pools each question's own ``_track`` is used for family lookup.
    """
    return [
        q for q in pool
        if any(
            concept_matches_focus(qc, fc, q.get("_track", track))
            for qc in q.get("concepts", [])
            for fc in focus_concepts
        )
    ]


def _pyspark_format_targets(difficulty: str, num_questions: int) -> list[str]:
    """
    Target format slot sequence for PySpark sessions.
    Based on actual pool distribution:
      easy:   predict_output(19), conceptual(14), debug(7)
      medium: predict_output(32), conceptual(31), debug(27), scenario(14), optimization(16) [practice + mock-only combined]
      hard:   conceptual(20), scenario(4), predict_output(2) [practice only]
      mixed:  all of the above combined
    """
    targets: dict[str, list[str]] = {
        "easy":   ["predict_output", "conceptual", "predict_output", "debug", "predict_output", "conceptual"],
        "medium": ["predict_output", "debug", "predict_output", "debug", "conceptual", "scenario"],
        "hard":   ["conceptual", "scenario", "predict_output", "conceptual", "scenario", "conceptual"],
        "mixed":  ["conceptual", "scenario", "predict_output", "debug", "conceptual", "scenario"],
    }
    base = targets.get(difficulty, ["conceptual"] * num_questions)
    if len(base) >= num_questions:
        return base[:num_questions]
    return base + [base[-1] if base else "conceptual"] * (num_questions - len(base))


def _sample_by_format(
    pool: list[dict],
    targets: list[str],
    mocked_ids: set[int],
) -> tuple[list[dict], bool]:
    """
    Sample from pool following format slot targets (fresh-first within each slot).
    Falls back to any remaining question if a format partition is exhausted.
    Returns (chosen, type_fallback_occurred) where type_fallback_occurred is True
    if any slot was filled from outside its declared type partition.
    """
    by_type: dict[str, list[dict]] = {}
    for q in pool:
        by_type.setdefault(q.get("type", "conceptual"), []).append(q)

    chosen: list[dict] = []
    used_ids: set[int] = set()
    type_fallback = False

    for fmt in targets:
        partition = [q for q in by_type.get(fmt, []) if int(q["id"]) not in used_ids]
        if not partition:
            partition = [q for q in pool if int(q["id"]) not in used_ids]
            if partition:
                type_fallback = True
        if not partition:
            break
        fresh = [q for q in partition if int(q["id"]) not in mocked_ids]
        pick = random.choice(fresh) if fresh else random.choice(partition)
        chosen.append(pick)
        used_ids.add(int(pick["id"]))

    return chosen, type_fallback


def _mixed_difficulty_targets(num_questions: int) -> list[str]:
    """
    Target difficulty slot sequence for mixed-difficulty sessions.
      1q: [medium]
      2q: [easy, medium]
      3q: [easy, medium, hard]
      4q: [easy, medium, medium, hard]
      5q: [easy, medium, medium, hard, hard]
    """
    full = ["easy", "medium", "hard", "medium", "hard"]
    return full[:num_questions]


def _sample_by_difficulty(
    pool: list[dict],
    targets: list[str],
    mocked_ids: set[int],
) -> list[dict]:
    """
    Sample from pool following difficulty slot targets (fresh-first within each slot).
    Falls back to any remaining question if a difficulty partition is exhausted.
    """
    by_diff: dict[str, list[dict]] = {}
    for q in pool:
        by_diff.setdefault(q.get("difficulty", "medium"), []).append(q)

    chosen: list[dict] = []
    used_ids: set[int] = set()

    for diff in targets:
        partition = [q for q in by_diff.get(diff, []) if int(q["id"]) not in used_ids]
        if not partition:
            partition = [q for q in pool if int(q["id"]) not in used_ids]
        if not partition:
            break
        fresh = [q for q in partition if int(q["id"]) not in mocked_ids]
        pick = random.choice(fresh) if fresh else random.choice(partition)
        chosen.append(pick)
        used_ids.add(int(pick["id"]))

    return chosen


def _fresh_first_sample(pool: list[dict], count: int, mocked_ids: set[int]) -> list[dict]:
    fresh = [q for q in pool if int(q["id"]) not in mocked_ids]
    stale = [q for q in pool if int(q["id"]) in mocked_ids]
    if len(fresh) >= count:
        return random.sample(fresh, count)
    if len(fresh) + len(stale) >= count:
        return fresh + random.sample(stale, count - len(fresh))
    return []


def _sample_statistics_benchmark(pool: list[dict], mocked_ids: set[int]) -> list[dict]:
    numerical = [q for q in pool if q.get("subtype") == "numerical"]
    conceptual = [q for q in pool if q.get("subtype") == "conceptual"]

    chosen_numerical = _fresh_first_sample(numerical, 1, mocked_ids)
    chosen_conceptual = _fresh_first_sample(conceptual, 2, mocked_ids)

    if len(chosen_numerical) != 1 or len(chosen_conceptual) != 2:
        return []

    chosen = chosen_numerical + chosen_conceptual
    random.shuffle(chosen)
    return chosen


def _benchmark_type_targets(track: str, difficulty: str, num_questions: int) -> list[str]:
    if track == "pyspark":
        return _pyspark_format_targets(difficulty, num_questions)

    # Per-(track, difficulty) overrides for banks whose type distribution differs
    # from the track default at a specific difficulty. See docs/features/mock.md
    # § Benchmark composition for the canonical type-target contract.
    difficulty_overrides: dict[tuple[str, str], list[str]] = {
        ("data-modeling", "easy"): ["scenario", "conceptual", "conceptual", "conceptual", "conceptual"],
        # Experimentation medium/hard: intentional scenario skew documented in docs/tracks/experimentation.md.
        # Standard target asks for 2 conceptuals; medium bank has 1 and hard has 0.
        ("experimentation", "medium"): ["scenario", "predict_output", "debug", "scenario", "scenario", "scenario"],
        ("experimentation", "hard"): ["scenario", "debug", "predict_output", "scenario", "debug", "scenario"],
    }
    override = difficulty_overrides.get((track, difficulty))
    if override is not None:
        if len(override) >= num_questions:
            return override[:num_questions]
        return override + [override[-1]] * (num_questions - len(override))

    targets: dict[str, list[str]] = {
        "data-engineering": ["scenario", "conceptual", "debug", "scenario", "scenario", "conceptual"],
        "data-modeling": ["scenario", "conceptual", "scenario", "conceptual", "scenario"],
        "ml-fundamentals": ["scenario", "conceptual", "predict_output", "debug", "scenario", "conceptual"],
        "experimentation": ["scenario", "conceptual", "predict_output", "debug", "scenario", "conceptual"],
    }
    base = targets.get(track, ["conceptual"] * num_questions)
    if len(base) >= num_questions:
        return base[:num_questions]
    return base + [base[-1] if base else "conceptual"] * (num_questions - len(base))


async def _select_questions(
    track: str,
    difficulty: str,
    num_questions: int,
    user: dict,
    focus_concepts: list[str] | None = None,
    mode: str | None = None,
    role: str | None = None,
) -> tuple[list[dict], bool, bool, bool]:
    """
    Select `num_questions` questions for a mock session with freshness scoring.

    Freshness scoring: questions never seen by this user in any past mock session
    are preferred. Only falls back to previously-seen (stale) questions when the
    fresh pool is exhausted.

    When focus_concepts is provided (Elite only), the pool is filtered to questions
    tagged with those concepts. If fewer matching questions exist than needed, the
    selection falls back to the full pool (focus_fallback=True).

    Mixed track with mode=benchmark: per-track slot allocation per MIXED_BENCHMARK_CONFIGS[role].
    Mixed track with mode=custom: draws from role_tracks(role) pool combined.

    Returns (selected, focus_fallback, track_substituted, type_fallback) — see
    docs/features/mock.md § Degradation contracts for the full table of flags.
    `track_substituted` fires when a mixed-benchmark slot is filled from a
    different track in the role profile because the declared track's pool was
    exhausted for the user. `type_fallback` fires when a single-track benchmark
    slot is filled from outside its declared type partition (via _sample_by_format).
    """
    user_plan = user.get("plan", "free")
    user_id = user["id"]

    _not_enough = HTTPException(
        status_code=400,
        detail=(
            "Not enough unlocked questions for this configuration. "
            "Try a lower difficulty or upgrade your plan."
        ),
    )

    # ── Mixed benchmark: per-track slot filling ────────────────────────────────
    if track == "mixed" and mode == "benchmark":
        blueprint = MIXED_BENCHMARK_CONFIGS[role]  # role validated before this point
        mocked_ids = await get_previously_mocked_ids(user_id)
        chosen_raw: list[dict] = []
        substituted = False
        slots = blueprint["slots"]
        ordered_tracks = list(slots.keys())

        for t, slot_count in slots.items():
            solved = await _get_solved_ids_for_track(user_id, t)
            t_pool = _pool_for_track(t, difficulty, user_plan, solved)
            # Exclude already-chosen IDs from this batch
            used_ids = {int(q["id"]) for q in chosen_raw}
            t_pool = [q for q in t_pool if int(q["id"]) not in used_ids]
            selected = _fresh_first_sample(t_pool, slot_count, mocked_ids)
            if len(selected) < slot_count:
                # Fallback: substitute from next-deepest track in the role profile
                substituted = True
                fallback_tracks = [ft for ft in ordered_tracks if ft != t]
                for ft in fallback_tracks:
                    if len(selected) >= slot_count:
                        break
                    ft_solved = await _get_solved_ids_for_track(user_id, ft)
                    ft_pool = _pool_for_track(ft, difficulty, user_plan, ft_solved)
                    used_ids = {int(q["id"]) for q in chosen_raw} | {int(q["id"]) for q in selected}
                    ft_pool = [q for q in ft_pool if int(q["id"]) not in used_ids]
                    needed = slot_count - len(selected)
                    selected += _fresh_first_sample(ft_pool, needed, mocked_ids)
            chosen_raw.extend(selected)

        random.shuffle(chosen_raw)
        selected_list = [
            {"question_id": int(q["id"]), "track": q["_track"], "position": i + 1}
            for i, q in enumerate(chosen_raw)
        ]
        # Mixed benchmarks fill each track slot via fresh-first pool sampling
        # (not type-targeted), so type_fallback never applies on this path.
        return selected_list, False, substituted, False

    # ── Mixed custom: draw from role tracks combined pool ──────────────────────
    if track == "mixed":
        pool: list[dict] = []
        source_slugs = role_tracks(role) if role else mixed_mock_slugs()
        for t in source_slugs:
            solved = await _get_solved_ids_for_track(user_id, t)
            pool.extend(_pool_for_track(t, difficulty, user_plan, solved))
    else:
        solved = await _get_solved_ids_for_track(user_id, track)
        pool = _pool_for_track(track, difficulty, user_plan, solved)

    # ── Degradation flags (see docs/features/mock.md § Degradation contracts)
    focus_fallback = False
    type_fallback = False

    # ── Focus filtering (Elite only) ───────────────────────────────────────────
    focus_pool: list[dict] = []
    if focus_concepts:
        focus_pool = _match_focus_concepts(pool, focus_concepts, track)
        if len(focus_pool) >= num_questions:
            pool = focus_pool
            focus_pool = []
        else:
            focus_fallback = True

    # ── Freshness scoring ──────────────────────────────────────────────────────
    mocked_ids = await get_previously_mocked_ids(user_id)

    if focus_fallback and focus_pool:
        non_focus = [q for q in pool if q not in focus_pool]
        nf_fresh = [q for q in non_focus if int(q["id"]) not in mocked_ids]
        nf_stale = [q for q in non_focus if int(q["id"]) in mocked_ids]

        guaranteed = list(focus_pool)
        remaining_needed = num_questions - len(guaranteed)

        if remaining_needed > 0:
            if len(nf_fresh) + len(nf_stale) < remaining_needed:
                raise _not_enough
            take_fresh = min(remaining_needed, len(nf_fresh))
            take_stale = remaining_needed - take_fresh
            filler = random.sample(nf_fresh, take_fresh)
            if take_stale:
                filler += random.sample(nf_stale, take_stale)
        else:
            filler = []

        chosen_raw = guaranteed + filler
        random.shuffle(chosen_raw)
    elif mode == "benchmark" and track == "statistics":
        chosen_raw = _sample_statistics_benchmark(pool, mocked_ids)
        if len(chosen_raw) < num_questions:
            raise _not_enough
    elif mode == "benchmark" and track != "mixed" and get_track(track).eval_kind == "mcq":
        fmt_targets = _benchmark_type_targets(track, difficulty, num_questions)
        chosen_raw, type_fallback = _sample_by_format(pool, fmt_targets, mocked_ids)
        if len(chosen_raw) < num_questions:
            raise _not_enough
    elif track == "pyspark" and difficulty != "mixed":
        fmt_targets = _pyspark_format_targets(difficulty, num_questions)
        chosen_raw, type_fallback = _sample_by_format(pool, fmt_targets, mocked_ids)
        if len(chosen_raw) < num_questions:
            raise _not_enough
    elif difficulty == "mixed":
        diff_targets = _mixed_difficulty_targets(num_questions)
        chosen_raw = _sample_by_difficulty(pool, diff_targets, mocked_ids)
        if len(chosen_raw) < num_questions:
            raise _not_enough
    else:
        fresh = [q for q in pool if int(q["id"]) not in mocked_ids]
        stale = [q for q in pool if int(q["id"]) in mocked_ids]

        if len(fresh) >= num_questions:
            chosen_raw = random.sample(fresh, num_questions)
        elif len(fresh) + len(stale) >= num_questions:
            chosen_raw = fresh + random.sample(stale, num_questions - len(fresh))
        else:
            raise _not_enough

    selected = [
        {
            "question_id": int(q["id"]),
            "track": q["_track"],
            "position": i + 1,
        }
        for i, q in enumerate(chosen_raw)
    ]
    # Non-mixed paths can't set track_substituted (it's a mixed-only signal);
    # type_fallback is set only on the two _sample_by_format branches above.
    return selected, focus_fallback, False, type_fallback


async def _select_chain(
    track: str,
    difficulty: str,
    user: dict,
    focus_concepts: list[str] | None = None,
) -> tuple[dict, list[dict]]:
    """
    Select 1 chain (parent + follow-ups) for an Interview Loop session.

    Returns (parent_dict, [follow_up_dicts...]) with _track injected.
    Raises 409 pool_exhausted when no eligible chain remains.
    """
    user_id = user["id"]
    catalog = _get_catalog_for_track(track)

    # Get consumed chains for this user
    consumed_parent_ids = await get_consumed_chain_parent_ids(user_id)

    # Load mock-only questions for this track/difficulty
    mock_grouped = catalog.get_mock_questions_by_difficulty()
    if difficulty == "mixed":
        all_mock = [q for qs in mock_grouped.values() for q in qs]
    else:
        all_mock = mock_grouped.get(difficulty, [])

    # Find eligible parents: has follow_ups[] with length >= 1, not consumed
    parents = [
        q for q in all_mock
        if q.get("follow_ups") and len(q.get("follow_ups", [])) >= 1
        and int(q["id"]) not in consumed_parent_ids
    ]

    # Focus concept filter (applies to parent only; full chain travels regardless)
    if focus_concepts and parents:
        focused = _match_focus_concepts(parents, focus_concepts, track)
        if focused:
            parents = focused
        # If no focused parents match, use all eligible parents (focus doesn't cause pool exhaustion)

    if not parents:
        raise HTTPException(
            status_code=409,
            detail={
                "pool_exhausted": True,
                "block_copy": (
                    "You've completed all available Interview Loop chains for this track and difficulty. "
                    "Try a different track, or check back when new content is added."
                ),
            },
        )

    # Fresh-first selection
    mocked_ids = await get_previously_mocked_ids(user_id)
    fresh_parents = [p for p in parents if int(p["id"]) not in mocked_ids]
    selected_parent = random.choice(fresh_parents) if fresh_parents else random.choice(parents)

    # Load follow-up question objects in follow_ups[] order
    follow_up_ids = selected_parent.get("follow_ups", [])
    follow_ups: list[dict] = []
    for fuid in follow_up_ids:
        fu_q = catalog.get_question(int(fuid))
        if fu_q is None:
            raise HTTPException(
                status_code=500,
                detail=f"Follow-up question {fuid} not found in catalog",
            )
        follow_ups.append({**fu_q, "_track": track})

    return {**selected_parent, "_track": track}, follow_ups


def _public_question_payload(question: dict, track: str) -> dict:
    """Return safe question fields for the session start response (no solutions)."""
    payload: dict[str, Any] = {
        "id": question["id"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "track": track,
        "concepts": question.get("concepts", []),
        "hints": question.get("hints", []),
    }
    # New mock-only question format fields.
    # These keys are always present (None when not applicable) so the response
    # shape is consistent regardless of which question is selected.
    payload["type"] = question.get("type")
    payload["framing"] = question.get("framing")
    if question.get("interaction_mode") is not None:
        payload["interaction_mode"] = question.get("interaction_mode")
    # result_preview, debug_error, starter_code only apply to SQL and Pandas;
    # PySpark uses "debug" type differently (MCQ-style, no code editor).
    if track in ("sql", "python-data"):
        payload["result_preview"] = question.get("result_preview") if question.get("type") == "reverse" else None
        payload["debug_error"] = question.get("debug_error") if question.get("type") == "debug" else None
        # starter_query for SQL, starter_code for Pandas
        payload["starter_code"] = (
            question.get("starter_query") or question.get("starter_code")
        ) if question.get("type") == "debug" else None
    # SQL: include schema
    if track == "sql":
        payload["schema"] = question.get("schema", {})
        payload["dataset_files"] = question.get("dataset_files", [])
    # Python: include test case inputs (no expected outputs)
    if track == "python":
        public_cases = [
            {"input": tc.get("input"), "description": tc.get("description", "")}
            for tc in question.get("test_cases", [])[:question.get("public_test_cases", 999)]
        ]
        payload["test_cases"] = public_cases
    # Pandas: include available dataframes info
    if track == "python-data":
        payload["dataframes"] = {
            name: {"description": info.get("description", "") if isinstance(info, dict) else str(info)}
            for name, info in question.get("dataframes", {}).items()
        }
    # MCQ tracks (PySpark, Data Engineering, …): include options and display fields
    if get_track(track).eval_kind == "mcq":
        payload["options"] = question.get("options", [])
        payload["question_type"] = question.get("type", "conceptual")
        payload["code_snippet"] = question.get("code_snippet")
        payload["scenario_context"] = question.get("scenario_context")
    # Mixed subtype (Statistics): branch on per-question subtype
    if get_track(track).mixed_subtype:
        subtype = question.get("subtype", "conceptual")
        payload["subtype"] = subtype
        if subtype == "conceptual":
            payload["options"] = question.get("options", [])
            payload["question_type"] = question.get("type", "conceptual")
            payload["code_snippet"] = question.get("code_snippet")
            payload["scenario_context"] = question.get("scenario_context")
        else:  # numerical
            all_cases = question.get("test_cases", [])
            ptc = question.get("public_test_cases")
            public_count = len(ptc) if isinstance(ptc, list) else (ptc if isinstance(ptc, int) else len(all_cases))
            payload["test_cases"] = [
                {"input": tc.get("input"), "description": tc.get("description", "")}
                for tc in all_cases[:public_count]
            ]
            payload["starter_code"] = question.get("starter_code", "")
            payload["function_signature"] = question.get("function_signature")
    return payload


def _solution_payload(question: dict, track: str) -> dict:
    """Return solution fields, shown only in the finish/summary response."""
    if track == "sql":
        solution_text = question.get("solution_query", "")
        return {
            "solution": solution_text,
            "solution_query": solution_text,
            "explanation": question.get("explanation", ""),
        }
    if track in ("python", "python-data"):
        solution_text = question.get("expected_code", "")
        return {
            "solution": solution_text,
            "solution_code": solution_text,
            "explanation": question.get("explanation", ""),
        }
    if get_track(track).eval_kind == "mcq":
        correct_option = question.get("correct_option")
        return {
            "solution": str(correct_option) if correct_option is not None else None,
            "correct_option": correct_option,
            "explanation": question.get("explanation", ""),
        }
    if get_track(track).mixed_subtype:
        subtype = question.get("subtype", "conceptual")
        if subtype == "conceptual":
            correct_option = question.get("correct_option")
            return {
                "solution": str(correct_option) if correct_option is not None else None,
                "correct_option": correct_option,
                "explanation": question.get("explanation", ""),
            }
        solution_text = question.get("expected_code", "")
        return {
            "solution": solution_text,
            "solution_code": solution_text,
            "explanation": question.get("explanation", ""),
        }
    return {}


def _evaluate_submission(
    track: str,
    question: dict,
    code: str | None,
    selected_option: int | None,
) -> tuple[bool, dict]:
    """
    Run the appropriate evaluator and return (accepted, result_dict).
    result_dict is a lean dict safe to return mid-session (no solutions).
    """
    if track == "sql":
        if not code:
            return False, {"error": "No code provided"}
        try:
            result = evaluate(code, question["expected_query"], question)
        except (BadRequestError, ValueError) as exc:
            # Parse/guard errors (e.g. syntax error) still count as a failed attempt.
            # Return structured wrong-answer — no 400 raised, question consumed as incorrect.
            return False, {"correct": False, "feedback": [str(exc)]}
        accepted = bool(result.get("correct")) and bool(result.get("structure_correct", True))
        return accepted, {
            "correct": accepted,
            "feedback": result.get("feedback", []),
            "user_result": result.get("user_result"),
            "expected_result": result.get("expected_result"),
        }

    if track == "python":
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate_python_code(code, question)
        accepted = bool(result.get("correct"))
        return accepted, {
            "correct": accepted,
            "error": result.get("error"),
            "public_results": result.get("public_results", []),
            "hidden_summary": result.get("hidden_summary"),
        }

    if track == "python-data":
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate_python_data_code(code, question)
        accepted = bool(result.get("correct"))
        return accepted, {
            "correct": accepted,
            "error": result.get("error"),
        }

    if get_track(track).eval_kind == "mcq":
        if selected_option is None:
            return False, {"error": "No option selected"}
        accepted = is_mcq_correct(selected_option, question)
        return accepted, {"correct": accepted}

    if get_track(track).mixed_subtype:
        subtype = question.get("subtype", "conceptual")
        if subtype == "conceptual":
            if selected_option is None:
                return False, {"error": "No option selected"}
            accepted = is_mcq_correct(selected_option, question)
            return accepted, {"correct": accepted}
        # numerical
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate_python_code(code, question)
        accepted = bool(result.get("correct"))
        return accepted, {
            "correct": accepted,
            "error": result.get("error"),
            "public_results": result.get("public_results", []),
            "hidden_summary": result.get("hidden_summary"),
        }

    return False, {"error": f"Unknown track: {track}"}


def _validate_non_empty_input(
    track: str,
    code: str | None,
    selected_option: int | None,
    question: dict,
) -> None:
    """
    Raise 422 if the submission carries no real answer.

    Called BEFORE any DB write so blank/missing submissions never consume
    the question's one-submit slot.
    """
    if track in ("sql", "python", "python-data"):
        if not code or not code.strip():
            raise HTTPException(status_code=422, detail="Code cannot be blank")
    elif get_track(track).eval_kind == "mcq":
        if selected_option is None:
            raise HTTPException(status_code=422, detail="An option must be selected")
    elif get_track(track).mixed_subtype:
        subtype = question.get("subtype", "conceptual")
        if subtype == "conceptual" and selected_option is None:
            raise HTTPException(status_code=422, detail="An option must be selected")
        elif subtype == "numerical" and (not code or not code.strip()):
            raise HTTPException(status_code=422, detail="Code cannot be blank")


# ── Analytics helper ──────────────────────────────────────────────────────────

def _parse_iso_dt(s: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string (with or without Z suffix) to a timezone-aware datetime."""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _empty_mock_session_summary() -> dict[str, Any]:
    return {
        "total_sessions": 0,
        "sessions_last_30d": 0,
        "avg_score_pct": 0.0,
        "best_score_pct": 0.0,
        "avg_time_used_pct": 0.0,
        "track_breakdown": {},
        "difficulty_breakdown": {},
        "score_trend": [],
    }


def _compute_mock_session_summary(sessions: list[dict]) -> dict[str, Any]:
    completed = [
        s for s in sessions
        if s.get("status") == "completed" and (s.get("total_count") or 0) > 0
    ]

    empty = _empty_mock_session_summary()
    if not completed:
        return empty

    now = datetime.now(UTC)
    cutoff_30d = now - timedelta(days=30)

    # Score per session (0–100)
    def _score(s: dict) -> float:
        return s["solved_count"] / s["total_count"] * 100

    scores = [_score(s) for s in completed]
    avg_score_pct = round(sum(scores) / len(scores), 1)
    best_score_pct = round(max(scores), 1)

    # Sessions last 30 days (by ended_at or started_at)
    sessions_last_30d = sum(
        1 for s in completed
        if (_parse_iso_dt(s.get("ended_at")) or _parse_iso_dt(s.get("started_at")) or datetime.min.replace(tzinfo=UTC)) >= cutoff_30d
    )

    # Avg time-used pct (time used / time_limit, proxy from ended_at - started_at)
    time_pcts: list[float] = []
    for s in completed:
        limit = s.get("time_limit_s") or 0
        if limit <= 0:
            continue
        started = _parse_iso_dt(s.get("started_at"))
        ended = _parse_iso_dt(s.get("ended_at"))
        if started and ended:
            used_s = min(int((ended - started).total_seconds()), limit)
            time_pcts.append(used_s / limit * 100)
    avg_time_used_pct = round(sum(time_pcts) / len(time_pcts), 1) if time_pcts else 0.0

    # Score trend: last 10 completed sessions, chronological
    sorted_completed = sorted(
        completed,
        key=lambda s: s.get("ended_at") or s.get("started_at") or "",
    )
    score_trend = [round(_score(s), 1) for s in sorted_completed[-10:]]

    # Track breakdown
    track_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"sessions": 0, "score_sum": 0.0})
    for s in completed:
        t = s.get("track", "sql")
        track_stats[t]["sessions"] += 1
        track_stats[t]["score_sum"] += _score(s)
    track_breakdown = {
        t: {
            "sessions": v["sessions"],
            "avg_score_pct": round(v["score_sum"] / v["sessions"], 1),
        }
        for t, v in track_stats.items()
    }

    # Difficulty breakdown
    diff_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"sessions": 0, "score_sum": 0.0})
    for s in completed:
        d = s.get("difficulty", "medium")
        diff_stats[d]["sessions"] += 1
        diff_stats[d]["score_sum"] += _score(s)
    difficulty_breakdown = {
        d: {
            "sessions": v["sessions"],
            "avg_score_pct": round(v["score_sum"] / v["sessions"], 1),
        }
        for d, v in diff_stats.items()
    }

    return {
        "total_sessions": len(completed),
        "sessions_last_30d": sessions_last_30d,
        "avg_score_pct": avg_score_pct,
        "best_score_pct": best_score_pct,
        "avg_time_used_pct": avg_time_used_pct,
        "track_breakdown": track_breakdown,
        "difficulty_breakdown": difficulty_breakdown,
        "score_trend": score_trend,
    }


def _compute_mock_analytics(
    sessions: list[dict],
    events: list[dict],
    loop_events: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Pure function — compute aggregate analytics from sessions + submission events.

    sessions    : list from get_mock_history
    events      : list from get_submission_events (track, question_id, is_correct)
    loop_events : list from get_loop_question_events (follow_up_dimension, is_solved)

    Returns overall analytics plus separated benchmark/custom/loop summaries.
    """
    overall = _compute_mock_session_summary(sessions)
    completed = [
        s for s in sessions
        if s.get("status") == "completed" and (s.get("total_count") or 0) > 0
    ]
    benchmark_sessions = [s for s in completed if s.get("mode") == "benchmark"]
    custom_sessions = [s for s in completed if s.get("mode") == "custom"]
    loop_sessions = [s for s in completed if s.get("mode") == "interview_loop"]
    drill_sessions = custom_sessions  # alias for backwards compat

    mode_breakdown = {
        "benchmark": len(benchmark_sessions),
        "custom": len(custom_sessions),
        "interview_loop": len(loop_sessions),
        # legacy alias kept for any existing frontend reads
        "drill": len(custom_sessions),
    }

    empty_concepts: dict[str, Any] = {
        **overall,
        "mode_breakdown": mode_breakdown,
        "benchmark_summary": _empty_mock_session_summary(),
        "drill_summary": _empty_mock_session_summary(),
        "loop_summary": {"sessions": 0, "per_dimension_performance": {}},
        "top_concepts": [],
        "weak_concepts": [],
    }
    if not completed:
        return empty_concepts

    # Concept accuracy from submission events
    concept_attempts: dict[str, int] = defaultdict(int)
    concept_correct: dict[str, int] = defaultdict(int)
    for event in events:
        track_key = event.get("track", "sql")
        qid = int(event.get("question_id", 0))
        concepts = _CONCEPTS_LOOKUP.get(track_key, {}).get(qid, [])
        for concept in concepts:
            concept_attempts[concept] += 1
            if event.get("is_correct"):
                concept_correct[concept] += 1

    all_concept_stats = [
        {
            "concept": c,
            "correct": concept_correct.get(c, 0),
            "attempted": concept_attempts[c],
            "accuracy_pct": round(concept_correct.get(c, 0) / concept_attempts[c] * 100, 1),
        }
        for c in concept_attempts
        if concept_attempts[c] >= 3
    ]

    top_concepts = sorted(all_concept_stats, key=lambda x: -x["attempted"])[:5]
    weak_concepts = sorted(
        [c for c in all_concept_stats if c["accuracy_pct"] < 60],
        key=lambda x: x["accuracy_pct"],
    )[:3]

    # Loop: per-dimension performance breakdown
    dim_attempts: dict[str, int] = defaultdict(int)
    dim_correct: dict[str, int] = defaultdict(int)
    for ev in (loop_events or []):
        dim = ev.get("follow_up_dimension")
        if not dim:
            continue
        dim_attempts[dim] += 1
        if ev.get("is_solved"):
            dim_correct[dim] += 1
    per_dimension_performance = {
        dim: {
            "attempted": dim_attempts[dim],
            "correct": dim_correct.get(dim, 0),
            "accuracy_pct": round(dim_correct.get(dim, 0) / dim_attempts[dim] * 100, 1),
        }
        for dim in dim_attempts
    }
    loop_summary = {
        "sessions": len(loop_sessions),
        "per_dimension_performance": per_dimension_performance,
    }

    return {
        **overall,
        "mode_breakdown": mode_breakdown,
        "benchmark_summary": _compute_mock_session_summary(benchmark_sessions),
        "drill_summary": _compute_mock_session_summary(drill_sessions),
        "loop_summary": loop_summary,
        "top_concepts": top_concepts,
        "weak_concepts": weak_concepts,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/access")
async def get_mock_access(
    track: str = "sql",
    mode: str = "benchmark",
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Pre-flight check: can this user start a mock session for a given track + mode?
    Returns access state for each difficulty so the UI can render per-button state.
    """
    user_plan = current_user.get("plan", "free")
    user_id = current_user["id"]

    daily_benchmark_used = await get_daily_benchmark_usage(user_id)
    daily_custom_used = await get_daily_custom_usage(user_id)
    weekly_benchmark_used = await get_weekly_benchmark_usage(user_id)

    access: dict[str, Any] = {}
    for diff in ("easy", "medium", "hard", "mixed"):
        access[diff] = compute_mock_access(
            plan=user_plan,
            track=track,
            difficulty=diff,
            mode=mode,
            daily_benchmark_used=daily_benchmark_used,
            daily_custom_used=daily_custom_used,
            weekly_benchmark_used=weekly_benchmark_used,
        )

    return {
        "plan": user_plan,
        "track": track,
        "mode": mode,
        "daily_benchmark_used": daily_benchmark_used,
        "daily_custom_used": daily_custom_used,
        "weekly_benchmark_used": weekly_benchmark_used,
        "access": access,
    }


@router.get("/history")
async def get_history(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await get_mock_history(current_user["id"], limit=20)


@router.get("/analytics")
async def get_analytics(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Elite-only: return aggregate analytics over the user's last 50 mock sessions.
    Includes score trends, concept accuracy breakdown, track/difficulty splits,
    and per-dimension Interview Loop performance.
    """
    if normalize_plan(current_user.get("plan", "free")) != "elite":
        raise HTTPException(status_code=403, detail="Elite plan required")
    sessions = await get_mock_history(current_user["id"], limit=50)
    events = await get_submission_events(current_user["id"])
    loop_events = await get_loop_question_events(current_user["id"])
    return _compute_mock_analytics(sessions, events, loop_events)


@router.post("/start")
async def start_session(
    body: MockStartRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    user_plan = current_user.get("plan", "free")
    user_id = current_user["id"]

    # ── Basic validation ──────────────────────────────────────────────────────
    if body.track not in VALID_TRACKS:
        raise HTTPException(status_code=400, detail=f"Invalid track. Must be one of: {', '.join(VALID_TRACKS)}")
    if body.difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}")

    valid_start_modes = {"benchmark", "custom", "interview_loop"} | set(MODE_CONFIGS)
    if body.mode not in valid_start_modes:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be 'benchmark', 'custom', or 'interview_loop'.")

    # Legacy read-only modes cannot be started new
    if body.mode in MODE_CONFIGS:
        raise HTTPException(status_code=400, detail=f"Mode '{body.mode}' is read-only legacy and cannot be started.")

    # ── Role validation ───────────────────────────────────────────────────────
    if body.track == "mixed":
        if not body.role:
            raise HTTPException(status_code=400, detail="role is required when track is 'mixed'.")
        if body.role not in VALID_MOCK_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(sorted(VALID_MOCK_ROLES))}")
    else:
        if body.role is not None:
            raise HTTPException(status_code=400, detail="role must be omitted (or null) for non-mixed tracks.")

    # ── Interview Loop: Elite only ────────────────────────────────────────────
    if body.mode == "interview_loop" and normalize_plan(user_plan) != "elite":
        raise HTTPException(status_code=403, detail="Interview Loop is an Elite-only feature.")

    # ── Access gate (plan + daily/weekly caps) ────────────────────────────────
    daily_benchmark_used = await get_daily_benchmark_usage(user_id)
    daily_custom_used = await get_daily_custom_usage(user_id)
    weekly_benchmark_used = await get_weekly_benchmark_usage(user_id)

    access = compute_mock_access(
        plan=user_plan,
        track=body.track,
        difficulty=body.difficulty,
        mode=body.mode,
        daily_benchmark_used=daily_benchmark_used,
        daily_custom_used=daily_custom_used,
        weekly_benchmark_used=weekly_benchmark_used,
        company_filter=bool(body.company_filter),
    )
    if not access["can_start"]:
        raise HTTPException(status_code=403, detail=access["block_copy"] or "Access denied.")

    # ── Focus concepts (Elite only, max 3) ────────────────────────────────────
    focus_concepts: list[str] | None = None
    if body.focus_concepts:
        if normalize_plan(user_plan) != "elite":
            raise HTTPException(status_code=403, detail="Focus mode requires Elite plan")
        if len(body.focus_concepts) > 3:
            raise HTTPException(status_code=422, detail="focus_concepts must have at most 3 items")
        focus_concepts = [c.upper() for c in body.focus_concepts if c.strip()]

    # ── Block if active session exists ────────────────────────────────────────
    active = await get_active_mock_session(user_id)
    if active:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "active_session_exists",
                "message": "You have an active mock session. End it before starting a new one.",
                "session_id": active["session_id"],
                "track": active["track"],
                "difficulty": active["difficulty"],
                "mode": active["mode"],
            },
        )

    # ── Interview Loop: chain selection ──────────────────────────────────────
    if body.mode == "interview_loop":
        if body.track == "mixed":
            raise HTTPException(status_code=400, detail="Interview Loop does not support mixed track.")

        parent, follow_ups = await _select_chain(
            track=body.track,
            difficulty=body.difficulty,
            user=current_user,
            focus_concepts=focus_concepts,
        )
        chain_length = 1 + len(follow_ups)
        time_limit_s = chain_length * 900  # 15 min per question

        # Build questions list: parent at position 1, follow-ups after
        selected: list[dict] = [
            {
                "question_id": int(parent["id"]),
                "track": body.track,
                "position": 1,
                "follow_up_dimension": None,
            }
        ]
        for i, fu in enumerate(follow_ups, start=2):
            selected.append({
                "question_id": int(fu["id"]),
                "track": body.track,
                "position": i,
                "follow_up_dimension": fu.get("follow_up_dimension"),
            })

        # Fetch question details for response
        all_q_dicts = [parent] + follow_ups
        question_details: list[dict] = []
        for pos_idx, (sel, q) in enumerate(zip(selected, all_q_dicts), start=1):
            question_details.append({
                **_public_question_payload(q, body.track),
                "position": sel["position"],
                "follow_up_dimension": sel.get("follow_up_dimension"),
                "is_solved": False,
                "final_code": None,
                "time_spent_s": None,
                "is_follow_up": pos_idx > 1,
            })

        session = await create_mock_session(
            user_id=user_id,
            mode=body.mode,
            track=body.track,
            difficulty=body.difficulty,
            time_limit_s=time_limit_s,
            questions=selected,
            focus_fallback=False,
            role=body.role,
            chain_parent_id=int(parent["id"]),
        )
        return {
            **session,
            "questions": question_details,
            "focus_fallback": False,
        }

    # ── Benchmark: derive num_questions + time_limit_s ────────────────────────
    if body.mode == "benchmark":
        if body.track == "mixed":
            blueprint = MIXED_BENCHMARK_CONFIGS[body.role]  # role validated above
            num_questions = sum(blueprint["slots"].values())
            time_limit_s = blueprint["time_limit_s"]
        else:
            benchmark = BENCHMARK_CONFIGS.get(body.track)
            if benchmark is None:
                raise HTTPException(status_code=400, detail="Benchmark mode is not configured for this track.")
            num_questions = benchmark["num_questions"]
            time_limit_s = benchmark["time_limit_s"]

    # ── Custom: user-supplied parameters ─────────────────────────────────────
    elif body.mode == "custom":
        nq = body.num_questions
        tm = body.time_minutes
        if nq is None or not (1 <= nq <= 5):
            raise HTTPException(status_code=400, detail="num_questions must be between 1 and 5 for custom mode.")
        if tm is None or not (10 <= tm <= 90):
            raise HTTPException(status_code=400, detail="time_minutes must be between 10 and 90 for custom mode.")
        num_questions = nq
        time_limit_s = tm * 60

    else:
        raise HTTPException(status_code=400, detail="Invalid mode.")

    # ── Select questions ──────────────────────────────────────────────────────
    selected_q, focus_fallback, track_substituted, type_fallback = await _select_questions(
        body.track, body.difficulty, num_questions, current_user, focus_concepts, body.mode, body.role
    )

    # Fetch question details for response
    question_details = []
    for sel in selected_q:
        catalog = _get_catalog_for_track(sel["track"])
        q = catalog.get_question(sel["question_id"])
        if q is None:
            raise HTTPException(status_code=500, detail=f"Question {sel['question_id']} not found")
        question_details.append({
            **_public_question_payload(q, sel["track"]),
            "position": sel["position"],
            "is_solved": False,
            "final_code": None,
            "time_spent_s": None,
            "is_follow_up": False,
        })

    # ── Persist session ───────────────────────────────────────────────────────
    session = await create_mock_session(
        user_id=user_id,
        mode=body.mode,
        track=body.track,
        difficulty=body.difficulty,
        time_limit_s=time_limit_s,
        questions=selected_q,
        focus_fallback=focus_fallback,
        role=body.role,
    )

    return {
        **session,
        "questions": question_details,
        "focus_fallback": focus_fallback,
        "track_substituted": track_substituted,
        "type_fallback": type_fallback,
    }


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich question rows with public question detail
    enriched_questions: list[dict] = []
    for q_row in session.get("questions", []):
        catalog = _get_catalog_for_track(q_row["track"])
        q = catalog.get_question(q_row["question_id"])
        if q is None:
            continue
        enriched_questions.append({
            **_public_question_payload(q, q_row["track"]),
            "position": q_row["position"],
            "is_solved": q_row["is_solved"],
            "submitted_at": q_row.get("submitted_at"),
            "final_code": q_row["final_code"],
            "time_spent_s": q_row["time_spent_s"],
            "is_follow_up": q_row.get("is_follow_up", False),
            "follow_up_dimension": q_row.get("follow_up_dimension"),
        })

    return {**session, "questions": enriched_questions}


@router.post("/{session_id}/submit")
async def submit_answer(
    session_id: int,
    body: MockSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if body.track not in TRACK_TO_TOPIC:
        raise HTTPException(status_code=400, detail=f"Invalid track: {body.track}")

    # Load and validate session
    logger.info(
        "submit_answer: session_id=%s user_id=%s question_id=%s track=%s",
        session_id, current_user["id"], body.question_id, body.track,
    )
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
        logger.warning(
            "submit_answer: session not found — session_id=%s user_id=%s",
            session_id, current_user["id"],
        )
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Verify question belongs to session
    session_q_ids = {q["question_id"] for q in session.get("questions", [])}
    if body.question_id not in session_q_ids:
        raise HTTPException(status_code=400, detail="Question not part of this session")

    # Load full question
    catalog = _get_catalog_for_track(body.track)
    question = catalog.get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # Reject blank/empty input before consuming the submit slot
    _validate_non_empty_input(body.track, body.code, body.selected_option, question)

    # Evaluate
    accepted, result = _evaluate_submission(body.track, question, body.code, body.selected_option)

    # Persist mock submission record
    persisted = await submit_mock_question(
        session_id=session_id,
        question_id=body.question_id,
        user_id=current_user["id"],
        is_solved=accepted,
        code=body.code,
        time_spent_s=body.time_spent_s,
    )
    if not persisted:
        raise HTTPException(status_code=409, detail="Question already submitted for this session")

    # Track progress if correct
    if accepted:
        topic = TRACK_TO_TOPIC[body.track]
        await mark_solved(current_user["id"], body.question_id, topic=topic)
        await record_submission(
            user_id=current_user["id"],
            track=body.track,
            question_id=body.question_id,
            is_correct=True,
            code=body.code,
        )
    else:
        await record_submission(
            user_id=current_user["id"],
            track=body.track,
            question_id=body.question_id,
            is_correct=False,
            code=body.code,
        )

    # Return lean result — no solutions mid-session
    # Benchmark/Interview Loop + MCQ: also suppress correctness signal per spec invariant
    # "No correctness reveal mid-session" (mock-benchmark-spec.md § Benchmark invariants)
    if session.get("mode") in ("benchmark", "interview_loop") and get_track(body.track).eval_kind == "mcq":
        result = {k: v for k, v in result.items() if k != "correct"}
    return result


@router.post("/{session_id}/finish")
async def finish_session(
    session_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    summary = await finish_mock_session(session_id, current_user["id"])
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich questions with public detail + solutions
    enriched_questions: list[dict] = []
    for q_row in summary.get("questions", []):
        catalog = _get_catalog_for_track(q_row["track"])
        q = catalog.get_question(q_row["question_id"])
        if q is None:
            continue
        enriched_questions.append({
            **_public_question_payload(q, q_row["track"]),
            **_solution_payload(q, q_row["track"]),   # solutions only at end
            "position": q_row["position"],
            "is_solved": q_row["is_solved"],
            "final_code": q_row["final_code"],
            "time_spent_s": q_row["time_spent_s"],
            "is_follow_up": q_row.get("is_follow_up", False),
            "follow_up_dimension": q_row.get("follow_up_dimension"),
        })

    # Build Elite coaching debrief (template-based, no external AI needed)
    debrief = None
    effective_plan = normalize_plan(current_user.get("plan", "free"))
    if effective_plan == "elite":
        events = await get_submission_events(current_user["id"])
        debrief = build_session_debrief(enriched_questions, summary, events, effective_plan)

    return {**summary, "questions": enriched_questions, "debrief": debrief}


@router.delete("/{session_id}", status_code=204)
async def discard_session(
    session_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> None:
    """Discard an active mock session started within the last 2 minutes.

    Deletes the session and its questions entirely so it never appears in
    history or contributes to any stats. Returns 403 if the session is
    older than 2 minutes or already completed (server-side guard matching
    the frontend's 60-second threshold with buffer).
    """
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") != "active":
        raise HTTPException(status_code=400, detail="Only active sessions can be discarded")

    started_at_raw = session.get("started_at")
    try:
        started_at = datetime.fromisoformat(started_at_raw).replace(tzinfo=UTC) if started_at_raw else None
    except (ValueError, TypeError):
        started_at = None
    if started_at is None or (datetime.now(UTC) - started_at).total_seconds() > 120:
        raise HTTPException(
            status_code=403,
            detail="Session is too old to discard (must be within 2 minutes of starting)",
        )

    await discard_mock_session(session_id, current_user["id"])
