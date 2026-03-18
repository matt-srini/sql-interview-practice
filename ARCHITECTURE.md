# Architecture Notes (Progression + Navigation)

## Question Catalog

- The seeded question bank lives in `backend/question_bank/` split by difficulty (`easy.py`, `medium.py`, `hard.py`).
- `backend/questions.py` loads and validates the full catalog at import time, builds an in-memory index by id, and exposes:
  - `get_all_questions()` (list view)
  - `get_question(id)` (detail view)
  - `get_questions_by_difficulty()` (ordered lists per difficulty)
- IDs are aligned with progression ranges:
  - easy: `1..25`
  - medium: `26..50`
  - hard: `51..75`

This keeps authoring simple (plain Python dicts) while still being easy to refactor into JSON/YAML later.

## Backend Routing

- `backend/main.py` now handles app wiring only (lifespan, CORS, rate-limit middleware, and router registration).
- Domain routes are split into `backend/routers/`:
  - `system.py` (`/health`)
  - `catalog.py` (`/catalog`, `/api/catalog`)
  - `questions.py` (practice question routes + run/submit)
  - `sample.py` (sample mode routes)
  - `spa.py` (frontend static serving + SPA fallback; registered last)

## Progress Tracking

- Progress is stored in DuckDB (file-backed DB) in a single table:
  - `user_progress(user_id, question_id, solved_at)`
- Sample exposure state is stored in:
  - `user_sample_seen(user_id, difficulty, question_id, seen_at)`
- The backend identifies a user via:
  - `X-User-Id` header (useful for tests / API clients), otherwise
  - an HttpOnly cookie `sql_practice_uid` (generated automatically on first use)

This provides persistent progression without adding authentication.

## Unlock Logic

- Unlocking is sequential *within each difficulty*.
- A question is `unlocked` iff all earlier questions in that difficulty are solved.
- The first `unlocked` but unsolved question in a difficulty is marked `is_next=true` for UI highlighting.

## Navigation

- The frontend fetches `/catalog` once at startup and renders a left sidebar with collapsible groups.
- After a correct submission, the question view refreshes `/catalog` so the next question unlocks immediately.
- Locked questions are rendered as non-clickable rows (no routing).
- The practice work area now also shows a “Next Question” button after a correct submit, so progression does not depend only on the sidebar/hamburger.

## Evaluation Behavior

- Result normalization handles:
  - case-insensitive columns
  - NULL/NaN canonicalization
  - float tolerance
  - duplicate-row preservation
- Row order is enforced **only** when expected SQL explicitly contains `ORDER BY`.
- For questions without `ORDER BY`, comparison remains order-insensitive.

## Guardrails

All existing query guardrails remain enforced:

- Read-only SQL (sqlglot parsing)
- Single-statement restriction
- Timeout and row cap
- Join-count cap and cartesian join prevention
- API rate limiting (in-memory or Redis-backed)
