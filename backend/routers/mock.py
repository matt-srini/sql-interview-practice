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

import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_catalog
from db import (
    create_mock_session,
    finish_mock_session,
    get_daily_mock_usage,
    get_mock_history,
    get_mock_session,
    get_previously_mocked_ids,
    get_submission_events,
    inject_follow_up_question,
    mark_solved,
    record_submission,
    submit_mock_question,
)
from deps import get_current_user
from evaluator import evaluate
from python_evaluator import evaluate_python_code, evaluate_python_data_code
from routers.insights import _CONCEPTS_LOOKUP, build_session_debrief
from unlock import compute_mock_access, compute_unlock_state, normalize_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mock")

# ── Constants ──────────────────────────────────────────────────────────────────

MODE_CONFIGS: dict[str, dict[str, int]] = {
    "30min": {"num_questions": 2, "time_limit_s": 1800},
    "60min": {"num_questions": 3, "time_limit_s": 3600},
}

VALID_TRACKS = {"sql", "python", "python-data", "pyspark", "mixed"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "mixed"}

# Maps URL-style track name → topic string used in mark_solved / get_solved_ids
TRACK_TO_TOPIC: dict[str, str] = {
    "sql": "sql",
    "python": "python",
    "python-data": "python_data",
    "pyspark": "pyspark",
}


# ── Request models ─────────────────────────────────────────────────────────────

class MockStartRequest(BaseModel):
    mode: str           # '30min' | '60min' | 'custom'
    track: str          # 'sql' | 'python' | 'python-data' | 'pyspark' | 'mixed'
    difficulty: str     # 'easy' | 'medium' | 'hard' | 'mixed'
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
    if track == "sql":
        return sql_catalog
    if track == "python":
        return python_questions
    if track == "python-data":
        return python_data_questions
    if track == "pyspark":
        return pyspark_questions
    raise ValueError(f"Unknown track: {track}")


async def _get_solved_ids_for_track(user_id: str, track: str) -> set[int]:
    from db import get_solved_ids
    topic = TRACK_TO_TOPIC[track]
    return await get_solved_ids(user_id, topic)


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
    """
    effective_plan = normalize_plan(user_plan)
    include_mock_only = effective_plan in ("pro", "elite") and difficulty != "easy"

    catalog = _get_catalog_for_track(track)
    grouped = catalog.get_questions_by_difficulty()
    unlock_state = compute_unlock_state(user_plan, solved_ids, grouped, track=track)

    pool: list[dict] = []

    # Standard practice questions — filtered to unlocked/solved state
    for diff, qs in grouped.items():
        if difficulty != "mixed" and diff != difficulty:
            continue
        for q in qs:
            if unlock_state.get(int(q["id"]), "locked") != "locked":
                pool.append({**q, "_track": track, "_mock_only": False})

    # Mock-only questions — bypass unlock gate entirely
    if include_mock_only:
        mock_grouped = catalog.get_mock_questions_by_difficulty()
        for diff, qs in mock_grouped.items():
            if difficulty != "mixed" and diff != difficulty:
                continue
            for q in qs:
                pool.append({**q, "_track": track, "_mock_only": True})

    return pool


async def _select_questions(
    track: str,
    difficulty: str,
    num_questions: int,
    user: dict,
    focus_concepts: list[str] | None = None,
) -> tuple[list[dict], bool]:
    """
    Select `num_questions` questions for a mock session with freshness scoring.

    Freshness scoring: questions never seen by this user in any past mock session
    are preferred. Only falls back to previously-seen (stale) questions when the
    fresh pool is exhausted.

    When focus_concepts is provided (Elite only), the pool is filtered to questions
    tagged with those concepts. If fewer matching questions exist than needed, the
    selection falls back to the full pool (focus_fallback=True).

    Returns (list[{"question_id", "track", "position"}], focus_fallback_bool).
    """
    user_plan = user.get("plan", "free")
    user_id = user["id"]

    if track == "mixed":
        single_tracks = ["sql", "python", "python-data", "pyspark"]
        pool: list[dict] = []
        for t in single_tracks:
            solved = await _get_solved_ids_for_track(user_id, t)
            pool.extend(_pool_for_track(t, difficulty, user_plan, solved))
    else:
        solved = await _get_solved_ids_for_track(user_id, track)
        pool = _pool_for_track(track, difficulty, user_plan, solved)

    # Focus filtering (Elite only)
    focus_fallback = False
    if focus_concepts:
        normalized_fc = [c.upper() for c in focus_concepts]
        focus_pool = [
            q for q in pool
            if any(c.upper() in normalized_fc for c in q.get("concepts", []))
        ]
        if len(focus_pool) >= num_questions:
            pool = focus_pool
        else:
            # Not enough focused questions — top up from general pool
            focus_fallback = True
            non_focus = [q for q in pool if q not in focus_pool]
            pool = focus_pool + non_focus

    # Freshness scoring: prefer questions this user has never seen in mock before
    mocked_ids = await get_previously_mocked_ids(user_id)
    fresh = [q for q in pool if int(q["id"]) not in mocked_ids]
    stale = [q for q in pool if int(q["id"]) in mocked_ids]

    if len(fresh) >= num_questions:
        chosen_raw = random.sample(fresh, num_questions)
    elif len(fresh) + len(stale) >= num_questions:
        chosen_raw = fresh + random.sample(stale, num_questions - len(fresh))
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Not enough unlocked questions for this configuration. "
                "Try a lower difficulty or upgrade your plan."
            ),
        )

    selected = [
        {
            "question_id": int(q["id"]),
            "track": q["_track"],
            "position": i + 1,
        }
        for i, q in enumerate(chosen_raw)
    ]
    return selected, focus_fallback


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
    # PySpark: include options
    if track == "pyspark":
        payload["options"] = question.get("options", [])
        payload["question_type"] = question.get("type", "mcq")
        payload["code_snippet"] = question.get("code_snippet")
        payload["scenario_context"] = question.get("scenario_context")
    return payload


def _solution_payload(question: dict, track: str) -> dict:
    """Return solution fields, shown only in the finish/summary response."""
    if track == "sql":
        return {
            "solution_query": question.get("solution_query", ""),
            "explanation": question.get("explanation", ""),
        }
    if track in ("python", "python-data"):
        return {
            "solution_code": question.get("expected_code", ""),
            "explanation": question.get("explanation", ""),
        }
    if track == "pyspark":
        return {
            "correct_option": question.get("correct_option"),
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
        result = evaluate(code, question["expected_query"], question)
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

    if track == "pyspark":
        if selected_option is None:
            return False, {"error": "No option selected"}
        accepted = selected_option == question.get("correct_option")
        return accepted, {"correct": accepted}

    return False, {"error": f"Unknown track: {track}"}


# ── Analytics helper ──────────────────────────────────────────────────────────

def _parse_iso_dt(s: str | None) -> datetime | None:
    """Parse an ISO-8601 datetime string (with or without Z suffix) to a timezone-aware datetime."""
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _compute_mock_analytics(
    sessions: list[dict],
    events: list[dict],
) -> dict[str, Any]:
    """
    Pure function — compute aggregate analytics from sessions + submission events.

    sessions : list from get_mock_history (session_id, mode, track, difficulty,
               started_at, ended_at, time_limit_s, status, total_count, solved_count)
    events   : list from get_submission_events (track, question_id, is_correct,
               submitted_at)

    Returns a dict with:
      total_sessions, sessions_last_30d, avg_score_pct, best_score_pct,
      avg_time_used_pct, track_breakdown, difficulty_breakdown, score_trend,
      top_concepts, weak_concepts
    """
    completed = [
        s for s in sessions
        if s.get("status") == "completed" and (s.get("total_count") or 0) > 0
    ]

    empty: dict[str, Any] = {
        "total_sessions": 0,
        "sessions_last_30d": 0,
        "avg_score_pct": 0.0,
        "best_score_pct": 0.0,
        "avg_time_used_pct": 0.0,
        "track_breakdown": {},
        "difficulty_breakdown": {},
        "score_trend": [],
        "top_concepts": [],
        "weak_concepts": [],
    }
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

    return {
        "total_sessions": len(completed),
        "sessions_last_30d": sessions_last_30d,
        "avg_score_pct": avg_score_pct,
        "best_score_pct": best_score_pct,
        "avg_time_used_pct": avg_time_used_pct,
        "track_breakdown": track_breakdown,
        "difficulty_breakdown": difficulty_breakdown,
        "score_trend": score_trend,
        "top_concepts": top_concepts,
        "weak_concepts": weak_concepts,
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/access")
async def get_mock_access(
    track: str = "sql",
    difficulty: str = "medium",
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Pre-flight check: can this user start a mock session with these parameters?
    Returns access state for each difficulty so the UI can render per-button state.
    Used by MockHub.js to show predictive gating instead of a post-click error.
    """
    user_plan = current_user.get("plan", "free")
    user_id = current_user["id"]

    # Get daily usage across medium and hard
    daily_usage = await get_daily_mock_usage(user_id)

    # For the requested track, check whether medium is unlocked
    medium_unlocked = False
    if track != "mixed":
        try:
            solved = await _get_solved_ids_for_track(user_id, track)
            catalog = _get_catalog_for_track(track)
            grouped = catalog.get_questions_by_difficulty()
            unlock_state = compute_unlock_state(user_plan, solved, grouped, track=track)
            medium_unlocked = any(
                v != "locked" for qid, v in unlock_state.items()
                if any(int(q["id"]) == qid for q in grouped.get("medium", []))
            )
        except Exception:
            pass
    else:
        # Mixed track: medium unlocked if unlocked in any single track
        for t in ["sql", "python", "python-data", "pyspark"]:
            try:
                solved = await _get_solved_ids_for_track(user_id, t)
                catalog = _get_catalog_for_track(t)
                grouped = catalog.get_questions_by_difficulty()
                unlock_state = compute_unlock_state(user_plan, solved, grouped, track=t)
                if any(v != "locked" for qid, v in unlock_state.items()
                       if any(int(q["id"]) == qid for q in grouped.get("medium", []))):
                    medium_unlocked = True
                    break
            except Exception:
                pass

    # Build access state for each difficulty
    access: dict[str, Any] = {}
    for diff in ("easy", "medium", "hard", "mixed"):
        access[diff] = compute_mock_access(
            plan=user_plan,
            track=track,
            difficulty=diff,
            medium_unlocked=medium_unlocked,
            daily_medium_used=daily_usage.get("medium", 0),
            daily_hard_used=daily_usage.get("hard", 0),
        )

    return {
        "plan": user_plan,
        "track": track,
        "daily_usage": daily_usage,
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
    Includes score trends, concept accuracy breakdown, track/difficulty splits.
    """
    if normalize_plan(current_user.get("plan", "free")) != "elite":
        raise HTTPException(status_code=403, detail="Elite plan required")
    sessions = await get_mock_history(current_user["id"], limit=50)
    events = await get_submission_events(current_user["id"])
    return _compute_mock_analytics(sessions, events)


@router.post("/start")
async def start_session(
    body: MockStartRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    # Validate track and difficulty
    if body.track not in VALID_TRACKS:
        raise HTTPException(status_code=400, detail=f"Invalid track. Must be one of: {', '.join(VALID_TRACKS)}")
    if body.difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}")

    # Enforce plan/daily-limit access gates (mirrors the /access endpoint — must stay in sync)
    user_plan = current_user.get("plan", "free")
    user_id = current_user["id"]
    daily_usage = await get_daily_mock_usage(user_id)

    check_track = body.track if body.track != "mixed" else "sql"
    medium_unlocked = False
    if body.track == "mixed":
        for t in ["sql", "python", "python-data", "pyspark"]:
            try:
                solved = await _get_solved_ids_for_track(user_id, t)
                catalog = _get_catalog_for_track(t)
                grouped = catalog.get_questions_by_difficulty()
                unlock_state = compute_unlock_state(user_plan, solved, grouped, track=t)
                if any(v != "locked" for qid, v in unlock_state.items()
                       if any(int(q["id"]) == qid for q in grouped.get("medium", []))):
                    medium_unlocked = True
                    break
            except Exception:
                pass
    else:
        try:
            solved = await _get_solved_ids_for_track(user_id, check_track)
            catalog = _get_catalog_for_track(check_track)
            grouped = catalog.get_questions_by_difficulty()
            unlock_state = compute_unlock_state(user_plan, solved, grouped, track=check_track)
            medium_unlocked = any(
                v != "locked" for qid, v in unlock_state.items()
                if any(int(q["id"]) == qid for q in grouped.get("medium", []))
            )
        except Exception:
            pass

    access = compute_mock_access(
        plan=user_plan,
        track=check_track,
        difficulty=body.difficulty,
        medium_unlocked=medium_unlocked,
        daily_medium_used=daily_usage.get("medium", 0),
        daily_hard_used=daily_usage.get("hard", 0),
        company_filter=bool(body.company_filter),
    )
    if not access["can_start"]:
        raise HTTPException(status_code=403, detail=access["block_copy"] or "Access denied.")

    # Derive num_questions and time_limit_s
    if body.mode in MODE_CONFIGS:
        num_questions = MODE_CONFIGS[body.mode]["num_questions"]
        time_limit_s = MODE_CONFIGS[body.mode]["time_limit_s"]
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
        raise HTTPException(status_code=400, detail="Invalid mode. Must be '30min', '60min', or 'custom'.")

    # Validate focus_concepts (Elite only, max 3 items)
    focus_concepts: list[str] | None = None
    if body.focus_concepts:
        if normalize_plan(user_plan) != "elite":
            raise HTTPException(status_code=403, detail="Focus mode requires Elite plan")
        if len(body.focus_concepts) > 3:
            raise HTTPException(status_code=422, detail="focus_concepts must have at most 3 items")
        focus_concepts = [c.upper() for c in body.focus_concepts if c.strip()]

    # Select questions
    selected, focus_fallback = await _select_questions(
        body.track, body.difficulty, num_questions, current_user, focus_concepts
    )

    # Fetch question details for response
    question_details: list[dict] = []
    for sel in selected:
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

    # Persist session
    session = await create_mock_session(
        user_id=current_user["id"],
        mode=body.mode,
        track=body.track,
        difficulty=body.difficulty,
        time_limit_s=time_limit_s,
        questions=selected,
    )

    return {
        **session,
        "questions": question_details,
        "focus_fallback": focus_fallback,
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
            "final_code": q_row["final_code"],
            "time_spent_s": q_row["time_spent_s"],
            "is_follow_up": q_row.get("is_follow_up", False),
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
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
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

    # Evaluate
    accepted, result = _evaluate_submission(body.track, question, body.code, body.selected_option)

    # Persist mock submission record
    await submit_mock_question(
        session_id=session_id,
        question_id=body.question_id,
        user_id=current_user["id"],
        is_solved=accepted,
        code=body.code,
        time_spent_s=body.time_spent_s,
    )

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

    # Follow-up injection: if this question has a follow_up_id and was answered correctly,
    # inject the follow-up question after the current position (but never at the last position)
    follow_up_injected = False
    follow_up_id = question.get("follow_up_id") if question else None
    if follow_up_id and accepted:
        session_questions = session.get("questions", [])
        current_position = next(
            (sq["position"] for sq in session_questions if sq["question_id"] == body.question_id),
            None,
        )
        if current_position is not None:
            max_position = max((sq["position"] for sq in session_questions), default=0)
            # Only inject if not at the last position — avoid bloating an already-final question
            if current_position < max_position:
                await inject_follow_up_question(
                    session_id=session_id,
                    follow_up_question_id=follow_up_id,
                    after_position=current_position,
                )
                follow_up_injected = True

    # Return lean result — no solutions mid-session
    return {**result, "follow_up_injected": follow_up_injected}


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
        })

    # Build Elite coaching debrief (template-based, no external AI needed)
    debrief = None
    effective_plan = normalize_plan(current_user.get("plan", "free"))
    if effective_plan == "elite":
        events = await get_submission_events(current_user["id"])
        debrief = build_session_debrief(enriched_questions, summary, events, effective_plan)

    return {**summary, "questions": enriched_questions, "debrief": debrief}
