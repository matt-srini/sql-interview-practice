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

### Allowed business scenarios per tier

The construct table bounds the *tools*; this bounds the *feel*. Even easy questions resemble small real-world reporting/KPI tasks, never textbook SQL drills.

| Tier | Representative business scenarios |
|---|---|
| **Easy** | Monthly revenue by country · active vs inactive users · users with no orders · first purchase date per user · simple category-level sales summaries · basic duplicate detection. The challenge is interpreting the requirement correctly (filtering logic, aggregation grain, NULL handling, dedup intent) — not recalling syntax. |
| **Medium** | Monthly retention trends · top products by region · refund-adjusted revenue · users with declining activity · category contribution analysis · ticket-resolution KPI reporting · repeat-purchase behaviour · funnel drop-off summaries. The challenge is selecting the right analytical approach and sequencing logic (aggregation order, join direction/impact, WHERE vs HAVING, metric correctness). |
| **Hard** | Cohort retention · funnel conversion breakdowns · sessionization · Pareto revenue contribution · customer-lifecycle state transitions · experiment-impact analysis · anomaly investigation · churn-risk detection · rolling KPI trends · fraud/anomaly heuristics. These resemble senior-level analytics, product-analytics, experimentation, and data-investigation tasks — the kind a practicing analyst still faces years into the role. The challenge is decomposing a realistic business problem into logically correct stages under edge cases, ambiguity, and dirty data. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | SELECT/WHERE/ORDER BY → GROUP BY + basic aggregates → DISTINCT + NULL handling + COALESCE → one INNER JOIN → STRFTIME / date bucketing → CASE WHEN → introductory CTE |
| Medium | Multi-table JOINs (INNER + LEFT) → GROUP BY + HAVING → IN/EXISTS subqueries → CASE WHEN + aggregation → LAG one-step delta → date arithmetic and range conditions → 3–4 table pipelines |
| Hard | ROW_NUMBER/RANK/DENSE_RANK (deduplication, top-N) → running totals + moving averages → LAG/LEAD gap detection → multi-CTE pipelines (2–3 layers) → sessionization → correlated subqueries → cohort retention → funnel + ROWS/RANGE frames → Pareto / threshold filtering → state machine detection |

Curriculum arc placement is enforced by the `order` field. **Order is not file-append position** — it is pedagogical position. Prerequisites must appear at lower `order` values. No cold introductions at hard tier of concepts that never appeared at medium. Spiral reinforcement (re-entering an earlier concept from a new angle) is the curriculum, not redundancy.

## Concept families

Full registry: [`docs/concept-taxonomy.md` → SQL section](../concept-taxonomy.md#sql--concept-families).

26 canonical families. Every `concepts` tag in every SQL question must map to one via the resolution algorithm in the taxonomy doc. The SQL blocklist forbids mechanic-name tags (`JOIN`, `GROUP BY`, `WINDOW FUNCTION`, etc.) — describe the *reasoning* the construct enables.

Six families are new in the 2026-05 refactor, surfacing reasoning patterns the bank had only implicit. The first three are SQL-specific; the last three are shared with the Pandas track (and partially with PySpark) — same reasoning skill, transferable across executable analytics tracks:

- **`METRIC INTERPRETATION & DENOMINATOR CHOICE`** — when "active user" or "revenue" has multiple defensible definitions, picking and defending one
- **`DATA QUALITY SKEPTICISM`** — duplicate / orphan / NULL anomaly detection as a reasoning skill, not an afterthought
- **`DOUBLE-COUNTING DETECTION`** — fan-out from joins, inflated metrics, grain mismatch debugging
- **`METRIC RECONCILIATION`** — validating a computed metric against an independent source of truth (distinct from data-quality reasoning: this is about the *number*, not the *data*)
- **`OUTPUT SANITY VALIDATION`** — self-checking your own analytical output before declaring done; the discipline that separates senior practitioners from junior ones
- **`PERFORMANCE-AWARE ANALYTICS`** — choosing the more efficient analytical approach (scan reduction, pre-aggregation, cardinality control) without sacrificing correctness; distinct from engine-optimisation trivia

**Phase 2 (2026-05) status of these six families:**

Three are now **practice-covered** — the bank has tagged existing questions whose reasoning already fits, and new practice questions were authored:
- `DOUBLE-COUNTING DETECTION` — 3 practice questions (12065, 12066, 13050)
- `DATA QUALITY SKEPTICISM` — 4 practice questions (re-tagged from existing hard questions + 2 original)
- `METRIC RECONCILIATION` — 1 practice question (12032 — full-outer-join reconciliation)

Three are **mock-only realism lenses** — they appear only on `mock_only: true` questions where they co-occur with ≥1 practice-grounded family. They must never appear as a question's sole concept tag:
- `METRIC INTERPRETATION & DENOMINATOR CHOICE`
- `OUTPUT SANITY VALIDATION`
- `PERFORMANCE-AWARE ANALYTICS`

This three-way split is enforced by `_validate_mock_only_realism()` in `backend/scripts/validate_content.py`.

## Authoring allocation matrix

This is the contract that prevents ad-hoc "practice or mock?" decisions during authoring.

| Question kind | Where it lives | When to author |
|---|---|---|
| **Practice easy (free on-ramp)** | `easy.json` no `mock_only` | When the question teaches one core SQL concept clearly. First-time exposure. Curriculum role: build vocabulary. |
| **Practice medium (free with threshold unlock)** | `medium.json` no `mock_only` | When the question composes 2–3 concepts and reinforces prior tier. Curriculum role: build reasoning. |
| **Practice hard (free with capped unlock, Pro full)** | `hard.json` no `mock_only` | When the question requires dependent reasoning steps. Curriculum role: build production-grade thinking. |
| **Practice path content (curated walks)** | Existing practice IDs referenced in `backend/content/paths/*.json` | When you are building a curated sequence. Do not author new questions just for paths — reference existing practice content. See [`docs/content-authoring.md`](../content-authoring.md) §Paths for path semantics. |
| **Mock-only medium (Pro/Elite, single)** | `medium.json` with `mock_only: true` | When you can recombine medium-tier concepts the practice bank already teaches into a *fresh business scenario* (different KPI, time window, multi-table relationship), with mild ambiguity or dirty-data framing. No new concept families. The gap families (`METRIC INTERPRETATION`, `DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`) are natural fits *once practice teaches them* — until then, only recombine families with existing practice coverage. No chain. |
| **Mock-only hard (Pro/Elite, single)** | `hard.json` with `mock_only: true` | Same as medium, raised difficulty. Often `reverse` or `debug` type. Still recombines learned hard-tier reasoning under unseen framing — never debuts a concept. |
| **Mock-only chain parent + follow-ups (Pro/Elite, sets up Interview Loop)** | Parent in `medium.json` or `hard.json` with `follow_ups: [...]`; children in same difficulty file with `mock_only: true`, `parent_id`, `follow_up_dimension` | When the question has natural interviewer pivots — exclude refunded orders, change time grain, scale up, address dirty data. Length 2–4 (parent + 1–3 follow-ups). Each follow-up escalates exactly one `follow_up_dimension`, different from the previous. Powers Interview Loop. |

**Easy mock-only: never.** Easy is practice-only. Easy mocks for Free draw from the practice pool; Pro/Elite get easy via the same practice pool. There's no business case for mock-only easy content.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing, realism, and ambiguity — *not* new concepts. A mock-only question recombines previously-learned SQL reasoning in a business scenario the practice bank doesn't explore (fresh KPI, time window, relationship, stakeholder pressure, dirty data). It must **not** clone the framing of an existing practice question, and it must **not** introduce a concept family the practice curriculum hasn't already taught at that difficulty or lower. If a mock would need an untaught concept, author the practice question first.

## Coverage & sizing targets

These are the durable *targets* (what the bank ought to look like). For live counts (what it *is* right now) see the "Question bank current state" table in [`docs/content-authoring.md`](../content-authoring.md) and the content footprint in `CLAUDE.md`. **Targets are provisional — revisit against real Pro/Elite usage data.**

- **Practice: lean.** Roughly one teaching arc per family per applicable tier — grow only to (a) ground a gradable gap family or (b) fix a genuine arc break. Do **not** pad practice for volume; that fights the curriculum philosophy. Tier balance stays easy → medium → hard heavy enough to teach progression (no thin hard tier).
- **Mock-only: sized for the power-user runway.** A serious candidate works most of practice, then does heavy mock for an interview months out; chains are consumed once ever, so inventory must (a) exceed peak multi-month consumption and (b) **span every interview-relevant medium/hard family** — order ~150–180 mock-only questions. Medium + hard only (easy is practice-only), **hard-skewed (~60/40)**, with **~⅓ of questions as chain members** (parents + follow-ups feeding Interview Loop).
- **Mock distribution is weighted by interview importance, not spread evenly.** Core interview-defining families (window functions, ranking, cohort, funnel, sessionization, double-counting, multi-table fan-out, CTE pipelines) carry the most mock weight; supporting families (set ops, reconciliation, the realism lenses) carry less. The blind spot to watch: joins / fan-out / double-counting.

## Anti-patterns specific to SQL

- **One-liner whose only challenge is knowing a function name** — `SELECT AVG(salary) FROM employees`. Reject.
- **Trivial joins that add no analytical complexity** — joining `categories` only because the question mentions a category name when the category_id column on `products` was already there. Reject.
- **Multiple defensible interpretations of expected output** — "top products" without defining top. Reject.
- **Non-deterministic output** — ranking ties without a tie-breaker rule. Reject.
- **Artificial multi-CTE pipelines** — chaining 5 CTEs when 2 would do, just to look harder. Reject.
- **Stacking unrelated requirements to inflate difficulty** — "find top users AND their longest session AND their most recent ticket AND..." That's noise, not depth.
- **Mock-only that clones a practice question's framing** — same scenario with cosmetic changes defeats the purpose. Recombine learned concepts in a genuinely fresh business scenario instead.
- **Mock-only that introduces an untaught concept** — mock evaluates *transfer* of learned reasoning; a concept the practice curriculum never taught has no business debuting in a mock. Author the practice question first.

## DuckDB syntax requirements

This platform runs DuckDB — generic SQL is **not** acceptable.

| Operation | Use | Do **not** use |
|---|---|---|
| Date bucketing (string output) | `STRFTIME('%Y-%m', order_date)` | `DATE_TRUNC` for string-format results |
| Date bucketing (DATE-type output) | `DATE_TRUNC('month', order_date)` | `STRFTIME` when you need a proper DATE for downstream date arithmetic |
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
