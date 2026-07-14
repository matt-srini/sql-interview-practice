# CLAUDE.md — Project context for AI assistance

This file is the canonical context reference for Claude in this repository. **Keep it current.**
Full docs index: [`docs/README.md`](docs/README.md).

---

## Roles and perspective

Work simultaneously from five vantage points:
- **Senior full-stack engineer** — know the full request lifecycle (auth → lock check → guard → execute → evaluate → progress), where state lives (Postgres vs. DuckDB vs. in-process), and the scaling bottlenecks.
- **UI/UX designer** — professional productivity tool used in long sessions. Respect the design language: single `App.css` token system, two-tone editor (always dark), 900 px breakpoint, spacing/radius conventions.
- **User-behaviour expert** — users are under interview pressure. Anonymous-first identity, in-place registration, and persistent progress are intentional product choices. Every friction point costs confidence.
- **Curriculum designer** — 965 practice questions with intentional difficulty progressions, real-world datasets, and semantic concept tags. Changes to unlock rules or question ordering must preserve the learning arc.
- **Product-minded operator** — three subscription tiers (Free / Pro / Elite) are the revenue model. The unlock gates, rate limiting, and error shapes (`{ error, request_id }`) exist for real operational reasons.

---

## Platform position

datathink is a **premium reasoning-based data-interview-prep platform**. We train the reasoning that makes someone genuinely effective in a data-driven role; interview success is the consequence, not the goal.

- **Curriculum weighted by reasoning surface, never by interview frequency.** High-reasoning patterns that rarely appear in competitor banks stay; rote-recall patterns that dominate them are rejected.
- **Content benchmarks against the durable contract, never competitor banks.** "LeetCode has this" is not a defence. The defence is: this question exercises reasoning a practicing professional uses years into the role (see [`docs/content-authoring.md`](docs/content-authoring.md) § The one test every question must pass).
- **Premium tier value lives in reasoning depth, not coverage volume.** Volume parity with competitors is not the goal; depth differentiation is.

When two paths satisfy every immediate rule but point in different curriculum directions, pick the one that strengthens reasoning-premium positioning.

---

## Standing instructions

### Pushback checklist
Before agreeing to any request involving design, product, UX, gating, content, or architecture:
1. *Is this the right call?* — Does it solve the root problem or just the surface symptom?
2. *What do premium products do here?* — Linear, Notion, Stripe, Vercel, Figma. Defensible divergence only.
3. *What is the user psychology?* — First-time visitor? Returning user under interview-week pressure?
4. *Does it align with datathink's philosophy?* — "Reasoning first; interview success is the consequence."
5. *What's the long-term cost?* — Maintenance burden, conceptual debt, schema lock-in.
6. *Is this serving the user or a metric?* — Name retention tricks, artificial friction, vanity features.
7. *Would I defend this in a year?*
8. *Is there a cleaner abstraction we're avoiding?* — Name it, even if we ship the hack.
9. *Does this earn its place?* — Every feature, counter, doc, line of UI.

Disagree **plainly with a counter-proposal**. Push back a second time if overruled without reasoning.

### No stale docs
Every change to code, strategy, or product behaviour MUST update the relevant SoT doc in the same commit. When in doubt: update more docs, not fewer.

| Change area | Source-of-truth |
|---|---|
| System design, data flows, execution model, scaling | `docs/architecture.md` |
| **Sandbox threat model** | `docs/specs/sandbox-threat-model.md` (canonical) |
| API routes, routers, backend behaviour, persistence | `docs/backend.md` |
| Pages, components, routes, design tokens, frontend behaviour | `docs/frontend.md` |
| **SEO: titles, meta, robots/sitemap, structured data** | `docs/seo.md` (architecture); runtime: `routers/spa.py` `_build_seo_meta` + `routers/system.py`; canonical domain: `backend/config.py` `CANONICAL_BASE_URL`. No em-dashes in SEO strings. |
| Dataset schema, row counts, edge cases | `docs/datasets.md` |
| Env vars, Docker, Railway, deployment, secrets | `docs/deployment.md` |
| **Pending production DB migrations** | `docs/deployment.md` § Pending production DB migrations |
| Question authoring schema + cross-track contract | `docs/content-authoring.md` |
| Per-track question philosophy, modality, datasets, concept arc | `docs/tracks/<track>.md` |
| Concept-family registry + follow-up dimension taxonomy | `docs/concept-taxonomy.md` |
| Socratic interview-hook inventory | `docs/concept-hooks.md` |
| Pricing tiers, plan entitlements, Razorpay / Paddle flows | `docs/features/pricing.md` |
| **Free-tier access policy (canonical = code)** | `backend/unlock.py` — flat: free = all easy; medium + hard = Pro/Elite. No thresholds, no caps, no ladder (removed 2026-06-29). |
| **User-facing tier comparison** | `frontend/src/data/tierFeatures.js` → rendered at `/pricing`; `docs/tier-wise-features.html` is a manual mirror |
| Plan prices (display vs charge) | `frontend/src/utils/currency.js` (display) + `backend/config.py` (charge) |
| **Mock plan-tier matrix, chain atomicity, Interview Loop** | `docs/features/mock.md` |
| Mock benchmark invariants, blueprint principles | `docs/specs/mock-benchmark-spec.md` |
| Practice modality matrix, eval kinds, subtypes | `docs/specs/practice-modality-spec.md` |
| Platform North Star, role-to-track framing | `docs/specs/platform-north-star.md` |
| Dashboard insights, weak-spot detection, readiness scores | `docs/features/dashboard.md` |
| Product overview, tech stack, content footprint | This file (`CLAUDE.md`) |
| User-facing platform guide | `docs/USERGUIDE.md` |
| **Go-to-market, distribution strategy** | `docs/growth/gtm-strategy.md` + `docs/growth/editorial-calendar.md` + `docs/growth/starter-assets.md` |
| **`/guides` article voice, persona, rules** | `docs/growth/guides-style-guide.md` (senior-practitioner persona, anti-AI-tells, frontmatter + SEO mechanics) |
| New track onboarding process | `docs/track-onboarding.md` |
| **New-track integration surfaces** (every place a track appears; what auto-derives vs. needs a manual entry) | `docs/track-integration-surfaces.md` |
| **Why a decision was made + rejected alternatives** | `docs/decisions/DECISIONS.md` |

### Single-SoT rule
Every fact has exactly one home — a doc or a code file. The SoT declares itself in a header; everywhere else links to it rather than restating. Never silently duplicate a number or gate — that is the mechanism behind every entitlement-drift bug we've hit.

### Docs serve the product
When the right product move conflicts with a doc, **the doc changes** — deliberately, with reasoning in [`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md). The bar: the change must be defensibly better for the product and aligned with datathink positioning. This is the complement of "no stale docs", not a loophole.

### Schema migrations
Every new Alembic migration MUST be applied to production in the same session that authors it. Steps — no exceptions:
1. Write the migration file.
2. **Update `_SCHEMA_SQL` in `backend/db.py`** with the same change. The test DB builds from `_SCHEMA_SQL`, not Alembic — skipping this fails every test that touches the new column.
3. Run against prod: `cd backend && DATABASE_URL="<backend/.env line 4>" ../.venv/bin/alembic upgrade head`
4. Confirm: `../.venv/bin/alembic current` → new revision ID + `(head)`.
5. Update `docs/deployment.md` § Pending migrations — move to "Already applied".
6. Commit: migration file + `_SCHEMA_SQL` update + doc update.

The prod `DATABASE_URL` is in `backend/.env` line 4 (commented out). Read it there — never hardcode. Never ask the user to run the migration. The Alembic chain, `_SCHEMA_SQL`, and live prod DB must never diverge.

### Question authoring
Never edit question JSON directly — always invoke [`.github/agents/question-authoring.agent.md`](.github/agents/question-authoring.agent.md). **No exceptions.** Read the agent file, the relevant [`docs/tracks/<track>.md`](docs/tracks/), and [`docs/concept-taxonomy.md`](docs/concept-taxonomy.md) before authoring. Follow the agent's final checklist literally.

### Per-track framing authority
Each `docs/tracks/<track>.md` "What this track trains" section is the **authoritative framing** for that track. Reinforce it — never substitute your own lens. When a track doc's prose contradicts its difficulty ladder or concept arc, fix the doc to match its stated framing.

### Audits benchmark against durable docs
Never benchmark against the archived Phase 2 tracker (`docs/archive/2026-05-authoring-refactor.md` — historical only). Durable rules live in: [`docs/content-authoring.md`](docs/content-authoring.md), [`docs/tracks/<track>.md`](docs/tracks/), [`docs/concept-taxonomy.md`](docs/concept-taxonomy.md), [`.github/agents/question-authoring.agent.md`](.github/agents/question-authoring.agent.md), [`docs/features/mock.md`](docs/features/mock.md), [`docs/orchestration-runbook.md`](docs/orchestration-runbook.md), and `backend/concept_families.py` / `backend/scripts/validate_content.py`.

### Sonnet handoff model-gate
Any prompt generated by an Opus analysis session that will run bulk authoring/remap on Sonnet must open with the exact text: *"★ STOP — MODEL CHECK: this is a bulk question-AUTHORING + remap task and must run on Sonnet, not Opus (cost). Before doing ANYTHING, confirm the active model is Sonnet. If it is not, do not proceed — tell the user to switch the model to Sonnet, then resume. Do not author, edit, or commit anything until the model is Sonnet."*

### Phase 2 orchestration runbook
Any Opus session running orchestration for a future Phase 2 / Phase 2.5 / Stage C audit must read [`docs/orchestration-runbook.md`](docs/orchestration-runbook.md) before producing any Stage artefact. All active tracks closed Phase 2 by 2026-05-26.

### Always commit
End every session of edits with a `git commit` carrying a specific message. Co-author: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

### Decision log
[`docs/decisions/DECISIONS.md`](docs/decisions/DECISIONS.md) is the append-only **why** layer.
- **Before reversing** anything load-bearing (architecture, content gating, mock contract, pricing, concept taxonomy, curriculum framing): grep the log first. Honor prior entries or supersede deliberately — never silently re-litigate.
- **After any meaningful decision**: append a 4–6 line entry in the same commit. Append-only; never edit past entries except to flip a superseded `Status:`.

### Post-fix verification (question JSON edits)
After any batch fix touching question JSON files — no exceptions:
1. `cd backend && ../.venv/bin/python scripts/validate_content.py` — zero errors. Key validators: `_validate_correct_option_explanation_consistency`, `_validate_no_numeric_option_references`, `_validate_code_reference_reproduces_tests`, `_validate_answer_position_balance` (≤40% per position, ≤5 same-index run), `_validate_answer_length_balance` (≤55% "correct is longest"), `_validate_reverse_preview_matches_key`. After authoring any MCQ batch also run `scripts/check_batch_balance.py <ids>` (batch distribution; group-level dilution can mask batch bias). For `expected_query`/`expected_code` edits also run: `../.venv/bin/python -m pytest tests/test_code_references.py -q`.
2. Manual spot-review: ≥5 changed questions — `correct_option` → keyed option text → explanation conclusion. Explanation must defend the keyed option, not refute it.
3. Hint rewrites: every specific number (ms, ×, p99) in the new hint must appear verbatim in the question stem.

### Path config changes require pytest
After any change to `backend/content/paths/*.json`, `backend/path_patterns.py`, or `_validate_paths` rules, run: `cd backend && ../.venv/bin/python -m pytest tests/test_paths_quality.py tests/test_10_paths.py -q` (must be green). Path-size range, foundational-count, and prereq-DAG guards live only in `test_paths_quality.py` — `validate_content.py` alone is not sufficient.

### Delegation gate — Sonnet / Opus
**≥3 files or a cleanly decomposable batch → delegate to Sonnet subagents** (`Agent` tool, `model: sonnet`) with a deterministic spec (absolute paths, precise changes/values, what to remove, verification commands, and the literal line *"do NOT run git — the orchestrator commits"*). Parallelize disjoint files across agents; keep coupled edits (same file) in one agent. **Opus orchestrates, reviews, and commits — never delegates those.** Sonnet never runs git.

### Git worktree per task
Each task runs in its own worktree (`git worktree add ../<repo>-<task> -b <task-branch>`), not directly on `main`. When done: from the main worktree run `scripts/land.sh <task-branch>` — syncs main from origin (ff-only), fast-forwards main to the branch's commits, pushes, removes the worktree and branch. Invariant after every completed task: `main` ≡ `origin/main`, no leftover worktrees or branches. Trivial meta-changes (one-line doc/config fix) may go straight to `main`.

### CI green invariant
After every push to `origin/main`: `gh run list --commit "$(git rev-parse HEAD)"` then `gh run watch <run-id>`. Fix red CI in the same session — even pre-existing failures. Never end a task on a red `origin/main`. (CI: `backend-tests` = migrations + `validate_content.py` + pytest; `frontend-build` = `npm run lint` + `npm test` + `npm run build`.)

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| Query execution | DuckDB (in-memory, loaded once at startup from CSVs) |
| Payments | Razorpay (Orders + Subscriptions, INR/India) + Paddle (Merchant of Record, USD/global) — both with verified webhooks |
| Rate limiting | Redis (production) / in-memory fallback (development) |
| Testing | pytest + httpx (backend) · Vitest + React Testing Library (frontend unit) · Playwright (e2e) |
| Observability | Sentry (backend + frontend error capture) + PostHog (product analytics) |

---

## Content footprint

**965 practice questions · 1,269 mock-only questions (Pro/Elite) · 90 sample questions (10 tracks × 9)**

| Track | Easy | Medium | Hard | Mock-only | Format | Location |
|---|---|---|---|---|---|---|
| SQL | 37 | 50 | 31 | 196 | SQL via DuckDB | `backend/content/questions/` |
| Python | 33 | 30 | 18 | 103 | Algorithm + test cases | `backend/content/python_questions/` |
| Pandas | 28 | 40 | 25 | 132 | DataFrame + output comparison | `backend/content/pandas_questions/` |
| PySpark | 40 | 45 | 42 | 150 | MCQ (no execution) | `backend/content/pyspark_questions/` |
| Data Engineering | 30 | 35 | 26 | 110 | MCQ (no execution) | `backend/content/data_engineering_questions/` |
| Data Modeling | 25 | 31 | 25 | 97 | MCQ (no execution) | `backend/content/data_modeling_questions/` |
| Statistics | 31 | 43 | 26 | 134 | MCQ + numerical Python | `backend/content/statistics_questions/` |
| ML Fundamentals | 30 | 40 | 30 | 143 | MCQ (no execution) | `backend/content/ml_fundamentals_questions/` |
| Experimentation | 30 | 33 | 24 | 104 | MCQ (no execution) | `backend/content/experimentation_questions/` |
| Product Sense | 30 | 33 | 24 | 100 | MCQ (no execution) | `backend/content/product_sense_questions/` |

**Learning paths:** 103 total (SQL 11 · Python 11 · Pandas 9 · PySpark 14 · DE 9 · DM 11 · Statistics 11 · ML 12 · Exp 8 · Product Sense 7). Curated 5–9 question walks through a practitioner skill pattern. All paths accessible to all users; questions inside follow the standard plan policy (free = easy; Pro/Elite = all). Paths do not unlock questions. See [`docs/content-authoring.md`](docs/content-authoring.md) §Paths.

**Sample questions:** 10 tracks × 3 difficulties × 3 questions = 90 dedicated sample questions. IDs use the TXS format; files live in `backend/content/sample_questions/`. Never drawn from the practice or mock pools.

**Unlock model (flat, plan-based):**

| Plan | Practice access | Mock access |
|---|---|---|
| Free | All easy (all 10 tracks) | 1 benchmark/rolling 7 days, easy only |
| Pro | All easy + medium + hard | 3 benchmark/day + 3 custom/day, any difficulty |
| Elite | Full catalog | Unlimited + Interview Loop + focus_concepts |

Canonical SoT: [`backend/unlock.py`](backend/unlock.py). No thresholds, no ladder, no per-track caps.

---

## Local dev accounts

Three permanent accounts in the local Postgres DB. Always use these — never create throwaway accounts for plan-level UI testing.

| Plan | Email | Notes |
|---|---|---|
| Free | `matt.srini@gmail.com` | Default non-paying user |
| Pro | `srinivas.assampally@gmail.com` | 3 drills/day + 3 benchmarks/day; no Elite features |
| Elite | `admin@datathink.co` | Full access — analytics, debrief, focus, Interview Loop, unlimited |

**Password for all three:** `Test1234!`

Sign in at `/auth`. Programmatic login from `preview_eval`:
```js
fetch('/api/auth/login', {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password})})
```

---

## Product reference

For detailed product behaviour, API reference, component docs, and design tokens — use these canonical docs rather than asking Claude to recall from memory:

| Topic | Doc |
|---|---|
| Backend API, routes, evaluation, sandbox layers | [`docs/backend.md`](docs/backend.md) |
| Frontend routes, components, design system, tokens | [`docs/frontend.md`](docs/frontend.md) |
| Architecture, data flows, repository layout | [`docs/architecture.md`](docs/architecture.md) |
| Local development setup, env vars, Railway | [`docs/deployment.md`](docs/deployment.md) |
| Mock interview modes — full contract | [`docs/features/mock.md`](docs/features/mock.md) |
| Sandbox threat model — all layers + residuals | [`docs/specs/sandbox-threat-model.md`](docs/specs/sandbox-threat-model.md) |
| Per-track philosophy, datasets, concept arc | [`docs/tracks/<track>.md`](docs/tracks/) |
| SEO architecture | [`docs/seo.md`](docs/seo.md) |
| Full docs index | [`docs/README.md`](docs/README.md) |
