import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

import pyspark_questions as pyspark_catalog
import python_data_questions as python_data_catalog
import python_evaluator
import python_guard
import python_questions as python_catalog
from deps import RunQueryRequest, SubmitRequest, _validate_difficulty, get_current_user
from evaluator import evaluate, run_query
from middleware.request_context import get_request_id
from progress import clear_seen_sample_ids, get_seen_sample_ids, mark_sample_seen
from questions import get_public_question
from sample_questions import (
    get_sample_question,
    get_sample_question_for_topic,
    get_topic_sample_pool,
    normalize_sample_topic,
)

router = APIRouter(prefix="/api/sample")

logger = logging.getLogger(__name__)


class SampleRunCodeRequest(BaseModel):
    code: str
    question_id: int


class SampleSubmitCodeRequest(BaseModel):
    code: str
    question_id: int


class SampleSubmitPySparkRequest(BaseModel):
    selected_option: int
    question_id: int


def _topic_api_slug(topic: str) -> str:
    if topic == "python_data":
        return "python-data"
    return topic


def _validate_topic(topic: str) -> str:
    try:
        return normalize_sample_topic(topic)
    except ValueError:
        raise HTTPException(status_code=404, detail="Topic not found")


def _public_question_for_topic(question: dict[str, Any], topic: str) -> dict[str, Any]:
    if topic == "sql":
        return get_public_question(question)
    if topic == "python":
        return python_catalog.get_public_question(question)
    if topic == "python_data":
        return python_data_catalog.get_public_question(question)
    if topic == "pyspark":
        return pyspark_catalog.get_public_question(question)
    raise HTTPException(status_code=404, detail="Topic not found")


def _parse_body(model_cls: type[BaseModel], body: dict[str, Any]) -> BaseModel:
    try:
        return model_cls.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors())


async def _get_sample_question_by_topic_and_difficulty(
    *,
    topic: str,
    difficulty: str,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    normalized_difficulty = _validate_difficulty(difficulty)
    logger.info(
        "[request_id=%s] Get sample question: user_id=%s topic=%s difficulty=%s",
        request_id,
        current_user["id"],
        normalized_topic,
        normalized_difficulty,
    )

    pool, served_difficulty = get_topic_sample_pool(
        topic=normalized_topic,
        difficulty=normalized_difficulty,
    )
    if not pool:
        raise HTTPException(status_code=404, detail="Sample questions not found")

    seen_ids = await get_seen_sample_ids(
        current_user["id"],
        normalized_difficulty,
        topic=normalized_topic,
    )
    next_unseen = next((question for question in pool if int(question["id"]) not in seen_ids), None)
    if next_unseen is None:
        raise HTTPException(status_code=409, detail="All sample questions exhausted for this topic and difficulty.")

    await mark_sample_seen(
        current_user["id"],
        normalized_difficulty,
        int(next_unseen["id"]),
        topic=normalized_topic,
    )
    seen_in_pool_before = sum(1 for question in pool if int(question["id"]) in seen_ids)
    seen_count = seen_in_pool_before + 1
    remaining_count = max(len(pool) - seen_count, 0)

    public_question = _public_question_for_topic(next_unseen, normalized_topic)
    public_question["difficulty"] = normalized_difficulty

    return {
        **public_question,
        "progress": {
            "state": "unlocked",
            "is_next": False,
            "unlocked": True,
            "mode": "sample",
        },
        "sample": {
            "topic": _topic_api_slug(normalized_topic),
            "difficulty": normalized_difficulty,
            "served_difficulty": served_difficulty,
            "shown_count": seen_count,
            "total": len(pool),
            "remaining": remaining_count,
            "exhausted": remaining_count == 0,
        },
    }


@router.get("/{difficulty}")
async def get_sql_sample_question_by_difficulty(
    difficulty: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return await _get_sample_question_by_topic_and_difficulty(
        topic="sql",
        difficulty=difficulty,
        current_user=current_user,
    )


@router.get("/{topic}/{difficulty}")
async def get_topic_sample_question_by_difficulty(
    topic: str,
    difficulty: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    return await _get_sample_question_by_topic_and_difficulty(
        topic=topic,
        difficulty=difficulty,
        current_user=current_user,
    )


@router.post("/{difficulty}/reset")
async def reset_sql_sample_progress_for_difficulty(
    difficulty: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, object]:
    return await reset_topic_sample_progress_for_difficulty("sql", difficulty, current_user)


@router.post("/{topic}/{difficulty}/reset")
async def reset_topic_sample_progress_for_difficulty(
    topic: str,
    difficulty: str,
    current_user: dict = Depends(get_current_user),
) -> dict[str, object]:
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    normalized_difficulty = _validate_difficulty(difficulty)
    logger.info(
        "[request_id=%s] Reset sample progress: user_id=%s topic=%s difficulty=%s",
        request_id,
        current_user["id"],
        normalized_topic,
        normalized_difficulty,
    )
    await clear_seen_sample_ids(current_user["id"], normalized_difficulty, topic=normalized_topic)
    return {
        "topic": _topic_api_slug(normalized_topic),
        "difficulty": normalized_difficulty,
        "reset": True,
    }


@router.post("/run-query")
def run_sample_query(body: RunQueryRequest) -> dict:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Sample /run-query: question_id=%s",
        request_id,
        body.question_id,
    )
    question = get_sample_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    return run_query(body.query, question)


@router.post("/submit")
def submit_sample_answer(body: SubmitRequest) -> dict:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Sample /submit: question_id=%s",
        request_id,
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


@router.post("/{topic}/run-code")
def run_topic_sample_code(topic: str, body: SampleRunCodeRequest) -> dict[str, Any]:
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    logger.info(
        "[request_id=%s] Sample /%s/run-code: question_id=%s",
        request_id,
        normalized_topic,
        body.question_id,
    )

    if normalized_topic == "sql" or normalized_topic == "pyspark":
        raise HTTPException(status_code=400, detail="Run endpoint is not supported for this topic.")

    question = get_sample_question_for_topic(body.question_id, normalized_topic)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    guard_topic = "python_data" if normalized_topic == "python_data" else "python"
    guard_errors = python_guard.validate_code(body.code, topic=guard_topic)
    if guard_errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
        )

    if normalized_topic == "python":
        return python_evaluator.run_python_code(body.code, question)
    return python_evaluator.run_python_data_code(body.code, question)


@router.post("/{topic}/submit")
def submit_topic_sample_answer(topic: str, body: dict[str, Any]) -> dict[str, Any]:
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    logger.info(
        "[request_id=%s] Sample /%s/submit",
        request_id,
        normalized_topic,
    )

    if normalized_topic == "sql":
        parsed = _parse_body(SubmitRequest, body)
        question = get_sample_question_for_topic(parsed.question_id, "sql")
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        result = evaluate(parsed.query, question["expected_query"], question)
        return {
            **result,
            "solution_query": question["solution_query"],
            "explanation": question["explanation"],
        }

    if normalized_topic == "python":
        parsed = _parse_body(SampleSubmitCodeRequest, body)
        question = get_sample_question_for_topic(parsed.question_id, "python")
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        guard_errors = python_guard.validate_code(parsed.code, topic="python")
        if guard_errors:
            raise HTTPException(
                status_code=400,
                detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
            )
        result = python_evaluator.evaluate_python_code(parsed.code, question)
        if result.get("correct"):
            result["solution_code"] = question.get("expected_code", "")
            result["explanation"] = question.get("explanation", "")
        return result

    if normalized_topic == "python_data":
        parsed = _parse_body(SampleSubmitCodeRequest, body)
        question = get_sample_question_for_topic(parsed.question_id, "python_data")
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        guard_errors = python_guard.validate_code(parsed.code, topic="python_data")
        if guard_errors:
            raise HTTPException(
                status_code=400,
                detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
            )
        result = python_evaluator.evaluate_python_data_code(parsed.code, question)
        if result.get("correct"):
            result["solution_code"] = question.get("expected_code", "")
            result["explanation"] = question.get("explanation", "")
        return result

    parsed = _parse_body(SampleSubmitPySparkRequest, body)
    question = get_sample_question_for_topic(parsed.question_id, "pyspark")
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    correct = parsed.selected_option == question["correct_option"]
    return {
        "correct": correct,
        "explanation": question.get("explanation", ""),
    }
