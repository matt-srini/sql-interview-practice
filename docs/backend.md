# Backend

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md) · [Frontend](./frontend.md)

FastAPI + Uvicorn. PostgreSQL for all product state. DuckDB for SQL query execution (in-memory, loaded at startup). Python/PySpark execution runs in subprocess sandboxes.

---

## Routers

Registered in `backend/main.py`:

| Router file | Prefix | Purpose |
|---|---|---|
| `routers/auth.py` | `/api/auth` | Register, login, logout, current user, forgot/reset password, OAuth (Google + GitHub) |
| `routers/system.py` | — | Health check |
| `routers/catalog.py` | `/api/catalog` | SQL catalog by difficulty |
| `routers/questions.py` | `/api/questions` | SQL question detail, run query, submit (with repeat-attempt detection) |
| `routers/sample.py` | `/api/sample` | Topic-aware sample questions, run, submit, reset |
| `routers/plan.py` | `/api/user` | User profile, plan, unlock state |
| `routers/razorpay.py` | `/api/razorpay` | Order/Subscription creation, client verify, webhook handler |
| `routers/python_questions.py` | `/api/python` | Python algorithm catalog, detail, run-code, submit |
| `routers/python_data_questions.py` | `/api/python-data` | Pandas catalog, detail, run-code, submit |
| `routers/pyspark_questions.py` | `/api/pyspark` | PySpark catalog, detail, submit (MCQ only) |
| `routers/dashboard.py` | `/api` | Cross-track progress dashboard, submission history |
| `routers/paths.py` | `/api/paths` | Learning path catalog and path detail with per-question state |
| `routers/mock.py` | `/api/mock` | Mock interview sessions (start, submit, finish, history) |
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
| POST | `/api/auth/forgot-password` | Send password reset email (always returns 200 to prevent email enumeration) |
| POST | `/api/auth/reset-password` | Consume reset token, set new password (400 if token invalid/expired) |
| GET | `/api/auth/oauth/{provider}/authorize` | Return OAuth authorization URL (`google` or `github`) |
| GET | `/api/auth/oauth/{provider}/callback` | OAuth callback — exchange code, upsert user, set session cookie, redirect to `/` |

Anonymous visitors receive a real user row and session cookie. Registration upgrades that session rather than replacing it, preserving progress. OAuth sign-in uses `get_or_create_oauth_user()` — new users are created, returning users are looked up by `(provider, provider_user_id)`. Password reset emails require `RESEND_API_KEY` to be configured.

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

### Razorpay — `/api/razorpay`

| Method | Path | Description |
|---|---|---|
| POST | `/api/razorpay/create-order` | Creates a Razorpay Order (lifetime plans) or Subscription (pro/elite) for the authenticated user; returns modal-ready payload `{ order_id \| subscription_id, amount, currency, key_id, name, description, prefill_email, prefill_name, is_subscription }` |
| POST | `/api/razorpay/verify-payment` | Verifies HMAC signature on the client-side Razorpay checkout callback and applies the plan change immediately. Idempotent via synthetic event id `verify:<payment_id>` shared with the webhook path |
| POST | `/api/razorpay/webhook` | Verifies `X-Razorpay-Signature` against the raw body, dispatches `payment.captured` / `subscription.activated` / `subscription.charged` / `subscription.cancelled` / `subscription.halted` / `payment.failed`; authoritative source of truth. Lifetime plans are protected against stray subscription-cancel events |

Signature formulas:
- One-time order callback: HMAC-SHA256 of `"{order_id}|{payment_id}"` with `RAZORPAY_KEY_SECRET`
- Subscription callback: HMAC-SHA256 of `"{payment_id}|{subscription_id}"` with `RAZORPAY_KEY_SECRET`
- Webhook: HMAC-SHA256 of the raw request body with `RAZORPAY_WEBHOOK_SECRET`

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
| GET | `/api/submissions` | Submission history for a question (`track`, `question_id`, `limit` query params; max 20) |

Response shape: `{ tracks: { sql, python, python_data, pyspark }, concepts_by_track, recent_activity }`. Each track includes `by_difficulty: { easy: { solved, total }, medium: { solved, total }, hard: { solved, total } }` — note both `solved` and `total` are included in each difficulty object, not bare integers.

### Learning paths — `/api/paths`

| Method | Path | Description |
|---|---|---|
| GET | `/api/paths` | All learning paths with per-user `solved_count` |
| GET | `/api/paths/{slug}` | Path detail including `questions[]` with per-question `state` (`solved`/`unlocked`/`locked`) |

Paths are defined as JSON files in `backend/content/paths/`. The `path_loader.py` module reads them at startup. Each path record has `slug`, `title`, `description`, `topic`, and `questions[]` (ordered list of question IDs). The `/api/paths/{slug}` response enriches each question entry with its catalog metadata and the user's current state.

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

**Quality and feedback extras:**
- On correct + `structure_correct` submissions, `_compute_quality()` runs DuckDB `EXPLAIN` on both queries and returns `{ efficiency_note, style_notes, complexity_hint, alternative_solution }` for the Solution Analysis UI.
- On wrong submissions where the user result shares the **same row and column count** as expected (close-miss), `style_notes` are surfaced as a partial quality object to give coaching feedback without revealing the answer.
- **Repeat-attempt detection** (`routers/questions.py`): before evaluating, `get_latest_submission()` is called. If the prior submission was the identical wrong query, a nudge message is prepended to `feedback` encouraging the user to try a different approach.

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
| `payment_events` | Idempotent payment provider event records (Razorpay webhook ids + synthetic `verify:<payment_id>` ids from client callback) |

**`user_progress` and `user_sample_seen` carry a `topic` column** (DEFAULT `'sql'`). All `db.py` progress functions accept `topic: str = "sql"`. Progress is independent per topic — solving SQL questions does not affect Python unlock state.

**Unlock tiers (pure policy in `unlock.py`, applied independently per topic):**

| Plan | Access |
|---|---|
| Free | All easy. Medium/hard unlock in batches based on solves (track-specific thresholds). Hard is capped. |
| Pro | All easy + all medium + all hard (no cap) |
| Elite | Full catalog |

**Free-tier thresholds — code tracks (SQL, Python, Pandas):**
- Medium: 8 easy → 3 · 15 easy → 8 · 25 easy → all
- Hard: 8 medium → 3 · 15 medium → 8 · 22 medium → 15 *(cap = 15)*

**Free-tier thresholds — PySpark** (higher thresholds — MCQ is lower cognitive effort):
- Medium: 12 easy → 3 · 20 easy → 8 · 30 easy → all
- Hard: 15 medium → 5 · 22 medium → 10 *(cap = 10)*

**Learning path shortcuts:** `compute_unlock_state` accepts `path_state: dict`. `starter_done=True` → all medium unlocked (bypasses threshold grinding). `intermediate_done=True` → full hard cap unlocked. The router fetches path completion state from `GET /api/paths` and passes it in.

**Mock daily limits** (enforced in `compute_mock_access`):
- Free: 1 medium mock/day, unlimited easy and hard
- Pro: 3 hard mocks/day, unlimited easy and medium
- Elite: unlimited

Solved questions remain solved permanently regardless of plan changes.

---

## Request context and error handling

**Request ID** — `middleware/request_context.py` assigns a UUID per request, attaches it to `request.state`, stores it in a contextvar, and returns it as `X-Request-ID`. Structured logs use `[request_id=<id>]` prefix.

**Error payloads** — All user-facing errors follow: `{ error, request_id }`

**Rate limiting** — Applied as middleware to all routes except `/health`.
- Default: 60 requests per 60-second window per IP
- Redis-backed when `REDIS_URL` is set; in-memory fallback otherwise
- Config: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` in `config.py`
- Localhost bypass: requests from `127.0.0.1` / `::1` skip rate limiting in non-prod mode — safe for local dev and Playwright e2e tests

---

## Mock interview router (`routers/mock.py`)

Prefix: `/api/mock`

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/mock/history` | required | Past sessions list (last 20), sorted by `started_at DESC` |
| POST | `/api/mock/start` | required | Start a session; selects questions, persists, returns full question payloads |
| GET | `/api/mock/{id}` | required | Load session state (for reload recovery) |
| POST | `/api/mock/{id}/submit` | required | Evaluate an answer mid-session; updates `mock_session_questions`; no solutions returned |
| POST | `/api/mock/{id}/finish` | required | Mark session completed; returns summary with per-question solutions (idempotent) |

> **Access enforcement:** `POST /api/mock/start` validates plan and daily limits server-side via `compute_mock_access()` before persisting any session. A 403 is returned if the user's plan doesn't allow the requested difficulty, or if daily limits are exhausted. The daily-limit check at `GET /api/mock/access` is a UI preflight only — it does not gate actual session creation.

### Request bodies

**`POST /start`**
```json
{ "mode": "30min|60min|custom", "track": "sql|python|python-data|pyspark|mixed",
  "difficulty": "easy|medium|hard|mixed",
  "num_questions": 2,   // custom only, 1-5
  "time_minutes": 30    // custom only, 10-90
}
```

**`POST /{id}/submit`**
```json
{ "question_id": 1001, "track": "sql", "code": "SELECT ...", "time_spent_s": 120 }
// PySpark: { "question_id": ..., "track": "pyspark", "selected_option": 2 }
```

### Data model

```sql
mock_sessions (id BIGSERIAL, user_id UUID, mode, track, difficulty,
               started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ, time_limit_s INT, status TEXT)

mock_session_questions (id BIGSERIAL, session_id BIGINT→mock_sessions, question_id INT,
                        track TEXT, position INT, is_solved BOOL, submitted_at TIMESTAMPTZ,
                        final_code TEXT, time_spent_s INT)
```

### Question selection

- Questions are randomly sampled from the user's unlocked pool (via `compute_unlock_state`).
- `mixed` track: pools questions from all 4 catalogs.
- `mixed` difficulty: samples across easy/medium/hard.
- Returns 400 if the pool has fewer questions than requested.

### Evaluator reuse

The mock submit endpoint reuses the same evaluators as the practice tracks:
- SQL: `evaluator.evaluate()`
- Python: `python_evaluator.evaluate_python_code()`
- Pandas: `python_evaluator.evaluate_python_data_code()`
- PySpark: direct `selected_option == correct_option` comparison

Correct submissions also call `mark_solved()` and `record_submission()` to update challenge progress.
