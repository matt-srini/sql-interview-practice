"""Learning paths API endpoints — multi-track aware."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import data_engineering_questions as de_mod
import data_modeling_questions as dm_mod
import experimentation_questions as exp_mod
import ml_fundamentals_questions as ml_mod
import python_data_questions as pandas_mod
import python_questions as python_mod
import pyspark_questions as pyspark_mod
import questions as sql_mod
import statistics_questions as stats_mod
from db import get_solved_ids
from deps import get_current_user
from path_loader import get_all_paths, get_path
from unlock import compute_unlock_state, get_unlock_hint, normalize_plan

router = APIRouter()

# Map topic slug → question module
_TOPIC_MOD = {
    "sql": sql_mod,
    "python": python_mod,
    "python-data": pandas_mod,
    "pyspark": pyspark_mod,
    "data-engineering": de_mod,
    "data-modeling": dm_mod,
    "statistics": stats_mod,
    "ml-fundamentals": ml_mod,
    "experimentation": exp_mod,
}

# Map topic slug → db topic string used in user_progress
_TOPIC_DB = {
    "sql": "sql",
    "python": "python",
    "python-data": "python-data",
    "pyspark": "pyspark",
    "data-engineering": "data-engineering",
    "data-modeling": "data-modeling",
    "statistics": "statistics",
    "ml-fundamentals": "ml-fundamentals",
    "experimentation": "experimentation",
}


async def _solved_for_topic(user_id: str, topic: str) -> set[int]:
    db_topic = _TOPIC_DB.get(topic, topic)
    return await get_solved_ids(user_id, db_topic)


def _can_access_path(path: dict, user_plan: str) -> bool:
    """Free users can only access paths with tier='free'."""
    effective_plan = normalize_plan(user_plan)
    if effective_plan in ("pro", "elite"):
        return True
    return path.get("tier", "pro") == "free"


@router.get("/api/paths")
async def list_paths(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Return all paths with per-user progress counts and tier/access info."""
    paths = get_all_paths()
    user_plan = current_user.get("plan", "free")

    # Fetch solved IDs for all topics we'll need (deduplicated)
    topics_needed = {p["topic"] for p in paths}
    solved_by_topic: dict[str, set[int]] = {}
    for topic in topics_needed:
        solved_by_topic[topic] = await _solved_for_topic(current_user["id"], topic)

    result = []
    for path in paths:
        solved_ids = solved_by_topic[path["topic"]]
        question_ids = path["questions"]
        solved_count = sum(1 for qid in question_ids if int(qid) in solved_ids)
        accessible = _can_access_path(path, user_plan)
        result.append(
            {
                "slug": path["slug"],
                "title": path["title"],
                "description": path["description"],
                "topic": path["topic"],
                "tier": path.get("tier", "pro"),
                "level": path.get("level", "advanced"),
                "focus_concepts": path.get("focus_concepts", []),
                "outcomes": path.get("outcomes", ""),
                "recommended_after": path.get("recommended_after", []),
                "question_count": len(question_ids),
                "solved_count": solved_count if accessible else 0,
                "accessible": accessible,
            }
        )
    return result


@router.get("/api/paths/{slug}")
async def get_path_detail(
    slug: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Return path detail with per-question unlock state."""
    path = get_path(slug)
    if path is None:
        raise HTTPException(status_code=404, detail="Path not found")

    user_plan = current_user.get("plan", "free")
    topic = path["topic"]
    mod = _TOPIC_MOD.get(topic)
    if mod is None:
        raise HTTPException(status_code=400, detail=f"Unknown topic: {topic}")

    # Gate Pro paths for Free users
    if not _can_access_path(path, user_plan):
        # Return a limited view: overview + first 2 questions as preview, rest locked
        preview_ids = path["questions"][:2]
        questions_payload = []
        for i, qid in enumerate(path["questions"]):
            q = mod.get_question(int(qid))
            if q is None:
                continue
            questions_payload.append(
                {
                    "id": q["id"],
                    "title": q["title"],
                    "difficulty": q["difficulty"],
                    "order": q["order"],
                    "state": "unlocked" if qid in preview_ids else "locked",
                }
            )
        return {
            "slug": path["slug"],
            "title": path["title"],
            "description": path["description"],
            "topic": path["topic"],
            "tier": path.get("tier", "pro"),
            "level": path.get("level", "advanced"),
            "focus_concepts": path.get("focus_concepts", []),
            "outcomes": path.get("outcomes", ""),
            "recommended_after": path.get("recommended_after", []),
            "accessible": False,
            "question_count": len(questions_payload),
            "solved_count": 0,
            "questions": questions_payload,
            "unlock_hint": None,
        }

    # Full access — compute unlock state
    solved_ids = await _solved_for_topic(current_user["id"], topic)
    grouped = mod.get_questions_by_difficulty()

    unlock_state = compute_unlock_state(user_plan, solved_ids, grouped, track=topic)

    questions_payload = []
    for qid in path["questions"]:
        q = mod.get_question(int(qid))
        if q is None:
            continue
        state = unlock_state.get(int(qid), "locked")
        questions_payload.append(
            {
                "id": q["id"],
                "title": q["title"],
                "difficulty": q["difficulty"],
                "order": q["order"],
                "state": state,
            }
        )

    solved_count = sum(1 for item in questions_payload if item["state"] == "solved")
    completed = solved_count == len(questions_payload) and len(questions_payload) > 0
    unlock_hint = get_unlock_hint(user_plan, solved_ids, grouped, track=topic)

    return {
        "slug": path["slug"],
        "title": path["title"],
        "description": path["description"],
        "topic": path["topic"],
        "tier": path.get("tier", "pro"),
        "level": path.get("level", "advanced"),
        "focus_concepts": path.get("focus_concepts", []),
        "outcomes": path.get("outcomes", ""),
        "recommended_after": path.get("recommended_after", []),
        "accessible": True,
        "question_count": len(questions_payload),
        "solved_count": solved_count,
        "completed": completed,
        "unlock_hint": unlock_hint,
        "questions": questions_payload,
    }
