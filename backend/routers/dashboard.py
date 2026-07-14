import logging
from typing import Any

from fastapi import APIRouter, Depends

from tracks import TRACKS
from db import get_recent_activity, get_solved_ids
from deps import get_current_user, require_authenticated_user
from middleware.request_context import get_request_id

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

# Derived from the TRACKS registry — the single SoT for the track list. A new track
# appears here automatically; no per-router edit needed.
_TOPIC_MODULES = {t.slug: t.catalog_module for t in TRACKS}


def _build_index(module: Any) -> dict[int, dict[str, Any]]:
    """Return a question id → question dict mapping for a catalog module."""
    return {int(q["id"]): q for q in module.get_all_questions()}


def _solved_by_difficulty(
    solved_ids: set[int],
    grouped: dict[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int]]:
    return {
        diff: {
            "solved": sum(1 for q in qs if int(q["id"]) in solved_ids),
            "total": len(qs),
        }
        for diff, qs in grouped.items()
    }


@router.get("/dashboard")
async def get_dashboard(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /api/dashboard: user_id=%s",
        request_id,
        current_user["id"],
    )

    user_id = current_user["id"]

    # Gather solved IDs for each topic
    topic_solved: dict[str, set[int]] = {}
    for topic in _TOPIC_MODULES:
        topic_solved[topic] = await get_solved_ids(user_id, topic=topic)

    # Build per-track summary
    tracks: dict[str, Any] = {}
    concepts_by_track: dict[str, list[str]] = {}

    for topic, module in _TOPIC_MODULES.items():
        grouped = module.get_questions_by_difficulty()
        solved_ids = topic_solved[topic]

        total = sum(len(qs) for qs in grouped.values())
        solved_count = sum(1 for qid in solved_ids if any(
            int(q["id"]) == qid
            for qs in grouped.values()
            for q in qs
        ))

        tracks[topic] = {
            "solved": solved_count,
            "total": total,
            "by_difficulty": _solved_by_difficulty(solved_ids, grouped),
        }

        # Collect concepts for solved questions
        all_questions_flat = [q for qs in grouped.values() for q in qs]
        solved_concepts: list[str] = []
        seen_concepts: set[str] = set()
        for q in all_questions_flat:
            if int(q["id"]) in solved_ids:
                for concept in q.get("concepts", []):
                    if concept not in seen_concepts:
                        seen_concepts.add(concept)
                        solved_concepts.append(concept)

        if solved_concepts:
            concepts_by_track[topic] = solved_concepts

    # Build recent activity with title/difficulty enrichment.
    #
    # recent_activity is a PRACTICE-scoped surface: both consumers (the landing
    # "Resume" card and the dashboard feed) deep-link each row into
    # /practice/<topic>/questions/<id>. But user_progress also holds mock-only
    # solves — mock submit calls mark_solved() for every accepted answer,
    # mock-only questions included — and practice rejects those ("Question not
    # available in practice mode"). So intersect with the practice catalog here,
    # exactly as the solve-count / readiness / drill reads already do (see
    # docs/decisions/DECISIONS.md). get_question() resolves mock-only IDs too
    # (its index spans the full bank), so the q.get("mock_only") check is what
    # excludes them. Over-fetch so a recent burst of mock solves can't starve
    # the feed, then cap at the display limit.
    _RECENT_LIMIT = 10
    raw_activity = await get_recent_activity(user_id, limit=_RECENT_LIMIT * 4)
    recent_activity: list[dict[str, Any]] = []
    for row in raw_activity:
        topic = row.get("topic", "sql")
        module = _TOPIC_MODULES.get(topic)
        if module is None:
            continue
        q = module.get_question(row["question_id"])
        # Skip unknown IDs and mock-only questions — neither is reachable in
        # practice, so deep-linking either is a guaranteed dead-end.
        if q is None or q.get("mock_only"):
            continue
        recent_activity.append(
            {
                "topic": topic,
                "question_id": row["question_id"],
                "title": q.get("title"),
                "difficulty": q.get("difficulty"),
                "solved_at": row.get("solved_at"),
            }
        )
        if len(recent_activity) >= _RECENT_LIMIT:
            break

    return {
        "tracks": tracks,
        "concepts_by_track": concepts_by_track,
        "recent_activity": recent_activity,
    }


@router.get("/progress/solved-total")
async def get_solved_total(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    total = 0
    for topic, module in _TOPIC_MODULES.items():
        solved_ids = await get_solved_ids(current_user["id"], topic=topic)
        catalog_ids = {
            int(q["id"])
            for qs in module.get_questions_by_difficulty().values()
            for q in qs
        }
        total += len(solved_ids & catalog_ids)
    return {"total": total}
