from __future__ import annotations

from typing import Any


FREE_MEDIUM_THRESHOLDS: list[tuple[int, int | None]] = [
    (30, None),
    (20, 8),
    (10, 3),
]
FREE_HARD_THRESHOLDS: list[tuple[int, int]] = [
    (30, 15),
    (20, 8),
    (10, 3),
]
PRO_HARD_CAP = 22


def _sorted_catalog(catalog: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        difficulty: sorted(catalog.get(difficulty, []), key=lambda question: int(question.get("order", 0)))
        for difficulty in ("easy", "medium", "hard")
    }


def _free_medium_limit(total_medium: int, easy_solved: int) -> int:
    for solved_threshold, limit in FREE_MEDIUM_THRESHOLDS:
        if easy_solved >= solved_threshold:
            return total_medium if limit is None else min(limit, total_medium)
    return 0


def _free_hard_limit(total_hard: int, medium_solved: int) -> int:
    for solved_threshold, limit in FREE_HARD_THRESHOLDS:
        if medium_solved >= solved_threshold:
            return min(limit, total_hard)
    return 0


def compute_unlock_state(
    plan: str,
    solved_ids: set[int],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[int, str]:
    ordered_catalog = _sorted_catalog(catalog)
    solved_set = {int(question_id) for question_id in solved_ids}

    easy_questions = ordered_catalog["easy"]
    medium_questions = ordered_catalog["medium"]
    hard_questions = ordered_catalog["hard"]

    easy_solved = sum(1 for question in easy_questions if int(question["id"]) in solved_set)
    medium_solved = sum(1 for question in medium_questions if int(question["id"]) in solved_set)

    if plan == "elite":
        limits = {
            "easy": len(easy_questions),
            "medium": len(medium_questions),
            "hard": len(hard_questions),
        }
    elif plan == "pro":
        limits = {
            "easy": len(easy_questions),
            "medium": len(medium_questions),
            "hard": min(PRO_HARD_CAP, len(hard_questions)),
        }
    else:
        limits = {
            "easy": len(easy_questions),
            "medium": _free_medium_limit(len(medium_questions), easy_solved),
            "hard": _free_hard_limit(len(hard_questions), medium_solved),
        }

    unlock_state: dict[int, str] = {}
    for difficulty, questions in ordered_catalog.items():
        unlocked_prefix = limits[difficulty]
        for index, question in enumerate(questions):
            question_id = int(question["id"])
            unlock_state[question_id] = "unlocked" if index < unlocked_prefix else "locked"

    for question_id in solved_set:
        unlock_state[question_id] = "solved"

    return unlock_state


def get_next_questions(
    unlock_state: dict[int, str],
    catalog: dict[str, list[dict[str, Any]]],
) -> dict[str, int | None]:
    ordered_catalog = _sorted_catalog(catalog)
    next_questions: dict[str, int | None] = {}

    for difficulty, questions in ordered_catalog.items():
        next_question_id = next(
            (
                int(question["id"])
                for question in questions
                if unlock_state.get(int(question["id"])) == "unlocked"
            ),
            None,
        )
        next_questions[difficulty] = next_question_id

    return next_questions
