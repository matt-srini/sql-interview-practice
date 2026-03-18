import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response

from deps import RunQueryRequest, SubmitRequest, _validate_difficulty, get_user_id
from evaluator import evaluate, run_query
from middleware.request_context import get_request_id
from progress import clear_seen_sample_ids, get_seen_sample_ids, mark_sample_seen
from questions import get_public_question
from sample_questions import get_sample_question, get_sample_questions_by_difficulty

router = APIRouter(prefix="/api/sample")


logger = logging.getLogger(__name__)


@router.get("/{difficulty}")
def get_sample_question_by_difficulty(
    difficulty: str,
    response: Response,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%sGet sample question: user_id=%s difficulty=%s",
        prefix,
        user_id,
        difficulty,
    )
    normalized = _validate_difficulty(difficulty)
    grouped = get_sample_questions_by_difficulty()
    pool = grouped.get(normalized, [])
    if not pool:
        raise HTTPException(status_code=404, detail="Sample questions not found")

    seen_ids = get_seen_sample_ids(user_id, normalized)
    next_unseen = next((q for q in pool if int(q["id"]) not in seen_ids), None)
    if next_unseen is None:
        raise HTTPException(status_code=409, detail="All sample questions exhausted for this difficulty.")

    mark_sample_seen(user_id, normalized, int(next_unseen["id"]))
    seen_count = len(seen_ids) + 1
    remaining_count = max(len(pool) - seen_count, 0)

    return {
        **get_public_question(next_unseen),
        "progress": {
            "state": "unlocked",
            "is_next": False,
            "unlocked": True,
            "mode": "sample",
        },
        "sample": {
            "difficulty": normalized,
            "shown_count": seen_count,
            "total": len(pool),
            "remaining": remaining_count,
            "exhausted": remaining_count == 0,
        },
    }


@router.post("/{difficulty}/reset")
def reset_sample_progress_for_difficulty(
    difficulty: str,
    response: Response,
    user_id: str = Depends(get_user_id),
) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%sReset sample progress: user_id=%s difficulty=%s",
        prefix,
        user_id,
        difficulty,
    )
    normalized = _validate_difficulty(difficulty)
    clear_seen_sample_ids(user_id, normalized)
    return {
        "difficulty": normalized,
        "reset": True,
    }


@router.post("/run-query")
def run_sample_query(body: RunQueryRequest) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%sSample /run-query: question_id=%s",
        prefix,
        body.question_id,
    )
    question = get_sample_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    return run_query(body.query, question)


@router.post("/submit")
def submit_sample_answer(body: SubmitRequest) -> dict[str, Any]:
    request_id = get_request_id()
    prefix = f"[request_id={request_id}] "
    logger.info(
        "%sSample /submit: question_id=%s",
        prefix,
        body.question_id,
    )
    question = get_sample_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    result = evaluate(body.query, question["expected_query"], question)

    return {
        **result,
        "solution_query": question["solution_query"],
        "explanation": question["explanation"],
    }
