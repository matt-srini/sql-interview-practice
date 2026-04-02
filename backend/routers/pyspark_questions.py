import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

import pyspark_questions as catalog
from db import get_solved_ids, mark_solved, record_submission
from deps import get_current_user
from middleware.request_context import get_request_id
from models import PySparkSubmitRequest
from unlock import compute_unlock_state, get_next_questions

router = APIRouter(prefix="/api/pyspark")

logger = logging.getLogger(__name__)


async def _get_pyspark_unlock_state(
    current_user: dict[str, Any],
) -> tuple[dict[int, str], dict[str, int | None]]:
    grouped = catalog.get_questions_by_difficulty()
    solved_ids = await get_solved_ids(current_user["id"], topic="pyspark")
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped)
    next_questions = get_next_questions(unlock_state, grouped)
    return unlock_state, next_questions


@router.get("/catalog")
async def get_pyspark_catalog(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    grouped = catalog.get_questions_by_difficulty()
    solved_ids = await get_solved_ids(current_user["id"], topic="pyspark")
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


@router.get("/questions/{question_id}")
async def get_pyspark_question_detail(
    question_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    q = catalog.get_question(question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    unlock_state, next_questions = await _get_pyspark_unlock_state(current_user)
    state = unlock_state.get(int(q["id"]), "locked")
    if state == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    unlocked = state != "locked"
    is_next = state == "unlocked" and next_questions.get(q["difficulty"]) == int(q["id"])

    payload = {
        **catalog.get_public_question(q),
        "progress": {
            "state": state,
            "is_next": is_next,
            "unlocked": unlocked,
        },
    }
    return payload


@router.post("/submit")
async def submit_pyspark_answer(
    body: PySparkSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /api/pyspark/submit: user_id=%s question_id=%s",
        request_id,
        current_user["id"],
        body.question_id,
    )
    q = catalog.get_question(body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    unlock_state, _ = await _get_pyspark_unlock_state(current_user)
    if unlock_state.get(int(q["id"]), "locked") == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    correct = body.selected_option == q["correct_option"]

    if correct:
        await mark_solved(current_user["id"], int(q["id"]), topic="pyspark")

    await record_submission(
        user_id=current_user["id"],
        track="pyspark",
        question_id=int(body.question_id),
        is_correct=correct,
        code=None,
    )

    return {
        "correct": correct,
        "explanation": q.get("explanation", ""),
    }
