from __future__ import annotations

from pathlib import Path

from path_loader import PATHS_DIR, get_all_paths
from pyspark_questions import get_questions_by_difficulty as get_pyspark_by_difficulty
from python_data_questions import get_questions_by_difficulty as get_python_data_by_difficulty
from python_questions import get_questions_by_difficulty as get_python_by_difficulty
from questions import get_questions_by_difficulty as get_sql_by_difficulty


REQUIRED_FIELDS = {"slug", "title", "description", "topic", "questions", "tier", "role"}
VALID_TOPICS = {"sql", "python", "python-data", "pyspark"}
VALID_TIERS = {"free", "pro"}
VALID_ROLES = {"starter", "intermediate", "advanced"}
EXPECTED_COUNTS_BY_TOPIC = {"sql": 7, "python": 5, "python-data": 5, "pyspark": 5}


def _id_set(grouped: dict[str, list[dict]]) -> set[int]:
    return {int(item["id"]) for questions in grouped.values() for item in questions}


def test_paths_catalog_has_expected_track_distribution() -> None:
    paths = get_all_paths()
    assert len(paths) == 22

    counts = {topic: 0 for topic in EXPECTED_COUNTS_BY_TOPIC}
    for path in paths:
        counts[path["topic"]] += 1

    assert counts == EXPECTED_COUNTS_BY_TOPIC


def test_paths_have_required_fields_and_valid_values() -> None:
    paths = get_all_paths()
    seen_slugs: set[str] = set()

    for path in paths:
        assert REQUIRED_FIELDS.issubset(path.keys())

        slug = str(path["slug"])
        assert slug not in seen_slugs
        seen_slugs.add(slug)

        assert path["topic"] in VALID_TOPICS
        assert path["tier"] in VALID_TIERS
        assert path["role"] in VALID_ROLES

        questions = [int(qid) for qid in path["questions"]]
        assert questions
        assert len(questions) == len(set(questions))


def test_path_slug_matches_filename() -> None:
    file_stems = {p.stem for p in Path(PATHS_DIR).glob("*.json")}
    slugs = {str(path["slug"]) for path in get_all_paths()}

    assert file_stems == slugs


def test_path_question_ids_exist_in_track_catalog() -> None:
    catalogs = {
        "sql": _id_set(get_sql_by_difficulty()),
        "python": _id_set(get_python_by_difficulty()),
        "python-data": _id_set(get_python_data_by_difficulty()),
        "pyspark": _id_set(get_pyspark_by_difficulty()),
    }

    for path in get_all_paths():
        topic = path["topic"]
        ids = [int(qid) for qid in path["questions"]]
        unknown = [qid for qid in ids if qid not in catalogs[topic]]
        assert not unknown, f"Path {path['slug']} has unknown IDs for {topic}: {unknown}"


def test_each_topic_has_single_starter_and_intermediate_path() -> None:
    roles = {
        topic: {"starter": 0, "intermediate": 0}
        for topic in VALID_TOPICS
    }

    for path in get_all_paths():
        role = path["role"]
        if role in ("starter", "intermediate"):
            roles[path["topic"]][role] += 1

    for topic, counts in roles.items():
        assert counts["starter"] == 1, f"{topic} must have exactly one starter path"
        assert counts["intermediate"] == 1, f"{topic} must have exactly one intermediate path"
