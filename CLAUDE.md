# CLAUDE.md — Project context for AI assistance

This file is the canonical context reference for Claude in this repository.
**Keep it current.** Any time the architecture, design, content, or behaviour of this platform changes, update this file and the relevant files in `docs/` before finishing the task.

---

## Standing instructions

- **Always commit after meaningful changes.** End every session of edits with a `git commit` carrying a clear, specific message (not "update files" — something like "refactor landing page to centered hero, remove timed-mode placeholder"). Co-author line: `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.
- **Keep `docs/` in sync.** When architecture, API routes, UI layout, design tokens, or product behaviour changes, update the relevant file(s) in `docs/` as part of the same task — not as a follow-up.
- **Keep `CLAUDE.md` in sync.** When anything in this file becomes stale, update it in the same commit as the code change.

---

## What this is

A SQL interview practice platform. Users write SQL against realistic datasets, get instant feedback, and work through a gated challenge bank. Two distinct tracks:

- **Challenge mode** — 86 questions across three difficulty tiers, plan-aware unlock rules, persistent progress
- **Sample mode** — 9 sandbox questions (3 per difficulty), no progress recorded, no login required

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

- **Challenge questions:** 86 total — 30 easy, 30 medium, 26 hard (JSON in `backend/content/questions/`)
- **Sample questions:** 9 total — 3 per difficulty (Python in `backend/sample_questions.py`)
- Every question has `hints` (1–2 entries) and `concepts` (semantic tags surfaced as pills)
- Schemas are validated against committed CSV headers at catalog load time

---

## Repository layout

```
sql-interview-practice/
├── backend/
│   ├── content/questions/     # Challenge question JSON (easy.json, medium.json, hard.json)
│   ├── datasets/              # Committed CSVs + metadata JSON
│   ├── middleware/            # Request context, request_id, X-Request-ID
│   ├── routers/               # auth, system, catalog, questions, sample, plan, stripe, spa
│   ├── scripts/               # Dataset generator, anonymous user cleanup
│   ├── tests/                 # API, evaluator, rate limiter tests
│   ├── alembic/               # Postgres migrations
│   ├── main.py                # App wiring, middleware, routers, lifespan
│   ├── config.py              # Env settings, CORS, rate limiter, dist path
│   ├── db.py                  # Async Postgres pool, all product-state persistence
│   ├── database.py            # DuckDB engine startup, table loading, cursor access
│   ├── evaluator.py           # Query execution, timeout, comparison normalization
│   ├── unlock.py              # Pure plan + solve-history → unlock policy
│   ├── questions.py           # Challenge catalog loader/validator
│   ├── sample_questions.py    # Sample catalog loader
│   ├── sql_guard.py           # Read-only SQL validation
│   ├── progress.py            # Challenge/sample persistence wrappers
│   ├── rate_limiter.py        # In-memory and Redis-backed limiter
│   └── models.py / deps.py    # Pydantic models and shared dependencies
├── frontend/
│   ├── src/
│   │   ├── App.js             # Route tree
│   │   ├── App.css            # Global styles and design tokens (single stylesheet)
│   │   ├── api.js             # Axios client, base URL resolution
│   │   ├── catalogContext.js  # Catalog state and refresh
│   │   ├── contexts/
│   │   │   └── AuthContext.js # Auth state (user, loading, refreshUser)
│   │   ├── components/
│   │   │   ├── AppShell.js    # Challenge workspace shell, sidebar container
│   │   │   ├── SidebarNav.js  # Question list, lock/solved/next states
│   │   │   ├── SQLEditor.js   # Monaco editor wrapper
│   │   │   ├── ResultsTable.js
│   │   │   └── SchemaViewer.js
│   │   └── pages/
│   │       ├── LandingPage.js
│   │       ├── QuestionPage.js
│   │       ├── SampleQuestionPage.js
│   │       └── AuthPage.js
│   └── package.json
├── docs/                      # Architecture and design reference docs
├── CLAUDE.md                  # This file
├── README.md                  # Setup and usage guide
├── Dockerfile                 # Single-service production image
├── docker-compose.yml         # Local Postgres + Redis stack
└── railway.json               # Railway deployment config
```

---

## Frontend routes

```
/                          → LandingPage
/auth                      → AuthPage (register / sign in)
/sample/:difficulty        → SampleQuestionPage
/practice                  → AppShell + CatalogProvider
  /practice/questions/:id  → QuestionPage
/questions/:id             → redirect → /practice/questions/:id
```

---

## Landing page structure

Centered, single-column layout. No split hero. No placeholder/planned features visible.

```
TOPBAR
  "SQL Interview Practice"              [Sign in] or [name · Sign out]

HERO  (centered, max-width 560px)
  kicker: "86 questions · easy, medium, hard"
  headline: "Get sharp at SQL interviews."
  copy: one sentence about challenge bank + samples
  CTAs: [Start the challenge] → /practice   [Try a sample] → /sample/easy

SAMPLE TILES  (3-col grid, max-width 800px)
  [easy]   3 warm-up questions. No progress recorded.   Open sample →
  [medium] 3 mid-tier questions to test your range.     Open sample →
  [hard]   3 hard questions to find your ceiling.       Open sample →
```

CSS classes: `.landing-hero`, `.landing-kicker`, `.landing-title`, `.landing-copy`, `.landing-actions`, `.landing-samples`, `.sample-tile`.
Topbar auth: `.topbar-user-pill`, `.topbar-user-name`, `.topbar-signout-btn`, `.topbar-auth-link`.

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Philosophy:** Professional tool aesthetic — calm, fast, distraction-free. Light mode primary, warm dark mode via `prefers-color-scheme`. SQL editor always dark (`#1e1e1e`) regardless of colour scheme.

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

--radius-lg: 20px  (editor wrapper)
--radius-md: 14px  (inner cards, schema blocks)
--radius-sm: 10px  (badges, tokens)
```

**Fonts:** Inter (UI), JetBrains Mono (editor, results, code blocks) — both from Google Fonts.

**Buttons:** `.btn-primary` (accent fill), `.btn-secondary` (outlined, context-sensitive bg), `.btn-success` (success tint). All hover: `translateY(-1px)`, `150ms ease-out`.

**Question page chrome:** Minimal — no section kickers (content self-evident from titles/badges). Editor topbar is single-line ("SQL editor" / "DuckDB sandbox"). Editor footer is buttons-only, right-aligned. Post-submit verdict + feedback grouped in `.submit-outcome` wrapper. Cards use tight padding (`1.1rem 1.15rem`) with `14px` border-radius.

---

## Datasets

11 CSV tables in `backend/datasets/`, loaded into DuckDB at startup:

| Table | Rows | Domain |
|---|---|---|
| users | 600 | Accounts |
| categories | 16 | Product taxonomy |
| products | 260 | Product catalog |
| orders | 4200 | Order headers |
| order_items | 12665 | Line items |
| payments | 4737 | Payment events |
| sessions | 9000 | Web sessions |
| events | 44964 | Event stream |
| support_tickets | 1300 | Support cases |
| departments | 10 | HR dimension |
| employees | 180 | Employee records |

Intentional edge cases: NULL emails, NULL launch dates, unresolved tickets, departments with no employees, salary ties, mixed payment statuses.

---

## Backend behaviour

**Query execution pipeline:** `sql_guard.py` → `evaluator.py` → `database.py`
- Parser-based read-only validation (no writes, single statement)
- Shared in-memory DuckDB cursor (loaded once at startup)
- 3-second thread-pool timeout
- 200-row result cap

**Evaluation (submit):** Both user query and expected query run in DuckDB, results compared as pandas DataFrames after normalising column casing, column order, float precision, nulls. Row order ignored unless expected query has `ORDER BY`.

**Unlock model** (pure policy in `unlock.py`):
| Plan | Access |
|---|---|
| Free | All easy. Medium unlocks at 10/20/30 solved easy. Hard unlocks at 10/20/30 solved medium (capped). |
| Pro | All easy + medium + first 22 hard |
| Elite | Full catalog |

Solved questions stay solved permanently across plan changes.

**Identity:** Anonymous visitors get real user rows + session cookies. Registration upgrades the existing session (no progress lost). Login merges anonymous progress into an existing account.

**Error shape:** `{ error, request_id }` on all user-facing errors. `X-Request-ID` header on all responses.

**Rate limiting:** 60 req/60s per IP. Redis-backed in production, in-memory fallback otherwise.

---

## Key API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Status, Postgres, loaded tables |
| GET | `/api/catalog` | Questions grouped by difficulty with per-user state |
| GET | `/api/questions/{id}` | Question detail (403 if locked, omits solution pre-submit) |
| POST | `/api/run-query` | Execute SQL, return rows |
| POST | `/api/submit` | Evaluate SQL, return verdict + solution on correct |
| GET | `/api/sample/{difficulty}` | Next unseen sample (409 when exhausted) |
| POST | `/api/sample/{difficulty}/reset` | Clear seen state |
| GET | `/api/auth/me` | Current user identity |
| POST | `/api/auth/register` | Create account, upgrade anonymous session |
| POST | `/api/auth/login` | Authenticate, merge anonymous progress |
| POST | `/api/stripe/create-checkout` | Stripe Checkout session |
| POST | `/api/stripe/webhook` | Verified, idempotent plan update |

---

## Local development

**Start infrastructure:**
```bash
docker-compose up -d postgres redis
```

**Backend** (from `backend/`):
```bash
uvicorn main:app --reload --port 8000
```
Requires `DATABASE_URL` set (see `backend/.env`).

**Frontend** (from `frontend/`):
```bash
npm run dev
```
Runs on port 5173. API client auto-resolves to `http://localhost:8000/api` in dev.

**Health check:**
```
GET http://localhost:8000/health
→ { "status": "healthy", "postgres": true, "tables_loaded": [...] }
```

**Tests:**
```bash
# Backend
cd backend && pytest -q

# Frontend
cd frontend && npm test
```

---

## Docs index

| File | What it covers |
|---|---|
| `docs/project-blueprint.md` | Architecture, structure, content footprint, strengths/weaknesses |
| `docs/frontend.md` | Routes, pages, components, data flows |
| `docs/backend.md` | Routers, API reference, execution pipeline, identity model |
| `docs/datasets.md` | Dataset inventory, schema details, edge cases |
| `docs/deployment.md` | Local dev, Docker, production image, env vars, Railway |
| `docs/ui-design-system.md` | Design tokens, layout, buttons, editor, landing page structure |
| `docs/question-authoring-guidelines.md` | Rules for authoring challenge questions |
| `docs/sql-curriculum-spec.md` | Difficulty tiers and curriculum standards |
| `docs/USERGUIDE.md` | End-user guide to the platform |
