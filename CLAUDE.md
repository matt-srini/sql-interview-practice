# CLAUDE.md — Project context for AI assistance

This file is the canonical context reference for Claude in this repository.
**Keep it current.** Any time the architecture, design, content, or behaviour of this platform changes, update this file and the relevant files in `docs/` as part of the same task — not as a follow-up.

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

---

## What this is

A data interview practice platform covering four tracks. Users write SQL or Python, answer MCQ questions, get instant feedback, and work through gated challenge banks.

**Modes per track:**
- **Challenge mode** — plan-aware unlock rules, persistent progress, 311+ questions across 4 tracks
- **Sample mode** — 36 sandbox questions across all four tracks (3 per track+difficulty), no progress recorded, no login required

**Tracks:**
- **SQL** — 86 questions, DuckDB execution, realistic relational datasets
- **Python** — algorithms and data structures, test-case evaluation
- **Pandas** — pandas/numpy data manipulation, DataFrame comparison
- **PySpark** — conceptual MCQ, predict-output questions

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| Query execution | DuckDB (in-memory, loaded once at startup from CSVs) |
| Payments | Stripe Checkout + verified webhooks |
| Rate limiting | Redis (production) / in-memory fallback (development) |
| Testing | pytest + httpx (backend), Vitest + React Testing Library (frontend) |

---

## Content footprint

| Track | Questions | Format | Location |
|---|---|---|---|
| SQL | 86 (30 easy, 30 medium, 26 hard) | SQL query | `backend/content/questions/` |
| Python | 75 (30 easy, 25 medium, 20 hard) | Algorithm test cases | `backend/content/python_questions/` |
| Pandas | 75 (30 easy, 25 medium, 20 hard) | DataFrame comparison | `backend/content/python_data_questions/` |
| PySpark | 75 (30 easy, 25 medium, 20 hard) | MCQ / predict output | `backend/content/pyspark_questions/` |

- **Sample questions:** 3 per track+difficulty = 36 total across all tracks
- Every question has `hints` (1–2 entries) and `concepts` (semantic tags surfaced as pills)
- SQL questions have a `companies` field (`["Meta", "Stripe", ...]`) used for the company filter in SidebarNav
- SQL schemas validated against committed CSV headers at catalog load time

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
│   ├── routers/                    # auth, system, catalog, questions, sample, plan, stripe, mock, paths, spa
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
│   │   │   ├── SidebarNav.js       # Question list, lock/solved/next states (topic-aware)
│   │   │   ├── CodeEditor.js       # Language-agnostic Monaco editor wrapper
│   │   │   ├── SQLEditor.js        # Thin re-export of CodeEditor with language="sql"
│   │   │   ├── ResultsTable.js
│   │   │   ├── SchemaViewer.js
│   │   │   ├── TestCasePanel.js    # Python algorithm test case results
│   │   │   ├── PrintOutputPanel.js # Captured stdout from Python execution
│   │   │   ├── VariablesPanel.js   # Available DataFrames for Pandas questions
│   │   │   ├── MCQPanel.js         # Radio-button MCQ for PySpark questions
│   │   │   ├── TrackProgressBar.js # Reusable horizontal progress bar
│   │   │   ├── PathProgressCard.js # Path card with topic dot, progress bar, CTA (used on Landing + TrackHub)
│   │   │   └── Topbar.js           # Shared top nav bar used by all standalone pages (Practice dropdown, Mock, Dashboard, auth)
│   │   └── pages/
│   │       ├── LandingPage.js          # Fixed-topbar landing with track/sample tabs and compact progress panels
│   │       ├── QuestionPage.js         # Topic-aware question page (all 4 tracks)
│   │       ├── TrackHubPage.js         # Per-track landing (progress, next-up summary, concept preview, paths)
│   │       ├── LearningPath.js         # Curated path page at /learn/:topic/:slug (breadcrumb, progress, question list)
│   │       ├── LearningPathsIndex.js   # Index of all paths at /learn and /learn/:topic (grouped, filterable)
│   │       ├── ProgressDashboard.js    # Cross-track progress overview at /dashboard
│   │       ├── MockHub.js              # Mock interview lobby at /mock (mode/track/difficulty selection)
│   │       ├── MockSession.js          # Active mock session + summary at /mock/:id
│   │       ├── SampleQuestionPage.js
│   │       └── AuthPage.js
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
/                              → LandingPage (4-tile track grid)
/auth                          → AuthPage (register / sign in)
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

`:topic` values: `sql` | `python` | `python-data` | `pyspark`

---

## Landing page structure

Fixed topbar → centered hero (logged-out only) → dark showcase → light practice section.

```
TOPBAR
  "datanest"                             [Mock] [Dashboard] [name · Sign out] or [Login]

HERO  (logged-out only)
  Centered, max-width 620px inner wrapper
  kicker · headline · copy · CTAs: [Explore tracks ↓] [Create account]

SHOWCASE  (all users)
  Dark section (#0C0C0A), 4-card flex row with per-track glow
  Auto-advances every ~5s; typing animation on active card

TRACK SELECTION  (all users, id="landing-tracks")
  Light section, pill nav (SQL/Python/Pandas/PySpark)
  Per-track panel: description · progress bar · CTA · 3 sample tiles
```

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Key tokens:**
```
--bg-page:         #F7F7F5   (dark: #141413)
--surface-card:    #FFFFFF   (dark: #1C1C1A)
--accent:          #5B6AF0   (dark: #7B8AF5)
--text-strong:     #1A1A18   (dark: #F0EEE9)
--text-secondary:  #6B6862
--success:         #2D9E6B
--warning:         #C47F17
--danger:          #D94F3D
--radius-lg: 20px  --radius-md: 14px  --radius-sm: 10px
```

**Fonts:** Inter (UI), JetBrains Mono (editor/code), Geist Mono (showcase animation only).

---

## Backend behaviour

**SQL:** `sql_guard.py` → `evaluator.py` → DuckDB. Parser-based read-only validation; 3-second timeout; 200-row cap. Submit: both queries run → DataFrames normalized → compared. On correct+structure_correct submissions, `_compute_quality()` runs DuckDB `EXPLAIN` on both queries and returns `{ efficiency_note, style_notes, complexity_hint, alternative_solution }` for the Solution Analysis UI in `QuestionPage.js`.

**Python/Pandas:** `python_guard.py` → `python_evaluator.py` → subprocess harness. AST guard, 5-second timeout, 512 MB RLIMIT_AS.

**PySpark:** No execution. `selected_option` compared to `correct_option`. Explanation always returned.

**Unlock model** (pure policy in `unlock.py`, applied independently per topic):

| Plan | Access |
|---|---|
| Free | All easy. Medium unlocks at 10/20/30 solved easy. Hard unlocks at 10/20/30 solved medium (capped). |
| Pro | All easy + medium + first 22 hard |
| Elite | Full catalog |

**Identity:** Anonymous visitors get real user rows + session cookies. Registration upgrades the session in place. Login merges anonymous progress into an existing account.

**Error shape:** `{ error, request_id }` on all user-facing errors. `X-Request-ID` header on all responses.

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
| GET | `/api/pyspark/catalog` | PySpark catalog |
| POST | `/api/pyspark/submit` | Submit MCQ answer |
| GET | `/api/dashboard` | Cross-track progress summary |
| GET | `/api/submissions` | Submission history for a question (`track`, `question_id`, `limit` params) |
| GET | `/api/paths` | All learning paths with per-user `solved_count` |
| GET | `/api/paths/{slug}` | Path detail with per-question `state` (solved/unlocked/locked) |
| GET | `/api/mock/history` | Past mock sessions list (last 20) |
| POST | `/api/mock/start` | Start a mock session `{ mode, track, difficulty }` → `{ session_id, questions[], time_limit_s, started_at }` |
| GET | `/api/mock/{id}` | Session state for reload recovery |
| POST | `/api/mock/{id}/submit` | Submit answer mid-session → `{ correct, feedback }` (no solution revealed) |
| POST | `/api/mock/{id}/finish` | End session → full summary with per-question solutions |
| GET | `/api/sample/{topic}/{difficulty}` | Next unseen sample (409 when exhausted) |
| POST | `/api/sample/{topic}/{difficulty}/reset` | Clear seen state |
| POST | `/api/sample/sql/run-query` | Execute SQL sample query |
| POST | `/api/sample/{topic}/run-code` | Execute Python/Pandas sample code |
| POST | `/api/sample/{topic}/submit` | Submit sample answer (no challenge progress impact) |
| GET | `/api/auth/me` | Current user identity |
| POST | `/api/auth/register` | Create account, upgrade anonymous session |
| POST | `/api/auth/login` | Authenticate, merge anonymous progress |
| POST | `/api/stripe/create-checkout` | Stripe Checkout session |
| POST | `/api/stripe/webhook` | Verified, idempotent plan update |

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
| `docs/README.md` | Documentation hub and quick orientation |
| `docs/architecture.md` | System design, request lifecycles, data model, execution pipelines, scaling |
| `docs/backend.md` | All API routes, routers, execution pipeline, identity model |
| `docs/frontend.md` | Routes, pages, components, design system, data flows |
| `docs/datasets.md` | Dataset inventory, schema details, edge cases |
| `docs/deployment.md` | Local dev, Docker, production image, env vars, Railway |
| `docs/content-authoring.md` | Curriculum specs and authoring rules for all four tracks |
| `docs/USERGUIDE.md` | End-user guide to the platform |
