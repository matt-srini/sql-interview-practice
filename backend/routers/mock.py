"""
Mock interview router.

Endpoints:
  GET  /api/mock/history
  POST /api/mock/start
  GET  /api/mock/{session_id}
  POST /api/mock/{session_id}/submit
  POST /api/mock/{session_id}/finish

NOTE: /history must be registered before /{session_id} to avoid FastAPI
interpreting the string "history" as an integer session ID.
"""
from __future__ import annotations

import logging
import random
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import python_data_questions
import python_questions
import pyspark_questions
import questions as sql_catalog
from db import (
    create_mock_session,
    finish_mock_session,
    get_mock_history,
    get_mock_session,
    mark_solved,
    record_submission,
    submit_mock_question,
)
from deps import get_current_user
from evaluator import evaluate
from python_evaluator import evaluate_python_code, evaluate_python_data_code
from unlock import compute_unlock_state

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mock")

# ── Constants ──────────────────────────────────────────────────────────────────

MODE_CONFIGS: dict[str, dict[str, int]] = {
    "30min": {"num_questions": 2, "time_limit_s": 1800},
    "60min": {"num_questions": 3, "time_limit_s": 3600},
}

VALID_TRACKS = {"sql", "python", "python-data", "pyspark", "mixed"}
VALID_DIFFICULTIES = {"easy", "medium", "hard", "mixed"}

# Maps URL-style track name → topic string used in mark_solved / get_solved_ids
TRACK_TO_TOPIC: dict[str, str] = {
    "sql": "sql",
    "python": "python",
    "python-data": "python_data",
    "pyspark": "pyspark",
}


# ── Request models ─────────────────────────────────────────────────────────────

class MockStartRequest(BaseModel):
    mode: str           # '30min' | '60min' | 'custom'
    track: str          # 'sql' | 'python' | 'python-data' | 'pyspark' | 'mixed'
    difficulty: str     # 'easy' | 'medium' | 'hard' | 'mixed'
    num_questions: int | None = None   # custom mode only, 1–5
    time_minutes: int | None = None    # custom mode only, 10–90


class MockSubmitRequest(BaseModel):
    question_id: int
    track: str
    code: str | None = None
    selected_option: int | None = None  # PySpark MCQ
    time_spent_s: int | None = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_catalog_for_track(track: str):
    """Return the catalog module for a single (non-mixed) track."""
    if track == "sql":
        return sql_catalog
    if track == "python":
        return python_questions
    if track == "python-data":
        return python_data_questions
    if track == "pyspark":
        return pyspark_questions
    raise ValueError(f"Unknown track: {track}")


async def _get_solved_ids_for_track(user_id: str, track: str) -> set[int]:
    from db import get_solved_ids
    topic = TRACK_TO_TOPIC[track]
    return await get_solved_ids(user_id, topic)


def _pool_for_track(
    track: str,
    difficulty: str,
    user_plan: str,
    solved_ids: set[int],
) -> list[dict]:
    """
    Return a list of question dicts that are unlocked (not locked) for the given
    track and difficulty, tagged with their track name.
    """
    catalog = _get_catalog_for_track(track)
    grouped = catalog.get_questions_by_difficulty()
    unlock_state = compute_unlock_state(user_plan, solved_ids, grouped)

    all_questions: list[dict] = []
    for diff, qs in grouped.items():
        if difficulty != "mixed" and diff != difficulty:
            continue
        for q in qs:
            state = unlock_state.get(int(q["id"]), "locked")
            if state != "locked":
                all_questions.append({**q, "_track": track})

    return all_questions


async def _select_questions(
    track: str,
    difficulty: str,
    num_questions: int,
    user: dict,
) -> list[dict]:
    """
    Select `num_questions` questions for a mock session.
    Returns list of {"question_id", "track", "position"} dicts.
    """
    user_plan = user.get("plan", "free")
    user_id = user["id"]

    if track == "mixed":
        single_tracks = ["sql", "python", "python-data", "pyspark"]
        pool: list[dict] = []
        for t in single_tracks:
            solved = await _get_solved_ids_for_track(user_id, t)
            pool.extend(_pool_for_track(t, difficulty, user_plan, solved))
    else:
        solved = await _get_solved_ids_for_track(user_id, track)
        pool = _pool_for_track(track, difficulty, user_plan, solved)

    if len(pool) < num_questions:
        raise HTTPException(
            status_code=400,
            detail=(
                "Not enough unlocked questions for this configuration. "
                "Try a lower difficulty or upgrade your plan."
            ),
        )

    chosen = random.sample(pool, num_questions)
    return [
        {
            "question_id": int(q["id"]),
            "track": q["_track"],
            "position": i + 1,
        }
        for i, q in enumerate(chosen)
    ]


def _public_question_payload(question: dict, track: str) -> dict:
    """Return safe question fields for the session start response (no solutions)."""
    payload: dict[str, Any] = {
        "id": question["id"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "track": track,
        "concepts": question.get("concepts", []),
        "hints": question.get("hints", []),
    }
    # SQL: include schema
    if track == "sql":
        payload["schema"] = question.get("schema", {})
    # Python: include test case inputs (no expected outputs)
    if track == "python":
        public_cases = [
            {"input": tc.get("input"), "description": tc.get("description", "")}
            for tc in question.get("test_cases", [])[:question.get("public_test_cases", 999)]
        ]
        payload["test_cases"] = public_cases
    # Pandas: include available dataframes info
    if track == "python-data":
        payload["dataframes"] = {
            name: {"description": info.get("description", "")}
            for name, info in question.get("dataframes", {}).items()
        }
    # PySpark: include options
    if track == "pyspark":
        payload["options"] = question.get("options", [])
        payload["question_type"] = question.get("question_type", "mcq")
    return payload


def _solution_payload(question: dict, track: str) -> dict:
    """Return solution fields, shown only in the finish/summary response."""
    if track == "sql":
        return {
            "solution_query": question.get("solution_query", ""),
            "explanation": question.get("explanation", ""),
        }
    if track in ("python", "python-data"):
        return {
            "solution_code": question.get("expected_code", ""),
            "explanation": question.get("explanation", ""),
        }
    if track == "pyspark":
        return {
            "correct_option": question.get("correct_option"),
            "explanation": question.get("explanation", ""),
        }
    return {}


def _evaluate_submission(
    track: str,
    question: dict,
    code: str | None,
    selected_option: int | None,
) -> tuple[bool, dict]:
    """
    Run the appropriate evaluator and return (accepted, result_dict).
    result_dict is a lean dict safe to return mid-session (no solutions).
    """
    if track == "sql":
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate(code, question["expected_query"], question)
        accepted = bool(result.get("correct")) and bool(result.get("structure_correct", True))
        return accepted, {
            "correct": accepted,
            "feedback": result.get("feedback", []),
            "user_result": result.get("user_result"),
            "expected_result": result.get("expected_result"),
        }

    if track == "python":
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate_python_code(code, question)
        accepted = bool(result.get("correct"))
        return accepted, {
            "correct": accepted,
            "error": result.get("error"),
            "public_results": result.get("public_results", []),
            "hidden_summary": result.get("hidden_summary"),
        }

    if track == "python-data":
        if not code:
            return False, {"error": "No code provided"}
        result = evaluate_python_data_code(code, question)
        accepted = bool(result.get("correct"))
        return accepted, {
            "correct": accepted,
            "error": result.get("error"),
        }

    if track == "pyspark":
        if selected_option is None:
            return False, {"error": "No option selected"}
        accepted = selected_option == question.get("correct_option")
        return accepted, {"correct": accepted}

    return False, {"error": f"Unknown track: {track}"}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/history")
async def get_history(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    return await get_mock_history(current_user["id"], limit=20)


@router.post("/start")
async def start_session(
    body: MockStartRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    # Validate track and difficulty
    if body.track not in VALID_TRACKS:
        raise HTTPException(status_code=400, detail=f"Invalid track. Must be one of: {', '.join(VALID_TRACKS)}")
    if body.difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty. Must be one of: {', '.join(VALID_DIFFICULTIES)}")

    # Derive num_questions and time_limit_s
    if body.mode in MODE_CONFIGS:
        num_questions = MODE_CONFIGS[body.mode]["num_questions"]
        time_limit_s = MODE_CONFIGS[body.mode]["time_limit_s"]
    elif body.mode == "custom":
        nq = body.num_questions
        tm = body.time_minutes
        if nq is None or not (1 <= nq <= 5):
            raise HTTPException(status_code=400, detail="num_questions must be between 1 and 5 for custom mode.")
        if tm is None or not (10 <= tm <= 90):
            raise HTTPException(status_code=400, detail="time_minutes must be between 10 and 90 for custom mode.")
        num_questions = nq
        time_limit_s = tm * 60
    else:
        raise HTTPException(status_code=400, detail="Invalid mode. Must be '30min', '60min', or 'custom'.")

    # Select questions
    selected = await _select_questions(body.track, body.difficulty, num_questions, current_user)

    # Fetch question details for response
    question_details: list[dict] = []
    for sel in selected:
        catalog = _get_catalog_for_track(sel["track"])
        q = catalog.get_question(sel["question_id"])
        if q is None:
            raise HTTPException(status_code=500, detail=f"Question {sel['question_id']} not found")
        question_details.append({
            **_public_question_payload(q, sel["track"]),
            "position": sel["position"],
            "is_solved": False,
            "final_code": None,
            "time_spent_s": None,
        })

    # Persist session
    session = await create_mock_session(
        user_id=current_user["id"],
        mode=body.mode,
        track=body.track,
        difficulty=body.difficulty,
        time_limit_s=time_limit_s,
        questions=selected,
    )

    return {
        **session,
        "questions": question_details,
    }


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich question rows with public question detail
    enriched_questions: list[dict] = []
    for q_row in session.get("questions", []):
        catalog = _get_catalog_for_track(q_row["track"])
        q = catalog.get_question(q_row["question_id"])
        if q is None:
            continue
        enriched_questions.append({
            **_public_question_payload(q, q_row["track"]),
            "position": q_row["position"],
            "is_solved": q_row["is_solved"],
            "final_code": q_row["final_code"],
            "time_spent_s": q_row["time_spent_s"],
        })

    return {**session, "questions": enriched_questions}


@router.post("/{session_id}/submit")
async def submit_answer(
    session_id: int,
    body: MockSubmitRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    if body.track not in TRACK_TO_TOPIC:
        raise HTTPException(status_code=400, detail=f"Invalid track: {body.track}")

    # Load and validate session
    session = await get_mock_session(session_id, current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Verify question belongs to session
    session_q_ids = {q["question_id"] for q in session.get("questions", [])}
    if body.question_id not in session_q_ids:
        raise HTTPException(status_code=400, detail="Question not part of this session")

    # Load full question
    catalog = _get_catalog_for_track(body.track)
    question = catalog.get_question(body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    # Evaluate
    accepted, result = _evaluate_submission(body.track, question, body.code, body.selected_option)

    # Persist mock submission record
    await submit_mock_question(
        session_id=session_id,
        question_id=body.question_id,
        user_id=current_user["id"],
        is_solved=accepted,
        code=body.code,
        time_spent_s=body.time_spent_s,
    )

    # Track progress if correct
    if accepted:
        topic = TRACK_TO_TOPIC[body.track]
        await mark_solved(current_user["id"], body.question_id, topic=topic)
        await record_submission(
            user_id=current_user["id"],
            track=body.track,
            question_id=body.question_id,
            is_correct=True,
            code=body.code,
        )
    else:
        await record_submission(
            user_id=current_user["id"],
            track=body.track,
            question_id=body.question_id,
            is_correct=False,
            code=body.code,
        )

    # Return lean result — no solutions mid-session
    return result


@router.post("/{session_id}/finish")
async def finish_session(
    session_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    summary = await finish_mock_session(session_id, current_user["id"])
    if summary is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enrich questions with public detail + solutions
    enriched_questions: list[dict] = []
    for q_row in summary.get("questions", []):
        catalog = _get_catalog_for_track(q_row["track"])
        q = catalog.get_question(q_row["question_id"])
        if q is None:
            continue
        enriched_questions.append({
            **_public_question_payload(q, q_row["track"]),
            **_solution_payload(q, q_row["track"]),   # solutions only at end
            "position": q_row["position"],
            "is_solved": q_row["is_solved"],
            "final_code": q_row["final_code"],
            "time_spent_s": q_row["time_spent_s"],
        })

    return {**summary, "questions": enriched_questions}
