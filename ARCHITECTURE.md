
# Architecture Notes (Current Backend and Execution Model)

## Question Catalog

- Challenge questions: JSON-backed, in backend/content/questions/ split by difficulty (easy.json, medium.json, hard.json), with schemas.json for loader expectations
- backend/questions.py loads and validates the full catalog at import time, builds an in-memory index by id, and exposes:
  - get_all_questions() (list view)
  - get_question(id) (detail view)
  - get_questions_by_difficulty() (ordered lists per difficulty)
- IDs are aligned with progression ranges:
  - easy: 1001..1999
  - medium: 2001..2999
  - hard: 3001..3999
- Sample questions: Python-backed, in backend/sample_questions.py, with their own non-overlapping ID ranges

## Backend Routing and Structure

- backend/main.py: app wiring, lifespan, CORS, rate-limit middleware, router registration, exception handling
- backend/routers/:
  - system.py: /health
  - catalog.py: /catalog, /api/catalog
  - questions.py: challenge question routes + run/submit
  - sample.py: sample mode routes
  - plan.py: user profile, plan, Stripe endpoints
  - spa.py: frontend static serving + SPA fallback (registered last)

## User Profile, Plan, and Stripe Logic

- User profiles (user_id, plan, metadata) are stored in user_profiles table in persistent DuckDB
- Plan changes and unlock logic are handled via backend/routers/plan.py
- Stripe integration is stubbed: endpoints simulate session creation and webhook events, updating user plan on successful webhook

## Progress Tracking

- Progress is stored in DuckDB (file-backed) in user_progress (user_id, question_id, solved_at)
- Sample exposure state is stored in user_sample_seen (user_id, difficulty, question_id, seen_at)
- User identity: X-User-Id header (for tests/API clients) or HttpOnly cookie sql_practice_uid (auto-generated)
- No authentication or account system

## Unlock Logic

- Unlocking is sequential within each difficulty
- A question is unlocked iff all earlier questions in that difficulty are solved
- The first unlocked but unsolved question in a difficulty is marked is_next=true for UI highlighting

## Query Execution and Evaluation

- backend/database.py: persistent DuckDB for user/profile/progress, in-memory DuckDB for per-query execution
- On startup, all CSVs in backend/datasets/ are loaded into persistent DuckDB tables
- For query execution, a fresh in-memory DuckDB connection is created, loading only the tables listed in the question's dataset_files
- backend/evaluator.py: query execution, timeout, result serialization, evaluation normalization
- backend/sql_guard.py: SQL validation and safety checks (read-only, single-statement, timeout, row cap, join cap)
- Evaluation: result normalization (case-insensitive columns, NULL/NaN canonicalization, float tolerance, duplicate-row preservation), row order enforced only if expected SQL contains ORDER BY

## Guardrails

- Read-only SQL (parser-based)
- Single-statement restriction
- Timeout and row cap
- Join-count cap and cartesian join prevention
- API rate limiting (in-memory or Redis-backed)

## Navigation and UI

- Frontend fetches /catalog at startup, renders sidebar with grouped questions
- After correct submission, question view refreshes /catalog so next question unlocks immediately
- Locked questions: non-clickable rows
- "Next Question" button after correct submit

## Error Handling and Logging

- backend/main.py: centralized exception handling for AppError, HTTPException, and unexpected exceptions
- User-facing error payloads: { error, request_id }
- backend/middleware/request_context.py: assigns UUID request_id per request, attached to request.state and returned as X-Request-ID
- Structured logs: [request_id=<id>] message
