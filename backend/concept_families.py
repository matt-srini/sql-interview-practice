"""
Concept family definitions shared by mock question selection and dashboard insights.

This file is a faithful implementation of docs/concept-taxonomy.md.  Whenever the
taxonomy doc changes, update this file to match — the two must stay in sync.

CONCEPT_FAMILIES maps each track slug to a dict of {family_name: [match_patterns]}.

Resolution algorithm (mirrors the taxonomy doc):
  1. Exact match — tag appears verbatim in any family's match_patterns list.
  2. Substring match — tag contains any pattern (case-insensitive).  The FIRST
     family whose pattern matches wins (order within the dict is significant).
  3. Blocklist — tag matches any entry in CONCEPT_BLOCKLISTS[track] → error.
  4. No match → error; author must remap the tag.

MOCK_ONLY_REALISM_FAMILIES lists the SQL (and Pandas/PySpark) families that are
assessment lenses, not curriculum concepts.  Validated by validate_content.py:
  - May appear only in mock_only questions, never practice.
  - May never be a question's sole concept tag (must co-occur with ≥1 practice-
    grounded family).
  - Exempt from the practice-grounding prerequisite.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Mock-only realism families (assessment lenses, not curriculum concepts).
# Used by validate_content.py to enforce the co-tag rule.
# ---------------------------------------------------------------------------

MOCK_ONLY_REALISM_FAMILIES: dict[str, set[str]] = {
    "sql": {
        "METRIC INTERPRETATION & DENOMINATOR CHOICE",
        "OUTPUT SANITY VALIDATION",
        "PERFORMANCE-AWARE ANALYTICS",
    },
    "python-data": {
        "METRIC INTERPRETATION & DENOMINATOR CHOICE",
        "OUTPUT SANITY VALIDATION",
        "PERFORMANCE-AWARE ANALYTICS",
        "MEMORY & VECTORIZATION REASONING",
    },
    # PySpark: NO mock-only realism families. All 3 ⚡ families
    # (DATA QUALITY SKEPTICISM, DOUBLE-COUNTING DETECTION, OUTPUT SANITY VALIDATION)
    # are practice-grounded because PySpark is MCQ-only — sanity-check / validation
    # reasoning grades cleanly as predict_output or debug MCQ. The SQL rationale
    # for designating those families mock-only-realism (they don't grade as
    # query-writing) does not transfer. See docs/tracks/pyspark.md and the
    # PySpark Phase 2 decision log.
    "pyspark": set(),
    # Python: NO realism families by design. Python's families are pure
    # algorithmic patterns; the candidate "lens" (complexity & memory) is
    # practice-gradable via the harness (O(n²) times out / load-everything
    # OOMs on sized hidden inputs) and surfaces in mock as the
    # `performance_pivot` chain dimension, not a concept tag.
    # See docs/tracks/python.md and the Python Phase 2 decision log.
    "python": set(),
}

# ---------------------------------------------------------------------------
# Concept family registries, one dict per track.
# Within each track dict, ORDER MATTERS: the first family whose pattern appears
# as a case-insensitive substring of the concept tag wins.
#
# Naming convention: family names match docs/concept-taxonomy.md exactly.
# ---------------------------------------------------------------------------

CONCEPT_FAMILIES: dict[str, dict[str, list[str]]] = {

    # -----------------------------------------------------------------------
    # SQL — 26 canonical families (docs/concept-taxonomy.md § SQL)
    # -----------------------------------------------------------------------
    "sql": {
        # --- Running totals / moving windows (before WINDOW FUNCTIONS so
        #     "RUNNING TOTAL" tags don't fall through to the generic window family) ---
        "RUNNING TOTAL & MOVING WINDOW": [
            "RUNNING TOTAL",        # RUNNING TOTAL THRESHOLD DETECTION, RUNNING TOTAL
            "CUMULATIVE",           # CUMULATIVE CONTRIBUTION, CUMULATIVE SUM
            "MOVING AVERAGE",
            "MOVING WINDOW",
            "RUNNING SHARE",        # RUNNING SHARE THRESHOLD
            "THRESHOLD-CROSSING",   # FIRST THRESHOLD-CROSSING ROW, THRESHOLD-CROSSING INCLUSION
        ],

        # --- Ranking / top-N / deduplication (before WINDOW FUNCTIONS so
        #     RANK-containing tags resolve here, not to the generic family) ---
        "RANKING & TOP-N PER GROUP": [
            "PARTITIONED WINNER",   # PARTITIONED WINNER SELECTION
            "PARTITIONED RANK",     # PARTITIONED RANK FILTERING
            "TOP-N",                # TOP-N PER GROUP, TOP-N QUERY
            "TOP-K",                # (Pandas cross-track alignment)
            "LATEST STATE",         # LATEST STATE DERIVATION
            "DETERMINISTIC TIE",    # DETERMINISTIC TIE-BREAKING
            "MANUAL TOP-N",         # MANUAL TOP-N RANKING
            "LEADERBOARD",          # CHANNEL-LEVEL LEADERBOARD
            "QUALIFY",              # QUALIFY (DuckDB window filter clause)
            "LATEST-ROW DEDUP",     # LATEST-ROW DEDUPLICATION
            "PREFERENCE SHIFT",     # CATEGORY PREFERENCE SHIFT
            "RANK",                 # WINDOW RANK, PARTITIONED RANK, WINDOW RANK WITH PARTITION
                                    # — kept last within group so PARTITIONED RANK wins over RANK
        ],

        # --- Generic window functions (after RUNNING TOTAL and RANKING) ---
        "WINDOW FUNCTIONS": [
            "ROWS VS RANGE",        # ROWS vs RANGE FRAME SEMANTICS, WINDOW FRAME DIVERGENCE
            "ROWS VS RANGE FRAME",
            "LAG WINDOW",           # LAG WINDOW FUNCTION
            "LEAD",                 # LEAD window function
            "WINDOWING",            # POST-AGGREGATION WINDOWING, CROSS-GRAIN WINDOWING
            "WINDOW",               # catch-all: WINDOW RANK, GLOBAL WINDOW MAX, WINDOW FILTER
            "PROPORTIONAL CONTRIBUTION",  # PROPORTIONAL CONTRIBUTION ANALYSIS (revenue share via window)
            "PERSONAL BASELINE",    # PERSONAL BASELINE COMPARISON
            "PERCENTILE",           # PERCENTILE FUNCTION, PERCENTILE_CONT
            "FORWARD WINDOW",       # FORWARD WINDOW QUALIFICATION
            "PEAK PERIOD",          # PEAK PERIOD IDENTIFICATION
            "POST-PEAK",            # POST-PEAK DECLINE ANALYSIS
        ],

        # --- Cohort retention ---
        "COHORT RETENTION": [
            "COHORT",               # COHORT ANALYSIS, MULTI-DIMENSION COHORT
            "RETENTION",            # RETENTION BY MONTH OFFSET
            "REACTIVATION",         # REACTIVATION DETECTION
        ],

        # --- Funnel analysis ---
        "FUNNEL ANALYSIS": [
            "FUNNEL",               # CONVERSION FUNNEL, FUNNEL ORDER ENFORCEMENT, ACQUISITION FUNNEL
            "CONVERSION FUNNEL",
            "DROP-OFF",             # CHANNEL-LEVEL DROP-OFF
        ],

        # --- Sessionization / gap-and-island / state machines ---
        "SESSIONIZATION": [
            "SESSIONIZATION",       # exact
            "INACTIVITY GAP",       # INACTIVITY GAP DETECTION
            "DERIVED GROUP IDENT",  # DERIVED GROUP IDENTIFIERS
            "SEQUENTIAL EVENT",     # SEQUENTIAL EVENT PATTERN
            "USER-PRODUCT JOURNEY", # USER-PRODUCT JOURNEY MODELING
            "STATE TRANSITION",     # STATE TRANSITION DETECTION
            "EVENT-LEVEL TO SESSION", # EVENT-LEVEL TO SESSION-LEVEL AGGREGATION
            "TIME-BOUNDED CHAIN",   # TIME-BOUNDED CHAIN VALIDATION
            "GAP DETECTION",        # GAP DETECTION
            "RECOVERY WINDOW",      # RECOVERY WINDOW ANALYSIS
            "GAP",                  # general gap patterns (after more specific above)
            "ISLAND",
            "ANOMALY DETECTION",    # detecting sequential anomaly patterns
        ],

        # --- CTE pipelines ---
        "CTE PIPELINE": [
            "CTE",                  # CTE PIPELINE, MULTI-CTE PIPELINE, CTE REUSE, CTE FILTER
            "RECURSIVE",            # RECURSIVE CTE
            "STAGED QUERY",         # STAGED QUERY DECOMPOSITION
            "MULTI-STAGE",          # MULTI-STAGE METRIC FILTERING
        ],

        # --- Subquery patterns ---
        "SUBQUERY PATTERNS": [
            "SUBQUERY",             # CORRELATED SUBQUERY, SUBQUERY FILTER, SCALAR SUBQUERY IN CASE
            "CORRELATED",           # CORRELATED SUBQUERY, CORRELATED FROM CLAUSE
            "NESTED FILTER",        # NESTED FILTER LOGIC
            "EXISTS PATTERN",       # EXISTS PATTERN
            "SCALAR SUBQUERY",      # SCALAR SUBQUERY IN CASE
            "LATERAL",              # LATERAL JOIN, CORRELATED FROM CLAUSE
            "CROSS JOIN",           # CROSS JOIN WITH SCALAR
            "BEHAVIORAL EXCLUSION", # BEHAVIORAL EXCLUSION (correlated-subquery anti-join pattern)
            "BEHAVIORAL",           # broader behavioral patterns via subquery
            "FIRST-TO-LATER",       # FIRST-TO-LATER EVENT COMPARISON
            "TABLE ALIAS",          # TABLE ALIASES (alias scope in SQL clauses)
            "ALIASING RULES",       # ALIASING RULES
        ],

        # --- Self-comparison / recursion ---
        "SELF-COMPARISON & RECURSION": [
            "SELF-COMPAR",          # ROW-LEVEL SELF-COMPARISON, SELF-COMPARISON RANK EMULATION
            "ROW-LEVEL SELF",
            "ROW-TO-ROW",           # ROW-TO-ROW COMPARISON
            "HIERARCHY",            # recursive hierarchy traversal
        ],

        # --- Multi-table entity linking ---
        "MULTI-TABLE ENTITY LINKING": [
            "MULTI-TABLE",          # MULTI-TABLE ENTITY LINKING
            "ENTITY LINKING",
            "REQUIRED ENTITY MATCHING",
            "OPTIONAL ENTITY PRESERVATION",
            "LEFT JOIN DIRECTION",  # LEFT JOIN DIRECTION
            "FULL OUTER",           # FULL OUTER JOIN RECONCILIATION
            "ANTI-JOIN",            # ANTI-JOIN PATTERN, NULL-SAFE ANTI-JOIN
            "JOIN AGGREG",          # JOIN AGGREGATE (join + aggregate pattern)
            "LEFT JOIN AGGREG",     # LEFT JOIN AGGREGATE
            "DATE-RANGE JOIN",      # DATE-RANGE JOIN (join on date interval)
            "LEFT JOIN FOR OPTIONAL", # LEFT JOIN FOR OPTIONAL MATCH
            "TABLE NAME ERROR",     # TABLE NAME ERRORS (debug: wrong table reference)
            "CATALOG ERROR",        # CATALOG ERROR (wrong table name)
        ],

        # --- Set operations ---
        "SET OPERATIONS & COMPARISON": [
            "UNION",                # UNION SET OPERATION
            "INTERSECT",            # INTERSECT SET OPERATION, SHARED SET MEMBERSHIP
            "EXCEPT",               # EXCEPT SET OPERATION
            "SET DIFFER",           # BEHAVIORAL SET DIFFERENCE, SET DIFFERENCE
            "CROSS-SOURCE",         # CROSS-SOURCE MEMBERSHIP TESTS, CROSS-SOURCE RECONCILIATION
            "SET CONSOLIDATION",    # SET CONSOLIDATION (per brief)
            "JOIN EQUIVALENCE",     # JOIN EQUIVALENCE (per brief)
            "SHARED SET",           # SHARED SET MEMBERSHIP
            "BEHAVIORAL SET",       # BEHAVIORAL SET DIFFERENCE
        ],

        # --- Post-aggregation filtering (HAVING) ---
        "POST-AGGREGATION FILTERING": [
            "POST-AGGREGATION FILTER",  # POST-AGGREGATION FILTERING (exact), POST-AGGREGATION FILTER
            "HAVING",               # HAVING THRESHOLD, HAVING ON COUNT, HAVING VS WHERE
            "GROUP SIZE",           # GROUP SIZE COMPARISON (HAVING COUNT > N)
            "AVERAGE-BASED BENCH",  # AVERAGE-BASED BENCHMARKING (filter groups above average)
            "MULTI-STAGE METRIC FILTER",  # MULTI-STAGE METRIC FILTERING
        ],

        # --- Pre-aggregation filtering (WHERE) ---
        "PRE-AGGREGATION FILTERING": [
            "PRE-AGGREGATION FILTER",   # PRE-AGGREGATION FILTERING (exact)
            "PRE VS POST AGGREGATION",  # PRE VS POST AGGREGATION FILTERING
            "CONDITIONAL ROW FILTER",   # CONDITIONAL ROW FILTERING
            "RANGE FILTER",             # RANGE FILTERING
            "WHERE CLAUSE",             # WHERE CLAUSE
            "IN CLAUSE",                # IN CLAUSE FILTERING
            "SET MEMBERSHIP FILTER",    # SET MEMBERSHIP FILTERING → IN-clause pattern
            "SET MEMBERSHIP TEST",      # SET MEMBERSHIP TEST → IN-clause pattern
            "NUMERIC COMPARISON FILTER",# NUMERIC COMPARISON FILTER
            "MULTI-CONDITION FILTER",   # MULTI-CONDITION FILTERING
            "KNOWN-VALUE FILTER",       # KNOWN-VALUE FILTERING
            "OPTIONAL FIELD FILTER",    # OPTIONAL FIELD FILTERING
            "COMBINED AND",             # COMBINED AND CONDITIONS
            "CONDITIONAL FILTER",       # CONDITIONAL FILTERING
            "FILTERED GROUP",           # FILTERED GROUP BY
        ],

        # --- Grouped aggregation ---
        "GROUPED AGGREGATION": [
            "AGGREG",               # GROUPED AGGREGATION, CONDITIONAL AGGREGATION, VALUE AGGREGATION
                                    # CROSS-DIMENSIONAL AGGREGATION, MULTI-DIMENSION AGGREGATION etc.
            "ORDERED-SET AGGR",     # ORDERED-SET AGGREGATE
            "GROUP BY RULES",       # GROUP BY RULES
            "MULTI-COLUMN GROUP BY",# MULTI-COLUMN GROUP BY
            "MULTI-COLUMN GROUPING",# MULTI-COLUMN GROUPING
            "ROW COUNT AGGREG",     # ROW COUNT AGGREGATION (matches AGGREG too, redundant but safe)
            "EXTREMUM IDENTIF",     # EXTREMUM IDENTIFICATION (MAX/MIN single-column)
            "LOWEST-VALUE IDENTIF", # LOWEST-VALUE IDENTIFICATION
            "MULTI-METRIC SUMMAR",  # MULTI-METRIC SUMMARIZATION
            "TABLE-WIDE SUMMARY",   # TABLE-WIDE SUMMARY (scalar aggregate)
            "DISTRIBUTION ANAL",    # DISTRIBUTION ANALYSIS
            "MULTI-COLUMN SEGMENT", # MULTI-COLUMN SEGMENT AGGREGATION
            "GROUPING SETS",        # GROUPING SETS (per brief)
            "ARRAY_AGG",            # ARRAY_AGG (per brief)
            "ORDERED NESTED",       # ORDERED NESTED STRUCTURES
            "ROLLUP",               # ROLLUP SUBTOTALS (per brief)
            "GRAND TOTAL",          # GRAND TOTAL
            "COUNT NON-NULL",       # COUNT NON-NULL vs COUNT STAR
            "ORDER BY WITHIN",      # ORDER BY WITHIN AGGREGATE
            "SESSION ANAL",         # SESSION ANALYSIS (domain: count sessions by type)
            "ENGAGEMENT METRIC",    # ENGAGEMENT METRICS
            "REVENUE SHARE",        # REVENUE SHARE, REVENUE SHARE PER GROUP
            "FAILURE RATE",         # FAILURE RATE CALCULATION
            "SALARY ANAL",          # SALARY ANALYSIS
            "SALARY DISTRIBUT",     # SALARY DISTRIBUTION
            "SALARY BAND",          # SALARY BAND ANALYSIS (CASE WHEN banding)
            "SPEND ANAL",           # SPEND ANALYSIS
            "SUPPORT SLA",          # SUPPORT SLA ANALYSIS
            "SUPPORT ANAL",         # SUPPORT ANALYSIS
            "SUPPORT TICKET ANAL",  # SUPPORT TICKET ANALYSIS
            "PAYMENTS ANAL",        # PAYMENTS ANALYSIS
            "PAYMENT FAILURE ANAL", # PAYMENT FAILURE ANALYSIS
            "PAYMENT TREND",        # PAYMENT TREND ANALYSIS
            "PRODUCT FREQUENCY",    # PRODUCT FREQUENCY ANALYSIS
            "CATEGORY ANAL",        # CATEGORY ANALYSIS
            "ACQUISITION CHANNEL ANAL", # ACQUISITION CHANNEL ANALYSIS
            "GEO REVENUE ANAL",     # GEO REVENUE ANALYSIS (per brief)
            "HR HEADCOUNT",         # HR HEADCOUNT ANALYSIS
            "HR ANAL",              # HR ANALYTICS, HR SALARY ANALYSIS
            "COMPOSITE SCORING",    # COMPOSITE SCORING FORMULA
            "MULTI-DIMENSIONAL",    # MULTI-DIMENSIONAL SUMMARY
            "FILTER CLAUSE",        # FILTER CLAUSE (SQL aggregate FILTER keyword)
        ],

        # --- Conditional logic / CASE WHEN ---
        "CONDITIONAL LOGIC & CASE": [
            "CASE WHEN",            # CASE WHEN LADDER
            "RULE-BASED",           # RULE-BASED CLASSIFICATION
            "CONDITIONAL FLAG",     # CONDITIONAL FLAG AGGREGATION
            "CATEGORICAL SEGM",     # CATEGORICAL SEGMENTATION
            "PRIORITY-BASED",       # PRIORITY-BASED SEGMENTATION, PRECEDENCE-BASED CLASSIFICATION
            "PRECEDENCE-BASED",
            "TIERING",              # LOYALTY TIERING
            "LOYALTY TIER",         # LOYALTY TIERING
        ],

        # --- NULL handling ---
        "NULL HANDLING & COALESCE": [
            "COALESCE",             # COALESCE DEFAULT SUBSTITUTION, COALESCE NULL BRIDGING
            "ZERO-COUNT",           # ZERO-COUNT PRESERVATION
            "NULL AWARE",           # NULL AWARENESS
            "NULL STATE",           # NULL STATE FILTERING
            "NULL-SAFE",            # NULL-SAFE ARITHMETIC, NULL-SAFE ANTI-JOIN
            "NULL HANDLING",        # NULL HANDLING IN CONCAT
            "NULL CHECK",           # NULL CHECK COMBINED WITH COMPARISON
            "IS NOT NULL",
            "IS NULL",
            "NULL",                 # broad catch (after more specific patterns above)
        ],

        # --- Time-series / date ---
        "TIME-SERIES BUCKETING & ARITHMETIC": [
            "DATE",                 # DATE ARITHMETIC, DATE TRUNCATION, DATE BUCKET GROUPING, etc.
            "TIME-",                # TIME-SERIES AGGREGATION, TIME-WINDOW COMPARISON, TIME-SLICE
            "STRFTIME",             # STRFTIME FORMATTING
            "TEMPORAL",             # TEMPORAL JOIN LOGIC
            "MONTHLY",              # MONTHLY TREND, MONTHLY ENTITY COUNTING
            "QUARTER",              # QUARTER DERIVATION
            "PERIOD-OVER-PERIOD",   # PERIOD-OVER-PERIOD COMPARISON
            "CALENDAR SPINE",       # CALENDAR SPINE
            "BEFORE-AND-AFTER",     # BEFORE-AND-AFTER COMPARISON
            "INTERVAL ADDITION",    # INTERVAL ADDITION (per brief)
            "AT TIME ZONE",         # AT TIME ZONE (per brief)
            "TIMEZONE",             # TIMEZONE HANDLING
            "UTC CONVERS",          # UTC CONVERSION
            "TENURE",               # TENURE CALCULATION (per brief)
            "SUBSCRIPTION EXPIRY",  # SUBSCRIPTION EXPIRY
            "SEQUENCE GENERATION",  # SEQUENCE GENERATION (per brief)
            "GENERATE_SERIES",      # GENERATE_SERIES (per brief)
            "RECENCY COMP",         # RECENCY COMPARISON
            "LATEST-DATE",          # LATEST-DATE REFERENCE LOGIC
            "TREND ANAL",           # PAYMENT TREND ANALYSIS, etc. (domain time-series)
        ],

        # --- Deduplication ---
        "DEDUPLICATION LOGIC": [
            "DEDUP",                # DEDUPLICATION, DEDUPLICATED RESULT SHAPING, etc.
            "DISTINCT ENTITY",      # DISTINCT ENTITY COUNTING
            "DISTINCT PAYMENT-METHOD",  # DISTINCT PAYMENT-METHOD COUNTING
            "DISTINCT COUNT",       # DISTINCT COUNT
            "LATEST-ROW DEDUP",     # LATEST-ROW DEDUPLICATION
        ],

        # --- String parsing ---
        "STRING PARSING & PATTERN MATCHING": [
            "SPLIT_PART",           # SPLIT_PART
            "SUBSTRING",            # SUBSTRING EXTRACTION
            "PATTERN-BASED",        # PATTERN-BASED FILTERING
            "STRING",               # STRING TRIMMING, STRING CONCATENATION, DELIMITED STRING PARSING
            "REGEX",                # REGEX REPLACEMENT
            "TEXT NORMALI",         # TEXT NORMALIZATION
            "INITCAP",              # INITCAP TITLE CASE
            "EMAIL PARS",           # EMAIL PARSING
            "CHANNEL STANDARD",     # CHANNEL STANDARDIZATION
            "NORMALIZATION",        # CASE-INSENSITIVE NORMALIZATION
            "EMPLOYEE LABEL",       # EMPLOYEE LABELING (string output shaping)
            "LIKE",
            "ILIKE",
        ],

        # --- Result shaping & ordering ---
        "RESULT SHAPING & ORDERING": [
            "RESULT ORDERING",      # DETERMINISTIC RESULT ORDERING (incidental → will be stripped
                                    #   but must still resolve until stripped)
            "COLUMN PROJECTION",    # COLUMN PROJECTION (incidental → will be stripped)
            "DETERMINISTIC RESULT", # DETERMINISTIC RESULT ORDERING
            "OUTPUT SCHEMA",        # OUTPUT SCHEMA SHAPING
            "MULTI-COLUMN ORDER",   # MULTI-COLUMN ORDERING
            "DESCENDING RESULT",    # DESCENDING RESULT ORDERING
            "ASCENDING RESULT",     # ASCENDING RESULT ORDERING
            "LONG-FORMAT",          # LONG-FORMAT CROSS-TAB
            "COMPOSITE KEY",        # COMPOSITE KEY DESIGN
            "DERIVED FIELD",        # DERIVED FIELD CREATION
            "ORDER-FIRST",
            "COLUMN NAME ERROR",    # COLUMN NAME ERRORS (debug: wrong column reference)
        ],

        # ---- ⚡ New families (practice-grounded) ----

        "DATA QUALITY SKEPTICISM": [
            "DUPLICATE DETECTION",  # (canonical member tag)
            "ORPHAN RECORD",        # ORPHAN RECORD CHECK
            "ROW COUNT RECONCIL",   # ROW COUNT RECONCILIATION
            "NULL ANOMALY",         # NULL ANOMALY INSPECTION
            "DATA QUALITY GATE",    # (canonical member tag)
            "DATA QUALITY CLASS",   # DATA QUALITY CLASSIFICATION → re-tags to this family
            "DATA QUALITY",         # broad catch (after more specific above)
            "NOISY DATA",           # NOISY DATA RESOLUTION (Q13019)
            "CONTRADICTION",        # CONTRADICTION DETECTION (Q13023)
            "MISSING-EVIDENCE",     # MISSING-EVIDENCE HANDLING (Q13023)
            "ATTRIBUTION CONFLICT", # ATTRIBUTION CONFLICT RESOLUTION (conflicting signals)
            "ANOMALY",              # catch remaining anomaly patterns
        ],

        "DOUBLE-COUNTING DETECTION": [
            "FAN-OUT",              # FAN-OUT DETECTION, JOIN FAN-OUT
            "JOIN MULTIPLICATION",  # JOIN MULTIPLICATION
            "GRAIN MISMATCH",       # GRAIN MISMATCH
            "INFLATED METRIC",      # INFLATED METRIC DEBUG
        ],

        "METRIC RECONCILIATION": [
            "RECONCILIATION",       # METRIC RECONCILIATION, CROSS-SOURCE RECONCILIATION, etc.
            "MISMATCH AUDIT",
            "MISMATCH INVESTIGATION",
            "SOURCE OF TRUTH",
            "AUDIT",
        ],

        # ---- ⚡ Mock-only realism families (assessment lenses) ----
        # These may appear only in mock_only questions, never in practice,
        # and must co-occur with ≥1 practice-grounded family.

        "METRIC INTERPRETATION & DENOMINATOR CHOICE": [
            "ACTIVE-USER DEFINITION",
            "REVENUE BASIS CHOICE",
            "DENOMINATOR SELECTION",
            "DENOMINATOR",
            "RATE BASE NORMALI",    # RATE BASE NORMALIZATION
            "AMBIGUOUS METRIC",
            "KPI INTERPRETATION",
            "METRIC INTERPRETATION",
            "REVENUE SHARE CHOICE",
        ],

        "OUTPUT SANITY VALIDATION": [
            "SANITY",               # OUTPUT SANITY VALIDATION, ROW COUNT SANITY
            "OUTPUT VALIDATION",
            "ROW COUNT CHECK",
            "PLAUSIBILITY CHECK",
            "OUTPUT SANITY",
            "NULL COVERAGE SANITY",
        ],

        "PERFORMANCE-AWARE ANALYTICS": [
            "PERFORMANCE-AWARE",
            "SCAN REDUCTION",
            "CARDINALITY REDUCTION",
            "PRE-AGGREGATION STRATEGY",
            "REPEATED COMPUTATION ELIMINATION",
            "EFFICIENT ALTERNATIVE",
            "EFFICIENT APPROACH",
            "COST-AWARE",
        ],
    },

    # -----------------------------------------------------------------------
    # Python — 19 canonical families (docs/concept-taxonomy.md § Python)
    # -----------------------------------------------------------------------
    "python": {
        "SLIDING WINDOW": [
            "SLIDING WINDOW",
            "FIXED WINDOW",
            "MINIMUM WINDOW",
        ],
        "TWO POINTERS": [
            "TWO POINTER",
            "TWO-POINTER",
            "BOUNDARY POINTER",
            "THREE-WAY PARTITION",      # 3-bucket sweep (e.g. Dutch National Flag reframed)
            "TWO-POINTER SWEEP",
        ],
        "HASH-MAP STATE": [
            "HASH MAP",
            "HASH TABLE",
            "HASH SET",                 # set used for membership / dedup
            "HASH-BASED",
            "FREQUENCY COUNT",
            "FREQUENCY-BASED",
            "FREQUENCY",                # catches `character frequency`, `frequency tracking`
            "MEMBERSHIP-BASED",
            "BIJECTION",                # bijective key-value mapping
            "COMPLEMENT SEARCH",        # find complement / two-sum pattern
            "SET-BASED LOOKUP",
            "COUNTER",                  # Python Counter class
            "GROUPING BY KEY",
            "GROUPING",                 # group-by-key hashing
            "LRU",                      # LRU cache uses hash map + ordered structure
            "CACHE",                    # per brief: cache/lru → HASH-MAP STATE
            "BOYER-MOORE",              # Boyer-Moore majority/voting → heavy-hitter detection
            "CANDIDATE TRACKING",       # candidate-tracking variant of majority-vote
            "MAJORITY ELEMENT",
        ],
        "BINARY SEARCH": [
            "BINARY SEARCH",
            "PEAK FINDING",
            "PATIENCE SORTING",         # LIS via binary search / patience sort
        ],
        "INDEXED SEQUENCE REASONING": [
            "INDEXED SEQUENCE",
            "LINEAR STATE UPDATE",
            "LINEAR SCAN",
            "SUBARRAY",
            "PREFIX SUM",
            "PREFIX PRODUCT",           # prefix-product array pattern
            "RUNNING MAXIMUM",          # running max/min scan
            "CYCLIC SHIFT",             # rotate/shift by index arithmetic
            "CIRCULAR ARRAY",           # circular subarray problems
        ],
        # STREAMING / ONLINE REDUCTION: single-pass scan over an unbounded stream with bounded auxiliary
        # state. Distinct from SLIDING WINDOW (bounded-window expand/contract) and INDEXED SEQUENCE
        # REASONING (random-access where index meaning matters). Must come BEFORE STRING PATTERN
        # REASONING to prevent "ACCUMULATOR" etc. falling to a generic match.
        "STREAMING / ONLINE REDUCTION": [
            "STREAMING / ONLINE REDUCTION",  # explicit self-match
            "STREAMING",                     # streaming / online processing
            "ONLINE",                        # online reduction / online dedup
            "RUNNING MEDIAN",                # running median (two-heap pattern)
            "RUNNING MEAN",                  # running mean / online average
            "RUNNING STAT",                  # running statistics (mean, variance, etc.)
            "RUNNING AVERAGE",
            "RUNNING VARIANCE",
            "ACCUMULATOR",                   # accumulator / bounded-state pattern
            "SINGLE-PASS",                   # single-pass bounded-state reduction
            "SINGLE-PASS SCAN",
            "BOUNDED STATE",                 # bounded auxiliary state
            "BOUNDED AUXILIARY",
            "MISRA-GRIES",                   # Misra-Gries heavy-hitter / space-budget approx
            "SPACE-BUDGET",                  # space-budget heavy-hitter (Misra-Gries variant)
            "ONLINE DEDUP",                  # online dedup / CDC last-write-wins
            "SEQUENCE PROCESSING WITH ACCUMULATORS",  # legacy non-canonical tag → routes here
            "ONLINE REDUCTION",
            "WELFORD",                       # Welford one-pass variance
            "RESERVOIR SAMPLING",            # reservoir / random sampling over stream
            "EXPONENTIAL DECAY",             # exponential weighted moving average
        ],
        "STRING PATTERN REASONING": [
            "STRING PATTERN",
            "STRING MANIPULATION",
            # ORDER-FIRST REASONING removed — that tag was a sort-then-process tag
            # mis-filed here; it is stripped as incidental on questions that use it.
            "STRING",
            "ANAGRAM",                  # anagram detection / grouping (per taxonomy)
            "PALINDROME",               # palindrome / symmetric string
            "RUN-LENGTH",               # run-length encoding
            "STRING ENCODING",
            "COMPRESSION",              # string/data compression
            "TRIE",                     # prefix trie (for prefix routing / autocomplete)
            "PREFIX TREE",
            "TOKENIZ",                  # tokenization / text segmentation
            "SEGMENTAT",
            "CIPHER",                   # character-level cipher
            "ENCODING",                 # broad encoding / transformation
            "NORMALIZ",                 # normalization / canonicalization of strings
            "CANONICAL",
        ],
        "STACK & MONOTONIC STRUCTURES": [
            "STACK",
            "MONOTONIC",
            "RPN",                      # Reverse Polish Notation / postfix evaluation
            "EXPRESSION",               # expression evaluation (e.g. rule engine)
        ],
        "HEAP & PRIORITY QUEUE": [
            "HEAP",
            "PRIORITY QUEUE",
            "K-WAY MERGE",
            "MEDIAN TRACKING",
            "MEDIAN",                   # streaming median
            "TWO HEAPS",                # two-heap trick for streaming median
            "FREQUENCY-BASED SCHEDUL",  # task-scheduler heap pattern
            "IDLE SLOT",                # idle-slot calculation
        ],
        "GREEDY CHOICE": [
            "GREEDY",
            "INTERVAL SCHEDULING",
            "INTERVAL",                 # catches `interval problems`, `interval merge`
            "COOLDOWN",                 # greedy cooldown / task-scheduler pattern
            "SCHEDULING",
            "GREEDY ALGORITHM",
        ],
        # DYNAMIC PROGRAMMING (2D) must be checked BEFORE (1D) — the (1D) family's
        # "DYNAMIC PROGRAMMING" substring would otherwise catch "(2D)" tags first.
        "DYNAMIC PROGRAMMING (2D)": [
            "DYNAMIC PROGRAMMING (2D)", # explicit self-match — must be in patterns
            "2D DP",
            "MATRIX DP",
            "MATRIX",
            "GRID DP",                  # grid path / island DP
            "LCS",                      # Longest Common Subsequence
            "2D DP TABLE",
            "GRID PATH",
            "LONGEST COMMON",
            "EDIT DISTANCE",            # sequence alignment / fuzzy dedup DP
        ],
        "DYNAMIC PROGRAMMING (1D)": [
            "DYNAMIC PROGRAMMING (1D)", # explicit self-match (avoids ambiguity with (2D) above)
            "DYNAMIC PROGRAMMING",
            "1D DP",
            "MEMOIZATION",
            "KADANE",
            "COIN CHANGE",
            "LONGEST INCREASING SUBSEQUENCE",  # was 'LIS' — renamed to prevent false match with 'LIST...'
            "FIBONACCI",                # Fibonacci-recurrence DP
            "BOTTOM-UP",                # bottom-up tabulation
            "KNAPSACK",                 # knapsack DP (0/1 and unbounded)
            "WORD BREAK",               # text-segmentation DP
        ],
        # GRAPH TRAVERSAL (BFS / DFS): picking BFS vs DFS by problem shape, visited-set discipline,
        # cycle detection, unweighted reachability, topological sort (Kahn's). Does NOT cover
        # weighted shortest path (→ WEIGHTED SHORTEST PATH) or equivalence-class merge problems
        # (→ UNION-FIND & DISJOINT SET).
        "GRAPH TRAVERSAL (BFS / DFS)": [
            "GRAPH TRAVERSAL (BFS",     # explicit self-match prefix
            "BFS",
            "DFS",
            "UNWEIGHTED GRAPH",         # unweighted graph traversal
            "LEVEL ORDER",              # level-by-level BFS traversal
            "CYCLE DETECTION",          # DFS three-colour cycle detection
            "TOPOLOGICAL SORT",         # topological sort (Kahn's BFS or DFS)
            "KAHN",                     # Kahn's algorithm for topological sort
            "REACHABILITY",             # reachability / unweighted connectivity
            "DIRECTED GRAPH",           # directed graph traversal
        ],
        "UNION-FIND & DISJOINT SET": [
            "UNION-FIND & DISJOINT SET",  # explicit self-match
            "UNION-FIND",               # Union-Find / disjoint-set data structure
            "UNION FIND",
            "DISJOINT-SET",
            "DISJOINT SET",
            "UNION-BY-RANK",
            "UNION BY RANK",
            "PATH-COMPRESSION",         # path compression in Union-Find
            "PATH COMPRESSION",
            "CONNECTED-COMPONENT",      # component discovery via Union-Find
            "CONNECTED COMPONENT",
            "KRUSKAL",                  # Kruskal MST algorithm uses Union-Find
            "RECORD LINKAGE",           # entity resolution → Union-Find in practice
            "DSU",                      # Disjoint Set Union (alternative abbreviation)
        ],
        "WEIGHTED SHORTEST PATH": [
            "WEIGHTED SHORTEST PATH",   # explicit self-match
            "WEIGHTED SHORTEST",
            "DIJKSTRA",                 # Dijkstra's shortest path (weighted)
            "WEIGHTED GRAPH",
            "SHORTEST PATH",            # any shortest-path algorithm (weighted context)
            "MIN-COST PATH",
            "MIN COST PATH",            # unhyphenated variant
            "MIN-COST PATH RELAXATION", # edge relaxation pattern (Dijkstra/Bellman)
            "PRIORITY-ORDERED FRONTIER",
            "DISTANCE MAP",             # distance map in weighted graph search
            "GREEDY SHORTEST",          # greedy shortest-path expansion
            "BELLMAN-FORD",             # Bellman-Ford relaxation
            "A-STAR",                   # A* heuristic search
            "ASTAR",                    # alternate spelling (no hyphen)
            "A*",                       # symbolic form of A*
            "CRITICAL PATH",            # critical path method (weighted DAG DP)
        ],
        "BACKTRACKING & COMBINATORIAL SEARCH": [
            "BACKTRACKING",
            "COMBINATORICS",
            "RECURSION",
            "SERIALIZATION",            # tree/graph serialization (structural recursion)
            "PREORDER",                 # preorder / postorder traversal
            "BST",                      # binary search tree operations
            "VISITED STATE",            # visited-set tracking in search
        ],
        "IN-PLACE TRANSFORMATION & SPACE OPTIMIZATION": [
            "IN-PLACE",
            "SPACE",
            "REVERSAL TRICK",           # reverse-array-in-sections trick
            "IN-PLACE REVERSAL",
            "SEQUENCE BLOCK",           # reverse blocks / partition in place
            "POINTER MANIPULATION",     # pointer-rearrangement (linked structures)
        ],
        "MODULAR ARITHMETIC & NUMBER THEORY": [
            "MODULAR",
            "NUMBER THEORY",
            "XOR",
            "POWER-OF-TWO",
            "BIT MANIPULATION",
            "BIT",                      # per brief: `bit`/`xor` → MODULAR ARITHMETIC
            "TRIAL DIVISION",           # primality via trial division
            "SUM FORMULA",              # Gauss sum / closed-form formula
            "NUMERIC",                  # numeric property checks
        ],
        "LIST & COLLECTION TRANSFORMATION": [
            "LIST & COLLECTION TRANSFORMATION",  # explicit self-match
            "LIST MANIPULATION",
            "LIST",
            "COLLECTIONS",
            "DEFAULTDICT",              # defaultdict grouping
            "DEQUE",                    # deque-based window / queue
            "CHUNKED ITERATION",        # chunk / batch iteration
            "BATCH PROCESSING",
            "FILTER AND SORT",          # filter + sort pipeline
            "ORDER-PRESERVING",         # order-preserving dedup / filter
            "INTERSECTION",             # set intersection / common elements
        ],
    },

    # -----------------------------------------------------------------------
    # Pandas — 21 canonical families (docs/concept-taxonomy.md § Pandas)
    # -----------------------------------------------------------------------
    "python-data": {
        "WINDOW & ROLLING OPERATIONS": [
            "ROLLING",
            "EXPANDING",
            "RESAMPLE",
            "CUMSUM",
            "RUNNING TOTAL",
        ],
        "RANKING & TOP-N PER GROUP": [
            "RANK",
            "TOP-K",
            "TOP-N",
            "NLARGEST",
            "DETERMINISTIC TIE",
        ],
        "GROUPED AGGREGATION": [
            "GROUPED AGGREGATION",
            "GROUPBY AGGREGATION",
            "AGGREGATION",
            " AGG",
            "AGGREG",
            "NAMED AGGREG",
        ],
        "MULTI-DATAFRAME ENTITY LINKING": [
            "MULTI-DATAFRAME",
            "MULTI-TABLE JOIN",
            "ENTITY LINKING",
            "MERGE",
        ],
        "RESHAPING & PIVOT": [
            "WIDE-FORM RESHAPING",
            "PIVOT",
            "MELT",
            "STACK",
            "UNSTACK",
        ],
        "MISSING VALUE STRATEGY": [
            "MISSING-VALUE",
            "MISSING VALUES",
            "IMPUTATION",
            "FILLNA",
        ],
        "DATETIME OPERATIONS": [
            "DATETIME",
            "TIMEDELTA",
            "TIME SERIES",
            "DATE FORMATTING",
        ],
        "DEDUPLICATION LOGIC": [
            "DEDUP",
            "DISTINCT",
            "UNIQUE",
            "VALUE_COUNTS",
            "DISTINCT COUNTING",
        ],
        "BOOLEAN INDEXING & FILTERING": [
            "BOOLEAN INDEXING",
            "NULL-BASED ROW FILTERING",
            "QUERY FILTER",
        ],
        "COLUMN SELECTION & PROJECTION": [
            "COLUMN SELECTION",
            "DERIVED COLUMNS",
            ".ASSIGN",
        ],
        "METHOD CHAINING & PIPELINE STYLE": [
            "METHOD CHAINING",
            "PIPE",
            "CHAIN",
        ],
        "CATEGORICAL & BINNING": [
            "BUCKETING",
            "CUT",
            "QCUT",
            "CATEGORICAL",
            "BINNING",
        ],
        "TRANSFORM VS AGGREGATE": [
            "TRANSFORM",
        ],
        "OUTPUT SHAPE & ORDERING": [
            "OUTPUT SCHEMA",
            "RESULT ORDERING",
            "DETERMINISTIC",
            "RESET_INDEX",
        ],
        "DEBUG PANDAS": [
            "DEBUG",
            "KEYERROR",
        ],
        # ⚡ new families
        "MEMORY & VECTORIZATION REASONING": [
            "VECTORIZATION OVER APPLY",
            "DTYPE MEMORY CHOICE",
            "CHUNK READING",
            "APPLY VS TRANSFORM TRADEOFF",
            "VECTORIZ",
            "MEMORY",
        ],
        "METRIC INTERPRETATION & DENOMINATOR CHOICE": [
            "ACTIVE-USER DEFINITION",
            "DENOMINATOR",
            "RATE BASE",
            "AMBIGUOUS METRIC",
            "METRIC INTERPRETATION",
            "KPI INTERPRETATION",
        ],
        "DATA QUALITY SKEPTICISM": [
            "DATA QUALITY",
            "DUPLICATE DETECTION",
            "ORPHAN",
            "NULL ANOMALY",
            "DTYPE ANOMALY",
            "ROW COUNT SANITY",
        ],
        "DOUBLE-COUNTING DETECTION": [
            "FAN-OUT",
            "JOIN MULTIPLICATION",
            "MERGE MULTIPLICATION",
            "GRAIN MISMATCH",
            "INFLATED METRIC",
        ],
        "OUTPUT SANITY VALIDATION": [
            "SANITY",
            "OUTPUT VALIDATION",
            "ROW COUNT CHECK",
            "SHAPE ASSERTION",
            "DTYPE ASSERTION",
            "PLAUSIBILITY CHECK",
        ],
        "PERFORMANCE-AWARE ANALYTICS": [
            "PERFORMANCE-AWARE",
            "SCAN REDUCTION",
            "CARDINALITY REDUCTION",
            "PRE-AGGREGATION STRATEGY",
            "EFFICIENT ALTERNATIVE",
            "EFFICIENT APPROACH",
            "COST-AWARE",
        ],
    },

    # -----------------------------------------------------------------------
    # PySpark — 21 canonical families (docs/concept-taxonomy.md § PySpark)
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # PySpark — 23 canonical families (docs/concept-taxonomy.md § PySpark)
    # Phase 2 (2026-05): expanded match-patterns (~184 incidences resolved),
    # two new families (WINDOW FUNCTIONS & FRAMES, COLLECTION & ARRAY
    # OPERATIONS), and all ⚡ families now practice-grounded.
    # NOTE: ORDER MATTERS. More-specific families must precede families with
    # broader patterns (e.g. NARROW VS WIDE before SHUFFLE, DELTA LAKE before
    # catch-all families, STRUCTURED STREAMING before MEMORY for some tags).
    # -----------------------------------------------------------------------
    "pyspark": {

        # --- Execution model: lazy eval, DAG, lineage, RDD vs DataFrame ------
        # Keep BEFORE NARROW VS WIDE so that LINEAGE / STAGE tags resolve here.
        # NARROW VS WIDE and related patterns intentionally removed (Phase 2)
        # — they now live exclusively in NARROW VS WIDE TRANSFORMATIONS.
        "EXECUTION MODEL REASONING": [
            "LAZY EVALUATION",
            "LAZY EVAL",
            "LAZY ",          # catch "lazy evaluation" even without the word
            "EXECUTION MODEL",
            "DAG",
            "TRANSFORMATIONS VS",
            "LINEAGE",
            "STAGE",
            # Phase 2 expansions
            "RDD",            # RDD API, RDD vs DataFrame, RDD-based
            "DATAFRAME API",
            "DATASET VS",
            "IMMUTABILITY",
            "JOB EXECUTION",
            "CLUSTER ARCHITECTURE",
            "DISTRIBUTED SYSTEM",
            "SPARKSESSION",
            "GETORCREATE",
            "SESSION LIFECYCLE",
            "IDEMPOTENT FACTORY",
            "SPARK SQL CATALOG",
            "SESSION-SCOPED",
            "SPARK EXECUTION HIERARCHY",
            "TASK SCHEDULING",
            "TUNGSTEN",
            "EXECUTION ENGINE",
            "RECOMPUTATION",
            "CHECKPOINT",
            "ITERATIVE ALGORITHM",
            "LINEAGE EXPLOSION",
            "DAG COMPLEXITY",
            "DAG DEPTH",
            "F.EXPR",
            "SQL EXPRESSION",
            "ACTIONS",
            "RETURN VALUES",
        ],

        # --- Narrow vs wide: which operations cross partition boundaries -----
        # NARROW VS WIDE patterns moved here from EXECUTION MODEL REASONING.
        # SHUFFLE REASONING keeps bare SHUFFLE for shuffle-specific questions.
        "NARROW VS WIDE TRANSFORMATIONS": [
            "NARROW VS WIDE",
            "NARROW TRANSFORMATION",
            "WIDE TRANSFORMATION",
            "WIDE-AGGREGATION SHUFFLE",
            "SHUFFLE BOUNDARY",
        ],

        # --- Shuffle triggers, elimination, sort-by-key ----------------------
        # "shuffle" is ONLY in SHUFFLE REASONING; "narrow vs wide" is ONLY in
        # NARROW VS WIDE TRANSFORMATIONS (Phase 2 precision fix).
        "SHUFFLE REASONING": [
            "SHUFFLE",
            # Phase 2 expansions
            "REDUCEBYKEY",
            "GROUPBYKEY",
            "MAP-SIDE COMBINE",
            "CO-LOCATION",
            "SORTWITHPARTITIONS",
            "GLOBAL SORT",
            "ORDERBY",
            "SHUFFLE PARTITION IMBALANCE",
        ],

        # --- Join strategy: broadcast, sort-merge, skew join -----------------
        "JOIN STRATEGY SELECTION": [
            "BROADCAST JOIN",
            "JOIN OPTIMIZATION",
            "AUTOBROADCAST",
            "BROADCAST",
            "SORT-MERGE",
            "JOIN",
            # Phase 2 expansions
            "CARTESIAN PRODUCT",
            "SMALL TABLE OPTIMIZATION",
            "HINT OVERRIDE",
            "BUILD-SIDE REPLICATION",
        ],

        # --- Partitioning: count, layout, pruning, write strategy ------------
        "PARTITIONING STRATEGY": [
            "PARTITIONING",
            "PARTITION SHAPE",
            "PARTITION PRUNING",
            "COALESCE",
            "REPARTITION",
            "DYNAMIC PARTITION PRUNING",
            # Phase 2 expansions
            "PARTITIONS",
            "PARTITIONBY",
            "PARTITION SIZING",
            "PARTITION COUNT",
            "PARTITION SPLITTING",
            "DIRECTORY STRUCTURE",
            "BLOCK SIZE",
            "DATA DISTRIBUTION",
            "DPP",
            "SCAN-TIME PRUNING",
            "PARTITION SCAN STRATEGY",
            "PARTITION KEY ALIGNMENT",
            "DOWNSTREAM PARALLELISM",
            "OUTPUT PARALLELISM",
            "PARTITIONED WRITE",
            "ADVISORYPARTITION",
            "PARTITION-LEVEL TRANSFER",
            "PARTITION VS FILE-LEVEL",
        ],

        # --- Data skew: detection, salting, hot keys -------------------------
        "DATA SKEW & MITIGATION": [
            "DATA SKEW",
            "SKEW",
            "SALTING",
            "HOT KEY",
            "IMBALANCE",
            # Phase 2 expansions
            "PARTITION IMBALANCE",
        ],

        # --- AQE: runtime rewrites, skew splitting, partition coalescing -----
        "ADAPTIVE QUERY EXECUTION": [
            "AQE",
            "ADAPTIVE QUERY",
            "ADAPTIVE",
            "RUNTIME PLAN",
            "RUNTIME JOIN",
            # Phase 2 expansions
            "RUNTIME PARTITION RESTRUCTURING",
            "RUNTIME OPTIMIZATION",
        ],

        # --- Catalyst: plan analysis, predicate pushdown, file pruning -------
        "CATALYST OPTIMIZER": [
            "CATALYST",
            "OPTIMIZER",
            "LOGICAL PLAN",
            "PHYSICAL PLAN",
            "PREDICATE PUSH",
            "PROJECTION PUSHDOWN",
            "QUERY PLAN",
            "EXPLAIN",
            # Phase 2 expansions
            "EXECUTION PLAN",
            "QUERY OPTIMIZATION",
            "ANALYSIS PHASE",
            "PIPELINE OPTIMIZATION",
            "EXCHANGE OPERATOR",
            "HASHAGGR",
            "COLUMN PRUNING",
            "DATA SKIPPING",
            "DATA-SKIPPING PRUNING",
            "FILE-LEVEL STATISTICS",
            "PER-FILE MIN",
            "ROW GROUP PRUNING",
            "I/O OPTIMIZATION",
            "I-O REDUCTION",
            "COLUMN-STATISTICS FILTERING",
            "EXECUTION PLAN EQUIVALENCE",
            "PREDICATE PUSHDOWN IN MERGE",
        ],

        # --- Memory: driver vs executor, OOM, GC, spill, Arrow ---------------
        # Apache Arrow serialisation maps here (also fits UDF; MEMORY is first).
        "MEMORY MANAGEMENT": [
            "MEMORY",
            "OOM",
            "OUTOFMEMORYERROR",
            "OFF-HEAP",
            "GC",
            "SPILL",
            "SERIALIZATION",
            "DRIVER-SIDE MATERIALIZATION",
            # Phase 2 expansions
            "GARBAGE COLLECTION",
            "JVM GC",
            "JVM OBJECT",
            "DISK SPILL",
            "TOPANDAS",
            "DATA COLLECTION ANTI",
            "COLLECT() ANTI",
            "CLUSTER-SIDE AGGREGATION",
            "DISTRIBUTED AGGREGATION",
            "MATERIALISATION",
            "MATERIALIZATION",
            "YARN",
            "APACHE ARROW",
            "ARROW SERIAL",
        ],

        # --- Caching: persist storage levels, unpersist discipline -----------
        "CACHING & PERSISTENCE": [
            "CACHING",
            "CACHE",
            "PERSIST",
            "STORAGE LEVEL",
        ],

        # --- Schema & types: inference, coercion, null semantics -------------
        "SCHEMA & TYPE HANDLING": [
            "SCHEMA",
            "INFERSCHEMA",
            "STRUCTTYPE",
            "TYPE COERCION",
            # Phase 2 expansions
            "STRINGTYPE",
            "LONGTYPE",
            "DOUBLETYPE",
            "INTEGERTYPE",
            "TYPE INFERENCE",
            "TYPE PROMOTION",
            "TYPE CONTRACT",
            "TYPE SAFETY",
            "RETURNTYPE",
            "AGGREGATION OUTPUT TYPES",
            "NULLABLE VS NON-NULLABLE",
            "NULL PROPAGATION",
            "SILENT NULL PRODUCTION",
            "NULL PRODUCTION",
            "CAST NULL-ON-FAILURE",
            "PERMISSIVE NULLABILITY",
            "CONSERVATIVE NULLABILITY",
            "COMPUTED COLUMN NULLABILITY",
            "COLUMN REFERENCE QUALIFICATION",
            "COLUMN RESOLUTION",
            "UNIONBYNAME",
            "POSITIONAL MATCHING",
            "COLUMN RENAMING",
            "PYTHON NONE VS",
            "NDJSON",
            "JSON PARSING",
        ],

        # --- File formats: Parquet, CSV, JSON, columnar benefits -------------
        "FILE FORMATS & READERS": [
            "PARQUET",
            "CSV READING",
            "FILE FORMAT",
            "COLUMNAR",
        ],

        # --- UDF & Python boundary: vectorized UDFs, Arrow, mapPartitions ----
        "UDF & PYTHON BOUNDARY": [
            "UDF",
            "PANDAS UDF",
            # Phase 2 expansions
            "VECTORISED EXECUTION",
            "VECTORIZED EXECUTION",
            "JVM-PYTHON",
            "MAPPARTITIONS",
            "INITIALIZATION OVERHEAD",
            "ACCUMULATOR",
            "PYTHON UDF",
        ],

        # --- Structured Streaming: output modes, watermarks, stateful --------
        "STRUCTURED STREAMING": [
            "STRUCTURED STREAMING",
            "STREAMING",
            "STREAM-",
            "MICRO-BATCH",
            "WATERMARK",
            "FOREACHBATCH",
            "STATEFUL AGGREG",
            "MAPGROUPSWITHSTATE",
            # Phase 2 expansions
            "FOREACH",
            "UNBOUNDED TABLE",
            "CONTINUOUS PROCESSING",
            "LATE DATA",
            "LATE-DATA",
            "GROUPSTATETIMEOUT",
            "STATE EXPIRATION",
            "STATE MANAGEMENT",
            "KAFKA",
            "EVENT-TIME VS PROCESSING-TIME",
            "EVENT TIME VS PROCESSING TIME",
            "EVENT-TIME VS PROCESSING TIME",
            "UPDATE MODE",
            "APPEND MODE",
            "LATE-DATA DISCARD RULES",
            "APPEND-MODE EMISSION RULES",
            "EVENT-TIME GUARANTEE BOUNDARIES",
            "CUSTOM SINKS",
            "STREAMING WINDOW",
            "WATERMARK COLUMN MISMATCH",
            "STATEFUL AGGREGATION SCALING",
            "OUTPUT MODE",
            "LATE DATA DROP",
            "LATE DATA HANDLING",
            "EVENT-TIME LATENCY",
            "APPEND MODE WINDOW EMISSION",
            "KAFKA CONSUMER OFFSET",
        ],

        # --- Delta Lake: MERGE, time travel, schema evolution, Z-order -------
        # Bare MERGE intentionally excluded — false-positives on sort-merge
        # join tags. Use MERGE INTO / DELTA MERGE patterns instead.
        "DELTA LAKE OPERATIONS": [
            "DELTA LAKE",
            "DELTA",
            "MERGE INTO",
            "DELTA MERGE",
            # Phase 2 expansions
            "VERSIONASOF",
            "TRANSACTION LOG",
            "ACID TABLE MUTATION",
            "MATCHED VS UNMATCHED",
            "INCREMENTAL TABLE RECONCILIATION",
            "IMMUTABLE FILE REWRITE",
            "TABLE MAINTENANCE",
            "CDC PIPELINE",
            "CDC BATCH",
            "UPSERT CORRECTNESS",
            "MERGE-CONDITION LOGIC",
            "MERGE CARDINALITY",
            "SQL MERGE",
            "Z-ORDER CLUSTERING",
            "Z-ORDERING",
            "Z-ORDER",
            "DELTA STREAMING",
            "INCREMENTAL WRITE CLUSTERING",
            "OPTIMIZE ZORDER",
            "TIME TRAVEL",
        ],

        # --- Fault tolerance: lineage recovery, speculation, exactly-once ----
        "FAULT TOLERANCE & RECOVERY": [
            "FAULT TOLERANCE",
            "FAULT",
            "SPECULATIVE EXECUTION",
            "RECOVERY",
            # Phase 2 expansions
            "STRAGGLER TASK",
            "STRAGGLER",
            "SPARK.SPECULATION",
            "IDEMPOTENT SINK",
            "SINK IDEMPOTENCY",
            "AT-LEAST-ONCE WRITE",
            "AT-LEAST-ONCE SEMANTICS",
            "FOREACHBATCH AT-LEAST",
            "EXACTLY-ONCE",
            "TASK OUTPUT COMMIT",
            "PARTIAL WRITE ON",
            "EXTERNAL SIDE EFFECT",
            "FAILURE-SAFE",
        ],

        # --- Debug Spark errors: AnalysisException, TypeError, stack traces --
        "DEBUG SPARK ERRORS": [
            "ANALYSISEXCEPTION",
            "DEBUG",
            "EXCEPTION",
            "TYPEERROR",
        ],

        # --- Performance tuning: config, small files, cloud metadata --------
        "PERFORMANCE TUNING & TRADE-OFFS": [
            "PERFORMANCE",
            "PERFORMANCE TUNING",
            "TUNING",
            # Phase 2 expansions
            "SPARK.SERIALIZER",
            "TASK OVERHEAD",
            "SMALL FILE PROBLEM",
            "CLOUD STORAGE METADATA",
            "PRODUCTION PATTERN",
            "LARGE DATA",
            "ANTI-PATTERN AVOIDANCE",
            "EXTERNAL MERGE-SORT",
            "FALSE POSITIVES",
            "PROBABILISTIC",
        ],

        # ⚡ practice-grounded families — established via remap + new authoring
        # in Phase 2. All three are practice-grounded for PySpark (no mock-only
        # realism class; MCQ format makes sanity/validation reasoning gradeable).

        "DATA QUALITY SKEPTICISM": [
            "DATA QUALITY",
            "LATE EVENT",
            "LATE-EVENT",
            "DUPLICATE EVENT",
            "NULL KEY",
            "DIRTY INPUT",
            # Phase 2 remap targets (retag into this family via agent)
            "DROPDUPLICATE",
            "NON-DETERMINISM",
            "NON-DETERMIN",
            "DEDUPLICATION",
            "DEDUP",
            "SOURCE DEDUP",
            "NULL HANDLING",
            "PRODUCTION VS DEV DATA",
            "NAN-TO-NULL",
        ],

        "DOUBLE-COUNTING DETECTION": [
            "FAN-OUT",
            "JOIN MULTIPLICATION",
            "GRAIN MISMATCH",
            "INFLATED OUTPUT",
        ],

        "OUTPUT SANITY VALIDATION": [
            "SANITY",
            "OUTPUT VALIDATION",
            "ROW COUNT CHECK",
            "SCHEMA ASSERTION",
            "PLAUSIBILITY CHECK",
            # Phase 2 remap targets
            "COUNT VS COUNTDISTINCT",
            "LEN() VS COUNT",
            "SPARK UI DIAGNOSIS",
            "SPARK UI TASK METRICS",
            "FULL TABLE SCAN DIAGNOSIS",
        ],

        # --- New families added in Phase 2 ------------------------------------

        # Window functions: ranking, frames (ROWS vs RANGE), cumulative -------
        # Note: RANK pattern is safe here because JOIN STRATEGY SELECTION
        # (which precedes this in the dict) uses SORT-MERGE not bare RANK.
        "WINDOW FUNCTIONS & FRAMES": [
            "WINDOW FUNCTION",
            "WINDOW FRAME",
            "ROWSBETWEEN",
            "RANGEBETWEEN",
            "ROWS VS RANGE",
            "DENSE_RANK",
            "ROW_NUMBER",
            "CUMULATIVE AGGREGATION",
            "RUNNING AGGREGATION",
            "TIES HANDLING",
            "TIE HANDLING",
            "RANK",
        ],

        # Array ops: explode, collect_list/set, pivot, lateral view -----------
        "COLLECTION & ARRAY OPERATIONS": [
            "EXPLODE",
            "COLLECT_LIST",
            "COLLECT_SET",
            "COLLECT LIST",
            "COLLECT SET",
            "ARRAY COLUMN",
            "ARRAY ORDERING",
            "OUTER LATERAL VIEW",
            "PIVOT",
            "NULL VS EMPTY ARRAY",
            "ROW PRESERVATION",
            "WIDE DATAFRAME",
        ],

    },

    # -----------------------------------------------------------------------
    # Data Engineering — 21 canonical families
    # -----------------------------------------------------------------------
    "data-engineering": {
        "ETL VS ELT": [
            "ETL VS ELT",
            "ETL",
            "ELT",
            "EXTRACT",
            "LOAD ORDER",
        ],
        "IDEMPOTENCY": [
            "IDEMPOTEN",
            "DUPLICATE PREVENTION",
            "SAFE RERUN",
        ],
        "BACKFILL DESIGN": [
            "BACKFILL",
            "HISTORICAL REPROCESS",
            "PARTITION RERUN",
        ],
        "ORCHESTRATION": [
            "ORCHESTRAT",
            "DAG",
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
            "SCHEMA REGISTRY",
        ],
        "BATCH VS STREAMING": [
            "BATCH VS STREAM",
            "MICRO-BATCH",
            "REAL-TIME",
            "LATENCY TRADEOFF",
            "STREAM PROCESSING",
            "STREAMING ARCHITECTURE",
        ],
        "WATERMARKING": [
            "WATERMARK",
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
            "PARTITION",
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
        "STORAGE ARCHITECTURE": [
            "STORAGE ARCHITECTURE",
            "DATA LAKE",
            "DATA WAREHOUSE",
            "LAKEHOUSE",
            "OLAP",
        ],
        "CDC & INGESTION": [
            "CDC",
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
        "DATA CONTRACT": [
            "DATA CONTRACT",
        ],
        "LINEAGE & OBSERVABILITY": [
            "LINEAGE",
            "OBSERVABILITY",
            "FRESHNESS",
            "METADATA",
            "ALERTING",
        ],
        "SCD OPERATIONS": [
            "SCD",
            "SLOWLY CHANGING",
            "EFFECTIVE DATE",
            "SURROGATE KEY",
        ],
        "COST OPTIMIZATION": [
            "COST OPTIM",
            "COMPUTE VS STORAGE",
            "SCAN COST",
            "STORAGE TIER",
            "CLOUD COST",
            "BIGQUERY COST",
            "SNOWFLAKE COST",
            "WAREHOUSE COST",
        ],
        "INCIDENT RESPONSE": [
            "INCIDENT RESPONSE",
            "INCIDENT",
            "ROOT CAUSE",
            "REPLAY",
            "REMEDIATION",
            "CASCADING FAILURE",
            "PIPELINE RESILIENCE",
        ],
        "BACKPRESSURE": [
            "BACKPRESSURE",
            "KAFKA CONSUMER LAG",
        ],
        "DATA GOVERNANCE": [
            "GOVERNANCE",
            "GDPR",
            "CRYPTO SHREDDING",
            "IMMUTABLE STORAGE",
        ],
    },

    # -----------------------------------------------------------------------
    # Data Modeling — 22 canonical families
    # -----------------------------------------------------------------------
    "data-modeling": {
        "DIMENSIONAL MODELING": [
            "DIMENSIONAL MODELING",
            "STAR SCHEMA",
            "SNOWFLAKE SCHEMA",
        ],
        "FACT TABLE DESIGN": [
            "FACT TABLE",
            "FACT TYPE",
            "TRANSACTION FACT",
            "ACCUMULATING SNAPSHOT",
            "PERIODIC SNAPSHOT",
        ],
        "DIMENSION DESIGN": [
            "DIMENSION DESIGN",
            "CONFORMED",
            "DEGENERATE",
            "JUNK DIMENSION",
            "ROLE-PLAYING",
        ],
        "GRAIN DEFINITION": [
            "GRAIN",
        ],
        "SCD STRUCTURE": [
            "SCD",
            "SLOWLY CHANGING",
            "TYPE 1",
            "TYPE 2",
            "TYPE 3",
            "TYPE 4",
            "TYPE 6",
        ],
        "SURROGATE VS NATURAL KEYS": [
            "SURROGATE",
            "NATURAL KEY",
            "KEY STRATEGY",
        ],
        "NORMALIZATION": [
            "NORMALIZATION",
            "1NF",
            "2NF",
            "3NF",
            "BCNF",
        ],
        "DENORMALIZATION TRADEOFF": [
            "DENORMALIZATION",
        ],
        "BRIDGE & MANY-TO-MANY": [
            "BRIDGE",
            "MANY-TO-MANY",
            "MULTI-VALUED DIMENSION",
            "WEIGHTING FACTOR",
        ],
        "SCHEMA FROM REQUIREMENTS": [
            "SCHEMA FROM REQUIREMENTS",
            "REQUIREMENTS GATHERING",
        ],
        "REFERENTIAL INTEGRITY": [
            "REFERENTIAL INTEGRITY",
            "FOREIGN KEY",
            "ORPHAN",
            "CASCADE",
        ],
        "AGGREGATE & SUMMARY DESIGN": [
            "AGGREGATE",
            "SUMMARY DESIGN",
            "PRE-AGGREGATION",
            "CUBE",
        ],
        "BI-TEMPORAL MODELING": [
            "BI-TEMPORAL",
            "TRANSACTION TIME",
            "VALID TIME",
            "AS-OF",
        ],
        "DATA VAULT": [
            "DATA VAULT",
            "HUB",
            "LINK",
            "SATELLITE",
        ],
        "SEMANTIC LAYER & METRIC GOVERNANCE": [
            "SEMANTIC LAYER",
            "METRIC GOVERNANCE",
            "METRIC DEFINITION",
            "SINGLE SOURCE OF TRUTH",
        ],
        "SCHEMA EVOLUTION": [
            "SCHEMA EVOLUTION",
        ],
        "WIDE VS NARROW": [
            "WIDE VS NARROW",
            "OBT (ONE BIG TABLE)",
            "ONE BIG TABLE",
        ],
        "DBT MODELING": [
            "DBT MODELING",
            "DBT",
        ],
        "CONFORMED DIMENSIONS": [
            "CONFORMED DIMENSION",
            "MASTER DATA",
        ],
        "HIERARCHIES & MULTI-PATH": [
            "HIERARCHIES",
            "MULTI-VALUED",
            "CROSS-HIERARCHY",
            "MULTIPLE HIERARCHIES",
        ],
        "ADDITIVE VS NON-ADDITIVE": [
            "ADDITIVE",
            "NON-ADDITIVE",
            "SEMI-ADDITIVE",
        ],
        "DOUBLE-COUNTING & FAN-OUT": [
            "DOUBLE-COUNTING",
            "FAN-OUT",
            "ROW MULTIPLICATION",
            "FACT-TO-FACT JOIN",
        ],
    },

    # -----------------------------------------------------------------------
    # Statistics — 12 canonical families (lowercase canonical for this track)
    # -----------------------------------------------------------------------
    "statistics": {
        "descriptive statistics": [
            "descriptive statistics",
            "measures of central tendency",
            "outliers",
            "variance",
            "standard deviation",
        ],
        "probability & combinatorics": [
            "probability",
            "combinatorics",
            "combinations",
            "permutations",
            "expected value",
            "bayes",
            "conditional probability",
            "independence",
        ],
        "distributions": [
            "distribution",
            "bernoulli",
            "poisson",
            "binomial",
            "normal",
            "t-distribution",
            "chi-squared",
            "z-score",
        ],
        "sampling & central limit theorem": [
            "sampling",
            "central limit theorem",
            "CLT",
            "standard error",
            "law of large numbers",
            "sample size",
        ],
        "confidence intervals & estimation": [
            "confidence interval",
            "parameter estimation",
            "bootstrap",
            "resampling",
            "MLE",
            "maximum likelihood",
        ],
        "hypothesis testing": [
            "hypothesis testing",
            "p-value",
            "null hypothesis",
            "t-test",
            "z-test",
            "chi-squared test",
            "ANOVA",
        ],
        "errors & power": [
            "type i",
            "type ii",
            "statistical power",
            "effect size",
            "power analysis",
        ],
        "multiple testing & correction": [
            "multiple comparisons",
            "multiple testing",
            "bonferroni",
            "FDR",
        ],
        "bayesian inference": [
            "bayesian",
            "prior",
            "posterior",
            "bayes factor",
        ],
        "correlation, regression & causality": [
            "correlation",
            "regression",
            "confounding",
            "simpson",
            "causal inference",
            "collider",
            "selection bias",
            "observational",
            "odds ratio",
        ],
        "experimental design (within stats)": [
            "experimental design",
            "a/b testing",
            "randomization",
        ],
        "variance decomposition & ANOVA": [
            "variance decomposition",
            "anova",
            "f-statistic",
        ],
    },

    # -----------------------------------------------------------------------
    # ML Fundamentals — 29 canonical families
    # -----------------------------------------------------------------------
    "ml-fundamentals": {
        "BIAS-VARIANCE TRADEOFF": [
            "BIAS-VARIANCE",
            "BIAS",
            "VARIANCE",
        ],
        "OVERFITTING DIAGNOSIS": [
            "OVERFITTING",
            "UNDERFITTING",
            "TRAINING ACCURACY GAP",
        ],
        "REGULARIZATION EFFECT": [
            "REGULARIZATION",
            "L1",
            "L2",
            "DROPOUT",
            "EARLY STOPPING",
        ],
        "CROSS-VALIDATION DESIGN": [
            "CROSS-VALIDATION",
            "K-FOLD",
            "STRATIFIED",
            "TIME-SERIES CV",
            "NESTED CV",
        ],
        "DATA SPLITTING STRATEGY": [
            "DATA SPLITTING",
            "TRAIN/VAL/TEST",
            "HOLDOUT",
            "TEMPORAL SPLIT",
        ],
        "DATA LEAKAGE DETECTION": [
            "DATA LEAKAGE",
            "LEAKAGE",
            "TARGET LEAKAGE",
            "TRAIN-TEST CONTAMINATION",
        ],
        "CLASSIFICATION METRICS": [
            "CLASSIFICATION METRICS",
            "PRECISION",
            "RECALL",
            "F1",
            "AUC",
            "ROC",
            "PR CURVE",
        ],
        "REGRESSION METRICS": [
            "REGRESSION METRICS",
            "RMSE",
            "MAE",
            "MAPE",
            "R²",
            "R2",
        ],
        "CLASS IMBALANCE HANDLING": [
            "CLASS IMBALANCE",
            "SMOTE",
            "CLASS WEIGHTING",
            "RESAMPLING",
        ],
        "FEATURE SCALING NECESSITY": [
            "FEATURE SCALING",
            "STANDARDIZATION",
            "NORMALIZATION",
        ],
        "FEATURE SELECTION STRATEGY": [
            "FEATURE SELECTION",
            "FILTER",
            "WRAPPER",
            "EMBEDDED",
        ],
        "FEATURE IMPORTANCE INTERPRETATION": [
            "FEATURE IMPORTANCE",
            "PERMUTATION IMPORTANCE",
            "SHAP",
        ],
        "DIMENSIONALITY REDUCTION": [
            "DIMENSIONALITY REDUCTION",
            "PCA",
            "T-SNE",
            "UMAP",
        ],
        "MISSING DATA STRATEGY": [
            "MISSING DATA",
            "IMPUTATION",
            "MISSINGNESS AS SIGNAL",
        ],
        "ENSEMBLE STRATEGY": [
            "ENSEMBLE",
            "BAGGING",
            "BOOSTING",
            "STACKING",
        ],
        "BOOSTING MECHANICS": [
            "GRADIENT BOOSTING",
            "XGBOOST",
            "LIGHTGBM",
            "CATBOOST",
        ],
        "MODEL CALIBRATION": [
            "CALIBRATION",
            "PLATT SCALING",
            "ISOTONIC REGRESSION",
            "RELIABILITY DIAGRAM",
        ],
        "SUPERVISED VS UNSUPERVISED": [
            "SUPERVISED",
            "UNSUPERVISED",
            "SEMI-SUPERVISED",
            "SELF-SUPERVISED",
        ],
        "CLUSTERING EVALUATION": [
            "CLUSTERING",
            "SILHOUETTE",
            "INERTIA",
            "DAVIES-BOULDIN",
        ],
        "NEURAL NETWORK DESIGN": [
            "NEURAL NETWORK",
            "ARCHITECTURE",
            "DEPTH VS WIDTH",
            "ACTIVATION",
        ],
        "GRADIENT DESCENT BEHAVIOR": [
            "GRADIENT DESCENT",
            "SGD",
            "ADAM",
            "LEARNING RATE",
            "MOMENTUM",
        ],
        "GRADIENT PATHOLOGY": [
            "GRADIENT PATHOLOGY",
            "VANISHING GRADIENT",
            "EXPLODING GRADIENT",
            "DEAD RELU",
        ],
        "LOSS FUNCTION SELECTION": [
            "LOSS FUNCTION",
            "CROSS-ENTROPY",
            "MSE",
            "HUBER",
            "FOCAL LOSS",
        ],
        "HYPERPARAMETER SENSITIVITY": [
            "HYPERPARAMETER",
            "TUNING",
            "GRID SEARCH",
            "RANDOM SEARCH",
            "BAYESIAN OPTIMIZATION",
        ],
        "TRANSFER LEARNING STRATEGY": [
            "TRANSFER LEARNING",
            "PRETRAINED",
            "FINE-TUNING",
            "FROZEN LAYERS",
        ],
        "MODEL MONITORING": [
            "MODEL MONITORING",
            "DRIFT",
            "CONCEPT DRIFT",
            "DATA DRIFT",
            "FEATURE DRIFT",
        ],
        "TRAINING-SERVING SKEW": [
            "TRAINING-SERVING SKEW",
            "TRAIN-SERVE",
            "FEATURE PARITY",
        ],
        "DEPLOYMENT CONSTRAINTS": [
            "DEPLOYMENT",
            "LATENCY",
            "BATCH VS ONLINE",
            "EDGE",
        ],
        "INTERPRETABILITY TRADEOFF": [
            "INTERPRETABILITY",
            "EXPLAINABILITY",
            "BLACK BOX",
            "GLASS BOX",
        ],
    },

    # -----------------------------------------------------------------------
    # Experimentation — 22 canonical families
    # -----------------------------------------------------------------------
    "experimentation": {
        "EXPERIMENT DESIGN": [
            "EXPERIMENT DESIGN",
            "EXPERIMENTAL DESIGN",
            "RANDOMIZATION",
            "TREATMENT ASSIGNMENT",
            "BLOCKING",
        ],
        "HYPOTHESIS FORMULATION": [
            "HYPOTHESIS FORMULATION",
            "HYPOTHESIS",
            "NULL",
            "ALTERNATIVE",
        ],
        "METRIC SELECTION": [
            "METRIC SELECTION",
            "OEC",
            "NORTH STAR METRIC",
            "GUARDRAIL METRIC",
            "PROXY METRIC",
        ],
        "A/B TEST MECHANICS": [
            "A/B TEST MECHANICS",
            "TREATMENT",
            "CONTROL",
            "RANDOMIZATION UNIT",
        ],
        "STATISTICAL SIGNIFICANCE": [
            "STATISTICAL SIGNIFICANCE",
            "P-VALUE",
            "CONFIDENCE LEVEL",
        ],
        "STATISTICAL POWER": [
            "STATISTICAL POWER",
            "MDE",
            "MINIMUM DETECTABLE EFFECT",
            "POWER CALC",
        ],
        "TYPE I AND TYPE II ERRORS": [
            "TYPE I",
            "TYPE II",
            "FALSE POSITIVE",
            "FALSE NEGATIVE",
        ],
        "EXPERIMENT DURATION": [
            "EXPERIMENT DURATION",
            "SAMPLE SIZE CALC",
            "PEEKING",
        ],
        "CONFIDENCE INTERVALS": [
            "CONFIDENCE INTERVAL",
            "CI",
            "BOOTSTRAP INTERVAL",
        ],
        "SAMPLE RATIO MISMATCH": [
            "SAMPLE RATIO MISMATCH",
            "SRM",
            "TRAFFIC IMBALANCE",
        ],
        "VARIANCE REDUCTION": [
            "VARIANCE REDUCTION",
            "CUPED",
            "STRATIFICATION",
            "REGRESSION ADJUSTMENT",
        ],
        "NOVELTY EFFECTS": [
            "NOVELTY EFFECT",
            "PRIMACY EFFECT",
            "TEMPORAL EFFECT",
        ],
        "NETWORK EFFECTS": [
            "NETWORK EFFECT",
            "INTERFERENCE",
            "SUTVA VIOLATION",
            "PEER EFFECT",
        ],
        "SEGMENTATION ANALYSIS": [
            "SEGMENTATION ANALYSIS",
            "HETEROGENEOUS TREATMENT EFFECTS",
            "SUBGROUP",
        ],
        "MULTIPLE TESTING": [
            "MULTIPLE TESTING",
            "BONFERRONI",
            "FDR",
        ],
        "HOLDOUT GROUPS": [
            "HOLDOUT GROUPS",
            "LONG-TERM HOLDOUT",
        ],
        "SWITCHBACK EXPERIMENTS": [
            "SWITCHBACK",
            "TIME-BASED RANDOMIZATION",
        ],
        "MULTI-ARMED BANDIT": [
            "MULTI-ARMED BANDIT",
            "THOMPSON SAMPLING",
            "EPSILON-GREEDY",
        ],
        "BAYESIAN EXPERIMENTATION": [
            "BAYESIAN EXPERIMENTATION",
            "BAYESIAN A/B",
            "POSTERIOR PROBABILITY",
        ],
        "QUASI-EXPERIMENTAL METHODS": [
            "QUASI-EXPERIMENTAL",
            "DIFF-IN-DIFF",
            "REGRESSION DISCONTINUITY",
            "SYNTHETIC CONTROL",
        ],
        "CAUSAL INFERENCE": [
            "CAUSAL INFERENCE",
            "INSTRUMENTAL VARIABLES",
            "PROPENSITY SCORING",
            "POTENTIAL OUTCOMES",
        ],
        "SAMPLE SIZE BASICS": [
            "SAMPLE SIZE BASICS",
            "POWER VS SAMPLE SIZE",
        ],
    },
}


# ---------------------------------------------------------------------------
# Resolution functions (unchanged API; internals now use the taxonomy dict)
# ---------------------------------------------------------------------------

def resolve_to_family(concept: str, track: str) -> str:
    """Map a raw concept tag to its canonical family name for the given track.

    Tries exact then substring matching (case-insensitive) in family-registry
    order.  Returns the family name on match; returns the uppercased concept
    unchanged when no family is found (the validator will flag the miss).
    """
    concept_upper = concept.upper()
    for family_name, patterns in CONCEPT_FAMILIES.get(track, {}).items():
        for pattern in patterns:
            if pattern.upper() in concept_upper:
                return family_name
    return concept_upper


def concept_matches_focus(question_concept: str, focus_concept: str, q_track: str) -> bool:
    """Return True if *question_concept* belongs to the same family as *focus_concept*.

    Resolves both tags to their canonical families and compares.  Falls back to
    case-insensitive bidirectional substring matching when either tag has no
    registered family (e.g. a user-supplied free-text focus from an older session).
    """
    qc_family = resolve_to_family(question_concept, q_track)
    fc_family = resolve_to_family(focus_concept, q_track)

    # Both resolved to a known family — compare family names
    families = CONCEPT_FAMILIES.get(q_track, {})
    if qc_family in families and fc_family in families:
        return qc_family == fc_family

    # Fallback: bidirectional substring (handles unknown focus strings)
    qc_upper = question_concept.upper()
    fc_upper = focus_concept.upper()
    return fc_upper in qc_upper or qc_upper in fc_upper
