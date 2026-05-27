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

## Phase 2 — Open work, prioritised

### A. Schema and naming

**A1. Rename `path.role` → `path.level` and `starter` → `foundational`**
Two coupled renames:
- Field: `role` → `level`. `role` collides with the user-role concept ("Data Analyst", "Data Engineer") used on landing and north-star. `level` is ed-tech standard (Khan, Brilliant, Coursera) and describes the field honestly: where the path sits in the track's pattern arc.
- First-tier value: `starter` → `foundational`. `starter` is a noun outlier ("a starter for whom?") that quietly implies beginner-only. `foundational` is an adjective describing the *content layer* — useful even for experienced devs verifying their basics. Matches the canonical text in `docs/content-authoring.md §Paths` ("the foundational concept layer of the track").

Enum becomes `foundational / intermediate / advanced` — all adjectives, consistent grammar.

Scope:
- Rename field in all 46 path JSON files (`"role": "starter"` → `"level": "foundational"`; also `intermediate` and `advanced` updated to the new key name)
- `backend/scripts/validate_content.py::_validate_paths` — field name + error messages + singleton-foundational rule
- `backend/routers/insights.py`: `role_order` → `level_order`; `_build_concept_path_index` sort key
- `backend/routers/paths.py`: serialised field name in API responses
- `frontend/src/pages/TrackHubPage.js` (sort key + "Start here" pill renders against `level === 'foundational'`)
- `frontend/src/pages/LearningPath.js` (Schema.org `educationalLevel` mapping — map `foundational` → "Beginner" for the schema.org vocabulary, since that's their controlled vocabulary)
- `docs/content-authoring.md §Paths` (the SoT — update enum vocabulary + singleton rule wording)
- `docs/track-onboarding.md`, `docs/backend.md`, `CLAUDE.md` (cross-references)
- `tests/test_paths_quality.py` (assertions: `VALID_LEVELS = {"foundational", "intermediate", "advanced"}`; `test_rule2_exactly_one_foundational_per_track`)

API-contract note: this is a breaking change for any external consumer of `/api/paths`. We do not have external consumers — internal-only fields, one PR is fine. No migration needed beyond the in-repo rename.

### B. Curriculum spine + 1-question-1-path model

**Picked up after question-bank expansion completes.** Sequence: (1) expansion lands, (2) map every question to a pattern, (3) audit lean patterns and decide which need targeted authoring vs. registry removal.

**B1. Define canonical pattern registry per track**
Per-track canonical patterns proposed in the 2026-05-23 analysis (saved in this tracker — see "Canonical pattern set per track" notes below in the chat log; will move into `backend/path_patterns.py` at execution time). Each pattern becomes a path; each question maps to exactly one pattern.

**B2. Add `pattern` field to question schema**
Single-value optional field on each question. If set, must resolve to a registered pattern in the track's registry. If null, the question is catalog-only.

**B3. Question-to-pattern mapping pass (per track)**
**This is a real authoring exercise, not a sort.** The analytical-wins tie-breaker (a cohort question that uses window functions → goes in `cohort-and-retention`, not `window-functions`) requires human judgment on every question. A script can flag *candidates* per question by scanning concept tags, but the final pattern choice is an author call. Run per track as each track's expansion finishes.

**B4. Lean-path triage**
After B3, audit each pattern's question count and apply this triage:
- 0–2 questions → **drop the pattern** from the registry (don't ship a path that can't teach itself; reconsider when catalog grows)
- 3–4 questions → **keep the pattern**, tag `needs_content: true` in the registry, log the gap as a targeted authoring task in this tracker
- 5+ → **ship the path**

This protects against shipping a `Bayesian Methods`-style path with 4 questions just because the pattern is in the registry.

**B5. Auto-derive `path.questions[]` from question tags + collapse `patterns[]` to singular `pattern`**

Two coupled schema changes in this step:
- Path JSON's `patterns: [...]` array becomes singular `pattern: "..."` (one pattern per path; 1:1 model means multi-pattern paths no longer make sense — split them).
- Path JSON drops manual `questions[]`. Loader scans the track catalog for matching `pattern` and populates ordered by difficulty + ID. Validator enforces 1:1 (every question with `pattern == X` appears in exactly one path; the path for X).

Paths currently declaring multiple patterns will need splitting in B1's canonical-set decision:
- `groupby-and-joins` (python-data): `["groupby", "joins"]` → split into 2 paths.
- `sql-advanced-patterns` (sql): `["set-operations", "recursive-ctes", "grouping-extensions"]` → split into 3 paths (already in canonical proposal).
- `sql-string-and-date` (sql): `["string-functions", "date-functions"]` → split into 2 paths (already in canonical proposal).
- `pipeline-fundamentals` (data-engineering): `["etl-elt", "orchestration"]` → split into 2 paths (already in canonical proposal).
- `pipeline-evolution` (data-engineering): `["schema-evolution", "delivery-semantics", "backfill-design"]` → split into 3 paths (already in canonical proposal).
- `schema-design-basics` (data-modeling): `["star-snowflake", "fact-table-design", "scd"]` → split into 3 paths (already in canonical proposal).
- `dimensional-modeling-deep-dive` (data-modeling): `["scd", "bridge-tables", "grain-definition"]` → split (note: `scd` would now collide with schema-design-basics' `scd` after that split — resolve by treating SCD as a single pattern spanning easy → hard, not a depth-tier split). Likely outcome: `bridge-tables` + `grain-definition` become their own paths; SCD content from both current paths merges into one `scd` path.
- `ml-starter`, `ml-model-evaluation`, `ml-advanced-methods`, `ml-production` (ml-fundamentals): each declares 2+ patterns → all need splitting (already in canonical proposal).
- `stats-for-analysts` (statistics): `["descriptive-stats", "distributions"]` → split into 2 (already in canonical proposal).
- `experimentation-starter`, `experiment-design-and-power`, `variance-reduction-and-behavioral-effects` (experimentation): multi-pattern → split (already in canonical proposal).

**This collapse is the structural change**, not just B1. The canonical pattern set already anticipates the 1:1 outcome.

**B6. Doc the strategy in `docs/content-authoring.md §Paths`**
Add a "Pattern registry and 1:1 mapping" subsection covering the curriculum-spine framing, the analytical-wins tie-breaker, the lean-path triage thresholds, and the lifecycle (new question → choose pattern → goes in path).

**B7. Update `.github/agents/question-authoring.agent.md`**
Add a step: pick the question's primary pattern (or null) during authoring, with the selection rule.

### C. Concept-mastery loop wiring (front-end)

The product differentiator: Practice → Dashboard diagnoses weakness → recommend mastery PATH → after completion, mock drill on the same concept-family benchmarks the mastery. Loop.

**Blocker to resolve first:**

**C1. Resolve the pattern↔concept-family axis mismatch in Mock**
Mock filters by `focus_concepts` (concept families). Paths now declare `patterns` (practitioner skills). A "drill this path with a focused mock" CTA needs either (a) Mock to accept patterns as a filter, or (b) explicit pattern → concept-family translation, or (c) a `focus_patterns` field on paths that maps to the equivalent concept families. Pick one and design before any UI lands.

**Once C1 lands:**

**C2. MockHub URL deep-link parsing**
[`frontend/src/pages/MockHub.js`](../../frontend/src/pages/MockHub.js) — add `useSearchParams` extraction for `?focus=A,B&track=sql&mode=custom&difficulty=medium` alongside the existing `location.state.mockPreset` handler.

**C3. "Benchmark this with a focused drill" CTA on path completion**
[`frontend/src/pages/LearningPath.js:150-159`](../../frontend/src/pages/LearningPath.js#L150) — add a secondary CTA next to "What's next →" in the completion banner. Links to the deep-link URL built from the path's focus mapping (per C1).

**C4. "Drill in mock" CTA on dashboard weak-concept cards**
[`frontend/src/pages/ProgressDashboard.js:444-460`](../../frontend/src/pages/ProgressDashboard.js#L444) — secondary CTA beside the existing `Study: <path>` link.

**C5. Tier-gating UX**
`focus_concepts` is Elite-only on the backend. Options for non-Elite users:
- (A) Don't render CTA — clean, no upsell pressure
- (B) Render in muted style with "Elite" badge, click → `/pricing` — upsell at moment of highest intent
- (C) Render CTA, route to unfocused mock — confusing
Decision deferred — depends on C1 outcome.

### D. DAG-aware UX (`recommended_after[]` is currently backend-only)

**D1. TrackHub sorts paths by `recommended_after[]` topological order**
Replace the current role-based sort in [`frontend/src/pages/TrackHubPage.js:124`](../../frontend/src/pages/TrackHubPage.js#L124) with a topological sort over the prerequisite DAG.

**D2. "Prerequisite: complete X first" hint on path detail**
Render in [`frontend/src/pages/LearningPath.js`](../../frontend/src/pages/LearningPath.js) when the path has unsatisfied `recommended_after[]`. Soft hint, not a hard gate.

**D3. "Next recommended" CTA on path completion**
After completion, surface the first path whose `recommended_after[]` is now fully satisfied. Replaces the current generic "What's next →" with a DAG-aware target.

**D4. Pattern badges on path cards**
Show the path's `patterns[]` as chips on TrackHub + `/learn` cards so users can scan for the subject they want.

### E. Content cleanups exposed by the refactor

**E1. Split `variance-reduction-and-behavioral-effects` (Experimentation)**
The path now declares 11 focus_concepts after auto-broadening — it is doing too many things. Split into 2–3 narrower paths (variance-reduction, behavioral-effects-and-interference, sequential-and-bandits). Depends on B1 pattern audit.

**E2. Re-frame `practical-data-python` focus_concepts**
The path lost its domain-flavored focus_concepts (CSV / JSON / DATETIME / etc.) because Python's concept-family registry doesn't include them. Either register a "data-pipeline scripting" family or rethink the path's framing.

**E3. Normalise focus_concept casing across paths**
Some paths now mix UPPERCASE and lowercase tags after the auto-broadening pass (e.g., `experimental-design-inference` mixes `HYPOTHESIS TESTING` and `confidence intervals`). Cosmetic, not a validator issue. One pass to UPPERCASE everywhere.

### F. Track-specific path additions (audit-flagged but deferred)

**F1. Data Engineering: Cost & Performance Optimization path**
7 platform-specific questions exist (Snowflake auto-suspend, BigQuery partitioning, format selection for scan cost). Needs content review before path-ifying — many are vendor-specific and may belong in a different curriculum slot.

**F2. Statistics: Bayesian Methods path**
Blocked — would need ≥5 more Bayesian questions in the catalog before a dedicated path makes sense (currently only 4).

### G. Pre-existing content cleanups not directly path-related

**G1. ~60 question concept-tag-count failures** across Python / ML / Experimentation / Statistics / Pandas (`expected 2-5 concept tags, found 1`). Pre-existing — surfaced by the validator before the paths refactor crashed it. Owned by the per-track re-authoring effort, not this tracker.

---

## Open product questions (no owner yet)

1. **Does the `level` enum still earn its place once the DAG (`recommended_after[]`) is honored as the real ordering primitive?** The DAG already encodes prerequisite chains; level becomes a vibe-badge only. Worth revisiting after C/D land.

2. **Maximum path size — should there be one?** The 1:1 mapping (B-series) means paths grow with the catalog. A `joins` path could end up with 30+ questions. Is that fine (chunked by difficulty in the UI) or do we set a max and split patterns (`joins-basics` + `joins-advanced`) when they balloon?

3. **Should `pattern` on a question be required, or optional?** Required forces every question into the curriculum spine but rejects "general practice" questions that don't fit. Optional allows orphans. Current proposal: optional, with periodic audits flagging orphan counts per track.

4. **Path completion semantics for the loop.** Today path is "complete" when all its questions are solved (via path UI or directly from practice). For the loop's "you've mastered this — now benchmark" moment, is solved-via-practice enough, or do we want a "path completed flow" event (user actually walked through the path UI)? Affects how the C-series CTAs fire.

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
