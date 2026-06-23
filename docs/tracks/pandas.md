# Pandas Track

> **Authoring rule, no exceptions:** Every Pandas question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/pandas_questions/*.json` bypass the difficulty arc, the concept-taxonomy contract, and the pandas-idiomatic discipline.

## What this track trains

A data analyst or scientist who *thinks in pandas* writes meaningfully different code from one who *transliterates SQL into pandas*. The Pandas track exists to train pandas-native reasoning: when does `merge` beat `concat`, when does `transform` beat `agg`, when does the `.dt` accessor save you 50 lines of date parsing, when does an explicit dtype save you 4 GB of RAM. Idiomatic pandas is also fast pandas; the two are not separate concerns.

> *Datathink philosophy applied:* The analyst who runs `df.apply(lambda x: …)` on 10 million rows is the analyst who waits 40 minutes for an answer that should've taken 4 seconds. We're training the practitioner who recognises the row-wise antipattern, picks the vectorized path, and knows *why* — not the one who memorised method signatures.

## Modality

**Executable problem-solving.** Subprocess-sandboxed Python execution with the candidate's function called against pre-loaded DataFrames. 12-second timeout (data mode — grading compares the full result and a large output serializes a few MB). 512 MB RLIMIT_AS. The **full** output DataFrame is compared to expected via `normalize_dataframe()` (from `evaluator.py`) followed by `DataFrame.equals()`; only a 200-row preview is returned to the client. Normalization steps applied to both candidate and expected output before comparison:
1. Column names lowercased
2. Columns sorted alphabetically
3. Float columns rounded to 5 decimal places (eliminates floating-point arithmetic noise)
4. All values cast to canonical string — NULL variants become `"NULL"`, whole-number floats become their integer string (`5.0` → `"5"`); as a consequence, **dtype differences are not visible to the grader**
5. Rows sorted lexicographically (unless the question explicitly tests ORDER BY output, in which case row order is preserved as-is)
6. Index reset to `RangeIndex`

## Schema essentials (function shape + datasets)

Each question defines a top-level `def solve(...)` that takes one or more pre-loaded DataFrames and returns a DataFrame.

```python
def solve(orders: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    ...
```

DataFrames are loaded from the same 11-table business schema as the SQL track (see [`docs/datasets.md`](../datasets.md)). Schemas are validated against committed CSV headers at catalog load.

**Schema field ordering:** The `schema` column list for each DataFrame must follow the **exact CSV header order** — not a subset, not a reordering. Users read the schema panel top-to-bottom as a `df.info()` analogue; wrong column position causes confusion even when no column is missing. Verify with `head -1 datasets/<file>.csv` and match the list exactly.

Required output discipline:
- **Always** end with `.reset_index(drop=True)` unless the index *is* the result.
- Column names and order must match the expected output exactly.
- Determinism: explicit `.sort_values(...)` whenever a meaningful order is implied.
- **Datetime output handling (platform-managed, like SQL):** You **may** return `datetime64` / `Timestamp` / `date` columns directly. The sandbox harness serializes them to ISO strings (`python_sandbox_harness._json_default`, mirroring the SQL evaluator's `_to_json_native`), and the shared grading comparator (`evaluator.normalize_dataframe` → `_canonicalize_temporal`) **date-normalizes** before comparison: a `Timestamp` at midnight, a `date`, and an ISO date string all compare equal, and a `T` vs space separator is tolerated. So a candidate is **not** penalized for a trivial representation difference (e.g. returning a Timestamp where the reference used `.dt.date`). **Genuine** differences are still enforced — a real time-of-day (`23:28:10`) is not collapsed, and a coarser granularity that the prompt asks for (e.g. a month bucket `'2024-01'`) must still be produced explicitly. Only stringify in `expected_code` when the prompt asks for a **derived/formatted** value (e.g. `.dt.strftime('%Y-%m')` for a month label); for a plain date, returning the date is fine. Tip: for a date-concept column, prefer `.dt.date` or `.dt.strftime('%Y-%m-%d')` so the *displayed* expected output reads as `2024-01-05` rather than `2024-01-05T00:00:00` — cosmetic only, grading is identical either way.
- **Row count (platform-managed):** A per-row transformation over the full dataset is fine — `dropna`, derive-a-column, per-row datetime, window gaps, as-of enrichment, etc. The grader compares the **full** result; the client receives only a **~200-row preview** (`python_evaluator.DATA_PREVIEW_ROWS`, with `total_rows`/`truncated` so the panel shows "showing first 200 of N"). A high safety cap (`_MAX_DATA_RESULT_ROWS = 100,000`) only guards against pathological outputs — the largest dataset (events ≈ 45 k rows) sits well under it. So **do not aggregate or `head(N)` a result just to shrink it** — only aggregate when an aggregate *is* the question's intent. (Data-mode submissions get a roomier 12s timeout since a large result serializes a few MB for the grade.)

## ID range (TXNNN scheme)

`T=3` for Pandas.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 31001–31999 | `backend/content/pandas_questions/easy.json` |
| Medium | 32001–32999 | `backend/content/pandas_questions/medium.json` |
| Hard | 33001–33999 | `backend/content/pandas_questions/hard.json` |

Pandas has **dedicated sample questions** in `backend/content/sample_questions/pandas.json` (IDs 311–313 easy, 321–323 medium, 331–333 hard). Sample questions are completely separate from the practice and mock pools and must never duplicate practice content.

## Difficulty vocabulary

| Tier | Reasoning depth | Patterns | What's out |
|---|---|---|---|
| **Easy** | One pandas-idiomatic operation. The candidate immediately knows which accessor to reach for. | `.str` accessor, `.dt` accessor, single `groupby` + aggregate, `value_counts`, `pd.cut` for binning, simple boolean indexing | Multi-table merges, pivot_table, MultiIndex |
| **Medium** | 2–3 related operations, the reasoning is *recognising the pandas-idiomatic shape*. | `merge` with explicit `how` + `on`, `pivot_table`, `groupby.transform`, `rolling` / `expanding`, `resample`, `rank(pct=True)`, named aggregation | MultiIndex slicing, full memory optimization |
| **Hard** | Multi-step pipeline. Memory awareness. Cohort/funnel-style transforms. | `MultiIndex` / `.xs()`, memory optimization via dtypes, `groupby.apply` (where unavoidable), cohort/funnel pipelines, custom `agg` with multiple functions per column, dtype-driven optimization | "Hard because the SQL solution would be hard" — wrong track |

**Critical:** every question must test *pandas-idiomatic thinking*. If a question is equally elegant in SQL, it doesn't belong here. The track's purpose is teaching pandas as a tool with its own grammar — not as a SQL substitute.

### Representative tasks per tier

Difficulty controls reasoning depth, never licenses method-recall drills. Even easy questions read like a small real data-wrangling task on a realistic frame.

| Tier | Representative tasks |
|---|---|
| **Easy** | Parse a timestamp column and bucket by month · clean a `.str` field · count category frequencies · bin a numeric column · simple boolean-filtered summary. Small realistic wrangling, not "what's the keyword for X". |
| **Medium** | Join two frames and compute a per-group metric · pivot sales by region/month · per-group feature via `transform` · rolling/resampled time series · percentile rank within group. Dashboard / KPI-style framing. |
| **Hard** | Cohort retention pipeline · funnel with time-bucketed dropoff · memory-aware transform on a wide frame · multi-step lifecycle/state pipeline. Production-realistic analytics, memory and dtype awareness. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | `.dt` / `.str` accessors → boolean indexing → single-column `groupby` + agg → `value_counts` / `nunique` → `pd.cut` / `pd.qcut` binning → simple derived columns via `.assign` |
| Medium | `merge` (inner / left / outer) → `pivot_table` (with margins) → `groupby.transform` for per-group features → `rolling` / `expanding` windowed agg → `resample` for time-based windowing → `rank(pct=True)` for percentile rank → named aggregation |
| Hard | `MultiIndex` + `.xs()` slicing → memory optimization (dtype choice, `category`) → cohort / funnel pipelines → `groupby.apply` when justified → percentage-over-group via `transform('sum')` → dtype-driven optimization |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Pandas section](../concept-taxonomy.md#pandas--concept-families).

21 families (Phase 2 complete). Six were added in the 2026-05 refactor — three practice-grounded, three mock-only realism lenses. The first is Pandas-native; the other five are shared with the SQL track (same reasoning, same names — explicit cross-track alignment per the executable-track reusability principle):

- **`MEMORY & VECTORIZATION REASONING`** (Pandas-native) — vectorize over `apply(lambda)`, dtype-driven memory choices, chunk-reading large files. No direct SQL analogue.
- **`METRIC INTERPRETATION & DENOMINATOR CHOICE`** (shared with SQL) — picking and defending a metric definition under ambiguous business framing
- **`DATA QUALITY SKEPTICISM`** (shared with SQL + PySpark) — duplicate / orphan / NULL / dtype-anomaly detection as a reasoning skill
- **`DOUBLE-COUNTING DETECTION`** (shared with SQL + PySpark) — fan-out from one-to-many merges, inflated metrics, grain mismatch
- **`OUTPUT SANITY VALIDATION`** (shared with SQL + PySpark) — self-checking pipeline output: shape assertion, dtype assertion, plausibility check
- **`PERFORMANCE-AWARE ANALYTICS`** (shared with SQL) — broader analytical-cost reasoning beyond vectorize-vs-apply: pre-aggregation, cardinality control, scan reduction

Two existing families renamed to align with SQL: `DEDUPLICATION & DISTINCT COUNTING` → `DEDUPLICATION LOGIC`, and `RANKING & TOP-K` → `RANKING & TOP-N PER GROUP`. Existing tags resolve unchanged through preserved match patterns.

**2026-05 classification (locked):**

| Family | Class | Rationale |
|---|---|---|
| `MEMORY & VECTORIZATION REASONING` | **practice-grounded** | Gradable when a naive `apply(lambda)` approach returns wrong values or crashes — output correctness is verifiable. **Caveat:** the grader normalizes all values to strings (step 4 above), so dtype-only changes (e.g. `.astype('category')`) are invisible; questions must be framed around vectorized output correctness, not dtype proof. Anchored by 33021, 32049, 33038. |
| `DATA QUALITY SKEPTICISM` | **practice-grounded** | Debug-format questions grade cleanly (merge fan-out, grain mismatch); anchored by 32050. |
| `DOUBLE-COUNTING DETECTION` | **practice-grounded** | "Why does this merge inflate my user count?" is a gradable debugging exercise; anchored by 32051. |
| `METRIC INTERPRETATION & DENOMINATOR CHOICE` | **mock-only realism** | Choice of denominator is a judgment call, not a scorable output diff. Co-tag rule enforced. |
| `OUTPUT SANITY VALIDATION` | **mock-only realism** | Self-checking code inside a `solve()` function (shape assertions, null checks, plausibility guards) is invisible to the grader — only the returned DataFrame is compared via `normalize_dataframe()` + `DataFrame.equals()`. Co-tag rule enforced. |
| `PERFORMANCE-AWARE ANALYTICS` | **mock-only realism** | "Should you filter before joining?" is analytical-cost reasoning — not a scorable output. Co-tag rule enforced. |

Blocklist rejects method-name tags (`groupby`, `merge`, `pivot_table`, `apply`). Describe the *reasoning*.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One idiomatic operation. Build accessor familiarity. |
| Practice medium | `medium.json` no `mock_only` | Compose 2–3 operations. Idiom recognition. |
| Practice hard | `hard.json` no `mock_only` | Multi-step pipeline. Memory and dtype awareness. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real-world framing: dirty CSV reads, mixed dtypes, missing-data realism. Recombine families with existing practice coverage (e.g. `MISSING VALUE STRATEGY`, `DEBUG PANDAS`). `MEMORY & VECTORIZATION REASONING` is a fit *only once practice teaches it*. |
| Mock-only hard | `hard.json` with `mock_only: true` | Production-realistic pipelines: cohort analysis with dropoff, funnel with bucket time, retention curve. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (50 GB file), business rule (now exclude returns), data quality (mixed-dtype column), performance (apply → vectorize). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing, realism, and dirty-data conditions — not new operations. A mock-only question recombines pandas reasoning the practice bank already teaches at that difficulty (or lower) in a fresh business scenario; it must not clone an existing practice question and must not debut a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Coverage & sizing targets

These are the durable *targets* (what the bank ought to look like). For live counts (what it *is* right now) see the "Question bank current state" table in [`docs/content-authoring.md`](../content-authoring.md) and the content footprint in `CLAUDE.md`. **Targets are provisional — revisit against real Pro/Elite usage data.**

- **Practice: lean (~85–95 questions, ~⅓ easy / ~⅖ medium / ~¼ hard; currently 93: 28 easy / 40 medium / 25 hard).** Roughly one teaching arc per family per applicable tier. Grow only to (a) ground a new gradable family or (b) fix a genuine arc break. Do **not** pad practice for volume — that fights the curriculum philosophy. The hard tier is intentionally smaller: multi-step pipelines are sparse by design.
- **Mock-only: ~132, medium + hard only, ~69:63 m:h skew.** That ratio (1:0.9) now slightly favors medium over hard. The inventory multiple over practice is ~1.4×; a healthy band is 1.0×–1.5×. Easy is practice-only — never. **~⅓ of mock questions should be chain members** (parents + follow-ups feeding Interview Loop).
- **Realism vs. practice-grounded split.** `MEMORY & VECTORIZATION REASONING` is practice-grounded and Pandas-native — gradable when vectorized correctness is the measurable signal (a broken `apply(lambda)` returns wrong values or crashes; the grader catches that). Note: dtype-only changes are erased by the string normalization in step 4 and are not visible to the grader. The three mock-only realism families (`METRIC INTERPRETATION & DENOMINATOR CHOICE`, `OUTPUT SANITY VALIDATION`, `PERFORMANCE-AWARE ANALYTICS`) must **co-occur with ≥ 1 practice-grounded family** on every question that uses them.
- **Quality risk: SQL-in-Python clones.** Any question whose reference solution is idiomatic SQL transliterated into pandas (`groupby + merge + rename` where a single `pivot_table` would do) must be dropped, not padded. The track's purpose is teaching pandas as a tool with its own grammar; volume built on SQL-shaped problems actively harms the curriculum.

### Load-bearing family exception: GROUPED AGGREGATION

**GROUPED AGGREGATION currently appears on ~59–60% of practice questions, which exceeds the 50% ceiling (rule 3).** This is a documented, defended exception — not a coverage drift.

**Reasoning-depth defence:** `groupby()` is the central computational primitive of the Pandas track. Every meaningful aggregation, temporal bucketing, ranked-within-group pattern, and metric computation runs through it. Unlike SQL where GROUP BY is one clause among many, in pandas the groupby/split-apply-combine paradigm is the grammar itself — a practitioner who cannot reason about groupby mechanics, key selection, `as_index`, named aggregation, and multi-level groupby cannot use pandas professionally. The families that are *distinct* from GROUPED AGGREGATION (WINDOW & ROLLING, RESHAPING & PIVOT, DATETIME OPERATIONS, etc.) all routinely compose with groupby. A question about rolling averages by cohort is primarily WINDOW & ROLLING — but it still uses groupby to partition. Tagging both families on such questions is correct; GROUPED AGGREGATION's high share reflects this composition reality, not curriculum bloat.

**Why remediation would harm the curriculum:** Aggressively removing GROUPED AGGREGATION tags to get below 50% would either (a) drop the primary family from questions where groupby *is* the reasoning surface, mislabelling them, or (b) require manufacturing a large batch of non-groupby practice questions to dilute the share, which would pad volume against the track's stated anti-padding philosophy.

**Governance:** The validator treats this as a soft warning. Any future audit noting this warning should cross-reference this section and confirm the share is still driven by the composition reality above, not by untagged questions that should carry additional families (which would dilute the share naturally).

## Anti-patterns specific to Pandas

- **SQL-in-Python solutions** — using groupby+merge+rename when the idiomatic pandas would be a single `pivot_table`. The track is *teaching* pandas, not punishing the candidate for not knowing it.
- **`apply(lambda)` as the reference solution** when a vectorized path exists. The reference must use the vectorized form.
- **MultiIndex for the sake of MultiIndex** — only when the index *is* the structure being computed (e.g. wide pivot output).
- **Questions that test exact method-signature memorization** — "what's the keyword for X" is not a reasoning test.
- **Stale dtype expectations** — if your expected output assumes `int64` and pandas gives `Int64`, fix the expected, not the candidate.
- **Hand-stringifying dates the grader already handles** — do **not** force `.dt.strftime(...)` on a plain date/datetime output just to avoid a serializer error; that historical crash is gone (the harness ISO-serializes and the comparator date-normalizes — see "Datetime output handling" above). Only stringify when the prompt asks for a *derived/formatted* value (e.g. a month label `'YYYY-MM'`). Forcing a string format the prompt didn't request makes candidates guess your exact format and penalizes correct answers.
- **Aggregating just to shrink the output** — do not collapse a genuine per-row transformation to an aggregate (or `head(N)`) to "stay under a cap". The grader compares the full result and only previews ~200 rows for display (see "Row count (platform-managed)" above), so returning all transformed rows is correct. Only the ~100k safety cap is hard; legitimate outputs (events ≈ 45 k) are well under it. Aggregate only when an aggregate is the actual question.
- **Schema column order drift** — declaring the `schema` columns in a different order than the CSV header (e.g. `created_at` after `issue_type` when the CSV puts it second). The schema panel is read top-to-bottom; wrong order is misleading even if no column is absent. Always verify against `head -1 datasets/<file>.csv`.
- **Stale explanation after code change** — updating `expected_code` without updating `explanation`. The explanation must describe the live code path; leaving a reference to `.apply()` after switching to `np.select`, for example, creates a visible contradiction for any user who reads both.
- **Implicit completeness violation** — if the description says "for each date", "include all rows", "every X", or uses a date-spine framing, the solution must return a row for every X — using `pd.date_range` + `reindex`, or an explicit merge with a complete reference frame, or similar. The failure mode: solution filters rows first (e.g., `status == 'completed'`), then groups and aggregates, silently dropping dates/entities that exist only in filtered-out rows. The description overclaims completeness; the solution underdelivers it. Fix rule: either (a) implement the spine/reindex so the solution honors the completeness promise, or (b) rewrite the description to use conditional phrasing ("for each date with at least one completed order") that accurately describes what the solution computes. Never ship a description that promises more than the solution delivers.
- **Ordered funnel described, co-presence implemented** — if the description uses sequential funnel language ("step A then step B", "A → B" with arrow notation, "in order"), the solution must enforce that ordering — e.g., by joining on session ID and checking that event A's timestamp precedes event B's timestamp for the same session. The failure mode: solution uses two independent event-type filters (`df[df.event == 'add_to_cart']`, `df[df.event == 'purchase']`) and counts them separately, never validating that A preceded B for the same session. A session that purchases without adding to cart is counted in the purchase filter; the ordering claim is false. Fix rule: either (a) implement the ordering check (merge on session + timestamp comparison), or (b) rewrite the description to use co-presence language ("sessions that have both an add_to_cart event and a purchase event") without implying ordering. Ordered-funnel and co-presence-funnel are different metrics — do not conflate them.
- **Unstated precision / definition / method** (the 2026-06-23 mock-pandas blind-QA defect classes — see [`docs/content-authoring.md`](../content-authoring.md) § Output contract, clauses 6–9). The grader sorts rows+columns and rounds to 5 dp, so don't specify order — but DO state: any rounding the key applies (e.g. `avg_salary` 2 dp; an `ltv_proxy` from pre-rounded intermediates); the sign of a difference and the **population** of a count/sum (inner- vs left-merge decides whether zero-activity rows count; null handling in a headcount/denominator); and any result-affecting **method** (percentile interpolation, `pd.cut` vs `pd.qcut` + the `rank(method=…)` tie rule, calendar-month vs day offsets, "most recent" tie-breaks). And the worst class — a **wrong key** that passes its own grader: a window filter missing a bound (`days_to_order <= 30` with no `>= 0` counted pre-signup orders) or an inner-merge dropping rows the cohort includes. Fix the key, not the stem.
- **Relying on the stem alone for column names** — `VariablesPanel` is the only column surface for pandas (no SchemaViewer), so the question's `schema` MUST ship to it on every surface (practice/sample/mock — mock historically didn't; fixed 2026-06-23). A stem listing only some columns is fine *because* the panel shows the rest; do not author as if the panel were absent, but never omit `schema` from the payload either.

**Sample non-duplication: family+shape level.** The sample non-duplication rule applies at family+shape level, not just exact-title level. A sample question about "daily revenue rolling window" is a near-clone of a practice question about "7-day rolling revenue by status" even if the titles differ. Reshaping questions, time-alignment questions, and rolling-window questions are high-risk for near-clone drift — check the practice and mock banks for the full concept family before finalizing any sample question in these families.

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
# 1. Reference solution produces the documented expected output AND passes the full sandbox path
cd backend && ../.venv/bin/python -c "
import pandas as pd, json
q = json.load(open('content/pandas_questions/hard.json'))[INDEX]
# load each CSV listed in q['dataframes']
orders = pd.read_csv('datasets/orders.csv')
ns = {}
exec(q['expected_code'], ns)
result = ns['solve'](df_orders=orders)

# ---- Check 1: shape and dtypes ----
print(result.shape)
print(result.dtypes)

# ---- Check 2: serialization path (exactly what the sandbox does) ----
from python_sandbox_harness import _json_default
records = result.to_dict(orient='records')
json.dumps(records, default=_json_default)  # datetimes serialize to ISO strings (no longer raises)
print('Serialization: OK')

# ---- Check 3: row count (only the 100k safety cap is hard; full result is graded) ----
assert len(result) <= 100000, f'FAIL: {len(result)} rows exceeds the 100k safety cap'
print(f'Row count: {len(result)} OK (full result is graded; UI previews first 200)')
"

# 2. solution_code produces identical results to expected_code
# (normalize_dataframe() + DataFrame.equals() — same normalization the runtime grader uses)

# 3. Schema column order matches CSV header order exactly
# (membership checks alone are insufficient — order matters for the schema panel)
python3 -c "
import json, csv
q = json.load(open('content/pandas_questions/hard.json'))[INDEX]
for df_name, csv_file in q.get('dataframes', {}).items():
    with open(f'datasets/{csv_file}') as f:
        csv_cols = next(csv.reader(f))
    declared = q['schema'].get(df_name, [])
    assert declared == csv_cols, f'{df_name}: declared {declared} != CSV {csv_cols}'
print('Schema order: OK')
"

# 4. explanation is consistent with expected_code — read both and confirm no contradiction
# (e.g. explanation must not reference .apply() if expected_code uses np.select)

# 5. Full content validation (includes _validate_reverse_preview_matches_key for reverse questions)
python scripts/validate_content.py

# 6. Pandas evaluator tests
cd backend && ../.venv/bin/python -m pytest tests/test_python_evaluator.py -q -k pandas
```

For `reverse` questions (if introduced): `result_preview` must equal the live `expected_code` output; machine-enforced by `_validate_reverse_preview_matches_key` (ERROR).

For all executable questions: verify stem↔key logical consistency, output-contract completeness (exact column names, value formats, ordering, tie-breaks stated in the stem), and determinism. See `docs/content-authoring.md` § Output contract, determinism & stem↔key consistency for the full defect taxonomy from the 2026-06 blind-QA pass.
