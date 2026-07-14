"""Learning paths API endpoints — multi-track aware."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from tracks import TRACKS
from db import get_solved_ids
from deps import get_current_user
from path_loader import get_all_paths, get_path
from unlock import compute_unlock_state

router = APIRouter()

# Map topic slug → question module
# Both derived from the TRACKS registry (single SoT for the track list). A new track
# resolves here automatically — no per-router edit (this is what previously 500'd a
# new track's path detail when the maps were hand-maintained).
_TOPIC_MOD = {t.slug: t.catalog_module for t in TRACKS}
_TOPIC_DB = {t.slug: t.db_topic for t in TRACKS}


async def _solved_for_topic(user_id: str, topic: str) -> set[int]:
    db_topic = _TOPIC_DB.get(topic, topic)
    return await get_solved_ids(user_id, db_topic)


@router.get("/api/paths")
async def list_paths(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Return all paths with per-user progress counts and tier/access info."""
    paths = get_all_paths()

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
        result.append(
            {
                "slug": path["slug"],
                "title": path["title"],
                "description": path["description"],
                "topic": path["topic"],
                "tier": path.get("tier", "pro"),
                "level": path.get("level", "advanced"),
                "display_order": path.get("display_order", 999),
                "focus_concepts": path.get("focus_concepts", []),
                "outcomes": path.get("outcomes", ""),
                "recommended_after": path.get("recommended_after", []),
                "question_count": len(question_ids),
                "solved_count": solved_count,
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

    # Compute unlock state based on plan — free=easy only, pro/elite=all
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
    unlock_hint = None

    return {
        "slug": path["slug"],
        "title": path["title"],
        "description": path["description"],
        "topic": path["topic"],
        "tier": path.get("tier", "pro"),
        "level": path.get("level", "advanced"),
        "display_order": path.get("display_order", 999),
        "focus_concepts": path.get("focus_concepts", []),
        "outcomes": path.get("outcomes", ""),
        "recommended_after": path.get("recommended_after", []),
        "question_count": len(questions_payload),
        "solved_count": solved_count,
        "completed": completed,
        "unlock_hint": unlock_hint,
        "questions": questions_payload,
    }
