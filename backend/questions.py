"""Question catalog loaded from validated JSON content files."""

import csv
import json
import random
from pathlib import Path
from typing import Any, Optional


_CONTENT_DIR = Path(__file__).resolve().parent / "content" / "questions"
_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"
_SCHEMA_CONFIG_PATH = _CONTENT_DIR / "schemas.json"


def _fail(question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid challenge question (id={int(question_id)}): {reason}")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _table_name_from_dataset_file(dataset_file: str) -> str:
    return Path(dataset_file).stem


def _read_dataset_headers(dataset_file: str) -> set[str]:
    dataset_path = _DATASETS_DIR / dataset_file
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        try:
            return {str(column) for column in next(reader)}
        except StopIteration as exc:
            raise ValueError(f"Dataset file is empty: {dataset_file}") from exc


def _validate_question(question: dict[str, Any], *, required_fields: list[str], id_ranges: dict[str, list[int]]) -> None:
    qid = int(question.get("id", -1))
    for required in required_fields:
        if required not in question:
            _fail(qid, f"Missing required field: {required}")

    difficulty = str(question.get("difficulty"))
    if difficulty not in id_ranges:
        _fail(qid, f"Invalid difficulty: {difficulty}")

    lo, hi = id_ranges[difficulty]
    if not (lo <= qid <= hi):
        _fail(qid, f"ID out of range for difficulty={difficulty}: expected {lo}-{hi}")

    dataset_files = question.get("dataset_files")
    if not isinstance(dataset_files, list) or not dataset_files:
        _fail(qid, "dataset_files must be a non-empty list")

    schema = question.get("schema")
    if not isinstance(schema, dict) or not schema:
        _fail(qid, "schema must be a non-empty dict")

    dataset_files_set = {str(dataset_file) for dataset_file in dataset_files}
    schema_tables = {str(table_name) for table_name in schema.keys()}
    table_headers = {
        _table_name_from_dataset_file(dataset_file): _read_dataset_headers(dataset_file)
        for dataset_file in dataset_files_set
    }

    for dataset_file in dataset_files_set:
        if not dataset_file.endswith(".csv"):
            _fail(qid, f"dataset_files contains non-CSV entry: {dataset_file}")
        if not (_DATASETS_DIR / dataset_file).exists():
            _fail(qid, f"Dataset file not found: {dataset_file}")
        table_name = _table_name_from_dataset_file(dataset_file)
        if table_name not in schema_tables:
            _fail(qid, f"dataset_files includes '{dataset_file}' but schema is missing table '{table_name}'")

    for table_name in schema_tables:
        expected_file = f"{table_name}.csv"
        if expected_file not in dataset_files_set:
            _fail(qid, f"schema includes table '{table_name}' but dataset_files is missing '{expected_file}'")
        missing_columns = [column for column in schema[table_name] if str(column) not in table_headers[table_name]]
        if missing_columns:
            _fail(qid, f"schema columns not found in dataset '{expected_file}': {missing_columns}")


def _load_questions() -> list[dict[str, Any]]:
    schema_config = _load_json(_SCHEMA_CONFIG_PATH)
    required_fields = list(schema_config["question_required_fields"])
    difficulty_files = dict(schema_config["difficulty_files"])
    id_ranges = dict(schema_config["challenge_id_ranges"])

    questions: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for difficulty in ["easy", "medium", "hard"]:
        question_file = _CONTENT_DIR / str(difficulty_files[difficulty])
        content = _load_json(question_file)
        if not isinstance(content, list):
            _fail(-1, f"Question file must contain a list: {question_file.name}")

        for question in content:
            if not isinstance(question, dict):
                _fail(-1, f"Question entry must be an object in {question_file.name}")
            _validate_question(question, required_fields=required_fields, id_ranges=id_ranges)

            qid = int(question["id"])
            if qid in seen_ids:
                _fail(qid, "Duplicate question id")
            seen_ids.add(qid)
            questions.append(question)

    return questions


QUESTIONS: list[dict[str, Any]] = _load_questions()

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
