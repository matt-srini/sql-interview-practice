# Mock Modality Rollout Plan

Planning document for the practice and mock modality migration.

Status: execution started, Phase 0 audit complete, Phase 2 complete, Phase 3 complete
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

## Phase 6: Analytics, Debrief, And Entitlement Cleanup

Goal: make mock analytics and coaching modality-aware and tier-coherent.

Focus areas:

- benchmark analytics only compare like with like
- reasoning-track debriefs speak in diagnosis / interpretation language
- coding-track debriefs speak in execution / approach language
- Pro becomes the serious benchmark tier
- Elite becomes the intelligent coaching tier

Exit criteria:

- analytics are trustworthy by track family
- entitlement story is cleaner than today

## Phase 7: Content Quality Backfill

Goal: improve weak reasoning questions that are currently too option-led or too thin.

This is a deliberate editorial phase, not a side effect of metadata work.

Priority order:

1. PySpark
2. Data Engineering
3. Experimentation
4. ML Fundamentals
5. Data Modeling

Content work types allowed in this phase:

- targeted rewrites of weak reasoning questions
- selective new questions where concept-hooks coverage is still incomplete
- selective mock-only additions where benchmark blueprint coverage is inadequate

This phase is where the still-open ML Fundamentals and Experimentation audit outcomes may lead to new question authoring.

## Phase 8: Concept-Hooks Completion And Social Automation Readiness

Goal: make [docs/concept-hooks.md](./concept-hooks.md) exhaustive and usable for future social-media automation.

This phase is documentation and curriculum-governance work, not product-code work.

Requirements:

- non-mock sections remain the canonical exhaustive concept coverage for every track
- advanced mock-only hook sections are extended to all tracks, not just the currently covered subset
- hook phrasing is made publication-ready for future automation use
- the document clearly distinguishes between practice-track concept coverage and mock-only advanced-topic coverage

Parallel Codex lanes:

1. Hook expansion lane
   - extend advanced mock-only topic coverage to all tracks
2. Audit reconciliation lane
   - make sure hook lists, audit notes, and content-expansion status agree
3. Docs integration lane
   - update planning docs if hook coverage changes imply future authoring work

Exit criteria:

- every track has exhaustive non-mock hook coverage
- every track has an advanced mock-only hook section suitable for future automation workflows
- hook coverage status aligns with the content-expansion and modality plans

Exit criteria:

- weak questions are rewritten, not just re-labeled
- reasoning tracks feel premium by content quality, not only UI

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