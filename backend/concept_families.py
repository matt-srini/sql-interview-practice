"""
Concept family definitions shared by mock question selection and dashboard insights.

CONCEPT_FAMILIES maps each track to a dict of {family_name: [keyword_fragments]}.
A raw question concept tag belongs to a family when any of its keywords appears
as a case-insensitive substring of the tag.

Used in two places:
  - routers/mock.py  : focus-mode question pool filtering
  - routers/insights.py : weakest-concept and readiness-score accumulation
"""

from __future__ import annotations

CONCEPT_FAMILIES: dict[str, dict[str, list[str]]] = {
    "sql": {
        # WINDOW FUNCTIONS must come before AGGREGATION so that tags like
        # "POST-AGGREGATION WINDOWING" resolve to the window family (more specific).
        "WINDOW FUNCTIONS": [
            "WINDOW",               # WINDOW RANK, WINDOW RUNNING TOTAL, etc.
            "WINDOWING",            # POST-AGGREGATION WINDOWING, CROSS-GRAIN WINDOWING
            "RUNNING TOTAL",        # RUNNING TOTAL, WINDOW RUNNING TOTAL
            "CUMULATIVE",
            "ROWS VS RANGE",
            "LAG WINDOW",
        ],
        "AGGREGATION": [
            "AGGREG",               # …AGGREGATION, GROUPED AGGREGATION, etc.
            "ORDERED-SET AGGR",
        ],
        "JOINS": [
            "JOIN",                 # LEFT JOIN, ANTI-JOIN, DATE-RANGE JOIN, etc.
        ],
        "SUBQUERY PATTERNS": [
            "SUBQUERY",             # SUBQUERY FILTER, SCALAR SUBQUERY IN CASE
            "CORRELATED",
            "NESTED FILTER",        # NESTED FILTER LOGIC (subquery-equivalent patterns)
        ],
        "CTES": [
            "CTE",                  # CTE PIPELINE, CTE REUSE, MULTI-CTE, etc.
        ],
        "DATE FUNCTIONS": [
            "DATE",                 # DATE EXTRACTION, DATE COMPARISON, etc.
            "TIME-",                # TIME-SERIES, TIME-WINDOW, TIME-SLICE, etc.
            "STRFTIME",
            "TEMPORAL",
            "MONTHLY",
            "QUARTER",
            "PERIOD-OVER-PERIOD",
        ],
        "GROUP BY": [
            "GROUP BY",             # GROUP BY RULES, MULTI-COLUMN GROUP BY
            "GROUPED ",             # GROUPED AGGREGATION (trailing space avoids false matches)
            "HAVING",               # HAVING ON COUNT, HAVING THRESHOLD, HAVING VS WHERE
            "MULTI-AGGREGATE",
        ],
        "FILTERING": [
            "FILTER",               # CONDITIONAL FILTERING, PRE-AGGREGATION FILTER, etc.
            "WHERE CLAUSE",
            "IN CLAUSE",
            "RANGE FILTER",
        ],
        "COHORT RETENTION": [
            "COHORT",               # COHORT ANALYSIS, MULTI-DIMENSION COHORT
            "RETENTION",            # RETENTION BY MONTH OFFSET
            "REACTIVATION",
        ],
        "FUNNEL ANALYSIS": [
            "FUNNEL",               # CONVERSION FUNNEL, ACQUISITION FUNNEL, etc.
        ],
        "RANKING": [
            "RANK",                 # WINDOW RANK, PARTITIONED RANK, MANUAL TOP-N RANKING
            "TOP-N",                # TOP-N PER GROUP, TOP-N QUERY
        ],
        "SELF JOIN": [
            "SELF-COMPAR",          # ROW-LEVEL SELF-COMPARISON, SELF-COMPARISON RANK EMULATION
            "ROW-LEVEL SELF",
            "ROW-TO-ROW",
        ],
        "SET OPERATIONS": [
            "SET MEMBER",           # SET MEMBERSHIP FILTERING / TEST
            "SET DIFFER",           # BEHAVIORAL SET DIFFERENCE
            "ANTI-JOIN",            # ANTI-JOIN PATTERN
            "CROSS-SOURCE",
        ],
        "CASE WHEN": [
            "CASE WHEN",            # CASE WHEN LADDER
            "RULE-BASED",           # RULE-BASED CLASSIFICATION
            "CONDITIONAL FLAG",
            "CATEGORICAL SEGM",
            "PRIORITY-BASED",
        ],
        "STRING FUNCTIONS": [
            "PATTERN-BASED",        # PATTERN-BASED FILTERING
            "STRFTIME",
            "STRING",
        ],
    },
    "python": {
        "SORTING": [
            "SORT",                 # IN-PLACE SORT, ORDER-PRESERVING
            "K-WAY MERGE",
        ],
        "BINARY SEARCH": [
            "BINARY SEARCH",        # BINARY SEARCH, BINARY SEARCH TREE
            "PEAK FINDING",
        ],
        "HASH MAPS": [
            "HASH MAP",             # HASH MAP, HASH MAP COUNTING, HASH MAP GROUPING
            "HASH SET",
            "HASH-BASED",
            "FREQUENCY COUNT",      # FREQUENCY COUNTING, FREQUENCY TRACKING
            "FREQUENCY-BASED",
            "COUNTER",
        ],
        "TWO POINTERS": [
            "TWO POINTER",          # TWO POINTERS, TWO-POINTER SWEEP
            "TWO-POINTER",
            "BOUNDARY POINTER",
        ],
        "SLIDING WINDOW": [
            "SLIDING WINDOW",       # SLIDING WINDOW MAXIMUM
            "FIXED WINDOW",
            "MINIMUM WINDOW",
        ],
        "RECURSION": [
            "RECURSION",            # BASE CASE HANDLING
            "RECURSIVE",
            "BACKTRACKING",
            "FIBONACCI",
        ],
        "DYNAMIC PROGRAMMING": [
            "DYNAMIC PROGRAMMING",
            "BOTTOM-UP DP",
            "DP TABLE",
            "MEMOIZATION",
            "GRID DP",
            "COIN CHANGE",
            "KADANE",
        ],
        "GRAPHS": [
            "GRAPH",                # DIRECTED GRAPH, GRAPH CONNECTIVITY
            "BFS",
            "DFS",
            "SHORTEST PATH",
            "TOPOLOGICAL",
            "DISJOINT-SET",
            "WEIGHTED GRAPH",
        ],
        "TREES": [
            "TREE",                 # BINARY SEARCH TREE, TREE CENTER, LEAF TRIMMING
            "TRIE",
            "PREORDER",
        ],
        "LINKED LISTS": [
            "LINKED LIST",          # DOUBLY LINKED LIST
        ],
        "HEAPS": [
            "HEAP",                 # MIN-HEAP, TWO HEAPS
            "PRIORITY QUEUE",
            "K-WAY MERGE",
            "MEDIAN TRACKING",
        ],
        "STACK / QUEUE": [
            "STACK",                # MONOTONIC STACK
            "QUEUE",                # MONOTONIC QUEUE
            "MONOTONIC",
        ],
        "BIT MANIPULATION": [
            "BIT MANIPULATION",
            "XOR",
            "POWER-OF-TWO",
        ],
    },
    "python-data": {
        "GROUPBY": [
            "GROUPBY",              # GROUPBY AGG, MULTI-KEY GROUPBY, etc.
            "GROUP BY",
        ],
        "MERGING": [
            "MERGE",                # MERGE KEY, MULTI-DATAFRAME JOIN
            "JOIN",                 # INNER JOIN, LEFT JOIN, THREE-WAY JOIN
            "CONCAT",               # DATAFRAME CONCATENATION
        ],
        "PIVOTING": [
            "PIVOT",                # DATA PIVOTING
            "CROSSTAB",
            "CONTINGENCY",          # CONTINGENCY TABLE CONSTRUCTION
            "WIDE-FORM",
        ],
        "FILTERING": [
            "FILTER",               # BOOLEAN FILTER, FILTERING AGGREGATED RESULTS
            "BOOLEAN MASK",
            "BOOLEAN INDEXING",
            "QUERY FILTER",
            "NULL-BASED ROW FILTER",
        ],
        "AGGREGATION": [
            "AGGREGATION",          # GROUPBY AGGREGATION, CONDITIONAL AGGREGATION, etc.
            " AGG",                 # NAMED AGG, LAMBDA IN AGG (leading space avoids partial matches)
            "AGGREG",
        ],
        "WINDOW FUNCTIONS": [
            "WINDOW",               # WINDOW FUNCTIONS, WINDOW JOIN, WINDOW-LIKE, etc.
            "ROLLING",              # ROLLING WINDOW, MOVING AVERAGE
            "CUMSUM",
            "RUNNING TOTAL",
        ],
        "RESHAPING": [
            "RESHAPE",
            "UNSTACK",
            "STACK ",               # trailing space avoids matching MULTI-STEP
            "WIDE-FORM",
        ],
        "TIME SERIES": [
            "TIME SERIES",
            "DATETIME",             # DATETIME ARITHMETIC, DATETIME COMPONENT EXTRACTION
            "PERIOD",               # PERIOD ARITHMETIC, PERIOD-OVER-PERIOD
            "TIMEDELTA",
            "DATE",                 # DATE ARITHMETIC, DATE COMPARISON, etc.
            "MONTHLY",
        ],
        "STRING METHODS": [
            "STRING",               # VECTORIZED STRING TRANSFORMATION, etc.
            "SUBSTRING",
            "DELIMITER",
        ],
        "APPLY/MAP": [
            "APPLY",                # APPLY FOR CLASSIFICATION, etc.
            "LAMBDA",               # LAMBDA AGGREGATION, LAMBDA IN AGG
            " MAP",                 # leading space avoids matching HASH MAP etc.
        ],
        "COHORT ANALYSIS": [
            "COHORT",               # COHORT ANALYSIS
            "RETENTION",            # RETENTION ANALYSIS
            "CHURN",
        ],
        "MULTI-INDEX": [
            "MULTIINDEX",
            "MULTI-INDEX",          # MULTI-INDEX CROSS-SECTION LOOKUP
            "HIERARCHICAL",         # HIERARCHICAL INDEXING
        ],
    },
    "pyspark": {
        "DATAFRAME API": [
            "DATAFRAME",            # DATAFRAME API, DATAFRAME IMMUTABILITY, etc.
            "COLUMN EXPRESSION",
            "WITHCOLUMN",
        ],
        "GROUPBY": [
            "GROUPBY",              # GROUPSTATETIMEOUT, GROUPBYKEY
            "GROUPED",
        ],
        "JOINS": [
            "JOIN",                 # BROADCAST JOIN, SKEW JOIN, JOIN STRATEGY, etc.
        ],
        "WINDOW FUNCTIONS": [
            "WINDOW FRAME",         # WINDOW FRAME SEMANTICS
            "WINDOW FUNCTION",      # WINDOW FUNCTIONS
            "ROWSBETWEEN",
            "ROWS VS RANGE",
            "RANK",                 # RANK, DENSE_RANK, ROW_NUMBER, TIE HANDLING
            "DENSE_RANK",
            "ROW_NUMBER",
        ],
        "UDFS": [
            "UDF",                  # UDF, UDF NULL HANDLING, PYTHON UDF OVERHEAD, PANDAS UDF
        ],
        "PARTITIONING": [
            "PARTITION",            # PARTITIONING, PARTITION PRUNING, PARTITION SIZING, etc.
            "COALESCE",             # SHUFFLE COALESCING / PARTITION COALESCING
        ],
        "AGGREGATION": [
            "AGGREGATION",          # DISTRIBUTED AGGREGATION, CUMULATIVE AGGREGATION, etc.
            "HASHAGGREGATE",
        ],
        "STREAMING": [
            "STREAMING",            # STRUCTURED STREAMING, STREAMING CHECKPOINT, etc.
            "STREAM-",              # STREAM-STREAM JOIN
            "MICRO-BATCH",
            "WATERMARK",
            "FOREACHBATCH",
            "STATEFUL AGGREG",      # STATEFUL AGGREGATION, STATEFUL AGGREGATION SCALING
            "MAPGROUPSWITHSTATE",
        ],
        "CACHING": [
            "CACHING",
            "CACHE",                # CHECKPOINT (avoided — too broad), CACHE specific
            "PERSIST",              # PERSIST, PERSISTENCE LIFECYCLE
            "STORAGE LEVEL",        # STORAGE LEVEL SELECTION
        ],
        "BROADCAST JOIN": [
            "BROADCAST",            # BROADCAST JOIN, BROADCAST VARIABLE, etc.
        ],
        "SHUFFLE & PERFORMANCE": [
            "SHUFFLE",              # shuffle, shuffle optimization, WIDE-AGGREGATION SHUFFLE, etc.
            "PERFORMANCE",          # performance, performance tuning, performance bottleneck
            "EXCHANGE",             # Exchange operator in explain plan
            "REDUCEBYKEY",
            "GROUPBYKEY",
        ],
        "CATALYST & QUERY PLANNING": [
            "CATALYST",             # Catalyst optimizer (8 questions)
            "LAZY EVAL",            # lazy evaluation (5 questions)
            "LAZY ",                # lazy evaluation catch with trailing space
            "PREDICATE PUSH",       # predicate pushdown (4 questions)
            "LOGICAL PLAN",
            "PHYSICAL PLAN",
            "QUERY PLAN",           # query planning, query plan optimization
            "EXPLAIN",              # explain, explain plan
            "TRANSFORMATIONS VS",   # transformations vs actions (3 questions)
            "NARROW VS WIDE",
            "NARROW TRANSFORMATION",
            "WIDE TRANSFORMATION",
        ],
        "MEMORY MANAGEMENT": [
            "MEMORY",               # driver memory, executor memory, memory management, memory pressure
            "OOM",                  # OutOfMemoryError, driver OOM
            "OFF-HEAP",
            "GC",                   # GC pressure, JVM GC
            "HEAP",
            "SPILL",                # spill to disk, DISK SPILL
            "SERIALIZATION",        # serialization cost, Kryo serialization
        ],
        "DATA SKEW": [
            "SKEW",                 # data skew (4), skew join (2), SKEW DIAGNOSIS
            "SALTING",              # salting (2), key salting (1)
            "HOT KEY",
            "IMBALANCE",            # partition imbalance, shuffle partition imbalance
        ],
        "DELTA LAKE": [
            "DELTA",                # Delta Lake (3), DELTA LAKE MERGE, DELTA LAKE WRITE, etc.
        ],
        "AQE": [
            "AQE",                  # AQE (4 questions)
            "ADAPTIVE QUERY",       # adaptive query execution (2 questions)
            "ADAPTIVE",             # Adaptive Query Execution
            "RUNTIME PLAN",         # runtime plan rewriting
            "RUNTIME JOIN",         # RUNTIME JOIN STRATEGY SWITCHING
        ],
    },
    "data-engineering": {
        "ETL VS ELT": [
            "ETL VS ELT",
            "EXTRACT",
            "TRANSFORM",
            "LOAD ORDER",
        ],
        "IDEMPOTENCY": [
            "IDEMPOTEN",          # IDEMPOTENCY, IDEMPOTENT WRITE, etc.
            "DUPLICATE PREVENTION",
            "SAFE RERUN",
        ],
        "BACKFILL DESIGN": [
            "BACKFILL",
            "HISTORICAL REPROCESS",
            "PARTITION RERUN",
        ],
        "ORCHESTRATION": [
            "ORCHESTRAT",         # ORCHESTRATION, ORCHESTRATION DESIGN, etc.
            "DAG",                # DAG EXECUTION, DAG DEPENDENCY
            "DEPENDENCY",
            "RETRY",
        ],
        "SCHEDULING & SLAS": [
            "SCHEDULING",
            "SLA",
            "SLO",
            "CRON-BASED",
            "EVENT-DRIVEN",
        ],
        "SCHEMA EVOLUTION": [
            "SCHEMA EVOLUTION",
            "BACKWARD COMPAT",
            "FORWARD COMPAT",
            "BREAKING CHANGE",
            "DATA CONTRACT",
        ],
        "BATCH VS STREAMING": [
            "BATCH VS STREAM",
            "MICRO-BATCH",
            "REAL-TIME",
            "LATENCY TRADEOFF",
            "STREAM PROCESSING",
        ],
        "WATERMARKING": [
            "WATERMARK",          # WATERMARKING, WATERMARK CHOICE, etc.
            "LATE DATA",
            "ALLOWED LATENESS",
            "EVENT TIME",
        ],
        "DELIVERY SEMANTICS": [
            "DELIVERY SEMANTIC",
            "EXACTLY-ONCE",
            "AT-LEAST-ONCE",
            "AT-MOST-ONCE",
            "DEDUP",
        ],
        "PARTITIONING & PRUNING": [
            "PARTITION",          # PARTITIONING, PARTITION PRUNING, etc.
            "PREDICATE PUSHDOWN",
            "DATA SKEW",
        ],
        "STORAGE LAYOUT & FILE FORMATS": [
            "STORAGE LAYOUT",
            "FILE FORMAT",
            "COLUMNAR",
            "PARQUET",
            "AVRO",
            "COMPACTION",
            "SMALL FILE",
        ],
        "CDC & INGESTION": [
            "CDC",                # CDC & INGESTION, LOG-BASED CDC
            "CHANGE CAPTURE",
            "INGESTION",
            "LOG-BASED",
        ],
        "DATA QUALITY": [
            "DATA QUALITY",
            "ASSERTION",
            "ANOMALY DETECTION",
            "FRESHNESS CHECK",
            "NULL CHECK",
        ],
        "LINEAGE & OBSERVABILITY": [
            "LINEAGE",
            "OBSERVABILITY",
            "FRESHNESS",
            "METADATA",
            "ALERTING",
        ],
        "SCD OPERATIONS": [
            "SCD",                # SCD TYPE 2, SCD OPERATIONS, etc.
            "SLOWLY CHANGING",
            "EFFECTIVE DATE",
            "SURROGATE KEY",
        ],
        "STORAGE ARCHITECTURE": [
            "STORAGE ARCHITECTURE",
            "DATA LAKE",
            "DATA WAREHOUSE",
            "LAKEHOUSE",
            "OLAP",
        ],
        "COST OPTIMIZATION": [
            "COST OPTIM",         # COST OPTIMIZATION, COST-AWARE
            "COMPUTE VS STORAGE",
            "SCAN COST",
            "STORAGE TIER",
        ],
        "INCIDENT RESPONSE": [
            "INCIDENT RESPONSE",
            "ROOT CAUSE",
            "REPLAY",
            "REMEDIATION",
            "CASCADING FAILURE",
        ],
    },
}


def resolve_to_family(concept: str, track: str) -> str:
    """Map a raw ALL-CAPS concept tag to its family name for the given track.

    Returns the family name (e.g. "WINDOW FUNCTIONS") if a keyword match is
    found, otherwise returns the concept unchanged.  Matching is
    case-insensitive so mixed-case tags in the wild are handled safely.
    """
    concept_upper = concept.upper()
    for family_name, keywords in CONCEPT_FAMILIES.get(track, {}).items():
        if any(kw.upper() in concept_upper for kw in keywords):
            return family_name
    return concept_upper  # normalise to upper even when no family found


def concept_matches_focus(question_concept: str, focus_concept: str, q_track: str) -> bool:
    """Check whether a question concept tag matches a user-selected focus concept.

    Uses CONCEPT_FAMILIES for family-aware keyword matching, falling back to
    bidirectional substring matching for concepts not in the table.
    """
    qc_upper = question_concept.upper()
    fc_upper = focus_concept.upper()
    keywords = CONCEPT_FAMILIES.get(q_track, {}).get(fc_upper)
    if keywords:
        return any(kw.upper() in qc_upper for kw in keywords)
    return fc_upper in qc_upper or qc_upper in fc_upper
