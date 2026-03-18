from __future__ import annotations

from typing import Any

from question_bank.easy import QUESTIONS as EASY_QUESTIONS
from question_bank.hard import QUESTIONS as HARD_QUESTIONS
from question_bank.medium import QUESTIONS as MEDIUM_QUESTIONS


def load_question_bank() -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = [*EASY_QUESTIONS, *MEDIUM_QUESTIONS, *HARD_QUESTIONS]

    seen_ids: set[int] = set()
    for q in questions:
        qid = int(q["id"])
        if qid in seen_ids:
            raise ValueError(f"Duplicate question id: {qid}")
        seen_ids.add(qid)

        difficulty = q.get("difficulty")
        if difficulty not in {"easy", "medium", "hard"}:
            raise ValueError(f"Invalid difficulty for question {qid}: {difficulty}")

        for required in [
            "title",
            "description",
            "schema",
            "dataset_files",
            "expected_query",
            "solution_query",
            "explanation",
            "order",
        ]:
            if required not in q:
                raise ValueError(f"Question {qid} missing required field: {required}")

    return questions
