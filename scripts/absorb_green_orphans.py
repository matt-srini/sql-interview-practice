"""Bucket A — green absorptions only.

For each orphan whose tag-suggested pattern matches one of the GREEN
absorption targets, append the orphan's question ID to the designated
live path's questions[]. Re-sort by (difficulty, qid). Broaden the path's
focus_concepts ONLY IF needed to satisfy validator rule 5 — never touch
question content.

GREEN absorptions are the 22 cases where the target live path stays at or
under the 15-Q ceiling after absorption. Borderline (16–20) and Heavy (21+)
absorptions are deliberately excluded — they're per-path judgment calls
left out of this batch.

Output:
- Modifies path JSON files only (questions[], focus_concepts[] if needed)
- ZERO question file edits (verified by precondition: only reads question files)
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


# Green absorptions: (track, source_tag_pattern) → target_path_slug
GREEN_ABSORPTIONS: dict[tuple[str, str], str] = {
    # SQL — 5 paths, 15 Qs total
    ("sql", "period-over-period"): "period-over-period-analysis",
    ("sql", "funnel-and-event-analysis"): "funnel-and-events",
    ("sql", "window-functions"): "window-functions-mastery",
    ("sql", "string-and-text"): "sql-string-and-date",
    ("sql", "cohort-and-retention"): "cohort-and-retention",
    # Python — 1 path, 1 Q
    ("python", "graph-traversal"): "graph-and-tree-patterns",
    # Pandas — 3 paths, 16 Qs
    ("python-data", "time-series-pandas"): "time-series-analysis",
    ("python-data", "dataframe-basics"): "dataframe-fundamentals",
    ("python-data", "reshape-and-pivot"): "reshaping-and-pivoting",
    # PySpark — 3 paths, 9 Qs
    ("pyspark", "streaming"): "streaming-fundamentals",
    ("pyspark", "query-optimization"): "query-optimization",
    ("pyspark", "delta-lake"): "delta-lake-patterns",
    # DE — 1 path, 2 Qs
    ("data-engineering", "lineage-and-observability"): "lineage-and-observability",
    # DM — 1 path, 1 Q
    ("data-modeling", "wide-tables"): "wide-tables-and-obt",
    # Stats — 2 paths, 10 Qs
    ("statistics", "hypothesis-testing"): "hypothesis-testing",
    ("statistics", "descriptive-stats"): "descriptive-stats",
    # ML — 3 paths, 5 Qs
    ("ml-fundamentals", "production-and-monitoring"): "ml-production",
    ("ml-fundamentals", "supervised-unsupervised"): "ml-starter",
    ("ml-fundamentals", "feature-engineering"): "feature-engineering",
    # Experimentation — 3 paths, 11 Qs
    ("experimentation", "causal-inference"): "causal-inference-and-advanced-experimentation",
    ("experimentation", "variance-reduction"): "variance-reduction-and-behavioral-effects",
    ("experimentation", "subgroup-and-hte"): "subgroup-analysis-and-hte",
}

DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


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


def execute():
    paths_dir = REPO / "backend" / "content" / "paths"
    live = _load_live_paths_by_track()

    # Group additions by target path
    additions_by_path: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for (track, src_pattern), target_slug in GREEN_ABSORPTIONS.items():
        qmap = load_qmap(track)
        _, _, _, orphans, _ = walk_track(track, TRACK_DIRS[track], live_paths=live.get(track, []))
        matching = [o for o in orphans if o["tag_pattern"] == src_pattern]
        for o in matching:
            q = qmap.get(o["qid"])
            additions_by_path[target_slug].append((o["qid"], q, track))

    audit_log = []
    total_absorbed = 0
    total_broadened = 0

    for target_slug, items in sorted(additions_by_path.items()):
        path_file = paths_dir / f"{target_slug}.json"
        if not path_file.exists():
            audit_log.append(f"  WARN: target path {target_slug}.json not found; skipping {len(items)} orphans")
            continue
        path_data = json.loads(path_file.read_text())
        track = path_data["topic"]
        qmap = load_qmap(track)

        current_qids = set(int(q) for q in path_data["questions"])
        added_qids = []
        for qid, q, _track in items:
            if qid in current_qids:
                continue
            current_qids.add(qid)
            added_qids.append(qid)

        # Re-sort
        path_data["questions"] = sorted(
            current_qids,
            key=lambda qid: (DIFF_ORDER.get(qmap.get(qid, {}).get("__diff", "easy"), 9), qid),
        )

        # Check rule 5 for the newly added Qs; broaden focus_concepts if needed
        fc = list(path_data.get("focus_concepts", []))
        broadened_here = []
        for qid in added_qids:
            q = qmap.get(qid, {})
            q_tags = q.get("concepts", []) or []
            matched = any(concept_matches_focus(t, f, track) for t in q_tags for f in fc)
            if not matched and q_tags:
                # Add the question's first tag if not already in focus_concepts
                first_tag = q_tags[0]
                if first_tag not in fc:
                    fc.append(first_tag)
                    broadened_here.append(first_tag)
        if broadened_here:
            # Dedupe
            seen, deduped = set(), []
            for c in fc:
                if c not in seen:
                    seen.add(c)
                    deduped.append(c)
            path_data["focus_concepts"] = deduped
            total_broadened += len(set(broadened_here))

        path_file.write_text(json.dumps(path_data, indent=2, ensure_ascii=False) + "\n")
        before = len(items) and (len(current_qids) - len(added_qids))
        audit_log.append(
            f"  {target_slug:<55} +{len(added_qids):>2} Qs "
            f"({before} → {len(current_qids)})"
            + (f"  broadened focus_concepts: {broadened_here}" if broadened_here else "")
        )
        total_absorbed += len(added_qids)

    print("=== Bucket A green absorptions ===")
    for line in audit_log:
        print(line)
    print()
    print(f"  Total orphans absorbed:   {total_absorbed}")
    print(f"  Total focus_concepts broadened: {total_broadened}")


if __name__ == "__main__":
    execute()
