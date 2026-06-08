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

# Sample-question files participate in the same canonical-name + duplicate-family
# taxonomy checks as practice/mock. The mapping mirrors
# backend/sample_questions.py:_TRACK_SAMPLE_FILES but keys by validator-style
# track slug (e.g. "python-data", not "python_data") so the iteration aligns
# with QUESTION_DIRS and _TAXONOMY_VALIDATED_TRACKS membership.
_SAMPLE_DIR = BACKEND_ROOT / "content" / "sample_questions"
SAMPLE_FILES: dict[str, Path] = {
    "sql": _SAMPLE_DIR / "sql.json",
    "python": _SAMPLE_DIR / "python.json",
    "python-data": _SAMPLE_DIR / "pandas.json",
    "pyspark": _SAMPLE_DIR / "pyspark.json",
    "data-engineering": _SAMPLE_DIR / "data_engineering.json",
    "data-modeling": _SAMPLE_DIR / "data_modeling.json",
    "statistics": _SAMPLE_DIR / "statistics.json",
    "ml-fundamentals": _SAMPLE_DIR / "ml_fundamentals.json",
    "experimentation": _SAMPLE_DIR / "experimentation.json",
}

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
    # Sample-question files participate in the taxonomy + hint checks. All
    # tracks including SQL now have concepts/hints (Phase 4c, 2026-06-01).
    for track, sample_file in SAMPLE_FILES.items():
        if sample_file.exists():
            files.append((track, sample_file))
    return files


def _validate_concepts() -> None:
    from concept_families import resolve_to_family

    errors: list[str] = []
    nearduplicate_warnings: list[str] = []
    # Tracks where the near-duplicate-tag rule is mechanically enforced as an error.
    # Other tracks emit stderr warnings until their per-track cleanup pass lands.
    NEARDUP_ENFORCED = {"pyspark"}

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

            if len(concepts) < 1 or len(concepts) > 5:
                errors.append(
                    f"{track} {qid} {title}: expected 1-5 concept tags, found {len(concepts)}"
                )

            normalized_seen: set[str] = set()
            # Per-question near-duplicate check: no two tags may resolve to the
            # same canonical family (content-authoring.md §Concept-tag contract).
            family_seen_tags: dict[str, str] = {}
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

                # Near-duplicate (same-family) check
                fam = resolve_to_family(concept, track)
                if fam is not None:
                    prior = family_seen_tags.get(fam)
                    if prior is not None:
                        msg = (
                            f"{track} {qid} {title}: tags '{prior}' and '{concept}' both resolve to "
                            f"family '{fam}' — use the canonical family name once instead of multiple sub-patterns"
                        )
                        if track in NEARDUP_ENFORCED:
                            errors.append(msg)
                        else:
                            nearduplicate_warnings.append(msg)
                    else:
                        family_seen_tags[fam] = concept

    if nearduplicate_warnings:
        sys.stderr.write(
            f"WARNING: near-duplicate concept tags in {len(nearduplicate_warnings)} cases "
            f"across non-enforced tracks (each track to be cleaned in its own audit pass):\n"
        )
        for w in nearduplicate_warnings[:20]:
            sys.stderr.write(f"  - {w}\n")
        if len(nearduplicate_warnings) > 20:
            sys.stderr.write(f"  - ... and {len(nearduplicate_warnings) - 20} more\n")

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


def _validate_code_reference_reproduces_tests() -> None:
    """The reference solution must reproduce every literal test-case `expected` it ships with.

    This is the recurrence guard for the Phase-4 finding: a stored test-case
    `expected` value that the question's own `expected_code` no longer produces
    is silently ungradeable — the platform graded the user against a number the
    reference itself misses (73047: stored 0.9809, reference yields 0.9805).

    Scope is precisely the two tracks that ship *stored* expected values:
      - python      (all questions: expected_code + test_cases)
      - statistics  (numerical subtype only; conceptual is MCQ)
    SQL and pandas compute their expected output live from the reference at
    grade time, so they cannot drift this way and are out of scope here.

    Only *literal* cases are checked. Generator-spec inputs / {"compute":
    "reference"} cases derive their expected from the reference at run time, so
    by construction they cannot disagree with it. The declared per-case
    `tolerance` is honored exactly as the live grader does (1e-6 floor), so an
    intentionally approximate Monte-Carlo answer is not flagged.
    """
    import signal as _signal

    from python_sandbox_harness import _compare  # tolerance-aware, mirrors live grading

    class _RefTimeout(Exception):
        pass

    def _alarm(_sig, _frame):
        raise _RefTimeout()

    def _is_literal_case(tc: dict) -> bool:
        inp = tc.get("input", [])
        if any(isinstance(a, dict) and "gen" in a for a in inp):
            return False
        exp = tc.get("expected") if "expected" in tc else tc.get("expected_output")
        if isinstance(exp, dict) and exp.get("compute") == "reference":
            return False
        return True

    targets: list[tuple[str, Path]] = [("python", QUESTION_DIRS["python"])]
    if "statistics" in QUESTION_DIRS:
        targets.append(("statistics", QUESTION_DIRS["statistics"]))

    errors: list[str] = []
    has_alarm = hasattr(_signal, "SIGALRM")
    if has_alarm:
        _prev = _signal.signal(_signal.SIGALRM, _alarm)
    try:
        for track, directory in targets:
            for file_path in sorted(directory.glob("*.json")):
                if file_path.stem == "schemas":
                    continue
                with file_path.open("r", encoding="utf-8") as handle:
                    questions = json.load(handle)
                for q in questions:
                    if track == "statistics" and q.get("subtype") != "numerical":
                        continue
                    code = q.get("expected_code")
                    cases = q.get("test_cases")
                    if not code or not isinstance(cases, list) or not cases:
                        continue
                    qid = q.get("id", "<unknown>")
                    title = q.get("title", "<untitled>")
                    if has_alarm:
                        _signal.alarm(10)
                    try:
                        ns: dict = {}
                        exec(code, ns)  # noqa: S102 — vetted authored reference
                        solve = ns.get("solve")
                        if not callable(solve):
                            errors.append(f"{track} {qid} {title}: expected_code defines no callable solve()")
                            continue
                        for idx, tc in enumerate(cases):
                            if not _is_literal_case(tc):
                                continue
                            exp = tc.get("expected") if "expected" in tc else tc.get("expected_output")
                            tol = tc.get("tolerance", 1e-6)
                            try:
                                actual = solve(*tc.get("input", []))
                            except Exception as exc:
                                errors.append(f"{track} {qid} {title}: reference raised on test_case[{idx}]: {exc!r}")
                                continue
                            if not _compare(actual, exp, tol):
                                errors.append(
                                    f"{track} {qid} {title}: reference does not reproduce test_case[{idx}] "
                                    f"expected={exp!r} (got {actual!r}, tolerance={tol})"
                                )
                    except _RefTimeout:
                        errors.append(f"{track} {qid} {title}: reference solution timed out (>10s) during validation")
                    except Exception as exc:
                        errors.append(f"{track} {qid} {title}: reference solution failed to execute: {exc!r}")
                    finally:
                        if has_alarm:
                            _signal.alarm(0)
    finally:
        if has_alarm:
            _signal.signal(_signal.SIGALRM, _prev)

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        raise ValueError(f"Code reference-reproduces-tests validation failed:\n{joined}")


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
        # For practice/mock files (easy.json/medium.json/hard.json), every
        # question shares the file's difficulty. For sample files (e.g.,
        # pyspark.json), all 3 difficulties are mixed in one file. Read
        # difficulty from the question field — works uniformly for both.
        file_stem_difficulty = file_path.stem if file_path.stem in ("easy", "medium", "hard") else None
        is_sample = file_path.parent.name == "sample_questions"

        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for question in questions:
            qid = question.get("id", "<unknown>")
            title = question.get("title", "<untitled>")
            hints = question.get("hints")
            difficulty = question.get("difficulty") or file_stem_difficulty

            if not isinstance(hints, list) or not hints:
                errors.append(f"{track} {qid} {title}: hints must be a non-empty list")
                continue

            if difficulty in _HINT_COUNT_RULES.get(track, {}):
                min_hints, max_hints = _HINT_COUNT_RULES[track][difficulty]
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

            # First-hint leak-pattern regex check is calibrated for
            # practice/mock content. Sample-tier content has its own audit
            # cadence (sample-bank audit fix, 2026-06-01) and is exempt from
            # the strict per-track patterns — samples often legitimately
            # reference their own question subject (e.g., DM 612 is literally
            # titled "...Grain..."; the H1 mentioning "grain" is question
            # context, not a leak). Canonical-name + concept-blocklist +
            # near-duplicate checks still apply via _validate_concepts.
            if is_sample:
                continue

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
    "python",             # Python Phase 2: registry complete, all practice/mock tags validated
    "python-data",        # Pandas Phase 2: registry complete, all 112 practice tags validated
    "pyspark",            # PySpark Phase 2: registry complete (23 families), no realism families by design (MCQ-only), 0e/75m/75h mock-only validated; added 2026-05-25 post-closure cleanup (0 orphans across 278 questions)
    "data-engineering",   # DE Phase 2: registry complete, 21 families, 0e/50m/60h mock-only validated
    "data-modeling",      # DM Phase 2: registry complete (22 families), 0 realism families by design (MCQ-only), 0e/45m/51h mock-only validated
    "statistics",         # Statistics Phase 2: registry complete (13 families), 0e/66m/50h mock-only validated; lowercase tag convention; dual-subtype (conceptual + numerical)
    "ml-fundamentals",    # ML Fundamentals Phase 2: registry complete (29 families), 0e/66m/57h standalone mock-only + 8 chains (16 children) validated; MCQ-only, no realism families
    "experimentation",    # Experimentation Phase 2: registry complete (24 families), 0e/45m/59h mock-only validated; 10 chains (20 children); no realism families by design (MCQ-only)
    # Add a track here once its concept_families.py registry is fully populated.
})


def _warn_unenforced_tracks() -> None:
    """Emit a stderr warning listing tracks where tag-family resolution is skipped.

    The silent-skip in _validate_concept_taxonomy and _validate_mock_only_realism
    historically produced false-positive PASS reports during authoring rounds for
    tracks outside _TAXONOMY_VALIDATED_TRACKS. This warning makes the skip visible
    so authoring sessions cannot miss it. See docs/content-authoring.md §
    Validator coverage state.
    """
    import sys
    skipped: list[str] = []
    for track, _ in _iter_question_files():
        if track not in _TAXONOMY_VALIDATED_TRACKS and track not in skipped:
            skipped.append(track)
    if skipped:
        print(
            "WARNING: tag-family resolution and realism rules NOT enforced for: "
            + ", ".join(sorted(skipped))
            + ". See docs/content-authoring.md § Validator coverage state.",
            file=sys.stderr,
        )


def _validate_concept_taxonomy() -> None:
    """Every concept tag must (a) resolve to a registered family for its track
    AND (b) be written as the canonical family name itself, not a sub-pattern
    or alias that resolves via match_patterns.

    Rule (a) catches unresolvable tags — SQL blocklist values (REVERSE SQL,
    DEBUG SQL, OR, etc.) and typos. Rule (b) catches the historical hole where
    a sub-pattern like 'CLASSIFICATION METRICS & EVALUATION' resolves to
    'CLASSIFICATION METRICS' but isn't itself the canonical name. Sub-patterns
    exist for resolution and analytics, NOT as tag values (see authoring agent
    § Tag lookup procedure and docs/concept-taxonomy.md). Resolution ≠
    authoring permission.

    Comparison is case-insensitive because Statistics uses a lowercase
    convention while every other track uses uppercase.

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
                # Rule (a): unresolvable tag — resolver returned its input unchanged
                # and that string isn't itself a registered family name.
                if resolved == concept.upper() and resolved not in families:
                    errors.append(
                        f"{track} {qid} {title}: concept tag {concept!r} does not resolve to any registered family"
                    )
                    continue
                # Rule (b): tag resolves but isn't the canonical family name —
                # author wrote a sub-pattern / alias instead of the family header.
                if resolved in families and concept.strip().lower() != resolved.lower():
                    errors.append(
                        f"{track} {qid} {title}: concept tag {concept!r} is a sub-pattern of family "
                        f"{resolved!r} — write the canonical family name as the tag value, not the alias"
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


def _validate_per_family_coverage() -> None:
    """Emit warnings for per-family coverage rule breaches.

    Rules (see docs/content-authoring.md § Per-family coverage discipline):
      1. Practice floor: every applicable family has ≥1 practice question per
         applicable tier. (Tier applicability is judged on whether the family
         has any presence in that tier — i.e. we don't enforce e.g. "every
         family must have an easy question" since some families are inherently
         medium/hard. Floor is: if family appears in mock-only at a tier, it
         must appear in practice at that tier OR lower.)
      2. Mock-only floor: every practice-grounded family has ≥4 mock-only.
      3. Max-share ceiling: no family is tagged on >50% of questions in either
         tier (practice and mock-only computed independently).
      4. Zero dead families: every registered family appears in mock-only ≥1.
      5. Realism families exempt from rule 2 (still bounded by rule 3).

    Soft (warnings only, not errors) because rules 6 + 7 — quality override
    and load-bearing exceptions defended in track-docs — are real override
    paths. Stage C audit cross-references warnings to documented exceptions.

    Gated on _TAXONOMY_VALIDATED_TRACKS; tracks outside the set get a separate
    warning via _warn_unenforced_tracks().
    """
    import sys
    from collections import Counter
    from concept_families import (
        CONCEPT_FAMILIES,
        MOCK_ONLY_REALISM_FAMILIES,
        resolve_to_family,
    )

    warnings: list[str] = []

    for track in sorted(_TAXONOMY_VALIDATED_TRACKS):
        families = CONCEPT_FAMILIES.get(track)
        if not families:
            continue
        realism = MOCK_ONLY_REALISM_FAMILIES.get(track, set())

        # Tally per-tier, per-family presence.
        practice_per_family: dict[str, Counter] = {
            f: Counter() for f in families
        }
        mock_per_family: dict[str, Counter] = {f: Counter() for f in families}
        practice_total_per_tier: Counter = Counter()
        mock_total_per_tier: Counter = Counter()

        track_files = [
            (tk, fp) for tk, fp in _iter_question_files() if tk == track
        ]
        for _, file_path in track_files:
            tier = file_path.stem  # easy | medium | hard
            with file_path.open("r", encoding="utf-8") as handle:
                questions = json.load(handle)
            for q in questions:
                is_mock = q.get("mock_only", False)
                if is_mock:
                    mock_total_per_tier[tier] += 1
                else:
                    practice_total_per_tier[tier] += 1
                fams_in_q: set[str] = set()
                for concept in q.get("concepts", []):
                    if not isinstance(concept, str):
                        continue
                    f = resolve_to_family(concept, track)
                    if f in families:
                        fams_in_q.add(f)
                for f in fams_in_q:
                    if is_mock:
                        mock_per_family[f][tier] += 1
                    else:
                        practice_per_family[f][tier] += 1

        practice_total = sum(practice_total_per_tier.values())
        mock_total = sum(mock_total_per_tier.values())

        # Rule 4: every registered family appears in mock-only ≥1.
        for f in families:
            if sum(mock_per_family[f].values()) == 0:
                warnings.append(
                    f"{track}: family {f!r} has ZERO mock-only questions "
                    f"(rule 4 — dead family)"
                )

        # Rule 2: every practice-grounded family has ≥4 mock-only.
        for f in families:
            if f in realism:
                continue  # rule 5
            mock_count = sum(mock_per_family[f].values())
            if 0 < mock_count < 4:
                warnings.append(
                    f"{track}: family {f!r} has only {mock_count} mock-only "
                    f"questions (rule 2 — mock-only floor is 4)"
                )

        # Rule 1: if family appears in mock-only at tier T, it must appear in
        # practice at tier T or lower. (Captures the "no unseen concept"
        # invariant at tier-granularity.) Realism families are exempt by
        # design — they are mock-only-only and never have practice content.
        difficulty_order = ["easy", "medium", "hard"]
        for f in families:
            if f in realism:
                continue
            for tier in difficulty_order:
                if mock_per_family[f][tier] == 0:
                    continue
                tier_idx = difficulty_order.index(tier)
                allowed = difficulty_order[: tier_idx + 1]
                practice_at_or_below = sum(
                    practice_per_family[f][t] for t in allowed
                )
                if practice_at_or_below == 0:
                    warnings.append(
                        f"{track}: family {f!r} has mock-only at {tier} but "
                        f"NO practice question at {tier} or lower "
                        f"(rule 1 — practice floor)"
                    )

        # Rule 3: per-tier max-share ceiling 50%.
        for f in families:
            p_count = sum(practice_per_family[f].values())
            m_count = sum(mock_per_family[f].values())
            if practice_total > 0:
                share = p_count / practice_total
                if share > 0.50:
                    warnings.append(
                        f"{track}: family {f!r} tagged on "
                        f"{share*100:.1f}% of practice questions "
                        f"({p_count}/{practice_total}) — exceeds rule 3 "
                        f"50% ceiling. Document as load-bearing in "
                        f"docs/tracks/{track.replace('-','-')}.md with "
                        f"reasoning-depth defence, or remediate."
                    )
            if mock_total > 0:
                share = m_count / mock_total
                if share > 0.50:
                    warnings.append(
                        f"{track}: family {f!r} tagged on "
                        f"{share*100:.1f}% of mock-only questions "
                        f"({m_count}/{mock_total}) — exceeds rule 3 "
                        f"50% ceiling. Document as load-bearing in "
                        f"docs/tracks/{track.replace('-','-')}.md with "
                        f"reasoning-depth defence, or remediate."
                    )

    if warnings:
        print(
            "WARNING: per-family coverage rule breaches (see "
            "docs/content-authoring.md § Per-family coverage discipline):",
            file=sys.stderr,
        )
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


def _validate_solution_code_presence() -> None:
    """Flag mock_only questions in code-execution tracks that are missing solution_code.

    solution_code is the Elite post-session debrief teaching artifact. Its absence
    causes a silent quality gap — no runtime error, just a degraded Elite experience.
    Required on all medium/hard mock_only questions in the python-data and python tracks.
    """
    CODE_EXECUTION_TRACKS = frozenset({"python-data", "python"})
    errors: list[str] = []

    for track, file_path in _iter_question_files():
        difficulty = file_path.stem
        if difficulty == "easy":
            continue  # no mock_only at easy (enforced by chain integrity validator)

        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            if not q.get("mock_only", False):
                continue
            # statistics: only numerical subtype has expected_code / solution_code
            if track == "statistics" and q.get("subtype") != "numerical":
                continue
            if track not in CODE_EXECUTION_TRACKS and track != "statistics":
                continue
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            sc = q.get("solution_code")
            if not (isinstance(sc, str) and sc.strip()):
                errors.append(
                    f"{track} {qid} {title}: mock_only question missing solution_code"
                    f" (Elite debrief artifact — required on all medium/hard mock-only)"
                )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = max(0, len(errors) - 200)
        if remaining:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"solution_code presence validation failed:\n{joined}")


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
    - No orphan children: every question with parent_id set must appear in that parent's
      follow_ups list (child→parent reverse check; historically missed and surfaced as
      a real bug in Python Q23080→Q22092 chain 2026-05-26).
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

    # Second pass: orphan-child reverse check. Every question with parent_id set must
    # appear in that parent's follow_ups[] — i.e. all_children_seen[track]. Catches the
    # case where a child claims a parent but the parent does not claim the child back.
    # The parent-direction main loop above does NOT catch this because it iterates parents
    # and walks their follow_ups; an orphan child with no parent listing it is invisible.
    for track, lookup in track_all_questions.items():
        children_claimed_by_parents = all_children_seen.get(track, set())
        for qid, (q, difficulty) in lookup.items():
            parent_id = q.get("parent_id")
            if not parent_id:
                continue
            parent_id = int(parent_id)
            title = q.get("title", "<untitled>")
            if qid not in children_claimed_by_parents:
                parent_exists = parent_id in lookup
                if parent_exists:
                    parent_q, _ = lookup[parent_id]
                    parent_follow_ups = parent_q.get("follow_ups") or []
                    errors.append(
                        f"{track} {qid} {title}: parent_id={parent_id} but parent's follow_ups={parent_follow_ups!r} "
                        f"does not list {qid} — orphan child (chain broken)"
                    )
                else:
                    errors.append(
                        f"{track} {qid} {title}: parent_id={parent_id} but parent {parent_id} not found in track"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        raise ValueError(f"Chain integrity validation failed:\n{joined}")


def _validate_paths(paths: list[dict], catalogs_by_topic: dict[str, dict[str, list[dict]]]) -> None:
    """Content-integrity rules for learning paths.

    See ``docs/content-authoring.md`` §Paths for the canonical definition of
    each rule and the reasoning behind it.

    Rules:
      1. Required schema fields present; slug unique; file matches slug.
      2. ``level`` in {foundational, intermediate, advanced}; exactly one ``foundational``
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
      7. Question→path uniqueness: every question appears in at most one path
         (across all tracks). The 1:1 curriculum-spine model — each question
         belongs to exactly one pattern walk. A question in two paths means
         a user solving it sees partial progress in both, silently violating
         the product mental model.
    """
    from concept_families import CONCEPT_FAMILIES, resolve_to_family, concept_matches_focus
    from path_patterns import PATH_PATTERNS

    valid_topics = {t.slug for t in TRACKS}
    valid_tiers = {"free", "pro"}
    valid_levels = {"foundational", "intermediate", "advanced"}

    required_fields = {
        "slug", "title", "description", "topic", "questions",
        "tier", "level", "patterns", "focus_concepts",
    }

    path_files = {p.stem for p in (BACKEND_ROOT / "content" / "paths").glob("*.json")}
    slugs = set()
    foundational_counts: dict[str, int] = {topic: 0 for topic in valid_topics}

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
        level = path["level"]

        if topic not in valid_topics:
            raise ValueError(f"Invalid topic for path {slug}: {topic}")
        if tier not in valid_tiers:
            raise ValueError(f"Invalid tier for path {slug}: {tier}")
        if level not in valid_levels:
            raise ValueError(f"Invalid level for path {slug}: {level}")

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

        # Rule 2 (continued): track foundational count
        if level == "foundational":
            foundational_counts[topic] += 1

        paths_by_topic[topic][slug] = path

    # Rule 2: exactly one foundational per track
    for topic in valid_topics:
        if foundational_counts[topic] != 1:
            raise ValueError(
                f"Topic {topic} must have exactly one foundational path (found {foundational_counts[topic]})"
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

    # Rule 7: question→path uniqueness — every question appears in at most one path.
    # The 1:1 curriculum-spine model. Violations mean a user solving one question
    # advances progress in multiple paths, silently breaking the product mental model
    # that each question belongs to exactly one pattern walk.
    from collections import defaultdict
    qid_to_paths: dict[int, list[str]] = defaultdict(list)
    for path in paths:
        for qid in path.get("questions", []):
            qid_to_paths[qid].append(path["slug"])
    dupes = {qid: pths for qid, pths in qid_to_paths.items() if len(pths) > 1}
    if dupes:
        lines = [f"  Q{qid} appears in: {sorted(pths)}" for qid, pths in sorted(dupes.items())]
        raise ValueError(
            f"Path uniqueness rule 7 violated — {len(dupes)} question(s) appear in more than one path:\n"
            + "\n".join(lines)
        )


def _validate_sample_cross_bank_titles() -> None:
    """Check that no sample question title collides with any practice or mock question title.

    Both practice and mock-only (mock_only=true) questions count — sample titles must
    not duplicate either. Comparison is case-sensitive exact match. Missing sample or
    practice files are skipped with a warning.
    """
    errors: list[str] = []

    for track, sample_file in SAMPLE_FILES.items():
        if not sample_file.exists():
            sys.stderr.write(
                f"WARNING: sample file not found, skipping cross-bank title check: {sample_file}\n"
            )
            continue

        practice_dir = QUESTION_DIRS.get(track)
        if practice_dir is None:
            continue

        # Collect all titles from the practice/mock bank (easy + medium + hard).
        practice_titles: set[str] = set()
        for practice_file in sorted(practice_dir.glob("*.json")):
            if practice_file.stem == "schemas":
                continue
            with practice_file.open("r", encoding="utf-8") as handle:
                try:
                    questions = json.load(handle)
                except json.JSONDecodeError:
                    continue
            for q in questions:
                t = q.get("title")
                if isinstance(t, str) and t:
                    practice_titles.add(t)

        # Check each sample question against the collected titles.
        with sample_file.open("r", encoding="utf-8") as handle:
            sample_questions = json.load(handle)

        for q in sample_questions:
            qid = q.get("id", "<unknown>")
            title = q.get("title", "")
            if isinstance(title, str) and title in practice_titles:
                errors.append(
                    f"SAMPLE TITLE COLLISION [{track}] sample ID {qid}: title '{title}' matches practice/mock question"
                )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"Sample cross-bank title collision:\n{joined}")


def _validate_mcq_consistency() -> None:
    """Validate MCQ option-array consistency for all question files that contain an 'options' field.

    Checks applied to every question that has an 'options' key:
      (a) correct_option is a valid zero-based integer index into the options array.
      (b) If the description text explicitly names option labels using the patterns
          r"\\bOption [A-D]\\b" or r"\\([A-D]\\)", the count of *distinct* labels
          mentioned must not exceed len(options).

    Applied to both sample files and practice/mock files in non-SQL tracks.
    """
    _LABEL_PATTERN = re.compile(r"\bOption [A-D]\b|\([A-D]\)")

    errors: list[str] = []

    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            if "options" not in q:
                continue

            qid = q.get("id", "<unknown>")
            options = q.get("options", [])
            correct = q.get("correct_option")
            description = q.get("description", "") or ""

            # (a) correct_option range check
            if isinstance(correct, int) and isinstance(options, list):
                if correct < 0 or correct >= len(options):
                    errors.append(
                        f"MCQ INDEX OUT OF RANGE [{track}] ID {qid}: "
                        f"correct_option={correct} but options has {len(options)} entries"
                    )

            # (b) label-count vs options-array-length check
            if isinstance(description, str) and isinstance(options, list):
                labels_found = set(_LABEL_PATTERN.findall(description))
                if labels_found and len(labels_found) > len(options):
                    errors.append(
                        f"MCQ LABEL COUNT MISMATCH [{track}] ID {qid}: "
                        f"description references {len(labels_found)} distinct labels (A-D) "
                        f"but options has {len(options)} entries"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"MCQ consistency validation failed:\n{joined}")


def _validate_non_sql_sample_fields() -> None:
    """Validate required fields on every question in each non-SQL sample file.

    Universal required fields (all non-SQL sample questions):
      - id (integer)
      - title (non-empty string)
      - description (non-empty string)
      - difficulty (one of: "easy", "medium", "hard")
      - hints (list with exactly 2 entries)
      - concepts (list with 1–4 entries)
      - order (integer)

    Conditional required fields (detected by presence of field in question):
      - options: must be a non-empty list
      - expected_code / expected_query: must be non-empty string
      - test_cases: must be a non-empty list

    Missing sample files are skipped with a warning.
    """
    VALID_DIFFICULTIES = {"easy", "medium", "hard"}
    errors: list[str] = []

    for track, sample_file in SAMPLE_FILES.items():
        if track == "sql":
            continue  # SQL sample has a different schema (expected_query, not expected_code)

        if not sample_file.exists():
            sys.stderr.write(
                f"WARNING: sample file not found, skipping field check: {sample_file}\n"
            )
            continue

        with sample_file.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        for q in questions:
            qid = q.get("id", "<unknown>")

            # id — must be an integer
            if not isinstance(q.get("id"), int):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'id' must be an integer"
                )

            # title — non-empty string
            title = q.get("title")
            if not (isinstance(title, str) and title.strip()):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'title' must be a non-empty string"
                )

            # description — non-empty string
            description = q.get("description")
            if not (isinstance(description, str) and description.strip()):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'description' must be a non-empty string"
                )

            # difficulty — one of the valid values
            difficulty = q.get("difficulty")
            if difficulty not in VALID_DIFFICULTIES:
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'difficulty' must be one of {sorted(VALID_DIFFICULTIES)}, got {difficulty!r}"
                )

            # hints — list with exactly 2 entries
            hints = q.get("hints")
            if not isinstance(hints, list):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'hints' must be a list"
                )
            elif len(hints) != 2:
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'hints' must have exactly 2 entries, found {len(hints)}"
                )

            # concepts — list with 1–4 entries
            concepts = q.get("concepts")
            if not isinstance(concepts, list):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'concepts' must be a list"
                )
            elif not (1 <= len(concepts) <= 4):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'concepts' must have 1–4 entries, found {len(concepts)}"
                )

            # order — must be an integer
            if not isinstance(q.get("order"), int):
                errors.append(
                    f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'order' must be an integer"
                )

            # Conditional: options — non-empty list if present
            if "options" in q:
                options = q.get("options")
                if not isinstance(options, list) or len(options) == 0:
                    errors.append(
                        f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'options' must be a non-empty list"
                    )

            # Conditional: expected_code / expected_query — non-empty string if present
            for code_field in ("expected_code", "expected_query"):
                if code_field in q:
                    val = q.get(code_field)
                    if not (isinstance(val, str) and val.strip()):
                        errors.append(
                            f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field '{code_field}' must be a non-empty string"
                        )

            # Conditional: test_cases — non-empty list if present
            if "test_cases" in q:
                tc = q.get("test_cases")
                if not isinstance(tc, list) or len(tc) == 0:
                    errors.append(
                        f"MISSING/INVALID FIELD [{track}] sample ID {qid}: field 'test_cases' must be a non-empty list"
                    )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"Non-SQL sample field validation failed:\n{joined}")


def _validate_non_sql_sample_ids() -> None:
    """Check that no two questions in the same non-SQL sample file share an 'id' value.

    Missing sample files are skipped with a warning.
    """
    errors: list[str] = []

    for track, sample_file in SAMPLE_FILES.items():
        if track == "sql":
            continue

        if not sample_file.exists():
            sys.stderr.write(
                f"WARNING: sample file not found, skipping duplicate-ID check: {sample_file}\n"
            )
            continue

        with sample_file.open("r", encoding="utf-8") as handle:
            questions = json.load(handle)

        seen_ids: dict[int, int] = {}  # id -> count
        for q in questions:
            qid = q.get("id")
            if not isinstance(qid, int):
                continue
            seen_ids[qid] = seen_ids.get(qid, 0) + 1

        for qid, count in seen_ids.items():
            if count > 1:
                errors.append(
                    f"DUPLICATE SAMPLE ID [{track}] id={qid} appears more than once"
                )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise ValueError(f"Non-SQL sample duplicate-ID check failed:\n{joined}")


def _validate_correct_option_explanation_consistency() -> None:
    """ERROR-level check: detect when a question's explanation appears to
    explicitly refute the keyed correct option.

    For every MCQ question (has 'options' + 'correct_option' + 'explanation')
    in a _TAXONOMY_VALIDATED_TRACKS file, scan the explanation for patterns
    that signal the keyed letter (A/B/C/D) is described as wrong, a
    misconception, or incorrect.  Fires as ERROR because a wrong correct_option
    means the platform marks the right answer wrong and vice-versa.

    Root cause this catches: bulk authoring runs where options are written with
    the correct answer first (options[0]) but correct_option is accidentally set
    to 1 throughout.  The refutation language in the explanation ("Option B is
    incorrect...") then betrays the inversion mechanically in < 1 second.
    """
    letters = ["A", "B", "C", "D"]
    # Refutation signal: Option <letter> followed by up to 80 chars that do NOT
    # contain another "Option [A-D]" reference, then a refutation marker.
    # The no-cross-option constraint prevents matching "Option C. Option A is wrong"
    # as a refutation of C (false positive from explanation structure where the
    # author names the correct option then refutes the others in sequence).
    # Capture BOTH letter (A-D) and 0-indexed numeric (0-3) option references.
    # Older bulk-authored explanations referenced options as "Option 0/1/2/3"
    # (0-indexed), which the letter-only pattern silently ignored — that blind
    # spot let the statistics +1 key-shift survive prior audits. The loop below
    # normalises the captured token to an index and compares to correct_option.
    _REFUTE = re.compile(
        r"Option ([A-D0-3])\b"
        r"(?:(?!Option [A-D0-3]).){0,80}"
        r"(?:"
        r"is (?:wrong|incorrect|a misconception|not correct)"
        r"|states the common misconception"
        r"|mischaracterizes"
        r"|conflates"
        r"|describes (?:the naive|the old|an incorrect|the wrong)"
        r"|is not (?:the fix|correct|equivalent|applied|a valid|the right)"
        r")",
        re.IGNORECASE | re.DOTALL,
    )
    errors: list[str] = []

    for track, file_path in _iter_question_files():
        if track not in _TAXONOMY_VALIDATED_TRACKS:
            continue
        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)
        for q in questions:
            if "options" not in q or "explanation" not in q:
                continue
            correct = q.get("correct_option")
            if not isinstance(correct, int):
                continue
            opts = q.get("options", [])
            if correct < 0 or correct >= len(opts):
                continue
            keyed = letters[correct]
            expl = q.get("explanation", "")
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            for m in _REFUTE.finditer(expl):
                token = m.group(1).upper()
                ref_idx = (ord(token) - ord("A")) if token.isalpha() else int(token)
                if ref_idx == correct:
                    errors.append(
                        f"{track} {qid} {title}: explanation appears to refute "
                        f"keyed option {keyed} — '{m.group()[:80].strip()}'"
                    )
                    break  # one error per question is enough

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(
            f"correct_option/explanation consistency check failed:\n{joined}"
        )


def _validate_hint_numbers_in_stem() -> None:
    """WARN-level check: detect when a hint contains a latency, percentile, or
    multiplier value that does not appear in the question stem.

    This catches the regression class where a hint rewrite accidentally imports
    numbers from a different question (e.g. '20ms p99' when the stem says
    '50ms SLA').  Applied to all tracks; WARN-only (stderr, not ValueError).

    Units checked: ms (latency), p99 (percentile notation), × (multiplier).
    Plain percentages and bare integers are excluded — they appear too
    frequently in generic prose to be reliably context-specific.
    """
    _NUM_UNIT = re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(ms\b|p99\b|×)",
        re.IGNORECASE,
    )
    warnings: list[str] = []

    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)
        for q in questions:
            hints = q.get("hints")
            if not isinstance(hints, list) or not hints:
                continue
            # Concatenate all fields that constitute the question body / stem
            stem = " ".join(
                filter(
                    None,
                    [
                        q.get("description") or "",
                        q.get("scenario_context") or "",
                        q.get("question") or "",
                        q.get("prompt") or "",
                    ],
                )
            )
            stem_pairs: set[tuple[str, str]] = {
                (m.group(1), m.group(2).lower().rstrip())
                for m in _NUM_UNIT.finditer(stem)
            }
            qid = q.get("id", "<unknown>")
            title = q.get("title", "<untitled>")
            for i, hint in enumerate(hints):
                if not isinstance(hint, str):
                    continue
                for m in _NUM_UNIT.finditer(hint):
                    pair = (m.group(1), m.group(2).lower().rstrip())
                    if pair not in stem_pairs:
                        warnings.append(
                            f"{track} {qid} {title}: hint[{i}] uses "
                            f"'{m.group().strip()}' not found in stem"
                        )

    if warnings:
        sys.stderr.write(
            f"WARNING: hint numbers not present in stem "
            f"({len(warnings)} cases — possible hint regression):\n"
        )
        for w in warnings[:20]:
            sys.stderr.write(f"  - {w}\n")
        if len(warnings) > 20:
            sys.stderr.write(f"  - ... and {len(warnings) - 20} more\n")


def _validate_no_numeric_option_references() -> None:
    """ERROR-level: explanations must reference options by LETTER
    ('Option A/B/C/D'), never by number ('Option 0/1/2/3/4').

    Rationale: the UI labels options A-D, so a numeric reference reads wrong to
    users, and the inconsistent numeric convention (some questions 0-indexed,
    some 1-indexed) was the ambiguity that masked a real key inversion (pyspark
    43112: explanation said 'Option 2 is the most plausible' while
    correct_option was 1). The canonical convention is to tag the correct answer
    by its letter. The bank was normalised to letters bank-wide (2026-06-03), so
    this is now a hard gate — the convention can never silently regress.
    """
    pat = re.compile(r"\bOption [0-9]\b")
    hits: list[str] = []
    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)
        for q in questions:
            expl = q.get("explanation", "")
            if isinstance(expl, str) and pat.search(expl):
                hits.append(f"{track} {q.get('id', '<unknown>')}")

    if hits:
        joined = "\n".join(f"- {h}" for h in hits[:50])
        if len(hits) > 50:
            joined += f"\n- ... and {len(hits) - 50} more"
        raise ValueError(
            f"{len(hits)} explanation(s) reference options by number instead of "
            f"letter ('Option A/B/C/D'). The canonical convention is letters "
            f"(matches the A-D UI labels):\n{joined}"
        )


def _validate_no_embedded_option_labels() -> None:
    """Guard against the label-collision anti-pattern (docs/content-authoring.md
    § Reject on sight): an MCQ option's text must not embed a choice-naming label
    ('Option/Proposal/Approach/Strategy/Design/Method <letter>') that re-letters
    the choices.

    ERROR (raises): a CROSS-position embed — option text names a letter DIFFERENT
    from its own A/B/C/D position (e.g. position C reading 'Approach D is best').
    This is the harmful form: it makes solvers — and even strong models — answer
    the embedded letter instead of the position. It caused real blind-model
    answer flips in the Phase-1/Phase-2 MCQ audits (e.g. 83011, 52051, 83034,
    sample 421). The bank was de-collided 2026-06-04; this gate prevents regress.

    WARN (stderr, non-blocking): a SELF-MATCHING embed — option text restates its
    OWN position letter (e.g. position A reading 'Option A — ...'). Milder (no
    re-lettering) but still discouraged; surfaced as a cleanup backlog (a
    data-modeling option-prefix template + a few others), not yet remediated.

    Scope: OPTION text only — explanations legitimately reference answer positions
    as 'Option A/B/C/D' (the canonical letter convention) and are NOT checked
    here. Domain-entity words ('Variant A' for an experiment arm, 'Group B' for a
    cohort, etc.) are deliberately excluded — only choice-naming words match.
    """
    choice_word = r"(?:Option|Proposal|Approach|Strategy|Design|Method)(?:es|s)?"
    pat = re.compile(r"\b" + choice_word + r"\s+([A-D])\b")
    cross: list[str] = []
    selfmatch: list[str] = []
    for track, file_path in _iter_question_files():
        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)
        for q in questions:
            correct = q.get("correct_option")
            options = q.get("options")
            if (
                not isinstance(correct, int)
                or not isinstance(options, list)
                or len(options) < 2
            ):
                continue
            q_has_cross = False
            q_has_self = False
            cross_detail: list[str] = []
            for i, opt in enumerate(options):
                if not isinstance(opt, str):
                    continue
                own = chr(ord("A") + i)
                for m in pat.finditer(opt):
                    if m.group(1) != own:
                        q_has_cross = True
                        cross_detail.append(f"option {own} embeds '{m.group(0)}'")
                    else:
                        q_has_self = True
            qid = q.get("id", "<unknown>")
            if q_has_cross:
                cross.append(f"{track} {qid} ({'; '.join(cross_detail)})")
            elif q_has_self:
                selfmatch.append(f"{track} {qid}")

    if selfmatch:
        joined = ", ".join(selfmatch[:40])
        if len(selfmatch) > 40:
            joined += f", ... (+{len(selfmatch) - 40} more)"
        print(
            f"WARNING: {len(selfmatch)} MCQ question(s) embed a self-matching "
            f"option label ('Option A —' at position A). Milder than a collision "
            f"but discouraged — describe each choice on its own terms. Cleanup "
            f"backlog: {joined}",
            file=sys.stderr,
        )

    if cross:
        joined = "\n".join(f"- {h}" for h in cross[:50])
        if len(cross) > 50:
            joined += f"\n- ... and {len(cross) - 50} more"
        raise ValueError(
            f"{len(cross)} MCQ option(s) embed a CROSS-POSITION choice label "
            f"(option text names a letter different from its own A/B/C/D position "
            f"— the label-collision anti-pattern). Describe each choice on its "
            f"own terms; never re-letter the choices:\n{joined}"
        )


# ---------------------------------------------------------------------------
# MCQ answer-key debiasing validators (Phase 1 + Phase 2 tooling)
# ---------------------------------------------------------------------------

# The 6 MCQ-capable tracks.  Statistics participates only for its conceptual
# subtype (questions that have both int correct_option and list options).
_MCQ_DEBIAS_TRACKS: frozenset[str] = frozenset({
    "data-engineering",
    "data-modeling",
    "pyspark",
    "ml-fundamentals",
    "experimentation",
    "statistics",
})


def _collect_mcq_groups() -> dict[tuple, list[dict]]:
    """Build the group mapping used by both debias validators.

    Group key schema
    ----------------
    Practice/mock files  : (track, difficulty, pool)
                           where pool = "mock" | "practice"
    Sample files         : ("sample", track, "all")

    Only questions that are MCQ (have int correct_option + list options with
    len >= 2) are included.  Statistics numerical subtype questions (no
    correct_option / no options) are automatically excluded by the MCQ
    predicate.
    """
    from collections import defaultdict

    groups: dict[tuple, list[dict]] = defaultdict(list)

    # ---- practice/mock files -----------------------------------------------
    for track, file_path in _iter_question_files():
        if track not in _MCQ_DEBIAS_TRACKS:
            continue
        # Skip sample files in this loop; handle them below.
        if file_path.parent.name == "sample_questions":
            continue

        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)

        for q in questions:
            if not isinstance(q.get("correct_option"), int):
                continue
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                continue
            difficulty = q.get("difficulty") or file_path.stem
            pool = "mock" if q.get("mock_only") else "practice"
            key = (track, difficulty, pool)
            groups[key].append(q)

    # ---- sample files -------------------------------------------------------
    for track, file_path in _iter_question_files():
        if track not in _MCQ_DEBIAS_TRACKS:
            continue
        if file_path.parent.name != "sample_questions":
            continue

        with file_path.open("r", encoding="utf-8") as fh:
            questions = json.load(fh)

        for q in questions:
            if not isinstance(q.get("correct_option"), int):
                continue
            opts = q.get("options")
            if not isinstance(opts, list) or len(opts) < 2:
                continue
            key = ("sample", track, "all")
            groups[key].append(q)

    return dict(groups)


def _validate_answer_position_balance() -> None:
    """ERROR-level: detect answer-key position bias in MCQ question groups.

    Two checks per qualifying group (n >= 10 for practice/mock; n >= 6 for
    samples):

    (a) CONCENTRATION — any single position holds > 40% of the group's correct
        answers.  A perfectly uniform 4-option bank would land at 25%; 40% is
        a generous tolerance that still catches the severe authoring bias
        documented in the Phase 1 audit (some groups: 80–100% position A or B).

    (b) RUN — the questions sorted by their `order` field contain a run of >= 5
        consecutive identical correct_option values.  A run this long is visible
        to test-takers scanning the answer key and degrades the diagnostic value
        of the bank.

    Group definition:
      Practice/mock  — grouped by (track, difficulty, pool=mock|practice).
      Sample         — grouped by (track) across all difficulties.

    Only MCQ questions (int correct_option + list options len >= 2) are
    considered.  Statistics numerical-subtype questions are excluded because
    they have no correct_option.
    """
    MIN_N_PRACTICE = 10
    MIN_N_SAMPLE = 6
    MAX_POSITION_SHARE = 0.40
    MAX_RUN = 5  # runs of THIS length or longer are flagged

    groups = _collect_mcq_groups()
    errors: list[str] = []

    for key, qs in sorted(groups.items()):
        is_sample = key[0] == "sample"
        min_n = MIN_N_SAMPLE if is_sample else MIN_N_PRACTICE
        if len(qs) < min_n:
            continue

        n = len(qs)
        from collections import Counter
        position_counts: Counter = Counter(q["correct_option"] for q in qs)

        # (a) concentration check
        for pos, cnt in position_counts.items():
            share = cnt / n
            if share > MAX_POSITION_SHARE:
                label = chr(ord("A") + pos) if pos < 26 else str(pos)
                key_str = "/".join(str(k) for k in key)
                errors.append(
                    f"POSITION CONCENTRATION [{key_str}]: position {label} holds "
                    f"{cnt}/{n} ({share:.1%}) of answers — exceeds {MAX_POSITION_SHARE:.0%} cap"
                )

        # (b) run check — sort by order, then scan
        sorted_qs = sorted(qs, key=lambda q: (q.get("order") or 0))
        run_len = 1
        run_pos = sorted_qs[0]["correct_option"] if sorted_qs else None
        for i in range(1, len(sorted_qs)):
            cur = sorted_qs[i]["correct_option"]
            if cur == run_pos:
                run_len += 1
                if run_len >= MAX_RUN:
                    label = chr(ord("A") + run_pos) if run_pos < 26 else str(run_pos)
                    key_str = "/".join(str(k) for k in key)
                    errors.append(
                        f"POSITION RUN [{key_str}]: run of {run_len}+ consecutive "
                        f"position {label} starting near order "
                        f"{sorted_qs[i - run_len + 1].get('order')!r}"
                    )
                    # Only report the first trigger of each run to avoid spam
                    run_pos = None  # reset to avoid re-flagging same run
            else:
                run_len = 1
                run_pos = cur

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"MCQ answer-position balance check failed:\n{joined}")


def _validate_answer_length_balance() -> None:
    """ERROR-level: detect answer-key length bias in MCQ question groups.

    For each qualifying group (same definition as _validate_answer_position_balance),
    computes the fraction of questions where the correct option is the UNIQUE
    LONGEST option (i.e. its char length is strictly greater than every other
    option's char length).  If that fraction exceeds 55%, raises an error.

    Unique-longest definition: len(correct_text) > len(opt_text) for ALL other
    options.  If two or more options share the maximum length, neither is the
    unique longest — those questions contribute 0 to the fraction.

    55% threshold: a bank of well-crafted distractors should not allow a
    test-taker to identify the correct answer purely by picking the longest
    option more than ~50% of the time.  55% gives a small buffer above pure
    chance for plausibly-authored content before flagging.
    """
    MIN_N_PRACTICE = 10
    MIN_N_SAMPLE = 6
    MAX_LONGEST_SHARE = 0.55

    groups = _collect_mcq_groups()
    errors: list[str] = []

    for key, qs in sorted(groups.items()):
        is_sample = key[0] == "sample"
        min_n = MIN_N_SAMPLE if is_sample else MIN_N_PRACTICE
        if len(qs) < min_n:
            continue

        n = len(qs)
        unique_longest_count = 0
        for q in qs:
            opts = q.get("options", [])
            correct = q["correct_option"]
            if correct >= len(opts):
                continue
            correct_len = len(opts[correct])
            other_lens = [len(opts[i]) for i in range(len(opts)) if i != correct]
            if other_lens and correct_len > max(other_lens):
                unique_longest_count += 1

        share = unique_longest_count / n
        if share > MAX_LONGEST_SHARE:
            key_str = "/".join(str(k) for k in key)
            errors.append(
                f"LENGTH BIAS [{key_str}]: correct option is the unique longest in "
                f"{unique_longest_count}/{n} ({share:.1%}) of questions — "
                f"exceeds {MAX_LONGEST_SHARE:.0%} cap"
            )

    if errors:
        joined = "\n".join(f"- {item}" for item in errors[:200])
        remaining = len(errors) - min(len(errors), 200)
        if remaining:
            joined += f"\n- ... and {remaining} more"
        raise ValueError(f"MCQ answer-length balance check failed:\n{joined}")


# ---------------------------------------------------------------------------
# End of debias validators
# ---------------------------------------------------------------------------


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
    _warn_unenforced_tracks()
    _validate_concept_taxonomy()
    _validate_mock_only_realism()
    _validate_per_family_coverage()
    _validate_chain_integrity()
    _validate_hints()
    _validate_statistics_subtypes()
    _validate_code_reference_reproduces_tests()
    _validate_mcq_scenario_questions()
    _validate_mock_fields()
    _validate_solution_code_presence()
    _validate_sample_cross_bank_titles()
    _validate_mcq_consistency()
    _validate_non_sql_sample_fields()
    _validate_non_sql_sample_ids()
    _validate_correct_option_explanation_consistency()
    _validate_hint_numbers_in_stem()
    _validate_no_numeric_option_references()
    _validate_no_embedded_option_labels()
    _validate_answer_position_balance()
    _validate_answer_length_balance()

    print("Content validation passed")


if __name__ == "__main__":
    main()
