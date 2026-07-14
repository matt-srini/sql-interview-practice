# datathink — Data Interview Practice Platform

A data interview practice platform covering ten tracks. Users write SQL or Python, answer conceptual questions, get instant feedback, and work through plan-gated challenge banks. The product pairs a React frontend with a FastAPI backend, PostgreSQL-backed app state, DuckDB-backed SQL evaluation, a Python subprocess sandbox, learning paths, mock interviews, and plan-aware progression.

## Current State

- **965 practice questions** across 10 tracks with plan-gated unlock rules and persistent progress
- **1,269 mock-only questions** (Pro/Elite) across all tracks, never shown in the practice catalog
- **90 dedicated sample questions** (all 10 tracks × 3 difficulties × 3 questions each) — no login required, no impact on practice progress, and completely separate from the practice and mock banks.
- Challenge mode with persistent progress, bookmarks, draft autosave, hints, concept tags, and unlock logic
- Sample mode that is anonymous-friendly (no login required)
- Mock interviews: `benchmark` (fixed-shape track readiness signal, or role-based Mixed benchmark), `custom` (1–5 questions, 10–90 min), and `interview_loop` (Elite-only chain-driven dialogue) with plan-based limits and post-session analysis. Legacy `30min`/`60min` sessions are read-only history.
- Learning paths: 103 curated, track-specific walks through the practice catalog (they guide; they do not gate — access follows the standard plan policy: free = easy, Pro/Elite = all)
- Semantic concept tags, progressive hints, and company tags (SQL) surfaced in the practice UI
- Dashboard with coaching insights, streak tracking, weakest-concept signals, and (Elite) readiness scores + study plan
- Three subscription tiers (Free / Pro / Elite), billed via Razorpay (INR / India) or Paddle (USD / international, Merchant of Record)

## Question Bank

| Track | Easy | Medium | Hard | Practice total | Mock-only (Pro/Elite) |
|---|---|---|---|---|---|
| SQL | 37 | 50 | 31 | **118** | 196 (0 easy, 67 med, 129 hard) |
| Python | 33 | 30 | 18 | **81** | 103 (0 easy, 50 med, 53 hard) |
| Pandas | 28 | 40 | 25 | **93** | 132 (0 easy, 69 med, 63 hard) |
| PySpark | 40 | 45 | 42 | **127** | 150 (0 easy, 75 med, 75 hard) |
| Data Engineering | 30 | 35 | 26 | **91** | 110 (0 easy, 34 med, 76 hard) |
| Data Modeling | 25 | 31 | 25 | **81** | 97 (0 easy, 46 med, 51 hard) |
| Statistics | 31 | 43 | 26 | **100** | 134 (0 easy, 66 med, 68 hard) |
| ML Fundamentals | 30 | 40 | 30 | **100** | 143 (0 easy, 59 med, 84 hard) |
| Experimentation | 30 | 33 | 24 | **87** | 104 (0 easy, 45 med, 59 hard) |
| Product Sense | 30 | 33 | 24 | **87** | 100 (0 easy, 45 med, 55 hard) |
| **Total** | **314** | **380** | **271** | **965** | **1,269** |

Mock-only questions share the same TXNNN ID scheme, allocated at the top of each difficulty range. They never appear in the practice catalog.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Backend | Python, FastAPI, Uvicorn |
| App state | PostgreSQL (identity, sessions, progress, plans, billing) |
| SQL execution | DuckDB (in-memory, loaded from committed CSV datasets) |
| Python execution | AST-guarded subprocess sandbox (Python / Pandas) |
| Payments | Dual-rail: Razorpay (Orders + Subscriptions, INR) + Paddle (Merchant of Record, USD) — both with verified webhooks |
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
│   │   ├── pandas_questions/      # Pandas questions
│   │   ├── pyspark_questions/          # PySpark MCQ questions
│   │   ├── data_engineering_questions/ # Data Engineering MCQ / scenario / debug
│   │   ├── data_modeling_questions/    # Data Modeling MCQ / scenario
│   │   ├── statistics_questions/       # Statistics dual-subtype (conceptual MCQ + numerical Python)
│   │   ├── ml_fundamentals_questions/  # ML Fundamentals MCQ / scenario / predict-output / debug
│   │   ├── experimentation_questions/  # Experimentation MCQ / scenario / predict-output / debug
│   │   ├── product_sense_questions/    # Product Sense MCQ / scenario / debug / predict-output
│   │   └── paths/                      # Learning path configs
│   ├── datasets/                       # Committed CSVs + metadata JSON
│   ├── routers/                        # auth, catalog, questions, sample, mock, paths, dashboard, razorpay, paddle, spa, …
│   ├── tests/                          # Backend test suite
│   ├── alembic/                        # Postgres migrations
│   ├── database.py                     # DuckDB startup and shared state
│   ├── db.py                           # PostgreSQL persistence layer
│   ├── evaluator.py                    # SQL evaluation pipeline
│   ├── python_evaluator.py             # Python/Pandas execution pipeline
│   ├── unlock.py                       # Pure plan → access policy
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
| Product Sense | MCQ / scenario / debug / predict-output | No |

### Plan model

| Plan | Access |
|---|---|
| Free | All easy questions (medium and hard require Pro/Elite), 1 `benchmark` per rolling 7 days (easy only, practice-pool questions), free learning paths |
| Pro | Full practice catalog, all learning paths, 3 `benchmark`/day + 3 `custom`/day (independent counters, any difficulty), mock-only content pool unlocked |
| Elite | Full catalog, unlimited mocks (soft abuse cap), `focus_concepts` filter, `interview_loop` mode, deep mock analytics, readiness scores, study plan, session debrief |

`lifetime_pro` and `lifetime_elite` normalize to their base plans for access checks.

### Free-tier access (flat, plan-based)

Free unlocks **all easy questions across every track**; medium and hard require Pro or Elite. Access is a pure function of plan — no solve thresholds, no batch unlocks, no per-track caps (the progressive unlock ladder was removed 2026-06-29). Canonical policy: `backend/unlock.py`.

**Learning paths do not unlock anything** — they are curated walks through the catalog; a path question follows the same plan-based access as practicing it directly.

### Mock modes (post-Phase-3)

- **Benchmark** — fixed-shape track readiness signal, or role-based Mixed benchmark (Mixed requires role selection: Data Analyst / Data Engineer / Analytics Engineer / Data Scientist). Track-specific blueprints (e.g. Statistics enforces 1 numerical + 2 conceptual).
- **Custom** — user-tuned: 1–5 questions, 10–90 min. Mixed custom also requires role selection (defines the track pool).
- **Interview Loop** — Elite only. One chain per session (parent + all follow-ups, atomic); iterative interviewer dialogue. Not available on Mixed (chains are single-track).
- Legacy `30min` (Sprint drill) and `60min` sessions in history are read-only; they cannot be started new.

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
| [docs/features/pricing.md](./docs/features/pricing.md) | Plan entitlements, Razorpay + Paddle flows, CTA states, webhook rules |
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
