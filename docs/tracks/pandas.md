# Pandas Track

> **Authoring rule, no exceptions:** Every Pandas question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/python_data_questions/*.json` bypass the difficulty arc, the concept-taxonomy contract, and the pandas-idiomatic discipline.

## What this track trains

A data analyst or scientist who *thinks in pandas* writes meaningfully different code from one who *transliterates SQL into pandas*. The Pandas track exists to train pandas-native reasoning: when does `merge` beat `concat`, when does `transform` beat `agg`, when does the `.dt` accessor save you 50 lines of date parsing, when does an explicit dtype save you 4 GB of RAM. Idiomatic pandas is also fast pandas; the two are not separate concerns.

> *Datathink philosophy applied:* The analyst who runs `df.apply(lambda x: …)` on 10 million rows is the analyst who waits 40 minutes for an answer that should've taken 4 seconds. We're training the practitioner who recognises the row-wise antipattern, picks the vectorized path, and knows *why* — not the one who memorised method signatures.

## Modality

**Executable problem-solving.** Subprocess-sandboxed Python execution with the candidate's function called against pre-loaded DataFrames. 5-second timeout. 512 MB RLIMIT_AS. Output DataFrame compared to expected via `pd.testing.assert_frame_equal` (shape + dtypes + values + ordering).

## Schema essentials (function shape + datasets)

Each question defines a top-level `def solve(...)` that takes one or more pre-loaded DataFrames and returns a DataFrame.

```python
def solve(orders: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    ...
```

DataFrames are loaded from the same 11-table business schema as the SQL track (see [`docs/datasets.md`](../datasets.md)). Schemas are validated against committed CSV headers at catalog load.

Required output discipline:
- **Always** end with `.reset_index(drop=True)` unless the index *is* the result.
- Column names and order must match the expected output exactly.
- Determinism: explicit `.sort_values(...)` whenever a meaningful order is implied.

## ID range (TXNNN scheme)

`T=3` for Pandas.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 31001–31999 | `backend/content/python_data_questions/easy.json` |
| Medium | 32001–32999 | `backend/content/python_data_questions/medium.json` |
| Hard | 33001–33999 | `backend/content/python_data_questions/hard.json` |

Samples in `backend/content/python_data_questions/sample/` use `3XS` 3-digit IDs.

## Difficulty vocabulary

| Tier | Reasoning depth | Patterns | What's out |
|---|---|---|---|
| **Easy** | One pandas-idiomatic operation. The candidate immediately knows which accessor to reach for. | `.str` accessor, `.dt` accessor, single `groupby` + aggregate, `value_counts`, `pd.cut` for binning, simple boolean indexing | Multi-table merges, pivot_table, MultiIndex |
| **Medium** | 2–3 related operations, the reasoning is *recognising the pandas-idiomatic shape*. | `merge` with explicit `how` + `on`, `pivot_table`, `groupby.transform`, `rolling` / `expanding`, `resample`, `rank(pct=True)`, named aggregation | MultiIndex slicing, full memory optimization |
| **Hard** | Multi-step pipeline. Memory awareness. Cohort/funnel-style transforms. | `MultiIndex` / `.xs()`, memory optimization via dtypes, `groupby.apply` (where unavoidable), cohort/funnel pipelines, custom `agg` with multiple functions per column, dtype-driven optimization | "Hard because the SQL solution would be hard" — wrong track |

**Critical:** every question must test *pandas-idiomatic thinking*. If a question is equally elegant in SQL, it doesn't belong here. The track's purpose is teaching pandas as a tool with its own grammar — not as a SQL substitute.

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | `.dt` / `.str` accessors → boolean indexing → single-column `groupby` + agg → `value_counts` / `nunique` → `pd.cut` / `pd.qcut` binning → simple derived columns via `.assign` |
| Medium | `merge` (inner / left / outer) → `pivot_table` (with margins) → `groupby.transform` for per-group features → `rolling` / `expanding` windowed agg → `resample` for time-based windowing → `rank(pct=True)` for percentile rank → named aggregation |
| Hard | `MultiIndex` + `.xs()` slicing → memory optimization (dtype choice, `category`) → cohort / funnel pipelines → `groupby.apply` when justified → percentage-over-group via `transform('sum')` → dtype-driven optimization |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Pandas section](../concept-taxonomy.md#pandas--concept-families).

16 families. One new in the 2026-05 refactor: **`MEMORY & VECTORIZATION REASONING`** — real practitioners hit memory and speed problems constantly; the bank teaches vectorization implicitly through "your apply is too slow" framings but never tagged it as a family. Mock-only content from now on should test this directly.

Blocklist rejects method-name tags (`groupby`, `merge`, `pivot_table`, `apply`). Describe the *reasoning*.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One idiomatic operation. Build accessor familiarity. |
| Practice medium | `medium.json` no `mock_only` | Compose 2–3 operations. Idiom recognition. |
| Practice hard | `hard.json` no `mock_only` | Multi-step pipeline. Memory and dtype awareness. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real-world framing: dirty CSV reads, mixed dtypes, missing-data realism. Target `MEMORY & VECTORIZATION REASONING`, `MISSING VALUE STRATEGY`, `DEBUG PANDAS`. |
| Mock-only hard | `hard.json` with `mock_only: true` | Production-realistic pipelines: cohort analysis with dropoff, funnel with bucket time, retention curve. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (50 GB file), business rule (now exclude returns), data quality (mixed-dtype column), performance (apply → vectorize). |

**Easy mock-only: never.**

## Anti-patterns specific to Pandas

- **SQL-in-Python solutions** — using groupby+merge+rename when the idiomatic pandas would be a single `pivot_table`. The track is *teaching* pandas, not punishing the candidate for not knowing it.
- **`apply(lambda)` as the reference solution** when a vectorized path exists. The reference must use the vectorized form.
- **MultiIndex for the sake of MultiIndex** — only when the index *is* the structure being computed (e.g. wide pivot output).
- **Questions that test exact method-signature memorization** — "what's the keyword for X" is not a reasoning test.
- **Stale dtype expectations** — if your expected output assumes `int64` and pandas gives `Int64`, fix the expected, not the candidate.

## JSON schema

```json
{
  "id": 32021,
  "order": 14,
  "topic": "pandas",
  "difficulty": "medium",
  "title": "Monthly active users with first-touch trigger",
  "description": "Given `orders` (user_id, order_date, status, net_amount), compute the count of users whose **first ever completed order** fell in each calendar month. Return columns: `month` (YYYY-MM string), `new_active_users` (int). Sort by month ascending.",
  "dataset_files": ["orders.csv"],
  "dataframes": ["orders"],
  "schema": {
    "orders": ["order_id", "user_id", "order_date", "status", "net_amount"]
  },
  "starter_code": "import pandas as pd\n\ndef solve(orders: pd.DataFrame) -> pd.DataFrame:\n    # Your code here\n    pass",
  "expected_code": "import pandas as pd\n\ndef solve(orders: pd.DataFrame) -> pd.DataFrame:\n    completed = orders[orders['status'] == 'completed'].copy()\n    completed['order_date'] = pd.to_datetime(completed['order_date'])\n    first = completed.groupby('user_id', as_index=False)['order_date'].min()\n    first['month'] = first['order_date'].dt.strftime('%Y-%m')\n    out = (\n        first.groupby('month', as_index=False)\n             .agg(new_active_users=('user_id', 'nunique'))\n             .sort_values('month')\n             .reset_index(drop=True)\n    )\n    return out",
  "solution_code": "<same logic, possibly annotated>",
  "explanation": "Compute each user's earliest completed order, bucket by month, count distinct users. The `.dt.strftime` accessor handles month-formatting idiomatically.",
  "hints": [
    "Find each user's earliest qualifying order first, then bucket.",
    "The `.dt` accessor handles month string formatting in one call."
  ],
  "concepts": ["GROUPED AGGREGATION", "DATETIME OPERATIONS", "DEDUPLICATION & DISTINCT COUNTING"]
}
```

Required:
- Reference solution uses pandas-idiomatic operations (no SQL transliteration).
- `expected_code` ends with `.reset_index(drop=True)` (or the index is intentionally meaningful).
- Output dtypes match expected exactly.
- At least one test fixture covers the empty / edge case where applicable.

## Verification before commit

```bash
# 1. Reference solution produces the documented expected output
cd backend && ../.venv/bin/python -c "
import pandas as pd, json
q = json.load(open('content/python_data_questions/medium.json'))[INDEX]
# load each CSV in q['dataset_files']
orders = pd.read_csv('datasets/orders.csv')
exec(q['expected_code'])
result = solve(orders)
print(result.head())
print(result.dtypes)
"

# 2. solution_code produces identical results to expected_code
# (pd.testing.assert_frame_equal under the hood)

# 3. Full content validation
python scripts/validate_content.py

# 4. Pandas evaluator tests
cd backend && ../.venv/bin/python -m pytest tests/test_python_evaluator.py -q -k pandas
```
