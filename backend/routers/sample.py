import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

import python_evaluator
import python_guard
from deps import RunQueryRequest, SubmitRequest, _validate_difficulty, get_current_user
from evaluator import evaluate, run_query
from middleware.request_context import get_request_id
from progress import (
    clear_seen_sample_ids,
    get_seen_sample_counts,
    get_seen_sample_ids,
    mark_sample_seen,
)
from sample_questions import (
    get_sample_catalog_shape,
    get_sample_question,
    get_sample_question_for_topic,
    get_topic_sample_pool,
    normalize_sample_topic,
)
from tracks import get_track_by_db_topic

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
    return get_track_by_db_topic(topic).slug


def _validate_topic(topic: str) -> str:
    try:
        return normalize_sample_topic(topic)
    except ValueError:
        raise HTTPException(status_code=404, detail="Topic not found")


def _public_question_for_topic(question: dict[str, Any], topic: str) -> dict[str, Any]:
    return get_track_by_db_topic(topic).catalog_module.get_public_question(question)


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


@router.get("/summary")
async def get_sample_summary(
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Per-(track, difficulty) sample pool sizes and how many the user has tried.

    Powers the Sample Hub tile UI. Anonymous-but-tracked users (real user rows
    without an email) also get a real count — anonymous-first identity already
    persists `user_sample_seen` rows for them.

    Response:
        {
          "tracks": {
            "<api_slug>": {
              "<difficulty>": { "total": int, "tried": int }
            }
          }
        }
    """
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Sample /summary: user_id=%s",
        request_id,
        current_user["id"],
    )

    shape = get_sample_catalog_shape()  # {db_topic: {diff: total}}
    seen_counts = await get_seen_sample_counts(current_user["id"])  # {(db_topic, diff): tried}

    tracks: dict[str, dict[str, dict[str, int]]] = {}
    for db_topic, by_diff in shape.items():
        api_slug = _topic_api_slug(db_topic)
        tracks[api_slug] = {}
        for diff, total in by_diff.items():
            tried = seen_counts.get((db_topic, diff), 0)
            # Clamp tried to total — if pool size ever shrinks below historical
            # seen rows, never show "5/3 tried".
            tried_clamped = min(tried, total)
            tracks[api_slug][diff] = {"total": total, "tried": tried_clamped}
    return {"tracks": tracks}


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


@router.post("/sql/run-query")
def run_sql_sample_query(body: RunQueryRequest) -> dict:
    """Topic-namespaced alias for the SQL sample run-query endpoint."""
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Sample /sql/run-query: question_id=%s",
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

    track = get_track_by_db_topic(normalized_topic)
    eval_kind = track.eval_kind
    if eval_kind in ("sql", "mcq"):
        raise HTTPException(status_code=400, detail="Run endpoint is not supported for this topic.")

    question = get_sample_question_for_topic(body.question_id, normalized_topic)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # mixed (statistics): conceptual questions cannot run code
    if eval_kind == "mixed" and question.get("subtype") == "conceptual":
        raise HTTPException(status_code=400, detail="Run code is not supported for conceptual (MCQ) questions.")

    guard_errors = python_guard.validate_code(body.code, topic=normalized_topic)
    if guard_errors:
        raise HTTPException(
            status_code=400,
            detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
        )

    if eval_kind in ("python", "mixed"):
        return python_evaluator.run_python_code(body.code, question)
    # pandas: run comparison and add test_results
    raw = python_evaluator.run_python_data_code(body.code, question)
    if not raw.get("error"):
        expected_raw = python_evaluator.run_python_data_code(question.get("expected_code", ""), question)
        import pandas as pd
        from evaluator import normalize_dataframe
        try:
            user_df = pd.DataFrame(raw["result"]["rows"]) if raw.get("result") else pd.DataFrame()
            exp_df = pd.DataFrame(expected_raw["result"]["rows"]) if expected_raw.get("result") else pd.DataFrame()
            passed = normalize_dataframe(user_df).equals(normalize_dataframe(exp_df))
        except Exception:
            passed = False
        raw["test_results"] = [{"passed": passed, "actual": raw.get("result"), "expected": expected_raw.get("result")}]
    else:
        raw["test_results"] = [{"passed": False, "error": raw.get("error")}]
    return raw


@router.post("/{topic}/submit")
def submit_topic_sample_answer(topic: str, body: dict[str, Any]) -> dict[str, Any]:
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    logger.info(
        "[request_id=%s] Sample /%s/submit",
        request_id,
        normalized_topic,
    )

    eval_kind = get_track_by_db_topic(normalized_topic).eval_kind

    if eval_kind == "sql":
        parsed = _parse_body(SubmitRequest, body)
        question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        result = evaluate(parsed.query, question["expected_query"], question)
        return {
            **result,
            "solution_query": question["solution_query"],
            "explanation": question["explanation"],
        }

    if eval_kind in ("python", "pandas"):
        parsed = _parse_body(SampleSubmitCodeRequest, body)
        question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        guard_errors = python_guard.validate_code(parsed.code, topic=normalized_topic)
        if guard_errors:
            raise HTTPException(
                status_code=400,
                detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
            )
        if eval_kind == "python":
            result = python_evaluator.evaluate_python_code(parsed.code, question)
        else:
            result = python_evaluator.evaluate_python_data_code(parsed.code, question)
        result["solution_code"] = question.get("expected_code", "")
        result["explanation"] = question.get("explanation", "")
        return result

    # mixed (statistics): dispatch on per-question subtype
    if eval_kind == "mixed":
        subtype = None
        # Peek at question subtype to decide which parser to use
        question_id = body.get("question_id") if isinstance(body, dict) else None
        if question_id:
            _q_peek = get_sample_question_for_topic(question_id, normalized_topic)
            subtype = _q_peek.get("subtype") if _q_peek else None
        if subtype == "numerical":
            parsed = _parse_body(SampleSubmitCodeRequest, body)
            question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
            if question is None:
                raise HTTPException(status_code=404, detail="Question not found")
            guard_errors = python_guard.validate_code(parsed.code, topic=normalized_topic)
            if guard_errors:
                raise HTTPException(
                    status_code=400,
                    detail={"error": "Code contains disallowed constructs.", "guard_errors": guard_errors},
                )
            result = python_evaluator.evaluate_python_code(parsed.code, question)
            result["solution_code"] = question.get("expected_code", "")
            result["explanation"] = question.get("explanation", "")
            result["subtype"] = "numerical"
            return result
        else:  # conceptual
            parsed = _parse_body(SampleSubmitPySparkRequest, body)
            question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
            if question is None:
                raise HTTPException(status_code=404, detail="Question not found")
            correct = parsed.selected_option == question["correct_option"]
            return {
                "correct": correct,
                "subtype": "conceptual",
                "explanation": question.get("explanation", ""),
            }

    # mcq (pyspark and future mcq tracks)
    parsed = _parse_body(SampleSubmitPySparkRequest, body)
    question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    correct = parsed.selected_option == question["correct_option"]
    return {
        "correct": correct,
        "explanation": question.get("explanation", ""),
    }
