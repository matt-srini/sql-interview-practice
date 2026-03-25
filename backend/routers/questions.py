import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from deps import RunQueryRequest, SubmitRequest, _get_progress_snapshot, _question_detail_payload
from deps import get_current_user
from evaluator import evaluate, run_query
from middleware.request_context import get_request_id
from progress import mark_question_solved
from questions import get_all_questions, get_question

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/questions")
@router.get("/api/questions")
def list_questions() -> list[dict[str, Any]]:
    return get_all_questions()


@router.get("/questions/{question_id}")
@router.get("/api/questions/{question_id}")
async def get_question_detail(
    question_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    question = get_question(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    _, _, unlock_state, next_questions = await _get_progress_snapshot(current_user)
    state = unlock_state[int(question["id"])]
    unlocked = state != "locked"
    is_next = state == "unlocked" and next_questions.get(question["difficulty"]) == int(question["id"])

    if not unlocked:
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    return _question_detail_payload(question, state, unlocked=unlocked, is_next=is_next)


@router.post("/run-query")
@router.post("/api/run-query")
async def run_query_endpoint(
    body: RunQueryRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /run-query: user_id=%s question_id=%s",
        request_id,
        current_user["id"],
        body.question_id,
    )
    question = get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    _, _, unlock_state, _ = await _get_progress_snapshot(current_user)
    if unlock_state[int(question["id"])] == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    return run_query(body.query, question)


@router.post("/submit")
@router.post("/api/submit")
async def submit_answer(
    body: SubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] /submit: user_id=%s question_id=%s",
        request_id,
        current_user["id"],
        body.question_id,
    )
    question = get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    _, _, unlock_state, _ = await _get_progress_snapshot(current_user)
    if unlock_state[int(question["id"])] == "locked":
        raise HTTPException(status_code=403, detail="Question is locked for your current plan or progress.")

    result = evaluate(body.query, question["expected_query"], question)
    accepted = bool(result.get("correct")) and bool(result.get("structure_correct", True))

    if accepted:
        await mark_question_solved(current_user["id"], int(question["id"]))

    return {
        **result,
        "correct": accepted,
        "is_result_correct": bool(result.get("correct")),
        "structure_correct": bool(result.get("structure_correct", True)),
        "solution_query": question["solution_query"],
        "explanation": question["explanation"],
    }
