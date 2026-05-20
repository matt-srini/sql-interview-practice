# Mock Modality Rollout Plan

Planning document for the practice and mock modality migration.

Status: execution started, Phase 0 audit complete, Phase 2 complete, Phase 3 complete, Phase 4 complete, Phase 5A complete, Phase 6 planned
Date: 2026-05-19
Owner: GPT-5.4 orchestrator
Implementers: parallel GPT Codex agents

## Execution Status

Completed artifacts:

- [docs/phases/mock-modality-phase-0-backend-audit.md](./phases/mock-modality-phase-0-backend-audit.md)
- [docs/phases/mock-modality-phase-0-frontend-audit.md](./phases/mock-modality-phase-0-frontend-audit.md)
- [docs/phases/mock-modality-phase-0-content-audit.md](./phases/mock-modality-phase-0-content-audit.md)
- [docs/phases/mock-modality-phase-0-review.md](./phases/mock-modality-phase-0-review.md)

Current state:

- Phase 0 is complete as a docs-and-audit foundation phase
- no product-code behavior changed in Phase 0
- Phase 1 PySpark-first practice uplift is complete: additive metadata exposure and frontend terminology cleanup landed
- Phase 2 is complete: reasoning-track payloads now expose stable `interaction_mode` metadata across Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and Statistics; frontend prompt copy keeps modality family separate from question type; ML Fundamentals and Experimentation hook audits are complete with recorded gaps
- Phase 3 is complete: reasoning-track catalog rows expose additive `type` metadata; practice surfaces show question-form badges in SidebarNav and QuestionPage chrome; SidebarNav supports question-form filtering for mixed-form catalogs; QuestionPage adds prompt-guidance and evidence-layout chrome for reasoning prompts; TrackHub previews mixed question forms in the header
- Phase 4 is in progress: mock backend now accepts a real `benchmark` mode with track-specific fixed shapes; Statistics benchmark enforces a `1 numerical + 2 conceptual` mix; reasoning-track benchmarks now use track-specific type targets instead of PySpark's global sampler; MockHub now defaults to benchmark, reframes short/custom sessions as drills, treats Mixed as drill-only, and separates benchmark analytics/history from drills; MockSession active and summary chrome now carry benchmark-vs-drill framing so the session experience matches the new setup model
- Phase 5A is complete: MockHub is now a two-column desktop lobby (1060px max-width, `1fr 292px` CSS grid) with a sticky right-rail session brief showing the active mode badge, track, difficulty, question count, time limit, access state, and the anchored start button; the left column owns hero, mode cards, benchmark blueprint / drill planner, and config pills; analytics and history remain below the lobby. MockHub hero now frames `/mock` explicitly as a benchmarks-and-drills surface, the role-filter track mapping is aligned with the canonical Data Engineer track set (`data-modeling` included), drill modes render a dedicated planner card with inline custom controls, first-run and partial-history states explain benchmark-versus-drill jobs explicitly, and MockSession summaries split benchmark-review CTAs from drill-follow-up CTAs via a prefilled handoff back into MockHub. The benchmark summary "Review benchmarks" CTA was renamed to "Back to Mock" and the share result text was upgraded to include score + percentage + baseline delta (Pro/Elite) + top 2 weak concept gaps + platform URL, with `navigator.share()` used when available and clipboard as a fallback. MockSession active sessions now enforce a strict one-submit-per-question model: a dedicated `submitted{}` state (never cleared by Run) acts as the lock; blank code or missing MCQ option returns 422 without consuming the slot (409 on a genuine re-submit); the submit button is disabled and re-labelled after any submit; **no feedback is rendered from submit** — the button state is the only mid-session signal; "Next question →" appears after any submit on non-last questions; the last-position question after submit shows a two-variant nudge: "All questions answered — end your session when ready." when every question is submitted, or "End your session when ready, or go back to answer remaining questions." when some are still unanswered. A `.mock-session-rule` left-bordered sidebar callout (below the session-context card) shows two lines: the first is track-aware ("run freely before you commit" for code tracks; "select carefully before you commit" for MCQ/mixed tracks); the second is always the navigation arrow hint. `submitted_at` is included in the `GET /api/mock/{id}` question rows so the lock is restored correctly after a page reload.
- repeatable frontend QA now covers free/pro/elite mock flows through Playwright, including plan-specific `/mock` surfaces, right/wrong submissions, elite debrief visibility, and the summary-to-hub drill handoff

## Objective

Reshape the platform around accurate assessment modalities instead of the current coarse split between code and non-code.

Target modality model:

- Executable problem-solving: SQL, Python, Pandas, numerical Statistics
- Code-adjacent reasoning: PySpark first, selected Data Engineering / ML Fundamentals later
- Constructed reasoning: Data Engineering, Data Modeling, ML Fundamentals, Experimentation, conceptual Statistics
- Hybrid: Statistics overall

This plan covers:

- practice-track interaction model cleanup, starting with PySpark
- mock redesign around benchmark sessions by modality
- schema, taxonomy, UI language, composition rules, and review workflow
- a multi-agent execution model where GPT-5.4 orchestrates and GPT Codex implements

It also explicitly integrates the content-governance work that must stay aligned with the modality migration:

- [docs/concept-hooks.md](./concept-hooks.md) is the canonical exhaustive concept list per track
- [docs/concept-expansion-plan.md](./concept-expansion-plan.md) is the historical gap-audit and question-authoring record
- landing-page role mappings in [frontend/src/pages/LandingPage.js](../frontend/src/pages/LandingPage.js) are the live product view of which tracks belong to each role

Governing specs for this rollout:

- [docs/specs/platform-north-star.md](./specs/platform-north-star.md)
- [docs/specs/practice-modality-spec.md](./specs/practice-modality-spec.md)
- [docs/specs/mock-benchmark-spec.md](./specs/mock-benchmark-spec.md)

## Content Scope Guardrails

This rollout does not assume a whole-bank rewrite.

Default rule:

- do not rewrite whole tracks
- do not rewrite questions just because modality labels change
- do targeted metadata cleanup first
- then targeted rewrites where the content is too thin for the new modality framing
- add new questions only where concept-hooks audit or mock-blueprint coverage genuinely requires them

Current content stance by track:

| Track | Whole rewrite? | New audit needed? | Targeted new content likely? | Targeted rewrites likely? |
|---|---|---|---|---|
| SQL | No | No | Low | Low |
| Python | No | No | Low | Low |
| Pandas | No | No | Low | Low |
| PySpark | No | No | Medium | High |
| Data Engineering | No | No | Medium | Medium |
| Data Modeling | No | No | Medium | Medium |
| Statistics | No | No | Medium | Low |
| ML Fundamentals | No | No | Medium-high | Medium |
| Experimentation | No | No | Medium-high | Medium |

Immediate unanswered content questions to be resolved in-phase:

- ML Fundamentals audit is complete with recorded gaps; future work is targeted authoring rather than further hook-definition
- Experimentation audit is complete with recorded gaps; future work is targeted authoring rather than further hook-definition
- mock-only advanced-topic hook coverage exists only for a subset of tracks and must be extended to all tracks for future automation use

## Operating Model

### Roles

#### GPT-5.4 orchestrator

Owns:

- phase planning and sequencing
- task decomposition into parallel workstreams
- assignment of implementation tasks to Codex agents
- review of every Codex output before merge
- validation strategy and release gates
- scope control so work stays inside the approved phase

Does not own:

- direct product-code implementation except for planning artifacts, prompts, and agent definitions

#### GPT Codex implementation agents

Own:

- concrete code and content changes inside their assigned lane
- local validation before handoff
- short implementation notes for orchestrator review

Do not own:

- cross-lane scope changes
- product decisions outside the approved phase
- final merge approval

### Parallelism Rules

Run Codex agents in parallel only when their file surfaces are separable.

Safe parallel lanes:

- backend schema / router / composition work
- frontend practice or mock UI work
- content metadata audit and retagging work
- docs updates once implementation surfaces stabilize

Do not run in parallel when:

- two agents need the same file set
- API shape is still moving
- frontend depends on unfinished backend response changes
- content taxonomy is not frozen for the phase

### Review Gates

No phase is complete until the orchestrator verifies:

- scope matches the phase brief
- implementation matches the modality model
- no drift into generic MCQ language where reasoning language is required
- docs and prompts stay synchronized with behavior
- focused validation passes

## Canonical Product Decisions

These are the governing decisions for all phases unless explicitly revised.

### Modality taxonomy

| Track | Canonical modality | Notes |
|---|---|---|
| SQL | Executable problem-solving | Keep fully executable |
| Python | Executable problem-solving | Keep fully executable |
| Pandas | Executable problem-solving | Keep fully executable |
| Statistics | Hybrid | Numerical is executable; conceptual is reasoning |
| PySpark | Code-adjacent reasoning | Must move beyond thin answer-picking |
| Data Engineering | Constructed reasoning, with some code-adjacent later | Do not force execution |
| Data Modeling | Constructed reasoning | Should not be turned into a coding track |
| ML Fundamentals | Constructed reasoning, with selected code-adjacent later | Prioritize diagnosis over recall |
| Experimentation | Constructed reasoning | Prioritize case analysis and interpretation |

### Mock principles

- Remove the idea of a 2-question benchmark mock
- Keep `Run` for executable tracks
- Make `Submit` final for every track
- Do not reveal correctness or solutions mid-session in benchmark mocks
- Compose benchmark mocks by track-specific blueprint, not by one universal question count
- Keep custom or configurable sessions out of the benchmark layer; treat them as drills

### Practice principles

- Stop describing all non-executable tracks as MCQ tracks
- Treat subtype and interaction mode as first-class metadata
- Use practice UX language that reflects reasoning depth: debug, predict, diagnose, design, interpret
- Start the uplift with PySpark because it has the highest leverage and clearest need

### Role alignment principles

The modality migration must respect the current landing-page role-to-track framing because that is how the product already signals interview preparation paths.

Live role mappings from [frontend/src/pages/LandingPage.js](../frontend/src/pages/LandingPage.js):

| Role | Tracks |
|---|---|
| Data Analyst | SQL, Statistics, Pandas, Python |
| Data Engineer | Python, SQL, PySpark, Data Engineering, Data Modeling |
| Analytics Engineer | SQL, Data Modeling, Pandas, Python |
| Data Scientist | ML Fundamentals, Statistics, Experimentation, Python, SQL |

Implications:

- PySpark uplift has outsized value for the Data Engineer role surface
- ML Fundamentals and Experimentation audit quality materially affects the Data Scientist role narrative
- Data Modeling interaction quality matters not only for standalone track quality, but also for Analytics Engineer and Data Engineer role credibility

## Phase Plan

## Phase 0: Taxonomy Freeze And Audit Foundation

Goal: freeze the modality model and add the metadata structure needed for clean rollout.

Deliverables:

- approved modality taxonomy for all tracks
- approved subtype vocabulary
- approved naming language for practice and mock surfaces
- new content metadata design for `interaction_mode`
- audit checklist for existing questions by track
- audit linkage between modality plan and concept-hooks coverage expectations
- role-impact note for each track using landing-page role mappings

Codex lanes:

1. Content lane
   - inventory current `type` usage across all reasoning-heavy tracks
   - propose mapping from existing `type` to canonical `interaction_mode`
   - flag ambiguous or weak question shapes
   - map each track's current bank against [docs/concept-hooks.md](./concept-hooks.md) status and [docs/concept-expansion-plan.md](./concept-expansion-plan.md)
   - identify which content work is metadata-only, rewrite-only, or net-new authoring

2. Backend lane
   - design minimal schema changes for content loaders and public payloads
   - identify where `type`, `eval_kind`, and public question serializers need extension

3. Frontend lane
   - inventory where practice and mock UI currently hardcodes MCQ-style language
   - identify places where subtype-aware rendering or labels are needed

Orchestrator review output:

- one frozen modality matrix
- one approved subtype vocabulary
- one implementation diff map for backend, frontend, and content
- one content-scope decision: no rewrite / targeted rewrite / net-new questions per track

Exit criteria:

- no unresolved taxonomy ambiguity for PySpark and Statistics
- all affected surfaces identified before execution starts
- ML Fundamentals and Experimentation are explicitly scheduled as unfinished concept-hook audits, not forgotten backlog
- advanced mock-only hook expansion is assigned to a later content phase rather than left implicit

## Phase 1: PySpark Practice Uplift

Goal: make PySpark the first code-adjacent reasoning track instead of a generic option-based track.

Product outcomes:

- PySpark practice is described as technical reasoning, not MCQ
- question metadata supports subtype-aware UX
- practice UI reflects debug / predict-output / optimization / scenario distinctions

Workstreams:

1. Backend Codex
   - expose `interaction_mode` and stable subtype metadata in public question payloads
   - keep existing evaluation flow working while widening metadata
   - add tests for payload shape and backward compatibility

2. Frontend Codex
   - update track labels and helper copy away from MCQ language
   - render subtype-specific instructions and affordances on question pages
   - make practice surfaces feel code-adjacent where appropriate

3. Content Codex
   - classify all PySpark questions by `interaction_mode`
   - normalize subtype values where needed
   - flag weak questions for later rewrite rather than silently rebranding them
   - validate that the PySpark bank still adequately covers the full hook set in [docs/concept-hooks.md](./concept-hooks.md)

Exit criteria:

- PySpark question payloads include stable modality metadata
- PySpark practice no longer reads as a generic quiz experience
- no regression to catalog, question detail, or submission flows

## Phase 2: Reasoning-Track Metadata Generalization

Goal: extend the PySpark model to Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and conceptual Statistics.

Status: complete 2026-05-19

Product outcomes:

- platform-wide modality language becomes accurate
- reasoning tracks can later power better mock composition and filtering

Workstreams:

1. Content Codex
   - classify all reasoning-track banks by `interaction_mode`
   - normalize subtype taxonomies within each track
   - surface rewrite candidates where current format is too shallow
   - explicitly separate already-audited tracks from still-unaudited tracks
   - finish concept-hooks audit for ML Fundamentals
   - finish concept-hooks audit for Experimentation

2. Backend Codex
   - generalize loader and serializer support across all non-executable tracks
   - preserve compatibility with existing clients while exposing richer metadata

3. Frontend Codex
   - update generic practice components to consume shared modality metadata
   - show track-appropriate instructions instead of one-size-fits-all copy

Exit criteria:

- all reasoning tracks have stable modality metadata
- Statistics cleanly supports both executable and reasoning subtypes
- no track is mislabeled as plain MCQ in user-facing practice surfaces
- ML Fundamentals and Experimentation hook coverage is audited against the current bank with outcomes recorded

## Phase 3: Practice UX By Interaction Type

Goal: make practice mode visibly smarter, not just better tagged.

Status: complete 2026-05-19 — question-form badges, SidebarNav question-form filters, QuestionPage prompt-guidance/evidence chrome, and TrackHub question-form previews landed.

Product outcomes:

- question pages adapt to interaction type
- users understand whether they are solving, debugging, predicting, or reasoning
- track hubs and filters can later expose these distinctions cleanly

Candidate work:

- subtype-specific headers, hints, and submission framing
- improved layout for code-adjacent questions
- improved copy and badges in catalog and question chrome
- optional filters by interaction type where it materially helps discovery

Parallel Codex lanes:

1. Frontend UX lane
2. Backend payload / API support lane
3. Docs lane once UI behavior is stable

Exit criteria:

- practice interaction model is legible without reading docs
- no regressions for executable tracks

## Phase 4: Mock Benchmark Redesign

Goal: rebuild mock around benchmark sessions by modality, not the old quick/full/custom pattern.

Product outcomes:

- benchmark mock is fixed-shape and serious
- no 2-question benchmark mode
- track-specific blueprints replace one universal count model

Proposed benchmark blueprints:

| Track | Benchmark shape | Target duration |
|---|---|---|
| SQL | 3 executable problems | 60 min |
| Python | 2 executable problems | 50 min |
| Pandas | 2 executable problems | 50 min |
| Statistics | 1 numerical + 2 conceptual | 45 min |
| PySpark | 5-6 code-adjacent reasoning questions | 40 min |
| Data Engineering | 5-6 constructed reasoning questions | 40 min |
| Data Modeling | 4-5 constructed reasoning questions | 40 min |
| ML Fundamentals | 5-6 constructed reasoning questions | 40 min |
| Experimentation | 5-6 constructed reasoning questions | 40 min |

Execution rules:

- `Run` only on executable questions
- final `Submit` only once per question
- no correctness reveal mid-session
- no solution reveal mid-session
- finish response returns full review material

Parallel Codex lanes:

1. Backend mock composition and session rules
2. Frontend mock hub and session UX
3. Content blueprint mapping for each track
4. Content coverage check against benchmark blueprint so each benchmark uses genuinely representative interaction types

Exit criteria:

- benchmark mock no longer depends on quick/full/custom framing
- session composition is track-aware and modality-aware
- benchmark results are comparable within track and blueprint
- no benchmark blueprint depends on content that does not yet exist or is known to be weak

## Phase 5: Drill Mode Split

Goal: preserve flexibility without corrupting benchmark mock quality.

Product outcomes:

- benchmark mock stays fixed and comparable
- flexible custom sessions move into a distinct drill surface

Drill capabilities:

- concept targeting
- configurable counts and durations
- optionally coached behavior if desired later
- excluded from benchmark analytics

Exit criteria:

- user can distinguish benchmark from drill instantly
- analytics remain clean

### Phase 5A: MockHub Premium Lobby Layout Plan

This is a MockHub-specific layout upgrade, not a product-wide visual rewrite.

Assessment:

- the current MockHub is structurally improved, but it still reads more like a setup form than a premium interview lobby because setup controls, planner copy, analytics, and history still compete at roughly the same visual weight
- the core issue is hierarchy and composition, not the existing theme tokens; the page is too narrow and too vertically stacked for the importance of the mock surface
- Practice should remain the only full workspace surface in the product; its wide shell is appropriate because users are actively working there
- Dashboard should remain report-like and centered rather than being widened to match MockHub
- Account should remain narrow and transactional rather than being promoted into a high-density product workspace

Preserve:

- shared Topbar and overall page framing so Mock still feels like the same product as Practice, Dashboard, and Account
- Practice as the full-width, full-attention working surface
- Dashboard as a structured coaching/report page
- Account as a compact control-center page
- the benchmark-vs-drill product model already landed in Phases 4 and 5

Do not do:

- do not turn MockHub into another AppShell-style workspace
- do not widen Dashboard or Account just to create superficial cross-page consistency
- do not chase “premium” through decorative effects alone; stronger hierarchy matters more than extra gloss
- do not replace every simple pill control with a bespoke visual component unless it improves clarity or state communication

Planned layout outcomes:

- MockHub becomes a two-column desktop lobby with a wider max width than today
- the left side owns configuration and session-type selection
- the right rail becomes a sticky session brief with the active mode, track, difficulty, timing, question count, access state, and the anchored start action
- benchmark becomes the primary hero path rather than one visually peer-level card among three
- drills remain clearly secondary, but still intentional and premium rather than “fallback” options
- lower-page analytics and history shift from utility tables toward a more artifact-like session dashboard

Recommended implementation order:

1. Layout-only widening and two-column lobby composition
2. Benchmark hero redesign that folds the blueprint into the featured benchmark surface
3. Richer track and difficulty controls with clearer access-state communication
4. History and analytics redesign into stronger benchmark-vs-drill artifacts
5. Elite feature previews that feel aspirational instead of purely disabled or teaser text
6. Responsive regression pass to ensure mobile remains calm and readable

Execution brief for another model:

- treat Phase 5A as a frontend-only MockHub redesign unless a later artifact surface proves that a required field is genuinely missing from an existing response
- prefer one reviewable slice at a time; do not try to land all six implementation-order items in one pass
- preserve the benchmark-vs-drill product contract already shipped in Phases 4 and 5; this phase is about hierarchy, framing, and layout quality rather than re-litigating the product model

First implementation slice: required scope

- widen MockHub from the current narrow single-column composition into a two-column desktop lobby
- keep the existing shared Topbar and overall page entry framing
- move active setup controls into the left primary column
- add a sticky right rail that always shows the current session brief and the primary start action on desktop
- keep the current benchmark default, drill planner, recommendation banner, analytics panel, and split benchmark/drill history content, but reorganize them into the new hierarchy rather than redesigning their underlying logic
- do not change backend contracts in the first slice
- do not redesign MockSession, Dashboard, Account, or Practice as part of this slice

First implementation slice: explicit non-goals

- no new mock modes
- no entitlement-rule changes
- no analytics calculation changes
- no new debrief logic
- no AppShell migration for MockHub
- no visual-token rewrite across the rest of the product

Desktop layout contract for the first slice

- desktop breakpoint should present a true two-column lobby rather than a wide single column with inline cards
- left column is the primary reading and interaction lane; it owns hero framing, mode choice, benchmark hero or drill planner, and track/difficulty controls
- right rail is narrower, sticky, and decision-oriented; it owns the condensed session brief, access state, and the anchored primary start CTA
- analytics and history stay below the top lobby band rather than competing with setup controls above the fold
- benchmark should read as the primary serious path when active; drill options should still feel intentional, but visually secondary
- the user should be able to understand the currently selected session type, track, difficulty, and start readiness without scanning the entire page

Tablet and mobile contract for the first slice

- tablet may collapse to a single column if the two-column layout becomes cramped, but the session brief must remain visually close to the primary setup controls
- mobile must remain single-column, calm, and readable
- sticky behavior may be reduced or disabled on smaller screens if it harms usability
- no desktop-only dependency should make the start CTA or access state hard to find on touch devices

Section placement contract

- top of page: benchmarks-and-drills hero and any recommendation banner
- primary setup lane: mode selection, then benchmark hero when `mode='benchmark'` or drill planner when `mode!='benchmark'`, then track/difficulty controls
- decision rail: sticky session brief with session type, track, difficulty, timing, question count, access state, and start CTA
- lower page: benchmark analytics first, then benchmark history and drill history artifacts
- first-run and partial-history guidance should stay near history, not inside the primary setup lane

Acceptance criteria for the first slice

- on desktop, MockHub is visibly two-column and no longer reads as a vertically stacked setup form
- the primary start CTA is visible in the right rail without requiring the user to scan past analytics or history
- benchmark mode is visually dominant when selected and no longer appears as one peer-level card among equal alternatives
- drill setup remains fully functional and clearly distinct from benchmark setup
- analytics and history do not compete with setup for top-of-page attention
- the existing recommendation preset flow from MockSession summary still works unchanged
- mixed remains drill-only and the current benchmark/drill behavior rules are unchanged
- mobile and narrow-tablet layouts remain readable with no broken sticky behavior or inaccessible CTA state

Validation requirements for the first slice

- update focused frontend tests for any DOM or copy expectations affected by the MockHub restructuring
- run the existing MockHub unit coverage and the repeatable mock Playwright flow before calling the slice done
- run a frontend production build after the layout changes
- manually verify one benchmark path and one drill path in the browser at desktop width and mobile width

Suggested implementation prompt for the implementing model

- "Implement only the first Phase 5A slice from docs/mock-modality-rollout-plan.md: convert MockHub into a two-column desktop lobby with a sticky right-rail session brief while preserving current benchmark/drill behavior, recommendation presets, analytics logic, and history logic. Do not touch backend contracts or other pages. Update focused tests, run the mock Playwright flow, and run a frontend build."

Phase 5A scope guard:

- this layout plan belongs to MockHub only
- MockSession can inherit follow-up language and action cues from MockHub, but not the full layout treatment
- no backend contract changes are required for the layout work itself unless a later artifact surface reveals a genuine missing field

## Phase 6: Analytics, Debrief, And Entitlement Cleanup

Goal: make mock analytics and coaching modality-aware and tier-coherent.

Product outcomes:

- benchmark analytics compare only like with like, so a user can trust benchmark numbers as a real baseline for that track
- drill analytics remain visible as drills, not blended into benchmark calibration metrics
- reasoning-track debriefs speak in diagnosis / interpretation / prioritization language instead of coding language
- coding-track debriefs speak in execution / debugging / approach language instead of generic coaching copy
- Pro is the serious benchmark tier with credible baseline feedback but without Elite-only coaching intelligence
- Elite is the intelligent coaching tier with cross-session concept signals and richer next-step guidance

### What is already done — do not re-implement

Before starting any Phase 6 work, confirm these invariants are already satisfied in the current codebase:

- `_compute_mock_analytics()` in `backend/routers/mock.py` already produces separated `benchmark_summary` and `drill_summary` objects and an explicit `mode_breakdown` count
- Mixed-track sessions cannot be benchmarks — enforced server-side in `POST /api/mock/start`; they naturally fall into drill aggregates with no code change needed
- `MockHub.js` already pulls the analytics panel exclusively from `benchmarkAnalytics` (the `benchmark_summary` field); drills are shown only in the secondary card
- The `comparisonCopy` comparison line in `MockSession.js` summary is already gated to `isProOrElite` and uses the user's own historical accuracy — this is truthful for both tiers and requires no change

Do not re-implement or refactor any of the above.

### What this phase must actually change

**Gap 1 — Debrief language is modality-blind (backend, highest priority)**

`build_session_debrief()` in `backend/routers/insights.py` uses identical language for every track. The specific broken patterns:

- Pattern copy `"Try articulating the approach before writing code next time."` is code-centric and fires on every track including Data Engineering, Experimentation, and Data Modeling where no code is written.
- Priority action fallback `"filter by that concept tag and aim for 3 consecutive correct answers"` implies code drilling and is wrong for reasoning tracks.

Fix: add a track-family classifier inside `build_session_debrief()` and branch pattern and priority-action copy on it. Do not change the headline logic — score-band headlines ("Solid session", "Tough session") are generic and correct for all tracks.

Track family definitions for the debrief (these are the canonical buckets — use them verbatim):

| Track family | Tracks |
|---|---|
| `executable` | sql, python, python-data |
| `reasoning` | pyspark, data-engineering, data-modeling, ml-fundamentals, experimentation |
| `statistics` | statistics (special-cased — see Statistics hybrid rule below) |

Concrete language replacements:

| Location in debrief | Executable copy | Reasoning copy |
|---|---|---|
| Inconsistent concept pattern | "Try articulating the approach before writing code next time." | "Try walking through the tradeoffs out loud before committing to your answer." |
| Priority action fallback (no path match) | "filter by that concept tag and aim for 3 consecutive correct answers" | "focus on being able to state the tradeoffs and reasoning clearly without backtracking" |
| Priority action (no weak concepts) — medium | "You're handling this difficulty well. Try a hard session to push your ceiling." | "You're reasoning through this difficulty well. Try a hard session to push your ceiling." |
| Priority action (no weak concepts) — hard | "Excellent — consistent hard-session performance is what separates interview-ready candidates. Keep the cadence up." | "Excellent — consistent performance on hard reasoning questions is what separates interview-ready candidates. Keep the cadence up." |
| Priority action (no weak concepts) — easy | "Good warmup. Move to a medium or hard session for a more realistic challenge." | "Good warmup. Move to a medium or hard session for a more realistic challenge." *(same — this one is fine)* |

Statistics hybrid rule: check the actual subtype mix of `enriched_questions` in the session.

- if the session has at least one `numerical` question → treat as `executable` for debrief language purposes (code was written)
- if every question is `conceptual` → treat as `reasoning`
- the standard Statistics benchmark is 1 numerical + 2 conceptual, so it will always resolve to `executable` family

**Gap 2 — Cross-track analytics shown as a single aggregate number (frontend)**

The Elite analytics panel in `MockHub.js` shows `benchmarkAnalytics.avg_score_pct` as a single "Avg benchmark score" number. This violates the analytics invariant "benchmark comparisons are track-specific, never cross-track" — if a user ran SQL and Experimentation benchmarks, the average is meaningless as a baseline for either.

Fix: expose the `track_breakdown` field that `GET /api/mock/analytics` already returns. Below the aggregate stat row, add a per-track breakdown section that lists each track's session count and avg score. Label the aggregate stat as "Avg across all tracks" so users understand it spans tracks. No backend change is needed — the field is already in the response.

Do not add a track filter control — that is scope creep. The per-track breakdown section is sufficient.

**Gap 3 — Pro users see no analytics in MockHub (frontend)**

Currently Pro users see only the Elite teaser panel in MockHub. The approved entitlement for Pro is "benchmark-facing performance context, no concept-coaching panel." Pro currently gets nothing except the comparison line in the MockSession summary (which is correct and should stay).

Fix: add a stripped "Your benchmark history" card in `MockHub.js` that is visible to Pro users (not Free, not Elite — Elite gets the full panel). It shows:

- total benchmark sessions completed
- avg benchmark score across all tracks (labeled clearly as cross-track)
- last benchmark session: track, difficulty, score, date

No sparkline. No concept breakdown. No weak-concept signals. No drill stats. These are Elite-only.

This card must be visually distinct from the Elite analytics panel — plainer, smaller, no sparkline or concept rows. It is factual history, not coaching intelligence.

**Gap 4 — No tests for modality-aware debrief or Pro analytics tier (tests)**

The existing TC-158–TC-162 cover debrief headlines by score band but do not cover:

- A reasoning-track session must not contain code-centric pattern language ("before writing code", "consecutive correct answers")
- A Pro user completing a benchmark session must receive `debrief: null` (Pro gets no debrief — Elite only)
- A Pro user hitting `GET /api/mock/analytics` must receive 403 (Elite only)
- The benchmark analytics response must not include drill sessions in `benchmark_summary.total_sessions`
- Statistics: a session composed entirely of conceptual questions must produce reasoning-track debrief language; a session with at least one numerical question must produce executable-track language

Add these as new test cases in `backend/tests/test_11_mock.py`.

### Entitlement target for this phase

| Tier | Benchmark access | Drill access | MockSession comparison line | MockHub analytics panel | Coaching debrief |
|---|---|---|---|---|---|
| Free | current free limits only | current free limits only | none | none | none |
| Pro | yes | yes | yes — own historical accuracy vs this session | stripped benchmark history card (total sessions, avg score, last session row) — no concept panel, no sparkline | none |
| Elite | yes | yes | yes | full panel: aggregate stats, sparkline, per-track breakdown, drill summary card, top/weak concept rows | full modality-aware debrief |

Phase-6 implementation rule:

- if a metric cannot be made truthful for a tier or mode, hide it instead of approximating

### Analytics invariants

- benchmark analytics never include drill sessions in their aggregates *(already enforced in backend — verify, do not re-implement)*
- drill analytics remain separate and are always labeled as drills *(already enforced)*
- mixed-track sessions never contribute to benchmark baselines *(already enforced by mode gating)*
- benchmark comparisons are cross-track by default but must be labeled as such; per-track breakdowns must be visible so users can compare like-for-like within a track
- benchmark comparisons only draw from sessions where `mode = "benchmark"`, not from drill sessions *(already enforced)*
- if reasoning tracks need different language labels, the debrief must branch on track family — do not reuse one generic copy string

### Debrief language rules

- executable tracks (SQL, Python, Pandas, numerical Statistics) use execution / debugging / approach / precision language
- reasoning tracks (PySpark, Data Engineering, Data Modeling, ML Fundamentals, Experimentation) use diagnosis / interpretation / prioritization / tradeoff language
- Statistics is hybrid: resolve track family based on session subtype composition (see Gap 1 above)
- benchmark debriefs should explain what the result says about interview readiness for that track; the current score-band headlines already do this correctly and must not change
- drill summaries have no debrief (debrief is Elite + benchmark result only) — the existing `debrief: null` for non-Elite and the current summary CTAs are sufficient for drill follow-up framing

### Primary implementation surfaces

- backend: `backend/routers/insights.py` — modality-aware debrief language only; `backend/routers/mock.py` — no changes needed (analytics separation is already correct)
- frontend: `frontend/src/pages/MockHub.js` — Pro benchmark history card, Elite per-track breakdown addition
- tests: `backend/tests/test_11_mock.py` — new reasoning-track debrief test cases, Pro analytics 403 test, benchmark-only aggregation invariant test

### Implementation lanes

1. Backend debrief lane (`insights.py` only)
   - add `_track_family(track, questions)` helper that returns `"executable"`, `"reasoning"`, or resolves Statistics from subtype mix
   - branch pattern copy and priority action copy on track family using the concrete replacements specified in Gap 1
   - do not change headline logic, historical concept lookup, follow-up detection, or time-sink pattern detection
   - add new test cases for reasoning-track and Statistics hybrid debrief language

2. Frontend analytics lane (`MockHub.js` only)
   - add the Pro benchmark history card (visible to Pro, hidden from Free and Elite)
   - add per-track breakdown rows under the Elite aggregate stat block
   - label the aggregate "Avg across all tracks" to make the cross-track nature explicit
   - no backend changes required — all needed fields already exist in the `/api/mock/analytics` response

### Non-goals

- no new mock modes
- no benchmark composition changes
- no changes to one-submit session mechanics
- no new question authoring or content rewrites
- no practice-page modality work outside what is required for truthful shared coaching language
- no refactor of `_compute_mock_analytics()` or `_compute_mock_session_summary()` — the backend analytics computation is correct
- no changes to `MockSession.js` summary — the existing comparison line, concept breakdown, CTA split, and share text are correct

### Acceptance criteria

- benchmark analytics shown to users are benchmark-only (already enforced); the UI now labels the aggregate as cross-track and shows per-track breakdown for Elite
- Pro users see a stripped benchmark history card in MockHub; Free users see nothing; Elite users see the full panel
- debrief language for reasoning tracks contains no code-execution phrasing ("before writing code", "3 consecutive correct answers")
- debrief language for executable tracks continues to use execution / debugging / approach framing
- Statistics sessions resolve track family from subtype composition, not from the track name alone
- backend tests cover: reasoning-track debrief language, Pro 403 on analytics, benchmark-only aggregation invariant, Statistics conceptual-only → reasoning language, Statistics with numerical → executable language

### Validation commands

- `cd backend && ../.venv/bin/python -m pytest tests/test_11_mock.py -q`
- `cd frontend && npm run test -- src/pages/MockHub.test.js src/pages/MockSession.test.js src/mockModeConfig.test.js`
- `cd frontend && npx playwright test e2e/mock-plan-flows.spec.js`
- `cd frontend && npm run build`

### Exit criteria

- analytics are trustworthy by track family and session mode
- entitlement story is cleaner than today and visible in the UI, not just in docs
- another model can pick up Phase 6 from this brief without redefining tier rules, analytics invariants, or debrief language templates — everything is specified concretely above

## Phase 7: Content Quality Backfill

Goal: make reasoning-track questions earn the "reasoning" label by content depth, not just UI framing.

This is a deliberate editorial phase, not a side effect of metadata work.

### Terminology note

All questions in reasoning tracks use multiple-choice as the response mechanism. The question `type` field distinguishes *format*, not mechanism:

| Type | Meaning |
|---|---|
| `conceptual` | Conceptual or scenario question answered by picking the best option — no code to trace |
| `predict_output` | Given a code snippet, predict what it returns or what error fires |
| `debug` | Given broken code or an error message, identify the root cause and fix |
| `scenario` | Production diagnosis: given logs, metrics, or job configuration, identify root cause or best remediation |
| `optimization` | Given a job or pipeline description, choose the best performance or design strategy |

`predict_output`, `debug`, `scenario`, and `optimization` are **code-adjacent formats** — they require mental execution tracing and are the core of what makes PySpark a code-adjacent reasoning track. All five types use multiple choice as the answer mechanism; the distinction is the cognitive demand of the question itself.

The term "MCQ" refers only to the response format (multiple choice). It says nothing about whether a question tests recall or reasoning. All reasoning-track questions, regardless of type, should test analysis, tradeoffs, and interpretation — never definition recall.

### Product outcomes

- reasoning tracks feel premium because the questions themselves demand diagnosis, interpretation, prioritization, and tradeoff thinking — not just because the UI labels changed
- PySpark hard tier shifts from predominantly conceptual toward the ~48% conceptual / ~52% code-adjacent target in `docs/content-authoring.md`
- Data Engineering gains its first debug questions so the benchmark type template can deliver on its stated format distribution
- Data Engineering and Data Modeling gain viable mock-only pools so benchmarks can serve fresh, unseen questions to users who have completed the practice track
- targeted net-new questions are added only where concept-hook coverage or benchmark blueprint coverage is still materially weak after rewrites

### Known structural gaps to resolve first

These are concrete, pre-diagnosed issues — not editorial judgment calls. Resolve them before doing any open-ended quality pass.

**Gap A — PySpark hard tier format imbalance**

Current state (practice questions only):

| Difficulty | Total | Conceptual | Code-adjacent | % code-adjacent | After +10 hard |
|---|---|---|---|---|---|
| easy | 41 | 23 | 18 (predict_output 14 · debug 4) | 44% | unchanged |
| medium | 39 | 25 | 14 (debug 6 · scenario 5 · predict_output 1 · optimization 2) | 36% | unchanged |
| hard | 26 | 20 | 6 (scenario 4 · predict_output 2) | 23% | 16/36 = 44% |
| **all** | **106** | **68** | **38** | **36%** | **48/116 = 41%** |

Spec target (`docs/content-authoring.md`) is ~52% code-adjacent across the full track. That is not reachable by addition alone without an implausible volume of new questions; the practical Phase 7 target for hard tier is ≥40% code-adjacent (up from 23%) with no removals. Medium is in scope only if hard additions alone leave obvious coverage holes in AQE/DPP.

Hard tier conceptual questions already cover every hard topic (AQE, DPP, skew join, watermarks, speculative execution) — many well. The deficit is code-adjacent *formats* that force mental execution tracing, not missing topic coverage. New questions must use a distinct angle from the 20 existing conceptual questions: give a snippet or observed behavior, not a conceptual prompt.

Target: add exactly 10 hard practice questions (`predict_output` and `scenario` only — no new `conceptual` at hard). Split recommendation:
- 5 × `predict_output`: AQE partition coalescing output prediction, skew join salting output trace, watermark boundary late-data drop prediction, DPP activation from partition column usage, pandas UDF null propagation
- 5 × `scenario`: multi-signal production diagnosis (straggler + AQE interaction, broadcast OOM under tight driver heap, Delta MERGE write amplification, speculative execution duplicate side effects, streaming watermark + trigger interval mismatch)

**Gap B — Data Engineering has 0 debug questions; benchmark template expects one**

`_benchmark_type_targets` for `data-engineering` = `["scenario", "conceptual", "debug", "scenario", "scenario", "conceptual"]`. DE has zero debug questions in any difficulty file. `_sample_by_format` silently falls back when the debug slot is unfillable, so no error fires — but the benchmark is silently delivering a different type distribution than the spec intends. Add 3–5 debug questions covering realistic DE failure modes: schema compatibility violations, idempotency bugs in backfill jobs, late-data watermark misconfiguration, CDC replication lag issues.

**Gap C — Data Engineering and Data Modeling have 1 mock-only question each**

DE: 1 mock-only (hard scenario, ID 53024). DM: 1 mock-only (hard scenario, ID 63024). Their benchmarks draw almost entirely from practice questions users have already seen. A benchmark that serves previously-seen content is not a valid benchmark. Add 12–15 mock-only questions per track at medium and hard so the fresh-first sampler has a real pool to draw from.

DE benchmark template is 6 slots: `["scenario", "conceptual", "debug", "scenario", "scenario", "conceptual"]`. For benchmarks at medium or hard, freshness-first sampling needs ≥6 unseen questions in the right type distribution. With only 1 mock-only question today, every DE benchmark is drawing from practice questions the user has already seen.

DM benchmark template is 5 slots: `["scenario", "conceptual", "scenario", "conceptual", "scenario"]`. Same problem: 1 mock-only question is nowhere near enough for a meaningful fresh pool.

Target mock-only pool minimums and next available IDs:

| Track | Current mock-only (med+hard) | Phase 7 target | Next medium ID | Next hard ID |
|---|---|---|---|---|
| Data Engineering | 1 (hard only) | 6 medium + 7–8 hard = 13–14 total | 52034 | 53025 |
| Data Modeling | 1 (hard only) | 6 medium + 6–7 hard = 12–13 total | 62029 | 63025 |
| PySpark | 21 (10 medium + 10 hard + 1 hard) | no change needed | — | — |
| ML Fundamentals | 25 | no change needed | — | — |
| Experimentation | 25 | no change needed | — | — |

Type split for DE mock-only additions: scenario-heavy (7–8 scenario), conceptual (4–5), debug (2). This matches the benchmark template and covers the concept-hook gaps without duplicating the practice bank.

Type split for DM mock-only additions: scenario-heavy (8–9 scenario), conceptual (4–5). DM has no debug or predict_output in its type vocabulary.

### Quality bar

Every question — rewritten or new — must pass the test in `docs/content-authoring.md`:

> Would a senior data interviewer at Meta, Google, Stripe, or Amazon ask this in a 45-minute screen?

Secondary checks from the same doc:
- difficulty comes from reasoning complexity, not syntactic obscurity
- distractors represent actual misconceptions a trained candidate would hold, not obviously wrong answers
- explanations address all four options: why each wrong answer is wrong, not just why the correct answer is right
- concept tags reflect the actual analytical pattern tested, not the tool name or API surface

All rewritten questions must have concept tags reviewed and updated to reflect the rewritten question's actual conceptual focus. Tags feed the Elite debrief weak-concept signals and focus mode — stale tags degrade coaching accuracy silently.

### Editorial selection rules

- rewrite a question only if it shows one or more concrete weaknesses: thin stem, generic answer-elimination feel, weak evidence surface, shallow distractors, low diagnostic value, or mismatch between claimed difficulty and actual reasoning depth
- do not churn strong questions just to make tone more dramatic
- prefer targeted rewrites over replacement when the concept, ID, and curricular position are still correct
- add new questions only when a real coverage gap remains after reviewing existing candidates and rewrite options
- for new mock-only questions: the concept angle must be distinct from practice questions at the same difficulty

### Concept-hook gaps to drive new authoring

From the Phase 2 audit (`docs/concept-expansion-plan.md`):

- **Data Engineering:** backpressure and flow control, privacy/compliance architecture, data contract operationalization, warehouse cost modeling, incident containment patterns
- **Data Modeling:** bi-temporal modeling, semantic layer governance, semi-additive metric design, advanced hierarchy variants
- **ML Fundamentals:** parametric vs non-parametric reasoning, inductive bias, encoding strategy, activation function tradeoffs, batch normalization, attention mechanisms
- **Experimentation:** ratio-metric/delta-method coverage, surrogate-metric validation, control-vs-holdout A/A test nuance

These are the gaps Phase 7 authoring should draw from first. Do not author questions outside these concept families unless a benchmark slot cannot be filled otherwise.

### Priority order

1. **PySpark** — fix hard tier code-adjacent format deficit (Gap A)
2. **Data Engineering** — add debug questions (Gap B) + build mock-only pool (Gap C)
3. **Data Modeling** — build mock-only pool (Gap C)
4. **Experimentation** — targeted additions from hook audit gaps; existing mock-only pool is solid
5. **ML Fundamentals** — targeted additions from hook audit gaps; existing mock-only pool is solid

### Implementation lanes

**Lane 1: PySpark hard tier (Gap A)**

- Scope: `backend/content/pyspark_questions/hard.json` (primary); medium.json only if hard additions leave obvious AQE/DPP coverage holes
- Task: add exactly 10 new hard practice questions — 5 × `predict_output` + 5 × `scenario`. No new `conceptual` at hard.
- `predict_output` targets: (1) AQE partition coalescing — predict output partition count after a wide aggregation; (2) skew join salting — predict join output count/schema after manual salting; (3) watermark boundary — given watermark expression and event-time values, predict which late records are dropped vs retained; (4) DPP activation — given a filter on a non-partition column vs partition column, predict whether DPP fires; (5) pandas UDF null handling — predict what the UDF returns when the input column contains nulls
- `scenario` targets: (1) straggler task + AQE skew hint interaction producing unexpected partition count; (2) driver OOM during broadcast relation construction for a join within a UDF; (3) Delta MERGE producing write amplification at scale — given metrics, diagnose; (4) speculative execution creating duplicate writes to a non-idempotent sink; (5) structured streaming watermark + trigger interval mismatch causing delayed output in update mode
- Next available IDs: hard starts at 43037 (43027–43036 are mock-only)
- Do not touch existing hard questions; the 20 conceptual questions already cover every hard topic — the gap is format diversity, not topic coverage
- Each new question must have a realistic `code_snippet` or `scenario_context` per `docs/content-authoring.md` PySpark schema rules
- Update ID allocation table in `docs/concept-expansion-plan.md`

**Lane 2: Data Engineering gap resolution (Gaps B + C)**

- Scope: `backend/content/data_engineering_questions/medium.json` and `hard.json`

Task A — Gap B (debug questions, practice):
- Add 4 debug practice questions: 2 medium (IDs 52034–52035) + 2 hard (IDs 53025–53026). One additional hard if a strong candidate exists (53027).
- Each must include a `debug_error` field with a realistic error string. Single-bug root cause, no compound failures.
- Topic targets: (1) schema compatibility violation — Avro/Parquet schema evolution error on a downstream consumer after an upstream ALTER; (2) idempotency bug — backfill job that re-inserts instead of upserts, producing duplicate rows; (3) CDC replication lag — watermark misconfiguration causing late events to be dropped silently; (4) partition overwrite — dynamic partition overwrite deleting unexpected partitions due to missing `spark.sql.sources.partitionOverwriteMode` setting
- These are practice questions, not mock-only. The debug concept is weak across the entire DE bank; these should be in the practice progression.

Task B — Gap C (mock-only pool):
- Add 13 mock-only questions: 6 medium (IDs 52036–52041) + 7 hard (IDs 53028–53034, noting 53024 is already taken)
- Type split: 7–8 scenario, 4–5 conceptual, 2 debug (mock-only debug questions cover more niche failure modes than the practice debug questions above)
- Concept targets from hook audit gaps: backpressure and flow control mechanics, privacy/compliance architecture decisions, data contract enforcement patterns, warehouse cost modeling (partition vs clustering vs materialized view tradeoff), incident containment playbooks (runbook design, circuit breakers in pipelines)
- No concept tag may duplicate an existing practice question at the same difficulty level
- Update ID allocation table in `docs/concept-expansion-plan.md`

**Lane 3: Data Modeling mock-only pool (Gap C)**

- Scope: `backend/content/data_modeling_questions/medium.json` and `hard.json`
- Task: add 12 mock-only questions: 6 medium (IDs 62029–62034) + 6 hard (IDs 63025–63030), noting 63024 is already taken
- Type split: scenario-heavy (8–9 scenario) + conceptual (3–4). DM valid types are `scenario` and `conceptual` only — no debug/predict_output.
- Benchmark template is 5 slots: `["scenario", "conceptual", "scenario", "conceptual", "scenario"]` — mock-only additions should include enough conceptual questions to fill the 2 conceptual slots with fresh content
- Concept targets from hook audit gaps: bi-temporal modeling (transaction time vs valid time separation, bitemporal SCD design), semantic layer governance (certified vs experimental metrics, ownership and deprecation), conformed dimension governance across business units, SCD type selection under conflicting retention and query requirements, schema evolution strategy when downstream consumers have heterogeneous schema expectations
- No concept tag may duplicate an existing practice question at the same difficulty level
- Update ID allocation table in `docs/concept-expansion-plan.md`

**Lane 4: Experimentation + ML Fundamentals targeted additions**

Context: both tracks already have healthy mock-only pools (25 each) and broad concept-family coverage. These additions fill recorded concept-hook gaps in the practice bank only — no mock-only work needed here.

Experimentation — current practice bank: easy 30 (all conceptual), medium 30 (27 scenario · 2 predict_output · 1 debug), hard 20 (16 scenario · 2 predict_output · 2 debug).
- Next medium IDs: 92043–92046 (4 questions max). Next hard IDs: 93034–93037 (4 questions max).
- Gap hooks (from `docs/concept-hooks.md`): hook 22 (ratio metrics + delta method), hook 24 (surrogate vs long-term metrics validation), hooks 4–5–6 (control group design / holdout groups / A/A test nuance — present but shallow)
- Task: add 4 practice questions targeting these hooks. 2 medium (92043–92044): delta-method variance reduction for ratio metrics (scenario), surrogate metric validation framework (conceptual). 2 hard (93034–93035): A/A test detecting platform bias (scenario), ratio metric sensitivity vs count metric for sample-size planning (predict_output or scenario).
- Type guidance: delta-method and ratio metrics lend themselves to `predict_output` (given a formula or code, predict variance/CI output) or `scenario` (given test results, identify the sensitivity mistake). Keep them out of pure `conceptual` format since the concepts are already present in the bank.

ML Fundamentals — current practice bank: easy 30 (all conceptual), medium 35 (19 conceptual · 13 scenario · 2 predict_output · 1 debug), hard 25 (19 scenario · 4 conceptual · 1 predict_output · 1 debug).
- Next medium IDs: 82048–82051 (4 questions max). Next hard IDs: 83039–83041 (3 questions max).
- Gap hooks (from `docs/concept-hooks.md`): hook 3 (parametric vs non-parametric models), hook 4 (inductive bias), hook 23 (encoding strategy), hook 31 (activation function comparisons), hook 32 (batch normalization), hook 35 (attention mechanism)
- Task: add 6 practice questions targeting these hooks. 3 medium (82048–82050): parametric vs non-parametric capacity tradeoffs (conceptual), encoding strategy for tree vs linear models (scenario), activation function selection for deep vs shallow networks (conceptual). 3 hard (83039–83041): batch normalization placement and gradient stability (scenario or predict_output), attention mechanism — scaled dot-product output interpretation (predict_output), inductive bias comparison for SVM vs tree vs NN under distribution shift (scenario).
- Type guidance: prefer `scenario` or `predict_output` over pure `conceptual` for hard questions. Easy and medium already have ~57% conceptual; don't increase that share further.

**Lane 5: Content governance (runs after lanes 1–4)**

- Update `docs/concept-expansion-plan.md` with every question rewritten vs newly added, reason for change, and ID allocated
- Update the ID allocation table for any track where IDs were appended
- If any concept-tag families were extended or renamed during Phase 7 authoring, update the family lists in `docs/content-authoring.md`
- Run the duplicate-ID check from `docs/content-authoring.md` before closing the lane

### Non-goals

- no whole-bank rewrites
- no modality taxonomy changes
- no changes to `_benchmark_type_targets` in `backend/routers/mock.py` — the templates are correct; Phase 7 makes the content match them, not the other way around
- no frontend or backend UX work
- no new tracks, no new mock modes, and no entitlement changes
- no question rewrites done purely for voice/style polish when the question is already structurally strong

### Acceptance criteria

- PySpark hard tier: exactly 10 new hard practice questions added (`predict_output` + `scenario`); hard tier is ≥40% code-adjacent (up from 23%)
- Data Engineering: ≥4 debug practice questions exist; `_sample_by_format` can fill the debug slot in a DE benchmark from the practice pool without silent fallback
- Data Engineering mock-only pool at medium+hard: ≥13 questions total (was 1)
- Data Modeling mock-only pool at medium+hard: ≥12 questions total (was 1)
- Experimentation: 4 new practice questions targeting ratio-metric/delta-method, surrogate metrics, and A/A design hooks
- ML Fundamentals: 6 new practice questions targeting parametric/non-parametric, encoding strategy, activation functions, batch normalization, attention hooks
- All new questions pass the FAANG senior-interviewer test from `docs/content-authoring.md`
- All new questions have concept tags reviewed and accurate (not inherited from a nearby question by mistake)
- All new mock-only questions use concept angles distinct from practice questions at the same difficulty
- `docs/concept-expansion-plan.md` updated with every ID allocated in Phase 7 and reason for addition

### Validation commands

```bash
# Catalog and schema integrity
cd backend && ../.venv/bin/python -m pytest tests/test_08_pyspark.py tests/test_19_data_engineering.py tests/test_20_data_modeling.py tests/test_31_reasoning_metadata.py -q

# Mock composition (run when mock-only additions or benchmark content changes land)
cd backend && ../.venv/bin/python -m pytest tests/test_11_mock.py -q

# Duplicate ID check
.venv/bin/python -c "
import json, glob
all_ids = []
for f in glob.glob('backend/content/*/*.json'):
    if 'schemas' in f: continue
    all_ids.extend(q['id'] for q in json.load(open(f)))
dupes = [x for x in all_ids if all_ids.count(x) > 1]
print('Duplicate IDs:', set(dupes) or 'none')
"

# Docs diff
git diff -- docs/concept-expansion-plan.md docs/content-authoring.md
```

### Exit criteria

- Gap A resolved: PySpark hard tier practice pool is 36 questions, ≥16 code-adjacent (≥44%)
- Gap B resolved: DE debug practice pool has ≥4 questions; a DE benchmark at any difficulty can fill the `debug` slot from the real pool
- Gap C resolved: DE has ≥13 mock-only questions at medium+hard; DM has ≥12 mock-only questions at medium+hard
- Experimentation and ML Fundamentals hook audit gaps addressed: hooks 22 + 24 + A/A nuance covered for Exp; hooks 3 + 4 + 23 + 31 + 32 + 35 covered for ML
- All new IDs recorded in `docs/concept-expansion-plan.md`
- Full test suite passes (`tests/test_08_pyspark.py`, `tests/test_19_data_engineering.py`, `tests/test_20_data_modeling.py`, `tests/test_31_reasoning_metadata.py`, `tests/test_11_mock.py`)
- No duplicate IDs in the bank
- content additions remain targeted and justified, not opportunistic bank expansion
- another model can pick up any remaining Phase 7 work from the audit trail without re-auditing the whole bank

## Phase 8: Concept-Hooks Completion And Social Automation Readiness

Goal: make [docs/concept-hooks.md](./concept-hooks.md) exhaustive and usable for future social-media automation.

This phase is documentation and curriculum-governance work, not product-code work.

Product outcomes:

- `docs/concept-hooks.md` becomes the reliable canonical concept inventory for every live track
- every track gains an advanced mock-only hook section suitable for later social or content automation work
- hook phrasing becomes publication-ready: concise, specific, and non-duplicative
- hook docs, audit docs, and authoring docs agree on what is covered, what is missing, and what future authoring is still justified

Requirements:

- non-mock sections remain the canonical exhaustive concept coverage for every track
- advanced mock-only hook sections are extended to all tracks, not just the currently covered subset
- hook phrasing is made publication-ready for future automation use
- the document clearly distinguishes between practice-track concept coverage and mock-only advanced-topic coverage
- reconciled docs must make it obvious whether a gap is solved by existing questions, planned rewrites, or future net-new authoring

Primary implementation surfaces:

- `docs/concept-hooks.md`
- `docs/concept-expansion-plan.md`
- `docs/content-authoring.md`
- this rollout plan if hook completion changes the stated future authoring backlog

Suggested Codex lanes:

1. Hook expansion lane
   - extend advanced mock-only topic coverage to all tracks
   - fill any remaining missing non-mock sections or uneven track coverage in `docs/concept-hooks.md`

2. Audit reconciliation lane
   - make sure hook lists, audit notes, and content-expansion status agree
   - remove stale statements that no longer match current content reality

3. Publication-polish lane
   - tighten hook wording so it is specific enough for automation use and consistent in style across tracks
   - normalize section structure, phrasing patterns, and duplicate topic handling

4. Docs integration lane
   - update planning docs if hook coverage changes imply future authoring work
   - update `docs/content-authoring.md` if concept-tag or hook-writing guidance changes during reconciliation

Non-goals:

- no product-code changes
- no silent content JSON edits as part of hook cleanup unless explicitly scoped into another phase
- no whole-bank audit restart
- no social automation implementation itself — only readiness groundwork
- no speculative new hook sprawl that is not tied to actual platform curriculum or mock roadmap needs

Acceptance criteria:

- every track has exhaustive non-mock hook coverage
- every track has an advanced mock-only hook section suitable for future automation workflows
- hook coverage status aligns with the content-expansion and modality plans
- cross-doc contradictions between `concept-hooks`, `concept-expansion-plan`, and `content-authoring` are removed
- another model can use the docs as a trustworthy source of truth without re-reconciling the three documents first

Validation guidance:

- `cd /Users/matt/Work/projects/sql-interview-practice && git diff -- docs/concept-hooks.md docs/concept-expansion-plan.md docs/content-authoring.md docs/mock-modality-rollout-plan.md`
- if Phase 8 work also touches any content metadata files, run: `cd backend && ../.venv/bin/python -m pytest tests/test_31_reasoning_metadata.py -q`

Exit criteria:

- hook coverage is exhaustive, publication-ready, and cross-doc consistent
- future authoring needs are recorded explicitly instead of being left implicit in audit prose
- another model can pick up Phase 8 from this brief without redefining what counts as exhaustive coverage or automation readiness

## Codex Tasking Template

Every Codex task should include:

- phase number
- lane name
- exact files in scope
- explicit non-goals
- acceptance criteria
- validation commands
- handoff note format

Required handoff note from each Codex lane:

- changed files
- what was implemented
- what remains blocked or unresolved
- validation run and result
- risks or review notes for orchestrator

## Orchestrator Review Checklist

For every lane handoff, the orchestrator reviews:

1. Did the lane stay inside its exact phase scope?
2. Did the lane avoid product drift or speculative redesign?
3. Did the lane preserve track-specific fidelity?
4. Did the lane create truthful UX language for reasoning tracks?
5. Did the lane validate the touched slice narrowly?
6. Do docs and prompts need updates before merge?

## Initial Parallelization Map

Recommended first execution wave:

### Wave A: Phase 0

- Codex content audit lane
- Codex backend schema lane
- Codex frontend inventory lane

### Wave B: Phase 1

- Codex PySpark content classification lane
- Codex PySpark backend metadata lane
- Codex PySpark frontend UX lane

### Wave C: Phase 2

- Codex reasoning content generalization lane
- Codex shared backend serializer lane
- Codex shared frontend practice lane

Only start Wave B after orchestrator signs off on the Phase 0 freeze.
Only start Wave C after orchestrator signs off on PySpark.

### Wave D: Phase 8

- Codex hook expansion lane
- Codex audit reconciliation lane
- Codex docs integration lane

Only start Wave D after the orchestrator confirms the main modality taxonomy is stable enough that hook wording will not churn.

## Planning Notes

- This plan intentionally avoids product-code changes during planning.
- Planning artifacts may evolve, but implementation should start only after the orchestrator issues a phase-specific kickoff.
- If model-specific agent binding is unavailable in the environment, the orchestrator still assigns implementation work by choosing the GPT Codex model at invocation time.