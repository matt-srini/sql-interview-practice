# Architecture

> **Navigation:** [Docs index](../README.md) · [Backend](./backend.md) · [Frontend](./frontend.md) · [Deployment](./deployment.md)

Technical reference for the datathink platform — system design, data flows, execution models, and scaling considerations.

---

## System overview

```
Browser
  └── React SPA (Vite, port 5173 in dev / served by FastAPI in prod)
        └── Axios (cookie credentials) → FastAPI (port 8000)
              ├── PostgreSQL   — identity, sessions, progress, plans, billing
              ├── DuckDB       — in-memory SQL execution (loaded once at startup)
              ├── Python sandbox — subprocess per request for Python/Pandas execution
              └── Redis        — rate limiting (in-memory fallback in dev)
```

**Single-service production:** FastAPI serves both the REST API (`/api/*`) and the pre-built React SPA. No separate web server.

**Local dev:** Backend and frontend run natively; Postgres + Redis run in Docker containers.

---

## Component responsibilities

| Component | Owns | Does NOT own |
|---|---|---|
| PostgreSQL | All persistent state (users, sessions, progress, plans, payments) | Execution or content |
| DuckDB | SQL query execution (in-memory, stateless) | Persistent state |
| Python sandbox | Algorithm / Pandas code execution (ephemeral subprocess) | State, SQL |
| Redis | Rate limit counters per IP | Sessions or progress |
| JSON files | Question content (challenge + sample banks) | Runtime state |

---

## Request lifecycle — SQL challenge

```
POST /api/submit
  1. Session cookie → look up user in PostgreSQL
  2. Check question lock state (unlock.py — pure policy, no DB read)
  3. validate_read_only_select_query() — parser-based SQL guard
  4. Run user query in DuckDB (thread pool, 3-second timeout)
  5. Run expected_query in DuckDB
  6. normalize_dataframe() on both FULL result sets (column casing, order, floats, nulls, date-normalization)
  7. Compare normalized DataFrames → correct/incorrect (grading is on the full result; only a 200-row preview is returned to the client)
  8. If correct: mark solved in PostgreSQL (user_progress table)
  9. Return verdict + solution material
```

---

## Request lifecycle — Python / Pandas

```
POST /api/python/submit  (or /api/pandas/submit)
  1. Session cookie → look up user in PostgreSQL
  2. validate_python_code() — AST-based guard (import allowlist per track)
  3. Spawn python_sandbox_harness.py subprocess (512 MB RLIMIT_AS; 5s timeout for algorithm, 12s for pandas data — full-result grading serializes a larger result)
  4. Harness: exec() user code, call solve(*args) per test case (algorithm)
           OR load DataFrames from CSVs, call solve(**dataframes) (pandas)
  5. Parse JSON from harness stdout; non-zero exit or timeout = error
  6. Compare test case outputs (algorithm) or normalize + compare DataFrames (pandas)
  7. If correct: mark solved in PostgreSQL
  8. Return verdict + test summary + solution on correct
```

---

## Request lifecycle — PySpark reasoning submit

```
POST /api/pyspark/submit
  1. Session cookie → look up user in PostgreSQL
  2. Compare body.selected_option == question["correct_option"]
  3. If correct: mark solved in PostgreSQL
  4. Return { correct, explanation }
```
No code execution. Entirely answer-matching.

---

## PostgreSQL schema

Schema is defined in **two independent places that must be kept in sync manually:**

- **`_SCHEMA_SQL`** — a raw SQL string in `backend/db.py`, executed by `ensure_schema()` at startup (local dev) and by `ensure_schema_admin()` in `backend/tests/conftest.py` (test suite). Every fresh test database is built from this string — it never sees Alembic.
- **Alembic migrations** — `backend/alembic/versions/`. Applied to production only, manually via `alembic upgrade head`. Production never calls `ensure_schema()`.

**The invariant:** every Alembic migration that adds or alters columns must also have a matching change in `_SCHEMA_SQL` (additive: `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`; new tables: full `CREATE TABLE IF NOT EXISTS` block). There is no tooling to enforce this — it is a manual discipline. Violating it produces `column does not exist` errors in tests while production succeeds silently. Root cause of the 2026-06-10 `plan_override` test failure. Full rule in `CLAUDE.md` § migration checklist step 2 and `docs/deployment.md` § Two-track schema.

| Table | Purpose | Key columns |
|---|---|---|
| `users` | All users (anonymous + registered) | `id`, `email`, `name`, `plan`, `plan_override`, `plan_override_until` |
| `sessions` | Session tokens | `token`, `user_id`, `expires_at` |
| `user_progress` | Solved questions per topic | `user_id`, `question_id`, `topic`, `solved_at` |
| `user_sample_seen` | Sample question exposure | `user_id`, `difficulty`, `question_id`, `topic` |
| `plan_changes` | Audit log of plan upgrades | `user_id`, `old_plan`, `new_plan`, `created_at` |
| `payment_events` | Idempotent payment-provider event records (dual-rail: Razorpay + Paddle, disambiguated by a `provider` column) | `event_id`, `event_type`, `provider`, `processed_at` |
| `submissions` | Every submit attempt per user | `user_id`, `track`, `question_id`, `is_correct`, `code`, `submitted_at` |
| `mock_sessions` | Mock interview session records | `user_id`, `mode`, `track`, `difficulty`, `status`, `started_at`, `ended_at` |
| `mock_session_questions` | Per-question answers within a mock session | `session_id`, `question_id`, `track`, `is_solved`, `final_code`, `time_spent_s`, `is_follow_up`, `follow_up_dimension` |
| `mock_chain_consumption` | Interview Loop chains a user has consumed (so a chain is served once) | `user_id`, `parent_id`, `session_id`, `reclaimed` |
| `mock_discards` | Append-only log of penalty-free mock-session discards (per-day discard cap) | `user_id`, `discarded_at` |

**`user_progress` and `user_sample_seen` carry a `topic` column** (DEFAULT `'sql'`). Progress is completely independent per topic — solving SQL does not affect Python unlock state.

---

## Unlock model

Pure policy function in `backend/unlock.py`. Signature: `compute_unlock_state(plan, solved_ids, catalog, track, path_state)` → returns `dict[question_id, "unlocked"|"locked"|"solved"]`. No DB reads — all inputs passed by the router.

| Plan | Access |
|---|---|
| Free | All easy. Medium and hard are locked — Pro or Elite required. |
| Pro | All easy + all medium + all hard |
| Elite | Full catalog |

*(Canonical SoT for the access policy is [`backend/unlock.py`](../backend/unlock.py). See CLAUDE.md § Linked-docs / single-SoT rule.)*

**Free-tier access (flat model):** All easy questions are open — no thresholds, no batch unlocks, no per-track caps. Medium and hard are locked for Free users regardless of solve count.

Locked MCQ questions return 200 with `locked: true` and no `options` / `correct_option` (stem always visible). Submitting a locked MCQ returns 403.

**Learning paths and unlocks:** Paths are curated walks through the practice catalog and do not influence unlock state. A user who solves a question via the path UI gets the same `solved` mark as solving via practice. See [`docs/content-authoring.md`](./content-authoring.md) §Paths for the canonical path model.

Solved questions remain solved permanently regardless of plan changes or threshold reversals.

**Operator plan overrides:** The `users` table carries two nullable columns — `plan_override` (text) and `plan_override_until` (timestamptz). At every auth resolution point (`get_session_user`, login via `get_user_credentials_by_email`, `get_user_by_id/email`, OAuth flows), the `_effective_plan()` helper in `db.py` checks whether an active override is present. If `plan_override IS NOT NULL` and `plan_override_until > now()`, the override is used as the user's plan instead of the base `plan` column; otherwise the base `plan` is returned. No cron job is needed — expiry is evaluated lazily per request. Overrides are managed via `POST/DELETE /api/admin/grant-plan` (operator-only, Bearer-token protected). See [`docs/features/pricing.md`](./features/pricing.md) §Admin operator grants and [`docs/backend.md`](./backend.md) §Admin for the full API contract.

---

## DuckDB execution model

**Current (single cursor):**
```python
# database.py — one shared in-memory engine loaded once at startup
engine = duckdb.connect(':memory:')
for csv in datasets:
    engine.execute(f"CREATE TABLE {name} AS SELECT * FROM '{csv}'")
```

All queries share a single DuckDB connection via a thread-pool executor. At current load this is fine; at scale, replace with a connection pool (see Scalability section).

**Why DuckDB?** In-memory analytical engine with full SQL, columnar execution, zero network latency. The 11-table dataset (~72K rows total) fits entirely in memory (<100 MB).

---

## Python sandbox model

**Security layers:**
1. `python_guard.py` — AST walk before any execution
   - Algorithm track: blocks all imports + dangerous builtins (`eval`, `exec`, `open`, `__import__`)
   - Pandas track: allowlist only (`pandas`, `numpy`, `math`, `statistics`, `collections`, etc.)
   - Also blocks dangerous attribute access (`__class__`, `__subclasses__`, `system`)
2. Subprocess isolation — each execution is a fresh child process
3. `resource.RLIMIT_AS` — 512 MB memory cap set inside the subprocess before exec

**Harness flow:**
- Receives JSON via stdin: `{ mode, code, test_cases? dataframes? csv_dir? }`
- Algorithm: `exec(code)` → call `solve(*args)` for each test case
- Pandas: load DataFrames from CSVs → `exec(code)` → call `solve(**dataframes)` → serialize result
- Writes JSON to stdout → parent process parses it

---

## Identity and session model

**Anonymous-first:** Every visitor gets a real `users` row + `sessions` token cookie on first request. No login required to start practicing.

**Registration:** Upgrades the existing anonymous session in place. The `user_id` stays the same, `is_anonymous` flips to false, email is set. Progress is 100% preserved.

**Login:** Existing registered account absorbs any anonymous progress from the current session (merge at login time). The anonymous user row is then discarded.

**Lockout policy:** Repeated failed sign-in attempts are tracked in PostgreSQL (`failed_login_attempts`, `login_locked_until`). After `LOGIN_LOCKOUT_MAX_ATTEMPTS`, the account is temporarily locked for `LOGIN_LOCKOUT_WINDOW_MINUTES`.

**Session token:** HttpOnly cookie with `SameSite=Lax` (and `secure` in production by default), server-side session lifecycle managed in `sessions` table. (The separate non-HttpOnly CSRF cookie uses `SameSite=Strict`.)

**CSRF model:** In production, mutating `/api/*` requests that present a session cookie must include an `Origin` matching configured app origins. This blocks cross-site request forgery for cookie-authenticated writes.

---

## Rate limiting

Applied as middleware to all routes except `/health`.

- Default: 60 requests / 60-second window / IP
- Redis-backed when `REDIS_URL` is set (required in production)
- In-memory dict fallback for local dev (process-local only — does not share across instances)
- Localhost bypass: requests from `127.0.0.1` / `::1` skip rate limiting in non-prod mode (safe for local dev and e2e tests)
- Config: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` env vars

---

## Request correlation

`middleware/request_context.py` assigns a UUID to every request:
- Attaches to `request.state.request_id`
- Stored in a `contextvars.ContextVar` for structured logging
- Returned as `X-Request-ID` response header
- Returned with `X-Response-Time-Ms` latency header for each response
- Included in all error payloads: `{ error, request_id }`
- Log format: `[request_id=<id>] message`

---

## Static asset serving

In production, FastAPI serves the pre-built SPA:
- `GET /` → `frontend/dist/index.html`
- `GET /assets/*` → hashed static files (Vite output)
- `GET /{any-spa-path}` → falls back to `index.html` (SPA routing)
- `GET /api/*` → excluded from fallback, handled by API routers

`FRONTEND_DIST_DIR` env var controls the path (defaults to `/app/frontend/dist` in the production image).

---

## Scalability

> **Head-of-line blocking was the #1 bottleneck and is fixed.** Code execution used
> to run *directly on the single event loop*, so one 5–12 s execution froze every
> other request. It now runs off the loop via `backend/offload.py` (see `docs/backend.md`
> § Off-loop code execution). The canonical concurrency/scaling model + tiered roadmap
> lives in `docs/deployment.md` § Concurrency & scaling model; the table below is the
> remaining per-component view.

### Current bottlenecks

| Component | Bottleneck | Impact |
|---|---|---|
| Single replica CPU | One uvicorn worker, 8 vCPU; code execution is CPU/subprocess-bound | Top limiter post-offload — single replica saturated ~32 active users in load tests. Lift via horizontal replicas (Tier 2) / a worker fleet (Tier 3). |
| DuckDB | Single in-process engine; SQL grading serialized behind a process-wide lock (off-loop) for determinism + thread-safety (shared-conn concurrent use segfaults) | SQL grades one-at-a-time; sub-100 ms on ≤9k-row datasets so not the throughput limiter for this traffic mix. Per-cursor concurrency / per-replica engines are a measured-bottleneck-gated option. |
| Python sandbox | Subprocess spawn per request (~50–100ms cold start), bounded by `MAX_CONCURRENT_EXECUTIONS` | Cold-start latency; concurrency capped per replica. Pre-warmed worker pool / external fleet lifts it. |
| Rate limiter | In-memory fallback is process-local | Ineffective across multiple instances — use `REDIS_URL` (already supported) when scaling out. |
| Static assets | Served by FastAPI (Python) | CPU waste; better served by CDN |

### Scaling path

**DuckDB — connection pool (next step):**
```python
class DuckDBPool:
    def __init__(self, size=8):  # DUCKDB_POOL_SIZE env var
        self._pool = queue.Queue()
        for _ in range(size):
            conn = duckdb.connect(':memory:')
            _load_all_tables(conn)
            self._pool.put(conn)

    @contextmanager
    def acquire(self, timeout=5):
        conn = self._pool.get(timeout=timeout)
        try:
            yield conn
        finally:
            self._pool.put(conn)
```
Memory cost: ~100 MB/connection × 8 = ~800 MB. Acceptable for a dedicated instance.

**Python sandbox — pre-warmed worker pool:**
Replace per-request subprocess spawn with a `multiprocessing.Pool` of pre-forked workers. Workers stay alive between requests; state is reset between executions. Eliminates cold-start latency.

**Horizontal API scaling:**
FastAPI is already stateless (all state in PostgreSQL + Redis). Multiple instances behind a load balancer work out of the box. Requires `REDIS_URL` for shared rate limiting.

**Static assets — CDN:**
Build frontend to `dist/` with hashed filenames → serve from CloudFront/Cloudflare with long `Cache-Control` TTL. FastAPI only handles `/api/*` and `index.html` fallback.

**PostgreSQL:**
- Pool is sized per replica via `DB_POOL_SIZE` (default 10) + `DB_MAX_OVERFLOW` (default 20) = 30 max/replica — raised from the old 5+10. Keep `replicas × max` under the managed-Postgres `max_connections`.
- Add PgBouncer (transaction pooling) once `replicas × max` approaches `max_connections`
- Add read replica for dashboard/catalog reads

**Production topology for high scale:**
```
Cloudflare CDN  (static assets — hashed JS/CSS)
       ↓
Load Balancer  (Railway / AWS ALB)
    ↓  ↓  ↓
FastAPI × N    (stateless, DuckDB pool + Python worker pool per instance)
    ↓       ↓
PostgreSQL   Redis Cluster
(primary + read replica)
```

---

## Track registry

`backend/tracks.py` is the single source of truth for all track metadata. Each `TrackConfig` entry carries:

| Field | Type | Purpose |
|---|---|---|
| `slug` | `str` | URL/API slug (e.g. `"pandas"`); matches `:topic` route param |
| `db_topic` | `str` | Topic string stored in DB tables (equals slug for all tracks) |
| `catalog_module` | module | Exposes `get_questions_by_difficulty()`, `get_mock_questions_by_difficulty()`, `get_public_question()` |
| `label` | `str` | Human-readable name (e.g. `"Pandas"`) |
| `eval_kind` | `str` | `"sql" \| "python" \| "pandas" \| "mcq"` — drives submission dispatch |
| `unlock_profile` | `str` | `"code"` (SQL/Python/Pandas thresholds) or `"mcq"` (PySpark/DE — option-hiding balances lower effort) |
| `content_dir` | `Path` | Absolute path to the questions directory |
| `concept_blocklist` | `set[str]` | Syntax-level concepts rejected by `validate_content.py` |
| `hint_rules` | `dict` | Per-difficulty `(min, max)` hint count bounds |
| `first_hint_leak_patterns` | `tuple[re.Pattern]` | Regexes that flag an overly implementation-specific first hint |
| `in_mixed_mock` | `bool` | Whether the track is included in the `"mixed"` mock pool |
| `mixed_subtype` | `bool` | Phase D hook: `True` for tracks whose questions carry a `subtype` field to switch between MCQ and code editor per question |

**Helper functions:** `get_track(slug)`, `get_track_by_db_topic(db_topic)`, `all_slugs()`, `mixed_mock_slugs()`.

All files that previously hardcoded track lists — `unlock.py`, `routers/mock.py`, `routers/insights.py`, `routers/sample.py`, `sample_questions.py`, `scripts/validate_content.py` — now derive from this registry. Adding a track requires only a registry entry (plus its catalog module and content directory); no other file needs editing.

---

## Content architecture

**SQL questions:** JSON files in `backend/content/questions/` — `easy.json`, `medium.json`, `hard.json`. Loaded and validated at startup by `questions.py`. Schema validated against committed CSV column headers.

**Other tracks' questions:** Same pattern in the per-track content dirs — `python_questions/`, `pandas_questions/`, `pyspark_questions/`, `data_engineering_questions/`, `data_modeling_questions/`, `statistics_questions/`, `ml_fundamentals_questions/`, `experimentation_questions/`. Each directory has a `schemas.json` that defines ID ranges and required fields.

**Sample questions:** Every track has a dedicated sample file at `backend/content/sample_questions/<track>.json` (9 files total: `sql.json`, `python.json`, `pandas.json`, `pyspark.json`, `data_engineering.json`, `data_modeling.json`, `statistics.json`, `ml_fundamentals.json`, `experimentation.json`). Each file contains exactly 9 questions (3 per difficulty × 3 difficulties) using the compact 3-digit **TXS ID scheme** (T = track digit 1–9, X = difficulty digit 1/2/3, S = within-difficulty index 1–3). The loader `sample_questions.py:_load_track_samples` enforces field presence (every sample carries 2 hints + 1–4 canonical concept tags) and per-difficulty count (exactly 3 each) at module import. SQL samples additionally pass `_validate_sample_questions` for schema/CSV-header integrity. Sample content is completely separate from practice and mock pools — samples never duplicate practice or mock questions. Sample IDs (3-digit TXS) never collide with practice/mock IDs (5-digit TXNNN).

**ID ranges** (authoritative source: each track's `schemas.json`):
| Track | Easy | Medium | Hard |
|---|---|---|---|
| SQL | 11001–11999 | 12001–12999 | 13001–13999 |
| Python | 21001–21999 | 22001–22999 | 23001–23999 |
| Pandas | 31001–31999 | 32001–32999 | 33001–33999 |
| PySpark | 41001–41999 | 42001–42999 | 43001–43999 |
| Data Engineering | 51001–51999 | 52001–52999 | 53001–53999 |
| Data Modeling | 61001–61999 | 62001–62999 | 63001–63999 |
| Statistics | 71001–71999 | 72001–72999 | 73001–73999 |
| ML Fundamentals | 81001–81999 | 82001–82999 | 83001–83999 |
| Experimentation | 91001–91999 | 92001–92999 | 93001–93999 |

ID scheme: **TXNNN** (T=track 1–9, X=difficulty 1–3, NNN=sequence 001–999). Sample IDs: **TXS** (3 digits, S=1–3). SQL samples `111–133` only; other tracks serve samples from their practice pool by `order`.

---

## Testing

| Suite | Location | Coverage |
|---|---|---|
| Backend API | `backend/tests/test_01_system.py` through `backend/tests/test_20_data_modeling.py` | System, auth, catalog, track endpoints, mock, dashboard, payments, rate limiting, security, account |
| SQL evaluator | `backend/tests/test_05_sql.py` | SQL execution, normalization, comparison, ORDER BY sensitivity |
| Mock interviews | `backend/tests/test_11_mock.py` | Access rules, session lifecycle, mixed sessions, chain atomicity, summary visibility |
| Dashboard / insights | `backend/tests/test_12_dashboard.py` | Cross-track dashboard shape, insights metrics, weakest concepts, streaks, cache behavior |
| Rate limiter | `backend/tests/test_15_rate_limiting.py` | Window reset, limit enforcement |
| Frontend unit | `frontend/src/components/SidebarNav.test.js` | Question list collapse/expand, lock state rendering |
| Frontend unit | `frontend/src/pages/ProgressDashboard.test.js` | Legacy dashboard regression slice, X/Y count format, loading/error states, regression guard against plain-int shape |
| E2E (Playwright) | `frontend/e2e/plan-tiers.spec.js` | Dashboard counts, sidebar lock state, TrackHub banner, mock difficulty gating — live dev servers |

**Test infrastructure notes:**
- `backend/tests/conftest.py` (`isolated_state` fixture): resets DB state and clears rate limiter between every backend test to prevent cross-test contamination
- `frontend/e2e/global-setup.js`: creates elite/pro/free test users once before the full Playwright suite, writes credentials to `e2e/.test-users.json` (gitignored); avoids exhausting the dev server rate limiter across 7 tests
- Localhost requests bypass the rate limiter in non-prod mode (`main.py`) — required for Playwright tests running against the local dev server

**Run tests:**
```bash
# Backend
cd backend && ../.venv/bin/python -m pytest tests/ -q

# Frontend unit tests (Vitest)
cd frontend && npm test

# E2E (requires both dev servers running: backend :8000, frontend :5173)
cd frontend && npx playwright test
```
