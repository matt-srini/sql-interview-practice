Implementation Plan
- Expand the question catalog to 25 Easy / 25 Medium / 25 Hard using seeded modules that are easy to edit.
- Add DuckDB-backed progression (`user_progress`) keyed by a lightweight `user_id` (cookie by default, `X-User-Id` supported).
- Add a new `/catalog` endpoint returning grouped questions + per-user status (`locked`/`unlocked`/`solved`, plus `is_next`).
- Enforce sequential access by blocking `/run-query` and `/submit` for locked questions (SQL guardrails unchanged).
- Build a left sidebar (collapsible groups + nested question list) and refresh progression after correct submissions.
- Add backend + frontend tests and update docs + a manual checklist.
