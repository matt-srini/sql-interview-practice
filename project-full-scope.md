# Project Full Scope — Production Proposal

## Product Thesis

This project should evolve from a focused SQL practice app into a production-grade interview practice platform that feels fast, modern, calm, and deeply reliable under heavy load.

SQL remains the first-class track, but the platform should be intentionally designed so that future tracks such as Python, Pandas, data analysis, and system-design-style exercises can plug into the same product and entitlement model without a rewrite.

The platform should:
- feel lightweight and responsive on every screen
- render smoothly and stay easy on the eye during long practice sessions
- support seamless anonymous-to-accounted journeys
- scale to large bursts and sustained traffic in the low millions of active users
- preserve a clean architecture where content, identity, billing, unlocks, and execution are clearly separated

---

## Product Vision

### Core user promise
- Users can start instantly, practice with realistic content, and receive trustworthy feedback with minimal friction.
- Progress is never lost when a user signs up, upgrades, downgrades, or returns on another device.
- The UI feels focused, modern, and quiet rather than noisy or dashboard-heavy.
- The platform can serve both casual learners and serious interview candidates without splitting into separate products.

### Primary product surfaces
- Challenge track: structured progression through curated question banks
- Sample track: low-friction try-before-you-commit flow
- Timed challenge modes:
  - 30-minute challenge
  - 60-minute challenge
- Account and subscription management
- Future language tracks:
  - SQL
  - Python
  - Pandas / notebook-style data tasks
  - other coding or analytics tracks through pluggable execution engines

---

## Product Principles

### Experience principles
- Fast first: every common action should feel immediate
- Quiet interface: modern, clean, readable, low visual fatigue
- Progressive disclosure: avoid overwhelming new users
- Seamless continuity: anonymous, registered, and paid users stay on one identity path
- Deterministic feedback: correctness, unlocks, and entitlements should be transparent and reproducible

### Engineering principles
- Stateless application services wherever possible
- PostgreSQL as source of truth for product state
- Execution engines isolated from product state and billing systems
- Pure policy layers for unlocks and entitlements
- Strong observability, idempotency, and safe retries
- Easy horizontal scaling without shared local state
- Extensible engine model for non-SQL tracks in the future

## Non-Negotiable Constraints

- PostgreSQL is the single source of truth for all product state
- Execution engines (DuckDB, Python runners) must NEVER store product state
- Unlocks and entitlements must be computed, not persisted
- No business logic in the frontend
- No direct coupling between billing and execution paths
- All APIs must be idempotent where applicable
- Anonymous and registered users must share the same identity model

---

## Present Goal

The present product goal is focused and clear:
- build an excellent SQL interview practice experience first
- keep the system future-ready for additional tracks such as Python
- treat the UI and UX as a fresh design opportunity rather than an iteration on the current shell

This document should support a clean restart of the user-facing experience while keeping the core technology direction intact. The interface can be reimagined from the ground up as long as the product remains fast, clear, elegant, and structurally aligned with the platform architecture described here.

## Agent Responsibilities

When working on this project, you (the agent) should:

- Prefer simple, well-scoped implementations over premature abstractions
- Keep functions small, composable, and testable
- Avoid introducing global state or hidden coupling
- Ensure all new features respect entitlement and plan models
- Write code that is production-ready, not prototype-level
- Add logging, error handling, and observability hooks by default

## Anti-Patterns to Avoid

- Do not store derived state (e.g., unlocked questions)
- Do not embed SQL execution logic inside API routes
- Do not mix billing logic with core product logic
- Do not introduce synchronous blocking calls in request paths
- Do not create tightly coupled modules across layers
- Do not bypass the runner abstraction for execution

---

## Technology Commitments

The following platform choices are strategic and should remain stable:
- React frontend with Vite
- FastAPI backend
- PostgreSQL as the source of truth for product and user state
- DuckDB for SQL execution and evaluation
- Redis for rate limiting and short-lived coordination or caching
- Alembic for schema evolution
- unified session-based identity with anonymous-to-registered continuity

The following areas should still be treated as active product architecture work:
- timed challenge orchestration and scoring
- future track runner abstractions for Python and notebook-style tasks
- richer analytics, attempt history, and performance insights
- deeper background-job, search, and observability capabilities as scale grows

---

## North-Star Product Scope

### Tracks and modes

#### SQL practice
- guided challenge bank with progressive difficulty
- sample mode for onboarding
- realistic schemas and datasets
- trusted correctness feedback and solution explanations

#### Timed challenges
- 30-minute challenge
- 60-minute challenge
- daily or weekly rotating challenge sets
- leaderboards or percentile ranking can be added later without changing the core entitlement model

#### Future Data Track Expansion
- content model should support `track` or `language` as a first-class field
- initial tracks: SQL, Python, Pandas
- future tracks may include:
  - data engineering scenarios (ETL, pipelines)
  - analytics and BI-style problems
  - notebook-style exploratory tasks
- execution should route through pluggable runners
- SQL uses DuckDB-based safe execution
- Python and data workloads should run in sandboxed or containerized environments
- all tracks must reuse the same identity, entitlement, billing, and session systems

### Plan model
- `free`
- `pro`
- `elite`

Plans control:
- which question pools are accessible
- which timed modes are available
- how much historical performance data is visible
- access to premium tracks such as Python in future phases

Timed modes should be modeled as product capabilities rather than separate identity systems.

---

## Unlock and Entitlement Model

### Target model
Unlocks should be derived from:
- user plan
- solved question history
- future skill metrics such as accuracy
- selected mode or track

### SQL challenge unlock rules
- Free:
  - all easy unlocked
  - medium unlocks by easy solve thresholds
  - hard unlocks by medium solve thresholds
  - hard remains capped for free users
- Pro:
  - all easy
  - all medium
  - partial hard access
- Elite:
  - full access

### Timed modes
- Timed modes should be entitlement-aware:
  - free users may receive limited daily entries or smaller pools
  - pro users may unlock standard timed challenges
  - elite users may unlock all timed formats, archives, analytics, and premium challenge packs

### Design rule
Unlock computation must live in a pure policy layer and never be persisted as mutable product state.

---

## Experience and Design Direction

### Look and feel
- modern and clean
- easy on the eyes during long study sessions
- minimal chrome around the editor
- clear typography and strong spacing rhythm
- light visual hierarchy with calm color usage

### Frontend quality bar
- first contentful interactions should feel immediate
- transitions should be subtle and purposeful
- editor, results, schema, hints, and explanation panels should feel fluid
- mobile and desktop layouts should both feel intentional, not merely responsive
- long sessions should avoid jank, layout shift, and re-render storms

### Product UX expectations
- no forced sign-up before value
- no progress loss on registration
- clean upgrade flow
- consistent route and state behavior
- transparent locked vs unlocked vs solved states

---

## Platform Architecture

## Layer Boundaries

- API Layer:
  - Handles request/response
  - No business logic beyond orchestration

- Service Layer:
  - Core business logic
  - Entitlements, progress, evaluation

- Data Layer:
  - Database access only
  - No business decisions

- Execution Layer:
  - Isolated from product state
  - Stateless and sandboxed

- Policy Layer:
  - Pure functions
  - Determines unlocks and access

### Baseline platform shape

### Application state
- PostgreSQL via async SQLAlchemy + asyncpg + Alembic

### Query execution
- DuckDB-based SQL execution
- initially SQL-focused, with room to mature into a lower-latency shared execution layer

### Identity
- single user/session model
- anonymous users created as first-class users
- registration upgrades the same user where possible

### API shape
- FastAPI with `/api/` routes
- standardized error responses with `request_id`

### Production architecture target

### Core services
- web frontend
- stateless API service
- query execution service
- billing/webhook processing
- background jobs and cleanup workers
- analytics and observability pipeline

### Data stores
- PostgreSQL:
  - users
  - sessions
  - progress
  - sample tracking
  - plan changes
  - billing events
  - future challenge runs, scores, and analytics
- Redis:
  - rate limiting
  - short-lived cache
  - queue coordination if needed
- DuckDB or track-specific engines:
  - execution only
  - never source-of-truth product state

### Execution engine model
- `runner = resolve_runner(track, mode)`
- SQL runner:
  - preloaded in-memory golden DuckDB connection
  - fast cursor creation
  - read-only guarded queries
- Python runner:
  - containerized or sandboxed worker execution
  - CPU, memory, network, and time limits
- Future tracks:
  - same contract, different engine

## Canonical Flows

### Solve Question Flow
1. User submits query
2. API validates request
3. Execution runner evaluates query
4. Result compared against expected output
5. Submission stored
6. Entitlements recalculated
7. Response returned with correctness and updated access state

### Anonymous to Registered Flow
1. Anonymous session created
2. Progress stored against session user
3. User signs up
4. Session upgraded to registered identity
5. All progress retained

---

## Data and Domain Model

### Stable first-class entities
- user
- session
- plan
- question
- sample question
- challenge run
- submission
- billing event
- plan change
- entitlement result

### Future content model
Questions should be extensible with fields such as:
- `track`: sql, python, pandas, etc.
- `mode`: practice, timed, sample
- `difficulty`
- `duration_hint`
- `dataset_refs`
- `execution_profile`
- `grading_profile`

This keeps the platform from hard-coding SQL assumptions into the outer product shell.

## Data Ownership

- users: identity and authentication
- sessions: session lifecycle only
- submissions: immutable records of attempts
- progress: derived summary if persisted
- billing_events: append-only
- plans: static definitions

---

## Operational Requirements

### Reliability
- graceful degradation when Redis is unavailable
- idempotent billing events
- strong request tracing
- health checks for both Postgres and execution engine availability

### Security
- read-only SQL enforcement
- sandboxed future Python execution
- secure session cookies
- webhook signature verification
- no trust in client-side billing success callbacks

### Performance
- low latency for catalog and question fetches
- fast warm execution path
- bounded query runtime
- bounded result size
- efficient unlock evaluation

## Performance Targets

- Question load time: < 200ms
- Query execution (p95): < 2s
- API response time (p95): < 300ms
- First interactive load: < 1.5s

---

## Observability Requirements

- Every request must include a request_id
- All errors must be logged with context
- Execution time must be tracked per query
- Critical flows must emit structured logs

---

## Repository Conventions

- backend/
  - api/
  - services/
  - models/
  - policies/
  - runners/

- frontend/
  - components/
  - features/
  - hooks/
  - api/

- migrations/
- scripts/

Naming:
- snake_case for backend
- camelCase for frontend

## Definition of Done

A feature is complete only if:

- Code is clean and modular
- Edge cases are handled
- Errors are handled gracefully
- Logging is present
- Tests are added where applicable
- No architectural rules are violated

---

## Platform Reference Points

The platform should be understood through a few stable building blocks rather than a long list of implementation files.

### Experience layer
- The frontend should act as a focused practice environment with a calm shell, strong editor ergonomics, smooth results rendering, and clear progression cues.
- This layer owns navigation, layout, timed-mode flows, onboarding, and subscription surfaces.

### Identity and account layer
- Users should move seamlessly from anonymous usage to registered accounts without losing progress.
- Sessions, plans, and account continuity should remain simple and durable regardless of future UI changes.

### Content and entitlement layer
- The catalog, question ordering, unlocks, and timed-mode eligibility should be driven by deterministic policies.
- The product should clearly separate stored user state from computed entitlements.

### Execution and evaluation layer
- SQL execution should remain fast, safe, and isolated from application state.
- Future tracks such as Python should plug into this layer through a shared runner model rather than custom product logic.

### Billing and plan layer
- Plans should shape access, challenge formats, and premium capabilities without leaking billing complexity into the rest of the platform.
- Payment workflows should be resilient, auditable, and easy to extend.

### Operational layer
- Observability, health checks, cleanup workflows, and deployment reliability should be treated as first-class product requirements, not afterthoughts.
- The system should remain easy to operate locally while being ready for real-world scale in production.

---

## Shared Language

- Service endpoints should live under one clear API namespace so the product remains organized and predictable as it grows.
- User-facing error responses should stay consistent and always include a traceable request identifier.
- Challenge numbering should remain stable and easy to reason about:
  - `1xxx` easy
  - `2xxx` medium
  - `3xxx` hard
- Sample numbering should remain distinct from the main challenge bank:
  - `101-103` easy
  - `201-203` medium
  - `301-303` hard
- The session contract should stay centered on a single durable browser session token.
- Plans should continue to use a simple three-tier vocabulary: `free`, `pro`, `elite`.
- Access states should remain human-readable and consistent across the product: `locked`, `unlocked`, `solved`.

---

## Proposal Summary

This project should be treated as a modern interview-practice platform with SQL as the first mature track, not as a one-off SQL toy app. The delivery path should prioritize a redesigned, high-quality SQL experience first, while preserving an architecture that can extend naturally into timed modes, premium plans, and future tracks such as Python.

The proposal assumes a clean, modern UI/UX relaunch while keeping the core stack intact: React, FastAPI, PostgreSQL, DuckDB, Redis, and a session-based identity model. With that foundation, the platform can grow into timed challenges, premium entitlements, and future language tracks without re-architecting its foundations.
