"""B-series F3 — ship the 14 new paths that have ≥4 orphans available.

Creates 14 new pattern paths from F3 candidates whose orphan pool is
large enough (≥4 questions) to clear the path-size floor. Each new path
is named for its pattern and contains the orphan questions that tag-route
to that pattern.

Also registers the 14 new pattern slugs in backend/path_patterns.py.

Patterns skipped (3 or fewer orphans — defer to future content growth):
  SQL: top-n-and-ranking (3)
  Python: streaming-and-online (3)
  Pandas: window-and-rolling (2)
  DM: surrogate-keys (3), hierarchies-and-multipath (3), conformed-dimensions (1)
  Stats: variance-and-anova (3), survival-analysis (3)
  ML: algorithmic-fairness (3)
  Exp: sequential-and-bandits (3), experiment-platform-design (1)

For cost-and-format-optimization (20 Qs > 15 ceiling), trims to 15 by
dropping the 5 questions that fit other patterns better (SCD-tagged and
overlapping-with-delta-lake ones).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO / "scripts"))

from audit_pattern_coverage import TRACK_DIRS, walk_track, _load_live_paths_by_track

DIFF_ORDER = {"easy": 0, "medium": 1, "hard": 2}


# ---------------------------------------------------------------------------
# Patterns to register in backend/path_patterns.py
# (slug → human label, per track)
# ---------------------------------------------------------------------------
NEW_PATTERN_REGISTRATIONS: dict[str, dict[str, str]] = {
    "python": {
        "string-and-text-processing": "String & Text Processing",
        "heap-and-priority": "Heaps & Priority Queues",
    },
    "python-data": {
        "top-n-and-ranking": "Top-N & Ranking",
    },
    "pyspark": {
        "pyspark-windowing": "Window Functions & Frames",
    },
    "data-engineering": {
        "cost-and-format-optimization": "Cost & Format Optimization",
        "streaming-vs-batch": "Streaming vs Batch Architecture",
    },
    "data-modeling": {
        "data-vault": "Data Vault Modeling",
        "aggregate-and-summary-design": "Aggregate & Summary Design",
    },
    "statistics": {
        "bayesian-reasoning": "Bayesian Reasoning",
        "errors-and-power": "Errors, Power & Multiple Testing",
        "sampling-and-clt": "Sampling & CLT",
    },
    "ml-fundamentals": {
        "hyperparameter-tuning": "Hyperparameter Tuning",
        "neural-networks-and-gradients": "Neural Networks & Gradient Behaviour",
        "unsupervised-methods": "Unsupervised Methods",
    },
}


# ---------------------------------------------------------------------------
# Per-new-path metadata
# ---------------------------------------------------------------------------
NEW_PATH_SPECS: dict[str, dict] = {
    "string-and-text-processing": {
        "track": "python",
        "title": "String & Text Processing",
        "description": "Master the string and text patterns every data-Python role probes: character counting, compression, prefix matching, and trie-based search — the practical scaffolding behind log parsing, deduplication, and autocomplete.",
        "tier": "free",
        "level": "intermediate",
        "focus_concepts": ["STRING PATTERN REASONING", "INDEXED SEQUENCE REASONING"],
        "outcomes": "You'll process strings character-by-character with intent, design compression and prefix-matching algorithms, and build trie structures for fast prefix queries — the patterns behind real log-parsing and autocomplete code.",
        "recommended_after": ["arrays-and-hashing"],
    },
    "heap-and-priority": {
        "track": "python",
        "title": "Heaps & Priority Queues",
        "description": "Master the heap and priority-queue patterns every senior algorithm interview probes: Top-K from a stream, median maintenance with dual heaps, and minimum-resource scheduling under tight constraints.",
        "tier": "free",
        "level": "advanced",
        "focus_concepts": ["HEAP & PRIORITY QUEUE", "GREEDY CHOICE"],
        "outcomes": "You'll reach for heaps fluently when the problem hints at Top-K or rolling-extremes, design dual-heap median maintenance, and solve minimum-resource scheduling problems with the right greedy + priority-queue combination.",
        "recommended_after": ["arrays-and-hashing"],
    },
    "top-n-and-ranking": {
        "track": "python-data",
        "title": "Top-N & Ranking",
        "description": "Master the Top-N-per-group pattern that dominates Pandas analytics interviews: rank-within-group, percentile rank, latest-row-per-key, and the multi-table top-N that production dashboards depend on.",
        "tier": "free",
        "level": "intermediate",
        "focus_concepts": ["RANKING & TOP-N PER GROUP", "GROUPED AGGREGATION"],
        "outcomes": "You'll fluently rank rows within groups, compute percentile ranks, pick the latest row per key, and build Top-N-per-category queries that survive ties and edge cases.",
        "recommended_after": ["groupby"],
    },
    "pyspark-windowing": {
        "track": "pyspark",
        "title": "Window Functions & Frames",
        "description": "Master PySpark's window functions and frame semantics: RANK vs DENSE_RANK vs ROW_NUMBER under ties, ROWS vs RANGE behaviour with tied values, and the rangeBetween gotchas that silently change output when dates have gaps.",
        "tier": "free",
        "level": "intermediate",
        "focus_concepts": ["WINDOW FUNCTIONS & FRAMES"],
        "outcomes": "You'll choose RANK/DENSE_RANK/ROW_NUMBER correctly when ties matter, predict ROWS-vs-RANGE running-sum behaviour, and debug rangeBetween edge cases on integer dates and data gaps.",
        "recommended_after": ["spark-basics"],
    },
    "cost-and-format-optimization": {
        "track": "data-engineering",
        "title": "Cost & Format Optimization",
        "description": "Master the storage, format, and partitioning decisions that decide whether your pipeline costs $200/month or $20K/month: partition key choice, small-file problem, Parquet vs Avro, compaction, scan-cost optimization, and tiered storage.",
        "tier": "pro",
        "level": "intermediate",
        "focus_concepts": ["COST OPTIMIZATION", "STORAGE LAYOUT & FILE FORMATS", "PARTITIONING & PRUNING", "STORAGE ARCHITECTURE"],
        "outcomes": "You'll pick a partition key that avoids the small-file problem, choose between Parquet and Avro from the read pattern, apply compaction strategies, design tiered storage for cold data, and reduce warehouse scan costs through filter pushdown and materialization decisions.",
        "recommended_after": ["pipeline-fundamentals"],
        # Trim list — explicit exclusions to bring 20→15 (drop SCD-tangential + overlapping-with-delta-lake)
        "trim_exclude": [51017, 53010, 53018, 51019, 51020],
    },
    "streaming-vs-batch": {
        "track": "data-engineering",
        "title": "Streaming vs Batch Architecture",
        "description": "Master the architectural decision every production data team eventually faces: when streaming actually wins over batch, micro-batch vs true streaming latency, Lambda architecture trade-offs, and how to handle backpressure when the source outpaces the sink.",
        "tier": "pro",
        "level": "intermediate",
        "focus_concepts": ["BATCH VS STREAMING", "SCHEDULING & SLAS", "BACKPRESSURE"],
        "outcomes": "You'll justify when streaming actually wins over batch, distinguish micro-batch from true streaming on latency grounds, design Lambda-architecture trade-offs honestly, and handle backpressure without dropping events.",
        "recommended_after": ["pipeline-fundamentals"],
    },
    "data-vault": {
        "track": "data-modeling",
        "title": "Data Vault Modeling",
        "description": "Master the Hub-Link-Satellite methodology that enterprise data warehouses use to integrate multi-source data without losing source-system fidelity: Hub design for multi-source IDs, Satellite design for attribute conflicts, and Link design for multi-party financial relationships.",
        "tier": "pro",
        "level": "advanced",
        "focus_concepts": ["DATA VAULT", "SURROGATE VS NATURAL KEYS", "BRIDGE & MANY-TO-MANY", "SCHEMA FROM REQUIREMENTS"],
        "outcomes": "You'll design Hubs that resolve multi-source customer-ID conflicts, model Satellites that preserve source-system attribute conflicts, and structure Links that carry multi-party financial relationships without losing audit fidelity.",
        "recommended_after": ["star-snowflake"],
    },
    "aggregate-and-summary-design": {
        "track": "data-modeling",
        "title": "Aggregate & Summary Design",
        "description": "Decide when to materialize aggregates vs query raw fact tables live: pre-aggregation trade-offs for high-cardinality dashboards, partitioning strategy for billion-row event facts, customer-lifetime-value modeling, and the cost-vs-freshness curve you sit on.",
        "tier": "pro",
        "level": "advanced",
        "focus_concepts": ["AGGREGATE & SUMMARY DESIGN", "FACT TABLE DESIGN", "DENORMALIZATION TRADEOFF"],
        "outcomes": "You'll decide when to pre-aggregate vs query live based on dashboard cardinality, partition + cluster billion-row event facts, model CLV in a dimensional schema, and navigate the cost-vs-freshness trade-offs that drive summary-table architecture.",
        "recommended_after": ["fact-table-design"],
    },
    "bayesian-reasoning": {
        "track": "statistics",
        "title": "Bayesian Reasoning",
        "description": "Master the Bayesian reasoning every senior DS/ML interview probes: Bayes' theorem application, prior-likelihood-posterior reasoning, conjugate priors (beta-binomial), and posterior mean computation that production A/B systems depend on.",
        "tier": "pro",
        "level": "intermediate",
        "focus_concepts": ["bayesian inference", "probability & combinatorics"],
        "outcomes": "You'll apply Bayes' theorem fluently in diagnostic settings, distinguish Bayesian from frequentist framings, compute beta-binomial conjugate-prior posteriors, and update a posterior under new evidence without re-running the whole analysis.",
        "recommended_after": ["probability-and-combinatorics"],
    },
    "errors-and-power": {
        "track": "statistics",
        "title": "Errors, Power & Multiple Testing",
        "description": "Master the discipline that decides whether your hypothesis-testing pipeline is honest: Type I vs Type II trade-offs, statistical power calculation, family-wise error rate under multiple comparisons, and the Bonferroni power loss that surprises analysts who 'just adjust p-values'.",
        "tier": "pro",
        "level": "intermediate",
        "focus_concepts": ["errors & power", "multiple testing & correction", "hypothesis testing"],
        "outcomes": "You'll compute power for a target effect size, apply Bonferroni or other corrections to multiple comparisons, predict the power loss your correction incurs, and design tests that survive the multiple-testing problem without sacrificing detectability.",
        "recommended_after": ["hypothesis-testing"],
    },
    "sampling-and-clt": {
        "track": "statistics",
        "title": "Sampling & CLT",
        "description": "Master the sampling-theory foundation every inferential statistics interview assumes: CLT applicability, standard error of the mean, the law of large numbers, and the sampling distribution of a proportion that A/B tests are built on.",
        "tier": "pro",
        "level": "intermediate",
        "focus_concepts": ["sampling & central limit theorem", "probability & combinatorics"],
        "outcomes": "You'll reason about when CLT applies (and when it doesn't), compute standard error of the mean correctly, distinguish LLN from CLT, and derive the sampling distribution of a proportion for A/B test design.",
        "recommended_after": ["distributions"],
    },
    "hyperparameter-tuning": {
        "track": "ml-fundamentals",
        "title": "Hyperparameter Tuning",
        "description": "Master the hyperparameter discipline every applied-ML role assumes: which hyperparameters move the model and which don't (criterion vs depth, max_iter vs C), learning-rate schedules, and choosing between grid search and Bayesian optimization for the search budget you have.",
        "tier": "free",
        "level": "intermediate",
        "focus_concepts": ["HYPERPARAMETER SENSITIVITY", "REGULARIZATION EFFECT", "GRADIENT DESCENT BEHAVIOR"],
        "outcomes": "You'll predict which hyperparameters move predictions and which don't, design learning-rate schedules for convergence behaviour, choose between grid search and Bayesian optimization based on the search budget, and reason about regularization hyperparameters (C, λ) without misinterpreting their direction of effect.",
        "recommended_after": ["cross-validation"],
    },
    "neural-networks-and-gradients": {
        "track": "ml-fundamentals",
        "title": "Neural Networks & Gradient Behaviour",
        "description": "Build practitioner intuition for the gradient-flow patterns every senior-ML interview probes: learning-rate effects, convergence indicators, NN architecture choice for tabular data, transfer-learning misalignment, and diagnosing vanishing gradients from activation saturation.",
        "tier": "pro",
        "level": "advanced",
        "focus_concepts": ["GRADIENT DESCENT BEHAVIOR", "NEURAL NETWORK DESIGN", "GRADIENT PATHOLOGY", "TRANSFER LEARNING STRATEGY"],
        "outcomes": "You'll reason about learning rate effects on convergence vs divergence, decide when a neural network beats a boosted tree on tabular data, diagnose domain-adaptation failures in transfer learning, and recognise vanishing gradients from activation-saturation patterns.",
        "recommended_after": ["ml-starter"],
    },
    "unsupervised-methods": {
        "track": "ml-fundamentals",
        "title": "Unsupervised Methods",
        "description": "Master the clustering evaluation challenges that have no ground truth: elbow method limitations, silhouette score interpretation, reconciling disagreement between the two, and evaluating clusters when you have no labels to compare against.",
        "tier": "free",
        "level": "intermediate",
        "focus_concepts": ["CLUSTERING EVALUATION", "DIMENSIONALITY REDUCTION", "HYPERPARAMETER SENSITIVITY"],
        "outcomes": "You'll apply elbow method critically (knowing its limits), interpret silhouette scores correctly, reconcile when elbow and silhouette disagree, and design evaluation strategies for clustering when ground truth is unknown.",
        "recommended_after": ["ml-starter"],
    },
}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
def order_questions(qids: list[int], qmap: dict) -> list[int]:
    return sorted(qids, key=lambda q: (DIFF_ORDER.get(qmap.get(q, {}).get("__diff", "easy"), 9), q))


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


def register_patterns():
    """Add new pattern slugs to backend/path_patterns.py."""
    pp_file = REPO / "backend" / "path_patterns.py"
    content = pp_file.read_text()
    n_added = 0
    for track, new_entries in NEW_PATTERN_REGISTRATIONS.items():
        # Find the track's block in PATH_PATTERNS
        marker = f'    "{track}": {{'
        idx = content.find(marker)
        if idx < 0:
            print(f"  WARN: track '{track}' block not found in path_patterns.py; skipping")
            continue
        # Find the closing }, of this track
        end_idx = content.find("    },", idx)
        if end_idx < 0:
            print(f"  WARN: track '{track}' end not found")
            continue
        # Check which entries are missing
        block = content[idx:end_idx]
        to_add = [(slug, label) for slug, label in new_entries.items() if f'"{slug}":' not in block]
        if not to_add:
            continue
        # Build insertion text — add before the closing brace
        addition = ""
        for slug, label in to_add:
            addition += f'        "{slug}": "{label}",\n'
            n_added += 1
        content = content[:end_idx] + addition + content[end_idx:]
    pp_file.write_text(content)
    return n_added


def execute():
    paths_dir = REPO / "backend" / "content" / "paths"
    audit_log: list[str] = []

    # Register patterns first
    n_added_patterns = register_patterns()
    audit_log.append(f"Registered {n_added_patterns} new pattern slugs in path_patterns.py")

    # For each F3 pattern, collect orphans and write a new path
    live = _load_live_paths_by_track()
    for slug, spec in NEW_PATH_SPECS.items():
        track = spec["track"]
        qmap = load_qmap(track)
        # Get orphans for this pattern
        _, _, _, orphans, _ = walk_track(track, TRACK_DIRS[track], live_paths=live.get(track, []))
        matching = [o["qid"] for o in orphans if o["tag_pattern"] == slug]
        # Apply trim exclusions if any
        trim = set(spec.get("trim_exclude", []))
        if trim:
            matching = [q for q in matching if q not in trim]
        ordered = order_questions(matching, qmap)

        path_json = {
            "slug": slug,
            "title": spec["title"],
            "description": spec["description"],
            "topic": track,
            "questions": ordered,
            "tier": spec["tier"],
            "level": spec["level"],
            "patterns": [slug],
            "focus_concepts": spec["focus_concepts"],
            "outcomes": spec["outcomes"],
            "recommended_after": spec["recommended_after"],
        }
        out_file = paths_dir / f"{slug}.json"
        out_file.write_text(json.dumps(path_json, indent=2, ensure_ascii=False) + "\n")
        audit_log.append(f"  CREATE {slug}.json ({len(ordered)} Qs, track={track}, level={spec['level']})")

    print("=== F3 batch path-creation summary ===")
    for line in audit_log:
        print(line)
    print()
    print(f"  Total new paths created: {len(NEW_PATH_SPECS)}")


if __name__ == "__main__":
    execute()
