# SQL Interview Practice Platform

A data interview practice platform for SQL, Python, Pandas, and PySpark. The product combines a React frontend, a FastAPI backend, PostgreSQL-backed app state, DuckDB-backed SQL evaluation, Python sandbox execution, learning paths, mock interviews, and plan-aware progression.

## Current State

- Challenge bank: 356 questions across 4 tracks
- Sample bank: 36 questions total, with 3 sample questions per track and difficulty
- Challenge mode with persistent progress, plan gating, bookmarks, drafts, and unlock logic
- Sample mode with no login requirement and no challenge-progress impact
- Mock interviews with plan-based limits and post-session analysis
- Learning paths with free and Pro-gated track-specific curricula
- Semantic concept tags and progressive hints surfaced in the practice UI

## Question Bank

| Track | Easy | Medium | Hard | Practice total | Mock-only (Pro/Elite) |
|---|---|---|---|---|---|
| SQL | 32 | 34 | 29 | 95 | 33 (19 med, 14 hard) |
| Python | 30 | 29 | 24 | 83 | 20 (8 med, 12 hard) |
| Pandas | 22 | 31 | 23 | 76 | 24 (10 med, 14 hard) |
| PySpark | 38 | 38 | 26 | 102 | 20 (10 med, 10 hard) |
| **Total** | **122** | **132** | **102** | **356** | **97** |

Mock-only questions share the same TXNNN ID scheme, allocated at the top of each difficulty range. They never appear in the practice catalog.

Sample questions (no login, no progress tracking): 3 per track × 3 difficulties = **36 total**.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| State | PostgreSQL |
| SQL execution | DuckDB loaded from committed CSV datasets |
| Python execution | Guarded subprocess sandbox |
| Payments | Razorpay Orders, Subscriptions, verified webhooks |
| Rate limiting | Redis in production, in-memory fallback in development |
| Testing | pytest, httpx, Vitest, React Testing Library, Playwright |
| Observability | Sentry and PostHog |

## Repository Layout

```text
sql-interview-practice/
├── backend/
│   ├── content/                  # Challenge banks and learning paths
│   ├── datasets/                 # Committed CSV datasets and metadata
│   ├── routers/                  # FastAPI routers for auth, catalog, sample, plan, mock, Razorpay, dashboard
│   ├── tests/                    # Backend test suite
│   ├── database.py               # DuckDB startup and shared execution state
│   ├── db.py                     # PostgreSQL persistence layer
│   ├── evaluator.py              # SQL evaluation pipeline
│   ├── python_evaluator.py       # Python/Pandas execution pipeline
│   ├── unlock.py                 # Plan and progression policy
│   └── scripts/validate_content.py
├── frontend/
│   ├── src/components/           # Shared application components
│   ├── src/pages/                # Landing, practice, dashboard, mock, auth, and sample pages
│   └── src/App.js                # Route tree
├── docs/                         # Architecture, backend, frontend, content, pricing, and ops docs
├── CLAUDE.md                     # Canonical repo context for AI assistance
├── Dockerfile                    # Single-service production image
└── docker-compose.yml            # Local Postgres + Redis services
```

## Product Behavior

### Practice modes

- Challenge mode persists progress and applies plan-aware unlock rules.
- Sample mode is anonymous-friendly and does not affect challenge progression.

### Plan model

- Free: all easy questions, batch-gated medium and hard access, 3 free learning paths per track
- Pro: full challenge catalog, all learning paths, medium and hard mock access with daily caps
- Elite: full catalog, full mock access, and weak-spot insights after mocks
- `lifetime_pro` and `lifetime_elite` normalize to their base plans for access checks

### Unlock rules

- SQL, Python, Pandas free tiers unlock medium at 8, 15, and 25 easy solves, and hard at 8, 15, and 22 medium solves with a hard cap of 15
- PySpark free tier uses higher thresholds: medium at 12, 20, and 30 easy solves; hard at 15 and 22 medium solves with a hard cap of 10
- Completing the starter path for a track unlocks all medium questions for that track
- Completing the intermediate path for a track unlocks the full free-tier hard cap for that track

### Evaluation and safety

- SQL submissions are validated as read-only, executed with a 3-second timeout, and capped at 200 result rows
- Python and Pandas submissions are AST-guarded, sandboxed, and time-limited
- PySpark questions are evaluated as MCQ, predict-output, or debugging selections rather than code execution
- User-facing errors follow the `{ error, request_id }` shape and responses include `X-Request-ID`

## Local Development

See [docs/deployment.md](./docs/deployment.md) for the full setup guide. The shortest local path is:

```bash
docker compose up postgres redis -d
cd backend && ../.venv/bin/python -m uvicorn main:app --reload --port 8000
npm --prefix frontend run dev -- --host 127.0.0.1
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
| [docs/backend.md](./docs/backend.md) | All API routes, routers, query execution pipeline, Python sandbox, identity model |
| [docs/frontend.md](./docs/frontend.md) | Route tree, pages, components, design system, data flows |
| [docs/datasets.md](./docs/datasets.md) | All 11 CSV tables — columns, row counts, intentional edge cases |
| [docs/deployment.md](./docs/deployment.md) | Local dev setup, Docker, production build, environment variables, Railway |
| [docs/content-authoring.md](./docs/content-authoring.md) | Curriculum philosophy, question counts, concept coverage maps, per-track authoring rules, JSON schemas |
| [docs/features/pricing.md](./docs/features/pricing.md) | Pricing, plan entitlements, Razorpay checkout flow, and webhook handling |
| [docs/features/mock.md](./docs/features/mock.md) | Mock interview modes, limits, summary behavior, and coaching surfaces |
| [docs/features/dashboard.md](./docs/features/dashboard.md) | Dashboard metrics, streak logic, weakest-concept insights, and caching behavior |
| [docs/USERGUIDE.md](./docs/USERGUIDE.md) | End-user guide to the platform |

### Where to start

| Goal | Start here |
|---|---|
| Understand how the system works end-to-end | [docs/architecture.md](./docs/architecture.md) |
| Add or change a question | [docs/content-authoring.md](./docs/content-authoring.md) |
| Work on the API or execution pipeline | [docs/backend.md](./docs/backend.md) |
| Work on the UI | [docs/frontend.md](./docs/frontend.md) |
| Understand the datasets | [docs/datasets.md](./docs/datasets.md) |
| Set up the dev environment | [docs/deployment.md](./docs/deployment.md) |

### AI-assisted question authoring

Use the track-specific agent prompt files in `.github/agents/` with Claude Code:

| Track | Agent file |
|---|---|
| SQL | [`.github/agents/sql-question-authoring.agent.md`](./.github/agents/sql-question-authoring.agent.md) |
| Python | [`.github/agents/python-question-authoring.agent.md`](./.github/agents/python-question-authoring.agent.md) |
| Pandas | [`.github/agents/pandas-question-authoring.agent.md`](./.github/agents/pandas-question-authoring.agent.md) |
| PySpark | [`.github/agents/pyspark-question-authoring.agent.md`](./.github/agents/pyspark-question-authoring.agent.md) |
