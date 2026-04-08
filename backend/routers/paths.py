"""Learning paths API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends

from deps import get_current_user
from path_loader import get_all_paths, get_path
from progress import get_solved_question_ids
from questions import get_question, get_questions_by_difficulty
from unlock import compute_unlock_state

router = APIRouter()


@router.get("/api/paths")
async def list_paths(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    """Return all paths with per-user progress counts."""
    paths = get_all_paths()
    solved_ids = await get_solved_question_ids(current_user["id"])

    result = []
    for path in paths:
        question_ids = path["questions"]
        solved_count = sum(1 for qid in question_ids if int(qid) in solved_ids)
        result.append(
            {
                "slug": path["slug"],
                "title": path["title"],
                "description": path["description"],
                "topic": path["topic"],
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Path not found")

    solved_ids = await get_solved_question_ids(current_user["id"])
    grouped = get_questions_by_difficulty()
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped)

    questions_payload = []
    for qid in path["questions"]:
        q = get_question(int(qid))
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

    return {
        "slug": path["slug"],
        "title": path["title"],
        "description": path["description"],
        "topic": path["topic"],
        "question_count": len(questions_payload),
        "solved_count": solved_count,
        "questions": questions_payload,
    }
