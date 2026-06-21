# Backend

> **Navigation:** [Docs index](../README.md) · [Architecture](./architecture.md) · [Frontend](./frontend.md)

FastAPI + Uvicorn. PostgreSQL for all product state. DuckDB for SQL query execution (in-memory, loaded at startup). Python/PySpark execution runs in subprocess sandboxes.

## Observability

Backend Sentry is initialized during app startup when `SENTRY_DSN` is set.

What gets attached to backend events:
- `request_id`
- request path + method
- current user id/email when a session is present
- user plan and email-verification tags when available

Behavior:
- Expected 4xx-style app errors are filtered out before sending to Sentry
- Performance tracing is off by default; enable it with `SENTRY_TRACES_SAMPLE_RATE`
- `SENTRY_RELEASE` can be set to tag backend deploys/releases

---

## Routers

Registered in `backend/main.py`:

| Router file | Prefix | Purpose |
|---|---|---|
| `routers/auth.py` | `/api/auth` | Register, login, logout, current user, forgot/reset password, magic-link, OAuth (Google + GitHub) |
| `routers/system.py` | — | Health check, runtime config |
| `routers/catalog.py` | `/api/catalog` | SQL catalog by difficulty |
| `routers/questions.py` | `/api/questions` | SQL question detail, run query, submit (with repeat-attempt detection) |
| `routers/sample.py` | `/api/sample` | Topic-aware sample questions, run, submit, reset |
| `routers/plan.py` | `/api/user` | User profile, plan, unlock state |
| `routers/razorpay.py` | `/api/razorpay` | Order/Subscription creation, client verify, webhook handler |
| `routers/admin.py` | `/api/admin` | Operator plan-grant endpoints — grant/revoke/list time-limited plan overrides (`ADMIN_SECRET` Bearer token required) |
| `routers/python_questions.py` | `/api/python` | Python algorithm catalog, detail, run-code, submit |
| `routers/pandas_questions.py` | `/api/pandas` | Pandas catalog, detail, run-code, submit |
| `routers/pyspark_questions.py` | `/api/pyspark` | PySpark catalog, detail, submit (reasoning track; additive `interaction_mode` metadata) |
| `routers/data_engineering_questions.py` | `/api/data-engineering` | Data Engineering catalog, detail, submit (constructed-reasoning track; additive `interaction_mode` metadata) |
| `routers/data_modeling_questions.py` | `/api/data-modeling` | Data Modeling catalog, detail, submit (constructed-reasoning track; additive `interaction_mode` metadata) |
| `routers/ml_fundamentals_questions.py` | `/api/ml-fundamentals` | ML Fundamentals catalog, detail, submit (reasoning-first track; additive `interaction_mode` metadata) |
| `routers/experimentation_questions.py` | `/api/experimentation` | Experimentation catalog, detail, submit (constructed-reasoning track; additive `interaction_mode` metadata) |
| `routers/statistics_questions.py` | `/api/statistics` | Statistics catalog, detail, run-code (numerical only), submit (conceptual reasoning or numerical code; additive `interaction_mode` metadata) |
| `routers/account.py` | `/api/account` | Account & billing — rail-aware billing summary, profile update, cancel / switch-plan / update-payment-method / reactivate-subscription, delete account |
| `routers/submissions.py` | `/api/submissions` | Submission history |
| `routers/practice.py` | `/api/practice/drill` | Concept-drill question walks (family-aware, unsolved-first) |
| `routers/dashboard.py` | `/api` | Cross-track progress dashboard (`GET /api/dashboard`) |
| `routers/insights.py` | `/api/dashboard` | Coaching insights: per-track speed/accuracy, weakest concepts, streak |
| `routers/paths.py` | `/api/paths` | Learning path catalog and path detail with per-question state |
| `routers/mock.py` | `/api/mock` | Mock interview sessions (start, submit, finish, history) |
| `routers/spa.py` | — | Static assets + SPA fallback; `_build_seo_meta()` injects per-route title/description/canonical for all known routes including ~139 easy question pages (the four executable tracks SQL/Python/Pandas/PySpark; the five reasoning tracks are not currently SEO-prerendered) |

---

## API reference

### Auth — `/api/auth`

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/register` | Create account; upgrades anonymous session in place |
| POST | `/api/auth/login` | Authenticate; merges anonymous progress into existing account |
| POST | `/api/auth/logout` | Deletes session |
| GET | `/api/auth/me` | Returns current user identity + streak metadata (`streak_days`, `streak_at_risk`) |
| POST | `/api/auth/forgot-password` | Send password reset email (always returns 200 to prevent email enumeration) |
| POST | `/api/auth/reset-password` | Consume reset token, set new password (400 if token invalid/expired) |
| POST | `/api/auth/magic-link` | Request one-time sign-in link (non-enumerating response) |
| GET | `/api/auth/magic-link/callback` | Consume magic-link token, create session cookie, redirect to frontend |
| GET | `/api/auth/oauth/{provider}/authorize` | Return OAuth authorization URL (`google` or `github`) |
| GET | `/api/auth/oauth/{provider}/callback` | OAuth callback — validates one-time state, exchanges code, upserts user, sets session cookie, redirects to frontend |

Anonymous visitors receive a real user row and session cookie. Registration upgrades that session rather than replacing it, preserving progress. OAuth sign-in uses `get_or_create_oauth_user()` — new users are created, returning users are looked up by `(provider, provider_user_id)`. Password reset and magic-link email delivery require `RESEND_API_KEY`.

Security controls on auth:
- Reserved local-part email prefixes are blocked on registration (`admin`, `dev`, `tester`, etc.).
- Login lockout policy: after `LOGIN_LOCKOUT_MAX_ATTEMPTS` failed sign-in attempts, the account is temporarily locked for `LOGIN_LOCKOUT_WINDOW_MINUTES`.
- Session cookie uses `HttpOnly` + `SameSite=Lax`; `secure` is controlled by `SECURE_COOKIES` (defaults to enabled in production).
- OAuth state is server-generated, one-time-use, and short-lived; user-agent/IP-prefix mismatches are logged as risk signals and do not hard-block callback completion.
- Google OAuth authorize scope is `openid email profile`; GitHub OAuth authorize scope is `read:user user:email`.
- **Reserved-domain send guard** (`email_service._is_undeliverable_recipient`): all three senders (verification, password-reset, magic-link) refuse — before any Resend HTTP call — to send to RFC 2606 / 6761 reserved TLDs (`.test`, `.example`, `.invalid`, `.localhost`, `.local`), the `example.{com,net,org}` domains, and malformed addresses. These can never receive mail, so sending only burns quota and produces hard bounces that damage sender reputation. Backstop for the load-test harness, which registers `load-*@internal.test` virtual users (see `backend/loadtest/README.md` and `DECISIONS.md` 2026-06-08). Tested in `tests/test_email_reserved_domains.py`.

### System

| Method | Path | Response |
|---|---|---|
| GET | `/health` | `{ status, postgres, tables_loaded }` |
| GET | `/api/config` | Runtime frontend flags, currently `{ oauth_providers: ["google"|"github", ...] }` (providers are listed only when client id, client secret, and redirect URI are all configured) |

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
| POST | `/api/submit` | `{ query, question_id, duration_ms? }` → structured verdict always. Marks question solved on correct submission. |

Submit response fields:
- `correct` — final acceptance flag (drives progression)
- `is_result_correct` — whether result sets match
- `structure_correct` — structural approach check
- `feedback` — list of adjustment hints
- `user_result`, `expected_result` — both result sets (absent when query fails to execute)
- `solution_query`, `explanation` — always included so hint/solution flow works even on syntax errors

**Run vs Submit contract (SQL):** `run-query` returns a raw error (400) on parse/guard failures — it is a safe drafting tool. `submit` never returns 400; SQL parse or guard errors are wrapped into a structured `{ correct: false, feedback: [error_message], solution_query, explanation }` response so the frontend can always proceed to the verdict → hint stepper → solution reveal flow. A user stuck on syntax is never left in a dead end.

Also available without `/api` prefix.

### Sample — `/api/sample`

The Sample Hub at `/sample` is the discovery surface for the 81 sample questions; its attempted/total markers are powered by `GET /api/sample/summary`. SampleQuestionPage at `/sample/:topic/:difficulty` carries an in-page track + difficulty switcher so users can pivot without returning to the Hub.

**Resume model.** Sample progression follows a commit-not-glance contract: viewing a sample question (GET) is read-only and idempotent. Marking a question as attempted happens only on **submit** (the user committed an answer) or on the explicit **skip** endpoint (the user chose to move on). This means refreshing the page, closing/reopening the tab, or navigating away and back never advances the user past a question they didn't engage with. Anonymous-first identity ensures every visitor (even pre-signup) has a real user row, so the resume state persists across sessions for the same browser.

| Method | Path | Description |
|---|---|---|
| GET | `/api/sample/summary` | Aggregate per-`(track, difficulty)` attempted/total counts for the current user. Used by the Sample Hub tile UI. Response: `{ tracks: { <api_slug>: { <difficulty>: { total, tried } } } }`. The `tried` field is named for backward compatibility — semantically it now counts submits + skips, not GETs. |
| GET | `/api/sample/{topic}/{difficulty}` | Next unattempted sample for a track+difficulty. **Read-only — does not mark anything.** Returns 409 when all 3 have been submitted/skipped. Response `sample` block carries `position` (1-indexed within the pool), `total`, `attempted`, plus legacy aliases `shown_count` (= position) and `remaining` (questions left after the user submits this one). |
| POST | `/api/sample/{topic}/{difficulty}/skip` | Marks the supplied `question_id` as attempted without an answer submission, then returns the next unattempted question (same response shape as GET). Powers the "Another sample →" button. Body: `{ question_id: int }`. |
| POST | `/api/sample/{topic}/{difficulty}/reset` | Clears attempted state for that track+difficulty so the user can redo the set from scratch. |
| POST | `/api/sample/sql/run-query` | Run SQL in SQL sample context (no lock checks). Does not mark attempted. |
| POST | `/api/sample/{topic}/run-code` | Run Python / Pandas sample code (no lock checks). Does not mark attempted. |
| POST | `/api/sample/{topic}/submit` | Evaluate sample answer for any track. **Marks the question as attempted** (correct or incorrect — both count). Does not affect challenge progression. |
| GET | `/api/sample/{difficulty}` | Legacy SQL alias for `/api/sample/sql/{difficulty}` |
| POST | `/api/sample/{difficulty}/reset` | Legacy SQL alias for `/api/sample/sql/{difficulty}/reset` |
| POST | `/api/sample/run-query` | Legacy SQL alias for `/api/sample/sql/run-query` |
| POST | `/api/sample/submit` | Legacy SQL alias for `/api/sample/sql/submit`. Also marks attempted. |

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

### Paddle — `/api/paddle`

The global billing rail (Merchant of Record): used for every non-INR currency; INR uses Razorpay above. Full contract: [`docs/features/pricing.md`](features/pricing.md) § Global payments.

| Method | Path | Description |
|---|---|---|
| POST | `/api/paddle/create-checkout` | Returns the Paddle.js overlay config `{ client_token, environment, price_id, is_subscription, customer_email, custom_data }` for the target plan. No server-side Paddle API call (the overlay is price-id driven — no SDK dependency). Requires auth + verified email; enforces the shared upgrade-path matrix (`plan_policy.py`). Returns 503 until Paddle env vars are set |
| POST | `/api/paddle/webhook` | Source of truth. Verifies the `Paddle-Signature` header, applies/revokes the plan, dedupes on a `paddle:`-prefixed event id, records `provider='paddle'`. Grants on `transaction.completed` / `subscription.activated` / `subscription.updated`; revokes (→ `free`) on `subscription.canceled`. Lifetime plans protected against stray cancels (mirrors Razorpay) |

Paddle signature: header `Paddle-Signature: ts=<unix>;h1=<hmac>` where `h1 = HMAC-SHA256(PADDLE_WEBHOOK_SECRET, "{ts}:{raw_body}")`. The **user** resolves from `custom_data.user_id`; the **target plan** prefers the subscription's current `price_id` (`_plan_tier_for_price_id`, so a mid-cycle plan switch applies correctly) and falls back to `custom_data.target_plan` (set at create-checkout — Paddle's equivalent of Razorpay `notes`). Webhook is CSRF/Origin-exempt like the Razorpay webhook. The `/api/account` billing endpoints are **rail-aware**: a Paddle subscriber (no `razorpay_subscription_id`, has `provider='paddle'` charges) gets a Paddle-shaped `/billing` (history from `payment_events`, `managed_externally:true`) and a **409** on cancel/switch/update-payment (managed via Paddle) — see [`docs/features/pricing.md`](features/pricing.md) § Billing management.

### SPA / static

`GET /` and `GET /{asset_path:path}` serve `frontend/dist` assets. Falls back to `index.html` for SPA routes. `/api/*` paths are excluded from fallback.

---

### Python — `/api/python`

| Method | Path | Description |
|---|---|---|
| GET | `/api/python/catalog` | Python catalog grouped by difficulty with per-user state |
| GET | `/api/python/questions/{id}` | Question detail. Omits `solution_code`/`explanation` pre-submit. |
| POST | `/api/python/run-code` | `{ code, question_id }` → test case results (public cases only). Guard checked first. |
| POST | `/api/python/submit` | `{ code, question_id, duration_ms? }` → verdict + hidden test summary + solution on correct |

### Pandas — `/api/pandas`

| Method | Path | Description |
|---|---|---|
| GET | `/api/pandas/catalog` | Pandas catalog |
| GET | `/api/pandas/questions/{id}` | Question detail including `dataframes` and `schema` maps |
| POST | `/api/pandas/run-code` | `{ code, question_id }` → DataFrame result + `print_output` |
| POST | `/api/pandas/submit` | `{ code, question_id, duration_ms? }` → correct/incorrect + DataFrame comparison + solution on correct |

> **Pandas full-result grading with display preview.** Correctness is decided on the **complete** result (user vs expected DataFrame, normalized), so a correct answer over a large dataset is graded soundly — but only a **~200-row preview** is returned to the client (`python_evaluator._preview_result` / `DATA_PREVIEW_ROWS`; the result dict carries `total_rows` + `truncated` so the panel shows "showing first 200 of N"). The /run-code path routes through the single `run_pandas_code_checked` helper (used by both `pandas_questions.py` and `sample.py`); submit through `evaluate_pandas_code`. The sandbox safety cap is `_MAX_DATA_RESULT_ROWS = 100,000` (data mode) and data-mode spawns use a 12s wall timeout (`DATA_CODE_TIMEOUT_SECONDS`) since a large result serializes a few MB for the grade. **SQL grades on the same full-result/preview model:** `evaluator.run_query(query, question, preview=False)` returns the full result (capped at `MAX_GRADING_ROWS = 100,000`) and `evaluate()` compares it exactly, then returns a `MAX_RESULT_ROWS = 200` preview (`_preview_sql_result`, with `total_rows`/`truncated`). The display endpoints call `run_query` with the default `preview=True`. This closed the prior soundness gap where SQL graded only `head(200)` — a query that diverged only beyond row 200 (or an unordered result whose `head(200)` was non-deterministic) is no longer mis-graded.

> **MCQ answer evaluation (all MCQ tracks + sample + mock).** Every MCQ submit path routes through the single shared helper `backend/mcq.py` → `is_mcq_correct(selected_option, question)` (the 0-indexed `selected_option == correct_option` comparison; `correct_option` is 0-indexed: 0→A, 1→B, 2→C, 3→D, matching the A–D labels the frontend renders). `correct_letter(question)` returns the key's canonical letter. No track re-implements the comparison — this prevents per-track index drift (added 2026-06-03; replaced 10 duplicated call-sites across the 6 track routers, `sample.py`, and `mock.py`).

### PySpark — `/api/pyspark`

| Method | Path | Description |
|---|---|---|
| GET | `/api/pyspark/catalog` | PySpark catalog. Rows include additive `type` and `interaction_mode` metadata when present in content. |
| GET | `/api/pyspark/questions/{id}` | Question detail. Unlocked: full payload with `options` (no `correct_option`) plus additive `interaction_mode` metadata. Locked: 200 with `locked: true`, no `options` or `correct_option`. |
| POST | `/api/pyspark/submit` | `{ selected_option, question_id, duration_ms? }` → `{ correct, explanation }`. No code execution. 403 if locked. |

### Data Engineering — `/api/data-engineering`

| Method | Path | Description |
|---|---|---|
| GET | `/api/data-engineering/catalog` | Data Engineering catalog. Rows include `type` plus `interaction_mode: "constructed_reasoning"`. |
| GET | `/api/data-engineering/questions/{id}` | Question detail. Unlocked: full payload with `options` (no `correct_option`) plus `interaction_mode`. Locked: 200 with `locked: true`, no `options` or `correct_option`, but `interaction_mode` remains present. |
| POST | `/api/data-engineering/submit` | `{ selected_option, question_id, duration_ms? }` → `{ correct, explanation }`. No code execution. 403 if locked. |

### Data Modeling — `/api/data-modeling`

| Method | Path | Description |
|---|---|---|
| GET | `/api/data-modeling/catalog` | Data Modeling catalog. Rows include `type` plus `interaction_mode: "constructed_reasoning"`. |
| GET | `/api/data-modeling/questions/{id}` | Question detail. Unlocked: full payload with `options` (no `correct_option`) plus `interaction_mode`. Locked: 200 with `locked: true`, no `options` or `correct_option`, but `interaction_mode` remains present. |
| POST | `/api/data-modeling/submit` | `{ selected_option, question_id, duration_ms? }` → `{ correct, explanation }`. No code execution. 403 if locked. |

### ML Fundamentals — `/api/ml-fundamentals`

| Method | Path | Description |
|---|---|---|
| GET | `/api/ml-fundamentals/catalog` | ML Fundamentals catalog. Rows include `type` plus `interaction_mode: "constructed_reasoning"` in the current bank. |
| GET | `/api/ml-fundamentals/questions/{id}` | Question detail. Unlocked: full payload with `options` (no `correct_option`) plus `interaction_mode`. Locked: 200 with `locked: true`, no `options` or `correct_option`, but `interaction_mode` remains present. |
| POST | `/api/ml-fundamentals/submit` | `{ selected_option, question_id, duration_ms? }` → `{ correct, explanation }`. No code execution. 403 if locked. |

### Experimentation — `/api/experimentation`

| Method | Path | Description |
|---|---|---|
| GET | `/api/experimentation/catalog` | Experimentation catalog. Rows include `type` plus `interaction_mode: "constructed_reasoning"`. |
| GET | `/api/experimentation/questions/{id}` | Question detail. Unlocked: full payload with `options` (no `correct_option`) plus `interaction_mode`. Locked: 200 with `locked: true`, no `options` or `correct_option`, but `interaction_mode` remains present. |
| POST | `/api/experimentation/submit` | `{ selected_option, question_id, duration_ms? }` → `{ correct, explanation }`. No code execution. 403 if locked. |

### Statistics — `/api/statistics`

This track uses `eval_kind="mixed"` with `mixed_subtype=True`. Each question has a `subtype` field: `"conceptual"` (MCQ) or `"numerical"` (Python code).

| Method | Path | Description |
|---|---|---|
| GET | `/api/statistics/catalog` | Statistics catalog. Each catalog entry includes `type`, `subtype`, and `interaction_mode` (`constructed_reasoning` for conceptual, `executable_problem_solving` for numerical). |
| GET | `/api/statistics/questions/{id}` | Question detail. Conceptual: includes `options` (no `correct_option`) and `interaction_mode: "constructed_reasoning"`. Numerical: includes `starter_code` + `test_cases` (no expected outputs) and `interaction_mode: "executable_problem_solving"`. Both: `subtype` field. Locked: 200 with `locked: true` and preserved `interaction_mode`. |
| POST | `/api/statistics/run-code` | `{ question_id, code }` — only works for numerical questions (400 for conceptual). Applies statistics import allowlist guard. |
| POST | `/api/statistics/submit` | `{ question_id, selected_option }` for conceptual → `{ correct, subtype, explanation }`. `{ question_id, code }` for numerical → `{ correct, subtype, solution_code, explanation }`. 403 if locked. |

### Dashboard — `/api/dashboard`

| Method | Path | Description |
|---|---|---|
| GET | `/api/dashboard` | Per-track solved counts, concepts, and recent activity for the current user |
| GET | `/api/dashboard/insights` | Coaching metrics derived from submissions (per-track solve speed + accuracy, weakest concepts, streak, cross-track insight) |
| GET | `/api/submissions` | Submission history for a question (`track`, `question_id`, `limit` query params; max 20) including optional `duration_ms` when provided by clients |

Response shape includes every active track: `{ tracks: { sql, python, pandas, pyspark, data-engineering, data-modeling, statistics, ml-fundamentals, experimentation }, concepts_by_track, recent_activity }`. Each track includes `by_difficulty: { easy: { solved, total }, medium: { solved, total }, hard: { solved, total } }` — note both `solved` and `total` are included in each difficulty object, not bare integers.

`GET /api/dashboard/insights` response shape:

```json
{
    "per_track": {
        "sql": { "solve_count": 28, "median_solve_seconds": 512, "accuracy_pct": 0.82 },
        "python": { "solve_count": 12, "median_solve_seconds": 740, "accuracy_pct": 0.71 },
        "pandas": { "solve_count": 5, "median_solve_seconds": 930, "accuracy_pct": 0.8 },
        "pyspark": { "solve_count": 18, "median_solve_seconds": 120, "accuracy_pct": 0.88 }
    },
    "weakest_concepts": [
        { "concept": "window functions", "track": "sql", "attempts": 8, "correct": 3, "accuracy_pct": 0.375 }
    ],
    "cross_track_insight": "You solve Python ~4 minutes slower than SQL. Try 3 Python mediums to close the gap.",
    "streak_days": 7
}
```

Example is abbreviated for readability; the real payload includes all 9 active tracks.

Notes:
- `median_solve_seconds` is computed from first-attempt to first-correct duration per solved question, then medianed per track.
- `weakest_concepts` returns bottom 3 concepts by accuracy where attempts >= 3.
- `cross_track_insight` is deterministic and only returned when the slowest-vs-fastest median gap is at least 60 seconds.
- `streak_days` counts consecutive calendar days ending today with at least one correct submission.
- Endpoint is cached in-process for 60 seconds per user.

### Concept drill — `/api/practice`

| Method | Path | Description |
|---|---|---|
| GET | `/api/practice/drill` | All PRACTICE questions in one track whose concept tags resolve to the supplied concept family — the data behind a focused weak-concept drill walk. **Pro/Elite only** (403 for Free). |

Query params: `track` (slug) and `concept` (a concept **family** name, e.g. `GROUPED AGGREGATION`). Matching is **family-aware** via `concept_matches_focus` (the same resolver Mock's `focus_concepts` filter uses), so tag variants that resolve to the same family are included. Solved state is read per-track via `get_solved_ids(user_id, topic=track.db_topic)` (not the SQL-hardcoded `progress.get_solved_question_ids`). Response:

```json
{
  "track": "pandas",
  "track_label": "Pandas",
  "concept": "GROUPED AGGREGATION",
  "total": 46,
  "solved_count": 7,
  "questions": [
    { "id": 31011, "title": "…", "difficulty": "easy", "order": 1, "concepts": ["GROUPED AGGREGATION"], "state": "unlocked" }
  ]
}
```

Questions are ordered **unsolved-first → easy→hard → order asc** (a drill leads with what you haven't mastered; solved questions trail for review, so the entry point lands at position 1). Unknown `track` → 404; a concept with no matches → 200 with `questions: []`. The frontend consumes this as a `?drill=<concept>` context on `QuestionPage` (see [frontend.md §Concept drill](frontend.md#concept-drill)). Lives in `backend/routers/practice.py`; tests in `backend/tests/test_practice_drill.py`. This is the practice-side weak-concept drill — distinct from the mock custom-drill (`focus_concepts`) mode.

### Learning paths — `/api/paths`

| Method | Path | Description |
|---|---|---|
| GET | `/api/paths` | All learning paths with per-user `solved_count` |
| GET | `/api/paths/{slug}` | Path detail including `questions[]` with per-question `state` (`solved`/`unlocked`/`locked`) |

Paths are defined as JSON files in `backend/content/paths/`. The `path_loader.py` module reads them at startup. Each path record has `slug`, `title`, `description`, `topic`, and `questions[]` (ordered list of question IDs). The `/api/paths/{slug}` response enriches each question entry with its catalog metadata and the user's current state.

Current footprint: **96 paths total** (SQL 11, Python 11, Pandas 9, PySpark 14, Data Engineering 9, Data Modeling 11, Statistics 11, ML Fundamentals 12, Experimentation 8). Path records also include `tier` (`free`/`pro` — controls path-listing visibility only), `level` (`foundational`/`intermediate`/`advanced` — UX badge, see canonical definition in [`docs/content-authoring.md`](./content-authoring.md) §Paths), `patterns[]` (practitioner-skill slugs from `backend/path_patterns.py`), `focus_concepts[]` (concept-family tags used by insights), `outcomes`, and `recommended_after[]` (prerequisite path slugs forming a DAG).

The `GET /api/dashboard/insights` endpoint uses `focus_concepts` to attach `recommended_path_slug` and `recommended_path_title` to each entry in `weakest_concepts`. Matching is **family-aware**: both the weak concept and the path's `focus_concepts` are resolved to their canonical concept family before comparison (same resolver Mock's `focus_concepts` filter uses). Foundational paths take priority over intermediate, which take priority over advanced. **Routing note:** the coaching UI (dashboard focus card + weak-areas panel, logged-in landing weak-spots, mock post-mortem) now leads with the [concept drill](#concept-drill--apipractice) (`/practice/{track}?drill={concept}`) as the primary "Drill" action and offers `recommended_path_slug` only as an honest secondary (*Or take the … path →*). The Elite `study_plan` remains a curated mixed planner where a `learning_path` step is still legitimate (labelled *Start path →*).

### Admin — `/api/admin`

Operator-only endpoints for granting time-limited plan access (beta testers, invited users, etc.). All requests require `Authorization: Bearer <ADMIN_SECRET>` where `ADMIN_SECRET` is set in the environment. If `ADMIN_SECRET` is not configured, all endpoints return 503.

| Method | Path | Description |
|---|---|---|
| POST | `/api/admin/grant-plan` | Grant a time-limited Pro or Elite override to a user by email |
| DELETE | `/api/admin/grant-plan` | Revoke the override immediately (user returns to base plan) |
| GET | `/api/admin/grants` | List all users who have (or had) a `plan_override` set |

**Grant request body:** `{ email: string, plan: "pro"|"elite", days: 1–365 }`

**How overrides work:** The `users` table has two nullable columns — `plan_override` (text) and `plan_override_until` (timestamptz). At every auth resolution point (`get_session_user`, `get_user_credentials_by_email` login path, `get_user_by_id/email`, OAuth flows), the `_effective_plan()` helper checks whether an active override exists. If `plan_override IS NOT NULL` and `plan_override_until > now()`, the override is returned as the user's plan. Otherwise, the base `plan` column is used. No cron job is needed — override expiry is evaluated lazily on each request. After expiry the user silently reverts to their base plan at next session load.

POST and DELETE are idempotent: calling grant again on an already-granted user overwrites (useful to extend duration or upgrade from Pro to Elite). Calling DELETE on a user without an override is a no-op (returns the base plan).

**Security:** This router is internal tooling and is never accessible to end users. The `ADMIN_SECRET` should be a strong random value (at least 32 bytes of URL-safe entropy). Route is registered in `main.py` before `spa.router` so it won't be caught by the SPA fallback.

---

## Query execution pipeline

Files: `sql_guard.py` → `evaluator.py` → `database.py`

**Run path:**
1. `validate_read_only_select_query` — parser-based safety check (no writes, single statement; complexity guard rejects a cartesian join (no `ON`/`USING`) and more than `MAX_JOINS` joins — currently 9, since the 3s timeout + result caps are the real cost bound, see `docs/decisions/DECISIONS.md`)
2. Lightweight cursor from shared in-memory DuckDB engine
3. Execute directly (preserves `ORDER BY` semantics)
4. Thread pool with 3-second timeout
5. Display path (`run_query`, `preview=True`) caps to 200 rows; grading (`evaluate` → `run_query(preview=False)`) keeps the full result (≤ `MAX_GRADING_ROWS`)

**Evaluation path (submit):**
1. Run user query and expected query in same DuckDB environment
2. Build pandas DataFrames from both
3. Normalize: column casing, column order, float precision, nulls
4. Compare via `_results_match`: order-insensitive questions (no trailing `ORDER BY`) compare as **multisets** (rows sorted); order-sensitive questions require the **same row multiset AND the same sequence of `ORDER BY` key values**

Behavioral rules:
- Column ordering differences are ignored
- **Order-sensitive comparison is tie-tolerant.** When the expected query has a trailing `ORDER BY`, only the **key-column sequence** must match — rows that *tie* on the key may appear in any internal order (`_results_match` + `_parse_order_by_columns`, which reads the *outermost* trailing `ORDER BY`, ignoring window/CTE `ORDER BY`s, and falls back to strict positional comparison when the key is an expression/ordinal it cannot map to an output column). This replaced a full-row positional comparison that assumed every `ORDER BY` was a *total* order: when the sort key had ties, DuckDB returned tied rows in unstable order, so a correct answer — including the reference query graded against itself — was marked wrong a large fraction of the time (18 questions affected). A genuinely misordered answer is still rejected (the key sequence differs). Guarded by `tests/test_sql_grading_tie_tolerance.py`.
- **Deterministic grading engine.** The grading DuckDB connection runs single-threaded (`SET threads TO 1` in `database.init_query_engine`). DuckDB parallelises aggregation and float addition is non-associative, so a multi-threaded `avg()`/`sum()` could differ in its last bits between runs and a downstream `ROUND(…, 2)` near a boundary would flip the displayed value — marking a correct answer wrong on the unlucky run (2 questions exhibited this). Datasets are tiny (≤ ~9k rows) so the throughput cost is negligible. Guarded by `tests/test_sql_grading_determinism.py`.
- **Single-writer concurrency discipline.** The golden DuckDB connection is not thread-safe: concurrent `.execute()` on it (or creating a cursor while another thread runs) **segfaults the process**. Two changes make SQL safe under concurrency: (1) the loaded-table set is snapshotted once at startup (`database._loaded_table_names`), so `get_loaded_tables()` — hit by `/health` and by every SQL query via `get_query_cursor` — reads a cached tuple instead of running `SHOW TABLES` on the shared connection; (2) all SQL grading/execution runs through `offload.run_blocking_sql`, which serializes DuckDB behind a process-wide async lock (one op at a time) and off the event loop. Before this, the segfault was masked only because the single event loop serialized everything; offloading SQL to threads without these guards would have introduced a hard crash. SQL is sub-100 ms on these datasets, so serialization is not the throughput bottleneck for this product's traffic mix. Guarded by `tests/test_concurrency_smoke.py`.
- **Pinned grading engine version.** `duckdb` is pinned (`==1.5.0` in `requirements.txt`) — the version every SQL reference was authored and validated against. Single-threading fixes *run-to-run* jitter within a version, but a *version bump* can change query semantics outright: 1.5.3 has a window-function regression that made q13011's reference return 0 rows (vs the intended 83 on 1.5.0, same arch + data), which surfaced only because the engine was unpinned and CI installed the latest. A grading engine must be pinned to the validated version; bumping it requires re-running `tests/test_code_references.py` (executes every SQL/python/statistics reference and fails on any that becomes degenerate/empty) before merging.
- Duplicate rows preserved
- Float comparisons use tolerance-based normalization
- **Temporal normalization (shared SQL + pandas):** `normalize_dataframe` → `_canonicalize_temporal` canonicalizes date/datetime values so a trivial representation difference compares equal — a `Timestamp`/`date`/ISO-string of the same calendar value, a `T` vs space separator, and a zero time component all collapse to the same canonical form. **Real** time-of-day (`23:28:10`) and coarser granularity (a month bucket `'2024-01'`) are preserved, so a genuinely wrong answer never passes. This is the single shared comparator, so SQL and pandas behave identically. On the pandas side it pairs with `python_sandbox_harness._json_default`, which ISO-serializes `Timestamp`/`date`/numpy scalars out of the sandbox (mirroring the SQL evaluator's `_to_json_native`) — so pandas questions may return datetime columns directly without a serialization crash.

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
- Statistics track: allows `math`, `statistics`, `numpy`, `random`, `collections`, `itertools`, `functools`, `decimal`, `fractions`, `operator`, `typing`; blocks pandas and all others
- Also blocks dangerous attribute access (`__class__`, `__subclasses__`, `system`, etc.)

**Evaluator (`python_evaluator.py`):**
- Spawns `python_sandbox_harness.py` in a subprocess with 5-second timeout
- Algorithm mode: passes `{ mode: "algorithm", code, test_cases }`
- Data mode: passes `{ mode: "data", code, dataframes, csv_dir }`
- Parses JSON from stdout; non-zero exit or timeout → error response

**Harness (`python_sandbox_harness.py`):**
- Sets `resource.RLIMIT_AS` to 512 MB at the start of `main()` (the subprocess entry), before executing user code — deliberately **not** at import time, so importing helpers like `_compare` (the test suite, `validate_content.py`) does not cap the host process (a 512 MB cap on a pandas/DuckDB-loaded pytest process OOMs on Linux)
- Algorithm mode: `exec()`s user code, calls `solve(*args)` for each test case, captures stdout per case
- Data mode: loads DataFrames via `pd.read_csv`, `exec()`s user code with `pd`/`np` in namespace, calls `solve(**dataframes)`, serializes result DataFrame to JSON
- **Declared-tolerance grading (`_compare`):** a test case may carry a numeric `tolerance` (statistics Monte-Carlo / numerical-method answers where the reference is itself approximate). `_compare(actual, expected, tolerance)` honors it with a **1e-6 floor** — `eff_tol = max(tolerance, 1e-6)` — so a larger declared tolerance accepts a correct-but-approximate answer the author intended, while a tighter one can never make a currently-passing question stricter. Comparison is element-wise for equal-length numeric sequences (preserving both order-sensitive and order-insensitive matching), and short-circuits on `a == e` first so exact/`inf` values match before the `abs(a-e)` check (`abs(inf-inf)` is `nan`). The declared tolerance is threaded all the way through: `python_evaluator._expand_test_case` preserves the `tolerance` key when expanding generator specs, so it survives the submit-path into the harness. (Phase-4 fix: `tolerance` was authored on 30 statistics questions but previously dropped at expansion and ignored by the hard-coded 1e-6 in `_compare`, silently making approximate answers ungradeable — e.g. 73047 stored 0.9809, reference yields 0.9805 within the declared 0.02.)

**PySpark evaluation:**
No execution at all. `POST /api/pyspark/submit` compares `body.selected_option == question["correct_option"]` and returns `{ correct, explanation }`. `interaction_mode` is additive metadata only; it does not change PySpark scoring semantics in Phase 1.

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
| `payment_events` | Idempotent payment-provider event log across both billing rails. `provider` column (`razorpay` \| `paddle`). Ids: Razorpay webhook ids + synthetic `verify:<payment_id>` (client callback); Paddle ids stored `paddle:`-prefixed so the two rails can never collide in the shared `event_id` PK |

*(Representative subset — `backend/db.py` defines 15 tables in total. Omitted here: `submissions`, `oauth_accounts`, `password_reset_tokens`, `email_verification_tokens`, `oauth_states`, `magic_link_tokens`, `mock_sessions`, `mock_session_questions`, `mock_chain_consumption`, `mock_discards`.)*

**`user_progress` and `user_sample_seen` carry a `topic` column** (DEFAULT `'sql'`). All `db.py` progress functions accept `topic: str = "sql"`. Progress is independent per topic — solving SQL questions does not affect Python unlock state.

**Unlock tiers (pure policy in `unlock.py`, applied independently per topic):**

| Plan | Access |
|---|---|
| Free | All easy. Medium/hard unlock in batches based on solves (track-specific thresholds). Hard is capped. |
| Pro | All easy + all medium + all hard (no cap) |
| Elite | Full catalog |

*(A **render of [`backend/unlock.py`](../backend/unlock.py)**, the canonical SoT — keep in sync per CLAUDE.md § Linked-docs / single-SoT rule.)*

**Free-tier thresholds — code tracks (SQL, Python, Pandas):**
- Medium: 8 easy → 3 · 15 easy → 8 · 25 easy → all
- Hard: 8 medium → 3 · 15 medium → 8 · 22 medium → 15 *(cap = 8)*

**Free-tier thresholds — MCQ tracks (PySpark, Data Engineering)** (option-hiding balances the lower cognitive effort):
- Medium: 10 easy → 3 · 17 easy → 8 · 25 easy → all
- Hard: 12 medium → 5 *(cap = 5)*

**Learning paths and unlocks:** Paths do **not** influence unlock state. `compute_unlock_state` is threshold-only. A user solving a question via the path UI gets the same `solved` mark and the same threshold-counter advancement as solving from practice directly. See [`docs/content-authoring.md`](./content-authoring.md) §Paths for the canonical model.

**Mock limits** (post-Phase-3; enforced via `get_daily_benchmark_usage` / `get_daily_custom_usage` / `get_weekly_benchmark_usage`). Modes: `benchmark`, `custom`, `interview_loop`. Single source of truth: [`docs/features/mock.md`](./features/mock.md).
- Free: 1 `benchmark` per rolling 7 days (easy only, practice-pool questions). No `custom`. No `interview_loop`.
- Pro: 3 `benchmark`/day + 3 `custom`/day (independent counters), any difficulty. Mock-only content pool unlocked. No `interview_loop`.
- Elite: unlimited (soft abuse cap only). + `focus_concepts` filter. + `interview_loop`. + deep analytics + debrief.

Legacy `30min`/`60min` sessions in history are read-only and cannot be started new.

Solved questions remain solved permanently regardless of plan changes.

---

## Request context and error handling

**Request ID** — `middleware/request_context.py` assigns a UUID per request, attaches it to `request.state`, stores it in a contextvar, and returns it as `X-Request-ID`. Structured logs use `[request_id=<id>]` prefix.

**Error payloads** — All user-facing errors follow: `{ error, request_id }`

**Rate limiting** — Applied as middleware to all routes except `/health`. Keyed on `request.client.host`.
- Default: 60 requests per 60-second window per IP
- Redis-backed when `REDIS_URL` is set; in-memory fallback otherwise. **The in-memory limiter is process-local** — fine single-replica (dev), but ineffective as a *global* limit across horizontal replicas. `create_rate_limiter` therefore **raises at startup in production** if `REDIS_URL` is unset or Redis init fails, so the in-memory fallback can never silently run in prod (Redis is mandatory there).
- Config: `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` in `config.py`. Auth endpoints add `_auth_rate_limiter` (baseline) and `_auth_token_issue_limiter` (stricter, for token-issuing routes) — see `routers/auth.py` `_check_auth_limits`.
- Localhost bypass: requests from `127.0.0.1` / `::1` skip rate limiting in non-prod mode — safe for local dev and Playwright e2e tests. (Disabled in prod, where `IS_PROD` is true.)
- **Graceful degradation on a backend blip** (`BaseRateLimiter.check_safe`): `RedisRateLimiter.check` can raise on a transient post-startup Redis error; left unhandled it would surface as a **500**. `check_safe` logs the blip at WARNING and degrades deliberately — **fail-open** (allow) for the coarse per-IP limiter and the auth *baseline* limiter (a blip must not 500 every page; Postgres login-lockout is the real brute-force control), and **fail-closed** (deny, short `Retry-After`) for the token-issue limiter (it bounds expensive side effects — magic-link/verification emails, OAuth state — so refusing briefly beats allowing a blast). The in-memory limiter never raises, so this only triggers with Redis (prod). Guarded by `tests/test_15_rate_limiting.py` (TC-229..231).
- **Per-IP keying depends on the proxy hop.** uvicorn is started without an explicit `--forwarded-allow-ips`, defaulting to `proxy_headers=True` + `forwarded_allow_ips="127.0.0.1"`: `X-Forwarded-For` is trusted only when the socket peer is `127.0.0.1`, otherwise `request.client.host` is the socket peer. So keying is correct only if the prod proxy reaches the container from `127.0.0.1`; otherwise all clients collapse into one proxy-IP bucket. Operational guidance + the recommended `FORWARDED_ALLOW_IPS` fix (pin to the real proxy hop, never `*`) live in `docs/deployment.md` § Rate-limiter operational notes & findings; measured by `backend/loadtest/ratelimit.py`.

**Off-loop code execution + concurrency cap** (`offload.py`) — Every code execution is blocking: DuckDB SQL grading runs synchronous queries; Python/Pandas/statistics grading spawns an OS subprocess and blocks on `communicate()` for up to 5–12 s. The API runs on a single event loop (one uvicorn worker per replica), so a blocking call made *directly* from an `async def` endpoint freezes the whole loop for its full duration — stalling every other request (head-of-line blocking; a concurrent `/health` was measured stalling ~4.7 s behind a single 5 s execution). Two helpers fix this and are the **only** way the request path runs an evaluator:

- `offload.run_blocking_exec(fn, …)` — runs a subprocess-backed evaluator (Python/Pandas/statistics) in a worker thread (`asyncio.to_thread`) under a global `asyncio.Semaphore` (default **cores − 2**, `MAX_CONCURRENT_EXECUTIONS`). Sandboxes are process-isolated, so several run concurrently up to the cap.
- `offload.run_blocking_sql(fn, …)` — runs a DuckDB evaluator (`evaluate` / `run_query`) in a worker thread, serialized behind a process-wide async lock (DuckDB is a single in-process engine; concurrent connection use segfaults — see § SQL evaluation path). The SQL lock is acquired *before* the semaphore so SQL never consumes more than one slot.

Both keep the loop free regardless, so reads (`/health`, catalog, other users) stay fast while executions run. Applied uniformly across **all** code-exec paths: practice SQL/Python/Pandas (`questions.py`, `python_questions.py`, `pandas_questions.py`), statistics (`statistics_questions.py`), sample (`sample.py` — including the formerly-sync `run-query`/`run-code` endpoints, now `async`), and mock (`mock.py` `_evaluate_submission`). Previously the semaphore wrapped only 6 endpoints and was largely cosmetic (the blocking call serialized requests on the loop *before* the semaphore could parallelize them); statistics/sample/mock bypassed it entirely. The `cores − 2` default leaves CPU headroom and bounds peak sandbox memory (concurrency × `RLIMIT_AS` 512 MB), which the Railway container RAM cap must be sized above. See `docs/decisions/DECISIONS.md` (2026-06-08 head-of-line offload entry) and `backend/loadtest/` for the harness that measured this.

**Off-loop password hashing** (`offload.run_blocking_hash`) — Password hashing is the *other* blocking-CPU call on the request path: `db._hash_password` / `db.verify_password` run `hashlib.pbkdf2_hmac` with 260k iterations (~22 ms each, synchronous; PBKDF2 releases the GIL). Run directly on the loop they serialize an auth burst (e.g. 100 concurrent logins ≈ 2.2 s of loop block, stalling every unrelated request). The async wrappers `db.hash_password` / `db.verify_password_async` offload the work to a worker thread under a **separate** `asyncio.Semaphore` (`MAX_CONCURRENT_HASHES`, default **cores − 1**); the sync helpers stay the implementation and are still used by offline scripts/seeding. The hash cap is intentionally **independent** of `MAX_CONCURRENT_EXECUTIONS` — auth hashing (a small CPU burst) and sandbox execution (a heavy 512 MB subprocess) are different resource classes and must not contend for each other's slots. Request-path callers — register (`upgrade_anonymous_to_registered`, `add_password_to_existing_user`), login (incl. the constant-time dummy verify that blocks account enumeration), and reset-password (`update_password`) — all go through the async wrappers. The 260k iteration count is unchanged (a security parameter). Guarded by `tests/test_concurrency_smoke.py`. See `docs/decisions/DECISIONS.md` (2026-06-08 off-loop password hashing entry).

**Category-3 resource-exhaustion caps (sandbox).** Beyond the AST guard (which blocks *escapes*, not resource abuse — a bare `while True: pass` or `[0]*10**10` is correctly allowed), the runtime caps bound what abusive-but-guard-legal code can cost:
- **Timeout with process-GROUP kill** — `_spawn_harness` uses `Popen` + `communicate(timeout=...)`; on expiry `_kill_process_group` sends `SIGKILL` to the whole group (`os.killpg`, the sandbox is its own group via `setsid()`). Plain `subprocess.run` only kills the direct child, so a forked grandchild would orphan to init and outlive the timeout — the group kill closes that. Wall limits: 5 s algorithm / 12 s data.
- **`RLIMIT_NPROC` 256** — fork-bomb cap (per-UID; headroom for app + numpy/BLAS threads, bounds an exponential bomb).
- **`RLIMIT_AS` 512 MB** — memory bomb → `MemoryError`, no host OOM.
- **`RLIMIT_FSIZE` 64 MB** — disk-fill backstop in `/tmp`.
- **`RLIMIT_CPU` 14 s** — CPU backstop just above the longest wall timeout.
- Output caps: 64 KB stdout, 10k list items / 512 KB serialized result.
Validated by `tests/test_sandbox_resource_limits.py` (Linux-gated tests run in CI).

**CSRF mitigation** — In production, mutating API requests (`POST`, `PUT`, `PATCH`, `DELETE`) that include a session cookie must carry an `Origin` header matching configured app origins (`ALLOWED_ORIGINS`, `APP_BASE_URL`, `FRONTEND_BASE_URL`). External webhook paths are exempt.

**Response timing** — All responses include `X-Response-Time-Ms` for baseline latency observability.

---

## Mock interview router (`routers/mock.py`)

Prefix: `/api/mock`

### Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/mock/access` | required | Pre-flight access check: returns per-difficulty `can_start`, `block_reason`, `needs_upgrade`, `daily_limit`, `daily_used` for the given `?track=` and current plan. UI-only preflight — does not gate actual session creation. |
| GET | `/api/mock/history` | required | Past sessions list (last 20), sorted by `started_at DESC` |
| GET | `/api/mock/analytics` | required (Elite) | Aggregate analytics over last 50 sessions, including separated benchmark and drill summaries plus overall concept signals |
| POST | `/api/mock/start` | required | Start a session; selects questions, persists, returns full question payloads. Returns **409** `{"error": "active_session_exists", "session_id": ..., "track": ..., "difficulty": ..., "mode": ...}` if the user already has an active session. |
| GET | `/api/mock/{id}` | required | Load session state (for reload recovery). Each question row includes `submitted_at` so the client can restore the one-shot submit lock after a page reload. |
| POST | `/api/mock/{id}/submit` | required | Evaluate an answer mid-session; updates `mock_session_questions`; no solutions returned. Returns **409** if the question was already submitted this session. Returns **422** if code is blank or MCQ option is missing — neither consumes the one-shot slot. |
| POST | `/api/mock/{id}/finish` | required | Mark session completed; returns summary with per-question solutions (idempotent) |
| DELETE | `/api/mock/{id}` | required | Discard an active session entirely (removes from history/stats), refunding the rate-limit quota. Only allowed within 120 s of `started_at`; returns 204. Returns 400 if already completed, 403 if older than 120 s, and **429** once the daily penalty-free discard cap (`MAX_PENALTY_FREE_DISCARDS_PER_DAY=3`) is reached — in which case the session is **left active** (the user continues or ends it normally). See `docs/features/mock.md` § discard. |

> **Access enforcement:** `POST /api/mock/start` validates plan and daily limits server-side via `compute_mock_access()` before persisting any session. A 403 is returned if the user's plan doesn't allow the requested difficulty, or if daily limits are exhausted. The daily-limit check at `GET /api/mock/access` is a UI preflight only — it does not gate actual session creation.

> **Mode enforcement:** `POST /api/mock/start` accepts `benchmark`, `custom`, and `interview_loop` modes. `benchmark` supports `track="mixed"` — when track is mixed, a `role` is required (data_analyst / data_engineer / analytics_engineer / data_scientist) and the router selects questions via a role-specific slot blueprint (`MIXED_BENCHMARK_CONFIGS`); the 400 fires only when `role` is missing for a mixed track. It is `interview_loop` (not benchmark) that does not support `track="mixed"` — chains are single-track, so mixed has no chain pool. Legacy `60min` sessions remain readable in history, but new frontend setup flows no longer present them as a primary mode.

> **Analytics separation:** `GET /api/mock/analytics` now returns additive `benchmark_summary`, `drill_summary`, and `mode_breakdown` fields so benchmark performance can be compared like-with-like while flexible drill sessions remain visible without contaminating comparable benchmark stats.

> **Benchmark composition:** benchmark sessions now use track-specific composition targets for reasoning tracks instead of reusing PySpark's format sampler globally. PySpark retains its own format template; Statistics retains its `1 numerical + 2 conceptual` split; Data Engineering, Data Modeling, ML Fundamentals, and Experimentation now use track-specific `type` targets so benchmark coverage reflects the actual modality of each track.

### Request bodies

**`POST /start`**
```json
{ "mode": "benchmark|custom|interview_loop", "track": "sql|python|pandas|pyspark|data-engineering|data-modeling|statistics|ml-fundamentals|experimentation|mixed",
  "difficulty": "easy|medium|hard|mixed",
  "role": "data_analyst|data_engineer|analytics_engineer|data_scientist",  // required when track="mixed", else null
  "num_questions": 2,   // custom only, 1-5
  "time_minutes": 30    // custom only, 10-90
}
// Legacy modes 30min/60min are read-only history; not accepted for new sessions.
```

`benchmark` ignores `num_questions` and `time_minutes`; the router applies a fixed blueprint by track:

| Track | Benchmark shape | `time_limit_s` |
|---|---|---|
| SQL | 3 questions | 3600 |
| Python | 2 questions | 3000 |
| Pandas | 2 questions | 3000 |
| Statistics | 3 questions (`1 numerical + 2 conceptual`) | 2700 |
| PySpark | 6 questions | 2400 |
| Data Engineering | 6 questions | 2400 |
| Data Modeling | 5 questions | 2400 |
| ML Fundamentals | 6 questions | 2400 |
| Experimentation | 6 questions | 2400 |
| Mixed | role-dependent slot allocation per `MIXED_BENCHMARK_CONFIGS` — see [`docs/features/mock.md`](./features/mock.md) | role-dependent |

**`POST /{id}/submit`**
```json
{ "question_id": 1001, "track": "sql", "code": "SELECT ...", "time_spent_s": 120 }
// PySpark: { "question_id": ..., "track": "pyspark", "selected_option": 2 }
```

### Data model

```sql
mock_sessions (id BIGSERIAL, user_id UUID, mode, track, difficulty,
               started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ, time_limit_s INT, status TEXT,
               focus_fallback BOOLEAN NOT NULL DEFAULT FALSE, role TEXT)

mock_session_questions (id BIGSERIAL, session_id BIGINT→mock_sessions, question_id INT,
                        track TEXT, position INT, is_solved BOOL, submitted_at TIMESTAMPTZ,
                        final_code TEXT, time_spent_s INT, is_follow_up BOOL,
                        follow_up_dimension TEXT)
```

`is_follow_up = true` marks an Interview Loop chain follow-up question. In an Interview Loop session a parent question's `follow_ups[]` travel as one atomic unit — the parent is `is_follow_up = false`, every follow-up in the chain is `is_follow_up = true`. Benchmark and custom sessions draw standalone questions only and never set this flag. The debrief uses the flag to surface chain-follow-up performance as a coaching signal.

### Question selection

- Benchmark sessions now use track-aware composition instead of the old universal quick/full sizing.
- Statistics benchmark sessions enforce a subtype mix of exactly `1 numerical + 2 conceptual` before randomization.
- PySpark benchmark sessions use a six-slot format template so the benchmark stays code-adjacent rather than collapsing into generic MCQ sampling.

- Questions are randomly sampled from the user's unlocked pool (via `compute_unlock_state`).
- `mixed` track: **role-based** — requires a `role` (data_analyst / data_engineer / analytics_engineer / data_scientist). For `benchmark`, the role maps to a fixed per-track slot blueprint; for `custom`, the role defines the track pool drawn fresh-first. See [`docs/features/mock.md`](./features/mock.md) § Mixed Benchmark Blueprints for the canonical role→track mapping. (The legacy `mixed_mock_slugs()` / `in_mixed_mock` flag — the 4 executable tracks — predates the role-based blueprint and is no longer the mixed-pool source of truth.)
- `mixed` difficulty: samples across easy/medium/hard.
- Returns 400 if the pool has fewer questions than requested.

### Evaluator reuse

The mock submit endpoint reuses the same evaluators as the practice tracks:
- SQL: `evaluator.evaluate()`
- Python: `python_evaluator.evaluate_python_code()`
- Pandas: `python_evaluator.evaluate_pandas_code()`
- PySpark: direct `selected_option == correct_option` comparison

Correct submissions also call `mark_solved()` and `record_submission()` to update challenge progress.

---

## Track registry

`backend/tracks.py` is the single authoritative source for all track metadata. The `TRACKS` tuple holds one `TrackConfig` dataclass per track with: `slug`, `db_topic`, `catalog_module`, `label`, `eval_kind`, `unlock_profile`, `content_dir`, `concept_blocklist`, `hint_rules`, `first_hint_leak_patterns`, `in_mixed_mock`, and `mixed_subtype`.

**Lookup helpers:**
- `get_track(slug)` — by URL slug (raises `ValueError` if unknown)
- `get_track_by_db_topic(db_topic)` — by DB topic string (handles `pandas` legacy alias)
- `all_slugs()` — ordered list of all track slugs
- `mixed_mock_slugs()` — slugs with `in_mixed_mock=True` (all four currently)

All routers and utilities use these helpers instead of hardcoded track lists:
- `unlock.py` — `unlock_profile` drives which free-tier threshold table applies
- `routers/mock.py` — `VALID_TRACKS`, `TRACK_TO_TOPIC`, catalog dispatch, and mixed-pool loop all derive from the registry
- `routers/insights.py` — track enumeration replaced with `TRACKS`
- `routers/sample.py` — run-code dispatch uses `eval_kind`; public-question lookup uses `catalog_module`
- `sample_questions.py` — `get_topic_sample_pool()` uses `catalog_module` instead of per-track imports
- `scripts/validate_content.py` — question dirs, concept blocklists, hint rules, and path validation all derive from the registry

The `db_topic` ↔ `slug` mismatch for Pandas (`pandas` ↔ `pandas`) is the only legacy wart and lives exclusively in the registry entry.
