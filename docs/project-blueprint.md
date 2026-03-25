# Project Blueprint

> **Navigation:** [Docs index](./README.md) · [Backend](./backend.md) · [Frontend](./frontend.md) · [Datasets](./datasets.md) · [Deployment](./deployment.md)

---

## 1. What this is

A SQL interview practice platform with:
- A React frontend for browsing questions, writing SQL, and reviewing results
- A FastAPI backend for routing, progression, execution, evaluation, and static SPA serving
- A PostgreSQL-backed product-state layer plus a shared in-memory DuckDB execution engine

Users can work through challenge questions with plan-aware unlock rules, use a separate sample track without affecting challenge progression, execute read-only SQL safely against realistic CSV-backed datasets, and compare results against expected outputs before reviewing official solutions.

---

## 2. Architecture at a glance

```
Browser
  └── React SPA (Vite, port 5173 in dev)
        └── Axios → FastAPI (port 8000)
              ├── PostgreSQL  (identity, progress, plans, billing)
              ├── DuckDB      (in-memory, query execution only)
              └── Redis       (rate limiting, optional)
```

**Frontend** — React 18 + React Router + Vite. Monaco editor for SQL. Axios API client with cookie credentials. See [frontend.md](./frontend.md).

**Backend** — FastAPI + Uvicorn. Eight registered routers. All product state in PostgreSQL; DuckDB is execution-only and loaded once at startup from committed CSVs. See [backend.md](./backend.md).

**Datasets** — 11 CSV tables covering commerce, product, behavioral, support, and HR domains. See [datasets.md](./datasets.md).

**Deployment** — Single-service production image (FastAPI serves API + built SPA). Local dev runs frontend and backend natively, Postgres and Redis in Docker. See [deployment.md](./deployment.md).

---

## 3. Current content footprint

- **Challenge questions:** 86 total — 30 easy, 30 medium, 26 hard
- **Sample questions:** 9 total — 3 per difficulty
- Every question carries `hints` (1–2 entries) and `concepts` (semantic tags)
- Question schemas are validated against committed dataset headers at catalog load time

---

## 4. Project structure

### Root
- `README.md` — setup, usage, question bank inventory
- `MANUAL_TEST_CHECKLIST.md` — end-to-end QA checklist
- `TODO_FUTURE.md` — backlog
- `docker-compose.yml` — local Postgres + Redis (+ optional backend/frontend containers)
- `Dockerfile` — single-service production image
- `railway.json` — Railway deployment config

### `backend/`
- `main.py` — app wiring, middleware, routers, lifespan
- `config.py` — env settings, CORS, rate limiter, frontend dist path
- `db.py` — async PostgreSQL pool, schema, all app-state persistence
- `database.py` — DuckDB engine startup, table loading, cursor access
- `evaluator.py` — query execution, timeout, result serialization, comparison
- `unlock.py` — pure plan + solve-history → unlock policy
- `questions.py` / `sample_questions.py` — catalog loaders and validators
- `sql_guard.py` — SQL safety validation
- `progress.py` — challenge/sample persistence wrappers
- `rate_limiter.py` — in-memory and Redis-backed limiter
- `models.py` / `deps.py` — Pydantic models and shared dependencies
- `sql_analyzer.py` — SQL analysis utilities
- `middleware/request_context.py` — request-id, logging context, X-Request-ID
- `routers/` — auth, system, catalog, questions, sample, plan, stripe, spa
- `content/questions/` — challenge question JSON (easy.json, medium.json, hard.json)
- `datasets/` — committed CSVs + metadata
- `scripts/` — dataset generator, anonymous user cleanup
- `tests/` — API, evaluator, rate limiter tests

### `frontend/`
- `src/App.js` — route tree
- `src/api.js` — Axios client, base URL resolution
- `src/catalogContext.js` — catalog state and refresh
- `src/App.css` — global styles and design tokens
- `src/components/` — AppShell, SidebarNav, SQLEditor, ResultsTable, SchemaViewer
- `src/pages/` — LandingPage, QuestionPage, SampleQuestionPage, AuthPage
- `src/contexts/AuthContext.js` — auth state management

---

## 5. Implemented features

- Unified anonymous + registered identity with cookie-backed sessions
- Plan-aware unlock computation (free / pro / elite tiers)
- JSON-backed challenge bank and Python-backed sample bank
- Process-singleton DuckDB engine loaded once at startup
- SQL safety validation, execution timeout, 200-row cap
- Result-set comparison with ORDER BY-sensitive normalization
- Per-IP rate limiting (Redis or in-memory fallback)
- Stripe Checkout + verified idempotent webhook processing
- Request correlation via X-Request-ID headers
- Single-service production deployment (FastAPI serves API + SPA)

---

## 6. Strengths

- Clean separation between content, product state, execution, and billing
- PostgreSQL for product state makes the model horizontally scalable
- DuckDB preloaded once — fast execution path per request
- Server-side lock enforcement; unlock policy is pure and testable
- Anonymous progress preserved through registration and login merge
- Standardized error shapes `{ error, request_id }` across all routes

---

## 7. Weaknesses and risks

- In-memory rate limiting is process-local when Redis is absent
- No submission history or analytics layer
- No admin or content management UI
- No automated content QA pipeline beyond schema validation
- Production requires `REDIS_URL` when `ENV=production`
- This blueprint must be kept in sync as the platform evolves

---

## 8. Testing

Current test files:
- `backend/tests/test_api.py`
- `backend/tests/test_evaluator.py`
- `backend/tests/test_rate_limiter.py`
- `frontend/src/components/SidebarNav.test.js`

Gaps:
- No frontend page-flow test suite
- No end-to-end sample-mode regression suite

---

## 9. Next improvements

**Short-term**
- Extend CI content validation beyond schema-header checks
- Add frontend tests for sample exhaustion, reset flow, and progression UI

**Medium-term**
- Expand challenge bank (maintain difficulty discipline)
- Add content-review workflow for question JSON changes
- Add submission history and per-user analytics

**Long-term**
- Richer learning analytics dashboard
- Revisit execution architecture if usage scales materially
