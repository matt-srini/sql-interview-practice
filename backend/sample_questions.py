from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Optional

from tracks import TRACKS


_DATASETS_DIR = Path(__file__).resolve().parent / "datasets"


def _fail(question_id: int, reason: str) -> None:
    raise ValueError(f"Invalid question in sample_questions.py (id={int(question_id)}): {reason}")


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


def _enforce_sample_id_range(*, qid: int, difficulty: str) -> None:
    if difficulty == "easy":
        lo, hi = 111, 113
    elif difficulty == "medium":
        lo, hi = 121, 123
    elif difficulty == "hard":
        lo, hi = 131, 133
    else:
        _fail(qid, f"Invalid difficulty: {difficulty}")

    if not (lo <= int(qid) <= hi):
        _fail(qid, f"ID out of range for difficulty={difficulty}: expected {lo}–{hi}")


def _validate_sample_questions(questions: list[dict[str, Any]]) -> None:
    seen_ids: set[int] = set()
    by_diff: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}

    required_fields = [
        "id",
        "title",
        "description",
        "difficulty",
        "schema",
        "dataset_files",
        "expected_query",
        "solution_query",
        "explanation",
        "order",
    ]

    for qd in questions:
        qid = int(qd.get("id"))
        if qid in seen_ids:
            _fail(qid, "Duplicate question id")
        seen_ids.add(qid)

        for required in required_fields:
            if required not in qd:
                _fail(qid, f"Missing required field: {required}")

        difficulty = qd.get("difficulty")
        if difficulty not in by_diff:
            _fail(qid, f"Invalid difficulty: {difficulty}")
        _enforce_sample_id_range(qid=qid, difficulty=difficulty)
        by_diff[difficulty].append(qd)

        dataset_files = qd.get("dataset_files")
        if not isinstance(dataset_files, list) or not dataset_files:
            _fail(qid, "dataset_files must be a non-empty list")

        schema = qd.get("schema")
        if not isinstance(schema, dict) or not schema:
            _fail(qid, "schema must be a non-empty dict")

        dataset_files_set = {str(x) for x in dataset_files}
        for dataset_file in dataset_files_set:
            if not (_DATASETS_DIR / dataset_file).exists():
                _fail(qid, f"Dataset file not found: {dataset_file}")

        schema_tables = {str(t) for t in schema.keys()}
        table_headers = {
            _table_name_from_dataset_file(dataset_file): _read_dataset_headers(dataset_file)
            for dataset_file in dataset_files_set
        }

        for table in schema_tables:
            expected_file = f"{table}.csv"
            if expected_file not in dataset_files_set:
                _fail(qid, f"schema includes table '{table}' but dataset_files is missing '{expected_file}'")
            missing_columns = [column for column in schema[table] if str(column) not in table_headers[table]]
            if missing_columns:
                _fail(qid, f"schema columns not found in dataset '{expected_file}': {missing_columns}")

        for dataset_file in dataset_files_set:
            if not dataset_file.endswith(".csv"):
                _fail(qid, f"dataset_files contains non-CSV entry: {dataset_file}")
            table = _table_name_from_dataset_file(dataset_file)
            if table not in schema_tables:
                _fail(qid, f"dataset_files includes '{dataset_file}' but schema is missing table '{table}'")

    for diff in ["easy", "medium", "hard"]:
        if len(by_diff[diff]) != 3:
            _fail(-1, f"Expected exactly 3 sample questions for difficulty='{diff}', found {len(by_diff[diff])}")


# Build alias map from the registry: both slug and db_topic resolve to db_topic.
_TOPIC_ALIASES: dict[str, str] = {}
for _t in TRACKS:
    _TOPIC_ALIASES[_t.slug] = _t.db_topic
    _TOPIC_ALIASES[_t.db_topic] = _t.db_topic

_DIFFICULTY_ORDER = ("easy", "medium", "hard")
_SAMPLE_POOL_SIZE = 3

# Dedicated sample question files for every track.
# Each file contains exactly 9 questions: 3 easy, 3 medium, 3 hard.
# IDs follow the TXS compact format: T = track digit, X = difficulty digit (1/2/3), S = 1–3.
# SQL samples are validated against committed CSV headers (schema/dataset_files
# integrity) via _validate_sample_questions below. Other tracks rely on
# track-level catalog validators run by scripts/validate_content.py.
_SAMPLE_DIR = Path(__file__).resolve().parent / "content" / "sample_questions"
_TRACK_SAMPLE_FILES: dict[str, str] = {
    "sql": "sql.json",
    "python": "python.json",
    "pandas": "pandas.json",
    "pyspark": "pyspark.json",
    "data-engineering": "data_engineering.json",
    "data-modeling": "data_modeling.json",
    "statistics": "statistics.json",
    "ml-fundamentals": "ml_fundamentals.json",
    "experimentation": "experimentation.json",
}


def _load_track_samples(db_topic: str) -> dict[str, list[dict[str, Any]]]:
    """Load and group dedicated sample questions for a track by difficulty.

    Enforces exactly 3 questions per difficulty for every track. SQL gets
    additional schema/CSV-header validation via `_validate_sample_questions`
    below — this function provides the per-difficulty count guard that
    applies uniformly to every track. Previously the count check ran only
    for SQL, so a stray edit dropping a non-SQL track to 2 or 4 of any
    difficulty would silently return a wrong-sized pool via `pool[:3]` at
    request time. This guard raises at module import instead.
    """
    filename = _TRACK_SAMPLE_FILES[db_topic]
    sample_path = _SAMPLE_DIR / filename
    with sample_path.open("r", encoding="utf-8") as fh:
        questions: list[dict[str, Any]] = json.load(fh)
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in questions:
        diff = str(q.get("difficulty", "")).lower()
        if diff in grouped:
            grouped[diff].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x.get("order", 0)))
    # Per-difficulty count guard — every sample track must have exactly 3
    # questions per difficulty.
    for diff in ("easy", "medium", "hard"):
        n = len(grouped[diff])
        if n != 3:
            raise ValueError(
                f"Sample loader: db_topic={db_topic!r} difficulty={diff!r} "
                f"expected exactly 3 questions, found {n}"
            )
    # Field-presence guard — every sample (every track, every difficulty) must
    # carry exactly 2 hints and 1-4 canonical concept tags. Added 2026-06-01 as
    # the closing step of the sample-bank audit (Phase 5b). Belt-and-suspenders
    # alongside validate_content.py's checks: this fires at app startup so a
    # bad edit can't reach a user even if the validator hasn't been re-run.
    for diff in ("easy", "medium", "hard"):
        for q in grouped[diff]:
            qid = q.get("id", "<unknown>")
            hints = q.get("hints")
            if not isinstance(hints, list) or len(hints) != 2:
                hint_count = len(hints) if isinstance(hints, list) else 0
                raise ValueError(
                    f"Sample loader: db_topic={db_topic!r} qid={qid} "
                    f"expected exactly 2 hints, found {hint_count}"
                )
            if not all(isinstance(h, str) and h.strip() for h in hints):
                raise ValueError(
                    f"Sample loader: db_topic={db_topic!r} qid={qid} "
                    f"hints must be non-empty strings"
                )
            concepts = q.get("concepts")
            if not isinstance(concepts, list) or not (1 <= len(concepts) <= 4):
                concept_count = len(concepts) if isinstance(concepts, list) else 0
                raise ValueError(
                    f"Sample loader: db_topic={db_topic!r} qid={qid} "
                    f"expected 1-4 concept tags, found {concept_count}"
                )
            if not all(isinstance(c, str) and c.strip() for c in concepts):
                raise ValueError(
                    f"Sample loader: db_topic={db_topic!r} qid={qid} "
                    f"concept tags must be non-empty strings"
                )
    return grouped


# Pre-load every track's sample pool at module import time so the first
# request does not pay the file-read cost.
_TRACK_SAMPLES: dict[str, dict[str, list[dict[str, Any]]]] = {
    db_topic: _load_track_samples(db_topic)
    for db_topic in _TRACK_SAMPLE_FILES
}

# SQL samples carry executable schema and dataset_files — validate that schema
# columns match committed CSV headers and that exactly 3 questions exist per
# difficulty. Other tracks are MCQ/conceptual and don't need this check.
SAMPLE_QUESTIONS: list[dict[str, Any]] = [
    q for diff_pool in _TRACK_SAMPLES["sql"].values() for q in diff_pool
]
_validate_sample_questions(SAMPLE_QUESTIONS)
SAMPLE_INDEX: dict[int, dict[str, Any]] = {int(q["id"]): q for q in SAMPLE_QUESTIONS}


def normalize_sample_topic(topic: str) -> str:
    normalized = _TOPIC_ALIASES.get(str(topic).strip().lower())
    if normalized is None:
        raise ValueError(f"Unsupported sample topic: {topic}")
    return normalized


def get_sample_question(question_id: int) -> Optional[dict[str, Any]]:
    return SAMPLE_INDEX.get(int(question_id))


def get_sample_question_for_topic(question_id: int, topic: str) -> Optional[dict[str, Any]]:
    normalized_topic = normalize_sample_topic(topic)
    target_id = int(question_id)
    for difficulty in _DIFFICULTY_ORDER:
        pool, _ = get_topic_sample_pool(topic=normalized_topic, difficulty=difficulty)
        for question in pool:
            if int(question["id"]) == target_id:
                return question
    return None


def get_sample_questions_by_difficulty() -> dict[str, list[dict[str, Any]]]:
    """SQL-only legacy accessor used by tests. Other tracks should call
    get_topic_sample_pool() directly."""
    grouped: dict[str, list[dict[str, Any]]] = {"easy": [], "medium": [], "hard": []}
    for q in SAMPLE_QUESTIONS:
        grouped[q["difficulty"]].append(q)
    for diff in grouped:
        grouped[diff] = sorted(grouped[diff], key=lambda x: int(x["order"]))
    return grouped


def get_all_topic_db_slugs() -> list[str]:
    """All db_topic slugs that have a sample pool — one per dedicated file."""
    return list(_TRACK_SAMPLE_FILES.keys())


def get_sample_catalog_shape() -> dict[str, dict[str, int]]:
    """Return {db_topic: {difficulty: pool_size}} across every track with samples.

    Used by the summary endpoint so the frontend can compute remaining =
    total - tried per (track, difficulty).
    """
    shape: dict[str, dict[str, int]] = {}
    for db_topic in get_all_topic_db_slugs():
        shape[db_topic] = {}
        for diff in _DIFFICULTY_ORDER:
            pool, _ = get_topic_sample_pool(topic=db_topic, difficulty=diff)
            shape[db_topic][diff] = len(pool)
    return shape


def get_topic_sample_pool(
    *,
    topic: str,
    difficulty: str,
) -> tuple[list[dict[str, Any]], str]:
    normalized_topic = normalize_sample_topic(topic)
    normalized_difficulty = str(difficulty).strip().lower()
    if normalized_difficulty not in _DIFFICULTY_ORDER:
        raise ValueError(f"Unsupported sample difficulty: {difficulty}")

    # Every track — SQL included — is served from its dedicated sample file.
    pool = list(_TRACK_SAMPLES[normalized_topic].get(normalized_difficulty, []))
    return pool[:_SAMPLE_POOL_SIZE], normalized_difficulty
