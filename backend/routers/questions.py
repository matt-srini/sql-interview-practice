import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from deps import (
    RunQueryRequest,
    SubmitRequest,
    _get_progress_snapshot,
    _question_detail_payload,
    get_user_id,
)
from evaluator import evaluate, run_query
from middleware.request_context import get_request_id
from progress import get_solved_question_ids, is_unlocked_for_user, mark_question_solved
from questions import get_all_questions, get_question, get_questions_by_difficulty

router = APIRouter()


logger = logging.getLogger(__name__)


@router.get("/questions")
@router.get("/api/questions")
def list_questions() -> list[dict[str, Any]]:
    return get_all_questions()


@router.get("/questions/{question_id}")
@router.get("/api/questions/{question_id}")
def get_question_detail(
    question_id: int,
    response: Response,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    question = get_question(question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    grouped, solved_ids, statuses = _get_progress_snapshot(user_id)
    unlocked = is_unlocked_for_user(question=question, questions_by_difficulty=grouped, solved_ids=solved_ids)
    status = statuses[int(question["id"])]

    if not unlocked and int(question["id"]) not in solved_ids:
        raise HTTPException(status_code=403, detail="Question is locked. Solve previous questions first.")

    return _question_detail_payload(question, status, unlocked=unlocked)


@router.post("/run-query")
@router.post("/api/run-query")
def run_query_endpoint(
    body: RunQueryRequest,
    response: Response,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%s/run-query: user_id=%s question_id=%s",
        prefix,
        user_id,
        body.question_id,
    )
    question = get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    grouped = get_questions_by_difficulty()
    solved_ids = get_solved_question_ids(user_id)
    if not is_unlocked_for_user(question=question, questions_by_difficulty=grouped, solved_ids=solved_ids):
        raise HTTPException(status_code=403, detail="Question is locked. Solve previous questions first.")

    return run_query(body.query, question)


@router.post("/submit")
@router.post("/api/submit")
def submit_answer(
    body: SubmitRequest,
    response: Response,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%s/submit: user_id=%s question_id=%s",
        prefix,
        user_id,
        body.question_id,
    )
    question = get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    grouped = get_questions_by_difficulty()
    solved_ids = get_solved_question_ids(user_id)
    if not is_unlocked_for_user(question=question, questions_by_difficulty=grouped, solved_ids=solved_ids):
        raise HTTPException(status_code=403, detail="Question is locked. Solve previous questions first.")

    result = evaluate(body.query, question["expected_query"], question)

    if result.get("correct") is True:
        mark_question_solved(user_id, int(question["id"]))

    return {
        **result,
        "solution_query": question["solution_query"],
        "explanation": question["explanation"],
    }
