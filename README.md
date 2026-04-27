# SQL Interview Practice Platform

A data interview practice platform for SQL, Python, Pandas, and PySpark. The product combines a React frontend, a FastAPI backend, PostgreSQL-backed app state, DuckDB-backed SQL evaluation, Python sandbox execution, learning paths, mock interviews, and plan-aware progression.

## Current State

- Challenge bank: 350 questions across 4 tracks
- Sample bank: 36 questions total, with 3 sample questions per track and difficulty
- Challenge mode with persistent progress, plan gating, bookmarks, drafts, and unlock logic
- Sample mode with no login requirement and no challenge-progress impact
- Mock interviews with plan-based limits and post-session analysis
- Learning paths with free and Pro-gated track-specific curricula
- Semantic concept tags and progressive hints surfaced in the practice UI

The documentation hub lives in [docs/README.md](./docs/README.md).

## Question Bank

| Track | Easy | Medium | Hard | Total |
|---|---|---|---|---|
| SQL | 32 | 34 | 29 | 95 |
| Python | 30 | 29 | 24 | 83 |
| Pandas | 29 | 30 | 23 | 82 |
| PySpark | 38 | 30 | 22 | 90 |
| **Total** | **129** | **123** | **98** | **350** |

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
- Elite: full catalog, full mock access, company-filtered mocks, and weak-spot insights after mocks
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

## Documentation Map

- [docs/README.md](./docs/README.md): documentation hub
- [docs/architecture.md](./docs/architecture.md): system design and request lifecycles
- [docs/backend.md](./docs/backend.md): API routes and backend behavior
- [docs/frontend.md](./docs/frontend.md): routes, pages, and UI structure
- [docs/content-authoring.md](./docs/content-authoring.md): question and path authoring rules
- [docs/content-quality-remediation-plan.md](./docs/content-quality-remediation-plan.md): phased content-quality improvement plan
- [docs/deployment.md](./docs/deployment.md): local setup, Docker, and Railway deployment
- [docs/features/pricing.md](./docs/features/pricing.md): pricing surface, plan entitlements, Razorpay flow
- [docs/features/mock.md](./docs/features/mock.md): mock interview modes and summary behavior
- [docs/features/dashboard.md](./docs/features/dashboard.md): dashboard metrics, weak-spot insights, and streak logic
