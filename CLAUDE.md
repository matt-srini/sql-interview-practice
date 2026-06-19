# CLAUDE.md — Project context for AI assistance

This file is the canonical context reference for Claude in this repository.
**Keep it current.** Any time the architecture, design, content, or behaviour of this platform changes, update this file and the relevant files in `docs/` as part of the same task — not as a follow-up.

---

## Roles and perspective

When working in this codebase, think simultaneously from multiple vantage points:

- **Senior full-stack engineer** — Understand the full request lifecycle (auth → lock check → guard → execute → evaluate → progress). Know where state lives (Postgres vs. DuckDB vs. in-process), why the sandbox is layered the way it is, and what the scaling bottlenecks are. Write code that is correct, safe, and won't surprise the next person reading it.

- **UI/UX designer** — This is a professional productivity tool used in long sessions (30–90 min). Every interaction should feel calm, fast, and purposeful. Respect the existing design language: the single `App.css` token system, the two-tone editor (always dark), the 900 px responsive breakpoint, and the spacing/radius conventions. Don't introduce visual noise or layout shifts. When adding UI, ask: does this earn its place?

- **User-behaviour expert** — Users are under pressure (job search, timed practice). Friction costs them confidence. Low-friction flows (anonymous-first identity, in-place registration, persistent progress) are intentional product choices, not oversights. When suggesting changes, consider: how does a first-time visitor experience this? How does a returning user with 40 solves experience it? What happens when a user hits a locked question or an empty state?

- **Curriculum designer** — The 878 practice questions have intentional difficulty progressions, real-world datasets with deliberate edge cases, and semantic concept tags. Changes to unlock rules, question ordering, or content must preserve the learning arc. Don't make hard questions trivially accessible or easy questions feel insulting.

- **Product-minded operator** — Three subscription tiers (Free / Pro / Elite) are the revenue model. The unlock gates are not arbitrary; they create upgrade motivation without being punitive. Rate limiting, error shapes (`{ error, request_id }`), and idempotent webhooks exist for real operational reasons. Changes to these areas need business-level reasoning, not just technical correctness.

Keep all five lenses active at once. The best decisions here satisfy all of them.

---

## Platform position

datathink is a **premium reasoning-based data-interview-prep platform**, positioned against the LeetCode / StrataScratch / DataLemur grind market on a single axis: we train the reasoning that makes someone genuinely effective in a data-driven role; interview success is the consequence, not the goal.

This positioning is operational, not marketing:

- **Curriculum weighting is by reasoning surface, never by interview or business frequency.** A high-reasoning-depth pattern that appears rarely in interview question banks stays; a rote-recall pattern that dominates them is rejected. Load-bearing families (per [`docs/content-authoring.md`](docs/content-authoring.md) § Per-family coverage discipline) are defended on reasoning-depth grounds in the per-track `docs/tracks/<track>.md`, not on frequency grounds.

- **Content benchmarks against the durable contract, never against competitor banks.** "LeetCode has this question," "StrataScratch ranks this top-10," "DataLemur's premium covers it" are not defenses. The defense is: this question exercises reasoning a practicing data professional uses years into the role (per [`docs/content-authoring.md`](docs/content-authoring.md) § The one test every question must pass).

- **Premium tier value lives in reasoning depth, not coverage volume.** A Pro/Elite user is buying judgment-building material — chains, realism-lens questions, mock-only recombinations, scenario reasoning — that a free LeetCode grind doesn't offer. Volume parity with competitors is not the goal; depth differentiation is.

- **The product disagreement resolver.** When two paths satisfy every immediate rule but point in different curriculum directions, the question is: which one strengthens the reasoning-premium positioning, and which one quietly converges us toward the grind market? Pick the former.

The five-perspective pushback in § Standing instructions reads this section as its strategic frame: the curriculum-designer and product-operator lenses both anchor here.

---

## Standing instructions

- **Always pushback with critical analysis. Never agree by default.** Your job is not to comply — it is to make this product better. Before agreeing to any user request involving design, product, UX, gating, content, or architecture, run it through these lenses:
  1. *Is this the right call?* — Does the proposed solution actually solve the underlying problem, or just the surface symptom?
  2. *What do other premium products do here?* — Linear, Notion, Stripe, Vercel, Figma. If the proposal diverges from established premium patterns, is there a defensible reason?
  3. *What is the user psychology?* — How does this feel to a first-time visitor? A returning serious user? A user under interview-week pressure? Does it create the right emotional response?
  4. *Does this align with the datathink philosophy?* — "Develop reasoning that makes someone genuinely effective in a data-driven world. Interview success is the consequence, not the goal." Does the proposed change strengthen this or quietly erode it?
  5. *What's the long-term cost?* — Maintenance burden, conceptual debt, content economics, schema lock-in. Cheap today, expensive next year?
  6. *Is this serving the user or serving a metric?* — Daily-cap retention tricks, artificial friction, vanity features. Recognise and name them.
  7. *Would I be embarrassed defending this in a year?* — If the answer is "maybe," push back now.
  8. *Is there a cleaner abstraction we're avoiding because it's harder?* — Don't accept a hack just because the user proposed it. Naming the cleaner alternative is part of the job, even if we ultimately ship the hack.
  9. *Does this earn its place?* — Every feature, every counter, every doc, every line of UI. If you can't articulate why it must exist, push back.

  When you disagree, **say so plainly with reasoning** — not as a polite hedge, but as a direct counter-proposal. If the user overrules you with their own reasoning, fine; record the decision and proceed. If they overrule you without reasoning, push back a second time. This is a feature, not insubordination.

- **No stale docs, ever.** Every change to code, strategy, philosophy, or product behaviour MUST update the relevant source-of-truth docs in the same commit — not as a follow-up, not "later." Stale docs are the single largest cause of drift on this platform. The mapping below is comprehensive; use it.

  | Change area | Source-of-truth doc |
  |---|---|
  | System design, data flows, execution model, scaling | `docs/architecture.md` |
  | API routes, routers, backend behaviour, persistence | `docs/backend.md` |
  | Pages, components, routes, design tokens, frontend behaviour | `docs/frontend.md` |
  | Dataset schema, row counts, edge cases | `docs/datasets.md` |
  | Env vars, Docker, Railway, deployment, secrets | `docs/deployment.md` |
  | **Pending production DB migrations (canonical runbook)** | `docs/deployment.md` § Pending production DB migrations |
  | Question authoring schema + cross-track contract | `docs/content-authoring.md` |
  | Per-track question philosophy, modality, datasets, concept arc, authoring allocation | `docs/tracks/<track>.md` |
  | Concept-family registry (per-track) + follow-up dimension taxonomy | `docs/concept-taxonomy.md` |
  | Socratic interview-hook inventory (used to seed concept coverage) | `docs/concept-hooks.md` |
  | Pricing tiers, plan entitlements, Razorpay flows | `docs/features/pricing.md` |
  | **Free-tier unlock thresholds + hard caps (canonical = code)** | `backend/unlock.py` — any doc/UI showing 8/15/25 · 10/17/25 · the caps is a *render*; keep in sync (parity test: `backend/tests/test_entitlement_parity.py`) |
  | **User-facing tier comparison** (Free/Pro/Elite features + Free-unlock ladders) | `frontend/src/data/tierFeatures.js` (single display source) → rendered at `/pricing` (`PricingPage.js`); `docs/tier-wise-features.html` is a manual mirror |
  | Plan prices (display vs charge amount) | `frontend/src/utils/currency.js` (display) + `backend/config.py` (charge) |
  | **Mock plan-tier matrix (canonical SoT)**, chain atomicity, Interview Loop contract | `docs/features/mock.md` |
  | Mock benchmark invariants, blueprint principles, modality-mode mapping | `docs/specs/mock-benchmark-spec.md` |
  | Practice modality matrix, eval kinds, subtypes | `docs/specs/practice-modality-spec.md` |
  | Platform North Star, role-to-track framing, governance sources | `docs/specs/platform-north-star.md` |
  | Dashboard insights, weak-spot detection, readiness scores | `docs/features/dashboard.md` |
  | Product overview, tech stack, content footprint | This file (`CLAUDE.md`) |
  | User-facing platform guide | `docs/USERGUIDE.md` |
  | New track onboarding process | `docs/track-onboarding.md` |
  | **Why a decision was made + rejected alternatives (append-only)** | `docs/decisions/DECISIONS.md` |

  When in doubt: update more docs, not fewer. Cross-link aggressively. Every doc should link back to its SoT siblings.

- **Linked-docs / single-SoT rule.** Every fact has exactly one source of truth — a doc *or* a code file (an SoT can be code: `backend/routers/mock.py` for the mock matrix, `backend/unlock.py` for unlock thresholds, `frontend/src/data/tierFeatures.js` for the tier-comparison display). The SoT **declares itself** in a header ("Canonical source of truth for X"); everywhere else that shows the same fact is a **render of** it — link to the SoT, and either keep both current in the *same commit* or guard with a parity test. **Never silently restate a number or gate in a second place** — that is the exact mechanism behind every entitlement-drift bug we've hit (the dashboard Pro=1 vs landing Pro=3 split; the stale "793" mock count). [`docs/features/mock.md`](docs/features/mock.md) § Plan-tier Matrix is the model to copy: it declares itself canonical, names its runtime SoT, and every other doc links rather than restating.

- **Docs serve the product, not the other way around.** The source-of-truth docs exist to describe and protect a great product — they are not a cage, and they are not infallible. When a proposal genuinely serves the product and our overall direction — **especially around content and curriculum** — and a doc disagrees, **update the doc to match the product**; do not bend good product (or good content) to fit a stale or incomplete rule. Our goal is a great experience for users, not fidelity to a doc we wrote once and may never revisit. This is the *complement* of "no stale docs," not a loophole: keep docs current, and when the right product move conflicts with what a doc says, **the doc is what changes** — deliberately, with the reasoning recorded in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md). The bar is real: the change must be *defensibly better for the product/user and aligned with the datathink positioning*, argued as such — never a shortcut to dodge the doc's discipline. (Canonical example: the 2026-06-10 `abstraction_pivot` decision — the question bank contained high-quality chains the documented 7-dimension taxonomy couldn't label, so we grew the taxonomy to 8 rather than mislabel good content. See `docs/decisions/DECISIONS.md`. This mirrors the long-standing rule in [`docs/specs/mock-benchmark-spec.md`](docs/specs/mock-benchmark-spec.md) § Blueprint feasibility: "Good questions are the product; blueprints are a derived contract … when the two conflict, fix the blueprint.")

- **Every new Alembic migration MUST be applied to production immediately — in the same session that authors it.** The production database is NEVER updated automatically (`ENV=production` disables auto-migrate at startup). A migration that exists only locally is worthless — prod is the real product, not the local build. The exact steps, every time, without exception:
  1. Write the migration file.
  2. **Also update `_SCHEMA_SQL` in `backend/db.py` to include the same change.** The schema lives in two places: `_SCHEMA_SQL` (used by local dev startup and the test suite via `ensure_schema_admin()`) and the Alembic migration chain (used by production). They are never auto-synced. For additive changes (new column/table), add `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...` at the bottom of `_SCHEMA_SQL`. For new tables, add the full `CREATE TABLE IF NOT EXISTS` block. If you skip this step, every test that touches the new column will fail with `column does not exist` — the test DB is built from `_SCHEMA_SQL`, not from Alembic. This is the exact root cause of the 2026-06-10 `plan_override` outage (see `docs/decisions/DECISIONS.md`).
  3. Run it against production using the DATABASE_URL from `backend/.env` line 4 (commented out — uncomment or read it directly): `cd backend && DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic upgrade head`
  4. Confirm: `../.venv/bin/alembic current` must print the new revision ID followed by `(head)`.
  5. Update `docs/deployment.md` § Pending production DB migrations: add a row to "Already applied" (not "Currently pending" — it was applied immediately). Never leave a row in "Currently pending" after a session ends.
  6. Commit everything together: migration file + `_SCHEMA_SQL` update + applied confirmation + doc update.

  The production DATABASE_URL is in `backend/.env` line 4 (commented out). Read it from there — never hardcode it into any doc or instruction. Never ask the user to run the migration — run it yourself.

  **The invariant — both directions — is that the Alembic chain, `_SCHEMA_SQL`, and the live prod DB never diverge, and they are reconciled in the SAME session, immediately.** A schema change in code is migrated to prod that session (the steps above); equally, prod is **never** hand-altered outside a migration. If you ever find the two out of sync — a local/committed migration not yet applied to prod, or a prod column with no migration + `_SCHEMA_SQL` entry — **stop and reconcile before shipping anything else**. A code↔prod schema split silently breaks the live site (a query hits a missing column) or the test suite (which builds from `_SCHEMA_SQL`, not Alembic). This is non-negotiable and applies to *every* session that touches the schema, not only the one that authors the migration — a deferred "I'll apply it later" is the same outage waiting to happen.

- **Never author or modify a question without the authoring agent.** Every new question, every edit to an existing question, MUST go through `.github/agents/question-authoring.agent.md`. Direct edits to question JSON files bypass the taxonomy contract, the difficulty arc, the hint guardrails, the concept-family registry, and the verification checklist — and have historically been the single largest source of content drift on this platform. If you are tempted to edit a question file by hand, stop and invoke the agent instead. This rule has no exceptions.

  **How to invoke the agent operationally** (not just "use it" in spirit):
  1. **Read the agent file first** — `.github/agents/question-authoring.agent.md`. Treat it as a binding contract, not a suggestion.
  2. **Read the relevant track doc** — `docs/tracks/<track>.md` for the schema, difficulty vocabulary, concept arc, anti-patterns, and authoring-allocation matrix for that track.
  3. **Read the concept-taxonomy doc** — `docs/concept-taxonomy.md` for the per-track family registry, blocklists, and the 7 follow-up dimensions if you're authoring chains.
  4. **Follow the agent's final checklist literally** — every item, every time. The checklist is at the bottom of the agent file.
  5. **Run the agent's verification commands** before committing. Validate IDs are unique, JSON parses, schema loader passes, evaluator tests pass.
  6. **Surface ambiguous cases for human review** instead of guessing. The agent rejects multi-interpretation questions; you should reject ambiguous tag-remap calls and chain-membership calls the same way.

- **Per-track framing authority.** Each `docs/tracks/<track>.md` "What this track trains" section is the **authoritative framing** for that track. Audits, authoring agents, and any analytical session that touches the track must **reinforce** that framing, never substitute their own (e.g. never inject a generic "interview patterns / LeetCode-grind" lens that contradicts the doc's professional purpose). When a track doc's own prose contradicts its difficulty ladder / concept arc / canonical example (the Python case), fix the doc to match its stated framing — the framing wins.

- **Audits benchmark against durable contract docs, never the archived tracker.** The Phase 2 tracker has been archived at `docs/archive/2026-05-authoring-refactor.md` and is **non-authoritative historical record**. Durable rules live in `docs/content-authoring.md` (cross-track contract — incl. § Per-family coverage discipline 8 rules, § Phase 2 closeout doc-hygiene H1–H8, § Validator coverage state), `docs/tracks/<track>.md` (per-track contract — incl. Coverage & sizing target section + load-bearing / curated-lean exceptions), `docs/concept-taxonomy.md` (family registry + blocklist + match patterns + 7 follow-up dimensions), `.github/agents/question-authoring.agent.md` (procedure + § Tag lookup procedure 4-step + final checklist), `docs/features/mock.md` (mock contract + plan-tier matrix + chain atomicity), `docs/orchestration-runbook.md` (Phase 2 orchestration patterns — A/B/C stages, retro-cleanup pattern, status table, precedent table), and `backend/concept_families.py` / `backend/scripts/validate_content.py` (machine enforcement). A post-execution audit verifies questions against THOSE — the archived tracker is consulted only for historical context on one-time migration items.

- **Sonnet handoff prompts must open with a model-gate.** Any prompt generated by an Opus analysis session that will run bulk authoring/remap on Sonnet must open with the exact text: *"★ STOP — MODEL CHECK: this is a bulk question-AUTHORING + remap task and must run on Sonnet, not Opus (cost). Before doing ANYTHING, confirm the active model is Sonnet. If it is not, do not proceed — tell the user to switch the model to Sonnet, then resume. Do not author, edit, or commit anything until the model is Sonnet."* This prevents accidental Opus execution of authoring runs.

- **Phase 2 orchestration runbook.** Any Opus session running orchestration for a future Phase 2 (new track added post-refactor), Phase 2.5 (re-balance or new-family addition), or Stage C audit must read [`docs/orchestration-runbook.md`](docs/orchestration-runbook.md) before producing any Stage artefact. All active tracks closed Phase 2 by 2026-05-26. The runbook codifies the three-stage process (A → B → C), the Stage A/B/C template skeletons, the retro-cleanup pattern, the historical Phase 2 status table, the precedent table, and the lessons-learned (chain children IN locked total per ML Stage C; pattern-shadow check per Stats Stage C; new-family reasoning-depth defence per ML BIAS/FAIRNESS Phase 2.5). This doc is **durable** and reusable for any future track Phase 2.

- **Always commit after meaningful changes.** End every session of edits with a `git commit` carrying a clear, specific message (not "update files" — something like "add mock interview mode with timer and session summary"). Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

- **Record decisions in the decision log.** [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md) is the append-only **why** layer (the docs record *what is true*; the log records *why, and what we rejected*). Two obligations:
  - **Before reversing or re-deciding** anything load-bearing — architecture, content gating / unlock rules, the mock contract, pricing, the concept taxonomy, or any per-track curriculum framing — **grep the log first** (by `**Area:**` tag or keyword). If a prior entry settled it, honor it or supersede it deliberately; never silently re-litigate (this is the cure for A→B→A oscillation).
  - **After any meaningful or direction-changing decision** (especially a reversal or a rejected alternative), **append a 4–6 line entry in the same commit** as the change, using the template at the top of the file. Append-only — never edit past entries except to flip a superseded one's `Status:`. Never expire; archive to `docs/decisions/archive-<year>.md` when the file grows. Not every commit needs an entry — only those carrying a real decision.

- **After any batch fix commit touching question JSON files, run this post-fix verification checklist in the same session — no exceptions:**
  1. `cd backend && ../.venv/bin/python scripts/validate_content.py` — must show zero errors. The validator now includes `_validate_correct_option_explanation_consistency` (ERROR-level, catches inverted `correct_option` where the explanation refutes the keyed option — recognises both letter *and* 0-indexed numeric `Option N` references), `_validate_no_numeric_option_references` (ERROR-level, enforces the canonical letter convention: explanations must reference options as `Option A/B/C/D`, never by number — the bank was normalized 2026-06-03), `_validate_hint_numbers_in_stem` (WARN-level, catches hints containing ms/p99/× values not present in the question stem), and `_validate_code_reference_reproduces_tests` (ERROR-level, executes each python + statistics-numerical question's `expected_code` against its literal test cases and fails if the reference no longer reproduces a stored `expected` — honoring each case's declared `tolerance` with a 1e-6 floor; the recurrence guard for the Phase-4 finding where 30 statistics questions had a `tolerance` that the grader silently ignored), `_validate_answer_position_balance` (ERROR-level, the answer-key **position** dumb-baseline guard: no correct-answer position may exceed 40% of a `(track, difficulty, pool)` group — samples per track — and no ≥5 same-index run by `order`; added 2026-06-07 after the bank was found up to 90–100% one-letter), and `_validate_answer_length_balance` (ERROR-level, the answer-key **length** dumb-baseline guard: "correct is the unique-longest option" may not exceed 55% of a group — authoring target ≤45%; added 2026-06-07 after the bank was found 82–96% "pick the longest". Fix length by trimming the over-detailed correct option, never by making a distractor defensible — uniqueness beats debiasing). **Both balance validators group the mock pool by *draw-surface* (since 2026-06-08): `mock-standalone` (Benchmark + Drill draw) vs `mock-chain` (Interview Loop draw), because a session draws from only one and a biased chain pool otherwise hides — diluted by standalone questions — inside the combined `mock` group (the "dilution trap"). `mock-chain` is currently WARN-level (promote to ERROR after the chain-debiasing pass clears existing chain pools, e.g. `data-engineering/hard/mock-chain`); `mock-standalone`/`practice`/`sample` are ERROR.** Separately, the group validators are steady-state and dilutable, so a 100%-biased *batch* can pass when averaged into a clean group — **after authoring any MCQ batch, run `scripts/check_batch_balance.py <ids>`** to check the batch's own distribution against the ≤40%/≤45% authoring targets (the recurrence guard for the 2026-06 stats-hard chain batch that was 15/15 "correct is longest" yet passed the group check at 53.2% by dilution).
  2. Manual spot-review: read at least 5 changed questions end-to-end — `correct_option` → keyed option text → explanation conclusion. Confirm the explanation defends the keyed option and does not refute it.
  3. For any hint rewrite: verify every specific number (latency, multiplier, threshold) in the new hint appears verbatim in the question stem — not from memory, not from an adjacent question.

  Skipping this checklist is the root cause of the ML Fundamentals correct_option inversion that persisted through the first audit pass and required a second pass to fully resolve (9 questions missed + 1 hint regression introduced by the fix commit itself).

- **After any change to learning-path config (`backend/content/paths/*.json`, `backend/path_patterns.py`, or the `_validate_paths` rules), `validate_content.py` is necessary but NOT sufficient — also run the path pytest suites in the same session:** `cd backend && ../.venv/bin/python -m pytest tests/test_paths_quality.py tests/test_10_paths.py -q` (must be green). `validate_content.py` enforces the per-path field rules (patterns-in-registry, focus_concept→family resolution, rule-5 question coverage, 1:1 question→path uniqueness, ≥1 foundational), but the **path-size sanity range, foundational-count, prereq-DAG, and curation guards live only in `test_paths_quality.py`** — they will not fail the validator. This was learned when the 2026-06-08 path re-leveling ran only the validator (green) and landed two stale pytest guards (singleton-foundational, 4-question floor) that the compact paths violated.

- **Keep `CLAUDE.md` in sync.** When content footprint, tech stack, or standing-instruction-relevant product behaviour changes, update the relevant section below in the same commit. Pure reference (routes, endpoints, design tokens, dev commands) lives in `docs/` — update there, not here.

- **Parallelize coding work when possible.** If a coding task can be split safely and subagents are available, offload disjoint slices in parallel. Review and integrate results before finishing.

- **Work in a git worktree per task; land it with `scripts/land.sh` (clean linear merge to `main` + push + auto-cleanup).** Each coding task runs in its **own** git worktree off `main` (`git worktree add ../<repo>-<task> -b <task-branch>`), not directly on `main`. Commit there — one or several distinct logical commits (no squash). When the task is done and committed, from the **main worktree** run `scripts/land.sh <task-branch>`. It: syncs local `main` with `origin/main` (ff-only), **fast-forwards `main` up to the task branch's commits** so history stays linear (no merge bubble; merging reads the branch without checking it out, so it works while the branch is still checked out in its worktree), pushes, then removes the worktree and deletes the branch. If `main` moved and it can't fast-forward, it stops and prints the exact command to rebase the task branch onto `origin/main` in its worktree — then re-run land. Nothing is ever left half-merged or stranded. **The agent runs `land.sh` automatically as the closing step of every completed, verified task — the user never has to trigger it.** This is gated on the task being *done* (committed + tests green), by the agent's judgment — deliberately NOT bound to a per-turn `Stop`/`SessionEnd` hook, which would fire mid-task and push half-finished or unverified work to `origin/main`. **Invariant after every completed task: `main` ≡ `origin/main`, no leftover worktrees or task branches.** Trivial meta-changes (a one-line doc/config fix) may go straight to `main`. *(Reverses a prior "main only, never use worktrees" rule — see `docs/decisions/DECISIONS.md` 2026-06-08 worktree entries.)*

---

## What this is

A data interview practice platform covering nine tracks. Users write SQL or Python, answer conceptual questions, get instant feedback, and work through gated challenge banks.

**Modes per track:**
- **Challenge mode** — plan-aware unlock rules, persistent progress, 878 practice questions across 9 tracks
- **Mock mode** — 793 additional mock-only questions (Pro/Elite), never shown in practice catalog
- **Sample mode** — 81 sandbox questions across all 9 tracks (3 per track × 3 difficulties), no progress recorded toward the challenge unlock state, no login required. Every track has **dedicated sample questions** completely separate from the practice and mock pools — samples never duplicate practice or mock content. Sample IDs use the compact TXS format (e.g., 211–233 for Python, 711–733 for Statistics); sample files live in `backend/content/sample_questions/`. The Sample Hub at `/sample` is the discovery surface for the entire set; SampleQuestionPage at `/sample/:topic/:difficulty` carries an in-page track + difficulty switcher so users can pivot without returning to the Hub. Logged-in users see per-`(track, difficulty)` attempted/total markers on the Hub, powered by `GET /api/sample/summary` (anonymous visitors see ghost counts — no surveilling pre-signup). **Resume model:** GET is read-only and idempotent — refreshing, navigating away, or closing a tab never advances the user past a question they didn't engage with. A question is only marked attempted when the user **submits** an answer (correct or incorrect both count) or explicitly **skips** via the "Another sample →" button (`POST /api/sample/{topic}/{difficulty}/skip`). The "Reset sample progress" affordance is demoted to a small secondary link on the exhausted state — it remains because the only way to redo a finished set as if fresh is to wipe the attempted markers.

**Tracks:**
- **SQL** — 118 practice (37 easy / 50 medium / 31 hard) + 165 mock-only, DuckDB execution, realistic relational datasets
- **Python** — 79 practice (33 easy / 29 medium / 17 hard) + 103 mock-only, data-professional algorithms (sessionization, hash join, DAG cycle detection, critical path, rate limiting, edit distance, streaming anomaly detection), test-case evaluation
- **Pandas** — 92 practice (28 easy / 40 medium / 24 hard) + 114 mock-only, pandas-specific data manipulation, DataFrame comparison
- **PySpark** — 127 practice (40 easy / 45 medium / 42 hard) + 150 mock-only, conceptual / predict_output / debug / scenario / optimization (MCQ response), no code execution
- **Data Engineering** — 91 practice (30 easy / 35 medium / 26 hard) + 110 mock-only (0 easy / 34 medium / 76 hard), conceptual / scenario / debug (MCQ response), no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Data Modeling** — 81 practice (25 easy / 31 medium / 25 hard) + 97 mock-only, conceptual / scenario / debug (MCQ response), no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Statistics** — 100 practice (31 easy / 43 medium / 26 hard) + 134 mock-only (0 easy / 66 medium / 68 hard: 47 standalone + 21 chain questions from 7 Interview Loop chains), **dual-subtype**: each question is either `conceptual` (MCQ response) or `numerical` (Python code execution); `eval_kind="mixed"`, `unlock_profile="code"`, `mixed_subtype=true`, `in_mixed_mock=false`
- **ML Fundamentals** — 100 practice (30 easy / 40 medium / 30 hard) + 143 mock-only (0 easy / 59 medium / 84 hard: 68 standalone + 16 chain children from 8 chains), conceptual / scenario / predict_output / debug (MCQ response), no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Experimentation** — 87 practice (30 easy / 33 medium / 24 hard) + 104 mock-only (0 easy / 45 medium / 59 hard: 39 standalone + 20 chain children from 10 chains), conceptual / scenario / predict_output / debug (MCQ response), no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| Query execution | DuckDB (in-memory, loaded once at startup from CSVs) |
| Payments | Dual-rail: Razorpay (Orders + Subscriptions, INR/India) + Paddle (Merchant of Record, USD/global) — both with verified webhooks |
| Rate limiting | Redis (production) / in-memory fallback (development) |
| Testing | pytest + httpx (backend), Vitest + React Testing Library (frontend unit), Playwright (frontend e2e) |
| Observability | Sentry (backend + frontend error capture), PostHog (product analytics) |

---

## Content footprint

Mock-only questions (`mock_only: true`) live in the same JSON files as practice questions but are excluded from the practice catalog. They appear only in mock sessions for Pro/Elite users. IDs share the same TXNNN scheme, allocated at the top of each difficulty range.

| Track | Easy (practice + mock) | Medium (practice + mock) | Hard (practice + mock) | Format | Location |
|---|---|---|---|---|---|
| SQL | 37 + 0 | 50 + 62 | 31 + 103 | SQL query via DuckDB | `backend/content/questions/` |
| Python | 33 + 0 | 30 + 50 | 18 + 53 | Algorithm function, test cases | `backend/content/python_questions/` |
| Pandas | 28 + 0 | 40 + 51 | 25 + 63 | DataFrame function, output comparison | `backend/content/pandas_questions/` |
| PySpark | 40 + 0 | 45 + 75 | 42 + 75 | conceptual / predict_output / debug / scenario / optimization (MCQ) | `backend/content/pyspark_questions/` |
| Data Engineering | 30 + 0 | 35 + 34 | 26 + 76 | conceptual / scenario / debug (MCQ) | `backend/content/data_engineering_questions/` |
| Data Modeling | 25 + 0 | 31 + 46 | 25 + 51 | conceptual / scenario / debug (MCQ) | `backend/content/data_modeling_questions/` |
| Statistics | 31 + 0 | 43 + 66 | 26 + 68‡ | conceptual (MCQ) + numerical Python | `backend/content/statistics_questions/` |
| ML Fundamentals | 30 + 0 | 40 + 59 | 30 + 84† | conceptual / scenario / predict_output / debug (MCQ) | `backend/content/ml_fundamentals_questions/` |
| Experimentation | 30 + 0 | 33 + 45 | 24 + 59 | conceptual / scenario / predict_output / debug (MCQ) | `backend/content/experimentation_questions/` |

†ML Fundamentals hard mock-only: 68 standalone (including 8 chain parents) + 16 chain children from 8 chains.
‡Statistics hard mock-only: 47 standalone + 21 chain questions from 7 Interview Loop chains (7 parents + 14 follow-ups). Ratio = 1.34× (above the 1.15–1.25× band; deliberate — chains exclusively power the Elite Interview Loop and do not compete with practice content or benchmarks).

**Practice totals:** SQL 118 · Python 81 · Pandas 93 · PySpark 127 · Data Engineering 91 · Data Modeling 81 · Statistics 100 · ML Fundamentals 100 · Experimentation 87 = **878 practice questions**  
**Mock-only totals:** SQL 165 · Python 103 · Pandas 114 · PySpark 150 · Statistics 134 · ML Fundamentals 143 · Experimentation 104 · Data Modeling 97 · Data Engineering 110 = **1,120 mock-only questions** (Pro/Elite only)

See [docs/content-authoring.md](docs/content-authoring.md) for the full mock-only authoring spec.

- **Sample questions:** All 9 tracks × 3 difficulties × 3 questions = **81 dedicated sample questions** total. Sample questions live in `backend/content/sample_questions/<track>.json` and use the compact TXS ID format (SQL: 111–133, Python: 211–233, Pandas: 311–333, PySpark: 411–433, DE: 511–533, DM: 611–633, Statistics: 711–733, ML: 811–833, Exp: 911–933). Sample questions are never drawn from the practice or mock pools.
- **Learning paths:** 96 total — SQL: 11, Python: 11, Pandas: 9, PySpark: 14, Data Engineering: 9, Data Modeling: 11, Statistics: 11, ML Fundamentals: 12, Experimentation: 8. A path's `level` is **content-driven** — it reflects the questions actually in it (difficulty + prerequisite position + concept role), not a fixed template; per-level counts are whatever the content warrants. Each track has **at least one** `foundational` path (the UX entry point, ordered first); most have 2–3. Paths are curated 5–9 question walks through a *pattern* (practitioner skill — see `docs/content-authoring.md` §Paths). Paths do not unlock anything; unlocks follow the standard practice thresholds.
- Every question has `hints` (currently 1–3 entries across the bank; new content should target the active hint ladder) and `concepts` (semantic pattern tags surfaced as pills)
- SQL questions have a `companies` field (`["Meta", "Stripe", ...]`) used for the company filter in SidebarNav
- SQL schemas validated against committed CSV headers at catalog load time
- Full concept coverage per track and authoring rules: see [`docs/content-authoring.md`](docs/content-authoring.md)

---

## Repository layout

```
sql-interview-practice/
├── backend/
│   ├── content/questions/          # SQL challenge question JSON (easy.json, medium.json, hard.json)
│   ├── content/python_questions/   # Python algorithm questions
│   ├── content/pandas_questions/ # Pandas questions
│   ├── content/pyspark_questions/  # PySpark MCQ questions
│   ├── content/paths/              # Learning path configs (slug, title, description, topic, questions[])
│   ├── datasets/                   # Committed CSVs + metadata JSON
│   ├── middleware/                 # Request context, request_id, X-Request-ID
│   ├── routers/                    # auth, system, catalog, questions, sample, plan, razorpay, dashboard, insights, submissions, mock, paths, spa
│   ├── scripts/                    # Dataset generator, anonymous user cleanup
│   ├── tests/                      # API, evaluator, rate limiter tests
│   ├── alembic/                    # Postgres migrations
│   ├── main.py                     # App wiring, middleware, routers, lifespan
│   ├── config.py                   # Env settings, CORS, rate limiter, dist path
│   ├── db.py                       # Async Postgres pool, all product-state persistence
│   ├── database.py                 # DuckDB engine startup, table loading, cursor access
│   ├── evaluator.py                # Query execution, timeout, comparison normalization
│   ├── unlock.py                   # Pure plan + solve-history → unlock policy
│   ├── questions.py                # SQL catalog loader/validator
│   ├── sample_questions.py         # SQL sample catalog loader
│   ├── python_questions.py         # Python algorithm catalog loader
│   ├── pandas_questions.py    # Pandas catalog loader
│   ├── pyspark_questions.py        # PySpark catalog loader
│   ├── data_engineering_questions.py # Data Engineering catalog loader
│   ├── data_modeling_questions.py  # Data Modeling catalog loader
│   ├── statistics_questions.py     # Statistics dual-subtype catalog loader (conceptual + numerical)
│   ├── ml_fundamentals_questions.py # ML Fundamentals catalog loader (conceptual / scenario / predict_output / debug, MCQ response)
│   ├── experimentation_questions.py # Experimentation catalog loader (conceptual / scenario / predict_output / debug, MCQ response)
│   ├── path_loader.py              # Learning path catalog loader (reads content/paths/*.json)
│   ├── sql_guard.py                # Read-only SQL validation
│   ├── python_guard.py             # AST-based Python code validator
│   ├── python_evaluator.py         # Spawns sandbox, enforces timeout, compares results
│   ├── python_sandbox_harness.py   # Subprocess harness for Python/Pandas execution
│   ├── progress.py                 # Challenge/sample persistence wrappers
│   ├── rate_limiter.py             # In-memory and Redis-backed limiter
│   └── models.py / deps.py         # Pydantic models and shared dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js                  # Route tree
│   │   ├── App.css                 # Global styles and design tokens (single stylesheet)
│   │   ├── api.js                  # Axios client, base URL resolution
│   │   ├── catalogContext.js       # Catalog state and refresh
│   │   ├── contexts/
│   │   │   ├── AuthContext.js      # Auth state (user, loading, refreshUser)
│   │   │   └── TopicContext.js     # TRACK_META, TopicProvider, useTopic()
│   │   ├── components/
│   │   │   ├── AppShell.js         # Challenge workspace shell, sidebar, track switcher
│   │   │   ├── SidebarNav.js       # Question list, lock/solved/next states + bookmarks rail with question-form badges and question-form filters for reasoning tracks
│   │   │   ├── CodeEditor.js       # Language-agnostic Monaco editor wrapper
│   │   │   ├── SQLEditor.js        # Thin re-export of CodeEditor with language="sql"
│   │   │   ├── ResultsTable.js    # Tabular output with sticky headers + horizontal overflow cue
│   │   │   ├── SchemaViewer.js    # Schema browser with search + click-to-copy columns
│   │   │   ├── TestCasePanel.js    # Python algorithm test case results
│   │   │   ├── PrintOutputPanel.js # Captured stdout from Python execution
│   │   │   ├── VariablesPanel.js   # Available DataFrames for Pandas questions
│   │   │   ├── MCQPanel.js         # Radio-button MCQ for PySpark questions
│   │   │   ├── ConceptPanel.js     # Slide-in concept explanation panel opened from concept pills
│   │   │   ├── Skeleton.js         # Reusable shimmer/loading primitive used across workspace and dashboard
│   │   │   ├── ToastViewport.js    # Global in-app milestone/unlock toast stack
│   │   │   ├── TrackProgressBar.js # Reusable horizontal progress bar (animated fill)
│   │   │   ├── PathProgressCard.js # Path card with topic dot, progress bar, CTA (used on Landing + TrackHub)
│   │   │   ├── OnboardingTooltip.js # First-visit walkthrough tooltip for landing track/sample discovery
│   │   │   └── Topbar.js           # Shared top nav bar used by all standalone pages (Practice dropdown, Mock, Dashboard, auth)
│   │   └── pages/
│   │       ├── LandingPage.js          # Fixed-topbar landing with track/sample tabs and compact progress panels
│   │       ├── QuestionPage.js         # Topic-aware question page (all 4 tracks, question-form badges, prompt-guidance/evidence chrome, shortcuts, draft autosave, soft timer, bookmarks, unlock/streak milestone toasts)
│   │       ├── TrackHubPage.js         # Per-track landing (progress, next-up summary, question-form preview, concept preview, paths)
│   │       ├── LearningPath.js         # Curated path page at /learn/:topic/:slug (breadcrumb, progress, completion banner)
│   │       ├── LearningPathsIndex.js   # Index of all paths at /learn and /learn/:topic (grouped)
│   │       ├── ProgressDashboard.js    # Cross-track progress + coaching insights at /dashboard
│   │       ├── MockHub.js              # Mock interview lobby at /mock — two-column desktop lobby (left: hero + mode cards + benchmark blueprint / drill planner + config; right rail: sticky session brief + start CTA); analytics and history below; collapses to single-column on mobile
│   │       ├── MockSession.js          # Active mock session + post-mortem insights at /mock/:id with benchmark/drill-aware session framing and follow-up CTAs
│   │       ├── SampleHubPage.js        # Sample discovery surface at /sample — 9-track × 3-difficulty grid, tried/total markers when logged in
│   │       ├── SampleQuestionPage.js   # Topic-aware sample page with per-question draft autosave and in-page track + difficulty switcher
│   │       ├── AuthPage.js
│   │       ├── ResetPasswordPage.js    # Password reset token consumer at /auth/reset-password
│   │       └── VerifyEmailPage.js      # Email verification token consumer at /auth/verify-email
│   └── package.json
├── docs/                           # Architecture and design reference docs (see docs/README.md)
├── TODO.md                         # Phased product upgrade backlog
├── CLAUDE.md                       # This file
├── README.md                       # Setup and usage guide
├── Dockerfile                      # Single-service production image
├── docker-compose.yml              # Local Postgres + Redis stack
└── railway.json                    # Railway deployment config
```

---

## Frontend routes

Full route tree: [`docs/frontend.md`](docs/frontend.md) §Route tree.

`:topic` values: `sql` | `python` | `pandas` | `pyspark` | `data-engineering` | `data-modeling` | `statistics` | `ml-fundamentals` | `experimentation`

---

## Landing page structure

Editorial 8-section layout. All sections use max-width 1040px inner wrapper (`lp-inner`). Sections animate in on scroll via `IntersectionObserver` (skipped for `prefers-reduced-motion`).

```
TOPBAR
  "datathink"                    [Practice ▾] [Mock] [Dashboard] [name · Sign out] or [Sign in]

01 · HERO  (all users)
  Logged-out: 2-col grid — left: interview-urgent eyebrow + h1 + copy + CTAs ("Try a free sample →" / "Find your role ↓")
              right: HeroIDE — character-by-character SQL typing animation, then cycles through all tracks via hardcoded IDE_TRACKS array (high-signal practitioner scenarios per track; NOT derived from trackRegistry.js)
  Logged-in:  3-card strip (Resume · Dashboard · Mock) with accent-border hover

02 · THESIS  (all users)
  3-column editorial — "Recognition ≠ reasoning" · "Depth, not breadth" · "Real engines"
  Each column: mono index number, h3 title, copy

03 · WRONG / RIGHT  (all users)
  2-col diff table — left = "what candidates do", right = "what earns the job"
  Right column rows animate in staggered on intersection

04 · ROLE SELECTOR  (all users)
  tablist with 4 roles: Data Analyst · Data Engineer · Analytics Engineer · Data Scientist
  Each tab panel: ordered list of relevant tracks as cards (left accent border in track color)
  Coming-soon tracks shown with "Coming soon" badge; no CTA link

05 · PROOF STRIP  (all users)
  Stat row — N tracks · N+ questions (count-up animation on scroll)

06 · TRACKS INDEX  (all users)
  Dense list of all 8 tracks (all live) from ALL_TRACK_SLUGS
  Each row: color dot · track name · description · question count · format tag · "Enter →" or "Soon"

07 · GUIDED PROGRESSIONS  (all users)
  PathsShowcaseSection — calls /api/paths. Pitches curriculum STRUCTURE + BREADTH, funnels to /learn (never deep-links a single path).
  Left: one featured track's graded arc (SQL) as a connected numbered spine (foundational→advanced made visible, first 5 steps + "+N more"), linking to /learn/:topic.
  Right: breadth panel — "N tracks · M guided paths" stat + every track as a color-dotted chip with its path count, each → /learn/:topic.
  Footer: single primary CTA "Explore all paths →" → /learn; logged-in users with an unfinished path also get a "Continue: <path>" resume hook (the one legitimate leaf deep-link).
  No shuffle, no per-card progress bars (marketing surface shows the curriculum, not the user's emptiness).

08 · PRICING  (all users except `lifetime_elite`)
  Free / Pro / Elite columns · monthly + lifetime CTAs
  Pro users see pricing (so they can discover Elite upgrade)
```

---

## Design system

Behavior contracts:
- **Single global stylesheet** — `frontend/src/App.css`. No CSS framework, no CSS modules, no inline styled-components. New styles go in `App.css`.
- **Active theme: Forest & Ink — light-only at launch.** Dark mode is **deferred to a future version** and sits **dormant**: the `[data-theme="dark"]` CSS (App.css), the CodeEditor forest/charcoal switch, and the `isDark` logo-src logic all remain in the codebase but are unreachable — `ThemeProvider` (App.js) and the `index.html` pre-paint bootstrap both lock `theme='light'` / `isDark=false`, ignoring `localStorage` + OS `prefers-color-scheme` (and flushing any stored pref), and the toggle UI is removed from `Topbar`. Re-enabling dark is a near-one-line flip in both places. Two-tone editor (always dark): forest-dark under light pages (the charcoal `#16181C` dark-page variant is dormant). See `docs/decisions/DECISIONS.md` (2026-06-17 defer-dark) + `docs/design/color-palette.md` § Code editor & sandbox surfaces.
- **Track colors are fixed** — not overridden by theme changes. Track color is part of the track's identity.

Token values, full palette, typography, and component specs: [`docs/design/color-palette.md`](docs/design/color-palette.md) (canonical) and [`docs/frontend.md`](docs/frontend.md) §Design system.

---

## Backend behaviour

**SQL:** `sql_guard.py` → `evaluator.py` → DuckDB. Parser-based read-only validation (incl. a max-joins complexity cap, currently 9); 3-second timeout. Submit: both queries run → DataFrames normalized + compared on the **full** result (sound — no `head(200)` truncation); only a 200-row display preview is returned (`total_rows`/`truncated`). Comparison is order-insensitive unless the expected query has a trailing `ORDER BY`, in which case it is **tie-tolerant order-sensitive** (same multiset + same `ORDER BY`-key sequence; tied rows may permute), and the grading DuckDB connection runs **single-threaded** for float-aggregation determinism — see `docs/backend.md` § SQL evaluation path. On correct+structure_correct submissions, `_compute_quality()` runs DuckDB `EXPLAIN` on both queries and returns `{ efficiency_note, style_notes, complexity_hint, alternative_solution }` for the Solution Analysis UI in `QuestionPage.js`. On wrong answers where the user and expected results share the same shape (same row+column count but wrong values), style notes are surfaced as a partial quality object (close-miss feedback). Repeat identical wrong attempts are detected via `get_latest_submission()` and a nudge message is prepended to feedback.

**Python/Pandas:** `python_guard.py` → `python_evaluator.py` → subprocess harness. AST guard, 512 MB RLIMIT_AS; 5-second timeout (algorithm) / 12-second (pandas data mode — full-result grading serializes a larger result). Pandas grades on the full result and returns a 200-row display preview (`total_rows`/`truncated`); datetime columns are ISO-serialized + date-normalized (no hand-formatting needed).

**Sandbox security layers (as of 2026-06-06):**
1. **AST guard** (`python_guard.py`) — blocks dangerous bare names (`globals`, `locals`, `getattr`, `eval`, `exec`, `__builtins__`, `__import__`, etc. via `visit_Name`), dunder chains (`__class__`, `__globals__`, `__subclasses__`, frame/traceback walks via `visit_Attribute`), all imports except the per-track allowlist, and pandas/numpy filesystem methods. Red-teamed in `tests/test_guard_redteam.py` (34 escape attempts all BLOCKED, 13 legit snippets PASS).
2. **Scrubbed subprocess env** (`python_evaluator._sandbox_env`) — the harness subprocess sees only `PATH/HOME/LANG/locale/TMPDIR/TZ` + Python encoding flags. Every production secret (`DATABASE_URL`, `RAZORPAY_KEY_SECRET`, OAuth secrets, `RESEND_API_KEY`, `SENTRY_DSN`) is absent. No `PYTHONPATH`, so user code cannot import backend modules. Tested in `tests/test_sandbox_env_isolation.py`.
3. **In-process OS isolation** (`_sandbox_preexec`) — `os.setsid()` (new process group, SIGKILL kills the whole tree) + `os.chdir('/tmp')` (cwd away from app source).
4. **Seccomp egress filter** (`_install_seccomp_filter`, Linux) — per-process `pyseccomp` filter denying the network-syscall family (`socket`/`connect`/`sendto`/…), so a guard escape cannot open a socket (no phone-home / exfiltration / internal scan). Railway grants no `NET_ADMIN`/`--security-opt`, so this in-process filter is the egress block + seccomp profile. Validated in CI (`tests/test_sandbox_seccomp.py`). Deps: `pyseccomp` + `libseccomp2`; fails open if absent.
5. **Read-only app dir + non-root** — Dockerfile runs the app as non-root `appuser` with `/app` left **root-owned** (no `chown`), so the sandbox can read+execute but not write app code; only `/tmp` is writable. `PYTHONDONTWRITEBYTECODE=1`.
6. **Resource caps (category-3 / DoS)** — per-subprocess `RLIMIT_AS` 512 MB (memory bomb), `RLIMIT_NPROC` 256 (fork bomb), `RLIMIT_FSIZE` 64 MB (disk fill), `RLIMIT_CPU` 14 s (backstop). Wall-clock timeouts 5 s/12 s enforced via `Popen` + **process-group SIGKILL** (`_kill_process_group` → `os.killpg`), so a forked child cannot outlive the timeout (plain `subprocess.run` only kills the direct child). Output caps (64 KB stdout, 512 KB result). **All code execution runs off the single event loop** (`backend/offload.py`): subprocess sandboxes via `asyncio.to_thread` under the global `MAX_CONCURRENT_EXECUTIONS` semaphore (default **cores − 2**), and DuckDB SQL serialized behind a process-wide lock (single in-process engine; concurrent connection use segfaults). Applied uniformly across every code-exec path (practice SQL/Python/Pandas, statistics, sample, mock) — so a slow execution never freezes other users (head-of-line blocking, measured + fixed: see `docs/decisions/DECISIONS.md` 2026-06-08 offload entry and `backend/loadtest/`) and the semaphore now genuinely bounds concurrency + peak sandbox memory. Container RAM cap = the one remaining Railway-dashboard item (Settings → Scale → **Replica Limits**; size above app + semaphore×512 MB). Tests: `tests/test_sandbox_resource_limits.py` (infinite loop, memory bomb, fork-bomb killpg, output flood, recursion) + `tests/test_concurrency_smoke.py` (off-loop + bounded + SQL-serialized). See `docs/deployment.md` § Sandbox security hardening and § Concurrency & scaling model.

**PySpark:** No execution. `selected_option` compared to `correct_option`. Explanation always returned.

**Unlock model** (pure policy in `unlock.py`, applied independently per topic):

| Plan | Access |
|---|---|
| Free | All easy. Medium/hard unlock in batches as you solve questions (thresholds differ by track — see below). Hard is capped. |
| Pro | All easy + all medium + all hard (no cap) |
| Elite | Full catalog |

**Free-tier unlock thresholds (code tracks — SQL, Python, Pandas):**
- Medium: 8 easy → 3 medium · 15 easy → 8 medium · 25 easy → all medium
- Hard: 8 medium → 3 hard · 15 medium → 8 hard · 22 medium → 15 hard *(cap: 8)*

**Free-tier unlock thresholds (MCQ tracks — PySpark / Data Engineering):** option-hiding balances the lower effort per question:
- Medium: 10 easy → 3 medium · 17 easy → 8 medium · 25 easy → all medium
- Hard: 12 medium → 5 hard *(cap: 5)*

Locked MCQ questions return 200 with `locked: true` and no `options` or `correct_option` (stem visible; options and explanation hidden). Submitting a locked MCQ returns 403.

**Learning paths and unlocks:** Paths are curated walks through the practice catalog and **do not unlock questions**. A user who solves a path question gets the same `solved` state and threshold advancement as solving from practice directly. See `docs/content-authoring.md` §Paths for the canonical path model (patterns, roles, validator integrity rules).

**Mock modes (canonical, post-Phase-3):** `benchmark` (fixed-shape track readiness signal, or role-based Mixed benchmark), `custom` (1–5 Q, 10–90 min — user-tuned to competency), `interview_loop` (Elite only — chain-driven iterative interviewer dialogue). Legacy `30min` (Sprint drill) and `60min` sessions in history are read-only; they cannot be started new. Mixed track requires role selection (Data Analyst / Data Engineer / Analytics Engineer / Data Scientist) for both benchmark and custom. Single source of truth: `docs/features/mock.md`.

**Elite-only mock features:** `focus_concepts` filter (available on all three modes), Interview Loop (1 chain per session — parent + all follow-ups atomic, time = 15 min × chain length), deep analytics with per-dimension Loop breakdown, readiness scores + study plan, session debrief coaching narrative.

**Mock chain atomicity:** Chains appear **only** in Interview Loop sessions. Benchmark and custom sessions are standalone-questions only (no dynamic follow-up injection). Parent questions with `follow_ups[]` travel as an atomic unit in Interview Loop — entire chain whole, never split. Consumed at session start in `mock_chain_consumption` table; reclaimable within 2-minute discard window. Each chain is drawn once **by default**; once a user has completed every chain at a (track, difficulty) the exhausted state offers **consent-gated replay** (`/start` with `replay: true`) rather than a hard dead-end. Single source of truth: `docs/features/mock.md`.

**Plan-tier matrix:** Full matrix lives in `docs/features/mock.md` as the canonical source of truth. Summary:
- **Free** — 1 `benchmark` per rolling 7 days, easy only, any track/Mixed (with role). No `custom`. No `interview_loop`. Practice-pool questions only.
- **Pro** — 3 `benchmark`/day + 3 `custom`/day (independent counters), any difficulty. Mock-only content pool unlocked. No `interview_loop`.
- **Elite** — Unlimited (soft abuse cap only). + `focus_concepts`. + `interview_loop`. + deep analytics + debrief.

**Benchmark composition:** PySpark keeps its own format-targeted benchmark template, Statistics benchmarks enforce `1 numerical + 2 conceptual`, and the other reasoning tracks now use track-specific `type` targets during benchmark selection instead of reusing PySpark's format sampler.

**Dashboard insights:** `GET /api/dashboard/insights` computes per-track solve count, median solve time, and accuracy from `submissions`; weakest concepts (bottom 3 with >=3 attempts — **counts both practice and mock attempts**: a miss under mock-interview pressure is a strong weak-concept signal, so the concept lookup spans practice + mock-only questions. The *drill* the weak concept links to stays **practice-only** — mock-only questions are never served in a drill); deterministic cross-track pacing insight (only when slow-fast gap >= 60s); consecutive `streak_days` ending today; and (Elite only) `readiness_scores` (per-track 0–100 score from practice coverage + mock accuracy + concept strength) and `study_plan` (ordered list of 3–5 personalised next steps). Results are cached in-process for 60 seconds per user. Each weak concept surfaces as a **Pro+ concept drill** — the coaching *Drill* CTAs (dashboard focus card + weak-areas panel, logged-in landing weak-spots, mock post-mortem) link to `/practice/{track}?drill={concept}`, backed by `GET /api/practice/drill` (family-aware, unsolved-first), which renders a scoped practice walk on `QuestionPage` where **Next stays on the concept until done**. On the dashboard and logged-in landing the matching learning path is offered as an honest secondary; the **mock post-mortem is concept-drill-only** (debrief next-step + a per-weak-concept `Drill →` in the concept breakdown — no learning-path link anywhere in mock, so every weak concept is independently drillable and the user chooses). Distinct from the mock **custom-drill** mode (`focus_concepts`). See [`docs/features/dashboard.md`](docs/features/dashboard.md) + [`docs/frontend.md`](docs/frontend.md) §Concept drill.

**Identity:** Anonymous visitors get real user rows + session cookies. Registration upgrades the session in place. Login merges anonymous progress into an existing account. `GET /api/auth/me` returns identity plus streak metadata (`streak_days`, `streak_at_risk`) used by the workspace topbar and streak milestone toasts on solves. Session cookie is `HttpOnly` + `SameSite=Lax` (and secure in production by default).

**Operator plan overrides:** The `users` table carries `plan_override` (text, nullable) and `plan_override_until` (timestamptz, nullable). At every auth resolution point, `_effective_plan()` in `db.py` returns the override if it's non-null and not expired, otherwise the base `plan` column. No cron — expiry is lazy, evaluated per request. Managed via `POST/DELETE /api/admin/grant-plan` and `GET /api/admin/grants`, all protected by `Authorization: Bearer <ADMIN_SECRET>`. `ADMIN_SECRET` must be set in the Railway environment (strong random value, ≥32 bytes). If unset, admin endpoints return 503. This is internal operator tooling — never user-facing, no coupon, no Razorpay interaction. Full contract: [`docs/features/pricing.md`](docs/features/pricing.md) §Admin operator grants and [`docs/backend.md`](docs/backend.md) §Admin.

**OAuth + magic-link hardening:** OAuth `/authorize` now creates a short-lived, one-time server-side `state` token validated+consumed in `/callback`. User-agent/IP-prefix mismatches are logged as risk signals but are best-effort only (do not hard-block valid callbacks). Google authorize scope is `openid email profile` and GitHub authorize scope is `read:user user:email`. OAuth callbacks are configured per provider via `GOOGLE_REDIRECT_URI` and `GITHUB_REDIRECT_URI` (required in production when the corresponding provider credentials are set). Magic-link auth is available via `POST /api/auth/magic-link` and `GET /api/auth/magic-link/callback` with short-lived, single-use tokens.

**Auth hardening:** Reserved local-part email prefixes are blocked on registration. Failed sign-in attempts are tracked in Postgres; after `LOGIN_LOCKOUT_MAX_ATTEMPTS` failures, the account is temporarily locked for `LOGIN_LOCKOUT_WINDOW_MINUTES`.

**CSRF mitigation:** In production, mutating `/api/*` requests that include a session cookie require an `Origin` header matching configured app origins.

**Error shape:** `{ error, request_id }` on all user-facing errors. `X-Request-ID` header on all responses.

**Observability baseline:** Every response includes `X-Response-Time-Ms`; backend logs include request method, path, status, and latency keyed by `request_id`. Optional Sentry capture is enabled when `SENTRY_DSN` is configured (backend) or `VITE_SENTRY_DSN` (frontend — includes Session Replay on errors). In the single-service production deploy, frontend observability settings are injected into the SPA at request time by `routers/spa.py`, so Railway does not need Docker build args for Sentry/PostHog. Production frontend builds emit hidden sourcemaps and upload them to Sentry when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are present. PostHog product analytics fires on key funnel events (`question_submitted`, `question_solved`, `sample_submitted`, `mock_started`, `mock_completed`, `plan_upgrade_started`, `plan_upgraded`) when `VITE_POSTHOG_KEY` is set; SPA page views are tracked on route change.

---

## Key API endpoints

Full per-router endpoint reference: [`docs/backend.md`](docs/backend.md) §API reference. Mock-specific endpoints are also covered in [`docs/features/mock.md`](docs/features/mock.md); payment endpoints in [`docs/features/pricing.md`](docs/features/pricing.md).

---

## Local dev accounts

Three permanent accounts exist in the local Postgres DB for testing and browser preview. Always use these — never create throwaway accounts for plan-level UI testing.

| Plan | Email | Notes |
|---|---|---|
| **Free** | `matt.srini@gmail.com` | Default non-paying user |
| **Pro** | `srinivas.assampally@gmail.com` | Mid-tier; 3 drills/day + 3 benchmarks/day cap, no Elite features (no focus, no Interview Loop) |
| **Elite** | `admin@datathink.co` | Full access — analytics, debrief, focus mode, Interview Loop, unlimited |

**Password for all three:** `Test1234!`

To log in for browser preview, sign in at `/auth` with the email above. The session cookie (`session_token`, `httponly=true`) is set server-side via the Vite proxy (`/api → localhost:8000`), so sign-in through the UI works normally in dev. Use `fetch('/api/auth/login', {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password})})` from `preview_eval` to sign in programmatically.

---

## Local development

Setup, ports, Alembic migration commands, env vars: [`docs/deployment.md`](docs/deployment.md) §Local development.

---

## Docs index

Canonical docs index: [`docs/README.md`](docs/README.md). It maps every doc to its area of ownership — architecture, specs, features, content/authoring, runbooks. Start there for any task that needs reference material.

For question authoring specifically: the universal agent at [`.github/agents/question-authoring.agent.md`](.github/agents/question-authoring.agent.md) is the mandatory entry point, with per-track knowledge in [`docs/tracks/`](docs/tracks/) and the concept registry in [`docs/concept-taxonomy.md`](docs/concept-taxonomy.md).
