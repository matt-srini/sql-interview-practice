from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any, Iterable

from database import get_connection
from middleware.request_context import get_request_id


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuestionStatus:
    state: str  # locked | unlocked | solved
    is_next: bool


def init_progress_storage() -> None:
    logger.info("Initialising progress storage")
    conn = get_connection(read_only=False)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_progress (
              user_id VARCHAR NOT NULL,
              question_id INTEGER NOT NULL,
              solved_at TIMESTAMP NOT NULL,
              PRIMARY KEY(user_id, question_id)
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_sample_seen (
              user_id VARCHAR NOT NULL,
              difficulty VARCHAR NOT NULL,
              question_id INTEGER NOT NULL,
              seen_at TIMESTAMP NOT NULL,
              PRIMARY KEY(user_id, difficulty, question_id)
            );
            """
        )
    finally:
        conn.close()


def get_solved_question_ids(user_id: str) -> set[int]:
    conn = get_connection(read_only=True)
    try:
        rows = conn.execute(
            "SELECT question_id FROM user_progress WHERE user_id = ?",
            [user_id],
        ).fetchall()
        return {int(r[0]) for r in rows}
    finally:
        conn.close()


def mark_question_solved(user_id: str, question_id: int) -> None:
    request_id = get_request_id()
    logger.info(
        f"[request_id={request_id}] Mark question solved: user_id={user_id} question_id={int(question_id)}"
    )
    conn = get_connection(read_only=False)
    try:
        conn.execute(
            """
            INSERT INTO user_progress(user_id, question_id, solved_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, question_id) DO UPDATE SET solved_at = excluded.solved_at
            """,
            [user_id, int(question_id), datetime.now(timezone.utc)],
        )
    finally:
        conn.close()


def clear_user_progress(user_id: str) -> None:
    request_id = get_request_id()
    logger.info(f"[request_id={request_id}] Clear user progress: user_id={user_id}")
    conn = get_connection(read_only=False)
    try:
        conn.execute("DELETE FROM user_progress WHERE user_id = ?", [user_id])
        conn.execute("DELETE FROM user_sample_seen WHERE user_id = ?", [user_id])
    finally:
        conn.close()


def get_seen_sample_ids(user_id: str, difficulty: str) -> set[int]:
    conn = get_connection(read_only=True)
    try:
        rows = conn.execute(
            "SELECT question_id FROM user_sample_seen WHERE user_id = ? AND difficulty = ?",
            [user_id, difficulty],
        ).fetchall()
        return {int(r[0]) for r in rows}
    finally:
        conn.close()


def mark_sample_seen(user_id: str, difficulty: str, question_id: int) -> None:
    request_id = get_request_id()
    logger.info(
        f"[request_id={request_id}] Mark sample seen: user_id={user_id} difficulty={difficulty} question_id={int(question_id)}"
    )
    conn = get_connection(read_only=False)
    try:
        conn.execute(
            """
            INSERT INTO user_sample_seen(user_id, difficulty, question_id, seen_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, difficulty, question_id) DO UPDATE SET seen_at = excluded.seen_at
            """,
            [user_id, difficulty, int(question_id), datetime.now(timezone.utc)],
        )
    finally:
        conn.close()


def clear_seen_sample_ids(user_id: str, difficulty: str) -> None:
    request_id = get_request_id()
    logger.info(f"[request_id={request_id}] Clear seen sample ids: user_id={user_id} difficulty={difficulty}")
    conn = get_connection(read_only=False)
    try:
        conn.execute(
            "DELETE FROM user_sample_seen WHERE user_id = ? AND difficulty = ?",
            [user_id, difficulty],
        )
    finally:
        conn.close()


def compute_statuses(
    *,
    questions_by_difficulty: dict[str, list[dict[str, Any]]],
    solved_ids: Iterable[int],
) -> dict[int, QuestionStatus]:
    solved_set = {int(x) for x in solved_ids}
    statuses: dict[int, QuestionStatus] = {}

    for diff, questions in questions_by_difficulty.items():
        next_marked = False
        can_unlock = True
        for q in sorted(questions, key=lambda x: int(x.get("order", 0))):
            qid = int(q["id"])
            solved = qid in solved_set

            if solved:
                statuses[qid] = QuestionStatus(state="solved", is_next=False)
                continue

            if can_unlock:
                is_next = not next_marked
                statuses[qid] = QuestionStatus(state="unlocked", is_next=is_next)
                next_marked = True
                can_unlock = False
            else:
                statuses[qid] = QuestionStatus(state="locked", is_next=False)

        # Note: questions after the first unlocked unsolved are locked.

    return statuses


def is_unlocked_for_user(
    *,
    question: dict[str, Any],
    questions_by_difficulty: dict[str, list[dict[str, Any]]],
    solved_ids: set[int],
) -> bool:
    qid = int(question["id"])
    if qid in solved_ids:
        return True

    diff = question["difficulty"]
    ordered = sorted(questions_by_difficulty.get(diff, []), key=lambda x: int(x.get("order", 0)))

    for q in ordered:
        if int(q["id"]) == qid:
            break
        if int(q["id"]) not in solved_ids:
            return False

    # If all previous questions are solved, this one is unlocked.
    return True
