"""Statistics & Probability question catalog loaded from JSON content files.

Each question has a `subtype` field:
  - "conceptual": MCQ (options, correct_option, explanation) — like PySpark.
  - "numerical": Python-evaluated (expected_code, test_cases, starter_code) — like Python track.

The loader validates per-subtype required fields separately.
"""

import json
from pathlib import Path
from typing import Any, Optional

from interaction_modes import resolve_interaction_mode

_CONTENT_DIR = Path(__file__).resolve().parent / "content" / "statistics_questions"
_SCHEMA_CONFIG_PATH = _CONTENT_DIR / "schemas.json"

VALID_SUBTYPES = {"conceptual", "numerical"}
VALID_TYPES = {"mcq", "scenario", "numerical"}


def _fail(question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid statistics question (id={int(question_id)}): {reason}")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_question(question: dict[str, Any], *, id_ranges: dict[str, list[int]]) -> None:
    qid = int(question.get("id", -1))

    # Fields required by all subtypes
    common_required = ["id", "order", "title", "difficulty", "type", "subtype", "description"]
    for field in common_required:
        if field not in question:
            _fail(qid, f"Missing required field: {field}")

    difficulty = str(question.get("difficulty"))
    if difficulty not in id_ranges:
        _fail(qid, f"Invalid difficulty: {difficulty}")

    lo, hi = id_ranges[difficulty]
    if not (lo <= qid <= hi):
        _fail(qid, f"ID out of range for difficulty={difficulty}: expected {lo}-{hi}")

    q_type = str(question.get("type"))
    if q_type not in VALID_TYPES:
        _fail(qid, f"Invalid type: {q_type}, must be one of {VALID_TYPES}")

    subtype = str(question.get("subtype"))
    if subtype not in VALID_SUBTYPES:
        _fail(qid, f"Invalid subtype: {subtype}, must be 'conceptual' or 'numerical'")

    try:
        resolve_interaction_mode("statistics", question)
    except ValueError as exc:
        _fail(qid, str(exc))

    if subtype == "conceptual":
        _validate_conceptual(qid, question)
    else:
        _validate_numerical(qid, question)


def _validate_conceptual(qid: int, question: dict[str, Any]) -> None:
    for field in ["options", "correct_option", "explanation"]:
        if field not in question:
            _fail(qid, f"Conceptual question missing required field: {field}")

    options = question.get("options")
    if not isinstance(options, list) or len(options) < 2:
        _fail(qid, "options must be a list with at least 2 entries")

    correct = question.get("correct_option")
    if not isinstance(correct, int) or correct < 0 or correct >= len(options):
        _fail(qid, f"correct_option must be a valid index into options (0-{len(options)-1})")


def _validate_numerical(qid: int, question: dict[str, Any]) -> None:
    for field in ["expected_code", "test_cases", "explanation"]:
        if field not in question:
            _fail(qid, f"Numerical question missing required field: {field}")

    test_cases = question.get("test_cases")
    if not isinstance(test_cases, list) or len(test_cases) == 0:
        _fail(qid, "test_cases must be a non-empty list")


def _load_questions() -> list[dict[str, Any]]:
    schema_config = _load_json(_SCHEMA_CONFIG_PATH)
    difficulty_files = dict(schema_config["difficulty_files"])
    id_ranges = {k: list(v) for k, v in schema_config["id_ranges"].items()}

    questions: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for difficulty in ["easy", "medium", "hard"]:
        question_file = _CONTENT_DIR / str(difficulty_files[difficulty])
        if not question_file.exists():
            continue
        content = _load_json(question_file)
        if not isinstance(content, list):
            _fail(-1, f"Question file must contain a list: {question_file.name}")

        for question in content:
            if not isinstance(question, dict):
                _fail(-1, f"Question entry must be an object in {question_file.name}")
            _validate_question(question, id_ranges=id_ranges)
            qid = int(question["id"])
            if qid in seen_ids:
                _fail(qid, "Duplicate question id")
            seen_ids.add(qid)
            questions.append({**question, "interaction_mode": resolve_interaction_mode("statistics", question)})

    return questions


_ALL_QUESTIONS: list[dict[str, Any]] = _load_questions()
QUESTIONS: list[dict[str, Any]] = [q for q in _ALL_QUESTIONS if not q.get("mock_only")]
_INDEX: dict[int, dict[str, Any]] = {int(q["id"]): q for q in _ALL_QUESTIONS}


def get_all_questions() -> list[dict[str, Any]]:
    return [
        {"id": q["id"], "title": q["title"], "difficulty": q["difficulty"], "order": q["order"]}
        for q in QUESTIONS
    ]


def get_question(question_id: int) -> Optional[dict[str, Any]]:
    return _INDEX.get(int(question_id))


def get_public_question(question: dict[str, Any]) -> dict[str, Any]:
    """Return question payload safe to send to the client before answer is submitted."""
    subtype = question["subtype"]
    base: dict[str, Any] = {
        "id": question["id"],
        "order": question["order"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "type": question["type"],
        "subtype": subtype,
        "interaction_mode": question.get("interaction_mode"),
        "hints": question.get("hints", []),
        "concepts": question.get("concepts", []),
    }
    if subtype == "conceptual":
        base["options"] = question["options"]
        base["code_snippet"] = question.get("code_snippet")
        base["scenario_context"] = question.get("scenario_context")
    else:  # numerical
        base["starter_code"] = question.get("starter_code", "")
        base["function_signature"] = question.get("function_signature")
        all_cases = question.get("test_cases", [])
        public_count = question.get("public_test_cases", len(all_cases))
        base["test_cases"] = [
            {"input": tc.get("input"), "description": tc.get("description", "")}
            for tc in all_cases[:public_count]
        ]
    return base


def get_mock_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    """Return only mock_only=True questions, grouped by difficulty, sorted by order."""
    mock_qs = [q for q in _ALL_QUESTIONS if q.get("mock_only") is True]
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in mock_qs:
        grouped[q["difficulty"]].append(q)
    return {
        diff: sorted(qs, key=lambda x: int(x.get("order", 0)))
        for diff, qs in grouped.items()
    }


def get_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in QUESTIONS:
        grouped[q["difficulty"]].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x.get("order", 0)))
    return grouped
