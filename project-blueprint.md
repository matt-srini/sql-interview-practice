# Project Blueprint

## 1. High-Level Overview

### What this application is
This is a SQL interview practice platform with:
- A React frontend for browsing questions, writing SQL, and reviewing results
- A FastAPI backend for progression, execution, evaluation, and API orchestration
- A DuckDB-backed data layer for metadata persistence plus isolated in-memory execution per question

### Problem it solves
It provides a controlled SQL practice environment where learners can:
- Work through ordered challenge questions by difficulty
- Try a separate sample track without affecting challenge progression
- Execute read-only SQL safely against realistic datasets
- Compare results against expected outputs and view official solutions

### Main implemented features
- Progressive challenge mode with sequential unlocks by difficulty
- Seeded practice question bank (currently 5 questions: 4 easy, 1 medium; hard is empty after the latest reset)
- Dedicated sample mode with exactly 3 sample questions per difficulty
- Sample exhaustion tracking and sample progress reset
- Query run and answer submit workflows
- Official solution and explanation reveal on submit
- SQL safety guardrails with parser-based validation
- Per-question SQL execution isolation
- Per-IP API rate limiting with Redis or in-memory fallback
- Request correlation via X-Request-ID response header and request_id-prefixed logs
- Standardized API error responses shaped as { error, request_id }
- Responsive challenge shell with sidebar navigation and mobile drawer
- Single-service production deployment path for Railway + Cloudflare

---

## 2. Architecture Overview

### Frontend
- Framework: React 18 + React Router + Vite
- API client: Axios via a shared client in frontend/src/api.js
- Editor: Monaco Editor via @monaco-editor/react
- Core responsibilities:
  - Route orchestration for landing, sample, and challenge flows
  - Rendering question metadata, schema, results, and correctness feedback
  - Running and submitting SQL through backend APIs
  - Displaying progression state via the challenge catalog sidebar
  - Resolving API base URLs for both local development and production-style hosting

Key frontend entry points:
- frontend/src/App.js
- frontend/src/api.js
- frontend/src/catalogContext.js
- frontend/src/components/AppShell.js
- frontend/src/pages/QuestionPage.js
- frontend/src/pages/SampleQuestionPage.js
- frontend/src/pages/LandingPage.js

### Backend
- Framework: FastAPI
- Core responsibilities:
  - API layer and request validation
  - Best-effort user identity assignment with cookie/header support
  - Progression computation and persistence
  - SQL query validation and execution
  - Answer evaluation
  - Sample sequencing and reset
  - Rate limiting middleware
  - Production serving of the built frontend bundle

Key backend modules:
- backend/main.py
- backend/config.py
- backend/deps.py
- backend/evaluator.py
- backend/sql_guard.py
- backend/progress.py
- backend/questions.py
- backend/sample_questions.py
- backend/database.py
- backend/rate_limiter.py
- backend/routers/system.py
- backend/routers/catalog.py
- backend/routers/questions.py
- backend/routers/sample.py
- backend/routers/spa.py

### Database and query engine
- Engine: DuckDB
- Persistent database file: backend/sql_practice.duckdb
- Dataset source: CSV files in backend/datasets
- Current practice datasets: users.csv and orders.csv (orders uses the unified user_id-based schema)
- Persistent DuckDB usage:
  - Loaded base tables for local inspection and health visibility
  - user_progress table for challenge completion tracking
  - user_sample_seen table for sample exposure tracking
- Query execution usage:
  - Each query runs in a fresh in-memory DuckDB connection
  - Only the current question's dataset_files are loaded into that isolated connection

### Deployment model

#### Local development
- Frontend runs under Vite on port 5173
- Backend runs under FastAPI/Uvicorn on port 8000
- Vite can proxy /api requests to the backend during dev

#### Production path
- Recommended target: GitHub -> Railway -> Cloudflare
- The repository root Dockerfile builds the frontend and runs the backend as a single service
- FastAPI serves the built SPA and the API from one public origin
- Same-origin /api requests are the default production behavior

### Component interaction and request flow
1. User interacts in the browser UI.
2. Frontend resolves the backend base URL using frontend/src/api.js.
3. Browser sends API requests to /api on the current origin in production, or through Vite/localhost logic in development.
4. FastAPI routes in backend/routers/* process requests (wired by backend/main.py).
5. Query execution and evaluation run through evaluator.py and isolated DuckDB connections.
6. Progress and sample state are read and written through progress.py.
7. Backend returns JSON payloads to the frontend.
8. In production, FastAPI also serves the built frontend and SPA route fallbacks.

---

## 3. Project Structure Breakdown

### Root-level files
- README.md: setup, local development, and deployment documentation
- ARCHITECTURE.md: short architecture notes from earlier iterations
- MANUAL_TEST_CHECKLIST.md: manual QA checklist
- TODO_FUTURE.md: future enhancements backlog
- docker-compose.yml: local multi-container dev stack for Redis + backend + frontend
- Dockerfile: root production image for single-service deployment
- railway.json: Railway deployment metadata and health check settings
- .dockerignore: Docker build context exclusions
- project-blueprint.md: this architecture reference

### backend/
- main.py: FastAPI app wiring, lifespan setup, middleware, and router registration
- config.py: backend/frontend path constants used by static serving routes
- deps.py: shared request models and dependency helpers used across routers
- content/questions/: JSON-backed challenge content files (`easy.json`, `medium.json`, `hard.json`) plus `schemas.json`
- routers/: domain-focused route modules (`system.py`, `catalog.py`, `questions.py`, `sample.py`, `spa.py`)
- database.py: DuckDB connection helpers, CSV loading, and isolated execution connection creation
- evaluator.py: query execution and result evaluation logic
- sql_guard.py: parser-based SQL safety checks
- progress.py: persistence and unlock/sample progression logic
- questions.py: challenge bank loading, indexing, and public payload shaping
- sample_questions.py: dedicated sample bank with 3 questions per difficulty
- rate_limiter.py: in-memory and Redis-backed rate limiter implementations
- question_bank/: seeded challenge question content
- datasets/: CSV source data used for SQL practice
- tests/: API, evaluator, and rate limiter tests
- requirements.txt: backend dependencies
- Dockerfile: backend-only container build for local compose workflows

### frontend/
- src/App.js: route tree
- src/index.js: React bootstrap
- src/App.css: global, layout, and component styles
- src/api.js: shared Axios client with local and production base URL resolution
- src/catalogContext.js: challenge catalog provider and refresh logic
- src/components/AppShell.js: challenge shell with topbar, sidebar, and responsive layout
- src/components/SidebarNav.js: grouped challenge navigation and lock/next/solved states
- src/components/SQLEditor.js: Monaco wrapper
- src/components/ResultsTable.js: tabular result rendering
- src/components/SchemaViewer.js: schema rendering
- src/pages/LandingPage.js: entry page with sample and challenge choices
- src/pages/SampleQuestionPage.js: sample workflow with reset and exhaustion handling
- src/pages/QuestionPage.js: challenge question interaction page
- src/pages/QuestionListPage.js: alternate list page, currently not routed
- vite.config.js: Vite config, dev proxy, and test config
- package.json: scripts and dependencies
- Dockerfile: frontend-only container build for local compose workflows

---

## 4. Backend Deep Dive

### A. API layer

Router composition entry point: backend/main.py

Route modules:
- backend/routers/system.py
- backend/routers/catalog.py
- backend/routers/questions.py
- backend/routers/sample.py
- backend/routers/spa.py

#### System and catalog routes
- GET /health
  - Purpose: service status and currently loaded persistent DuckDB tables
  - Response: { status, tables_loaded }

- GET /catalog and GET /api/catalog
  - Purpose: grouped challenge questions with per-user progression state
  - User identity: cookie sql_practice_uid or header X-User-Id
  - Response: { user_id, groups[] }

#### Challenge routes
- GET /questions and GET /api/questions
  - Purpose: lightweight challenge question list

- GET /questions/{question_id} and GET /api/questions/{question_id}
  - Purpose: challenge question detail payload
  - Behavior:
    - 404 if missing
    - 403 if locked for current user and not already solved
    - omits expected_query, solution_query, and explanation
  - Includes progress metadata: state, is_next, unlocked, mode=practice

- POST /run-query and POST /api/run-query
  - Input: { query, question_id }
  - Behavior:
    - rejects locked challenge questions
    - validates SQL and executes against the current question's isolated dataset scope
  - Response: { columns, rows, row_limit }

- POST /submit and POST /api/submit
  - Input: { query, question_id }
  - Behavior:
    - rejects locked challenge questions
    - evaluates user_query against expected_query
    - on correct, marks the question solved in user_progress
  - Response: evaluation payload plus solution_query and explanation

#### Sample routes
- GET /api/sample/{difficulty}
  - Purpose: return the next unseen sample question for a difficulty
  - Behavior:
    - validates difficulty
    - consults user_sample_seen
    - marks the selected sample as seen
    - returns sample metadata: shown_count, remaining, total, exhausted
    - returns 409 when all 3 are exhausted

- POST /api/sample/{difficulty}/reset
  - Purpose: clear sample progress for the current user and difficulty
  - Effect: next fetch starts again at sample order 1

- POST /api/sample/run-query
  - Purpose: execute sample SQL in sample-question context

- POST /api/sample/submit
  - Purpose: evaluate sample answer and return official solution/explanation
  - Does not update challenge progression

#### Frontend serving routes
- GET /
  - Serves frontend/dist/index.html in production-style deployments

- GET /{asset_path:path}
  - Serves frontend assets when present
  - Falls back to index.html for SPA routes
  - Excludes /api/* from frontend fallback behavior

### B. Query execution logic

Files:
- backend/evaluator.py
- backend/database.py

Execution path:
1. Query is validated and normalized with validate_read_only_select_query in backend/sql_guard.py.
2. evaluator.py executes the validated query as-is (preserving ORDER BY semantics).
3. database.py creates a fresh in-memory DuckDB connection for the current question.
4. Only the tables listed in question.dataset_files are loaded from CSV into that connection.
5. Query execution is performed inside a thread with a 3-second timeout.
6. Results are capped to 200 rows for payload safety and serialized as JSON columns/rows.

Important isolation behavior:
- User queries no longer execute against the shared file-backed DuckDB catalog.
- Users can only access the tables explicitly referenced by the current question.
- Dataset file names and resolved paths are validated before loading.

### C. Evaluation logic

File: backend/evaluator.py

Evaluation algorithm:
1. Execute the user query using the question-scoped isolated connection.
2. Execute the expected query using the same question-scoped isolated connection rules.
3. Convert both outputs into pandas DataFrames.
4. Normalize by:
   - lowercasing column names
   - sorting columns alphabetically
  - canonicalizing NULL/NaN and numerics (including float tolerance)
  - sorting rows only for order-insensitive comparisons
5. Compare normalized DataFrames for equality.

Response shape from evaluate:
- correct: boolean
- user_result: { columns, rows, row_limit }
- expected_result: { columns, rows, row_limit }

Implications:
- Column ordering differences are ignored
- Row ordering differences are ignored unless expected SQL explicitly uses ORDER BY
- Minor type and representation mismatches can still affect equality in edge cases

### D. Safety and guardrails

File: backend/sql_guard.py

Implemented guardrails:
- Only a single SQL statement is allowed
- Only SELECT-style roots are allowed
- Mutating, DDL, transaction, and admin statements are rejected
- Max query length is capped at 5000 characters
- Max join count is capped at 4
- Cartesian joins are blocked unless joins use ON or USING appropriately

Additional runtime safeguards:
- Query timeout: 3 seconds
- Result row cap: 200 rows
- Rate limiting middleware on API requests
- Per-question isolated in-memory execution scope

Rate limiting implementations:
- InMemoryRateLimiter: process-local sliding window
- RedisRateLimiter: shared/distributed limiting when REDIS_URL is configured

---

## 5. Frontend Deep Dive

### Routing and pages

File: frontend/src/App.js

Routes:
- / -> LandingPage
- /sample/:difficulty -> SampleQuestionPage
- /practice -> AppShell
  - /practice/questions/:id -> QuestionPage
- /questions/:id -> legacy redirect to /practice/questions/:id

Page responsibilities:
- LandingPage:
  - introduces the product
  - links into sample mode and challenge mode
- SampleQuestionPage:
  - fetches the next unseen sample for a difficulty
  - runs and submits sample SQL
  - supports reset and exhaustion handling
- QuestionPage:
  - fetches challenge question details
  - runs and submits challenge SQL
  - refreshes the challenge catalog after correct submission
  - shows an in-context “Next Question” button after a correct submit

### API client behavior

File: frontend/src/api.js

API resolution strategy:
- If VITE_BACKEND_URL is set, the frontend calls `${VITE_BACKEND_URL}/api`
- If the app is running on localhost without the backend on the same port, it falls back to `http://localhost:8000/api`
- Otherwise it uses same-origin /api
- Axios uses `withCredentials: true` so browser identity cookies are sent during cross-origin local development

This is what allows both:
- Vite-based local development
- Same-origin production hosting from FastAPI
- Split-origin deployments if needed later

### Key components
- AppShell:
  - topbar, session badge, responsive sidebar, and challenge layout
  - redirects /practice to the next available question
- SidebarNav:
  - grouped difficulty navigation
  - lock/next/solved indicators
- SQLEditor:
  - Monaco SQL editor wrapper
- ResultsTable:
  - tabular result rendering
- SchemaViewer:
  - schema display for current question datasets

### State management approach
- Context-based challenge catalog state in frontend/src/catalogContext.js
- CatalogProvider fetches /catalog through the shared API client and exposes:
  - catalog
  - loading
  - error
  - refresh()
- QuestionPage triggers refresh() after a correct challenge submission so the next question unlock appears immediately

---

## 6. Data Flow (Step-by-Step)

### Challenge flow
1. User opens /practice.
2. AppShell reads catalog data and redirects to the next available challenge question.
3. QuestionPage fetches the question detail payload.
4. User writes SQL in Monaco.
5. On Run:
   - frontend posts query + question_id to /api/run-query or equivalent same-origin route
   - backend validates SQL and challenge access
   - backend creates an isolated per-question DuckDB connection and executes the query
   - frontend renders the result table
6. On Submit:
   - frontend posts to /api/submit
   - backend runs both the user query and expected query in the question-scoped isolated environment
   - backend compares normalized outputs
   - backend returns correctness, expected/user outputs, solution, and explanation
7. If correct, backend records the solve and frontend refreshes the catalog.
8. Sidebar and unlock state update in the UI.

### Sample flow
1. User opens /sample/{difficulty}.
2. Frontend requests the next unseen sample for that difficulty.
3. Backend selects the next sample, records it in user_sample_seen, and returns sample metadata.
4. Frontend renders the sample and current shown/remaining counts.
5. User can run or submit SQL against sample endpoints.
6. User can fetch another sample until exhausted, or reset sample progress.
7. Once all 3 are seen, the backend returns 409 and the frontend renders the exhausted state.

### Production serving flow
1. Railway starts the root Docker image.
2. The image contains both backend code and frontend/dist assets.
3. FastAPI serves index.html at / and asset files under /assets.
4. Browser-side routes such as /sample/easy fall back to index.html.
5. Frontend API calls use same-origin /api by default.

---

## 7. Strengths of Current Implementation

- Clear separation of concerns across backend modules for API orchestration, evaluation, guardrails, progression, and rate limiting.
- Stronger execution safety than a typical demo app because SQL runs inside a per-question isolated in-memory DuckDB context.
- Server-side enforcement of challenge locks, not just UI-level hiding.
- Dedicated sample mode is fully separated from challenge progression.
- Frontend API routing now works across local dev, direct localhost serving, and same-origin production deployment.
- The production path is simpler than the original split-service setup because one container serves both UI and API.
- Good validation coverage around API behavior, evaluator behavior, and rate limiting.
- Railway-targeted root Dockerfile and health check config exist in the repo.

---

## 8. Weaknesses and Risks

### Architectural and maintainability risks
- Route composition is modular now, but cross-module contracts (shared deps/models/imports) should stay disciplined to avoid drift.
- Question content remains hard-coded in Python, which is not ideal for non-engineering content workflows.
- The repo currently maintains both a production single-service path and older compose-based split frontend/backend dev containers, which adds some operational duality.

### Scalability and runtime risks
- Query isolation is safer, but it increases per-request overhead because CSV datasets are loaded into a fresh in-memory DuckDB connection every time.
- DuckDB remains acceptable for low-to-moderate educational traffic, but it is not a great fit for high-concurrency, write-heavy, multi-user systems.
- Without Redis, rate limiting is still per-process only.

### Security and abuse risks
- Authentication is still best-effort browser identity rather than a real account system.
- The progression cookie is HttpOnly and SameSite=Lax, but it is not configured with a Secure flag or explicit expiration policy.
- Sample and challenge submit endpoints intentionally reveal official solutions, which is fine for practice but easy to script.
- CORS is configurable now, but split-origin deployment still requires careful env configuration.

### Product risks
- Progress is browser-identity-based rather than account-based.
- There is no analytics, moderation, content tooling, or admin workflow.

---

## 9. Missing Features

- Real authentication and multi-device user accounts
- Explicit challenge progress reset in the UI and API
- Admin tooling for managing question content
- Metrics and tracing (request correlation via request_id is implemented)
- Submission history and audit trail
- Better feedback tooling such as hints or richer diffing between results
- Content migrations/versioning beyond code changes
- Stronger multi-tenant execution governance if public usage grows

---

## 10. Scalability Assessment

### Can this support multiple users?
- Yes, for low-to-moderate traffic and educational/demo usage.
- It is materially safer than the earlier shared-table execution model because question-level dataset isolation is now enforced.

### What breaks under load first?
- Per-request isolated DuckDB setup cost
- Python-side execution concurrency limits
- Lack of shared rate limiting if Redis is absent
- Limited observability for production incident triage

### What would need to change for larger-scale production?
- Move user/progress metadata to a more operationally standard store if usage grows materially
- Consider prebuilt per-question execution sandboxes or more efficient dataset loading strategies
- Add real auth/session management
- Add stronger telemetry and environment-specific security controls
- Externalize and validate question content outside the application code

---

## 11. Suggested Improvements

### Short-term
- Add focused integration tests for order-sensitive evaluation (ORDER BY) and order-insensitive comparison paths
- Add frontend tests for sample reset, exhaustion, and same-origin production behavior
- Document environment variables and deploy settings more explicitly for Railway
- Add an explicit challenge reset endpoint and UI

### Medium-term
- Externalize question definitions into validated content files or a content store
- Add metrics (e.g., request latency, error rates) and tracing as needed
- Harden cookie settings per environment, including Secure in production
- Add a Redis-backed production recommendation to the Railway setup

### Long-term
- Introduce real user accounts and optional organization/classroom support
- Move toward a more scalable execution architecture if public usage becomes significant
- Add richer learning feedback and analytics
- Evolve the service boundary only when product complexity justifies it; the current single-service deploy is the right default for this stage

---

## 12. Summary

Current state:
- This is a strong MVP or advanced prototype for SQL practice with meaningful safety controls, progression logic, and a simpler production deployment model than before.
- The most important architectural improvement since the earlier blueprint is SQL execution isolation: queries now only see the datasets declared for the current question.
- The most important deployment improvement is the single-service production path: FastAPI serves both the React app and the API, which fits Railway + Cloudflare well.

Readiness level:
- Good for local use, demos, and small-scale hosted usage.
- Still not fully production-hardened for broad public scale without stronger auth, observability, and higher-concurrency execution planning.