"""Trim near-duplicate questions from paths over 15 Qs.

Per-Q rationale captured in DROPS. All dropped Qs remain in the catalog
(solvable via /practice) — they just leave the curated walk.

Re-runnable + idempotent.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATHS_DIR = REPO / "backend" / "content" / "paths"

# (qid, kept_path, drop_reason)
DROPS = [
    # --- applied-stats: 18 → 15 (-3) ---
    (72038, "applied-stats",
     "Sampling Bias in Funnel duplicates 72034 Survivorship Bias (same concept; survivorship is more classic)."),
    (73007, "applied-stats",
     "Computing R-Squared is rote computation; 73006 R-Squared Interpretation teaches the reasoning."),
    (73018, "applied-stats",
     "Regression Bias-Variance Decomposition duplicates 73008 Bias-Variance Tradeoff (canonical conceptual version)."),

    # --- experimentation-starter: 17 → 15 (-2) ---
    (91002, "experimentation-starter",
     "Easy 'Choosing a Primary Metric' duplicates medium 92005 'Choosing the Right Primary Metric' — keep the deeper version."),
    (91014, "experimentation-starter",
     "Easy 'Guardrail Metrics' duplicates medium 92026 'Guardrail Metrics and Ship Decisions' — keep the deeper version."),

    # --- joins-and-filtering: 17 → 15 (-2) ---
    (12012, "joins-and-filtering",
     "'Brand reach in completed 2024 orders' overlaps 12020 'High-volume brands in completed 2024 orders' — keep 12020 + 12023 anti-join."),
    (12020, "joins-and-filtering",
     "'High-volume brands in completed 2024 orders' — same dataset framing as 12012/12023; trim to keep the anti-join Q 12023 as the distinctive one."),

    # --- aggregation-patterns: 18 → 15 (-3) ---
    (12004, "aggregation-patterns",
     "'Paid revenue by user country' is a subset of 12011 'Paid completed orders by country' (which adds JOIN + dedup)."),
    (11010, "aggregation-patterns",
     "'Support tickets by issue type' duplicates 11008 'Orders by status' (both basic COUNT-by-group)."),
    (11028, "aggregation-patterns",
     "'Highest and lowest order value' duplicates 11006 'Most expensive product' (both MIN/MAX patterns)."),

    # --- distributions: 18 → 17 (-1) ---
    (73009, "distributions",
     "'Chi-Squared Test Statistic' is rote computation; 73019 'Chi-Squared Test of Independence' teaches the same concept applied."),

    # --- scd: 17 → 16 (-1) ---
    (61015, "scd",
     "'SCD Type 1 vs Type 2' duplicates 63002 'Choosing the Right SCD Strategy for Analyst-Facing' (hard case study covers the same trade-off + applies it)."),

    # --- spark-joins-and-skew: 18 → 17 (-1) ---
    (42051, "spark-joins-and-skew",
     "'One-to-Many Join Row Count' is a subset of 43047 'Many-to-Many Join Fan-Out' (many-to-many subsumes one-to-many cardinality prediction)."),
]


def execute():
    print("=== Trimming near-duplicate Qs from paths over 15 ===\n")
    # Group by path for one write per path
    by_path: dict[str, list[int]] = {}
    rationales: dict[int, str] = {}
    for qid, slug, reason in DROPS:
        by_path.setdefault(slug, []).append(qid)
        rationales[qid] = reason

    for slug in sorted(by_path.keys()):
        f = PATHS_DIR / f"{slug}.json"
        d = json.loads(f.read_text())
        before = list(d["questions"])
        drop = by_path[slug]
        after = [q for q in before if q not in drop]
        d["questions"] = after
        f.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
        actually_dropped = [q for q in drop if q in before]
        print(f"{slug}: {len(before)} → {len(after)} Qs")
        for qid in actually_dropped:
            print(f"  − {qid}: {rationales[qid][:90]}")
        print()


if __name__ == "__main__":
    execute()
