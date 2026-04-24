from typing import Any

from fastapi import HTTPException, Request, Response
from pydantic import BaseModel

from config import SECURE_COOKIES
from db import SESSION_COOKIE_NAME, create_anonymous_user, create_session, get_session_user
from progress import get_solved_question_ids
from questions import get_public_question, get_questions_by_difficulty
from sentry_utils import set_sentry_user
from unlock import compute_unlock_state, get_next_questions


CSRF_COOKIE_NAME = "csrf_token"


class RunQueryRequest(BaseModel):
    query: str
    question_id: int


class SubmitRequest(BaseModel):
    query: str
    question_id: int
    duration_ms: int | None = None


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=SECURE_COOKIES,
        max_age=30 * 24 * 3600,
        path="/",
    )


def set_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        samesite="strict",
        secure=SECURE_COOKIES,
        max_age=30 * 24 * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


async def get_optional_current_user(request: Request) -> dict[str, Any] | None:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None
    user = await get_session_user(session_token)
    if user is not None:
        set_sentry_user(user, is_authenticated=bool(user.get("email")))
    return user


async def get_current_user(request: Request, response: Response) -> dict[str, Any]:
    existing = await get_optional_current_user(request)
    if existing is not None:
        set_sentry_user(existing, is_authenticated=bool(existing.get("email")))
        return existing

    user = await create_anonymous_user()
    token = await create_session(user["id"])
    set_session_cookie(response, token)
    set_sentry_user(user, is_authenticated=False)
    return user


def _validate_difficulty(difficulty: str) -> str:
    normalized = difficulty.lower()
    if normalized not in {"easy", "medium", "hard"}:
        raise HTTPException(status_code=404, detail="Difficulty not found")
    return normalized


async def _get_progress_snapshot(
    current_user: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], set[int], dict[int, str], dict[str, int | None]]:
    grouped = get_questions_by_difficulty()
    solved_ids = await get_solved_question_ids(current_user["id"])
    unlock_state = compute_unlock_state(current_user["plan"], solved_ids, grouped)
    next_questions = get_next_questions(unlock_state, grouped)
    return grouped, solved_ids, unlock_state, next_questions


def _question_detail_payload(
    question: dict[str, Any],
    state: str,
    *,
    unlocked: bool,
    is_next: bool,
    mode: str = "practice",
) -> dict[str, Any]:
    return {
        **get_public_question(question),
        "progress": {
            "state": state,
            "is_next": is_next,
            "unlocked": unlocked,
            "mode": mode,
        },
    }
