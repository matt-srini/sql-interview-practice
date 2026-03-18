"""Question catalog.

The MVP originally hard-coded a small list. This module now loads a larger seeded
catalog from the `question_bank` package while preserving the same public API.
"""

import random
from typing import Any, Optional

from question_bank import load_question_bank


QUESTIONS: list[dict[str, Any]] = load_question_bank()

_INDEX: dict[int, dict[str, Any]] = {int(q["id"]): q for q in QUESTIONS}


def get_all_questions() -> list[dict[str, Any]]:
    """Return a lightweight summary list for list views."""
    return [
        {
            "id": q["id"],
            "title": q["title"],
            "difficulty": q["difficulty"],
            "order": q["order"],
        }
        for q in QUESTIONS
    ]


def get_question(question_id: int) -> Optional[dict[str, Any]]:
    """Return the full question dict, or None if not found."""
    return _INDEX.get(int(question_id))


def get_public_question(question: dict[str, Any]) -> dict[str, Any]:
    """Return the question payload that is safe to expose before submission."""
    return {
        "id": question["id"],
        "order": question["order"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "schema": question["schema"],
        "dataset_files": question["dataset_files"],
    }


def get_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in QUESTIONS:
        grouped[q["difficulty"]].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x.get("order", 0)))
    return grouped


def get_random_question_by_difficulty(difficulty: str) -> Optional[dict[str, Any]]:
    questions = get_questions_by_difficulty().get(difficulty, [])
    if not questions:
        return None
    return random.choice(questions)
