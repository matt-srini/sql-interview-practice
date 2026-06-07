import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

import python_evaluator
import python_guard
from deps import RunQueryRequest, SubmitRequest, _validate_difficulty, get_current_user
from mcq import is_mcq_correct
from evaluator import evaluate, run_query
from exceptions import BadRequestError
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
    # Resume-model semantics: GET is read-only. The first unattempted question
    # is returned without marking anything; marking happens on submit (commit)
    # or on the explicit skip endpoint. This means refresh / navigate-back is
    # idempotent — viewing never advances the user's progress.
    next_unseen = next((question for question in pool if int(question["id"]) not in seen_ids), None)
    if next_unseen is None:
        raise HTTPException(status_code=409, detail="All sample questions exhausted for this topic and difficulty.")

    attempted_count = sum(1 for question in pool if int(question["id"]) in seen_ids)
    # 1-indexed position of the returned question within the pool order.
    position = next(
        (i + 1 for i, question in enumerate(pool) if int(question["id"]) == int(next_unseen["id"])),
        1,
    )

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
            "position": position,
            "total": len(pool),
            "attempted": attempted_count,
            # Legacy field names kept for backward compat with SampleQuestionPage
            # status line. `shown_count` is now the position of the current
            # question (1-indexed) and `remaining` is questions left after the
            # user submits the current one.
            "shown_count": position,
            "remaining": max(len(pool) - attempted_count - 1, 0),
            "exhausted": False,
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


async def _mark_sample_attempted(
    current_user: dict[str, Any],
    normalized_topic: str,
    question: dict[str, Any],
) -> None:
    """Record that the user attempted (submitted or skipped) this sample question.

    Resume-model semantics: marking is the side effect of *commitment* — a submit
    or an explicit skip — never a side effect of viewing. Keeping this in one
    place ensures both the submit and skip paths agree on what 'attempted' means.
    """
    await mark_sample_seen(
        current_user["id"],
        str(question["difficulty"]),
        int(question["id"]),
        topic=normalized_topic,
    )


@router.post("/submit")
async def submit_sample_answer(
    body: SubmitRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
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

    await _mark_sample_attempted(current_user, "sql", question)

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
    # pandas: compares against expected on the FULL result; returns a ~200-row preview.
    return python_evaluator.run_python_data_code_checked(body.code, question)


@router.post("/{topic}/{difficulty}/skip")
async def skip_sample_question(
    topic: str,
    difficulty: str,
    body: dict[str, Any],
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Explicitly skip the current sample question without submitting an answer.

    Marks the supplied `question_id` as attempted and returns the next unattempted
    question (same shape as GET). Used by the SampleQuestionPage "Another sample →"
    button so 'I'm moving on without solving this' is an explicit user intent,
    not a silent side effect of a page refresh.
    """
    request_id = get_request_id()
    normalized_topic = _validate_topic(topic)
    normalized_difficulty = _validate_difficulty(difficulty)
    qid_raw = body.get("question_id") if isinstance(body, dict) else None
    if qid_raw is None:
        raise HTTPException(status_code=422, detail="question_id is required")
    try:
        qid = int(qid_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="question_id must be an integer")
    logger.info(
        "[request_id=%s] Sample /%s/%s/skip: user_id=%s question_id=%s",
        request_id,
        normalized_topic,
        normalized_difficulty,
        current_user["id"],
        qid,
    )
    await mark_sample_seen(
        current_user["id"],
        normalized_difficulty,
        qid,
        topic=normalized_topic,
    )
    return await _get_sample_question_by_topic_and_difficulty(
        topic=normalized_topic,
        difficulty=normalized_difficulty,
        current_user=current_user,
    )


@router.post("/{topic}/submit")
async def submit_topic_sample_answer(
    topic: str,
    body: dict[str, Any],
    current_user: dict = Depends(get_current_user),
) -> dict[str, Any]:
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
        try:
            result = evaluate(parsed.query, question["expected_query"], question)
        except (BadRequestError, ValueError) as exc:
            await _mark_sample_attempted(current_user, normalized_topic, question)
            return {
                "correct": False,
                "is_result_correct": False,
                "structure_correct": False,
                "feedback": [str(exc)],
                "solution_query": question["solution_query"],
                "explanation": question["explanation"],
            }
        await _mark_sample_attempted(current_user, normalized_topic, question)
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
        await _mark_sample_attempted(current_user, normalized_topic, question)
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
            await _mark_sample_attempted(current_user, normalized_topic, question)
            return result
        else:  # conceptual
            parsed = _parse_body(SampleSubmitPySparkRequest, body)
            question = get_sample_question_for_topic(parsed.question_id, normalized_topic)
            if question is None:
                raise HTTPException(status_code=404, detail="Question not found")
            correct = is_mcq_correct(parsed.selected_option, question)
            await _mark_sample_attempted(current_user, normalized_topic, question)
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
    correct = is_mcq_correct(parsed.selected_option, question)
    await _mark_sample_attempted(current_user, normalized_topic, question)
    return {
        "correct": correct,
        "explanation": question.get("explanation", ""),
    }
