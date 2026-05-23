"""Path quality / content-integrity tests.

These tests outlive doc rot — they enforce the validator rules defined in
``docs/content-authoring.md`` §Paths as standalone assertions, separate from
``validate_content.py`` so a regression in either surface is visible.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from concept_families import CONCEPT_FAMILIES, concept_matches_focus, resolve_to_family
from path_loader import get_all_paths
from path_patterns import PATH_PATTERNS
from tracks import TRACKS


_TAXONOMY_VALIDATED_TRACKS = frozenset({"sql", "python"})


@pytest.fixture(scope="module")
def all_paths() -> list[dict]:
    return list(get_all_paths())


@pytest.fixture(scope="module")
def questions_by_id() -> dict[str, dict[int, dict]]:
    return {
        t.slug: {
            int(q["id"]): q
            for diff_qs in t.catalog_module.get_questions_by_difficulty().values()
            for q in diff_qs
        }
        for t in TRACKS
    }


@pytest.fixture(scope="module")
def valid_topics() -> set[str]:
    return {t.slug for t in TRACKS}


# ──────────────────────────────────────────────────────────────────────────────
# Rule 1 — Schema completeness
# ──────────────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "slug", "title", "description", "topic", "questions",
    "tier", "role", "patterns", "focus_concepts",
}


def test_rule1_every_path_has_required_fields(all_paths):
    """Every path JSON declares all required schema fields."""
    for path in all_paths:
        missing = REQUIRED_FIELDS - set(path.keys())
        assert not missing, f"Path {path.get('slug', '<unknown>')} missing fields: {sorted(missing)}"


def test_rule1_slugs_are_unique(all_paths):
    slugs = [p["slug"] for p in all_paths]
    assert len(slugs) == len(set(slugs)), "Duplicate path slugs found"


def test_rule1_slug_matches_filename(all_paths):
    files = {p.stem for p in (BACKEND / "content" / "paths").glob("*.json")}
    for path in all_paths:
        assert path["slug"] in files, f"Path slug {path['slug']!r} has no matching JSON file"


# ──────────────────────────────────────────────────────────────────────────────
# Rule 2 — Singleton starter per track; valid role enum
# ──────────────────────────────────────────────────────────────────────────────

VALID_ROLES = {"starter", "intermediate", "advanced"}


def test_rule2_role_enum(all_paths):
    for path in all_paths:
        assert path["role"] in VALID_ROLES, f"{path['slug']}: invalid role {path['role']!r}"


def test_rule2_exactly_one_starter_per_track(all_paths, valid_topics):
    starter_counts: dict[str, int] = defaultdict(int)
    for path in all_paths:
        if path["role"] == "starter":
            starter_counts[path["topic"]] += 1
    for topic in valid_topics:
        assert starter_counts[topic] == 1, (
            f"Track {topic} must have exactly one starter path "
            f"(found {starter_counts[topic]})"
        )


def test_rule2_intermediate_and_advanced_are_uncapped(all_paths):
    """Sanity: multiple intermediate or advanced is allowed (no validator gate)."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for path in all_paths:
        counts[path["topic"]][path["role"]] += 1
    # At least one track demonstrates the relaxed cap (post-refactor invariant)
    multi_intermediate = [t for t, c in counts.items() if c["intermediate"] > 1]
    multi_advanced = [t for t, c in counts.items() if c["advanced"] > 1]
    assert multi_intermediate or multi_advanced, (
        "Expected at least one track with multiple intermediates or advanceds "
        "to demonstrate the uncapped relaxation"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Rule 3 — patterns[] resolves to path_patterns.py registry
# ──────────────────────────────────────────────────────────────────────────────

def test_rule3_patterns_non_empty_and_registered(all_paths):
    for path in all_paths:
        patterns = path.get("patterns")
        slug = path["slug"]
        topic = path["topic"]
        assert isinstance(patterns, list) and patterns, (
            f"{slug}: patterns[] must be a non-empty list"
        )
        registry = PATH_PATTERNS.get(topic, {})
        for pat in patterns:
            assert pat in registry, (
                f"{slug}: pattern {pat!r} not registered in path_patterns.py "
                f"for track {topic!r}. Available: {sorted(registry.keys())}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Rule 4 — focus_concepts resolve to concept-family registry (taxonomy-validated tracks)
# ──────────────────────────────────────────────────────────────────────────────

def test_rule4_focus_concepts_non_empty(all_paths):
    for path in all_paths:
        fc = path.get("focus_concepts")
        assert isinstance(fc, list) and fc, (
            f"{path['slug']}: focus_concepts[] must be a non-empty list"
        )


def test_rule4_focus_concepts_resolve_for_taxonomy_validated_tracks(all_paths):
    for path in all_paths:
        topic = path["topic"]
        if topic not in _TAXONOMY_VALIDATED_TRACKS:
            continue
        families = CONCEPT_FAMILIES.get(topic, {})
        for fc in path["focus_concepts"]:
            resolved = resolve_to_family(fc, topic)
            assert resolved in families, (
                f"{path['slug']}: focus_concept {fc!r} does not resolve to a "
                f"registered family for track {topic!r} (resolved to {resolved!r})"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Rule 5 — Every path question carries a tag in same family as focus_concepts
# ──────────────────────────────────────────────────────────────────────────────

def test_rule5_question_tags_align_with_path_focus(all_paths, questions_by_id):
    """The mechanical guarantee that a path drills what it claims."""
    for path in all_paths:
        topic = path["topic"]
        focus = path["focus_concepts"]
        for qid in path["questions"]:
            q = questions_by_id[topic].get(int(qid))
            assert q is not None, (
                f"{path['slug']}: question {qid} not found in track {topic} catalog"
            )
            q_concepts = q.get("concepts", []) or []
            matched = any(
                concept_matches_focus(qc, fc, topic)
                for qc in q_concepts
                for fc in focus
            )
            assert matched, (
                f"{path['slug']}: question {qid} ({q.get('title')!r}) tags {q_concepts} "
                f"do not align with any of path focus_concepts {focus}"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Rule 6 — recommended_after references real path slugs + acyclic
# ──────────────────────────────────────────────────────────────────────────────

def test_rule6_recommended_after_references_valid_paths(all_paths):
    by_topic: dict[str, set[str]] = defaultdict(set)
    for p in all_paths:
        by_topic[p["topic"]].add(p["slug"])
    for path in all_paths:
        for prereq in path.get("recommended_after", []) or []:
            assert prereq in by_topic[path["topic"]], (
                f"{path['slug']}: recommended_after references {prereq!r} which is "
                f"not a path in track {path['topic']!r}"
            )


def test_rule6_recommended_after_graph_is_acyclic(all_paths):
    by_topic: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for p in all_paths:
        by_topic[p["topic"]][p["slug"]] = list(p.get("recommended_after", []) or [])

    for topic, nodes in by_topic.items():
        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str, stack: list[str]) -> None:
            if node in visiting:
                cycle = " → ".join(stack[stack.index(node):] + [node])
                pytest.fail(f"Cycle in {topic} paths: {cycle}")
            if node in visited:
                return
            visiting.add(node)
            stack.append(node)
            for prereq in nodes.get(node, []):
                dfs(prereq, stack)
            stack.pop()
            visiting.remove(node)
            visited.add(node)

        for slug in nodes:
            dfs(slug, [])


# ──────────────────────────────────────────────────────────────────────────────
# Path size discipline (soft guideline — see docs/content-authoring.md §Paths)
# ──────────────────────────────────────────────────────────────────────────────

def test_path_question_counts_in_curation_range(all_paths):
    """Sanity guardrail: paths should be 4–15 questions.

    The §Paths sweet spot is 5–9: below 5 → not enough progression; above 10 →
    completion stops being meaningful (users abandon mid-walk). This test
    catches only egregious violations (1–3 or 16+). The 5–9 sweet spot is
    enforced by author judgment, not by the validator.
    """
    out_of_range = []
    for p in all_paths:
        n = len(p["questions"])
        if n < 4 or n > 15:
            out_of_range.append((p["slug"], n))
    assert not out_of_range, (
        f"Paths outside 4–15 question sanity range: {out_of_range}. "
        f"See docs/content-authoring.md §Paths."
    )
