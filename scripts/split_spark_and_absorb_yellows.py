"""Split spark-core-concepts into 6 sub-pattern paths + apply 6 Bucket A yellow
absorptions. NO question-file edits — only path JSONs, pattern registry, and
the test-guardrail file are modified.

PART 1 — spark-core-concepts split
  Splits the existing spark-core-concepts path (and its 42 spark-basics
  orphans) into 6 narrower pattern paths totaling 48 questions:
    spark-execution-model-and-dag     (16 Qs, foundational — inherits singleton)
    spark-schema-and-type-handling    (11 Qs, intermediate)
    spark-memory-and-driver-executor  ( 6 Qs, intermediate)
    spark-io-and-file-formats         ( 5 Qs, intermediate)
    spark-fault-tolerance-and-recovery ( 5 Qs, advanced)
    spark-collections-and-arrays      ( 5 Qs, intermediate)

PART 2 — borderline (yellow) absorptions
  Absorb 25 orphans into 6 paths whose new size lands in the 16–20 range
  (allowed under the extended ceiling). cost-and-format-optimization
  EXCLUDED per explicit user decision.

PART 3 — guardrail extension
  test_paths_quality.py: 4–15 → 4–20.
  Doc: §Paths SoT and tracker note that 15 is the default cap; 16–20
  requires explicit per-path approval in the commit message.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from audit_pattern_coverage import TRACK_DIRS, walk_track, _load_live_paths_by_track
from concept_families import concept_matches_focus

DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


# ---------------------------------------------------------------------------
# PART 1 — Spark sub-pattern question lists (precomputed) + metadata
# ---------------------------------------------------------------------------
SPARK_SUB_PATTERNS: dict[str, dict] = {
    "spark-execution-model-and-dag": {
        "title": "Spark Execution Model & DAG",
        "description": "Build practitioner intuition for how Spark actually runs your code: lazy evaluation, action triggers, the Job/Stage/Task hierarchy, narrow vs wide transformations, and the DAG planning that turns DataFrame operations into physical work.",
        "tier": "free",
        "level": "foundational",
        "patterns": ["spark-execution-model-and-dag"],
        "focus_concepts": ["EXECUTION MODEL REASONING", "NARROW VS WIDE TRANSFORMATIONS", "CATALYST OPTIMIZER"],
        "outcomes": "You'll predict when an action triggers execution vs when transformations defer, distinguish narrow from wide transformations on shuffle grounds, trace Job → Stage → Task hierarchies through the DAG, and reason about how withColumn / when / SQL queries translate into Spark's execution plan.",
        "recommended_after": [],
        "qids": [41001, 41002, 41003, 41006, 41007, 41008, 41009, 41012, 41015, 41016, 41039, 41041, 42018, 42020, 42037, 43042],
    },
    "spark-schema-and-type-handling": {
        "title": "Spark Schema & Type Handling",
        "description": "Master the schema and type behaviours that cause most production Spark surprises: column renames, alias scope, type cast failures, union column matching, lit() nullability, and the output schema of groupBy + agg.",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["spark-schema-and-type-handling"],
        "focus_concepts": ["SCHEMA & TYPE HANDLING"],
        "outcomes": "You'll rename and alias columns without surprise, predict cast failure behaviour, reason about union column matching, derive the output schema of groupBy + agg before running it, and debug AnalysisException quickly.",
        "recommended_after": ["spark-execution-model-and-dag"],
        "qids": [41014, 41018, 41020, 41021, 41022, 41023, 41024, 41025, 41031, 42001, 42005],
    },
    "spark-memory-and-driver-executor": {
        "title": "Spark Memory & Driver/Executor Architecture",
        "description": "Reason about Spark's memory model and the driver vs executor split: where data lives, what crashes the driver vs an executor, why collect() is dangerous, and how Tungsten's off-heap format changes the picture.",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["spark-memory-and-driver-executor"],
        "focus_concepts": ["MEMORY MANAGEMENT", "EXECUTION MODEL REASONING"],
        "outcomes": "You'll distinguish driver OOM from executor OOM by reading the trace, predict the memory cost of collect() / limit / cache, pick the right alternative when collect would crash the driver, and reason about Tungsten's off-heap binary format.",
        "recommended_after": ["spark-execution-model-and-dag"],
        "qids": [41004, 41028, 41036, 42025, 43006, 43011],
    },
    "spark-io-and-file-formats": {
        "title": "Spark I/O & File Formats",
        "description": "Choose between CSV / JSON / Parquet for the workload at hand, manage inferSchema's production cost, and avoid the silent write-mode surprises that overwrite or duplicate data.",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["spark-io-and-file-formats"],
        "focus_concepts": ["FILE FORMATS & READERS", "SCHEMA & TYPE HANDLING"],
        "outcomes": "You'll select CSV/JSON/Parquet based on read pattern and analytical workload, run inferSchema safely in production without runaway scans, debug multi-line JSON parsing failures, and avoid unintended write-mode appends.",
        "recommended_after": ["spark-execution-model-and-dag"],
        "qids": [41005, 41026, 41030, 42009, 43008],
    },
    "spark-fault-tolerance-and-recovery": {
        "title": "Spark Fault Tolerance & Recovery",
        "description": "Master the recovery primitives that decide whether a long Spark job survives executor failures or duplicates writes on retry: checkpoint vs cache, speculative execution, and non-idempotent sink hazards.",
        "tier": "free",
        "level": "advanced",
        "patterns": ["spark-fault-tolerance-and-recovery"],
        "focus_concepts": ["FAULT TOLERANCE & RECOVERY", "EXECUTION MODEL REASONING"],
        "outcomes": "You'll pick checkpoint vs cache for iterative ML training (lineage truncation vs in-memory reuse), configure speculative execution without duplicating writes to non-idempotent sinks, and avoid the unintended-append write mode that causes the worst on-call incidents.",
        "recommended_after": ["spark-execution-model-and-dag"],
        "qids": [41017, 41029, 42021, 43010, 43026],
    },
    "spark-collections-and-arrays": {
        "title": "Spark Collections & Arrays",
        "description": "Wield Spark's collection and array operations correctly: collect_list vs collect_set on ordering/dedup grounds, explode's silent drops on empty/null arrays, and the explode_outer vs explode trade-off when row preservation matters.",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["spark-collections-and-arrays"],
        "focus_concepts": ["COLLECTION & ARRAY OPERATIONS", "DATA QUALITY SKEPTICISM"],
        "outcomes": "You'll choose collect_list vs collect_set on ordering/dedup grounds, anticipate explode's silent row-drop on empty/null arrays, switch to explode_outer when row preservation matters, and predict pivot's null propagation through arithmetic.",
        "recommended_after": ["spark-schema-and-type-handling"],
        "qids": [42049, 42053, 42056, 43049, 43052],
    },
}

# Pattern registrations for path_patterns.py (pyspark track gets 6 new slugs; remove old spark-basics)
PYSPARK_NEW_PATTERNS = {slug: spec["title"] for slug, spec in SPARK_SUB_PATTERNS.items()}


# ---------------------------------------------------------------------------
# PART 2 — Yellow absorptions
# ---------------------------------------------------------------------------
# (track, source_tag_pattern) → target_path_slug
YELLOW_ABSORPTIONS: dict[tuple[str, str], str] = {
    ("sql", "joins"): "joins-and-filtering",
    ("pyspark", "spark-joins-and-skew"): "spark-joins-and-skew",
    ("data-engineering", "etl-elt"): "pipeline-fundamentals",
    ("data-modeling", "scd"): "scd",
    ("statistics", "distributions"): "distributions",
    ("ml-fundamentals", "regularization"): "ml-advanced-methods",
    # EXCLUDED per user decision: ("data-engineering", "cost-and-format-optimization")
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_qmap(track: str) -> dict:
    qmap = {}
    for f in sorted(TRACK_DIRS[track].glob("*.json")):
        if f.stem == "schemas":
            continue
        diff = f.stem
        for q in json.loads(f.read_text()):
            q["__diff"] = diff
            qmap[int(q["id"])] = q
    return qmap


def order_questions(qids, qmap):
    return sorted(qids, key=lambda q: (DIFF_ORDER.get(qmap.get(q, {}).get("__diff", "easy"), 9), q))


# ---------------------------------------------------------------------------
# PART 1: spark split
# ---------------------------------------------------------------------------
def split_spark():
    paths_dir = REPO / "backend" / "content" / "paths"
    audit = []
    qmap = load_qmap("pyspark")

    # Verify spark-core-concepts exists and check its level
    sc_file = paths_dir / "spark-core-concepts.json"
    if not sc_file.exists():
        audit.append("  WARN: spark-core-concepts.json not found; skipping split")
        return audit
    sc_data = json.loads(sc_file.read_text())
    was_foundational = sc_data.get("level") == "foundational"
    audit.append(f"  spark-core-concepts current level: {sc_data.get('level')}; will inherit to execution-model-and-dag")

    # Create the 6 new sub-pattern path files
    for slug, spec in SPARK_SUB_PATTERNS.items():
        ordered = order_questions(spec["qids"], qmap)
        path_json = {
            "slug": slug,
            "title": spec["title"],
            "description": spec["description"],
            "topic": "pyspark",
            "questions": ordered,
            "tier": spec["tier"],
            "level": spec["level"],
            "patterns": spec["patterns"],
            "focus_concepts": spec["focus_concepts"],
            "outcomes": spec["outcomes"],
            "recommended_after": spec["recommended_after"],
        }
        out = paths_dir / f"{slug}.json"
        out.write_text(json.dumps(path_json, indent=2, ensure_ascii=False) + "\n")
        audit.append(f"  CREATE {slug}.json ({len(ordered)} Qs, level={spec['level']})")

    # Delete the old spark-core-concepts.json
    sc_file.unlink()
    audit.append("  DELETE spark-core-concepts.json")

    # Fix recommended_after on any path that referenced spark-core-concepts
    for f in paths_dir.glob("*.json"):
        d = json.loads(f.read_text())
        if d["topic"] != "pyspark":
            continue
        ra = d.get("recommended_after") or []
        if "spark-core-concepts" in ra:
            new_ra = ["spark-execution-model-and-dag" if x == "spark-core-concepts" else x for x in ra]
            d["recommended_after"] = new_ra
            f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
            audit.append(f"  FIX-RA {f.name}: spark-core-concepts → spark-execution-model-and-dag")

    return audit


# ---------------------------------------------------------------------------
# PART 2: yellow absorptions (same approach as green)
# ---------------------------------------------------------------------------
def apply_yellow_absorptions():
    paths_dir = REPO / "backend" / "content" / "paths"
    live = _load_live_paths_by_track()
    audit = []

    additions_by_path: dict[str, list[tuple[int, dict, str]]] = defaultdict(list)
    for (track, src_pattern), target_slug in YELLOW_ABSORPTIONS.items():
        qmap = load_qmap(track)
        _, _, _, orphans, _ = walk_track(track, TRACK_DIRS[track], live_paths=live.get(track, []))
        matching = [o for o in orphans if o["tag_pattern"] == src_pattern]
        for o in matching:
            q = qmap.get(o["qid"])
            additions_by_path[target_slug].append((o["qid"], q, track))

    for target_slug, items in sorted(additions_by_path.items()):
        path_file = paths_dir / f"{target_slug}.json"
        if not path_file.exists():
            audit.append(f"  WARN target {target_slug}.json not found; skipping {len(items)} orphans")
            continue
        path_data = json.loads(path_file.read_text())
        track = path_data["topic"]
        qmap = load_qmap(track)

        current_qids = set(int(q) for q in path_data["questions"])
        added = []
        for qid, q, _t in items:
            if qid in current_qids:
                continue
            current_qids.add(qid)
            added.append(qid)

        path_data["questions"] = order_questions(list(current_qids), qmap)

        # Broaden focus_concepts if any new Q's tags don't match existing focus
        fc = list(path_data.get("focus_concepts", []))
        for qid in added:
            q = qmap.get(qid, {})
            q_tags = q.get("concepts", []) or []
            matched = any(concept_matches_focus(t, f, track) for t in q_tags for f in fc)
            if not matched and q_tags:
                first_tag = q_tags[0]
                if first_tag not in fc:
                    fc.append(first_tag)
        # Dedupe focus_concepts
        seen, deduped = set(), []
        for c in fc:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        path_data["focus_concepts"] = deduped

        path_file.write_text(json.dumps(path_data, indent=2, ensure_ascii=False) + "\n")
        audit.append(f"  ABSORB {target_slug}: +{len(added)} Qs (now {len(current_qids)})")

    return audit


# ---------------------------------------------------------------------------
# PART 3: update path_patterns.py registry — add 6 new pyspark slugs, remove old spark-basics
# ---------------------------------------------------------------------------
def update_pattern_registry():
    pp_file = REPO / "backend" / "path_patterns.py"
    content = pp_file.read_text()
    audit = []

    # Find the pyspark block
    marker = '    "pyspark": {'
    idx = content.find(marker)
    end_idx = content.find("    },", idx)

    # Old pyspark block content
    old_block = content[idx:end_idx]

    # Build new entries
    new_entries = []
    for slug, label in PYSPARK_NEW_PATTERNS.items():
        if f'"{slug}":' not in old_block:
            new_entries.append(f'        "{slug}": "{label}",\n')

    if new_entries:
        addition = "".join(new_entries)
        content = content[:end_idx] + addition + content[end_idx:]
        audit.append(f"  REGISTER {len(new_entries)} new pyspark patterns")

    # Remove old "spark-basics" from pyspark block (no longer used after split)
    # Refresh indices since we modified content
    idx2 = content.find(marker)
    end_idx2 = content.find("    },", idx2)
    block2 = content[idx2:end_idx2]
    if '"spark-basics":' in block2:
        # Find and remove the spark-basics line
        for line_to_remove in [
            '        "spark-basics": "Core Spark Concepts",\n',
            '        "spark-basics": "Spark Basics",\n',
        ]:
            if line_to_remove in content:
                content = content.replace(line_to_remove, "")
                audit.append("  REMOVE old 'spark-basics' pattern entry")
                break

    pp_file.write_text(content)
    return audit


# ---------------------------------------------------------------------------
# PART 4: update test guardrail 4-15 → 4-20
# ---------------------------------------------------------------------------
def update_test_guardrail():
    f = REPO / "backend" / "tests" / "test_paths_quality.py"
    content = f.read_text()
    new_content = content

    # Replace the count check
    new_content = new_content.replace(
        "if n < 4 or n > 30:",
        "if n < 4 or n > 20:"
    )
    new_content = new_content.replace(
        "if n < 4 or n > 15:",
        "if n < 4 or n > 20:"
    )
    # Replace error messages
    new_content = new_content.replace(
        '"4–30 question sanity range"',
        '"4–20 question sanity range (default cap is 15; 16–20 requires explicit approval per path)"'
    )
    new_content = new_content.replace(
        '"4–15 question sanity range"',
        '"4–20 question sanity range (default cap is 15; 16–20 requires explicit approval per path)"'
    )

    # Update docstring
    if "Sanity guardrail: paths should be 4–30 questions." in new_content:
        new_content = new_content.replace(
            "Sanity guardrail: paths should be 4–30 questions.",
            "Sanity guardrail: paths should be 4–20 questions (default 15; 16–20 with approval)."
        )
    elif "Sanity guardrail: paths should be 4–15 questions." in new_content:
        new_content = new_content.replace(
            "Sanity guardrail: paths should be 4–15 questions.",
            "Sanity guardrail: paths should be 4–20 questions (default 15; 16–20 with approval)."
        )

    if new_content != content:
        f.write_text(new_content)
        return ["  UPDATE test guardrail: 4–15 → 4–20 (default 15; 16–20 requires explicit approval)"]
    return ["  WARN: test guardrail update made no changes (file structure may differ)"]


def execute():
    print("=== Spark split + yellow absorptions + guardrail extension ===\n")
    print("PART 1 — spark-core-concepts split:")
    for line in split_spark():
        print(line)
    print()
    print("PART 2 — yellow absorptions:")
    for line in apply_yellow_absorptions():
        print(line)
    print()
    print("PART 3 — pattern registry update:")
    for line in update_pattern_registry():
        print(line)
    print()
    print("PART 4 — test guardrail extension:")
    for line in update_test_guardrail():
        print(line)


if __name__ == "__main__":
    execute()
