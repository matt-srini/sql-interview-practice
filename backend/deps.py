from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

from progress import compute_statuses, get_solved_question_ids
from questions import get_public_question, get_questions_by_difficulty


class RunQueryRequest(BaseModel):
    query: str
    question_id: int


class SubmitRequest(BaseModel):
    query: str
    question_id: int


def get_user_id(request: Request, response: Response) -> str:
    """Best-effort user identity for progression (cookie or explicit header)."""
    header_uid = request.headers.get("X-User-Id")
    if header_uid:
        return header_uid

    cookie_uid = request.cookies.get("sql_practice_uid")
    if cookie_uid:
        return cookie_uid

    uid = str(uuid4())
    response.set_cookie(
        key="sql_practice_uid",
        value=uid,
        httponly=True,
        samesite="lax",
    )
    return uid


def _validate_difficulty(difficulty: str) -> str:
    normalized = difficulty.lower()
    if normalized not in {"easy", "medium", "hard"}:
        raise HTTPException(status_code=404, detail="Difficulty not found")
    return normalized


def _get_progress_snapshot(
    user_id: str,
) -> tuple[dict[str, list[dict[str, Any]]], set[int], dict[int, Any]]:
    grouped = get_questions_by_difficulty()
    solved_ids = get_solved_question_ids(user_id)
    statuses = compute_statuses(questions_by_difficulty=grouped, solved_ids=solved_ids)
    return grouped, solved_ids, statuses


def _question_detail_payload(
    question: dict[str, Any],
    status: Any,
    *,
    unlocked: bool,
    mode: str = "practice",
) -> dict[str, Any]:
    return {
        **get_public_question(question),
        "progress": {
            "state": status.state,
            "is_next": status.is_next,
            "unlocked": unlocked,
            "mode": mode,
        },
    }
