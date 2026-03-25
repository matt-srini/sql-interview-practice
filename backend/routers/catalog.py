from typing import Any

from fastapi import APIRouter, Depends

from deps import get_current_user
from progress import get_solved_question_ids
from questions import get_questions_by_difficulty
from unlock import compute_unlock_state, get_next_questions

router = APIRouter()


@router.get("/catalog")
@router.get("/api/catalog")
async def get_catalog(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    grouped = get_questions_by_difficulty()
    solved_ids = await get_solved_question_ids(current_user["id"])
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped)
    next_questions = get_next_questions(unlock_state, grouped)

    groups_payload = []
    for difficulty in ["easy", "medium", "hard"]:
        questions = []
        for q in grouped[difficulty]:
            question_id = int(q["id"])
            state = unlock_state[question_id]
            questions.append(
                {
                    "id": q["id"],
                    "title": q["title"],
                    "difficulty": q["difficulty"],
                    "order": q["order"],
                    "state": state,
                    "is_next": state == "unlocked" and next_questions[difficulty] == question_id,
                }
            )
        groups_payload.append(
            {
                "difficulty": difficulty,
                "questions": questions,
                "counts": {
                    "total": len(questions),
                    "solved": sum(1 for x in questions if x["state"] == "solved"),
                    "unlocked": sum(1 for x in questions if x["state"] != "locked"),
                },
            }
        )

    return {"user_id": current_user["id"], "groups": groups_payload}
