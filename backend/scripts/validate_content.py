from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Allow running from backend/ as `python scripts/validate_content.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from path_loader import get_all_paths
from pyspark_questions import get_questions_by_difficulty as get_pyspark_by_difficulty
from python_data_questions import get_questions_by_difficulty as get_python_data_by_difficulty
from python_questions import get_questions_by_difficulty as get_python_by_difficulty
from questions import get_questions_by_difficulty


BACKEND_ROOT = Path(__file__).resolve().parent.parent

QUESTION_DIRS = {
    "sql": BACKEND_ROOT / "content" / "questions",
    "python": BACKEND_ROOT / "content" / "python_questions",
    "python-data": BACKEND_ROOT / "content" / "python_data_questions",
    "pyspark": BACKEND_ROOT / "content" / "pyspark_questions",
}

_RAW_CONCEPTS_BY_TRACK: dict[str, set[str]] = {
    "sql": {
        "select",
        "where",
        "order by",
        "group by",
        "join",
        "inner join",
        "left join",
        "right join",
        "full outer join",
        "having",
        "count",
        "sum",
        "avg",
        "average",
        "min",
        "max",
        "case when",
        "row number",
        "row_number",
        "rank",
        "dense rank",
        "dense_rank",
        "lag",
        "lead",
        "cte introduction",
        "named temporary result set",
        "with clause syntax",
    },
    "python": {
        "dict",
        "dictionary",
        "set",
        "heapq",
        "for loop",
        "array",
        "string",
        "iteration",
        "sorting",
    },
    "python-data": {
        "groupby",
        "merge",
        "dropna",
        "fillna",
        "sort values",
        "sort_values",
        "rename",
        "resample",
        "pivot table",
        "pivot_table",
        "str accessor",
        "str split",
        "str.split",
        "copy",
        "size",
        "nunique",
    },
    "pyspark": {
        "filter",
        "filter()",
        "repartition",
        "repartition()",
        "withcolumn",
        "withcolumn()",
        "collect",
        "collect()",
        "cache",
        "cache()",
        "merge",
    },
}


def _normalize_concept(concept: str) -> str:
    return re.sub(r"\s+", " ", concept.strip().lower())


def _iter_question_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for track, directory in QUESTION_DIRS.items():
        for file_path in sorted(directory.glob("*.json")):
            if file_path.stem == "schemas":
                continue
            files.append((track, file_path))
    return files


def _validate_concepts() -> None:
    errors: list[str] = []

    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for question in questions:
            qid = question.get("id", "<unknown>")
            title = question.get("title", "<untitled>")
            concepts = question.get("concepts")

            if not isinstance(concepts, list) or not concepts:
                errors.append(f"{track} {qid} {title}: concepts must be a non-empty list")
                continue

            if len(concepts) < 2 or len(concepts) > 5:
                errors.append(
                    f"{track} {qid} {title}: expected 2-5 concept tags, found {len(concepts)}"
                )

            normalized_seen: set[str] = set()
            for concept in concepts:
                if not isinstance(concept, str) or not concept.strip():
                    errors.append(f"{track} {qid} {title}: concept tags must be non-empty strings")
                    continue

                normalized = _normalize_concept(concept)
                if normalized in normalized_seen:
                    errors.append(f"{track} {qid} {title}: duplicate concept tag '{concept}'")
                    continue
                normalized_seen.add(normalized)

                if normalized in _RAW_CONCEPTS_BY_TRACK[track]:
                    errors.append(
                        f"{track} {qid} {title}: concept tag '{concept}' is too syntax/API-level"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining > 0:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"Concept validation failed:\n{joined}")


def _validate_paths(paths: list[dict], catalogs_by_topic: dict[str, dict[str, list[dict]]]) -> None:
    valid_topics = {"sql", "python", "python-data", "pyspark"}
    valid_tiers = {"free", "pro"}
    valid_roles = {"starter", "intermediate", "advanced"}

    required_fields = {"slug", "title", "description", "topic", "questions", "tier", "role"}

    path_files = {p.stem for p in (BACKEND_ROOT / "content" / "paths").glob("*.json")}
    slugs = set()
    role_counts = {topic: {"starter": 0, "intermediate": 0} for topic in valid_topics}

    ids_by_topic = {
        topic: {int(q["id"]) for diff in grouped.values() for q in diff}
        for topic, grouped in catalogs_by_topic.items()
    }

    for path in paths:
        missing = required_fields - set(path.keys())
        if missing:
            raise ValueError(f"Path {path.get('slug', '<unknown>')} missing fields: {sorted(missing)}")

        slug = str(path["slug"])
        if slug in slugs:
            raise ValueError(f"Duplicate path slug: {slug}")
        slugs.add(slug)

        if slug not in path_files:
            raise ValueError(f"Path slug has no matching file: {slug}.json")

        topic = path["topic"]
        tier = path["tier"]
        role = path["role"]

        if topic not in valid_topics:
            raise ValueError(f"Invalid topic for path {slug}: {topic}")
        if tier not in valid_tiers:
            raise ValueError(f"Invalid tier for path {slug}: {tier}")
        if role not in valid_roles:
            raise ValueError(f"Invalid role for path {slug}: {role}")

        questions = [int(qid) for qid in path["questions"]]
        if not questions:
            raise ValueError(f"Path {slug} has no questions")
        if len(questions) != len(set(questions)):
            raise ValueError(f"Path {slug} has duplicate question IDs")

        unknown = sorted(qid for qid in questions if qid not in ids_by_topic[topic])
        if unknown:
            raise ValueError(f"Path {slug} references unknown question IDs for topic {topic}: {unknown}")

        if role in ("starter", "intermediate"):
            role_counts[topic][role] += 1

    for topic in valid_topics:
        if role_counts[topic]["starter"] != 1:
            raise ValueError(f"Topic {topic} must have exactly one starter path")
        if role_counts[topic]["intermediate"] != 1:
            raise ValueError(f"Topic {topic} must have exactly one intermediate path")


def _load_json_file(path: Path) -> None:
    with path.open("r", encoding="utf-8") as handle:
        json.load(handle)


def main() -> None:
    # Validate all raw JSON files parse cleanly.
    content_dirs = [
        BACKEND_ROOT / "content" / "questions",
        BACKEND_ROOT / "content" / "python_questions",
        BACKEND_ROOT / "content" / "python_data_questions",
        BACKEND_ROOT / "content" / "pyspark_questions",
        BACKEND_ROOT / "content" / "paths",
    ]
    for content_dir in content_dirs:
        for file_path in sorted(content_dir.glob("*.json")):
            _load_json_file(file_path)

    # Validate loader-level schemas and references.
    sql_catalog = get_questions_by_difficulty()
    python_catalog = get_python_by_difficulty()
    pandas_catalog = get_python_data_by_difficulty()
    pyspark_catalog = get_pyspark_by_difficulty()
    paths = get_all_paths()

    catalogs_by_topic = {
        "sql": sql_catalog,
        "python": python_catalog,
        "python-data": pandas_catalog,
        "pyspark": pyspark_catalog,
    }
    _validate_paths(paths, catalogs_by_topic)
    _validate_concepts()

    print("Content validation passed")


if __name__ == "__main__":
    main()
