# Backend

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md) · [Frontend](./frontend.md)

FastAPI + Uvicorn. PostgreSQL for all product state. DuckDB for SQL query execution (in-memory, loaded at startup). Python/PySpark execution runs in subprocess sandboxes.

---

## Routers

Registered in `backend/main.py`:

| Router file | Prefix | Purpose |
|---|---|---|
| `routers/auth.py` | `/api/auth` | Register, login, logout, current user |
| `routers/system.py` | — | Health check |
| `routers/catalog.py` | `/api/catalog` | SQL catalog by difficulty |
| `routers/questions.py` | `/api/questions` | SQL question detail, run query, submit |
| `routers/sample.py` | `/api/sample` | Topic-aware sample questions, run, submit, reset |
| `routers/plan.py` | `/api/user` | User profile, plan, unlock state |
| `routers/stripe.py` | `/api/stripe` | Checkout creation, webhook handler |
| `routers/python_questions.py` | `/api/python` | Python algorithm catalog, detail, run-code, submit |
| `routers/python_data_questions.py` | `/api/python-data` | Pandas catalog, detail, run-code, submit |
| `routers/pyspark_questions.py` | `/api/pyspark` | PySpark catalog, detail, submit (MCQ only) |
| `routers/dashboard.py` | `/api` | Cross-track progress dashboard |
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
| GET | `/api/sample/{topic}/{difficulty}` | Next unseen sample for a track+difficulty. Marks as seen. Returns 409 when all 3 are exhausted. |
| POST | `/api/sample/{topic}/{difficulty}/reset` | Clears seen state for that track+difficulty |
| POST | `/api/sample/sql/run-query` | Run SQL in SQL sample context (no lock checks) |
| POST | `/api/sample/{topic}/run-code` | Run Python / Pandas sample code (no lock checks) |
| POST | `/api/sample/{topic}/submit` | Evaluate sample answer for any track. Does not affect challenge progression. |
| GET | `/api/sample/{difficulty}` | Legacy SQL alias for `/api/sample/sql/{difficulty}` |
| POST | `/api/sample/{difficulty}/reset` | Legacy SQL alias for `/api/sample/sql/{difficulty}/reset` |
| POST | `/api/sample/run-query` | Legacy SQL alias for `/api/sample/sql/run-query` |
| POST | `/api/sample/submit` | Legacy SQL alias for `/api/sample/sql/submit` |

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

### Python — `/api/python`

| Method | Path | Description |
|---|---|---|
| GET | `/api/python/catalog` | Python catalog grouped by difficulty with per-user state |
| GET | `/api/python/questions/{id}` | Question detail. Omits `solution_code`/`explanation` pre-submit. |
| POST | `/api/python/run-code` | `{ code, question_id }` → test case results (public cases only). Guard checked first. |
| POST | `/api/python/submit` | `{ code, question_id }` → verdict + hidden test summary + solution on correct |

### Pandas — `/api/python-data`

| Method | Path | Description |
|---|---|---|
| GET | `/api/python-data/catalog` | Pandas catalog |
| GET | `/api/python-data/questions/{id}` | Question detail including `dataframes` and `schema` maps |
| POST | `/api/python-data/run-code` | `{ code, question_id }` → DataFrame result + `print_output` |
| POST | `/api/python-data/submit` | `{ code, question_id }` → correct/incorrect + DataFrame comparison + solution on correct |

### PySpark — `/api/pyspark`

| Method | Path | Description |
|---|---|---|
| GET | `/api/pyspark/catalog` | PySpark catalog |
| GET | `/api/pyspark/questions/{id}` | Question detail (options visible, `correct_option` hidden) |
| POST | `/api/pyspark/submit` | `{ selected_option, question_id }` → `{ correct, explanation }`. No code execution. |

### Dashboard — `/api/dashboard`

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard` | Per-track solved counts, concepts, and recent activity for the current user |

Response shape: `{ tracks: { sql, python, python_data, pyspark }, concepts_by_track, recent_activity }`.

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

## Python execution pipeline

Files: `python_guard.py` → `python_evaluator.py` → `python_sandbox_harness.py`

**Guard (`python_guard.py`):**
- AST-based validation runs before any execution
- Algorithm track: blocks all `import` statements plus dangerous builtins (`eval`, `exec`, `open`, `__import__`)
- Pandas track: allows `pandas`, `numpy`, `math`, `statistics`, `collections`, `itertools`, `functools`, `datetime`, `re`, `json`, `decimal`, `fractions`, `operator`, `string`; blocks all others
- Also blocks dangerous attribute access (`__class__`, `__subclasses__`, `system`, etc.)

**Evaluator (`python_evaluator.py`):**
- Spawns `python_sandbox_harness.py` in a subprocess with 5-second timeout
- Algorithm mode: passes `{ mode: "algorithm", code, test_cases }`
- Data mode: passes `{ mode: "data", code, dataframes, csv_dir }`
- Parses JSON from stdout; non-zero exit or timeout → error response

**Harness (`python_sandbox_harness.py`):**
- Sets `resource.RLIMIT_AS` to 512 MB before execution
- Algorithm mode: `exec()`s user code, calls `solve(*args)` for each test case, captures stdout per case
- Data mode: loads DataFrames via `pd.read_csv`, `exec()`s user code with `pd`/`np` in namespace, calls `solve(**dataframes)`, serializes result DataFrame to JSON

**PySpark evaluation:**
No execution at all. `POST /api/pyspark/submit` compares `body.selected_option == question["correct_option"]` and returns `{ correct, explanation }`.

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

**`user_progress` and `user_sample_seen` carry a `topic` column** (DEFAULT `'sql'`). All `db.py` progress functions accept `topic: str = "sql"`. Progress is independent per topic — solving SQL questions does not affect Python unlock state.

**Unlock tiers (pure policy in `unlock.py`, applied independently per topic):**

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
