# datathink — Data Interview Practice Platform

A data interview practice platform covering nine tracks. Users write SQL or Python, answer conceptual questions, get instant feedback, and work through plan-gated challenge banks. The product pairs a React frontend with a FastAPI backend, PostgreSQL-backed app state, DuckDB-backed SQL evaluation, a Python subprocess sandbox, learning paths, mock interviews, and plan-aware progression.

## Current State

- **828 practice questions** across 9 tracks with plan-gated unlock rules and persistent progress
- **165 mock-only questions** (Pro/Elite) across all tracks, never shown in the practice catalog
- **36 sample questions** across SQL, Python, Pandas, and PySpark — no login required, no progress impact. Data Engineering, Data Modeling, Statistics, ML Fundamentals, and Experimentation samples are auto-sliced from the first 3 practice questions per difficulty.
- Challenge mode with persistent progress, bookmarks, draft autosave, hints, concept tags, and unlock logic
- Sample mode that is anonymous-friendly (no login required)
- Mock interviews: `benchmark` (fixed-shape track benchmark) and drill modes (`30min`, `custom`, `mixed`) with plan-based limits and post-session analysis
- Learning paths with free and Pro-gated track-specific curricula (42 paths total)
- Semantic concept tags, progressive hints, and company tags (SQL) surfaced in the practice UI
- Dashboard with coaching insights, streak tracking, weakest-concept signals, and (Elite) readiness scores + study plan
- Three subscription tiers (Free / Pro / Elite) via Razorpay

## Question Bank

| Track | Easy | Medium | Hard | Practice total | Mock-only (Pro/Elite) |
|---|---|---|---|---|---|
| SQL | 37 | 45 | 30 | **112** | 38 (0 easy, 19 med, 19 hard) |
| Python | 39 | 32 | 24 | **95** | 20 (0 easy, 8 med, 12 hard) |
| Pandas | 27 | 36 | 23 | **86** | 26 (0 easy, 12 med, 14 hard) |
| PySpark | 41 | 39 | 26 | **106** | 21 (0 easy, 11 med, 10 hard) |
| Data Engineering | 30 | 33 | 23 | **86** | 1 |
| Data Modeling | 25 | 28 | 23 | **76** | 1 |
| Statistics | 31 | 41 | 25 | **97** | 8 |
| ML Fundamentals | 30 | 35 | 25 | **90** | 25 |
| Experimentation | 30 | 30 | 20 | **80** | 25 |
| **Total** | **290** | **319** | **219** | **828** | **165** |

Mock-only questions share the same TXNNN ID scheme, allocated at the top of each difficulty range. They never appear in the practice catalog.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| SQL execution | DuckDB (in-memory, loaded from committed CSV datasets) |
| Python execution | AST-guarded subprocess sandbox (Python / Pandas) |
| Payments | Razorpay Orders + Subscriptions + verified webhooks |
| Rate limiting | Redis (production) / in-memory fallback (development) |
| Testing | pytest + httpx (backend), Vitest + React Testing Library (unit), Playwright (e2e) |
| Observability | Sentry (backend + frontend), PostHog (product analytics) |

## Repository Layout

```text
sql-interview-practice/
├── backend/
│   ├── content/
│   │   ├── questions/                  # SQL challenge JSON (easy/medium/hard.json)
│   │   ├── python_questions/           # Python algorithm questions
│   │   ├── python_data_questions/      # Pandas questions
│   │   ├── pyspark_questions/          # PySpark MCQ questions
│   │   ├── data_engineering_questions/ # Data Engineering MCQ / scenario / debug
│   │   ├── data_modeling_questions/    # Data Modeling MCQ / scenario
│   │   ├── statistics_questions/       # Statistics dual-subtype (conceptual MCQ + numerical Python)
│   │   ├── ml_fundamentals_questions/  # ML Fundamentals MCQ / scenario / predict-output / debug
│   │   ├── experimentation_questions/  # Experimentation MCQ / scenario / predict-output / debug
│   │   └── paths/                      # Learning path configs
│   ├── datasets/                       # Committed CSVs + metadata JSON
│   ├── routers/                        # auth, catalog, questions, sample, mock, paths, dashboard, razorpay, spa, …
│   ├── tests/                          # Backend test suite
│   ├── alembic/                        # Postgres migrations
│   ├── database.py                     # DuckDB startup and shared state
│   ├── db.py                           # PostgreSQL persistence layer
│   ├── evaluator.py                    # SQL evaluation pipeline
│   ├── python_evaluator.py             # Python/Pandas execution pipeline
│   ├── unlock.py                       # Pure plan + solve-history → unlock policy
│   └── sql_guard.py / python_guard.py  # Read-only SQL + AST-based Python validation
├── frontend/
│   ├── src/
│   │   ├── App.js                      # Route tree
│   │   ├── App.css                     # Global styles and design tokens (single stylesheet)
│   │   ├── components/                 # Shared application components
│   │   └── pages/                      # Landing, practice, dashboard, mock, auth, sample, paths
│   └── package.json
├── docs/                               # Architecture, backend, frontend, content, pricing, and ops docs
├── CLAUDE.md                           # Canonical repo context for AI assistance
├── Dockerfile                          # Single-service production image
└── docker-compose.yml                  # Local Postgres + Redis services
```

## Product Behavior

### Tracks and evaluation modes

| Track | Eval mode | Code execution |
|---|---|---|
| SQL | DuckDB query comparison | Yes — DuckDB, 3 s timeout, 200-row cap |
| Python | Test-case harness | Yes — subprocess sandbox, 5 s timeout |
| Pandas | DataFrame output comparison | Yes — subprocess sandbox, 5 s timeout |
| PySpark | MCQ / predict-output / debug / scenario | No |
| Data Engineering | MCQ / scenario / debug | No |
| Data Modeling | MCQ / scenario | No |
| Statistics | Dual-subtype: conceptual (MCQ) or numerical (Python) | Only for numerical subtype |
| ML Fundamentals | MCQ / scenario / predict-output / debug | No |
| Experimentation | MCQ / scenario / predict-output / debug | No |

### Plan model

| Plan | Access |
|---|---|
| Free | All easy questions, batch-gated medium and hard (thresholds below), 1 medium mock/day, free learning paths |
| Pro | Full practice catalog, all learning paths, 3 hard mocks/day, benchmark + drill mock modes |
| Elite | Full catalog, unlimited mocks, focus mode, mock analytics, readiness scores, study plan |

`lifetime_pro` and `lifetime_elite` normalize to their base plans for access checks.

### Unlock thresholds (Free tier)

**Code tracks (SQL, Python, Pandas):**
- Medium: 8 easy → 3 medium · 15 easy → 8 medium · 25 easy → all medium
- Hard: 8 medium → 3 hard · 15 medium → 8 hard · 22 medium → 15 hard *(cap: 8)*

**MCQ tracks (PySpark, Data Engineering):**
- Medium: 10 easy → 3 medium · 17 easy → 8 medium · 25 easy → all medium
- Hard: 12 medium → 5 hard *(cap: 5)*

**Learning path shortcuts:** Completing a track's Starter path → all medium unlocked. Completing the Intermediate path → full free-tier hard cap unlocked.

### Mock modes

- **Benchmark** — fixed-shape track benchmark; not available for Mixed. Track-specific question blueprints (e.g. Statistics enforces 1 numerical + 2 conceptual).
- **Drill (30min / custom / mixed)** — flexible drill sessions; Mixed selects across all eligible tracks.

### Evaluation and safety

- SQL: parser-based read-only guard (`sql_guard.py`), 3-second DuckDB timeout, 200-row result cap. Correct submissions also run `EXPLAIN`-based quality analysis (efficiency note, style notes, alternative solution).
- Python/Pandas: AST guard (`python_guard.py`), subprocess sandbox, 5-second timeout, 512 MB `RLIMIT_AS`.
- MCQ (PySpark, DE, DM, Stats-conceptual, MLF, Exp): `selected_option` compared to `correct_option`; locked questions return `locked: true` with stem visible but options hidden.
- All user-facing errors follow `{ error, request_id }` and every response carries `X-Request-ID` + `X-Response-Time-Ms`.

## Local Development

See [docs/deployment.md](./docs/deployment.md) for the full setup guide.

```bash
# Infrastructure
docker compose up postgres redis -d

# Backend (virtualenv is at project root)
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

Useful endpoints:

- Frontend: http://127.0.0.1:5173
- Backend: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

## Documentation

| Doc | What it covers |
|---|---|
| [docs/architecture.md](./docs/architecture.md) | System design, request lifecycles, data model, execution pipelines, scaling |
| [docs/backend.md](./docs/backend.md) | All API routes, routers, execution pipeline, identity model |
| [docs/frontend.md](./docs/frontend.md) | Route tree, pages, components, design system, data flows |
| [docs/datasets.md](./docs/datasets.md) | All CSV tables — columns, row counts, intentional edge cases |
| [docs/deployment.md](./docs/deployment.md) | Local dev setup, Docker, production build, env vars, Railway |
| [docs/content-authoring.md](./docs/content-authoring.md) | Curriculum philosophy, question counts, concept coverage maps, per-track schemas, authoring rules |
| [docs/features/pricing.md](./docs/features/pricing.md) | Plan entitlements, Razorpay flows, CTA states, webhook rules |
| [docs/features/mock.md](./docs/features/mock.md) | Mock modes, limits, benchmark composition, coaching surfaces |
| [docs/features/dashboard.md](./docs/features/dashboard.md) | Dashboard metrics, streak logic, weakest-concept insights, readiness scores |
| [docs/USERGUIDE.md](./docs/USERGUIDE.md) | End-user guide to the platform |

### Where to start

| Goal | Start here |
|---|---|
| Understand the system end-to-end | [docs/architecture.md](./docs/architecture.md) |
| Add or change a question | [docs/content-authoring.md](./docs/content-authoring.md) |
| Work on the API or execution pipeline | [docs/backend.md](./docs/backend.md) |
| Work on the UI | [docs/frontend.md](./docs/frontend.md) |
| Set up the dev environment | [docs/deployment.md](./docs/deployment.md) |
| Add a new track | [docs/track-onboarding.md](./docs/track-onboarding.md) |

### AI-assisted question authoring

**Mandatory rule, no exceptions:** every new question — and every edit to an existing question — goes through the single universal authoring agent. Direct edits to question JSON files bypass the difficulty arc, the taxonomy contract, and the verification checklist; they are the largest historical source of content drift on this platform.

| Purpose | File |
|---|---|
| **Universal authoring agent (always)** | [`.github/agents/question-authoring.agent.md`](./.github/agents/question-authoring.agent.md) |
| Per-track knowledge (read while authoring) | [`docs/tracks/<track>.md`](./docs/tracks/) — one file per track |
| Concept-family registry + 7 follow-up dimensions | [`docs/concept-taxonomy.md`](./docs/concept-taxonomy.md) |
| Mock plan-tier matrix + chain mechanics | [`docs/features/mock.md`](./docs/features/mock.md) |
| Cross-track contract + ID scheme | [`docs/content-authoring.md`](./docs/content-authoring.md) |
| New track onboarding (end-to-end process) | [`.github/agents/track-onboarding.agent.md`](./.github/agents/track-onboarding.agent.md) |
