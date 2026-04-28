# Content Authoring

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md) · [Datasets](./datasets.md)

This is the authoritative guide for creating, editing, and reviewing questions on datathink. It covers the philosophy behind the question bank, the quality bar every question must clear, per-track authoring rules, and the exact JSON schemas the catalog loaders expect.

**AI authoring agents** (use these when generating questions with Claude):
- [`.github/agents/sql-question-authoring.agent.md`](../.github/agents/sql-question-authoring.agent.md)
- [`.github/agents/python-question-authoring.agent.md`](../.github/agents/python-question-authoring.agent.md)
- [`.github/agents/pandas-question-authoring.agent.md`](../.github/agents/pandas-question-authoring.agent.md)
- [`.github/agents/pyspark-question-authoring.agent.md`](../.github/agents/pyspark-question-authoring.agent.md)

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

| Track | Easy | Medium | Hard | Total | Format |
|---|---|---|---|---|---|
| SQL | 32 | 34 | 29 | **95** | SQL query, evaluated via DuckDB |
| Python | 30 | 29 | 24 | **83** | Function implementation, evaluated via test cases |
| Pandas | 22 | 31 | 23 | **76** | DataFrame function, evaluated via output comparison |
| PySpark | 38 | 30 | 22 | **90** | MCQ / predict-output / debug, evaluated by option selection |
| **Total** | **122** | **124** | **98** | **344** | |

Sample questions (no login, no progress): 3 per track × 3 difficulties = 9 per track = **36 total**.

### Learning paths (curated sequences)

| Track | Paths | Distribution |
|---|---:|---|
| SQL | 7 | 2 free shortcut paths (`starter`, `intermediate`) + 5 advanced (mixed free/pro) |
| Python | 5 | 2 free shortcut paths (`starter`, `intermediate`) + 3 advanced (mixed free/pro) |
| Pandas | 5 | 2 free shortcut paths (`starter`, `intermediate`) + 3 advanced (mixed free/pro) |
| PySpark | 5 | 2 free shortcut paths (`starter`, `intermediate`) + 3 advanced (mixed free/pro) |
| **Total** | **22** | |

Authoring constraints for path files in `backend/content/paths/`:
- Required fields: `slug`, `title`, `description`, `topic`, `questions`, `tier`, `role`
- `topic` must be one of: `sql`, `python`, `python-data`, `pyspark`
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

---

## ID ranges

| Track | Easy | Medium | Hard |
|---|---|---|---|
| SQL | 1001–1999 | 2001–2999 | 3001–3999 |
| Python | 4001–4299 | 4301–4599 | 4601–4999 |
| Pandas | 5001–5299 | 5300–5599 | 5600–5999 |
| PySpark | 11001–11299 | 11300–11599 | 11600–11999 |

SQL sample questions: `101–103` (easy) · `201–203` (medium) · `301–303` (hard) — defined in `backend/sample_questions.py`.

**IDs must be globally unique across all question files.** Before adding a question:
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

PySpark easy is the only allowed single-hint exception. Those questions are fast concept checks, so one strong execution-oriented hint is acceptable as long as the UI does not pretend there is a multi-step ladder.

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

### Easy (1001–1999)
Single-step logic. One core concept, at most two if tightly related (e.g., WHERE + IS NULL).

**Allowed:** SELECT, WHERE (AND/OR/IN/BETWEEN/LIKE), ORDER BY, DISTINCT, basic aggregation, single GROUP BY, simple INNER JOIN (max 1), IS NULL / IS NOT NULL, COALESCE, STRFTIME / date formatting, CTE (intro-level — one CTE wrapping a simple query).

**Not allowed:** Window functions, correlated subqueries, HAVING, multi-table joins.

### Medium (2001–2999)
2–3 related concepts. Complexity comes from multi-step reasoning, not from bolting together unrelated SQL features.

**Allowed:** Multi-table INNER + LEFT JOINs (2–4 tables), FULL OUTER JOIN, GROUP BY + HAVING, CASE WHEN, scalar/IN/EXISTS subqueries, LAG (one-step delta), date arithmetic, multi-column GROUP BY.

**Not allowed:** Full window function suites, recursive CTEs, complex multi-CTE pipelines.

### Hard (3001–3999)
Must require at least 2 dependent steps. At least one of: window functions (ROW_NUMBER, RANK, LAG, LEAD, SUM OVER, ROWS/RANGE), multi-CTE pipelines, correlated subqueries, advanced aggregation patterns.

Hard questions should feel like a real FAANG analytics problem: sessionization, cohort retention, funnel analysis, Pareto, state machine detection, running totals with conditions.

---

## SQL JSON schema

```json
{
  "id": 1031,
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

### Easy (4001–4299)
Single algorithmic concept, unambiguous I/O. Basic Python only: loops, conditionals, list/dict/set/str. No recursion beyond trivial cases.

- Test cases: 3–4 total, 2 public
- Time complexity: O(n) or O(n log n)

### Medium (4301–4599)
1–2 related concepts. Requires recognizing a known algorithmic pattern: sliding window, two pointers, binary search, stack, heap, prefix sum, BFS/DFS, 1D DP, backtracking.

- Test cases: 5–6 total, 2 public
- Time complexity: O(n log n) or non-obvious O(n)

### Hard (4601–4999)
Multi-stage reasoning: 2+ dependent algorithmic steps. Advanced patterns: DP (2D, memoization), graph algorithms (Dijkstra, Union-Find, topological sort), Trie, system-design data structures (LRU, median heap).

- O(n²) naive solution is NOT acceptable
- Test cases: 7+ total, 2 public

---

## Python JSON schema

```json
{
  "id": 4001,
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

### Easy (5001–5299)
Single pandas operation. Must teach a pandas-specific concept — not just boolean filtering.

Key concepts: `str` accessor, `pd.cut`, `dt` accessor, `dropna`, `groupby.size`, `value_counts`, `str.contains`, `str.split`, named aggregation basics.

### Medium (5300–5599)
2–3 related concepts. May involve: `merge`, `pivot_table`, `groupby.transform`, `rolling`, `resample`, `rank(pct=True)`, named aggregation.

### Hard (5600–5999)
Multi-step pipeline with 2+ dependent transformations. Non-obvious patterns: `MultiIndex`, `.xs()`, memory optimization, `groupby.apply`, cohort analysis, funnel analysis.

---

## Pandas JSON schema

```json
{
  "id": 5031,
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

### Easy (11001–11299)
Single concept, one unambiguous answer. Preferred types: `predict_output` and `debug`.

Do not create questions where the answer is "know the default config value." Every easy question should require the candidate to trace what Spark actually does.

### Medium (11300–11599)
Trade-off reasoning: comparing two approaches with meaningful differences. May involve reading a code snippet, interpreting an execution plan, or explaining what an error means.

Topics: partitioning, broadcast join, shuffle, repartition vs coalesce, Delta Lake MERGE / time travel / schema evolution, Structured Streaming output modes.

### Hard (11600–11999)
Multi-factor trade-off under realistic production constraints. All 4 options must be plausible to someone who partially understands the concept.

Topics: AQE internals, DPP, skew join / salting, pandas UDF memory, Z-ordering, watermark and late data, speculative execution.

---

## PySpark JSON schema

```json
{
  "id": 11032,
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
- SQL samples: hardcoded in `backend/sample_questions.py`; IDs `101–303`
- Non-SQL samples: first 3 questions by `order` from each difficulty tier of the main catalog
- Sample questions never affect `user_progress` (no solve credit, no unlock progress)
- Keep sample questions simpler than challenge questions — they're the platform demo for new visitors

**Never assign a challenge question ID (4-digit) to a sample question, and never reuse IDs across tracks.**
