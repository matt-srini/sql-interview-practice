"""B5 — split oversized paths into 1:1 pattern paths.

Splits 7 paths that exceed the 15-Q sanity guardrail. For each split:
  - Read the old path JSON
  - Distribute its questions[] across target sub-pattern paths via
    tag-routing (using audit_pattern_coverage.py::route_question)
  - "OTHER" questions (don't fit any target sub-pattern) get routed
    per OTHER_DISPOSITION below: either into a sibling new path, an
    existing live path, or orphaned (catalog-only).
  - Write new path JSON files with predetermined metadata
  - Delete the old path file

Predetermined per-split metadata (titles, descriptions, outcomes,
focus_concepts, recommended_after, levels) is embedded in NEW_PATH_SPECS
below — these were authored to match each sub-pattern's content with
honest scoping.

The script is idempotent within a single run: re-running rebuilds
the same target state from the source paths. Run from repo root.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from audit_pattern_coverage import (
    ROUTING, NORMALIZE_PATTERN, route_question, TRACK_DIRS,
)


# ---------------------------------------------------------------------------
# Per-split target sub-pattern sets
# ---------------------------------------------------------------------------
SPLITS: dict[str, dict] = {
    "groupby-and-joins": {
        "track": "pandas",
        "targets": ["groupby", "joins-and-merges"],
    },
    "dimensional-modeling-deep-dive": {
        "track": "data-modeling",
        "targets": ["scd", "grain-definition", "bridge-tables"],
    },
    "pipeline-evolution": {
        "track": "data-engineering",
        "targets": ["schema-evolution", "delivery-semantics", "backfill-design"],
    },
    "schema-design-basics": {
        "track": "data-modeling",
        "targets": ["star-snowflake", "fact-table-design"],
    },
    "stats-for-analysts": {
        "track": "statistics",
        "targets": ["descriptive-stats", "distributions"],
    },
    "experimental-design-inference": {
        "track": "statistics",
        "targets": ["hypothesis-testing", "confidence-intervals"],
    },
    "ml-model-evaluation": {
        "track": "ml-fundamentals",
        "targets": ["cross-validation", "metrics"],
    },
}

# ---------------------------------------------------------------------------
# OTHER-question dispositions: where to send questions whose tag-routing
# doesn't match any of the split's target sub-patterns. Each value is the
# slug of an existing or newly-created path file. None means "orphan"
# (the question stays in the catalog but in no live path).
# ---------------------------------------------------------------------------
OTHER_DISPOSITION: dict[int, str | None] = {
    # groupby-and-joins OTHER
    32006: "time-series-pandas",  # 7-Day Rolling Revenue → existing time-series path
    # dimensional-modeling-deep-dive OTHER
    62017: "wide-tables-and-obt",  # OBT vs Normalized → existing wide-tables path
    # pipeline-evolution OTHER
    52022: None,  # Parquet vs Avro → orphan (no live cost-and-format path)
    # schema-design-basics OTHER
    61013: "scd",  # SCD Type 1 → new scd path (from dim-modeling split)
    61016: "grain-definition",  # Grain Definition → new grain-definition path
    61010: None,  # Surrogate Key vs Natural Key → orphan (no live surrogate-keys path)
    # stats-for-analysts OTHER
    71008: "probability-and-combinatorics",  # Probability of Union → existing
    # experimental-design-inference OTHER (9 Qs)
    72008: "hypothesis-testing",  # Statistical Power → new hypothesis-testing
    72010: "hypothesis-testing",  # When to use t vs z → new hypothesis-testing
    72031: "hypothesis-testing",  # Sequential testing / peeking → new
    72001: None,  # CLT — orphan (no live sampling-and-clt)
    72002: None,  # SE — orphan
    72018: None,  # Bayes' Theorem — orphan (no live bayesian path)
    72022: None,  # Sampling distribution of proportion — orphan
    72028: None,  # CLT sampling mean — orphan
    72032: None,  # Metric sensitivity — orphan (cross-track concern)
    # ml-model-evaluation OTHER (8 Qs)
    81022: "cross-validation",  # Stratified K-Fold → new cross-validation
    81019: "ml-advanced-methods",  # Regularization → existing ml-advanced-methods (regularization)
    82018: "ml-advanced-methods",  # Boosting — Each Tree Corrects → ensembles
    82019: "ml-advanced-methods",  # Boosting interaction → ensembles
    82034: "ml-advanced-methods",  # Ensemble Depth → ensembles
    82008: "class-imbalance",  # Threshold Tuning for Fraud → existing class-imbalance
    81016: None,  # Gradient Descent Learning Rate → orphan (no neural-networks live path)
    83013: None,  # Dim Reduction Before/After Split → orphan (no unsupervised-methods live path)
}

# ---------------------------------------------------------------------------
# New path JSON metadata (per new path being created)
# ---------------------------------------------------------------------------
NEW_PATH_SPECS: dict[str, dict] = {
    # python-data
    "groupby": {
        "title": "GroupBy Aggregation",
        "description": "Master the GroupBy patterns every Pandas analyst reaches for: aggregation, transform-vs-aggregate, named aggregation, multi-level grouping, pipeline composition, and the subtle pitfalls of group-then-rank.",
        "topic": "pandas",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["groupby"],
        "focus_concepts": ["GROUPED AGGREGATION", "TRANSFORM VS AGGREGATE", "METHOD CHAINING & PIPELINE STYLE"],
        "outcomes": "You'll choose between aggregate and transform fluently, name aggregations clearly with .agg, group-then-rank without breaking the index, and compose multi-step grouping pipelines with .pipe.",
        "recommended_after": ["dataframe-fundamentals"],
    },
    "joins-and-merges": {
        "title": "DataFrame Joins & Merges",
        "description": "Master multi-DataFrame entity linking in Pandas: inner/left/outer merges, three-table joins, fan-out detection, and the double-counting gotchas that silently inflate revenue when joins multiply rows.",
        "topic": "pandas",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["joins"],
        "focus_concepts": ["MULTI-DATAFRAME ENTITY LINKING", "DOUBLE-COUNTING DETECTION"],
        "outcomes": "You'll choose the right merge type from the question shape, detect and fix fan-out double-counting, design three-table joins without losing rows, and reason about merge keys when entities don't line up cleanly.",
        "recommended_after": ["groupby"],
    },
    # data-modeling
    "scd": {
        "title": "Slowly Changing Dimensions",
        "description": "Master the SCD type choices that every dimensional-modeling interview probes: Type 1 vs 2 vs 3 vs 6, performance-vs-storage trade-offs, conformed vs role-playing dimensions, and bi-temporal modeling under regulatory deadlines.",
        "topic": "data-modeling",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["scd"],
        "focus_concepts": ["SCD STRUCTURE", "DIMENSION DESIGN", "SCHEMA EVOLUTION", "BI-TEMPORAL MODELING"],
        "outcomes": "You'll pick the right SCD type for the business question, design conformed and role-playing dimensions correctly, reason about junk/degenerate dimensions, handle schema evolution on shared dimensions under deadline pressure, and write bi-temporal queries with both time axes.",
        "recommended_after": ["star-snowflake"],
    },
    "grain-definition": {
        "title": "Grain Definition",
        "description": "Build the discipline that prevents the silent fan-out, mixed-granularity, and accumulating-snapshot bugs that haunt every dimensional model: choose the right grain for transaction, snapshot, and accumulating fact tables, and translate ambiguous business requirements into a single declared grain.",
        "topic": "data-modeling",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["grain-definition"],
        "focus_concepts": ["GRAIN DEFINITION", "FACT TABLE DESIGN", "SCHEMA FROM REQUIREMENTS"],
        "outcomes": "You'll declare grain explicitly on every fact table, distinguish transaction from periodic-snapshot from accumulating-snapshot grain, avoid fact-to-fact fan-out, and translate ambiguous funnel/subscription requirements into a single defensible grain.",
        "recommended_after": ["fact-table-design"],
    },
    "bridge-tables": {
        "title": "Bridge Tables & Many-to-Many",
        "description": "Resolve the many-to-many dimensional modeling problems where a simple star schema breaks: student-course, multi-valued promotions, weighting-factor edge cases, and bridge-table designs that preserve correct aggregation.",
        "topic": "data-modeling",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["bridge-tables"],
        "focus_concepts": ["BRIDGE & MANY-TO-MANY", "DIMENSION DESIGN"],
        "outcomes": "You'll design bridge tables that resolve student-course-style many-to-many relationships without distorting aggregations, apply weighting-factor patterns for multi-valued dimensions, and recognise when a bridge is the right tool vs an outrigger or junk dimension.",
        "recommended_after": ["star-snowflake"],
    },
    "star-snowflake": {
        "title": "Star & Snowflake Schemas",
        "description": "Build the foundational mental model for data-warehouse schema design: star vs snowflake trade-offs, OLTP vs OLAP optimization goals, identifying facts vs dimensions, and choosing between lake/warehouse/lakehouse for mixed ML+BI workloads.",
        "topic": "data-modeling",
        "tier": "free",
        "level": "foundational",
        "patterns": ["star-snowflake"],
        "focus_concepts": ["DIMENSIONAL MODELING", "STORAGE ARCHITECTURE TRADEOFFS", "NORMALIZATION"],
        "outcomes": "You'll distinguish star from snowflake schemas on storage + join trade-offs, identify facts vs dimensions from a business description, and pick the right storage architecture (lake/warehouse/lakehouse) for ML + BI workloads.",
        "recommended_after": [],
    },
    "fact-table-design": {
        "title": "Fact Table Design",
        "description": "Master the fact-table type choices that decide how the rest of the warehouse must be queried: transaction, periodic snapshot, accumulating snapshot, semi-additive facts, and multi-currency requirements that drive the model.",
        "topic": "data-modeling",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["fact-table-design"],
        "focus_concepts": ["FACT TABLE DESIGN", "SCHEMA FROM REQUIREMENTS", "ADDITIVE VS NON-ADDITIVE"],
        "outcomes": "You'll pick the right fact-table type from the business event shape, distinguish additive from semi-additive measures (and avoid double-counting account balances), and translate healthcare-event-style requirements into a defensible fact-table design.",
        "recommended_after": ["star-snowflake"],
    },
    # data-engineering
    "schema-evolution": {
        "title": "Schema Evolution",
        "description": "Survive the schema changes that production pipelines accumulate: backward/forward compatibility, schema-registry CI enforcement, breaking changes with active consumers, and columnar-storage merge gotchas across Parquet sources.",
        "topic": "data-engineering",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["schema-evolution"],
        "focus_concepts": ["SCHEMA EVOLUTION", "DATA CONTRACT"],
        "outcomes": "You'll reason about backward vs forward compatibility under live consumers, operationalise data contracts via schema-registry CI, contain breaking-change rollouts, and resolve Parquet schema-merge upcasting issues without losing data.",
        "recommended_after": ["pipeline-fundamentals"],
    },
    "delivery-semantics": {
        "title": "Delivery Semantics",
        "description": "Master the at-least-once vs at-most-once vs exactly-once decisions that decide whether your pipeline silently loses or duplicates data: watermarks, producer-side EO, consumer-side state, fan-out sinks, and CDC watermark tuning for late events.",
        "topic": "data-engineering",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["delivery-semantics"],
        "focus_concepts": ["DELIVERY SEMANTICS", "WATERMARKING", "IDEMPOTENCY"],
        "outcomes": "You'll choose the right delivery guarantee for the failure mode, design producer-side exactly-once that survives transactional boundaries, tune watermarks for out-of-order event storms and multi-source joins, and prevent silent CDC drops.",
        "recommended_after": ["pipeline-fundamentals"],
    },
    "backfill-design": {
        "title": "Backfill Design",
        "description": "Design backfills that survive late-arriving dimensions, partition-aware reruns, and idempotency requirements without corrupting downstream consumers.",
        "topic": "data-engineering",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["backfill-design"],
        "focus_concepts": ["BACKFILL DESIGN", "IDEMPOTENCY", "SCD OPERATIONS"],
        "outcomes": "You'll design partition-aware backfills, make jobs backfill-safe through idempotency, and reason about SCD Type 2 behavior under late-arriving dimension changes.",
        "recommended_after": ["pipeline-fundamentals"],
    },
    # statistics
    "descriptive-stats": {
        "title": "Descriptive Statistics",
        "description": "Build the descriptive-stats foundation every data role assumes: mean vs median under skew, standard deviation reasoning, interquartile range, and the basic shape of a sample.",
        "topic": "statistics",
        "tier": "free",
        "level": "foundational",
        "patterns": ["descriptive-stats"],
        "focus_concepts": ["descriptive statistics"],
        "outcomes": "You'll choose between mean and median based on distribution shape, compute and interpret standard deviation and IQR, and describe a sample's central tendency and spread clearly.",
        "recommended_after": [],
    },
    "distributions": {
        "title": "Probability Distributions",
        "description": "Master the distributions every data role interview probes: Bernoulli, binomial, Poisson, normal (68-95-99.7), uniform, geometric, log-normal, F-statistic, and chi-squared tests of independence.",
        "topic": "statistics",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["distributions"],
        "focus_concepts": ["distributions"],
        "outcomes": "You'll pick the right distribution for a discrete or continuous scenario, compute Bernoulli/Binomial/Poisson probabilities, reason about normal-distribution z-scores and the 68-95-99.7 rule, and apply chi-squared tests of independence.",
        "recommended_after": ["descriptive-stats"],
    },
    "hypothesis-testing": {
        "title": "Hypothesis Testing",
        "description": "Apply the hypothesis-testing reasoning every experimentation interview probes: A/B test sample sizing, t vs z choice, statistical power, sequential testing and the peeking problem, and guardrail-metric violations.",
        "topic": "statistics",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["hypothesis-testing"],
        "focus_concepts": ["hypothesis testing", "errors & power"],
        "outcomes": "You'll size A/B tests for a target MDE, choose between t and z distributions correctly, reason about statistical power and Type I/II error trade-offs, recognise sequential testing peeking, and detect guardrail-metric violations.",
        "recommended_after": ["distributions"],
    },
    "confidence-intervals": {
        "title": "Confidence Intervals & Estimation",
        "description": "Construct and interpret confidence intervals correctly — frequentist coverage, sample-size sensitivity, MLE and method-of-moments estimation, bootstrap CIs, and the trade-offs between bootstrap and parametric methods.",
        "topic": "statistics",
        "tier": "pro",
        "level": "intermediate",
        "patterns": ["confidence-intervals"],
        "focus_concepts": ["confidence intervals & estimation"],
        "outcomes": "You'll construct and interpret 95% confidence intervals, derive MLE for Bernoulli and exponential parameters, apply method-of-moments estimation, build bootstrap percentile CIs, and reason about when bootstrap beats parametric CI.",
        "recommended_after": ["distributions"],
    },
    # ml-fundamentals
    "cross-validation": {
        "title": "Cross-Validation",
        "description": "Master the cross-validation choices that decide whether your evaluation is honest: stratified k-fold for imbalanced data, group k-fold for grouped observations, time-series split for temporal data, and the leakage gotchas that invalidate CV silently.",
        "topic": "ml-fundamentals",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["cross-validation"],
        "focus_concepts": ["CROSS-VALIDATION DESIGN", "DATA SPLITTING STRATEGY"],
        "outcomes": "You'll pick between standard k-fold, stratified k-fold, group k-fold, and time-series split based on the data's structure, and avoid the splits that silently leak target signal across folds.",
        "recommended_after": ["ml-starter"],
    },
    "metrics": {
        "title": "Model Metrics",
        "description": "Master the metric choices that decide whether your model gets the right thing right: precision vs recall for imbalanced fraud, F1 for multi-class, ROC-AUC interpretation, MSE vs MAE for skewed regression, and model calibration when high AUC isn't enough.",
        "topic": "ml-fundamentals",
        "tier": "free",
        "level": "intermediate",
        "patterns": ["metrics"],
        "focus_concepts": ["CLASSIFICATION METRICS", "REGRESSION METRICS", "MODEL CALIBRATION", "LOSS FUNCTION SELECTION"],
        "outcomes": "You'll pick precision/recall/F1/ROC-AUC for the right scenario, choose between MSE and MAE based on outlier behavior, recognise when a high-AUC model is still mis-calibrated and apply Platt scaling, and debug regression models with heteroscedastic residuals.",
        "recommended_after": ["ml-starter"],
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


def load_qmap_for_track(track: str) -> dict:
    qmap = {}
    content_dir = TRACK_DIRS[track]
    for f in sorted(content_dir.glob("*.json")):
        if f.stem == "schemas":
            continue
        diff = f.stem
        for q in json.loads(f.read_text()):
            q["__diff"] = diff
            qmap[int(q["id"])] = q
    return qmap


def determine_target(qid: int, track: str, qmap: dict, targets: set[str]) -> str | None:
    """Return the target sub-pattern slug for this question, or None for OTHER."""
    q = qmap.get(qid)
    if not q:
        return None
    tag_pattern, _ = route_question(track, q)
    if not tag_pattern:
        return None
    normalized = NORMALIZE_PATTERN.get(track, {}).get(tag_pattern, tag_pattern)
    if normalized in targets:
        return normalized
    if tag_pattern in targets:
        return tag_pattern
    return None  # OTHER


def order_questions(qids: list[int], qmap: dict) -> list[int]:
    return sorted(qids, key=lambda q: (DIFF_ORDER.get(qmap.get(q, {}).get("__diff", "easy"), 9), q))


def execute_splits():
    paths_dir = REPO / "backend" / "content" / "paths"
    audit_log: list[str] = []
    total_new = 0
    total_deleted = 0
    total_moved_other = 0

    # Build accumulators for NEW paths (some sub-patterns receive OTHERs from other splits)
    new_path_questions: dict[str, list[int]] = defaultdict(list)
    additions_to_existing: dict[str, list[int]] = defaultdict(list)
    orphaned_qids: list[int] = []

    for old_slug, spec in SPLITS.items():
        track = spec["track"]
        targets = set(spec["targets"])
        qmap = load_qmap_for_track(track)
        old_path_file = paths_dir / f"{old_slug}.json"
        if not old_path_file.exists():
            audit_log.append(f"  SKIP {old_slug}: file does not exist")
            continue
        old_path = json.loads(old_path_file.read_text())
        for qid in old_path["questions"]:
            tgt = determine_target(int(qid), track, qmap, targets)
            if tgt:
                new_path_questions[tgt].append(int(qid))
            else:
                disposition = OTHER_DISPOSITION.get(int(qid), "_UNKNOWN")
                if disposition is None:
                    orphaned_qids.append(int(qid))
                elif disposition == "_UNKNOWN":
                    audit_log.append(f"  WARN: q{qid} from {old_slug} has no OTHER_DISPOSITION; orphaning")
                    orphaned_qids.append(int(qid))
                elif disposition in NEW_PATH_SPECS:
                    new_path_questions[disposition].append(int(qid))
                    total_moved_other += 1
                else:
                    # Disposition is an existing live path
                    additions_to_existing[disposition].append(int(qid))
                    total_moved_other += 1

    # Write new path files
    for slug, slug_spec in NEW_PATH_SPECS.items():
        qids = new_path_questions.get(slug, [])
        track = slug_spec["topic"]
        qmap = load_qmap_for_track(track)
        ordered = order_questions(qids, qmap)
        path_json = {
            "slug": slug,
            "title": slug_spec["title"],
            "description": slug_spec["description"],
            "topic": slug_spec["topic"],
            "questions": ordered,
            "tier": slug_spec["tier"],
            "level": slug_spec["level"],
            "patterns": slug_spec["patterns"],
            "focus_concepts": slug_spec["focus_concepts"],
            "outcomes": slug_spec["outcomes"],
            "recommended_after": slug_spec["recommended_after"],
        }
        out_file = paths_dir / f"{slug}.json"
        out_file.write_text(json.dumps(path_json, indent=2) + "\n")
        audit_log.append(f"  CREATE {slug}.json ({len(ordered)} Qs, level={slug_spec['level']})")
        total_new += 1

    # Apply additions to existing paths
    for slug, qids_to_add in additions_to_existing.items():
        target_file = paths_dir / f"{slug}.json"
        if not target_file.exists():
            audit_log.append(f"  WARN: existing path '{slug}.json' not found for OTHER additions {qids_to_add}; orphaning")
            orphaned_qids.extend(qids_to_add)
            continue
        target_data = json.loads(target_file.read_text())
        # Determine track from path
        track = target_data["topic"]
        qmap = load_qmap_for_track(track)
        existing = set(int(q) for q in target_data["questions"])
        for qid in qids_to_add:
            existing.add(qid)
        target_data["questions"] = order_questions(list(existing), qmap)
        target_file.write_text(json.dumps(target_data, indent=2) + "\n")
        audit_log.append(f"  EXTEND {slug}.json (+{len(qids_to_add)} Qs from OTHER: {sorted(qids_to_add)})")

    # Delete old oversized paths
    for old_slug in SPLITS:
        old_file = paths_dir / f"{old_slug}.json"
        if old_file.exists():
            old_file.unlink()
            audit_log.append(f"  DELETE {old_slug}.json")
            total_deleted += 1

    print(f"=== B5 split summary ===")
    for line in audit_log:
        print(line)
    print()
    print(f"  Total new paths created:      {total_new}")
    print(f"  Total old paths deleted:      {total_deleted}")
    print(f"  Total OTHER Qs redistributed: {total_moved_other}")
    print(f"  Total Qs orphaned (catalog):  {len(orphaned_qids)}")
    if orphaned_qids:
        print(f"    Orphaned IDs: {sorted(orphaned_qids)}")


if __name__ == "__main__":
    execute_splits()
