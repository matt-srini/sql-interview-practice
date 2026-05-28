# Test Guidance — datathink platform

> ⚠️ **STALE — DO NOT TREAT AS CANONICAL. Needs regeneration before use.** This document was written for an earlier **4-track / 22-path** era of the platform (SQL, Python, Pandas, PySpark only). The platform now has **9 tracks, 876 practice + 1,102 mock-only questions, and 46 learning paths**, plus Phase-3 mock modes (`benchmark` / `custom` / `interview_loop`) and role-based Mixed benchmarks. The vast majority of TC cases below (counts like "all 4 tracks", "22 paths", per-track expectations, the legacy `30min`/`60min` mock model) are **out of date**. Ground truth lives in `CLAUDE.md`, `docs/backend.md`, `docs/features/mock.md`, and the per-track docs. **Regenerate this test plan from the current spec before authoring any test suite from it** — do not write tests against the stale numbers below.
>
> **Original purpose (historical):** Spec-derived test plan mapping each testable spec claim to ≥1 test case. The "this document is canonical" claim below applied to the 4-track era and is **no longer valid**.
>
> **Scope:** Backend API tests (pytest + httpx TestClient). Frontend Playwright tests are
> addressed separately. Unit tests for pure functions (unlock, insights, debrief) are included
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
| 11 | [Mock Interviews](#11-mock-interviews) |
| 12 | [Dashboard & Insights](#12-dashboard--insights) |
| 13 | [Submission History](#13-submission-history) |
| 14 | [Payments & Webhooks](#14-payments--webhooks) |
| 15 | [Rate Limiting](#15-rate-limiting) |
| 16 | [Security Guards](#16-security-guards) |
| 17 | [Content & Static Integrity](#17-content--static-integrity) |

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
2. `ensure_schema_admin()` — create all tables via a throw-away NullPool engine
3. `reset_database_admin()` — truncate all tables (clean slate)
4. `_clear_rate_limit_state()` — reset in-memory rate limiter buckets

**Teardown (same steps):**
1. `close_pool()`
2. `reset_database_admin()` — leave clean for the next module
3. `_clear_rate_limit_state()`

The `_admin` variants use a NullPool disposable engine so no asyncpg pool state bleeds
between modules.

### 0.2 TestClient usage

```python
with TestClient(app) as client:
    # all requests inside this block
```

`TestClient` is **never** created at class or module scope. Every test function opens and
closes its own client. This ensures the ASGI lifespan (and any in-process caches attached to
it) is correctly scoped.

### 0.3 User seeding helpers

```python
def _make_user(client, plan="free", email=None, name="Test User", password="Password1"):
    """Seed anon session, register, optionally upgrade plan. Returns user dict."""
    client.get("/api/catalog")                          # seeds anonymous session
    reg = client.post("/api/auth/register", json={"email": email or _unique_email(),
                                                   "name": name, "password": password})
    assert reg.status_code == 201
    user_id = reg.json()["user"]["id"]
    if plan != "free":
        up = client.post("/api/user/plan", json={"user_id": user_id, "new_plan": plan,
                                                  "context": "test-setup"})
        assert up.status_code == 200
    return reg.json()["user"]
```

Plan values: `"free"`, `"pro"`, `"elite"`, `"lifetime_pro"`, `"lifetime_elite"`.

For state that cannot be driven through the HTTP API (e.g., inserting historical submissions
at specific timestamps), use direct psycopg2 helpers:

```python
def _insert_submission(user_id, *, track, question_id, is_correct, submitted_at=None)
def _insert_progress(user_id, *, track, question_id, solved_at=None)
def _db_conn()   # returns a short-lived psycopg2 connection, caller closes it
```

### 0.4 Email service

`email_service.send_verification_email` and `email_service.send_password_reset_email` are
patched globally as `AsyncMock(return_value=True)` in `pytest_configure`. Individual tests
MUST NOT re-patch these unless they are explicitly testing email dispatch side effects.

### 0.5 Rate limiter

`TESTING=1` env var is set globally. The rate limiter uses in-memory fallback (no Redis).
To test rate-limit enforcement, use `monkeypatch.setattr` to lower thresholds:

```python
monkeypatch.setattr("routers.auth.LOGIN_LOCKOUT_MAX_ATTEMPTS", 3)
```

To disable the rate limiter for non-rate-limit tests, use the `_clear_rate_limit_state()`
call that already runs in `isolated_state`.

### 0.6 No repetition rule

Each behaviour is tested exactly once in its most appropriate section. Where a later section
depends on a behaviour already verified in an earlier section (e.g., "question is unlocked"),
it may assume that behaviour and reference the earlier TC number rather than re-verifying it.

### 0.7 Unique email generation

```python
_counter = itertools.count(1)
def _unique_email(): return f"test-{next(_counter)}@internal.test"
```

Use `itertools.count` (not `uuid4`) — deterministic, readable in failure output.

### 0.8 Additional helpers

These helpers are used across multiple sections. Implement once in `conftest.py`.

```python
def _assert_unlock_state(client, track, expected_easy_count, expected_medium_count, expected_hard_count):
    """Assert exact unlock counts per difficulty for a given track.
    Pass -1 for 'all unlocked'. Calls GET /api/{track}/catalog (or /api/catalog for sql)
    and counts questions where state == 'unlocked' or state == 'solved'."""

def _insert_submissions_batch(conn, user_id, track, rows):
    """Insert multiple submission rows directly into Postgres in one call.
    rows = [{"question_id": int, "is_correct": bool, "time_seconds": int, "concepts": list[str]}]
    All rows default to 'sql' track unless overridden. Useful for seeding unlock thresholds."""

def _make_concept_setup(conn, user_id, concept_name, num_attempts, num_correct, track="sql"):
    """Seed submissions for a single concept tag.
    Inserts `num_attempts` rows, `num_correct` of which are is_correct=True.
    Used to test weakest_concepts accuracy buckets in §12C (TC-185–188)."""

def _seed_mock_sessions(conn, user_id, count, track, difficulty, *, completed=True, base_date=None):
    """Insert `count` mock_session rows directly into Postgres.
    All sessions are set to completed=True by default. base_date sets the started_at anchor
    (defaults to utcnow). Used for analytics/history tests in §11 (TC-141, TC-165–168)."""
```

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
- Expected: response is 4xx; body has keys `"error"` (non-empty string) and `"request_id"` (non-empty string); no other top-level error keys
- Tier: all

**TC-005 · Config endpoint returns provider availability**
- Steps: `GET /api/config`
- Expected: 200; body contains `"google_oauth_enabled"` and `"github_oauth_enabled"` as booleans
- Tier: all

---

## 2. Authentication & Identity

**Connection rules:** Each sub-area uses one `TestClient` block per test. `isolated_state`
resets DB between tests. No cross-test state.

---

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
- Expected: 201; body `{ "user": { id, email, name, plan: "free", email_verified: false } }`; `set-cookie` header for session; email_service mock called once
- Tier: all

**TC-009 · Duplicate email registration rejected**
- Steps: register once successfully; attempt to register again with same email
- Expected: second registration returns 400; body has `"error"` key
- Tier: all

**TC-010 · Weak password — missing uppercase**
- Steps: `POST /api/auth/register { password: "password1" }`
- Expected: 422 or 400; body error references password rule
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
- Steps: (a) register user A; mark one question solved for user A via `_insert_progress`; (b) in a fresh client, hit catalog (new anon user); mark a different question solved for anon user; (c) `POST /api/auth/login` with user A credentials
- Expected: 200; after login, `GET /api/catalog` shows both questions as solved
- Tier: all

**TC-019 · Logout clears session cookie**
- Preconditions: logged-in session
- Steps: `POST /api/auth/logout`; then `GET /api/auth/me`
- Expected: logout returns 200 `{ "ok": true }`; subsequent `/me` returns 401
- Tier: all

---

### 2D. Email verification

**TC-020 · Valid verification token marks account as verified**
- Steps: register (token created); call `POST /api/auth/verify-email { token }` with token captured from `create_email_verification_token` DB call
- Expected: 200 `{ "ok": true }`; subsequent `GET /api/auth/me` shows `email_verified: true`
- Tier: all

**TC-021 · Expired or consumed verification token returns 400**
- Steps: generate a token; consume it once; attempt `POST /api/auth/verify-email` a second time with the same token
- Expected: 400; error references "invalid or has expired"
- Tier: all

**TC-022 · Resend verification — unauthenticated returns 401**
- Steps: `POST /api/auth/resend-verification` with no session cookie
- Expected: 401
- Tier: all

**TC-023 · Resend verification — already-verified returns 400**
- Steps: register and verify email; `POST /api/auth/resend-verification`
- Expected: 400; error references "already verified"
- Tier: all

---

### 2E. Password reset

**TC-024 · Forgot-password always returns 200 (non-enumeration)**
- Steps: (a) `POST /api/auth/forgot-password { email: "nonexistent@example.com" }`; (b) repeat with a registered email
- Expected: both return 200 `{ "ok": true }`; response bodies and times are indistinguishable to the caller
- Tier: all

**TC-025 · Valid reset token updates password and marks email verified**
- Steps: create a password reset token via `create_password_reset_token`; `POST /api/auth/reset-password { token, password: "NewPass1" }`; attempt login with new password
- Expected: reset returns 200; login with new password succeeds; `email_verified: true` in login response
- Tier: all

**TC-026 · Expired or reused reset token returns 400**
- Steps: create token; consume it; attempt `POST /api/auth/reset-password` again with same token
- Expected: 400; error references "invalid or has expired"
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
- Steps: get dev_magic_link URL from TC-028; `GET {dev_magic_link_url}` with `follow_redirects=False`
- Expected: 302 redirect to frontend root; `set-cookie` header present
- Tier: all

**TC-030 · Magic link callback with invalid token redirects to auth error**
- Steps: `GET /api/auth/magic-link/callback?token=bogus` with `follow_redirects=False`
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-031 · Magic link token is single-use (second use redirects to error)**
- Steps: use a valid magic link once (TC-029); use the same URL again
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
- Steps: `GET /api/auth/oauth/google/authorize`; `GET /api/auth/oauth/google/authorize` again
- Expected: two different `state` values returned; each is a distinct token
- Tier: all

**TC-035 · /callback with invalid state redirects to error**
- Steps: `GET /api/auth/oauth/google/callback?code=abc&state=bogus`
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-036 · /callback with consumed state redirects to error**
- Steps: generate a valid state; consume it via `consume_oauth_state_token` directly; attempt callback with that state
- Expected: 302 redirect URL contains `/auth?error=`
- Tier: all

**TC-037 · /callback happy path creates session and redirects (patched exchange)**
- Steps: patch `_exchange_google_code` to return `{ email, name, provider_id }`; generate valid state; `GET /api/auth/oauth/google/callback?code=x&state={state}` with `follow_redirects=False`
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
- Expected: third (or fourth) attempt returns 429; error references "too many failed sign-in attempts"
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
- Steps: call `POST /api/auth/login` with wrong password 2 times; then call with correct password; then call with wrong password 2 more times
- Expected: account is NOT locked after the second round of failures (counter was reset by the successful login)
- Tier: all

**TC-240 · Session cookie uses SameSite=Lax attribute**
- Steps: register a user and log in; inspect `set-cookie` header
- Expected: `set-cookie` response header includes `samesite=lax` (case-insensitive)
- Tier: all

---

### 2I. GET /api/auth/me fields

**TC-042 · /me returns full user profile including streak metadata**
- Preconditions: registered and logged-in user with one correct submission today (via `_insert_submission`)
- Steps: `GET /api/auth/me`
- Expected: 200; body `{ "user": { id, email, name, plan, email_verified, streak_days: 1, streak_at_risk: false } }`
- Tier: all (Free used here)

**TC-043 · /me streak_at_risk is true when yesterday had solve but today has none**
- Preconditions: logged-in user; one correct submission inserted with `submitted_at = now() - 1 day`; none today
- Steps: `GET /api/auth/me`
- Expected: `streak_at_risk: true`; `streak_days: 0`
- Tier: all

---

## 3. Catalog & Unlock Logic

**Connection rules:** Use `_make_user(client, plan=...)` to seed users. Use `_insert_progress`
to simulate solves without HTTP overhead. Catalog endpoint is `GET /api/catalog` for SQL;
`GET /api/python/catalog`, `GET /api/python-data/catalog`, `GET /api/pyspark/catalog` for
other tracks.

Unit tests for `compute_unlock_state` in `unlock.py` are preferred over HTTP integration
tests where they cover the same code path — test the pure function directly.

---

### 3A. Free tier — code tracks (SQL, Python, Pandas)

> **⚡ PARAMETRIZE:** TC-044–052 all call `compute_unlock_state(...)` (unit-level pure function).
> Implement as a single parametrized test that covers all threshold checkpoints:
> ```python
> @pytest.mark.parametrize("easy_solves,medium_solves,expected_medium_unlock_count,expected_hard_unlock_count", [
>     (0,  0,  0,  0),  # TC-044: baseline
>     (8,  0,  3,  0),  # TC-045
>     (15, 0,  8,  0),  # TC-046
>     (25, 0,  -1, 0),  # TC-047: -1 = all
>     (25, 8,  -1, 3),  # TC-048
>     (25, 15, -1, 8),  # TC-049
>     (25, 22, -1, 8),  # TC-050: cap enforced
> ])
> ```
> TC-051 (solved state) and TC-052 (locked prefix boundary) are kept as separate tests because
> they test state transitions, not threshold counts.

**TC-044 · Fresh free user: all easy unlocked, no medium or hard unlocked**
- Preconditions: free user, zero solves
- Steps: `GET /api/catalog` (SQL); inspect state of easy, medium, hard questions
- Expected: all easy questions have state `"unlocked"`; all medium questions have state `"locked"`; all hard questions have state `"locked"`
- Tier: Free

**TC-045 · 8 easy solved → 3 medium unlocked**
- Preconditions: free user; 8 easy SQL questions solved via `_insert_progress`
- Steps (unit): `compute_unlock_state("free", solved_ids, catalog, track="sql")`
- Expected: first 3 medium questions (by `order`) have state `"unlocked"`; remaining medium questions `"locked"`
- Tier: Free

**TC-046 · 15 easy solved → 8 medium unlocked**
- Same as TC-045 with 15 easy solves
- Expected: first 8 medium questions unlocked
- Tier: Free

**TC-047 · 25 easy solved → all medium unlocked**
- Same with 25 easy solves
- Expected: all medium questions unlocked
- Tier: Free

**TC-048 · 8 medium solved → 3 hard unlocked**
- Preconditions: free user; 25 easy + 8 medium solved (so medium is fully unlocked first)
- Expected: first 3 hard questions unlocked
- Tier: Free

**TC-049 · 15 medium solved → 8 hard unlocked**
- Preconditions: free user; 25 easy + 15 medium solved
- Expected: first 8 hard questions unlocked
- Tier: Free

**TC-050 · 22 medium solved → hard cap enforced at 8 (not 15)**
- Preconditions: free user; 25 easy + 22 medium solved
- Expected: exactly 8 hard questions unlocked (FREE_HARD_CAP_CODE = 8); the rest are locked
- Note: the threshold table says "22 medium → 15 hard" but the cap is 8. The cap always wins.
- Tier: Free

**TC-051 · Already-solved questions retain "solved" state regardless of lock threshold**
- Preconditions: free user; 1 easy solved; that same question ID is in solved_ids
- Expected: the solved question has state `"solved"`, not `"unlocked"` or `"locked"`
- Tier: Free

**TC-052 · Questions beyond the unlocked prefix remain locked**
- Preconditions: free user; 8 easy solved (→ 3 medium unlocked)
- Expected: 4th medium question (by order) has state `"locked"` even though it's adjacent to unlocked ones
- Tier: Free

---

### 3B. Free tier — PySpark (higher thresholds)

> **⚡ PARAMETRIZE:** TC-053–058 mirror TC-044–050 for PySpark. Implement as one parametrized test:
> ```python
> @pytest.mark.parametrize("easy_solves,medium_solves,expected_medium_count,expected_hard_count", [
>     (11, 0,  0,  0),  # TC-053: below threshold
>     (12, 0,  3,  0),  # TC-054
>     (20, 0,  8,  0),  # TC-055
>     (30, 0,  -1, 0),  # TC-056: -1 = all
>     (30, 15, -1, 5),  # TC-057
>     (30, 22, -1, 5),  # TC-058: cap enforced at 5
> ])
> def test_pyspark_free_unlock_thresholds(easy_solves, medium_solves, ...):
> ```

**TC-053 · Fresh free PySpark user: 0 medium unlocked (threshold is 12, not 8)**
- Preconditions: free user; 11 easy PySpark solved
- Expected: all medium PySpark questions locked (threshold not yet met)
- Tier: Free

**TC-054 · 12 easy PySpark → 3 medium unlocked**
- Tier: Free

**TC-055 · 20 easy PySpark → 8 medium unlocked**
- Tier: Free

**TC-056 · 30 easy PySpark → all medium unlocked**
- Tier: Free

**TC-057 · 15 medium PySpark → 5 hard unlocked**
- Tier: Free

**TC-058 · 22 medium PySpark → hard cap enforced at 5 (FREE_HARD_CAP_PYSPARK)**
- Expected: exactly 5 hard PySpark questions unlocked
- Tier: Free

---

### 3C. Path shortcuts (Free)

**TC-059 · starter_done=True → all medium unlocked regardless of easy solve count**
- Preconditions: free user; 0 easy solved; `path_state={"starter_done": True}`
- Steps (unit): `compute_unlock_state("free", set(), catalog, track="sql", path_state={"starter_done": True})`
- Expected: all medium questions unlocked; hard questions still locked (no intermediate)
- Tier: Free

**TC-060 · intermediate_done=True → full hard cap unlocked regardless of medium solve count**
- Preconditions: free user; 0 medium solved; `path_state={"intermediate_done": True}`
- Expected: up to FREE_HARD_CAP_CODE hard questions unlocked; medium still at threshold-based access
- Tier: Free

**TC-061 · Both shortcuts active: all medium + full hard cap**
- `path_state={"starter_done": True, "intermediate_done": True}`
- Expected: all medium unlocked + up to cap hard unlocked
- Tier: Free

**TC-062 · Path shortcut takes precedence over threshold (higher limit wins)**
- Preconditions: free user; 8 easy solved (→ 3 medium by threshold); `starter_done=True`
- Expected: all medium unlocked (starter_done wins)
- Tier: Free

---

### 3D. Pro and Elite

**TC-063 · Pro user: all easy + all medium + all hard, no hard cap**
- Preconditions: pro user; zero solves
- Steps (unit): `compute_unlock_state("pro", set(), catalog, track="sql")`
- Expected: all easy, medium, hard questions have state `"unlocked"`
- Tier: Pro

**TC-064 · Elite user: full catalog across all 4 tracks**
- Preconditions: elite user; zero solves
- Expected: same as TC-063 for all four tracks
- Tier: Elite

**TC-065 · Pro — no hard cap (access all hard questions)**
- Verify the SQL hard count returned for pro equals the total hard questions in the catalog (≥ 29)
- Tier: Pro

---

### 3E. Lifetime plan normalization

**TC-066 · lifetime_pro normalizes to pro for all access checks**
- Steps (unit): `normalize_plan("lifetime_pro")` returns `"pro"`; `compute_unlock_state("lifetime_pro", ...)` returns same result as `"pro"`
- Tier: all

**TC-067 · lifetime_elite normalizes to elite for all access checks**
- Steps (unit): `normalize_plan("lifetime_elite")` returns `"elite"`
- Tier: all

**TC-068 · Lifetime variants are not downgraded by subscription.cancelled webhook**
- Cross-reference: TC-220 (lifetime_elite), TC-221 (lifetime_pro)

---

## 4. Question Access & Details

---

**TC-069 · Locked question returns 403**
- Preconditions: free user; no solves; pick a medium question ID
- Steps: `GET /api/questions/{medium_id}`
- Expected: 403; body has `"error"` key
- Tier: Free

**TC-070 · Unlocked question returns question detail**
- Preconditions: free user; pick an easy question ID (always unlocked for free)
- Steps: `GET /api/questions/{easy_id}`
- Expected: 200; body contains `id`, `title`, `prompt`, `hints`, `concepts`, `schema` (SQL); does NOT contain `solution` field
- Tier: Free

**TC-071 · Solution field absent before any submission**
- Steps: `GET /api/questions/{easy_id}` for any unlocked question
- Expected: response body does not have a `"solution"` key (or `solution` is `null`)
- Tier: all

**TC-072 · mock_only questions absent from practice catalog**
- Preconditions: elite user (full access)
- Steps: `GET /api/catalog`; count total questions
- Expected: count matches the documented practice-only total (95 SQL + 83 Python + 76 Pandas + 102 PySpark = 356); no `mock_only: true` question appears
- Note: The `GET /api/questions/{id}` for a mock-only question ID should return 404 or 403.
- Tier: Elite

**TC-073 · Python question detail includes test_cases and function_signature**
- Preconditions: pro user; pick an easy Python question
- Steps: `GET /api/python/questions/{easy_id}`
- Expected: 200; body contains `test_cases` array and `function_signature` string
- Tier: Pro

**TC-074 · PySpark question detail includes options array (4 options)**
- Preconditions: free user; pick an easy PySpark question
- Steps: `GET /api/pyspark/questions/{easy_id}`
- Expected: 200; body contains `options` array with exactly 4 entries; does NOT contain `correct_option` field
- Tier: Free

---

## 5. SQL Execution

**Connection rules:** Use an easy unlocked SQL question for all run/submit tests to avoid
lock-check interference. Use `_make_user(client, plan="pro")` to ensure access without
worrying about unlock thresholds.

---

### 5A. Run query

**TC-075 · Valid SELECT returns rows**
- Preconditions: pro user; easy SQL question
- Steps: `POST /api/run-query { question_id, query: <valid SELECT> }`
- Expected: 200; body contains `rows` array (length ≥ 1); each row is an object
- Tier: Free (uses easy question for Free too)

**TC-076 · Row cap: result exceeding 200 rows truncated to 200**
- Preconditions: SQL question whose expected output exceeds 200 rows (e.g., `SELECT * FROM sessions`)
- Steps: `POST /api/run-query { query: "SELECT * FROM sessions" }`
- Expected: 200; `rows` array length is exactly 200
- Tier: all

**TC-077 · SQL syntax error returns readable error message**
- Steps: `POST /api/run-query { query: "SELEKT * FORM users" }`
- Expected: 200 or 400; body contains `"error"` with a human-readable message; no stack trace exposed
- Tier: all

**TC-078 · Query execution timeout enforced (3-second limit)**
- Steps: `POST /api/run-query { query: "SELECT COUNT(*) FROM generate_series(1, 100000000)" }` (or equivalent slow query)
- Expected: error response with timeout indicator; completes within ~5 seconds wall-clock
- Tier: all

---

### 5B. Submit

**TC-079 · Correct answer returns verdict, solution, and quality object**
- Preconditions: pro user; easy SQL question with known correct solution
- Steps: `POST /api/submit { question_id, query: <correct query>, duration_ms: 5000 }`
- Expected: 200; `correct: true`; `solution` field present (non-null); `quality` object present with keys `efficiency_note`, `style_notes`, `complexity_hint`, `alternative_solution`
- Tier: all (easy unlocked for Free)

**TC-080 · Correct answer records progress in user_progress table**
- Preconditions: pro user; submit correct answer for question Q
- Steps: after submit, query DB directly for `user_progress` row for (user_id, question_id)
- Expected: row exists with `track="sql"` and a non-null `solved_at`
- Tier: all

**TC-081 · Wrong answer returns verdict without solution**
- Steps: `POST /api/submit { question_id, query: "SELECT 1 AS x" }` (clearly wrong)
- Expected: 200; `correct: false`; `solution` field absent or null; feedback message present
- Tier: all

**TC-082 · Close-miss feedback: same shape, wrong values → partial quality with style notes**
- Preconditions: a question whose expected output has a known column/row shape; craft a query that returns the same shape but wrong values
- Steps: `POST /api/submit { question_id, query: <same-shape wrong answer> }`
- Expected: `correct: false`; body contains `style_notes` (non-empty list) from the partial quality object
- Tier: all

**TC-083 · Repeat identical wrong attempt triggers nudge message**
- Steps: submit the same wrong query twice for the same question
- Expected: second response body `feedback` starts with a nudge prefix (distinct from first response)
- Tier: all

**TC-084 · duration_ms field is accepted and stored**
- Steps: `POST /api/submit { question_id, query: <correct>, duration_ms: 12000 }`
- Expected: 200 (no error); submission record in DB contains the provided duration
- Tier: all

**TC-243 · Submit always returns structure_correct field**
- Preconditions: pro user; any easy SQL question
- Steps: `POST /api/submit { question_id, query: <any query> }`
- Expected: 200; response body always contains `structure_correct` as a boolean (never absent)
- Tier: all

**TC-244 · required_concepts with enforce=true: correct result + missing concept → structure_correct: false**
- Preconditions: use a question that has `required_concepts` with `enforce: true` (e.g. a window-function question); craft a query that produces the correct data result without using the required technique
- Steps: `POST /api/submit { question_id, query: <correct-data-wrong-technique> }`
- Expected: 200; `correct: true`; `structure_correct: false`; feedback references the missing concept
- Tier: all

**TC-245 · required_concepts with enforce=false: correct result + missing concept → structure_correct: true with advisory**
- Preconditions: use a question that has `required_concepts` with `enforce: false`; craft a query that is data-correct but skips the concept
- Steps: `POST /api/submit { question_id, query: <correct-data-bypass-technique> }`
- Expected: 200; `correct: true`; `structure_correct: true`; `feedback` contains advisory text about the concept
- Tier: all

---

### 5C. SQL guard

> **⚡ PARAMETRIZE:** TC-085–090 are all test cases for the SQL write/multi-statement guard on
> `/api/run-query`. Implement as a single parametrized test:
> ```python
> @pytest.mark.parametrize("query,expect_reject", [
>     ("DROP TABLE users",                              True),   # TC-085
>     ("INSERT INTO users VALUES (...)",                True),   # TC-086
>     ("UPDATE users SET name='x'",                    True),   # TC-087
>     ("DELETE FROM users",                            True),   # TC-088
>     ("SELECT 1; DROP TABLE users",                   True),   # TC-089
>     ("SELECT * FROM (SELECT user_id FROM users LIMIT 5) t", False),  # TC-090
> ])
> ```

**TC-085 · DROP TABLE statement rejected (write guard)**
- Steps: `POST /api/run-query { query: "DROP TABLE users" }`
- Expected: 400; error references write restriction; DuckDB never called
- Tier: all

**TC-086 · INSERT statement rejected**
- Steps: `POST /api/run-query { query: "INSERT INTO users VALUES (...)" }`
- Expected: 400
- Tier: all

**TC-087 · UPDATE statement rejected**
- Steps: `POST /api/run-query { query: "UPDATE users SET name='x'" }`
- Expected: 400
- Tier: all

**TC-088 · DELETE statement rejected**
- Steps: `POST /api/run-query { query: "DELETE FROM users" }`
- Expected: 400
- Tier: all

**TC-089 · Multi-statement input rejected (SELECT + DROP)**
- Steps: `POST /api/run-query { query: "SELECT 1; DROP TABLE users" }`
- Expected: 400
- Tier: all

**TC-090 · Valid subquery SELECT accepted**
- Steps: `POST /api/run-query { query: "SELECT * FROM (SELECT user_id FROM users LIMIT 5) t" }`
- Expected: 200 with rows
- Tier: all

> **⚡ PARAMETRIZE:** TC-246–249 + TC-281–283 all exercise the SQL structural/security guard.
> TC-246–249 test `/api/run-query`; TC-281–283 verify the same guard on `/api/submit`.
> Implement as one parametrized test, parametrizing over `(query, endpoint)`:
> ```python
> @pytest.mark.parametrize("query,endpoint", [
>     ("SELECT * FROM users CROSS JOIN orders",       "/api/run-query"),   # TC-246
>     ("SELECT * FROM users, orders WHERE 1=1",       "/api/run-query"),   # TC-247
>     ("<5-join query>",                              "/api/run-query"),   # TC-248
>     ("SELECT * FROM read_csv('/etc/passwd')",       "/api/run-query"),   # TC-249
>     ("SELECT * FROM users CROSS JOIN orders",       "/api/submit"),      # TC-281
>     ("<5-join query>",                              "/api/submit"),      # TC-282
>     ("SELECT * FROM read_csv('/etc/passwd')",       "/api/submit"),      # TC-283
>     # Repeat TC-249 with each dangerous function as additional rows
> ])
> ```

**TC-246 · Cartesian join (CROSS JOIN) rejected**
- Steps: `POST /api/run-query { query: "SELECT * FROM users CROSS JOIN orders" }`
- Expected: 400; error references join restriction
- Tier: all

**TC-247 · Un-joined multi-table query (implicit cartesian) rejected**
- Steps: `POST /api/run-query { query: "SELECT * FROM users, orders WHERE 1=1" }`
- Expected: 400
- Tier: all

**TC-248 · Query with 5 or more joins rejected**
- Steps: `POST /api/run-query` with a query that joins 5+ tables
- Expected: 400; error references join count limit
- Tier: all

**TC-249 · Dangerous DuckDB functions rejected (read_csv, read_json, glob, etc.)**
- Steps (parametrized): `POST /api/run-query { query: "SELECT * FROM read_csv('/etc/passwd')" }` and similarly for `read_json`, `glob`, `read_parquet`, `httpfs`, `http_get`, `from_json`, `iceberg_scan`, `delta_scan`, `read_text`
- Expected: 400 for each; error references restriction
- Tier: all

**TC-250 · run-query on a locked question returns 403**
- Preconditions: free user; no solves; pick a medium question ID
- Steps: `POST /api/run-query { question_id: <medium_id>, query: "SELECT 1" }`
- Expected: 403 with `{error, request_id}` shape
- Tier: Free

**TC-251 · run-query on a non-existent question_id returns 404**
- Steps: `POST /api/run-query { question_id: 99999999, query: "SELECT 1" }`
- Expected: 404; body has `"error"` and `"request_id"` keys
- Tier: all

---

## 6. Python Execution

**Connection rules:** Use a Pro user and a known easy Python question for all run/submit tests.

---

### 6A. Run code

**TC-091 · Correct code passes test cases and returns captured stdout**
- Preconditions: pro user; easy Python question with known correct solution
- Steps: `POST /api/python/run-code { question_id, code: <correct solution> }`
- Expected: 200; body contains `test_results` array; at least one test passes; `print_output` present (may be empty string)
- Tier: all (easy for Free)

**TC-092 · Compile error returns readable error message**
- Steps: `POST /api/python/run-code { code: "def solve(x\n    return x" }`
- Expected: 200 or 400; body contains `"error"` with human-readable message; no raw traceback with server paths
- Tier: all

**TC-093 · 5-second execution timeout enforced**
- Steps: `POST /api/python/run-code { code: "def solve(n):\n    import time\n    time.sleep(10)\n    return n" }`
- Expected: error response indicating timeout; wall-clock completes within ~7 seconds
- Tier: all

**TC-094 · stdout captured in print_output**
- Steps: `POST /api/python/run-code { code: "def solve(n):\n    print('hello')\n    return n" }`
- Expected: `print_output` contains `"hello"`
- Tier: all

---

### 6B. Submit

**TC-095 · All test cases pass → correct: true + solution revealed**
- Steps: `POST /api/python/submit { question_id, code: <correct>, duration_ms: 3000 }`
- Expected: 200; `correct: true`; `solution` present
- Tier: all

**TC-096 · Any test case fails → correct: false + per-case breakdown**
- Steps: `POST /api/python/submit { question_id, code: <incorrect> }`
- Expected: 200; `correct: false`; response includes per-test breakdown showing which cases failed
- Tier: all

---

### 6C. Python guard

> **⚡ PARAMETRIZE:** TC-097–100 all exercise the Python AST guard on `/api/python/run-code`.
> TC-232–233 verify the same guard on `/api/python/submit`.
> Implement as one parametrized test across both endpoints:
> ```python
> @pytest.mark.parametrize("code,endpoint,expect_reject", [
>     ("import os; os.listdir('/')",            "/api/python/run-code", True),   # TC-097
>     ("import subprocess",                    "/api/python/run-code", True),   # TC-098
>     ("open('/tmp/pwned', 'w').write('x')",   "/api/python/run-code", True),   # TC-099
>     ("import math\ndef solve(n): return math.sqrt(n)", "/api/python/run-code", False),  # TC-100
>     ("import os\ndef solve(n): return os.getcwd()",  "/api/python/submit",   True),   # TC-232
>     ("import subprocess\ndef solve(n): return n",    "/api/python/submit",   True),   # TC-233
> ])
> ```

**TC-097 · import os rejected**
- Steps: `POST /api/python/run-code { code: "import os; os.listdir('/')" }`
- Expected: 400; error references disallowed import
- Tier: all

**TC-098 · import subprocess rejected**
- Steps: `POST /api/python/run-code { code: "import subprocess" }`
- Expected: 400
- Tier: all

**TC-099 · open() for file write rejected**
- Steps: `POST /api/python/run-code { code: "open('/tmp/pwned', 'w').write('x')" }`
- Expected: 400
- Tier: all

**TC-100 · Safe import math accepted**
- Steps: `POST /api/python/run-code { code: "import math\ndef solve(n): return math.sqrt(n)" }`
- Expected: not rejected by guard (200 or test-case error, not a guard 400)
- Tier: all

---

## 7. Pandas Execution

**Connection rules:** Pro user + easy Pandas question for all tests.

---

**TC-101 · Correct DataFrame output → correct: true**
- Preconditions: pro user; easy Pandas question with known correct solution
- Steps: `POST /api/python-data/run-code { question_id, code: <correct> }`; then `POST /api/python-data/submit { question_id, code: <correct> }`
- Expected: run-code returns at least one passing test; submit returns `correct: true` + solution
- Tier: all (easy for Free)

**TC-102 · Wrong DataFrame values (same shape) → correct: false**
- Steps: `POST /api/python-data/submit { code: <returns correct shape but wrong values> }`
- Expected: `correct: false`; feedback present
- Tier: all

**TC-103 · Wrong DataFrame shape → correct: false**
- Steps: submit code that returns a DataFrame with extra or missing columns
- Expected: `correct: false`
- Tier: all

**TC-104 · 5-second timeout enforced in Pandas sandbox**
- Steps: `POST /api/python-data/run-code { code: "import time; time.sleep(10)" }`
- Expected: timeout error; completes within ~7 seconds wall-clock
- Tier: all

**TC-105 · import pandas accepted by Python guard**
- Steps: `POST /api/python-data/run-code { code: "import pandas as pd\ndef solve(df): return df.head()" }`
- Expected: guard passes (200 or test failure, not guard rejection)
- Tier: all

---

## 8. PySpark MCQ

**Connection rules:** Free user + easy PySpark question.

---

**TC-106 · Correct option → correct: true + explanation always returned**
- Preconditions: free user; easy PySpark question; look up `correct_option` from catalog module
- Steps: `POST /api/pyspark/submit { question_id, selected_option: <correct_option> }`
- Expected: 200; `correct: true`; `explanation` non-null string
- Tier: all

**TC-107 · Wrong option → correct: false + explanation still returned**
- Steps: `POST /api/pyspark/submit { selected_option: (correct_option + 1) % 4 }`
- Expected: `correct: false`; `explanation` non-null (always returned)
- Tier: all

**TC-108 · Invalid option index (e.g., 5) → 422**
- Steps: `POST /api/pyspark/submit { selected_option: 5 }`
- Expected: 422 validation error
- Tier: all

**TC-109 · No DuckDB or subprocess invoked for PySpark submission**
- Verify by submitting and confirming the request completes in < 100 ms (no execution overhead)
- Expected: response time < 200 ms; no subprocess or DuckDB query logged
- Tier: all

---

## 9. Sample Mode

**Connection rules:** No login required. Each test verifies isolation from challenge progress.

---

**TC-110 · Anonymous user can access sample questions (no session required)**
- Preconditions: fresh client, no cookies at all
- Steps: `GET /api/sample/sql/easy`
- Expected: 200; question with `id`, `title`, `prompt` returned
- Tier: all (anonymous)

**TC-111 · Second call returns a different question (seen tracking)**
- Steps: `GET /api/sample/sql/easy` twice
- Expected: second response has a different `id` than the first
- Tier: all

**TC-112 · After all 3 easy SQL samples seen → 409**
- Steps: `GET /api/sample/sql/easy` three times (3 sample questions per difficulty per track)
- Expected: fourth call returns 409
- Tier: all

**TC-113 · POST /api/sample/sql/{difficulty}/reset clears seen state**
- Steps: exhaust all 3 easy samples (TC-112); `POST /api/sample/sql/easy/reset`; `GET /api/sample/sql/easy`
- Expected: reset returns 200; subsequent GET returns a question again (not 409)
- Tier: all

**TC-114 · Sample run-query executes without recording challenge progress**
- Steps: `POST /api/sample/sql/run-query { query: "SELECT 1" }`; then check `user_progress` table for any row
- Expected: run returns 200 with rows; `user_progress` is empty for this user
- Tier: all

**TC-115 · Sample submit returns verdict without recording challenge progress**
- Steps: `POST /api/sample/sql/submit { question_id, query: <correct> }`; check `user_progress`
- Expected: verdict returned (correct or incorrect); no row inserted in `user_progress`
- Tier: all

**TC-116 · Cross-track isolation: SQL seen does not affect Python seen count**
- Steps: exhaust all SQL easy samples; `GET /api/sample/python/easy`
- Expected: 200 (Python easy sample still available)
- Tier: all

**TC-117 · All 4 sample tracks are accessible (sql, python, python-data, pyspark)**
- Steps: `GET /api/sample/sql/easy`, `GET /api/sample/python/easy`, `GET /api/sample/python-data/easy`, `GET /api/sample/pyspark/easy`
- Expected: all four return 200 with different question schemas appropriate to their track
- Tier: all

**TC-118 · Sample run-code for python-data executes Pandas code**
- Steps: `POST /api/sample/python-data/run-code { question_id, code: <valid pandas code> }`
- Expected: 200 with test results
- Tier: all

---

## 10. Learning Paths

**Connection rules:** Use `_make_user` for plan-gated tests; anon for basic list tests.

---

**TC-119 · GET /api/paths returns all 22 paths**
- Preconditions: authenticated user (any plan)
- Steps: `GET /api/paths`
- Expected: 200; `paths` array length == 22; each path has `slug`, `title`, `topic`, `solved_count`
- Tier: all

**TC-120 · GET /api/paths/{slug} returns question list with per-question state**
- Preconditions: free user; use a free/starter path slug
- Steps: `GET /api/paths/{slug}`
- Expected: 200; body contains `questions` array; each question has `state` field with value `"solved"`, `"unlocked"`, or `"locked"`; `completed` field present
- Tier: Free

**TC-121 · Unknown path slug returns 404**
- Steps: `GET /api/paths/this-slug-does-not-exist`
- Expected: 404
- Tier: all

**TC-122 · Completed path shows completed: true and solved_count == total**
- Preconditions: user has solved all questions in a path (insert via `_insert_progress`)
- Steps: `GET /api/paths/{slug}`
- Expected: `completed: true`; `solved_count` equals `questions` array length
- Tier: all

**TC-123 · In-progress path shows correct solved_count**
- Preconditions: user has solved 2 out of N questions in a path
- Steps: `GET /api/paths/{slug}`
- Expected: `solved_count == 2`; `completed: false`
- Tier: all

**TC-124 · solved_count in GET /api/paths list matches individual path endpoint**
- Steps: GET list (TC-119); pick a path with solves; GET detail (TC-120) for same path
- Expected: `solved_count` matches between list and detail responses
- Tier: all

---

## 11. Mock Interviews

**Connection rules:** All mock tests require authenticated users. Use PySpark MCQ as the
default track (deterministic: look up `correct_option` from catalog; wrong = `(correct + 1) % 4`).
For plan-gate tests, seed via `_make_user(plan=...)`.

---

### 11A. compute_mock_access — pure unit tests

**TC-125 · Free user, easy difficulty → can_start: true**
- Steps (unit): `compute_mock_access("free", "sql", "easy", medium_unlocked=False)`
- Expected: `can_start: True`; `daily_limit: None`
- Tier: Free

**TC-126 · Free user, medium, medium NOT unlocked in practice → block_reason: not_unlocked**
- Steps (unit): `compute_mock_access("free", "sql", "medium", medium_unlocked=False)`
- Expected: `can_start: False`; `block_reason: "not_unlocked"`; `needs_upgrade: "pro"`
- Tier: Free

**TC-127 · Free user, medium, medium IS unlocked → can_start: true, daily_limit: 1**
- Steps (unit): `compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=0)`
- Expected: `can_start: True`; `daily_limit: 1`; `daily_used: 0`
- Tier: Free

**TC-128 · Free user, medium, daily limit reached → block_reason: daily_cap**
- Steps (unit): `compute_mock_access("free", "sql", "medium", medium_unlocked=True, daily_medium_used=1)`
- Expected: `can_start: False`; `block_reason: "daily_cap"`
- Tier: Free

**TC-129 · Free user, hard → block_reason: plan_locked, needs_upgrade: pro**
- Steps (unit): `compute_mock_access("free", "sql", "hard", medium_unlocked=True)`
- Expected: `can_start: False`; `block_reason: "plan_locked"`; `needs_upgrade: "pro"`
- Tier: Free

**TC-130 · Pro user, hard, daily_hard_used=2 → can_start: true (limit is 3)**
- Steps (unit): `compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=2)`
- Expected: `can_start: True`; `daily_limit: 3`; `daily_used: 2`
- Tier: Pro

**TC-131 · Pro user, hard, daily_hard_used=3 → block_reason: daily_cap**
- Steps (unit): `compute_mock_access("pro", "sql", "hard", medium_unlocked=True, daily_hard_used=3)`
- Expected: `can_start: False`; `block_reason: "daily_cap"`; `needs_upgrade: "elite"`
- Tier: Pro

**TC-132 · Elite user, hard → can_start: true, daily_limit: None (unlimited)**
- Steps (unit): `compute_mock_access("elite", "sql", "hard", medium_unlocked=True)`
- Expected: `can_start: True`; `daily_limit: None`
- Tier: Elite

**TC-133 · Company filter: non-Elite user → block_reason: plan_locked, needs_upgrade: elite**
- Steps (unit): `compute_mock_access("pro", "sql", "easy", medium_unlocked=True, company_filter=True)`
- Expected: `can_start: False`; `block_reason: "plan_locked"`; `needs_upgrade: "elite"`
- Tier: Free/Pro

**TC-134 · Company filter: Elite user → can_start: true**
- Steps (unit): `compute_mock_access("elite", "sql", "easy", medium_unlocked=True, company_filter=True)`
- Expected: `can_start: True`
- Tier: Elite

---

### 11B. Session lifecycle

> **⚡ PARAMETRIZE:** TC-125–134 all call `compute_mock_access(...)` (pure unit function).
> Implement as one parametrized test:
> ```python
> @pytest.mark.parametrize("plan,difficulty,medium_unlocked,daily_used,company_filter,expected_can_start,expected_block_reason", [
>     ("free",  "easy",   False, 0, False, True,  None),            # TC-125
>     ("free",  "medium", False, 0, False, False, "not_unlocked"),  # TC-126
>     ("free",  "medium", True,  0, False, True,  None),            # TC-127
>     ("free",  "medium", True,  1, False, False, "daily_cap"),     # TC-128
>     ("free",  "hard",   True,  0, False, False, "plan_locked"),   # TC-129
>     ("pro",   "hard",   True,  2, False, True,  None),            # TC-130
>     ("pro",   "hard",   True,  3, False, False, "daily_cap"),     # TC-131
>     ("elite", "hard",   True,  0, False, True,  None),            # TC-132
>     ("pro",   "easy",   True,  0, True,  False, "plan_locked"),   # TC-133
>     ("elite", "easy",   True,  0, True,  True,  None),            # TC-134
> ])
> ```

> **Valid `mode` values:** `"30min"` (2 questions, 1800 s) · `"60min"` (3 questions, 3600 s) · `"custom"` (1–5 questions, 10–90 min).
> Any other value returns 400. These are the **API wire values** — the UI labels "Quick" / "Full" map to `"30min"` / `"60min"` respectively.
>
> **`company_filter` type:** `string | null` (e.g. `"Meta"`). It is NOT a list.
> **`focus_concepts` type:** `string[] | null` (1–3 items). Elite only.
>
> **HTTP body shape on 403/400 from `/start`:** FastAPI `{"detail": "..."}` (plain string).
> `block_reason` and `needs_upgrade` are only present in `GET /api/mock/access` responses
> and the `compute_mock_access` pure-function return value (TC-125–TC-134).

> **⚡ PARAMETRIZE:** TC-135 and TC-136 verify `/start` response shape for each mode.
> Implement as a single parametrized test:
> ```python
> @pytest.mark.parametrize("mode,num_q_param,expected_questions,expected_time", [
>     ("30min",  None, 2, 1800),  # TC-135
>     ("60min",  None, 3, 3600),  # TC-135 extended
>     ("custom", 3,    3, 1800),  # TC-136
> ])
> ```

**TC-135 · POST /api/mock/start returns correct structure for each mode**
- Preconditions: Pro user for 30min/60min; Elite for custom; PySpark medium questions available
- Steps: `POST /api/mock/start` with given `mode` (and `num_questions` when custom)
- Expected: 201; body has `session_id` (UUID), `questions` array length == `expected_questions`, `time_limit_s` == `expected_time`
- Tier: Pro (30min/60min), Elite (custom)

**TC-137 · num_questions out of range (0 or 6) → 400**
- Steps: `POST /api/mock/start { mode: "custom", track: "pyspark", difficulty: "easy", num_questions: 0, time_minutes: 30 }` and separately `num_questions: 6`
- Expected: 400 (FastAPI `HTTPException`, not Pydantic 422); `detail` references the 1–5 constraint
- Tier: Elite

**TC-138 · POST /api/mock/{id}/submit mid-session returns verdict without solution**
- Preconditions: active session from TC-135; look up correct_option for first question
- Steps: `POST /api/mock/{id}/submit { question_id, selected_option: correct_option }`
- Expected: 200; `correct: true` or `correct: false` (correct if correct_option was used); `solution` field absent or null
- Tier: Pro

**TC-139 · POST /api/mock/{id}/finish returns full summary with solutions revealed**
- Preconditions: active session with at least one question answered
- Steps: `POST /api/mock/{id}/finish`
- Expected: 200; body contains `solved_count`, `total_count`, `time_used_s`; each question in `questions` array has `solution` present and non-null
- Tier: Pro

**TC-140 · GET /api/mock/{id} returns session state for reload recovery**
- Preconditions: active session
- Steps: `GET /api/mock/{id}`
- Expected: 200; body contains session metadata and current state; answered questions tracked
- Tier: Pro

**TC-141 · GET /api/mock/history returns last 20 sessions**
- Preconditions: Elite user with 21 completed mock sessions (insert directly via DB)
- Steps: `GET /api/mock/history`
- Expected: 200; `sessions` array length == 20
- Tier: all (returns empty list for users with no history)

**TC-142 · Session cannot be submitted to after finish**
- Steps: finish a session (TC-139); then `POST /api/mock/{id}/submit { question_id, selected_option: 0 }`
- Expected: 404 or 400
- Tier: Pro

**TC-171 · DELETE /api/mock/{id} within 2 minutes discards session**
- Preconditions: pro user; active session started within the last 2 minutes
- Steps: `DELETE /api/mock/{id}`
- Expected: 204; subsequent `GET /api/mock/{id}` returns 404
- Tier: Pro

**TC-252 · DELETE /api/mock/{id} more than 2 minutes after start → 403**
- Preconditions: pro user; active session whose `started_at` is more than 2 minutes ago (manipulate via DB)
- Steps: `DELETE /api/mock/{id}`
- Expected: 403
- Tier: Pro

**TC-253 · DELETE /api/mock/{id} on completed session → 403**
- Preconditions: pro user; completed session
- Steps: `DELETE /api/mock/{id}`
- Expected: 403
- Tier: Pro

**TC-254 · Different user submitting to another user's session → 404**
- Preconditions: user A starts a session; user B is logged in (separate client)
- Steps: user B calls `POST /api/mock/{session_A_id}/submit { question_id, selected_option: 0 }`
- Expected: 404; body references "Session not found" (not "Forbidden" — ownership is opaque)
- Tier: all

**TC-255 · GET /api/mock/{id} returns 404 for a session owned by a different user**
- Preconditions: same setup as TC-254
- Steps: user B calls `GET /api/mock/{session_A_id}`
- Expected: 404
- Tier: all

**TC-256 · Submitting a question not in the session → 400**
- Preconditions: active session; pick a valid question ID that is NOT in the session's question list
- Steps: `POST /api/mock/{id}/submit { question_id: <outside_session>, selected_option: 0 }`
- Expected: 400; body references question not in session
- Tier: all

**TC-257 · Finish is idempotent (second call returns 200)**
- Preconditions: active session
- Steps: `POST /api/mock/{id}/finish`; then `POST /api/mock/{id}/finish` again
- Expected: both calls return 200; response payloads are equivalent
- Tier: all

---

### 11C. Plan gates — HTTP level

**TC-143 · Free user starting a hard mock → 403**
- Preconditions: free user
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "hard" }`
- Expected: 403; body has `detail` string referencing Pro requirement (e.g. contains "Pro")
- Note: `/start` returns FastAPI's `{"detail": "..."}` shape; `block_reason`/`needs_upgrade` are only present in the `/api/mock/access` response and the `compute_mock_access` unit tests (TC-125–TC-134)
- Tier: Free

**TC-144 · Pro user starting a hard mock → 201**
- Preconditions: pro user
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "hard" }`
- Expected: 201
- Tier: Pro

**TC-145 · Elite user starting a hard mock → 201**
- Preconditions: elite user
- Steps: same as TC-144
- Expected: 201
- Tier: Elite

---

### 11D. Daily limits — HTTP level

**TC-146 · Free user: second medium mock same day is blocked**
- Preconditions: free user with medium unlocked (25 easy solved via `_insert_progress`); one medium mock session already completed today (insert `mock_sessions` row via DB with today's date)
- Steps: `POST /api/mock/start { mode: "custom", track: "pyspark", difficulty: "medium", num_questions: 1, time_minutes: 30 }`
- Expected: 403; `detail` string references daily limit
- Tier: Free

**TC-147 · Pro user: 4th hard mock same day is blocked**
- Preconditions: pro user; 3 hard mock sessions already completed today
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "hard" }`
- Expected: 403; `detail` string references daily limit and Elite upgrade
- Tier: Pro

**TC-148 · Elite user: 4th hard mock same day is allowed (unlimited)**
- Preconditions: elite user; 3 hard mock sessions completed today
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "hard" }`
- Expected: 201
- Tier: Elite

---

### 11E. Company filter (Elite, SQL only)

**TC-149 · Non-Elite user with company_filter → 403**
- Preconditions: pro user
- Steps: `POST /api/mock/start { mode: "30min", track: "sql", difficulty: "easy", company_filter: "Meta" }`
- Expected: 403; detail string references Elite requirement
- Tier: Free/Pro

**TC-150 · Elite user with valid company filter → session created**
- Preconditions: elite user
- Steps: `POST /api/mock/start { mode: "30min", track: "sql", difficulty: "medium", company_filter: "Meta" }`
- Expected: 201; `questions` array contains only questions tagged with "Meta"
- Tier: Elite

---

### 11F. Focus mode (Elite)

**TC-151 · Non-Elite user with focus_concepts → 403**
- Preconditions: pro user
- Steps: `POST /api/mock/start { mode: "30min", track: "sql", difficulty: "medium", focus_concepts: ["window functions"] }`
- Expected: 403; `detail` references Elite requirement
- Tier: Free/Pro

**TC-152 · Elite user, >3 focus_concepts → 422**
- Preconditions: elite user
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "easy", focus_concepts: ["a", "b", "c", "d"] }`
- Expected: 422; `detail` references max 3 items
- Tier: Elite

**TC-153 · Elite user, 1–3 focus_concepts → session created**
- Preconditions: elite user
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "easy", focus_concepts: ["dataframe operations"] }`
- Expected: 201; session created
- Tier: Elite

**TC-154 · Focus fallback when pool too small → focus_fallback: true in response**
- Steps (unit): use `_select_questions` with a concept that matches fewer questions than requested; verify `(selected, True)` tuple returned
- Expected: `focus_fallback == True`; `selected` contains questions (full pool used)
- Tier: Elite

**TC-155 · Empty focus_concepts [] treated same as None (no filtering)**
- Steps (unit): `_select_questions` with `focus_concepts=[]`
- Expected: full pool used; `focus_fallback == False`
- Tier: Elite

**TC-258 · Multiple focus_concepts use OR logic (question matches any one concept)**
- Steps (unit): `_select_questions` with `focus_concepts=["window functions", "CTEs"]`; pool has questions tagged only with "window functions" and others only with "CTEs"
- Expected: questions tagged with either concept are included; the match is OR not AND
- Tier: Elite

**TC-259 · Focus concept matching is case-insensitive**
- Steps (unit): `_select_questions` with `focus_concepts=["Window Functions"]`; pool has questions tagged `"window functions"` (lowercase)
- Expected: those questions are selected (case mismatch does not exclude them)
- Tier: Elite

**TC-260 · lifetime_elite can use focus_concepts**
- Preconditions: lifetime_elite user
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "easy", focus_concepts: ["dataframe operations"] }`
- Expected: 201 (not 403)
- Tier: lifetime_elite

**TC-261 · focus_fallback is always present in /start response**
- Preconditions: elite user; start a session with no focus_concepts
- Steps: `POST /api/mock/start { mode: "30min", track: "pyspark", difficulty: "easy" }`
- Expected: 201; response body contains `"focus_fallback"` key (value is `false` when no focus filter applied)
- Tier: Elite

---

### 11G. Mock pool and freshness

**TC-156 · mock_only questions appear in Pro/Elite sessions**
- Preconditions: pro user; SQL hard session started
- Steps: `POST /api/mock/start { track: "sql", difficulty: "hard", ... }`; inspect `questions` array
- Expected: at least some questions may have `mock_only: true` flag (or the pool draws from the mock-only bank)
- Note: verify indirectly by checking the question IDs overlap with `get_mock_questions_by_difficulty()` — not exposed on the API response, so test via unit test patching the pool.
- Tier: Pro/Elite

**TC-157 · Freshness scoring avoids recently-seen questions when alternatives exist**
- Steps (unit): seed `mocked_ids` with a set of recently-seen question IDs; call `_select_questions`
- Expected: selected questions do not contain recently-seen IDs (when pool is large enough)
- Tier: Pro/Elite

---

### 11H. Session debrief (Elite)

> **⚡ PARAMETRIZE:** TC-158–163 all call `POST /api/mock/{id}/finish` and check `debrief`.
> Use a single parametrized test with a custom session fixture:
> ```python
> @pytest.mark.parametrize("plan,correct,total,expected_debrief_null,expected_headline", [
>     ("elite", 1, 1, False, "Perfect"),   # TC-158
>     ("elite", 0, 1, False, "Tough"),     # TC-159
>     ("elite", 2, 3, False, "Solid"),     # TC-160
>     ("elite", 1, 3, False, "Partial"),   # TC-161
>     ("pro",   1, 1, True,  None),        # TC-162
>     ("free",  1, 1, True,  None),        # TC-163
> ])
> ```

**TC-158 · Finish response includes debrief for Elite (1/1 correct → "Perfect" headline)**
- Preconditions: elite user; custom session with 1 PySpark question; answer correctly
- Steps: finish session
- Expected: `debrief` in response; `debrief.headline` contains "Perfect"
- Tier: Elite

**TC-159 · 0/1 correct → "Tough" headline**
- Preconditions: elite user; 1-question session; answer incorrectly
- Steps: finish session
- Expected: `debrief.headline` contains "Tough"
- Tier: Elite

**TC-160 · 2/3 correct → "Solid" headline (≥67%)**
- Preconditions: elite user; 3-question session; 2 correct, 1 wrong
- Expected: `debrief.headline` contains "Solid"
- Tier: Elite

**TC-161 · 1/3 correct → "Partial" headline (34–66%)**
- Preconditions: elite user; 3-question session; 1 correct, 2 wrong
- Expected: `debrief.headline` contains "Partial"
- Tier: Elite

**TC-162 · debrief is null for Pro user**
- Preconditions: pro user; complete any session
- Steps: finish session
- Expected: `debrief: null` in response body
- Tier: Pro

**TC-163 · debrief is null for Free user**
- Preconditions: free user; complete any easy session
- Expected: `debrief: null`
- Tier: Free

**TC-164 · debrief contains patterns and priority_action fields**
- Preconditions: elite user; session with at least 2 questions of different concept outcomes
- Expected: `debrief.patterns` is an array (possibly empty); `debrief.priority_action` present (may be null)
- Tier: Elite

**TC-262 · debrief contains all documented keys**
- Preconditions: elite user; completed session
- Expected: `debrief` object contains exactly: `headline`, `patterns`, `priority_action`, `priority_path_slug`, `priority_path_title`, `priority_question_ids`; no undocumented internal keys present
- Tier: Elite

**TC-263 · Perfect session with ≤50% time used → time-to-spare headline variant**
- Preconditions: elite user; 1-question session; answer correctly in very short time (< 50% of time_limit_s)
- Steps: finish session
- Expected: `debrief.headline` references having time to spare (e.g. contains "time")
- Tier: Elite

**TC-264 · Session using nearly all time → time-pressure headline variant**
- Preconditions: elite user; session where `time_used_s` is close to `time_limit_s` (≥ 90%); manipulate via DB if needed
- Expected: `debrief.headline` references the time limit
- Tier: Elite

**TC-265 · patterns includes time-sink entry when one question dominates time (>55%)**
- Preconditions: elite user; 3-question session where one question consumed >55% of total time
- Expected: `debrief.patterns` contains an entry referencing time spent on that question
- Note: single-question sessions do NOT generate a time-sink pattern
- Tier: Elite

**TC-266 · priority_path_slug is present when weak concept maps to a learning path**
- Preconditions: elite user; weak concept that has a corresponding path (e.g. concept "window functions" maps to a SQL path)
- Expected: `debrief.priority_path_slug` is a non-null string; `debrief.priority_path_title` is a non-null string
- Tier: Elite

**TC-267 · priority_question_ids excludes questions already in the session**
- Preconditions: elite user; session contains question IDs X and Y; both X and Y are tagged with the weak concept
- Expected: `debrief.priority_question_ids` does NOT contain X or Y
- Tier: Elite

---

### 11I. Mock analytics (Elite)

**TC-165 · GET /api/mock/analytics returns 200 for Elite**
- Preconditions: elite user with at least 2 completed mock sessions
- Steps: `GET /api/mock/analytics`
- Expected: 200; body contains `total_sessions`, `sessions_last_30d`, `avg_score`, `best_score`, `avg_time_used_pct`, `score_trend`, `top_concepts`, `weak_concepts`, `track_breakdown`, `difficulty_breakdown`
- Note: `weak_concepts` in mock analytics requires **< 60% accuracy and ≥ 3 attempts** (different threshold from dashboard insights which uses < 50%); `top_concepts` is capped at 5 entries; `weak_concepts` capped at 3; `score_trend` is capped at the last 10 sessions in chronological order
- Tier: Elite

**TC-166 · GET /api/mock/analytics returns 403 for Pro**
- Preconditions: pro user
- Steps: `GET /api/mock/analytics`
- Expected: 403
- Tier: Pro

**TC-167 · GET /api/mock/analytics returns 403 for Free**
- Preconditions: free user
- Steps: `GET /api/mock/analytics`
- Expected: 403
- Tier: Free

**TC-168 · lifetime_elite can access mock analytics**
- Preconditions: lifetime_elite user (seeded via `POST /api/user/plan { new_plan: "lifetime_elite" }`)
- Steps: `GET /api/mock/analytics`
- Expected: 200
- Tier: lifetime_elite

---

### 11J. Solution visibility contract

**TC-169 · solution absent during session (submit endpoint)**
- Preconditions: active session
- Steps: `POST /api/mock/{id}/submit { question_id, selected_option }`
- Expected: response body does NOT contain `"solution"` key for the submitted question
- Tier: all

**TC-170 · solution present for all questions after finish**
- Preconditions: session with 2+ questions, some answered some not
- Steps: `POST /api/mock/{id}/finish`
- Expected: every entry in `questions` array has `solution` field present and non-null
- Tier: all

---

### 11K. Follow-up question injection

Some questions have a `follow_up_id` field. When a user answers such a question correctly
during a session, the follow-up question is injected into the session immediately after the
parent's position. This mechanic is tested via unit tests on the session-mutation logic plus
integration tests through the submit endpoint.

**TC-284 · Follow-up injection depends on correctness of the answer**
> **⚡ PARAMETRIZE:** TC-284 and TC-285 test the same path with different outcomes:
> ```python
> @pytest.mark.parametrize("is_correct,expect_inject", [
>     (True,  True),   # TC-284: correct → injected
>     (False, False),  # TC-285: wrong → not injected
> ])
> ```
- Preconditions: pro user; session contains question Q that has `follow_up_id = FU`; FU is a valid question ID
- Steps: `POST /api/mock/{id}/submit { question_id: Q, <correct or wrong answer> }` per parametrize row
- Expected: `follow_up_injected` matches `expect_inject`; subsequent `GET /api/mock/{id}` shows FU in session iff injected
- Tier: Pro

**TC-286 · Follow-up not injected when parent is the last question in the session**
- Preconditions: session where Q with `follow_up_id` is the last question
- Steps: answer Q correctly
- Expected: `follow_up_injected: false`; session question count unchanged
- Tier: Pro

**TC-287 · follow_up_injected is always present in submit response**
- Preconditions: active session; any question (with or without follow_up_id)
- Steps: `POST /api/mock/{id}/submit { question_id, <any answer> }`
- Expected: response body always contains `"follow_up_injected"` key as a boolean
- Tier: all

**TC-288 · Injected follow-up does not chain further (no recursive injection)**
- Preconditions: FU itself has a `follow_up_id`; Q is answered correctly (injecting FU); FU is answered correctly
- Steps: answer Q correctly, then answer FU correctly
- Expected: FU's own follow-up is NOT injected into the session (injection is one level deep only)
- Tier: Pro

---

## 12. Dashboard & Insights

**Connection rules:** Use `_make_user` for plan seeding. Use `_insert_submission` and
`_insert_progress` for deterministic data. `GET /api/dashboard/insights` is cached 60s
per user in-process — clear between test functions via `isolated_state`.

---

### 12A. Dashboard endpoint

**TC-172 · GET /api/dashboard returns track stats for all 4 tracks**
- Preconditions: pro user with solves in all 4 tracks (via `_insert_progress`)
- Steps: `GET /api/dashboard`
- Expected: 200; `tracks` contains entries for `sql`, `python`, `python-data`, `pyspark`; each has `by_difficulty` with `easy`, `medium`, `hard` sub-objects each having `solved` and `total`
- Tier: all

**TC-173 · python-data key is normalized (not python_data)**
- Steps: `GET /api/dashboard`
- Expected: track key is `"python-data"` (hyphen, not underscore) in the response
- Tier: all

**TC-174 · Unauthenticated GET /api/dashboard returns 401**
- Steps: `GET /api/dashboard` with no session
- Expected: 401
- Tier: all

**TC-175 · recent_activity is present and capped at 10 entries**
> **⚡ PARAMETRIZE:** TC-175 and TC-268 test presence and cap of `recent_activity`:
> ```python
> @pytest.mark.parametrize("num_submissions,expected_len", [
>     (1,  1),   # TC-175: present with 1 entry
>     (11, 10),  # TC-268: capped at 10
> ])
> ```
- Preconditions: user with `num_submissions` submissions (insert via `_insert_submissions_batch`)
- Steps: `GET /api/dashboard`
- Expected: `recent_activity` array present; `len(recent_activity) == expected_len`
- Tier: all

**TC-269 · concepts_by_track reflects solved question concepts**
> **⚡ PARAMETRIZE:** TC-269 and TC-270 test populated vs empty state:
> ```python
> @pytest.mark.parametrize("num_solves_with_concepts,expected_populated", [
>     (1, True),   # TC-269: at least one concept entry after a solve
>     (0, False),  # TC-270: empty for new user
> ])
> ```
- Preconditions: user with `num_solves_with_concepts` correct submissions on concept-tagged questions
- Steps: `GET /api/dashboard`
- Expected: `concepts_by_track` present; if `expected_populated`, contains at least one concept entry; if not, is empty
- Tier: all

---

### 12B. Insights — basic per-track stats

**TC-176 · GET /api/dashboard/insights returns per_track for all 4 tracks**
- Preconditions: pro user with solves in all 4 tracks
- Steps: `GET /api/dashboard/insights`
- Expected: 200; `per_track` has entries for sql, python, python-data, pyspark; each has `solve_count`, `median_solve_seconds`, `accuracy_pct`
- Tier: all

**TC-177 · median_solve_seconds is null when no correct submissions**
- Preconditions: user with only wrong submissions for a track
- Expected: `median_solve_seconds: null` for that track
- Tier: all

**TC-178 · accuracy_pct is computed as correct/total submissions (3 decimal places)**
- Preconditions: user with 2 correct + 2 wrong = 4 submissions on one track
- Expected: `accuracy_pct == 0.5` for that track
- Tier: all

**TC-179 · cross_track_insight is null when gap < 60 seconds between tracks**
- Preconditions: user with 2 tracks, both with median ~10s
- Expected: `cross_track_insight: null`
- Tier: all

**TC-180 · cross_track_insight is a non-null string when gap ≥ 60 seconds**
- Preconditions: insert submissions such that SQL median = 300s, Python median = 60s
- Expected: `cross_track_insight` is a string referencing the slow and fast track names
- Tier: all

**TC-181 · streak_days reflects consecutive days with correct submissions**
- Preconditions: insert correct submissions for today and yesterday (2 consecutive days)
- Expected: `streak_days == 2`
- Tier: all

---

### 12C. Insights — weakest concepts

**TC-182 · Concept with ≥ 3 attempts appears in weakest_concepts**
- Preconditions: insert 3 wrong submissions for questions tagged with the same concept
- Expected: that concept appears in `weakest_concepts` array (up to 3 entries)
- Tier: all

**TC-183 · Concept with < 3 attempts excluded**
- Preconditions: insert 2 submissions for a concept
- Expected: that concept does NOT appear in `weakest_concepts`
- Tier: all

**TC-184 · At most 3 weakest concepts returned**
- Preconditions: submit wrong answers for 5+ distinct concepts, each with ≥ 3 attempts
- Expected: `weakest_concepts` array length ≤ 3
- Tier: all

**TC-185 · Accuracy < 30% → summary contains "highest-priority gap"**
- Preconditions: 0 correct out of 3+ attempts for a concept
- Expected: `weakest_concepts[0].summary` contains "highest-priority gap"
- Tier: all

**TC-186 · Accuracy < 50% → summary contains "isn't sticking"**
- Preconditions: 1 correct out of 3 attempts (33%)
- Expected: summary contains "isn't sticking"
- Tier: all

**TC-187 · Accuracy 50–69% → summary contains "breaks under new angles"**
- Preconditions: 2 correct out of 4 attempts (50%)
- Expected: summary mentions "breaks under" or "new angles"
- Tier: all

**TC-188 · Accuracy ≥ 70% → summary contains "not fully consistent"**
- Preconditions: 3 correct out of 4 attempts (75%)
- Expected: summary contains "consistent"
- Tier: all

**TC-189 · recommended_question_ids excludes already-solved questions**
- Preconditions: user has solved question Q tagged with concept C; other questions with C exist
- Expected: Q does not appear in `recommended_question_ids` for concept C
- Tier: all

**TC-190 · Free user: recommended_question_ids limited to easy questions**
- Preconditions: free user; weakest concept has easy + medium + hard tagged questions
- Expected: `recommended_question_ids` contains only easy question IDs
- Tier: Free

**TC-191 · Pro/Elite: recommended_question_ids may include medium/hard**
- Preconditions: pro user; same weakest concept setup
- Expected: `recommended_question_ids` may contain medium or hard IDs
- Tier: Pro/Elite

---

### 12D. Elite-only insights gates

**TC-192 · Free user: readiness_scores is null, study_plan is null**
- Preconditions: free user
- Steps: `GET /api/dashboard/insights`
- Expected: `readiness_scores: null`; `study_plan: null`
- Tier: Free

**TC-193 · Pro user: readiness_scores is null, study_plan is null**
- Preconditions: pro user
- Expected: same as TC-192
- Tier: Pro

**TC-194 · Elite user: readiness_scores present for all 4 tracks**
- Preconditions: elite user with some solves
- Steps: `GET /api/dashboard/insights`
- Expected: `readiness_scores` is an object with keys `sql`, `python`, `python-data`, `pyspark`; each has `score` (int 0–100), `label` (string), `components` (with `practice`, `mock_accuracy`, `concept_strength`)
- Tier: Elite

**TC-195 · Elite user: study_plan present (3–5 items)**
- Preconditions: elite user with weak concepts and low coverage
- Expected: `study_plan` is an array, 3 ≤ length ≤ 5; each item has `type`, `title`, `description`, `cta_label`, `cta_href`, `track`, `priority`
- Tier: Elite

**TC-196 · study_plan action types are valid values**
- Expected: all `type` values in `study_plan` are one of: `concept_drill`, `learning_path`, `mock_session`, `practice_hard`
- Tier: Elite

**TC-197 · No duplicate (type, track) pairs in study_plan**
- Expected: no two items share the same `(type, track)` combination
- Tier: Elite

**TC-295 · study_plan items are ordered by priority ascending**
- Preconditions: elite user; DB state that generates multiple study_plan items with different priority values
- Steps: `GET /api/dashboard/insights`
- Expected: `study_plan` items are sorted by `priority` in ascending order (lowest integer first)
- Tier: Elite

**TC-296 · concept_drill cta_href starts with /practice/; learning_path cta_href contains /learn/**
- Preconditions: elite user; at least one `concept_drill` item and one `learning_path` item in study_plan
- Steps: `GET /api/dashboard/insights`
- Expected: items of `type: "concept_drill"` have `cta_href` starting with `/practice/`; items of `type: "learning_path"` have `cta_href` containing `/learn/`
- Tier: Elite

---

### 12E. Readiness score components (unit tests)

**TC-198 · Practice coverage component: 0 solves → 0 pts**
- Steps (unit): `_compute_readiness_scores` with no solved IDs
- Expected: `components.practice == 0.0`
- Tier: Elite

**TC-199 · Practice coverage component: 100% easy, 100% medium, 40% hard → ~40 pts**
- Steps (unit): solve all easy + all medium + 40% of hard for one track
- Expected: `components.practice` ≈ 40.0 (10 + 20 + 10)
- Tier: Elite

**TC-200 · Mock accuracy: no sessions → 0 pts**
- Expected: `components.mock_accuracy == 0.0`
- Tier: Elite

**TC-201 · Readiness label thresholds: <40 → "Early stage", 40–64 → "Building", 65–79 → "Getting there", 80–89 → "Interview ready", ≥90 → "Strong"**
- Steps (unit): test each boundary value
- Tier: Elite

---

### 12F. Caching

**TC-202 · Second call within 60s returns cached payload**
- Preconditions: insert a submission; call insights; insert another submission; call insights again within 1 second
- Expected: second response does NOT reflect the new submission (cache hit)
- Tier: all

**TC-203 · Cache is per-user (different users do not share cache)**
- Preconditions: two users A and B; call insights for A (populates A's cache); insert submissions for B; call insights for B
- Expected: B's response reflects B's data (not A's cached response)
- Tier: all

---

## 13. Submission History

**Connection rules:** Use `_insert_submission` for deterministic history.

---

**TC-204 · GET /api/submissions returns history for a question**
- Preconditions: user with 3 submissions for question Q (track=sql); insert via `_insert_submission`
- Steps: `GET /api/submissions?track=sql&question_id={Q}`
- Expected: 200; array of 3 items; each item has `is_correct`, `submitted_at`, `feedback`
- Tier: all

**TC-205 · limit param restricts returned records**
- Preconditions: user with 5 submissions for question Q
- Steps: `GET /api/submissions?track=sql&question_id={Q}&limit=2`
- Expected: array length == 2
- Tier: all

**TC-206 · Empty history returns empty array (not 404)**
- Preconditions: user with no submissions for question Q
- Steps: `GET /api/submissions?track=sql&question_id={Q}`
- Expected: 200; empty array `[]`
- Tier: all

**TC-207 · Unauthenticated returns 401**
- Steps: `GET /api/submissions?track=sql&question_id=1001` with no session
- Expected: 401
- Tier: all

---

## 14. Payments & Webhooks

**Connection rules:** Mock the Razorpay HTTP client entirely. Do not call the real Razorpay API.
Use `monkeypatch` or `patch` to replace `razorpay.Client` with a test double.
Use `_make_user` for authenticated user preconditions.

---

### 14A. Create order

**TC-208 · plan=pro → subscription response**
- Preconditions: free user; Razorpay client mocked
- Steps: `POST /api/razorpay/create-order { plan: "pro", currency: "INR" }`
- Expected: 200; body has `subscription_id` (non-null), `order_id: null`, `is_subscription: true`, `key_id`, `amount`, `currency: "INR"`
- Tier: Free → Pro

**TC-209 · plan=lifetime_pro → order response (one-time)**
- Steps: `POST /api/razorpay/create-order { plan: "lifetime_pro", currency: "INR" }`
- Expected: 200; body has `order_id` (non-null), `subscription_id: null`, `is_subscription: false`; `amount == 1199900` (₹11,999 in paise)
- Tier: all

**TC-210 · plan=lifetime_elite → order response with correct amount**
- Steps: `POST /api/razorpay/create-order { plan: "lifetime_elite", currency: "INR" }`
- Expected: `amount == 1999900` (₹19,999 in paise); `is_subscription: false`
- Tier: all

**TC-211 · Invalid plan → 422**
- Steps: `POST /api/razorpay/create-order { plan: "diamond" }`
- Expected: 422
- Tier: all

**TC-212 · Unauthenticated → 401**
- Steps: `POST /api/razorpay/create-order { plan: "pro" }` with no session
- Expected: 401
- Tier: all

**TC-271 · plan=free → 400**
- Steps: `POST /api/razorpay/create-order { plan: "free" }` (authenticated user)
- Expected: 400; error references invalid upgrade target
- Tier: all

**TC-272 · Downgrade attempt → 400**
- Preconditions: elite user
- Steps: `POST /api/razorpay/create-order { plan: "pro" }` (attempting to downgrade from elite)
- Expected: 400; error references invalid upgrade path
- Tier: Elite

**TC-273 · Razorpay SDK not installed or credentials not configured → 503**
- Preconditions: monkeypatch `RAZORPAY_KEY_ID=""` or patch `razorpay` import to raise ImportError
- Steps: `POST /api/razorpay/create-order { plan: "pro" }`
- Expected: 503; body has `"error"` referencing service unavailability
- Tier: all

**TC-274 · Multiple create-order calls for same user → Razorpay customer created only once**
- Preconditions: free user; Razorpay client mocked with a spy on `customer.create`
- Steps: call `POST /api/razorpay/create-order { plan: "lifetime_pro" }` twice
- Expected: `customer.create` called exactly once across both calls (deduplication)
- Tier: all

---

### 14B. Verify payment

**TC-213 · Valid HMAC for one-time order → plan upgraded immediately**
- Preconditions: free user; construct valid HMAC signature using test secret
- Steps: `POST /api/razorpay/verify-payment { plan: "lifetime_pro", razorpay_payment_id, razorpay_order_id, razorpay_signature }`
- Expected: 200; user plan updated to `"lifetime_pro"` in DB; `GET /api/auth/me` returns `plan: "lifetime_pro"`
- Tier: Free → lifetime_pro

**TC-214 · Valid HMAC for subscription → plan upgraded**
- Steps: same with subscription HMAC formula
- Expected: 200; plan upgraded to `"pro"`
- Tier: Free → Pro

**TC-215 · Invalid HMAC signature → 400**
- Steps: `POST /api/razorpay/verify-payment { razorpay_signature: "bogus" }`
- Expected: 400; plan NOT changed
- Tier: all

**TC-216 · Idempotent re-verification → 200 no-op (plan not re-applied)**
- Steps: verify once successfully; verify again with same `razorpay_payment_id`
- Expected: second call returns 200; no duplicate `payment_events` row inserted; plan unchanged (already upgraded)
- Tier: all

---

### 14C. Webhook

**TC-217 · payment.captured event with valid signature → plan applied**
- Steps: `POST /api/razorpay/webhook` with signed payload for `payment.captured`; body includes `user_id` and `plan`
- Expected: 200; user plan upgraded in DB
- Tier: all

**TC-218 · subscription.activated → plan upgraded**
- Steps: webhook payload for `subscription.activated`
- Expected: 200; plan set to subscription's plan
- Tier: all

**TC-219 · subscription.cancelled → plan downgraded to free**
- Preconditions: pro user with `plan="pro"`
- Steps: webhook for `subscription.cancelled` for that user's subscription
- Expected: 200; user plan becomes `"free"`
- Tier: Pro

**TC-220 · subscription.cancelled on lifetime_elite → plan NOT downgraded (lifetime protection)**
- Preconditions: user with `plan="lifetime_elite"`
- Steps: webhook for `subscription.cancelled`
- Expected: 200; plan remains `"lifetime_elite"` (lifetime variants are not downgraded by subscription events)
- Tier: lifetime_elite

**TC-221 · subscription.cancelled on lifetime_pro → plan NOT downgraded**
- Same as TC-220 for `"lifetime_pro"`
- Tier: lifetime_pro

**TC-222 · Invalid webhook signature → 400**
- Steps: `POST /api/razorpay/webhook` with `X-Razorpay-Signature: bogus`
- Expected: 400; no DB changes
- Tier: all

**TC-223 · Duplicate webhook event → idempotent 200 no-op**
- Steps: send same webhook event twice (same `payment_id`)
- Expected: second call returns 200; only one `payment_events` row exists for that payment_id
- Tier: all

**TC-275 · subscription.charged → plan preserved (monthly renewal)**
- Preconditions: pro user; their subscription is being renewed
- Steps: webhook for `subscription.charged` for that subscription
- Expected: 200; user plan remains `"pro"` (not downgraded)
- Tier: Pro

**TC-276 · subscription.halted → plan downgraded to free**
- Preconditions: pro user with `plan="pro"`
- Steps: webhook for `subscription.halted` for that user's subscription
- Expected: 200; user plan becomes `"free"`
- Tier: Pro

**TC-277 · Webhook with unknown user_id → graceful 200 no crash**
- Steps: `POST /api/razorpay/webhook` with valid signature; payload references a `user_id` that does not exist in the DB
- Expected: 200; no 5xx; no DB side-effects
- Tier: all

**TC-278 · payment.failed event → ignored, plan unchanged**
- Preconditions: free user
- Steps: webhook for `payment.failed` for that user
- Expected: 200 with `status: "ignored"` or similar; user plan unchanged (`"free"`)
- Tier: all

**TC-279 · Invalid target_plan in webhook payload → silently ignored**
- Steps: webhook with `payment.captured`; payload `target_plan: "diamond"` (not a valid plan)
- Expected: 200 with `status: "ignored"`; no DB plan changes
- Tier: all

---

## 15. Rate Limiting

**Connection rules:** Use `monkeypatch` to set low thresholds. Use `isolated_state` to ensure
rate-limiter state is reset between tests.

---

**TC-224 · Global rate limit: exceeding 60 req/60s per IP → 429**
- Preconditions: monkeypatch global limiter threshold to 3 requests
- Steps: make 4 identical requests to `GET /api/catalog`
- Expected: 4th request returns 429; body has `"error"` key
- Tier: all

**TC-225 · Auth rate limit: login attempts trigger auth-specific limit**
- Preconditions: monkeypatch `AUTH_RATE_LIMIT_REQUESTS` to 3
- Steps: POST /api/auth/login 4 times (with any credentials)
- Expected: 4th attempt returns 429 from auth limiter
- Tier: all

**TC-226 · Auth token-issue rate limit: magic-link and OAuth authorize share a separate bucket**
- Preconditions: monkeypatch `AUTH_TOKEN_ISSUE_RATE_LIMIT_REQUESTS` to 2
- Steps: POST /api/auth/magic-link 3 times
- Expected: 3rd attempt returns 429
- Tier: all

**TC-227 · Localhost bypasses global rate limit in non-production**
- Preconditions: TESTING=1 (default); request client is 127.0.0.1
- Steps: make 100 rapid requests to `GET /health`
- Expected: no 429 responses (localhost is exempt)
- Tier: all

**TC-228 · Rate limiter state is isolated between test modules**
- Verify that `_clear_rate_limit_state()` (called by `isolated_state`) resets all buckets
- Steps: exhaust rate limit; trigger `isolated_state` teardown/setup; repeat request
- Expected: first request after reset is not rate-limited
- Tier: all

**TC-241 · Rate-limit headers present on every response**
- Steps: `GET /api/catalog`
- Expected: response includes `X-RateLimit-Limit` and `X-RateLimit-Remaining` headers as numeric strings
- Tier: all

**TC-280 · Redis connection failure → rate limiter falls back to in-memory**
- Preconditions: monkeypatch `REDIS_URL` to an invalid/unreachable address
- Steps: create the rate limiter; make a request
- Expected: no crash; requests succeed; rate limiter operates with in-memory fallback
- Tier: all

---

## 16. Security Guards

**Connection rules:** Use a Pro user to avoid lock-gate interference on SQL/Python endpoints.

---

### 16A. SQL guard — submit endpoint variants

> The primary SQL guard tests (write rejection, CROSS JOIN, join count, dangerous functions) live
> in **§5C** (TC-085–090, TC-246–249) where they test the `/api/run-query` endpoint.
> The tests below verify that the **same guard also applies to `/api/submit`** (i.e. the guard
> is not bypassed by submitting a write or cartesian query directly without a prior run-query call).

**TC-281 · Cartesian join (CROSS JOIN) rejected by submit endpoint**
- Steps: `POST /api/submit { question_id, query: "SELECT * FROM users CROSS JOIN orders" }`
- Expected: 400; same guard response as TC-246
- Tier: all

**TC-282 · Too-many-joins (≥ 5 joins) rejected by submit endpoint**
- Steps: `POST /api/submit { question_id, query: <query with 5 JOINs> }`
- Expected: 400; same guard response as TC-248
- Tier: all

**TC-283 · Dangerous DuckDB functions rejected by submit endpoint**
- Steps (parametrized): `POST /api/submit { question_id, query: "SELECT * FROM read_csv('/etc/passwd')" }` (and similarly for other dangerous functions per TC-249)
- Expected: 400; guard rejects before execution
- Tier: all

---

### 16B. Python guard — submit endpoint variants

> The primary Python guard tests live in **§6C** (TC-097–100) where they test `/api/python/run-code`.
> The tests below verify the guard also applies to `/api/python/submit`.

**TC-232 · import os rejected in Python submit**
- Steps: `POST /api/python/submit { question_id, code: "import os\ndef solve(n): return os.getcwd()" }`
- Expected: 400
- Tier: all

**TC-233 · import subprocess rejected in Python submit**
- Steps: `POST /api/python/submit { code: "import subprocess\ndef solve(n): return n" }`
- Expected: 400
- Tier: all

---

### 16C. CSRF

**TC-237 · Production mode: mutating request without Origin header → 403**
- Preconditions: monkeypatch `IS_PROD=True`, `_CSRF_ALLOWED_ORIGINS={"https://app.example.com"}`; active session cookie present
- Steps: `POST /api/auth/logout` with no `Origin` header
- Expected: 403
- Tier: all

**TC-238 · Production mode: mutating request with valid Origin → allowed**
- Preconditions: same as TC-237
- Steps: `POST /api/auth/logout` with `Origin: https://app.example.com`
- Expected: 200
- Tier: all

**TC-239 · Non-production mode: mutating request without Origin → allowed (CSRF disabled)**
- Preconditions: TESTING=1 (default, IS_PROD=False)
- Steps: `POST /api/auth/logout` with no `Origin`
- Expected: 200 (CSRF check skipped)
- Tier: all

---

## 17. Content & Static Integrity

**Connection rules:** These are read-only integrity checks that run entirely through Python
without any HTTP calls. They verify that the shipped question content is internally consistent
and executes without error. Mark the module with `pytestmark = pytest.mark.usefixtures("isolated_state")`.

---

### 17A. SQL expected_query execution

**TC-289 · All SQL challenge expected_query execute without error**
- Steps (parametrized over every entry in `questions.py` catalog): execute `question["expected_query"]` against the live DuckDB engine via `database.execute_query()`
- Expected: no exception raised; result is a non-empty list (or empty list — not an exception)
- Tier: static

**TC-290 · All SQL sample expected_query execute without error**
- Steps (parametrized over every entry in `sample_questions.py` catalog): execute `question["expected_query"]`
- Expected: no exception raised
- Tier: static

---

### 17B. Learning path integrity

**TC-291 · Exactly 22 paths with correct track distribution**
- Steps: load all paths via `path_loader.load_all_paths()` (or equivalent)
- Expected: 22 paths total; SQL: 7, Python: 5, Pandas (python-data): 5, PySpark: 5
- Tier: static

**TC-292 · Each track has exactly one `starter` path and one `intermediate` path**
- Steps: group loaded paths by `(track, shortcut_type)` where `shortcut_type` in ("starter", "intermediate")
- Expected: each of the 4 tracks has exactly one entry per shortcut type (4 × 2 = 8 total shortcut paths)
- Tier: static

**TC-293 · All question IDs referenced in any path exist in their track's catalog**
- Steps: for each path, load its `questions` array; look up each question ID in the correct track's catalog loader
- Expected: no missing IDs; every referenced question_id exists in the track catalog
- Tier: static

**TC-294 · Each path's slug matches its JSON filename**
- Steps: for each path file at `content/paths/*.json`, load it; compare `path["slug"]` to the filename stem
- Expected: `path["slug"] == filename_without_extension` for every file
- Tier: static

---

## Appendix A: Test Case Index by Plan Tier

| Plan tier | TC numbers |
|-----------|-----------|
| All tiers | TC-001–005, TC-006–007, TC-017, TC-024, TC-027, TC-028–032, TC-033, TC-038, TC-039–043, TC-069, TC-074, TC-075–090, TC-091–100, TC-101–118, TC-119–124, TC-169–170, TC-207, TC-211–212, TC-222–228, TC-229–239, TC-240–241, TC-268–270, TC-271, TC-273, TC-277–279, TC-280, TC-287 |
| Free | TC-008–016, TC-018–023, TC-025–026, TC-044–058, TC-059–062, TC-125–129, TC-133, TC-143, TC-146, TC-149, TC-151, TC-163, TC-167, TC-174, TC-192 |
| Pro | TC-063, TC-065, TC-073, TC-130–131, TC-135–138, TC-144, TC-147, TC-162, TC-166, TC-193, TC-208, TC-213–216, TC-219, TC-284–288 |
| Elite | TC-064, TC-132, TC-134, TC-145, TC-148, TC-150, TC-153–161, TC-164–165, TC-168, TC-194–201, TC-210, TC-242, TC-243–245, TC-258–261, TC-262–267, TC-295–296 |
| lifetime_pro | TC-066, TC-068, TC-209, TC-221 |
| lifetime_elite | TC-067, TC-068, TC-168, TC-220, TC-260 |
| Static (no HTTP) | TC-289–294 |

---

## Appendix B: Cross-Reference Map

| Feature | Spec source | TC numbers |
|---------|-------------|-----------|
| Unlock thresholds (code tracks) | `unlock.py`, CLAUDE.md | TC-044–052 |
| Unlock thresholds (PySpark) | `unlock.py`, CLAUDE.md | TC-053–058 |
| Path shortcuts | `unlock.py`, CLAUDE.md | TC-059–062 |
| Hard cap (code: 8, PySpark: 5) | `unlock.py` FREE_HARD_CAP_* | TC-050, TC-058 |
| Lifetime plan normalization | `unlock.py` normalize_plan | TC-066–068 |
| mock_only exclusion from catalog | CLAUDE.md content footprint | TC-072, TC-156 |
| SQL read-only guard | `sql_guard.py` | TC-085–090, TC-229–231, TC-246–251 |
| SQL cartesian/implicit-product guard | `sql_guard.py` | TC-246–247, TC-281 |
| SQL join count limit (≥5) | `sql_guard.py` | TC-248, TC-282 |
| SQL dangerous DuckDB functions | `sql_guard.py` | TC-249, TC-283 |
| run-query on locked question | `routers/questions.py` | TC-250 |
| run-query on nonexistent question | `routers/questions.py` | TC-251 |
| Python AST guard | `python_guard.py` | TC-097–100, TC-232–236 |
| 3-second SQL timeout | CLAUDE.md, evaluator.py | TC-078 |
| 5-second Python/Pandas timeout | CLAUDE.md | TC-093, TC-104 |
| 200-row cap | CLAUDE.md | TC-076 |
| structure_correct field | `evaluator.py` | TC-243–245 |
| required_concepts enforcement | question JSON + evaluator | TC-244–245 |
| Close-miss feedback | CLAUDE.md backend behavior | TC-082 |
| Repeat-attempt nudge | CLAUDE.md backend behavior | TC-083 |
| Quality object on correct submit | CLAUDE.md backend behavior | TC-079 |
| Anonymous-first identity | CLAUDE.md identity model | TC-006–007, TC-018 |
| Login merges anon progress | CLAUDE.md identity model | TC-018 |
| Login lockout | CLAUDE.md auth hardening | TC-039, TC-242 |
| CSRF mitigation | CLAUDE.md auth hardening | TC-040–041, TC-237–239 |
| Non-enumeration (forgot-password) | CLAUDE.md backend behavior | TC-024 |
| OAuth state single-use | CLAUDE.md OAuth hardening | TC-036 |
| Magic link single-use | auth.py | TC-031 |
| Session cookie SameSite=Lax | CLAUDE.md auth | TC-240 |
| X-RateLimit-* headers | `rate_limiter.py` | TC-241 |
| Session debrief plan gates | `docs/features/mock.md` | TC-158–164, TC-262–267 |
| Debrief time-to-spare headline | `routers/mock.py` | TC-263 |
| Debrief time-pressure headline | `routers/mock.py` | TC-264 |
| Debrief time-sink pattern | `routers/mock.py` | TC-265 |
| Debrief priority_path_slug | `routers/mock.py` | TC-266 |
| Debrief priority_question_ids | `routers/mock.py` | TC-267 |
| Mock analytics plan gates | `docs/features/mock.md` | TC-165–168 |
| Mock analytics weak_concepts threshold | `routers/mock.py` (< 60%) | TC-165 (note) |
| Mock analytics top_concepts cap | `routers/mock.py` (max 5) | TC-165 (note) |
| Company filter (Elite SQL only) | `docs/features/mock.md` | TC-133–134, TC-149–150 |
| Focus mode (Elite only) | `docs/features/mock.md` | TC-151–155, TC-258–261 |
| Focus concept OR logic | `routers/mock.py` | TC-258 |
| Focus concept case-insensitive | `routers/mock.py` | TC-259 |
| focus_fallback always in response | `routers/mock.py` | TC-261 |
| Mock session ownership | `routers/mock.py` | TC-254–255 |
| Mock session DELETE endpoint | CLAUDE.md API table | TC-171, TC-252–253 |
| Submit to other user's session | `routers/mock.py` | TC-254 |
| Finish idempotency | `routers/mock.py` | TC-257 |
| Follow-up injection | `routers/mock.py` | TC-284–288 |
| Mock daily limits | `unlock.py` MOCK_DAILY_LIMITS | TC-125–132, TC-146–148 |
| Dashboard recent_activity cap | `routers/dashboard.py` | TC-268 |
| Dashboard concepts_by_track | `routers/dashboard.py` | TC-269–270 |
| Dashboard insights caching (60s) | `routers/insights.py` | TC-202–203 |
| Readiness score formula | `routers/insights.py` | TC-198–201 |
| Study plan (Elite only) | `routers/insights.py` | TC-195–197, TC-295–296 |
| Study plan ordering by priority | `routers/insights.py` | TC-295 |
| Study plan cta_href patterns | `routers/insights.py` | TC-296 |
| Weakest concepts (≥3 attempts) | `routers/insights.py` | TC-182–183 |
| Recency-weighted concept accuracy | `routers/insights.py` | (see TC-182–191 setup notes) |
| Streak logic | `db.py`, `routers/insights.py` | TC-042–043, TC-181 |
| Razorpay plan=free rejected | `routers/razorpay.py` | TC-271 |
| Razorpay downgrade rejected | `routers/razorpay.py` | TC-272 |
| Razorpay SDK not configured → 503 | `routers/razorpay.py` | TC-273 |
| Razorpay customer deduplication | `routers/razorpay.py` | TC-274 |
| Webhook idempotency | `docs/features/pricing.md` | TC-216, TC-223 |
| Webhook subscription.charged | `routers/razorpay.py` | TC-275 |
| Webhook subscription.halted | `routers/razorpay.py` | TC-276 |
| Webhook unknown user | `routers/razorpay.py` | TC-277 |
| Webhook payment.failed ignored | `routers/razorpay.py` | TC-278 |
| Webhook invalid target_plan | `routers/razorpay.py` | TC-279 |
| Lifetime subscription protection | `docs/features/pricing.md` | TC-220–221 |
| Rate limiter Redis fallback | `rate_limiter.py` | TC-280 |
| Sample mode: no challenge progress | CLAUDE.md | TC-114–115 |
| Sample exhaustion (409) | CLAUDE.md | TC-112 |
| Error shape { error, request_id } | CLAUDE.md | TC-004 |
| X-Request-ID on all responses | CLAUDE.md | TC-002 |
| X-Response-Time-Ms on all responses | CLAUDE.md | TC-003 |
| SQL expected_query execution | `questions.py`, DuckDB | TC-289–290 |
| Learning path count and distribution | `path_loader.py`, CLAUDE.md | TC-291 |
| Path shortcut type uniqueness | `path_loader.py`, CLAUDE.md | TC-292 |
| Path question ID validity | `path_loader.py` | TC-293 |
| Path slug matches filename | `path_loader.py` | TC-294 |
