"""Pattern-coverage audit script.

Walks every practice question across all 9 tracks, routes each to one
pattern-path using the per-track (concept-family → pattern) routing
tables, and emits a per-track coverage report:

  - Per pattern: question count + easy/medium/hard split + ordered IDs
  - Per concept-family: which patterns its questions landed in
  - Gap classification: empty / thin / uneven / healthy
  - Per-question proposed pattern (sidecar artefact)

This is documentation-only. No question JSONs or path JSONs are modified.

Routing rules:
  1. Mock-only questions are skipped entirely.
  2. For each practice question, resolve each concept tag to a family.
  3. If any family is analytical (in track's ANALYTICAL_FAMILIES set),
     route to its pattern — analytical wins over construct.
  4. Otherwise, route to the pattern of the first family that has a
     routing entry, in question.concepts declared order.
  5. Mock-only realism families (DATA QUALITY SKEPTICISM, etc.) never
     route — they're co-tags only.
  6. If no family routes, pattern = None (catalog-only).
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from concept_families import CONCEPT_FAMILIES, MOCK_ONLY_REALISM_FAMILIES, resolve_to_family

# ---------------------------------------------------------------------------
# Track → content dir
# ---------------------------------------------------------------------------
TRACK_DIRS = {
    "sql":               REPO / "backend/content/questions",
    "python":            REPO / "backend/content/python_questions",
    "python-data":       REPO / "backend/content/python_data_questions",
    "pyspark":           REPO / "backend/content/pyspark_questions",
    "data-engineering":  REPO / "backend/content/data_engineering_questions",
    "data-modeling":     REPO / "backend/content/data_modeling_questions",
    "statistics":        REPO / "backend/content/statistics_questions",
    "ml-fundamentals":   REPO / "backend/content/ml_fundamentals_questions",
    "experimentation":   REPO / "backend/content/experimentation_questions",
}

# ---------------------------------------------------------------------------
# Canonical pattern set per track (current registry + proposed expansions
# derived from the family inventory in 2026-XX audit).
#
# Each entry: pattern_slug → display_label
# ---------------------------------------------------------------------------
PROPOSED_PATTERNS: dict[str, dict[str, str]] = {
    "sql": {
        "aggregation": "Aggregation",
        "joins": "Joins",
        "subqueries": "Subqueries & EXISTS",
        "set-operations": "Set Operations (UNION / INTERSECT / EXCEPT)",
        "window-functions": "Window Functions",
        "ctes-and-recursion": "CTEs & Recursion",
        "grouping-extensions": "ROLLUP / CUBE / GROUPING SETS",
        "string-and-text": "String & Text Functions",
        "date-and-time": "Date & Time Functions",
        "cohort-and-retention": "Cohort & Retention Analysis",
        "funnel-and-event-analysis": "Funnel & Event Analysis",
        "period-over-period": "Period-over-Period & Trends",
        "top-n-and-ranking": "Top-N & Ranking",
        "pivot-and-unpivot": "Pivot & Conditional Aggregation",
    },
    "python": {
        "arrays-and-hashing": "Arrays & Hashing",
        "sliding-window": "Sliding Window & Two Pointers",
        "stacks-and-queues": "Stacks & Queues",
        "heap-and-priority": "Heaps & Priority Queues",
        "dynamic-programming": "Dynamic Programming",
        "graph-traversal": "Graph & Tree Traversal",
        "string-and-text-processing": "String & Text Processing",
        "streaming-and-online": "Streaming & Online Algorithms",
        "data-pipeline-scripting": "Data Pipeline Scripting",
    },
    "python-data": {
        "dataframe-basics": "DataFrame Basics",
        "groupby": "GroupBy Aggregation",
        "joins-and-merges": "Joins & Merges",
        "reshape-and-pivot": "Reshape & Pivot",
        "time-series-pandas": "Time Series",
        "window-and-rolling": "Window & Rolling Operations",
        "data-cleaning": "Data Cleaning",
        "top-n-and-ranking": "Top-N & Ranking",
        "customer-analytics": "Customer Analytics Pipelines",
    },
    "pyspark": {
        "spark-basics": "Core Spark Concepts",
        "spark-performance": "Spark Performance",
        "query-optimization": "Catalyst & Query Optimization",
        "spark-joins-and-skew": "Joins & Skew Handling",
        "streaming": "Structured Streaming",
        "delta-lake": "Delta Lake",
        "pyspark-windowing": "Window Functions & Frames",
    },
    "data-engineering": {
        "etl-elt": "ETL / ELT Design",
        "orchestration": "Pipeline Orchestration",
        "schema-evolution": "Schema Evolution",
        "delivery-semantics": "Delivery Semantics",
        "backfill-design": "Backfill Design",
        # `data-lineage` and `pipeline-observability` merged into one pattern
        # because the concept-family registry already combines them into a
        # single family ("LINEAGE & OBSERVABILITY"). Splitting at the path
        # layer was an earlier authoring assumption that the family registry
        # contradicts. Honest 1:1 = one pattern per family.
        "lineage-and-observability": "Lineage & Pipeline Observability",
        "streaming-vs-batch": "Streaming vs Batch Architecture",
        "cost-and-format-optimization": "Cost & Format Optimization",
        "data-quality-and-incident-response": "Data Quality & Incident Response",
    },
    "data-modeling": {
        "star-snowflake": "Star & Snowflake Schemas",
        "fact-table-design": "Fact Table Design",
        "surrogate-keys": "Surrogate vs Natural Keys",
        "grain-definition": "Grain Definition",
        "scd": "Slowly Changing Dimensions",
        "normalization": "Normalization (1NF–3NF)",
        "referential-integrity": "Referential Integrity",
        "bridge-tables": "Bridge Tables & Many-to-Many",
        "dbt-modeling": "dbt Layered Modeling",
        "wide-tables": "Wide Tables & OBT",
        "conformed-dimensions": "Conformed Dimensions",
        "data-vault": "Data Vault",
        "aggregate-and-summary-design": "Aggregate & Summary Design",
        "hierarchies-and-multipath": "Hierarchies & Multi-Path Dimensions",
    },
    "statistics": {
        "descriptive-stats": "Descriptive Statistics",
        "probability-and-combinatorics": "Probability & Combinatorics",
        "distributions": "Probability Distributions",
        "sampling-and-clt": "Sampling & CLT",
        "hypothesis-testing": "Hypothesis Testing",
        "confidence-intervals": "Confidence Intervals",
        "errors-and-power": "Errors, Power & Multiple Testing",
        "regression-and-correlation": "Regression, Correlation & Causality",
        "variance-and-anova": "Variance Decomposition & ANOVA",
        "bayesian-reasoning": "Bayesian Reasoning",
        "survival-analysis": "Survival Analysis & Time-to-Event",
    },
    "ml-fundamentals": {
        "supervised-unsupervised": "Supervised vs Unsupervised Framing",
        "bias-variance": "Bias-Variance & Overfitting",
        "cross-validation": "Cross-Validation",
        "metrics": "Model Metrics",
        "regularization": "Regularization",
        "ensembles": "Ensemble Methods",
        "missing-data-and-preprocessing": "Missing Data & Preprocessing Hygiene",
        "feature-engineering": "Feature Engineering",
        "class-imbalance": "Class Imbalance",
        "model-interpretability": "Model Interpretability",
        "unsupervised-methods": "Unsupervised Methods",
        "neural-networks-and-gradients": "Neural Networks & Gradient Behaviour",
        "hyperparameter-tuning": "Hyperparameter Tuning",
        "algorithmic-fairness": "Algorithmic Fairness",
        "production-and-monitoring": "Production ML & Monitoring",
    },
    "experimentation": {
        "ab-test-mechanics": "A/B Test Mechanics",
        "metric-selection": "Metric Selection",
        "power-and-sample-size": "Power & Sample Size",
        "variance-reduction": "Variance Reduction",
        "behavioral-effects-and-interference": "Behavioral Effects & Interference",
        "subgroup-and-hte": "Subgroup Analysis & HTE",
        "causal-inference": "Causal Inference",
        "sequential-and-bandits": "Sequential Testing & Bandits",
        "experiment-platform-design": "Experiment Platform Design",
    },
}

# ---------------------------------------------------------------------------
# Routing tables: (concept-family → pattern_slug) per track.
# Built by reading the concept_families.py registry and assigning each
# family to its canonical destination pattern. Families that legitimately
# split across patterns route to their *primary* pattern; per-question
# routing then applies analytical-wins tie-breaker.
# ---------------------------------------------------------------------------
ROUTING: dict[str, dict[str, str]] = {
    "sql": {
        "GROUPED AGGREGATION": "aggregation",
        "POST-AGGREGATION FILTERING": "aggregation",
        "PRE-AGGREGATION FILTERING": "aggregation",
        "CONDITIONAL LOGIC & CASE": "pivot-and-unpivot",  # CASE/WHEN is SQL pivot idiom
        "MULTI-TABLE ENTITY LINKING": "joins",
        "SUBQUERY PATTERNS": "subqueries",
        "SET OPERATIONS & COMPARISON": "set-operations",
        "WINDOW FUNCTIONS": "window-functions",
        "RUNNING TOTAL & MOVING WINDOW": "window-functions",
        "RANKING & TOP-N PER GROUP": "top-n-and-ranking",
        "CTE PIPELINE": "ctes-and-recursion",
        "SELF-COMPARISON & RECURSION": "ctes-and-recursion",
        "STRING PARSING & PATTERN MATCHING": "string-and-text",
        "TIME-SERIES BUCKETING & ARITHMETIC": "period-over-period",
        "COHORT RETENTION": "cohort-and-retention",
        "FUNNEL ANALYSIS": "funnel-and-event-analysis",
        "SESSIONIZATION": "funnel-and-event-analysis",
        "DEDUPLICATION LOGIC": None,    # loose family — route by other tags
        "NULL HANDLING & COALESCE": None,
        "RESULT SHAPING & ORDERING": None,
        # Mock-only realism families — never primary:
        "DATA QUALITY SKEPTICISM": None,
        "DOUBLE-COUNTING DETECTION": None,
        "METRIC INTERPRETATION & DENOMINATOR CHOICE": None,
        "METRIC RECONCILIATION": None,
        "OUTPUT SANITY VALIDATION": None,
        "PERFORMANCE-AWARE ANALYTICS": None,
    },
    "python": {
        "HASH-MAP STATE": "arrays-and-hashing",
        "INDEXED SEQUENCE REASONING": "arrays-and-hashing",
        "LIST & COLLECTION TRANSFORMATION": "data-pipeline-scripting",
        "IN-PLACE TRANSFORMATION & SPACE OPTIMIZATION": "arrays-and-hashing",
        "SLIDING WINDOW": "sliding-window",
        "TWO POINTERS": "sliding-window",
        "STACK & MONOTONIC STRUCTURES": "stacks-and-queues",
        "HEAP & PRIORITY QUEUE": "heap-and-priority",
        "DYNAMIC PROGRAMMING (1D)": "dynamic-programming",
        "DYNAMIC PROGRAMMING (2D)": "dynamic-programming",
        "GRAPH TRAVERSAL (BFS / DFS)": "graph-traversal",
        "WEIGHTED SHORTEST PATH": "graph-traversal",
        "UNION-FIND & DISJOINT SET": "graph-traversal",
        "STREAMING / ONLINE REDUCTION": "streaming-and-online",
        "STRING PATTERN REASONING": "string-and-text-processing",
        "BINARY SEARCH": "arrays-and-hashing",     # no own pattern; nearest fit
        "GREEDY CHOICE": None,                       # cross-cutting; route by co-tag
        "MODULAR ARITHMETIC & NUMBER THEORY": None,  # rare
        "BACKTRACKING & COMBINATORIAL SEARCH": None,
    },
    "python-data": {
        "GROUPED AGGREGATION": "groupby",
        "TRANSFORM VS AGGREGATE": "groupby",
        "MULTI-DATAFRAME ENTITY LINKING": "joins-and-merges",
        "RESHAPING & PIVOT": "reshape-and-pivot",
        "DATETIME OPERATIONS": "time-series-pandas",
        "WINDOW & ROLLING OPERATIONS": "window-and-rolling",
        "RANKING & TOP-N PER GROUP": "top-n-and-ranking",
        "MISSING VALUE STRATEGY": "data-cleaning",
        "DEDUPLICATION LOGIC": "data-cleaning",
        "CATEGORICAL & BINNING": "data-cleaning",
        "DEBUG PANDAS": "data-cleaning",
        "BOOLEAN INDEXING & FILTERING": "dataframe-basics",
        "COLUMN SELECTION & PROJECTION": "dataframe-basics",
        "OUTPUT SHAPE & ORDERING": "dataframe-basics",
        "METHOD CHAINING & PIPELINE STYLE": None,    # cross-cutting
        "MEMORY & VECTORIZATION REASONING": None,
        # Mock-only realism — never primary:
        "DATA QUALITY SKEPTICISM": None,
        "DOUBLE-COUNTING DETECTION": None,
        "METRIC INTERPRETATION & DENOMINATOR CHOICE": None,
        "OUTPUT SANITY VALIDATION": None,
        "PERFORMANCE-AWARE ANALYTICS": None,
    },
    "pyspark": {
        "EXECUTION MODEL REASONING": "spark-basics",
        "NARROW VS WIDE TRANSFORMATIONS": "spark-basics",
        "SCHEMA & TYPE HANDLING": "spark-basics",
        "COLLECTION & ARRAY OPERATIONS": "spark-basics",
        "JOIN STRATEGY SELECTION": "spark-joins-and-skew",
        "DATA SKEW & MITIGATION": "spark-joins-and-skew",
        "PARTITIONING STRATEGY": "spark-performance",
        "SHUFFLE REASONING": "spark-performance",
        "PERFORMANCE TUNING & TRADE-OFFS": "spark-performance",
        "MEMORY MANAGEMENT": "spark-performance",
        "CACHING & PERSISTENCE": "spark-performance",
        "CATALYST OPTIMIZER": "query-optimization",
        "ADAPTIVE QUERY EXECUTION": "query-optimization",
        "STRUCTURED STREAMING": "streaming",
        "DELTA LAKE OPERATIONS": "delta-lake",
        "WINDOW FUNCTIONS & FRAMES": "pyspark-windowing",
        "FAULT TOLERANCE & RECOVERY": "spark-basics",
        "FILE FORMATS & READERS": "spark-basics",
        "UDF & PYTHON BOUNDARY": "spark-performance",
        "DEBUG SPARK ERRORS": None,           # cross-cutting
        # Mock-only realism — never primary:
        "DATA QUALITY SKEPTICISM": None,
        "DOUBLE-COUNTING DETECTION": None,
        "OUTPUT SANITY VALIDATION": None,
    },
    "data-engineering": {
        "ETL VS ELT": "etl-elt",
        "CDC & INGESTION": "etl-elt",
        "IDEMPOTENCY": "etl-elt",
        "ORCHESTRATION": "orchestration",
        "SCHEDULING & SLAS": "orchestration",
        "SCHEMA EVOLUTION": "schema-evolution",
        "DATA CONTRACT": "schema-evolution",
        "DELIVERY SEMANTICS": "delivery-semantics",
        "WATERMARKING": "delivery-semantics",
        "BACKFILL DESIGN": "backfill-design",
        "LINEAGE & OBSERVABILITY": "lineage-and-observability",
        "DATA QUALITY": "data-quality-and-incident-response",
        "INCIDENT RESPONSE": "data-quality-and-incident-response",
        "BATCH VS STREAMING": "streaming-vs-batch",
        "BACKPRESSURE": "streaming-vs-batch",
        "COST OPTIMIZATION": "cost-and-format-optimization",
        "STORAGE LAYOUT & FILE FORMATS": "cost-and-format-optimization",
        "PARTITIONING & PRUNING": "cost-and-format-optimization",
        "STORAGE ARCHITECTURE": "cost-and-format-optimization",
        "SCD OPERATIONS": None,   # belongs to data-modeling primarily
        "DATA GOVERNANCE": None,  # thin (2 Qs)
    },
    "data-modeling": {
        "DIMENSIONAL MODELING": "star-snowflake",
        "FACT TABLE DESIGN": "fact-table-design",
        "ADDITIVE VS NON-ADDITIVE": "fact-table-design",
        "SURROGATE VS NATURAL KEYS": "surrogate-keys",
        "GRAIN DEFINITION": "grain-definition",
        "SCD STRUCTURE": "scd",
        "DIMENSION DESIGN": "scd",                    # most dim-design Qs are SCD-adjacent
        "NORMALIZATION": "normalization",
        "REFERENTIAL INTEGRITY": "referential-integrity",
        "BRIDGE & MANY-TO-MANY": "bridge-tables",
        "DBT MODELING": "dbt-modeling",
        "WIDE VS NARROW": "wide-tables",
        "DENORMALIZATION TRADEOFF": "wide-tables",
        "CONFORMED DIMENSIONS": "conformed-dimensions",
        "DATA VAULT": "data-vault",
        "AGGREGATE & SUMMARY DESIGN": "aggregate-and-summary-design",
        "HIERARCHIES & MULTI-PATH": "hierarchies-and-multipath",
        "BI-TEMPORAL MODELING": "scd",                # closest fit
        "SCHEMA EVOLUTION": "scd",
        "SCHEMA FROM REQUIREMENTS": None,             # cross-cutting; route by co-tag
        "SEMANTIC LAYER & METRIC GOVERNANCE": None,   # thin (1 Q)
        "DOUBLE-COUNTING & FAN-OUT": None,            # mock-only realism
    },
    "statistics": {
        "descriptive statistics": "descriptive-stats",
        "probability & combinatorics": "probability-and-combinatorics",
        "distributions": "distributions",
        "sampling & central limit theorem": "sampling-and-clt",
        "hypothesis testing": "hypothesis-testing",
        "confidence intervals & estimation": "confidence-intervals",
        "errors & power": "errors-and-power",
        "multiple testing & correction": "errors-and-power",
        "correlation, regression & causality": "regression-and-correlation",
        "variance decomposition & ANOVA": "variance-and-anova",
        "bayesian inference": "bayesian-reasoning",
        "survival analysis & time-to-event": "survival-analysis",
        "experimental design (within stats)": "hypothesis-testing",
    },
    "ml-fundamentals": {
        "SUPERVISED VS UNSUPERVISED": "supervised-unsupervised",
        "BIAS-VARIANCE TRADEOFF": "bias-variance",
        "OVERFITTING DIAGNOSIS": "bias-variance",
        "CROSS-VALIDATION DESIGN": "cross-validation",
        "DATA SPLITTING STRATEGY": "cross-validation",
        "CLASSIFICATION METRICS": "metrics",
        "REGRESSION METRICS": "metrics",
        "MODEL CALIBRATION": "metrics",
        "LOSS FUNCTION SELECTION": "metrics",
        "REGULARIZATION EFFECT": "regularization",
        "ENSEMBLE STRATEGY": "ensembles",
        "BOOSTING MECHANICS": "ensembles",
        "MISSING DATA STRATEGY": "missing-data-and-preprocessing",
        "DATA LEAKAGE DETECTION": "missing-data-and-preprocessing",
        "FEATURE SCALING NECESSITY": "feature-engineering",
        "FEATURE SELECTION STRATEGY": "feature-engineering",
        "FEATURE IMPORTANCE INTERPRETATION": "feature-engineering",
        "CLASS IMBALANCE HANDLING": "class-imbalance",
        "INTERPRETABILITY TRADEOFF": "model-interpretability",
        "CLUSTERING EVALUATION": "unsupervised-methods",
        "DIMENSIONALITY REDUCTION": "unsupervised-methods",
        "NEURAL NETWORK DESIGN": "neural-networks-and-gradients",
        "GRADIENT DESCENT BEHAVIOR": "neural-networks-and-gradients",
        "GRADIENT PATHOLOGY": "neural-networks-and-gradients",
        "TRANSFER LEARNING STRATEGY": "neural-networks-and-gradients",
        "HYPERPARAMETER SENSITIVITY": "hyperparameter-tuning",
        "ALGORITHMIC FAIRNESS": "algorithmic-fairness",
        "MODEL MONITORING": "production-and-monitoring",
        "TRAINING-SERVING SKEW": "production-and-monitoring",
        "DEPLOYMENT CONSTRAINTS": "production-and-monitoring",
    },
    "experimentation": {
        "A/B TEST MECHANICS": "ab-test-mechanics",
        "EXPERIMENT DESIGN": "ab-test-mechanics",
        "HYPOTHESIS FORMULATION": "ab-test-mechanics",
        "METRIC SELECTION": "metric-selection",
        "METRIC SENSITIVITY": "metric-selection",
        "STATISTICAL POWER": "power-and-sample-size",
        "SAMPLE SIZE BASICS": "power-and-sample-size",
        "EXPERIMENT DURATION": "power-and-sample-size",
        "STATISTICAL SIGNIFICANCE": "ab-test-mechanics",
        "TYPE I AND TYPE II ERRORS": "ab-test-mechanics",
        "CONFIDENCE INTERVALS": "ab-test-mechanics",
        "VARIANCE REDUCTION": "variance-reduction",
        "NETWORK EFFECTS": "behavioral-effects-and-interference",
        "NOVELTY EFFECTS": "behavioral-effects-and-interference",
        "SWITCHBACK EXPERIMENTS": "behavioral-effects-and-interference",
        "SEGMENTATION ANALYSIS": "subgroup-and-hte",
        "MULTIPLE TESTING": "subgroup-and-hte",
        "CAUSAL INFERENCE": "causal-inference",
        "QUASI-EXPERIMENTAL METHODS": "causal-inference",
        "SEQUENTIAL TESTING": "sequential-and-bandits",
        "MULTI-ARMED BANDIT": "sequential-and-bandits",
        "BAYESIAN EXPERIMENTATION": "sequential-and-bandits",
        "HOLDOUT GROUPS": "experiment-platform-design",
        "SAMPLE RATIO MISMATCH": "experiment-platform-design",
    },
}

# ---------------------------------------------------------------------------
# Per-track: which patterns are "analytical" (data-thinking) rather than
# "construct" (language toolkit). When a question's tags hit both axes,
# the analytical one wins.
# ---------------------------------------------------------------------------
ANALYTICAL_PATTERNS: dict[str, set[str]] = {
    "sql": {
        "cohort-and-retention", "funnel-and-event-analysis", "period-over-period",
        "top-n-and-ranking", "pivot-and-unpivot",
    },
    "python": {
        "streaming-and-online", "data-pipeline-scripting",
    },
    "python-data": {
        "customer-analytics", "data-cleaning", "top-n-and-ranking",
    },
    "pyspark": set(),  # all PySpark patterns are construct/architecture
    "data-engineering": set(),
    "data-modeling": set(),
    "statistics": {
        "regression-and-correlation", "bayesian-reasoning",
    },
    "ml-fundamentals": {
        "missing-data-and-preprocessing", "feature-engineering", "class-imbalance",
        "model-interpretability", "algorithmic-fairness", "production-and-monitoring",
    },
    "experimentation": {
        "behavioral-effects-and-interference", "subgroup-and-hte",
        "causal-inference", "sequential-and-bandits", "experiment-platform-design",
    },
}


# ---------------------------------------------------------------------------
# Walk
# ---------------------------------------------------------------------------
def route_question(track: str, q: dict) -> tuple[str | None, str]:
    """Return (pattern_slug or None, reason) for one practice question.

    Reason explains the routing decision in one short phrase, for the audit log.
    """
    routes = ROUTING.get(track, {})
    analytical = ANALYTICAL_PATTERNS.get(track, set())
    candidates: list[tuple[str, str, str]] = []  # (concept, family, pattern)

    for raw_concept in q.get("concepts", []) or []:
        if not isinstance(raw_concept, str):
            continue
        family = resolve_to_family(raw_concept, track)
        pattern = routes.get(family)
        if pattern:
            candidates.append((raw_concept, family, pattern))

    if not candidates:
        return None, "no concept-family routes to a pattern"

    # Analytical wins
    for concept, family, pattern in candidates:
        if pattern in analytical:
            return pattern, f"analytical-wins via family {family!r}"

    # Otherwise first construct match
    first = candidates[0]
    return first[2], f"first construct-family match: {first[1]!r}"


def walk_track(track: str, content_dir: Path):
    """Walk practice questions for one track. Returns dict of analyses."""
    per_question = []  # list of (qid, difficulty, title, pattern, reason, concepts)
    pattern_buckets: dict[str | None, list[tuple[int, str, str]]] = defaultdict(list)
    family_landings: dict[str, Counter] = defaultdict(Counter)

    for f in sorted(content_dir.glob("*.json")):
        if f.stem == "schemas":
            continue
        difficulty = f.stem
        for q in json.loads(f.read_text()):
            if q.get("mock_only"):
                continue
            qid = int(q["id"])
            title = q.get("title", "<untitled>")
            concepts = q.get("concepts", []) or []
            pattern, reason = route_question(track, q)
            per_question.append((qid, difficulty, title, pattern, reason, concepts))
            pattern_buckets[pattern].append((qid, difficulty, title))
            # Track which families "fed" this question's pattern
            for c in concepts:
                if isinstance(c, str):
                    family = resolve_to_family(c, track)
                    family_landings[family][pattern or "(unrouted)"] += 1

    return per_question, pattern_buckets, family_landings


# ---------------------------------------------------------------------------
# Classification + markdown rendering
# ---------------------------------------------------------------------------
def classify_pattern(qs: list[tuple[int, str, str]]) -> str:
    if not qs:
        return "EMPTY"
    n = len(qs)
    diffs = {d for (_, d, _) in qs}
    has_e = "easy" in diffs
    has_m = "medium" in diffs
    has_h = "hard" in diffs
    if n < 5:
        return "THIN"
    if not (has_e and has_m and has_h):
        return "UNEVEN"
    return "HEALTHY"


def render_markdown(audits: dict) -> str:
    lines: list[str] = []
    lines.append("# Pattern coverage audit (2026-XX)")
    lines.append("")
    lines.append("**Status:** durable record. Drives next content batch.")
    lines.append("**Generated by:** `scripts/audit_pattern_coverage.py` — re-run anytime to regenerate.")
    lines.append("")
    lines.append("This audit maps every practice question (mock-only excluded) to exactly one")
    lines.append("pattern-path using the per-track (concept-family → pattern) routing tables")
    lines.append("at the top of the script. The analytical pattern wins over the construct pattern")
    lines.append("when both apply to a question.")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append("| Track | Practice Qs | Patterns | Healthy | Uneven | Thin | Empty | Unrouted Qs |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for track, data in audits.items():
        pats = PROPOSED_PATTERNS.get(track, {})
        buckets = data["buckets"]
        per_q = data["per_question"]
        healthy = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "HEALTHY")
        uneven = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "UNEVEN")
        thin = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "THIN")
        empty = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "EMPTY")
        unrouted = len(buckets.get(None, []))
        total = len(per_q)
        lines.append(f"| {track} | {total} | {len(pats)} | {healthy} | {uneven} | {thin} | {empty} | {unrouted} |")
    lines.append("")
    lines.append("Legend: **Healthy** ≥5 Qs across easy/medium/hard · **Uneven** ≥5 Qs but missing a difficulty · **Thin** 1–4 Qs · **Empty** 0 Qs · **Unrouted** = question whose concept tags didn't match any pattern.")
    lines.append("")

    # Per-track sections
    for track, data in audits.items():
        pats = PROPOSED_PATTERNS.get(track, {})
        buckets = data["buckets"]
        per_q = data["per_question"]
        family_landings = data["family_landings"]

        lines.append("---")
        lines.append(f"## {track}")
        lines.append("")
        lines.append(f"Practice questions audited: **{len(per_q)}**.  Patterns in proposed canonical set: **{len(pats)}**.")
        lines.append("")
        lines.append("### Pattern coverage")
        lines.append("")
        lines.append("| Pattern | Display | Easy | Medium | Hard | Total | Class |")
        lines.append("|---|---|---:|---:|---:|---:|---|")
        for slug, label in pats.items():
            qs = buckets.get(slug, [])
            ne = sum(1 for (_, d, _) in qs if d == "easy")
            nm = sum(1 for (_, d, _) in qs if d == "medium")
            nh = sum(1 for (_, d, _) in qs if d == "hard")
            cls = classify_pattern(qs)
            cls_badge = {
                "HEALTHY": "✅ healthy",
                "UNEVEN": "⚠️ uneven",
                "THIN": "🟡 thin (needs content)",
                "EMPTY": "🔴 empty (needs content)",
            }[cls]
            lines.append(f"| `{slug}` | {label} | {ne} | {nm} | {nh} | {ne+nm+nh} | {cls_badge} |")
        # Unrouted bucket
        un = buckets.get(None, [])
        lines.append(f"| _(unrouted)_ | — | {sum(1 for (_,d,_) in un if d=='easy')} | {sum(1 for (_,d,_) in un if d=='medium')} | {sum(1 for (_,d,_) in un if d=='hard')} | {len(un)} | — |")
        lines.append("")

        # Concept-family → pattern landings cross-map
        lines.append("### Concept-family → pattern landings")
        lines.append("")
        lines.append("How each track family's questions distributed across patterns (a single question")
        lines.append("contributes once to each of its family tags — multi-tag questions count multiply).")
        lines.append("")
        lines.append("| Family | Top landing | Other landings |")
        lines.append("|---|---|---|")
        for fam, landing_counter in sorted(family_landings.items()):
            sorted_landings = landing_counter.most_common()
            if not sorted_landings:
                continue
            top = f"`{sorted_landings[0][0]}` ({sorted_landings[0][1]})"
            others = ", ".join(f"`{p}` ({n})" for p, n in sorted_landings[1:5])
            lines.append(f"| {fam} | {top} | {others or '—'} |")
        lines.append("")

        # Gap punch list
        thin_or_empty = [
            (slug, classify_pattern(buckets.get(slug, [])), len(buckets.get(slug, [])))
            for slug in pats
            if classify_pattern(buckets.get(slug, [])) in ("THIN", "EMPTY")
        ]
        if thin_or_empty:
            lines.append("### Coverage gaps in this track")
            lines.append("")
            for slug, cls, n in thin_or_empty:
                marker = "🔴" if cls == "EMPTY" else "🟡"
                lines.append(f"- {marker} **`{slug}`** — {n} practice Q{'s' if n != 1 else ''} ({cls.lower()}). {'Needs initial content.' if cls == 'EMPTY' else 'Author 3–5 more to reach healthy threshold.'}")
            lines.append("")
        else:
            lines.append("### Coverage gaps in this track")
            lines.append("")
            lines.append("None — every pattern in the proposed canonical set has healthy or uneven (≥5 Qs) coverage.")
            lines.append("")

    # Sidecar: per-question routing proposal
    lines.append("---")
    lines.append("## Per-question routing proposal (sidecar)")
    lines.append("")
    lines.append("Each practice question's proposed `pattern` value, derived from the routing tables.")
    lines.append("**Not yet committed to question JSONs.** Apply via a follow-up authoring pass per the")
    lines.append("learning-paths tracker §B.")
    lines.append("")
    for track, data in audits.items():
        lines.append(f"### {track}")
        lines.append("")
        lines.append("| QID | Difficulty | Pattern | Title |")
        lines.append("|---|---|---|---|")
        for qid, diff, title, pattern, reason, concepts in sorted(data["per_question"]):
            pat_repr = f"`{pattern}`" if pattern else "_unrouted_"
            t = title.replace("|", "\\|")
            lines.append(f"| {qid} | {diff} | {pat_repr} | {t} |")
        lines.append("")

    return "\n".join(lines)


def main():
    audits = {}
    for track, content_dir in TRACK_DIRS.items():
        per_q, buckets, family_landings = walk_track(track, content_dir)
        audits[track] = {
            "per_question": per_q,
            "buckets": buckets,
            "family_landings": family_landings,
        }
    md = render_markdown(audits)
    out = REPO / "docs" / "phases" / "pattern-coverage-audit.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"Wrote {out}")
    # Summary
    print()
    print("Headline:")
    for track, data in audits.items():
        pats = PROPOSED_PATTERNS.get(track, {})
        buckets = data["buckets"]
        healthy = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "HEALTHY")
        uneven = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "UNEVEN")
        thin = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "THIN")
        empty = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "EMPTY")
        unrouted = len(buckets.get(None, []))
        print(f"  {track:>18}: {len(pats)} patterns | healthy={healthy} uneven={uneven} thin={thin} empty={empty} | unrouted={unrouted}")


if __name__ == "__main__":
    main()
