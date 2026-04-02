# Architecture

> **Navigation:** [Docs index](./README.md) · [Backend](./backend.md) · [Frontend](./frontend.md) · [Deployment](./deployment.md)

Technical reference for the datanest platform — system design, data flows, execution models, and scaling considerations.

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
  6. normalize_dataframe() on both result sets (column casing, order, floats, nulls)
  7. Compare normalized DataFrames → correct/incorrect
  8. If correct: mark solved in PostgreSQL (user_progress table)
  9. Return verdict + solution material
```

---

## Request lifecycle — Python / Pandas

```
POST /api/python/submit  (or /api/python-data/submit)
  1. Session cookie → look up user in PostgreSQL
  2. validate_python_code() — AST-based guard (import allowlist per track)
  3. Spawn python_sandbox_harness.py subprocess (5-second timeout, 512 MB RLIMIT_AS)
  4. Harness: exec() user code, call solve(*args) per test case (algorithm)
           OR load DataFrames from CSVs, call solve(**dataframes) (pandas)
  5. Parse JSON from harness stdout; non-zero exit or timeout = error
  6. Compare test case outputs (algorithm) or normalize + compare DataFrames (pandas)
  7. If correct: mark solved in PostgreSQL
  8. Return verdict + test summary + solution on correct
```

---

## Request lifecycle — PySpark MCQ

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

Tables managed by Alembic migrations in `backend/alembic/`.

| Table | Purpose | Key columns |
|---|---|---|
| `users` | All users (anonymous + registered) | `id`, `email`, `is_anonymous`, `plan_tier` |
| `sessions` | Session tokens | `token`, `user_id`, `created_at` |
| `user_progress` | Solved questions per topic | `user_id`, `question_id`, `topic`, `solved_at` |
| `user_sample_seen` | Sample question exposure | `user_id`, `sample_id`, `topic`, `difficulty` |
| `plan_changes` | Audit log of plan upgrades | `user_id`, `old_plan`, `new_plan`, `changed_at` |
| `stripe_events` | Idempotent Stripe webhook records | `event_id`, `processed_at` |

**`user_progress` and `user_sample_seen` carry a `topic` column** (DEFAULT `'sql'`). Progress is completely independent per topic — solving SQL does not affect Python unlock state.

---

## Unlock model

Pure policy function in `backend/unlock.py`. Takes `(plan, solved_ids)` → returns `set[int]` of unlocked question IDs. No DB reads inside the function — all inputs passed by the router.

| Plan | Access |
|---|---|
| Free | All easy. Medium unlocks at 10/20/30 solved easy. Hard unlocks at 10/20/30 solved medium (capped). |
| Pro | All easy + medium + first 22 hard questions |
| Elite | Full catalog |

Solved questions remain solved permanently regardless of plan changes.

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

**Session token:** HttpOnly cookie, no expiry (server-side sessions managed in `sessions` table).

---

## Rate limiting

Applied as middleware to all routes except `/health`.

- Default: 60 requests / 60-second window / IP
- Redis-backed when `REDIS_URL` is set (required in production)
- In-memory dict fallback for local dev (process-local only — does not share across instances)
- Config: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` env vars

---

## Request correlation

`middleware/request_context.py` assigns a UUID to every request:
- Attaches to `request.state.request_id`
- Stored in a `contextvars.ContextVar` for structured logging
- Returned as `X-Request-ID` response header
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

### Current bottlenecks

| Component | Bottleneck | Impact |
|---|---|---|
| DuckDB | Single shared cursor (not thread-safe under concurrent writes) | Queries block each other at high concurrency |
| Python sandbox | Subprocess spawn per request (~50–100ms cold start) | Latency spikes under load |
| Rate limiter | In-memory fallback is process-local | Ineffective when running multiple instances |
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
- Increase `asyncpg` pool size (default 10 → 50 for moderate scale)
- Add PgBouncer connection pooler for 1,000+ concurrent connections
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

## Content architecture

**SQL questions:** JSON files in `backend/content/questions/` — `easy.json`, `medium.json`, `hard.json`. Loaded and validated at startup by `questions.py`. Schema validated against committed CSV column headers.

**Python / Pandas / PySpark questions:** Same pattern in `backend/content/python_questions/`, `python_data_questions/`, `pyspark_questions/`. Each directory has a `schemas.json` that defines ID ranges and required fields.

**Sample questions:** Defined in `backend/sample_questions.py` (SQL) and equivalent Python files. Fixed IDs (3 digits). Completely separate from challenge banks — never overlap.

**ID ranges:**
| Track | Easy | Medium | Hard |
|---|---|---|---|
| SQL | 1001–1999 | 2001–2999 | 3001–3999 |
| Python | 4001–4299 | 4301–4599 | 4601–4999 |
| Pandas | 5001–5999 | 6001–6999 | 7001–7999 |
| PySpark | 11001–11999 | 12001–12999 | 13001–13999 |

Sample IDs are always 3 digits and never overlap with challenge IDs.

---

## Testing

| Suite | Location | Coverage |
|---|---|---|
| Backend API | `backend/tests/test_api.py` | Auth, catalog, question fetch, submit, sample |
| SQL evaluator | `backend/tests/test_evaluator.py` | Normalization, comparison, ORDER BY sensitivity |
| Rate limiter | `backend/tests/test_rate_limiter.py` | Window reset, limit enforcement |
| Frontend | `frontend/src/components/SidebarNav.test.js` | Question list states |

**Gaps:** No frontend page-flow tests. No end-to-end sample exhaustion / reset regression suite.

**Run tests:**
```bash
cd backend && pytest -q
cd frontend && npm test
```
