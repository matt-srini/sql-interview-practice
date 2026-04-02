# Content Authoring

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md)

Curriculum specifications and authoring rules for all four tracks. This is the contract for all question creation and modification.

---

## Global principles

- Focus on **real-world business datasets** — users, orders, products, events, employees, payments
- Avoid academic or artificial problems; prefer **clarity over cleverness**
- Every question must be **deterministic**, **evaluatable via result comparison**, and **free of ambiguity**
- Difficulty must come from **reasoning depth and multi-stage logic**, not concept stacking

---

## ID ranges

| Track | Easy | Medium | Hard | Sample IDs |
|---|---|---|---|---|
| SQL | 1001–1999 | 2001–2999 | 3001–3999 | 101–103 (E), 201–203 (M), 301–303 (H) |
| Python | 4001–4299 | 4301–4599 | 4601–4999 | 401–403 (E), 411–413 (M), 421–423 (H) |
| Pandas | 5001–5999 | 6001–6999 | 7001–7999 | 501–503 (E), 601–603 (M), 701–703 (H) |
| PySpark | 11001–11999 | 12001–12999 | 13001–13999 | 4501–4503 (E), 4601–4603 (M), 4701–4703 (H) |

**IDs must be globally unique across all tracks.** Check for duplicates before adding:
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

## Adding questions — checklist

Before committing any new question:

- [ ] ID is in the correct range and globally unique
- [ ] `order` is the next sequential integer in the file
- [ ] difficulty is correct and matches reasoning depth
- [ ] description is unambiguous — clearly states output columns, filters, ordering
- [ ] expected query / expected code is correct and deterministic
- [ ] solution query / solution code is clean and readable
- [ ] explanation covers logic step-by-step, WHY it works, and common pitfalls
- [ ] concepts tags are semantic reasoning patterns, not SQL/Python primitive names
- [ ] dataset_files / schema exist and are accurate (SQL + Pandas)
- [ ] test cases pass (Python + Pandas)
- [ ] `pytest backend/tests/` passes (catalog loader catches schema violations)

---

---

# SQL Track

---

## Difficulty standards

### Easy (1001–1999)

**Core concepts:** 1–2 maximum, directly related.

**Allowed:**
- SELECT, WHERE (AND/OR, IN, BETWEEN, LIKE)
- ORDER BY (ASC/DESC)
- Basic aggregation: COUNT, SUM, AVG, MIN, MAX
- Single-column GROUP BY
- DISTINCT
- INNER JOIN (basic PK–FK, max 1 join)
- IS NULL / IS NOT NULL

**Not allowed:** Subqueries, window functions, CTEs, HAVING, multi-table joins.

**Table complexity:** 1–2 tables, one-to-many only.

### Medium (2001–2999)

**Core concepts:** 1–2, directly related. Complexity comes from multi-step reasoning, not concept stacking.

**Allowed:**
- Multi-table INNER + LEFT JOINs (2–4 tables)
- GROUP BY multi-column + HAVING
- CASE WHEN (as helper only)
- Subqueries: IN / EXISTS / scalar (simple, single reasoning layer)
- Date filters, combined conditions

**Not allowed:** Window functions, ranking problems.

### Hard (3001–3999)

**Must include at least one:**
- Window functions (ROW_NUMBER, RANK, LAG, LEAD)
- Correlated subqueries (EXISTS / NOT EXISTS)
- Multi-level aggregation
- Conditional aggregation

**Must require at least 2 dependent steps** — e.g., aggregate → rank, sequence → filter.

**Table complexity:** 3–5 tables, complex joins including self-joins.

---

## Concept tagging (all difficulties)

The `concepts` field is a **learner-facing semantic tag**, not a raw SQL primitive inventory.

✅ Good tags: `COHORT ANALYSIS`, `RUNNING TOTAL THRESHOLD DETECTION`, `LATEST STATE DERIVATION`, `FUNNEL ORDER ENFORCEMENT`, `CUMULATIVE CONTRIBUTION`

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
  "explanation": "Step-by-step logic, WHY the approach works, key concepts, edge-case handling.",
  "hints": ["Guide thinking, do not reveal answer", "Progressive hint if needed"],
  "concepts": ["SEMANTIC REASONING TAG", "ANOTHER TAG"]
}
```

`expected_query` vs `solution_query`: They must produce identical results. `expected_query` is used for evaluation; `solution_query` is what users see post-submit and should be the cleanest form.

---

## SQL style rules

- Easy + Medium: portable across PostgreSQL, MySQL, SQL Server (no DuckDB-specific functions)
- Hard: can use advanced SQL; prefer standard SQL first
- Use explicit JOIN syntax (no implicit comma joins)
- No SELECT * — always name columns explicitly
- If ordering matters, include explicit ORDER BY
- Use clear table aliases

---

## SQL anti-patterns (strictly avoid)

- Vague terms like "top" or "best" without clear definition
- Non-deterministic ordering (no ORDER BY when order matters)
- Ambiguous grouping
- Multiple valid interpretations of the result
- Mixing difficulty levels in a single question
- Artificially increasing difficulty via unrelated concept stacking

---

---

# Python (Algorithms) Track

---

## Difficulty standards

### Easy (4001–4299)
- Single function, clear I/O contract
- No more than 1 core algorithmic concept
- Basic Python: loops, conditionals, built-in types (list, dict, set, str)
- No recursion, no OOP, no complex data structures
- Test cases: 3 total (2 public, 1 hidden)
- Expected time complexity: O(n) or O(n log n)

### Medium (4301–4599)
- 1–2 concepts, directly related
- May require a known data structure (stack, queue, deque, heap) or algorithm pattern (binary search, two pointers, sliding window)
- Recursion allowed
- Test cases: 5 total (2 public, 3 hidden)
- Expected: O(n log n) or O(n) non-obvious

### Hard (4601–4999)
- Multi-stage reasoning: at least 2 dependent algorithmic steps
- Advanced patterns: DP, backtracking, graph traversal (BFS/DFS), monotonic stack, trie
- Test cases: 7 total (2 public, 5 hidden)
- O(n²) naive is not acceptable — expected O(n log n) or better

---

## Python question JSON schema

```json
{
  "id": 4001,
  "order": 1,
  "topic": "python",
  "title": "Two Sum",
  "difficulty": "easy",
  "description": "Given a list of integers `nums` and a target integer `target`, return a list containing the indices of the two numbers that add up to `target`. You may assume exactly one solution exists.",
  "starter_code": "def solve(nums: list, target: int) -> list:\n    # Your code here\n    pass",
  "expected_code": "def solve(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "solution_code": "def solve(nums: list, target: int) -> list:\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i",
  "explanation": "Use a hash map to store each number and its index as you iterate. For each number n, check if (target - n) is already in the map. O(n) time, O(n) space.",
  "test_cases": [
    { "input": [[2, 7, 11, 15], 9], "expected": [0, 1] },
    { "input": [[3, 2, 4], 6], "expected": [1, 2] },
    { "input": [[3, 3], 6], "expected": [0, 1] }
  ],
  "public_test_cases": 2,
  "hints": ["Consider using a hash map to store seen numbers."],
  "concepts": ["hash map", "linear scan"]
}
```

**Rules:**
- Always use `def solve(...)` as the function name
- `public_test_cases` must be ≤ `len(test_cases)` — controls what users see during Run
- Include at least one edge case: empty list, single element, duplicates, zero, negatives
- Do not require Python 3.12+ features; do not require any imported library
- Frame problems with realistic context, not toy-like phrasing

**Testing before commit:**
```python
exec(expected_code)
for tc in test_cases:
    result = solve(*tc["input"])
    assert result == tc["expected"], f"Failed: {result} != {tc['expected']}"
print("All test cases passed")
```

---

---

# Pandas Track

---

## Difficulty standards

### Easy (5001–5999)
- Single core pandas operation
- 1–2 DataFrames, no joins
- Expected solution: 1–3 method chains
- Skills: filtering, selecting columns, sorting, basic aggregation, null handling, string ops, renaming

### Medium (6001–6999)
- 2–3 concepts, directly related
- May involve: merge, pivot/melt/stack, groupby+transform, rolling windows, numpy operations
- Expected solution: 3–6 method chains
- Skills: merge, concat, pivot_table, melt, groupby+transform, rolling, rank, cut/qcut, numpy broadcasting, datetime ops

### Hard (7001–7999)
- Multi-step pipeline with at least 2 dependent transformations
- Non-obvious chaining, numpy-pandas interplay, or performance considerations
- Expected solution: 5+ steps, may use intermediate DataFrames
- Skills: named aggregation, time-series resampling, cumulative ops, cross-tab, stack/unstack, vectorised patterns

---

## Pandas question JSON schema

```json
{
  "id": 5001,
  "order": 1,
  "topic": "python_data",
  "title": "Filter US Users",
  "difficulty": "easy",
  "description": "Given `df_users`, return a DataFrame containing only users where `country = 'US'`, sorted by `user_id` ascending. Keep all columns. Reset the index.",
  "dataset_files": ["users.csv"],
  "schema": {
    "users": ["user_id", "name", "email", "country", "signup_date", "plan", "status"]
  },
  "dataframes": {
    "df_users": "users.csv"
  },
  "starter_code": "import pandas as pd\n\ndef solve(df_users):\n    # Your code here\n    pass",
  "expected_code": "import pandas as pd\n\ndef solve(df_users):\n    return df_users[df_users['country'] == 'US'].sort_values('user_id').reset_index(drop=True)",
  "solution_code": "import pandas as pd\n\ndef solve(df_users):\n    return df_users[df_users['country'] == 'US'].sort_values('user_id').reset_index(drop=True)",
  "explanation": "Filter rows where country equals 'US', sort by user_id, reset the integer index.",
  "hints": ["Use boolean indexing to filter rows."],
  "concepts": ["filtering", "sorting"]
}
```

**Rules:**
- Use the real dataset tables with their actual column names
- Specify exactly which columns the output should contain
- Specify sort order explicitly in the description
- Do not assume specific pandas version behavior for edge cases
- Avoid `apply()` in expected solutions unless the question is specifically teaching `apply()`

**Testing before commit:**
```python
import pandas as pd
df_users = pd.read_csv("backend/datasets/users.csv")
exec(expected_code)
result = solve(df_users=df_users)
print(result.head(10), result.dtypes, result.shape)
# Verify: column names match description, row count reasonable, no unexpected NaN
```

---

---

# PySpark Track

---

## What this track covers

Spark architecture, the PySpark DataFrame API, and real-world optimization. **No code is executed** — all questions are multiple-choice (4 options). Some include a read-only code snippet.

**Question subtypes:**
- `mcq` — choose the correct conceptual answer
- `predict_output` — given a PySpark snippet, predict what it returns
- `debug` — given broken code or an error message, identify the fix
- `optimization` — given a Spark job setup, choose the best strategy

---

## Difficulty standards

### Easy (11001–11999)
- Single concept, no ambiguity
- Tests recall and understanding of fundamental Spark behavior
- Common in screening rounds and entry-level data engineering interviews

### Medium (12001–12999)
- Reasoning about Spark internals (partitioning, shuffle, execution plans)
- Comparing two or more approaches
- May require reading and interpreting a code snippet or `explain()` output

### Hard (13001–13999)
- Multi-factor trade-off reasoning
- Memory model, AQE, or advanced optimization
- May involve ordering questions

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
  "description": "Which of the following is a Spark **action** (triggers job execution)?",
  "code_snippet": null,
  "options": [
    "df.filter(df.age > 30)",
    "df.select('name', 'age')",
    "df.count()",
    "df.withColumn('senior', df.age > 60)"
  ],
  "correct_option": 2,
  "explanation": "df.count() is an action — it triggers job execution and returns a Python integer. The others (filter, select, withColumn) are transformations that build a lazy execution plan.",
  "hints": ["Think about what actually runs Spark jobs vs what just builds a plan."],
  "concepts": ["lazy evaluation", "transformations vs actions"]
}
```

**`correct_option`** is the 0-indexed position in `options`.

**Rules:**
- Anchor in a real-world scenario (not "what does filter() return?" as pure trivia)
- Distractors must represent actual misconceptions, not obvious wrong answers
- For `predict_output`: keep code snippet mentally runnable with 3–5 sample rows
- For `optimization`: do not write questions where all 4 options could be correct in some scenario
- Do not ask about default configuration values (trivia)
- Do not use deprecated Spark APIs (RDD-based API, `sc.parallelize`) unless specifically teaching migration

**Verification before commit:**
- `correct_option` is 0-indexed correctly
- All 4 options are plausible but only one is unambiguously correct
- Explanation covers all 4 options (why the wrong ones are wrong)

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
