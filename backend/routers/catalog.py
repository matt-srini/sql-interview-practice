from typing import Any

from fastapi import APIRouter, Depends, Response

from deps import get_user_id
from progress import compute_statuses, get_solved_question_ids
from questions import get_questions_by_difficulty

router = APIRouter()


@router.get("/catalog")
@router.get("/api/catalog")
def get_catalog(response: Response, user_id: str = Depends(get_user_id)) -> dict[str, Any]:
    grouped = get_questions_by_difficulty()
    solved_ids = get_solved_question_ids(user_id)
    statuses = compute_statuses(questions_by_difficulty=grouped, solved_ids=solved_ids)

    groups_payload = []
    for difficulty in ["easy", "medium", "hard"]:
        questions = []
        for q in grouped[difficulty]:
            st = statuses[int(q["id"])]
            questions.append(
                {
                    "id": q["id"],
                    "title": q["title"],
                    "difficulty": q["difficulty"],
                    "order": q["order"],
                    "state": st.state,
                    "is_next": st.is_next,
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

    return {"user_id": user_id, "groups": groups_payload}
