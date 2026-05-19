# CLAUDE.md — Project context for AI assistance

This file is the canonical context reference for Claude in this repository.
**Keep it current.** Any time the architecture, design, content, or behaviour of this platform changes, update this file and the relevant files in `docs/` as part of the same task — not as a follow-up.

---

## Roles and perspective

When working in this codebase, think simultaneously from multiple vantage points:

- **Senior full-stack engineer** — Understand the full request lifecycle (auth → lock check → guard → execute → evaluate → progress). Know where state lives (Postgres vs. DuckDB vs. in-process), why the sandbox is layered the way it is, and what the scaling bottlenecks are. Write code that is correct, safe, and won't surprise the next person reading it.

- **UI/UX designer** — This is a professional productivity tool used in long sessions (30–90 min). Every interaction should feel calm, fast, and purposeful. Respect the existing design language: the single `App.css` token system, the two-tone editor (always dark), the 900 px responsive breakpoint, and the spacing/radius conventions. Don't introduce visual noise or layout shifts. When adding UI, ask: does this earn its place?

- **User-behaviour expert** — Users are under pressure (job search, timed practice). Friction costs them confidence. Low-friction flows (anonymous-first identity, in-place registration, persistent progress) are intentional product choices, not oversights. When suggesting changes, consider: how does a first-time visitor experience this? How does a returning user with 40 solves experience it? What happens when a user hits a locked question or an empty state?

- **Curriculum designer** — The 828 practice questions have intentional difficulty progressions, real-world datasets with deliberate edge cases, and semantic concept tags. Changes to unlock rules, question ordering, or content must preserve the learning arc. Don't make hard questions trivially accessible or easy questions feel insulting.

- **Product-minded operator** — Three subscription tiers (Free / Pro / Elite) are the revenue model. The unlock gates are not arbitrary; they create upgrade motivation without being punitive. Rate limiting, error shapes (`{ error, request_id }`), and idempotent webhooks exist for real operational reasons. Changes to these areas need business-level reasoning, not just technical correctness.

Keep all five lenses active at once. The best decisions here satisfy all of them.

---

## Standing instructions

- **Always commit after meaningful changes.** End every session of edits with a `git commit` carrying a clear, specific message (not "update files" — something like "add mock interview mode with timer and session summary"). Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

- **Keep docs in sync automatically.** When a change affects any of the following areas, update the corresponding doc in the same commit:
  | Change area | Doc to update |
  |---|---|
  | System design, data flows, execution model, scaling | `docs/architecture.md` |
  | API routes, routers, backend behaviour | `docs/backend.md` |
  | Pages, components, routes, design tokens | `docs/frontend.md` |
  | Dataset schema, row counts, edge cases | `docs/datasets.md` |
  | Env vars, Docker, Railway, deployment | `docs/deployment.md` |
  | Question authoring rules, curriculum specs | `docs/content-authoring.md` |
  | Product overview, tech stack, content footprint | This file (`CLAUDE.md`) |

- **Keep `CLAUDE.md` in sync.** When content footprint, tech stack, routes, or product behaviour changes, update the relevant section below in the same commit.

- **Parallelize coding work when possible.** If a coding task can be split safely and subagents are available, offload disjoint slices in parallel. Review and integrate results before finishing.

- **Always work directly on `main`.** Never create feature branches, worktrees, or `claude/*` branches. All changes — including multi-step implementations — go directly to `main` and are committed and pushed there.

---

## What this is

A data interview practice platform covering nine tracks. Users write SQL or Python, answer MCQ questions, get instant feedback, and work through gated challenge banks.

**Modes per track:**
- **Challenge mode** — plan-aware unlock rules, persistent progress, 828 practice questions across 9 tracks
- **Mock mode** — 165 additional mock-only questions (Pro/Elite), never shown in practice catalog
- **Sample mode** — 36 sandbox questions across SQL/Python/Pandas/PySpark (3 per track+difficulty), no progress recorded, no login required. Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation samples are auto-sliced from the first 3 practice questions per difficulty (no dedicated sample IDs).

**Tracks:**
- **SQL** — 112 practice (37 easy / 45 medium / 30 hard) + 38 mock-only, DuckDB execution, realistic relational datasets
- **Python** — 95 practice (39 easy / 32 medium / 24 hard) + 20 mock-only, algorithms and data structures, test-case evaluation
- **Pandas** — 86 practice (27 easy / 36 medium / 23 hard) + 26 mock-only, pandas-specific data manipulation, DataFrame comparison
- **PySpark** — 106 practice (41 easy / 39 medium / 26 hard) + 21 mock-only, MCQ / predict-output / debug / scenario formats
- **Data Engineering** — 86 practice (30 easy / 33 medium / 23 hard) + 1 mock-only, MCQ / scenario / debug, no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Data Modeling** — 76 practice (25 easy / 28 medium / 23 hard) + 1 mock-only, MCQ / scenario, no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Statistics** — 97 practice (31 easy / 41 medium / 25 hard) + 8 mock-only, **dual-subtype**: each question is either `conceptual` (MCQ) or `numerical` (Python code execution); `eval_kind="mixed"`, `unlock_profile="code"`, `mixed_subtype=true`, `in_mixed_mock=false`
- **ML Fundamentals** — 90 practice (30 easy / 35 medium / 25 hard) + 25 mock-only, MCQ / scenario / predict-output / debug, no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`
- **Experimentation** — 80 practice (30 easy / 30 medium / 20 hard) + 25 mock-only, MCQ / scenario / predict-output / debug, no code execution; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| Query execution | DuckDB (in-memory, loaded once at startup from CSVs) |
| Payments | Razorpay (Orders + Subscriptions) + verified webhooks |
| Rate limiting | Redis (production) / in-memory fallback (development) |
| Testing | pytest + httpx (backend), Vitest + React Testing Library (frontend unit), Playwright (frontend e2e) |
| Observability | Sentry (backend + frontend error capture), PostHog (product analytics) |

---

## Content footprint

Mock-only questions (`mock_only: true`) live in the same JSON files as practice questions but are excluded from the practice catalog. They appear only in mock sessions for Pro/Elite users. IDs share the same TXNNN scheme, allocated at the top of each difficulty range.

| Track | Easy (practice + mock) | Medium (practice + mock) | Hard (practice + mock) | Format | Location |
|---|---|---|---|---|---|
| SQL | 37 + 0 | 45 + 19 | 30 + 19 | SQL query via DuckDB | `backend/content/questions/` |
| Python | 39 + 0 | 32 + 8 | 24 + 12 | Algorithm function, test cases | `backend/content/python_questions/` |
| Pandas | 27 + 0 | 36 + 12 | 23 + 14 | DataFrame function, output comparison | `backend/content/python_data_questions/` |
| PySpark | 41 + 0 | 39 + 11 | 26 + 10 | MCQ / predict-output / debug / scenario | `backend/content/pyspark_questions/` |
| Data Engineering | 30 + 0 | 33 + 0 | 23 + 1 | MCQ / scenario / debug | `backend/content/data_engineering_questions/` |
| Data Modeling | 25 + 0 | 28 + 0 | 23 + 1 | MCQ / scenario | `backend/content/data_modeling_questions/` |
| Statistics | 31 + 0 | 41 + 0 | 25 + 8 | conceptual MCQ + numerical Python | `backend/content/statistics_questions/` |
| ML Fundamentals | 30 + 0 | 35 + 12 | 25 + 13 | MCQ / scenario / predict-output / debug | `backend/content/ml_fundamentals_questions/` |
| Experimentation | 30 + 0 | 30 + 12 | 20 + 13 | MCQ / scenario / predict-output / debug | `backend/content/experimentation_questions/` |

**Practice totals:** SQL 112 · Python 95 · Pandas 86 · PySpark 106 · Data Engineering 86 · Data Modeling 76 · Statistics 97 · ML Fundamentals 90 · Experimentation 80 = **828 practice questions**  
**Mock-only totals:** SQL 38 · Python 20 · Pandas 26 · PySpark 21 · Statistics 8 · ML Fundamentals 25 · Experimentation 25 · Data Modeling 1 · Data Engineering 1 = **165 mock-only questions** (Pro/Elite only)

See [docs/content-authoring.md](docs/content-authoring.md) for the full mock-only authoring spec.

- **Sample questions:** SQL/Python/Pandas/PySpark: 3 per track × 3 difficulties = 36 total. Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation samples are auto-sliced from the first 3 practice questions per difficulty (no dedicated IDs).
- **Learning paths:** 42 total — SQL: 9, Python: 6, Pandas: 5, PySpark: 5, Data Engineering: 2, Data Modeling: 4, Statistics: 3, ML Fundamentals: 4, Experimentation: 4 (each track has exactly one `starter` and one `intermediate` free shortcut path; additional paths are advanced, mixed free/pro)
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
│   ├── content/python_data_questions/ # Pandas questions
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
│   ├── python_data_questions.py    # Pandas catalog loader
│   ├── pyspark_questions.py        # PySpark catalog loader
│   ├── data_engineering_questions.py # Data Engineering catalog loader
│   ├── data_modeling_questions.py  # Data Modeling catalog loader
│   ├── statistics_questions.py     # Statistics dual-subtype catalog loader (conceptual + numerical)
│   ├── ml_fundamentals_questions.py # ML Fundamentals catalog loader (MCQ / scenario / predict-output / debug)
│   ├── experimentation_questions.py # Experimentation catalog loader (MCQ / scenario / predict-output / debug)
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
│   │       ├── LearningPathsIndex.js   # Index of all paths at /learn and /learn/:topic (grouped + in-progress rail)
│   │       ├── ProgressDashboard.js    # Cross-track progress + coaching insights at /dashboard
│   │       ├── MockHub.js              # Mock interview lobby at /mock (mode/track/difficulty selection + empty state)
│   │       ├── MockSession.js          # Active mock session + post-mortem insights at /mock/:id
│   │       ├── SampleQuestionPage.js   # Topic-aware sample page with per-question draft autosave
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

```
/                              → LandingPage (editorial landing — hero, role selector, 7-track index, pricing)
/auth                          → AuthPage (register / sign in / forgot password / OAuth)
/auth/reset-password           → ResetPasswordPage (consume reset token, set new password)
/auth/verify-email             → VerifyEmailPage (consume email verification token)
/dashboard                     → ProgressDashboard (cross-track progress)
/mock                          → MockHub (mode/track/difficulty selector + history)  [AuthRequired]
/mock/:id                      → MockSession (active session + inline summary)        [AuthRequired]
/learn                         → LearningPathsIndex (all paths, grouped by track, topic pills)
/learn/:topic                  → LearningPathsIndex (filtered to one track)
/learn/:topic/:slug            → LearningPath (curated path — breadcrumb, progress bar, question list)
/sample/:topic/:difficulty     → SampleQuestionPage (topic-aware sample mode)
/sample/:difficulty            → redirect → /sample/sql/:difficulty
/practice/:topic               → TopicShell (TopicProvider + CatalogProvider + AppShell)
  /practice/:topic             → TrackHubPage (hub page when no question selected)
  /practice/:topic/questions/:id → QuestionPage (topic-aware)
/practice/questions/:id        → redirect → /practice/sql/questions/:id (legacy)
/practice                      → redirect → /practice/sql
/questions/:id                 → redirect → /practice/sql/questions/:id (legacy)
```

`:topic` values: `sql` | `python` | `python-data` | `pyspark` | `data-engineering` | `data-modeling` | `statistics` | `ml-fundamentals` | `experimentation`

---

## Landing page structure

Editorial 8-section layout. All sections use max-width 1040px inner wrapper (`lp-inner`). Sections animate in on scroll via `IntersectionObserver` (skipped for `prefers-reduced-motion`).

```
TOPBAR
  "datathink"                    [Practice ▾] [Mock] [Dashboard] [name · Sign out] or [Sign in]

01 · HERO  (all users)
  Logged-out: 2-col grid — left: eyebrow + h1 + copy + CTAs ("Start thinking →" / "Find your track ↓")
              right: HeroIDE — character-by-character SQL typing animation, then cycles through all tracks via hardcoded IDE_TRACKS array (one demo MCQ/code frame per track; NOT derived from trackRegistry.js)
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
  Paths section — calls /api/paths; renders PathProgressCard per path (same component as TrackHub)

08 · PRICING  (all users except `lifetime_elite`)
  Free / Pro / Elite columns · monthly + lifetime CTAs
  Pro users see pricing (so they can discover Elite upgrade)
```

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Active theme: Forest & Ink.** Full token reference: [`docs/design/color-palette.md`](docs/design/color-palette.md).

**Key tokens:**
```
--bg-page:         #F5F7F4   (dark: #0D1A10)
--surface-card:    #FFFFFF   (dark: #132218)
--accent:          #166534   (dark: #4ADE80)
--text-strong:     #14291B   (dark: #E8F5E9)
--text-secondary:  #4B6858
--success:         #15803D
--warning:         #C47F17
--danger:          #D94F3D
--radius-lg: 20px  --radius-md: 14px  --radius-sm: 10px
```

**Logo mark:** two diagonal rounded squares (big bottom-left, small top-right) — thought-bubble motif. SVGs at `frontend/public/branding/`.

**Fonts:** Inter (UI), JetBrains Mono (editor/code), Geist Mono (showcase animation only).

**Track colors are fixed** (not overridden by theme changes) — SQL `#5B6AF0`, Python `#2D9E6B`, Pandas `#C47F17`, PySpark `#D94F3D`, DE `#B9762B`, Data Modeling `#3F8E8C`, Statistics `#7A5AF0`, ML Fundamentals `#E0456A`, Experimentation `#0EA5E9`.

---

## Backend behaviour

**SQL:** `sql_guard.py` → `evaluator.py` → DuckDB. Parser-based read-only validation; 3-second timeout; 200-row cap. Submit: both queries run → DataFrames normalized → compared. On correct+structure_correct submissions, `_compute_quality()` runs DuckDB `EXPLAIN` on both queries and returns `{ efficiency_note, style_notes, complexity_hint, alternative_solution }` for the Solution Analysis UI in `QuestionPage.js`. On wrong answers where the user and expected results share the same shape (same row+column count but wrong values), style notes are surfaced as a partial quality object (close-miss feedback). Repeat identical wrong attempts are detected via `get_latest_submission()` and a nudge message is prepended to feedback.

**Python/Pandas:** `python_guard.py` → `python_evaluator.py` → subprocess harness. AST guard, 5-second timeout, 512 MB RLIMIT_AS.

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

**Learning path shortcuts:** completing the Starter path for a track → all medium unlocked immediately; completing the Intermediate path → full hard cap unlocked. Either acts as an express-lane alternative to threshold grinding.

**Mock daily limits:** Free = 1 medium/day · Pro = 3 hard/day · Elite = unlimited.

**Elite mock exclusives:** (1) Focus mode — `focus_concepts` param in `/start` filters pool to concept-tagged questions; (2) Mock history analytics — `GET /api/mock/analytics` returns score trends, concept breakdown, and track/difficulty splits over last 50 sessions.

**Dashboard insights:** `GET /api/dashboard/insights` computes per-track solve count, median solve time, and accuracy from `submissions`; weakest concepts (bottom 3 with >=3 attempts); deterministic cross-track pacing insight (only when slow-fast gap >= 60s); consecutive `streak_days` ending today; and (Elite only) `readiness_scores` (per-track 0–100 score from practice coverage + mock accuracy + concept strength) and `study_plan` (ordered list of 3–5 personalised next steps). Results are cached in-process for 60 seconds per user.

**Identity:** Anonymous visitors get real user rows + session cookies. Registration upgrades the session in place. Login merges anonymous progress into an existing account. `GET /api/auth/me` returns identity plus streak metadata (`streak_days`, `streak_at_risk`) used by the workspace topbar and streak milestone toasts on solves. Session cookie is `HttpOnly` + `SameSite=Lax` (and secure in production by default).

**OAuth + magic-link hardening:** OAuth `/authorize` now creates a short-lived, one-time server-side `state` token validated+consumed in `/callback`. User-agent/IP-prefix mismatches are logged as risk signals but are best-effort only (do not hard-block valid callbacks). Google authorize scope is `openid email profile` and GitHub authorize scope is `read:user user:email`. OAuth callbacks are configured per provider via `GOOGLE_REDIRECT_URI` and `GITHUB_REDIRECT_URI` (required in production when the corresponding provider credentials are set). Magic-link auth is available via `POST /api/auth/magic-link` and `GET /api/auth/magic-link/callback` with short-lived, single-use tokens.

**Auth hardening:** Reserved local-part email prefixes are blocked on registration. Failed sign-in attempts are tracked in Postgres; after `LOGIN_LOCKOUT_MAX_ATTEMPTS` failures, the account is temporarily locked for `LOGIN_LOCKOUT_WINDOW_MINUTES`.

**CSRF mitigation:** In production, mutating `/api/*` requests that include a session cookie require an `Origin` header matching configured app origins.

**Error shape:** `{ error, request_id }` on all user-facing errors. `X-Request-ID` header on all responses.

**Observability baseline:** Every response includes `X-Response-Time-Ms`; backend logs include request method, path, status, and latency keyed by `request_id`. Optional Sentry capture is enabled when `SENTRY_DSN` is configured (backend) or `VITE_SENTRY_DSN` (frontend — includes Session Replay on errors). In the single-service production deploy, frontend observability settings are injected into the SPA at request time by `routers/spa.py`, so Railway does not need Docker build args for Sentry/PostHog. Production frontend builds emit hidden sourcemaps and upload them to Sentry when `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are present. PostHog product analytics fires on key funnel events (`question_submitted`, `question_solved`, `sample_submitted`, `mock_started`, `mock_completed`, `plan_upgrade_started`, `plan_upgraded`) when `VITE_POSTHOG_KEY` is set; SPA page views are tracked on route change.

---

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Status, Postgres, loaded tables |
| GET | `/api/catalog` | SQL questions grouped by difficulty with per-user state |
| GET | `/api/questions/{id}` | SQL question detail (403 if locked, omits solution pre-submit) |
| POST | `/api/run-query` | Execute SQL, return rows |
| POST | `/api/submit` | Evaluate SQL, return verdict + solution on correct |
| GET | `/api/python/catalog` | Python catalog |
| GET | `/api/python/questions/{id}` | Python question detail |
| POST | `/api/python/run-code` | Run Python code, return test results + stdout |
| POST | `/api/python/submit` | Submit Python code |
| GET | `/api/python-data/catalog` | Pandas catalog |
| POST | `/api/python-data/run-code` | Run pandas code |
| POST | `/api/python-data/submit` | Submit pandas code |
| GET | `/api/pyspark/catalog` | PySpark catalog (`type` + `interaction_mode` on reasoning rows) |
| POST | `/api/pyspark/submit` | Submit MCQ answer |
| GET | `/api/statistics/catalog` | Statistics catalog (`type`, `subtype`, and `interaction_mode` per question) |
| GET | `/api/statistics/questions/{id}` | Statistics question detail (conceptual: options; numerical: starter_code + test_cases) |
| POST | `/api/statistics/run-code` | Run Python code for numerical statistics questions (400 for conceptual) |
| POST | `/api/statistics/submit` | Submit answer: `selected_option` for conceptual, `code` for numerical |
| GET | `/api/dashboard` | Cross-track progress summary |
| GET | `/api/dashboard/insights` | Coaching insights (speed, accuracy, weak concepts, streak) |
| GET | `/api/submissions` | Submission history for a question (`track`, `question_id`, `limit` params) |
| GET | `/api/paths` | All learning paths with per-user `solved_count` |
| GET | `/api/paths/{slug}` | Path detail with per-question `state` (solved/unlocked/locked) |
| GET | `/api/mock/access` | Pre-flight access check — per-difficulty `can_start`, `block_reason`, `needs_upgrade`, `daily_limit`, `daily_used` |
| GET | `/api/mock/history` | Past mock sessions list (last 20) |
| GET | `/api/mock/analytics` | Elite only: aggregate analytics over last 50 sessions |
| POST | `/api/mock/start` | Start a mock session `{ mode, track, difficulty, focus_concepts? }` → `{ session_id, questions[], time_limit_s, started_at, focus_fallback }`. Returns 409 if user has an active session (includes `session_id` in error body). |
| GET | `/api/mock/{id}` | Session state for reload recovery |
| POST | `/api/mock/{id}/submit` | Submit answer mid-session → `{ correct, feedback }` (no solution revealed) |
| POST | `/api/mock/{id}/finish` | End session → full summary with per-question solutions |
| DELETE | `/api/mock/{id}` | Discard an active session started within 2 minutes (returns 204); 403 if older than 2 min or already completed |
| GET | `/api/sample/{topic}/{difficulty}` | Next unseen sample (409 when exhausted) |
| POST | `/api/sample/{topic}/{difficulty}/reset` | Clear seen state |
| POST | `/api/sample/sql/run-query` | Execute SQL sample query |
| POST | `/api/sample/{topic}/run-code` | Execute Python/Pandas sample code |
| POST | `/api/sample/{topic}/submit` | Submit sample answer (no challenge progress impact) |
| GET | `/api/auth/me` | Current user identity + streak metadata (`streak_days`, `streak_at_risk`) |
| POST | `/api/auth/register` | Create account, upgrade anonymous session |
| POST | `/api/auth/login` | Authenticate, merge anonymous progress |
| POST | `/api/auth/logout` | Delete session |
| POST | `/api/auth/forgot-password` | Send password reset email (always returns 200 to prevent enumeration) |
| POST | `/api/auth/reset-password` | Consume reset token, set new password (also marks email verified) |
| POST | `/api/auth/verify-email` | Consume email verification token, mark account verified |
| POST | `/api/auth/resend-verification` | Resend verification email to the current signed-in user |
| POST | `/api/auth/magic-link` | Request one-time magic-link sign-in email (non-enumerating response) |
| GET | `/api/auth/magic-link/callback` | Consume magic-link token, create session, redirect to frontend |
| GET | `/api/auth/oauth/{provider}/authorize` | Return OAuth authorization URL (`google` or `github`) |
| GET | `/api/auth/oauth/{provider}/callback` | OAuth callback — validate+consume state, exchange code, upsert user, set session cookie |
| POST | `/api/razorpay/create-order` | Create Razorpay Order (lifetime) or Subscription (pro/elite) |
| POST | `/api/razorpay/verify-payment` | Verify HMAC on client callback, apply plan immediately (idempotent) |
| POST | `/api/razorpay/webhook` | Verified, idempotent plan update (authoritative source of truth) |

---

## Local dev accounts

Three permanent accounts exist in the local Postgres DB for testing and browser preview. Always use these — never create throwaway accounts for plan-level UI testing.

| Plan | Email | Notes |
|---|---|---|
| **Free** | `matt.srini@gmail.com` | Default non-paying user |
| **Pro** | `srinivas.assampally@gmail.com` | Mid-tier; 3 hard mocks/day, no Elite features |
| **Elite** | `admin@datathink.co` | Full access — analytics, debrief, focus mode, unlimited |

**Password for all three:** `Test1234!`

To log in for browser preview, sign in at `/auth` with the email above. The session cookie (`session_token`, `httponly=true`) is set server-side via the Vite proxy (`/api → localhost:8000`), so sign-in through the UI works normally in dev. Use `fetch('/api/auth/login', {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email, password})})` from `preview_eval` to sign in programmatically.

---

## Local development

> Full details, node path quirks, and Alembic migration commands: **[`docs/deployment.md`](docs/deployment.md)**

```bash
# Infrastructure
docker compose up postgres redis -d

# Backend (from backend/ — virtualenv is at project root)
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Backend tests (from backend/)
cd backend && ../.venv/bin/python -m pytest tests/ -q

# Alembic migrations (asyncpg driver required)
cd backend && DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sql_practice" \
  ../.venv/bin/alembic upgrade head
```

---

## Docs index

| File | What it covers |
|---|---|
| `docs/architecture.md` | System design, request lifecycles, data model, execution pipelines, scaling |
| `docs/backend.md` | All API routes, routers, execution pipeline, identity model |
| `docs/frontend.md` | Routes, pages, components, design system, data flows |
| `docs/datasets.md` | All 11 dataset tables — columns, row counts, intentional edge cases |
| `docs/deployment.md` | Local dev, Docker, production image, env vars, Railway |
| `docs/content-authoring.md` | Platform philosophy, question counts, concept coverage maps, per-track schemas, authoring rules |
| `docs/specs/platform-north-star.md` | Canonical product goal, role framing, practice/dashboard/mock relationship, filter policy |
| `docs/specs/practice-modality-spec.md` | Track modality matrix, practice interaction rules, metadata contract |
| `docs/specs/mock-benchmark-spec.md` | Benchmark-vs-drill split, mock invariants, analytics contract |
| `docs/track-onboarding.md` | End-to-end process for adding a new track — spec, backend, frontend, content, paths, docs |
| `docs/USERGUIDE.md` | End-user guide to the platform |
| `docs/features/pricing.md` | Pricing feature reference — plan entitlements, Razorpay flows, CTA states, webhook rules |
| `docs/features/mock.md` | Mock interview feature reference — plan gates, endpoints, coaching insights, test coverage |
| `docs/features/dashboard.md` | Dashboard feature reference — plan gates, endpoints, coaching insights, streak logic, caching |

**AI question authoring agents** (prompts for generating questions with Claude):

| Track | Agent file |
|---|---|
| **All tracks (universal)** | `.github/agents/question-authoring.agent.md` — start here; all 9 tracks, all difficulties, practice + mock-only, self-contained guardrails |
| SQL | `.github/agents/sql-question-authoring.agent.md` |
| Python | `.github/agents/python-question-authoring.agent.md` |
| Pandas | `.github/agents/pandas-question-authoring.agent.md` |
| PySpark | `.github/agents/pyspark-question-authoring.agent.md` |
| Data Engineering | `.github/agents/data-engineering-question-authoring.agent.md` |
| Data Modeling | `.github/agents/data-modeling-question-authoring.agent.md` |
| Statistics | `.github/agents/statistics-question-authoring.agent.md` — dual-subtype (conceptual MCQ + numerical Python) |
| ML Fundamentals | `.github/agents/ml-fundamentals-question-authoring.agent.md` |
| Experimentation | `.github/agents/experimentation-question-authoring.agent.md` |
| Any new track | `.github/agents/track-onboarding.agent.md` — drives full track onboarding end-to-end |
