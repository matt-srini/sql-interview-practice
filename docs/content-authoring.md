# Content Authoring

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md)

Curriculum specifications and authoring rules for all four tracks. This is the contract for all question creation and modification.

> **AI authoring agents** — track-specific prompt files live in `.github/agents/`:
> [`sql-question-authoring.agent.md`](../.github/agents/sql-question-authoring.agent.md) ·
> [`python-question-authoring.agent.md`](../.github/agents/python-question-authoring.agent.md) ·
> [`pandas-question-authoring.agent.md`](../.github/agents/pandas-question-authoring.agent.md) ·
> [`pyspark-question-authoring.agent.md`](../.github/agents/pyspark-question-authoring.agent.md)

---

## Platform philosophy

This is a **FAANG-level interview preparation platform**, not a syntax tutorial. Every question must pass a single test: **would a senior data interviewer at Meta, Google, Stripe, or Amazon ask this?**

### What good questions do

- **Test reasoning depth**, not syntax recall — the candidate should have to think, not just remember a keyword
- **Mirror real business scenarios** — queries and code that could appear in an actual analytics or engineering codebase
- **Teach a durable concept** — after solving it, the user should understand *why* the approach works, not just memorize the solution
- **Progress logically** — each question builds on a mental model; the curriculum is a learning arc, not a random collection

### What good questions avoid

- Trivial one-liners that test nothing beyond "did you memorize this function name"
- Academic or toy problems with no connection to real data work
- Multiple valid interpretations of the expected output
- Redundant coverage of the same concept (3+ questions with identical patterns)
- Artificially increasing difficulty via concept stacking (e.g., making a question hard by requiring 8 unrelated operations)

### Difficulty philosophy

Difficulty should come from **reasoning complexity and multi-stage logic**, not from syntactic obscurity or concept stacking.

- **Easy**: One central concept, clear input/output, applies to a realistic single-table or simple two-table scenario
- **Medium**: Two to three related concepts that must be composed; requires thinking through a multi-step problem; no window functions in SQL
- **Hard**: Multi-layer reasoning with dependent steps; at least one advanced concept (window functions, graph algorithms, streaming semantics, cohort analysis); often requires choosing between approaches

---

## ID ranges

| Track | Easy | Medium | Hard | Sample IDs |
|---|---|---|---|---|
| SQL | 1001–1999 | 2001–2999 | 3001–3999 | 101–103 (E), 201–203 (M), 301–303 (H) |
| Python | 4001–4299 | 4301–4599 | 4601–4999 | 401–403 (E), 411–413 (M), 421–423 (H) |
| Pandas | 5001–5299 | 5300–5599 | 5600–5999 | 501–503 (E), 601–603 (M), 701–703 (H) |
| PySpark | 11001–11299 | 11300–11599 | 11600–13999 | 4501–4503 (E), 4601–4603 (M), 4701–4703 (H) |

**IDs must be globally unique across all tracks.** Check for duplicates before adding:
```bash
python3 -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    data = json.load(open(f))
    if isinstance(data, list):
        all_ids.extend(q['id'] for q in data)
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Total:', len(all_ids), '| Duplicates:', set(dupes) or 'none')
"
```

---

## Adding questions — checklist

Before committing any new question:

- [ ] ID is in the correct range and globally unique
- [ ] `order` is the next sequential integer in the file
- [ ] Difficulty is correct: does the question require the reasoning depth for that tier?
- [ ] Description is unambiguous: output columns, filters, ordering are all stated explicitly
- [ ] Expected query / expected code is correct, deterministic, and verified against real data
- [ ] Explanation teaches the *why* — covers logic step-by-step, key concepts, common pitfalls, edge cases
- [ ] Hints are directional (guide thinking toward the approach) not prescriptive (don't give the answer)
- [ ] Concept tags are semantic reasoning patterns, not raw primitive names
- [ ] `pytest backend/tests/` passes (catalog loader catches schema violations)

---

---

# SQL Track

---

## Difficulty standards

### Easy (1001–1999)

**Core concepts:** 1–2 maximum, directly related.

**Allowed:**
- SELECT, WHERE (AND/OR, IN, BETWEEN, LIKE, IS NULL/IS NOT NULL)
- ORDER BY (ASC/DESC, multi-column)
- Basic aggregation: COUNT, SUM, AVG, MIN, MAX, COALESCE
- Single-column or multi-column GROUP BY
- DISTINCT
- INNER JOIN or LEFT JOIN (basic PK–FK, max 1 join)
- Date filtering and date extraction functions (STRFTIME)
- Simple CTEs (WITH clause) for an intro-level CTE question

**Not allowed:** Subqueries, window functions, HAVING (except in straightforward GROUP BY + HAVING), complex multi-table joins.

**Table complexity:** 1–2 tables, one-to-many only.

**Quality bar:** Would a first-year analyst be expected to write this in their first week?

### Medium (2001–2999)

**Core concepts:** 1–2, directly related. Complexity comes from multi-step reasoning, not concept stacking.

**Allowed:**
- Multi-table INNER + LEFT + FULL OUTER JOINs (2–4 tables)
- GROUP BY multi-column + HAVING
- CASE WHEN expressions
- Subqueries: IN / EXISTS / scalar (single reasoning layer)
- CTEs (WITH clause) for readability
- Date arithmetic, combined conditions
- LAG/LEAD window functions for adjacent-period comparisons (period-over-period)

**Not allowed:** Advanced window functions (partitioned RANK, running totals, complex frame clauses).

**Quality bar:** Would this appear in a data analyst SQL screen at a mid-size tech company?

### Hard (3001–3999)

**Must include at least one of:**
- Window functions (ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, SUM OVER, ROWS vs RANGE)
- CTEs with dependent layers (CTE chain)
- Multi-level aggregation (aggregate → rank, sequence → filter)
- Conditional aggregation with business logic
- State transition detection, cohort analysis, sessionization, funnel analysis

**Must require at least 2 dependent steps** — e.g., aggregate → rank, sequence → filter, CTE → window.

**Table complexity:** 2–5 tables, may include self-joins or complex event-level tables.

**Quality bar:** Would this appear in a senior analyst or data engineering SQL screen at FAANG?

---

## Concept tagging (all difficulties)

The `concepts` field is a **learner-facing semantic tag**, not a raw SQL primitive inventory.

✅ Good tags: `COHORT ANALYSIS`, `RUNNING TOTAL THRESHOLD DETECTION`, `LATEST STATE DERIVATION`, `FUNNEL ORDER ENFORCEMENT`, `CUMULATIVE CONTRIBUTION`, `DATE BUCKET GROUPING`, `NULL-SAFE ARITHMETIC`

❌ Bad tags: `JOIN`, `AGGREGATION`, `WINDOW FUNCTION`, `SUBQUERY`, `ROW_NUMBER`, `LAG`

Target 2–4 tags per question. Tags describe the analytical *pattern*, not the SQL *mechanism*.

---

## SQL question JSON schema

```json
{
  "id": 1001,
  "order": 1,
  "title": "Short descriptive title",
  "difficulty": "easy",
  "description": "Clear problem statement. State: what to compute, required output columns, any filters, ordering requirements.",
  "dataset_files": ["users.csv"],
  "schema": {
    "users": ["user_id", "name", "email", "country"]
  },
  "expected_query": "SELECT ... (used for evaluation — must be correct and deterministic)",
  "solution_query": "SELECT ... (shown to user — clean, readable, best-practice SQL)",
  "required_concepts": ["order_by"],
  "enforce_concepts": true,
  "explanation": "Step-by-step logic, WHY the approach works, key concepts, edge-case handling, common mistakes.",
  "hints": ["Guide thinking, do not reveal answer", "Progressive hint if needed"],
  "concepts": ["SEMANTIC REASONING TAG", "ANOTHER TAG"],
  "companies": ["Meta", "Amazon"]
}
```

`required_concepts` keys: `order_by`, `distinct`, `where`, `group_by`, `having`, `join`, `left_join`, `subquery`, `cte`, `window_function`, `case_when`, `coalesce`, `date_trunc`, `null_check`, `union`, `exists`, `recursive_cte`

`companies` (optional): canonical set: `Meta`, `Google`, `Amazon`, `Stripe`, `Airbnb`, `Netflix`, `Uber`, `Microsoft`, `LinkedIn`, `Shopify`, `eBay`, `PayPal`, `Salesforce`, `Zendesk`, `Amplitude`. Map to companies actually known to ask this style of question.

---

## SQL style rules

- Easy + Medium: portable across PostgreSQL, MySQL, DuckDB, SQL Server
- Hard: DuckDB-compatible; prefer standard SQL first; DuckDB-specific syntax (STRFTIME, JULIANDAY, `||` concat) is acceptable
- Use explicit JOIN syntax (no implicit comma joins)
- No SELECT * — always name columns explicitly
- If ordering matters, include explicit ORDER BY
- Use clear table aliases on all multi-table queries
- Prefer `>= '2024-01-01' AND < '2025-01-01'` over `YEAR(date) = 2024` for date range filtering

---

## SQL anti-patterns (strictly avoid)

- Vague terms like "top" or "best" without a precise definition
- Non-deterministic ordering (no ORDER BY when result order matters)
- Ambiguous grouping or multiple valid interpretations of the result
- Artificially increasing difficulty via unrelated concept stacking
- Questions that test memorization of default values or obscure syntax quirks
- Using synthetic column values that break the realism (e.g., LIKE 'User%' on names that are literally "User 1")

---

---

# Python (Algorithms) Track

---

## What this track covers

Classic data structures and algorithms problems — the type asked in coding screens at FAANG for data engineering, ML engineering, and analytics engineering roles. Problems should feel like they could appear on LeetCode Medium or Hard but are framed with realistic context.

## Difficulty standards

### Easy (4001–4299)
- Single function, clear I/O contract
- No more than 1 core algorithmic concept
- Basic Python: loops, conditionals, built-in types (list, dict, set, str)
- No recursion beyond simple cases, no complex data structures
- Test cases: 3–4 total (2 public, rest hidden)
- Expected time complexity: O(n) or O(n log n)

### Medium (4301–4599)
- 1–2 concepts, directly related
- May require a known data structure (stack, queue, deque, heap, trie) or algorithm pattern
- Recursion and backtracking allowed
- Test cases: 5–6 total (2 public, rest hidden)
- Expected: O(n log n) or O(n) non-obvious

### Hard (4601–4999)
- Multi-stage reasoning with at least 2 dependent algorithmic steps
- Advanced patterns: DP, backtracking, graph traversal (BFS/DFS/Dijkstra), Union-Find, monotonic stack, trie, system design data structures
- Test cases: 7+ total (2 public, rest hidden)
- O(n²) naive is not acceptable; expected O(n log n) or better where applicable
- Problems should require the candidate to *choose* the right data structure, not just implement a given one

---

## Python question JSON schema

```json
{
  "id": 4001,
  "order": 1,
  "topic": "python",
  "title": "Two Sum",
  "difficulty": "easy",
  "description": "Problem statement with examples in code blocks.",
  "starter_code": "def solve(nums: list, target: int) -> list:\n    # Your code here\n    pass",
  "expected_code": "def solve(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "solution_code": "def solve(nums: list, target: int) -> list:\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "explanation": "Step-by-step explanation with time/space complexity analysis.",
  "test_cases": [
    { "input": [[2, 7, 11, 15], 9], "expected": [0, 1] }
  ],
  "public_test_cases": 2,
  "hints": ["Directional hint toward the approach"],
  "concepts": ["hash map", "linear scan"]
}
```

**Rules:**
- Always use `def solve(...)` as the function name
- `public_test_cases` must be ≤ `len(test_cases)` — controls what users see during Run
- Include at least one edge case: empty input, single element, duplicates, zero, negatives
- Do not require Python 3.12+ features or external libraries
- Explanation must include time and space complexity
- Frame problems with realistic context, not toy-like phrasing

---

---

# Pandas Track

---

## What this track covers

Pandas-specific data manipulation patterns used in data science and analytics engineering roles. Questions must test *pandas thinking*, not just replicate SQL operations. The key question for each question: **would a data scientist or analytics engineer actually write this in a Jupyter notebook or production pipeline?**

### Pandas-specific concepts to cover (not just SQL equivalents)

- `str` accessor operations (`.str.split`, `.str.contains`, `.str.extract`)
- `pd.cut` / `pd.qcut` for bucketing and binning
- `resample()` for proper time series aggregation
- `explode()` for list-valued columns
- Memory optimization (`astype('category')`, `int32`, `memory_usage`)
- Named aggregation syntax (`groupby().agg(name=(col, func))`)
- `groupby().rank()` and `groupby().transform()` for within-group operations
- `pd.pivot_table()` and `pd.melt()` for reshaping
- MultiIndex and `.xs()` for hierarchical data
- Rolling windows, `shift()`, cumulative operations

## Difficulty standards

### Easy (5001–5299)
- Single core pandas operation
- 1–2 DataFrames, no joins required
- Expected solution: 1–4 method chains
- **Must test pandas-specific thinking**, not just boolean filtering that mirrors SQL WHERE

### Medium (5300–5599)
- 2–3 concepts, directly related
- May involve: merge, pivot/melt, groupby+transform, rolling windows, resample, rank, cut/qcut, named aggregation
- Expected solution: 3–7 method chains or a small pipeline with intermediate steps

### Hard (5600–5999)
- Multi-step pipeline with at least 2 dependent transformations
- Non-obvious chaining, memory considerations, or performance-aware patterns
- Expected solution: 5+ steps, may use intermediate DataFrames
- Examples: cohort retention, RFM, funnel analysis, MultiIndex operations, dtype optimization

---

## Pandas question JSON schema

```json
{
  "id": 5001,
  "order": 1,
  "topic": "python_data",
  "title": "Title",
  "difficulty": "easy",
  "description": "Given `df_users`, ... Return columns X, Y sorted by Z ascending.",
  "dataframes": { "df_users": "users.csv" },
  "schema": { "df_users": ["col1", "col2", ...] },
  "starter_code": "import pandas as pd\n\ndef solve(df_users):\n    # comment\n    pass",
  "expected_code": "import pandas as pd\n\ndef solve(df_users):\n    ...",
  "solution_code": "import pandas as pd\n\ndef solve(df_users):\n    ...",
  "explanation": "Step-by-step explanation of the pandas approach and why it works.",
  "hints": ["Hint 1", "Hint 2"],
  "concepts": ["tag1", "tag2"]
}
```

**Rules:**
- Use real dataset column names exactly (verified against CSV headers)
- Specify exactly which columns the output should contain
- Specify sort order explicitly in the description
- `expected_code` and `solution_code` must be identical and correct
- Always include `.reset_index(drop=True)` at the end for clean 0-based index
- Avoid `apply()` in expected solutions unless the question specifically teaches `apply()`
- Prefer vectorized operations over loops

---

---

# PySpark Track

---

## What this track covers

Spark architecture, the PySpark DataFrame API, performance optimization, Delta Lake, and Structured Streaming. **No code is executed** — all questions are multiple-choice (4 options). Questions anchor in real-world scenarios: actual error messages, production bottlenecks, deployment decisions.

### PySpark must cover (across all difficulties)

**Foundations (Easy):** Transformations vs actions, lazy evaluation, DAG, driver vs executor, narrow vs wide transformations, RDD vs DataFrame, schema inference, Catalyst optimizer basics — PLUS predict-output and debug question types to test applied understanding, not just recall.

**Optimization (Medium):** Partitioning, shuffle, broadcast join, repartition vs coalesce, caching, AQE overview, Delta Lake MERGE/time travel/schema evolution, Structured Streaming output modes.

**Advanced (Hard):** AQE internals (all 3 optimizations), DPP activation, skew join / salting, pandas UDF memory, Z-ordering, watermark and late data handling, speculative execution.

**Question subtypes:**
- `mcq` — choose the correct conceptual answer (anchored in a scenario)
- `predict_output` — given a PySpark snippet, predict what it returns or prints
- `debug` — given broken code or an error, identify the problem and fix
- `optimization` — given a Spark job setup, choose the best strategy

Easy tier must include a mix of all four types. Pure MCQ recall without code is not sufficient for easy questions.

## Difficulty standards

### Easy (11001–11299)
- Single concept, tested with a realistic scenario or code snippet
- Common question types: predict_output (what does this return?), debug (what error? what fix?), mcq (which statement is correct?)
- Tests understanding, not pure memorization — distractor options must represent real misconceptions
- Avoid questions whose answer is just "know the default configuration value"

### Medium (11300–11599)
- Reasoning about Spark internals or trade-offs (partitioning, shuffle, execution plans)
- Comparing two approaches with nuanced differences
- May involve reading and interpreting a code snippet or error message
- Delta Lake: MERGE, time travel, schema evolution
- Structured Streaming: output modes, trigger types

### Hard (11600–13999)
- Multi-factor trade-off reasoning under realistic constraints
- Memory model, AQE internals, streaming state management
- Delta Lake advanced: Z-ordering, OPTIMIZE, VACUUM, data skipping
- May require selecting the CORRECT answer from options that are all plausible

---

## PySpark question JSON schema

```json
{
  "id": 11001,
  "order": 1,
  "topic": "pyspark",
  "type": "mcq",
  "difficulty": "easy",
  "title": "Transformations vs Actions",
  "description": "Scenario-anchored question text.",
  "code_snippet": "# Python code or null",
  "options": [
    "Option A",
    "Option B",
    "Option C",
    "Option D"
  ],
  "correct_option": 2,
  "explanation": "Full explanation covering ALL 4 options: why the correct answer is right AND why each wrong answer is wrong.",
  "hints": ["One directional hint"],
  "concepts": ["lazy evaluation", "transformations vs actions"]
}
```

**`correct_option`** is the 0-indexed position in `options`.

**Rules:**
- Anchor in a real-world scenario — not abstract "what does X return?"
- Distractors must represent actual misconceptions, not obviously wrong answers
- For `predict_output`: code snippet must be mentally runnable with simple sample data
- For `debug`: show real error types (AnalysisException, TypeError, OOM) and explain when they fire
- Explanation must cover all 4 options — explain why wrong answers are wrong
- Do not ask about default configuration values as trivia
- Do not use deprecated Spark APIs (RDD-based API, `sc.parallelize`) unless teaching migration

---

---

## Schemas.json files

Each content directory has a `schemas.json` that the catalog loader uses for validation:

- `backend/content/python_questions/schemas.json`
- `backend/content/python_data_questions/schemas.json`
- `backend/content/pyspark_questions/schemas.json`

These define `id_ranges`, `required_fields`, `optional_fields`, and `difficulty_files`. The SQL track validates directly against the catalog loader in `questions.py`.

---

## Sample questions vs challenge questions

Sample questions are **completely separate** from challenge banks:
- Different ID ranges (3-digit sample IDs never overlap with 4+ digit challenge IDs)
- Stored in `backend/sample_questions.py` (SQL) and equivalent Python-backed loaders
- No progression impact — they never affect `user_progress`
- Must be simpler and platform-demo oriented

**Never mix sample and challenge question sources. Never reuse IDs across systems.**

---

## Current question counts (as of April 2026)

| Track | Easy | Medium | Hard | Total |
|---|---|---|---|---|
| SQL | 32 | 34 | 29 | 95 |
| Python | 30 | 29 | 24 | 83 |
| Pandas | 29 | 30 | 23 | 82 |
| PySpark | 38 | 30 | 22 | 90 |
| **Total** | **129** | **123** | **98** | **350** |
