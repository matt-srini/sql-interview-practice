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
        "EXECUTION MODEL REASONING": "spark-execution-model-and-dag",
        # Post 2026-XX spark-core-concepts split — route to new sub-patterns
        "NARROW VS WIDE TRANSFORMATIONS": "spark-execution-model-and-dag",
        "SCHEMA & TYPE HANDLING": "spark-schema-and-type-handling",
        "COLLECTION & ARRAY OPERATIONS": "spark-collections-and-arrays",
        "JOIN STRATEGY SELECTION": "spark-joins-and-skew",
        "DATA SKEW & MITIGATION": "spark-joins-and-skew",
        "PARTITIONING STRATEGY": "spark-performance",
        "SHUFFLE REASONING": "spark-performance",
        "PERFORMANCE TUNING & TRADE-OFFS": "spark-performance",
        "MEMORY MANAGEMENT": "spark-memory-and-driver-executor",
        "CACHING & PERSISTENCE": "spark-performance",
        "CATALYST OPTIMIZER": "query-optimization",
        "ADAPTIVE QUERY EXECUTION": "query-optimization",
        "STRUCTURED STREAMING": "streaming",
        "DELTA LAKE OPERATIONS": "delta-lake",
        "WINDOW FUNCTIONS & FRAMES": "pyspark-windowing",
        "FAULT TOLERANCE & RECOVERY": "spark-fault-tolerance-and-recovery",
        "FILE FORMATS & READERS": "spark-io-and-file-formats",
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
# Per-track analytical priority ordering.
#
# When a question's tags span multiple analytical patterns (analytical-vs-
# analytical tie), use this ordering to break the tie deterministically.
# Higher priority (earlier in list) wins.
#
# Rationale per track:
#   sql: cohort framing dominates funnel/sessionization when both are tagged
#        (the cohort lens is the analytical framing; sessionization is the
#        primitive). Top-N is its own narrow pattern. PoP and pivot are
#        independent of cohort/funnel and lose only if a cohort/funnel tag
#        also exists.
# ---------------------------------------------------------------------------
ANALYTICAL_PRIORITY: dict[str, list[str]] = {
    "sql": [
        "cohort-and-retention",          # dominates funnel/sessionization
        "funnel-and-event-analysis",
        "period-over-period",             # 2026-XX: PoP wins over top-n
        "top-n-and-ranking",
        "pivot-and-unpivot",
    ],
    # 2026-XX: ML analytical priority derived from divergent audit B3 findings.
    # production-and-monitoring dominates missing-data/feature-engineering when
    # the question's framing is a production scenario (drift, SMOTE-in-prod, etc.).
    "ml-fundamentals": [
        "production-and-monitoring",
        "missing-data-and-preprocessing",
        "class-imbalance",
        "feature-engineering",
        "algorithmic-fairness",
        "model-interpretability",
    ],
    # 2026-XX: Experimentation priority — causal/HTE methodology wins over
    # platform/behavioral cross-tags.
    "experimentation": [
        "causal-inference",
        "subgroup-and-hte",
        "variance-reduction",
        "behavioral-effects-and-interference",
        "experiment-platform-design",
        "sequential-and-bandits",
    ],
}


# ---------------------------------------------------------------------------
# Walk
# ---------------------------------------------------------------------------
def route_question(track: str, q: dict) -> tuple[str | None, str]:
    """Return (pattern_slug or None, reason) for one practice question.

    Reason explains the routing decision in one short phrase, for the audit log.

    Routing rules (in order):
      1. No tag routes to a pattern → None.
      2. Multiple analytical patterns match → ANALYTICAL_PRIORITY breaks the tie
         per track (when defined); otherwise first analytical match wins.
      3. No analytical match → first construct match wins.
    """
    routes = ROUTING.get(track, {})
    analytical = ANALYTICAL_PATTERNS.get(track, set())
    priority = ANALYTICAL_PRIORITY.get(track, [])
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

    # Analytical wins; resolve analytical-vs-analytical ties via priority.
    analytical_cands = [c for c in candidates if c[2] in analytical]
    if analytical_cands:
        if priority:
            analytical_cands.sort(
                key=lambda c: priority.index(c[2]) if c[2] in priority else len(priority)
            )
        winner = analytical_cands[0]
        if len(analytical_cands) > 1 and priority:
            return winner[2], (
                f"analytical-wins via family {winner[1]!r} "
                f"(priority over {sorted({c[2] for c in analytical_cands[1:]})})"
            )
        return winner[2], f"analytical-wins via family {winner[1]!r}"

    # Otherwise first construct match
    first = candidates[0]
    return first[2], f"first construct-family match: {first[1]!r}"


# ---------------------------------------------------------------------------
# Live-path → proposed-pattern slug normalisation.
#
# Live path JSON files declare patterns[] using slugs that may not match the
# proposed canonical set in PROPOSED_PATTERNS. This map normalises a live
# slug → the canonical slug so audit coverage aggregates correctly.
#
# When a slug is unchanged across live and proposed, no entry is needed.
# ---------------------------------------------------------------------------
NORMALIZE_PATTERN: dict[str, dict[str, str]] = {
    "sql": {
        "cohort-analysis": "cohort-and-retention",
        "funnel-analysis": "funnel-and-event-analysis",
        "recursive-ctes": "ctes-and-recursion",
        "string-functions": "string-and-text",
        "date-functions": "date-and-time",
    },
    "python": {
        "data-pipelines": "data-pipeline-scripting",
    },
    "python-data": {
        "joins": "joins-and-merges",
        "time-series": "time-series-pandas",
    },
    "data-engineering": {
        "data-lineage": "lineage-and-observability",
        "pipeline-observability": "lineage-and-observability",
    },
    "ml-fundamentals": {
        "monitoring": "production-and-monitoring",
        "missing-data": "missing-data-and-preprocessing",
    },
    "experimentation": {
        "ab-test-basics": "ab-test-mechanics",
        "power-analysis": "power-and-sample-size",
        "subgroup-analysis": "subgroup-and-hte",
    },
    "statistics": {
        "regression": "regression-and-correlation",
    },
}


def _normalize(track: str, slug: str) -> str:
    return NORMALIZE_PATTERN.get(track, {}).get(slug, slug)


def _load_live_paths_by_track() -> dict[str, list[dict]]:
    """Return {track: [live path dicts]} from backend/content/paths/."""
    out: dict[str, list[dict]] = defaultdict(list)
    for f in sorted((REPO / "backend" / "content" / "paths").glob("*.json")):
        d = json.loads(f.read_text())
        out[d["topic"]].append(d)
    return out


def walk_track(track: str, content_dir: Path, live_paths: list[dict] | None = None):
    """Walk practice questions for one track using **live paths as authoritative**.

    Returns:
      per_question: list of dicts per practice question with:
        qid, difficulty, title, concepts,
        live_path: slug of the live path containing this Q (or None if orphan),
        attributed_pattern: normalised canonical pattern slug (live path drives this, or None),
        tag_pattern: pattern suggested by tag-routing (used for divergence + orphan suggestion),
        divergent: bool — true when live_path attributes to A but tag-routing says B
      pattern_buckets: {canonical_pattern_slug: [(qid, diff, title)]} aggregated from live paths
      family_landings: {family: Counter(pattern→count)} for the cross-map view
      orphan_list: [per_question dicts where live_path is None]
      divergence_list: [per_question dicts where divergent=True]
    """
    if live_paths is None:
        live_paths = []

    # Build live-membership: qid → (path_slug, normalised_canonical_pattern)
    live_membership: dict[int, tuple[str, str]] = {}
    for p in live_paths:
        path_slug = p["slug"]
        path_patterns = p.get("patterns", []) or []
        normalised_path_patterns = [_normalize(track, s) for s in path_patterns]
        for qid in p.get("questions", []) or []:
            # If the path has one pattern, attribute there.
            # If multiple, pick the one whose pattern matches the question's tag-derived routing
            # (so multi-pattern paths split intelligently when 1:1 lands).
            chosen = normalised_path_patterns[0] if normalised_path_patterns else None
            live_membership[int(qid)] = (path_slug, chosen)

    per_question = []
    pattern_buckets: dict[str | None, list[tuple[int, str, str]]] = defaultdict(list)
    family_landings: dict[str, Counter] = defaultdict(Counter)
    orphan_list = []
    divergence_list = []

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

            tag_pattern, tag_reason = route_question(track, q)

            # If this question is in a multi-pattern live path, refine attribution:
            # prefer the pattern in the path's patterns[] that matches the tag-derived pattern.
            mem = live_membership.get(qid)
            if mem is not None:
                live_path_slug, default_attr = mem
                # Find the path again to access its patterns[] for multi-pattern refinement
                this_path = next((p for p in live_paths if p["slug"] == live_path_slug), None)
                normalised_options = [
                    _normalize(track, s) for s in (this_path.get("patterns", []) if this_path else [])
                ]
                if tag_pattern and tag_pattern in normalised_options:
                    attributed_pattern = tag_pattern
                else:
                    attributed_pattern = default_attr
                divergent = (tag_pattern is not None) and (tag_pattern != attributed_pattern)
            else:
                live_path_slug = None
                attributed_pattern = None
                divergent = False

            per_question_record = {
                "qid": qid,
                "difficulty": difficulty,
                "title": title,
                "concepts": concepts,
                "live_path": live_path_slug,
                "attributed_pattern": attributed_pattern,
                "tag_pattern": tag_pattern,
                "tag_reason": tag_reason,
                "divergent": divergent,
            }
            per_question.append(per_question_record)

            # Pattern bucket aggregation (from live-path attribution)
            if attributed_pattern is not None:
                pattern_buckets[attributed_pattern].append((qid, difficulty, title))

            # Orphan / divergence lists
            if live_path_slug is None:
                orphan_list.append(per_question_record)
            elif divergent:
                divergence_list.append(per_question_record)

            # Family-landing cross-map: where did each family's questions land
            for c in concepts:
                if isinstance(c, str):
                    family = resolve_to_family(c, track)
                    family_landings[family][attributed_pattern or "(orphan)"] += 1

    return per_question, pattern_buckets, family_landings, orphan_list, divergence_list


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
    lines.append("**Authoritative source for pattern membership: live path JSON files** in")
    lines.append("`backend/content/paths/*.json`. The script aggregates each live path's `questions[]`")
    lines.append("under the path's `patterns[]` (normalised to the canonical set via `NORMALIZE_PATTERN`).")
    lines.append("")
    lines.append("Tag-derived routing (the per-track concept-family → pattern tables in this script)")
    lines.append("is used for two secondary purposes:")
    lines.append("")
    lines.append("- **Orphan suggestion** — for catalog questions not in any live path, the audit")
    lines.append("  suggests which pattern they could join based on their tags.")
    lines.append("- **Divergence detection** — for questions in a live path whose tags suggest a")
    lines.append("  different pattern, the audit flags the divergence for author review.")
    lines.append("")
    lines.append("Headline coverage tables reflect the **live state of paths**, not tag-derived hypotheticals.")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append("| Track | Practice Qs | In a live path | Orphans | Divergent | Patterns (proposed) | Healthy | Uneven | Thin | Empty |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for track, data in audits.items():
        pats = PROPOSED_PATTERNS.get(track, {})
        buckets = data["buckets"]
        per_q = data["per_question"]
        n_in_path = sum(1 for r in per_q if r["live_path"] is not None)
        n_orphan = len(data["orphans"])
        n_div = len(data["divergences"])
        healthy = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "HEALTHY")
        uneven = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "UNEVEN")
        thin = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "THIN")
        empty = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "EMPTY")
        total = len(per_q)
        lines.append(
            f"| {track} | {total} | {n_in_path} | {n_orphan} | {n_div} | "
            f"{len(pats)} | {healthy} | {uneven} | {thin} | {empty} |"
        )
    lines.append("")
    lines.append("**Legend:**  ")
    lines.append("`In a live path` = practice questions currently included in some live path's `questions[]`.  ")
    lines.append("`Orphans` = practice questions in no live path (catalog-only).  ")
    lines.append("`Divergent` = questions in a live path whose tag-derived routing suggests a different pattern.  ")
    lines.append("Pattern classes are based on live-path-aggregated coverage: **Healthy** ≥5 across easy/medium/hard · **Uneven** ≥5 but missing a difficulty · **Thin** 1–4 Qs · **Empty** 0 Qs (proposed but no live path or no questions).  ")
    lines.append("")

    # Per-track sections
    for track, data in audits.items():
        pats = PROPOSED_PATTERNS.get(track, {})
        buckets = data["buckets"]
        per_q = data["per_question"]
        family_landings = data["family_landings"]
        orphans = data["orphans"]
        divergences = data["divergences"]

        lines.append("---")
        lines.append(f"## {track}")
        lines.append("")
        n_in_path = sum(1 for r in per_q if r["live_path"] is not None)
        lines.append(
            f"Practice questions: **{len(per_q)}** "
            f"({n_in_path} in live paths · {len(orphans)} orphans · {len(divergences)} divergent). "
            f"Proposed canonical patterns: **{len(pats)}**."
        )
        lines.append("")

        # Pattern coverage (live-aggregated)
        lines.append("### Pattern coverage (live-path-aggregated)")
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
                "EMPTY": "🔴 empty (no live path or no questions)",
            }[cls]
            lines.append(f"| `{slug}` | {label} | {ne} | {nm} | {nh} | {ne+nm+nh} | {cls_badge} |")
        lines.append("")

        # Concept-family → pattern landings cross-map
        lines.append("### Concept-family → pattern landings")
        lines.append("")
        lines.append("Where each track family's questions actually landed (per live-path attribution).")
        lines.append("A question contributes once per family tag — multi-tag questions count multiply.")
        lines.append("`(orphan)` = the family's questions that are not in any live path.")
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

        # Divergences within live paths
        if divergences:
            lines.append("### Divergences (live path says A, tags suggest B)")
            lines.append("")
            lines.append("Questions currently in a live path whose tag-derived routing would put them elsewhere.")
            lines.append("Each is a candidate for author review — the divergence is honest if the question's")
            lines.append("primary objective genuinely differs from its tag-primary primitive.")
            lines.append("")
            lines.append("| QID | Diff | Live path | Attributed pattern | Tag-suggested pattern | Title |")
            lines.append("|---|---|---|---|---|---|")
            for r in sorted(divergences, key=lambda x: (x["live_path"] or "", x["qid"])):
                t = r["title"].replace("|", "\\|")
                lines.append(
                    f"| {r['qid']} | {r['difficulty']} | `{r['live_path']}` | "
                    f"`{r['attributed_pattern']}` | `{r['tag_pattern']}` | {t} |"
                )
            lines.append("")
        else:
            lines.append("### Divergences (live path says A, tags suggest B)")
            lines.append("")
            lines.append("None.")
            lines.append("")

        # Orphans (questions not in any live path) with suggested pattern
        if orphans:
            lines.append("### Orphans (catalog questions in no live path)")
            lines.append("")
            lines.append("Practice questions whose IDs are not referenced by any live path's `questions[]`.")
            lines.append("The tag-suggested pattern is where they would land under tag-derived routing —")
            lines.append("a starting point for deciding which path (existing or new) should include them.")
            lines.append("")
            lines.append("| QID | Diff | Tag-suggested pattern | Title |")
            lines.append("|---|---|---|---|")
            for r in sorted(orphans, key=lambda x: (x["difficulty"], x["qid"])):
                t = r["title"].replace("|", "\\|")
                tp = f"`{r['tag_pattern']}`" if r["tag_pattern"] else "_unrouted_"
                lines.append(f"| {r['qid']} | {r['difficulty']} | {tp} | {t} |")
            lines.append("")
        else:
            lines.append("### Orphans (catalog questions in no live path)")
            lines.append("")
            lines.append("None — every practice question is in some live path.")
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
                if cls == "EMPTY":
                    detail = "No live path or no questions. Either create a path that aggregates this pattern, or author initial content."
                else:
                    detail = "Author or recruit 3–5 more to reach healthy threshold."
                lines.append(f"- {marker} **`{slug}`** — {n} practice Q{'s' if n != 1 else ''} ({cls.lower()}). {detail}")
            lines.append("")
        else:
            lines.append("### Coverage gaps in this track")
            lines.append("")
            lines.append("None — every pattern in the proposed canonical set is healthy or uneven (≥5 Qs).")
            lines.append("")

    # Sidecar: per-question full table (annotated)
    lines.append("---")
    lines.append("## Per-question table (sidecar)")
    lines.append("")
    lines.append("Every practice question with its live-path attribution and tag-derived suggestion.")
    lines.append("`Live path` = the path's `slug` that owns this question. `Attributed` = canonical pattern")
    lines.append("the audit credits the question to. `Tag-suggested` = where tag-routing would place it")
    lines.append("(used for divergence + orphan analysis). `Divergent?` = ✗ when live and tag disagree.")
    lines.append("")
    for track, data in audits.items():
        lines.append(f"### {track}")
        lines.append("")
        lines.append("| QID | Diff | Live path | Attributed | Tag-suggested | Divergent? | Title |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(data["per_question"], key=lambda x: x["qid"]):
            t = r["title"].replace("|", "\\|")
            live = f"`{r['live_path']}`" if r["live_path"] else "_orphan_"
            attr = f"`{r['attributed_pattern']}`" if r["attributed_pattern"] else "—"
            tag = f"`{r['tag_pattern']}`" if r["tag_pattern"] else "_unrouted_"
            div = "⚠️" if r["divergent"] else ""
            lines.append(f"| {r['qid']} | {r['difficulty']} | {live} | {attr} | {tag} | {div} | {t} |")
        lines.append("")

    return "\n".join(lines)


def main():
    live_paths_by_track = _load_live_paths_by_track()
    audits = {}
    for track, content_dir in TRACK_DIRS.items():
        per_q, buckets, family_landings, orphans, divergences = walk_track(
            track, content_dir, live_paths=live_paths_by_track.get(track, [])
        )
        audits[track] = {
            "per_question": per_q,
            "buckets": buckets,
            "family_landings": family_landings,
            "orphans": orphans,
            "divergences": divergences,
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
        per_q = data["per_question"]
        n_in_path = sum(1 for r in per_q if r["live_path"] is not None)
        n_orph = len(data["orphans"])
        n_div = len(data["divergences"])
        healthy = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "HEALTHY")
        uneven = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "UNEVEN")
        thin = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "THIN")
        empty = sum(1 for p in pats if classify_pattern(buckets.get(p, [])) == "EMPTY")
        print(
            f"  {track:>18}: {len(per_q)}Q ({n_in_path} in path, {n_orph} orph, {n_div} div) | "
            f"{len(pats)} patterns | H={healthy} U={uneven} T={thin} E={empty}"
        )


if __name__ == "__main__":
    main()
