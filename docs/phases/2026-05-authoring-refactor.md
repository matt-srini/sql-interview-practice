# Authoring System Refactor — Tracking Doc

> **Delete this file once Phase 3 ships and Interview Loop is live in production.** This is a temporary tracking artifact, not canonical documentation. Source-of-truth for *what was decided* lives in the files this doc points to.

**Started:** 2026-05-21
**Owner:** matt + Claude
**Goal:** Re-found the question authoring system around datathink's philosophy (durable professional reasoning, interview success as consequence), a per-track concept taxonomy with teeth, a mandatory single authoring entry point, and a mock layer that supports atomic follow-up chains and an Elite-only Interview Loop mode.

---

## How to use this doc

If you are a fresh model session picking this up: **read this entire doc first**, then read the linked source-of-truth files. This doc is the onboarding brief; it explains the *why* behind each locked decision. The SoT files contain the canonical *what*.

If you are mid-stream: jump to the **Phase status** section. Active work is marked `[in progress]`.

---

## The datathink philosophy (verbatim — this is the spine)

> We live in an era defined by data. Every transaction, interaction, and decision leaves a digital trace — and the volume of this data is growing faster than our collective ability to make sense of it.
>
> But data, on its own, means nothing. The real work is generating meaning from it — building systems that store it efficiently, retrieve it reliably, model it thoughtfully, and ultimately transform raw signal into insight that drives better decisions, better products, and better outcomes for people.
>
> This work gave rise to an entire class of technical professions: data engineers who design the pipelines, analysts who surface the patterns, scientists who build the models, and architects who ensure the systems scale. These are not peripheral roles — they are increasingly the backbone of how modern organizations function and grow.
>
> Datathink exists for these professionals — and for those becoming them.
>
> Not as another platform of interview puzzles to crack before a hiring deadline, but as a place to develop the kind of reasoning that makes someone genuinely effective in a data-driven world. The kind of professional who doesn't just write a correct query, but understands why the data is structured the way it is, what question is really worth asking, and how the answer should inform a decision.
>
> If that preparation also makes you exceptional in interviews — and it will — that's a consequence, not the goal.

### The one test every question must pass

Primary:
> *Does this question build the kind of reasoning a practicing data professional would still rely on years into the role?*

Secondary (grounding):
> *And would the same reasoning earn the offer in a real interview screen?*

The old "Would a senior data interviewer at Meta/Google/Stripe/Amazon ask this in a 45-min screen?" test is **retired** as the primary frame. It becomes the secondary grounding test only.

---

## Why this refactor exists (the diagnosis)

The platform accumulated four overlapping sources of truth for question authoring:

1. A universal authoring agent (`.github/agents/question-authoring.agent.md`)
2. Nine per-track authoring agents (`.github/agents/<track>-question-authoring.agent.md`) — 40% overlap with universal
3. `docs/content-authoring.md` (988 lines with per-track encyclopedia)
4. `docs/concept-hooks.md` (1,048 lines, Socratic but not enforced) + hardcoded `backend/concept_families.py`

Result: drift, ad-hoc authoring decisions ("is this practice or mock?"), inconsistent concept tagging, no enforceable contract between content and the mock/insights surfaces that consume it. Concept tags in SQL drifted toward implementation primitives (`JOIN`, `WINDOW FUNCTION`); the family-mapping was a substring hack in Python code, not a registered taxonomy.

This refactor consolidates to:
- **One universal agent** (the procedure)
- **Per-track knowledge docs** at `docs/tracks/<track>.md` (the track-specific philosophy + content)
- **One canonical concept taxonomy** at `docs/concept-taxonomy.md` (the registry, per-track families, no cross-track namespace)
- **One mandatory authoring rule** — never edit a question without the agent
- **One canonical mock SoT** at `docs/features/mock.md` (plan-tier matrix, chain atomicity, Interview Loop contract)

---

## Locked decisions (do not relitigate without a new design conversation)

### Philosophy
- Platform North Star is **professional reasoning development**. Interview success is the consequence, not the goal.
- The verbatim philosophy text above is canonical and lives in `docs/specs/platform-north-star.md`.
- "FAANG-level interview prep" language is being scrubbed. Every doc, every agent file, every UI copy block.
- New primary test (above) replaces the old FAANG-screen test.

### Authoring architecture
- **One universal agent:** `.github/agents/question-authoring.agent.md` owns procedure + cross-track contract.
- **Per-track knowledge in `docs/tracks/<track>.md`** (one file per track, 9 total). Owns: modality, datasets/schema essentials, ID range, difficulty vocabulary, concept arc, anti-patterns, authoring allocation matrix.
- **Per-track agent files DELETED** — 9 files removed in Phase 1 commit C.
- **`docs/concept-taxonomy.md` is the canonical concept-family registry.** Per-track families only (no cross-track namespace — decision rationale below).
- **`docs/content-authoring.md` slims** to the platform-level cross-track contract. Per-track encyclopedic content migrates to the track docs.
- **Mandatory-agent rule** lives in CLAUDE.md, content-authoring.md, and every track doc with identical wording. No question is authored or modified without invoking the agent. This rule has no exceptions.

### Concept taxonomy
- **One `concepts` field on each question.** Families derived via the taxonomy registry (substring/exact match documented per family).
- **Per-track families only, no cross-track family namespace.** Cross-track aggregation is a Phase 3 dashboard lens, not a taxonomy constraint. Forcing alignment muddies authoring; "METRIC INTERPRETATION in SQL" is genuinely different from "in Stats" and faking the unification dilutes signal.
- **Family blocklists per track** — mechanic-name tags forbidden where they obscure reasoning (e.g., `JOIN`, `GROUP BY` in SQL).
- **New tags require PR to taxonomy doc first.** No drive-by additions. The taxonomy is the discipline.
- **Authoring breadcrumb** — author writes a free-form `concepts` tag; tag must map to exactly one registered family. Family is what users see in concept pills; tag is the authoring detail.

### Mock contract
Single canonical SoT: **`docs/features/mock.md`**. Decisions summarised here so this tracker is self-contained:

**Three modes:** `benchmark`, `short_drill` (30 min / 2 Q), `custom_drill` (10–90 min / 1–5 Q). Long-form drill (`60min` / 3 Q) is retired — `custom_drill` covers that range. Legacy `60min` sessions in history are read-only.

**Plan-gated mock pool sourcing:**
- **Free** → practice pool only (no mock-only, no chains). 1 benchmark per rolling 7 days + unlimited easy `short_drill`.
- **Pro** → practice + mock-only. Chains eligible. Combined 3 drills/day cap (`short_drill` medium/hard + `custom_drill`); easy `short_drill` unlimited; 3 benchmarks/day.
- **Elite** → all Pro features + `focus_concepts` + Interview Loop + deep analytics + debrief. UI says "Unlimited"; backend soft rate-limit ~10/hr for abuse defense only.

**Chain atomicity (locked):** parent question + all `follow_ups[]` travel together; consumed once per user globally; zero or all. Marked consumed at session start; 2-min reclaim window via `DELETE /api/mock/:id`; pool exhaustion returns hard 409 with switch-tracks copy.

**Chain authoring rules:**
- Length 2–4 (parent + 1–3 follow-ups).
- Each follow-up uses a different `follow_up_dimension` than the previous. No two consecutive scale pivots.
- No nested chains (child has no `follow_ups[]`).
- No shared children across parents.
- Chain shares track, same or escalating difficulty.

**Follow-up dimension taxonomy (7 universal):**
`scale_pivot` · `business_rule_pivot` · `data_quality_pivot` · `edge_case_pivot` · `performance_pivot` · `ambiguity_pivot` · `stakeholder_pivot`. Definitions and cross-track examples in mock.md.

**Interview Loop mode (Elite only):**
- Chain-driven only — parents with `follow_ups[]` length ≥2 required.
- Session = 1–3 chains; 15 min per chain default.
- All benchmark invariants apply (no mid-session reveal).
- New analytics dimension: per-dimension weak-spot detection ("strong on scale pivots, weak on ambiguity pivots").

### Why 1 benchmark/week (rolling) for Free?
- Free users need to *experience* the benchmark loop, not just hear about it. Otherwise the upgrade pitch lands flat — they cannot picture what they would buy.
- Calendar week (Monday reset) creates spike load + "wasted Sunday" frustration. Rolling 7 days is smoother UX and aligns with how users actually consume.
- Single benchmark is the conversion moment: "I want another, I should upgrade."
- Easy `short_drill` unlimited covers the daily habit hook. Bounded scope, not throttled scope.

### Why no daily counter on Free medium?
- Daily-cap throttling reads as mobile-game energy. Off-brand for a serious professional tool.
- "1 medium/day" gave free users a misleading product experience (medium without surrounding context isn't a benchmark, isn't practice — it's a teaser).
- Medium in the new model lives where it belongs: inside the weekly benchmark, alongside easy and hard difficulties in a blueprint.

### Why combined 3 drills/day for Pro (not 2+2)?
- 2+2 = 4 total, exceeds the implicit 3-cap intent.
- Two counters force the user to mentally track each.
- Combined-3 lets the user choose their cadence and matches metered-SaaS conventions (Notion blocks, Linear actions).

### Why 6 sessions/day for Pro is acceptable (3+3)?
- Cap exists for content economics + Elite differentiation, not friction.
- Pro paying for unlimited would feel premium; capped-at-6 means Elite still wins clearly (unlimited + focus + Loop + deeper analytics).
- 6/day matches peak prep cadence (week-of-interview); steady-state Pro use is 1–3/day, well under cap.
- True throttle ends up being chain availability anyway (see Phase 2 sizing math).

### Why session-start (not first-submit) as chain consumption trigger?
- Considered: consume at first submit (allows users to read all questions and never submit, infinite re-rolls)
- Considered: consume at finish (same abuse vector)
- Chosen: consume at start, 2-min reclaim as safety valve
- 2-min window: short enough to prevent peek-and-bail, long enough for "wrong track" recovery

### Why per-track families, not cross-track?
- The dream of "you're weak on metric interpretation across SQL *and* Experimentation" is a *Phase 3 dashboard lens*, not a *taxonomy constraint*.
- Forcing concept-family alignment between tracks creates fake equivalences ("METRIC INTERPRETATION" means different things in SQL vs Stats vs Exp). Same name, different mental model.
- Cleaner: each track owns its families; a separate dashboard lens *maps* family signals to a shared view later if it earns its place.

---

## Files touched / to be touched

### Phase 0 — Cleanup [completed 2026-05-21, commit `4125102`]

**Deleted (12 files, ~2,610 lines):**
- `docs/mock-modality-rollout-plan.md`
- `docs/concept-expansion-plan.md`
- `docs/phases/mock-modality-phase-0-{backend,content,frontend}-audit.md`
- `docs/phases/mock-modality-phase-0-review.md`
- `.github/agents/mock-modality-orchestrator.agent.md`
- `.github/agents/mock-{backend,content,frontend}-codex.agent.md`
- `.github/prompts/{kickoff-modality-phase,review-codex-phase-output}.prompt.md`

**Edited:**
- `docs/specs/platform-north-star.md` — governance-source bullets rewritten

**Created:**
- `docs/phases/2026-05-authoring-refactor.md` — this doc

### Pre-Phase 1 — Decision lock [in progress, commit pending]

**Edited:**
- `CLAUDE.md` — pushback rule added, doc-sync mapping expanded to comprehensive table, mandatory-agent rule added prominently, plan-tier section rewritten with mock.md as SoT
- `docs/features/mock.md` — becomes canonical plan-tier matrix SoT; full plan-tier matrix with rationale; chain atomicity section; Interview Loop spec section; 2-min discard window UX requirements; cross-link header
- `docs/phases/2026-05-authoring-refactor.md` — this enrichment

**To edit before commit:**
- `docs/features/pricing.md` — point at mock.md for mock-feature gating; do not restate
- `docs/specs/platform-north-star.md` — already pointed at mock.md indirectly via governance sources; verify cross-link is explicit

### Phase 1 commit A — Foundation specs [pending, blocked on decision lock]

**Create:**
- `docs/concept-taxonomy.md` — 9 per-track family registries + 7-dimension follow-up taxonomy

**Edit:**
- `docs/specs/mock-benchmark-spec.md` — extend with chain atomicity contract (linking mock.md as SoT), Interview Loop mode contract, `follow_ups[]` schema, plan-gated pool sourcing reference

### Phase 1 commit B — Track docs [pending]

**Create 9 files:**
- `docs/tracks/sql.md`
- `docs/tracks/python.md`
- `docs/tracks/pandas.md`
- `docs/tracks/pyspark.md`
- `docs/tracks/data-engineering.md`
- `docs/tracks/data-modeling.md`
- `docs/tracks/statistics.md`
- `docs/tracks/ml-fundamentals.md`
- `docs/tracks/experimentation.md`

**Each track doc structure (canonical template):**
1. Track philosophy — datathink philosophy applied to the track ("what does effective reasoning look like for a {data analyst, engineer, scientist} working in {track}?")
2. Mandatory-agent rule reminder
3. Modality (executable / code-adjacent / constructed / hybrid — link to `practice-modality-spec.md`)
4. Datasets / schema essentials (or: "MCQ, no execution")
5. ID range (TXNNN scheme)
6. Difficulty vocabulary (where complexity comes from at easy/medium/hard for this track)
7. Concept arc (early → late progression)
8. Concept families for this track (link to `docs/concept-taxonomy.md`)
9. Authoring allocation matrix:
   - Practice (free tier on-ramp): what shapes, what concept families
   - Practice (path-shortcut unlocks): what advanced families
   - Mock-only (Pro): what shapes, what follow-up dimensions are common
   - Mock-only (Elite via Loop): what kinds of chains
10. Anti-patterns specific to this track
11. Track-specific JSON schema (what fields, how, with example)
12. Verification commands for this track

### Phase 1 commit C — Universal agent + cross-cutting [pending]

**Edit:**
- `.github/agents/question-authoring.agent.md` — strip per-track schema (lives in track docs now), add philosophy verbatim, new primary test, follow-up dimension taxonomy reference, taxonomy linkage, mandatory-agent self-reference, scrub FAANG language
- `docs/content-authoring.md` — slim to cross-track contract only; per-track sections migrated to track docs; philosophy intro replaced; mandatory-agent rule prominent
- `docs/specs/platform-north-star.md` — philosophy verbatim, FAANG language fully scrubbed

**Delete:**
- `.github/agents/sql-question-authoring.agent.md`
- `.github/agents/python-question-authoring.agent.md`
- `.github/agents/pandas-question-authoring.agent.md`
- `.github/agents/pyspark-question-authoring.agent.md`
- `.github/agents/data-engineering-question-authoring.agent.md`
- `.github/agents/data-modeling-question-authoring.agent.md`
- `.github/agents/statistics-question-authoring.agent.md`
- `.github/agents/ml-fundamentals-question-authoring.agent.md`
- `.github/agents/experimentation-question-authoring.agent.md`

### Phase 1.5 — Frontend copy sweep [pending, after Phase 1 docs]

**Audit and edit (estimated 6–10 files):**
- `frontend/src/pages/LandingPage.js` — hero, sections, role selector, tracks index — replace FAANG framing with philosophy
- `frontend/src/components/Topbar.js` — tagline if any
- `frontend/src/pages/AuthPage.js` — copy alignment
- `frontend/src/pages/MockHub.js` — plan-tier surface (counter chips, upgrade nudges) per mock.md
- `frontend/src/pages/MockSession.js` — discard countdown UX, chain banner per mock.md
- `frontend/src/pages/ProgressDashboard.js` — intro copy
- Pricing-related views — link to philosophy + mock.md plan-tier matrix
- Empty states across surfaces

### Phase 1 followup — Color review [pending]

After Phase 1 docs are committed, spin up dev preview, screenshot landing/workspace/dashboard/mock surfaces, evaluate whether `--bg-page` (#F5F7F4) should pull closer to white (#FAFBFA / #F8FAF8). Deliver written recommendation with screenshots; no token change yet.

### Phase 2 — Content alignment [pending, depends on Phase 1]

- Remap existing 993 question `concepts` arrays to new per-track families (~80% automatable, edge cases need human review)
- Author new mock-only content with `follow_up_dimension` + `follow_ups[]` — target 3-month Pro runway (~180 questions/track from current 8–38)
- Refactor `backend/concept_families.py` to load from `docs/concept-taxonomy.md` (or compile at build time)
- Add catalog-load validations to `validate_content.py`: chain integrity, dimension diversity, no orphans, no shared children, length bounds
- Add CI check flagging question file edits without agent invocation marker

### Phase 3 — Interview Loop full stack [pending, depends on Phase 2 content]

- DB: `mock_chain_consumption` table + Alembic migration
- Backend: chain-aware selection (filter consumed parents + their children), Interview Loop endpoint, plan gating, soft rate-limit for Elite "unlimited"
- Frontend: Interview Loop card in MockHub, Loop session UI (interviewer-pivot framing card between chain questions), prominent 2-min discard countdown chip
- Analytics: dimension-level weak-spot insight in dashboard
- UI surface of plan-tier matrix (counter chips on MockHub, upgrade modals)

---

## Phase status

### Phase 0 — Cleanup ✅ completed 2026-05-21
- [x] Delete 6 stale planning docs
- [x] Delete 6 obsolete agent/prompt files
- [x] Update governance-source references in north-star.md
- [x] Create this tracking doc

### Pre-Phase 1 — Decision lock ✅ completed 2026-05-21
- [x] CLAUDE.md: pushback rule, doc-sync mapping, mandatory-agent rule
- [x] CLAUDE.md: plan-tier section pointing at mock.md
- [x] mock.md: canonical plan-tier matrix
- [x] mock.md: chain atomicity section
- [x] mock.md: Interview Loop spec section
- [x] mock.md: 2-min discard UX requirements
- [x] mock.md: discard + chain-reclaim don't count against quota (explicit section)
- [x] mock.md: Elite anti-abuse 3-layer cap detailed (30 s + 5/hr + 20/day)
- [x] mock.md: 6/day Pro rationale (role-coverage floor for 4–5 tracks)
- [x] tracker doc: heavy enrichment + full decision log (16 entries)
- [x] pricing.md: cross-link to mock.md as SoT
- [x] north-star.md: philosophy verbatim + explicit mock.md cross-link
- [x] commit 0888b1a + amendment commit

### Phase 1 commit A — Foundation specs ✅ completed 2026-05-21 (commit `b1ddc6b`)
- [x] `docs/concept-taxonomy.md` created — 920 lines, 9 per-track family registries + 7-dimension follow-up taxonomy
- [x] `docs/specs/mock-benchmark-spec.md` extended with chain atomicity contract, Interview Loop spec, plan-gated pool sourcing reference

### Phase 1 commit B — Track docs ✅ completed 2026-05-21 (3 commits: `2396da7`, `bb66d11`, `ad0f4f6`)
- [x] B-i: `docs/tracks/{sql,python,pandas}.md` (executable tracks)
- [x] B-ii: `docs/tracks/{pyspark,statistics}.md` (code-adjacent + hybrid)
- [x] B-iii: `docs/tracks/{data-engineering,data-modeling,ml-fundamentals,experimentation}.md` (constructed reasoning)

### Phase 1 commit C — Universal agent + cross-cutting ✅ completed 2026-05-21 (commit `c1ef9f4`)
- [x] `.github/agents/question-authoring.agent.md` refined (philosophy verbatim, new primary test, taxonomy linkage, mandatory-agent rule, per-track schema stripped)
- [x] `docs/content-authoring.md` slimmed from 988 → 313 lines
- [x] `docs/specs/platform-north-star.md` updated with philosophy verbatim + mock.md cross-link (in earlier commit `0888b1a`)
- [x] CLAUDE.md plan-tier section updated to point at mock.md as SoT
- [x] 9 per-track agent files deleted
- [x] README.md and `.github/agents/track-onboarding.agent.md` updated to remove stale references

### Phase 1.5 — Frontend copy sweep ✅ completed 2026-05-21 (commit `fd1c1ca`)
- [x] Landing hero (eyebrow / H1 / sub) reframed to philosophy
- [x] Pricing cards rewritten for new plan-tier matrix (Free benchmark-only weekly + unlimited easy short_drill; Pro 3+3 cap; Elite + Interview Loop + per-dimension weak-spots)
- [x] MockHub Elite features panel updated (Interview Loop, per-dimension weak-spots)
- [x] FAQ "What are mocks" rewritten with 3 modes; Pro/Elite distinction updated
- [x] Auth and landing meta descriptions reframed
- [x] Surgical sweep — preserved "interview" language where it legitimately describes mock features

### Phase 1 followup — Color review ✅ completed 2026-05-21 (commit `03e5881`)
- [x] Eyes-on review of `--bg-page: #F5F7F4` on live dev server (hero + pricing surfaces)
- [x] Computed-color verification via getComputedStyle (not just screenshots)
- [x] Written memo at `docs/phases/2026-05-color-review.md` — recommend KEEP, no token change
- [x] Two adjacent observations flagged for future separate pass (workspace topbar; Pro 8% accent already correct)

### Phase 2 — Content alignment ⏸ pending (Sonnet picks up from here)
This is the first phase a fresh Sonnet session should be able to execute end-to-end from the committed docs alone. Read this file for the full brief.

**Suggested execution order** (each item unblocks or de-risks the next):

1. **Refactor `backend/concept_families.py` to load from `docs/concept-taxonomy.md`** — do this first so the remap (item 2) and the validation (item 4) both consume the same registry. Eliminates the hand-mirrored Python dict and makes the taxonomy doc the runtime source of truth. Catalog loader, mock focus mode, and dashboard insights all benefit immediately.
2. **Remap existing 993 question `concepts` arrays** to new per-track families. Tooling: write a script that reads `docs/concept-taxonomy.md`, applies the resolution algorithm (exact → substring → blocklist → fail), and proposes replacements. ~80% automatable; the other ~20% needs disciplined judgement (see risk section below).
   - **⚡ gap-family grounding (do as part of this remap).** The `⚡ real-world gap` families **have zero coverage today — verified 2026-05-22 across practice AND mock.** They split into two classes (see the cross-track decision below and the SQL execution brief): **practice-grounded** (must be taught in practice — grounded here via remap re-tag + small authoring) and **mock-only realism** (assessment lenses, never in practice, exempt from grounding). The remap is the moment to establish the *practice-grounded* ones: re-tag existing practice questions whose reasoning already fits (e.g. dirty-data/conflicting-evidence questions → DATA QUALITY SKEPTICISM; reconciliation questions → METRIC RECONCILIATION). Where none fits, author through the agent (e.g. fan-out → DOUBLE-COUNTING DETECTION needs new `debug` questions). **Grounding the practice-grounded ⚡ families is a hard prerequisite for item 4.** Per-track ⚡ class assignments are in each track's execution brief; SQL is fully specified below.
   - **Doc correction owed.** The ⚡ callout in [`docs/concept-taxonomy.md`](../concept-taxonomy.md) and the per-track ⚡ caveats in the track docs currently say *all* ⚡ families are "practice-curriculum targets." That over-generalises — refine them to distinguish practice-grounded ⚡ families from mock-only realism families (this is a Phase 2 doc step, do it when you touch the taxonomy).
3. **Add catalog-load validations to `validate_content.py`**: chain integrity (parent ↔ child back-refs, no nested chains, no shared children, length 2–4, dimension diversity in consecutive follow-ups), tag-resolution per the taxonomy, blocklist enforcement. Crash on violation.
4. **Author new mock-only content** with `follow_up_dimension` + `follow_ups[]` — target 3-month Pro runway (~180 questions per track from current 8–38). **Always via the universal authoring agent** following the operational steps in CLAUDE.md. **Mock-only basis (locked 2026-05-22):** mock-only never introduces a concept the practice curriculum hasn't already taught at that difficulty or lower — it *recombines* learned concepts under fresh, production-realistic framing (mild ambiguity, evolving requirements, edge cases, dirty data). The differentiator is framing/realism, not concept novelty. The old "≤15% concept reuse / 85% fresh families" cap is **retired**; the new rule is "no unseen concepts + no framing clones of practice questions." See [`docs/content-authoring.md` → What separates practice from mock-only](../content-authoring.md#what-separates-practice-from-mock-only). This means item 4 *depends on the practice bank being complete first* for any track you author mock content for.
5. **Add CI check flagging question-file edits without agent invocation marker** — long-tail discipline; doesn't block Phase 3.

### Phase 2 risk and discipline (read before starting)

**The 993-question concept-tag remap is mostly mechanical, but the ~20% edge cases require real judgement.** Common edge-case shapes Sonnet will encounter:

- **Multi-meaning tags** — e.g. an existing SQL tag like `DATA QUALITY CLASSIFICATION` could map to `DATA QUALITY SKEPTICISM` (if the question is about detecting bad data) OR to `CONDITIONAL LOGIC & CASE` (if the question is about classifying rows with rules). Same tag string, different intent depending on the question. Read the question, not just the tag.
- **Blocklisted tags with non-obvious replacements** — e.g. a SQL question tagged `OR` (currently 3 occurrences) is a blocklisted boolean-operator tag, but the question itself might genuinely be about `PRE-AGGREGATION FILTERING` or `SET MEMBERSHIP FILTERING` depending on context.
- **Tags that resolve to two near-identical families** — e.g. `RUNNING TOTAL THRESHOLD DETECTION` could resolve to `RUNNING TOTAL & MOVING WINDOW` (the calculation) or `PERFORMANCE-AWARE ANALYTICS` (if the question is about cost). Pick by question intent.
- **Singleton tags that look bespoke** — many existing tags appear once and look like an author's free-form choice (e.g. `USER-PRODUCT JOURNEY MODELING`). Don't preserve these for sentimental reasons; map them to the closest registered family.
- **Pandas-track renames** — existing `TOP-K RESULT EXTRACTION` resolves to the renamed `RANKING & TOP-N PER GROUP` family via the preserved `TOP-K` match pattern. **Don't rewrite the tag string**; the family-name update is enough.

**Discipline rules for the remap:**

1. **Never auto-apply edge-case decisions in bulk.** Surface them in a manifest for human review, or re-author the question through the agent so the full checklist runs.
2. **Read the question, not just the tag.** A tag's meaning is downstream of the question's actual reasoning.
3. **Never edit a question file by hand.** If a remap needs more than a `concepts` array rewrite (e.g. the question itself is incoherent with its tags), invoke the authoring agent for that question instead of patching.
4. **Commit in batches of one track at a time.** SQL first, validate, commit, then Python, then Pandas, etc. Atomic rollback if a track-level batch turns out to have systemic remap errors.
5. **Run the catalog loader after each batch.** A successful load is the signal the remap is internally consistent. A crash is the signal something is wrong — fix before continuing.
6. **The mock content authoring (item 4) is the longest stretch of Phase 2.** Estimate: 9 tracks × ~170 new questions × ~10 min each through the agent = ~250 hours of focused work. This is not a one-session task. Pace accordingly; commit after each authoring session.

### Cross-track decision: mock-only realism families (locked 2026-05-22)

Some `⚡` families are not curriculum *concepts* — they are assessment *lenses* layered over a concept the learner already knows. They are designated **mock-only realism families**, marked `mock_only: true` in the taxonomy registry, and governed by these rules:

- A mock-only realism family **may appear only in mock content**, never in practice.
- It **may never be a question's sole concept tag** — it must co-occur with ≥1 practice-grounded family. (That underlying concept is always practice-taught, so the no-unseen-concepts rule is never violated — the lens adds *framing/assessment*, not a new concept.)
- It is **exempt from the practice-grounding prerequisite** (precisely because it is not a new curriculum concept).

The validator (item 3) must enforce the `mock_only` flag and the co-tag rule. This class applies across tracks; per-track assignment of which ⚡ families are realism vs practice-grounded lives in each track's execution brief.

### SQL Phase 2 execution brief (locked 2026-05-22) — self-contained for a fresh Sonnet session

This is the complete, decided plan for the SQL track. Execute it in this order; do not relitigate.

**1. ⚡ family classification (SQL):**

| Family | Class | How it gets grounded |
|---|---|---|
| DATA QUALITY SKEPTICISM | practice-grounded | **Remap re-tag** of existing hard questions: `Q13019` (NOISY DATA RESOLUTION), `Q13023` (CONTRADICTION DETECTION + MISSING-EVIDENCE), candidate `Q13026` (conflicting attribution). +1–2 new medium `debug` if a teaching gap remains. |
| DOUBLE-COUNTING DETECTION | practice-grounded | **New authoring only** — no existing question fits. ~3–4 `debug` questions on join fan-out (orders→order_items revenue ×line-count; orders→payments retry inflation). Medium + hard. |
| METRIC RECONCILIATION | practice-grounded | **Remap re-tag** `Q12032` (order-payment reconciliation, currently `DATA QUALITY CLASSIFICATION` + `FULL OUTER JOIN RECONCILIATION`). +1–2 new if needed. |
| METRIC INTERPRETATION & DENOMINATOR CHOICE | **mock-only realism** | never practice; co-tag with the underlying concept (e.g. GROUPED AGGREGATION). |
| OUTPUT SANITY VALIDATION | **mock-only realism** | never practice; realized as `debug`/`scenario` mock questions. |
| PERFORMANCE-AWARE ANALYTICS | **mock-only realism** | never practice; realized as `debug`/`scenario`/`reverse` mock questions. |

**2. Remap (SQL) — residuals ≈ 0. Verified 2026-05-22.** 124 unresolved tag incidences (105 distinct) resolve as:
   - **Strip type-markers from `concepts`:** `REVERSE SQL` (8), `DEBUG SQL` (6) — the `type` field already encodes these. *(via agent)*
   - **Expand taxonomy match-patterns (~80 incidences, NO question-file edits):** add patterns so legit synonyms resolve — e.g. `ROLLUP SUBTOTALS`/`GROUPING SETS`/`ARRAY_AGG`/`MULTI-DIMENSIONAL SUMMARY` → GROUPED AGGREGATION; `PERCENTILE_CONT`/`PERCENTILE FUNCTION`/`QUALIFY` → WINDOW FUNCTIONS or RANKING & TOP-N; `GENERATE_SERIES`/`SEQUENCE GENERATION`/`AT TIME ZONE`/`INTERVAL ADDITION`/`TENURE CALCULATION` → TIME-SERIES BUCKETING & ARITHMETIC; `LATERAL JOIN` → SUBQUERY PATTERNS; `SET CONSOLIDATION`/`JOIN EQUIVALENCE` → SET OPERATIONS & COMPARISON; the `<domain> ANALYSIS` family of tags (`HR ANALYTICS`, `SPEND ANALYSIS`, `GEO REVENUE ANALYSIS`, …) → GROUPED AGGREGATION (or, where it's a ratio like `FAILURE RATE`/`REVENUE SHARE`, the realism family METRIC INTERPRETATION **only in mock**; in practice keep GROUPED AGGREGATION).
   - **Re-tag into practice-grounded ⚡ families (~5, via agent):** the DATA QUALITY / RECONCILIATION questions listed in step 1.
   - **Blocklist fix:** `OR` (3) → PRE-AGGREGATION FILTERING.
   - **True residuals: none.** Do not force-fit; if a future tag genuinely has no home, surface it for human review rather than guessing.

**3. De-noise foundational families (SQL) — Finding 5.** Tag by the *distinguishing* technique, not incidental mechanics (matches StrataScratch / DataLemur / LeetCode SQL convention):
   - Strip `DETERMINISTIC RESULT ORDERING` and `COLUMN PROJECTION` everywhere they're incidental; keep RESULT SHAPING & ORDERING **only** where shaping/ordering is the primary skill (ORDER BY semantics, NULLS LAST, deterministic tie-breaking, cross-tab). Expected: RESULT SHAPING ~40 → ~10–12 incidences, legitimately easy-heavy.
   - Drop GROUPED AGGREGATION on the ~12 medium/hard questions where a higher-order family is the real technique (window/ranking/running-total/sessionization/CTE) — e.g. `Q13001` (revenue share → WINDOW), `Q13034` (cumulative → RUNNING TOTAL), `Q13027` (session score → SESSIONIZATION + CTE). Keep it where group-by genuinely *is* the reasoning.
   - All re-tagging goes through the authoring agent (never hand-edit `concepts`).

**4. Mock-only formats (SQL) — locked addition 2026-05-22.** Mock-only SQL content is **not limited to query-writing.** `debug`, `reverse`, and `scenario` reasoning questions are first-class mock-only types — they simulate real interview dynamics (read a broken query, infer intent from output, reason about a business situation) and are the natural home for the realism families (sanity / performance / metric-interpretation) that don't grade cleanly as query-writing.

**5. SQL sizing (locked):**
   - **Practice: 112 → ~118–122.** Net new authoring only ~6–10: ~3–4 DOUBLE-COUNTING `debug`, ~1–2 DATA QUALITY top-up, ~1–2 METRIC RECONCILIATION. Everything else is remap/de-noise (no new questions). Thin arcs (cohort/funnel/running-total at 3 each) — **leave as-is**; do not pad for volume.
   - **Mock-only: 38 → ~150.** Medium+hard only, hard-skewed (~60/40), ~⅓ chain members. **Top priority = the join/fan-out/double-counting blind spot** (mock has 0 MULTI-TABLE ENTITY LINKING and 0 DOUBLE-COUNTING today). MULTI-TABLE is already practice-taught (34) so multi-table mock can start immediately; double-counting mock follows once practice grounds it. Then fill core advanced families (WINDOW, RANKING, COHORT, FUNNEL, SESSIONIZATION, CTE) and the 3 realism lenses. Natural chains: correct multi-table KPI → `data_quality_pivot` (duplicate payments) → `business_rule_pivot` (exclude refunds).

**6. Doc nit:** `docs/tracks/sql.md` says "25 canonical families"; the registry has **26**. Fix the count when you touch the file.

### Phase 3 — Interview Loop full stack ⏸ pending (depends on Phase 2 content)

**Phase 3 — Interview Loop full stack** ⏸ pending (depends on Phase 2 content)
- [ ] DB: `mock_chain_consumption` table + Alembic migration (schema is fully specified in `docs/specs/mock-benchmark-spec.md`)
- [ ] Backend: chain-aware selection (filter consumed parents + their children), Interview Loop endpoint, plan gating, soft rate-limit for Elite (30s gap + 5/hr + 20/day)
- [ ] Frontend: Interview Loop card in MockHub, Loop session UI (interviewer-pivot framing card between chain questions), prominent 2-min discard countdown chip
- [ ] Analytics: `loop_summary` payload in `/api/mock/analytics` Elite response; dimension-level weak-spot insight in dashboard
- [ ] UI surface of plan-tier matrix (counter chips on MockHub, upgrade modals when gated capability clicked)

---

## Phase 2 content sizing (for planning)

Mock-only content per track today vs target for 3-month Pro runway. Math: 5 sessions/week × 4 weeks × 3 Q/session × ~half (chain atomicity halves effective inventory) = ~60 Q/month consumed; 3 months = ~180. This is 3–22× current inventory per track.

| Track | Mock-only today | ~Months runway today | Target (3 mo Pro) |
|---|---|---|---|
| SQL | 38 | ~0.6 | ~180 |
| Pandas | 26 | ~0.4 | ~180 |
| ML | 25 | ~0.4 | ~180 |
| Experimentation | 25 | ~0.4 | ~180 |
| PySpark | 21 | ~0.3 | ~180 |
| Python | 20 | ~0.3 | ~180 |
| DE | 14 | ~0.2 | ~180 |
| DM | 13 | ~0.2 | ~180 |
| Stats | 8 | ~0.1 | ~180 |

This sizing is provisional. Re-evaluate against real Pro usage data once Phase 1 ships. The foundation laid in Phase 1 (chain schema, dimension taxonomy, authoring agent flow) must make bulk authoring fast and consistent — there's going to be a lot of it.

---

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-05-21 | Per-track concept families, NOT cross-track | Cross-track aggregation is a Phase 3 dashboard lens; forcing alignment muddies authoring |
| 2026-05-21 | Drop per-track authoring agent files | 40% overlap with universal agent caused drift; track docs hold the knowledge instead |
| 2026-05-21 | Mock chains are globally atomic per user | Simplest mental model ("zero or one"); preserves readiness signal |
| 2026-05-21 | Mock-only is Pro/Elite, free uses practice pool | Fairness alignment with paid value; chains stay premium |
| 2026-05-21 | Interview Loop is chain-only | Otherwise it's "benchmark with a name" |
| 2026-05-21 | Pool exhaustion → hard 409 | Soft fallback dilutes the readiness signal |
| 2026-05-21 | Philosophy shift: development primary, interview success consequence | Tonal pivot away from "FAANG prep" toward durable professional reasoning |
| 2026-05-21 | 3 modes: benchmark, short_drill, custom_drill (long_drill retired) | Custom covers the long-drill range; reduces mode-selection cognitive load |
| 2026-05-21 | Free: 1 benchmark/rolling-7-days + unlimited easy short_drill (no daily medium counter) | Free user must *experience* benchmarking once; daily counters are off-brand; rolling 7d smoother than calendar week |
| 2026-05-21 | Pro: combined 3 drills/day cap (not 2+2) + 3 benchmarks/day | User agency without dual counters; matches metered-SaaS convention |
| 2026-05-21 | Pro `custom_drill` allows full difficulty (not capped at medium) | Pro has full practice difficulty already; capping mock would be incoherent |
| 2026-05-21 | Elite "unlimited" means soft backend rate-limit (~10/hr) hidden from UI | Anti-abuse defense without surfacing the limit as a feature |
| 2026-05-21 | 2-min chain reclaim window stays; UX must be far more prominent (countdown chip + visible button) | Window is right; current UX (hidden behind Exit) is wrong |
| 2026-05-21 | CLAUDE.md gets standing pushback rule + comprehensive doc-sync mapping + mandatory-agent rule | Codify the discipline that prevents this kind of refactor in future |
| 2026-05-21 | Free stays benchmark-only (no weekly drill added) | User overrode my recommendation; reasoning "keep it simpler" — fewer counters, one clean demo moment, cleaner upgrade pitch |
| 2026-05-21 | Mixed track stays accessible to Free within their session shape | User overrode my recommendation; reasoning "don't multiply gates that frustrate users." Mixed inherits each tier's mode/difficulty rules |
| 2026-05-21 | Elite anti-abuse: 30 s burst gap + 5/hr + 20/day rolling | Three-layer defense against script-spam and password-sharing. All values well above human ceiling; invisible unless triggered |
| 2026-05-21 | 2-min discard + chain reclaim do NOT count against daily quota | Misclick or "wrong track" recovery shouldn't cost a quota slot; double-penalty for chain users would be even worse |
| 2026-05-21 | Concept-taxonomy research grounds families in industry sources (StrataScratch, DataLemur, Glassdoor posts, canonical textbooks) but never lifts question content. Research validates exhaustiveness only; question authoring stays aligned to datathink's own philosophy and flow | User-specified discipline: "don't lift questions, only search for exhaustiveness" |
| 2026-05-21 | Everything after Phase 1 must be implementable by Sonnet from the docs alone | Phase 1 deliverables must be detailed enough that subsequent phases need no design conversation — taxonomy precise, mock contract complete, track docs prescriptive |
| 2026-05-21 | Cross-track family naming reusability scoped to executable analytics tracks (SQL / Pandas / PySpark) only; Python algorithmic patterns stay native | Original cross-track-portability decision was about all 9 tracks; this is a narrower refinement for the 3 tracks that genuinely share business-analytics reasoning patterns. Pushback by Claude accepted by user. |
| 2026-05-21 | Closed 5 taxonomy gaps surfaced by self-audit against the concept-tag philosophy | Added OUTPUT SANITY VALIDATION + PERFORMANCE-AWARE ANALYTICS + METRIC RECONCILIATION to SQL. Added 5 parallel families to Pandas (the SQL ⚡ trio + sanity + performance). Added 3 to PySpark (data quality + double-counting + sanity; intentionally NOT metric-interpretation or performance which overlap PySpark-native families). Renamed Pandas DEDUPLICATION & DISTINCT COUNTING → DEDUPLICATION LOGIC and RANKING & TOP-K → RANKING & TOP-N PER GROUP to align with SQL. Existing tags continue resolving via preserved match patterns. |
| 2026-05-22 | Mock-only basis = recombine learned concepts under fresh framing; retired the "≤15% reuse / 85% fresh families" cap | User-supplied authoring philosophy (SQL-anchored, applied to all 9 tracks). The old cap pushed mock-only toward concept families *not* in practice at that difficulty, which is incoherent with "practice teaches, mock evaluates transfer" — a mock can't fairly test transfer of reasoning the curriculum never taught. New rule: mock-only introduces no unseen concept family and must not clone a practice question's framing; it recombines learned concepts in a fresh business scenario (new KPI, time window, relationship, stakeholder pressure, dirty data). Differentiator is framing/realism/ambiguity, not concept novelty. Codified in content-authoring.md, the agent, concept-taxonomy.md (validation rule 7), all 9 track docs, mock.md, and track-onboarding.md. |
| 2026-05-22 | Every difficulty tier maps to realistic business tasks, never textbook drills — added per-tier "allowed business scenarios" to all 9 track docs | Difficulty controls reasoning depth only; it never licenses toy/syntax-recall exercises. Construct lists bound the *tools*; the new scenario lists bound the *feel*. Both gate a question. SQL scenarios taken verbatim from the user's spec; the other 8 tracks translated to track-appropriate realistic tasks. |
| 2026-05-22 | ⚡ "real-world gap" families have zero coverage and are practice targets, not mock material | Verified empirically (2026-05-22): all six SQL ⚡ families, all six Pandas ⚡ families, and all three PySpark ⚡ families resolve to **0 practice and 0 mock** occurrences (one incidental SQL substring hit on `FULL OUTER JOIN RECONCILIATION`). The refactor had added them to the taxonomy with notes like "mock will lean heavily here" — which directly violates the new no-unseen-concepts rule. Corrected: ⚡ families must be grounded in **practice first** (via the Phase 2 remap + new practice authoring), then mock recombines them. Caught when the user spot-checked an over-claiming sql.md edit; fixed across sql/pandas/pyspark track docs, the taxonomy intro callout, and the two taxonomy "mock will lean" notes. |
| 2026-05-22 | Mock-only realism family class + co-tag rule | METRIC INTERPRETATION & DENOMINATOR CHOICE, OUTPUT SANITY VALIDATION, PERFORMANCE-AWARE ANALYTICS (and Pandas MEMORY & VECTORIZATION REASONING) are assessment *lenses*, not curriculum concepts. Designated `mock_only` in the registry; may never be a question's sole tag (must co-occur with a practice-grounded family); exempt from practice-grounding. Does not violate no-unseen-concepts because the underlying concept is always practice-taught — the lens adds framing/assessment. User-approved. |
| 2026-05-22 | SQL ⚡ split: 3 practice-grounded (DATA QUALITY SKEPTICISM, DOUBLE-COUNTING DETECTION, METRIC RECONCILIATION) + 3 mock-only realism | Data-quality & reconciliation grounded mostly via remap re-tag of existing hard questions; double-counting is the one true content gap (needs ~3–4 new `debug`). METRIC RECONCILIATION kept practice-grounded (concrete right answer; Q12032 exists) — user deferred the call. |
| 2026-05-22 | Mock-only content is not limited to query-writing | `debug` / `reverse` / `scenario` reasoning questions are first-class mock-only SQL types — they simulate real interview dynamics and are the natural home for the realism families. User-specified. |
| 2026-05-22 | SQL remap residuals ≈ 0; remap is mostly taxonomy match-pattern expansion, not question re-tagging | Empirical audit (2026-05-22): of 124 unresolved tag incidences, ~80 are legit synonyms needing match-patterns (no question edit), ~14 are type-markers to strip, ~8 re-tag into practice-grounded ⚡ families or fix a blocklist hit. No tag lacks an honest family home. "Don't force-fit" — surface genuine unknowns for review. |
| 2026-05-22 | De-noise foundational SQL families (RESULT SHAPING, GROUPED AGGREGATION) | Tag by the distinguishing technique, not incidental mechanics — strip `DETERMINISTIC RESULT ORDERING`/`COLUMN PROJECTION` where incidental and GROUPED AGGREGATION on advanced questions whose real skill is window/ranking/CTE. Matches StrataScratch/DataLemur/LeetCode SQL convention; sharpens weak-spot signal. User-approved with the caveat: keep it where genuinely primary. |
| 2026-05-22 | SQL sizing: practice 112 → ~118–122 (only ~6–10 new), mock 38 → ~150 | Practice barely grows because remap + the mock-only-realism decision absorb most of the gap; honors "don't overload practice against core philosophy." Mock fan-out/double-counting is top priority. |
| 2026-05-22 | Kept all 7 follow-up dimensions (user's spec listed 5) | data_quality_pivot is genuinely distinct from edge_case_pivot (dirtier-than-implied data ≠ an excluded case); stakeholder_pivot is distinct from business_rule_pivot (delivery to a human with an agenda ≠ a definition change). User's 5 (scale, business rule, ambiguity, edge-case, performance) are now documented as the core subset; data_quality + stakeholder round out the 7. No content used any dimension yet, so zero migration cost. |

---

## Open questions / follow-ups (NOT blocking Phase 1)

- Sizing for Phase 2 mock content expansion — confirm 3-month-Pro-runway target after observing real usage patterns
- Should free-tier mock be allowed to re-show solved practice questions? Default: yes, fresh-first preferred. Confirmed by user 2026-05-21.
- Soft rate-limit for Elite — pick exact threshold (10/hr starting assumption)
- Browser pass on color tokens — `--bg-page` (#F5F7F4) → consider #FAFBFA or #F8FAF8 closer to white, recommendation pending Phase 1 commit
- Interview Loop session length tuning — 15 min per chain is a guess; revisit after first Pro/Elite user feedback in Phase 3
- Whether to surface chain-consumption progress to the user ("You've explored 47 of 156 available scenarios in SQL")

---

## Cross-reference map

Files in this refactor and what they own:

| File | Owns | Cross-refs from |
|---|---|---|
| `docs/features/mock.md` | Plan-tier matrix, chain atomicity, Interview Loop contract, discard UX | CLAUDE.md, pricing.md, north-star.md |
| `docs/concept-taxonomy.md` | Per-track concept families, blocklists, follow-up dimension taxonomy | track docs, universal agent, content-authoring.md |
| `docs/tracks/<track>.md` | Per-track philosophy, modality, datasets, concept arc, authoring allocation | universal agent, content-authoring.md |
| `.github/agents/question-authoring.agent.md` | Authoring procedure (track-agnostic), quality bar, hint rules, verification | (invoked, not cross-linked) |
| `docs/content-authoring.md` | Cross-track contract, JSON schema templates, validation rules | CLAUDE.md, universal agent |
| `docs/specs/platform-north-star.md` | Product North Star, philosophy, role-to-track framing | CLAUDE.md, all docs |
| `docs/specs/mock-benchmark-spec.md` | Benchmark invariants, blueprint principles, modality mapping | mock.md, universal agent |
| `docs/specs/practice-modality-spec.md` | Modality matrix, interaction modes, eval kinds | track docs, content-authoring.md |
| `docs/concept-hooks.md` | Socratic interview-hook inventory (seeding tool, not registry) | track docs (informational) |
| `CLAUDE.md` | Standing instructions, project overview, content footprint, doc-sync map | (the entry point) |
| `docs/phases/2026-05-authoring-refactor.md` | This refactor's progress tracking | (self-deletes when done) |
