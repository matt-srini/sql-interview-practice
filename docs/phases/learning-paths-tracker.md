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

**Question-bank expansion is complete (2026-XX).** Coverage audit has been run end-to-end — see [`docs/phases/pattern-coverage-audit.md`](./pattern-coverage-audit.md) for the per-question pattern proposal, per-track pattern coverage matrices, and concept-family → pattern landings.

**Locked rules (B-series final):**
- **1:1 mapping.** Each practice question routes to exactly one pattern-path. No multi-membership.
- **Routing by objective.** Match on the question's *primary objective* (captured by its concept-family tag). Construct usage doesn't override objective.
- **Analytical wins.** When a question's tags span both an analytical pattern (e.g., `cohort-and-retention`) and a construct pattern (e.g., `window-functions`), the analytical pattern wins.
- **Mock-only excluded.** Pattern-paths contain *only* practice questions. Mock-only questions stay strictly out.
- **Easy → hard ordering** within each path's `questions[]`. Stable sort: difficulty → ID.
- **Mock + dashboard stay concept-family driven.** Pattern-paths are practice-only. No bridge ever (see §C).

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

### C. Concept-mastery loop wiring (front-end) — **DEFERRED INDEFINITELY (2026-XX)**

**Decision (2026-XX):** Pattern-paths and mock are an explicit *two-system* design. Patterns drive practice. Concept-families drive mock + dashboard diagnostics. They **do not loop into each other.** C1–C5 are kept below as the audit trail for what was considered and why it's not being pursued.

**What stays live (was always concept-family driven, doesn't depend on patterns):**
- Dashboard `weakest_concepts` → recommended path via `focus_concepts` (family-aware via `_path_for_concept` in `insights.py`). Shipped 2026-05.
- Mock `focus_concepts` filter (Elite only). Shipped.

**What's dropped (originally proposed, no longer planned):**
- **C1.** Resolve pattern↔concept-family axis mismatch in Mock — *not pursued.* Axes stay parallel by design.
- **C2.** MockHub `?focus=` URL deep-link parsing — *not pursued.*
- **C3.** "Benchmark with focused drill" CTA on path completion — *not pursued.*
- **C4.** "Drill in mock" CTA on dashboard weak-concept cards — *not pursued.*
- **C5.** Tier-gating UX for the dropped CTAs — *not applicable.*

If the loop ever becomes a product direction again, the items above are the starting list. Reopening requires a fresh product decision because the parallel-systems shape is now load-bearing across `§Paths` SoT, `pattern-coverage-audit.md`, and the active content authoring direction.

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

**F3. Patterns needing new paths (post-2026-XX orphan recruitment).**
After orphan recruitment, the following thin/empty patterns still have *no live path* declaring them. Each is a stage-2 decision: create a new path, merge into an existing pattern, or defer.

Orphan-count shown is recruitable practice questions (from Pass 2) — strong upside for a new path.

| Track | Pattern | Orphans available | Likely action |
|---|---|---:|---|
| sql | `top-n-and-ranking` | 3 | New path |
| sql | ~~`pivot-and-unpivot`~~ | ~~7~~ | ✅ **Done** (`pivot-and-conditional-aggregation.json` created 2026-XX) |
| python | `heap-and-priority` | 4 | New path |
| python | `string-and-text-processing` | 4 | New path |
| python | `streaming-and-online` | 3 | New path |
| python-data | ~~`data-cleaning`~~ | ~~18~~ | ✅ **Done** (`data-cleaning.json` created 2026-XX) |
| python-data | `top-n-and-ranking` | 7 | New path |
| python-data | `window-and-rolling` | 2 | Merge into time-series or new |
| pyspark | ~~`spark-joins-and-skew`~~ | ~~16~~ | ✅ **Done** (`spark-joins-and-skew.json` created 2026-XX) |
| pyspark | `pyspark-windowing` | 5 | New path |
| data-engineering | `streaming-vs-batch` | 6 | New path |
| data-engineering | `cost-and-format-optimization` | 19 | **New path (strong)** — see F1 caveat (vendor-heavy) |
| data-engineering | ~~`data-quality-and-incident-response`~~ | ~~7~~ | ✅ **Done** (`data-quality-and-incident-response.json` created 2026-XX) |
| data-modeling | `surrogate-keys` | 2 | Merge or new |
| data-modeling | `conformed-dimensions` | 1 | Defer (too thin) |
| data-modeling | `data-vault` | 4 | New path or defer |
| data-modeling | `aggregate-and-summary-design` | 4 | New path or defer |
| data-modeling | `hierarchies-and-multipath` | 3 | Merge or new |
| statistics | ~~`probability-and-combinatorics`~~ | ~~12~~ | ✅ **Done** (`probability-and-combinatorics.json` created 2026-XX) |
| statistics | `sampling-and-clt` | 1 | Defer |
| statistics | `errors-and-power` | 5 | New path |
| statistics | `variance-and-anova` | 3 | New path or defer |
| statistics | `bayesian-reasoning` | 5 | New path (was F2-blocked; now viable at 5) |
| statistics | `survival-analysis` | 3 | Defer |
| ml-fundamentals | ~~`feature-engineering`~~ | ~~13~~ | ✅ **Done** (`feature-engineering.json` created 2026-XX) |
| ml-fundamentals | ~~`class-imbalance`~~ | ~~6~~ | ✅ **Done** (`class-imbalance.json` created 2026-XX) |
| ml-fundamentals | `model-interpretability` | 2 | Defer or merge with algorithmic-fairness |
| ml-fundamentals | `unsupervised-methods` | 4 | New path |
| ml-fundamentals | `neural-networks-and-gradients` | 4 | New path |
| ml-fundamentals | `hyperparameter-tuning` | 6 | New path |
| ml-fundamentals | `algorithmic-fairness` | 3 | Merge with model-interpretability as "Responsible ML" |
| experimentation | ~~`behavioral-effects-and-interference`~~ | ~~5~~ | ✅ **Done** (`behavioral-effects-and-interference.json` created 2026-XX) |
| experimentation | `sequential-and-bandits` | 4 | New path or defer |
| experimentation | `experiment-platform-design` | 2 | Defer |

**Oversized paths flagged for stage-2 split** (>15 questions after recruitment):
- `groupby-and-joins` (python-data): 6 → 27 — split into `groupby` + `joins-and-merges` (2 separate paths)
- `pipeline-evolution` (data-engineering): 5 → 27 — split into `schema-evolution` + `delivery-semantics` + `backfill-design` (3 separate paths)
- `dimensional-modeling-deep-dive` (data-modeling): 6 → 28 — split into `scd` + `grain-definition` + `bridge-tables` (3 separate paths)
- `schema-design-basics` (data-modeling): 6 → 16 — borderline; split into `star-snowflake` + `fact-table-design`
- `stats-for-analysts` (statistics): 8 → 24 — split into `descriptive-stats` + `distributions`
- `experimental-design-inference` (statistics): 12 → 20 — split into `hypothesis-testing` + `confidence-intervals`
- `ml-model-evaluation` (ml-fundamentals): 10 → 19 — split into `cross-validation` + `metrics`

These splits are the natural completion of the 1:1 question→path migration (B5 in this tracker).

### G. Pre-existing content cleanups not directly path-related

**G1. ~60 question concept-tag-count failures** across Python / ML / Experimentation / Statistics / Pandas (`expected 2-5 concept tags, found 1`). Pre-existing — surfaced by the validator before the paths refactor crashed it. Owned by the per-track re-authoring effort, not this tracker.

---

## Open product questions (no owner yet)

1. **Does the `level` enum still earn its place once the DAG (`recommended_after[]`) is honored as the real ordering primitive?** The DAG already encodes prerequisite chains; level becomes a vibe-badge only. Worth revisiting after C/D land.

2. **Maximum path size — should there be one?** The 1:1 mapping (B-series) means paths grow with the catalog. A `joins` path could end up with 30+ questions. Is that fine (chunked by difficulty in the UI) or do we set a max and split patterns (`joins-basics` + `joins-advanced`) when they balloon?

3. **Should `pattern` on a question be required, or optional?** Required forces every question into the curriculum spine but rejects "general practice" questions that don't fit. Optional allows orphans. Current proposal: optional, with periodic audits flagging orphan counts per track.

4. **Path completion semantics for the loop.** Today path is "complete" when all its questions are solved (via path UI or directly from practice). For the loop's "you've mastered this — now benchmark" moment, is solved-via-practice enough, or do we want a "path completed flow" event (user actually walked through the path UI)? Affects how the C-series CTAs fire.

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
| 2026-06-08 | **SQL `aggregation-patterns` absorption — 11 of 22 orphans + 11 catalog-only by design.** Cluster analysis of the 22 SQL-aggregation orphans split cleanly: 11 "real aggregation" Qs (with `GROUPED AGGREGATION` tag) + 11 pure SELECT/WHERE Qs tag-routed to aggregation via the `PRE-AGGREGATION FILTERING` family-membership artifact. Applied: absorb the 11 real-agg orphans into `aggregation-patterns` 7→18 (added: 11006, 11007, 11022, 11023, 11028, 11032, 12017, 12018, 12034, 12055, 12123). The 11 SELECT/WHERE Qs (11001, 11002, 11003, 11013, 11015, 11016, 11018, 11019, 11020, 11027, 11030) deliberately left as catalog-only — a curatorial decision that the foundational SQL path should not open the platform with trivial filtering exercises, given SQL is the first track and aggregation-patterns is its first path. All 11 absorptions verified against validator rule 5 (concept tags align with path's focus_concepts). Zero question-content edits. SQL orphan count: 27 → 16. Validator + 19/19 tests pass. |
| 2026-06-08 | **Bucket A.live extended-range (16–20) absorption — 27 orphans into 4 paths.** Authorized expansion under the 16–20 exception policy. Absorbed: `python-data data-cleaning` 15→18 (+3: 33016, 33023, 33038), `statistics applied-stats` 8→18 (+10: 72011–72023, 73002–73027), `experimentation experiment-design-and-power` 10→18 (+8: 91008–91023, 92009–92027), `pyspark spark-memory-and-driver-executor` 6→12 (+6: 41032, 41034, 42010, 43002, 43013, 43046 — under 15, safe-green). All 27 orphans verified to pass validator rule 5 (concept tags align with target path's focus_concepts); zero question-content edits. Orphan totals shift: statistics 16→6, experimentation 22→14, python-data 5→2, pyspark 21→15. `scripts/absorb_bucket_a_extended.py` re-runnable + idempotent. Validator + 19/19 tests pass. |
| 2026-06-07 | **Spark split (6 sub-pattern paths) + 6 yellow absorptions + ceiling extended 15→20.** `spark-core-concepts` (monolithic, 44+ Qs) split into 6 focused paths: `spark-execution-model-and-dag` (foundational, 16 Qs), `spark-schema-and-type-handling` (intermediate, 11), `spark-memory-and-driver-executor` (intermediate, 6), `spark-io-and-file-formats` (intermediate, 5), `spark-fault-tolerance-and-recovery` (advanced, 5), `spark-collections-and-arrays` (intermediate, 5). Yellow-band paths absorbed into nearest healthy path: `distributions` → 18 Qs, `joins-and-filtering` → 17 Qs, `ml-advanced-methods` → 16 Qs, `pipeline-fundamentals` → 19 Qs, `scd` → 17 Qs, `spark-joins-and-skew` → 16 Qs. `cost-and-format-optimization` deliberately excluded from yellow absorption (pattern too distinct to merge cleanly). Path-length guardrail extended 4–15 → 4–20 (default cap stays 15; 16–20 requires explicit per-path approval captured in the commit message). **Path count: 77 → 82.** Validator + tests pass. |
