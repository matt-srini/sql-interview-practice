"""Pandas question catalog loaded from JSON content files."""

import json
from pathlib import Path
from typing import Any, Optional

_CONTENT_DIR = Path(__file__).resolve().parent / "content" / "python_data_questions"
_SCHEMA_CONFIG_PATH = _CONTENT_DIR / "schemas.json"
_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def _fail(question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid python_data question (id={int(question_id)}): {reason}")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_question(question: dict[str, Any], *, id_ranges: dict[str, list[int]]) -> None:
    qid = int(question.get("id", -1))
    required = ["id", "order", "title", "difficulty", "description", "starter_code", "expected_code", "dataframes"]
    for field in required:
        if field not in question:
            _fail(qid, f"Missing required field: {field}")

    difficulty = str(question.get("difficulty"))
    if difficulty not in id_ranges:
        _fail(qid, f"Invalid difficulty: {difficulty}")

    lo, hi = id_ranges[difficulty]
    if not (lo <= qid <= hi):
        _fail(qid, f"ID out of range for difficulty={difficulty}: expected {lo}-{hi}")

    dataframes = question.get("dataframes")
    if not isinstance(dataframes, dict) or not dataframes:
        _fail(qid, "dataframes must be a non-empty dict")

    # Validate CSV files exist
    for var_name, csv_file in dataframes.items():
        csv_path = _DATASETS_DIR / csv_file
        if not csv_path.exists():
            _fail(qid, f"Dataset CSV not found: {csv_file}")


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
            questions.append(question)

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
    return {
        "id": question["id"],
        "order": question["order"],
        "title": question["title"],
        "description": question["description"],
        "difficulty": question["difficulty"],
        "starter_code": question["starter_code"],
        "hints": question.get("hints", []),
        "concepts": question.get("concepts", []),
        "schema": question.get("schema", {}),
        "dataframes": question.get("dataframes", {}),
    }


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
