# Backend

> **Navigation:** [Docs index](./README.md) · [Project blueprint](./project-blueprint.md) · [Frontend](./frontend.md)

FastAPI + Uvicorn. PostgreSQL for all product state. DuckDB for query execution only (in-memory, loaded at startup).

---

## Routers

Registered in `backend/main.py`:

| Router file | Prefix | Purpose |
|---|---|---|
| `routers/auth.py` | `/api/auth` | Register, login, logout, current user |
| `routers/system.py` | — | Health check |
| `routers/catalog.py` | `/api/catalog` | Challenge catalog by difficulty |
| `routers/questions.py` | `/api/questions` | Question detail, run query, submit |
| `routers/sample.py` | `/api/sample` | Sample questions, run, submit, reset |
| `routers/plan.py` | `/api/user` | User profile, plan, unlock state |
| `routers/stripe.py` | `/api/stripe` | Checkout creation, webhook handler |
| `routers/spa.py` | — | Static assets + SPA fallback |

---

## API reference

### Auth — `/api/auth`

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account; upgrades anonymous session in place |
| POST | `/api/auth/login` | Authenticate; merges anonymous progress into existing account |
| POST | `/api/auth/logout` | Deletes session |
| GET | `/api/auth/me` | Returns current user identity |

Anonymous visitors receive a real user row and session cookie. Registration upgrades that session rather than replacing it, preserving progress.

### System

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{ status, postgres, tables_loaded }` |

### Catalog — `/api/catalog`

| Method | Path | Description |
|---|---|---|
| GET | `/api/catalog` | Returns questions grouped by difficulty with per-group counts (total, solved, unlocked) and per-question state and `is_next` flag |

Also available without `/api` prefix at `/catalog`.

### Challenge questions — `/api/questions`

| Method | Path | Description |
|---|---|---|
| GET | `/api/questions` | Lightweight question list |
| GET | `/api/questions/{id}` | Full question detail. 404 if not found. 403 if locked. Omits `solution_query`, `expected_query`, and `explanation` before submission. |
| POST | `/api/run-query` | `{ query, question_id }` → `{ columns, rows, row_limit }`. Rejects locked questions. |
| POST | `/api/submit` | `{ query, question_id }` → verdict + result comparison + solution material on acceptance. Marks question solved on correct submission. |

Submit response fields:
- `correct` — final acceptance flag (drives progression)
- `is_result_correct` — whether result sets match
- `structure_correct` — structural approach check
- `feedback` — list of adjustment hints
- `user_result`, `expected_result` — both result sets
- `solution_query`, `explanation` — revealed after submission

Also available without `/api` prefix.

### Sample — `/api/sample`

| Method | Path | Description |
|---|---|---|
| GET | `/api/sample/{difficulty}` | Next unseen sample for difficulty. Marks as seen. Returns 409 when all 3 exhausted. |
| POST | `/api/sample/{difficulty}/reset` | Clears seen state for that difficulty |
| POST | `/api/sample/run-query` | Run SQL in sample context (no lock checks) |
| POST | `/api/sample/submit` | Evaluate SQL; returns solution. Does not affect challenge progression. |

### User and plan — `/api/user`

| Method | Path | Description |
|---|---|---|
| GET | `/api/user/profile` | User identity and plan tier |
| PUT | `/api/user/profile` | Direct plan change (dev mode only) |
| POST | `/api/user/plan` | Plan mutation (dev mode / tests) |
| GET | `/api/user/unlocks` | Computed unlock state across full catalog |

### Stripe — `/api/stripe`

| Method | Path | Description |
|---|---|---|
| POST | `/api/stripe/create-checkout` | Creates Stripe Checkout session for authenticated user |
| POST | `/api/stripe/webhook` | Verifies signature, applies idempotent plan change, records audit event |

### SPA / static

`GET /` and `GET /{asset_path:path}` serve `frontend/dist` assets. Falls back to `index.html` for SPA routes. `/api/*` paths are excluded from fallback.

---

## Query execution pipeline

Files: `sql_guard.py` → `evaluator.py` → `database.py`

**Run path:**
1. `validate_read_only_select_query` — parser-based safety check (no writes, single statement)
2. Lightweight cursor from shared in-memory DuckDB engine
3. Execute directly (preserves `ORDER BY` semantics)
4. Thread pool with 3-second timeout
5. Cap results at 200 rows before serialization

**Evaluation path (submit):**
1. Run user query and expected query in same DuckDB environment
2. Build pandas DataFrames from both
3. Normalize: column casing, column order, float precision, nulls
4. Sort rows for comparison *unless* expected query contains `ORDER BY`
5. Compare normalized DataFrames for equality

Behavioral rules:
- Column ordering differences are ignored
- Row ordering ignored unless expected query is order-sensitive
- Duplicate rows preserved
- Float comparisons use tolerance-based normalization

---

## Identity and unlock model

Files: `db.py`, `progress.py`, `unlock.py`

**PostgreSQL tables:**

| Table | Purpose |
|---|---|
| `users` | User rows (anonymous and registered) |
| `sessions` | Session tokens mapped to users |
| `user_progress` | Per-user solved question records |
| `user_sample_seen` | Per-user sample exposure records |
| `plan_changes` | Audit log of plan tier changes |
| `stripe_events` | Idempotent Stripe webhook event records |

**Unlock tiers (pure policy in `unlock.py`):**

| Plan | Access |
|---|---|
| Free | All easy. Medium unlocks at 10/20/30 solved easy. Hard unlocks at 10/20/30 solved medium (capped). |
| Pro | All easy + medium + first 22 hard questions |
| Elite | Full catalog |

Solved questions remain solved permanently regardless of plan changes.

---

## Request context and error handling

**Request ID** — `middleware/request_context.py` assigns a UUID per request, attaches it to `request.state`, stores it in a contextvar, and returns it as `X-Request-ID`. Structured logs use `[request_id=<id>]` prefix.

**Error payloads** — All user-facing errors follow: `{ error, request_id }`

**Rate limiting** — Applied as middleware to all routes except `/health`.
- Default: 60 requests per 60-second window per IP
- Redis-backed when `REDIS_URL` is set; in-memory fallback otherwise
- Config: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` in `config.py`
