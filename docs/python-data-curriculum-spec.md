# Pandas Curriculum Spec

Track: **Pandas**
Topic key: `python_data`
ID range: easy 5001–5999, medium 6001–6999, hard 7001–7999
Sample IDs: easy 501–503, medium 601–603, hard 701–703

---

## What This Track Covers

pandas and numpy data manipulation — the core skills tested in data analyst, data scientist, and analytics engineer interviews. Questions use the same 11-table dataset as the SQL track (loaded into pandas DataFrames from CSVs).

Available packages in `solve()`: `pandas`, `numpy`, `math`, `statistics`, `collections`, `itertools`, `functools`, `datetime`, `re`. All others are blocked by the guard.

---

## Difficulty Standards

### Easy

- Single core pandas operation
- 1–2 DataFrames, no joins
- Expected solution: 1–3 method chains
- Skills: filtering, selecting columns, sorting, basic aggregation, null handling, string ops, renaming, simple assignment

### Medium

- 2–3 concepts, directly related
- May involve joins (merge), reshaping (pivot, melt, stack), groupby+transform, rolling windows, or numpy operations
- Expected solution: 3–6 method chains, possibly split across a few steps
- Skills: merge, concat, pivot_table, melt, groupby+transform, rolling, rank, cut/qcut, numpy broadcasting, datetime ops

### Hard

- Multi-step pipeline with at least 2 dependent transformations
- Non-obvious chaining, numpy-pandas interplay, or performance considerations
- Expected solution: 5+ steps, may use temporary intermediate DataFrames
- Skills: named aggregation, time-series resampling, cumulative ops, cross-tab, stack/unstack, custom aggregation, vectorised patterns (avoid apply for performance)

---

## Question JSON Schema

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
  "expected_code": "import pandas as pd\n\ndef solve(df_users):\n    return (\n        df_users[df_users['country'] == 'US']\n        .sort_values('user_id')\n        .reset_index(drop=True)\n    )",
  "solution_code": "import pandas as pd\n\ndef solve(df_users):\n    return (\n        df_users[df_users['country'] == 'US']\n        .sort_values('user_id')\n        .reset_index(drop=True)\n    )",
  "explanation": "Boolean indexing (`df[df['col'] == value]`) selects rows matching the condition. `.sort_values('user_id')` ensures deterministic output order. `.reset_index(drop=True)` resets the integer index so it starts at 0.",
  "hints": [
    "Use boolean indexing: df[df['col'] == value]",
    "Use .sort_values('user_id').reset_index(drop=True) to order and reset the index"
  ],
  "concepts": ["boolean indexing", "sort_values", "reset_index"]
}
```

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | int | Yes | easy 5001–5999, medium 6001–6999, hard 7001–7999 |
| `order` | int | Yes | 1-based display order |
| `topic` | string | Yes | Always `"python_data"` |
| `title` | string | Yes | ≤ 50 chars |
| `difficulty` | string | Yes | `"easy"` / `"medium"` / `"hard"` |
| `description` | string | Yes | State the problem clearly. Name available DataFrame variables. Specify sort order and which columns to include. |
| `dataset_files` | array | Yes | CSV filenames from `backend/datasets/`. Used for schema validation. |
| `schema` | object | Yes | Maps table name → column list. Must match actual CSV headers. |
| `dataframes` | object | Yes | Maps variable name → CSV filename. These are the kwargs passed to `solve()`. |
| `starter_code` | string | Yes | Includes `import pandas as pd` (+ `import numpy as np` if needed). Always ends with `pass`. |
| `expected_code` | string | Yes | Trusted, correct solution. Evaluated without sandbox. |
| `solution_code` | string | Yes | Formatted solution shown to user after correct solve. |
| `explanation` | string | Yes | Explain each step. Reference pandas methods by name. |
| `hints` | array | No | 1–2 progressive hints. |
| `concepts` | array | No | 1–3 semantic tags: pandas method names, numpy patterns. |

### `dataframes` field

Maps the Python variable name (what appears in `solve()`'s parameters) to a CSV file in `backend/datasets/`:

```json
"dataframes": {
  "df_users": "users.csv",
  "df_orders": "orders.csv"
}
```

The harness loads each CSV as `pd.read_csv(path)` and calls `solve(df_users=..., df_orders=...)`.

### Evaluation

User's `solve(**dataframes)` result and `expected_code`'s `solve(**dataframes)` result are both passed through `normalize_dataframe()` from `evaluator.py`:
- Column names lowercased
- Columns sorted alphabetically
- Floats rounded to 5 decimal places
- NULLs / NaN → canonical string "NULL"
- Rows sorted deterministically (unless expected result has an inherent order due to specific sort requirement)

For numpy array results, the harness wraps in `pd.DataFrame({'result': arr})` before normalization.

---

## Available DataFrames (from datasets)

| Variable name | CSV | Rows | Key columns |
|---|---|---|---|
| `df_users` | users.csv | 600 | user_id, name, email, country, signup_date, plan, status |
| `df_categories` | categories.csv | 16 | category_id, name, parent_id |
| `df_products` | products.csv | 260 | product_id, name, category_id, price, launch_date |
| `df_orders` | orders.csv | 4200 | order_id, user_id, order_date, status, total_amount |
| `df_order_items` | order_items.csv | 12665 | item_id, order_id, product_id, quantity, unit_price |
| `df_payments` | payments.csv | 4737 | payment_id, order_id, amount, status, payment_date |
| `df_sessions` | sessions.csv | 9000 | session_id, user_id, start_time, end_time, device |
| `df_events` | events.csv | 44964 | event_id, user_id, event_type, timestamp, properties |
| `df_support_tickets` | support_tickets.csv | 1300 | ticket_id, user_id, subject, status, created_at |
| `df_departments` | departments.csv | 10 | department_id, name, manager_id |
| `df_employees` | employees.csv | 180 | employee_id, name, department_id, salary, hire_date |

Only include the DataFrames a question actually needs in `dataframes`.

---

## MVP Question Bank — 30 Questions

### Easy (10) — IDs 5001–5010

| ID | Title | Skill | DataFrames |
|---|---|---|---|
| 5001 | Filter US Users | Boolean indexing (single condition) | df_users |
| 5002 | High-Value Orders | Boolean indexing (multiple conditions) | df_orders |
| 5003 | Select Product Columns | Column selection + rename | df_products |
| 5004 | Top 10 Products by Price | sort_values + head | df_products |
| 5005 | Order Status Counts | value_counts | df_orders |
| 5006 | Users with Missing Email | isnull / boolean indexing | df_users |
| 5007 | Fill Missing Country | fillna | df_users |
| 5008 | Gmail Users | str.contains | df_users |
| 5009 | Revenue per Order Status | groupby + agg (sum) | df_orders |
| 5010 | Unique Countries | drop_duplicates + sort | df_users |

### Medium (10) — IDs 6001–6010

| ID | Title | Skill | DataFrames |
|---|---|---|---|
| 6001 | Orders with User Info | merge (inner join) | df_orders, df_users |
| 6002 | Users with No Orders | merge (left join + isna anti-join) | df_users, df_orders |
| 6003 | Monthly Revenue | groupby on datetime + agg | df_orders |
| 6004 | Product Revenue Pivot | pivot_table | df_order_items, df_products |
| 6005 | Add User Avg Order to Each Row | groupby + transform | df_orders |
| 6006 | 7-Day Rolling Revenue | rolling window (7) + sum | df_orders |
| 6007 | Rank Products by Price per Category | rank() within group | df_products |
| 6008 | Revenue Contribution % | numpy broadcasting (arr / arr.sum()) | df_orders |
| 6009 | Orders by Month-Year | pd.to_datetime + dt accessor | df_orders |
| 6010 | Price Buckets | pd.cut | df_products |

### Hard (10) — IDs 7001–7010

| ID | Title | Skill | DataFrames |
|---|---|---|---|
| 7001 | Monthly Cohort Retention | Multi-step pipeline: merge, groupby, pivot | df_users, df_orders |
| 7002 | Revenue Percentile by Category | Named aggregation + percentile | df_order_items, df_products |
| 7003 | 30-Day Moving Avg Revenue | Time-series resampling + rolling | df_orders |
| 7004 | User Revenue Rank (no apply) | Vectorised: merge + groupby + rank | df_users, df_orders |
| 7005 | Cumulative Revenue by User | groupby + cumsum | df_orders |
| 7006 | Order Count vs Revenue Correlation | numpy corrcoef | df_orders |
| 7007 | Support Ticket Resolution Rate | Conditional groupby + pivot | df_support_tickets |
| 7008 | Employee Salary Distribution | numpy histogram + bin labels | df_employees |
| 7009 | Cross-Tab: Country × Status | pd.crosstab | df_users |
| 7010 | Stack/Unstack Order Status × Month | stack + unstack + fillna | df_orders |

---

## Authoring Rules

1. **`solve()` must accept DataFrame kwargs matching `dataframes` keys exactly.** Signature must be `def solve(df_users):` or `def solve(df_users, df_orders):` etc. No `*args`, no `**kwargs`.

2. **`solve()` must return a pandas DataFrame.** Numpy array results are accepted but will be wrapped in `pd.DataFrame({'result': arr})` — document this in the description if used.

3. **`expected_code` must be self-contained** — it includes its own imports and works without any global state.

4. **Sort the result deterministically.** Always end with `.sort_values([...]).reset_index(drop=True)` or equivalent so normalization is consistent.

5. **State the expected columns in the description.** "Return a DataFrame with columns: user_id, name, country."

6. **State sort order in the description.** "Sort by order_id ascending." If order doesn't matter, say "order does not matter."

7. **Use only the DataFrames listed in `dataframes`.** Do not reference columns not in `schema`.

8. **Concepts are pandas/numpy method names**, lowercase. E.g. `"groupby"`, `"merge"`, `"rolling"`, `"boolean indexing"`, `"pivot_table"`.

9. **Avoid `apply()` in easy/medium expected solutions** unless the question is specifically teaching `apply`. Prefer vectorised operations.

10. **Test with the actual CSV data.** Run your `expected_code` locally against the real CSVs and verify the result makes sense.
