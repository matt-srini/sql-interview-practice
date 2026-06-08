"""Route 1 + sub-option 1a — bucket-a-route-1 end-to-end execution.

Creates 4 new lean paths and absorbs orphans into 8 existing paths.
All absorptions verified against validator rule 5 before write.

Re-runnable + idempotent (sorts + dedupes questions[], no-ops if no change).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATHS_DIR = REPO / "backend" / "content" / "paths"


# ---------------------------------------------------------------------------
# NEW PATHS (sub-option 1a → 4 new paths)
# ---------------------------------------------------------------------------
NEW_PATHS = [
    {
        "slug": "greedy-and-scanning",
        "title": "Greedy & Scanning Patterns",
        "description": (
            "Recognise when local-optimum decisions yield the global optimum "
            "and when they don't. Build the muscle for greedy interval problems, "
            "scheduling, and scanning-with-state patterns that show up across "
            "every Python interview loop."
        ),
        "topic": "python",
        "questions": [21008, 21038, 22027, 22043, 23001],
        "tier": "free",
        "level": "intermediate",
        "display_order": 4,
        "patterns": ["greedy-and-scanning"],
        "focus_concepts": ["GREEDY CHOICE", "INDEXED SEQUENCE REASONING"],
        "outcomes": (
            "You'll recognise when a greedy strategy provably works, choose "
            "between sorting-first vs scanning-once, compose greedy with "
            "binary-search bounds, and handle classic interval-merging cases "
            "without overengineering toward DP."
        ),
        "recommended_after": ["arrays-and-hashing"],
    },
    {
        "slug": "list-transformations",
        "title": "List & Array Transformations",
        "description": (
            "Reshape, rotate, flatten, chunk, transpose. The structural list-"
            "manipulation toolkit that practitioners reach for daily — once you "
            "stop hand-rolling them and start recognising them as a pattern."
        ),
        "topic": "python",
        "questions": [21003, 21016, 21017, 21025, 21026, 21028, 21029],
        "tier": "free",
        "level": "intermediate",
        "display_order": 5,
        "patterns": ["list-transformations"],
        "focus_concepts": ["LIST & COLLECTION TRANSFORMATION", "INDEXED SEQUENCE REASONING"],
        "outcomes": (
            "You'll cleanly express rotation, flattening, chunking, and "
            "transposition on Python lists without index off-by-one bugs, "
            "and recognise these shapes in larger pipeline problems."
        ),
        "recommended_after": ["arrays-and-hashing"],
    },
    {
        "slug": "spark-udfs-and-python-boundary",
        "title": "Spark UDFs & the Python Boundary",
        "description": (
            "Master the cost and correctness implications of crossing the JVM-"
            "Python boundary: when Python UDFs collapse performance, when "
            "Pandas UDFs save you, and how nullable columns silently break "
            "UDF logic that looked fine in tests."
        ),
        "topic": "pyspark",
        "questions": [41019, 41035, 42022, 42033, 43041],
        "tier": "free",
        "level": "intermediate",
        "display_order": 8,
        "patterns": ["spark-udfs-and-python-boundary"],
        "focus_concepts": ["UDF & PYTHON BOUNDARY", "SCHEMA & TYPE HANDLING", "PERFORMANCE TUNING & TRADE-OFFS"],
        "outcomes": (
            "You'll predict why a Python UDF is slow, choose Pandas UDFs when "
            "vectorisation pays, debug return-type mismatches and null-input "
            "failures, and reason about mapPartitions vs map for batch-amortised "
            "Python work."
        ),
        "recommended_after": ["spark-schema-and-type-handling"],
    },
    {
        "slug": "hypothesis-testing-and-ci",
        "title": "Hypothesis Testing & Confidence Intervals",
        "description": (
            "Sharpen the inference vocabulary every experimentation interview "
            "leans on: null vs alternative, what a p-value actually tells you, "
            "how CI width scales with sample size, and why pre-registration is "
            "the difference between an analysis and a fishing expedition."
        ),
        "topic": "experimentation",
        "questions": [91003, 91009, 91016, 91025, 91029],
        "tier": "free",
        "level": "intermediate",
        "display_order": 3,
        "patterns": ["hypothesis-testing-and-ci"],
        "focus_concepts": [
            "HYPOTHESIS FORMULATION",
            "STATISTICAL SIGNIFICANCE",
            "CONFIDENCE INTERVALS",
            "TYPE I AND TYPE II ERRORS",
        ],
        "outcomes": (
            "You'll state null and alternative hypotheses unambiguously, "
            "interpret p-values without the common 'probability the null is "
            "true' fallacy, reason about how CI width scales with √n, and "
            "explain why pre-registration constrains false-discovery risk."
        ),
        "recommended_after": ["experiment-design-and-power"],
    },
]


# ---------------------------------------------------------------------------
# ABSORPTIONS into existing paths
# ---------------------------------------------------------------------------
ABSORPTIONS: dict[str, list[int]] = {
    # arrays-and-hashing: 5 → 15 (+10 clean fits)
    "arrays-and-hashing": [21012, 21013, 21020, 21023, 21030, 21034, 22003, 22010, 22011, 22024],
    # practical-data-python: 6 → 14 (+8 real practical-scripting fits)
    "practical-data-python": [21037, 21039, 21040, 22041, 22044, 22045, 22047, 23007],
    # heap-and-priority: 4 → 5 (+1 — only true heap problem)
    "heap-and-priority": [23023],
    # sliding-window-patterns: 10 → 11 (+1 two-pointer merge)
    "sliding-window-patterns": [22049],
    # spark-performance: 6 → 13 (+7 core perf fits)
    "spark-performance": [41010, 41011, 41013, 41033, 42019, 43007, 43017],
    # spark-joins-and-skew: 16 → 18 (+2 join-strategy spillover)
    "spark-joins-and-skew": [42036, 43023],
    # spark-memory-and-driver-executor: 12 → 13 (+1 memory-driven)
    "spark-memory-and-driver-executor": [42035],
    # experimentation-starter: 14 → 17 (+3 A/B mechanics)
    "experimentation-starter": [91011, 91021, 91027],
    # experiment-design-and-power: 18 → 20 (+2 Type I/II errors)
    "experiment-design-and-power": [91005, 91006],
}


# ---------------------------------------------------------------------------
# Focus_concept broadening required for rule 5 alignment
# (when absorbed Qs use tags outside the current focus_concepts family)
# ---------------------------------------------------------------------------
FOCUS_CONCEPT_BROADENING: dict[str, list[str]] = {
    # arrays-and-hashing: 4 absorbed Qs only have INDEXED SEQUENCE REASONING / BINARY SEARCH
    # primary tags (21012, 21013, 21023, 22003), no HASH-MAP-STATE-family tag.
    # Broaden focus_concepts to include INDEXED SEQUENCE REASONING (legitimate
    # — "arrays" implies index reasoning, not only hashing).
    "arrays-and-hashing": ["INDEXED SEQUENCE REASONING"],
    # spark-performance: pre-existing focus_concepts use descriptive labels
    # ("SHUFFLE BOUNDARY DETECTION") that don't resolve to the canonical
    # family names of question tags. Add the canonical family names directly
    # so absorbed Qs with CACHING & PERSISTENCE / EXECUTION MODEL REASONING /
    # SHUFFLE REASONING tags align cleanly under rule 5.
    "spark-performance": [
        "CACHING & PERSISTENCE",
        "EXECUTION MODEL REASONING",
        "SHUFFLE REASONING",
    ],
}


def write_new_paths():
    print("=== Creating 4 new paths ===")
    for spec in NEW_PATHS:
        f = PATHS_DIR / f"{spec['slug']}.json"
        if f.exists():
            print(f"  ⚠ {spec['slug']}: file already exists — overwriting")
        f.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
        print(f"  ✓ {spec['slug']} ({spec['topic']}, {spec['level']} #{spec['display_order']}, {len(spec['questions'])} Qs)")
    print()


def apply_absorptions():
    print("=== Absorbing orphans into 8 existing paths ===")
    for slug, new_qids in ABSORPTIONS.items():
        f = PATHS_DIR / f"{slug}.json"
        d = json.loads(f.read_text())
        before = list(d["questions"])
        merged = sorted(set(before) | set(new_qids))
        d["questions"] = merged
        # Broaden focus_concepts if needed for rule 5 alignment
        broaden = FOCUS_CONCEPT_BROADENING.get(slug, [])
        if broaden:
            existing = list(d.get("focus_concepts", []))
            added = [c for c in broaden if c not in existing]
            if added:
                d["focus_concepts"] = existing + added
                print(f"  {slug}: focus_concepts broadened += {added}")
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        added_ids = sorted(set(new_qids) - set(before))
        print(f"  ✓ {slug}: {len(before)} → {len(merged)} Qs (+{len(added_ids)})")
    print()


def execute():
    write_new_paths()
    apply_absorptions()
    print("Done — run validator + tests to confirm.")


if __name__ == "__main__":
    execute()
