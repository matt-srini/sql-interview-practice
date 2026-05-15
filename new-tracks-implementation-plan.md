# New Tracks + Landing Redesign — Implementation Plan

> **Temporary working doc.** Delete this file *and* `new-tracks-roadmap.md` once
> all three tracks are launched and the landing redesign has shipped. This plan
> supersedes the roadmap wherever they conflict (see "Decisions" below).

This plan is grounded in a read of the actual codebase (loaders, routers,
`unlock.py`, `mock.py`, `insights.py`, `validate_content.py`, `TopicContext.js`,
`QuestionPage.js`, `catalogContext.js`, `App.js`, `sample_questions.py`,
`db.py`). It is engineered so each track is a near-mechanical, low-risk change
rather than a re-touch of eight files three times over.

---

## 0. Decisions that override / clarify the roadmap

| # | Decision | Rationale |
|---|---|---|
| D1 | **Landing exposure is decoupled.** New tracks ship fully functional and reachable via the Practice dropdown, SidebarNav track switcher, TrackHub, direct `/practice/:topic` route, mock, and learning paths — but are **NOT** added to the legacy 4-tile landing grid. Landing surfacing happens only in the redesign workstream (Phase E). | The 4-tile grid is being retired; expanding it is throwaway work. |
| D2 | **One combined plan, separate workstreams.** Phases A–D (platform + 3 tracks) and Phase E (landing redesign) are independent; E can land any time after Phase A without blocking track work. | Keeps the philosophy-first redesign from gating content delivery. |
| D3 | **Slug == DB topic == `:topic` param == API segment, hyphenated, no underscore alias.** New tracks use `data-engineering`, `data-modeling`, `statistics` *everywhere*. We do **not** repeat the `python-data`↔`python_data` split (that is legacy debt — do not propagate it). | Every hyphen/underscore alias is a hardcoded mapping site and a bug surface. One string everywhere = fewest edits. |
| D4 | **No DB migration required.** `user_progress.topic` and `submissions.track` are `TEXT NOT NULL` with no enum/CHECK (verified in `db.py`). New topic strings work immediately. | Removes a feared migration risk; do not add one. |
| D5 | **Question IDs follow the authoritative TXNNN strategy in §8 — no deviation.** New tracks: Data Engineering `T=5`, Data Modeling `T=6`, Statistics `T=7` (`51001/52001/53001`, `61001/…`, `71001/…`). Mock-only IDs sit at the *top* of each difficulty range (no separate numbering). IDs are append-only. Non-SQL tracks get **no dedicated sample IDs** (samples are auto-sliced from the first 3 practice questions by `order`). | Single self-contained scheme; guarantees no cross-track overlap by construction; matches the verified live JSON. §8 is binding. |
| D6 | **Sequential track rollout stays.** DE Concepts → Data Modeling → Statistics, each end-to-end before the next (roadmap rule). Phase A (platform prep) and Phase E (landing) are *not* track work and do not violate this. | Roadmap constraint; preserves content QA focus. |
| D7 | **New tracks are NOT added to the mock `mixed` pool initially.** They are selectable as their own mock track. Revisit `mixed` composition + role-based presets only after all three launch. | Silently changing `mixed` mock composition would surprise existing users. |
| D8 | **Statistics renders per-question, not per-track.** `subtype: "conceptual"` → MCQ render/eval; `subtype: "numerical"` → Python editor + test cases (reuses `python_evaluator.py`). Driven by the question payload, gated by a `mixedSubtype` meta flag. | TRACK_META's single `hasMCQ`/`hasRunCode` cannot express a per-question split — see Phase D. |

---

## 0.5 Phase A0 — Docs baseline audit (do this first, before any code)

Per the standing instruction "make sure all docs are up to date before we
start." Implementation must begin from a doc baseline that matches reality.

- [x] **A0.1.** Reconcile `docs/content-authoring.md` with actual loaders.
  Known drift to fix: the Pandas section lists IDs as `5001–5999` (Easy
  `5001–5299`, Medium `5300–5599`, Hard `5600–5999`) but `python_data_questions/
  schemas.json` actually uses `31001/32001/33001`. Correct the doc to the real
  ranges. Sweep the whole "ID ranges" + per-track difficulty sections for any
  other loader/doc mismatch.
- [x] **A0.2.** Verify `CLAUDE.md` content footprint counts match the live
  catalog loaders (question counts per track/difficulty) and fix any skew.
- [x] **A0.3.** Confirm every doc cross-reference resolves (`docs/README.md`
  index, links between docs, `.github/agents/*` references).
- [x] **A0.4.** Add a short "Track registry" placeholder note to
  `docs/architecture.md` and `docs/backend.md` describing that Phase A will
  introduce `backend/tracks.py` as the single source of truth (so the doc and
  the refactor land coherently).
- [x] **A0.5.** Commit the baseline-audit fixes on their own ("docs: reconcile
  content-authoring ID ranges and footprint counts with loaders") before
  Phase A code begins.

Rule for everything after A0: **no phase is complete until its doc targets are
updated in the same commit.** The mapping in §5 is binding.

---

## 1. The core engineering decision — Phase A: Track Registry

The roadmap's per-track backend tasks each independently re-edit the same
hardcoded track lists. Doing that three times guarantees drift and bugs. Instead,
**Phase A introduces one source of truth and refactors the existing four tracks
onto it, with zero behavior change.** After Phase A, adding a track is mostly a
registry entry + content + a few render maps.

### Hardcoded track-list sites (the full blast radius)

Backend:
- `unlock.py` — `_is_pyspark()`, threshold-table selection, `compute_mock_access` `_track_label`
- `routers/mock.py` — `VALID_TRACKS`, `TRACK_TO_TOPIC`, `_get_catalog_for_track`, the `["sql","python","python-data","pyspark"]` mixed list (**×4 occurrences**), `_public_question_payload`, `_solution_payload`, `_evaluate_submission`, `_pyspark_format_targets`
- `routers/insights.py` — `_TRACK_ORDER`, `_TRACK_CATALOGS`, two label maps, `_CONCEPTS_LOOKUP` builder
- `routers/sample.py` — `_public_question_for_topic`, `_topic_api_slug`, run-code/submit topic branches
- `sample_questions.py` — `_TOPIC_ALIASES`, `_TOPIC_CATALOGS`
- `routers/spa.py` — track references (sitemap/meta — verify and extend)
- `concept_families.py` — `CONCEPT_FAMILIES` per-track keys (mock focus + weak-concept insights)
- `scripts/validate_content.py` — `QUESTION_DIRS`, `_RAW_CONCEPTS_BY_TRACK`, `_HINT_COUNT_RULES`, `_FIRST_HINT_LEAK_PATTERNS`, `_validate_paths` `valid_topics` + role-count enforcement, `catalogs_by_topic`
- `main.py` — router registration

Frontend:
- `contexts/TopicContext.js` — `TRACK_META`
- `catalogContext.js` — `apiPathForTopic` switch
- `pages/QuestionPage.js` — `meta.hasMCQ` / `meta.language` branching
- `SidebarNav.js`, `LandingPage.js`, `TrackHubPage.js`, `MockHub.js`, `MockSession.js`, `ProgressDashboard.js`, `Topbar.js` (Practice dropdown), `LoggedInWelcome.js`, `InsightStrip.js`, `LearningPath.js`, `LearningPathsIndex.js`, `PathProgressCard.js`
- Tests: `*.test.js` that enumerate tracks (LandingPageTiers, MockSession, ProgressDashboard, PathProgressCard)

### Phase A tasks

- [x] **A1.** Create `backend/tracks.py` — a single registry. Each entry:
  `slug`, `db_topic` (== slug per D3), `catalog_module`, `label`, `eval_kind`
  (`"sql"` | `"python"` | `"pandas"` | `"mcq"` | `"mixed"`), `unlock_profile`
  (`"code"` | `"mcq"`), `content_dir`, `id_ranges`, `concept_blocklist`,
  `hint_rules`, `first_hint_leak_patterns`, `in_mixed_mock` (bool, D7).
  Seed with the existing four tracks **exactly reproducing current behavior**
  (PySpark `unlock_profile="mcq"`, others `"code"`; `python-data` keeps its
  legacy `db_topic="python_data"` alias — registry is where that one wart lives,
  nowhere else).
- [x] **A2.** Refactor `unlock.py` to take `unlock_profile` from the registry
  instead of `_is_pyspark`. Behavior must be byte-identical for the 4 tracks.
- [x] **A3.** Refactor `mock.py` to derive `VALID_TRACKS`, topic mapping, catalog
  lookup, mixed-track list (from `in_mixed_mock`), and payload/eval dispatch
  (by `eval_kind`) from the registry.
- [x] **A4.** Refactor `insights.py` and `sample_questions.py`/`routers/sample.py`
  to read the registry.
- [x] **A5.** Refactor `scripts/validate_content.py` to derive `QUESTION_DIRS`,
  concept blocklist, hint rules, leak patterns, `valid_topics`, `catalogs_by_topic`
  from the registry. **Keep** the "exactly one starter + one intermediate path
  per topic" rule — note it becomes a hard ordering constraint (see §3).
- [x] **A6.** Frontend mirror: add `frontend/src/trackRegistry.js` (or extend
  `TRACK_META`) as the single FE source; refactor `catalogContext.js` and the
  enumerating pages/components to read it. `QuestionPage.js` gains a
  `mixedSubtype` branch (no-op for existing tracks).
- [x] **A7.** **Regression gate (mandatory).** Existing 4 tracks are the oracle:
  - Backend: full `pytest tests/ -q` green; `validate_content.py` passes.
  - Frontend: full Vitest suite green; Playwright e2e green.
  - UI preview: manually exercise SQL, Python, Pandas, PySpark — catalog,
    question solve, mock, dashboard, learning path — confirm zero visible change.
- [x] **A8.** Docs: update `docs/architecture.md` (new registry as the track
  source of truth) + `docs/backend.md`. Commit.

**Phase A ships no new track.** Its success criterion is "nothing changed for
users, but adding a track is now a registry entry."

---

## 2. Per-track phases (B, C, D) — sequential, end-to-end each

Each track follows the same skeleton. The roadmap's detailed content-coverage
tables and launch-gate checklists still apply per track — use them. Below is the
*engineering* sequence that prevents rewrites.

### Phase B — Track 1: Data Engineering Concepts (`data-engineering`)

Format: MCQ/scenario/predict-output/debug — identical eval to PySpark.
`unlock_profile="mcq"`, `eval_kind="mcq"`, `in_mixed_mock=false`.

- [ ] **B1. Content scaffold.** `backend/content/data_engineering_questions/`
  with `schemas.json` **created first** (`id_ranges` per §8:
  `51001–51999 / 52001–52999 / 53001–53999`) + `easy.json/medium.json/
  hard.json` (start empty arrays). Loader crashes at startup on any ID outside
  range — schemas.json before questions, always.
- [ ] **B2. Loader.** `backend/data_engineering_questions.py` — copy
  `pyspark_questions.py` verbatim, change paths only. Same `VALID_TYPES`,
  `get_questions_by_difficulty`, `get_mock_questions_by_difficulty`,
  `get_public_question`.
- [ ] **B3. Router.** `backend/routers/data_engineering_questions.py` — copy
  `routers/pyspark_questions.py`, swap catalog import + prefix
  `/api/data-engineering`. Register in `main.py`.
- [ ] **B4. Registry entry** (`tracks.py` + FE registry): slug
  `data-engineering`, label "Data Engineering", color **warm amber** (distinct
  from PySpark `#D94F3D` — pick an unused token-consistent hex), `eval_kind="mcq"`,
  `unlock_profile="mcq"`. This single entry lights up unlock, mock dispatch,
  insights, sample, validator, FE catalog/route/sidebar/trackhub automatically
  (route is automatic — `TopicProvider` accepts any `TRACK_META` key; **no
  `App.js` change needed** — the roadmap's "add route" task is obsolete post-A6).
- [ ] **B5. Validator extension.** Add `data-engineering` concept blocklist,
  hint rules, leak patterns to the registry. **Validator must accept the track
  before any content lands** (it's one script for all tracks).
- [ ] **B6. Sample + mock.** **Do NOT author dedicated sample questions or
  sample IDs** (per §8 — non-SQL tracks have none). `get_topic_sample_pool()`
  auto-serves the first 3 practice questions by `order` per difficulty; just
  confirm `/api/sample/data-engineering/{difficulty}` returns them once the
  catalog has ≥3 questions per difficulty. Mock: generalize
  `_pyspark_format_targets` to any `eval_kind="mcq"` track (or add a generic
  variant) and confirm the track is mock-selectable. Any mock-only questions
  use the top of each difficulty range (no separate numbering — §8).
- [ ] **B7. Content authoring.** Create
  `.github/agents/data-engineering-question-authoring.agent.md`. Author 30
  easy / 30 medium / 20 hard per the roadmap coverage table + format mix.
- [ ] **B8. Learning paths (HARD ORDERING CONSTRAINT).** Because the validator
  enforces "exactly one starter + one intermediate path per registered topic,"
  the two paths (`starter` "Pipeline Fundamentals" free; `intermediate`
  "Advanced DE Systems" pro) **must be authored and committed in the same change
  that registers the track in the validator's topic set.** Add path JSON +
  `content/paths/*.json`, register slugs.
- [ ] **B9. Tests (mandatory, per project testing standard).** Backend: catalog,
  question detail (locked/unlocked), submit (correct/incorrect/locked 403),
  unlock thresholds (mcq profile), sample, mock start/submit/finish for the
  track, paths. Frontend: catalog renders, MCQ solve flow, sidebar switcher,
  trackhub. Add registry-driven cases to existing enumerating tests.
- [ ] **B10. UI preview verification.** Dev server: practice the track end to
  end (catalog → MCQ → submit → next), mock session, learning path, dashboard
  shows the track. Confirm unlock gating (free/pro). Screenshot proof.
- [ ] **B11. Docs in same commit(s).** `CLAUDE.md` (content footprint + track
  list + unlock thresholds), `docs/backend.md` (endpoints), `docs/frontend.md`
  (track meta), `docs/content-authoring.md` (DE concept map + schema),
  `docs/features/mock.md` if mock behavior notes change. Update
  `new-tracks-roadmap.md` status table → `Done` + launch date.
- [ ] **B12. Launch gate.** Run the roadmap's Track-1 launch-gate checklist.
  Commit + push to `main`.

### Phase C — Track 2: Data Modeling (`data-modeling`)

Same skeleton as Phase B (it's the same `eval_kind="mcq"` shape). Differences:

- [ ] IDs `61001/62001/63001`; dir `data_modeling_questions/`; loader
  `data_modeling_questions.py`; router prefix `/api/data-modeling`.
- [ ] Registry entry: label "Data Modeling", distinct color, `eval_kind="mcq"`,
  `unlock_profile="mcq"`, `in_mixed_mock=false`.
- [ ] Target 25 easy / 25 medium / 20 hard per roadmap coverage table
  (~40% pure MCQ / ~60% scenario).
- [ ] Paths: `starter` "Schema Design Basics" (free), `intermediate`
  "Dimensional Modeling Deep Dive" (pro) — same hard ordering constraint as B8.
- [ ] Authoring agent `.github/agents/data-modeling-question-authoring.agent.md`.
- [ ] **Note the future SQL-DDL/DuckDB upgrade path is explicitly OUT of scope**
  (roadmap §Track2). Do not build it. Record as a one-line "future" note only.
- [ ] B9–B12 equivalents (tests, UI preview, docs-in-commit, launch gate).

### Phase D — Track 3: Statistics & Probability (`statistics`)

The only structurally novel track: **dual subtype**. This is the highest-risk
phase — design it explicitly.

- [ ] **D1. Schema.** Question JSON adds `subtype: "conceptual" | "numerical"`.
  - `conceptual`: PySpark-shaped (`options`, `correct_option`, `explanation`).
  - `numerical`: Python-algorithm-shaped (`starter_code`, `expected_code`,
    `test_cases`, optional `function_signature`).
  - Loader `statistics_questions.py` validates **per-subtype** (branch the
    `_validate_question` required-field set on `subtype`). IDs
    `71001/72001/73001`.
- [ ] **D2. Unlock profile = `code`** (roadmap cross-track: numerical questions
  take real effort → Python/Pandas thresholds, not the MCQ table).
- [ ] **D3. Router** `routers/statistics_questions.py`:
  - `GET /api/statistics/catalog`, `GET /api/statistics/questions/{id}`
  - `POST /api/statistics/run-code` → delegate to `python_evaluator.run_python_code`
    (numerical only; 400 for conceptual).
  - `POST /api/statistics/submit` → **route by the stored question's `subtype`**:
    conceptual → option compare (PySpark logic); numerical →
    `python_evaluator.evaluate_python_code` (Python logic). `get_public_question`
    must include `subtype` and, for numerical, the Python fields.
- [ ] **D4. Registry entry**: label "Statistics", distinct color,
  `eval_kind="mixed"`, `unlock_profile="code"`, `mixedSubtype=true` (FE),
  `in_mixed_mock=false`.
- [ ] **D5. Frontend dual-render (the key risk).** In `QuestionPage.js`, when
  `meta.mixedSubtype`, derive effective render flags from the **question
  payload** not meta:
  - `subtype==="conceptual"` → render `MCQPanel`, submit as option (like PySpark).
  - `subtype==="numerical"` → render `CodeEditor` + `TestCasePanel` +
    `PrintOutputPanel`, language `python`, Run enabled (like Python).
  Implement as a single derived `renderMode` memo (`'mcq' | 'code'`) used
  everywhere the file currently reads `meta.hasMCQ`/`meta.language`. Catalog,
  SidebarNav, TrackHub need no subtype awareness (they only list).
- [ ] **D6. Mock dual-subtype.** `_public_question_payload` /
  `_evaluate_submission` / `_solution_payload` for `statistics` must branch on
  the question's `subtype` (registry `eval_kind="mixed"` → look at question).
  Mock submit request already carries both `code` and `selected_option`.
- [ ] **D7. Sample dual-subtype.** `routers/sample.py` submit/run-code branches:
  for `statistics`, dispatch by the sample question's `subtype`.
- [ ] **D8. Validator.** Concept blocklist, hint rules, leak patterns for
  `statistics`. The path role-count rule applies (paths land with track).
  Validator must tolerate both subtypes (don't require `options` on numerical,
  don't require `test_cases` on conceptual).
- [ ] **D9. Content.** Agent
  `.github/agents/statistics-question-authoring.agent.md` (covers both subtypes
  + numerical test-case spec). Author 28 easy (~70/30 MCQ/numerical) / 28 medium
  (~60/40) / 24 hard (~50/50) per roadmap.
- [ ] **D10. Paths.** `starter` "Stats for Analysts" (free), `intermediate`
  "Experimental Design & Inference" (pro). Same ordering constraint.
- [ ] **D11. Tests.** Everything in B9 **plus** explicit subtype-routing tests:
  conceptual submit → option compare; numerical submit → Python evaluator;
  run-code 400 on conceptual; mock with mixed subtypes; FE renders correct panel
  per subtype.
- [ ] **D12. UI preview.** Verify a conceptual question (MCQ) and a numerical
  question (code editor + test results) in the same track, in practice + sample
  + mock. Screenshot both.
- [ ] **D13. Docs in same commit**: `CLAUDE.md`, `docs/backend.md`
  (run-code/submit subtype routing), `docs/frontend.md` (dual-render),
  `docs/content-authoring.md` (dual-subtype schema). Launch gate. Push.

---

## 3. Hard ordering constraints (bug-prevention)

1. **Phase A before B/C/D.** Don't extend hardcoded lists per-track; do the
   registry once. Phase A's regression gate (A7) is non-negotiable.
2. **Within each track: validator topic registration ⇄ both learning paths land
   together.** `validate_content.py` throws for *all* tracks if a registered
   topic lacks exactly one starter + one intermediate path, or if concept/hint
   rules are missing for the track. Sequence inside a track commit:
   loader+`schemas.json`+router+registry+validator-rules+both paths must be a
   coherent set before `validate_content.py` is run in CI. (No sample-question
   authoring step — §8: non-SQL samples are auto-sliced from practice.)
3. **Content authoring after validator accepts the track**, never before.
4. **Sequential tracks (D6 decision):** do not start Phase C until Phase B's
   launch gate is fully checked; likewise C before D.
5. **Phase E (landing) can interleave** after Phase A but must not modify track
   backend behavior.

---

## 4. Phase E — Landing page: full ground-up redesign

A complete rebuild of `LandingPage.js`. **Take nothing from the current page
except the philosophy.** The current page is a track-taxonomy brochure; the new
one is an argument that ends in a product tour. It must feel like a precision
instrument, not a marketing site — clinical, editorial, confident, quietly
premium. It is the first proof of the product's claim: *we are rigorous about
how you think.*

### E.0 Design language (the non-negotiable spine)

**Keep the design *system*, reinvent the *composition*.** Per `CLAUDE.md`,
the App.css token system, font stack, dark mode, and 900px breakpoint *are* the
brand — replacing them would be visual noise and scope creep. "Fresh" means a
new information architecture, visual hierarchy, and motion language built on the
same tokens, not a new palette.

- **Canvas — near-monochrome.** Page is `--bg-page` (#F7F7F5 / dark #141413).
  Surfaces are `--surface-card`. Ink `--text-strong`. The indigo `--accent`
  (#5B6AF0 / dark #7B8AF5) is rationed: it is the *single signal that something
  is alive* — the running cursor, the active role tab, the primary CTA, a result
  cell filling in. Nothing decorative is accent-colored. No gradients, no blobs,
  no glassmorphism. Clinical = restraint.
- **Track identity colors are tags, never fields.** Each of the 7 tracks keeps
  its token color (SQL #5B6AF0, Python #2D9E6B, Pandas #C47F17, PySpark #D94F3D,
  + 3 new — see §E.4) but only as a 6px dot or a 2px left rule. Never as a card
  fill. Seven full-color tiles would be the exact noise we are retiring.
- **Typography encodes the thesis.** Inter for all prose (display sizes,
  `-0.03em` tracking on H1/H2, `1.5` body). **JetBrains Mono for "system"
  chrome**: section indices (`01 / THE THESIS`), eyebrow kickers, metric units,
  track format tags, the IDE. This sans/mono duality *is* "thinking +
  execution" rendered typographically — on-brand and free. Geist Mono stays
  scoped to the showcase animation only (as today).
- **Grid.** 1040px max content wrapper (already the standard). A strict
  editorial grid with generous vertical rhythm (section padding ≥ 120px desktop
  / 72px mobile). Hairline rules (`1px` at ~8% ink) separate sections and list
  rows — the "clinical" texture. No drop shadows except existing radius/shadow
  tokens on genuinely floating elements (IDE, sticky bar).
- **Motion — subtle, earned, interruptible.** Premium = confidence, not
  spectacle.
  - Entrance: opacity 0→1 + translateY 8px→0, 420ms,
    `cubic-bezier(0.2,0.7,0.2,1)`, 60ms stagger, fired once on
    scroll-into-view (IntersectionObserver, `rootMargin -10%`).
  - The **one signature motion**: in the hero IDE a query types itself
    (~28ms/char), the caret blinks, then the result table streams in row-by-row
    (50ms/row, ≤6 rows) with the accent flashing once per row. This single
    moment carries the entire "real execution" claim.
  - Role switch: 220ms crossfade + 4px slide; the active tab's 2px accent
    underline slides, never pops.
  - Hairline link affordance: 1px underline draws left→right on hover (140ms).
  - Proof-strip count-ups: 600ms ease-out, once.
  - **No** parallax, scroll-jacking, autoplay video, or motion that moves text
    the user is reading. The user always owns scroll.
  - `prefers-reduced-motion`: every animation resolves to its final state at
    first paint (extend the existing showcase convention page-wide). Checked,
    not assumed.

### E.1 Section flow (top → bottom)

```
TOPBAR   sticky; transparent → hairline border + surface on scroll
  datathink (mono, lowercase)        Tracks · Mock · Pricing · [Sign in / name]

01  HERO                                                [logged-out: full]
    eyebrow: INTERVIEW PREPARATION, REASONED
    H1:  "Data interviews test how you reason — not what you memorized."
    sub: "Your SQL runs on a real engine. Your Python executes in a live
          sandbox. Seven tracks that make you earn the answer."
    CTAs: [ Start thinking → ]   ( Find your track ↓ )
    right: live mini-IDE — query types itself, result streams in
    (logged-in: collapses to a one-row Resume / Dashboard / Mock strip)

02  THE THESIS — "What data thinking is"
    Three hairline-separated columns, mono indices:
      01 RECOGNITION ≠ REASONING   02 EXECUTION, NOT EXPLANATION
      03 ANSWERS ARE EARNED
    Below: the FULL IDE showcase — real query → real result, then a
    deliberately wrong attempt → close-miss feedback. Shows the guided-lesson
    loop, not just syntax highlighting.

03  THE WRONG WAY / THE RIGHT WAY
    Clinical 2-col diff (no competitor names):
      muted, struck                |  ink, accented
      flash cards → recognition    |  write
      AI answers → you read        |  run
      syntax drills → no reasoning |  compare
                                   |  understand
    Right column steps draw in sequence on scroll-in.

04  YOUR ROLE SHAPES WHICH THINKING MATTERS
    Segmented switcher (mono labels):
      Data Analyst · Data Engineer · Analytics Engineer · Data Scientist
    Selected panel (220ms crossfade): weighted track stack (dot + thin
    emphasis bar), 2–3 real sample questions (click → /sample/...), and the
    matching learning paths (starter free, intermediate pro).
    The ONLY place all 7 tracks surface — by relevance, not as a grid.
    Default: Data Analyst.

05  PROOF STRIP
    Mono numerals, hairline dividers, count-up once:
      7 tracks · 350+ engineered questions · real DuckDB execution ·
      live Python sandbox · mocks withhold solutions
    Retired companies trust line folds in here as one quiet item:
      "questions modeled on Meta, Stripe, Airbnb, Google interviews"

06  THE TRACKS — full index (replaces the 4-tile grid)
    A dense editorial LIST, not tiles. One row per track:
      ● <color dot>  Name      what it trains (1 line)      N q   FORMAT
    Row reveals a hairline + "Enter →" on hover. Scales to 7/10/20 tracks
    with zero layout pressure. New tracks appear automatically from the
    FE registry.

07  PRICING        (hidden for lifetime_elite)
    Free / Pro / Elite. Mono price, Inter outcome lines (outcomes, not
    feature bullets). Elite keeps exactly one qualified line:
      "SQL company filter — Meta, Google, Stripe, Airbnb"

08  CLOSER
    One line restating the philosophy + [ Start thinking → ].
    Footer: minimal, mono, legal/links.
```

### E.2 Logged-in variant

HERO compresses to a returning-user strip (Resume last track · Dashboard ·
Mock · streak). THE THESIS and WRONG/RIGHT collapse to a one-line restatement.
ROLES, the TRACKS index, and PRICING (unless `lifetime_elite`) remain — a
logged-in user still benefits from role-guided navigation into the 7 tracks.

### E.3 Retire explicitly

- 4-tile grid as primary navigation → replaced by §06 index + §04 roles.
- Onboarding tooltip walkthrough → the role switcher *is* the guided entry.
- Standalone companies strip → one quiet line in §05; the only feature-level
  company mention is the single Elite pricing bullet (prior decision stands —
  company tags are SQL-only/Elite-only, never a headline).
- Auto-rotating showcase carousel → replaced by the single deliberate hero-IDE
  motion + the in-context §02 showcase.

### E.4 Build tasks

- [ ] **E1.** New `LandingPage.js` from scratch, one component per section
  (`Hero`, `Thesis`, `WrongRight`, `RoleSelector`, `ProofStrip`,
  `TracksIndex`, `Pricing`, `Closer`). §04 and §06 are data-driven from the FE
  track registry (Phase A6) so all 7 tracks appear without layout edits.
- [ ] **E2.** Role→track weighting config (single object, drives §04):
  - Data Analyst → SQL, Statistics, Python
  - Data Engineer → SQL, Python, PySpark, Data Engineering, Data Modeling
  - Analytics Engineer → SQL, Data Modeling, Python
  - Data Scientist → Python, Statistics, SQL
- [ ] **E3.** Hero mini-IDE + §02 showcase: self-contained typing/stream
  component, reduced-motion aware at first paint, seeded with a real sample
  question's query + result (no lorem).
- [ ] **E4.** Three new track identity colors in the registry, token-consistent
  and distinct from the existing four and each other (proposed: Data
  Engineering amber `#B9762B`, Data Modeling teal-slate `#3F8E8C`, Statistics
  violet `#7A5AF0`) — finalize against dark-mode AA contrast.
- [ ] **E5.** Styles added to `App.css` using existing tokens only; no new
  color tokens; classes namespaced `lp-*`.
- [ ] **E6.** Shared reduced-motion-aware IntersectionObserver entrance hook,
  used by every section.
- [ ] **E7.** A11y: semantic landmarks; role switcher is a real
  `tablist`/`tab`/`tabpanel` with arrow-key nav; focus-visible rings; AA
  contrast in light and dark; motion-safe.
- [ ] **E8.** Tests + UI preview: logged-out and logged-in (returning-user
  strip + `lifetime_elite` no-pricing), role switching, reduced-motion, dark
  mode, ≤900px and ≥1280px. Replace the obsolete `LandingPageTiers.test.js`
  with role/index tests. Screenshot every state.
- [ ] **E9.** Docs in same commit: rewrite `CLAUDE.md` "Landing page structure"
  + landing route notes, and `docs/frontend.md` "LandingPage (`/`)" section, to
  the new IA; note retired components.

### E.5 Sequencing

Phase E depends only on Phase A (FE registry). Land it **after Phase B** so the
role panels and §06 index render against ≥1 real new track; not a hard blocker.
E must not alter any track backend behavior.

---

## 5. Standing requirements applied to every phase

Per `CLAUDE.md` + the user's explicit instruction ("update all the docs
regularly whenever there's significant change"):

- **Docs in the same commit, never deferred.** Every phase lists its doc
  targets; the change is incomplete until those are updated. Mapping:
  registry/architecture → `docs/architecture.md`; endpoints → `docs/backend.md`;
  routes/components/meta → `docs/frontend.md`; question schema/coverage →
  `docs/content-authoring.md`; mock/dashboard behavior → `docs/features/*.md`;
  footprint/tech-stack/track-list/unlock-thresholds → `CLAUDE.md`. Update the
  `new-tracks-roadmap.md` status table as each track moves
  `Not started → In progress → Content authoring → QA → Done`.
- **Testing standard (mandatory after every phase):** comprehensive backend
  `pytest` + frontend Vitest unit + Playwright e2e green, **and** browser UI
  preview verification of every changed surface with screenshot proof. A phase
  is not done until both are satisfied.
- **Git:** work directly on `main` (no branches/worktrees). Commit after each
  meaningful, coherent change with a specific message; co-author line
  `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`. Push only when the
  user asks or the launch-gate step explicitly calls for it.
- **No scope creep:** copy proven patterns (PySpark loader/router, Python
  evaluator) rather than redesigning; do not build the Data-Modeling SQL-DDL
  evaluator (explicitly future/out-of-scope).

---

## 6. Definition of done (delete-the-docs gate)

All true →

- [ ] Phase A registry shipped; 4 existing tracks regression-clean.
- [ ] Data Engineering, Data Modeling, Statistics each pass their roadmap
  launch-gate checklist and are live on production.
- [ ] All new question banks pass `validate_content.py`; both learning paths per
  track published; mock + sample + dashboard + unlock verified per track.
- [ ] Landing redesign (Phase E) shipped; new tracks surface via role panels;
  legacy grid/tooltip/standalone-companies retired.
- [ ] `CLAUDE.md` + all affected `docs/*` reflect final state.
- [ ] **Delete `new-tracks-roadmap.md` and `new-tracks-implementation-plan.md`**
  in a final cleanup commit.

---

## 7. Appendix — Concept taxonomy for the new tracks (authoring spine)

This is the *big-picture* concept map authored **before** any question, so each
track has a coherent learning arc rather than a bag of trivia. It feeds three
places and must be consistent across all of them:

1. `concept_families.py` — each **FAMILY** (uppercase) maps to keyword variants
   so per-question `concepts` strings resolve to a family (mock focus mode +
   weak-concept insights).
2. Per-question `concepts` field — 2–5 **semantic, reasoning-level** tags
   (validator rejects syntax/API-level tags; tags should be drawn from / roll
   up to these families).
3. `docs/content-authoring.md` "Concept coverage by track" — the public map,
   added when each track lands.

**Authoring spread rules (apply per track, consistent with existing tracks):**

- Difficulty = *reasoning complexity*, not obscurity (existing platform rule).
- Every family that appears at Hard must have an Easy or Medium on-ramp where
  the roadmap coverage table marks earlier coverage — no concept debuts cold at
  Hard.
- Easy = one family, one decision. Medium = compose 2 families / introduce a
  tradeoff. Hard = multi-family judgment, ambiguous-by-design scenario with a
  defensible best answer + plausible distractors (mirror the PySpark scenario
  validator: substantive options ≥20 chars, an observation anchor for
  scenarios).
- Concept families are spread roughly evenly within a difficulty (no single
  family >~25% of a difficulty file) so learning-path sequences and mock focus
  pools stay balanced.
- The first hint never names the mechanism (existing leak-pattern rule extends
  to these tracks — register patterns in the validator before authoring).

### 7.1 Data Engineering Concepts — families

`ETL VS ELT` · `IDEMPOTENCY` · `BACKFILL DESIGN` · `ORCHESTRATION`
(DAG modeling, task deps, retries, sensors) · `SCHEDULING & SLAS` (cron vs
event, SLA vs SLO) · `SCHEMA EVOLUTION` (forward/backward compatibility, data
contracts) · `BATCH VS STREAMING` · `WATERMARKING` (event time, late data,
allowed lateness) · `DELIVERY SEMANTICS` (at-least-once / exactly-once / dedup)
· `PARTITIONING & PRUNING` (predicate pushdown, skew) · `STORAGE LAYOUT & FILE
FORMATS` (columnar, compaction, small-files) · `CDC & INGESTION` (log-based
change capture) · `DATA QUALITY` (assertions, anomaly detection) · `LINEAGE &
OBSERVABILITY` (freshness, alerting, metadata) · `SCD OPERATIONS` (SCD applied
in pipelines) · `STORAGE ARCHITECTURE` (lake / warehouse / lakehouse) · `COST
OPTIMIZATION` (compute/storage economics) · `INCIDENT RESPONSE` (root cause,
replay, mitigation).

Arc: Easy → ETL/ELT, idempotency, basic orchestration, partitioning, SCD
basics, storage architecture. Medium → schema evolution, batch/streaming
tradeoffs, watermarking, data quality, cost. Hard → exactly-once,
incident response, observability under failure, multi-system tradeoffs.

### 7.2 Data Modeling — families

`DIMENSIONAL MODELING` (star/snowflake/galaxy) · `NORMALIZATION` (1NF–3NF
reasoning) · `DENORMALIZATION TRADEOFF` · `FACT TABLE DESIGN`
(transaction/periodic/accumulating snapshot) · `GRAIN DEFINITION` ·
`DIMENSION DESIGN` (conformed, role-playing, junk, degenerate) · `SURROGATE
VS NATURAL KEYS` · `SCD STRUCTURE` (types 1/2/3/4 structurally) · `BRIDGE &
MANY-TO-MANY` · `HIERARCHIES` (ragged, recursive) · `PARTITIONING &
CLUSTERING STRATEGY` (modeling-side) · `SCHEMA FROM REQUIREMENTS` (business
scenario → model) · `REFERENTIAL INTEGRITY` (constraint tradeoffs in analytics
stores) · `DBT MODELING` (staging/marts layering, materialization strategy) ·
`DATA VAULT` (hubs/links/satellites — advanced) · `AGGREGATE & SUMMARY DESIGN`
(pre-aggregation, OLAP) · `WIDE VS NARROW` (one-big-table debate) · `STORAGE
ARCHITECTURE TRADEOFFS` (lake/warehouse/lakehouse for modeling).

Arc: Easy → star vs snowflake, normalization, fact/dim basics, surrogate keys.
Medium → grain, SCD structure, bridge tables, dbt layering, schema-from-scenario.
Hard → data vault, referential-integrity tradeoffs, aggregate strategy,
ambiguous business-scenario design.

### 7.3 Statistics & Probability — families (subtype-tagged)

`PROBABILITY RULES` (combinatorics, expectation, conditional) [C] ·
`DISTRIBUTIONS` (normal/binomial/Poisson/uniform) [C] · `DESCRIPTIVE
STATISTICS` (central tendency, dispersion) [C/N] · `SAMPLING & BIAS` [C] ·
`CENTRAL LIMIT THEOREM` [C] · `ESTIMATION` (point/interval, bias–variance
intuition) [C/N] · `CONFIDENCE INTERVALS` [C/N] · `HYPOTHESIS TESTING`
(null/alt, test selection) [C/N] · `P-VALUE & SIGNIFICANCE` (interpretation,
pitfalls) [C] · `ERROR TYPES & POWER` (Type I/II, power) [C/N] · `AB TEST
DESIGN` (sample size, MDE, guardrails) [C/N] · `EXPERIMENT PITFALLS` (peeking,
multiple comparisons, novelty) [C] · `CORRELATION VS CAUSATION` [C] ·
`COVARIANCE & CORRELATION` (computation) [N] · `BAYESIAN REASONING`
(priors/posteriors, conditional) [C/N] · `CONFOUNDING & SIMPSON'S PARADOX` [C]
· `REGRESSION FUNDAMENTALS` (R², residuals, overfitting) [C/N] ·
`NON-PARAMETRIC METHODS` [C].

`[C]` = conceptual (MCQ) leaning · `[N]` = has numerical (Python-evaluated)
variants · `[C/N]` = authored as both subtypes. The `subtype` field is per
question (Phase D); a family can host both.

Arc: Easy → distributions, descriptive stats, sampling, CLT, basic probability,
Type I/II definitions. Medium → confidence intervals, hypothesis testing,
correlation/causation, Bayesian basics, A/B fundamentals (incl. numerical CI /
mean computations). Hard → power & sample-size calculation, experiment pitfalls,
regression diagnostics, non-parametric selection, Simpson's paradox reasoning,
numerical inference end-to-end.

> Numerical-subtype questions reuse the Python algorithm pipeline verbatim
> (`function_signature` + `test_cases` + `starter_code`, evaluated by
> `python_evaluator.py`). Author them like Python questions whose *domain* is
> statistics — deterministic inputs, exact expected outputs (fixed seeds /
> closed-form), no plotting, stdlib + numpy only (confirm against
> `python_guard.py` allow-list during Phase D).

---

## 8. Appendix — Question ID & Numbering Strategy

> **Canonical source:** `docs/content-authoring.md` § "Question ID & Numbering Strategy". That doc is permanent and will not be deleted. This appendix is a convenience copy; if they ever diverge, the permanent doc wins.

The summary below matches the canonical doc exactly. Every phase obeys it.

### 8.1 Scheme: `TXNNN` (5 digits)

```
T   = track digit (1–9)
X   = difficulty digit (1=easy, 2=medium, 3=hard)
NNN = sequence within that difficulty (001–999)
```

Examples: `11005` = SQL easy #5 · `42017` = PySpark medium #17 ·
`53004` = Data Engineering hard #4.

### 8.2 Track assignments

| Track | T | Easy base | Medium base | Hard base |
|---|---|---|---|---|
| SQL | 1 | 11001 | 12001 | 13001 |
| Python | 2 | 21001 | 22001 | 23001 |
| Pandas | 3 | 31001 | 32001 | 33001 |
| PySpark | 4 | 41001 | 42001 | 43001 |
| Data Engineering | 5 | 51001 | 52001 | 53001 |
| Data Modeling | 6 | 61001 | 62001 | 63001 |
| Statistics | 7 | 71001 | 72001 | 73001 |
| (reserved) | 8–9 | — | — | — |

T digits 8–9 are reserved for future tracks. New tracks pick the next unused T.

### 8.3 Practice vs mock-only

Practice and `mock_only: true` questions **share the same `TXNNN` space within
each difficulty file**. Mock-only questions are allocated at the **top of each
difficulty range**, immediately after the last practice question — never
separately numbered. No mock-only questions exist at *easy* for any track (by
design: easy is practice-only). Verified current allocation:

| Track | Easy | Medium (practice · mock) | Hard (practice · mock) |
|---|---|---|---|
| SQL | 11001–11032 (32p) | 12001–12034 (34p) · 12035–12053 (19m) | 13001–13029 (29p) · 13030–13043 (14m) |
| Python | 21001–21030 (30p) | 22001–22029 (29p) · 22030–22037 (8m) | 23001–23024 (24p) · 23025–23036 (12m) |
| Pandas | 31001–31022 (22p) | 32001–32031 (31p) · 32032–32041 (10m) | 33001–33023 (23p) · 33024–33037 (14m) |
| PySpark | 41001–41038 (38p) | 42001–42038 (38p) · 42039–42048 (10m) | 43001–43026 (26p) · 43027–43036 (10m) |

### 8.4 SQL sample IDs (3-digit, SQL only)

SQL samples use compact `TXS` (S=1–3): `111–113` easy, `121–123` medium,
`131–133` hard. Designed never to collide with 5-digit practice IDs.

**Non-SQL tracks have NO separate sample files or sample IDs.**
`get_topic_sample_pool()` in `backend/sample_questions.py` serves samples by
slicing the **first 3 practice questions by `order`** from the live catalog.
→ DE, Data Modeling, Statistics: do not author sample questions; samples are
just the lowest-`order` practice questions, automatically. The roadmap's launch
-gate item "3 sample questions live (1 per difficulty)" is satisfied **by this
auto-slicing** for non-SQL tracks — there is nothing to author and no IDs to
allocate; only verify the endpoint returns 3/difficulty once the catalog fills.

### 8.5 Authoritative runtime source

Each track's `schemas.json` defines valid `id_ranges`; the catalog loader
validates every ID at startup and **crashes on violation**. The JSON files are
the truth; docs reflect them. Locations:
`backend/content/questions/schemas.json`,
`…/python_questions/schemas.json`, `…/python_data_questions/schemas.json`,
`…/pyspark_questions/schemas.json`. **New tracks (DE, DM, Stats) must have
`schemas.json` created before any question is added** (Phase B1/C1/D1).

### 8.6 Ordering vs ID

The `order` field controls **pedagogical sequence** (sidebar order; the slice
samples are drawn from) and is **independent of the ID**. IDs were assigned by
sorting on `order` then numbering sequentially, so today they align — but this
is not guaranteed as questions are inserted mid-sequence.
**Rule: assign IDs by appending to the end of the difficulty range. Never
re-align ID gaps to `order` gaps.** Renumbering is forbidden (it would break
`submissions`, `user_progress`, `follow_up_id`, and path arrays).

### 8.7 Learning path arrays

All 22 path JSON files in `backend/content/paths/` hardcode question IDs (kept
in sync at the TXNNN renumbering). When adding questions, update any path that
references adjacent questions. New tracks' two paths are authored fresh against
the new IDs (Phase B8/C/D10).

### 8.8 No-overlap guarantee

`TXNNN` guarantees zero overlap across tracks/difficulties by construction;
3-digit SQL samples (111–133) never collide with 5-digit IDs. Adding a track is
purely "take the next free T digit."
