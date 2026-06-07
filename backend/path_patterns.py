"""
Per-track pattern registry for learning paths.

Patterns are *practitioner-skill* labels: subject-matter areas a user picks up by
working through a learning path (e.g. "window-functions", "scd", "causal-inference").

This is deliberately distinct from concept families in ``concept_families.py``,
which describe *reasoning families* used for dashboard weak-spot detection and
mock focus filtering.  The two axes serve different surfaces:

  - ``focus_concepts`` (on a path) → reasoning families the path strengthens.
    Used by the dashboard insights router to recommend paths for weak concepts.

  - ``patterns`` (on a path) → practitioner subject-matter the path masters.
    Used by the path UI ("what you'll learn"), search, and the future
    Practice → Path → Mock loop.

A path always declares at least one pattern from the per-track registry below.
Multiple paths may declare the same pattern at different depths (e.g. ``scd``
appears in both Schema Design Basics and Dimensional Modeling Deep Dive).

The validator (``backend/scripts/validate_content.py::_validate_paths``)
enforces every ``patterns[]`` entry resolves to an entry in this registry for
the path's track.

See ``docs/content-authoring.md`` §Paths for the canonical definition.
"""

from __future__ import annotations

# Map: track slug → {pattern slug → human-readable display label}
PATH_PATTERNS: dict[str, dict[str, str]] = {
    "sql": {
        "aggregation": "Aggregation",
        "joins": "Joins",
        "window-functions": "Window Functions",
        "subqueries": "Subqueries & EXISTS",
        "set-operations": "Set Operations (UNION / INTERSECT / EXCEPT)",
        "recursive-ctes": "Recursive CTEs",
        "grouping-extensions": "ROLLUP / CUBE / GROUPING SETS",
        "string-functions": "String Functions",
        "date-functions": "Date Functions",
        "cohort-analysis": "Cohort & Retention Analysis",
        "funnel-analysis": "Funnel & Event Analysis",
        "period-over-period": "Period-over-Period Analysis",
        "pivot-and-unpivot": "Pivot & Conditional Aggregation",
    },
    "python": {
        "arrays-and-hashing": "Arrays & Hashing",
        "sliding-window": "Sliding Window & Two Pointers",
        "stacks-and-queues": "Stacks & Queues",
        "dynamic-programming": "Dynamic Programming",
        "graph-traversal": "Graph & Tree Traversal",
        "data-pipelines": "Data Pipeline Scripting",
        "string-and-text-processing": "String & Text Processing",
        "heap-and-priority": "Heaps & Priority Queues",
    },
    "python-data": {
        "dataframe-basics": "DataFrame Basics",
        "groupby": "GroupBy Aggregation",
        "joins": "DataFrame Joins",
        "reshape-and-pivot": "Reshape & Pivot",
        "time-series": "Time Series",
        "customer-analytics": "Customer Analytics Pipelines",
        "data-cleaning": "Data Cleaning",
        "top-n-and-ranking": "Top-N & Ranking",
    },
    "pyspark": {
        "spark-performance": "Spark Performance",
        "query-optimization": "Catalyst & Query Optimization",
        "streaming": "Structured Streaming",
        "delta-lake": "Delta Lake",
        "spark-joins-and-skew": "Spark Joins & Skew Handling",
        "pyspark-windowing": "Window Functions & Frames",
        "spark-execution-model-and-dag": "Spark Execution Model & DAG",
        "spark-schema-and-type-handling": "Spark Schema & Type Handling",
        "spark-memory-and-driver-executor": "Spark Memory & Driver/Executor Architecture",
        "spark-io-and-file-formats": "Spark I/O & File Formats",
        "spark-fault-tolerance-and-recovery": "Spark Fault Tolerance & Recovery",
        "spark-collections-and-arrays": "Spark Collections & Arrays",
    },
    "data-engineering": {
        "etl-elt": "ETL / ELT Design",
        "orchestration": "Pipeline Orchestration",
        "schema-evolution": "Schema Evolution",
        "delivery-semantics": "Delivery Semantics",
        "backfill-design": "Backfill Design",
        "data-lineage": "Data Lineage",
        "pipeline-observability": "Pipeline Observability",
        "data-quality-and-incident-response": "Data Quality & Incident Response",
        "cost-and-format-optimization": "Cost & Format Optimization",
        "streaming-vs-batch": "Streaming vs Batch Architecture",
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
        "data-vault": "Data Vault Modeling",
        "aggregate-and-summary-design": "Aggregate & Summary Design",
    },
    "statistics": {
        "descriptive-stats": "Descriptive Statistics",
        "distributions": "Probability Distributions",
        "hypothesis-testing": "Hypothesis Testing",
        "confidence-intervals": "Confidence Intervals",
        "regression": "Regression Analysis",
        "probability-and-combinatorics": "Probability & Combinatorics",
        "bayesian-reasoning": "Bayesian Reasoning",
        "errors-and-power": "Errors, Power & Multiple Testing",
        "sampling-and-clt": "Sampling & CLT",
    },
    "ml-fundamentals": {
        "supervised-unsupervised": "Supervised vs Unsupervised Framing",
        "bias-variance": "Bias-Variance & Overfitting",
        "cross-validation": "Cross-Validation",
        "metrics": "Model Metrics",
        "regularization": "Regularization",
        "ensembles": "Ensemble Methods",
        "monitoring": "Model Monitoring & Drift",
        "missing-data": "Missing Data & Imputation",
        "feature-engineering": "Feature Engineering",
        "class-imbalance": "Class Imbalance Handling",
        "hyperparameter-tuning": "Hyperparameter Tuning",
        "neural-networks-and-gradients": "Neural Networks & Gradient Behaviour",
        "unsupervised-methods": "Unsupervised Methods",
    },
    "experimentation": {
        "ab-test-basics": "A/B Test Mechanics",
        "metric-selection": "Metric Selection",
        "power-analysis": "Power & Sample Size",
        "variance-reduction": "Variance Reduction (CUPED)",
        "causal-inference": "Causal Inference",
        "subgroup-analysis": "Subgroup Analysis & HTE",
        "behavioral-effects-and-interference": "Behavioral Effects & Interference",
    },
}


def get_track_patterns(track: str) -> dict[str, str]:
    """Return the pattern slug→label registry for a track, or empty dict if unknown."""
    return PATH_PATTERNS.get(track, {})


def is_valid_pattern(track: str, pattern: str) -> bool:
    """True if ``pattern`` is a registered pattern slug for ``track``."""
    return pattern in PATH_PATTERNS.get(track, {})
