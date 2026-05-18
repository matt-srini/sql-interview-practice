# Concept Coverage Expansion Plan

Tracks concept-hooks.md coverage against the question bank, identifies gaps, and drives new question authoring across all 8 tracks.

**Initiated:** 2026-05-18  
**Status:** Phase 1 in progress (Phase 0 complete 2026-05-18)

---

## Audit Status

| Track | Hooks in concept-hooks.md | Gap analysis done? | Questions added? |
|---|---|---|---|
| SQL | ✅ hooks 1–88 + Missing Topics | ✅ done | ⬜ Phase 1 |
| PySpark | ✅ hooks 1–60 + Missing Topics | ✅ done | ⬜ Phase 4 |
| Pandas | ✅ hooks 1–62 + Missing Topics | ✅ done | ⬜ Phase 3 |
| Python | ✅ hooks 1–60 + Missing Topics | ✅ done | ⬜ Phase 3 |
| Data Engineering | ✅ hooks 1–62 + Missing Topics | ✅ done | ⬜ Phase 4 |
| Data Modeling | ✅ hooks 1–53 + Missing Topics | ✅ done | ⬜ Phase 4 |
| Statistics | ✅ hooks 1–78 + Missing Topics | ✅ done | ⬜ Phase 2 |
| ML Fundamentals | ❌ **no hooks written yet** | ❌ blocked on hooks | ⬜ future |

> **ML Fundamentals note:** Phase 0 adds the ML hooks to `concept-hooks.md`. The gap analysis and question authoring for ML is deferred — it will be a separate phase after the hooks are reviewed and approved.

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
| PySpark | easy | 41038 · 38 | none | **41039** | **39** | n/a |
| PySpark | medium | 42038 · 38 | 42048 · 48 | **42049** | **49** | after new practice |
| PySpark | hard | 43026 · 26 | 43036 · 36 | **43037** | **37** | after new practice |

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
| Data Engineering | 0, deferred | MCQ format is already assessment-like; hard practice Qs serve the same purpose; keep at 0 for now |
| Data Modeling | 0, deferred | Same as DE; keep at 0 for now |
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
| `orders` | order_id, user_id, order_date, status, total_amount |
| `order_items` | item_id, order_id, product_id, quantity, unit_price |
| `products` | product_id, product_name, category_id, price |
| `categories` | category_id, category_name |
| `employees` | employee_id, name, department_id, salary, hire_date, manager_id |
| `departments` | department_id, department_name, region |
| `events` | event_id, user_id, product_id, event_name, event_time |
| `payments` | payment_id, order_id, amount, payment_date, payment_method, status |
| `support_tickets` | ticket_id, user_id, created_at, resolved_at, issue_type, status |

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

**String Functions (6 questions — easy/medium, all practice):**
- [ ] TRIM / LTRIM / RTRIM — what each removes, real cleaning use case
- [ ] SUBSTRING / LEFT / RIGHT — extracting fixed-length segments
- [ ] CONCAT vs `||` — NULL behavior differences
- [ ] REPLACE vs REGEXP_REPLACE — when regex power is worth it
- [ ] SPLIT_PART / STRING_SPLIT — extracting the nth delimited segment
- [ ] STRING_AGG / LISTAGG / GROUP_CONCAT — aggregating rows into a list

**Date & Time Nuances (4 questions — easy/medium, all practice):**
- [ ] CURRENT_DATE vs NOW() vs CURRENT_TIMESTAMP — type and precision differences
- [ ] DATE_TRUNC vs EXTRACT — return type difference (timestamp vs number) in a real query
- [ ] Adding 1 month vs 30 days — why they diverge at month boundaries
- [ ] Timezone-aware vs naive timestamps — what breaks when you mix them

**Set Operations (3 questions — easy/medium, all practice):**
- [ ] UNION vs UNION ALL — performance cost and when deduplication matters
- [ ] INTERSECT vs INNER JOIN — equivalence and when they diverge
- [ ] EXCEPT / MINUS vs NOT IN — NULL trap that returns zero rows

**Advanced Aggregation (3 questions — medium/hard, all practice):**
- [ ] ROLLUP — hierarchical subtotals from a single GROUP BY
- [ ] GROUPING SETS — custom aggregation combinations
- [ ] FILTER(WHERE) on aggregate vs CASE WHEN — cleaner conditional aggregation

**Specialist / Hard Patterns (6 questions — hard; 5 mock-only, 1 practice):**
- [ ] ARRAY_AGG vs STRING_AGG — when you want an array vs a string (mock-only)
- [ ] Recursive CTE — hierarchy traversal base + recursive case (practice)
- [ ] Recursive CTE hard variant — date spine generation (mock-only)
- [ ] LATERAL join — correlated subquery in FROM when unavoidable (mock-only)
- [ ] JSON column extraction — `->`, `->>`, JSON_VALUE on a semi-structured column (mock-only)
- [ ] Calendar spine join — filling missing dates in a time series (mock-only)

**Notes:**
- All new SQL questions use existing DuckDB datasets (orders, users, employees, etc.)
- IDs: allocate at top of each difficulty range following the mock-only ID convention

---

### Phase 2 — Statistics new questions (+20 questions)
**Target files:** `backend/content/statistics_questions/easy.json`, `medium.json`, `hard.json`  
**Mostly practice; 3–4 hard questions designated mock-only** (CUPED numerical, MDE numerical, causal DAG — these are appropriate for Pro/Elite timed assessment)

**Distribution gaps (5 questions — easy/medium, conceptual MCQ):**
- [ ] Kurtosis — excess kurtosis and tail behavior interpretation
- [ ] Binomial vs Bernoulli — relationship and parameter meaning
- [ ] Geometric distribution — first-success framing and memoryless property
- [ ] Log-normal distribution — real-world quantities and why log-transform works
- [ ] F-distribution — what it is and where it appears (ANOVA connection)

**A/B Testing depth (5 questions — medium/hard, mixed subtypes):**
- [ ] Sequential testing / peeking — why stopping early on significance is wrong (conceptual)
- [ ] Minimum detectable effect — calculation given α, power, baseline rate (numerical)
- [ ] Metric sensitivity — mean vs median behavior under treatment, which to use (conceptual)
- [ ] CUPED / pre-experiment variance reduction — covariate, formula, what it buys (numerical)
- [ ] Guardrail vs primary metric — role of each and what happens when they conflict (conceptual)

**Applied / Bias patterns (5 questions — medium, conceptual MCQ):**
- [ ] Survivorship bias — scenario diagnosis and corrected analysis approach
- [ ] Berkson's bias — hospital-based study negative correlation explanation
- [ ] Regression to the mean — Sports Illustrated jinx, when it appears
- [ ] Goodhart's Law — when a metric becomes a target it stops being a good measure
- [ ] Sampling bias in funnel analysis — why step-3 users aren't representative of step-1

**Logistic & Causal (5 questions — medium/hard, conceptual):**
- [ ] Logistic regression — log-odds interpretation, why not linear for binary outcome
- [ ] Odds ratio vs relative risk — when they diverge significantly
- [ ] Paired vs unpaired t-test — what makes a design paired and why it reduces variance
- [ ] MCAR vs MAR vs MNAR — how each mechanism changes analysis strategy
- [ ] Causal DAG basics — confounding, colliders, and adjustment sets

---

### Phase 3 — Pandas (+12) + Python (+12) new questions
**Target files:** `backend/content/python_data_questions/` and `backend/content/python_questions/`

**Pandas (12 questions):**
- [ ] SettingWithCopyWarning / chained indexing (easy, practice)
- [ ] dropna(how='all') vs how='any' (easy, practice)
- [ ] fillna(method='ffill') vs fillna(value) (easy, practice)
- [ ] groupby(dropna=False) — NaN key grouping behavior (easy, practice)
- [ ] as_index=False in groupby — result shape change (easy, practice)
- [ ] merge_asof() — nearest-key join for event streams (medium, practice)
- [ ] combine_first() — patching missing values from a second DataFrame (medium, practice)
- [ ] explode() — unnesting list-like columns and reaggregating (medium, practice)
- [ ] assign() for method chaining — enabling fluid pipelines (medium, practice)
- [ ] pipe() — integrating custom functions into a chain (medium, practice)
- [ ] tz_localize() vs tz_convert() — when to use each (medium, mock-only)
- [ ] Chunked reading with chunksize — when and why (medium, mock-only)

**Python (12 questions — all practice):**

Practical Data Python (5):
- [ ] csv.DictReader — reading structured files without pandas (easy)
- [ ] json.loads() — handling nested keys and missing fields safely (easy)
- [ ] datetime.strptime() vs datetime.fromisoformat() — format flexibility (easy)
- [ ] Aggregating without pandas — group-by with defaultdict, sum, mean (medium)
- [ ] Duplicate detection in a list of dicts — key-based uniqueness (easy)

Data Structure Choice (3):
- [ ] list vs tuple — when immutability matters beyond convention (easy)
- [ ] defaultdict vs dict.get() vs setdefault() — when to use each (easy)
- [ ] deque vs list for a queue — O(1) popleft vs O(n) (easy)

Pythonic Patterns (4):
- [ ] Generator expression vs list comprehension — lazy evaluation memory savings (easy)
- [ ] zip() on unequal iterables / zip_longest — what gets dropped, what doesn't (easy)
- [ ] Context manager — what __enter__ and __exit__ give you (medium)
- [ ] namedtuple vs dataclass — simple value objects (medium)

---

### Phase 4 — PySpark (+5) + DE (+6) + DM (+6) fills
**Target files:** pyspark, data_engineering, data_modeling question directories

**PySpark (5 questions — all practice except 1 mock-only):**
- [ ] collect_list() vs collect_set() — ordering and deduplication guarantees (medium, practice)
- [ ] Pivot with dynamic schema — what happens when pivot columns are runtime-determined (medium, mock-only)
- [ ] F.expr() usage — when a SQL string in the DataFrame API is useful (easy, practice)
- [ ] Cross join opt-in — why PySpark requires explicit permission (easy, practice)
- [ ] DataFrame vs Dataset typed safety — when the extra type safety matters in practice (easy, practice)

**Data Engineering (6 questions — all practice):**
- [ ] Backpressure and flow control — what happens when consumers can't keep up (medium)
- [ ] Privacy/compliance architecture — PII handling, deletion workflows, access boundaries (medium)
- [ ] Data contract operationalization — enforcement, versioning, rollout mechanics (medium)
- [ ] Warehouse cost modeling — how storage, compute, scan volume drive spend (hard)
- [ ] Warehouse cost deep-dive — partition/clustering impact on bytes scanned (hard)
- [ ] Incident containment patterns — blast radius limiting, staged recovery (hard)

**Data Modeling (6 questions — all practice):**
- [ ] Bi-temporal modeling — valid time vs system time and when both matter (hard)
- [ ] Bi-temporal query pattern — finding a record valid at a given business date as-of a system date (hard)
- [ ] Semantic layer governance — centrally defined metrics and what marts alone can't enforce (medium)
- [ ] Semi-additive metric design — balances and inventory measures across time dimensions (medium)
- [ ] Alternate rollup hierarchy — multiple rollup paths for the same dimension (medium)
- [ ] Cross-hierarchy reporting — querying across hierarchies with different structures (hard)

---

### Phase 5 — New learning paths (4 new, 2 updated)
**Target:** `backend/content/paths/` (new JSON files)

**New paths (all Pro / Advanced tier):**
- [ ] `sql-string-and-date` — "SQL String & Date Functions" — 7 questions from Phase 1
- [ ] `sql-advanced-patterns` — "Advanced SQL Patterns" — 7 questions from Phase 1 (ROLLUP, Recursive CTE, LATERAL, JSON, etc.)
- [ ] `applied-stats` — "Applied Statistics for Data Work" — 8 questions from Phase 2 (bias patterns + applied A/B)
- [ ] `practical-data-python` — "Practical Data Python" — 6 questions from Phase 3

**Updated paths (add new questions to existing path question lists):**
- [ ] `experimental-design-inference` (Statistics) — add CUPED + MDE questions from Phase 2
- [ ] `dataframe-fundamentals` (Pandas) — add SettingWithCopyWarning question from Phase 3

---

### Phase 6 — CLAUDE.md + docs sync
**After all questions are authored and paths updated:**

- [ ] Update `CLAUDE.md` content footprint table — new practice + mock counts per track
- [ ] Update `CLAUDE.md` paths count (32 → 36 total)
- [ ] Update `docs/content-authoring.md` — add ML hooks reference, update concept tag guidance for new tracks
- [ ] Final validation: run `pytest tests/` to confirm catalog loads cleanly
- [ ] Spot-check 3–5 new questions via the dev UI (start server, navigate to new question IDs)

---

### Phase 7 (future) — ML Fundamentals audit + question gaps
**Blocked until:** Phase 0 ML hooks are reviewed and approved.

After the ML Fundamentals hooks in `concept-hooks.md` are finalized:
- [ ] Run gap analysis: ML question bank (90 practice + 25 mock) vs new ML hooks
- [ ] Identify any missing concept areas
- [ ] Author new ML questions if gaps exist
- [ ] Update learning paths if needed

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
