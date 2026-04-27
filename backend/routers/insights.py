from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any

from fastapi import APIRouter, Depends

import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_questions
from db import get_submission_events
from deps import get_current_user
from path_loader import get_all_paths
from unlock import normalize_plan

router = APIRouter(prefix="/api/dashboard")

_TRACK_LABELS = {
    "sql": "SQL",
    "python": "Python",
    "python-data": "Pandas",
    "pyspark": "PySpark",
}

_TRACK_ORDER = ["sql", "python", "python-data", "pyspark"]

_TOPIC_MODULES = {
    "sql": sql_questions,
    "python": python_questions,
    "python-data": python_data_questions,
    "pyspark": pyspark_questions,
}

_CACHE_TTL_SECONDS = 60
_insights_cache: dict[str, dict[str, Any]] = {}

# Maps (track, concept) → (slug, title, tier) for the highest-priority matching path.
# Starter paths take precedence over intermediate, which take precedence over advanced,
# so the recommendation points to the most foundational accessible path first.
def _build_concept_path_index() -> dict[tuple[str, str], tuple[str, str, str]]:
    role_order = {"starter": 0, "intermediate": 1, "advanced": 2}
    paths = sorted(
        get_all_paths(),
        key=lambda p: role_order.get(p.get("role", "advanced"), 2),
    )
    index: dict[tuple[str, str], tuple[str, str, str]] = {}
    for path in paths:
        track = path["topic"]
        tier = path.get("tier", "pro")
        for concept in path.get("focus_concepts", []):
            key = (track, concept)
            if key not in index:
                index[key] = (path["slug"], path["title"], tier)
    return index


_CONCEPT_PATH_INDEX = _build_concept_path_index()


def _build_concepts_lookup() -> dict[str, dict[int, list[str]]]:
    lookup: dict[str, dict[int, list[str]]] = {}
    for track, module in _TOPIC_MODULES.items():
        grouped = module.get_questions_by_difficulty()
        questions = [q for difficulty_questions in grouped.values() for q in difficulty_questions]
        lookup[track] = {
            int(q["id"]): list(q.get("concepts", []))
            for q in questions
        }
    return lookup


_CONCEPTS_LOOKUP = _build_concepts_lookup()


def _cache_get(user_id: str) -> dict[str, Any] | None:
    cached = _insights_cache.get(user_id)
    if not cached:
        return None
    if cached["expires_at"] <= datetime.now(UTC):
        _insights_cache.pop(user_id, None)
        return None
    return cached["payload"]


def _cache_set(user_id: str, payload: dict[str, Any]) -> None:
    _insights_cache[user_id] = {
        "expires_at": datetime.now(UTC) + timedelta(seconds=_CACHE_TTL_SECONDS),
        "payload": payload,
    }


def _compute_streak_days(correct_dates: set[datetime.date]) -> int:
    today = datetime.now(UTC).date()
    if today not in correct_dates:
        return 0

    streak = 0
    cursor = today
    while cursor in correct_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _to_median_solve_seconds(events: list[dict[str, Any]]) -> dict[str, int | None]:
    per_track_durations: dict[str, list[int]] = defaultdict(list)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[(event["track"], int(event["question_id"]))].append(event)

    for (track, _question_id), attempt_events in grouped.items():
        first_attempt_at = attempt_events[0]["submitted_at"]
        first_correct_at = next(
            (item["submitted_at"] for item in attempt_events if item["is_correct"]),
            None,
        )
        if first_correct_at is None:
            continue

        duration_s = int((first_correct_at - first_attempt_at).total_seconds())
        per_track_durations[track].append(max(0, duration_s))

    medians: dict[str, int | None] = {}
    for track in _TRACK_ORDER:
        durations = per_track_durations.get(track, [])
        medians[track] = int(median(durations)) if durations else None
    return medians


def _build_cross_track_insight(per_track: dict[str, dict[str, Any]]) -> str | None:
    candidates: list[tuple[str, int]] = []
    for track, stats in per_track.items():
        median_seconds = stats.get("median_solve_seconds")
        if isinstance(median_seconds, int):
            candidates.append((track, median_seconds))

    if len(candidates) < 2:
        return None

    slow_track, slow_seconds = max(candidates, key=lambda item: item[1])
    fast_track, fast_seconds = min(candidates, key=lambda item: item[1])
    gap = slow_seconds - fast_seconds
    if gap < 60:
        return None

    slow_label = _TRACK_LABELS.get(slow_track, slow_track)
    fast_label = _TRACK_LABELS.get(fast_track, fast_track)
    gap_minutes = max(1, round(gap / 60))

    return (
        f"You solve {slow_label} ~{gap_minutes} minute{'s' if gap_minutes != 1 else ''} "
        f"slower than {fast_label}. Try 3 {slow_label} mediums to close the gap."
    )


@router.get("/insights")
async def get_dashboard_insights(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = current_user["id"]
    effective_plan = normalize_plan(current_user.get("plan", "free"))

    cached = _cache_get(user_id)
    if cached is not None:
        return cached

    events = await get_submission_events(user_id)

    per_track_attempts: dict[str, int] = defaultdict(int)
    per_track_correct: dict[str, int] = defaultdict(int)
    per_track_solved_question_ids: dict[str, set[int]] = defaultdict(set)
    concept_attempts: dict[tuple[str, str], int] = defaultdict(int)
    concept_correct: dict[tuple[str, str], int] = defaultdict(int)
    correct_dates: set[datetime.date] = set()

    for event in events:
        track = event["track"]
        if track not in _TRACK_ORDER:
            continue

        question_id = int(event["question_id"])
        is_correct = bool(event["is_correct"])
        submitted_at = event["submitted_at"]

        per_track_attempts[track] += 1
        if is_correct:
            per_track_correct[track] += 1
            per_track_solved_question_ids[track].add(question_id)
            if submitted_at is not None:
                correct_dates.add(submitted_at.date())

        concepts = _CONCEPTS_LOOKUP.get(track, {}).get(question_id, [])
        for concept in concepts:
            key = (track, concept)
            concept_attempts[key] += 1
            if is_correct:
                concept_correct[key] += 1

    medians = _to_median_solve_seconds(events)

    per_track: dict[str, dict[str, Any]] = {}
    for track in _TRACK_ORDER:
        attempts = per_track_attempts.get(track, 0)
        correct = per_track_correct.get(track, 0)
        accuracy = (correct / attempts) if attempts else 0.0
        per_track[track] = {
            "solve_count": len(per_track_solved_question_ids.get(track, set())),
            "median_solve_seconds": medians.get(track),
            "accuracy_pct": round(accuracy, 3),
        }

    weakest_concepts: list[dict[str, Any]] = []
    for (track, concept), attempts in concept_attempts.items():
        if attempts < 3:
            continue
        correct = concept_correct.get((track, concept), 0)
        weakest_concepts.append(
            {
                "concept": concept,
                "track": track,
                "attempts": attempts,
                "correct": correct,
                "accuracy_pct": round(correct / attempts, 3),
            }
        )

    weakest_concepts.sort(
        key=lambda item: (item["accuracy_pct"], -item["attempts"], item["concept"])
    )

    # Attach recommended path for each weak concept where one exists and is accessible
    for entry in weakest_concepts[:3]:
        lookup = _CONCEPT_PATH_INDEX.get((entry["track"], entry["concept"]))
        if lookup:
            slug, title, tier = lookup
            if tier == "free" or effective_plan in ("pro", "elite"):
                entry["recommended_path_slug"] = slug
                entry["recommended_path_title"] = title

    payload = {
        "per_track": per_track,
        "weakest_concepts": weakest_concepts[:3],
        "cross_track_insight": _build_cross_track_insight(per_track),
        "streak_days": _compute_streak_days(correct_dates),
    }

    _cache_set(user_id, payload)
    return payload
