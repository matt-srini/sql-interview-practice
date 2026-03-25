from __future__ import annotations

import logging

from db import clear_progress, clear_seen_samples, get_seen_sample_ids as db_get_seen_sample_ids
from db import get_solved_ids as db_get_solved_ids
from db import mark_sample_seen as db_mark_sample_seen
from db import mark_solved as db_mark_solved
from middleware.request_context import get_request_id


logger = logging.getLogger(__name__)


async def get_solved_question_ids(user_id: str) -> set[int]:
    return await db_get_solved_ids(user_id)


async def mark_question_solved(user_id: str, question_id: int) -> None:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Mark question solved: user_id=%s question_id=%s",
        request_id,
        user_id,
        int(question_id),
    )
    await db_mark_solved(user_id, question_id)


async def clear_user_progress(user_id: str) -> None:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Clear user progress: user_id=%s",
        request_id,
        user_id,
    )
    await clear_progress(user_id)
    await clear_seen_samples(user_id)


async def get_seen_sample_ids(user_id: str, difficulty: str) -> set[int]:
    return await db_get_seen_sample_ids(user_id, difficulty)


async def mark_sample_seen(user_id: str, difficulty: str, question_id: int) -> None:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Mark sample seen: user_id=%s difficulty=%s question_id=%s",
        request_id,
        user_id,
        difficulty,
        int(question_id),
    )
    await db_mark_sample_seen(user_id, difficulty, question_id)


async def clear_seen_sample_ids(user_id: str, difficulty: str) -> None:
    request_id = get_request_id()
    logger.info(
        "[request_id=%s] Clear seen sample ids: user_id=%s difficulty=%s",
        request_id,
        user_id,
        difficulty,
    )
    await clear_seen_samples(user_id, difficulty)
