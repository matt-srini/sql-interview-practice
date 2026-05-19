# Mock Modality Migration - Phase 0 Frontend Audit

Date: 2026-05-19
Owner lane: Frontend (Phase 0)
Scope: audit and implementation foundation only (docs-only, no product behavior changes)

## 1) Objective (Frontend Phase 0)

Create a concrete, file-level frontend inventory of where current practice and mock UX still collapses modality into generic MCQ framing, and where future subtype-aware rendering and terminology changes must land in Phase 1+ without changing backend contracts in this phase.

This audit is anchored to:
- [docs/mock-modality-rollout-plan.md](../mock-modality-rollout-plan.md)
- [docs/specs/platform-north-star.md](../specs/platform-north-star.md)
- [docs/specs/practice-modality-spec.md](../specs/practice-modality-spec.md)
- [docs/specs/mock-benchmark-spec.md](../specs/mock-benchmark-spec.md)

## 2) Inventory: Current Surfaces That Blur Modality

### Practice and track-labeling surfaces

| Surface | Current behavior | Why it is a modality mismatch |
|---|---|---|
| [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js) | Reasoning-first tracks use taglines with MCQ language (for example: conceptual · MCQ · scenario). | Global track metadata is reused across practice hub, dashboard, and landing role cards, so generic MCQ framing propagates everywhere. |
| [frontend/src/pages/TrackHubPage.js](../../frontend/src/pages/TrackHubPage.js) | Track descriptions and hub copy include MCQ-centric labeling, especially PySpark and reasoning tracks. | Hub is the first practice surface per track and should describe interaction mode, not answer format shorthand. |
| [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js) | Hero IDE cards and tracks-index format labels use MCQ badges for PySpark and reasoning tracks. | Marketing/editorial surface currently signals quiz framing instead of reasoning modality. |
| [frontend/src/pages/ProgressDashboard.js](../../frontend/src/pages/ProgressDashboard.js) | Dashboard track rows display taglines from track metadata, including MCQ labels. | Coaching surface should reinforce modality and track intent, not generic answer format. |
| [frontend/src/components/AppShell.js](../../frontend/src/components/AppShell.js) | Internal unlock helpers are named by MCQ-vs-code split and include MCQ terminology in hint logic comments. | Internal model currently reflects binary code-vs-MCQ framing, making future modality generalization harder. |

### Practice question rendering surfaces

| Surface | Current behavior | Why it is a modality mismatch |
|---|---|---|
| [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js) | Branches mostly on code vs MCQ (renderMode = code or mcq). MCQ side uses a single heading: Choose the correct answer. | Subtype-aware rendering is shallow; debug, predict-output, scenario, and reasoning variants mostly share one affordance. |
| [frontend/src/components/MCQPanel.js](../../frontend/src/components/MCQPanel.js) | Generic option picker UI with explanation area. | Component naming and wording is answer-format-centric, not interaction-mode-centric. |
| [frontend/src/pages/SampleQuestionPage.js](../../frontend/src/pages/SampleQuestionPage.js) | Mirrors the same code-vs-MCQ split and same Choose the correct answer heading. | Sample surface repeats the same modality collapse as main practice. |

### Mock surfaces

| Surface | Current behavior | Why it is a modality mismatch |
|---|---|---|
| [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) | Primary mode model is Quick / Full / Custom; wording and controls are centered on custom question count and time knobs. | Benchmark spec requires benchmark-vs-drill separation and fixed benchmark blueprints by track/modality. |
| [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) | PySpark composition hints explicitly include mcq slots and labels. | Keeps PySpark framed as option-picking instead of code-adjacent reasoning. |
| [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) | Active session rendering uses hasMCQ boolean split; MCQ branch is generic and not subtype-specific. | No path for richer reasoning interaction variants inside mock sessions. |
| [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) | Mid-session verdict message reveals correct vs not correct after each submit. | Violates benchmark invariant: no correctness reveal mid-session. |
| [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) | Wrong-answer feedback is shown mid-session; users can skip and re-submit until solved. | Current behavior is drill-like, not strict benchmark behavior. |

## 3) Exact Routes/Pages/Components Needing Subtype-Aware Rendering or Terminology Changes

### Route-level map

| Route | Page | Targeted area |
|---|---|---|
| /practice/:topic/questions/:id | [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js) | Replace generic MCQ language; add subtype-aware instructions and action framing for reasoning tracks. |
| /practice/:topic | [frontend/src/pages/TrackHubPage.js](../../frontend/src/pages/TrackHubPage.js) | Update track-specific helper copy/taglines away from generic MCQ labels. |
| /sample/:topic/:difficulty | [frontend/src/pages/SampleQuestionPage.js](../../frontend/src/pages/SampleQuestionPage.js) | Keep sample parity with practice terminology updates and subtype cues. |
| /mock | [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) | Split benchmark framing from drill framing in future phases; remove Quick/Full/Custom as benchmark model. |
| /mock/:id | [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) | Add benchmark-safe no-verdict mid-session path and subtype-aware question chrome. |
| /dashboard | [frontend/src/pages/ProgressDashboard.js](../../frontend/src/pages/ProgressDashboard.js) | Ensure track taglines/coaching labels reflect modality taxonomy. |
| / | [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js) | Align editorial labels and showcase badges with modality model. |

### Shared components and metadata

- [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js): canonical place to normalize taglines and modality-facing labels.
- [frontend/src/components/MCQPanel.js](../../frontend/src/components/MCQPanel.js): currently generic answer-picker language.
- [frontend/src/components/AppShell.js](../../frontend/src/components/AppShell.js): unlock-helper naming still reflects MCQ-vs-code binary.

## 4) Track-by-Track Notes (PySpark, Statistics, Reasoning-First Tracks)

### PySpark (code-adjacent reasoning)

Current state:
- Practice question rendering is largely the generic MCQ branch in [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js).
- Mock hub expectation labels in [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) explicitly include mcq slots.
- Landing and hub labels continue MCQ framing in [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js) and [frontend/src/pages/TrackHubPage.js](../../frontend/src/pages/TrackHubPage.js).

Phase implication:
- Phase 1 should prioritize PySpark wording and subtype affordance differentiation (predict, debug, scenario, optimization) without changing scoring logic in Phase 0.

### Statistics (hybrid track)

Current state:
- Practice has partial subtype-aware branching (numerical -> code, conceptual -> MCQ) in [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js).
- Surface labeling still includes MCQ shorthand in [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js) and downstream views.
- Mock session branch in [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) is driven by hasMCQ and is not explicitly subtype-aware for benchmark composition.

Phase implication:
- Future phases need explicit hybrid mock rendering cues and payload-driven subtype handling so numerical statistics questions can behave as executable mock items where required.

### Reasoning-first tracks (Data Engineering, Data Modeling, ML Fundamentals, Experimentation)

Current state:
- Track labels and editorial copy still rely on MCQ-centric descriptors in [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js), [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js), and [frontend/src/pages/TrackHubPage.js](../../frontend/src/pages/TrackHubPage.js).
- Practice rendering currently uses one generic non-code branch in [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js).

Phase implication:
- Phase 1 should begin terminology cleanup where already approved; richer subtype-specific rendering for these tracks should follow once backend/content taxonomy is stabilized in later phases.

## 5) Mock-Specific UX Inventory

### What currently reveals during active mock session

In [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js):
- Per-submit correctness verdict is shown immediately (correct vs not quite).
- Wrong-answer feedback list appears mid-session.
- Users can continue editing/re-submitting unsolved questions.
- Skip for now and Next question controls create drill-style flow.

### What is currently benchmark-safe

In [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js):
- Correct option index is intentionally hidden mid-session for MCQ-style questions.
- Explanation text is withheld mid-session.
- Full solutions/explanations are revealed in summary after finish.
- Run button is only shown where execution exists.

### What should later split benchmark vs drill

- Benchmark path (future): fixed track blueprints, single final submit per question, no correctness/solution reveal mid-session, neutral submission acknowledgment only.
- Drill path (future): keep interactive feedback loops, skips, configurable counts/timers, and optional immediate coaching.
- Current Quick/Full/Custom controls in [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) map more closely to drill and should migrate there in later phases.

## 6) Risks and Dependencies (Backend/Taxonomy)

1. Practice and mock payloads currently drive most frontend branching from track-level booleans (hasMCQ, hasRunCode, mixedSubtype), which is insufficient for full interaction_mode/subtype UX.
2. Frontend needs a stable, canonical subtype and interaction vocabulary from backend/content lanes before large UI refactors to avoid churn.
3. Benchmark-safe mock behavior likely needs explicit backend session flags (for example, benchmark vs drill semantics and reveal policy) so frontend does not infer critical rules heuristically.
4. Statistics mock hybrid behavior depends on backend composition/payload support for numerical-vs-conceptual subtype in session questions.
5. Naming migration must be coordinated across shared metadata and tests because [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js) is reused by landing, practice hub, and dashboard.

## 7) Focused Validation Commands for Later Frontend Phases

Recommended focused checks after Phase 1+ implementation:

- npm --prefix frontend run test -- src/pages/MockSession.test.js
- npm --prefix frontend run test -- src/pages/ProgressDashboard.test.js
- npm --prefix frontend run test -- src/pages/LandingPageTiers.test.js
- npm --prefix frontend run test -- src/components/SidebarNav.test.js
- npm --prefix frontend run test
- npm --prefix frontend run build

Optional broader UI validation when backend/frontend dev servers are running:

- npx --prefix frontend playwright test

## 8) Recommendations: Phase 1 vs Later Phases

### Phase 1 (frontend-facing, low-regret changes)

1. Update shared track terminology in [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js) and dependent display surfaces to remove generic MCQ-first phrasing where specs already define better modality language.
2. Implement PySpark-first practice copy and subtype cues in [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/TrackHubPage.js), and [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js) without changing scoring contracts.
3. Preserve current backend API behavior while making UI wording explicitly reasoning-oriented.

### Later phases (after backend/content metadata stabilization)

1. Move from binary code-vs-MCQ branching to payload-driven interaction_mode/subtype rendering in practice and mock.
2. Redesign [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js) and [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js) into benchmark vs drill split aligned with mock benchmark spec.
3. Add benchmark-safe session UX path with no mid-session correctness reveals and final-submit semantics.
4. Introduce explicit hybrid handling for statistics mock sessions once backend composition contract is updated.
5. Expand modality-specific component structure beyond generic [frontend/src/components/MCQPanel.js](../../frontend/src/components/MCQPanel.js) abstractions.

## Source Files Reviewed (frontend)

- [frontend/src/App.js](../../frontend/src/App.js)
- [frontend/src/trackRegistry.js](../../frontend/src/trackRegistry.js)
- [frontend/src/contexts/TopicContext.js](../../frontend/src/contexts/TopicContext.js)
- [frontend/src/components/AppShell.js](../../frontend/src/components/AppShell.js)
- [frontend/src/components/SidebarNav.js](../../frontend/src/components/SidebarNav.js)
- [frontend/src/components/MCQPanel.js](../../frontend/src/components/MCQPanel.js)
- [frontend/src/pages/QuestionPage.js](../../frontend/src/pages/QuestionPage.js)
- [frontend/src/pages/SampleQuestionPage.js](../../frontend/src/pages/SampleQuestionPage.js)
- [frontend/src/pages/TrackHubPage.js](../../frontend/src/pages/TrackHubPage.js)
- [frontend/src/pages/MockHub.js](../../frontend/src/pages/MockHub.js)
- [frontend/src/pages/MockSession.js](../../frontend/src/pages/MockSession.js)
- [frontend/src/pages/ProgressDashboard.js](../../frontend/src/pages/ProgressDashboard.js)
- [frontend/src/pages/LandingPage.js](../../frontend/src/pages/LandingPage.js)
- [frontend/src/pages/MockSession.test.js](../../frontend/src/pages/MockSession.test.js)
- [frontend/src/pages/LandingPageTiers.test.js](../../frontend/src/pages/LandingPageTiers.test.js)
