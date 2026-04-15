import logging
from typing import Any

from fastapi import APIRouter, Depends

import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_questions
from db import get_recent_activity, get_solved_ids
from deps import get_current_user
from middleware.request_context import get_request_id

router = APIRouter(prefix="/api")

logger = logging.getLogger(__name__)

_TOPIC_MODULES = {
    "sql": sql_questions,
    "python": python_questions,
    "python_data": python_data_questions,
    "pyspark": pyspark_questions,
}


def _build_index(module: Any) -> dict[int, dict[str, Any]]:
    """Return a question id → question dict mapping for a catalog module."""
    return {int(q["id"]): q for q in module.get_all_questions()}


def _solved_by_difficulty(
    solved_ids: set[int],
    grouped: dict[str, list[dict[str, Any]]],
) -> dict[str, int]:
    return {
        diff: sum(1 for q in qs if int(q["id"]) in solved_ids)
        for diff, qs in grouped.items()
    }


@router.get("/dashboard")
async def get_dashboard(
    current_user: dict[str, Any] = Depends(get_current_user),
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

    # Build recent activity with title/difficulty enrichment
    raw_activity = await get_recent_activity(user_id, limit=10)
    recent_activity: list[dict[str, Any]] = []
    for row in raw_activity:
        topic = row.get("topic", "sql")
        module = _TOPIC_MODULES.get(topic)
        title = None
        difficulty = None
        if module is not None:
            q = module.get_question(row["question_id"])
            if q is not None:
                title = q.get("title")
                difficulty = q.get("difficulty")
        recent_activity.append(
            {
                "topic": topic,
                "question_id": row["question_id"],
                "title": title,
                "difficulty": difficulty,
                "solved_at": row.get("solved_at"),
            }
        )

    def _remap(d: dict) -> dict:
        """Rename python_data → python-data to match frontend topic slugs."""
        return {("python-data" if k == "python_data" else k): v for k, v in d.items()}

    for row in recent_activity:
        if row["topic"] == "python_data":
            row["topic"] = "python-data"

    return {
        "tracks": _remap(tracks),
        "concepts_by_track": _remap(concepts_by_track),
        "recent_activity": recent_activity,
    }
