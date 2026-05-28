# Test Guidance — datathink platform

> **Last updated: 2026-05-29.** This document reflects the current state of the platform:
> **9 tracks · 876 practice + 1,102 mock-only questions · 46 learning paths · Phase 3 mock modes
> (benchmark / custom / interview_loop)**. Test files live in `backend/tests/`. The numbered TC
> scheme maps one-to-one to the test functions in those files — use them as the authoritative
> cross-reference. Update this document alongside any spec change.
>
> **Scope:** Backend API tests (pytest + httpx TestClient). Frontend Vitest unit tests and
> Playwright e2e tests are addressed separately (see `frontend/src/**/*.test.js` and
> `frontend/e2e/`). Unit tests for pure functions (unlock, insights, debrief) are included
> where they are faster or more precise than integration tests.
>
> **Format per test case:**
> `TC-NNN · Name · Actors/preconditions · Steps · Expected result · Tier(s)`

---

## Table of Contents

| # | Section |
|---|---------|
| 0 | [Test Infrastructure Standards](#0-test-infrastructure-standards) |
| 1 | [API Contract & System Endpoints](#1-api-contract--system-endpoints) |
| 2 | [Authentication & Identity](#2-authentication--identity) |
| 3 | [Catalog & Unlock Logic](#3-catalog--unlock-logic) |
| 4 | [Question Access & Details](#4-question-access--details) |
| 5 | [SQL Execution](#5-sql-execution) |
| 6 | [Python Execution](#6-python-execution) |
| 7 | [Pandas Execution](#7-pandas-execution) |
| 8 | [PySpark MCQ](#8-pyspark-mcq) |
| 9 | [Sample Mode](#9-sample-mode) |
| 10 | [Learning Paths](#10-learning-paths) |
| 11 | [Mock Interviews (Phase 3)](#11-mock-interviews-phase-3) |
| 12 | [Dashboard & Insights](#12-dashboard--insights) |
| 13 | [Submission History](#13-submission-history) |
| 14 | [Payments & Webhooks](#14-payments--webhooks) |
| 15 | [Rate Limiting](#15-rate-limiting) |
| 16 | [Security Guards](#16-security-guards) |
| 17 | [Content & Static Integrity](#17-content--static-integrity) |
| 18 | [Data Engineering Track](#18-data-engineering-track) |
| 19 | [Data Modeling Track](#19-data-modeling-track) |
| 20 | [Statistics Track (dual-subtype)](#20-statistics-track-dual-subtype) |
| 21 | [ML Fundamentals & Experimentation Tracks](#21-ml-fundamentals--experimentation-tracks) |
| 22 | [Account Management (Billing)](#22-account-management-billing) |
| 23 | [Reasoning Track Metadata](#23-reasoning-track-metadata) |
| 24 | [Python Evaluator Unit Tests](#24-python-evaluator-unit-tests) |

---

## 0. Test Infrastructure Standards

These rules apply to every test module. They are stated once here; individual test cases do not
repeat them.

### 0.1 Module-level isolation

Every test module MUST declare:

```python
pytestmark = pytest.mark.usefixtures("isolated_state")
```

The `isolated_state` fixture performs the following in order:

**Setup:**
1. `close_pool()` — drain any existing asyncpg connection pool
2. `_reset_db_sync()` — truncate all user-facing tables via psycopg2 (with deadlock-retry logic)
3. `_clear_rate_limit_state()` — reset in-memory rate limiter buckets
4. Monkeypatches `ensure_schema` to a no-op (schema was already created by the session-scoped
   `_test_db_schema` fixture)

**Teardown (same steps).**

The `_test_db_schema` session-scoped fixture runs DDL once at session start via
`asyncio.run(ensure_schema_admin())`. The `isolated_state` fixture's no-op patch prevents
deadlocks between `TRUNCATE` (in teardown) and `CREATE INDEX IF NOT EXISTS` (in lifespan).

### 0.2 TestClient usage

```python
with TestClient(app) as client:
    # all requests inside this block
```

`TestClient` is **never** created at class or module scope. Every test function opens and
closes its own client. This ensures the ASGI lifespan and in-process caches are correctly scoped.

### 0.3 User seeding helpers

```python
def _make_user(client, plan="free", email=None, name="Test User", password="Password1",
               existing_user=None):
    """Seed anon session, register, optionally upgrade plan. Returns user dict.

    If existing_user is provided, re-logs that user into the new client session
    instead of registering a fresh account.
    """
    if existing_user is not None:
        client.get("/api/catalog")
        login = client.post("/api/auth/login", json={
            "email": existing_user["email"], "password": password
        })
        return login.json().get("user", existing_user)
    client.get("/api/catalog")                          # seeds anonymous session
    reg = client.post("/api/auth/register", json={"email": email or _unique_email(),
                                                   "name": name, "password": password})
    assert reg.status_code == 201
    user = reg.json()["user"]
    if plan != "free":
        up = client.post("/api/user/plan", json={"user_id": user["id"], "new_plan": plan,
                                                  "context": "test-setup"})
        assert up.status_code == 200
    return user
```

Plan values: `"free"`, `"pro"`, `"elite"`, `"lifetime_pro"`, `"lifetime_elite"`.

For state that cannot be driven through the HTTP API (e.g., inserting historical submissions
at specific timestamps), use direct psycopg2 helpers defined in `conftest.py`:

```python
def _insert_submission(user_id, question_id, *, track, is_correct, submitted_at=None, duration_ms=None)
def _insert_progress(user_id, question_id, *, track, solved_at=None)
def _db_conn()   # returns a short-lived psycopg2 connection, caller closes it
def _create_email_verification_token(user_id) -> str
def _create_password_reset_token(user_id) -> str
def _create_oauth_state_token(provider="google") -> str
def _consume_oauth_state_token(state_token)
def verify_test_user(user_id)  # marks email_verified=true directly in DB
```

Note: `_insert_progress` maps track slugs to `db_topic` values (`python-data` → `python_data`).

### 0.4 Email service

`email_service.send_verification_email` and `email_service.send_password_reset_email` are
patched globally as `AsyncMock(return_value=True)` in `pytest_configure`. Individual tests
MUST NOT re-patch these unless explicitly testing email dispatch side effects.

### 0.5 Rate limiter

`TESTING=1` env var is set globally. The rate limiter uses in-memory fallback (no Redis).
To test rate-limit enforcement, use `monkeypatch.setattr` to lower thresholds:

```python
monkeypatch.setattr("routers.auth.LOGIN_LOCKOUT_MAX_ATTEMPTS", 3)
```

### 0.6 No repetition rule

Each behaviour is tested exactly once in its most appropriate section. Where a later section
depends on a behaviour already verified earlier, it may assume that behaviour and reference the
earlier TC number rather than re-verifying it.

### 0.7 Unique email generation

```python
_counter = itertools.count(1)
def _unique_email(): return f"test-{next(_counter)}@internal.test"
```

Use `itertools.count` (not `uuid4`) — deterministic, readable in failure output.

### 0.8 Database safety guard

`_reset_db_sync` and `isolated_state` both assert that `DATABASE_URL` ends in `_test`. This
prevents accidental truncation of the main database. The default test DB is
`postgresql://postgres:postgres@localhost:5432/sql_practice_test`.

---

## 1. API Contract & System Endpoints

**Connection rules:** No user seeding needed. Use a bare `TestClient(app)`.

---

**TC-001 · Health check — happy path**
- Preconditions: Postgres reachable, DuckDB tables loaded
- Steps: `GET /health`
- Expected: 200; body contains `"status": "ok"`; body contains `"postgres": "ok"`; body contains at least one loaded table name
- Tier: all

**TC-002 · X-Request-ID header present on every response**
- Steps: `GET /health`
- Expected: response header `X-Request-ID` is a non-empty string
- Tier: all

**TC-003 · X-Response-Time-Ms header present on every response**
- Steps: `GET /health`
- Expected: response header `X-Response-Time-Ms` is a numeric string (≥ 0)
- Tier: all

**TC-004 · Error shape: { error, request_id }**
- Steps: `GET /api/questions/99999999` (non-existent question, no session)
- Expected: response is 4xx; body has keys `"error"` (non-empty string) and `"request_id"` (non-empty string)
- Tier: all

**TC-005 · Config endpoint returns provider availability**
- Steps: `GET /api/config`
- Expected: 200; body contains `"google_oauth_enabled"` and `"github_oauth_enabled"` as booleans
- Tier: all

---

## 2. Authentication & Identity

### 2A. Anonymous identity

**TC-006 · Unauthenticated catalog hit creates anonymous user**
- Preconditions: fresh DB
- Steps: `GET /api/catalog`
- Expected: 200; session cookie set; subsequent `GET /api/auth/me` returns 401 (anon has no email)
- Tier: all

**TC-007 · GET /api/auth/me — anonymous session returns 401**
- Preconditions: session cookie from `GET /api/catalog`
- Steps: `GET /api/auth/me`
- Expected: 401; body `{ "user": null }`
- Tier: all

---

### 2B. Registration

**TC-008 · Happy path registration**
- Steps: hit catalog (anon), `POST /api/auth/register { email, name, password }`
- Expected: 201; body `{ "user": { id, email, name, plan: "free", email_verified: false } }`; `set-cookie` header; email_service mock called once
- Tier: all

**TC-009 · Duplicate email registration rejected**
- Steps: register once; attempt again with same email
- Expected: second registration returns 400; body has `"error"` key
- Tier: all

**TC-010 · Weak password — missing uppercase**
- Steps: `POST /api/auth/register { password: "password1" }`
- Expected: 422 or 400; error references password rule
- Tier: all

**TC-011 · Weak password — missing digit**
- Steps: `POST /api/auth/register { password: "Passwordonly" }`
- Expected: 422 or 400
- Tier: all

**TC-012 · Weak password — too short (< 8 chars)**
- Steps: `POST /api/auth/register { password: "Ab1" }`
- Expected: 422 or 400
- Tier: all

**TC-013 · Reserved email prefix blocked**
- Steps: `POST /api/auth/register { email: "admin@example.com" }`
- Expected: 400; error references reservation
- Tier: all

**TC-014 · Blocked registration domain rejected**
- Steps: `POST /api/auth/register { email: "user@datathink.co" }`
- Expected: 400
- Tier: all

**TC-015 · Already-registered session cannot re-register**
- Steps: register successfully; call `POST /api/auth/register` again with the same session
- Expected: 400
- Tier: all

---

### 2C. Login & Logout

**TC-016 · Correct credentials set session cookie**
- Preconditions: registered user with verified email (use `verify_test_user()`)
- Steps: `POST /api/auth/login { email, password }`
- Expected: 200; body `{ "user": { id, email, name, plan, email_verified } }`; `set-cookie` contains session token
- Tier: all

**TC-017 · Wrong password returns 401**
- Steps: `POST /api/auth/login { email: valid, password: "WrongPass1" }`
- Expected: 401; body `{ "error": "Invalid email or password.", ... }`
- Tier: all

**TC-018 · Login merges anonymous progress into existing account**
- Steps: (a) register user A; mark one question solved via `_insert_progress`; (b) fresh client, new anon; mark a different question solved; (c) `POST /api/auth/login` with user A credentials
- Expected: after login, catalog shows both questions as solved
- Tier: all

**TC-019 · Logout clears session cookie**
- Preconditions: logged-in session
- Steps: `POST /api/auth/logout`; then `GET /api/auth/me`
- Expected: logout returns 200 `{ "ok": true }`; subsequent `/me` returns 401
- Tier: all

---

### 2D. Email verification

**TC-020 · Valid verification token marks account as verified**
- Steps: register; call `POST /api/auth/verify-email { token }` with token from `_create_email_verification_token(user_id)`
- Expected: 200 `{ "ok": true }`; `GET /api/auth/me` shows `email_verified: true`
- Tier: all

**TC-021 · Expired or consumed verification token returns 400**
- Steps: generate token; consume it once; attempt `POST /api/auth/verify-email` a second time
- Expected: 400; error references "invalid or has expired"
- Tier: all

**TC-022 · Resend verification — unauthenticated returns 401**
- Steps: `POST /api/auth/resend-verification` with no session
- Expected: 401
- Tier: all

**TC-023 · Resend verification — already-verified returns 400**
- Steps: register and verify; `POST /api/auth/resend-verification`
- Expected: 400; error references "already verified"
- Tier: all

---

### 2E. Password reset

**TC-024 · Forgot-password always returns 200 (non-enumeration)**
- Steps: (a) `POST /api/auth/forgot-password { email: "nonexistent@example.com" }`; (b) repeat with registered email
- Expected: both return 200 `{ "ok": true }`; responses indistinguishable
- Tier: all

**TC-025 · Valid reset token updates password and marks email verified**
- Steps: `_create_password_reset_token(user_id)`; `POST /api/auth/reset-password { token, password: "NewPass1" }`; login with new password
- Expected: reset returns 200; login with new password succeeds; `email_verified: true`
- Tier: all

**TC-026 · Expired or reused reset token returns 400**
- Steps: create token; consume it; attempt second `POST /api/auth/reset-password` with same token
- Expected: 400
- Tier: all

**TC-027 · New password in reset must meet strength rules**
- Steps: valid reset token; `POST /api/auth/reset-password { token, password: "weak" }`
- Expected: 422 or 400; error references password requirements
- Tier: all

---

### 2F. Magic link

**TC-028 · Dev-mode magic link response includes callback URL**
- Preconditions: `IS_PROD=False` (default in TESTING), `RESEND_API_KEY=""` (default in conftest)
- Steps: register a user; `POST /api/auth/magic-link { email }`
- Expected: 200; body contains `"dev_magic_link"` key with a URL string
- Tier: all

**TC-029 · Magic link callback with valid token creates session and redirects**
- Steps: get `dev_magic_link` URL from TC-028; `GET {url}` with `follow_redirects=False`
- Expected: 302 redirect to frontend root; `set-cookie` header present
- Tier: all

**TC-030 · Magic link callback with invalid token redirects to auth error**
- Steps: `GET /api/auth/magic-link/callback?token=bogus` with `follow_redirects=False`
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-031 · Magic link token is single-use (second use redirects to error)**
- Steps: use a valid magic link once; use the same URL again
- Expected: second use redirects to `/auth?error=`
- Tier: all

**TC-032 · Magic link for unknown email returns 200 without leaking existence**
- Steps: `POST /api/auth/magic-link { email: "nobody@example.com" }`
- Expected: 200 `{ "ok": true }`; body does NOT contain `dev_magic_link`
- Tier: all

---

### 2G. OAuth

**TC-033 · Unconfigured OAuth provider returns 503**
- Preconditions: `GOOGLE_CLIENT_ID=""` (monkeypatched)
- Steps: `GET /api/auth/oauth/google/authorize`
- Expected: 503; error references "not configured"
- Tier: all

**TC-034 · /authorize creates single-use state token in DB**
- Preconditions: Google OAuth configured (monkeypatched with fake credentials)
- Steps: call `/authorize` twice
- Expected: two different `state` values; each is a distinct token
- Tier: all

**TC-035 · /callback with invalid state redirects to error**
- Steps: `GET /api/auth/oauth/google/callback?code=abc&state=bogus`
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-036 · /callback with consumed state redirects to error**
- Steps: generate valid state via `_create_oauth_state_token`; consume via `_consume_oauth_state_token`; call callback with that state
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-037 · /callback happy path creates session and redirects (patched exchange)**
- Steps: patch `_exchange_google_code` to return `{ email, name, provider_id }`; generate valid state; call callback with `follow_redirects=False`
- Expected: 302 redirect to frontend root; `set-cookie` header present
- Tier: all

**TC-038 · Unknown OAuth provider returns 404**
- Steps: `GET /api/auth/oauth/twitter/authorize`
- Expected: 404
- Tier: all

---

### 2H. Auth hardening

**TC-039 · Login lockout after N failed attempts**
- Preconditions: monkeypatch `LOGIN_LOCKOUT_MAX_ATTEMPTS=3`; registered user
- Steps: call `POST /api/auth/login` with wrong password 3 times
- Expected: third or fourth attempt returns 429; error references "too many failed sign-in attempts"
- Tier: all

**TC-040 · CSRF: mutating request without Origin in production is rejected**
- Preconditions: monkeypatch `IS_PROD=True` and `_CSRF_ALLOWED_ORIGINS={"https://app.example.com"}`; active session cookie
- Steps: `POST /api/auth/logout` with no `Origin` header
- Expected: 403
- Tier: all

**TC-041 · CSRF: mutating request with valid Origin passes**
- Preconditions: same as TC-040
- Steps: `POST /api/auth/logout` with `Origin: https://app.example.com`
- Expected: 200
- Tier: all

**TC-242 · Login failure counter resets after a successful login**
- Preconditions: monkeypatch `LOGIN_LOCKOUT_MAX_ATTEMPTS=3`; registered user with verified email
- Steps: 2 wrong logins → 1 correct login → 2 more wrong logins
- Expected: account NOT locked after second round (counter was reset by the successful login)
- Tier: all

**TC-240 · Session cookie uses SameSite=Lax attribute**
- Steps: register and log in; inspect `set-cookie` header
- Expected: header includes `samesite=lax` (case-insensitive)
- Tier: all

---

### 2I. GET /api/auth/me fields

**TC-042 · /me returns full user profile including streak metadata**
- Preconditions: logged-in user with one correct submission today (via `_insert_submission`)
- Steps: `GET /api/auth/me`
- Expected: 200; body `{ "user": { id, email, name, plan, email_verified, streak_days: 1, streak_at_risk: false } }`
- Tier: all

**TC-043 · /me streak_at_risk is true when yesterday had solve but today has none**
- Preconditions: one correct submission inserted with `submitted_at = now() - 1 day`; none today
- Steps: `GET /api/auth/me`
- Expected: `streak_at_risk: true`; `streak_days: 0`
- Tier: all

---

## 3. Catalog & Unlock Logic

**Connection rules:** Use `_make_user(client, plan=...)` to seed users. Use `_insert_progress`
to simulate solves. Catalog endpoints: `GET /api/catalog` (SQL), `GET /api/{track}/catalog`
for all other tracks.

Unit tests for `compute_unlock_state` in `unlock.py` are preferred over HTTP integration
tests where they cover the same code path.

---

### 3A. Free tier — code tracks (SQL, Python, Pandas)

> **⚡ PARAMETRIZE:** TC-044–052 all call `compute_unlock_state(...)` (unit-level pure function).
> Implement as a single parametrized test across threshold checkpoints.

**TC-044 · Fresh free user: all easy unlocked, no medium or hard**
- Preconditions: free user, zero solves
- Steps: `GET /api/catalog` (SQL); inspect state of easy/medium/hard questions
- Expected: all easy `"unlocked"`; all medium `"locked"`; all hard `"locked"`
- Tier: Free

**TC-045 · 8 easy solved → 3 medium unlocked**
- Preconditions: 8 easy SQL solved via `_insert_progress`
- Expected: first 3 medium (by order) `"unlocked"`; remaining `"locked"`
- Tier: Free

**TC-046 · 15 easy solved → 8 medium unlocked**
- Tier: Free

**TC-047 · 25 easy solved → all medium unlocked**
- Tier: Free

**TC-048 · 8 medium solved → 3 hard unlocked**
- Preconditions: 25 easy + 8 medium solved
- Tier: Free

**TC-049 · 15 medium solved → 8 hard unlocked**
- Preconditions: 25 easy + 15 medium solved
- Tier: Free

**TC-050 · 22 medium solved → hard cap enforced at 8 (not 15)**
- Note: threshold says 22→15 but FREE_HARD_CAP_CODE=8 always wins
- Tier: Free

**TC-051 · Already-solved questions retain "solved" state regardless of lock threshold**
- Preconditions: 1 easy solved
- Expected: that question has state `"solved"`, not `"unlocked"` or `"locked"`
- Tier: Free

**TC-052 · Questions beyond the unlocked prefix remain locked**
- Preconditions: 8 easy solved → 3 medium unlocked
- Expected: 4th medium question (by order) is `"locked"`
- Tier: Free

---

### 3B. Free tier — MCQ tracks (PySpark, Data Engineering, Data Modeling)

These tracks use higher unlock thresholds because MCQ requires less effort per question.
PySpark, Data Engineering, and Data Modeling all share the same MCQ profile thresholds.

> **⚡ PARAMETRIZE:** TC-053–058 implement as one parametrized test:
> ```python
> @pytest.mark.parametrize("easy_solves,medium_solves,expected_medium_count,expected_hard_count", [
>     (11, 0,  0,  0),  # TC-053: below threshold
>     (12, 0,  3,  0),  # TC-054: actually threshold is 10 easy → 3 medium for MCQ tracks
>     (20, 0,  8,  0),  # TC-055: 17 easy → 8 medium
>     (25, 0,  -1, 0),  # TC-056: -1 = all
>     (25, 15, -1, 5),  # TC-057
>     (25, 22, -1, 5),  # TC-058: cap enforced at 5
> ])
> ```
>
> **MCQ track thresholds (PySpark / Data Engineering / Data Modeling):**
> - Medium: 10 easy → 3 medium · 17 easy → 8 medium · 25 easy → all medium
> - Hard: 12 medium → 5 hard *(cap: 5)*

**TC-053 · Fresh free PySpark/DE/DM user: 9 easy solved → 0 medium unlocked (threshold is 10)**
- Expected: all medium locked

**TC-054 · 10 easy MCQ → 3 medium unlocked**

**TC-055 · 17 easy MCQ → 8 medium unlocked**

**TC-056 · 25 easy MCQ → all medium unlocked**

**TC-057 · 12 medium MCQ → 5 hard unlocked**

**TC-058 · Hard cap enforced at 5 (FREE_HARD_CAP_PYSPARK)**
- Expected: exactly 5 hard questions unlocked regardless of medium count

---

### 3C. Path shortcuts (Free)

**TC-059 · starter_done=True → all medium unlocked regardless of easy solve count**
- Steps (unit): `compute_unlock_state("free", set(), catalog, track="sql", path_state={"starter_done": True})`
- Expected: all medium unlocked; hard still locked
- Tier: Free

**TC-060 · intermediate_done=True → full hard cap unlocked**
- Steps (unit): `path_state={"intermediate_done": True}`
- Expected: up to FREE_HARD_CAP_CODE hard unlocked
- Tier: Free

**TC-061 · Both shortcuts active: all medium + full hard cap**
- `path_state={"starter_done": True, "intermediate_done": True}`
- Tier: Free

**TC-062 · Path shortcut takes precedence over threshold (higher limit wins)**
- Preconditions: 8 easy solved (→ 3 medium by threshold); `starter_done=True`
- Expected: all medium unlocked (starter_done wins)
- Tier: Free

---

### 3D. Pro and Elite

**TC-063 · Pro user: all easy + all medium + all hard, no hard cap**
- Steps (unit): `compute_unlock_state("pro", set(), catalog, track="sql")`
- Expected: all questions `"unlocked"`
- Tier: Pro

**TC-064 · Elite user: full catalog across all 9 tracks**
- Expected: same as TC-063 for all tracks
- Tier: Elite

**TC-065 · Pro — no hard cap (access all hard questions)**
- Verify SQL hard count for pro equals total hard questions in catalog (≥ 31)
- Tier: Pro

---

### 3E. Lifetime plan normalization

**TC-066 · lifetime_pro normalizes to pro for all access checks**
- Steps (unit): `compute_unlock_state("lifetime_pro", ...)` returns same result as `"pro"`
- Tier: all

**TC-067 · lifetime_elite normalizes to elite for all access checks**
- Tier: all

---

## 4. Question Access & Details

**TC-069 · Locked question returns 403**
- Preconditions: free user; no solves; pick a medium question ID
- Steps: `GET /api/questions/{medium_id}`
- Expected: 403; body has `"error"` key
- Tier: Free

**TC-070 · Unlocked question returns question detail**
- Preconditions: free user; easy question ID (always unlocked for free)
- Steps: `GET /api/questions/{easy_id}`
- Expected: 200; body contains `id`, `title`, `prompt`, `hints`, `concepts`, `schema` (SQL); does NOT contain `solution` field
- Tier: Free

**TC-071 · Solution field absent before any submission**
- Steps: `GET /api/questions/{easy_id}` for any unlocked question
- Expected: response body does not have a `"solution"` key (or `solution` is null)
- Tier: all

**TC-072 · mock_only questions absent from practice catalog**
- Preconditions: elite user (full access)
- Steps: `GET /api/catalog`; count total SQL questions
- Expected: count matches documented SQL practice total (118); no `mock_only: true` question appears.
  Total across all tracks: 876 practice questions. A mock-only question ID queried via
  `GET /api/questions/{id}` returns 404 or 403.
- Tier: Elite

**TC-073 · Python question detail includes test_cases and function_signature**
- Preconditions: pro user; easy Python question
- Steps: `GET /api/python/questions/{easy_id}`
- Expected: 200; body contains `test_cases` array and `function_signature` string
- Tier: Pro

**TC-074 · PySpark question detail includes options array, correct_option absent**
- Preconditions: free user; easy PySpark question
- Steps: `GET /api/pyspark/questions/{easy_id}`
- Expected: 200; body contains `options` array with exactly 4 entries; does NOT contain `correct_option` field
- Tier: Free

---

## 5. SQL Execution

### 5A. Run query

**TC-075 · Valid SELECT returns rows**
- Preconditions: pro user; easy SQL question
- Steps: `POST /api/run-query { question_id, query: <valid SELECT> }`
- Expected: 200; `rows` array (length ≥ 1)
- Tier: Free

**TC-076 · Row cap: result exceeding 200 rows truncated to 200**
- Steps: `POST /api/run-query { query: "SELECT * FROM sessions" }`
- Expected: `rows` array length == 200
- Tier: all

**TC-077 · SQL syntax error returns readable error message**
- Steps: `POST /api/run-query { query: "SELEKT * FORM users" }`
- Expected: body contains `"error"` with human-readable message; no stack trace exposed
- Tier: all

**TC-078 · Query execution timeout enforced (3-second limit)**
- Steps: `POST /api/run-query { query: "SELECT COUNT(*) FROM generate_series(1, 100000000)" }`
- Expected: error response with timeout indicator; completes within ~5 seconds wall-clock
- Tier: all

---

### 5B. Submit

**TC-079 · Correct answer returns verdict, solution, and quality object**
- Preconditions: pro user; easy SQL question with known correct solution
- Steps: `POST /api/submit { question_id, query: <correct>, duration_ms: 5000 }`
- Expected: 200; `correct: true`; `solution` present; `quality` object with keys `efficiency_note`, `style_notes`, `complexity_hint`, `alternative_solution`
- Tier: all

**TC-080 · Correct answer records progress in user_progress table**
- Steps: submit correct answer; query DB for `user_progress` row
- Expected: row exists with `track="sql"` and non-null `solved_at`
- Tier: all

**TC-081 · Wrong answer returns verdict without solution**
- Steps: `POST /api/submit { question_id, query: "SELECT 1 AS x" }`
- Expected: `correct: false`; `solution` absent or null; feedback message present
- Tier: all

**TC-082 · Close-miss feedback: same shape, wrong values → partial quality with style notes**
- Steps: craft query that returns same shape (column count/names) but wrong values
- Expected: `correct: false`; body contains `style_notes` (non-empty list)
- Tier: all

**TC-083 · Repeat identical wrong attempt triggers nudge message**
- Steps: submit the same wrong query twice
- Expected: second response `feedback` starts with a nudge prefix distinct from first
- Tier: all

**TC-084 · duration_ms field is accepted and stored**
- Steps: `POST /api/submit { question_id, query: <correct>, duration_ms: 12000 }`
- Expected: 200; submission record contains the provided duration
- Tier: all

**TC-243 · Submit always returns structure_correct field**
- Expected: response body always contains `structure_correct` as a boolean
- Tier: all

**TC-244 · required_concepts with enforce=true: correct result + missing concept → structure_correct: false**
- Preconditions: question with `required_concepts` and `enforce: true`; craft query producing correct data without the required technique
- Expected: `correct: true`; `structure_correct: false`; feedback references missing concept
- Tier: all

**TC-245 · required_concepts with enforce=false: correct result + missing concept → structure_correct: true with advisory**
- Expected: `correct: true`; `structure_correct: true`; `feedback` contains advisory text
- Tier: all

---

### 5C. SQL guard

> **⚡ PARAMETRIZE:** TC-085–090 test the SQL write/multi-statement guard on `/api/run-query`.

**TC-085 · DROP TABLE statement rejected**
- Expected: 400; error references write restriction; DuckDB never called
- Tier: all

**TC-086 · INSERT statement rejected**
- Tier: all

**TC-087 · UPDATE statement rejected**
- Tier: all

**TC-088 · DELETE statement rejected**
- Tier: all

**TC-089 · Multi-statement input rejected (SELECT + DROP)**
- Tier: all

**TC-090 · Valid subquery SELECT accepted**
- Expected: 200 with rows
- Tier: all

**TC-246 · Cartesian join (CROSS JOIN) rejected**
- Steps: `POST /api/run-query { query: "SELECT * FROM users CROSS JOIN orders" }`
- Expected: 400; error references join restriction
- Tier: all

**TC-247 · Un-joined multi-table query (implicit cartesian) rejected**
- Steps: `POST /api/run-query { query: "SELECT * FROM users, orders WHERE 1=1" }`
- Expected: 400
- Tier: all

**TC-248 · Query with 5 or more joins rejected**
- Expected: 400; error references join count limit
- Tier: all

**TC-249 · Dangerous DuckDB functions rejected (read_csv, read_json, glob, etc.)**
- Steps (parametrized): `read_csv`, `read_json`, `glob`, `read_parquet`, `httpfs`, `http_get`, `from_json`, `iceberg_scan`, `delta_scan`, `read_text`
- Expected: 400 for each
- Tier: all

**TC-250 · run-query on a locked question returns 403**
- Preconditions: free user; medium question
- Expected: 403 with `{error, request_id}` shape
- Tier: Free

**TC-251 · run-query on a non-existent question_id returns 404**
- Expected: 404; body has `"error"` and `"request_id"` keys
- Tier: all

**TC-281 · Cartesian join rejected by submit endpoint**
**TC-282 · Too-many-joins (≥ 5 joins) rejected by submit endpoint**
**TC-283 · Dangerous DuckDB functions rejected by submit endpoint**
- Same expectations as TC-246–249 but via `POST /api/submit`
- Tier: all

---

## 6. Python Execution

### 6A. Run code

**TC-091 · Correct code passes test cases and returns captured stdout**
- Preconditions: pro user; easy Python question
- Expected: 200; `test_results` array; at least one test passes; `print_output` present
- Tier: all

**TC-092 · Compile error returns readable error message**
- Steps: `POST /api/python/run-code { code: "def solve(x\n    return x" }`
- Expected: body contains `"error"` with human-readable message; no raw traceback with server paths
- Tier: all

**TC-093 · 5-second execution timeout enforced**
- Steps: submit code with `time.sleep(10)`
- Expected: timeout error; wall-clock completes within ~7 seconds
- Tier: all

**TC-094 · stdout captured in print_output**
- Expected: `print_output` contains the printed string
- Tier: all

---

### 6B. Submit

**TC-095 · All test cases pass → correct: true + solution revealed**
- Expected: `correct: true`; `solution` present
- Tier: all

**TC-096 · Any test case fails → correct: false + per-case breakdown**
- Expected: `correct: false`; response includes per-test breakdown
- Tier: all

---

### 6C. Python guard

> **⚡ PARAMETRIZE:** TC-097–100 test the AST guard on `/api/python/run-code`.
> TC-232–233 verify the same guard on `/api/python/submit`.

**TC-097 · import os rejected**
- Expected: 400; error references disallowed import
- Tier: all

**TC-098 · import subprocess rejected**
- Tier: all

**TC-099 · open() for file write rejected**
- Tier: all

**TC-100 · Safe import math accepted**
- Expected: not rejected by guard (200 or test failure, not guard 400)
- Tier: all

**TC-232 · import os rejected in Python submit**
**TC-233 · import subprocess rejected in Python submit**

---

## 7. Pandas Execution

**TC-101 · Correct DataFrame output → correct: true**
- Preconditions: pro user; easy Pandas question
- Expected: run-code returns at least one passing test; submit returns `correct: true` + solution
- Tier: all

**TC-102 · Wrong DataFrame values (same shape) → correct: false**
**TC-103 · Wrong DataFrame shape → correct: false**

**TC-104 · 5-second timeout enforced in Pandas sandbox**
- Expected: timeout error; completes within ~7 seconds wall-clock
- Tier: all

**TC-105 · import pandas accepted by Python guard**
- Expected: guard passes
- Tier: all

---

## 8. PySpark MCQ

**TC-106 · Correct option → correct: true + explanation always returned**
- Preconditions: free user; easy PySpark question; look up `correct_option` from catalog
- Steps: `POST /api/pyspark/submit { question_id, selected_option: <correct_option> }`
- Expected: `correct: true`; `explanation` non-null string
- Tier: all

**TC-107 · Wrong option → correct: false + explanation still returned**
- Expected: `correct: false`; `explanation` non-null (always returned regardless of outcome)
- Tier: all

**TC-108 · Invalid option index (e.g., 5) → 422**
- Tier: all

**TC-109 · No DuckDB or subprocess invoked for PySpark submission**
- Verify by response time < 200 ms; no subprocess or DuckDB query logged
- Tier: all

---

## 9. Sample Mode

**TC-110 · Anonymous user can access sample questions (no session required)**
- Preconditions: fresh client, no cookies
- Steps: `GET /api/sample/sql/easy`
- Expected: 200; question returned
- Tier: all

**TC-111 · Second call returns a different question (seen tracking)**
- Expected: second response has different `id`
- Tier: all

**TC-112 · After all 3 easy SQL samples seen → 409**
- Steps: call three times; fourth call → 409
- Tier: all

**TC-113 · POST /api/sample/sql/{difficulty}/reset clears seen state**
- Steps: exhaust samples; reset; GET again
- Expected: GET returns a question again (not 409)
- Tier: all

**TC-114 · Sample run-query executes without recording challenge progress**
- Steps: `POST /api/sample/sql/run-query { query: "SELECT 1" }`; check `user_progress`
- Expected: runs successfully; `user_progress` empty for this user
- Tier: all

**TC-115 · Sample submit returns verdict without recording challenge progress**
- Expected: verdict returned; no row inserted in `user_progress`
- Tier: all

**TC-116 · Cross-track isolation: SQL seen does not affect Python seen count**
- Steps: exhaust SQL easy samples; `GET /api/sample/python/easy`
- Expected: 200
- Tier: all

**TC-117 · All 4 dedicated sample tracks are accessible (sql, python, python-data, pyspark)**
- Expected: all four return 200 with appropriate schemas
- Note: DE, DM, Stats, ML, Experimentation samples are auto-sliced from first 3 practice
  questions per difficulty — no dedicated sample IDs; they share the standard catalog routes.
- Tier: all

**TC-118 · Sample run-code for python-data executes Pandas code**
- Expected: 200 with test results
- Tier: all

---

## 10. Learning Paths

**Connection rules:** Use `_make_user` for plan-gated tests; anon for basic list tests.

---

**TC-119 · GET /api/paths returns paths covering all 9 tracks**
- Preconditions: authenticated user (any plan)
- Steps: `GET /api/paths`
- Expected: 200; `paths` array; each path has `slug`, `title`, `topic`, `solved_count`; all 9
  track slugs represented: `sql`, `python`, `python-data`, `pyspark`, `data-engineering`,
  `data-modeling`, `statistics`, `ml-fundamentals`, `experimentation`; total count ≥ 18
  (floor check — current bank holds 46, but this assertion trips only if the loader breaks).
- Tier: all

**TC-120 · GET /api/paths/{slug} returns question list with per-question state**
- Preconditions: free user; any starter path slug
- Expected: 200; `questions` array; each question has `state` field; `completed` field present
- Tier: Free

**TC-121 · Unknown path slug returns 404**
- Tier: all

**TC-122 · Completed path shows completed: true and solved_count == total**
- Preconditions: all questions in a path solved via `_insert_progress`
- Expected: `completed: true`; `solved_count` equals `questions` length
- Tier: all

**TC-123 · In-progress path shows correct solved_count**
- Preconditions: 2 of N questions solved
- Expected: `solved_count == 2`; `completed: false`
- Tier: all

**TC-124 · solved_count in list matches individual path endpoint**
- Expected: `solved_count` matches between `GET /api/paths` and `GET /api/paths/{slug}`
- Tier: all

---

## 11. Mock Interviews (Phase 3)

**Background — three modes:**
- **`benchmark`** — fixed-shape track readiness signal (or role-based Mixed benchmark)
- **`custom`** — user-tuned: 1–5 questions, 10–90 minutes
- **`interview_loop`** — Elite-only; chain-driven iterative session; time = chain_length × 900 s

**Legacy modes (`30min`, `60min`) cannot be started** — `POST /api/mock/start` returns 400.

**Plan-tier matrix summary:**
- Free: 1 benchmark per rolling 7 days; easy only; any single track or Mixed (with role). No `custom`. No `interview_loop`.
- Pro: 3 benchmark/day + 3 custom/day (independent counters); any difficulty. Mock-only pool unlocked. No `interview_loop`.
- Elite: Unlimited (soft abuse cap). + `focus_concepts`. + `interview_loop`. + deep analytics + debrief.

**Connection rules:** All mock tests require authenticated users. Use PySpark MCQ as the
default track for simple lifecycle tests (deterministic: look up `correct_option` from catalog).
Interview Loop tests target `ml-fundamentals` hard (8 chains available there).

---

### 11A. compute_mock_access — pure unit tests

`compute_mock_access` now takes a `mode` parameter (`"benchmark"`, `"custom"`,
`"interview_loop"`) in addition to plan, track, and difficulty.

> **⚡ PARAMETRIZE:** TC-125–134G all call `compute_mock_access(...)` (unit-level).
> Implement as one or two parametrized tests grouped by logical axis.

**TC-125 · Free + benchmark + easy → can_start: True; weekly_benchmark_limit: 1**
```python
result = compute_mock_access("free", "sql", "easy", mode="benchmark", weekly_benchmark_used=0)
assert result["can_start"] is True
assert result["weekly_benchmark_limit"] == 1
assert result["weekly_benchmark_used"] == 0
```

**TC-126 · Free + benchmark + medium → plan_locked (medium/hard require Pro)**
```python
result = compute_mock_access("free", "sql", "medium", mode="benchmark")
assert result["can_start"] is False
assert result["block_reason"] == "plan_locked"
assert result["needs_upgrade"] == "pro"
```

**TC-127 · Free + benchmark + easy + weekly_used=1 → weekly_cap**
```python
result = compute_mock_access("free", "sql", "easy", mode="benchmark", weekly_benchmark_used=1)
assert result["block_reason"] == "weekly_cap"
assert result["weekly_benchmark_limit"] == 1
```

**TC-128 · Free + custom → plan_locked**
```python
result = compute_mock_access("free", "sql", "easy", mode="custom")
assert result["block_reason"] == "plan_locked"
assert result["needs_upgrade"] == "pro"
```

**TC-129 · Free + benchmark + hard → plan_locked; needs_upgrade: pro**

**TC-130 · Pro + benchmark + hard + daily_used=2 → can_start: True; daily_limit: 3**
```python
result = compute_mock_access("pro", "sql", "hard", mode="benchmark", daily_benchmark_used=2)
assert result["can_start"] is True
assert result["daily_limit"] == 3
assert result["daily_used"] == 2
```

**TC-131 · Pro + benchmark + hard + daily_used=3 → daily_cap**
```python
result = compute_mock_access("pro", "sql", "hard", mode="benchmark", daily_benchmark_used=3)
assert result["block_reason"] == "daily_cap"
assert result["needs_upgrade"] == "elite"
```

**TC-132 · Elite + benchmark + hard → can_start: True; daily_limit: None (unlimited)**

**TC-133 · Pro + company_filter → plan_locked; needs_upgrade: elite**
```python
result = compute_mock_access("pro", "sql", "easy", mode="benchmark", company_filter=True)
assert result["block_reason"] == "plan_locked"
assert result["needs_upgrade"] == "elite"
```

**TC-134 · Elite + company_filter → can_start: True**

**TC-134B · Pro + custom + daily_custom_used=2 → can_start: True; daily_limit: 3**
- Note: `benchmark` and `custom` caps are independent counters on Pro.

**TC-134C · Pro + custom + daily_custom_used=3 → daily_cap**

**TC-134D · Free + interview_loop → plan_locked (Elite-only)**

**TC-134E · Pro + interview_loop → plan_locked (Elite-only)**

**TC-134F · Elite + interview_loop → can_start: True**

**TC-134G · Benchmark cap and custom cap are independent counters**
```python
# Benchmark capped but custom still available
bench_capped  = compute_mock_access("pro", "sql", "easy", mode="benchmark", daily_benchmark_used=3)
custom_ok     = compute_mock_access("pro", "sql", "easy", mode="custom",    daily_benchmark_used=3, daily_custom_used=0)
assert bench_capped["can_start"] is False
assert custom_ok["can_start"] is True
```

---

### 11B. Session lifecycle

> **Valid `mode` values:** `"benchmark"` · `"custom"` · `"interview_loop"`
>
> `"30min"` and `"60min"` are legacy — `/start` returns 400 for them (TC-181).
>
> **`company_filter` type:** `string | null` (e.g. `"Meta"`) — SQL only.
> **`focus_concepts` type:** `string[] | null` (1–3 items) — Elite only.
> **`role` param:** required for `track: "mixed"` — `"data_analyst"`, `"data_engineer"`,
> `"analytics_engineer"`, `"data_scientist"`.

**TC-135 · POST /api/mock/start returns correct structure for benchmark mode**
- Preconditions: Pro user; PySpark easy questions available
- Steps: `POST /api/mock/start { mode: "benchmark", track: "pyspark", difficulty: "easy" }`
- Expected: 201; body has `session_id` (UUID), `questions` array, `time_limit_s`,
  `focus_fallback` (bool); questions follow the track-specific benchmark shape
- Tier: Pro

**TC-136 · Custom mode: num_questions and time_minutes honored**
- Steps: `POST /api/mock/start { mode: "custom", track: "pyspark", difficulty: "easy", num_questions: 3, time_minutes: 30 }`
- Expected: 201; `questions` array length == 3; `time_limit_s == 1800`
- Tier: Pro

**TC-136B · Benchmark mode uses track-specific shape**
- Steps: start benchmark for PySpark; verify question types match PySpark benchmark template
- Tier: Pro

**TC-136C · Statistics benchmark enforces 1 numerical + 2 conceptual**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "statistics", difficulty: "easy" }`
- Expected: 201; among the questions, exactly 1 has `subtype: "numerical"` and ≥ 2 have `subtype: "conceptual"`
- Tier: Pro

**TC-136D · Mixed benchmark requires role**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "mixed" }` with no `role`
- Expected: 400; error references role requirement
- Tier: Pro

**TC-136E · ML benchmark includes debug and predict_output question types when available**
- Tier: Pro

**TC-137 · num_questions out of range (0 or 6) → 400**
- Steps: `POST /api/mock/start { mode: "custom", ..., num_questions: 0 }` and `num_questions: 6`
- Expected: 400 (not Pydantic 422); `detail` references 1–5 constraint
- Tier: Elite

**TC-138 · POST /api/mock/{id}/submit mid-session returns verdict without solution**
- Preconditions: active session; look up correct_option for first question
- Steps: `POST /api/mock/{id}/submit { question_id, selected_option }`
- Expected: 200; `correct: true/false`; `solution` absent or null; `follow_up_injected` absent (this is not Interview Loop)
- Tier: Pro

**TC-139 · POST /api/mock/{id}/finish returns full summary with solutions revealed**
- Steps: `POST /api/mock/{id}/finish`
- Expected: 200; `solved_count`, `total_count`, `time_used_s`; each question in `questions` has non-null `solution`
- Tier: Pro

**TC-140 · GET /api/mock/{id} returns session state for reload recovery**
- Expected: 200; session metadata and current state; answered questions tracked
- Tier: Pro

**TC-141 · GET /api/mock/history returns last 20 sessions**
- Preconditions: Elite user with 21 completed mock sessions inserted via DB
- Expected: `sessions` array length == 20
- Tier: all

**TC-142 · Session cannot be submitted to after finish**
- Steps: finish session; then submit a question
- Expected: 404 or 400
- Tier: Pro

**TC-171 · DELETE /api/mock/{id} within 2 minutes discards session**
- Expected: 204; subsequent GET returns 404
- Tier: Pro

**TC-252 · DELETE /api/mock/{id} more than 2 minutes after start → 403**
- Preconditions: session with `started_at` manipulated to >2 min ago via DB
- Expected: 403
- Tier: Pro

**TC-253 · DELETE /api/mock/{id} on completed session → 403**
- Expected: 403
- Tier: Pro

**TC-254 · Different user submitting to another user's session → 404**
- Expected: 404 (ownership is opaque — not "Forbidden")
- Tier: all

**TC-255 · GET /api/mock/{id} returns 404 for another user's session**
- Tier: all

**TC-256 · Submitting a question not in the session → 400**
- Tier: all

**TC-257 · Finish is idempotent (second call returns 200)**
- Expected: both calls return 200; payloads equivalent
- Tier: all

**TC-172 (mock) · Blank code submit returns 422 and does not consume question slot**
- Preconditions: active session with a numerical statistics question
- Steps: `POST /api/mock/{id}/submit { question_id, code: "" }` (blank code)
- Expected: 422; question slot NOT consumed; subsequent valid submit still works
- Tier: Pro

**TC-173 (mock) · Missing MCQ option returns 422 and does not consume question slot**
- Preconditions: active session with MCQ question
- Steps: `POST /api/mock/{id}/submit { question_id }` (no selected_option field)
- Expected: 422; question still available to answer
- Tier: all

**TC-174 (mock) · Second submit after correct answer returns 409**
- Steps: submit correct answer; submit again
- Expected: second call returns 409; `error` references already answered
- Tier: all

**TC-175 (mock) · Second submit after wrong answer returns 409**
- Same as TC-174 but first answer is wrong
- Expected: 409 on second attempt
- Tier: all

**TC-176 (mock) · Blank submit does NOT block subsequent real submit**
- Preconditions: active session; submit blank code (422 rejected); then submit valid code
- Expected: second submit succeeds (422 is a guard rejection, not a slot consumption)
- Tier: Pro

**TC-181 · Legacy mode "30min" start returns 400**
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "easy" }`
- Expected: 400; error references invalid mode
- Tier: all

**TC-182 · Mixed custom without role returns 400**
- Steps: `POST /api/mock/start { mode: "custom", track: "mixed", ..., num_questions: 1 }` (no `role`)
- Expected: 400; error references role requirement
- Steps 2: same with `role: "data_analyst"`
- Expected: 201
- Tier: Pro

---

### 11C. Plan gates — HTTP level

**TC-143 · Free user starting a medium/hard mock → 403**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "pyspark", difficulty: "hard" }`
- Expected: 403; `error` references Pro requirement
- Tier: Free

**TC-144 · Pro user starting a hard mock → 201**
- Tier: Pro

**TC-145 · Elite user starting a hard mock → 201**
- Tier: Elite

---

### 11D. Daily limits — HTTP level

**TC-146 · Free user: custom mode returns 403 (plan_locked, not daily_cap)**
- Preconditions: free user
- Steps: `POST /api/mock/start { mode: "custom", ... }`
- Expected: 403; `error` references Pro requirement (Free cannot use custom at all)
- Tier: Free

**TC-147 · Pro user: 4th custom same day is blocked**
- Preconditions: 3 custom sessions already completed today (insert via DB)
- Steps: `POST /api/mock/start { mode: "custom", ... }`
- Expected: 403; `error` references daily limit and Elite upgrade
- Tier: Pro

**TC-148 · Elite user: 4th custom same day is allowed (unlimited)**
- Preconditions: 3 custom sessions completed today
- Steps: same start request
- Expected: 201
- Tier: Elite

---

### 11E. Company filter (Elite, SQL only)

**TC-149 · Non-Elite user with company_filter → 403**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "sql", difficulty: "easy", company_filter: "Meta" }`
- Expected: 403; error references Elite requirement
- Tier: Free/Pro

**TC-150 · Elite user with valid company filter → session created**
- Expected: 201; `questions` array contains only questions tagged with "Meta"
- Tier: Elite

---

### 11F. Focus mode (Elite)

**TC-151 · Non-Elite user with focus_concepts → 403**
- Steps: `POST /api/mock/start { ..., focus_concepts: ["window functions"] }`
- Expected: 403
- Tier: Free/Pro

**TC-152 · Elite user, >3 focus_concepts → 422**
- Expected: 422; references max 3 items
- Tier: Elite

**TC-153 · Elite user, 1–3 focus_concepts → session created**
- Tier: Elite

**TC-154 · Focus fallback when pool too small → focus_fallback: true in response**
- Steps (unit): use `_select_questions` with a concept matching fewer questions than requested
- Expected: `focus_fallback == True`; `selected` contains questions (full pool used)
- Tier: Elite

**TC-155 · Empty focus_concepts [] treated same as None (no filtering)**
- Expected: full pool used; `focus_fallback == False`
- Tier: Elite

**TC-258 · Multiple focus_concepts use OR logic**
- Expected: question matching either concept is included; OR not AND
- Tier: Elite

**TC-259 · Focus concept matching is case-insensitive**
- Expected: `focus_concepts=["Window Functions"]` matches `"window functions"` tagged questions
- Tier: Elite

**TC-260 · lifetime_elite can use focus_concepts**
- Expected: 201 (not 403)
- Tier: lifetime_elite

**TC-261 · focus_fallback is always present in /start response**
- Expected: response contains `"focus_fallback"` key even when no focus filter applied (value is `false`)
- Tier: Elite

---

### 11G. Mock pool and freshness

**TC-156 · mock_only questions appear in Pro/Elite sessions**
- Verify via unit test patching the pool: questions drawn from `get_mock_questions_by_difficulty()` include mock-only IDs
- Tier: Pro/Elite

**TC-157 · Freshness scoring avoids recently-seen questions when alternatives exist**
- Steps (unit): seed `mocked_ids` with recently-seen question IDs; call `_select_questions`
- Expected: selected questions do not include recently-seen IDs (when pool is large enough)
- Tier: Pro/Elite

---

### 11H. Session debrief (Elite)

> **⚡ PARAMETRIZE:** TC-158–163 as one parametrized test:
> ```python
> @pytest.mark.parametrize("plan,correct,total,expect_null,expected_headline", [
>     ("elite", 1, 1, False, "Perfect"),
>     ("elite", 0, 1, False, "Tough"),
>     ("elite", 2, 3, False, "Solid"),
>     ("elite", 1, 3, False, "Partial"),
>     ("pro",   1, 1, True,  None),
>     ("free",  1, 1, True,  None),
> ])
> ```

**TC-158 · 1/1 correct → "Perfect" headline**
**TC-159 · 0/1 correct → "Tough" headline**
**TC-160 · 2/3 correct → "Solid" headline (≥67%)**
**TC-161 · 1/3 correct → "Partial" headline (34–66%)**
**TC-162 · Pro user: debrief is null**
**TC-163 · Free user: debrief is null**

**TC-164 · debrief contains patterns and priority_action fields**
- Expected: `debrief.patterns` is an array (possibly empty); `debrief.priority_action` present
- Tier: Elite

**TC-172 (debrief) · Reasoning-track debrief uses no code-centric language**
- Preconditions: Elite; complete a session using DE/DM/ML/Exp questions (MCQ only, no code execution)
- Expected: `debrief` does not contain terms like "query", "code", "execute", "syntax"
- Tier: Elite

**TC-173 (debrief) · Reasoning-track with no weak concepts uses reasoning-copy fallback**
- Preconditions: Elite; all questions answered correctly for a reasoning track session
- Expected: `debrief.priority_action` references review/deeper-practice language, not weak-concept language
- Tier: Elite

**TC-174 (debrief) · Statistics all-conceptual session uses reasoning language**
- Tier: Elite

**TC-175 (debrief) · Statistics session with numerical question uses executable language**
- Tier: Elite

**TC-262 · debrief contains all documented keys**
- Expected: `headline`, `patterns`, `priority_action`, `priority_path_slug`, `priority_path_title`, `priority_question_ids`
- Tier: Elite

**TC-263 · Perfect session with ≤50% time used → time-to-spare headline variant**
**TC-264 · Session using nearly all time → time-pressure headline variant**

**TC-265 · patterns includes time-sink entry when one question dominates time (>55%)**
- Note: single-question sessions do NOT generate a time-sink pattern

**TC-266 · priority_path_slug is present when weak concept maps to a learning path**
**TC-267 · priority_question_ids excludes questions already in the session**

---

### 11I. Mock analytics (Elite)

**TC-165 · GET /api/mock/analytics returns 200 for Elite**
- Expected: 200; body contains `total_sessions`, `sessions_last_30d`, `avg_score`, `best_score`,
  `avg_time_used_pct`, `score_trend`, `top_concepts`, `weak_concepts`, `track_breakdown`,
  `difficulty_breakdown`, `mode_breakdown`, `loop_summary`
- Notes: `weak_concepts` threshold is **< 60% accuracy and ≥ 3 attempts** (different from
  dashboard insights which uses < 50%); `top_concepts` capped at 5; `weak_concepts` capped at 3;
  `score_trend` is last 10 sessions in chronological order
- Tier: Elite

**TC-165B · Analytics separates benchmark from drills in mode_breakdown**
- Preconditions: Elite; seed one benchmark session, one custom session, one interview_loop session via DB
- Expected: `mode_breakdown` contains `{"benchmark": 1, "custom": 1, "interview_loop": 1, "drill": ...}` (drill count depends on legacy data)
- Tier: Elite

**TC-166 · GET /api/mock/analytics returns 403 for Pro**
**TC-167 · GET /api/mock/analytics returns 403 for Free**
**TC-168 · lifetime_elite can access mock analytics**

**TC-183 · Analytics includes loop_summary for Interview Loop sessions**
- Preconditions: Elite; insert completed interview_loop session with follow-up questions having `follow_up_dimension` values
- Expected: `loop_summary.sessions == 1`; `loop_summary.per_dimension_performance` contains entries for each dimension
- Tier: Elite

---

### 11J. Solution visibility contract

**TC-169 · solution absent during session submit**
**TC-170 · solution present for all questions after finish**

---

### 11K. Interview Loop (Elite only)

**TC-177 · Elite + interview_loop + ml-fundamentals hard → session with chain; time = chain_len × 900**
- Expected: 201; `questions` has ≥ 2 entries (parent + ≥ 1 follow-up);
  `time_limit_s == len(questions) * 900`;
  `questions[0].follow_up_dimension` is null (parent); each child has non-null `follow_up_dimension`
- Tier: Elite

**TC-178 · Pro user + interview_loop → 403**
- Expected: 403; error references Elite requirement
- Tier: Pro

**TC-179 · All chains consumed → 409 pool_exhausted**
- Preconditions: insert all ML hard chain parent IDs into `mock_chain_consumption` for this user
- Expected: 409; body contains `pool_exhausted: true` or `"exhausted"` in error
- Tier: Elite

**TC-180 · Discard Interview Loop session within 2 min → chain reclaimed; restart succeeds**
- Steps: start loop; `DELETE /api/mock/{id}` (within 2 min → 204); start loop again
- Expected: second start succeeds (chain was reclaimed from `mock_chain_consumption`)
- Tier: Elite

---

## 12. Dashboard & Insights

**Connection rules:** Use `_make_user` for plan seeding. Use `_insert_submission` and
`_insert_progress` for deterministic data. `GET /api/dashboard/insights` is cached 60s
per user in-process — cleared between test functions by `isolated_state`.

---

### 12A. Dashboard endpoint

**TC-172 (dashboard) · GET /api/dashboard returns track stats for code tracks**
- Preconditions: pro user with solves in sql, python, python-data, pyspark (via `_insert_progress`)
- Steps: `GET /api/dashboard`
- Expected: 200; `tracks` contains entries for `sql`, `python`, `python-data`, `pyspark`;
  each has `by_difficulty` with `easy`, `medium`, `hard` sub-objects having `solved` and `total`
- Note: The dashboard router handles all 9 tracks (including DE, DM, Stats, ML, Exp).
  TC-172 verifies at minimum the 4 code tracks; additional reasoning track solves would appear
  under their respective slugs.
- Tier: all

**TC-173 · python-data key is normalized (not python_data)**
- Expected: track key is `"python-data"` (hyphen)
- Tier: all

**TC-174 · Unauthenticated GET /api/dashboard returns 401**
- Tier: all

**TC-175 · recent_activity is present and capped at 10 entries**
- Expected: `recent_activity` array present; capped at 10 even when >10 submissions exist
- Tier: all

**TC-268 · concepts_by_track reflects solved question concepts**
- Expected: `concepts_by_track` present; non-empty after at least one concept-tagged solve
- Tier: all

---

### 12B. Insights — basic per-track stats

**TC-176 (insights) · GET /api/dashboard/insights returns per_track for code tracks**
- Preconditions: pro user with solves in sql, python, python-data, pyspark
- Steps: `GET /api/dashboard/insights`
- Expected: 200; `per_track` has entries for those tracks; each has `solve_count`,
  `median_solve_seconds`, `accuracy_pct`
- Note: Insights cover all 9 tracks via `tracks.TRACKS`; this TC verifies the 4 code tracks.
- Tier: all

**TC-177 · median_solve_seconds is null when no correct submissions**
**TC-178 · accuracy_pct is computed as correct/total submissions**
**TC-179 · cross_track_insight is null when gap < 60 seconds between tracks**
**TC-180 · cross_track_insight is a non-null string when gap ≥ 60 seconds**
**TC-181 · streak_days reflects consecutive days with correct submissions**

---

### 12C. Insights — weakest concepts

**TC-182 · Concept with ≥ 3 attempts appears in weakest_concepts**
**TC-183 · Concept with < 3 attempts excluded**
**TC-184 · At most 3 weakest concepts returned**

**TC-185 · Accuracy < 30% → summary contains "highest-priority gap"**
**TC-186 · Accuracy < 50% → summary contains "isn't sticking"**
**TC-187 · Accuracy 50–69% → summary contains "breaks under new angles"**
**TC-188 · Accuracy ≥ 70% → summary contains "not fully consistent"**

**TC-189 · recommended_question_ids excludes already-solved questions**
**TC-190 · Free user: recommended_question_ids limited to easy questions**
**TC-191 · Pro/Elite: recommended_question_ids may include medium/hard**

---

### 12D. Elite-only insights gates

**TC-192 · Free user: readiness_scores null, study_plan null**
**TC-193 · Pro user: readiness_scores null, study_plan null**

**TC-194 · Elite user: readiness_scores present for all 9 tracks**
- Expected: `readiness_scores` is an object with keys for all 9 track slugs:
  `sql`, `python`, `python-data`, `pyspark`, `data-engineering`, `data-modeling`,
  `statistics`, `ml-fundamentals`, `experimentation`; each has `score` (int 0–100),
  `label` (string), `components` with `practice`, `mock_accuracy`, `concept_strength`
- Tier: Elite

**TC-195 · Elite user: study_plan present (3–5 items)**
**TC-196 · study_plan action types are valid values**
- Valid `type` values: `concept_drill`, `learning_path`, `mock_session`, `practice_hard`
**TC-197 · No duplicate (type, track) pairs in study_plan**
**TC-295 · study_plan items are ordered by priority ascending**
**TC-296 · cta_href patterns: concept_drill starts with /practice/; learning_path contains /learn/**

---

### 12E. Readiness score components (unit tests)

**TC-198 · Practice coverage: 0 solves → 0 pts**
**TC-199 · Practice coverage: 100% easy + 100% medium + 40% hard → ~40 pts**
**TC-200 · Mock accuracy: no sessions → 0 pts**
**TC-201 · Readiness label thresholds: <40→"Early stage" · 40–64→"Building" · 65–79→"Getting there" · 80–89→"Interview ready" · ≥90→"Strong"**

---

### 12F. Caching

**TC-202 · Second call within 60s returns cached payload**
**TC-203 · Cache is per-user (different users do not share cache)**

---

## 13. Submission History

**TC-204 · GET /api/submissions returns history for a question**
- Preconditions: 3 submissions for question Q (track=sql) via `_insert_submission`
- Steps: `GET /api/submissions?track=sql&question_id={Q}`
- Expected: 200; array of 3 items; each has `is_correct`, `submitted_at`, `feedback`
- Tier: all

**TC-205 · limit param restricts returned records**
**TC-206 · Empty history returns empty array (not 404)**
**TC-207 · Unauthenticated returns 401**

---

## 14. Payments & Webhooks

**Connection rules:** Mock the Razorpay HTTP client entirely via `monkeypatch` or `patch`.
Do not call the real Razorpay API.

---

### 14A. Create order

**TC-208 · plan=pro → subscription response**
- Expected: body has `subscription_id` (non-null), `order_id: null`, `is_subscription: true`, `key_id`, `amount`, `currency: "INR"`
- Tier: Free → Pro

**TC-209 · plan=lifetime_pro → order response (one-time); amount == 1199900 (₹11,999 in paise)**
**TC-210 · plan=lifetime_elite → order response; amount == 1999900 (₹19,999 in paise)**
**TC-211 · Invalid plan → 400 (not 422)**
**TC-212 · Unauthenticated → 401**
**TC-271 · plan=free → 400**
**TC-272 · Downgrade attempt → 400; error references invalid upgrade path**
**TC-273 · Razorpay not configured → 503**
**TC-274 · Multiple create-order calls → Razorpay customer created only once (deduplication)**

---

### 14B. Verify payment

**TC-213 · Valid HMAC for one-time order → plan upgraded immediately**
**TC-214 · Valid HMAC for subscription → plan upgraded**
**TC-215 · Invalid HMAC signature → 400; plan NOT changed**
**TC-216 · Idempotent re-verification → 200 no-op**

---

### 14C. Webhook

**TC-217 · payment.captured event with valid signature → plan applied**
**TC-218 · subscription.activated → plan upgraded**
**TC-219 · subscription.cancelled → plan downgraded to free**

**TC-220 · subscription.cancelled on lifetime_elite → plan NOT downgraded**
**TC-221 · subscription.cancelled on lifetime_pro → plan NOT downgraded**

**TC-222 · Invalid webhook signature → 400**
**TC-223 · Duplicate webhook event → idempotent 200 no-op**

**TC-275 · subscription.charged → plan preserved (monthly renewal)**
**TC-276 · subscription.halted → plan downgraded to free**
**TC-277 · Webhook with unknown user_id → graceful 200 no crash**
**TC-278 · payment.failed event → ignored, plan unchanged**
**TC-279 · Invalid target_plan in webhook payload → silently ignored**

---

## 15. Rate Limiting

**TC-224 · Global rate limit: exceeding threshold → 429**
**TC-225 · Auth rate limit: login attempts trigger auth-specific limit**
**TC-226 · Auth token-issue rate limit: magic-link shares separate bucket**
**TC-227 · Localhost bypasses global rate limit in non-production**
**TC-228 · Rate limiter state is isolated between test modules**
**TC-241 · Rate-limit headers present on every response** (`X-RateLimit-Limit`, `X-RateLimit-Remaining`)
**TC-280 · Redis connection failure → rate limiter falls back to in-memory**

---

## 16. Security Guards

### 16A. SQL guard — submit endpoint variants

> Primary SQL guard tests live in §5C (TC-085–090, TC-246–249) for `/api/run-query`.
> TC-281–283 verify the same guard on `/api/submit`.

**TC-281 · Cartesian join rejected by submit endpoint**
**TC-282 · Too-many-joins (≥ 5 joins) rejected by submit endpoint**
**TC-283 · Dangerous DuckDB functions rejected by submit endpoint**

---

### 16B. Python guard — submit endpoint variants

> Primary Python guard tests live in §6C (TC-097–100) for `/api/python/run-code`.

**TC-232 · import os rejected in Python submit**
**TC-233 · import subprocess rejected in Python submit**

---

### 16C. CSRF

**TC-237 · Production mode: mutating request without Origin → 403**
**TC-238 · Production mode: mutating request with valid Origin → allowed**
**TC-239 · Non-production mode: mutating request without Origin → allowed (CSRF disabled)**

---

## 17. Content & Static Integrity

**Connection rules:** Read-only integrity checks. No HTTP calls. Mark the module with
`pytestmark = pytest.mark.usefixtures("isolated_state")`.

---

### 17A. SQL expected_query execution

**TC-289 · All SQL challenge expected_query execute without error**
- Steps (parametrized over every entry in `questions.py` catalog): execute `question["expected_query"]` via `database.execute_query()`
- Expected: no exception raised
- Tier: static

**TC-290 · All SQL sample expected_query execute without error**
- Tier: static

---

### 17B. Learning path integrity

These tests live in `test_paths_quality.py` and verify the 46-path bank against the
content-authoring.md rule set.

**Rule 1 — Required fields and uniqueness**
- Every path has `slug`, `title`, `topic`, `role`, `type`, `questions`, `patterns`, `focus_concepts`, `recommended_after`
- All slugs are unique across the entire bank
- Each slug matches its JSON filename stem

**Rule 2 — Type and starter invariants**
- `role` is one of `"data_analyst"`, `"data_engineer"`, `"analytics_engineer"`, `"data_scientist"`, `"generalist"`
- Each track has exactly one path of type `"starter"`
- `"intermediate"` and `"advanced"` types are uncapped

**Rule 3 — Patterns non-empty and registered**
- Every path has ≥ 1 entry in `patterns`; each pattern name resolves in the concept-family registry for its track

**Rule 4 — focus_concepts non-empty and taxonomy-consistent**
- Every path has ≥ 1 focus concept; for taxonomy-validated tracks, each focus concept resolves to a family

**Rule 5 — Question tag alignment**
- Questions in a path have ≥ 1 concept tag matching the path's `focus_concepts`

**Rule 6 — recommended_after graph is acyclic and slug-valid**
- All slugs in `recommended_after` reference valid existing path slugs; no cycles

**TC-293 · All question IDs referenced in any path exist in their track's catalog**
- Steps: for each path, load its `questions` array; look up each ID in the track's catalog loader
- Expected: no missing IDs

**TC-294 · Each path's slug matches its JSON filename**

**TC-291 · Path coverage floor**
- Steps: load all paths via `path_loader.get_all_paths()`
- Expected: count ≥ 18 (sanity floor); all 9 track slugs represented; current bank target: 46
- Note: test does NOT assert a hardcoded total — it verifies the structural properties above.
  The 46 breakdown is: SQL 9, Python 6, Pandas 5, PySpark 5, DE 3, DM 5, Stats 3, ML 5, Exp 5.

**TC-292 · Each of the 9 tracks has exactly one starter path**
- Steps: group paths by `(topic, type)` where `type == "starter"`
- Expected: exactly one entry per track for the starter type; 9 starter paths total

---

## 18. Data Engineering Track

**File:** `backend/tests/test_19_data_engineering.py`
**Track slug:** `data-engineering` | **Eval kind:** `mcq` | **Unlock profile:** `mcq`
**Format:** conceptual / scenario / debug (MCQ response; no code execution)
**Catalog endpoint:** `GET /api/data-engineering/catalog`

---

**TC-DE-01 · Catalog returns easy/medium/hard groups**
- Preconditions: free user
- Expected: 200; `groups` set == `{"easy", "medium", "hard"}`

**TC-DE-02 · Free user — all easy questions unlocked**

**TC-DE-03 · Free user — medium questions locked (no easy solves)**

**TC-DE-04 · Pro user — all questions unlocked**

**TC-DE-05 · Question detail includes options, prompt, hints, concepts**
- Expected: 200; body has `options` (4 entries), `prompt`, `hints`, `concepts`; does NOT have `correct_option`

**TC-DE-06 · Locked question returns 403**

**TC-DE-07 · Correct option → correct: true + explanation returned**
- Steps: `POST /api/data-engineering/submit { question_id, selected_option: <correct_option> }`
- Expected: `correct: true`; `explanation` non-null

**TC-DE-08 · Wrong option → correct: false + explanation returned**

**TC-DE-09 · Correct submit records progress**
- Expected: row exists in `user_progress` with `topic="data-engineering"`

**TC-DE-10 · Free user MCQ unlock: 10 easy → 3 medium unlocked**
- Steps (unit): `compute_unlock_state("free", solved_ids, catalog, track="data-engineering")`
- Expected: first 3 medium questions unlocked after 10 easy solves

**TC-DE-11 · Hard cap enforced at 5 for free users**

**TC-DE-12 · Pro user: mock session can include DE questions**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "data-engineering", difficulty: "easy" }`
- Expected: 201

**TC-DE-13 · Locked MCQ options hidden: options and correct_option absent from locked question response**
- Preconditions: free user; locked medium question
- Steps: `GET /api/data-engineering/questions/{medium_id}`
- Expected: 200 with `locked: true`; `options` absent; `correct_option` absent; prompt visible

**TC-DE-14 · Submit to locked MCQ question returns 403**

**TC-DE-15 · Question detail exposes eval_kind="mcq"**
- Expected: `eval_kind: "mcq"` in response
- (or inferred from response shape matching MCQ pattern)

**TC-DE-16 · Invalid option index → 422**

**TC-DE-17 · Catalog total matches documented count: 30 easy + 35 medium + 26 hard = 91 practice**
- Steps (unit): count questions from `data_engineering_questions.get_questions_by_difficulty()`
  where `mock_only` is falsy
- Expected: 30 easy, 35 medium, 26 hard

**TC-DE-18 · Mock pool includes DE mock-only questions for Pro/Elite**
- Expected: `get_mock_questions_by_difficulty()` returns 34 medium + 76 hard (mock-only)

**TC-DE-19 · DE has in_mixed_mock=false — DE questions do not appear in Mixed mock pool**

**TC-DE-20 · Free user attempting to start DE mock at medium difficulty → 403**

---

## 19. Data Modeling Track

**File:** `backend/tests/test_20_data_modeling.py`
**Track slug:** `data-modeling` | **Eval kind:** `mcq` | **Unlock profile:** `mcq`
**Format:** conceptual / scenario / debug (MCQ; no code execution)
**Catalog endpoint:** `GET /api/data-modeling/catalog`

Tests mirror the Data Engineering pattern (TC-DM-01 through TC-DM-20). Key differences:
- Practice totals: 25 easy + 31 medium + 25 hard = 81 practice
- Mock-only: 46 medium + 51 hard = 97 mock-only
- Same MCQ unlock thresholds as DE (10/17/25 easy; 12 medium hard cap 5)
- `in_mixed_mock=false`

**TC-DM-01 · Catalog returns easy/medium/hard groups**
**TC-DM-02 · Free user — all easy unlocked**
**TC-DM-03 · Free user — medium locked without solves**
**TC-DM-04 · Pro user — all unlocked**
**TC-DM-05 · Question detail has MCQ fields; correct_option absent**
**TC-DM-06 · Locked question returns 403**
**TC-DM-07 · Correct submit → correct: true + explanation**
**TC-DM-08 · Wrong submit → correct: false + explanation**
**TC-DM-09 · Correct submit records progress with topic="data-modeling"**
**TC-DM-10 · 10 easy → 3 medium unlocked (MCQ threshold)**
**TC-DM-11 · Hard cap 5 for free users**
**TC-DM-12 · Pro user can start DM benchmark session**
**TC-DM-13 · Locked question: options + correct_option hidden; prompt visible**
**TC-DM-14 · Submit to locked question → 403**
**TC-DM-15 · Catalog totals: 25 easy + 31 medium + 25 hard = 81 practice**
**TC-DM-16 · Mock pool: 46 medium + 51 hard mock-only**
**TC-DM-17 · in_mixed_mock=false — DM absent from Mixed mock pool**
**TC-DM-18 · Invalid option index → 422**
**TC-DM-19 · Free user medium benchmark → 403**
**TC-DM-20 · Unauthenticated catalog returns 200 with all-locked medium/hard**

---

## 20. Statistics Track (dual-subtype)

**File:** `backend/tests/test_30_statistics.py`
**Track slug:** `statistics` | **Eval kind:** `mixed` | **Unlock profile:** `code`
**Format:** `conceptual` (MCQ response) or `numerical` (Python code execution)
**Catalog endpoint:** `GET /api/statistics/catalog`

This is the only track with a dual-subtype model:
- `subtype: "conceptual"` questions are answered like MCQ tracks (select an option)
- `subtype: "numerical"` questions are answered like Python tracks (submit Python code)
- The catalog exposes a `subtype` field on every question entry

---

**TC-ST-01 · Catalog returns all three difficulty groups**
**TC-ST-02 · Free user — all easy unlocked**
**TC-ST-03 · Free user — medium locked without easy solves**
**TC-ST-04 · Pro user — all unlocked**
**TC-ST-05 · Catalog question entries expose subtype field (conceptual or numerical)**
- Expected: every question in the catalog response has `subtype` in `{"conceptual", "numerical"}`

**TC-ST-06 · Both subtypes exist across the easy pool**
- Expected: at least one `"conceptual"` and one `"numerical"` question in easy difficulty

**TC-ST-07 · Conceptual question detail has options (4 entries); no test_cases**
- Preconditions: pro user; easy conceptual question
- Expected: `options` array with 4 items; `test_cases` absent

**TC-ST-08 · Numerical question detail has test_cases and function_signature; no options**
- Preconditions: pro user; easy numerical question
- Expected: `test_cases` array; `function_signature` string; `options` absent

**TC-ST-09 · Correct conceptual answer → correct: true + explanation**
**TC-ST-10 · Wrong conceptual answer → correct: false + explanation**

**TC-ST-11 · Correct numerical code → correct: true + solution**
- Steps: `POST /api/statistics/submit { question_id, code: <correct>, subtype: "numerical" }`
- Expected: `correct: true`; `solution` present

**TC-ST-12 · Wrong numerical code → correct: false + per-test breakdown**

**TC-ST-13 · Subtype mismatch: submitting MCQ option to a numerical question → 422**
- Steps: `POST /api/statistics/submit { question_id: <numerical_id>, selected_option: 0 }`
- Expected: 422; error references subtype mismatch

**TC-ST-14 · Subtype mismatch: submitting code to a conceptual question → 422**

**TC-ST-15 · Correct submit records progress for both subtypes**
- Expected: `user_progress` row with `topic="statistics"` regardless of subtype

**TC-ST-16 · Statistics uses code-track unlock thresholds (not MCQ thresholds)**
- Preconditions: free user; 8 easy solved
- Expected: first 3 medium unlocked (code profile: 8 easy → 3 medium, NOT the MCQ 10-easy threshold)

**TC-ST-17 · Hard cap is 8 (code profile)**
- Expected: exactly 8 hard questions unlocked for free user at maximum threshold

**TC-ST-18 · Benchmark session enforces 1 numerical + 2 conceptual**
- Steps: `POST /api/mock/start { mode: "benchmark", track: "statistics", difficulty: "easy" }`
- Expected: among questions, `subtype: "numerical"` count ≥ 1, `subtype: "conceptual"` count ≥ 2

**TC-ST-19 · Numerical question: 5-second timeout enforced in sandbox**
**TC-ST-20 · Conceptual question: response time < 200 ms (no subprocess invoked)**

**TC-ST-21 · Catalog totals: 31 easy + 43 medium + 26 hard = 100 practice**
**TC-ST-22 · Mock pool: 0 easy + 66 medium + 50 hard mock-only = 116 mock-only**

**TC-ST-23 · in_mixed_mock=false — Statistics absent from Mixed mock pool**
**TC-ST-24 · mixed_subtype=true on catalog loader — both subtypes can appear in mock sessions**

**TC-ST-25 · Readiness score for statistics uses code-profile coverage (not MCQ-profile)**
- Preconditions: elite user; solve 100% easy + 100% medium for statistics
- Expected: `readiness_scores["statistics"].components.practice > 0`

**TC-ST-26 · Weakest concepts reported for statistics in dashboard insights**
- Preconditions: insert wrong submissions for a statistics concept × 3
- Expected: that concept appears in `weakest_concepts` for the statistics track

**TC-ST-27 · Free user: statistics easy unlocked, medium locked**
**TC-ST-28 · Pro user: statistics benchmark at medium difficulty → 201**
**TC-ST-29 · Numerical sandbox stdout captured in print_output**
**TC-ST-30 · Debrief for statistics session with numerical questions uses executable language**
- Tier: Elite; expected: `debrief` body contains language like "code", "solution", "runs"

---

## 21. ML Fundamentals & Experimentation Tracks

**ML Fundamentals:** `backend/tests/` — no dedicated test file yet; covered via mock test
(test_11_mock.py uses ML hard for Interview Loop tests) and content validation.

**Experimentation:** No dedicated test file yet; covered via integration tests in
`test_03_catalog.py` and content validation.

Both tracks:
- `eval_kind="mcq"` | `unlock_profile="mcq"` | `in_mixed_mock=false`
- Format: conceptual / scenario / predict_output / debug (MCQ response; no code execution)
- Catalog endpoints: `GET /api/ml-fundamentals/catalog`, `GET /api/experimentation/catalog`
- MCQ unlock thresholds: same as PySpark/DE/DM

**TC-ML-01 · ML catalog returns all three difficulty groups**
**TC-ML-02 · Experimentation catalog returns all three difficulty groups**
**TC-ML-03 · ML practice totals: 30 easy + 40 medium + 30 hard = 100**
**TC-ML-04 · Experimentation practice totals: 30 easy + 33 medium + 24 hard = 87**
**TC-ML-05 · ML mock-only: 0 easy + 59 medium + 84 hard (68 standalone + 16 chain children) = 143**
**TC-ML-06 · Experimentation mock-only: 0 easy + 45 medium + 59 hard (39 standalone + 20 chain children) = 104**
**TC-ML-07 · ML hard chain parents: 8 chains available for Interview Loop**
**TC-ML-08 · Experimentation hard chain parents: 10 chains available for Interview Loop**
**TC-ML-09 · Chain parent has follow_up_dimension: null; chain children have follow_up_dimension set**
**TC-ML-10 · Correct submit records progress with correct topic slug**

---

## 22. Account Management (Billing)

**File:** `backend/tests/test_17_account.py`

These tests cover billing info, subscription management, plan switching, and payment updates.
All endpoints are under `/api/account/` and require authentication.

---

### 22A. GET /api/account/billing

**TC-224 · Unauthenticated → 401**
**TC-225 · Free user → billing response with base fields**
- Expected: 200; body contains `plan`, `billing_status`; no `subscription_id`

**TC-226 · Lifetime user → billing response with lifetime flag**
- Expected: `lifetime: true` in response

**TC-227 · Pro user without subscription_id → billing response with unknown/none status**

**TC-228 · Pro user with subscription_id → live subscription data from Razorpay**
- Preconditions: patch Razorpay client to return a mock subscription object
- Expected: response contains subscription status from Razorpay

---

### 22B. POST /api/account/cancel

**TC-229 · Unauthenticated → 401**
**TC-230 · Free user → 400** (nothing to cancel)
**TC-231 · Lifetime user → 400** (lifetime plans cannot be cancelled)
**TC-232 (account) · Pro user without subscription_id → 400**
**TC-233 · Pro user with active subscription → 200 with cancel_at date**
**TC-234 · Already-cancelled subscription → 400**

---

### 22C. POST /api/account/switch-plan

**TC-235 · Unauthenticated → 401**
**TC-236 · Free user → 400** (must have active subscription to switch)
**TC-237 · Same plan → 400**
**TC-238 · Downgrade with `timing: "now"` → 400** (downgrades require end-of-cycle timing)
**TC-239 · Upgrade with `timing: "cycle_end"` → 200; scheduled change stored**
**TC-240 · Upgrade with `timing: "now"` → 200; plan switched immediately**

---

### 22D. POST /api/account/update-payment

**TC-241 (account) · Unauthenticated → 401**
**TC-242 (account) · Free user → 400** (no subscription to update payment for)
**TC-243 · Pro user → returns Razorpay short_url for payment update**
**TC-244 · Razorpay returns no short_url → 400**

---

### 22E. POST /api/account/reactivate

**TC-245 · Unauthenticated → 401**
**TC-246 (account) · Free user → 400**
**TC-247 · Active (non-pending-cancel) subscription → 400**
**TC-248 · Pending-cancel subscription → 200; cancellation reversed; `cancel_at` cleared**

---

## 23. Reasoning Track Metadata

**File:** `backend/tests/test_31_reasoning_metadata.py`

Tests that constructed-reasoning loaders (DE, DM, ML, Exp) expose and validate
`interaction_mode` correctly. Statistics is omitted (its `mixed` eval kind has different rules).

---

> **⚡ PARAMETRIZE:** TC-RM-01 and TC-RM-02 parametrize over all four constructed-reasoning tracks:
> `data-engineering`, `data-modeling`, `ml-fundamentals`, `experimentation`.

**TC-RM-01 · Constructed-reasoning loaders reject mismatched interaction_mode values**
- Steps: inject a question with `interaction_mode: "code_adjacent_reasoning"` (invalid for these tracks)
- Expected: `_validate_question(candidate)` raises `ValueError` matching "Invalid interaction_mode"
- Note: valid values for constructed-reasoning tracks are `"domain_reasoning"` and `"analytical_reasoning"`

**TC-RM-02 · Constructed-reasoning catalog rows expose interaction_mode field**
- Steps: call `get_questions_by_difficulty()` for each track; inspect all question dicts
- Expected: every question has `interaction_mode` in `{"domain_reasoning", "analytical_reasoning"}`

**TC-RM-03 · Statistics loader accepts numerical questions without interaction_mode**
- Expected: statistics numerical questions may omit `interaction_mode` without validation error

**TC-RM-04 · SQL/Python/Pandas/PySpark loaders do not require interaction_mode**
- Expected: code-execution tracks pass validation without `interaction_mode` field

**TC-RM-05 · Mock session payload exposes interaction_mode when present**
- Preconditions: Elite; start Interview Loop session with ML hard chain
- Steps: `GET /api/mock/{id}`
- Expected: each question in the response has `interaction_mode` field set

**TC-RM-06 · Interaction_mode values are distinct between domain and analytical questions**
- Expected: the bank contains at least one question with each value across the reasoning tracks

**TC-RM-07 · DE questions exclusively use domain_reasoning**
**TC-RM-08 · DM questions exclusively use domain_reasoning**
**TC-RM-09 · ML and Experimentation questions use analytical_reasoning**
**TC-RM-10 · Statistics conceptual questions may use either value (or omit)**

---

## 24. Python Evaluator Unit Tests

**File:** `backend/tests/test_python_evaluator.py`

Tests the generator/expansion layer in `python_evaluator.py` — specifically the `_expand_arg`,
`_expand_test_case`, `_expand_test_cases` helpers and the `_GENERATORS` registry.
No HTTP calls; no DB. Does not need `isolated_state`.

---

**Test 1 · Literal passthrough: literal input + literal expected pass through unchanged**
```python
tc = {"input": [42, [1, 2, 3]], "expected": 6}
result = _expand_test_case(tc, "def solve(x, lst): return sum(lst)")
assert result["input"] == [42, [1, 2, 3]]
assert result["expected"] == 6
```

**Test 2 · random_ints + compute=reference is deterministic (same seed → same output)**
- Same seed must produce identical input list and expected value on repeated calls

**Test 3 · random_graph with dag=True — all edges satisfy u < v**
- `_gen_random_graph(n_nodes=200, n_edges=500, seed=7, dag=True)`
- Expected: every (u, v) in the result has u < v

**Test 4 · random_graph with dag=False may contain bidirectional or back edges**

**Test 5 · sorted_ints generator returns a non-decreasing sequence**
- `_gen_sorted_ints(n=1000, seed=42)`
- Expected: each element ≤ the next

**Test 6 · _GENERATORS registry contains expected keys**
- Expected: `_GENERATORS` dict has at minimum `"random_ints"`, `"sorted_ints"`, `"random_graph"`

**Test 7 · _expand_test_cases handles a list of mixed literal and generator test cases**
- Steps: call `_expand_test_cases([tc_literal, tc_gen], reference_code)`
- Expected: returns list of same length; literal case unchanged; generator case expanded

---

## Appendix A: Test File → Section Mapping

| Test file | Sections covered |
|-----------|-----------------|
| `test_01_system.py` | §1 |
| `test_02_auth.py` | §2 |
| `test_03_catalog.py` | §3 |
| `test_04_questions.py` | §4 |
| `test_05_sql.py` | §5 |
| `test_06_python.py` | §6 |
| `test_07_pandas.py` | §7 |
| `test_08_pyspark.py` | §8 |
| `test_09_sample.py` | §9 |
| `test_10_paths.py` | §10 |
| `test_11_mock.py` | §11 |
| `test_12_dashboard.py` | §12 |
| `test_13_submissions.py` | §13 |
| `test_14_payments.py` | §14 |
| `test_15_rate_limiting.py` | §15 |
| `test_16_security.py` | §16 |
| `test_17_account.py` | §22 |
| `test_19_data_engineering.py` | §18 |
| `test_20_data_modeling.py` | §19 |
| `test_30_statistics.py` | §20 |
| `test_31_reasoning_metadata.py` | §23 |
| `test_paths_quality.py` | §17B |
| `test_python_evaluator.py` | §24 |

---

## Appendix B: Plan Tier Cross-Reference

| Plan tier | TC numbers |
|-----------|-----------|
| All tiers | TC-001–005, TC-006–007, TC-017, TC-024, TC-027, TC-028–032, TC-033, TC-038, TC-039–043, TC-069, TC-074, TC-075–090, TC-091–100, TC-101–118, TC-119–124, TC-169–170, TC-207, TC-211–212, TC-222–228, TC-229–239, TC-240–241, TC-271, TC-273, TC-277–279, TC-280, TC-DE-07, TC-DE-08, TC-DM-07, TC-DM-08 |
| Free | TC-008–016, TC-018–023, TC-025–026, TC-044–058, TC-059–062, TC-125–129, TC-133, TC-143, TC-146, TC-149, TC-151, TC-163, TC-167, TC-174, TC-192, TC-DE-03, TC-DM-03, TC-ST-03 |
| Pro | TC-063, TC-065, TC-073, TC-130–131, TC-134B–C, TC-135–136, TC-138, TC-144, TC-147, TC-162, TC-166, TC-193, TC-208, TC-213–216, TC-219, TC-DE-04, TC-DE-12, TC-DM-04, TC-ST-04, TC-ST-28 |
| Elite | TC-064, TC-132, TC-134, TC-134F, TC-145, TC-148, TC-150, TC-153–161, TC-164–165, TC-168, TC-177–180, TC-183, TC-194–201, TC-210, TC-242 (TC), TC-258–261, TC-262–267, TC-295–296, TC-ST-30 |
| lifetime_pro | TC-066, TC-209, TC-221, TC-231 |
| lifetime_elite | TC-067, TC-168, TC-220, TC-226, TC-260 |
| Static (no HTTP) | TC-289–294, TC-DE-17–18, TC-DM-15–16, TC-ST-21–24, TC-ML-03–09 |

---

## Appendix C: Feature Cross-Reference

| Feature | Spec source | TC numbers |
|---------|-------------|-----------|
| Unlock thresholds (code tracks) | `unlock.py`, CLAUDE.md | TC-044–052 |
| Unlock thresholds (MCQ tracks) | `unlock.py`, CLAUDE.md | TC-053–058, TC-DE-10–11, TC-DM-10–11 |
| Statistics unlock uses code profile | `unlock.py` | TC-ST-16–17 |
| Path shortcuts | `unlock.py`, CLAUDE.md | TC-059–062 |
| Hard cap (code: 8, MCQ: 5) | `unlock.py` FREE_HARD_CAP_* | TC-050, TC-058 |
| Lifetime plan normalization | `unlock.py` normalize_plan | TC-066–067 |
| mock_only exclusion from catalog | CLAUDE.md | TC-072, TC-156 |
| SQL read-only guard | `sql_guard.py` | TC-085–090, TC-246–251 |
| SQL cartesian / implicit-product guard | `sql_guard.py` | TC-246–247, TC-281 |
| SQL join count limit (≥5) | `sql_guard.py` | TC-248, TC-282 |
| SQL dangerous DuckDB functions | `sql_guard.py` | TC-249, TC-283 |
| Python AST guard | `python_guard.py` | TC-097–100, TC-232–233 |
| 3-second SQL timeout | CLAUDE.md, evaluator.py | TC-078 |
| 5-second Python/Pandas timeout | CLAUDE.md | TC-093, TC-104, TC-ST-19 |
| 200-row cap | CLAUDE.md | TC-076 |
| structure_correct field | `evaluator.py` | TC-243–245 |
| Close-miss feedback | CLAUDE.md | TC-082 |
| Repeat-attempt nudge | CLAUDE.md | TC-083 |
| Quality object on correct submit | CLAUDE.md | TC-079 |
| Anonymous-first identity | CLAUDE.md | TC-006–007, TC-018 |
| Login merges anon progress | CLAUDE.md | TC-018 |
| Login lockout | CLAUDE.md auth hardening | TC-039, TC-242 |
| CSRF mitigation | CLAUDE.md auth hardening | TC-040–041, TC-237–239 |
| Non-enumeration (forgot-password) | CLAUDE.md | TC-024 |
| OAuth state single-use | CLAUDE.md | TC-036 |
| Magic link single-use | auth.py | TC-031 |
| Session cookie SameSite=Lax | CLAUDE.md | TC-240 |
| Phase 3 mock modes | `docs/features/mock.md` | TC-125–183, TC-RM-05 |
| compute_mock_access mode param | `unlock.py` | TC-125–134G |
| Free: 1 benchmark/week | `docs/features/mock.md` | TC-127 |
| Pro: 3 benchmark/day (independent of custom) | `docs/features/mock.md` | TC-134G |
| Pro: 3 custom/day | `docs/features/mock.md` | TC-134B–C, TC-147 |
| interview_loop (Elite only) | `docs/features/mock.md` | TC-134D–F, TC-177–180 |
| Interview Loop chain atomicity | `docs/features/mock.md` | TC-177–180 |
| mock_chain_consumption reclaim | `routers/mock.py` | TC-180 |
| Pool exhaustion 409 | `routers/mock.py` | TC-179 |
| Legacy 30min/60min → 400 | `routers/mock.py` | TC-181 |
| Mixed track requires role | `routers/mock.py` | TC-136D, TC-182 |
| Statistics benchmark: 1 numerical + 2 conceptual | `docs/specs/mock-benchmark-spec.md` | TC-136C, TC-ST-18 |
| Blank/invalid submit → 422, no slot consumed | `routers/mock.py` | TC-172(mock), TC-173(mock) |
| Second submit after correct/wrong → 409 | `routers/mock.py` | TC-174(mock), TC-175(mock) |
| Session debrief plan gates | `docs/features/mock.md` | TC-158–164, TC-262–267 |
| Debrief: reasoning-track language | `routers/mock.py` | TC-172(debrief)–175(debrief) |
| Mock analytics loop_summary | `routers/mock.py` | TC-183 |
| Mode breakdown in analytics | `routers/mock.py` | TC-165B |
| Company filter (Elite SQL only) | `docs/features/mock.md` | TC-133–134, TC-149–150 |
| Focus mode (Elite only) | `docs/features/mock.md` | TC-151–155, TC-258–261 |
| Dashboard 9-track support | `routers/dashboard.py` | TC-172(dashboard) |
| Dashboard insights 9-track support | `routers/insights.py` (TRACKS) | TC-176(insights) |
| Readiness scores all 9 tracks (Elite) | `routers/insights.py` | TC-194 |
| Study plan (Elite only) | `routers/insights.py` | TC-195–197, TC-295–296 |
| Weakest concepts (≥3 attempts, <50%) | `routers/insights.py` | TC-182–183 |
| Mock analytics weak_concepts (<60%) | `routers/mock.py` | TC-165 (note) |
| Streak logic | `db.py`, `routers/insights.py` | TC-042–043, TC-181 |
| Razorpay payment flows | `routers/razorpay.py` | TC-208–223, TC-271–279 |
| Account billing endpoints | `routers/account.py` | TC-224–248 |
| Webhook idempotency | `docs/features/pricing.md` | TC-216, TC-223 |
| Lifetime subscription protection | `docs/features/pricing.md` | TC-220–221 |
| Rate limiter Redis fallback | `rate_limiter.py` | TC-280 |
| 46 learning paths covering 9 tracks | `path_loader.py`, CLAUDE.md | TC-119, TC-291–294 |
| Path quality rules (patterns, focus, graph) | `test_paths_quality.py` | Rules 1–6 |
| Statistics dual-subtype | `statistics_questions.py` | TC-ST-05–30 |
| interaction_mode field on reasoning tracks | `tracks.py`, loaders | TC-RM-01–10 |
| Python evaluator generator expansion | `python_evaluator.py` | Tests 1–7 |
| SQL expected_query integrity | `questions.py`, DuckDB | TC-289–290 |
