"""Enforce the 1:1 question→path rule.

Resolves 15 pre-existing duplicates by removing each Q from the
non-primary path. Each removal is justified in the RESOLUTIONS table
based on the Q's title + concept tags vs the candidate paths' identities.

Also backfills `stacks-and-queues` with orphan 22088 (Next Greater
Element — classic monotonic-stack) because removing 22002 would drop
it to 3, breaching the 4-Q floor.

After this script, no question appears in more than one path.

Re-runnable + idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATHS_DIR = REPO / "backend" / "content" / "paths"


# (qid, primary_path_kept, non_primary_path_removed, rationale)
RESOLUTIONS = [
    # --- Python singleton dupe ---
    # Sliding Window Maximum is genuinely a both-paths Q: problem CATEGORY is sliding
    # window; canonical SOLUTION is a monotonic deque (stack-like). Keep in
    # stacks-and-queues because the *technique* (monotonic structure) is the
    # transferable lesson, and stacks-and-queues is thin (4 Qs) while
    # sliding-window-patterns is plentiful (11). Pragmatic tiebreaker for an
    # otherwise both-defensible call.
    (22002, "stacks-and-queues", "sliding-window-patterns",
     "Both paths claim it; tiebreaker is preserving 4-Q floor on stacks-and-queues. "
     "Monotonic deque is the canonical solution technique."),

    # --- Pandas singleton dupe ---
    (31002, "groupby", "dataframe-fundamentals",
     "GROUPED AGGREGATION primary tag → groupby. dataframe-fundamentals "
     "should be pure DataFrame creation / selection basics."),

    # --- DE singleton dupe ---
    (51009, "backfill-design", "pipeline-fundamentals",
     "BACKFILL DESIGN is the more specific primary skill; pipeline-fundamentals "
     "is the foundational sampler."),

    # --- DM cluster: 7 Qs all kept in wide-tables-and-obt ---
    # All 7 are fundamentally wide-vs-normalized trade-off questions. Other paths
    # (normalization, dbt-modeling) had them as illustrative side examples; the
    # primary teaching is the design trade-off, which is wide-tables-and-obt's identity.
    (61018, "wide-tables-and-obt", "normalization-and-referential-integrity",
     "Trade-off Q (denorm read perf in OLAP). Primary: wide-vs-narrow."),
    (61019, "wide-tables-and-obt", "normalization-and-referential-integrity",
     "Trade-off Q (denorm cost: update anomalies). Primary: wide-vs-narrow tradeoff."),
    (62015, "wide-tables-and-obt", "normalization-and-referential-integrity",
     "Trade-off Q (when to denormalize). Primary: wide-vs-narrow choice."),
    (62017, "wide-tables-and-obt", "dbt-and-modern-analytics-modeling",
     "Wide OBT vs Star comparison Q. Primary: wide-vs-narrow design."),
    (62018, "wide-tables-and-obt", "dbt-and-modern-analytics-modeling",
     "Wide Table Scalability Limits. Primary: wide-vs-narrow design."),
    (63004, "wide-tables-and-obt", "dbt-and-modern-analytics-modeling",
     "Wide OBT vs Normalized for ML features. Primary: design tradeoff."),
    (63019, "wide-tables-and-obt", "dbt-and-modern-analytics-modeling",
     "Wide OBT vs Normalized for real-time. Primary: design tradeoff."),

    # --- ML starter cluster: 4 Qs removed from ml-starter ---
    # ml-starter is the foundational path; it accumulated Qs that more specifically
    # belong in the specialized intermediate paths. Each Q kept in the specialized
    # path; ml-starter shrinks from 14 to 10 (still healthy).
    (81007, "missing-data-and-preprocessing-hygiene", "ml-starter",
     "DATA SPLITTING + LEAKAGE primary; specialized path."),
    (81010, "cross-validation", "ml-starter",
     "Title 'Cross-Validation: Purpose and Motivation'. Specialized path."),
    (81019, "ml-advanced-methods", "ml-starter",
     "REGULARIZATION primary; advanced ML technique, not foundational."),
    (81025, "missing-data-and-preprocessing-hygiene", "ml-starter",
     "DATA SPLITTING + LEAKAGE primary; specialized path."),

    # --- ML pure-advanced dupe ---
    (82034, "ml-advanced-methods", "ml-production",
     "Random Forest ensemble behavior; algorithmic-techniques angle (ml-advanced-methods) "
     "beats productionization angle (ml-production) for this Q."),
]


# No backfills needed — flipped the 22002 decision (kept in stacks-and-queues,
# removed from sliding-window-patterns) so the 4-Q floor is preserved without
# adding a non-canonical orphan.
BACKFILLS: dict[str, list[int]] = {}


def execute():
    print("=== 1:1 dedupe: removing duplicates ===\n")

    # Apply removals
    by_path_remove: dict[str, list[int]] = {}
    for qid, keep, remove, _ in RESOLUTIONS:
        by_path_remove.setdefault(remove, []).append(qid)

    for slug, qids_to_remove in by_path_remove.items():
        f = PATHS_DIR / f"{slug}.json"
        d = json.loads(f.read_text())
        before = list(d["questions"])
        after = [q for q in before if q not in qids_to_remove]
        d["questions"] = after
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        removed = [q for q in qids_to_remove if q in before]
        print(f"  {slug}: {len(before)} → {len(after)} Qs (removed: {sorted(removed)})")

    # Apply backfills
    print("\n=== Backfills (to preserve 4-Q floor) ===\n")
    for slug, qids_to_add in BACKFILLS.items():
        f = PATHS_DIR / f"{slug}.json"
        d = json.loads(f.read_text())
        before = list(d["questions"])
        merged = sorted(set(before) | set(qids_to_add))
        d["questions"] = merged
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        added = [q for q in qids_to_add if q not in before]
        print(f"  {slug}: {len(before)} → {len(merged)} Qs (added: {sorted(added)})")

    # Audit summary
    print("\n=== Audit: any remaining duplicates? ===\n")
    from collections import defaultdict
    qid_to_paths = defaultdict(list)
    for f in sorted(PATHS_DIR.glob("*.json")):
        d = json.loads(f.read_text())
        for qid in d["questions"]:
            qid_to_paths[qid].append(d["slug"])
    dupes = {qid: paths for qid, paths in qid_to_paths.items() if len(paths) > 1}
    if dupes:
        print(f"  ⚠ {len(dupes)} duplicates remain:")
        for qid, paths in dupes.items():
            print(f"    {qid} → {paths}")
    else:
        print(f"  ✓ Zero duplicates. {len(qid_to_paths)} unique Qs across all paths.")


if __name__ == "__main__":
    execute()
