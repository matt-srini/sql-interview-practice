# Learning Paths Tracker

**Status:** active
**Owner:** product + platform
**Last updated:** 2026-05-23
**Canonical SoT for path semantics:** [`docs/content-authoring.md`](../content-authoring.md) §Paths

This is the single self-contained tracker for in-flight and deferred work on the learning-paths system. Delete this file once every item below is shipped or explicitly cancelled.

---

## What landed in the 2026-05 paths refactor

For context — work already shipped (commits `b31fdea` + `53a575d`):

- `patterns` introduced as a first-class concept distinct from concept-family. Per-track registry in `backend/path_patterns.py`.
- All 42 existing paths gained `patterns[]`. 4 new paths added for sparse tracks (DE Lineage & Observability, DM Wide Tables & OBT, ML Missing Data & Preprocessing Hygiene, Exp Subgroup Analysis & HTE).
- `dimensional-modeling-deep-dive` reverted to `intermediate`. `advanced-de-systems` renamed to `pipeline-evolution`.
- Path validator rewritten around 6 content-integrity rules; replaced the dead `exactly one intermediate per track` rule. New `tests/test_paths_quality.py` enforces the same rules at test time.
- `insights.py` concept→path matching is now family-aware (mirrors Mock's resolver).
- Every stale "path completion unlocks medium/hard" claim purged from docs. `docs/content-authoring.md §Paths` is the canonical SoT.

Path count: 42 → 46.

---

## Decisions captured (durable record, not work items)

These are choices made during the 2026-05 refactor or the 2026-05-23 design pass. Future sessions should treat them as locked unless explicitly re-opened.

**D-1. One authoring agent, not two.** Path authoring is rare enough that we extend `.github/agents/question-authoring.agent.md` with a path-applicability step (B7) rather than create a parallel `path-authoring.agent.md`. Easier to enforce mandatory invocation when there's one entry point for all content work.

**D-2. Auto-broadening was a Band-Aid.** Rule 5 of the new validator (every path question carries a tag in same family as one path focus_concept) surfaced 58 misalignments during the 2026-05 PR. Rather than block the PR on per-question re-tagging (which requires the question-authoring agent and is deferred per user direction), we broadened 22 paths' `focus_concepts[]` so existing questions matched. **The resulting `focus_concepts[]` on those 22 paths is noisier than honest** (some now have 7–11 entries; healthy is 2–5). Do not treat them as canonical. The real fix is the B3 1:1 mapping pass, which re-asks "what is this question's primary pattern?" and naturally cleans up which questions belong in which path.

Paths most affected by the Band-Aid (most-broadened focus_concepts):
- `variance-reduction-and-behavioral-effects` (+7) — also flagged for splitting in E1
- `experiment-design-and-power` (+3)
- `ml-model-evaluation` (+3)
- `causal-inference-and-advanced-experimentation` (+2)
- `dataframe-fundamentals` (+2)
- `experimentation-starter` (+2)
- `pipeline-fundamentals` (+2)
- `practical-data-python` (+2 — but with caveat E2)
- `spark-core-concepts` (+2)
- `window-functions-mastery` (+2)

**D-3. `level` field is purely cosmetic post-refactor.** No unlock effect, no pricing effect, no mock effect. It drives only:
- TrackHub sort order (`foundational → intermediate → advanced`)
- "Start here" pill on the singleton `foundational` path
- Schema.org `educationalLevel` metadata on path detail pages
- Concept→path recommendation tie-breaker (foundational wins when multiple paths cover the same concept)

This makes Open Question #1 (does `level` still earn its place once the DAG is honored?) a real conversation. The DAG could subsume tie-breaker + sort; the "Start here" pill needs *some* way to identify the entry point, but that could be a separate boolean.

**D-4. `tier` (`free` / `pro`) on paths is visibility-only.** Does NOT gate the questions inside (those follow practice unlock thresholds regardless of path tier). A pro path's questions are accessible to a free user who has unlocked them via threshold; they just don't see the path itself in the listing.

**D-5. Pattern slug naming convention.** Kebab-case, lowercase, ASCII-only. Multi-word patterns use hyphens (e.g., `window-functions`, `cohort-and-retention`, `missing-data-and-preprocessing-hygiene`). Slugs ≤ 40 chars. Registered in `backend/path_patterns.py`.

**D-6. Taxonomy validation status by track.** The path validator's rule 4 (every `focus_concept` resolves to a registered concept family in `concept_families.py`) only fires for tracks listed in `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py`. Currently: `{"sql", "python"}`. Other tracks get a presence-only check until their per-track concept-family registry is complete. **When a track joins the validated set, the path validator immediately enforces rule 4 strictly for it** — coordinate the registry completion + paths re-check in the same PR.

**D-7. Curriculum-spine signal: Data Engineering is the most under-served track.** Current 3 paths vs proposed 8 canonical patterns = 60%+ growth on top of just having been doubled in the 2026-05 PR. Likely indicates DE deserves prioritised content authoring (more practice questions to fill out the proposed patterns) before B3 mapping happens. Other notable gaps: Statistics (3→8, 167% growth) and ML Fundamentals (5→11, 120% growth). SQL/Python/Pandas/PySpark are closer to their canonical sets.

---

## Phase 2 — Remaining open work

The active items left. Everything else has shipped, is locked as deferred,
or is out of scope (see "Shipped / closed" section below for the audit trail).

### Content cleanups

- **E1.** Split `variance-reduction-and-behavioral-effects` (experimentation).
  Path declares many focus_concepts and tries to teach 2–3 distinct things.
  Candidates: keep `variance-reduction` as its own path; `behavioral-effects-and-interference`
  already exists; add `sequential-and-bandits` when catalog supports it (currently in Bucket B).
- **E2.** Re-frame `practical-data-python` focus_concepts. Path grew to 14 Qs
  via Bucket A Route 1 but the focus_concepts haven't been re-audited. Either
  register a "data-pipeline scripting" family in `concept_families.py` or
  refresh the path's framing/focus_concepts to match the current Q mix.

### New paths blocked on catalog growth (Bucket B)

11 thin patterns where the catalog doesn't yet support a path (under the
4-Q floor for new paths). Wait for catalog growth before path-ifying.
Tracked from the 2026-06-08 bucket-accounting work.

| Track | Pattern | Practice Qs available |
|---|---|---:|
| python | `streaming-and-online` | 3 |
| python-data | `window-and-rolling` | 2 |
| sql | `top-n-and-ranking` | 3 |
| data-modeling | `surrogate-keys` | 3 |
| data-modeling | `hierarchies-and-multipath` | 3 |
| data-modeling | `conformed-dimensions` | 1 |
| statistics | `variance-and-anova` | 3 |
| statistics | `survival-analysis` | 3 |
| ml-fundamentals | `algorithmic-fairness` | 3 |
| experimentation | `sequential-and-bandits` | 3 |
| experimentation | `experiment-platform-design` | 1 |

### Locked: deferred indefinitely

- **Concept-mastery loop wiring (front-end).** Pattern-paths and mock are
  an explicit two-system design. Practice runs on patterns; mock + dashboard
  run on concept-families. They do not loop into each other. Originally
  proposed bridges (C1–C5: mock axis-mismatch resolution, MockHub `?focus=`
  deep-link, "benchmark with focused drill" CTA, "drill in mock" CTA,
  tier-gating UX) are **not pursued**. Reopening requires a fresh product
  decision because the parallel-systems shape is now load-bearing across
  `§Paths` SoT, `pattern-coverage-audit.md`, and active content authoring.
  What stays live (always was concept-family driven): dashboard
  `weakest_concepts` → recommended path; mock `focus_concepts` filter (Elite).

### Catalog-only by design (locked exclusions)

These questions exist in the catalog but deliberately don't earn a path slot:

- **5 cost-and-format-optimization Qs** (51017, 51019, 51020, 53010, 53018):
  trimmed during F3 batch; vendor-heavy edge content not absorbed.
- **11 SQL SELECT/WHERE Qs** (11001, 11002, 11003, 11013, 11015, 11016,
  11018, 11019, 11020, 11027, 11030): tag-routed to aggregation via the
  PRE-AGGREGATION FILTERING family-membership artifact, but semantically
  pure filtering exercises. SQL is the first track and aggregation-patterns
  is its first path — the platform doesn't open with trivial filtering.
- **4 Bucket C orphans** with no canonical pattern fit: DE 52032 (GDPR
  crypto-shredding), DM 62026 (semantic layer governance), SQL 11004 +
  11024 (NULL handling trivia).

### Out of scope for this tracker

- **G1.** ~60 question concept-tag-count failures across Python / ML /
  Experimentation / Statistics / Pandas (`expected 2-5 concept tags, found 1`).
  Pre-existing — surfaced by the validator before the paths refactor crashed it.
  Owned by the per-track re-authoring effort, not this tracker.

### Open product questions

*(none currently — all four prior product questions have been resolved or
closed alongside §B, §C, §D, and the path-size policy.)*

---

## Shipped / closed (audit trail)

For reference. The above is the live work; the below is what's done.

| Original item | Status | Notes |
|---|---|---|
| **A1.** Rename `role`→`level` + `starter`→`foundational` | ✅ shipped | commit `b5b0394` — schema, validator, frontend, docs, tests |
| **B1.** Canonical pattern registry per track | ✅ shipped | `backend/path_patterns.py` |
| **B2.** Add `pattern` field to question schema | ❌ closed (superseded) | Validator rule 7 enforces 1:1 mapping via the path's `questions[]` array. Adding a `pattern` field on each Q would be a redundant second source of truth. Closed as not needed. |
| **B3.** Question-to-pattern mapping pass | ❌ closed (superseded) | Routing decisions made in-place during the 2026-06-08 bucketing/dedupe batches. Each Q's home is in exactly one path's `questions[]` array. |
| **B4.** Lean-path triage | ✅ shipped (implicit) | The Bucket B deferral list (11 thin patterns above) is the formal triage output. |
| **B5.** Auto-derive `path.questions[]` + collapse `patterns[]` to singular | ❌ closed (superseded) | Same reason as B2/B3. Manual `questions[]` arrays with validator rule 7 = same correctness guarantee, simpler model. |
| **B6.** Doc the strategy in §Paths | ✅ shipped | Rules 1–7 + path-size policy + primary-path-selection guidance all documented in `docs/content-authoring.md §Paths`. |
| **B7.** Update authoring agent | ✅ shipped | Path-applicability step (B7) added. |
| **D1.** TrackHub topological sort by `recommended_after[]` | ❌ closed (superseded) | `display_order` is our editorial ordering primitive and approximates the DAG in practice. Topo sort would produce the same result with extra complexity. |
| **D2.** "Prerequisite: complete X first" hint | ❌ closed (adds friction) | Paths aren't gated; user chose this path. With the 1:1 + solved-status-sync model, prereqs may be already complete via catalog solves — hint would fire spuriously. |
| **D3.** "Next recommended" CTA on completion | ❌ closed (low value) | Trivially computable from `display_order`, but `/learn` already shows what's next; users navigate fine. Auto-suggest read as paternalistic for a calm curation surface. |
| **D4.** Pattern badges on path cards | ❌ closed (redundant) | After the 1:1 rule, most paths have ONE pattern whose name duplicates the path title (e.g., "Joins & Filtering Mastery" + chip "joins"). |
| **C1–C5.** Concept-mastery loop wiring | ❌ deferred indefinitely | Two-system design — see Locked section above. |
| **E3.** Normalize focus_concept casing | ✅ shipped | Done in earlier 2026-XX batch. |
| **F1.** DE Cost & Performance Optimization path | ✅ shipped | `cost-and-format-optimization` (15 Qs). |
| **F2.** Statistics Bayesian Methods path | ✅ shipped | `bayesian-reasoning` (6 Qs). |
| **F3.** New paths from thin patterns | ✅ partial / mostly shipped | 14 of 25 originally-proposed F3 patterns shipped as paths; 11 remain in Bucket B (above) waiting on catalog. |
| **Oversized-path splits** (B5 tail) | ✅ shipped | `groupby-and-joins`, `pipeline-evolution`, `dimensional-modeling-deep-dive`, `schema-design-basics`, `stats-for-analysts`, `experimental-design-inference`, `ml-model-evaluation`, `spark-core-concepts` all split into focused per-pattern paths. |
| **display_order field + per-track ordering** | ✅ shipped 2026-06-08 | Every path has a 1-based `display_order` per `(topic, level)`; `scripts/apply_path_display_order.py` is the SoT. |
| **Re-leveling pass** | ✅ shipped 2026-06-08 | `joins-and-filtering` (SQL) → intermediate; `spark-joins-and-skew` → intermediate; `bayesian-reasoning` → advanced; etc. |
| **Path-size ceiling extension 15→20** | ✅ shipped 2026-06-07 | Default cap 15, extended ceiling 20 with explicit per-path approval. Validator enforces 4–20 hard range. |
| **Bucket A.live extended-range absorption** | ✅ shipped 2026-06-08 | 27 orphans into 4 paths (data-cleaning, applied-stats, experiment-design-and-power, spark-memory-and-driver-executor). |
| **SQL aggregation absorption** | ✅ shipped 2026-06-08 | 11 of 22 real-aggregation orphans absorbed; 11 SELECT/WHERE Qs deliberately kept catalog-only. |
| **Bucket A.live heavy (Route 1 + 1a)** | ✅ shipped 2026-06-08 | 4 new paths (greedy-and-scanning, list-transformations, spark-udfs-and-python-boundary, hypothesis-testing-and-ci) + 47 orphans routed across 9 existing paths. |
| **Rule 7: 1:1 question→path uniqueness** | ✅ shipped 2026-06-08 | `_validate_paths` rule 7 + `test_rule7_question_appears_in_at_most_one_path`. 15 pre-existing duplicates resolved in the same commit. |

---

## Coverage audit results (2026-XX)

Headline from [`pattern-coverage-audit.md`](./pattern-coverage-audit.md):

| Track | Practice Qs | Patterns | Healthy | Uneven | Thin | Empty | Unrouted |
|---|---:|---:|---:|---:|---:|---:|---:|
| sql | 118 | 14 | 3 | 5 | 4 | 2 | 2 |
| python | 79 | 9 | 3 | 2 | 4 | 0 | 0 |
| python-data | 92 | 9 | 5 | 3 | 0 | 1 | 0 |
| pyspark | 127 | 7 | 4 | 3 | 0 | 0 | 0 |
| data-engineering | 91 | 9 | 5 | 3 | 1 | 0 | 1 |
| data-modeling | 81 | 14 | 6 | 1 | 7 | 0 | 1 |
| statistics | 100 | 11 | 1 | 8 | 2 | 0 | 0 |
| ml-fundamentals | 100 | 15 | 5 | 4 | 6 | 0 | 0 |
| experimentation | 87 | 9 | 2 | 7 | 0 | 0 | 0 |
| **Total** | **875** | **97** | **34** | **36** | **24** | **3** | **4** |

Legend: **Healthy** = ≥5 Qs across easy/medium/hard. **Uneven** = ≥5 Qs but missing a difficulty band. **Thin** = 1–4 Qs (needs content). **Empty** = 0 Qs (needs initial content). **Unrouted** = practice question whose tags don't route to any pattern.

### Per-track gap punch list (patterns needing content)

**SQL — 2 empty + 4 thin:**
- 🔴 `grouping-extensions` (0 Qs) — no questions on ROLLUP/CUBE/GROUPING SETS exist; needs initial authoring + a `GROUPING EXTENSIONS` concept-family.
- 🔴 `date-and-time` (0 Qs) — TIME-SERIES BUCKETING family routes to period-over-period (analytical-wins). No questions on pure date arithmetic / date functions distinct from period analysis. Either drop the pattern *(deferred to user)* or author basic date-function content.
- 🟡 `subqueries` (4 Qs), `set-operations` (3), `ctes-and-recursion` (2), `cohort-and-retention` (2) — all need 3–5 more questions for healthy depth.

**Python-data — 1 empty:**
- 🔴 `customer-analytics` (0 Qs) — the existing path's questions route to `groupby` / `reshape-and-pivot` / `time-series-pandas` because no concept-family in the pandas registry maps to customer-analytics. Either author a `CUSTOMER ANALYTICS PIPELINE` family or accept the pattern doesn't survive the 1:1 model.

**Data Engineering — 1 thin:**
- 🟡 `streaming-vs-batch` (7 Qs, uneven — missing hard) — needs 2–3 hard architectural decision Qs.

**Data Modeling — 7 thin:**
- 🟡 `surrogate-keys` (5), `bridge-tables` (7), `referential-integrity` (8), `conformed-dimensions` (3), `data-vault` (4), `aggregate-and-summary-design` (7), `hierarchies-and-multipath` (3) — most are uneven on difficulty mix; need targeted hard-tier authoring.

**Statistics — 2 thin:**
- 🟡 `bayesian-reasoning` (6 Qs, uneven) and `survival-analysis` (3 Qs).

**ML Fundamentals — 6 thin:**
- 🟡 `supervised-unsupervised` (2), `unsupervised-methods` (8 — at threshold but uneven), `model-interpretability` (6 — uneven), `algorithmic-fairness` (3), `neural-networks-and-gradients` (11 — uneven), `production-and-monitoring` (11 — uneven). Several are at the threshold; needs hard-tier coverage.

**Pass 2 — rebalance recommendations (2026-XX):**
`scripts/audit_pattern_rebalance.py` walks the audit output and, for each thin/empty pattern, finds practice questions *currently routed elsewhere* that have a co-tag pointing to the thin pattern. These are "recruitable candidates" — the analytical-wins rule sent them to a high-coverage pattern, but a secondary tag suggests their primary objective might actually be the thin pattern. Pass 2 output is appended to [`pattern-coverage-audit.md`](./pattern-coverage-audit.md) §"Pass 2: Rebalance recommendations".

Upper-bound impact (if *every* candidate were honestly moved — reality will be lower):
- **~15 thin patterns** could shift to healthy potential with zero new authoring.
- **3 empty patterns + ~10 thin patterns with no candidates** stay genuinely under-covered and need new questions.

Notably recruitable:
- SQL `ctes-and-recursion`: 2 → up to 9 (7 candidates, mostly weak-attached `period-over-period` Qs with `CTE PIPELINE` tags)
- SQL `subqueries`: 4 → up to 10 (6 candidates)
- DM `normalization`: 4 → up to 12 (8 candidates)
- ML `regularization`: 4 → up to 12 (8 candidates)
- ML `cross-validation`: 4 → up to 10 (6 candidates)
- DE `backfill-design`: 3 → up to 9 (6 candidates)

The rebalance section is a *routing-refinement tool*, not an auto-reassignment script. Stage 2 review confirms per-question which moves are honest, then refines `scripts/audit_pattern_coverage.py::ROUTING` (typically by tightening the analytical-wins rule or adding more-specific family→pattern mappings).

**Patterns with no concept-family routing source** (registry gaps to consider):
- SQL: `grouping-extensions` (no family for ROLLUP/CUBE)
- SQL: `date-and-time` (TIME-SERIES BUCKETING is captured under period-over-period)
- python-data: `customer-analytics` (no analytics-pipeline family)

These are not bugs in the audit — they're real findings about where the registry and the proposed pattern set don't yet match. Decisions in stage 2 (do we author new families + questions, or drop these patterns?).

---

## Reference: canonical pattern proposals per track (2026-05-23 analysis)

Snapshot of the per-track pattern audit from the 2026-05-23 analysis. **Treat as a starting proposal, not a locked decision** — revisit during B3 (question→pattern mapping) when the expanded question bank reveals actual coverage. Each pattern is annotated:

- *exists* — already a path
- *split* — currently bundled inside an over-broad path; should be its own
- *new* — proposed gap-filler
- *deferred* — proposed but blocked on catalog depth

Tier annotations: `c` = construct (language toolkit), `a` = analytical (data-thinking), `arch` = architectural (system design).

### SQL — 14 patterns (today 9)

| Pattern | Tier | Status |
|---|---|---|
| `aggregation` | c | exists |
| `joins` | c | exists |
| `subqueries-and-exists` | c | exists |
| `set-operations` | c | split (from sql-advanced-patterns) |
| `window-functions` | c | exists |
| `ctes-and-recursion` | c | split (from sql-advanced-patterns) |
| `grouping-extensions` | c | split (from sql-advanced-patterns) |
| `string-and-text` | c | split (from sql-string-and-date) |
| `date-and-time` | c | split (from sql-string-and-date) |
| `top-n-and-ranking` | a | new |
| `pivot-and-unpivot` | a | new (verify catalog depth first) |
| `cohort-and-retention` | a | exists |
| `funnel-and-event-analysis` | a | exists |
| `period-over-period` | a | exists |

### Python — 9 patterns (today 6)

| Pattern | Tier | Status |
|---|---|---|
| `arrays-and-hashing` | c | exists |
| `sliding-window` | c | exists |
| `stacks-and-queues` | c | exists |
| `heap-and-priority` | c | new |
| `dynamic-programming` | c | exists |
| `graph-traversal` | c | exists |
| `streaming-and-online` | a | new |
| `string-and-text-processing` | c | new (split off from DP / data-pipelines) |
| `data-pipeline-scripting` | a | exists |

### Pandas (python-data) — 8 patterns (today 6)

| Pattern | Tier | Status |
|---|---|---|
| `dataframe-basics` | c | exists |
| `groupby` | c | exists |
| `joins-and-merges` | c | exists (rename) |
| `reshape-and-pivot` | c | exists |
| `time-series-pandas` | a | exists |
| `data-cleaning` | a | new |
| `window-and-rolling` | c | new (split from time-series) |
| `customer-analytics` | a | exists |

### PySpark — 6 patterns (today 5)

| Pattern | Tier | Status |
|---|---|---|
| `spark-basics` | c | exists |
| `spark-performance` | c | exists |
| `query-optimization` | c | exists |
| `streaming` | arch | exists |
| `delta-lake` | arch | exists |
| `spark-joins-and-skew` | c | new |

### Data Engineering — 8 patterns (today 3 after this PR)

| Pattern | Tier | Status |
|---|---|---|
| `etl-elt-fundamentals` | arch | exists (rename of pipeline-fundamentals split) |
| `orchestration-and-scheduling` | arch | new (split from pipeline-fundamentals) |
| `schema-evolution` | arch | split (from pipeline-evolution) |
| `delivery-semantics` | arch | split (from pipeline-evolution) |
| `backfill-design` | arch | split (from pipeline-evolution) |
| `data-lineage` | arch | exists (in lineage-and-observability) |
| `pipeline-observability` | arch | exists (in lineage-and-observability) |
| `streaming-vs-batch` | arch | new |
| `cost-and-format-optimization` | arch | deferred (F1 — vendor-heavy content; verify first) |

### Data Modeling — 10 patterns (today 5)

| Pattern | Tier | Status |
|---|---|---|
| `star-and-snowflake` | arch | exists |
| `fact-table-design` | arch | split (from schema-design-basics) |
| `grain-definition` | arch | split (from basics + deep-dive) |
| `surrogate-keys` | c | split (from schema-design-basics) |
| `scd` | arch | exists |
| `normalization` | arch | exists |
| `bridge-tables` | c | split (from dimensional-modeling-deep-dive) |
| `dbt-modeling` | arch | exists |
| `wide-tables-and-obt` | arch | exists (new path) |
| `conformed-dimensions` | arch | new (verify catalog depth first) |

### Statistics — 8 patterns (today 3) + 1 deferred

| Pattern | Tier | Status |
|---|---|---|
| `descriptive-stats` | c | split (from stats-for-analysts) |
| `probability-and-combinatorics` | c | new (split from distributions) |
| `distributions` | c | split (from stats-for-analysts) |
| `sampling-and-clt` | c | new |
| `hypothesis-testing` | c | exists |
| `confidence-intervals` | c | exists |
| `regression-analysis` | a | exists (rename of applied-stats) |
| `bias-and-confounding` | a | new |
| `bayesian-reasoning` | a | deferred (F2 — catalog too thin, 4 Qs) |

### ML Fundamentals — 11 patterns (today 5)

| Pattern | Tier | Status |
|---|---|---|
| `supervised-unsupervised-framing` | a | exists (in ml-starter) |
| `bias-variance` | a | exists (in ml-starter) |
| `cross-validation` | c | exists (in ml-model-evaluation) |
| `metrics` | c | exists (in ml-model-evaluation) |
| `regularization` | c | split (from ml-advanced-methods) |
| `ensembles` | c | split (from ml-advanced-methods) |
| `feature-engineering` | a | new |
| `class-imbalance` | a | new |
| `missing-data-and-preprocessing` | a | exists (new path) |
| `model-interpretability` | a | new |
| `production-and-monitoring` | arch | exists (rename of ml-production) |
| `unsupervised-methods` | c | new |

### Experimentation — 8 patterns (today 5)

| Pattern | Tier | Status |
|---|---|---|
| `ab-test-mechanics` | a | exists |
| `metric-selection` | a | exists |
| `power-and-sample-size` | a | exists |
| `variance-reduction` | a | split (from variance-reduction-and-behavioral-effects) |
| `behavioral-effects-and-interference` | a | new (split from variance-reduction-and-behavioral-effects) |
| `causal-inference` | a | exists |
| `subgroup-and-hte` | a | exists (new path) |
| `sequential-and-bandits` | a | new (split from variance-reduction-and-behavioral-effects) |
| `experiment-platform-design` | arch | new |

### Aggregate footprint (proposal)

| Track | Today | Proposed | Net |
|---|---|---|---|
| SQL | 9 | 14 | +5 |
| Python | 6 | 9 | +3 |
| Pandas | 5 | 8 | +3 |
| PySpark | 5 | 6 | +1 |
| Data Engineering | 3 | 8 | +5 |
| Data Modeling | 5 | 10 | +5 |
| Statistics | 3 | 8 | +5 |
| ML Fundamentals | 5 | 11 | +6 |
| Experimentation | 5 | 8 | +3 |
| **Total** | **46** | **82** | **+36** |

Most growth = honest splits of compound paths. New patterns filling genuine interview-relevant gaps: ~10. Deferred until catalog supports them: 2 (Bayesian, DE cost-and-format).

---

## Changelog

| Date | Note |
|---|---|
| 2026-05-23 | Initial tracker. Captures Phase 2 deferred items from the 2026-05 paths refactor. |
| 2026-05-23 | A1 rename scope finalised: `role` → `level`, `starter` → `foundational`. Other two values (`intermediate`, `advanced`) unchanged. |
| 2026-05-23 | Canonical pattern proposals per track (82 total proposed vs 46 today) saved into reference section. Triggered after question-bank expansion completes. |
| 2026-XX | Coverage audit complete. 97 patterns proposed across 9 tracks (up from 82 after family-inventory revealed additional gaps); 875 practice questions routed; 3 empty / 24 thin / 36 uneven / 34 healthy. Gap punch list documented per track. C-series (concept-mastery loop) deferred indefinitely — patterns and concept-families are explicit two-system parallel design. |
| 2026-XX | Pass 2 rebalance complete. `scripts/audit_pattern_rebalance.py` produced recruitable-candidate lists per thin pattern. Upper bound: ~15 patterns can shift thin → healthy via rebalance alone (no new authoring). 3 empty + ~10 thin patterns remain genuine authoring gaps. |
| 2026-XX | Routing fix (SQL only): introduced `ANALYTICAL_PRIORITY` in `audit_pattern_coverage.py`. When a question's tags hit multiple analytical patterns (e.g., SESSIONIZATION + COHORT RETENTION), priority order `cohort > funnel > top-n > period-over-period > pivot` breaks the tie. Fixes the q13015 case (was misrouted to funnel; now correctly cohort). No validator impact — audit script is separate from validator. |
| 2026-XX | **Audit model refactor: live paths are now authoritative.** `audit_pattern_coverage.py` reads live path JSONs first; pattern coverage = sum of each path's `questions[]` aggregated under the path's `patterns[0]` (slug-normalised to canonical via `NORMALIZE_PATTERN`). Tag-routing demoted to a secondary tool used only for: (a) suggesting which pattern an orphan question could join, (b) flagging divergences (questions in path X whose tags suggest Y). `pattern-coverage-audit.md` now has Divergences and Orphans sections per track. **Pass 2 rebalance** rewritten to recommend orphan + divergent candidates per thin pattern. Headline: ~35 thin/empty patterns can become healthy via orphan recruitment alone (catalog already has the content; just not yet in paths). |
| 2026-XX | **Orphan recruitment applied across all tracks.** `scripts/recruit_orphans.py` added 134 orphans into existing live paths whose `patterns[]` declares the orphan's tag-suggested pattern. Coverage shifts: data-modeling 31→65 in path; data-engineering 19→46; statistics 28→52; ml-fundamentals 40→55; python-data 29→50; python 29→35; experimentation 43→49; sql 58→59 (only ctes-and-recursion had a live target). Pattern classes: many thin patterns are now healthy or uneven. 34 thin/empty patterns were SKIPPED because no live path declares them — these are stage-2 new-path decisions (per the §F "Track-specific path additions" list, expanded below). Path-size guardrail in `test_paths_quality.py` widened to 4–30 (paths >15 are flagged for stage-2 splitting; tightens back once split). Focus_concepts auto-broadened on 2 paths (dimensional-modeling-deep-dive, pipeline-fundamentals) to satisfy validator rule 5 for recruited orphans. Validator + tests pass. |
| 2026-XX | **8 new paths created for high-orphan thin patterns** (zero new questions authored — all 96 Qs drawn from existing catalog orphans). Adds: `data-cleaning` (python-data, 18 Qs), `spark-joins-and-skew` (pyspark, 16), `feature-engineering` (ml-fundamentals, 13), `probability-and-combinatorics` (statistics, 12), `data-quality-and-incident-response` (DE, 7), `pivot-and-conditional-aggregation` (sql, 7), `class-imbalance` (ml-fundamentals, 6), `behavioral-effects-and-interference` (experimentation, 5). `backend/path_patterns.py` registered 8 new pattern slugs. **Path count: 46 → 54.** Coverage: in-path questions 433 → 529; healthy patterns 18 → 23; empty patterns 35 → 26 (the remaining 26 are mostly patterns deferred per F3 — thin with low orphan availability). Validator + tests pass. |
| 2026-XX | **Per-question divergent audit + actions across all tracks.** `scripts/divergent_audit.py` classified 133 divergents into 4 buckets (B1 leave / B2 use-case-framed move-if-dest-thin / B3 routing priority fix / B4 tag-gap add). Classifier uses a per-pattern title-keyword guard to demote ambiguous "no canonical tag" cases from B4 to B1 (cost asymmetry: false-B4 pollutes question tags; false-B1 leaves a benign audit divergence). Results: **B1=74** (left alone, mostly questions in advanced paths whose tags are construct-primary; divergence is honest); **B2=43** (1 moved to thin dest, 42 skipped because dest is healthy or has no live path); **B3=8** (resolved via additions to `ANALYTICAL_PRIORITY` for SQL, ML, and Experimentation tracks — no question changes); **B4=8** (3 effective tag additions: q21032 `LIST & COLLECTION TRANSFORMATION`, q81013 `SUPERVISED VS UNSUPERVISED`, q83020 `MODEL MONITORING`; 5 customer-analytics cases noop because no concept-family routes to that pattern — a known finding). Net divergent count 133 → 122. Validator + tests pass. |
| 2026-06-08 | **Trim near-duplicate Qs from 7 paths over 15; close §D entirely.** Reviewed all 12 paths >15 Qs for near-duplicate questions (title-token overlap + concept-tag overlap). Trimmed 10 Qs across 7 paths (all dropped Qs remain in catalog, solvable via /practice; just removed from curated walk): aggregation-patterns 18→15 (-12004, -11010, -11028); applied-stats 18→15 (-72038, -73007, -73018); experimentation-starter 17→15 (-91002, -91014 — easy duplicates of medium versions kept); joins-and-filtering 17→15 (-12012, -12020); distributions 18→17 (-73009); scd 17→16 (-61015); spark-joins-and-skew 18→17 (-42051). 5 paths kept as-is (no defensible drops): data-cleaning 18, pipeline-fundamentals 18, ml-advanced-methods 16, spark-execution-model-and-dag 16, experiment-design-and-power 20 (only 1 near-dupe, Type I/II pair pedagogically belongs together). Net: 4 paths land at 15 target, 3 paths closer to 15, 5 stay where they are. **§D (DAG-aware UX) closed entirely.** Critical re-review showed all 4 D-items either superseded by `display_order` (D1), would add friction (D2), low-value (D3), or redundant with path titles (D4). The 1:1 + solved-status-sync architecture + display_order ordering already deliver the goal: a calm curation lens over the catalog. Paths total 827 → 817 Qs in paths. Validator + 14/14 path-quality tests pass. Zero question-content edits. Tracker hygiene: closed §D, removed all 4 prior open product questions (all resolved). |
| 2026-06-08 | **Tracker hygiene pass.** Phase 2 section rewritten to show only actual open work (frontend D1–D4, content E1/E2, Bucket B catalog-growth-blocked patterns). Closed B-series as shipped or superseded by rule 7: B1 shipped (registry); B2/B3/B5 superseded (rule 7 enforces 1:1 via path's `questions[]` array — a `pattern` field on each Q would be redundant); B4 shipped implicitly (Bucket B = the formal triage output); B6/B7 shipped. Closed E3, F1, F2 as shipped. Moved completed items into a "Shipped / closed" audit-trail table. Closed 3 of 4 Open Product Questions (path-size policy resolved; pattern-field-on-Q closed with B; loop semantics closed with C). Net tracker size: 522 → 442 lines. No code or path changes — doc-only. |
| 2026-06-08 | **Rule 7 added — question→path uniqueness (1:1 model) now enforced.** 15 pre-existing duplicate questions (Qs in 2 paths) discovered when the user asked "is the 1:1 rule enforced?". Rule was never validator-enforced and slipped through across many earlier batches in this session. Added `_validate_paths` rule 7 (ERROR-level) and `test_rule7_question_appears_in_at_most_one_path`. Resolved the 15 duplicates by assigning each Q to its primary pattern path: kept 1 in `stacks-and-queues` (Q22002 Sliding Window Maximum — both-paths Q; tiebreaker preserved 4-Q floor), removed 1 each from `dataframe-fundamentals` (Q31002), `pipeline-fundamentals` (Q51009), `sliding-window-patterns` (Q22002), `ml-production` (Q82034); removed 3 from `normalization-and-referential-integrity` (61018, 61019, 62015 — all wide-vs-narrow tradeoff Qs); removed 4 from `dbt-and-modern-analytics-modeling` (62017, 62018, 63004, 63019 — all wide-table comparison Qs); removed 4 from `ml-starter` (81007, 81010, 81019, 81025 — preprocessing/CV/regularization Qs that belong in their specialized paths, not the foundational sampler). Net path size changes: 7 paths shrank by 1–4 Qs each, no path breached 4-Q floor. `docs/content-authoring.md §Paths` updated with rule 7 documentation. `scripts/dedupe_paths.py` re-runnable + idempotent. **Zero question-content edits.** Validator + 14/14 path-quality tests pass. |
| 2026-06-08 | **Bucket A.live heavy (Route 1 + sub-1a) — 4 new paths + 8 existing-path absorptions, 47 orphans routed.** Cluster analysis of the remaining 4 Bucket A.live heavy candidates (python data-pipeline-scripting, python arrays-and-hashing, pyspark spark-performance, experimentation ab-test-mechanics) revealed pervasive tag-family-membership artifacts — orphans tag-routed to a target path but semantically belonging elsewhere. Created 4 NEW lean paths to absorb the leakage cleanly: `greedy-and-scanning` (python intermediate, 5 Qs: 21008, 21038, 22027, 22043, 23001), `list-transformations` (python intermediate, 7 Qs: 21003, 21016, 21017, 21025, 21026, 21028, 21029), `spark-udfs-and-python-boundary` (pyspark intermediate, 5 Qs: 41019, 41035, 42022, 42033, 43041), `hypothesis-testing-and-ci` (experimentation intermediate, 5 Qs: 91003, 91009, 91016, 91025, 91029). Absorbed into existing paths (with cluster-routed redistribution): arrays-and-hashing 5→15 (+10), practical-data-python 6→14 (+8), sliding-window-patterns 10→11 (+22049 two-pointer), heap-and-priority 4→5 (+23023), spark-performance 6→13 (+7), spark-joins-and-skew 16→18 (+2 join spillover), spark-memory-and-driver-executor 12→13 (+42035), experimentation-starter 14→17 (+3 A/B mechanics), experiment-design-and-power 18→20 (+2 Type I/II errors). Focus_concepts broadened on 2 paths to align rule 5: `arrays-and-hashing` += INDEXED SEQUENCE REASONING, `spark-performance` += CACHING & PERSISTENCE, EXECUTION MODEL REASONING, SHUFFLE REASONING (canonical family names; pre-existing descriptive labels like "SHUFFLE BOUNDARY DETECTION" didn't resolve correctly). Registered 4 new pattern slugs in `backend/path_patterns.py`. Updated `scripts/apply_path_display_order.py` with new positions. Bucket A.live heavy is now CLEARED. **Path count: 82 → 86.** Orphan totals: python 35→8, pyspark 21→6, experimentation 14→4. All 13 path-quality tests + validator pass. Zero question-content edits. Done in worktree, merged to main. |
| 2026-06-08 | **SQL `aggregation-patterns` absorption — 11 of 22 orphans + 11 catalog-only by design.** Cluster analysis of the 22 SQL-aggregation orphans split cleanly: 11 "real aggregation" Qs (with `GROUPED AGGREGATION` tag) + 11 pure SELECT/WHERE Qs tag-routed to aggregation via the `PRE-AGGREGATION FILTERING` family-membership artifact. Applied: absorb the 11 real-agg orphans into `aggregation-patterns` 7→18 (added: 11006, 11007, 11022, 11023, 11028, 11032, 12017, 12018, 12034, 12055, 12123). The 11 SELECT/WHERE Qs (11001, 11002, 11003, 11013, 11015, 11016, 11018, 11019, 11020, 11027, 11030) deliberately left as catalog-only — a curatorial decision that the foundational SQL path should not open the platform with trivial filtering exercises, given SQL is the first track and aggregation-patterns is its first path. All 11 absorptions verified against validator rule 5 (concept tags align with path's focus_concepts). Zero question-content edits. SQL orphan count: 27 → 16. Validator + 19/19 tests pass. |
| 2026-06-08 | **Bucket A.live extended-range (16–20) absorption — 27 orphans into 4 paths.** Authorized expansion under the 16–20 exception policy. Absorbed: `python-data data-cleaning` 15→18 (+3: 33016, 33023, 33038), `statistics applied-stats` 8→18 (+10: 72011–72023, 73002–73027), `experimentation experiment-design-and-power` 10→18 (+8: 91008–91023, 92009–92027), `pyspark spark-memory-and-driver-executor` 6→12 (+6: 41032, 41034, 42010, 43002, 43013, 43046 — under 15, safe-green). All 27 orphans verified to pass validator rule 5 (concept tags align with target path's focus_concepts); zero question-content edits. Orphan totals shift: statistics 16→6, experimentation 22→14, python-data 5→2, pyspark 21→15. `scripts/absorb_bucket_a_extended.py` re-runnable + idempotent. Validator + 19/19 tests pass. |
| 2026-06-07 | **Spark split (6 sub-pattern paths) + 6 yellow absorptions + ceiling extended 15→20.** `spark-core-concepts` (monolithic, 44+ Qs) split into 6 focused paths: `spark-execution-model-and-dag` (foundational, 16 Qs), `spark-schema-and-type-handling` (intermediate, 11), `spark-memory-and-driver-executor` (intermediate, 6), `spark-io-and-file-formats` (intermediate, 5), `spark-fault-tolerance-and-recovery` (advanced, 5), `spark-collections-and-arrays` (intermediate, 5). Yellow-band paths absorbed into nearest healthy path: `distributions` → 18 Qs, `joins-and-filtering` → 17 Qs, `ml-advanced-methods` → 16 Qs, `pipeline-fundamentals` → 19 Qs, `scd` → 17 Qs, `spark-joins-and-skew` → 16 Qs. `cost-and-format-optimization` deliberately excluded from yellow absorption (pattern too distinct to merge cleanly). Path-length guardrail extended 4–15 → 4–20 (default cap stays 15; 16–20 requires explicit per-path approval captured in the commit message). **Path count: 77 → 82.** Validator + tests pass. |
