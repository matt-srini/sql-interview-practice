"""Apply display_order to every learning path.

Within each track, paths are ordered foundational → intermediate → advanced
(by `level`). Within each level, this script applies a per-path
`display_order` (1-based) reflecting conceptual progression — earlier
numbers = earlier in the track's recommended walk.

Where two paths could honestly be ordered either way, the choice is the
author's; this script encodes one defensible ordering.

NO question-file edits. Only path JSON metadata.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATHS_DIR = REPO / "backend" / "content" / "paths"


# ---------------------------------------------------------------------------
# Per-track ordering — slug → display_order (1-based, lower = earlier)
# Foundational implicitly = 1 (singleton enforced by validator).
# Intermediate and advanced follow conceptual progression within their level.
# ---------------------------------------------------------------------------
DISPLAY_ORDER: dict[str, dict[str, int]] = {
    "sql": {
        # foundational
        "aggregation-patterns": 1,
        # intermediate (joins moved here from advanced — conceptually a mid-tier
        # construct that everything analytical depends on)
        "joins-and-filtering": 1,
        "window-functions-mastery": 2,
        "pivot-and-conditional-aggregation": 3,
        # advanced (analytical use cases that compose joins + windows)
        "subqueries-and-existence": 1,
        "sql-string-and-date": 2,
        "sql-advanced-patterns": 3,
        "period-over-period-analysis": 4,
        "cohort-and-retention": 5,
        "funnel-and-events": 6,
    },
    "python": {
        # foundational
        "arrays-and-hashing": 1,
        # intermediate (stacks-and-queues moved here — basic DS toolkit;
        # greedy-and-scanning + list-transformations added 2026-06-08 via Route 1)
        "string-and-text-processing": 1,
        "stacks-and-queues": 2,
        "sliding-window-patterns": 3,
        "greedy-and-scanning": 4,
        "list-transformations": 5,
        "streaming-and-online": 6,  # added 2026-06-08: orphan-closure
        # advanced
        "heap-and-priority": 1,
        "graph-and-tree-patterns": 2,
        "dynamic-programming": 3,
        "practical-data-python": 4,
    },
    "python-data": {
        # foundational
        "dataframe-fundamentals": 1,
        # intermediate (reshaping moved here — pivot/melt is everyday pandas)
        "data-cleaning": 1,
        "groupby": 2,
        "joins-and-merges": 3,
        "top-n-and-ranking": 4,
        "reshaping-and-pivoting": 5,
        # advanced
        "time-series-analysis": 1,
        "customer-analytics": 2,
    },
    "pyspark": {
        # foundational
        "spark-execution-model-and-dag": 1,
        # intermediate (spark-joins-and-skew moved here — joins are core)
        "spark-schema-and-type-handling": 1,
        "spark-joins-and-skew": 2,
        "spark-collections-and-arrays": 3,
        "spark-io-and-file-formats": 4,
        "spark-memory-and-driver-executor": 5,
        "spark-performance": 6,
        "pyspark-windowing": 7,
        "spark-udfs-and-python-boundary": 8,  # added 2026-06-08 via Route 1
        # advanced
        "query-optimization": 1,
        "spark-fault-tolerance-and-recovery": 2,
        "delta-lake-patterns": 3,
        "streaming-fundamentals": 4,
    },
    "data-engineering": {
        # foundational
        "pipeline-fundamentals": 1,
        # intermediate
        "streaming-vs-batch": 1,
        "schema-evolution": 2,
        "delivery-semantics": 3,
        "backfill-design": 4,
        "lineage-and-observability": 5,
        "cost-and-format-optimization": 6,
        # advanced
        "data-quality-and-incident-response": 1,
    },
    "data-modeling": {
        # foundational
        "star-snowflake": 1,
        # intermediate (normalization moved before SCD — more foundational)
        "fact-table-design": 1,
        "grain-definition": 2,
        "normalization-and-referential-integrity": 3,
        "scd": 4,
        "wide-tables-and-obt": 5,
        "bridge-tables": 6,
        # advanced
        "dbt-and-modern-analytics-modeling": 1,
        "aggregate-and-summary-design": 2,
        "data-vault": 3,
    },
    "statistics": {
        # foundational
        "descriptive-stats": 1,
        # intermediate
        "probability-and-combinatorics": 1,
        "distributions": 2,
        "sampling-and-clt": 3,
        "hypothesis-testing": 4,
        "confidence-intervals": 5,
        "errors-and-power": 6,
        # advanced (bayesian-reasoning moved here — paradigm shift, builds on frequentist)
        "applied-stats": 1,
        "bayesian-reasoning": 2,
    },
    "ml-fundamentals": {
        # foundational
        "ml-starter": 1,
        # intermediate
        "metrics": 1,
        "cross-validation": 2,
        "feature-engineering": 3,
        "missing-data-and-preprocessing-hygiene": 4,
        "class-imbalance": 5,
        "unsupervised-methods": 6,
        "hyperparameter-tuning": 7,
        # advanced
        "ml-advanced-methods": 1,
        "neural-networks-and-gradients": 2,
        "ml-production": 3,
    },
    "experimentation": {
        # foundational
        "experimentation-starter": 1,
        # intermediate (hypothesis-testing-and-ci added 2026-06-08 via Route 1)
        "experiment-design-and-power": 1,
        "subgroup-analysis-and-hte": 2,
        "hypothesis-testing-and-ci": 3,
        # advanced
        "variance-reduction-and-behavioral-effects": 1,
        "behavioral-effects-and-interference": 2,
        "causal-inference-and-advanced-experimentation": 3,
    },
}


def execute():
    audit: list[str] = []
    total = 0
    missing_paths: list[str] = []

    # Build slug→track index from order dict for cross-check
    expected_slugs_per_track = {
        track: set(orderings.keys()) for track, orderings in DISPLAY_ORDER.items()
    }
    found_slugs_per_track: dict[str, set] = {track: set() for track in expected_slugs_per_track}

    for f in sorted(PATHS_DIR.glob("*.json")):
        d = json.loads(f.read_text())
        slug = d["slug"]
        track = d["topic"]
        track_orderings = DISPLAY_ORDER.get(track, {})
        order = track_orderings.get(slug)
        if order is None:
            missing_paths.append(f"{track}/{slug}")
            continue
        found_slugs_per_track[track].add(slug)
        # Insert display_order field (after level for readability).
        # Skip any pre-existing display_order key in the source dict so the
        # NEW value placed after level isn't overwritten when we copy the
        # rest of the keys forward.
        new_d = {}
        for k, v in d.items():
            if k == "display_order":
                continue  # drop stale value; replaced below
            new_d[k] = v
            if k == "level":
                new_d["display_order"] = order
        # If level wasn't present (shouldn't happen), append at end
        if "display_order" not in new_d:
            new_d["display_order"] = order
        f.write_text(json.dumps(new_d, indent=2, ensure_ascii=False) + "\n")
        audit.append(f"  {track:<20} {slug:<48} display_order={order}")
        total += 1

    # Check for paths in DISPLAY_ORDER that didn't exist on disk
    for track, expected in expected_slugs_per_track.items():
        unfound = expected - found_slugs_per_track[track]
        if unfound:
            audit.append(f"  WARN: {track} expected paths not found on disk: {sorted(unfound)}")

    print("=== display_order applied ===")
    for line in audit[:90]:
        print(line)
    if len(audit) > 90:
        print(f"  ... +{len(audit)-90} more")
    print()
    print(f"  Total paths updated: {total}")
    if missing_paths:
        print(f"  Paths without an ordering in DISPLAY_ORDER ({len(missing_paths)}):")
        for p in missing_paths:
            print(f"    {p}")


if __name__ == "__main__":
    execute()
