# SQL Track

> **Authoring rule, no exceptions:** Every SQL question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/questions/*.json` bypass the difficulty arc, the concept-taxonomy contract, and the verification checklist — and are the largest historical source of content drift on this platform. If you are about to hand-edit a question file, stop and invoke the agent instead.

## What this track trains

A working data professional does not get rewarded for syntactically clever SQL. They get rewarded for **asking the right business question and translating it into a deterministic, defensible data answer** — one that survives review, doesn't double-count, doesn't quietly miss edge cases, and produces a number a stakeholder can act on.

The SQL track exists to build that translation skill: business question → schema reading → data shape → query → defensible result. Every question should make the candidate think about *which* tool fits, *why* a join direction matters here, *what* the right grain is, *whether* the metric definition is even unambiguous. Syntax knowledge is the entry fee, not the test.

> *Datathink philosophy applied:* The kind of analyst who matters at week 200 on the job isn't the one who memorised every window-function frame — it's the one who reads a stakeholder's question, names the ambiguity, picks a grain on purpose, defends the denominator, and notices when the data quality is suspect before the report ships.

## Modality

**Executable problem-solving.** DuckDB execution. Parser-based read-only validation. 3-second query timeout. 200-row output cap. Both candidate's query and reference query run; DataFrames normalised and compared.

## Datasets (DuckDB, loaded from CSV at startup)

The SQL track works exclusively against the 11-table business schema. **Never invent columns or tables.** Schemas are validated against committed CSV headers at catalog load.

| Table | Key columns |
|---|---|
| `users` | user_id, name, email, signup_date, country, acquisition_channel, plan_tier, is_active |
| `orders` | order_id, user_id, order_date, status, gross_amount, discount_amount, net_amount, payment_status |
| `order_items` | order_item_id, order_id, product_id, quantity, unit_price, line_amount |
| `products` | product_id, product_name, category_id, brand, price, launch_date, is_active |
| `categories` | category_id, category_name, parent_category |
| `payments` | payment_id, order_id, payment_date, payment_method, amount, status |
| `sessions` | session_id, user_id, session_start, device_type, traffic_source, country |
| `events` | event_id, session_id, user_id, event_time, event_name, product_id |
| `employees` | employee_id, employee_name, email, salary, department_id, hire_date, country |
| `departments` | department_id, department_name, region |
| `support_tickets` | ticket_id, user_id, created_at, issue_type, priority, status, resolution_hours |

Full row counts and intentional edge cases (NULLs, duplicates, orphans): see [`docs/datasets.md`](../datasets.md).

## ID range (TXNNN scheme)

`T=1` for SQL. Practice and `mock_only: true` questions share the same space within each difficulty file; mock-only IDs allocate at the top of the range.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 11001–11999 | `backend/content/questions/easy.json` |
| Medium | 12001–12999 | `backend/content/questions/medium.json` |
| Hard | 13001–13999 | `backend/content/questions/hard.json` |

Samples use a separate `TXS` 3-digit format (`111–133`) in `backend/content/questions/sample/`. Never give a sample a 5-digit ID.

## Difficulty vocabulary (where complexity lives)

| Tier | Reasoning depth | Allowed constructs | What's out of bounds |
|---|---|---|---|
| **Easy** | One core concept (max two if tightly coupled). Single-step logic. Unambiguous output. | SELECT/WHERE/ORDER BY, DISTINCT, single-column GROUP BY, basic aggregates, ONE INNER JOIN, IS NULL/COALESCE, simple STRFTIME, IN/BETWEEN/LIKE, introductory single-CTE | Window functions, HAVING, subqueries, multi-table joins |
| **Medium** | 2–3 related concepts. The reasoning is recognising *which tool fits*. Multi-step: aggregate→filter, or join→aggregate→rank. | 2–4 table JOINs (INNER + LEFT + FULL OUTER), GROUP BY + HAVING, CASE WHEN, IN/EXISTS subqueries, one-step LAG, date arithmetic | Multi-CTE pipelines (3+), full window-function suites, sessionization |
| **Hard** | 2+ dependent reasoning steps. Trade-offs. Edge-case awareness. Production-grade thinking. | Window functions (ROW_NUMBER/RANK/DENSE_RANK/LAG/LEAD/SUM OVER/ROWS BETWEEN/RANGE BETWEEN), multi-CTE pipelines, correlated subqueries, sessionization, cohort retention, funnel analysis, Pareto, state machines, gaps-and-islands | "Hard because of unrelated piled-on requirements" — that's not hard, that's noise |

**Difficulty comes from reasoning complexity, never from syntactic obscurity.** If you can make a question harder by removing a clarification, it was ambiguous, not hard.

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | SELECT/WHERE/ORDER BY → GROUP BY + basic aggregates → DISTINCT + NULL handling + COALESCE → one INNER JOIN → STRFTIME / date bucketing → CASE WHEN → introductory CTE |
| Medium | Multi-table JOINs (INNER + LEFT) → GROUP BY + HAVING → IN/EXISTS subqueries → CASE WHEN + aggregation → LAG one-step delta → date arithmetic and range conditions → 3–4 table pipelines |
| Hard | ROW_NUMBER/RANK/DENSE_RANK (deduplication, top-N) → running totals + moving averages → LAG/LEAD gap detection → multi-CTE pipelines (2–3 layers) → sessionization → correlated subqueries → cohort retention → funnel + ROWS/RANGE frames → Pareto / threshold filtering → state machine detection |

Curriculum arc placement is enforced by the `order` field. **Order is not file-append position** — it is pedagogical position. Prerequisites must appear at lower `order` values. No cold introductions at hard tier of concepts that never appeared at medium. Spiral reinforcement (re-entering an earlier concept from a new angle) is the curriculum, not redundancy.

## Concept families

Full registry: [`docs/concept-taxonomy.md` → SQL section](../concept-taxonomy.md#sql--concept-families).

22 canonical families. Every `concepts` tag in every SQL question must map to one via the resolution algorithm in the taxonomy doc. The SQL blocklist forbids mechanic-name tags (`JOIN`, `GROUP BY`, `WINDOW FUNCTION`, etc.) — describe the *reasoning* the construct enables.

Three families are new in the 2026-05 refactor, surfacing reasoning patterns the bank had only implicit:

- **`METRIC INTERPRETATION & DENOMINATOR CHOICE`** — when "active user" or "revenue" has multiple defensible definitions, picking and defending one
- **`DATA QUALITY SKEPTICISM`** — duplicate / orphan / NULL anomaly detection as a reasoning skill, not an afterthought
- **`DOUBLE-COUNTING DETECTION`** — fan-out from joins, inflated metrics, grain mismatch debugging

Mock-only content authored from now on must lean into these three families to address the gap.

## Authoring allocation matrix

This is the contract that prevents ad-hoc "practice or mock?" decisions during authoring.

| Question kind | Where it lives | When to author |
|---|---|---|
| **Practice easy (free on-ramp)** | `easy.json` no `mock_only` | When the question teaches one core SQL concept clearly. First-time exposure. Curriculum role: build vocabulary. |
| **Practice medium (free with threshold unlock)** | `medium.json` no `mock_only` | When the question composes 2–3 concepts and reinforces prior tier. Curriculum role: build reasoning. |
| **Practice hard (free with capped unlock, Pro full)** | `hard.json` no `mock_only` | When the question requires dependent reasoning steps. Curriculum role: build production-grade thinking. |
| **Practice path content (free shortcut paths)** | Existing practice IDs referenced in `backend/content/paths/*.json` | When you are building a curated sequence. Do not author new questions just for paths — reference existing practice content. |
| **Mock-only medium (Pro/Elite, single)** | `medium.json` with `mock_only: true` | When the question is fresh business angle not in practice catalog, no chain. Targets `METRIC INTERPRETATION`, `DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`, ambiguity-heavy framing. |
| **Mock-only hard (Pro/Elite, single)** | `hard.json` with `mock_only: true` | Same as medium, raised difficulty. Often `reverse` or `debug` type. |
| **Mock-only chain parent + follow-ups (Pro/Elite, sets up Interview Loop)** | Parent in `medium.json` or `hard.json` with `follow_ups: [...]`; children in same difficulty file with `mock_only: true`, `parent_id`, `follow_up_dimension` | When the question has natural interviewer pivots — exclude refunded orders, change time grain, scale up, address dirty data. Length 2–4 (parent + 1–3 follow-ups). Each follow-up uses a different `follow_up_dimension`. Powers Interview Loop. |

**Easy mock-only: never.** Easy mocks for Free draw from the practice pool only; Pro/Elite get easy via the same practice pool when they want them. There's no business case for mock-only easy content.

**Content cap:** ≤15% of a mock-only batch may reinforce a concept family already in the practice bank at that difficulty. The other 85%+ must cover fresh business angles using existing datasets — different KPIs, time windows, multi-table relationships the practice bank doesn't explore.

## Anti-patterns specific to SQL

- **One-liner whose only challenge is knowing a function name** — `SELECT AVG(salary) FROM employees`. Reject.
- **Trivial joins that add no analytical complexity** — joining `categories` only because the question mentions a category name when the category_id column on `products` was already there. Reject.
- **Multiple defensible interpretations of expected output** — "top products" without defining top. Reject.
- **Non-deterministic output** — ranking ties without a tie-breaker rule. Reject.
- **Artificial multi-CTE pipelines** — chaining 5 CTEs when 2 would do, just to look harder. Reject.
- **Stacking unrelated requirements to inflate difficulty** — "find top users AND their longest session AND their most recent ticket AND..." That's noise, not depth.
- **Mocking with practice-bank concept overlap > 15%** — defeats the purpose of mock-only content.

## DuckDB syntax requirements

This platform runs DuckDB — generic SQL is **not** acceptable.

| Operation | Use | Do **not** use |
|---|---|---|
| Date bucketing | `STRFTIME('%Y-%m', order_date)` | `DATE_TRUNC` |
| Date arithmetic | `order_date::DATE + INTERVAL 7 DAY` | `DATE(x, '+7 days')` |
| Date diff | `julian(date2) - julian(date1)` | `JULIANDAY`, `DATEDIFF` |
| NULL-last ordering | `ORDER BY col ASC NULLS LAST` | (engine-specific equivalents) |
| String concat | `first_name \|\| ' ' \|\| last_name` | `CONCAT` (non-portable) |

Other style rules:
- Explicit `JOIN ... ON ...` (no comma joins, ever).
- Never `SELECT *` — name output columns.
- Use short aliases: `u` for users, `o` for orders, `p` for products.
- Include `ORDER BY` when result ordering is meaningful; omit when the evaluator's normalization makes it irrelevant.

## JSON schema

Standard practice or mock-only question:

```json
{
  "id": 12042,
  "order": 18,
  "title": "Monthly active users with first-order trigger",
  "difficulty": "medium",
  "description": "For each calendar month, count distinct users whose first order ever was placed in that month. Output columns: month (YYYY-MM), new_active_users. Order by month ascending.",
  "dataset_files": ["users.csv", "orders.csv"],
  "schema": {
    "users": ["user_id", "signup_date"],
    "orders": ["order_id", "user_id", "order_date", "status"]
  },
  "expected_query": "WITH first_orders AS (SELECT user_id, MIN(order_date) AS first_order_date FROM orders WHERE status = 'completed' GROUP BY user_id) SELECT STRFTIME('%Y-%m', first_order_date) AS month, COUNT(DISTINCT user_id) AS new_active_users FROM first_orders GROUP BY 1 ORDER BY 1;",
  "solution_query": "<readable annotated version producing identical results>",
  "explanation": "Step-by-step logic, why CTE-then-bucket is cleaner than nested aggregation, edge case for users with zero completed orders being excluded.",
  "hints": [
    "Compute each user's first qualifying order date before bucketing.",
    "Counting distinct user_id per bucket gives you the new-active count for that month."
  ],
  "concepts": ["LATEST STATE DERIVATION", "TIME-SERIES BUCKETING & ARITHMETIC", "CTE PIPELINE"],
  "companies": ["Stripe", "Airbnb"]
}
```

Mock-only with chain follow-ups:

```json
// Parent
{
  "id": 12380,
  "mock_only": true,
  "follow_ups": [12381, 12382],
  ...
}

// First follow-up
{
  "id": 12381,
  "mock_only": true,
  "parent_id": 12380,
  "follow_up_dimension": "business_rule_pivot",
  "description": "Same setup as the previous question. Now the finance team has redefined 'active' to exclude users whose only orders are refunded...",
  ...
}

// Second follow-up — different dimension from previous follow-up
{
  "id": 12382,
  "mock_only": true,
  "parent_id": 12380,
  "follow_up_dimension": "scale_pivot",
  "description": "Same business definition as the previous answer. Now the orders table holds 5 billion rows...",
  ...
}
```

Special types (mock-only):
- **`type: "reverse"`** — user sees a `result_preview` table (≤8 rows, ≤4 columns) and writes the query that produces it. The `expected_query` still evaluates.
- **`type: "debug"`** — `starter_query` has exactly one bug producing a stated `debug_error` (real DuckDB error string).
- **`framing: "scenario"`** — `description` carries a ≤3-sentence grounded business narrative without giving away the approach.

## Hints discipline

- 2 hints standard, max 3 on hard.
- Hints name the *approach or construct*, never the implementation.
- ✅ "Use a CTE to compute each user's first order date, then join back" — strategy
- ❌ "Write `WITH first_orders AS (SELECT user_id, MIN(order_date)...)`" — implementation
- The first hint must not contain the answer's key construct verbatim.

## Verification before commit

```bash
# 1. The query runs in DuckDB against real CSVs
cd backend && ../.venv/bin/python -c "
import duckdb
con = duckdb.connect(':memory:')
# load each CSV referenced in dataset_files...
con.execute(open('your_query.sql').read())
"

# 2. expected_query and solution_query produce identical results
# (eyeball or diff)

# 3. Full content validation
python scripts/validate_content.py

# 4. SQL evaluator tests
cd backend && ../.venv/bin/python -m pytest tests/test_evaluator.py -q
```

For `reverse` questions: also confirm `result_preview` exactly matches the live `expected_query` output (run it, copy values).

For `debug` questions: confirm `debug_error` matches the actual DuckDB error string when running `starter_query`.
