# Project Blueprint

## 1. High-Level Overview

### What this application is
This repository is a SQL interview practice platform with:
- A React frontend for browsing questions, writing SQL, and reviewing results
- A FastAPI backend for routing, progression, execution, evaluation, and static SPA serving
- A PostgreSQL-backed product-state layer plus a shared in-memory DuckDB execution engine

### Problem it solves
It provides a controlled SQL practice environment where learners can:
- Work through challenge questions with plan-aware unlock rules
- Use a separate sample track without affecting challenge progression
- Execute read-only SQL safely against realistic CSV-backed datasets
- Compare their results against expected outputs and then review official solutions and explanations

### Current implemented features
- Unified anonymous and registered identity with cookie-backed sessions
- PostgreSQL-backed users, sessions, progress, sample tracking, plan changes, and Stripe audit events
- Plan-aware unlock computation shared across catalog, question guards, and profile routes
- JSON-backed challenge question bank in backend/content/questions/
- Python-backed sample question bank with exactly 3 questions per difficulty
- Deterministic dataset generation via backend/scripts/generate_v1_datasets.py
- Process-singleton DuckDB query engine loaded once at startup
- SQL safety validation with parser-based checks in backend/sql_guard.py
- Query execution timeout and row-count capping
- Result-set comparison with normalization and ORDER BY-sensitive evaluation behavior
- Sample exhaustion tracking and per-difficulty sample reset
- Per-IP rate limiting with Redis or in-memory fallback
- Stripe Checkout creation plus verified, idempotent webhook processing
- Health checks that validate both Postgres and the query engine
- Anonymous-session cleanup script for stale users and expired sessions
- Request correlation with X-Request-ID headers and request_id-prefixed logs
- Standardized API error payloads shaped as { error, request_id }
- Single-service production deployment path where FastAPI serves both the API and the built frontend

### Current content footprint
- Challenge questions: 86 total
  - easy: 30
  - medium: 30
  - hard: 26
- Sample questions: 9 total
  - easy: 3
  - medium: 3
  - hard: 3
- Question schemas are validated against committed dataset headers during catalog loading
- Every question carries `hints` (1–2 entries) and `concepts` (semantic reasoning tags) fields

---

## 2. Architecture Overview

### Frontend
- Framework: React 18 + React Router + Vite
- API client: Axios via frontend/src/api.js
- Editor: Monaco Editor via @monaco-editor/react
- Test tooling: Vitest + React Testing Library

Core responsibilities:
- Route orchestration for landing, sample, and challenge flows
- Rendering question metadata, schema, results, feedback, solution, and explanation
- Running and submitting SQL through backend APIs
- Displaying challenge progression state in the sidebar shell
- Resolving API base URLs for local development, same-origin production, and split-origin deployment

Key frontend entry points:
- frontend/src/App.js
- frontend/src/api.js
- frontend/src/catalogContext.js
- frontend/src/components/AppShell.js
- frontend/src/components/SidebarNav.js
- frontend/src/components/SQLEditor.js
- frontend/src/components/ResultsTable.js
- frontend/src/components/SchemaViewer.js
- frontend/src/pages/LandingPage.js
- frontend/src/pages/QuestionPage.js
- frontend/src/pages/SampleQuestionPage.js


### Backend
- **Framework:** FastAPI
- **Persistence:** PostgreSQL for product state, DuckDB for SQL execution only
- **Test tooling:** pytest + httpx

**Core responsibilities:**
- API layer and dependency handling
- User identity via unified session_token cookie with anonymous-to-registered continuity
- Challenge progression, sample sequencing, plans, and billing audits persisted in PostgreSQL
- SQL validation, execution, and evaluation (read-only, single-statement, timeout, row cap)
- Per-IP rate limiting (Redis-backed or in-memory)
- Stripe Checkout and verified webhook handling
- User profile and plan management
- Request-id assignment and structured logging
- Serving the built frontend bundle in production

**Key backend modules:**
- backend/main.py: app wiring, middleware, exception handlers, router registration, lifespan setup
- backend/config.py: environment settings, CORS, rate-limiter, frontend dist path
- backend/db.py: async PostgreSQL access layer for users, sessions, progress, plans, and Stripe audit data
- backend/database.py: DuckDB golden connection startup, table loading, and cursor access for execution
- backend/evaluator.py: query execution, timeout, result serialization, evaluation normalization
- backend/progress.py: challenge/sample persistence wrappers
- backend/unlock.py: pure unlock and next-question policy logic
- backend/questions.py: challenge catalog loader/validator
- backend/sample_questions.py: sample catalog loader
- backend/rate_limiter.py: in-memory and Redis-backed rate limiter
- backend/sql_guard.py: SQL validation and safety checks
- backend/middleware/request_context.py: request-id assignment, logging context, X-Request-ID header
- backend/routers/: system, auth, catalog, questions, sample, plan, stripe, spa
- backend/content/questions/: challenge question content files and schema config
- backend/datasets/: committed generated CSV datasets + metadata
- backend/scripts/generate_v1_datasets.py: dataset generator/validator
- backend/scripts/cleanup_anonymous.py: stale anonymous-user cleanup command
- backend/tests/: backend API, evaluator, and rate limiter tests

**Data and execution model:**
- Source datasets: backend/datasets/
- PostgreSQL: source of truth for users, sessions, progress, sample exposure, plan changes, and Stripe event audits
- On startup: backend/database.py loads all committed CSVs into a single in-memory DuckDB connection
- For query execution: backend/database.py returns lightweight cursors against the shared in-memory engine
- DuckDB is execution-only and never stores product state
- All committed datasets are visible to execution, with writes blocked by sql_guard.py and query limits

**Stripe and user profile logic:**
- User profiles, sessions, and plans are stored in PostgreSQL
- Direct plan changes remain available in development mode for testing
- Stripe checkout lives in backend/routers/stripe.py
- Webhooks are signature-verified, idempotent, and recorded in audit tables
- Solved questions always remain solved across upgrades and downgrades


### Deployment model

#### Local development
- Frontend: Vite dev server on port 5173
- Backend: Uvicorn/FastAPI on port 8000
- Optional: docker-compose stack with Postgres, Redis, backend, and frontend

#### Production path
- Root Dockerfile builds frontend and runs backend as a single service
- FastAPI serves frontend/dist and /api routes from one origin
- Railway: intended hosting target for single-service deploy
- Cloudflare: intended fronting layer for custom domain delivery

### Request flow
1. User interacts with browser UI
2. Frontend resolves API base URL via frontend/src/api.js
3. Requests go to same-origin /api in production, or to localhost/Vite-backed routing in development
4. FastAPI routes requests through backend/routers/* registered in backend/main.py
5. SQL validation and execution run through backend/sql_guard.py, backend/evaluator.py, and backend/database.py
6. Progress, sample exposure, identity, and plan state are read/written via backend/db.py and backend/progress.py
7. FastAPI returns JSON payloads to the frontend
8. In production, FastAPI also serves the built SPA and asset routes

---

## 3. Project Structure Breakdown

### Root-level files
- README.md: setup and usage documentation and current question-bank inventory
- ARCHITECTURE.md: shorter historical architecture notes
- MANUAL_TEST_CHECKLIST.md: manual QA checklist
- TODO_FUTURE.md: backlog and future enhancements
- docker-compose.yml: local multi-container stack for Postgres + Redis + backend + frontend
- Dockerfile: root single-service production image
- railway.json: Railway deployment metadata
- docs/project-blueprint.md: this detailed architecture and state reference
- docs/question-authoring-guidelines.md: rules for challenge question authoring quality and structure

### backend/
- main.py: app wiring, middleware, exception handlers, router registration, lifespan setup
- config.py: environment settings, CORS origins, rate-limiter settings, frontend dist path
- deps.py: request models and shared dependencies
- db.py: PostgreSQL connection pool, schema helpers, and app-state persistence
- database.py: shared DuckDB query engine and cursor helpers
- evaluator.py: query execution, timeout handling, result serialization, evaluation normalization
- exceptions.py: user-facing application exception types
- progress.py: challenge completion and sample-exposure persistence wrappers
- unlock.py: pure entitlement and next-question policy logic
- questions.py: validated JSON-backed challenge catalog loading and shaping
- sample_questions.py: validated Python-backed sample catalog with fixed counts by difficulty
- rate_limiter.py: in-memory and Redis-backed rate limiter implementations
- sql_guard.py: SQL validation and safety checks
- middleware/request_context.py: request-id assignment, logging context, X-Request-ID header propagation
- routers/: route modules for auth, system, catalog, challenge, sample, plan, Stripe, and SPA/static serving
- content/questions/: challenge question content files and schema config
- datasets/: committed generated CSV datasets plus metadata JSON
- scripts/generate_v1_datasets.py: dataset generator and validator
- tests/: backend API, evaluator, and rate limiter tests

### frontend/
- src/App.js: route tree
- src/index.js: React bootstrap
- src/App.css: shared styling
- src/api.js: shared Axios client and API base URL resolution
- src/catalogContext.js: challenge catalog state and refresh logic
- src/components/AppShell.js: challenge shell and responsive layout wrapper
- src/components/SidebarNav.js: grouped challenge navigation and lock/next/solved indicators
- src/components/SidebarNav.test.js: current frontend test coverage
- src/components/SQLEditor.js: Monaco SQL editor wrapper
- src/components/ResultsTable.js: tabular result rendering
- src/components/SchemaViewer.js: table schema rendering
- src/pages/LandingPage.js: entry page for sample and challenge flows
- src/pages/QuestionPage.js: challenge question interaction page
- src/pages/SampleQuestionPage.js: sample workflow page
- src/pages/QuestionListPage.js: present in source but not currently routed in App.js
- package.json: frontend scripts and dependencies
- vite.config.js: Vite config and test configuration

---

## 4. Dataset Inventory

### Source of truth
The current repository has two authoritative dataset references:
- backend/scripts/generate_v1_datasets.py: table definitions, generation rules, edge-case design, and validation logic
- backend/datasets/dataset_metadata_v1.json: generated metadata including row counts and quality metrics for the committed dataset snapshot

Important note:
- A checked-in backend/datasets/DATA_DICTIONARY_V1.md file is not present in the current workspace.
- Documentation should therefore treat the generator script and metadata JSON as the current source of truth.

### Current committed snapshot
The committed metadata file indicates:
- dataset version: v1
- seed: 20260318
- scale: small

Current committed row counts:
- users: 600
- categories: 16
- products: 260
- orders: 4200
- order_items: 12665
- payments: 4737
- sessions: 9000
- events: 44964
- support_tickets: 1300
- departments: 10
- employees: 180

### Supported scale ranges
The generator currently supports two scale profiles:
- small
- medium

For the fixed-profile tables, the current supported ranges are:
- users: about 600 to 1000
- categories: about 16 to 24
- products: about 260 to 450
- orders: about 4200 to 7000
- sessions: about 9000 to 15000
- support_tickets: about 1300 to 2400
- departments: about 10 to 14
- employees: about 180 to 300

For derived tables, the actual counts depend on generated behavior volume:
- order_items: roughly 12000 to 21000
- payments: roughly 4700 to 7900
- events: roughly 45000 to 75000

### CSV catalog

#### users.csv
- Models the user/account dimension for the platform's business data
- Key columns: user_id, name, email, signup_date, country, acquisition_channel, plan_tier, is_active
- Current committed count: 600
- Typical generated range: about 600 to 1000
- Designed for signup analysis, country/channel segmentation, activity filtering, and anti-join exercises involving users with no orders or no sessions

#### categories.csv
- Models the product category taxonomy
- Key columns: category_id, category_name, parent_category
- Current committed count: 16
- Typical generated range: about 16 to 24
- Includes optional parent_category values and intentionally unsold categories for anti-join and coverage-gap questions

#### products.csv
- Models the product catalog sold through the commerce flow
- Key columns: product_id, product_name, category_id, brand, price, launch_date, is_active
- Current committed count: 260
- Typical generated range: about 260 to 450
- Supports catalog analytics, category joins, active/inactive filtering, and launch-date null handling

#### orders.csv
- Models order headers linked to users
- Key columns: order_id, user_id, order_date, status, gross_amount, discount_amount, net_amount, payment_status
- Current committed count: 4200
- Typical generated range: about 4200 to 7000
- Supports order-volume, discount, net-revenue, and lifecycle-status analysis
- All question content is aligned to these column names; the legacy amount column is no longer referenced

#### order_items.csv
- Models line items within each order
- Key columns: order_item_id, order_id, product_id, quantity, unit_price, line_amount
- Current committed count: 12665
- Typical generated range: roughly 12000 to 21000
- Supports basket analysis, product revenue, item-level joins, and order-detail aggregation

#### payments.csv
- Models payment events attached to orders
- Key columns: payment_id, order_id, payment_date, payment_method, amount, status
- Current committed count: 4737
- Typical generated range: roughly 4700 to 7900
- Includes paid, failed, refunded, and chargeback states plus some deliberate amount mismatches for reconciliation-style questions

#### sessions.csv
- Models user web sessions
- Key columns: session_id, user_id, session_start, device_type, traffic_source, country
- Current committed count: 9000
- Typical generated range: about 9000 to 15000
- Supports traffic-source analysis, device segmentation, and user activity/funnel questions

#### events.csv
- Models event streams inside sessions
- Key columns: event_id, session_id, user_id, event_time, event_name, product_id
- Current committed count: 44964
- Typical generated range: roughly 45000 to 75000
- Supports funnel analysis across view_product, add_to_cart, start_checkout, and purchase events
- product_id can be null in some purchase events, which is useful for null-handling questions

#### support_tickets.csv
- Models customer support cases linked to users
- Key columns: ticket_id, user_id, created_at, issue_type, priority, status, resolution_hours
- Current committed count: 1300
- Typical generated range: about 1300 to 2400
- Supports service-operations analysis including SLA timing, unresolved tickets, issue mix, and priority breakdowns

#### departments.csv
- Models the department dimension for the HR dataset slice
- Key columns: department_id, department_name, region
- Current committed count: 10
- Typical generated range: about 10 to 14
- Includes deliberate empty departments for anti-join and headcount-gap questions

#### employees.csv
- Models employee records linked to departments
- Key columns: employee_id, employee_name, email, salary, department_id, hire_date, country
- Current committed count: 180
- Typical generated range: about 180 to 300
- Supports ranking, compensation, department aggregation, hire-date analysis, and window-function questions
- Salary ties are intentionally introduced for ranking exercises

### Built-in data quality features
The generator intentionally creates edge cases that are useful for interview questions:
- users with no sessions
- users with sessions but no orders
- categories with no sales
- departments with no employees
- null emails
- null product launch dates
- null ticket resolution_hours for unresolved tickets
- salary ties in employees
- mixed payment statuses and small reconciliation mismatches

---

## 5. Backend Deep Dive

### A. API layer

Router composition entry point:
- backend/main.py

Registered route modules:
- backend/routers/auth.py
- backend/routers/system.py
- backend/routers/catalog.py
- backend/routers/questions.py
- backend/routers/sample.py
- backend/routers/plan.py
- backend/routers/stripe.py
- backend/routers/spa.py

#### Auth routes
- Prefix: /api/auth
- Anonymous sessions are upgraded in place on registration when possible
- Login can merge anonymous progress into an existing account
- Includes register, login, logout, and current-user endpoints

#### System route
- GET /health
  - Returns: { status, postgres, tables_loaded }
  - Used for service health and orchestration checks

#### Catalog routes
- GET /catalog
- GET /api/catalog
  - Returns grouped challenge questions by difficulty for the current user
  - Each group includes counts for total, solved, and unlocked
  - Each question summary includes id, title, difficulty, order, state, and is_next

#### Challenge routes
- GET /questions
- GET /api/questions
  - Returns lightweight challenge question summaries

- GET /questions/{question_id}
- GET /api/questions/{question_id}
  - Returns challenge question detail payload
  - 404 if the question does not exist
  - 403 if the question is locked and not already solved
  - Omits expected_query, solution_query, and explanation before submission
  - Includes hints and concepts in the pre-submission payload
  - Includes progress metadata with mode set to practice

- POST /run-query
- POST /api/run-query
  - Input: { query, question_id }
  - Rejects locked questions
  - Validates and runs the query against the shared DuckDB execution engine
  - Returns { columns, rows, row_limit }

- POST /submit
- POST /api/submit
  - Input: { query, question_id }
  - Rejects locked questions
  - Evaluates user output against expected_query
  - Uses `correct` as the final acceptance flag for challenge progression
  - Also returns `is_result_correct`, `structure_correct`, and `feedback` for result-vs-approach clarity
  - On accepted submission, marks the question solved
  - Returns acceptance/result flags plus user_result, expected_result, solution_query, and explanation

#### Sample routes
- Prefix: /api/sample

- GET /api/sample/{difficulty}
  - Returns the next unseen sample question for that difficulty
  - Marks the returned sample as seen
  - Returns progress metadata, hints, concepts, and sample counters
  - Returns 409 when the user has exhausted all 3 samples for that difficulty

- POST /api/sample/{difficulty}/reset
  - Clears sample exposure state for that difficulty

- POST /api/sample/run-query
  - Runs SQL in sample context without challenge lock checks

- POST /api/sample/submit
  - Evaluates sample SQL and returns solution and explanation
  - Does not affect challenge progression

#### Plan and account routes
- GET /api/user/profile
  - Returns user identity and plan information
- PUT /api/user/profile
  - Allows direct plan changes in development mode
- POST /api/user/plan
  - Development-mode plan mutation endpoint for tests and local workflows
- GET /api/user/unlocks
  - Returns computed access state across the challenge catalog

#### Stripe routes
- POST /api/stripe/create-checkout
  - Creates a Stripe Checkout session for authenticated users
- POST /api/stripe/webhook
  - Verifies Stripe signatures, applies idempotent plan changes, and records audit events

#### SPA/static routes
- GET /
- GET /{asset_path:path}
  - Serves frontend/dist assets when present
  - Falls back to index.html for SPA routes
  - Excludes /api/* from SPA fallback behavior

### B. Request context, errors, and rate limiting

#### Request identity and logging
- backend/middleware/request_context.py assigns a UUID request_id per request
- The request_id is attached to request.state, stored in a contextvar, and returned as X-Request-ID
- Structured logs use the format [request_id=<id>] message

#### Error handling
- backend/main.py centralizes exception handling for AppError, HTTPException, and unexpected exceptions
- User-facing error payloads follow the shape:
  - { error, request_id }

#### Rate limiting
- backend/main.py applies per-IP rate limiting as middleware for all API traffic except /health
- Default settings come from config.py:
  - RATE_LIMIT_REQUESTS=60
  - RATE_LIMIT_WINDOW_SECONDS=60
- Redis-backed distributed limiting is used when REDIS_URL is configured
- In-memory limiting is used otherwise

### C. Query execution and evaluation

Files:
- backend/sql_guard.py
- backend/evaluator.py
- backend/database.py

Execution path:
1. The submitted SQL is validated by validate_read_only_select_query.
2. A lightweight cursor is created from the shared in-memory DuckDB engine.
3. The validated query is executed directly to preserve ORDER BY semantics.
4. Execution is run through a thread pool with a 3-second timeout.
5. Results are capped at 200 rows before serialization.

Evaluation path:
1. Run the user's query in the shared in-memory execution environment.
2. Run the expected query in the same execution environment.
3. Build pandas DataFrames from both payloads.
4. Normalize column casing, column order, float precision, and null handling.
5. Sort rows for comparison unless the expected query explicitly contains ORDER BY.
6. Compare normalized DataFrames for equality.

Behavioral implications:
- Column ordering differences are ignored
- Row ordering differences are ignored unless the expected query is order-sensitive
- Duplicate rows are preserved during evaluation
- Float comparisons use a tolerance-oriented normalization step

### D. Identity, progression, and storage

Files:
- backend/db.py
- backend/progress.py
- backend/unlock.py

Current challenge unlock model:
- Unlock state is derived from plan + solve history through a pure policy layer
- Free users have all easy questions, medium thresholds at 10/20/30 solved easy, and hard thresholds at 10/20/30 solved medium with a free hard cap
- Pro users have all easy and medium questions plus the first 22 hard questions
- Elite users have the full catalog
- Solved questions remain solved regardless of future plan changes

Stored tables:
- users
- sessions
- user_progress
- user_sample_seen
- stripe_events
- plan_changes

Identity model:
- Anonymous visitors receive first-class user rows and real session cookies
- Registration upgrades the same user where possible
- Login can merge anonymous progress into an existing account
- Multi-device account access is supported through authenticated sessions

---

## 6. Frontend Deep Dive

### Current route tree
Defined in frontend/src/App.js:
- / -> LandingPage
- /sample/:difficulty -> SampleQuestionPage
- /practice -> AppShell inside CatalogProvider
  - /practice/questions/:id -> QuestionPage
- /questions/:id -> legacy redirect to /practice/questions/:id

### Page responsibilities

#### LandingPage
- Introduces sample mode and challenge mode
- Links to /sample/easy, /sample/medium, /sample/hard, and /practice

#### QuestionPage
- Loads challenge question details
- Renders schema, editor, results, and answer feedback
- Renders `concepts` as pill-style semantic reasoning badges below the question description
- Supports running and submitting SQL
- Refreshes the catalog after a correct answer so unlock state updates immediately
- After submission, shows hints sequentially (one per button click); the solution button only appears after all hints are revealed

#### SampleQuestionPage
- Loads the next unseen sample for the selected difficulty
- Shows sample counters such as shown_count and remaining
- Renders `concepts` as pill-style semantic reasoning badges below the question description
- Supports running and submitting SQL
- After submission, shows hints sequentially; the solution button only appears after all hints are revealed
- Supports requesting another sample and resetting seen samples for the current difficulty
- Handles 409 exhaustion responses from the backend

### Shared state and components

#### catalogContext.js
- Fetches /api/catalog
- Exposes catalog, loading, error, and refresh()

#### AppShell
- Provides the challenge shell layout, top bar, and responsive sidebar container

#### SidebarNav
- Groups questions by difficulty
- Shows lock, next, and solved states
- Has current frontend tests in frontend/src/components/SidebarNav.test.js

#### SQLEditor
- Wraps Monaco for SQL entry

#### ResultsTable
- Renders tabular execution and evaluation results

#### SchemaViewer
- Displays table schema metadata supplied by the question payload

### API client behavior
frontend/src/api.js resolves the backend base URL as follows:
- If VITE_BACKEND_URL is set, use that origin plus /api
- If running on localhost without same-origin backend routing, fall back to http://localhost:8000/api
- Otherwise use same-origin /api

Axios is configured with withCredentials: true so cookie-based identity works during cross-origin local development.

---

## 7. Data Flow

### Challenge flow
1. User opens /practice.
2. CatalogProvider fetches the current challenge catalog.
3. AppShell renders the challenge layout.
4. User opens a question route under /practice/questions/:id.
5. The frontend fetches the question detail payload.
6. The user runs SQL against /api/run-query.
7. The backend validates SQL, enforces unlock state, creates a DuckDB cursor, and returns tabular results.
8. The user submits SQL to /api/submit.
9. The backend re-runs both user and expected queries, compares normalized results, and returns final acceptance, result correctness, structural correctness, feedback, and official answer material.
10. On accepted submission, challenge progression is persisted and the frontend refreshes catalog state.

### Sample flow
1. User opens /sample/{difficulty}.
2. The frontend requests /api/sample/{difficulty}.
3. The backend returns the next unseen sample and marks it as seen.
4. The user can run or submit SQL through sample endpoints.
5. When all 3 samples for that difficulty are exhausted, the backend returns 409.
6. The user can reset sample progress with /api/sample/{difficulty}/reset.

### Production serving flow
1. The root Dockerfile builds the frontend bundle.
2. The runtime image starts FastAPI/Uvicorn from backend/main.py.
3. FastAPI serves both SPA assets and /api routes.
4. Browser requests use same-origin /api by default.

---

## 8. Current Strengths

- Clear separation between challenge content, sample content, product state, execution, billing, and rate limiting
- Horizontally friendlier product-state model because identity, progress, sessions, and plans live in PostgreSQL
- Faster execution path because datasets are preloaded once into a shared in-memory DuckDB engine
- Server-side enforcement of challenge locks
- Unified identity that preserves anonymous progress through registration and login merge flows
- Real Stripe billing path with signature verification, idempotency, and audit logging
- Standardized request-id propagation and user-facing error shapes
- Deterministic dataset generation with explicit validation of edge-case coverage
- Dual deployment story: simple local split dev flow and single-service production path
- Lightweight but real test coverage on backend APIs, evaluator logic, rate limiting, and a key frontend navigation component

---

## 9. Current Weaknesses and Risks

### Documentation drift
- This document must continue to be updated alongside platform changes, especially around timed modes, future tracks, and production billing operations.
- This blueprint should be treated as the current corrective reference.

### Runtime and scalability limits
- Each query execution loads CSV data into a fresh in-memory DuckDB connection, which is safer but increases per-request overhead.
- In-memory rate limiting is process-local when Redis is absent.
- The current model is appropriate for low-to-moderate educational usage, not high-concurrency public scale.

### Product limitations
- No real authentication or user accounts
- No submission history or analytics layer
- No admin/content management UI
- No automated content QA pipeline beyond code validation and tests

### Deployment considerations
- Production requires REDIS_URL when ENV=production, as enforced by backend/config.py
- Split-origin deployments still require careful CORS and frontend backend-url configuration

---

## 10. Testing Snapshot

Current automated test files:
- backend/tests/test_api.py
- backend/tests/test_evaluator.py
- backend/tests/test_rate_limiter.py
- frontend/src/components/SidebarNav.test.js

Current coverage emphasis:
- Backend API behavior
- Evaluator normalization and correctness behavior
- Rate limiting behavior
- Sidebar navigation interaction

Current gaps:
- No broad frontend page-flow test suite
- No dedicated end-to-end integration suite for sample-mode regressions

---

## 11. Suggested Next Improvements

### Short-term
- Add a committed data dictionary document if a human-readable dataset contract is still desired
- Extend content validation coverage in CI beyond current schema-header and query-execution checks
- Update README and any other stale docs to match the current challenge counts and dataset inventory

### Medium-term
- Expand the challenge bank while preserving strict schema correctness and difficulty discipline
- Add focused frontend tests for sample exhaustion, reset flow, and challenge progression UI
- Add a content-review workflow for question JSON changes

### Long-term
- Introduce real user accounts if multi-device persistence becomes necessary
- Add richer learning analytics and submission history
- Revisit the execution architecture if concurrency or public usage grows materially

---

## 12. Summary

Current state:
- The platform is structurally sound as a small SQL practice application with clear separation between frontend, backend, content, and execution logic.
- The committed dataset inventory is broader and more realistic than the older docs implied, covering commerce, product, behavioral, support, and HR domains.
- The live challenge bank now includes 30 easy, 30 medium, and 25 hard questions.
- The sample bank is complete at 3 questions per difficulty.
- Question content now aligns with the current orders schema, and schema/header mismatches fail fast during catalog loading.

Readiness level:
- Good for local development, demos, and continued iterative build-out.
- Not yet content-complete or fully production-hardened for larger-scale public usage.
