# Concept Taxonomy — canonical registry

> **Source of truth for every `concepts` tag on every question, across all 9 tracks, plus the universal follow-up dimension taxonomy used in mock chains.** This file is the discipline. No `concepts` tag may appear in a question file unless it maps to a family registered here. New families require a PR to this file *first*.

**Why this file exists.** Before this registry, concept tags drifted: SQL questions tagged with implementation primitives (`JOIN`, `GROUP BY`), PySpark questions accumulated 493 unique tags many of which were lowercase mechanic names (`shuffle`, `Catalyst optimizer`), Statistics tags were mixed-case and ad-hoc. The result was a fragmented inventory that mock focus mode and dashboard insights could only weakly aggregate over. This registry consolidates that history into per-track canonical families with explicit blocklists.

**Discipline applied to this taxonomy.** Families are grounded in two practical lenses, not academic curricula:
1. **Real business / engineering work** — does a working practitioner actually reason this way on the job?
2. **Real interview shapes** — is this what a serious data interviewer probes for at FAANG, Stripe, Airbnb, Netflix, and the broader serious-data-employer market?

If a family fails either test, it doesn't belong here. We are **not** building a textbook curriculum. We are surfacing the reasoning patterns serious practitioners and serious interviewers care about.

> **⚡ gap families — Phase 2 status.** Families marked `⚡ *real-world gap*` were added by the 2026-05 refactor to surface reasoning the bank previously had only *implicitly*. **SQL Phase 2 complete:** `DOUBLE-COUNTING DETECTION`, `DATA QUALITY SKEPTICISM`, and `METRIC RECONCILIATION` now have practice coverage; `METRIC INTERPRETATION & DENOMINATOR CHOICE`, `OUTPUT SANITY VALIDATION`, and `PERFORMANCE-AWARE ANALYTICS` are established as **mock-only realism lenses** (appear only on `mock_only: true` questions, always co-occurring with ≥1 practice-grounded family; enforced by `_validate_mock_only_realism()`). **Python Phase 2 complete:** Python has **no ⚡/realism families by design** — Python's families are pure algorithmic patterns, and the candidate "lens" (complexity & memory) is **practice-gradable** via the executable harness (`O(n²)` times out, `load-everything` OOMs on the sized hidden inputs) and surfaces in mock as the `performance_pivot` chain dimension, not as a concept tag. **PySpark Phase 2 complete:** `DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`, and `OUTPUT SANITY VALIDATION` are practice-grounded (new practice questions authored; all three ⚡ markers removed from PySpark section). PySpark has no mock-only realism families — MCQ format makes all three reasoning lenses gradeable as `predict_output` / `debug`. **Pandas Phase 2 complete:** six new families grounded — `MEMORY & VECTORIZATION REASONING`, `DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION` are practice-grounded; `METRIC INTERPRETATION & DENOMINATOR CHOICE`, `OUTPUT SANITY VALIDATION`, `PERFORMANCE-AWARE ANALYTICS` are mock-only realism lenses (same contract as the SQL realism trio). See Pandas section below for full entries. **Data Engineering Phase 2 complete:** DE has no mock-only realism families — all 21 concept families are practice-grounded (MCQ constructed-reasoning format makes every family directly gradeable as `scenario`/`debug`/`conceptual`; the "assessment lens" rationale for SQL/Pandas mock-only realism does not transfer). `MOCK_ONLY_REALISM_FAMILIES["data-engineering"] = set()` enforced in `concept_families.py`. **ML Fundamentals Phase 2 complete; BIAS/FAIRNESS Phase 2.5 complete (2026-05-26):** ML Fundamentals has 30 concept families (all UPPERCASE). `ALGORITHMIC FAIRNESS` added at position 30 — practice-grounded (path-ii preserved; `MOCK_ONLY_REALISM_FAMILIES["ml-fundamentals"] = set()` unchanged). No mock-only realism families by design: MCQ constructed-reasoning format makes every reasoning lens directly gradeable as `scenario`/`debug`/`conceptual`/`predict_output` — the "assessment lens" rationale for SQL/Pandas mock-only realism does not transfer. `MOCK_ONLY_REALISM_FAMILIES["ml-fundamentals"] = set()` enforced in `concept_families.py`. **Experimentation Phase 2 complete:** Experimentation has 24 concept families (all UPPERCASE). No mock-only realism families by design: MCQ constructed-reasoning format makes every reasoning lens (SRM diagnosis, novelty detection, peeking) directly gradeable as `scenario`/`debug`/`predict_output` — the "assessment lens" rationale for SQL/Pandas mock-only realism does not transfer. Registry expanded 22→24 with SEQUENTIAL TESTING and METRIC SENSITIVITY. `MOCK_ONLY_REALISM_FAMILIES["experimentation"] = set()` enforced in `concept_families.py`. **Data Modeling Phase 2 complete:** DM has no mock-only realism families — all 22 concept families are practice-grounded (MCQ constructed-reasoning format makes every family directly gradeable as `scenario`/`debug`/`conceptual`; the "assessment lens" rationale for SQL/Pandas mock-only realism does not transfer). `MOCK_ONLY_REALISM_FAMILIES["data-modeling"] = set()` enforced in `concept_families.py`. **Statistics Phase 2 complete:** Statistics has 13 concept families using lowercase canonical tag style (a deliberate exception to the UPPERCASE convention — preserves the existing corpus and matches academic/industry norms). No mock-only realism families by design: the dual-subtype format (conceptual MCQ + numerical Python execution) makes every reasoning lens directly gradeable regardless of subtype — the "assessment lens" rationale for SQL/Pandas mock-only realism (they can't grade as query-writing) does not apply when MCQ and code execution are both first-class. `MOCK_ONLY_REALISM_FAMILIES["statistics"] = set()` enforced in `concept_families.py`.

---

## Cross-track family naming reusability

Family names may be **reused across tracks only within the executable analytics cluster** (SQL, Pandas, PySpark). Where the same reasoning skill applies under the same name (e.g. `DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`, `OUTPUT SANITY VALIDATION`), the shared name carries — same family, same semantics, distinct per-track member tags and match patterns. This makes cross-track dashboards meaningful.

**Outside that cluster, families do not transfer.** Python algorithmic patterns are native to Python (no SQL/Pandas/PySpark sharing). DE/DM/Stats/ML/Exp families are reasoning-domain-specific and stay within their track. Borrowing a family name into a track where it doesn't carry identical semantics is forbidden — it produces fake cross-track signal in dashboards.

## How this file is used

### By authors (and the authoring agent)

- Every question's `concepts` array must contain 2–4 tags (5 only when a hard question genuinely teaches multiple dependent patterns).
- Each tag is a free-form string the author writes — but it **must map to exactly one family** for that track via the resolution rules below.
- The agent rejects any tag that resolves to no family OR matches a blocklist pattern.
- New tag string fine, new family requires a PR to this doc.

### By the backend (concept-families enforcement)

- `backend/concept_families.py` is **derived from this file**. After any change to a per-track family registry here, regenerate or hand-mirror the Python dict so the catalog loader / mock focus / insights engine sees the same families.
- The Phase 2 work item: refactor `concept_families.py` to read from this doc directly (YAML frontmatter or structured Markdown parse), eliminating the manual mirror.

### By dashboards and mock focus mode

- The **family name** is what users see as a concept pill, what surfaces in weak-spot insights, and what mock focus mode filters on.
- The free-form tag is the authoring breadcrumb, surfaced only in admin/debug views.
- This separation lets authors write descriptive tags without polluting user-facing UI.

### Family resolution algorithm (mechanical)

For each `tag` in a question's `concepts` array, find its family by trying in order:

1. **Exact match** — tag appears verbatim in any family's `members` list → that family.
2. **Substring match** — tag contains any of the family's `match_patterns` (case-insensitive substring) → that family. The first family in registry order wins; this is why specificity matters in pattern design (e.g. `WINDOW FUNCTIONS` family checks for `WINDOW` and `RUNNING TOTAL` before `AGGREGATION` checks for `AGGREG`).
3. **Blocklist check** — tag matches any blocklist pattern for that track → **error**, catalog load crashes. Validator suggests the canonical alternative.
4. **No match** — **error**, catalog load crashes. Author must either add the tag to an existing family's `members` list or propose a new family.

### Updating this file

1. Open a PR that includes (a) the family change, (b) the resulting `concept_families.py` change once Phase 2 codifies the pipeline, (c) reasoning rooted in real-world / interview value (not "completeness").
2. If consolidating singleton tags into a family, list which tags collapse.
3. Run `python scripts/validate_content.py` — it will refuse the PR if any existing question's `concepts` no longer resolves.

---

## The 8 universal follow-up dimensions (chain pivots)

Used by every track's mock-only follow-up chains. Each follow-up in a chain must carry a `follow_up_dimension` value from this list; consecutive follow-ups in a chain must use different dimensions (no two `scale_pivot` follow-ups in a row). **Both rules are machine-enforced** by `backend/scripts/validate_content.py` against the canonical set in `backend/follow_up_dimensions.py` (mirrored in the frontend's `mockModeConfig.js`).

**Spelling / aliases.** The canonical token carries the `_pivot` suffix (`data_quality_pivot`). Some chains in the bank — notably Data Engineering — authored the `_pivot`-less form (`data_quality`); these are accepted as **aliases** and normalised to the canonical token by `canonical_dimension()`, so analytics and validation treat the two spellings as one dimension. New content should prefer the canonical `_pivot` form, but the alias is valid and requires no re-authoring (see `docs/decisions/DECISIONS.md` 2026-06-10).

Full chain mechanics live in [`docs/features/mock.md`](features/mock.md#follow-up-chain-atomicity-proelite--mock-only-content). This taxonomy is the universal vocabulary used across all tracks.

The five most common pivots — `scale_pivot`, `business_rule_pivot`, `ambiguity_pivot`, `edge_case_pivot`, `performance_pivot` — cover the bulk of natural interviewer escalations. `data_quality_pivot` (dirtier data than implied — distinct from `edge_case_pivot`), `stakeholder_pivot` (a human with a different agenda changes the delivery), and `abstraction_pivot` (step up a level — generalise from the instance, or reframe under a different lens) round out the set. A follow-up escalates **exactly one** dimension at a time; that single-axis escalation is what makes a chain feel like an interviewer extending the discussion rather than a new question.

### `scale_pivot`
The numbers change by an order of magnitude. The question itself doesn't morph; the answer's shape does.
- **SQL example angle:** "Now the orders table holds 10 billion rows instead of 50 million. Does your query still finish?"
- **Python example angle:** "Now the input list is 10⁸ elements. Walk me through what changes."
- **Pandas example angle:** "The file is 50 GB. How does your pipeline change?"
- **PySpark example angle:** "Cluster has 4 executors, dataset is 2 TB skewed. Your join above will fail — fix it."
- **DE example angle:** "Throughput jumps 100×. Which part of this pipeline breaks first?"
- **DM example angle:** "The dimension grows from 10 K rows to 100 M. Does your SCD strategy still work?"
- **Stats example angle:** "Now you have 10× more samples per arm. Does your test design need to change?"
- **ML example angle:** "Training set grows from 1 M to 100 M rows. What batching / memory / training-time tradeoffs surface?"
- **Experimentation example angle:** "We need to ship a decision in 1/10th the time. What changes about your design?"

### `business_rule_pivot`
The business changes its definition of something — what counts, what doesn't, who's in, who's out. Question logic stays the same; the *definition* shifts.
- SQL: "Now exclude refunded orders from revenue." / "Active means signed in *and* placed an order in the last 30 days."
- Python: "Now ignore items where category is `internal`." 
- Pandas: "Now exclude weekends from the DAU calculation."
- PySpark: "Upstream service changed its semantics — what was an 'event' is now an 'attempt + outcome' pair."
- DE: "Compliance requires you to exclude EU users from the warehouse copy. Adapt the pipeline."
- DM: "Marketing now wants 'customer' to include trial users. Does your fact-table grain still work?"
- Stats: "The metric definition changed mid-experiment. How do you handle the rolling cohort?"
- ML: "Label definition just changed (was binary, now graded 1–5). Re-think the loss."
- Experimentation: "The success metric is now NDCG@5 instead of CTR. Does your power calc still hold?"

### `data_quality_pivot`
The data is dirtier than the parent question implied. The candidate must adapt to duplicates, NULLs, late events, schema drift, orphan records.
- SQL: "There are duplicate orders for the same `order_id`. What does that do to your answer?"
- Python: "Input may contain None values. Handle gracefully."
- Pandas: "Some sessions have NULL `user_id`. What happens to your groupby?"
- PySpark: "Events arrive up to 24 hours late. Update your streaming logic."
- DE: "Upstream just started double-writing for 30 min. Your overnight pipeline fired. Diagnose."
- DM: "Conformed dimension came in with conflicting attributes from two source systems. Resolve."
- Stats: "5% of observations are MNAR (missing not at random). Does your test still make sense?"
- ML: "10% of labels are noisy. What changes about your training and evaluation?"
- Experimentation: "Tracking gap from 2 PM to 5 PM yesterday. Salvage what you can from the experiment."

### `edge_case_pivot`
The case the parent question implicitly excluded — empty input, zero users, ties, single-day windows, single-row groups — now matters.
- SQL: "What if a user has zero orders?" / "What if two products tied on revenue?"
- Python: "What if the input is empty? What if it's a single element?"
- Pandas: "What if the rolling window covers a single day?"
- PySpark: "Empty partitions on one side of the join. What does your code return?"
- DE: "First run of the pipeline, no historical state. Does your incremental logic still work?"
- DM: "A dimension has zero matching rows in the fact. Does your grain hold?"
- Stats: "n=5 per group. Is your t-test still valid?"
- ML: "Rare class has 12 examples in train, 3 in test. What do you change?"
- Experimentation: "One arm got 1% of the traffic by accident. Salvage what you can."

### `performance_pivot`
The answer works, but it's expensive. Reduce cost / latency / compute / scans without breaking correctness.
- SQL: "This query works. Reduce repeated scans of `events`."
- Python: "Your solution is O(n²). Can you get to O(n log n)?"
- Pandas: "Apply-lambda is killing you on 10 M rows. Rewrite vectorized."
- PySpark: "Three shuffles for one report. Eliminate two."
- DE: "Daily cost just spiked 3×. Find why and propose a fix."
- DM: "Fact table query takes 14 minutes. Where would aggregation help?"
- Stats: "Your bootstrap takes 4 hours. Can you reduce variance another way?"
- ML: "Inference latency is 500 ms. Budget is 50 ms. Choose."
- Experimentation: "Power analysis says 6 weeks. Business says 2 weeks. What gives?"

### `ambiguity_pivot`
The question gets *less* specified, not more. The candidate must surface clarifying assumptions, name tradeoffs, or commit to a defensible reading.
- SQL: "Define 'active user' for this report." (no answer provided — candidate proposes)
- Python: "Optimize for what — readability, runtime, memory? Justify."
- Pandas: "What time grain matters for this question? Defend your choice."
- PySpark: "Should this run hourly or daily? Argue your call."
- DE: "Is this a batch or streaming problem? Make the case."
- DM: "What's the grain of this fact? You decide."
- Stats: "Is this a one-tailed or two-tailed test? Defend it."
- ML: "What's the right metric here? Why?"
- Experimentation: "The stakeholder wants 'better engagement.' Define and defend a metric."

### `stakeholder_pivot`
A real human with a different agenda enters the picture. The technical answer doesn't change but the *delivery* of it does — and sometimes that forces a different answer.
- SQL: "Exec wants this weekly, not monthly. What changes?"
- Python: "Code review: the senior eng says your nested loop is unreadable. Refactor for readability."
- Pandas: "Analyst on your team won't trust the result unless you can show your work step by step. Show it."
- PySpark: "Infra team says this job hit the cluster cap last night. Negotiate the redesign."
- DE: "Finance owner needs daily reconciliation reports by 9 AM. Your pipeline runs at 8:45 sometimes. Solve."
- DM: "The data science team wants a different grain than the BI team. Pick or compromise."
- Stats: "PM wants a simpler explanation than a p-value. Frame the answer."
- ML: "Risk team blocks deployment because the model isn't explainable enough. What do you do?"
- Experimentation: "Leadership wants to ship despite an inconclusive test. Frame your push-back."

### `abstraction_pivot`
The interviewer steps up a level: generalise the specific case to the underlying principle, or re-frame the same problem under a different conceptual lens / framework. The data and scenario need not change — the *level of abstraction* does. This tests whether the candidate can move between the concrete and the general (and recognise the same problem in a new framing), which separates genuine understanding from pattern-matching on a memorised template.
- SQL: "You solved this for 3 tiers. Now write it so it works for any number of tiers without changing the query shape."
- Python: "That handles this graph. State the general invariant your algorithm relies on."
- Stats: "You explained the frequentist 95% CI for this conversion rate — now what does a Bayesian credible interval on the same data claim?" / "You spotted the collider here — now classify any variable as confounder, mediator, or collider in general."
- ML: "You diagnosed this leak. Generalise: what's the *class* of feature that causes train-serve skew?"
- DE: "You fixed this pipeline. Abstract the failure mode into a data-contract rule that prevents the whole class."

**Why it's a distinct dimension (reasoning-depth defense):** the other seven keep the candidate at the same level of abstraction and change an *external* property of the problem (more data, a new rule, dirtier inputs, a stakeholder). `abstraction_pivot` instead changes the *candidate's vantage point* — concrete ↔ general, or one framework ↔ another — a different and harder reasoning move that strong interviewers use to separate "knows the recipe" from "understands the principle." Added 2026-06-10 to fit high-quality Statistics chains the original 7 couldn't cleanly label — **docs serve the product** (see `docs/decisions/DECISIONS.md`).

### Authoring rules summary

- A chain (parent + follow-ups) of length N has N−1 follow-ups, each with a `follow_up_dimension`.
- **Consecutive follow-ups must use different dimensions.** Two scale pivots in a row is repetitive; mix the angles.
- The parent question carries no `follow_up_dimension` (it's the anchor).
- Author intent matters: name the dimension that *best* describes the pivot, not the most flattering one.

---

## SQL — concept families

**Modality:** Executable problem-solving. DuckDB execution.
**Reasoning archetype:** Translate a business question into a deterministic data answer, anticipating where the data and the question are each ambiguous.
**Current tag inventory:** 276 unique tags / 491 occurrences — heavy long-tail fragmentation. Top 30 tags cover ~70% of occurrences; the rest are singletons that consolidate into the families below.

### Family registry

#### `GROUPED AGGREGATION`
**What it tests:** picking the right grain, picking the right aggregate, handling NULLs in aggregates, distinguishing `COUNT(*)` vs `COUNT(col)` vs `COUNT(DISTINCT col)`.
**Typical question shape:** "compute X per Y" where Y is one or more grouping keys.
**Match patterns:** `AGGREG` (covers GROUPED AGGREGATION, VALUE AGGREGATION, CONDITIONAL AGGREGATION, MULTI-AGGREGATE), `ORDERED-SET AGGR`
**Example existing tags collapsing into this family:** GROUPED AGGREGATION (26), VALUE AGGREGATION (5), ROW COUNT AGGREGATION (6), CONDITIONAL AGGREGATION (5), MULTI-COLUMN SEGMENT AGGREGATION
**Authoring note:** plain `SUM`, `COUNT`, `AVG` mechanic terms are blocklisted — describe the *reasoning* (e.g. `CONDITIONAL AGGREGATION` over `SUM CASE WHEN`).

#### `POST-AGGREGATION FILTERING`
**What it tests:** knowing that HAVING runs after GROUP BY, what aliases are visible in HAVING, when to push filters before vs after aggregation.
**Typical question shape:** "find groups where the aggregate exceeds N."
**Match patterns:** `POST-AGGREGATION FILTER`, `HAVING`
**Example existing tags:** POST-AGGREGATION FILTERING (18), HAVING THRESHOLD (2), HAVING ON COUNT
**Real-world angle:** filtering at the wrong layer is one of the most common analyst mistakes; this family is non-negotiable.

#### `PRE-AGGREGATION FILTERING`
**What it tests:** knowing what to filter at row level *before* aggregation, recognising when filter placement changes the result.
**Match patterns:** `PRE-AGGREGATION FILTER`, `CONDITIONAL ROW FILTERING`, `RANGE FILTER`, `WHERE CLAUSE`, `IN CLAUSE`
**Example existing tags:** CONDITIONAL ROW FILTERING (20), RANGE FILTERING (2), SET MEMBERSHIP FILTERING (2), PRE VS POST AGGREGATION FILTERING

#### `MULTI-TABLE ENTITY LINKING`
**What it tests:** picking the right join type and direction, recognising when LEFT vs INNER produces different counts, avoiding fan-out from one-to-many joins.
**Match patterns:** `MULTI-TABLE`, `ENTITY LINKING`, `REQUIRED ENTITY MATCHING`, `OPTIONAL ENTITY PRESERVATION`, `LEFT JOIN DIRECTION`, `FULL OUTER`, `ANTI-JOIN`
**Example existing tags:** MULTI-TABLE ENTITY LINKING (14), REQUIRED ENTITY MATCHING (8), OPTIONAL ENTITY PRESERVATION (6), ANTI-JOIN PATTERN (3), FULL OUTER JOIN RECONCILIATION (1)
**Real-world angle:** "which users have no orders?" / "list users and their last support ticket if any" — both are entity-link reasoning, not join-mechanic recall.

#### `WINDOW FUNCTIONS`
**What it tests:** when window functions let you keep detail rows that GROUP BY would collapse, choosing the right partition, choosing rows-vs-range framing.
**Match patterns:** `WINDOW`, `WINDOWING`, `ROWS VS RANGE`, `LAG WINDOW`, `LEAD`
**Example existing tags:** WINDOW RANK (2), WINDOW RANK WITH PARTITION (2), POST-AGGREGATION WINDOWING (2), LAG WINDOW FUNCTION (1)
**Authoring note:** the *use* (running totals, period-over-period, partitioned top-N) maps to other families below; this family is reserved for questions where the window-function *choice* is the reasoning challenge.

#### `RUNNING TOTAL & MOVING WINDOW`
**What it tests:** cumulative sums, moving averages, threshold detection inside a running calculation, ROWS-vs-RANGE frame distinctions.
**Match patterns:** `RUNNING TOTAL`, `CUMULATIVE`, `MOVING AVERAGE`, `MOVING WINDOW`
**Example existing tags:** RUNNING TOTAL THRESHOLD DETECTION (2), CUMULATIVE SUM, MOVING AVERAGE
**Real-world angle:** "when did cumulative revenue first cross $1M?" — classic finance/ops question.

#### `RANKING & TOP-N PER GROUP`
**What it tests:** picking ROW_NUMBER vs RANK vs DENSE_RANK based on tie semantics, top-N-per-group via subquery/CTE/QUALIFY, deterministic tie-breaking.
**Match patterns:** `RANK`, `TOP-N`, `DEDUPLICAT`, `LATEST STATE`, `DETERMINISTIC TIE`
**Example existing tags:** PARTITIONED RANK FILTERING (3), TOP-N PER GROUP (3), TOP-N QUERY (2), WINDOW RANK (2), LATEST STATE DERIVATION (3), DETERMINISTIC TIE-BREAKING (2)
**Real-world angle:** "top 3 products per category last quarter" — every analyst writes this.

#### `DEDUPLICATION LOGIC`
**What it tests:** distinguishing DISTINCT vs GROUP BY vs ROW_NUMBER()=1, picking the right keying for "true duplicates" vs "valid repeats."
**Match patterns:** `DEDUP`, `DISTINCT ENTITY`, `DISTINCT COUNT`, `MEMBERSHIP-BASED DEDUPLICATION`
**Example existing tags:** DISTINCT ENTITY COUNTING (4), DISTINCT COUNT (4), DEDUPLICATED RESULT SHAPING (1)
**Real-world angle:** dirty event streams; tracking-system over-firing; the "is this a duplicate or a valid re-event?" question is a daily analyst task.

#### `SUBQUERY PATTERNS`
**What it tests:** when a correlated subquery is unavoidable, when EXISTS beats IN with NULLs, derived tables vs CTEs vs joins.
**Match patterns:** `SUBQUERY`, `CORRELATED`, `EXISTS PATTERN`, `NESTED FILTER`, `SCALAR SUBQUERY`
**Example existing tags:** CORRELATED SUBQUERY (7), NESTED FILTER LOGIC (5), EXISTS PATTERN (6), SCALAR SUBQUERY IN CASE
**Authoring note:** when a problem is *equally* solvable by JOIN, prefer to teach the join; subquery problems should be where the join doesn't work or is ugly.

#### `CTE PIPELINE`
**What it tests:** decomposing a multi-step problem into named layers, sequencing CTEs so each depends on the prior, knowing when a CTE materializes.
**Match patterns:** `CTE`, `MULTI-CTE`, `RECURSIVE`
**Example existing tags:** CTE PIPELINE (2), MULTI-CTE PIPELINE (2), RECURSIVE CTE (2)
**Real-world angle:** real production queries are 3–7 CTEs; teaching this is teaching "how analysts actually write SQL."

#### `TIME-SERIES BUCKETING & ARITHMETIC`
**What it tests:** date truncation, period-over-period comparisons, date arithmetic (month-end edge cases), calendar-spine joins for missing days.
**Match patterns:** `DATE`, `TIME-`, `STRFTIME`, `TEMPORAL`, `MONTHLY`, `QUARTER`, `PERIOD-OVER-PERIOD`, `CALENDAR SPINE`, `BEFORE-AND-AFTER`
**Example existing tags:** DATE TRUNCATION (2), DATE ARITHMETIC (2), MONTHLY TREND (2), TIME-WINDOW COMPARISON (2), PERIOD-OVER-PERIOD COMPARISON (1), QUARTER DERIVATION (1), CALENDAR SPINE (2), BEFORE-AND-AFTER COMPARISON (3)
**Real-world angle:** time analysis is most of analytics work; never tag with `STRFTIME` (mechanic), always with the analytical pattern.

#### `COHORT RETENTION`
**What it tests:** defining a cohort key, calculating return rate over offset weeks/months, distinguishing rolling vs fixed cohorts.
**Match patterns:** `COHORT`, `RETENTION`, `REACTIVATION`
**Example existing tags:** COHORT ANALYSIS, RETENTION BY MONTH OFFSET, REACTIVATION
**Real-world angle:** every growth team's bread and butter.

#### `FUNNEL ANALYSIS`
**What it tests:** sequencing steps, joining events to a session/journey, computing conversion rates with the right denominator.
**Match patterns:** `FUNNEL`, `CONVERSION`, `STEP CONVERSION`
**Example existing tags:** CONVERSION FUNNEL, FUNNEL DROPOFF, ACQUISITION FUNNEL
**Real-world angle:** product / marketing analytics standard.

#### `SESSIONIZATION`
**What it tests:** assigning a session ID to events based on time gaps, gap-and-island detection, state machine reasoning on event streams.
**Match patterns:** `SESSION`, `GAP`, `ISLAND`, `STATE TRANSITION`
**Example existing tags:** SEQUENTIAL EVENT PATTERN (2), STATE TRANSITION DETECTION (3), USER-PRODUCT JOURNEY MODELING (2)
**Real-world angle:** classic Meta / Stripe / Airbnb interview pattern; also a real analyst task for tracking quality investigations.

#### `CONDITIONAL LOGIC & CASE`
**What it tests:** CASE WHEN inside SUM/COUNT, CASE as a GROUP BY key for custom bucketing, rule-based row classification.
**Match patterns:** `CASE WHEN`, `RULE-BASED`, `CONDITIONAL FLAG`, `CATEGORICAL SEGM`, `PRIORITY-BASED`, `PRECEDENCE-BASED`
**Example existing tags:** RULE-BASED CLASSIFICATION (6), CONDITIONAL SEGMENT AGGREGATION (3), PRECEDENCE-BASED CLASSIFICATION (2), MULTI-COLUMN SEGMENT AGGREGATION

#### `NULL HANDLING & COALESCE`
**What it tests:** what NULL does in joins, aggregates, comparisons, ORDER BY; when COALESCE rescues you and when it lies.
**Match patterns:** `NULL`, `COALESCE`, `ZERO-COUNT`, `IS NULL`, `IS NOT NULL`
**Example existing tags:** ZERO-COUNT PRESERVATION (1), COALESCE NULL BRIDGING (1), COUNT NON-NULL vs COUNT STAR (1), NULL-BASED ROW FILTERING (3)

#### `SET OPERATIONS & COMPARISON`
**What it tests:** UNION vs UNION ALL, INTERSECT vs INNER JOIN, EXCEPT/MINUS with NULLs, anti-join patterns for "in A but not B" questions.
**Match patterns:** `SET MEMBER`, `SET DIFFER`, `UNION`, `INTERSECT`, `EXCEPT`, `CROSS-SOURCE`
**Example existing tags:** SET MEMBERSHIP FILTERING (2), BEHAVIORAL SET DIFFERENCE, CROSS-SOURCE RECONCILIATION

#### `SELF-COMPARISON & RECURSION`
**What it tests:** when self-joins solve hierarchy or row-vs-row comparison problems, recursive CTEs for variable-depth hierarchies.
**Match patterns:** `SELF-COMPAR`, `ROW-LEVEL SELF`, `ROW-TO-ROW`, `RECURSIVE`, `HIERARCHY`
**Example existing tags:** ROW-LEVEL SELF-COMPARISON (2), SELF-COMPARISON RANK EMULATION

#### `STRING PARSING & PATTERN MATCHING`
**What it tests:** SUBSTRING / SPLIT_PART / regex pickoff for extracting from delimited fields, LIKE vs ILIKE, pattern-based filtering.
**Match patterns:** `STRING`, `SPLIT_PART`, `SUBSTRING`, `PATTERN-BASED`, `LIKE`, `REGEX`
**Example existing tags:** SPLIT_PART (2), PATTERN-BASED FILTERING

#### `RESULT SHAPING & ORDERING`
**What it tests:** explicit ORDER BY when meaningful, column projection discipline, deterministic output shape, output-schema design.
**Match patterns:** `RESULT ORDERING`, `COLUMN PROJECTION`, `DETERMINISTIC RESULT`, `OUTPUT SCHEMA`, `ORDER-FIRST`
**Example existing tags:** DETERMINISTIC RESULT ORDERING (24), COLUMN PROJECTION (14), OUTPUT SCHEMA SHAPING, DEDUPLICATED RESULT SHAPING

#### `METRIC INTERPRETATION & DENOMINATOR CHOICE`
**What it tests:** picking the right metric definition under ambiguous business framing, choosing the right denominator for rates/ratios, recognising when "active user" or "revenue" or "session" has multiple defensible definitions.
**Typical question shape:** Mock-only ambiguity-pivot follow-ups; questions where the description deliberately leaves the metric definition open and the answer hinges on what the candidate picks and why.
**Member tags (canonical):** `ACTIVE-USER DEFINITION`, `REVENUE BASIS CHOICE`, `DENOMINATOR SELECTION`, `RATE BASE NORMALIZATION`, `AMBIGUOUS METRIC`
**Why this is new:** the existing bank had this implicit (questions about "active users" or "revenue including/excluding refunds") but never tagged the *reasoning* as a family. **Phase 2 (SQL) status: mock-only realism lens** — appears only on `mock_only: true` SQL questions, always co-occurring with ≥1 practice-grounded family. Other tracks: treat as a practice-curriculum target until covered.

#### `DATA QUALITY SKEPTICISM`
**What it tests:** noticing duplicates that shouldn't be there, finding orphan records, recognising suspicious NULLs, validating row counts against source-of-truth, anti-join reconciliation as a debugging tool.
**Typical question shape:** Debug-SQL questions; scenario questions where the data is dirty by design and the candidate must catch and address it before answering.
**Member tags (canonical):** `DUPLICATE DETECTION`, `ORPHAN RECORD CHECK`, `ROW COUNT RECONCILIATION`, `NULL ANOMALY INSPECTION`, `DATA QUALITY GATE`
**Why this is new:** present implicitly via DEBUG SQL questions and dirty-data scenarios, but never surfaced as a coherent reasoning family. Real practitioners spend 30–50% of their time on data quality; this family must be teachable.

#### `DOUBLE-COUNTING DETECTION`
**What it tests:** spotting fan-out from one-to-many joins, recognising inflated metrics from joining facts to facts, choosing aggregation grain to prevent multiplication.
**Typical question shape:** Mock-only debug or scenario questions where a query "looks right" but returns inflated numbers because of a join mistake.
**Member tags (canonical):** `FAN-OUT DETECTION`, `JOIN MULTIPLICATION`, `GRAIN MISMATCH`, `INFLATED METRIC DEBUG`
**Why this is new:** the bank has `MULTI-TABLE ENTITY LINKING` (14) which tests *correct* joins. This new family targets the *failure mode* where joins inflate results. DM has `DOUBLE-COUNTING` (1) and `FAN-OUT` (1) tags surfacing this idea; SQL should have a parallel family.

#### `METRIC RECONCILIATION`
**What it tests:** validating a computed metric against an independent source of truth — does my number match what finance / the source system / the prior pipeline reports? Reconciliation queries, cross-system checks, audit patterns, mismatch investigation.
**Typical question shape:** "These two queries should produce the same total but they differ by N rows / N dollars — find why." Often anchors a debug or scenario question.
**Match patterns:** `RECONCILIATION`, `AUDIT`, `CROSS-SOURCE VALIDATION`, `MISMATCH INVESTIGATION`, `SOURCE OF TRUTH`
**Member tags (canonical):** `METRIC RECONCILIATION`, `CROSS-SOURCE RECONCILIATION`, `MISMATCH AUDIT`, `ROW-COUNT RECONCILIATION` (distinct from data-quality use of the same term — here the lens is *the metric*, not *the data*)
**Why this is new:** distinct from `DATA QUALITY SKEPTICISM` — that family is about the *data* being dirty; this family is about the *computed metric* being verified against independent truth. Every senior analyst runs reconciliation queries weekly; the bank tested this only implicitly.

#### `OUTPUT SANITY VALIDATION`
**What it tests:** self-checking your own analytical output before declaring done — row count plausibility, NULL-coverage sanity, distribution-shape spot-check, "does this number even make sense given the input?"
**Typical question shape:** Mock-only scenarios where the candidate must defend why their answer is right (or, in debug variants, why an apparently-correct-looking answer is wrong because it failed a sanity check).
**Match patterns:** `SANITY`, `OUTPUT VALIDATION`, `ROW COUNT CHECK`, `OUTPUT SANITY`, `PLAUSIBILITY CHECK`
**Member tags (canonical):** `OUTPUT SANITY VALIDATION`, `RESULT PLAUSIBILITY CHECK`, `ROW COUNT SANITY`, `NULL COVERAGE SANITY`
**Why this is new:** sanity-checking your own work is the discipline that separates senior practitioners from junior ones. The bank had no family teaching this explicitly — questions either had right answers or wrong answers, with no surface for "did you verify your own output?" **Phase 2 (SQL) status: mock-only realism lens** — appears only on `mock_only: true` SQL questions, always co-occurring with ≥1 practice-grounded family. Other tracks: teach it in practice first before mock-only may recombine it.

#### `PERFORMANCE-AWARE ANALYTICS`
**What it tests:** choosing the more efficient analytical approach without sacrificing correctness — avoiding unnecessary table scans, reducing cardinality explosion before joins, minimising repeated computation across CTEs, picking the simpler correct approach over the clever expensive one. **This is analytical reasoning about cost, not engine-optimisation trivia.**
**Typical question shape:** "This query works but reads the events table 3 times — eliminate two of those reads while keeping the result identical." Or: "Two approaches give the same answer — which scales better and why?"
**Match patterns:** `PERFORMANCE-AWARE`, `SCAN REDUCTION`, `CARDINALITY`, `REPEATED COMPUTATION`, `EFFICIENT APPROACH`, `COST-AWARE`
**Member tags (canonical):** `SCAN REDUCTION`, `CARDINALITY REDUCTION`, `PRE-AGGREGATION STRATEGY`, `REPEATED COMPUTATION ELIMINATION`, `EFFICIENT ALTERNATIVE`
**Why this is new:** distinct from the chain-dimension `performance_pivot` (which is a *follow-up* angle). This family is for *practice* and *mock-only single* questions where performance reasoning is the primary skill being tested. Real practitioners reason about cost constantly; the bank made this only a follow-up dimension, never a first-class family.

### SQL blocklist

The following tags are **forbidden** as `concepts` values — they are mechanic names that obscure reasoning. The validator rejects them with a suggestion mapping to the canonical alternative:

| Blocked tag | Canonical alternative |
|---|---|
| `JOIN` | Use the entity-link family or describe the analytical purpose |
| `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `FULL JOIN` | `MULTI-TABLE ENTITY LINKING` |
| `GROUP BY` | `GROUPED AGGREGATION` (or the segment-pattern family) |
| `HAVING` | `POST-AGGREGATION FILTERING` |
| `WHERE` | `PRE-AGGREGATION FILTERING` (or the specific reasoning) |
| `WINDOW FUNCTION`, `OVER`, `PARTITION BY` | a specific window family (RANKING, RUNNING TOTAL, etc.) |
| `ROW_NUMBER`, `RANK`, `DENSE_RANK` | `RANKING & TOP-N PER GROUP` |
| `LAG`, `LEAD` | the analytical purpose (period-over-period, gap detection) |
| `CTE`, `WITH` | `CTE PIPELINE` |
| `UNION`, `INTERSECT`, `EXCEPT` | `SET OPERATIONS & COMPARISON` |
| `DISTINCT` | `DEDUPLICATION LOGIC` or `DISTINCT ENTITY COUNTING` |
| `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` | a specific aggregation family |
| `CASE`, `IIF` | `CONDITIONAL LOGIC & CASE` |
| `NULL`, `IS NULL`, `COALESCE` | `NULL HANDLING & COALESCE` |
| `STRFTIME`, `EXTRACT`, `DATE_TRUNC` | `TIME-SERIES BUCKETING & ARITHMETIC` |
| `LIKE`, `ILIKE`, `REGEX` | `STRING PARSING & PATTERN MATCHING` |
| `OR`, `AND`, `IN`, `BETWEEN` | `PRE-AGGREGATION FILTERING` or specific |
| `ORDER BY` | `RESULT SHAPING & ORDERING` |
| `LIMIT` | `RESULT SHAPING & ORDERING` or `RANKING & TOP-N PER GROUP` |
| `SUBQUERY`, `NESTED QUERY` | `SUBQUERY PATTERNS` |

---

## Python — concept families

**Modality:** Executable problem-solving. Sandbox execution. Algorithm + data structure focus.
**Reasoning archetype:** Pick the right algorithmic pattern for the problem shape; reason about time / space complexity; recognise when a brute-force solution doesn't scale.
**Current tag inventory:** 219 unique tags / 366 occurrences — mid-fragmentation; algorithm pattern names are mostly clean (lowercase canonical) but with several singleton variants.

### Family registry

#### `SLIDING WINDOW`
**What it tests:** recognising the "find / count substrings or subarrays satisfying property X" problem shape; expand/contract pointers; tracking window state efficiently.
**Match patterns:** `sliding window`, `SLIDING WINDOW`
**Example existing tags:** sliding window (6)

#### `TWO POINTERS`
**What it tests:** sorted-input traversal from both ends, fast/slow pointer for cycle / midpoint, pair-finding patterns.
**Match patterns:** `two pointer`, `TWO POINTER`
**Example existing tags:** two pointers (7)

#### `HASH-MAP STATE`
**What it tests:** O(1) membership testing, frequency counting, "have I seen this before" patterns, prefix-sum-with-hashmap.
**Match patterns:** `hash map`, `HASH MAP`, `frequency count`, `MEMBERSHIP-BASED`
**Example existing tags:** hash map (10), frequency count (2), MEMBERSHIP-BASED DEDUPLICATION (4)

#### `BINARY SEARCH`
**What it tests:** searching on a sorted array; binary search on the *answer space* (parametric search); finding boundaries (leftmost / rightmost matching).
**Match patterns:** `binary search`, `BINARY SEARCH`
**Example existing tags:** binary search (5)

#### `INDEXED SEQUENCE REASONING`
**What it tests:** array/list traversal where index *meaning* matters; subarray problems; prefix/suffix arrays; relative-position invariants.
**Match patterns:** `INDEXED SEQUENCE`, `LINEAR STATE UPDATE`, `linear scan`, `subarray`, `prefix sum`
**Example existing tags:** INDEXED SEQUENCE REASONING (19), LINEAR STATE UPDATE (7), linear scan (4), subarray (5), prefix sum (2)

#### `STREAMING / ONLINE REDUCTION`
**What it tests:** single-pass scan over an unbounded stream with **bounded auxiliary state** — see one element, commit state, no rewind. Tests whether the candidate can pick a reduction that stays correct under memory and look-back constraints. Distinct from `SLIDING WINDOW` (bounded-window expand/contract over a known input) and `INDEXED SEQUENCE REASONING` (random-access where the *index meaning* matters). Captures online statistics (running mean / variance / median via two heaps), Misra-Gries / space-budget heavy hitters, online prefix-sum / Kadane variants, gap-based sessionization in one pass, CDC last-write-wins dedup, online run-length encoding. This is the contemporary data-infra primitive (Kafka consumers, Flink/Beam reductions, monitoring-stack online quantiles).
**Match patterns:** `streaming`, `online`, `running median`, `running mean`, `running stat`, `accumulator`, `single-pass`, `bounded state`, `misra-gries`, `space-budget`, `online dedup`, `sequence processing with accumulators`
**Example existing tags:** sequence processing with accumulators (15)

#### `STRING PATTERN REASONING`
**What it tests:** character-level state machines, palindrome checking, anagram detection, KMP-style scanning, parsing tokens.
**Match patterns:** `STRING PATTERN`, `string manipulation`, `STRING`, `anagram`, `palindrome`, `run-length`, `trie`, `prefix tree`, `tokeniz`, `segmentat`, `encoding`, `normaliz`, `canonical`
**Example existing tags:** STRING PATTERN REASONING (6), string manipulation (7)
**Note:** `ORDER-FIRST REASONING` was previously listed here in error — it is a sort-then-process tag used on two-pointer/merge/heap questions and belongs to no STRING family. Strip as incidental wherever it appears.

#### `STACK & MONOTONIC STRUCTURES`
**What it tests:** LIFO ordering, balanced-bracket patterns, monotonic stack for next-greater/next-smaller, expression evaluation.
**Match patterns:** `stack`, `STACK`, `monotonic`
**Example existing tags:** stack (5)

#### `HEAP & PRIORITY QUEUE`
**What it tests:** top-K patterns, streaming median, scheduling with priority, k-way merge.
**Match patterns:** `heap`, `HEAP`, `priority queue`, `PRIORITY QUEUE`
**Example existing tags:** priority queue (4), heap (3)

#### `GREEDY CHOICE`
**What it tests:** recognising when local optima compose to a global optimum; sorting + scan; interval scheduling; minimum-cost-to-X patterns.
**Match patterns:** `greedy`, `GREEDY`, `interval scheduling`
**Example existing tags:** greedy (5), interval scheduling (2)

#### `DYNAMIC PROGRAMMING (1D)`
**What it tests:** subproblem identification, state design, transition function, base cases; sequence DP (LIS, edit distance) vs partition DP (coin change, word break).
**Match patterns:** `dynamic programming`, `DYNAMIC PROGRAMMING`, `1D DP`, `memoization`
**Example existing tags:** dynamic programming (14), memoization (2)

#### `DYNAMIC PROGRAMMING (2D)`
**What it tests:** matrix-based DP, grid problems, two-dimensional state, when 2D collapses to 1D for memory.
**Match patterns:** `2D DP`, `matrix DP`
**Example existing tags:** matrix (4)

#### `GRAPH TRAVERSAL (BFS / DFS)`
**What it tests:** picking BFS vs DFS by problem shape, visited-set discipline, level-by-level vs depth-first reasoning, cycle detection by colour-marking, unweighted reachability. Topological sort via Kahn's algorithm stays here (BFS-flavoured topo). For weighted shortest paths see `WEIGHTED SHORTEST PATH`; for connectivity / equivalence-class problems with incremental merges see `UNION-FIND & DISJOINT SET`.
**Match patterns:** `BFS`, `DFS`, `unweighted graph`, `level order`, `cycle detection`, `topological sort`, `kahn`, `reachability`, `directed graph`
**Example existing tags:** BFS (4), graph (4), topological sort (3)

#### `UNION-FIND & DISJOINT SET`
**What it tests:** equivalence-class reasoning under incremental merges — record linkage, connected components, Kruskal's MST, "are these two entities the same group yet?" patterns. Tests path-compression / union-by-rank discipline and recognising when a problem is *really* disjoint-set rather than graph traversal (incremental merges, retrieval of representatives, not a single traversal). Data analogue: entity resolution / fuzzy dedup grouping; clustering on a similarity graph; pipeline-component reachability after incremental edge additions.
**Match patterns:** `union find`, `union-find`, `disjoint set`, `disjoint-set`, `connected component`, `kruskal`, `path compression`, `union by rank`, `dsu`
**Example existing tags:** disjoint-set maintenance, connected-component discovery, path-compression optimization, union-by-rank heuristic

#### `WEIGHTED SHORTEST PATH`
**What it tests:** shortest / minimum-cost path in a weighted graph — Dijkstra with min-heap, weighted DAG critical-path via topological order + edge relaxation, A* when an admissible heuristic exists. Tests whether the candidate recognises that BFS is insufficient under non-uniform edge weights and reaches for the right relaxation pattern with a priority-ordered frontier. Data analogue: pipeline critical-path / latency analysis; lowest-cost route in a cost-annotated DAG; SLA reasoning across a service mesh.
**Match patterns:** `dijkstra`, `weighted graph`, `weighted shortest path`, `critical path`, `min cost path`, `min-cost path relaxation`, `priority-ordered frontier`, `distance map`, `a*`, `astar`
**Example existing tags:** min-cost path relaxation, priority-ordered frontier, distance map maintenance, weighted graph traversal

#### `BACKTRACKING & COMBINATORIAL SEARCH`
**What it tests:** systematic exploration of a solution tree, pruning, restoring state, permutations / combinations / subsets.
**Match patterns:** `backtracking`, `BACKTRACKING`, `combinatorics`, `recursion`
**Example existing tags:** backtracking (3), recursion (2), combinatorics (2)

#### `IN-PLACE TRANSFORMATION & SPACE OPTIMIZATION`
**What it tests:** modifying input without extra allocation, two-pass with constant extra space, recognising when O(1) extra space is achievable.
**Match patterns:** `in-place`, `IN-PLACE`, `SPACE`
**Example existing tags:** in-place (2)

#### `MODULAR ARITHMETIC & NUMBER THEORY`
**What it tests:** modular operations to avoid overflow, GCD / LCM patterns, prime factorization, bit-manipulation tricks.
**Match patterns:** `modular`, `MODULAR`, `number theory`
**Example existing tags:** modular arithmetic (3)

#### `LIST & COLLECTION TRANSFORMATION`
**What it tests:** Pythonic list comprehensions and `collections.Counter` / `defaultdict` patterns; transformation pipelines.
**Match patterns:** `list manipulation`, `LIST`, `collections`
**Example existing tags:** list manipulation (3), collections (3)

### Python blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `for loop`, `while loop` | the algorithmic pattern (sliding window, two pointers, etc.) |
| `if/else`, `conditional` | the algorithmic pattern |
| `function`, `def` | the algorithmic pattern |
| `dictionary`, `dict` | `HASH-MAP STATE` |
| `set` | `HASH-MAP STATE` (if membership) or specific |
| `list`, `tuple` | the algorithmic pattern |
| `heapq`, `bisect`, `collections.X` | the pattern that motivates the library (HEAP, BINARY SEARCH, etc.) |
| `sort`, `sorted` | only allowed when sorting *is* the reasoning step (otherwise the pattern it enables) |
| `lambda` | the algorithmic pattern |

---

## Pandas — concept families

**Modality:** Executable problem-solving. Sandbox execution.
**Reasoning archetype:** Express data transformations idiomatically (vectorized, accessor-driven) — never SQL-in-Python. Pick the right DataFrame operation for the problem shape.
**Current tag inventory:** 263 unique tags / 494 occurrences — similar long-tail shape to SQL.

### Family registry

#### `GROUPED AGGREGATION`
**Match patterns:** `GROUPED AGGREGATION`, `groupby aggregation`, `aggregation`, `named aggregation`
**Example existing tags:** GROUPED AGGREGATION (41), aggregation (6), named aggregation (5), groupby aggregation (4)

#### `MULTI-DATAFRAME ENTITY LINKING`
**What it tests:** `merge` semantics (how / on / suffixes), recognising when `concat` vs `merge` vs `join` is right, handling many-to-many merges.
**Match patterns:** `MULTI-DATAFRAME`, `multi-table join`, `ENTITY LINKING`, `MERGE`
**Example existing tags:** MULTI-DATAFRAME ENTITY LINKING (20), multi-table join (4), left join (3)

#### `RESHAPING & PIVOT`
**What it tests:** `pivot` / `pivot_table` / `melt` / `stack` / `unstack` — picking the right one for the input vs desired shape.
**Match patterns:** `WIDE-FORM RESHAPING`, `pivot`, `melt`, `stack`, `unstack`
**Example existing tags:** WIDE-FORM RESHAPING (6)

#### `MISSING VALUE STRATEGY`
**What it tests:** when to drop, when to impute, picking the right fill value (zero vs mean vs forward-fill), distinguishing NaN from None from NaT.
**Match patterns:** `MISSING-VALUE`, `missing values`, `IMPUTATION`, `fillna`
**Example existing tags:** MISSING-VALUE IMPUTATION (4), missing values (4)

#### `DATETIME OPERATIONS`
**What it tests:** parsing strings to datetimes, `.dt` accessor for component extraction, timedelta arithmetic, timezone awareness.
**Match patterns:** `datetime`, `DATETIME`, `timedelta`, `time series`, `date formatting`
**Example existing tags:** datetime (15), DATETIME TYPE PARSING (4), timedelta (4), time series (7), date formatting (3)

#### `WINDOW & ROLLING OPERATIONS`
**What it tests:** `.rolling()` and `.expanding()` for windowed aggregates; `.resample()` for time-based windowing; ROWS-vs-window semantics.
**Match patterns:** `rolling`, `ROLLING`, `expanding`, `resample`, `cumsum`
**Example existing tags:** rolling window (3), cumsum (3)

#### `RANKING & TOP-N PER GROUP`
**What it tests:** `.rank()` vs `.nlargest()` vs sort-and-slice; tie semantics; per-group top-N via groupby + transform; deterministic tie-breaking.
**Match patterns:** `rank`, `RANK`, `TOP-K`, `TOP-N`, `nlargest`, `DETERMINISTIC TIE`
**Example existing tags:** rank (4), TOP-K RESULT EXTRACTION (4)
**Cross-track alignment:** same family name as SQL — `TOP-N` member preserved alongside `TOP-K` so existing pandas tags continue to resolve.

#### `DEDUPLICATION LOGIC`
**What it tests:** `.drop_duplicates()` keying, `.nunique()` per group, `.value_counts()` shape; distinguishing "true duplicates" from "valid repeats."
**Match patterns:** `DEDUP`, `DISTINCT`, `unique`, `value_counts`, `distinct counting`
**Example existing tags:** DISTINCT ENTITY COUNTING (5), distinct counting (3)
**Cross-track alignment:** same family name as SQL — the reasoning transfers directly. A `DUPLICATE EVENT COLLAPSE` tag works in both tracks.

#### `BOOLEAN INDEXING & FILTERING`
**What it tests:** boolean mask construction, `.loc[]` vs `.iloc[]` discipline, chained-condition filtering, query string syntax.
**Match patterns:** `boolean indexing`, `BOOLEAN INDEXING`, `NULL-BASED ROW FILTERING`, `query`
**Example existing tags:** boolean indexing (4), NULL-BASED ROW FILTERING (3)

#### `COLUMN SELECTION & PROJECTION`
**What it tests:** explicit column selection over `.iloc`, derived column expressions, `.assign()` for chain-friendly transforms.
**Match patterns:** `column selection`, `derived columns`, `.assign`
**Example existing tags:** column selection (5), derived columns (6)

#### `METHOD CHAINING & PIPELINE STYLE`
**What it tests:** writing pandas as a readable chain, avoiding intermediate variables, `.pipe()` for custom functions in chains.
**Match patterns:** `METHOD CHAINING`, `pipe`, `chain`
**Example existing tags:** METHOD CHAINING (3)

#### `CATEGORICAL & BINNING`
**What it tests:** `pd.cut` / `pd.qcut` for binning continuous data, `.astype('category')` for memory + speed.
**Match patterns:** `BUCKETING`, `cut`, `qcut`, `CATEGORICAL`, `binning`
**Example existing tags:** VALUE BUCKETING (4), ORDERED CATEGORICAL BINNING (3)

#### `TRANSFORM VS AGGREGATE`
**What it tests:** `.groupby().transform()` for per-group features that preserve row count vs `.groupby().agg()` for collapsing.
**Match patterns:** `transform`, `TRANSFORM`
**Example existing tags:** transform (4)

#### `OUTPUT SHAPE & ORDERING`
**What it tests:** `.reset_index(drop=True)` discipline, explicit `.sort_values()` for deterministic output, column ordering.
**Match patterns:** `OUTPUT SCHEMA`, `RESULT ORDERING`, `DETERMINISTIC`, `reset_index`
**Example existing tags:** DETERMINISTIC RESULT ORDERING (18), OUTPUT SCHEMA SHAPING (8)

#### `MEMORY & VECTORIZATION REASONING`
**What it tests:** when `apply(lambda)` is fine vs when it's a 10× slowdown, picking dtypes for memory, chunking large reads, recognising the row-wise vs column-wise antipattern.
**Match patterns:** `VECTORIZATION OVER APPLY`, `DTYPE MEMORY CHOICE`, `CHUNK READING`, `APPLY VS TRANSFORM TRADEOFF`, `MEMORY FOOTPRINT OPTIMIZATION`, `DTYPE DOWNSIZING`, `CATEGORICAL ENCODING`, `MEMORY USAGE AUDITING`, `LOSSLESS TYPE CONVERSION`, `int32 downcast`, `astype category`, `deep=True`, `VECTORIZ`, `MEMORY`
**Practice grounding:** 33021 ("Memory optimization with dtype conversion") anchors this family; vectorized-vs-apply + dtype-choice reasoning is gradable via `assert_frame_equal` (dtype mismatches are caught). Questions 32049 and 33038 extend coverage to medium difficulty and the vectorize-over-apply specific pattern.

#### `DEBUG PANDAS`
**Match patterns:** `debug`, `DEBUG`, `KeyError`
**Example existing tags:** debug (5), KeyError (3)

#### `METRIC INTERPRETATION & DENOMINATOR CHOICE` *(mock-only realism)*
**Designation:** mock-only realism family. May appear **only** on `mock_only: true` questions; must co-occur with ≥1 practice-grounded family; enforced by `_validate_mock_only_realism()`.
**What it tests:** same as the SQL family of the same name — picking the right metric definition under ambiguous business framing, choosing the right denominator for rates / ratios, recognising when "active user" / "revenue" / "session" has multiple defensible definitions, defending the call.
**Typical question shape:** Mock-only ambiguity-pivot framings where the description deliberately leaves the metric definition open and the answer hinges on what the candidate picks.
**Match patterns:** `ACTIVE-USER DEFINITION`, `DENOMINATOR`, `RATE BASE`, `AMBIGUOUS METRIC`, `METRIC INTERPRETATION`, `KPI INTERPRETATION`
**Member tags (canonical):** `METRIC INTERPRETATION`, `DENOMINATOR SELECTION`, `RATE BASE NORMALIZATION`, `AMBIGUOUS KPI DEFINITION`, `BUSINESS RULE DISAMBIGUATION`
**Cross-track alignment:** parallel to the SQL family. The same business-reasoning skill applies regardless of the language used to compute it.

#### `DATA QUALITY SKEPTICISM`
**What it tests:** same reasoning as the SQL family — noticing duplicates that shouldn't be there, finding orphan records, recognising suspicious NULLs, validating row counts against source-of-truth, anti-join reconciliation as a debugging tool. The pandas surface adds dtype-anomaly detection (object column where numeric expected, NaT vs NaN vs None).
**Typical question shape:** Mock-only debug or scenario questions where the input DataFrame is dirty by design and the candidate must catch and address it before answering.
**Match patterns:** `DATA QUALITY`, `DUPLICATE DETECTION`, `ORPHAN`, `NULL ANOMALY`, `DTYPE ANOMALY`, `ROW COUNT SANITY`
**Member tags (canonical):** `DATA QUALITY SKEPTICISM`, `DUPLICATE DETECTION`, `ORPHAN RECORD CHECK`, `NULL ANOMALY INSPECTION`, `DTYPE ANOMALY DETECTION`
**Cross-track alignment:** parallel to SQL. Real practitioners spend 30–50% of their time on data quality regardless of the tool.

#### `DOUBLE-COUNTING DETECTION`
**What it tests:** same as SQL — spotting fan-out from one-to-many merges, recognising inflated metrics from merging facts to facts, choosing aggregation grain to prevent multiplication. Pandas-specific failure mode: `merge(how='left')` that silently inflates rows when right side has duplicates on the join key.
**Typical question shape:** Mock-only debug questions where a pandas pipeline "looks right" but returns inflated numbers because of a merge mistake.
**Match patterns:** `FAN-OUT`, `JOIN MULTIPLICATION`, `MERGE MULTIPLICATION`, `GRAIN MISMATCH`, `INFLATED METRIC`
**Member tags (canonical):** `FAN-OUT DETECTION`, `MERGE MULTIPLICATION`, `GRAIN MISMATCH`, `INFLATED METRIC DEBUG`
**Cross-track alignment:** parallel to SQL.

#### `OUTPUT SANITY VALIDATION` *(mock-only realism)*
**Designation:** mock-only realism family. May appear **only** on `mock_only: true` questions; must co-occur with ≥1 practice-grounded family; enforced by `_validate_mock_only_realism()`.
**What it tests:** same as the SQL family — self-checking your own pipeline's output before declaring done. Pandas-specific angle includes verifying `.reset_index(drop=True)` discipline, dtype assertions, shape assertions (no rows lost / no rows gained unexpectedly).
**Typical question shape:** Mock-only scenarios where the pipeline produces an answer that *looks* correct but fails a sanity check the candidate should have run.
**Match patterns:** `SANITY`, `OUTPUT VALIDATION`, `ROW COUNT CHECK`, `SHAPE ASSERTION`, `DTYPE ASSERTION`, `PLAUSIBILITY CHECK`
**Member tags (canonical):** `OUTPUT SANITY VALIDATION`, `RESULT PLAUSIBILITY CHECK`, `SHAPE ASSERTION`, `DTYPE SANITY`
**Cross-track alignment:** parallel to SQL.

#### `PERFORMANCE-AWARE ANALYTICS` *(mock-only realism)*
**Designation:** mock-only realism family. May appear **only** on `mock_only: true` questions; must co-occur with ≥1 practice-grounded family; enforced by `_validate_mock_only_realism()`.
**What it tests:** choosing the more efficient pandas approach without sacrificing correctness — vectorize over `apply(lambda)`, pick the right dtype for memory, chunk large reads instead of loading everything, recognise the row-wise antipattern. **This is question-level performance reasoning, distinct from the `performance_pivot` chain dimension and from the existing `MEMORY & VECTORIZATION REASONING` family** (which focuses on the vectorize-vs-apply choice specifically; this family is the broader analytical-cost family that includes pre-aggregation, query pushdown, and scan-reduction reasoning).
**Typical question shape:** "This pipeline finishes in 40 minutes on 10M rows — get it under 5 minutes without changing the output." Or: "Two approaches give the same answer — which scales better?"
**Match patterns:** `PERFORMANCE-AWARE`, `SCAN REDUCTION`, `CARDINALITY REDUCTION`, `PRE-AGGREGATION STRATEGY`, `EFFICIENT APPROACH`, `COST-AWARE`
**Member tags (canonical):** `PRE-AGGREGATION STRATEGY`, `SCAN REDUCTION`, `CARDINALITY REDUCTION`, `EFFICIENT ALTERNATIVE`
**Cross-track alignment:** parallel to SQL. Note: `MEMORY & VECTORIZATION REASONING` stays as a separate Pandas-native family — it tests the specific vectorize-vs-apply tradeoff which has no direct SQL analogue.

### Pandas blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `groupby`, `df.groupby` | `GROUPED AGGREGATION` (or `TRANSFORM VS AGGREGATE`) |
| `merge`, `df.merge`, `join` | `MULTI-DATAFRAME ENTITY LINKING` |
| `pivot`, `pivot_table`, `melt` | `RESHAPING & PIVOT` |
| `fillna`, `dropna` | `MISSING VALUE STRATEGY` |
| `dt`, `to_datetime` | `DATETIME OPERATIONS` |
| `rolling`, `resample` | `WINDOW & ROLLING OPERATIONS` |
| `rank`, `nlargest`, `nsmallest` | `RANKING & TOP-N PER GROUP` |
| `drop_duplicates`, `nunique`, `value_counts` | `DEDUPLICATION LOGIC` |
| `loc`, `iloc`, `query` | `BOOLEAN INDEXING & FILTERING` or `COLUMN SELECTION & PROJECTION` |
| `apply`, `apply(lambda)` | `MEMORY & VECTORIZATION REASONING` (or the underlying pattern) |
| `concat`, `append` | the entity-link or reshape family |
| `cut`, `qcut` | `CATEGORICAL & BINNING` |
| `sort_values`, `reset_index` | `OUTPUT SHAPE & ORDERING` |

---

## PySpark — concept families

**Modality:** Code-adjacent reasoning. No execution. Question types: conceptual / predict_output / debug / scenario / optimization. Response: MCQ.
**Reasoning archetype:** Reason about Spark's execution model — what code triggers a shuffle, when broadcast wins, where memory goes, what AQE rewrites — without running the job.
**Current tag inventory:** Phase 2 (2026-05) consolidated 493 unique tags / 623 occurrences to 23 canonical families via match-pattern expansion, blocklist enforcement, and agent-based retags. Target: UNRESOLVED = 0. Two new families added (`WINDOW FUNCTIONS & FRAMES`, `COLLECTION & ARRAY OPERATIONS`) to cover previously ungrounded mock content.

### Family registry

#### `EXECUTION MODEL REASONING`
**What it tests:** transformation-vs-action distinction, lazy evaluation, DAG construction, stage / task / job semantics, RDD vs DataFrame API, session lifecycle, iterative algorithm lineage explosion.
**Match patterns:** `lazy evaluation`, `EXECUTION MODEL`, `DAG`, `transformations vs actions`, `stage`, `lineage`, `RDD`, `DataFrame API`, `Dataset vs`, `immutability`, `job execution`, `cluster architecture`, `distributed system`, `SparkSession`, `getOrCreate`, `session lifecycle`, `idempotent factory`, `Spark SQL catalog`, `session-scoped`, `SPARK EXECUTION HIERARCHY`, `task scheduling`, `Tungsten`, `execution engine`, `recomputation`, `checkpoint`, `iterative algorithm`, `lineage explosion`, `DAG complexity`, `DAG depth`, `F.expr`, `SQL expression`, `actions`, `return values`

#### `NARROW VS WIDE TRANSFORMATIONS`
**What it tests:** which operations require shuffles, which stay within partition, why this matters for performance.
**Match patterns:** `narrow vs wide`, `NARROW TRANSFORMATION`, `WIDE TRANSFORMATION`, `shuffle boundary`
**Precision note:** `shuffle` (bare) resolves to SHUFFLE REASONING only, not here. `narrow vs wide` (bare) resolves here only, not to EXECUTION MODEL REASONING.

#### `SHUFFLE REASONING`
**What it tests:** identifying shuffle triggers, shuffle cost in I/O, `spark.sql.shuffle.partitions` tuning, shuffle elimination strategies, `reduceByKey` vs `groupByKey`, global sort.
**Match patterns:** `shuffle`, `reduceByKey`, `groupByKey`, `map-side combine`, `co-location`, `sortWithinPartitions`, `global sort`, `orderBy`, `shuffle partition imbalance`
**Precision note:** `shuffle` resolves here only; `narrow vs wide` resolves to NARROW VS WIDE TRANSFORMATIONS only.

#### `JOIN STRATEGY SELECTION`
**What it tests:** broadcast vs sort-merge vs shuffle-hash decision, `autoBroadcastJoinThreshold`, when to force broadcast, Cartesian product costs.
**Match patterns:** `broadcast join`, `JOIN`, `join optimization`, `autoBroadcast`, `BROADCAST`, `sort-merge`, `Cartesian product`, `small table optimization`, `hint override`, `build-side replication`

#### `PARTITIONING STRATEGY`
**What it tests:** partition count selection, `repartition` vs `coalesce` vs `partitionBy` on write, partition pruning, dynamic partition pruning, write directory layout.
**Match patterns:** `partitioning`, `PARTITION SHAPE`, `partition pruning`, `coalesce`, `repartition`, `dynamic partition pruning`, `partitions`, `partitionBy`, `partition sizing`, `partition count`, `partition splitting`, `directory structure`, `block size`, `data distribution`, `DPP`, `scan-time pruning`, `partition scan strategy`, `partition key alignment`, `downstream parallelism`, `output parallelism`, `partitioned write`, `advisoryPartitionSize`, `partition-level transfer`, `partition vs file-level`

#### `DATA SKEW & MITIGATION`
**What it tests:** detecting skew, salting strategies, AQE skew-join optimization, custom partitioner approaches.
**Match patterns:** `data skew`, `SKEW`, `salting`, `hot key`, `imbalance`, `partition imbalance`

#### `ADAPTIVE QUERY EXECUTION`
**What it tests:** what AQE rewrites at runtime, partition coalescing post-shuffle, sort-merge-to-broadcast conversion, skew handling, runtime partition restructuring.
**Match patterns:** `AQE`, `adaptive query execution`, `runtime rewrite`, `runtime plan`, `runtime join`, `runtime partition restructuring`, `runtime optimization`

#### `CATALYST OPTIMIZER`
**What it tests:** what the optimizer does for free (predicate pushdown, projection pushdown), logical vs physical plans, when optimizer cannot help, column pruning, file-level statistics for pruning.
**Match patterns:** `Catalyst`, `optimizer`, `logical plan`, `physical plan`, `predicate pushdown`, `projection pushdown`, `query plan`, `explain`, `execution plan`, `query optimization`, `analysis phase`, `pipeline optimization`, `Exchange operator`, `HashAggregate`, `column pruning`, `data skipping`, `data-skipping pruning`, `file-level statistics`, `per-file min`, `row group pruning`, `I/O optimization`, `I-O reduction`, `column-statistics filtering`, `execution plan equivalence`, `predicate pushdown in merge`

#### `MEMORY MANAGEMENT`
**What it tests:** driver vs executor memory, OOM debugging, when `collect()` kills the driver, GC pressure, spill to disk, `toPandas` driver materialization, Arrow serialisation overhead.
**Match patterns:** `memory`, `OOM`, `OutOfMemoryError`, `off-heap`, `GC`, `spill`, `serialization`, `DRIVER-SIDE MATERIALIZATION`, `garbage collection`, `JVM GC`, `JVM object`, `disk spill`, `toPandas`, `data collection anti`, `collect() anti`, `cluster-side aggregation`, `distributed aggregation`, `materialisation`, `materialization`, `YARN`, `Apache Arrow`, `arrow serial`

#### `CACHING & PERSISTENCE`
**What it tests:** `cache()` vs `persist()` with explicit storage level, when caching helps vs hurts, `unpersist()` discipline.
**Match patterns:** `caching`, `cache`, `persist`, `unpersist`, `STORAGE LEVEL`

#### `SCHEMA & TYPE HANDLING`
**What it tests:** `inferSchema` tradeoffs, explicit `StructType`, schema evolution, type coercion gotchas, null semantics (Python None vs Spark null), column resolution.
**Match patterns:** `schema`, `inferSchema`, `StructType`, `type coercion`, `StringType`, `LongType`, `DoubleType`, `IntegerType`, `type inference`, `type promotion`, `type contract`, `type safety`, `returnType`, `aggregation output types`, `nullable vs non-nullable`, `null propagation`, `silent null production`, `null production`, `cast null-on-failure`, `permissive nullability`, `conservative nullability`, `computed column nullability`, `column reference qualification`, `column resolution`, `unionByName`, `positional matching`, `column renaming`, `Python None vs`, `NDJSON`, `JSON parsing`

#### `FILE FORMATS & READERS`
**What it tests:** Parquet vs CSV vs JSON tradeoffs, column projection benefits in columnar formats, file-size sweet spots.
**Match patterns:** `Parquet`, `CSV reading`, `FILE FORMAT`, `columnar`

#### `UDF & PYTHON BOUNDARY`
**What it tests:** UDF performance cost, pandas-UDF (vectorized) vs regular UDF memory model, JVM–Python boundary, `mapPartitions` initialization overhead.
**Match patterns:** `UDF`, `pandas UDF`, `vectorised execution`, `vectorized execution`, `JVM-Python`, `mapPartitions`, `initialization overhead`, `accumulator`, `Python UDF`

#### `STRUCTURED STREAMING`
**What it tests:** output modes (append / update / complete), watermarks, late-data handling, stateful streaming, `foreachBatch` semantics, Kafka integration.
**Match patterns:** `structured streaming`, `STREAMING`, `stream-`, `micro-batch`, `watermark`, `foreachBatch`, `stateful aggreg`, `mapGroupsWithState`, `foreach`, `unbounded table`, `continuous processing`, `late data`, `late-data`, `GroupStateTimeout`, `state expiration`, `state management`, `Kafka`, `event-time vs processing-time`, `event time vs processing time`, `update mode`, `append mode`, `LATE-DATA DISCARD RULES`, `APPEND-MODE EMISSION RULES`, `EVENT-TIME GUARANTEE BOUNDARIES`, `custom sinks`, `streaming window`, `watermark column mismatch`, `stateful aggregation scaling`, `output mode`, `late data drop`, `late data handling`, `event-time latency`, `append mode window emission`, `Kafka consumer offset`

#### `DELTA LAKE OPERATIONS`
**What it tests:** MERGE semantics, time travel (`versionAsOf`), schema evolution, Z-ordering vs partitioning, ACID guarantees, CDC pipeline design.
**Match patterns:** `Delta Lake`, `DELTA`, `MERGE INTO`, `DELTA MERGE`, `versionAsOf`, `transaction log`, `ACID TABLE MUTATION`, `matched vs unmatched`, `incremental table reconciliation`, `immutable file rewrite`, `table maintenance`, `CDC pipeline`, `CDC batch`, `upsert correctness`, `merge-condition logic`, `merge cardinality`, `SQL MERGE`, `Z-order clustering`, `Z-ordering`, `Z-order`, `delta streaming`, `incremental write clustering`, `OPTIMIZE ZORDER`, `time travel`
**Precision note:** bare `MERGE` is intentionally **not** a match pattern — it false-positives on `sort-merge join` tags. Use `MERGE INTO` or `DELTA MERGE` as concept tag values.

#### `FAULT TOLERANCE & RECOVERY`
**What it tests:** lineage-based recovery, speculative execution, straggler tasks, at-least-once vs exactly-once sink semantics, idempotent sink design.
**Match patterns:** `fault tolerance`, `FAULT`, `speculative execution`, `recovery`, `straggler task`, `straggler`, `spark.speculation`, `idempotent sink`, `sink idempotency`, `at-least-once write`, `at-least-once semantics`, `foreachBatch at-least`, `exactly-once`, `task output commit`, `partial write on`, `external side effect`, `failure-safe`

#### `DEBUG SPARK ERRORS`
**What it tests:** reading `AnalysisException` for schema/column issues, `OutOfMemoryError` for skew/driver issues, `TypeError` for Python boundary mismatches, common stack-trace interpretation.
**Match patterns:** `AnalysisException`, `DEBUG`, `debug`, `Exception`, `TypeError`

#### `PERFORMANCE TUNING & TRADE-OFFS`
**What it tests:** general performance reasoning — which configs to tune in what order, when to add hardware vs change code, small-file problem, cloud storage metadata cost.
**Match patterns:** `performance`, `PERFORMANCE TUNING`, `tuning`, `spark.serializer`, `task overhead`, `small file problem`, `cloud storage metadata`, `production pattern`, `large data`, `anti-pattern avoidance`, `external merge-sort`, `false positives`, `probabilistic`

#### `DATA QUALITY SKEPTICISM` *(practice-grounded — Phase 2)*
**What it tests:** PySpark surface of the cross-track family — recognising suspect data before processing it: late-arriving events that should have been watermarked, schema drift the read silently absorbed, NULL-key explosion on joins, duplicate event-IDs from at-least-once upstreams, non-deterministic deduplication with `dropDuplicates`. The PySpark question-shape is usually `predict_output` ("what does this code do when the input has X dirty rows?") or `debug` ("the output looks wrong because the input was dirty in this specific way — diagnose").
**Match patterns:** `DATA QUALITY`, `LATE EVENT`, `DUPLICATE EVENT`, `NULL KEY`, `DIRTY INPUT`, `dropDuplicate`, `non-determinism`, `non-determin`, `deduplication`, `dedup`, `source dedup`, `null handling`, `production vs dev data`, `NaN-to-null`
**Member tags (canonical):** `DATA QUALITY SKEPTICISM`, `LATE-EVENT HANDLING`, `DUPLICATE EVENT COLLAPSE`, `NULL KEY DETECTION`, `DIRTY INPUT REASONING`
**Cross-track alignment:** parallel to the SQL and Pandas families of the same name.
**Practice grounding:** DATA QUALITY SKEPTICISM is practice-grounded in PySpark (not mock-only realism). MCQ format makes this reasoning gradeable as `predict_output` / `debug`.

#### `DOUBLE-COUNTING DETECTION` *(practice-grounded — Phase 2)*
**What it tests:** spotting fan-out from one-to-many joins in PySpark, same conceptual failure mode as SQL — but the PySpark angle adds the operational consequence: a fan-out join in Spark not only inflates the output but also amplifies shuffle volume and can tip the job into OOM. The reasoning is therefore *both* correctness and runtime impact.
**Match patterns:** `DOUBLE-COUNTING`, `DOUBLE COUNTING`, `FAN-OUT`, `JOIN MULTIPLICATION`, `GRAIN MISMATCH`, `INFLATED OUTPUT`
**Member tags (canonical):** `FAN-OUT DETECTION`, `JOIN MULTIPLICATION`, `GRAIN MISMATCH`, `INFLATED OUTPUT DEBUG`, `DOUBLE-COUNTING DETECTION`
**Cross-track alignment:** parallel to SQL and Pandas.
**Practice grounding:** new `debug` / `predict_output` questions authored in Phase 2 (medium + hard). True content gap prior to Phase 2.

#### `OUTPUT SANITY VALIDATION` *(practice-grounded — Phase 2)*
**What it tests:** PySpark-specific self-check reasoning — `.count()` plausibility on the output DataFrame, `.printSchema()` shape verification after a transform, row-count assertions before writes, `count()` vs `countDistinct()` confusion, `len()` vs `count()` driver-vs-executor anti-pattern.
**Match patterns:** `SANITY`, `OUTPUT VALIDATION`, `ROW COUNT CHECK`, `SCHEMA ASSERTION`, `PLAUSIBILITY CHECK`, `count vs countDistinct`, `len() vs count`, `Spark UI diagnosis`, `SPARK UI TASK METRICS`, `FULL TABLE SCAN DIAGNOSIS`
**Member tags (canonical):** `OUTPUT SANITY VALIDATION`, `ROW COUNT ASSERTION`, `SCHEMA SHAPE CHECK`, `RESULT PLAUSIBILITY CHECK`
**Cross-track alignment:** parallel to SQL and Pandas.
**Practice grounding:** existing practice questions retagged in Phase 2. No mock-only realism class for PySpark (MCQ format makes this gradeable as `predict_output` / `debug`).

#### `WINDOW FUNCTIONS & FRAMES` *(new — Phase 2)*
**What it tests:** ranking functions (`RANK` / `DENSE_RANK` / `ROW_NUMBER`), window-frame semantics (`ROWS BETWEEN` / `RANGE BETWEEN`), `rowsBetween` / `rangeBetween` API, cumulative / running aggregations via windows, tie handling in `ORDER BY` within a window, `partitionBy` / `orderBy` semantics in window context.
**Match patterns:** `window function`, `window frame`, `rowsBetween`, `rangeBetween`, `ROWS vs RANGE`, `DENSE_RANK`, `ROW_NUMBER`, `cumulative aggregation`, `running aggregation`, `ties handling`, `tie handling`, `RANK`
**Cross-track alignment:** SQL `WINDOW FUNCTIONS`, Pandas `WINDOW & ROLLING` (executable-track reusability principle).
**Why new:** existing mock questions 42041 and 43029 tested window-frame semantics without practice grounding. Phase 2 adds practice questions to establish the family.

#### `COLLECTION & ARRAY OPERATIONS` *(new — Phase 2)*
**What it tests:** `explode` / `explode_outer`, `collect_list` / `collect_set`, array-column transformations, `pivot`, lateral-view semantics, null-vs-empty-array distinction, row preservation across explode.
**Match patterns:** `array operation` *(self-resolving)*, `explode`, `collect_list`, `collect_set`, `collect list`, `collect set`, `array column`, `array ordering`, `outer lateral view`, `pivot`, `null vs empty array`, `row preservation`, `wide DataFrame`
**Why new:** existing mock questions 42040, 42050, and 43028 tested explode / pivot without practice grounding. Phase 2 adds practice questions to establish the family.

**Note on PySpark scope of cross-track families:** `METRIC INTERPRETATION & DENOMINATOR CHOICE` is intentionally NOT added to PySpark — PySpark questions test Spark execution reasoning, not business-metric interpretation. `PERFORMANCE-AWARE ANALYTICS` is also not added: PySpark already has 7 native performance-focused families (`SHUFFLE REASONING`, `JOIN STRATEGY SELECTION`, `DATA SKEW & MITIGATION`, `MEMORY MANAGEMENT`, `ADAPTIVE QUERY EXECUTION`, `CATALYST OPTIMIZER`, `PERFORMANCE TUNING & TRADE-OFFS`).

**No mock-only realism families for PySpark.** All three ⚡ families (`DATA QUALITY SKEPTICISM`, `DOUBLE-COUNTING DETECTION`, `OUTPUT SANITY VALIDATION`) are practice-grounded because PySpark is MCQ-only — sanity-check and validation reasoning grades cleanly as `predict_output` or `debug` MCQ. The SQL rationale (executable queries don't grade sanity-check reasoning) does not transfer.

### PySpark blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `withColumn`, `select`, `filter` | the reasoning pattern (transformation type, projection, etc.) |
| `DataFrame`, `df` | reasoning family |
| `Spark`, `SparkSession`, `spark.X` | reasoning family |
| `RDD` | `EXECUTION MODEL REASONING` |
| `parallelism` | `PARTITIONING STRATEGY` |
| `executor`, `driver` (alone) | `MEMORY MANAGEMENT` (the reasoning, not the entity name) |
| `alias` | `SCHEMA & TYPE HANDLING` (column renaming reasoning) or strip as incidental |
| `withColumnRenamed` | `SCHEMA & TYPE HANDLING` |
| `col() function` | strip as incidental (mechanic name, not reasoning family) |
| `show`, `limit`, `head` | `MEMORY MANAGEMENT` (driver materialisation anti-pattern) or strip |
| `Row objects` | `SCHEMA & TYPE HANDLING` or strip as incidental |

---

## Statistics — concept families

**Modality:** Hybrid. Conceptual MCQ + numerical Python execution.
**Reasoning archetype:** Choose the right inference tool for the question; recognise when assumptions don't hold; reason about uncertainty as a first-class quantity.
**Current tag inventory:** 149 unique tags / 346 occurrences. Existing tags are mostly **lowercase canonical** (e.g. `probability`, `hypothesis testing`) — a casing inconsistency vs the rest of the bank that needs normalization. Families below use **lowercase** as the canonical form for this track only (preserves existing tags); the rest of the bank uses UPPERCASE.

### Family registry

#### `descriptive statistics`
Mean, median, mode, IQR, std dev, outlier detection — the summary-statistic reasoning before any inference.
**Match patterns:** `descriptive statistics`, `measures of central tendency`, `outliers`, `variance`, `standard deviation`
**Example existing tags:** descriptive statistics (16), measures of central tendency (4), outliers (3)

#### `probability & combinatorics`
Sample space, conditional probability, independence, Bayes' theorem, permutations / combinations, expected value, variance of a random variable.
**Match patterns:** `probability`, `combinatorics`, `combinations`, `permutations`, `expected value`, `Bayes`, `conditional probability`, `independence`
**Example existing tags:** probability (20), expected value (5), independence (4), combinatorics (4), combinations (3), conditional probability (3), Bayes' theorem (2)

#### `distributions`
Bernoulli, binomial, Poisson, normal, t, chi-squared, exponential — when each applies, key parameters, when to approximate one with another.
**Match patterns:** `distribution`, `Bernoulli`, `Poisson`, `binomial`, `normal`, `t-distribution`, `chi-squared`, `z-score`
**Example existing tags:** distributions (12), Bernoulli distribution (3), Poisson distribution (3), discrete distributions (4), z-scores (3), probability distributions (3), t-distribution (2)

#### `sampling & central limit theorem`
Sampling distributions, standard error vs std dev, CLT applicability and limits, Law of Large Numbers.
**Match patterns:** `sampling`, `central limit theorem`, `CLT`, `standard error`, `Law of Large Numbers`, `sample size`
**Example existing tags:** sampling distributions (6), standard error (6), central limit theorem (3), sample size (2)

#### `confidence intervals & estimation`
CI construction, interpretation pitfalls, bootstrap CIs, point vs interval estimates, MLE basics.
**Match patterns:** `confidence interval`, `parameter estimation`, `bootstrap`, `resampling`, `MLE`, `maximum likelihood`
**Example existing tags:** confidence intervals (6), parameter estimation (3), bootstrap (3), resampling (3)

#### `hypothesis testing`
Null/alternative framing, p-value interpretation, test selection (t-test, z-test, chi-squared, ANOVA), one-tailed vs two-tailed.
**Match patterns:** `hypothesis testing`, `p-value`, `null hypothesis`, `t-test`, `z-test`, `chi-squared test`, `ANOVA`
**Example existing tags:** hypothesis testing (18), ANOVA (4)

#### `errors & power`
Type I / Type II errors, statistical power, effect size, power-vs-sample-size tradeoffs.
**Match patterns:** `Type I`, `Type II`, `statistical power`, `effect size`, `power analysis`
**Example existing tags:** statistical power (7), Type I error (4), Type II error (3)

#### `multiple testing & correction`
Bonferroni, FDR, family-wise error rate, why running 20 tests changes interpretation.
**Match patterns:** `multiple comparisons`, `multiple testing`, `Bonferroni`, `FDR`
**Example existing tags:** multiple comparisons (4)

#### `bayesian inference`
Prior / likelihood / posterior, conjugate priors, Bayes factors, frequentist-vs-Bayesian framing.
**Match patterns:** `Bayesian`, `prior`, `posterior`, `Bayes factor`
**Example existing tags:** Bayesian inference (6), frequentist inference (3)

#### `correlation, regression & causality`
Pearson vs Spearman, regression R², bias-variance in regression, residual analysis, correlation-vs-causation framing, confounding, Simpson's paradox.
**Match patterns:** `correlation`, `regression`, `confounding`, `Simpson`, `causal inference`, `collider`, `selection bias`, `observational`, `odds ratio`
**Example existing tags:** regression (5), correlation (3), confounding variables (3), causal inference (3), collider bias (3), observational study (4), selection bias (4), odds ratio (3)

#### `experimental design (within stats)`
A/B testing setup, randomization, controls, blocking — the part of experimentation that lives in the Statistics curriculum (more advanced experimentation lives in the Experimentation track).
**Match patterns:** `experimental design`, `A/B testing` (when the question is about statistical design, not the platform-engineering of the experiment), `randomization`
**Example existing tags:** A/B testing (7), experimental design (2)

#### `variance decomposition & ANOVA`
Total / between / within variance, ANOVA mechanics, F-statistic interpretation.
**Match patterns:** `variance decomposition`, `ANOVA`, `F-statistic`
**Example existing tags:** variance decomposition (6)

#### `survival analysis & time-to-event`
Time-to-event modeling, hazard rates, censoring, Kaplan-Meier estimation — the duration-until-event reasoning surface (churn timing, failure analysis, retention curves).
**Match patterns:** `survival analysis`, `hazard rate`, `Kaplan-Meier`, `kaplan meier`, `time-to-event`, `censoring`
**Example existing tags:** survival analysis, time-to-event, censoring

### Statistics blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `statistics`, `stats` | a specific family |
| `numpy`, `scipy`, `pandas` | the family, not the library |
| `mean`, `median`, `mode` (alone) | `descriptive statistics` |
| `python` | irrelevant — this track has subtype; conceptual carries no library, numerical uses Python by definition |

---

## Data Engineering — concept families

**Modality:** Constructed reasoning. No execution. Question types: conceptual / scenario / debug. Response: MCQ.
**Reasoning archetype:** System-level reasoning about pipelines, semantics, recovery, cost, and operational excellence.
**Current tag inventory:** 41 unique tags / 276 occurrences — **already well-formed.** Top 20 tags cover ~95% of usage. This track's existing concept-family discipline is the model the others are catching up to.

### Family registry (light formalization of existing structure)

| Family | Match patterns | Notes |
|---|---|---|
| `ETL VS ELT` | `ETL`, `ELT` | When to load-then-transform vs transform-then-load |
| `IDEMPOTENCY` | `IDEMPOTEN`, `idempoten` | The non-negotiable property of any production pipeline |
| `BACKFILL DESIGN` | `BACKFILL` | Reprocessing history without breaking incrementality |
| `ORCHESTRATION` | `ORCHESTRATION`, `DAG-based scheduling` | Dependency graphs, retries, conditional triggers |
| `SCHEDULING & SLAS` | `SCHEDULING`, `SLA` | When jobs run, what happens when they miss |
| `SCHEMA EVOLUTION` | `SCHEMA EVOLUTION`, `BACKWARD COMPATIBILITY`, `SCHEMA REGISTRY` | Adding/removing/renaming columns without breaking consumers |
| `BATCH VS STREAMING` | `BATCH VS STREAMING`, `STREAMING ARCHITECTURE` | Choosing the right paradigm; lambda/kappa architecture |
| `WATERMARKING` | `WATERMARK` | Late-data handling in streaming |
| `DELIVERY SEMANTICS` | `DELIVERY SEMANTICS`, `at-least-once`, `at-most-once`, `exactly-once` | The 3-way tradeoff every DE owns |
| `PARTITIONING & PRUNING` | `PARTITIONING`, `PRUNING` | Lay out for the query pattern |
| `STORAGE LAYOUT & FILE FORMATS` | `STORAGE LAYOUT`, `FILE FORMAT`, `Parquet`, `ORC` | Columnar vs row, file size, compression |
| `STORAGE ARCHITECTURE` | `STORAGE ARCHITECTURE`, `data lake`, `lakehouse`, `warehouse` | The high-level choice |
| `CDC & INGESTION` | `CDC`, `INGESTION` | Change data capture mechanics |
| `DATA QUALITY` | `DATA QUALITY` | Validation, contracts, alerting |
| `DATA CONTRACT` | `DATA CONTRACT` | Producer/consumer schema agreements |
| `LINEAGE & OBSERVABILITY` | `LINEAGE`, `OBSERVABILITY` | Tracing data, detecting silent failures |
| `SCD OPERATIONS` | `SCD` | Slowly changing dimensions from the engineering side |
| `COST OPTIMIZATION` | `COST`, `CLOUD COST`, `WAREHOUSE COST`, `BIGQUERY COST`, `SNOWFLAKE COST` | The bill is the constraint |
| `INCIDENT RESPONSE` | `INCIDENT`, `PIPELINE RESILIENCE` | When something breaks at 3 AM |
| `BACKPRESSURE` | `BACKPRESSURE`, `KAFKA CONSUMER LAG` | When producers outpace consumers |
| `DATA GOVERNANCE` | `GOVERNANCE`, `GDPR`, `CRYPTO SHREDDING`, `IMMUTABLE STORAGE` | Compliance and policy |

### Data Engineering blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `Airflow`, `Dagster`, `Prefect` (alone) | `ORCHESTRATION` |
| `Kafka`, `Kinesis`, `Pulsar` (alone) | `BATCH VS STREAMING` or `BACKPRESSURE` |
| `S3`, `GCS`, `ADLS` (alone) | `STORAGE ARCHITECTURE` |
| `Snowflake`, `BigQuery`, `Redshift` (alone) | the family the question is about (cost, schema, etc.) |
| `Spark`, `Flink`, `Beam` (alone) | the family the question is about |

---

## Data Modeling — concept families

**Modality:** Constructed reasoning. No execution. Question types: conceptual / scenario / debug (debug mock-only only). Response: MCQ.
**Reasoning archetype:** Schema design under conflicting requirements, grain decisions, change-over-time tradeoffs.
**Current tag inventory:** 41 unique tags / 515 occurrences (post Phase 2: 5 orphan tags remediated, 96 mock-only questions added).

### Family registry

| Family | Match patterns | Notes |
|---|---|---|
| `DIMENSIONAL MODELING` | `DIMENSIONAL MODELING`, `star schema`, `snowflake schema` | Kimball-style; the dominant practical paradigm |
| `FACT TABLE DESIGN` | `FACT TABLE`, `fact type`, `transaction fact`, `accumulating snapshot`, `periodic snapshot` | What goes in a fact, what stays out |
| `DIMENSION DESIGN` | `DIMENSION DESIGN`, `conformed`, `degenerate`, `junk dimension`, `role-playing` | Dimensional patterns and anti-patterns |
| `GRAIN DEFINITION` | `GRAIN`, `grain alignment`, `grain mismatch` | The most-violated rule in real-world modeling |
| `SCD STRUCTURE` | `SCD`, `slowly changing`, `Type 1`, `Type 2`, `Type 3`, `Type 4`, `Type 6` | Change-over-time semantics |
| `SURROGATE VS NATURAL KEYS` | `SURROGATE`, `NATURAL KEY`, `key strategy` | When the source PK is the wrong PK for the warehouse |
| `NORMALIZATION` | `NORMALIZATION`, `1NF`, `2NF`, `3NF`, `BCNF` | When to denormalize away from these |
| `DENORMALIZATION TRADEOFF` | `DENORMALIZATION` | Performance vs integrity |
| `BRIDGE & MANY-TO-MANY` | `BRIDGE`, `MANY-TO-MANY`, `multi-valued dimension`, `weighting factor` | Resolving many-to-many in dimensional models |
| `SCHEMA FROM REQUIREMENTS` | `SCHEMA FROM REQUIREMENTS`, `requirements gathering` | The interview-realistic skill of inferring schema from a stakeholder brief |
| `REFERENTIAL INTEGRITY` | `REFERENTIAL INTEGRITY`, `foreign key`, `orphan`, `cascade` | Consistency rules and what enforces them |
| `AGGREGATE & SUMMARY DESIGN` | `AGGREGATE`, `SUMMARY DESIGN`, `pre-aggregation`, `cube` | Pre-built rollups for performance |
| `BI-TEMPORAL MODELING` | `BI-TEMPORAL`, `TRANSACTION TIME`, `VALID TIME`, `as-of` | Both "when was it true" and "when did we know it" |
| `DATA VAULT` | `DATA VAULT`, `hub`, `link`, `satellite` | The alternative paradigm; when it wins |
| `SEMANTIC LAYER & METRIC GOVERNANCE` | `SEMANTIC LAYER`, `METRIC GOVERNANCE`, `metric definition`, `single source of truth` | dbt metrics, LookML, Cube — the layer above SQL |
| `SCHEMA EVOLUTION` | `SCHEMA EVOLUTION` (DM-specific angle: model adaptation, not DE plumbing) | New attributes, new dimensions, deprecation |
| `WIDE VS NARROW` | `WIDE VS NARROW`, `OBT (one big table)` | Modern warehouse antipattern debate |
| `DBT MODELING` | `DBT MODELING`, `dbt` | Modern modeling workflow specifics |
| `CONFORMED DIMENSIONS` | `CONFORMED DIMENSION`, `master data` | Cross-system consistency |
| `HIERARCHIES & MULTI-PATH` | `HIERARCHIES`, `MULTI-VALUED`, `CROSS-HIERARCHY`, `MULTIPLE HIERARCHIES` | Org charts, product categorization with multiple parents |
| `ADDITIVE VS NON-ADDITIVE` | `ADDITIVE`, `NON-ADDITIVE`, `SEMI-ADDITIVE` | Which measures sum cleanly across which dimensions |
| `DOUBLE-COUNTING & FAN-OUT` | `DOUBLE-COUNTING`, `FAN-OUT`, `ROW MULTIPLICATION`, `FACT-TO-FACT JOIN` | The modeling failure mode that creates the SQL family of the same name |

### Data Modeling blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `dbt`, `Looker`, `Cube` (alone) | the modeling concept the tool implements |
| `primary key`, `foreign key` (alone) | `REFERENTIAL INTEGRITY` |

---

## ML Fundamentals — concept families

**Modality:** Constructed reasoning. No execution. Question types: conceptual / scenario / predict_output / debug. Response: MCQ.
**Reasoning archetype:** Diagnose model behavior, not write training code; recognise leakage and bias before they ship.
**Current tag inventory:** 30 unique tags / 488 occurrences — **already tight.** (ALGORITHMIC FAIRNESS family added BIAS/FAIRNESS Phase 2.5 2026-05-26; 7 new questions + retag Q83031. Prior count "210 occurrences" was stale pre-Phase-2; recount on full 243-question bank = 488.)

### Family registry

| Family | Match patterns | Notes |
|---|---|---|
| `BIAS-VARIANCE TRADEOFF` | `BIAS-VARIANCE`, `bias`, `variance` | The mental model that explains overfit / underfit |
| `OVERFITTING DIAGNOSIS` | `OVERFITTING`, `underfitting`, `training accuracy gap` | Recognising symptoms before chasing causes |
| `REGULARIZATION EFFECT` | `REGULARIZATION`, `L1`, `L2`, `dropout`, `early stopping` | Tools that trade bias for variance and vice versa |
| `CROSS-VALIDATION DESIGN` | `CROSS-VALIDATION`, `K-fold`, `stratified`, `time-series CV`, `nested CV` | How you split decides what you measure |
| `DATA SPLITTING STRATEGY` | `DATA SPLITTING`, `train/val/test`, `holdout`, `temporal split` | Beyond random 80/20 |
| `DATA LEAKAGE DETECTION` | `DATA LEAKAGE`, `LEAKAGE`, `target leakage`, `train-test contamination` | The single most expensive failure mode in industry ML |
| `CLASSIFICATION METRICS` | `CLASSIFICATION METRICS`, `precision`, `recall`, `F1`, `AUC`, `ROC`, `PR curve` | Picking the right metric for the business cost |
| `REGRESSION METRICS` | `REGRESSION METRICS`, `RMSE`, `MAE`, `MAPE`, `R²` | Same, for continuous targets |
| `CLASS IMBALANCE HANDLING` | `CLASS IMBALANCE`, `SMOTE`, `class weighting`, `resampling` | When 99% of labels are the boring class |
| `FEATURE SCALING NECESSITY` | `FEATURE SCALING`, `standardization`, `normalization` | When it matters (gradient methods, distance methods) and when it doesn't (trees) |
| `FEATURE SELECTION STRATEGY` | `FEATURE SELECTION`, `filter`, `wrapper`, `embedded` | Reducing dimensionality and noise |
| `FEATURE IMPORTANCE INTERPRETATION` | `FEATURE IMPORTANCE`, `permutation importance`, `SHAP` | What the feature ranking actually tells you |
| `DIMENSIONALITY REDUCTION` | `DIMENSIONALITY REDUCTION`, `PCA`, `t-SNE`, `UMAP` | Compressing feature space |
| `MISSING DATA STRATEGY` | `MISSING DATA`, `imputation`, `missingness as signal` | Choices that affect model behaviour |
| `ENSEMBLE STRATEGY` | `ENSEMBLE`, `bagging`, `boosting`, `stacking` | When combining helps; tradeoffs of each — note: `GRADIENT BOOSTING` tag resolves here (substring `BOOSTING`), not to BOOSTING MECHANICS; `BOOSTING MECHANICS` is registered FIRST in `concept_families.py` to prevent shadow |
| `BOOSTING MECHANICS` | `BOOSTING MECHANICS`, `XGBOOST`, `LIGHTGBM`, `CATBOOST` | The dominant tabular winner; registered before ENSEMBLE STRATEGY so `BOOSTING MECHANICS` tag routes here correctly; `GRADIENT BOOSTING` still falls to ENSEMBLE STRATEGY (none of these patterns match it) |
| `MODEL CALIBRATION` | `CALIBRATION`, `Platt scaling`, `isotonic regression`, `reliability diagram` | When probabilities matter, not just rankings |
| `SUPERVISED VS UNSUPERVISED` | `SUPERVISED`, `UNSUPERVISED`, `semi-supervised`, `self-supervised` | Problem-shape recognition |
| `CLUSTERING EVALUATION` | `CLUSTERING`, `silhouette`, `inertia`, `Davies-Bouldin` | Metrics without ground truth |
| `NEURAL NETWORK DESIGN` | `NEURAL NETWORK`, `architecture`, `depth vs width`, `activation` | Capacity, regularization, choice of layers |
| `GRADIENT DESCENT BEHAVIOR` | `GRADIENT DESCENT`, `SGD`, `Adam`, `learning rate`, `momentum` | When optimizer choice changes outcome |
| `GRADIENT PATHOLOGY` | `GRADIENT PATHOLOGY`, `vanishing gradient`, `exploding gradient`, `dead ReLU` | What goes wrong in deep nets |
| `LOSS FUNCTION SELECTION` | `LOSS FUNCTION`, `cross-entropy`, `MSE`, `Huber`, `focal loss` | Aligning the loss with the business cost |
| `HYPERPARAMETER SENSITIVITY` | `HYPERPARAMETER`, `tuning`, `grid search`, `random search`, `Bayesian optimization` | Which hyperparameters move metrics and which don't |
| `TRANSFER LEARNING STRATEGY` | `TRANSFER LEARNING`, `pretrained`, `fine-tuning`, `frozen layers` | Reusing learned representations |
| `MODEL MONITORING` | `MODEL MONITORING`, `drift`, `concept drift`, `data drift`, `feature drift` | Post-deployment health |
| `TRAINING-SERVING SKEW` | `TRAINING-SERVING SKEW`, `train-serve`, `feature parity` | Why models that pass eval still fail in prod |
| `DEPLOYMENT CONSTRAINTS` | `DEPLOYMENT`, `latency`, `memory`, `batch vs online`, `edge` | Production reality vs lab freedom |
| `INTERPRETABILITY TRADEOFF` | `INTERPRETABILITY`, `explainability`, `black box`, `glass box` | Linear / tree-based / opaque |
| `ALGORITHMIC FAIRNESS` | `ALGORITHMIC FAIRNESS`, `FAIRNESS`, `disparate impact`, `demographic parity`, `equalized odds`, `group fairness`, `fairness metric`, `fairness constraint` | The fairness lens: metric selection, disparate-impact diagnosis, group-conditional reading, threshold adjustment, fairness-constrained training, individual-vs-group frame. Added BIAS/FAIRNESS Phase 2.5 (2026-05-26). |

### ML Fundamentals blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `scikit-learn`, `sklearn`, `TensorFlow`, `PyTorch` | the concept the library is being used to teach |
| `GRADIENT BOOSTING` | use `BOOSTING MECHANICS` (routes to family directly), `XGBOOST`/`LIGHTGBM`/`CATBOOST` for tool-specific routing, or `ENSEMBLE STRATEGY` if the question is about general boosting trade-offs |
| mixed-case `XGBoost`, `LightGBM`, `CatBoost` | use UPPERCASE: `XGBOOST`, `LIGHTGBM`, `CATBOOST` (routes to BOOSTING MECHANICS) |
| `ALGORITHMIC BIAS` | use `ALGORITHMIC FAIRNESS` — `ALGORITHMIC BIAS` shadows to BIAS-VARIANCE TRADEOFF via its `BIAS` substring pattern |
| `BIAS DETECTION` | use `DISPARATE IMPACT` or `FAIRNESS METRIC` — `BIAS DETECTION` shadows to BIAS-VARIANCE TRADEOFF |
| `CALIBRATION BY GROUP`, `CALIBRATION WITHIN GROUPS` | co-tag `ALGORITHMIC FAIRNESS` + `MODEL CALIBRATION`; do not put "calibration by group" inside a tag string — it shadows to MODEL CALIBRATION only |
| `FAIR ML`, `FAIRML` | use `ALGORITHMIC FAIRNESS` — these strings do not match any registered pattern |

---

## Experimentation — concept families

**Modality:** Constructed reasoning. No execution. Question types: conceptual / scenario / predict_output / debug. Response: MCQ.
**Reasoning archetype:** Design experiments that survive contact with reality (network effects, novelty, SRM, biased traffic); interpret results with appropriate uncertainty.
**Current tag inventory:** 24 unique tags — **the tightest registry in the bank.** (Phase 2 expanded from 22 → 24: added SEQUENTIAL TESTING and METRIC SENSITIVITY.)

### Family registry

| Family | Match patterns | Notes |
|---|---|---|
| `EXPERIMENT DESIGN` | `EXPERIMENT DESIGN`, `experimental design`, `randomization`, `treatment assignment`, `blocking` | The shape of the test |
| `HYPOTHESIS FORMULATION` | `HYPOTHESIS FORMULATION`, `hypothesis`, `null`, `alternative` | What you're actually testing |
| `METRIC SELECTION` | `METRIC SELECTION`, `OEC`, `north star metric`, `guardrail metric`, `proxy metric` | What you measure decides what you ship |
| `A/B TEST MECHANICS` | `A/B TEST MECHANICS`, `treatment`, `control`, `randomization unit` | The mechanics any practitioner runs daily |
| `STATISTICAL SIGNIFICANCE` | `STATISTICAL SIGNIFICANCE`, `p-value`, `confidence level` | When the result is real |
| `STATISTICAL POWER` | `STATISTICAL POWER`, `MDE`, `minimum detectable effect`, `power calc` | How much signal you can detect at this sample size |
| `TYPE I AND TYPE II ERRORS` | `TYPE I`, `TYPE II`, `false positive`, `false negative` | The two failure modes |
| `EXPERIMENT DURATION` | `EXPERIMENT DURATION`, `sample size calc`, `peeking` | When to stop |
| `CONFIDENCE INTERVALS` | `CONFIDENCE INTERVAL`, `CI`, `bootstrap interval` | Interpreting effect size with uncertainty |
| `SAMPLE RATIO MISMATCH` | `SAMPLE RATIO MISMATCH`, `SRM`, `traffic imbalance` | The first thing you check before reading results |
| `VARIANCE REDUCTION` | `VARIANCE REDUCTION`, `CUPED`, `stratification`, `regression adjustment` | Squeezing power from the data you have |
| `NOVELTY EFFECTS` | `NOVELTY EFFECT`, `primacy effect`, `temporal effect` | Why short tests can mislead |
| `NETWORK EFFECTS` | `NETWORK EFFECT`, `interference`, `SUTVA violation`, `peer effect` | When subjects influence each other |
| `SEGMENTATION ANALYSIS` | `SEGMENTATION ANALYSIS`, `heterogeneous treatment effects`, `subgroup` | When the average hides the truth |
| `MULTIPLE TESTING` | `MULTIPLE TESTING`, `Bonferroni`, `FDR` | When you test many metrics simultaneously |
| `HOLDOUT GROUPS` | `HOLDOUT GROUPS`, `long-term holdout` | Measuring long-term effects |
| `SWITCHBACK EXPERIMENTS` | `SWITCHBACK`, `time-based randomization` | Marketplaces and other interference-heavy domains |
| `MULTI-ARMED BANDIT` | `MULTI-ARMED BANDIT`, `Thompson sampling`, `epsilon-greedy` | When exploration / exploitation matters |
| `BAYESIAN EXPERIMENTATION` | `BAYESIAN EXPERIMENTATION`, `Bayesian A/B`, `posterior probability of improvement` | The alternative inference frame |
| `QUASI-EXPERIMENTAL METHODS` | `QUASI-EXPERIMENTAL`, `diff-in-diff`, `regression discontinuity`, `synthetic control` | When you can't randomize |
| `CAUSAL INFERENCE` | `CAUSAL INFERENCE`, `instrumental variables`, `propensity scoring`, `potential outcomes` | The deeper layer underneath A/B |
| `SAMPLE SIZE BASICS` | `SAMPLE SIZE BASICS`, `power vs sample size` | Pre-test sizing fundamentals |
| `SEQUENTIAL TESTING` | `SEQUENTIAL TESTING`, `always-valid`, `mSPRT`, `group sequential`, `alpha spending`, `optional stopping`, `anytime-valid` | Continuous-monitoring methods that control Type I error without a fixed horizon — mSPRT, group sequential designs, alpha spending |
| `METRIC SENSITIVITY` | `METRIC SENSITIVITY`, `sensitive metric`, `low-sensitivity metric`, `metric granularity`, `metric definition tightness` | How the precision of a metric definition affects detectability — high-variance or coarsely-defined metrics that structurally limit power regardless of sample size |

### Experimentation blocklist

| Blocked tag | Canonical alternative |
|---|---|
| `t-test`, `z-test`, `chi-squared` (alone, in experimentation context) | the test selection family or the broader statistical-significance family |
| `Excel`, `Optimizely`, `Statsig` (alone) | the experimentation concept the tool implements |

---

## Validation rules (the discipline this taxonomy enforces)

The `validate_content.py` script (Phase 2 work item) must enforce:

1. **Every `concepts` tag resolves to exactly one registered family per track.** A tag matching no family **OR** matching a blocklist pattern crashes catalog load with a suggested canonical alternative.
2. **Family count per question: 2–4** (5 max for hard questions teaching multiple dependent patterns). Outside that range = warning.
3. **No duplicate families on a single question.** Two tags resolving to the same family is redundant — keep only the more specific tag.
4. **No mock-only-specific families in practice content.** If we add follow-up-only families later (e.g. families that only make sense in chain follow-ups), they must be tagged as `mock_only=true` in the registry.
5. **Chain `follow_up_dimension` must resolve to one of the 8 canonical dimensions.** Either a canonical `*_pivot` token or an accepted `_pivot`-less alias (normalised via `backend/follow_up_dimensions.py` `canonical_dimension()`); anything else is an ERROR in `validate_content.py`.
6. **Consecutive `follow_up_dimension` values within a chain must differ.** `validate_content.py` flags two of the same canonical dimension back-to-back (e.g. two `scale_pivot` in a row).
7. **Mock-only introduces no unseen concept families.** Every family a `mock_only: true` question (or chain) tests must already appear in the practice bank for that track at that difficulty or lower. Mock-only recombines learned reasoning under fresh framing; it never debuts a concept the curriculum skipped. (Differentiation is framing/realism/ambiguity, not concept novelty — see [`docs/content-authoring.md`](content-authoring.md#what-separates-practice-from-mock-only).)

These validators are the discipline. They are intentionally strict: the cost of catalog-load-crash on a bad tag is small (the author fixes it before commit); the cost of accumulated tag drift is large (we just paid it).

---

## Glossary cross-reference

- **Tag** — the free-form string an author writes in a question's `concepts` array
- **Family** — the canonical registered group (e.g. `GROUPED AGGREGATION`) that tags resolve to
- **Member tag** — an example tag listed in this doc as belonging to a family (informational, not exhaustive)
- **Match pattern** — the substring(s) the family resolver checks when an exact-match fails
- **Blocklist** — patterns that are forbidden as tags; usually mechanic/API names that obscure reasoning
- **Follow-up dimension** — one of the 7 universal chain pivots; orthogonal to concept families
