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
This is the first phase a fresh Sonnet session should be able to execute end-to-end from the committed docs alone. Read [`docs/phases/2026-05-authoring-refactor.md`](2026-05-authoring-refactor.md) (this file) for the full brief.

- [ ] Remap existing 993 question `concepts` arrays to new per-track families (~80% automatable, edge cases need human review). Tooling: write a script that reads `docs/concept-taxonomy.md`, applies the resolution algorithm, and proposes replacements for review.
- [ ] Refactor `backend/concept_families.py` to load from `docs/concept-taxonomy.md` (or compile at build time). Eliminates the hand-mirror.
- [ ] Author new mock-only content with `follow_up_dimension` + `follow_ups[]` — target 3-month Pro runway (~180 questions/track from current 8–38). Always via the universal authoring agent.
- [ ] Add catalog-load validations to `validate_content.py`: chain integrity, dimension diversity, no orphans, no shared children, length bounds. Crash on violation.
- [ ] Add CI check flagging question file edits without agent invocation marker.

### Phase 3 — Interview Loop full stack ⏸ pending (depends on Phase 2 content)
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
