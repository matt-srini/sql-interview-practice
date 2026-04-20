from __future__ import annotations

import json
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

    print("Content validation passed")


if __name__ == "__main__":
    main()
