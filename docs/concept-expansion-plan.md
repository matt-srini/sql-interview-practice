# Concept Coverage Expansion Plan

Tracks concept-hooks.md coverage against the question bank, identifies gaps, and drives new question authoring across all 9 tracks.

**Initiated:** 2026-05-18  
**Status:** Phase 7 complete 2026-05-21 (Phase 0 complete 2026-05-18, Phase 1 complete 2026-05-18, Phase 2 complete 2026-05-18, Phase 3 complete 2026-05-19, Phase 4 complete 2026-05-19, Phase 5 complete 2026-05-19, Phase 6 complete 2026-05-20)

---

## Audit Status

| Track | Hooks in concept-hooks.md | Gap analysis done? | Questions added? |
|---|---|---|---|
| SQL | ✅ hooks 1–92 (Phase 0 expanded) | ✅ done | ✅ Phase 1 (+22) |
| PySpark | ✅ hooks 1–66 (Phase 0 expanded) | ✅ done | ✅ Phase 4 (+5) |
| Pandas | ✅ hooks 1–67 (Phase 0 expanded) | ✅ done | ✅ Phase 3 (+12) |
| Python | ✅ hooks 1–67 (Phase 0 expanded) | ✅ done | ✅ Phase 3 (+12) |
| Data Engineering | ✅ hooks 1–67 (Phase 0 expanded) | ✅ done | ✅ Phase 4 (+6) |
| Data Modeling | ✅ hooks 1–57 (Phase 0 expanded) | ✅ done | ✅ Phase 4 (+6) |
| Statistics | ✅ hooks 1–84 (Phase 0 expanded) | ✅ done | ✅ Phase 2 (+20) |
| ML Fundamentals | ✅ hooks 1–40 (Phase 0 written) | ✅ complete with gaps recorded (2026-05-19) | ⬜ follow-on authoring only if gaps warrant |
| Experimentation | ✅ hooks 1–33 (written 2026-05-18) | ✅ complete with gaps recorded (2026-05-19) | ⬜ follow-on authoring only if gaps warrant |

> **ML Fundamentals & Experimentation note:** Gap analysis is now complete for both tracks. Remaining work is targeted question authoring driven by the recorded gaps, not additional hook-definition work.

Recorded audit outcomes:
- ML Fundamentals: strongest coverage is in bias-variance and overfitting, leakage and splitting, metrics and imbalance, ensembles, and monitoring; recorded gaps include parametric vs non-parametric, inductive bias, encoding strategy, activation functions, batch normalization, attention, and deeper representation-learning comparisons.
- Experimentation: all 22 concept families are represented in the current bank; recorded gaps include direct ratio-metric/delta-method coverage, deeper surrogate-metric validation, and broader control-vs-holdout/A/A nuance beyond the current foundation subset.

---

## Summary of Gaps Found

### SQL (most significant gaps)
- String function section entirely absent: TRIM, SUBSTRING, CONCAT, REPLACE, SPLIT_PART, STRING_AGG
- Advanced aggregation absent: ROLLUP, CUBE, GROUPING SETS, FILTER(WHERE) on aggregate, ARRAY_AGG
- Set operations only partially covered: UNION vs UNION ALL performance, INTERSECT vs JOIN, EXCEPT NULL trap
- Date/time nuances thin: month vs 30 days, NOW() vs CURRENT_DATE, timezone pitfalls
- Specialist hard patterns missing: LATERAL join, JSON extraction, UNNEST, calendar spine, Recursive CTE, QUALIFY
- Existing questions often lack technique-level concept tags (only business-pattern tags set)

### Statistics (major gaps in applied/advanced sections)
- Distribution gaps: kurtosis, binomial, geometric, log-normal, F-distribution
- A/B testing depth almost entirely absent: sequential testing, MDE, CUPED, metric sensitivity, guardrail metrics, SUTVA
- Applied/bias patterns absent: survivorship bias, Berkson's bias, regression to mean, Goodhart's Law, sampling bias
- Other gaps: logistic regression, odds ratio, paired vs unpaired t-test, MCAR/MAR/MNAR, causal DAGs

### Pandas (targeted gaps)
- SettingWithCopyWarning / chained indexing
- dropna variations, fillna ffill, groupby(dropna=False), as_index=False
- merge_asof(), combine_first(), explode()
- assign() / pipe() method chaining
- tz_localize() vs tz_convert(), chunked reading

### Python (practical data Python section entirely absent)
- Entire "Data-Specific Python (No Pandas)" section: csv.DictReader, json.loads(), datetime parsing, defaultdict aggregation
- Pythonic patterns thin: generators, zip/enumerate nuances, context managers, args/kwargs, namedtuple/dataclass

### PySpark (minor gaps only)
- collect_list() vs collect_set() guarantees
- Pivot with dynamic schema
- F.expr() usage, cross join opt-in, DataFrame vs Dataset

### Data Engineering (Missing Topics section uncovered)
- Backpressure and flow control, privacy/compliance architecture
- Data contract operationalization, warehouse cost modeling, incident containment patterns

### Data Modeling (Missing Topics section uncovered)
- Bi-temporal modeling, semantic layer governance
- Semi-additive metric design, advanced hierarchy variants

---

## Authoring reference (read before writing any question)

### ID allocation and `order` field — how they differ

Two fields control question sequencing and they serve different purposes:

| Field | Purpose | Rule |
|---|---|---|
| `id` | Permanent identity key (submissions, progress, paths) | Append to end of range. **Never renumber.** |
| `order` | Sidebar display order / sample pool slice | Controls practice catalog sort; mock-only Qs are filtered out of sidebar entirely |

**Why IDs don't control display:** Mock-only questions are filtered out of the practice catalog by the catalog loader. So a practice question with `id: 12054` (numerically after mock `id: 12035`) still appears correctly in the sidebar based solely on its `order` value.

**The ordering convention:** Within each difficulty file, practice questions have lower `order` values than mock-only questions. New practice questions must get `order` values that place them in the practice sequence — meaning AFTER the current practice max order but the exact position relative to existing mock orders doesn't matter (mock is invisible in the sidebar).

**ID rule:** IDs are appended to the end of the range. Since existing mock IDs sit at the current end, new practice IDs will numerically follow existing mock IDs. This is acceptable — the no-renumber rule is a hard constraint.

Current state and next-available values:

| Track | Difficulty | Last practice (id · order) | Last mock (id · order) | Next practice id | Next practice order | Next mock id |
|---|---|---|---|---|---|---|
| SQL | easy | 11032 · 32 | none | **11033** | **33** | n/a |
| SQL | medium | 12034 · 34 | 12053 · 53 | **12054** | **54** | after new practice |
| SQL | hard | 13029 · 29 | 13043 · 43 | **13044** | **44** | after new practice |
| Statistics | easy | 71028 · 28 | none | **71029** | **29** | n/a (see mock policy) |
| Statistics | medium | 72028 · 28 | none | **72029** | **29** | after new practice |
| Statistics | hard | 73024 · 24 | none | **73025** | **25** | after new practice |
| Pandas | easy | 31022 · 22 | none | **31023** | **23** | n/a |
| Pandas | medium | 32031 · 31 | 32041 · 41 | **32042** | **42** | after new practice |
| Pandas | hard | 33023 · 23 | 33037 · 37 | **33038** | **38** | after new practice |
| Python | easy | 21030 · 30 | none | **21031** | **31** | n/a |
| Python | medium | 22029 · 29 | 22037 · 37 | **22038** | **38** | n/a (all practice) |
| Python | hard | 23024 · 24 | 23036 · 36 | **23037** | **37** | n/a |
| PySpark | easy | 41041 · 41 | none | **41042** | **42** | n/a |
| PySpark | medium | 42049 · 49 | 42050 · 50 | **42051** | **51** | after new practice |
| PySpark | hard | 43046 · 46 | 43036 · 36 | **43047** | **47** | after new practice |

> **schemas.json:** No update needed — all new IDs fall within existing declared ranges (e.g. SQL 11001–11999). Catalog loader validates at startup and crashes on range violation.

### Question JSON schema — SQL

All fields required unless marked optional:

```json
{
  "id": 11033,
  "order": 33,
  "title": "...",
  "difficulty": "easy",
  "description": "...",
  "dataset_files": ["tablename.csv"],
  "schema": { "tablename": ["col1", "col2"] },
  "expected_query": "SELECT ...",
  "solution_query": "SELECT ...;",
  "explanation": "...",
  "hints": ["...", "..."],
  "concepts": ["ALL-CAPS TAG", "ANOTHER TAG"],
  "complexity_hint": "O(n) full scan",
  "companies": ["Meta", "Stripe"],
  "required_concepts": ["string_function"],
  "enforce_concepts": true
}
```

Mock-only additions (hard questions only): add `"mock_only": true` and optionally `"follow_up_id": <id>`.

### Concept tag naming — SQL

- **Style:** ALL-CAPS, descriptive phrases (matches existing bank)
- **New technique tags for Phase 1 questions:** Each new question gets both a technique tag and a business-pattern tag where appropriate:

| Topic | Primary technique tag | Notes |
|---|---|---|
| TRIM / LTRIM / RTRIM | `STRING TRIMMING` | |
| SUBSTRING / LEFT / RIGHT | `SUBSTRING EXTRACTION` | |
| CONCAT / \|\| | `STRING CONCATENATION` | |
| REPLACE / REGEXP_REPLACE | `REGEX REPLACEMENT` | |
| SPLIT_PART / STRING_SPLIT | `DELIMITED STRING PARSING` | |
| STRING_AGG / LISTAGG | `STRING AGGREGATION` | |
| ARRAY_AGG | `ARRAY AGGREGATION` | |
| UNION vs UNION ALL | `UNION SET OPERATION` | |
| INTERSECT | `INTERSECT SET OPERATION` | |
| EXCEPT / MINUS | `EXCEPT SET OPERATION` | |
| ROLLUP | `ROLLUP SUBTOTALS` | |
| GROUPING SETS | `GROUPING SETS` | |
| FILTER(WHERE) on aggregate | `AGGREGATE FILTER` | |
| Recursive CTE | `RECURSIVE CTE` | |
| LATERAL join | `LATERAL JOIN` | |
| JSON extraction | `JSON EXTRACTION` | |
| UNNEST / FLATTEN | `ARRAY UNNESTING` | |
| Calendar spine | `CALENDAR SPINE` | |
| Date math nuances | `DATE ARITHMETIC` | |
| Timezone handling | `TIMEZONE HANDLING` | |

### Mock-only rules

**Important:** `in_mixed_mock=False` in `tracks.py` means the track is excluded from cross-track mixed sessions. It does NOT prevent track-specific mock questions. ML Fundamentals is `in_mixed_mock=False` and has 25 mock-only questions — those appear in ML-specific mock sessions.

Mock-only questions are drawn into the mock pool only for Pro/Elite users at medium and hard difficulty. Easy mock is never used (by design).

| Track | Mock-only questions | Policy for this expansion |
|---|---|---|
| SQL | ✅ existing 33 | Add 5 new hard mock-only specialist patterns |
| Python | ✅ existing 20 | Practical Python Qs = all practice; algorithmic hard = practice |
| Pandas | ✅ existing 24 | Add 3 new hard mock-only |
| PySpark | ✅ existing 20 | Add 1 new hard mock-only (pivot with dynamic schema) |
| Statistics | 0 today, **CAN add** | Add 3–4 hard mock-only (CUPED numerical, MDE numerical, causal DAG) — track-specific mock sessions are supported |
| Data Engineering | ✅ 14 (6 medium + 8 hard added Phase 7) | Medium: backpressure, data contracts, residency, cost modeling, incident patterns; Hard: CDC, partition overwrite, schema merge, streaming/warehouse/privacy/schema topics |
| Data Modeling | ✅ 13 (6 medium + 6 hard added Phase 7; 1 existing) | Medium: bi-temporal, conformed ext, semantic layer, SCD selection, schema evolution, high-churn SCD; Hard: post-acquisition conformed dim, metric deprecation, semi-additive, as-of reporting, zero-downtime migration, intra-day snapshot |
| ML Fundamentals | ✅ existing 25 | New ML questions are practice unless audit reveals clear mock-only candidates |

### Learning path rules

- Each track already has its one `starter` and one `intermediate` free path. New paths = **Pro / Advanced tier only**
- Path JSON lives in `backend/content/paths/<slug>.json`
- `questions[]` = array of integer IDs (must all exist in same track catalog)
- `recommended_after` = array of path slugs (prerequisites)
- Paths are added in **Phase 5** after all question IDs are known
- Path IDs referenced by `recommended_after` must already exist at commit time

### `order` field

The `order` field controls sidebar position for practice questions (mock-only questions are filtered out of the sidebar entirely). Set it to the next integer after the current max order in each file — see the "Next practice order" column in the ID table above. New mock-only questions also need an `order` value; set it after the new practice orders in the same file.

### Datasets available in DuckDB (SQL questions only)

All SQL questions must use existing CSVs. Available tables:

| Table | Key columns |
|---|---|
| `users` | user_id, name, email, signup_date, country, acquisition_channel, plan_tier, is_active |
| `orders` | order_id, user_id, order_date, status, gross_amount, discount_amount, **net_amount**, payment_status |
| `order_items` | **order_item_id**, order_id, product_id, quantity, unit_price, line_amount |
| `products` | product_id, product_name, category_id, brand, price, launch_date, is_active |
| `categories` | category_id, category_name, parent_category |
| `employees` | employee_id, **employee_name**, email, salary, department_id, hire_date, country (**no manager_id**) |
| `departments` | department_id, department_name, region |
| `events` | event_id, session_id, user_id, event_time, event_name, product_id |
| `payments` | payment_id, order_id, payment_date, payment_method, amount, status |
| `support_tickets` | ticket_id, user_id, created_at, issue_type, priority, status, resolution_hours |
| `sessions` | session_id, user_id, session_start, device_type, traffic_source, country |

String/date function questions use `employees`, `users`, or `orders` — they have rich text and date columns. JSON extraction would need a new dataset (noted in Phase 1 hard section).

---

## Phase Breakdown

---

### Phase 0 — concept-hooks.md housekeeping + concept tag cleanup
**Goal:** Get the metadata right before adding questions. No new questions in this phase.

- [x] Gap analysis complete for all 7 audited tracks
- [x] Add ML Fundamentals section to `concept-hooks.md` (40 hooks across 7 sections)
- [x] Promote "Missing Topics To Add" sections into numbered hooks for all 7 audited tracks (SQL → 92 hooks, PySpark → 66, Pandas → 67, Python → 67, DE → 67, DM → 57, Stats → 84)
- [x] Add technique-level secondary concept tags to 9 existing SQL questions (14 tag additions: CORRELATED SUBQUERY, EXISTS PATTERN, ORDERED-SET AGGREGATE)

---

### Phase 1 — SQL new questions (+22 questions)
**Target files:** `backend/content/questions/easy.json`, `medium.json`, `hard.json`  
**Status: ✅ Complete 2026-05-18** — 37 easy / 45 medium / 30 hard practice; 38 mock-only total

**String Functions (6 questions — easy/medium, all practice):**
- [x] 11033 — TRIM + UPPER channel normalization (TRIM / UPPER / STRING TRIMMING)
- [x] 11034 — SPLIT_PART email domain extraction (SUBSTRING EXTRACTION)
- [x] 11035 — CONCAT + COALESCE employee label (STRING CONCATENATION / NULL HANDLING)
- [x] 12054 — REGEXP_REPLACE event name normalization + INITCAP (REGEX REPLACEMENT)
- [x] 12055 — STRING_AGG products per category with ORDER BY inside aggregate
- [x] 12064 — SPLIT_PART composite key parse + CONCAT build (DELIMITED STRING PARSING)

**Date & Time Nuances (4 questions — easy/medium, all practice):**
- [x] 11036 — CURRENT_DATE minus signup_date → days tenure (CURRENT DATE / DATE ARITHMETIC)
- [x] 11037 — DATE_TRUNC('month') for monthly trend (DATE TRUNCATION)
- [x] 12056 — INTERVAL '365 days' + BETWEEN window → renewal flag (DATE ARITHMETIC / INTERVAL ADDITION)
- [x] 12057 — AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles' (TIMEZONE HANDLING)

**Set Operations (3 questions — medium, all practice):**
- [x] 12058 — UNION deduplication across orders + support_tickets (UNION SET OPERATION)
- [x] 12059 — INTERSECT shared users (INTERSECT SET OPERATION)
- [x] 12060 — EXCEPT anti-join (EXCEPT SET OPERATION)

**Advanced Aggregation (3 questions — medium + hard practice):**
- [x] 12061 — GROUP BY ROLLUP revenue with COALESCE (ROLLUP SUBTOTALS)
- [x] 12062 — FILTER(WHERE payment_status = ...) conditional counts (AGGREGATE FILTER)
- [x] 13044 — GROUPING SETS three independent revenue slices (GROUPING SETS) [hard practice]

**Specialist / Hard Patterns (6 questions — hard; 5 mock-only, 1 practice):**
- [x] 12063 — Recursive CTE monthly spine LEFT JOIN to orders [moved to medium practice]
- [x] 13045 — ARRAY_AGG(DISTINCT ... ORDER BY) product arrays per user [mock]
- [x] 13046 — Recursive CTE date spine + LEFT JOIN revenue gap-fill [mock]
- [x] 13047 — CROSS JOIN LATERAL top-2 products per category [mock]
- [x] 13048 — QUALIFY + ROW_NUMBER latest order per user [mock] *(replaced JSON extraction — no JSON column in dataset)*
- [x] 13049 — GENERATE_SERIES daily spine + is_weekend flag [mock]

**Notes:**
- JSON extraction deferred: no existing dataset has a JSON column; would require a new CSV
- QUALIFY replaces JSON in the mock set — it's a high-value DuckDB/Snowflake pattern
- employees has no manager_id column — hierarchy CTE uses date spine approach instead

---

### Phase 2 — Statistics new questions (+20 questions)
**Target files:** `backend/content/statistics_questions/easy.json`, `medium.json`, `hard.json`  
**Mostly practice; 3–4 hard questions designated mock-only** (CUPED numerical, MDE numerical, causal DAG — these are appropriate for Pro/Elite timed assessment)

**Distribution gaps (5 questions — easy/medium, conceptual MCQ):**
- [x] Kurtosis — excess kurtosis and tail behavior interpretation (71029 easy)
- [x] Binomial vs Bernoulli — relationship and parameter meaning (71030 easy)
- [x] Geometric distribution — first-success framing and memoryless property (71031 easy)
- [x] Log-normal distribution — real-world quantities and why log-transform works (72029 medium)
- [x] F-distribution — what it is and where it appears (ANOVA connection) (72030 medium)

**A/B Testing depth (5 questions — medium/hard, mixed subtypes):**
- [x] Sequential testing / peeking — why stopping early on significance is wrong (72031 medium conceptual)
- [x] Minimum detectable effect — calculation given α, power, baseline rate (73025 hard numerical mock-only)
- [x] Metric sensitivity — mean vs median behavior under treatment, which to use (72032 medium conceptual)
- [x] CUPED / pre-experiment variance reduction — covariate, formula, what it buys (73026 hard numerical mock-only)
- [x] Guardrail vs primary metric — role of each and what happens when they conflict (72033 medium conceptual)

**Applied / Bias patterns (5 questions — medium, conceptual MCQ):**
- [x] Survivorship bias — scenario diagnosis and corrected analysis approach (72034 medium)
- [x] Berkson's bias — hospital-based study negative correlation explanation (72035 medium)
- [x] Regression to the mean — Sports Illustrated jinx, when it appears (72036 medium)
- [x] Goodhart's Law — when a metric becomes a target it stops being a good measure (72037 medium)
- [x] Sampling bias in funnel analysis — why step-3 users aren't representative of step-1 (72038 medium)

**Logistic & Causal (5 questions — medium/hard, conceptual):**
- [x] Logistic regression — log-odds interpretation, why not linear for binary outcome (72039 medium)
- [x] Odds ratio vs relative risk — when they diverge significantly (72040 medium)
- [x] Paired vs unpaired t-test — what makes a design paired and why it reduces variance (72041 medium)
- [x] MCAR vs MAR vs MNAR — how each mechanism changes analysis strategy (73027 hard)
- [x] Causal DAG basics — confounding, colliders, and adjustment sets (73028 hard conceptual mock-only)

---

### Phase 3 — Pandas (+12) + Python (+12) new questions
**Target files:** `backend/content/python_data_questions/` and `backend/content/python_questions/`  
**Status: ✅ Complete 2026-05-19** — Pandas 86 practice (27/36/23) + 26 mock-only; Python 95 practice (39/32/24) + 20 mock-only

**Pandas (12 questions):**
- [x] 31023 — SettingWithCopyWarning / .loc conditional assignment (easy, practice)
- [x] 31024 — dropna(subset=...) — column-specific null filtering (easy, practice)
- [x] 31025 — ffill after sort — forward fill missing emails (easy, practice)
- [x] 31026 — groupby(dropna=False, as_index=False) — NaN key grouping (easy, practice)
- [x] 31027 — as_index=False + named aggregation — avg order value by status (easy, practice)
- [x] 32042 — merge_asof() — nearest-key join for event streams (medium, practice)
- [x] 32043 — combine_first() — patching missing values from a second Series (medium, practice)
- [x] 32044 — assign() chained — discount_pct and is_discounted flag (medium, practice)
- [x] 32045 — pipe() — integrating custom functions into a chain (medium, practice)
- [x] 32046 — tz_localize() vs tz_convert() — UTC to New York time (medium, practice)
- [x] 32047 — explode() — unnest product lists and filter multi-product orders (medium, mock-only)
- [x] 32048 — pd.qcut + assign + groupby — revenue quartile distribution (medium, mock-only)

**Python (12 questions — all practice):**

Practical Data Python (9 easy):
- [x] 21031 — csv.DictReader — parse CSV lines into list of dicts (easy)
- [x] 21032 — json.loads() — parse JSON log entry, return [level, message] (easy)
- [x] 21033 — datetime.strptime() — find most recent date from MM/DD/YYYY list (easy)
- [x] 21034 — Find duplicates — values appearing more than once, no Counter (easy)
- [x] 21035 — defaultdict grouping — group (category, item) pairs by key (easy)
- [x] 21036 — deque sliding window maximum — O(n) with monotonic deque (easy)
- [x] 21037 — Generator expression — sum of squares of odd numbers (easy)
- [x] 21038 — zip_longest — pair two lists with fill value (easy)
- [x] 21039 — namedtuple — create Player instances, sort by score desc (easy)

Pythonic Patterns (3 medium):
- [x] 22038 — contextlib.suppress — safe division, suppress ZeroDivisionError (medium)
- [x] 22039 — Chunked list processing — sum each chunk with range(0, len, n) (medium)
- [x] 22040 — json.loads + filter/sort — extract ERROR/CRITICAL messages from JSON log (medium)

---

### Phase 4 — PySpark (+5) + DE (+6) + DM (+6) fills
**Target files:** pyspark, data_engineering, data_modeling question directories  
**Status: ✅ Complete 2026-05-19** — PySpark 106 practice (41/39/26) + 21 mock-only; DE 86 practice (30/33/23) + 1 mock-only; DM 76 practice (25/28/23) + 1 mock-only

**PySpark (5 questions — 4 practice + 1 mock-only):**
- [x] 41039 — F.expr() usage — when a SQL string in the DataFrame API is useful (easy, practice)
- [x] 41040 — Cross join opt-in — why PySpark requires .crossJoin() (easy, practice)
- [x] 41041 — DataFrame vs Dataset typed safety — Dataset[T] only in Scala/Java (easy, practice)
- [x] 42049 — collect_list() vs collect_set() — ordering and deduplication guarantees (medium, practice)
- [x] 42050 — Pivot with dynamic schema — driver OOM at high cardinality without values list (medium, mock-only)

**Data Engineering (6 questions — all practice):**
- [x] 52031 — Backpressure in a streaming pipeline — throughput math + parallelism fix (medium, scenario)
- [x] 52032 — GDPR erasure in immutable data lake — crypto shredding via per-user KMS key deletion (medium, mcq)
- [x] 52033 — Data contract operationalization — schema registry + CI compatibility check (medium, mcq)
- [x] 53022 — Snowflake warehouse cost optimization — separate warehouses + auto-suspend sizing (hard, scenario)
- [x] 53023 — BigQuery cost reduction — date partitioning + cluster + incremental export (hard, scenario)
- [x] 53024 — Schema drift incident — containment, last-good snapshot, alias at ingest, contract test (hard, scenario)

**Data Modeling (6 questions — all practice):**
- [x] 62026 — Semantic layer governance — centralized metric definition vs view vs documentation (medium, mcq)
- [x] 62027 — Semi-additive facts — bank balance: additive across accounts, not across time (medium, mcq)
- [x] 62028 — Multi-valued dimension — bridge table for 0–5 promotions per order (medium, mcq)
- [x] 63022 — Bi-temporal query predicates — recorded_from/to for transaction time, valid_from/to for business time (hard, scenario)
- [x] 63023 — Cross-hierarchy reporting — flat columns in dim_product + RANK() OVER PARTITION BY each hierarchy (hard, scenario)
- [x] 63024 — Fact-to-fact fan-out join — pre-aggregate in CTEs before joining on customer_id (hard, scenario)

---

### Phase 5 — New learning paths (4 new, 2 updated)
**Target:** `backend/content/paths/` (new JSON files)  
**Status: ✅ Complete 2026-05-19** — 42 total paths (was 38); SQL: 9, Python: 6, Statistics: 3

**New paths (all Pro / Advanced tier):**
- [x] `sql-string-and-date` — "SQL String & Date Functions" — 7 questions (11033–11037, 12054, 12056)
- [x] `sql-advanced-patterns` — "Advanced SQL Patterns" — 7 questions (12058–12063, 13044; set ops + ROLLUP + FILTER + Recursive CTE + GROUPING SETS)
- [x] `applied-stats` — "Applied Statistics for Data Work" — 8 questions (72034–72041; bias patterns + logistic regression + odds ratio + paired t-test)
- [x] `practical-data-python` — "Practical Data Python" — 6 questions (21031–21033, 21035, 22039–22040; CSV/JSON/datetime/defaultdict/chunked)

**Updated paths (add new questions to existing path question lists):**
- [x] `experimental-design-inference` (Statistics) — added 72031 (sequential testing), 72032 (metric sensitivity), 72033 (guardrail metrics); now 13 questions
- [x] `dataframe-fundamentals` (Pandas) — added 31023 (SettingWithCopyWarning); now 7 questions

---

### Phase 6 — CLAUDE.md + docs sync
**After all questions are authored and paths updated:**

- [ ] Update `CLAUDE.md` content footprint table — new practice + mock counts per track
- [ ] Update `CLAUDE.md` paths count (32 → 36 total)
- [ ] Update `docs/content-authoring.md` — add ML hooks reference, update concept tag guidance for new tracks
- [ ] Final validation: run `pytest tests/` to confirm catalog loads cleanly
- [ ] Spot-check 3–5 new questions via the dev UI (start server, navigate to new question IDs)

---

### Phase 7 — PySpark / DE / DM / Exp / ML Fundamentals expansion
**Status: ✅ Complete 2026-05-21**

Five lanes executed in order. Final state: 853 practice + 190 mock-only = 1,043 total questions.

#### Lane 1 — PySpark hard (+10 practice, 43037–43046, orders 37–46)

- [x] 43037 — predict_output — AQE Skew Join: How Many Tasks Process the Hot Partition?
- [x] 43038 — predict_output — Salted Join: What Does result.count() Return?
- [x] 43039 — predict_output — Watermark Boundary: Which Incoming Events Are Dropped?
- [x] 43040 — predict_output — foreachBatch Driver Crash Mid-Write: What Is in the Output Table?
- [x] 43041 — predict_output — Pandas UDF: Predicting Output for Null and Zero Inputs
- [x] 43042 — scenario — Iterative PageRank Crashes with StackOverflowError During Plan Materialization
- [x] 43043 — scenario — Streaming Windows Always Emitted One Full Trigger Cycle Late
- [x] 43044 — scenario — Delta MERGE Fails on Large Batch After Consumer Offset Reset
- [x] 43045 — scenario — MERGE Scans 798 of 800 Files After 30 Days of Good Pruning
- [x] 43046 — scenario — 9× Slowdown After Halving Executor Memory Despite Identical Partition Count

#### Lane 2 — Data Engineering (+2 medium practice, +6 medium mock-only, +3 hard practice, +7 hard mock-only)

Medium practice (52034–52035, orders 34–35):
- [x] 52034 — debug — Avro Consumer Failing After Producer Adds Required Field Without Default
- [x] 52035 — debug — Backfill Job Producing Duplicate Rows in the Warehouse

Medium mock-only (52036–52041, orders 36–41):
- [x] 52036 — scenario — Consumer Lag Grows Unboundedly During Traffic Spike [FULL_TRANSITIVE schema compat]
- [x] 52037 — scenario — Fact Table Corrupted by Bad Pipeline Write: Containment and Recovery
- [x] 52038 — conceptual — Choosing the Right Data Contract Enforcement Tier
- [x] 52039 — scenario — EU Data Residency: Preventing Cross-Region PII Replication
- [x] 52040 — debug — Pipeline Keeps Flooding a Degraded Downstream System [backpressure]
- [x] 52041 — conceptual — Clustering Key vs Partitioning for Mixed Read/Write Workloads

Hard practice (53025–53027, orders 25–27):
- [x] 53025 — debug — CDC Watermark Too Short — Late Debezium Events Silently Dropped
- [x] 53026 — debug — Dynamic Partition Overwrite Deleting the Entire Table
- [x] 53027 — debug — Schema Merge Upcasting Numeric Column to String Across Parquet Sources

Hard mock-only (53028–53034, orders 28–34):
- [x] 53028 — scenario — Sink-Side I/O Backpressure Causing Unbounded State Accumulation
- [x] 53029 — scenario — Warehouse Cost Spike: Dashboard Refresh Rate Preventing Auto-Suspend
- [x] 53030 — scenario — Incremental Pipeline Serving Stale Rows After Upstream Backfill Inversion
- [x] 53031 — scenario — Breaking Schema Change Escaping CI: Non-Transitive Compatibility
- [x] 53032 — conceptual — Privacy-Preserving Analytics: Trade-offs Across Three Techniques
- [x] 53033 — debug — Duplicate Events from Two Streaming Pipelines Sharing a Checkpoint
- [x] 53034 — conceptual — Designing an Effective Runbook for P1 Data Pipeline Incidents

#### Lane 3 — Data Modeling (+6 medium mock-only, +6 hard mock-only)

*Questions audited post-authoring against data-modeling-question-authoring.agent.md; concept tag and first-hint violations corrected before commit.*

Medium mock-only (62029–62034, orders 29–34):
- [x] 62029 — scenario — Bi-Temporal Modeling: When SCD Type 2 Cannot Reconstruct System State [concepts: BI-TEMPORAL MODELING, SCD STRUCTURE, DIMENSIONAL MODELING]
- [x] 62030 — scenario — Conformed Dimension Extension: Adding a Business-Unit-Specific Attribute [concepts: CONFORMED DIMENSIONS, SCHEMA EVOLUTION, DIMENSIONAL MODELING]
- [x] 62031 — conceptual — Semantic Layer Governance: Certified vs Experimental Metric Lifecycle [concepts: SEMANTIC LAYER, DIMENSIONAL MODELING]
- [x] 62032 — scenario — SCD Type Selection Under Conflicting Retention and Query Requirements [concepts: SCD STRUCTURE, STORAGE ARCHITECTURE TRADEOFFS, DIMENSIONAL MODELING]
- [x] 62033 — conceptual — Schema Evolution for a Shared Dimension: Breaking vs Non-Breaking Change Classification [concepts: SCHEMA EVOLUTION, DIMENSIONAL MODELING]
- [x] 62034 — scenario — High-Churn SCD: When Type 2 Row Explosion Becomes Impractical [concepts: SCD STRUCTURE, STORAGE ARCHITECTURE TRADEOFFS, FACT TABLE DESIGN, DIMENSIONAL MODELING]

Hard mock-only (63025–63030, orders 25–30):
- [x] 63025 — scenario — Post-Acquisition Conformed Dimension: Resolving Overlapping Natural Keys [concepts: CONFORMED DIMENSIONS, SURROGATE VS NATURAL KEYS, DATA VAULT, DIMENSIONAL MODELING]
- [x] 63026 — conceptual — Semantic Layer: Deprecating a Certified Metric Without Breaking Downstream Consumers [concepts: SEMANTIC LAYER, DIMENSIONAL MODELING]
- [x] 63027 — scenario — Semi-Additive Fact Design for Balance with Period-Change Analytics [concepts: SEMI-ADDITIVE FACTS, PERIODIC SNAPSHOT, FACT TABLE DESIGN, DIMENSIONAL MODELING]
- [x] 63028 — scenario — Regulatory As-Of Reporting: When a Dimension Must Reconstruct Its Own Past State [concepts: BI-TEMPORAL MODELING, SCD STRUCTURE, DIMENSIONAL MODELING]
- [x] 63029 — scenario — Zero-Downtime Schema Migration for a High-Fan-Out Fact Table [concepts: SCHEMA EVOLUTION, DIMENSIONAL MODELING]
- [x] 63030 — conceptual — Intra-Day Periodic Snapshot: Granularity Trade-offs and Fact Table Design [concepts: PERIODIC SNAPSHOT, FACT TABLE DESIGN, STORAGE ARCHITECTURE TRADEOFFS, DIMENSIONAL MODELING, SEMI-ADDITIVE FACTS]

#### Lane 4 — Experimentation (+4 practice) and ML Fundamentals (+6 practice)

Experimentation medium practice (92043–92044, orders 31–32):
- [x] 92043 — debug — CUPED Covariate Window: Contamination Through Post-Exposure Measurement [concepts: VARIANCE REDUCTION, EXPERIMENT DESIGN]
- [x] 92044 — scenario — Two-Sided Marketplace Equilibration: Why Short-Duration Tests Miss Steady-State Effects [concepts: EXPERIMENT DURATION, NETWORK EFFECTS]

Experimentation hard practice (93034–93035, orders 21–22):
- [x] 93034 — scenario — Long-Run Holdout Group Decay: When the Counterfactual Diverges from Current Users [concepts: HOLDOUT GROUPS, CAUSAL INFERENCE]
- [x] 93035 — debug — Switchback Experiment Analysis: Temporal Autocorrelation Inflates the Test Statistic [concepts: SWITCHBACK EXPERIMENTS, EXPERIMENT DESIGN]

ML Fundamentals medium practice (82048–82050, orders 36–38):
- [x] 82048 — scenario — Missing Value Imputation Before Split: Why Preprocessing Order Invalidates Evaluation [concepts: MISSING DATA STRATEGY, DATA LEAKAGE DETECTION]
- [x] 82049 — scenario — K-Means Evaluation: Reconciling Elbow Method and Silhouette Score Disagreement [concepts: CLUSTERING EVALUATION, HYPERPARAMETER SENSITIVITY]
- [x] 82050 — debug — Feature Selection Before Train/Test Split: Implicit Test Target Leakage [concepts: FEATURE SELECTION STRATEGY, DATA LEAKAGE DETECTION]

ML Fundamentals hard practice (83039–83041, orders 26–28):
- [x] 83039 — scenario — Domain-Adaptive Pre-Training: When General Pre-Training Representations Misalign with Target Domain [concepts: TRANSFER LEARNING STRATEGY, DEPLOYMENT CONSTRAINTS]
- [x] 83040 — scenario — Silent Feature Transformation: Upstream Business Logic Change Causes Precision Collapse [concepts: MODEL MONITORING, TRAINING-SERVING SKEW]
- [x] 83041 — debug — Deep Sigmoid Network: Diagnosing Vanishing Gradients from Activation Saturation [concepts: GRADIENT PATHOLOGY, NEURAL NETWORK DESIGN]

#### Lane 5 — Docs governance

- [x] concept-expansion-plan.md updated with all Phase 7 IDs, titles, concepts
- [x] CLAUDE.md updated: PySpark 106→116, DE 85→91, DM 70→76, Exp 80→84, MLF 90→96 practice; totals 843→853 practice, 165→190 mock-only
- [x] Duplicate ID check passed: 1,043 total questions, 0 duplicates
- [x] Concept tag blocklist audit: all Phase 7 questions use canonical tags; violations found post-authoring in Lane 3 were corrected before commit

---

## Key decisions captured

| Decision | Rationale |
|---|---|
| Statistics: no mock-only questions | Existing policy at launch; new Stats questions all go to practice pool |
| DE / DM / Stats / ML: no mock (in_mixed_mock=false) | These tracks are excluded from mixed mock sessions by design |
| SQL new hard questions → 5 mock-only | Hard specialist patterns (LATERAL, JSON, calendar spine, etc.) are mock-appropriate difficulty |
| Python "practical data" questions → all practice | These are concept-builders, not performance-under-pressure questions |
| New learning paths → all Pro / Advanced tier | Each track already has its one starter + one intermediate free shortcut path |
| SQL technique tags added to existing questions | Concept pills currently only show business-problem tags; technique tags help users identify what they're practicing |
| Python concept tag capitalization | New questions will follow lowercase style (matching majority of existing); no retroactive fix to 83 existing questions |
| ML hooks written before ML audit | Can't audit coverage without hooks to audit against |
