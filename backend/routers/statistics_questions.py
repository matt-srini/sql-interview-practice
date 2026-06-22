import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import python_guard
import python_evaluator
import statistics_questions as catalog
from db import get_solved_ids, mark_solved, record_submission
from deps import get_current_user
from offload import run_blocking_exec
from mcq import is_mcq_correct
from middleware.request_context import get_request_id
from unlock import compute_unlock_state, get_next_questions

router = APIRouter(prefix="/api/statistics")

logger = logging.getLogger(__name__)


class StatisticsRunCodeRequest(BaseModel):
    code: str
    question_id: int


class StatisticsSubmitRequest(BaseModel):
    question_id: int
    selected_option: Optional[int] = None
    code: Optional[str] = None
    duration_ms: Optional[int] = None


async def _get_stats_unlock_state(
    current_user: dict[str, Any],
) -> tuple[dict[int, str], dict[str, int | None]]:
    grouped = catalog.get_questions_by_difficulty()
    solved_ids = await get_solved_ids(current_user["id"], topic="statistics")
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped, track="statistics")
    next_questions = get_next_questions(unlock_state, grouped)
    return unlock_state, next_questions


@router.get("/catalog")
async def get_statistics_catalog(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    grouped = catalog.get_questions_by_difficulty()
    solved_ids = await get_solved_ids(current_user["id"], topic="statistics")
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped, track="statistics")
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
                    "type": q["type"],
                    "subtype": q["subtype"],
                    "interaction_mode": q.get("interaction_mode"),
                    "state": state,
                    "is_next": state == "unlocked" and next_questions[difficulty] == question_id,
                    "concepts": q.get("concepts", []),
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
async def get_statistics_question_detail(
    question_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    q = catalog.get_question(question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    unlock_state, next_questions = await _get_stats_unlock_state(current_user)
    state = unlock_state.get(int(q["id"]), "locked")
    unlocked = state != "locked"
    is_next = state == "unlocked" and next_questions.get(q["difficulty"]) == int(q["id"])

    if not unlocked:
        public = catalog.get_public_question(q)
        locked_payload: dict[str, Any] = {
            "id": public["id"],
            "order": public["order"],
            "title": public["title"],
            "description": public["description"],
            "difficulty": public["difficulty"],
            "type": public["type"],
            "subtype": public["subtype"],
            "interaction_mode": public.get("interaction_mode"),
            "hints": public.get("hints", []),
            "concepts": public.get("concepts", []),
            "locked": True,
            "progress": {"state": state, "is_next": is_next, "unlocked": False},
        }
        return locked_payload

    payload = {
        **catalog.get_public_question(q),
        "progress": {
            "state": state,
            "is_next": is_next,
            "unlocked": unlocked,
        },
    }
    return payload


@router.post("/run-code")
async def run_statistics_code(
    body: StatisticsRunCodeRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /api/statistics/run-code: user_id=%s question_id=%s",
        request_id,
        current_user["id"],
        body.question_id,
    )
    q = catalog.get_question(body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    if q["subtype"] == "conceptual":
        raise HTTPException(status_code=400, detail="Run code is not supported for conceptual (MCQ) questions.")

    unlock_state, _ = await _get_stats_unlock_state(current_user)
    if unlock_state.get(int(q["id"]), "locked") == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    if detail := python_guard.guard_detail(body.code, "statistics"):
        raise HTTPException(status_code=400, detail=detail)

    return await run_blocking_exec(python_evaluator.run_python_code, body.code, q)


@router.post("/submit")
async def submit_statistics_answer(
    body: StatisticsSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /api/statistics/submit: user_id=%s question_id=%s",
        request_id,
        current_user["id"],
        body.question_id,
    )
    q = catalog.get_question(body.question_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Question not found")

    unlock_state, _ = await _get_stats_unlock_state(current_user)
    if unlock_state.get(int(q["id"]), "locked") == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    subtype = q["subtype"]

    if subtype == "conceptual":
        if body.selected_option is None:
            raise HTTPException(status_code=422, detail="selected_option is required for conceptual questions.")
        correct = is_mcq_correct(body.selected_option, q)
        if correct:
            await mark_solved(current_user["id"], int(q["id"]), topic="statistics")
        await record_submission(
            user_id=current_user["id"],
            track="statistics",
            question_id=int(body.question_id),
            is_correct=correct,
            code=None,
            duration_ms=body.duration_ms,
        )
        return {
            "correct": correct,
            "subtype": subtype,
            "explanation": q.get("explanation", ""),
        }

    # numerical
    if not body.code:
        raise HTTPException(status_code=422, detail="code is required for numerical questions.")
    if detail := python_guard.guard_detail(body.code, "statistics"):
        raise HTTPException(status_code=400, detail=detail)
    result = await run_blocking_exec(python_evaluator.evaluate_python_code, body.code, q)
    correct = bool(result.get("correct"))
    if correct:
        await mark_solved(current_user["id"], int(q["id"]), topic="statistics")
    await record_submission(
        user_id=current_user["id"],
        track="statistics",
        question_id=int(body.question_id),
        is_correct=correct,
        code=body.code,
        duration_ms=body.duration_ms,
    )
    if correct:
        result["solution_code"] = q.get("expected_code", "")
        result["explanation"] = q.get("explanation", "")
    result["subtype"] = subtype
    return result
