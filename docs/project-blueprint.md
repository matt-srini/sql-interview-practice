# Project Blueprint

> **Navigation:** [Docs index](./README.md) · [Backend](./backend.md) · [Frontend](./frontend.md) · [Datasets](./datasets.md) · [Deployment](./deployment.md)

---

## 1. What this is

A data interview practice platform with four tracks:

| Track | Questions | Execution |
|---|---|---|
| SQL | 86 challenge questions | DuckDB in-memory |
| Python | 10+ algorithm questions | Subprocess sandbox + test cases |
| Python (Data) | 10+ pandas/numpy questions | Subprocess sandbox + DataFrame comparison |
| PySpark | 10+ conceptual MCQ questions | No execution (answer matching) |

- React frontend for browsing questions, writing code (SQL/Python), answering MCQs, and reviewing results
- FastAPI backend for routing, progression, execution, evaluation, and static SPA serving
- PostgreSQL-backed product-state layer with per-topic progress tracking
- DuckDB in-memory for SQL execution; Python subprocess sandbox for algorithm and data tracks

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

| Track | Questions | Status |
|---|---|---|
| SQL | 86 (30 easy, 30 medium, 26 hard) | Full curriculum |
| Python | 10 easy | MVP — expanding |
| Python (Data) | 10 easy | MVP — expanding |
| PySpark | 10 easy | MVP — expanding |

- **Sample questions (SQL only):** 9 total — 3 per difficulty
- Every question carries `hints` (1–2 entries) and `concepts` (semantic tags)
- SQL question schemas validated against committed dataset headers at catalog load time

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
- `db.py` — async PostgreSQL pool, schema, all app-state persistence (topic-aware)
- `database.py` — DuckDB engine startup, table loading, cursor access
- `evaluator.py` — SQL query execution, timeout, result serialization, comparison
- `unlock.py` — pure plan + solve-history → unlock policy (applies to all topics)
- `questions.py` / `sample_questions.py` — SQL catalog loaders and validators
- `python_questions.py` — Python algorithms catalog loader
- `python_data_questions.py` — Python (Data) catalog loader
- `pyspark_questions.py` — PySpark MCQ catalog loader
- `sql_guard.py` — SQL safety validation
- `python_guard.py` — AST-based Python code validator (import allowlist per track)
- `python_sandbox_harness.py` — subprocess harness for Python execution
- `python_evaluator.py` — spawns harness, enforces timeout, compares results
- `progress.py` — challenge/sample persistence wrappers
- `rate_limiter.py` — in-memory and Redis-backed limiter
- `models.py` / `deps.py` — Pydantic models and shared dependencies
- `sql_analyzer.py` — SQL analysis utilities
- `middleware/request_context.py` — request-id, logging context, X-Request-ID
- `routers/` — auth, system, catalog, questions, sample, plan, stripe, python_questions, python_data_questions, pyspark_questions, dashboard, spa
- `content/questions/` — SQL challenge question JSON (easy.json, medium.json, hard.json)
- `content/python_questions/` — Python algorithm questions
- `content/python_data_questions/` — Python (Data) questions
- `content/pyspark_questions/` — PySpark MCQ questions
- `datasets/` — committed CSVs + metadata
- `scripts/` — dataset generator, anonymous user cleanup
- `tests/` — API, evaluator, rate limiter tests

### `frontend/`
- `src/App.js` — route tree with topic-scoped routes
- `src/api.js` — Axios client, base URL resolution
- `src/catalogContext.js` — topic-aware catalog state and refresh
- `src/App.css` — global styles and design tokens
- `src/contexts/AuthContext.js` — auth state management
- `src/contexts/TopicContext.js` — TRACK_META, TopicProvider, useTopic()
- `src/components/` — AppShell, SidebarNav, CodeEditor, SQLEditor, ResultsTable, SchemaViewer, TestCasePanel, PrintOutputPanel, VariablesPanel, MCQPanel, TrackProgressBar
- `src/pages/` — LandingPage, TrackHubPage, QuestionPage, ProgressDashboard, SampleQuestionPage, AuthPage

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
