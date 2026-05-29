# Pandas Track

> **Authoring rule, no exceptions:** Every Pandas question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/python_data_questions/*.json` bypass the difficulty arc, the concept-taxonomy contract, and the pandas-idiomatic discipline.

## What this track trains

A data analyst or scientist who *thinks in pandas* writes meaningfully different code from one who *transliterates SQL into pandas*. The Pandas track exists to train pandas-native reasoning: when does `merge` beat `concat`, when does `transform` beat `agg`, when does the `.dt` accessor save you 50 lines of date parsing, when does an explicit dtype save you 4 GB of RAM. Idiomatic pandas is also fast pandas; the two are not separate concerns.

> *Datathink philosophy applied:* The analyst who runs `df.apply(lambda x: …)` on 10 million rows is the analyst who waits 40 minutes for an answer that should've taken 4 seconds. We're training the practitioner who recognises the row-wise antipattern, picks the vectorized path, and knows *why* — not the one who memorised method signatures.

## Modality

**Executable problem-solving.** Subprocess-sandboxed Python execution with the candidate's function called against pre-loaded DataFrames. 5-second timeout. 512 MB RLIMIT_AS. Output DataFrame compared to expected via `normalize_dataframe()` (from `evaluator.py`) followed by `DataFrame.equals()`. Normalization steps applied to both candidate and expected output before comparison:
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

Samples are not stored separately. `sample_questions.py` slices the first 3 questions per difficulty by `order` field directly from the live practice catalog (e.g. `medium.json`). Sample IDs are regular practice IDs (e.g. 32001, 32002, 32003 for medium). There is no `sample/` subdirectory and no `3XS` IDs for Pandas.

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

- **Practice: lean (~85–95 questions, ~⅓ easy / ~⅖ medium / ~¼ hard).** Roughly one teaching arc per family per applicable tier. Grow only to (a) ground a new gradable family or (b) fix a genuine arc break. Do **not** pad practice for volume — that fights the curriculum philosophy. The hard tier is intentionally smaller: multi-step pipelines are sparse by design.
- **Mock-only: ~110, medium + hard only, ~50:60 m:h skew.** That ratio (1:1.2) mirrors the SQL track. The inventory multiple over practice is ~1.2×; a healthy band is 1.0×–1.5×. Easy is practice-only — never. **~⅓ of mock questions should be chain members** (parents + follow-ups feeding Interview Loop).
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
# (normalize_dataframe() + DataFrame.equals() — same normalization the runtime grader uses)

# 3. Full content validation
python scripts/validate_content.py

# 4. Pandas evaluator tests
cd backend && ../.venv/bin/python -m pytest tests/test_python_evaluator.py -q -k pandas
```
