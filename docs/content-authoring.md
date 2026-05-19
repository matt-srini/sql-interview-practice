# Content Authoring

> **Navigation:** [Docs index](../README.md) · [Architecture](./architecture.md) · [Datasets](./datasets.md)

This is the authoritative guide for creating, editing, and reviewing questions on datathink. It covers the philosophy behind the question bank, the quality bar every question must clear, per-track authoring rules, and the exact JSON schemas the catalog loaders expect.

**New track onboarding:** See [`docs/track-onboarding.md`](./track-onboarding.md) for the complete phase-by-phase process (spec → backend → frontend → content → paths → docs). The AI agent prompt is at [`.github/agents/track-onboarding.agent.md`](../.github/agents/track-onboarding.agent.md).

**AI authoring agents** (use these when generating questions with Claude):
- [`.github/agents/question-authoring.agent.md`](../.github/agents/question-authoring.agent.md) — **universal authoring agent**: all 9 tracks, all difficulties, practice + mock-only, self-contained guardrails. Start here; use the per-track agents below only for deep schema specifics.
- [`.github/agents/sql-question-authoring.agent.md`](../.github/agents/sql-question-authoring.agent.md)
- [`.github/agents/python-question-authoring.agent.md`](../.github/agents/python-question-authoring.agent.md)
- [`.github/agents/pandas-question-authoring.agent.md`](../.github/agents/pandas-question-authoring.agent.md)
- [`.github/agents/pyspark-question-authoring.agent.md`](../.github/agents/pyspark-question-authoring.agent.md)
- [`.github/agents/data-engineering-question-authoring.agent.md`](../.github/agents/data-engineering-question-authoring.agent.md)
- [`.github/agents/data-modeling-question-authoring.agent.md`](../.github/agents/data-modeling-question-authoring.agent.md)
- [`.github/agents/statistics-question-authoring.agent.md`](../.github/agents/statistics-question-authoring.agent.md) — dual-subtype (conceptual MCQ + numerical Python)
- [`.github/agents/ml-fundamentals-question-authoring.agent.md`](../.github/agents/ml-fundamentals-question-authoring.agent.md)
- [`.github/agents/experimentation-question-authoring.agent.md`](../.github/agents/experimentation-question-authoring.agent.md)
- [`.github/agents/track-onboarding.agent.md`](../.github/agents/track-onboarding.agent.md) — drives any new track end-to-end

---

## Platform philosophy

datathink is **FAANG-level interview preparation**, not a syntax tutorial. The single test every question must pass:

> *Would a senior data interviewer at Meta, Google, Stripe, or Amazon ask this in a 45-minute screen?*

### What good questions do

- **Test reasoning depth, not syntax recall.** The candidate should have to think about *why* an approach works, not remember a keyword or function signature.
- **Mirror real business scenarios.** Queries and code that could appear in an actual analytics or engineering codebase — not contrived puzzles or academic exercises.
- **Teach a durable concept.** After solving it, the user understands *why* the approach works and can transfer that understanding to novel problems.
- **Progress logically.** Each difficulty tier builds on the previous one's mental models. The curriculum is a learning arc, not a random collection.

### What good questions avoid

- One-liners that test nothing beyond "did you memorize this function name"
- Academic toy problems with no connection to real data work
- Multiple valid interpretations of the expected output
- Redundant coverage: 3+ questions testing the same pattern with trivially different surface details
- Artificial difficulty from concept stacking (making a question hard by requiring 8 unrelated things)

### Difficulty comes from reasoning complexity, not syntactic obscurity

**Easy** → single-step logic, one clear concept, unambiguous expected output  
**Medium** → 2–3 related concepts, multi-step reasoning, recognizing which tool applies  
**Hard** → multi-stage dependent logic, trade-offs, edge-case awareness, production-grade thinking

---

## Question bank — current state

Practice questions are the full curriculum. Mock-only questions live in the same per-track JSON banks but are excluded from the practice catalog and used only in mock sessions.

| Track | Easy | Medium | Hard | Practice total | Format |
|---|---|---|---|---|---|
| SQL | 37 | 45 | 30 | **112** | SQL query, evaluated via DuckDB |
| Python | 39 | 32 | 24 | **95** | Function implementation, evaluated via test cases |
| Pandas | 27 | 36 | 23 | **86** | DataFrame function, evaluated via output comparison |
| PySpark | 41 | 39 | 26 | **106** | Predict-output / debug / scenario / option-based reasoning |
| Data Engineering | 30 | 33 | 23 | **86** | Scenario / debug / systems reasoning |
| Data Modeling | 25 | 28 | 23 | **76** | Modeling / design / scenario reasoning |
| Statistics | 31 | 41 | 25 | **97** | Dual-subtype: conceptual reasoning or numerical Python code |
| ML Fundamentals | 30 | 35 | 25 | **90** | Predict-output / debug / scenario / model reasoning |
| Experimentation | 30 | 30 | 20 | **80** | Experiment design / interpretation / causal reasoning |
| **Total** | **290** | **319** | **219** | **828** | |

Mock-only add-on bank: **165 questions total**. Samples remain **36 total** across SQL, Python, Pandas, and PySpark, while Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation sample rounds are auto-sliced from practice questions.

### Learning paths (curated sequences)

| Track | Paths | Distribution |
|---|---:|---|
| SQL | 9 | 2 free shortcut paths (`starter`, `intermediate`) + 7 advanced (mixed free/pro) |
| Python | 6 | 2 free shortcut paths (`starter`, `intermediate`) + 4 advanced (mixed free/pro) |
| Pandas | 5 | 2 free shortcut paths (`starter`, `intermediate`) + 3 advanced (mixed free/pro) |
| PySpark | 5 | 2 free shortcut paths (`starter`, `intermediate`) + 3 advanced (mixed free/pro) |
| Data Engineering | 2 | `starter` "Pipeline Fundamentals" (free) · `intermediate` "Advanced DE Systems" (pro) |
| Data Modeling | 4 | `starter` "Schema Design Basics" (free) · `intermediate` "Dimensional Modeling Deep Dive" (pro) · "Normalization & Referential Integrity" (free) · "dbt & Modern Analytics Modeling" (pro) |
| Statistics | 3 | `starter` "Stats for Analysts" (free) · `intermediate` "Experimental Design & Inference" (pro) + 1 advanced path |
| ML Fundamentals | 4 | `starter` "ML Fundamentals Starter" (free) · `intermediate` "Model Evaluation & Validation" (free) · "Production ML & Model Monitoring" (pro) · "Advanced ML Methods" (pro) |
| Experimentation | 4 | `starter` "Experimentation Starter" (free) · `intermediate` "Experiment Design & Power" (free) · "Variance Reduction & Behavioral Effects" (pro) · "Causal Inference & Advanced Experimentation" (pro) |
| **Total** | **42** | |

Authoring constraints for path files in `backend/content/paths/`:
- Required fields: `slug`, `title`, `description`, `topic`, `questions`, `tier`, `role`
- `topic` must be one of: `sql`, `python`, `python-data`, `pyspark`, `data-engineering`, `data-modeling`, `statistics`, `ml-fundamentals`, `experimentation`
- `tier` must be `free` or `pro`
- `role` must be `starter`, `intermediate`, or `advanced`
- Exactly one `starter` and one `intermediate` path per track (used by unlock shortcuts)
- Every `questions[]` ID must exist in the same track catalog and be unique within the path

**Recommended additional fields (all paths should include these):**

| Field | Type | Purpose |
|---|---|---|
| `focus_concepts` | `string[]` | 2–4 semantic concept tags this path trains. Must match the concept-tag style in `docs/content-authoring.md` (not raw syntax/API names). Used by the insights engine to route users from weak concepts to the right path. |
| `outcomes` | `string` | One or two sentences starting with "You'll…" describing what the user will be able to do after completing this path. Shown in the UI as a learning objective. |
| `recommended_after` | `string[]` | Slugs of paths that are good prerequisites. Empty array `[]` for starter paths. Used by the recommendation engine to respect curriculum order. |

**Authoring rules for `focus_concepts`:**
- Use the same semantic-tag style as question `concepts` fields (e.g. `GROUPED AGGREGATION`, not `GROUP BY`)
- Pick concepts that the majority of questions in the path actually train
- 2–4 concepts per path; don't list every concept that appears — only the defining ones
- The insights engine maps `weakest_concepts` → `recommended_path_slug` by matching these tags, so accuracy matters

**Authoring rules for `outcomes`:**
- Start with "You'll…" (first-person, active voice)
- Describe capability, not activity ("You'll analyze cohorts" not "This path covers cohorts")
- Keep it to 1–2 sentences max

---

## Concept coverage by track

### SQL — concepts covered

| Tier | Concepts |
|---|---|
| Easy | SELECT / WHERE / ORDER BY, DISTINCT, basic aggregation (COUNT/SUM/AVG/MIN/MAX), single GROUP BY, INNER JOIN (1 table), IS NULL / IS NOT NULL, COALESCE, STRFTIME / date bucketing, half-open date intervals, IN / BETWEEN / LIKE, multi-column GROUP BY, CTE intro (WITH clause) |
| Medium | Multi-table JOINs (2–4 tables), LEFT JOIN direction, FULL OUTER JOIN, GROUP BY + HAVING, conditional aggregation (CASE WHEN), scalar / IN / EXISTS subqueries, LAG window function (delta between rows), QoQ analysis, date arithmetic, 3-table WHERE+HAVING pipelines |
| Hard | ROW_NUMBER / RANK / DENSE_RANK, LAG / LEAD, SUM OVER / running totals, ROWS vs RANGE frame semantics, multi-CTE pipelines, correlated subqueries, sessionization, cohort retention, funnel with date-range JOIN, Pareto analysis, state machine detection, deduplication / latest-state derivation |

### Python — concepts covered

| Tier | Concepts |
|---|---|
| Easy | Hash map (two-sum pattern), two pointers, sets for deduplication, string manipulation, sorting, stack (balanced brackets), recursion basics, binary search (intro) |
| Medium | Sliding window (fixed + variable), prefix sums, binary search (advanced), heap / priority queue, BFS/DFS (matrix/graph), 1D dynamic programming, backtracking (permutations), deque / monotonic queue, bit manipulation, Task Scheduler (greedy), anagram detection, topological trimming |
| Hard | 2D dynamic programming, memoization, Trie (insert/search/startsWith), Union-Find with path compression, Dijkstra (shortest path), k-way merge with min-heap, DFS + backtracking (word search), LRU Cache, median from stream (dual heap), topological sort, interval scheduling |

### Pandas — concepts covered

| Tier | Concepts |
|---|---|
| Easy | Boolean indexing, `str` accessor (`str.split`, `str.contains`, `str.extract`), `pd.cut` / binning, `dt` accessor, `dropna`, `sort_values`, `groupby.size` / `value_counts`, named aggregation (basic), `reset_index`, email domain extraction |
| Medium | `merge` / join types, `pivot_table`, `groupby.transform`, `rolling` windows, `resample` (time series), `rank(pct=True)`, named aggregation (advanced), multi-condition operations, retention rate with `groupby.apply` |
| Hard | `MultiIndex` + `.xs()`, dtype / memory optimization (`astype`, `category` dtype), `memory_usage(deep=True)`, `groupby.apply` with custom functions, cohort analysis, RFM segmentation, funnel analysis with set operations |

### PySpark — concepts covered

| Tier | Concepts |
|---|---|
| Easy | Transformations vs actions, lazy evaluation, DAG, RDD vs DataFrame, driver role, `withColumn`, `filter` / `count` order, `cache()` laziness, `len(df)` TypeError, `collect()` OOM risk, UDF return type mismatch, Catalyst predicate pushdown, narrow vs wide transforms |
| Medium | Partitioning, `repartition` vs `coalesce`, shuffle triggers, broadcast join thresholds, PySpark window function API, Delta Lake MERGE (upsert), Delta time travel, schema evolution / enforcement, Structured Streaming output modes (append / update / complete), streaming trigger intervals |
| Hard | AQE (all 3 optimizations), dynamic partition pruning, skew join / salting, pandas UDF memory model, Z-ordering vs partition pruning, watermark and late data drop behavior, speculative execution |

### Data Engineering — concepts covered

| Tier | Concepts |
|---|---|
| Easy | ETL vs ELT (transformation placement), idempotency (safe reruns), basic DAG orchestration (task dependencies, triggers), batch vs streaming fundamentals, partitioning & predicate pushdown, SCD types 1/2/3 basics, data lake vs warehouse vs lakehouse, CDC introduction, data quality assertions, forward/backward schema compatibility, at-least-once vs at-most-once delivery, SLA definition |
| Medium | Forward/backward schema compatibility tradeoffs, Avro schema evolution, batch vs streaming latency tradeoffs, micro-batching, watermarks and late-data handling, state store sizing, data quality monitoring (anomaly detection, row count checks), exactly-once vs at-least-once, idempotent writes, backfill idempotency, partitioned backfill, data skew, columnar vs row-based formats, small-file problem, log-based vs query-based CDC, data freshness observability, cost of scans vs storage |
| Hard | Exactly-once semantics (idempotent writes + transactional sources), incident response (cascading failures, replay, root cause), data lineage for debugging, SCD Type 4, schema breaking changes (required-field addition, type changes), columnar scan cost reduction, partition granularity vs cost tradeoffs, allowed lateness vs watermarks, session windows with late data, lakehouse vs warehouse for mixed workloads, hot vs cold storage tiers, anomaly-detection false-alert risk |

**Concept families for `data-engineering` (used in `concept_families.py`):**

`ETL VS ELT` · `IDEMPOTENCY` · `BACKFILL DESIGN` · `ORCHESTRATION` · `SCHEDULING & SLAS` · `SCHEMA EVOLUTION` · `BATCH VS STREAMING` · `WATERMARKING` · `DELIVERY SEMANTICS` · `PARTITIONING & PRUNING` · `STORAGE LAYOUT & FILE FORMATS` · `CDC & INGESTION` · `DATA QUALITY` · `LINEAGE & OBSERVABILITY` · `SCD OPERATIONS` · `STORAGE ARCHITECTURE` · `COST OPTIMIZATION` · `INCIDENT RESPONSE` · `DATA CONTRACT`

**Concept blocklist for `data-engineering`** (too implementation-specific — validator rejects these as concept tags):
`airflow`, `spark`, `kafka`, `flink`, `dbt`, `s3`, `glue`, `task`, `operator`, `sensor`, `trigger`, `pipeline`, `etl`, `elt`, `cron`

**First-hint leak patterns for `data-engineering`** (forbidden in first hint):
`idempoten*`, `watermark*`, `exactly-once`, `SCD`, `change data capture`, `backfill`, `at-least-once`, `at-most-once`

### Data Modeling — concepts covered

| Tier | Concepts |
|---|---|
| Easy | Star vs snowflake schemas, 1NF/2NF/3NF normalization, fact table types (transaction/periodic snapshot/accumulating snapshot), surrogate vs natural keys, SCD Type 1 vs 2 basics, OLTP vs OLAP distinction, grain definition, bridge tables intro, degenerate dimensions, role-playing dimensions intro, junk dimensions, additive vs semi-additive vs non-additive measures |
| Medium | Grain choice under ambiguity, SCD Type 2 vs 3 tradeoffs, SCD Type 4, bridge table design for many-to-many, conformed vs role-playing dimensions, wide vs normalized models, Data Vault (hub/link/satellite), outrigger tables, late-arriving facts/dimensions, schema design from business requirements, additive facts with multi-currency, factless fact tables |
| Hard | Multi-hop grain alignment, SCD choice under conflicting business requirements, Data Vault vs Kimball tradeoffs, conformed dimension governance across business units, slowly-changing hierarchies, heterogeneous products (one fact table multiple grains), real-time DWH design, schema evolution strategy, hybrid normalized/denormalized design, partitioning strategy for DWH |

**Concept families for `data-modeling`** (used in concept pills and insights engine):

`DIMENSIONAL MODELING` · `NORMALIZATION` · `DENORMALIZATION TRADEOFF` · `FACT TABLE DESIGN` · `DIMENSION DESIGN` · `SURROGATE VS NATURAL KEYS` · `SCD STRUCTURE` · `GRAIN DEFINITION` · `BRIDGE & MANY-TO-MANY` · `SCHEMA FROM REQUIREMENTS` · `STORAGE ARCHITECTURE TRADEOFFS` · `DATA VAULT` · `WIDE VS NARROW` · `OLTP VS OLAP` · `MEASURE ADDITIVITY` · `ROLE-PLAYING DIMENSIONS` · `CONFORMED DIMENSIONS` · `SCHEMA EVOLUTION` · `BI-TEMPORAL MODELING`

**Concept blocklist for `data-modeling`** (too implementation-specific — validator rejects these as concept tags):
`star schema`, `snowflake schema`, `fact table`, `dimension table`, `foreign key`, `primary key`, `scd`, `surrogate key`, `natural key`, `dbt`, `hub`, `link`, `satellite`

**First-hint leak patterns for `data-modeling`** (forbidden in first hint):
`star schema`, `snowflake schema`, `slowly changing`, `SCD type`, `surrogate key`, `data vault`, `grain`, `conformed dimension`

### Statistics — concepts covered

This is a **dual-subtype** track. Each question has `"subtype": "conceptual"` (MCQ) or `"subtype": "numerical"` (Python code). The same concept families apply to both subtypes.

| Tier | Mix | Concepts |
|---|---|---|
| Easy (~70% conceptual / ~30% numerical) | Descriptive statistics (mean, median, mode, IQR, std dev), probability basics (sample space, union/intersection/complement), conditional probability, independence, expected value, Bernoulli/binomial basics, normal distribution, z-scores, 68-95-99.7 rule, basic combinatorics (permutations, combinations) |
| Medium (~60% conceptual / ~40% numerical) | Central Limit Theorem, sampling distributions, confidence intervals for means, hypothesis testing basics (null hypothesis, p-value, significance level), Type I and Type II errors, statistical power, t vs z distributions, correlation vs causation, A/B testing setup, sample size estimation, Bayesian vs frequentist reasoning, Law of Large Numbers, Poisson distribution |
| Hard (~50% conceptual / ~50% numerical) | Bayesian posterior calculation, multiple comparisons and Bonferroni correction, Simpson's paradox, power analysis and effect size (Cohen's d), regression (R-squared, bias-variance tradeoff), bootstrap and resampling, maximum likelihood estimation, chi-squared tests, ANOVA, survival analysis basics, variance decomposition |

**Concept families for `statistics`** (used in concept pills and insights engine):

`DESCRIPTIVE STATISTICS` · `PROBABILITY BASICS` · `CONDITIONAL PROBABILITY` · `EXPECTED VALUE` · `DISTRIBUTIONS` · `NORMAL DISTRIBUTION` · `HYPOTHESIS TESTING` · `CONFIDENCE INTERVALS` · `TYPE I AND TYPE II ERRORS` · `STATISTICAL POWER` · `A/B TESTING` · `CENTRAL LIMIT THEOREM` · `BAYESIAN REASONING` · `CORRELATION VS CAUSATION` · `REGRESSION` · `RESAMPLING METHODS` · `MULTIPLE COMPARISONS` · `ANOVA` · `VARIANCE DECOMPOSITION` · `NON-PARAMETRIC TESTS` · `LOGISTIC REGRESSION` · `CAUSAL INFERENCE` · `RESIDUAL DIAGNOSTICS`

**Concept blocklist for `statistics`** (too implementation-specific — validator rejects these):
`mean`, `median`, `variance`, `standard deviation`, `p-value`, `t-test`, `chi-squared`, `z-score`, `normal distribution`, `binomial distribution`, `scipy`, `numpy`, `statsmodels`, `r-squared`, `pearson`, `spearman`

**First-hint leak patterns for `statistics`** (forbidden in first hint):
`p-value`, `null hypothesis`, `central limit theorem`, `confidence interval`, `bayesian`, `type I error`, `type II error`, `statistical power`, `simpson's paradox`

**Schema rules for statistics question JSON:**
- All questions: `id`, `order`, `title`, `difficulty`, `type`, `subtype`, `description`, `hints`, `concepts`
- Conceptual only: `options` (4 strings, each ≥ 20 chars), `correct_option` (int 0–3), `explanation`
- Numerical only: `starter_code` (function stub), `expected_code` (full working implementation), `test_cases` (list of `{"input": [], "expected_output": value}`), `explanation`
- Allowed imports for numerical code: `math`, `statistics`, `numpy`, `random`, `collections`, `itertools`, `functools`, `decimal`, `fractions`, `operator`, `typing`
- `type` field: use `"mcq"` for conceptual, `"numerical"` for numerical
- ID ranges: easy 71001–71028, medium 72001–72028, hard 73001–73024

### ML Fundamentals — concepts covered

| Tier | Concepts |
|---|---|
| Easy | SUPERVISED VS UNSUPERVISED, OVERFITTING DIAGNOSIS, BIAS-VARIANCE TRADEOFF, DATA SPLITTING STRATEGY, FEATURE SCALING NECESSITY, CROSS-VALIDATION DESIGN, CLASSIFICATION METRICS, REGRESSION METRICS, LOSS FUNCTION SELECTION, GRADIENT DESCENT BEHAVIOR, REGULARIZATION EFFECT |
| Medium | ENSEMBLE STRATEGY, CLASS IMBALANCE HANDLING, DIMENSIONALITY REDUCTION, FEATURE IMPORTANCE INTERPRETATION, MODEL CALIBRATION, FEATURE SELECTION STRATEGY, MISSING DATA STRATEGY, HYPERPARAMETER SENSITIVITY, BOOSTING MECHANICS, CLUSTERING EVALUATION, DATA LEAKAGE DETECTION |
| Hard | NEURAL NETWORK DESIGN, GRADIENT PATHOLOGY, TRANSFER LEARNING STRATEGY, MODEL MONITORING, DEPLOYMENT CONSTRAINTS, INTERPRETABILITY TRADEOFF, TRAINING-SERVING SKEW |

**Concept families for `ml-fundamentals`** (used in concept pills and insights engine):

`SUPERVISED VS UNSUPERVISED` · `OVERFITTING DIAGNOSIS` · `BIAS-VARIANCE TRADEOFF` · `DATA SPLITTING STRATEGY` · `FEATURE SCALING NECESSITY` · `CROSS-VALIDATION DESIGN` · `CLASSIFICATION METRICS` · `REGRESSION METRICS` · `LOSS FUNCTION SELECTION` · `GRADIENT DESCENT BEHAVIOR` · `REGULARIZATION EFFECT` · `ENSEMBLE STRATEGY` · `CLASS IMBALANCE HANDLING` · `DIMENSIONALITY REDUCTION` · `FEATURE IMPORTANCE INTERPRETATION` · `MODEL CALIBRATION` · `FEATURE SELECTION STRATEGY` · `MISSING DATA STRATEGY` · `HYPERPARAMETER SENSITIVITY` · `BOOSTING MECHANICS` · `CLUSTERING EVALUATION` · `DATA LEAKAGE DETECTION` · `NEURAL NETWORK DESIGN` · `GRADIENT PATHOLOGY` · `TRANSFER LEARNING STRATEGY` · `MODEL MONITORING` · `DEPLOYMENT CONSTRAINTS` · `INTERPRETABILITY TRADEOFF` · `TRAINING-SERVING SKEW`

**Concept blocklist for `ml-fundamentals`** (too implementation-specific — validator rejects these as concept tags):
`sklearn`, `tensorflow`, `pytorch`, `keras`, `xgboost`, `lightgbm`, `catboost`, `random_forest`, `svm`, `pca`, `kmeans`, `adam`, `sgd`, `relu`, `sigmoid`, `softmax`, `dropout`, `batchnorm`, `rmsprop`, `tanh`, `fit`, `predict`, `transform`, `pipeline`, `cross_val_score`, `gridsearchcv`, `randomizedsearchcv`, `roc_auc_score`, `f1_score`, `recall_score`, `precision_score`, `logistic_regression`, `tsne`, `umap`

**First-hint leak patterns for `ml-fundamentals`** (forbidden in first hint):
`bias-variance`, `overfitting`, `underfitting`, `regularization`, `cross-validation`, `gradient descent`, `ensemble`, `boosting`, `bagging`, `data leakage`, `concept drift`, `training-serving skew`, `calibration`, `SMOTE`, `SHAP`

**Schema rules for ML Fundamentals question JSON:**
- All questions: `id`, `order`, `topic`, `type`, `difficulty`, `title`, `description`, `options` (4 strings), `correct_option` (int 0–3), `explanation`, `hints`, `concepts`
- Optional: `code_snippet` (string, shown in monospace above options), `scenario_context` (string, shown as lead-in paragraph), `mock_only` (bool, default false)
- Allowed `type` values: `"mcq"`, `"scenario"`, `"predict_output"`, `"debug"`
- ID ranges: easy 81001–81030 (practice), medium 82001–82035 (practice) + 82036–82047 (mock), hard 83001–83025 (practice) + 83026–83038 (mock)

### Experimentation — concepts covered

| Tier | Concepts |
|---|---|
| Easy | EXPERIMENT DESIGN, HYPOTHESIS FORMULATION, STATISTICAL SIGNIFICANCE, TYPE I AND TYPE II ERRORS, METRIC SELECTION, A/B TEST MECHANICS, STATISTICAL POWER, CONFIDENCE INTERVALS, SAMPLE SIZE BASICS |
| Medium | MULTIPLE TESTING, SAMPLE RATIO MISMATCH, NOVELTY EFFECTS, STATISTICAL POWER, VARIANCE REDUCTION, NETWORK EFFECTS, SEGMENTATION ANALYSIS, EXPERIMENT DURATION, METRIC SELECTION |
| Hard | CAUSAL INFERENCE, SWITCHBACK EXPERIMENTS, BAYESIAN EXPERIMENTATION, MULTI-ARMED BANDIT, HOLDOUT GROUPS, NETWORK EFFECTS, QUASI-EXPERIMENTAL METHODS, VARIANCE REDUCTION |

**Concept families for `experimentation`** (used in concept pills and insights engine):

`EXPERIMENT DESIGN` · `HYPOTHESIS FORMULATION` · `STATISTICAL SIGNIFICANCE` · `TYPE I AND TYPE II ERRORS` · `METRIC SELECTION` · `A/B TEST MECHANICS` · `STATISTICAL POWER` · `CONFIDENCE INTERVALS` · `SAMPLE SIZE BASICS` · `MULTIPLE TESTING` · `SAMPLE RATIO MISMATCH` · `NOVELTY EFFECTS` · `NETWORK EFFECTS` · `VARIANCE REDUCTION` · `SEGMENTATION ANALYSIS` · `EXPERIMENT DURATION` · `CAUSAL INFERENCE` · `BAYESIAN EXPERIMENTATION` · `SWITCHBACK EXPERIMENTS` · `MULTI-ARMED BANDIT` · `HOLDOUT GROUPS` · `QUASI-EXPERIMENTAL METHODS`

**Concept blocklist for `experimentation`** (too vague or belongs in Statistics track — validator rejects these as concept tags):
`a/b test`, `control group`, `treatment group`, `randomization`, `p-value`, `null hypothesis`, `alpha`, `beta`, `bootstrap`, `permutation test`, `z-test`, `t-test`, `chi-square`, `sample size`, `significance`

**First-hint leak patterns for `experimentation`** (forbidden in first hint):
`cuped`, `sample ratio mismatch`, `bonferroni`, `benjamini-hochberg`, `holm`, `switchback`, `difference-in-differences`, `regression discontinuity`, `thompson sampling`, `novelty effect`, `sutva`

**Schema rules for Experimentation question JSON:**
- All questions: `id`, `order`, `topic`, `type`, `difficulty`, `title`, `description`, `options` (4 strings), `correct_option` (int 0–3), `explanation`, `hints`, `concepts`
- Optional: `code_snippet` (string), `scenario_context` (string), `mock_only` (bool, default false)
- Allowed `type` values: `"mcq"`, `"scenario"`, `"predict_output"`, `"debug"`
- Hint counts: easy = 1, medium = 2, hard = 2
- ID ranges: easy 91001–91030 (practice), medium 92001–92030 (practice) + 92031–92042 (mock), hard 93001–93020 (practice) + 93021–93033 (mock)

---

## Question ID & Numbering Strategy (authoritative — no deviation)

This is the single authoritative source for the `TXNNN` ID scheme. Every track, every question, every phase of content authoring obeys it. Where any other document, plan file, or older note conflicts, **this section wins.**

### Scheme: `TXNNN` (5 digits)

```
T   = track digit (1–9)
X   = difficulty digit (1=easy, 2=medium, 3=hard)
NNN = sequence within that difficulty (001–999)
```

Examples: `11005` = SQL easy #5 · `42017` = PySpark medium #17 · `53004` = Data Engineering hard #4.

### Track assignments

| Track | T | Easy range | Medium range | Hard range |
|---|---|---|---|---|
| SQL | 1 | 11001–11999 | 12001–12999 | 13001–13999 |
| Python | 2 | 21001–21999 | 22001–22999 | 23001–23999 |
| Pandas | 3 | 31001–31999 | 32001–32999 | 33001–33999 |
| PySpark | 4 | 41001–41999 | 42001–42999 | 43001–43999 |
| Data Engineering | 5 | 51001–51999 | 52001–52999 | 53001–53999 |
| Data Modeling | 6 | 61001–61999 | 62001–62999 | 63001–63999 |
| Statistics | 7 | 71001–71999 | 72001–72999 | 73001–73999 |
| ML Fundamentals | 8 | 81001–81999 | 82001–82999 | 83001–83999 |
| Experimentation | 9 | 91001–91999 | 92001–92999 | 93001–93999 |

All T digits 1–9 are now allocated. New tracks beyond T9 are not yet spec'd — revisit the T assignment table when that time comes.

### Practice vs mock-only allocation

Practice and `mock_only: true` questions **share the same `TXNNN` space within each difficulty file**. Mock-only questions are allocated at the **top of each difficulty range**, immediately after the last practice question — never separately numbered. No mock-only questions exist at easy for any track (by design: easy is practice-only).

Verified current allocation for existing tracks:

| Track | Easy | Medium (practice · mock) | Hard (practice · mock) |
|---|---|---|---|
| SQL | 11001–11032 (32p) | 12001–12034 (34p) · 12035–12053 (19m) | 13001–13029 (29p) · 13030–13043 (14m) |
| Python | 21001–21030 (30p) | 22001–22029 (29p) · 22030–22037 (8m) | 23001–23024 (24p) · 23025–23036 (12m) |
| Pandas | 31001–31022 (22p) | 32001–32031 (31p) · 32032–32041 (10m) | 33001–33023 (23p) · 33024–33037 (14m) |
| PySpark | 41001–41038 (38p) | 42001–42038 (38p) · 42039–42048 (10m) | 43001–43026 (26p) · 43027–43036 (10m) |
| ML Fundamentals | 81001–81030 (30p) | 82001–82035 (35p) · 82036–82047 (12m) | 83001–83025 (25p) · 83026–83038 (13m) |
| Experimentation | 91001–91030 (30p) | 92001–92030 (30p) · 92031–92042 (12m) | 93001–93020 (20p) · 93021–93033 (13m) |
| Data Modeling | 61001–61025 (25p) | 62001–62025 (25p) | 63001–63020 (20p) · 63021 (1m) |
| Data Engineering | 51001–51030 (30p) | 52001–52030 (30p) | 53001–53020 (20p) · 53021 (1m) |
| Statistics | 71001–71031 (31p) | 72001–72041 (41p) | 73001–73025 (25p) · 73026–73033 (8m) |

### SQL sample IDs (3-digit, SQL only)

SQL sample questions use a compact `TXS` format (S=1–3): `111–113` easy · `121–123` medium · `131–133` hard. Defined in `backend/sample_questions.py`. Designed never to collide with 5-digit practice IDs.

**Non-SQL tracks have no separate sample files or sample IDs.** `get_topic_sample_pool()` in `backend/sample_questions.py` serves samples by slicing the **first 3 practice questions by `order`** from the live catalog. For Data Engineering, Data Modeling, and Statistics: do not author dedicated sample questions and do not allocate sample IDs. The sample endpoint is satisfied automatically once the catalog has at least 3 questions per difficulty.

### `schemas.json`-first rule

Each track's `schemas.json` defines valid `id_ranges`; the catalog loader validates every ID at startup and **crashes on violation**. `schemas.json` must be created before any question file is added to a new track. The JSON files are the runtime truth; this doc reflects them. Locations: `backend/content/questions/schemas.json`, `…/python_questions/schemas.json`, `…/python_data_questions/schemas.json`, `…/pyspark_questions/schemas.json`.

### Ordering vs ID

The `order` field controls pedagogical sequence (sidebar order; slice samples are drawn from it) and is **independent of the ID**. IDs were originally assigned by sorting on `order` then numbering sequentially, so today they align — but this is not guaranteed as questions are inserted mid-sequence.

**Rule: assign IDs by appending to the end of the difficulty range. Never re-align ID gaps to `order` gaps.** Renumbering is forbidden — it breaks `submissions`, `user_progress`, `follow_up_id`, and learning-path arrays.

### No-overlap guarantee

`TXNNN` guarantees zero overlap across tracks and difficulties by construction. Adding a track is purely "take the next free T digit." 3-digit SQL samples (111–133) never collide with 5-digit IDs.

### Duplicate ID check

**IDs must be globally unique across all question files.** Before committing any question:
```bash
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    all_ids.extend(q['id'] for q in json.load(open(f)))
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"
```

---

## Hint guidelines (all tracks)

Hints guide thinking toward the correct approach without revealing it. The current bank ranges from 1 to 3 hints per question; new or rewritten content should follow the active ladder below instead of treating hints as free-form notes.

| Difficulty | Target hint count | Hint ladder |
|---|---|---|
| Easy | 2 | Hint 1 identifies the mental model or operation class. Hint 2 points to the concrete tool or transformation family. |
| Medium | 2-3 | Hint 1 identifies the core pattern. Hint 2 identifies the subproblem split or intermediate representation. Hint 3 names the tool or control-flow shape only if the problem genuinely needs it. |
| Hard | 2-3 | Hint 1 identifies the decomposition strategy. Hint 2 identifies dependency ordering, state representation, or the bottleneck to isolate. Hint 3 points to final assembly or the constraint that commonly breaks solutions. |

### Minimum counts by track

| Track | Easy | Medium | Hard |
|---|---|---|---|
| SQL | 2 | 2-3 | 2-3 |
| Python | 2 | 2-3 | 2-3 |
| Pandas | 2 | 2-3 | 2-3 |
| PySpark | 1-2 | 2-3 | 2-3 |
| Data Engineering | 1-2 | 2-3 | 2-3 |
| Data Modeling | 1-2 | 2-3 | 2-3 |

PySpark, Data Engineering, and Data Modeling easy are the only allowed single-hint exceptions. Those questions are fast concept checks, so one strong execution-oriented hint is acceptable as long as the UI does not pretend there is a multi-step ladder.

**Good hint:** "Use a hash map to look up previously seen values in O(1) as you iterate"  
**Bad hint:** "Use a dictionary where the key is the number and value is its index"

Good hints name the *class of tool* or *direction of reasoning*. Bad hints describe the implementation.

Track-specific guidance:

- SQL: point to the clause family or intermediate result shape, not the exact clause text to type.
- Python: avoid naming the exact data structure in the first hint unless the entire learning objective is choosing that structure.
- Pandas: prefer the transformation pattern over leaking the exact method chain immediately.
- PySpark: focus on execution reasoning, plan consequences, or distractor elimination rather than answer restatement.

### Hint anti-patterns

- Do not make hint 1 read like the first line of the solution.
- Do not paste code fragments, method chains, or exact clause text into hint 1.
- Do not make hint 2 a disguised answer key by naming every required operation in order.
- For PySpark MCQs, do not restate the correct option; hint through elimination logic or execution behavior instead.

---

## Concept tags (all tracks)

The `concepts` field is a **learner-facing semantic tag** describing the *analytical or algorithmic pattern*, not the raw API primitive.

Treat `concepts` as the shared language for three user-facing systems:

- question-level concept pills
- weak-spot insights on dashboard and mock summary
- future path and drill recommendations

If a tag would read like parser jargon, library syntax, or method lookup help, it is too low-level.

| Track | Good tags | Bad tags |
|---|---|---|
| SQL | `RUNNING TOTAL THRESHOLD`, `COHORT RETENTION`, `LATEST STATE DERIVATION`, `FUNNEL COMPLETION RATE` | `JOIN`, `GROUP BY`, `WINDOW FUNCTION`, `ROW_NUMBER` |
| Python | `sliding window with constraint`, `graph shortest path`, `two-pointer shrink` | `for loop`, `dict`, `heapq` |
| Pandas | `time-series bucketing`, `percentile rank`, `multi-level aggregation` | `groupby`, `merge`, `resample` |
| PySpark | `lazy evaluation`, `shuffle boundary detection`, `delta lake upsert` | `filter()`, `repartition()`, `MERGE` |

Target 2–4 tags per question. 5 is acceptable only when a hard question genuinely teaches multiple dependent patterns.

### Concept tag rules

- Prefer *problem patterns* over *tool names*.
- Prefer *what the learner is reasoning about* over *what function they happen to type*.
- Tags should still make sense if the same problem were solved in a different syntax or library.
- Tags must be distinct. Do not include near-duplicates like `JOIN` and `INNER JOIN` or `groupby` and `aggregation` unless they truly describe different mental models.
- Do not use onboarding/meta tags like `CTE INTRODUCTION`, `WITH CLAUSE SYNTAX`, or `NAMED TEMPORARY RESULT SET`.

### Track-specific anti-patterns

- SQL: avoid raw clause/function tags such as `SELECT`, `WHERE`, `GROUP BY`, `HAVING`, `JOIN`, `COUNT`, `ROW_NUMBER`, `LAG`, `LEAD`.
- Python: avoid raw implementation nouns such as `dict`, `set`, `heapq`, `for loop`, `array`, `string`, `iteration` when they are not framed as a reasoning pattern.
- Pandas: avoid method names such as `groupby`, `merge`, `dropna`, `fillna`, `sort_values`, `resample`, `pivot_table`, `str.split`.
- PySpark: avoid API/operator names such as `filter()`, `repartition()`, `withColumn`, `collect()`, `cache()`, `MERGE`.

### Quick test

Ask this before saving a tag:

> If the user saw this tag in a weak-spot insight, would it teach them *what kind of thinking to improve*?

If the answer is no, rewrite it.

---

---

# SQL Track

---

## Difficulty standards

### Easy (11001–11999)
Single-step logic. One core concept, at most two if tightly related (e.g., WHERE + IS NULL).

**Allowed:** SELECT, WHERE (AND/OR/IN/BETWEEN/LIKE), ORDER BY, DISTINCT, basic aggregation, single GROUP BY, simple INNER JOIN (max 1), IS NULL / IS NOT NULL, COALESCE, STRFTIME / date formatting, CTE (intro-level — one CTE wrapping a simple query).

**Not allowed:** Window functions, correlated subqueries, HAVING, multi-table joins.

### Medium (12001–12999)
2–3 related concepts. Complexity comes from multi-step reasoning, not from bolting together unrelated SQL features.

**Allowed:** Multi-table INNER + LEFT JOINs (2–4 tables), FULL OUTER JOIN, GROUP BY + HAVING, CASE WHEN, scalar/IN/EXISTS subqueries, LAG (one-step delta), date arithmetic, multi-column GROUP BY.

**Not allowed:** Full window function suites, recursive CTEs, complex multi-CTE pipelines.

### Hard (13001–13999)
Must require at least 2 dependent steps. At least one of: window functions (ROW_NUMBER, RANK, LAG, LEAD, SUM OVER, ROWS/RANGE), multi-CTE pipelines, correlated subqueries, advanced aggregation patterns.

Hard questions should feel like a real FAANG analytics problem: sessionization, cohort retention, funnel analysis, Pareto, state machine detection, running totals with conditions.

---

## SQL JSON schema

```json
{
  "id": 11023,
  "order": 23,
  "title": "Active users by country",
  "difficulty": "easy",
  "description": "Return each country and the count of active users in that country as `user_count`. Only include users where `is_active = true`. Order by `user_count` DESC, then `country` ASC.",
  "dataset_files": ["users.csv"],
  "schema": {
    "users": ["user_id", "name", "email", "signup_date", "country", "acquisition_channel", "plan_tier", "is_active"]
  },
  "expected_query": "SELECT country, COUNT(*) AS user_count\nFROM users\nWHERE is_active = true\nGROUP BY country\nORDER BY user_count DESC, country ASC",
  "solution_query": "SELECT country,\n       COUNT(*) AS user_count\nFROM users\nWHERE is_active = true\nGROUP BY country\nORDER BY user_count DESC, country ASC;",
  "explanation": "Filter rows to active users first with WHERE. Then GROUP BY country to aggregate, counting rows per group. ORDER BY user_count DESC puts the largest countries first; the secondary country ASC makes ties deterministic.",
  "hints": [
    "Filter with WHERE before aggregating — don't use HAVING here, since HAVING filters after aggregation",
    "ORDER BY two columns: primary sort on count, tie-breaker on country"
  ],
  "concepts": ["CONDITIONAL FILTERING BEFORE AGGREGATION", "MULTI-COLUMN SORT"],
  "companies": ["Meta", "Stripe"],
  "required_concepts": ["group_by", "where", "order_by"],
  "enforce_concepts": true
}
```

**Field notes:**
- `expected_query` — used for evaluation (must be exactly correct and deterministic)
- `solution_query` — shown to the user after a correct submission; can be more readable/commented
- `schema` — must match the actual CSV headers exactly (validated at startup)
- `companies` — optional; canonical values: Meta, Google, Amazon, Stripe, Airbnb, Netflix, Uber, Microsoft, LinkedIn, Shopify, eBay, PayPal, Salesforce, Zendesk, Amplitude
- `required_concepts` / `enforce_concepts` — powers structure-check feedback; only add when the question specifically teaches that concept

---

## SQL style rules

- **DuckDB-native platform.** All SQL runs against DuckDB. Use DuckDB syntax: `STRFTIME('%Y-%m', date_col)`, `date_col::DATE + INTERVAL 7 DAY`, `julian(date_col)`, `NULLS LAST`.
- Easy + Medium: write portable SQL where possible (standard JOIN syntax, no vendor-specific functions beyond DuckDB date helpers).
- Hard: DuckDB-specific window frames and CTEs are fine.
- Always use explicit JOIN syntax (no comma joins).
- No `SELECT *` — name every output column.
- If result ordering matters to the question's purpose, include `ORDER BY`.
- Use clear table aliases (`u`, `o`, `p`, etc.).

---

## SQL anti-patterns

- Questions where the only challenge is knowing a function name
- Non-deterministic results without ORDER BY when order is meaningful
- Ambiguous output: "find the top users" without defining top
- Artificially joining tables that add no analytical complexity
- Trivial one-liners: `SELECT AVG(salary) FROM employees` — no reasoning required

---

---

# Python (Algorithms) Track

---

## Difficulty standards

### Easy (21001–21999)
Single algorithmic concept, unambiguous I/O. Basic Python only: loops, conditionals, list/dict/set/str. No recursion beyond trivial cases.

- Test cases: 3–4 total, 2 public
- Time complexity: O(n) or O(n log n)

### Medium (22001–22999)
1–2 related concepts. Requires recognizing a known algorithmic pattern: sliding window, two pointers, binary search, stack, heap, prefix sum, BFS/DFS, 1D DP, backtracking.

- Test cases: 5–6 total, 2 public
- Time complexity: O(n log n) or non-obvious O(n)

### Hard (23001–23999)
Multi-stage reasoning: 2+ dependent algorithmic steps. Advanced patterns: DP (2D, memoization), graph algorithms (Dijkstra, Union-Find, topological sort), Trie, system-design data structures (LRU, median heap).

- O(n²) naive solution is NOT acceptable
- Test cases: 7+ total, 2 public

---

## Python JSON schema

```json
{
  "id": 21001,
  "order": 1,
  "topic": "python",
  "difficulty": "easy",
  "title": "Two Sum",
  "description": "Given a list of integers `nums` and a target integer `target`, return the **indices** of the two numbers that add up to `target`. You may assume exactly one solution exists and you cannot use the same element twice.\n\n**Example:**\n```python\nsolve([2, 7, 11, 15], 9)  # → [0, 1]\nsolve([3, 2, 4], 6)       # → [1, 2]\n```",
  "starter_code": "def solve(nums: list, target: int) -> list:\n    # Your code here\n    pass",
  "expected_code": "def solve(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "solution_code": "def solve(nums: list, target: int) -> list:\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "explanation": "Use a hash map to store each number and its index as you iterate. For each number n, check if (target - n) is already in the map — if so, you've found the pair. This avoids the O(n²) nested loop. Time: O(n). Space: O(n).",
  "test_cases": [
    {"input": [[2, 7, 11, 15], 9], "expected": [0, 1]},
    {"input": [[3, 2, 4], 6], "expected": [1, 2]},
    {"input": [[3, 3], 6], "expected": [0, 1]},
    {"input": [[-1, -2, -3, -4, -5], -8], "expected": [2, 4]}
  ],
  "public_test_cases": 2,
  "hints": [
    "As you iterate, check whether the complement (target - current) has been seen before",
    "A hash map gives O(1) lookup — store each number's index as you go"
  ],
  "concepts": ["hash map", "complement lookup", "linear scan"]
}
```

**Field notes:**
- Always use `def solve(...)` as the top-level function name
- `expected_code` and `solution_code` must be identical and produce correct results for ALL test cases
- `public_test_cases` = 2 always — controls what users see during Run
- Include at least one edge case: empty input, single element, duplicates, negatives
- Explanations must state time AND space complexity
- Do not require Python 3.12+ features or external libraries beyond `collections`, `heapq`, `bisect`

---

---

# Pandas Track

---

## Core principle

Pandas questions must test **pandas-specific thinking**, not SQL-in-Python. The candidate should have to know the pandas way: `.str` accessors, `groupby.transform`, `resample`, `pd.cut`, `pivot_table`, `MultiIndex` — not just translate a SQL WHERE clause through Python syntax.

**Self-check before writing a question:** If someone who knows SQL but has never used pandas could solve it identically, rethink the question.

---

## Difficulty standards

### Easy (31001–31999)
Single pandas operation. Must teach a pandas-specific concept — not just boolean filtering.

Key concepts: `str` accessor, `pd.cut`, `dt` accessor, `dropna`, `groupby.size`, `value_counts`, `str.contains`, `str.split`, named aggregation basics.

### Medium (32001–32999)
2–3 related concepts. May involve: `merge`, `pivot_table`, `groupby.transform`, `rolling`, `resample`, `rank(pct=True)`, named aggregation.

### Hard (33001–33999)
Multi-step pipeline with 2+ dependent transformations. Non-obvious patterns: `MultiIndex`, `.xs()`, memory optimization, `groupby.apply`, cohort analysis, funnel analysis.

---

## Pandas JSON schema

```json
{
  "id": 31004,
  "order": 4,
  "topic": "python_data",
  "difficulty": "easy",
  "title": "Extract Email Domain",
  "description": "Given `df_users`, extract the domain from each email address (the part after `@`) into a new column `domain`. Return a DataFrame with columns `user_id`, `email`, `domain`, sorted by `user_id` ascending. Reset the index.",
  "dataset_files": ["users.csv"],
  "dataframes": {"df_users": "users.csv"},
  "schema": {
    "df_users": ["user_id", "name", "email", "signup_date", "country", "acquisition_channel", "plan_tier", "is_active"]
  },
  "starter_code": "import pandas as pd\n\ndef solve(df_users):\n    # Your code here\n    pass",
  "expected_code": "import pandas as pd\n\ndef solve(df_users):\n    df = df_users.copy()\n    df['domain'] = df['email'].str.split('@').str[1]\n    return df[['user_id', 'email', 'domain']].sort_values('user_id').reset_index(drop=True)",
  "solution_code": "import pandas as pd\n\ndef solve(df_users):\n    df = df_users.copy()\n    df['domain'] = df['email'].str.split('@').str[1]\n    return df[['user_id', 'email', 'domain']].sort_values('user_id').reset_index(drop=True)",
  "explanation": "The `str` accessor chains: `.str.split('@')` produces a Series of lists, then `.str[1]` indexes into each list to extract the domain. This is the pandas-idiomatic pattern — no `apply()` or regex needed for this case.",
  "hints": [
    "Use the pandas `str` accessor: `.str.split('@')` returns a Series of lists",
    "Chain `.str[1]` after the split to extract the second element of each list"
  ],
  "concepts": ["str accessor", "string splitting", "column derivation"]
}
```

**Dataset schemas (exact column names — never invent columns):**

| DataFrame | File | Columns |
|---|---|---|
| df_users | users.csv | user_id, name, email, signup_date, country, acquisition_channel, plan_tier, is_active |
| df_orders | orders.csv | order_id, user_id, order_date, status, gross_amount, discount_amount, net_amount, payment_status |
| df_products | products.csv | product_id, product_name, category_id, brand, price, launch_date, is_active |
| df_order_items | order_items.csv | order_item_id, order_id, product_id, quantity, unit_price, line_amount |
| df_employees | employees.csv | employee_id, employee_name, email, salary, department_id, hire_date, country |
| df_departments | departments.csv | department_id, department_name, region |
| df_payments | payments.csv | payment_id, order_id, payment_date, payment_method, amount, status |
| df_events | events.csv | event_id, session_id, user_id, event_time, event_name, product_id |
| df_support_tickets | support_tickets.csv | ticket_id, user_id, created_at, issue_type, priority, status, resolution_hours |

**Field notes:**
- `expected_code` and `solution_code` must be identical and correct
- Always include `.reset_index(drop=True)` for a clean 0-based integer index
- Specify exact output columns and sort order in the description — never ambiguous
- Prefer vectorized operations over `apply(lambda...)` in expected solutions

---

## Pandas anti-patterns

- Questions whose only challenge is `df[df['col'] == val]` with no pandas-specific learning
- Non-reproducible code depending on index order without `reset_index`
- Using `apply(lambda...)` when a vectorized equivalent (`.str`, `.dt`, arithmetic) exists

---

---

# PySpark Track

---

## What this track tests

Spark architecture, the PySpark DataFrame API, and production optimization. **No code is executed** — all questions are multiple choice with 4 options. The goal: test whether the candidate can *reason about* what Spark will do, not whether they can recall config values.

---

## Question subtypes

| Type | Use for |
|---|---|
| `mcq` | Conceptual understanding anchored in a real-world scenario |
| `predict_output` | Given a PySpark snippet, predict what it returns or what error it raises |
| `debug` | Given broken code or an error message, identify the root cause and fix |
| `optimization` | Given a Spark job description, choose the best performance strategy |
| `scenario` | Multi-clue production diagnosis: given job configuration, observed behavior, error logs, and/or metrics — identify the root cause or correct remediation |

**Easy tier must mix types** — do not use pure-recall MCQ at easy level. Prefer `predict_output`, `debug`, or `scenario` to force mental execution tracing. Pure-recall MCQ is only acceptable at easy when the concept cannot be meaningfully tested by code tracing.

**Target type distribution:**

| Type | Target share |
|---|---|
| `mcq` | ~48% |
| `predict_output` | ~17% |
| `debug` | ~13% |
| `scenario` | ~13% |
| `optimization` | ~8% |

---

## Difficulty standards

### Easy (41001–41999)
Single concept, one unambiguous answer. Preferred types: `predict_output` and `debug`.

Do not create questions where the answer is "know the default config value." Every easy question should require the candidate to trace what Spark actually does.

### Medium (42001–42999)
Trade-off reasoning: comparing two approaches with meaningful differences. May involve reading a code snippet, interpreting an execution plan, or explaining what an error means.

Topics: partitioning, broadcast join, shuffle, repartition vs coalesce, Delta Lake MERGE / time travel / schema evolution, Structured Streaming output modes.

### Hard (43001–43999)
Multi-factor trade-off under realistic production constraints. All 4 options must be plausible to someone who partially understands the concept.

Topics: AQE internals, DPP, skew join / salting, pandas UDF memory, Z-ordering, watermark and late data, speculative execution.

---

## PySpark JSON schema

```json
{
  "id": 41032,
  "order": 10,
  "topic": "pyspark",
  "type": "debug",
  "difficulty": "easy",
  "title": "UDF Return Type Mismatch",
  "description": "A data engineer registers a UDF with `returnType=StringType()` but the Python function returns an integer. What happens when the DataFrame action fires?",
  "code_snippet": "from pyspark.sql.functions import udf\nfrom pyspark.sql.types import StringType\n\n@udf(returnType=StringType())\ndef double_it(x):\n    return x * 2\n\ndf.withColumn('doubled', double_it('amount')).show()",
  "scenario_context": null,
  "options": [
    "Integers are automatically cast to strings — the job succeeds",
    "An AnalysisException is raised at plan analysis time",
    "The 'doubled' column contains null for every row because the return value can't be serialized as StringType",
    "A Python TypeError propagates as a SparkException at execution time"
  ],
  "correct_option": 2,
  "explanation": "Spark trusts the declared returnType and attempts to serialize the Python return value as that type. Since the Python function returns an int but StringType is declared, serialization fails silently — every row produces null. Spark does NOT validate that the actual return type matches the declaration at definition or analysis time. Option A is wrong: no automatic cast happens inside a Python UDF. Option B is wrong: AnalysisException fires for column/schema issues in SQL expressions, not UDF return types. Option D is wrong: the failure is a serialization null, not a Python-level exception.",
  "hints": ["PySpark UDFs trust the declared returnType — they do not validate the actual Python return value at runtime"],
  "concepts": ["UDF return type contract", "silent null production", "UDF serialization"]
}
```

**Field notes:**
- `correct_option` is **0-indexed** (0 = first option)
- Explanation must address **all 4 options** — explain why each wrong answer is wrong
- Distractors must represent actual misconceptions, not obviously wrong answers
- For `predict_output`: keep code mentally runnable with ≤5 simple rows
- For `debug`: use real Spark error types (AnalysisException, TypeError, SparkException) and specify when they fire
- For `scenario`: always populate both `code_snippet` and `scenario_context`; the description sets context, code_snippet shows the pipeline, scenario_context shows observed output/logs
- `code_snippet` uses `\n` for newlines in JSON; use `null` (not the string `"null"`) when absent
- `scenario_context`: optional string for simulated log output, metrics excerpt, or Spark UI observations. Use `null` for non-scenario questions. Renders in a distinct terminal-style panel in the UI.
- Do not use deprecated RDD/`sc.parallelize` API unless specifically teaching migration

### `scenario_context` authoring rules

`scenario_context` is a simulated observation block that makes `scenario` questions feel like real production debugging. It should contain one or more of:

- Log snippets: real-looking Spark/YARN log lines (timestamps, ERROR/WARN prefixes, exception class names)
- Spark UI metrics: stage summary rows in plain text (e.g. `Stage 3: 200 tasks, median 4s, max 87min, shuffle read 480GB`)
- Error stack traces: realistic Java/Python exception traces showing the relevant frames
- Job configuration: relevant `spark.conf` settings in context

Format rules:
- Keep it under ~20 lines — enough to be realistic, short enough to read quickly
- Use realistic-looking timestamps and class names, but not exhaustively verbose
- The scenario_context should provide the clues that point to the root cause, but not state the cause outright
- One context block per question; do not mix unrelated log types (e.g., don't combine a streaming watermark log with a shuffle OOM trace)

---

## PySpark anti-patterns

- Questions answerable by "know the default config value"
- Distractors that no reasonable engineer would choose
- Questions with multiple defensible correct answers depending on Spark version
- Easy-tier questions that are pure recall MCQ with no code to trace

---

---

## Authoring workflow

### Before committing any question

```bash
# 1. Check for duplicate IDs
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    all_ids.extend(q['id'] for q in json.load(open(f)))
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"

# 2. Validate all JSON files parse cleanly
python3 -c "
import json, glob
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    json.load(open(f))
print('All valid')
"

# 3. Run backend tests (catalog loader validates schemas at startup)
cd backend && ../.venv/bin/python -m pytest tests/test_evaluator.py tests/test_api.py -q
```

### SQL query verification

```python
import duckdb
con = duckdb.connect()
con.execute("CREATE TABLE users AS SELECT * FROM read_csv_auto('backend/datasets/users.csv')")
result = con.execute(your_expected_query).fetchdf()
print(result.head(10))
```

### Pandas code verification

```python
import pandas as pd
df_users = pd.read_csv("backend/datasets/users.csv")
exec(expected_code)
result = solve(df_users=df_users)
print(result.head(10), result.dtypes, result.shape)
```

### Checklist

- [ ] ID in correct range, globally unique
- [ ] `order` is the next sequential integer in the file
- [ ] Difficulty matches reasoning depth, not concept count
- [ ] Description unambiguous — output columns, filters, ordering all stated
- [ ] Expected query / code is correct and deterministic
- [ ] Solution query / code is readable best-practice
- [ ] Explanation covers logic, why the approach works, and key edge cases
- [ ] Concept tags are semantic patterns, not raw API names
- [ ] Hints guide thinking without revealing the answer
- [ ] `pytest tests/` passes

---

## Sample questions vs challenge questions

Sample questions are a completely separate system:
- SQL samples: hardcoded in `backend/sample_questions.py`; IDs `111–133` (format: TXS — track 1, difficulty 1/2/3, sequence 1–3)
- Non-SQL samples: first 3 questions by `order` from each difficulty tier of the main catalog
- Sample questions never affect `user_progress` (no solve credit, no unlock progress)
- Keep sample questions simpler than challenge questions — they're the platform demo for new visitors

**Never assign a challenge question ID (5-digit, TXNNN) to a sample question, and never reuse IDs across tracks.**

---

## Mock-only questions

Mock-only questions are exclusive to mock interview sessions — they never appear in the practice catalog. They give Pro and Elite users a genuinely fresh pool of unseen questions in mock mode.

### The `mock_only` flag

```json
"mock_only": true
```

- **Effect on the catalog loader:** `QUESTIONS` (the filtered practice list) excludes `mock_only` questions. `_ALL_QUESTIONS` and `_INDEX` include them so the mock router can fetch them by ID.
- **Effect on the mock pool:** `get_mock_questions_by_difficulty()` returns only `mock_only: true` questions. Pro and Elite users get the practice catalog + mock-only bank in their pool; Free users get only unlocked practice questions.
- **Effect on `validate_content.py`:** the script validates mock-only questions with the same rules as practice questions (concepts, hints, schema).

### Follow-up pairs

```json
// On the parent question:
"follow_up_id": 22030

// The follow-up question is a separate question entry (also mock_only: true)
```

When a user answers the parent question correctly in a mock session, the follow-up is injected as the next position in the session with `is_follow_up: true`. The follow-up banner appears in MockSession and the question tab shows a "Follow-up" badge.

**Authoring rules for follow-up pairs:**
- The parent should be medium or hard difficulty
- The follow-up escalates **exactly one dimension**: scale constraint, additional business rule, schema change, or performance requirement
- The follow-up must feel like a natural interviewer pivot ("What if the dataset was 10× larger?", "Now add a monthly breakdown")
- Never chain follow-ups: `follow_up_id` chains are limited to depth 1 (the follow-up itself should not have a `follow_up_id`)

### Scenario framing (SQL, Pandas, Python)

```json
"framing": "scenario"
```

Adds a styled narrative brief block above the question in MockSession. The `description` field holds the business narrative (≤3 sentences, sets up real-world context and ambiguity). The question `prompt` contains the actual ask.

**Good scenario framing:** "Your team is preparing a cohort analysis for the board. The `orders` table holds 18 months of transaction data including cancelled orders. Leadership wants to understand revenue retention month-over-month."

**Avoid:** abstract scenarios that add no context ("You are given a dataset..."), overly long briefs (>3 sentences), or scenarios that give away the approach.

### Reverse SQL questions (`type: "reverse"`)

Applies to SQL only. The user sees a result table and must write the query that produces it.

```json
"type": "reverse",
"result_preview": [
  {"region": "North", "total_revenue": 142500.00},
  {"region": "South", "total_revenue": 98300.00}
]
```

**Rules:**
- `result_preview` is required and must be a non-empty array
- Maximum 8 rows, maximum 4 columns (UI fit constraint)
- Column names must be clear and self-documenting
- The data in `result_preview` must exactly match what `expected_query` produces against the real datasets — run the query in DuckDB to confirm
- The `expected_query` field still holds the reference solution used for evaluation

### Debug questions (`type: "debug"`)

The user sees an error callout and broken starter code, and must fix the bug.

```json
"type": "debug",
"debug_error": "KeyError: 'acquisition_channel'",
"starter_code": "def solve(df_orders, df_users):\n    return df_orders.groupby('acquisition_channel')['net_amount'].sum()"
```

**For SQL:** use `starter_query` instead of `starter_code`.

**Rules:**
- `debug_error` must be a realistic error string (e.g., `AnalysisException: Reference 'user_id' is ambiguous`, `KeyError: 'revenue'`) — not made-up
- The starter code must have **exactly one bug** that produces the stated error
- The fix must be minimal (change one thing) and the corrected code is the `expected_query`/`expected_code`
- Write the `debug_error` exactly as it would appear in a real stack trace

### Business datasets for mock content

Mock-only questions should use the 11 existing practice datasets so SQL queries and Pandas code run against real data. For Python algorithm questions, no dataset is needed.

| Dataset | Tables / key columns |
|---|---|
| users | user_id, name, email, signup_date, country, acquisition_channel, plan_tier, is_active |
| orders | order_id, user_id, order_date, status, net_amount, payment_method |
| order_items | order_item_id, order_id, product_id, quantity, unit_price |
| products | product_id, name, category_id, price, stock_quantity |
| categories | category_id, name, parent_category_id |
| employees | employee_id, name, department_id, salary, hire_date, manager_id |
| departments | department_id, name, budget, location |
| events | event_id, user_id, event_type, event_time, page, session_id |
| sessions | session_id, user_id, start_time, end_time, traffic_source, device_type |
| payments | payment_id, order_id, amount, payment_date, payment_method, status |
| support_tickets | ticket_id, user_id, subject, status, created_at, resolved_at, resolution_hours |

**For SQL/Pandas mock questions:** frame the question in a business context drawn from these datasets but use fresh angles not covered in the practice bank (different aggregations, time windows, joins, business KPIs).

### Mock-only question checklist

In addition to the standard authoring checklist, every `mock_only` question must pass:

- [ ] `"mock_only": true` present
- [ ] Uses a concept angle not already in the practice bank for this difficulty level
- [ ] If `follow_up_id` set: follow-up escalates exactly one dimension and is itself `mock_only: true`; follow-up has no `follow_up_id` of its own
- [ ] If `type: "reverse"`: `result_preview` present, ≤8 rows, ≤4 columns, data matches `expected_query` output exactly
- [ ] If `type: "debug"`: exactly one bug in `starter_code`/`starter_query`, `debug_error` is a realistic error string
- [ ] If `framing: "scenario"`: description is ≤3 sentences, sets up real business context
- [ ] `python scripts/validate_content.py` passes clean after authoring
