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


def _validate_statistics_subtypes() -> None:
    """Validate that every statistics question has a valid subtype and per-subtype required fields."""
    from tracks import TRACKS as _TRACKS
    stats_track = next((t for t in _TRACKS if t.slug == "statistics"), None)
    if stats_track is None:
        return
    errors: list[str] = []
    track_dir = stats_track.content_dir
    for file_path in sorted(track_dir.glob("*.json")):
        if file_path.stem == "schemas":
            continue
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)
        for q in questions:
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            subtype = q.get("subtype")
            if subtype not in ("conceptual", "numerical"):
                errors.append(f"statistics {qid} {title}: subtype must be 'conceptual' or 'numerical', got {subtype!r}")
                continue
            if subtype == "conceptual":
                for field in ("options", "correct_option", "explanation"):
                    if field not in q:
                        errors.append(f"statistics {qid} {title}: conceptual question missing field '{field}'")
                options = q.get("options", [])
                correct = q.get("correct_option")
                if isinstance(options, list) and isinstance(correct, int):
                    if correct < 0 or correct >= len(options):
                        errors.append(f"statistics {qid} {title}: correct_option={correct} out of range for {len(options)} options")
            else:  # numerical
                for field in ("expected_code", "test_cases", "explanation"):
                    if field not in q:
                        errors.append(f"statistics {qid} {title}: numerical question missing field '{field}'")
                if not isinstance(q.get("test_cases"), list) or len(q.get("test_cases", [])) == 0:
                    errors.append(f"statistics {qid} {title}: test_cases must be a non-empty list")
    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        raise ValueError(f"Statistics subtype validation failed:\n{joined}")


def _validate_mcq_scenario_questions() -> None:
    """Validate scenario-type MCQ questions (any track) have required observation anchors and rich options."""
    from tracks import TRACKS as _TRACKS
    # Pure MCQ tracks + statistics (for its conceptual questions only)
    mcq_track_slugs = {t.slug for t in _TRACKS if t.eval_kind == "mcq"}
    mixed_track_slugs = {t.slug for t in _TRACKS if t.mixed_subtype}
    errors: list[str] = []

    for track_slug in mcq_track_slugs | mixed_track_slugs:
        track_dir = QUESTION_DIRS.get(track_slug)
        if track_dir is None:
            continue

        for file_path in sorted(track_dir.glob("*.json")):
            if file_path.stem == "schemas":
                continue
            with file_path.open("r", encoding="utf-8") as handle:
                questions = json.load(handle)

            for question in questions:
                # For mixed-subtype tracks (statistics), only validate conceptual scenario questions
                if track_slug in mixed_track_slugs and question.get("subtype") != "conceptual":
                    continue
                if question.get("type") != "scenario":
                    continue
                qid = question.get("id", "<unknown>")
                title = question.get("title", "<untitled>")

                # Must have non-empty description
                if not str(question.get("description", "")).strip():
                    errors.append(f"{track_slug} {qid} {title}: scenario type requires a non-empty description")

                # Must have at least one observation anchor: code_snippet, scenario_context, or description
                # (description serves as the anchor for textual scenario questions authored before this rule)
                has_code = bool(str(question.get("code_snippet") or "").strip())
                has_context = bool(str(question.get("scenario_context") or "").strip())
                has_desc = bool(str(question.get("description") or "").strip())
                if not (has_code or has_context or has_desc):
                    errors.append(
                        f"{track_slug} {qid} {title}: scenario type must have code_snippet, scenario_context, or description (at least one observation anchor)"
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

            # type: "debug" requires debug_error and starter_code/starter_query (SQL, Pandas, Python)
            # Note: PySpark uses "debug" type differently (MCQ-style), no debug_error needed there
            if q.get("type") == "debug" and track in ("sql", "python-data", "python"):
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


_TAXONOMY_VALIDATED_TRACKS: frozenset[str] = frozenset({
    "sql",
    "python",         # Python Phase 2: registry complete, all practice/mock tags validated
    "python-data",    # Pandas Phase 2: registry complete, all 112 practice tags validated
    # Add a track here once its concept_families.py registry is fully populated.
})


def _validate_concept_taxonomy() -> None:
    """Every concept tag must resolve to a registered family for its track.

    Tags that remain unresolved (resolve_to_family returns the input unchanged
    and that string is not itself a registered family name) are authoring errors.
    SQL blocklist tags (REVERSE SQL, DEBUG SQL, OR, etc.) are also caught here
    because they have no registered family and won't match any pattern.

    Only runs for tracks listed in _TAXONOMY_VALIDATED_TRACKS.
    """
    from concept_families import CONCEPT_FAMILIES, resolve_to_family

    errors: list[str] = []

    for track, file_path in _iter_question_files():
        if track not in _TAXONOMY_VALIDATED_TRACKS:
            continue
        # Only check tracks whose families are fully registered in concept_families.py
        families = CONCEPT_FAMILIES.get(track)
        if not families:
            continue

        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            for concept in q.get("concepts", []):
                if not isinstance(concept, str):
                    continue
                resolved = resolve_to_family(concept, track)
                if resolved == concept.upper() and resolved not in families:
                    errors.append(
                        f"{track} {qid} {title}: concept tag {concept!r} does not resolve to any registered family"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = max(0, len(errors) - 200)
        if remaining:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"Concept taxonomy validation failed:\n{joined}")


def _validate_mock_only_realism() -> None:
    """Validate mock-only realism family constraints.

    Rules:
    - Realism families (METRIC INTERPRETATION & DENOMINATOR CHOICE, OUTPUT SANITY
      VALIDATION, PERFORMANCE-AWARE ANALYTICS, ...) must appear only on mock_only=true.
    - A realism family must co-occur with ≥1 practice-grounded family (i.e. must
      not be the question's *only* resolved family).
    """
    from concept_families import CONCEPT_FAMILIES, MOCK_ONLY_REALISM_FAMILIES, resolve_to_family

    errors: list[str] = []

    for track, file_path in _iter_question_files():
        if track not in _TAXONOMY_VALIDATED_TRACKS:
            continue
        realism = MOCK_ONLY_REALISM_FAMILIES.get(track, set())
        if not realism:
            continue
        families = CONCEPT_FAMILIES.get(track, {})

        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            concepts = q.get("concepts", [])
            resolved_families = [resolve_to_family(c, track) for c in concepts if isinstance(c, str)]
            realism_present = [f for f in resolved_families if f in realism]

            if not realism_present:
                continue

            # Rule 1: realism families only on mock_only questions
            if not q.get("mock_only", False):
                for fam in realism_present:
                    errors.append(
                        f"{track} {qid} {title}: realism family {fam!r} may only appear on mock_only questions"
                    )

            # Rule 2: must co-occur with at least one practice-grounded family
            practice_grounded = [f for f in resolved_families if f in families and f not in realism]
            if not practice_grounded:
                errors.append(
                    f"{track} {qid} {title}: all concept tags resolve to realism families only — "
                    f"must co-occur with ≥1 practice-grounded family"
                )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        raise ValueError(f"Mock-only realism family validation failed:\n{joined}")


_DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def _validate_chain_integrity() -> None:
    """Validate follow-up chain structure.

    Rules (from authoring agent):
    - follow_ups[] on a parent must all exist in the SAME TRACK (may be a harder difficulty)
    - Child difficulty must be >= parent difficulty (no down-difficulty chains)
    - Each child listed in follow_ups must have mock_only=true
    - Each child must have parent_id matching the parent's id
    - Each child must have a follow_up_dimension
    - Chain length 2-4 (parent + 1-3 children)
    - No nested chains: children must not themselves have follow_ups
    - No shared children: each child belongs to exactly one parent
    - No easy mock_only (checked here to complement _validate_mock_fields)
    """
    errors: list[str] = []

    # Build a full cross-difficulty lookup: {track: {id: (question, difficulty)}}
    track_all_questions: dict[str, dict[int, tuple[dict, str]]] = {}
    for track, file_path in _iter_question_files():
        difficulty = file_path.stem
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)
        if track not in track_all_questions:
            track_all_questions[track] = {}
        for q in questions:
            qid = int(q.get("id", 0))
            if qid:
                track_all_questions[track][qid] = (q, difficulty)

    all_children_seen: dict[str, set[int]] = {}  # track -> set of child IDs

    for track, file_path in _iter_question_files():
        difficulty = file_path.stem
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        if track not in all_children_seen:
            all_children_seen[track] = set()

        track_lookup = track_all_questions.get(track, {})

        for q in questions:
            qid = int(q.get("id", 0))
            title = q.get("title", "<untitled>")

            # Validate chains defined on this parent
            follow_ups = q.get("follow_ups", [])
            if follow_ups:
                if not isinstance(follow_ups, list):
                    errors.append(f"{track} {qid} {title}: follow_ups must be a list")
                    continue

                child_count = len(follow_ups)
                if child_count > 3:
                    errors.append(
                        f"{track} {qid} {title}: chain has {child_count} follow-ups (max 3, chain length 2-4)"
                    )

                for child_id in follow_ups:
                    child_id = int(child_id)
                    if child_id in all_children_seen[track]:
                        errors.append(
                            f"{track} {qid} {title}: child {child_id} is shared across multiple parent chains"
                        )
                    all_children_seen[track].add(child_id)

                    if child_id not in track_lookup:
                        errors.append(
                            f"{track} {qid} {title}: follow_ups child {child_id} not found in any difficulty file for track"
                        )
                        continue

                    child, child_diff = track_lookup[child_id]
                    c_title = child.get("title", "<untitled>")

                    # Child difficulty must be >= parent difficulty
                    if _DIFFICULTY_ORDER.get(child_diff, 0) < _DIFFICULTY_ORDER.get(difficulty, 0):
                        errors.append(
                            f"{track} {qid} {title}: chain child {child_id} is at {child_diff!r} "
                            f"difficulty (parent is {difficulty!r}) — child must be same or harder"
                        )

                    if not child.get("mock_only", False):
                        errors.append(
                            f"{track} {child_id} {c_title}: chain child must have mock_only=true"
                        )

                    if int(child.get("parent_id", 0)) != qid:
                        errors.append(
                            f"{track} {child_id} {c_title}: parent_id {child.get('parent_id')!r} does not match parent {qid}"
                        )

                    if not child.get("follow_up_dimension"):
                        errors.append(
                            f"{track} {child_id} {c_title}: chain child must have follow_up_dimension"
                        )

                    if child.get("follow_ups"):
                        errors.append(
                            f"{track} {child_id} {c_title}: nested chains not allowed (child has follow_ups)"
                        )

            # No mock_only at easy
            if q.get("mock_only", False) and difficulty == "easy":
                errors.append(f"{track} {qid} {title}: mock_only=true not allowed at easy difficulty")

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        raise ValueError(f"Chain integrity validation failed:\n{joined}")


def _validate_paths(paths: list[dict], catalogs_by_topic: dict[str, dict[str, list[dict]]]) -> None:
    """Content-integrity rules for learning paths.

    See ``docs/content-authoring.md`` §Paths for the canonical definition of
    each rule and the reasoning behind it.

    Rules:
      1. Required schema fields present; slug unique; file matches slug.
      2. ``role`` in {starter, intermediate, advanced}; exactly one ``starter``
         per track (UX promise: every track has one obvious entry point).
         No upper bound on intermediate or advanced.
      3. ``patterns[]`` non-empty; each entry resolves to the track's registry
         in ``path_patterns.py``.
      4. ``focus_concepts[]`` non-empty; each entry resolves to a registered
         family in ``concept_families.py`` for the track (same rule the
         question validator already applies).
      5. Every question in ``questions[]`` carries at least one concept tag
         that resolves to the same family as at least one of the path's
         ``focus_concepts[]`` — mechanical guarantee that the path actually
         drills what it claims.
      6. ``recommended_after[]`` references real path slugs in the same track;
         the resulting graph is acyclic.
    """
    from concept_families import CONCEPT_FAMILIES, resolve_to_family, concept_matches_focus
    from path_patterns import PATH_PATTERNS

    valid_topics = {t.slug for t in TRACKS}
    valid_tiers = {"free", "pro"}
    valid_roles = {"starter", "intermediate", "advanced"}

    required_fields = {
        "slug", "title", "description", "topic", "questions",
        "tier", "role", "patterns", "focus_concepts",
    }

    path_files = {p.stem for p in (BACKEND_ROOT / "content" / "paths").glob("*.json")}
    slugs = set()
    starter_counts: dict[str, int] = {topic: 0 for topic in valid_topics}

    # Build question lookup by topic for tag inspection (rule 5).
    questions_by_id: dict[str, dict[int, dict]] = {}
    for topic, grouped in catalogs_by_topic.items():
        questions_by_id[topic] = {
            int(q["id"]): q for diff in grouped.values() for q in diff
        }
    ids_by_topic = {topic: set(lookup.keys()) for topic, lookup in questions_by_id.items()}

    # Pass 1: per-path field validation (rules 1–5).
    paths_by_topic: dict[str, dict[str, dict]] = {topic: {} for topic in valid_topics}

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

        # Rule 3: patterns
        patterns = path["patterns"]
        if not isinstance(patterns, list) or not patterns:
            raise ValueError(f"Path {slug} has empty or invalid patterns[]")
        track_patterns = PATH_PATTERNS.get(topic, {})
        for pat in patterns:
            if pat not in track_patterns:
                raise ValueError(
                    f"Path {slug}: pattern '{pat}' not in registry for track '{topic}'. "
                    f"Register it in backend/path_patterns.py or use an existing slug. "
                    f"Available: {sorted(track_patterns.keys())}"
                )

        # Rule 4: focus_concepts resolve to track's concept families.
        # Only enforced for taxonomy-validated tracks (mirrors the
        # question-concept validator's _TAXONOMY_VALIDATED_TRACKS gate).
        # Other tracks: presence check only — full resolution is enforced
        # once their concept-family registry is complete.
        focus_concepts = path["focus_concepts"]
        if not isinstance(focus_concepts, list) or not focus_concepts:
            raise ValueError(f"Path {slug} has empty or invalid focus_concepts[]")
        if topic in _TAXONOMY_VALIDATED_TRACKS:
            track_families = CONCEPT_FAMILIES.get(topic, {})
            for fc in focus_concepts:
                resolved = resolve_to_family(fc, topic)
                if resolved not in track_families:
                    raise ValueError(
                        f"Path {slug}: focus_concept '{fc}' does not resolve to a registered "
                        f"family for track '{topic}' (resolved to '{resolved}'). "
                        f"Use a concept that maps to one of: {sorted(track_families.keys())}"
                    )

        # Rule 1 (continued): question IDs valid
        questions = [int(qid) for qid in path["questions"]]
        if not questions:
            raise ValueError(f"Path {slug} has no questions")
        if len(questions) != len(set(questions)):
            raise ValueError(f"Path {slug} has duplicate question IDs")

        unknown = sorted(qid for qid in questions if qid not in ids_by_topic[topic])
        if unknown:
            raise ValueError(f"Path {slug} references unknown question IDs for topic {topic}: {unknown}")

        # Rule 5: every question carries a tag in same family as one focus_concept
        for qid in questions:
            q = questions_by_id[topic][qid]
            q_concepts = q.get("concepts", []) or []
            match = False
            for qc in q_concepts:
                for fc in focus_concepts:
                    if concept_matches_focus(qc, fc, topic):
                        match = True
                        break
                if match:
                    break
            if not match:
                raise ValueError(
                    f"Path {slug}: question {qid} ('{q.get('title', '<untitled>')}') has no concept tag "
                    f"that resolves to the same family as any of the path's focus_concepts. "
                    f"Question concepts: {q_concepts}. Path focus_concepts: {focus_concepts}"
                )

        # Rule 2 (continued): track starter count
        if role == "starter":
            starter_counts[topic] += 1

        paths_by_topic[topic][slug] = path

    # Rule 2: exactly one starter per track
    for topic in valid_topics:
        if starter_counts[topic] != 1:
            raise ValueError(
                f"Topic {topic} must have exactly one starter path (found {starter_counts[topic]})"
            )

    # Rule 6: recommended_after references + acyclic
    for topic, topic_paths in paths_by_topic.items():
        for slug, path in topic_paths.items():
            prereqs = path.get("recommended_after", []) or []
            for prereq in prereqs:
                if prereq not in topic_paths:
                    raise ValueError(
                        f"Path {slug}: recommended_after references '{prereq}' which is not a path in track '{topic}'"
                    )
        # DFS cycle detection per track
        visiting: set[str] = set()
        visited: set[str] = set()

        def _dfs(node: str, stack: list[str]) -> None:
            if node in visiting:
                cycle = " → ".join(stack[stack.index(node):] + [node])
                raise ValueError(f"Path cycle in track {topic}: {cycle}")
            if node in visited:
                return
            visiting.add(node)
            stack.append(node)
            for prereq in topic_paths[node].get("recommended_after", []) or []:
                _dfs(prereq, stack)
            stack.pop()
            visiting.remove(node)
            visited.add(node)

        for slug in topic_paths:
            _dfs(slug, [])


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
    _validate_concept_taxonomy()
    _validate_mock_only_realism()
    _validate_chain_integrity()
    _validate_hints()
    _validate_statistics_subtypes()
    _validate_mcq_scenario_questions()
    _validate_mock_fields()

    print("Content validation passed")


if __name__ == "__main__":
    main()
