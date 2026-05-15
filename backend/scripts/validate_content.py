from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Allow running from backend/ as `python scripts/validate_content.py`
sys.path.insert(0, str(Path(__file__).parent.parent))

from path_loader import get_all_paths
from tracks import TRACKS


BACKEND_ROOT = Path(__file__).resolve().parent.parent

QUESTION_DIRS: dict[str, Path] = {t.slug: t.content_dir for t in TRACKS}

_RAW_CONCEPTS_BY_TRACK: dict[str, set[str]] = {t.slug: t.concept_blocklist for t in TRACKS}

_HINT_COUNT_RULES: dict[str, dict[str, tuple[int, int]]] = {t.slug: t.hint_rules for t in TRACKS}

_FIRST_HINT_LEAK_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    t.slug: t.first_hint_leak_patterns for t in TRACKS
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


def _validate_mcq_scenario_questions() -> None:
    """Validate scenario-type MCQ questions (any track) have required observation anchors and rich options."""
    from tracks import TRACKS as _TRACKS
    mcq_track_slugs = {t.slug for t in _TRACKS if t.eval_kind == "mcq"}
    errors: list[str] = []

    for track_slug in mcq_track_slugs:
        track_dir = QUESTION_DIRS.get(track_slug)
        if track_dir is None:
            continue

        for file_path in sorted(track_dir.glob("*.json")):
            if file_path.stem == "schemas":
                continue
            with file_path.open("r", encoding="utf-8") as handle:
                questions = json.load(handle)

            for question in questions:
                if question.get("type") != "scenario":
                    continue
                qid = question.get("id", "<unknown>")
                title = question.get("title", "<untitled>")

                # Must have non-empty description
                if not str(question.get("description", "")).strip():
                    errors.append(f"{track_slug} {qid} {title}: scenario type requires a non-empty description")

                # Must have at least one observation anchor: code_snippet or scenario_context
                has_code = bool(str(question.get("code_snippet") or "").strip())
                has_context = bool(str(question.get("scenario_context") or "").strip())
                if not (has_code or has_context):
                    errors.append(
                        f"{track_slug} {qid} {title}: scenario type must have code_snippet or scenario_context (at least one observation anchor)"
                    )

                # All 4 option strings must be substantive (>=20 chars each)
                options = question.get("options", [])
                for i, opt in enumerate(options):
                    if isinstance(opt, str) and len(opt.strip()) < 20:
                        errors.append(
                            f"{track_slug} {qid} {title}: scenario option {i} is too short (< 20 chars) — distractors must be substantive"
                        )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"MCQ scenario validation failed:\n{joined}")


def _validate_hints() -> None:
    errors: list[str] = []

    for track, file_path in _iter_question_files():
        difficulty = file_path.stem
        min_hints, max_hints = _HINT_COUNT_RULES[track][difficulty]

        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for question in questions:
            qid = question.get("id", "<unknown>")
            title = question.get("title", "<untitled>")
            hints = question.get("hints")

            if not isinstance(hints, list) or not hints:
                errors.append(f"{track} {qid} {title}: hints must be a non-empty list")
                continue

            if len(hints) < min_hints or len(hints) > max_hints:
                errors.append(
                    f"{track} {qid} {title}: expected {min_hints}-{max_hints} hints, found {len(hints)}"
                )

            normalized_seen: set[str] = set()
            for hint in hints:
                if not isinstance(hint, str) or not hint.strip():
                    errors.append(f"{track} {qid} {title}: hints must be non-empty strings")
                    continue

                normalized = re.sub(r"\s+", " ", hint.strip().lower())
                if normalized in normalized_seen:
                    errors.append(f"{track} {qid} {title}: duplicate hint '{hint}'")
                    continue
                normalized_seen.add(normalized)

            first_hint = hints[0] if hints else ""
            for pattern in _FIRST_HINT_LEAK_PATTERNS[track]:
                if isinstance(first_hint, str) and pattern.search(first_hint):
                    errors.append(
                        f"{track} {qid} {title}: first hint is too implementation-specific ('{first_hint}')"
                    )
                    break

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining > 0:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"Hint validation failed:\n{joined}")


def _validate_mock_fields() -> None:
    """Validate new mock-only question fields: mock_only, follow_up_id, framing, type=reverse/debug."""
    errors: list[str] = []

    # Pass 1: collect all question IDs per track for follow_up_id cross-reference
    all_ids_by_track: dict[str, set[int]] = {track: set() for track in QUESTION_DIRS}
    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)
        for q in questions:
            qid = q.get("id")
            if qid is not None:
                all_ids_by_track[track].add(int(qid))

    # Pass 2: validate per-question mock fields
    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")

            # mock_only must be boolean if present
            if "mock_only" in q and not isinstance(q["mock_only"], bool):
                errors.append(
                    f"{track} {qid} {title}: mock_only must be boolean, got {type(q['mock_only']).__name__}"
                )

            # follow_up_id must be integer if present, and must resolve within the same track
            if "follow_up_id" in q:
                if not isinstance(q["follow_up_id"], int):
                    errors.append(f"{track} {qid} {title}: follow_up_id must be an integer")
                elif int(q["follow_up_id"]) not in all_ids_by_track[track]:
                    errors.append(
                        f"{track} {qid} {title}: follow_up_id {q['follow_up_id']} does not exist in this track"
                    )

            # framing — allowed values only
            if "framing" in q and q["framing"] not in ("scenario",):
                errors.append(
                    f"{track} {qid} {title}: framing must be 'scenario', got '{q['framing']}'"
                )

            # type: "reverse" requires non-empty result_preview (SQL and Pandas only)
            if q.get("type") == "reverse" and track in ("sql", "python-data"):
                result_preview = q.get("result_preview")
                if not isinstance(result_preview, list) or len(result_preview) == 0:
                    errors.append(
                        f"{track} {qid} {title}: type=reverse requires non-empty result_preview array"
                    )
                elif len(result_preview) > 8:
                    errors.append(
                        f"{track} {qid} {title}: result_preview must have ≤8 rows for UI fit"
                    )

            # type: "debug" requires debug_error and starter_code/starter_query (SQL and Pandas only)
            # Note: PySpark uses "debug" type differently (MCQ-style), no debug_error needed there
            if q.get("type") == "debug" and track in ("sql", "python-data"):
                if not str(q.get("debug_error", "") or "").strip():
                    errors.append(
                        f"{track} {qid} {title}: type=debug requires non-empty debug_error string"
                    )
                has_starter = (
                    bool(str(q.get("starter_code", "") or "").strip())
                    or bool(str(q.get("starter_query", "") or "").strip())
                )
                if not has_starter:
                    errors.append(
                        f"{track} {qid} {title}: type=debug requires starter_code (Python/Pandas) or starter_query (SQL)"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining > 0:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"Mock field validation failed:\n{joined}")


def _validate_paths(paths: list[dict], catalogs_by_topic: dict[str, dict[str, list[dict]]]) -> None:
    valid_topics = {t.slug for t in TRACKS}
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
    content_dirs = list(QUESTION_DIRS.values()) + [BACKEND_ROOT / "content" / "paths"]
    for content_dir in content_dirs:
        for file_path in sorted(content_dir.glob("*.json")):
            _load_json_file(file_path)

    # Validate loader-level schemas and references.
    paths = get_all_paths()

    catalogs_by_topic = {
        t.slug: t.catalog_module.get_questions_by_difficulty()
        for t in TRACKS
    }
    _validate_paths(paths, catalogs_by_topic)
    _validate_concepts()
    _validate_hints()
    _validate_mcq_scenario_questions()
    _validate_mock_fields()

    print("Content validation passed")


if __name__ == "__main__":
    main()
