from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sample_questions import SAMPLE_QUESTIONS


_DATASETS_DIR = Path(__file__).resolve().parent.parent / "datasets"
_CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "questions"
_SCHEMA_REGISTRY_PATH = _CONTENT_DIR / "schemas.json"


def _fail(source: str, question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid question in {source} (id={int(question_id)}): {reason}")


def _extract_qid(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return -1


def _table_name_from_dataset_file(dataset_file: str) -> str:
    # Convention: users.csv -> table users
    p = Path(dataset_file)
    return p.stem


def _load_json_file(path: Path, *, source: str) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        _fail(source, -1, f"Missing content file: {path.name}")
    except json.JSONDecodeError as exc:
        _fail(source, -1, f"Invalid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno})")


def _load_schema_registry() -> dict[str, Any]:
    source = "schemas.json"
    raw = _load_json_file(_SCHEMA_REGISTRY_PATH, source=source)
    if not isinstance(raw, dict):
        _fail(source, -1, "Schema registry must be a JSON object")

    for key in [
        "question_required_fields",
        "question_optional_fields",
        "difficulty_files",
        "challenge_id_ranges",
    ]:
        if key not in raw:
            _fail(source, -1, f"Missing registry key: {key}")

    return raw


def _normalize_id_ranges(registry: dict[str, Any]) -> dict[str, tuple[int, int]]:
    source = "schemas.json"
    raw_ranges = registry.get("challenge_id_ranges")
    if not isinstance(raw_ranges, dict):
        _fail(source, -1, "challenge_id_ranges must be an object")

    normalized: dict[str, tuple[int, int]] = {}
    for diff in ["easy", "medium", "hard"]:
        pair = raw_ranges.get(diff)
        if not isinstance(pair, list) or len(pair) != 2:
            _fail(source, -1, f"challenge_id_ranges.{diff} must be a two-item array")
        lo = int(pair[0])
        hi = int(pair[1])
        normalized[diff] = (lo, hi)

    return normalized


def _enforce_id_range(*, source: str, qid: int, difficulty: str, ranges: dict[str, tuple[int, int]]) -> None:
    bounds = ranges.get(difficulty)
    if bounds is None:
        _fail(source, qid, f"Invalid difficulty: {difficulty}")

    lo, hi = bounds

    if not (lo <= int(qid) <= hi):
        _fail(source, qid, f"ID out of range for difficulty={difficulty}: expected {lo}-{hi}")


def _validate_schema_shape(*, q: dict[str, Any], source: str, qid: int) -> None:
    schema = q.get("schema")
    if not isinstance(schema, dict) or not schema:
        _fail(source, qid, "schema must be a non-empty object")

    for table, columns in schema.items():
        if not isinstance(table, str) or not table:
            _fail(source, qid, "schema table names must be non-empty strings")
        if not isinstance(columns, list) or not columns:
            _fail(source, qid, f"schema['{table}'] must be a non-empty array of column names")
        for column in columns:
            if not isinstance(column, str) or not column:
                _fail(source, qid, f"schema['{table}'] contains an invalid column name")


def _validate_dataset_files(*, q: dict[str, Any], source: str, qid: int) -> set[str]:
    dataset_files = q.get("dataset_files")
    if not isinstance(dataset_files, list) or not dataset_files:
        _fail(source, qid, "dataset_files must be a non-empty list")

    dataset_files_set: set[str] = set()
    for entry in dataset_files:
        if not isinstance(entry, str) or not entry:
            _fail(source, qid, "dataset_files must contain non-empty string entries")
        dataset_files_set.add(entry)

    for dataset_file in dataset_files_set:
        if not dataset_file.endswith(".csv"):
            _fail(source, qid, f"dataset_files contains non-CSV entry: {dataset_file}")
        if not (_DATASETS_DIR / dataset_file).exists():
            _fail(source, qid, f"Dataset file not found: {dataset_file}")

    return dataset_files_set


def _validate_schema_dataset_consistency(*, q: dict[str, Any], source: str, qid: int, dataset_files_set: set[str]) -> None:
    schema_tables = {str(t) for t in q["schema"].keys()}

    # Bidirectional schema <-> dataset consistency.
    for table in schema_tables:
        expected_file = f"{table}.csv"
        if expected_file not in dataset_files_set:
            _fail(source, qid, f"schema includes table '{table}' but dataset_files is missing '{expected_file}'")

    for dataset_file in dataset_files_set:
        table = _table_name_from_dataset_file(dataset_file)
        if table not in schema_tables:
            _fail(source, qid, f"dataset_files includes '{dataset_file}' but schema is missing table '{table}'")


def _validate_question_types(*, q: dict[str, Any], source: str, qid: int) -> None:
    if not isinstance(q.get("title"), str) or not str(q.get("title")).strip():
        _fail(source, qid, "title must be a non-empty string")
    if not isinstance(q.get("description"), str) or not str(q.get("description")).strip():
        _fail(source, qid, "description must be a non-empty string")
    if not isinstance(q.get("expected_query"), str) or not str(q.get("expected_query")).strip():
        _fail(source, qid, "expected_query must be a non-empty string")
    if not isinstance(q.get("solution_query"), str) or not str(q.get("solution_query")).strip():
        _fail(source, qid, "solution_query must be a non-empty string")
    if not isinstance(q.get("explanation"), str) or not str(q.get("explanation")).strip():
        _fail(source, qid, "explanation must be a non-empty string")

    if not isinstance(q.get("order"), int):
        _fail(source, qid, "order must be an integer")

    hints = q.get("hints", [])
    if not isinstance(hints, list):
        _fail(source, qid, "hints must be a list when provided")
    if any((not isinstance(x, str) or not x) for x in hints):
        _fail(source, qid, "hints must contain non-empty strings")

    concepts = q.get("concepts", [])
    if not isinstance(concepts, list):
        _fail(source, qid, "concepts must be a list when provided")
    if any((not isinstance(x, str) or not x) for x in concepts):
        _fail(source, qid, "concepts must contain non-empty strings")


def _validate_required_fields(*, q: dict[str, Any], source: str, required_fields: list[str]) -> None:
    qid = _extract_qid(q.get("id"))
    for required in required_fields:
        if required not in q:
            _fail(source, qid, f"Missing required field: {required}")


def _validate_question(
    *,
    q: dict[str, Any],
    source: str,
    required_fields: list[str],
    id_ranges: dict[str, tuple[int, int]],
) -> None:
    _validate_required_fields(q=q, source=source, required_fields=required_fields)
    qid = _extract_qid(q.get("id"))
    if qid < 0:
        _fail(source, -1, "id must be an integer")

    difficulty = q.get("difficulty")
    if difficulty not in {"easy", "medium", "hard"}:
        _fail(source, qid, f"Invalid difficulty: {difficulty}")

    _enforce_id_range(source=source, qid=qid, difficulty=difficulty, ranges=id_ranges)
    _validate_question_types(q=q, source=source, qid=qid)
    _validate_schema_shape(q=q, source=source, qid=qid)
    dataset_files_set = _validate_dataset_files(q=q, source=source, qid=qid)
    _validate_schema_dataset_consistency(q=q, source=source, qid=qid, dataset_files_set=dataset_files_set)


def _validate_question_list_and_collect_sources(
    *,
    questions: list[dict[str, Any]],
    source: str,
    expected_difficulty: str,
    id_to_source: dict[int, str],
    required_fields: list[str],
    id_ranges: dict[str, tuple[int, int]],
) -> None:
    if not isinstance(questions, list):
        _fail(source, -1, "File must contain a JSON array of questions")

    for q in questions:
        if not isinstance(q, dict):
            _fail(source, -1, "Each question entry must be a JSON object")

        qid = _extract_qid(q.get("id"))
        if qid < 0:
            _fail(source, -1, "id must be an integer")
        if qid in id_to_source:
            _fail(source, qid, f"Duplicate question id (also defined in {id_to_source[qid]})")
        id_to_source[qid] = source

        if q.get("difficulty") != expected_difficulty:
            _fail(source, qid, f"Difficulty purity violation: expected '{expected_difficulty}'")
        _validate_question(
            q=q,
            source=source,
            required_fields=required_fields,
            id_ranges=id_ranges,
        )


def load_question_bank() -> list[dict[str, Any]]:
    registry = _load_schema_registry()
    difficulty_files = registry.get("difficulty_files", {})
    if not isinstance(difficulty_files, dict):
        _fail("schemas.json", -1, "difficulty_files must be an object")

    required_fields = registry.get("question_required_fields", [])
    if not isinstance(required_fields, list) or any(not isinstance(x, str) for x in required_fields):
        _fail("schemas.json", -1, "question_required_fields must be an array of strings")

    id_ranges = _normalize_id_ranges(registry)

    def _load_questions_for(diff: str) -> tuple[str, list[dict[str, Any]]]:
        file_name = difficulty_files.get(diff)
        if not isinstance(file_name, str) or not file_name:
            _fail("schemas.json", -1, f"difficulty_files.{diff} must be a non-empty string")
        source = file_name
        path = _CONTENT_DIR / file_name
        raw = _load_json_file(path, source=source)
        if not isinstance(raw, list):
            _fail(source, -1, "File must contain a JSON array")
        return source, raw

    easy_source, easy_questions = _load_questions_for("easy")
    medium_source, medium_questions = _load_questions_for("medium")
    hard_source, hard_questions = _load_questions_for("hard")

    id_to_source: dict[int, str] = {}
    _validate_question_list_and_collect_sources(
        questions=easy_questions,
        source=easy_source,
        expected_difficulty="easy",
        id_to_source=id_to_source,
        required_fields=required_fields,
        id_ranges=id_ranges,
    )
    _validate_question_list_and_collect_sources(
        questions=medium_questions,
        source=medium_source,
        expected_difficulty="medium",
        id_to_source=id_to_source,
        required_fields=required_fields,
        id_ranges=id_ranges,
    )
    _validate_question_list_and_collect_sources(
        questions=hard_questions,
        source=hard_source,
        expected_difficulty="hard",
        id_to_source=id_to_source,
        required_fields=required_fields,
        id_ranges=id_ranges,
    )

    questions: list[dict[str, Any]] = [*easy_questions, *medium_questions, *hard_questions]
    challenge_ids: set[int] = set(id_to_source.keys())

    sample_ids = {int(q["id"]) for q in SAMPLE_QUESTIONS}
    overlap = challenge_ids.intersection(sample_ids)
    if overlap:
        # Show one representative ID; the presence of any overlap is a hard failure.
        bad = sorted(overlap)[0]
        _fail(id_to_source.get(bad, "question_bank"), bad, "ID collision with sample_questions.py")

    return questions
