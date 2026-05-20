# Platform Backlog

Consolidated backlog for features deferred from the main roadmap. Remove items as they ship; update `docs/` and `CLAUDE.md` in the same commit.

---

## Phase 1 — Trial Pro (7-day free trial)

**What it is:** A 7-day free trial of the Pro plan, available once per verified email account. No credit card or phone number required. Trial users get full Pro access (`plan = 'pro'`). After 7 days the account auto-downgrades to `free`. Configurable duration via `TRIAL_DURATION_DAYS` env var (default: 7). Pro only — not Elite.

**Abuse tolerance strategy:** Email-only gating with three mitigations: (1) disposable email domain blocklist at registration + trial start, (2) Gmail canonical normalization to block `+suffix`/dot tricks, (3) IP rate limit of 1 trial activation per IP per 24 hours. Accepted risk: a user with multiple real email addresses can get multiple trials. This is a deliberate product decision — friction cost of phone OTP outweighs abuse risk for this product type.

---

#### 1. Database migration

New file: `backend/alembic/versions/20260513_000001_add_trial_and_email_canonical.py`

Add the following columns to the `users` table (all backwards-compatible, safe to deploy before code):

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_trial          BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_expires_at  TIMESTAMPTZ NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS trial_used        BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_canonical   TEXT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_canonical ON users (email_canonical)
  WHERE email_canonical IS NOT NULL;
```

- `is_trial`: true while the user is on an active trial.
- `trial_expires_at`: UTC timestamp when the trial ends. NULL for non-trial users.
- `trial_used`: set to true when a trial is activated; never reset. Prevents re-trialling.
- `email_canonical`: normalized email (lowercase, Gmail dot-stripping, `+suffix` removal). UNIQUE partial index (only rows where not NULL). Populated for all new registrations going forward; existing rows stay NULL (they're grandfathered, can still trial).

Backfill existing rows is intentionally skipped — existing users without `email_canonical` are not blocked from trialling. Only new registrations get the deduplication protection.

---

#### 2. Configuration

`backend/config.py` — add one field to the `Settings` class:

```python
TRIAL_DURATION_DAYS: int = Field(default=7, env="TRIAL_DURATION_DAYS")
```

Import and use `settings.TRIAL_DURATION_DAYS` in the trial activation logic. Do not hardcode 7 anywhere in the code.

---

#### 3. Disposable email blocklist

New file: `backend/disposable_domains.py`

```python
import os

_DOMAINS: set[str] = set()

def _load() -> set[str]:
    path = os.path.join(os.path.dirname(__file__), "disposable_domain_list.txt")
    with open(path) as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}

def is_disposable_email(email: str) -> bool:
    global _DOMAINS
    if not _DOMAINS:
        _DOMAINS = _load()
    domain = email.lower().split("@")[-1]
    return domain in _DOMAINS
```

New file: `backend/disposable_domain_list.txt`
Source from https://github.com/disposable-email-domains/disposable-email-domains (the raw `disposable_email_blocklist.conf` file). Commit the full list (~3,500 domains). One domain per line. Update periodically.

Call `is_disposable_email(email)` in:
- `POST /api/auth/register` — raise `HTTP 422` with `{ "error": "Email domain not accepted.", "request_id": "..." }` if disposable.
- `POST /api/trial/start` — same check as a secondary gate (catches anyone who registered before the check was added).

---

#### 4. Gmail canonical normalization

New function in `backend/routers/auth.py` (or a shared `backend/email_utils.py`):

```python
def canonical_email(email: str) -> str | None:
    """
    Returns a normalized email for deduplication. Only normalizes Gmail/Googlemail.
    Returns None if the email is malformed.
    """
    if not email or "@" not in email:
        return None
    local, domain = email.lower().rsplit("@", 1)
    if domain in ("gmail.com", "googlemail.com"):
        local = local.split("+")[0].replace(".", "")
        domain = "gmail.com"  # normalize googlemail.com → gmail.com
    return f"{local}@{domain}"
```

At `POST /api/auth/register`: compute `canonical_email(email)` and store it in `users.email_canonical`. If the INSERT raises a unique constraint violation on `email_canonical`, return `HTTP 409` with `{ "error": "An account with this email already exists.", "request_id": "..." }` — same error shape as the regular email duplicate check.

Non-Gmail domains: `canonical_email` returns `local@domain` unchanged (no normalization, still stored for index coverage).

---

#### 5. Backend — `db.py` changes

Add the following helpers. Keep them near the existing plan helpers (`set_user_plan`, `record_plan_change`):

```python
async def activate_trial(user_id: str, duration_days: int) -> dict[str, Any]:
    """Set plan=pro, is_trial=true, trial_expires_at, trial_used=true. Returns updated user row."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            text("""
                UPDATE users
                SET plan = 'pro',
                    is_trial = true,
                    trial_expires_at = now() + :duration * INTERVAL '1 day',
                    trial_used = true
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, email_verified, is_trial,
                          trial_expires_at, trial_used, razorpay_customer_id, created_at, upgraded_at
            """),
            {"user_id": user_id, "duration": duration_days},
        )
        return dict(row)

async def expire_trial(user_id: str) -> dict[str, Any]:
    """Downgrade a trial user back to free. trial_used stays true. Returns updated user row."""
    async with get_conn() as conn:
        row = await conn.fetchrow(
            text("""
                UPDATE users
                SET plan = 'free',
                    is_trial = false,
                    trial_expires_at = NULL
                WHERE id = CAST(:user_id AS UUID)
                RETURNING id, email, name, plan, email_verified, is_trial,
                          trial_expires_at, trial_used, razorpay_customer_id, created_at, upgraded_at
            """),
            {"user_id": user_id},
        )
        return dict(row)
```

Update `get_user_by_id()` and every function that fetches a user row and returns it to the caller (search for `SELECT id, email, name, plan` in db.py — there are several) to include `is_trial`, `trial_expires_at`, `trial_used` in the SELECT and in the returned dict.

Add lazy expiry via a `_check_and_expire_trial(conn, user_id, user_dict)` coroutine called inline in `get_current_user()`:

```python
async def _check_and_expire_trial(conn, user: dict) -> dict:
    if user.get("is_trial") and user.get("trial_expires_at"):
        if user["trial_expires_at"] < datetime.now(tz=timezone.utc):
            updated = await expire_trial(user["id"])
            updated["trial_just_expired"] = True
            return updated
    user.setdefault("trial_just_expired", False)
    return user
```

Call this inside `get_current_user()` (used by `GET /api/auth/me`) and any other full-user-fetch path. Do NOT call it in lightweight plan-only helpers like `get_user_plan()`.

Ensure the returned user dict always includes:
```python
{
    "is_trial": bool,
    "trial_expires_at": datetime | None,   # UTC-aware
    "trial_used": bool,
    "trial_just_expired": bool,            # True only when we just auto-downgraded this request
    "trial_days_remaining": int | None,    # floor((trial_expires_at - now) / 86400); None if not on trial
}
```

`trial_days_remaining` calculation:
```python
import math
if user["is_trial"] and user["trial_expires_at"]:
    delta = user["trial_expires_at"] - datetime.now(tz=timezone.utc)
    user["trial_days_remaining"] = max(0, math.floor(delta.total_seconds() / 86400))
else:
    user["trial_days_remaining"] = None
```

---

#### 6. Backend — `models.py` changes

Update `UserResponse` to include:

```python
is_trial: bool = False
trial_expires_at: datetime | None = None
trial_used: bool = False
trial_just_expired: bool = False
trial_days_remaining: int | None = None
```

Add new request/response models:

```python
class TrialStartResponse(BaseModel):
    plan: str           # "pro"
    is_trial: bool      # True
    trial_expires_at: datetime
    trial_days_remaining: int

class TrialStatusResponse(BaseModel):
    eligible: bool
    reason: str | None  # None if eligible. One of: "already_on_trial", "trial_used",
                        # "already_paid", "email_not_verified", "anonymous_user", "disposable_email"
    is_trial: bool
    trial_days_remaining: int | None
    trial_used: bool
    trial_expires_at: datetime | None
```

---

#### 7. Backend — `routers/trial.py` (new file)

```python
router = APIRouter(prefix="/api/trial", tags=["trial"])
```

**`GET /api/trial/status`**
- Auth: `get_current_user` (anonymous OK — returns eligible=false with reason="anonymous_user")
- No side effects.
- Logic: anonymous → "anonymous_user"; unverified → "email_not_verified"; trial_used → "trial_used"; paid plan → "already_paid"; is_trial → "already_on_trial"; otherwise eligible=True.

**`POST /api/trial/start`**
- Auth: `get_current_user` (must be real user, not anonymous)
- Gates (HTTP 403 for each): anonymous, unverified email, trial_used, already paid, already on trial.
- Extra gates: disposable email → 422; IP rate limit (1/IP/24h) → 429.
- Action: `activate_trial` → `record_plan_change(context="trial_start")` → return `TrialStartResponse`.
- No Razorpay interaction. No email sent.

Register in `main.py`.

---

#### 8. Backend — `routers/razorpay.py` changes

In `_apply_plan_change()`, before calling `set_user_plan`:

```python
if user.get("is_trial"):
    await db.expire_trial(user["id"])  # clears trial state first, then set_user_plan sets the paid plan
```

The subscription-cancelled / payment-failed webhook path that downgrades to `free` should NOT touch `is_trial` — just call `set_user_plan(user_id, 'free')` as today.

---

#### 9. Frontend — `api.js` changes

```js
export const getTrialStatus = () => api.get('/api/trial/status')
export const startTrial = () => api.post('/api/trial/start')
```

---

#### 10. Frontend — `contexts/AuthContext.js` changes

1. Trial fields flow through automatically from `/api/auth/me` response — no extra parsing needed.

2. Add `setTimeout` for automatic expiry detection after every `refreshUser()`:
```js
const trialTimerRef = useRef(null)
// After setting user state:
if (trialTimerRef.current) clearTimeout(trialTimerRef.current)
if (data.is_trial && data.trial_expires_at) {
  const msUntilExpiry = new Date(data.trial_expires_at) - Date.now() + 2000
  if (msUntilExpiry > 0) {
    trialTimerRef.current = setTimeout(async () => { await refreshUser() }, msUntilExpiry)
  }
}
// Cleanup on unmount:
useEffect(() => () => { if (trialTimerRef.current) clearTimeout(trialTimerRef.current) }, [])
```

3. Add `trialJustExpired` state + `clearTrialJustExpired`. Set it when `data.trial_just_expired` is true after a refresh. Expose both from context.

---

#### 11. Frontend — `components/TrialBanner.js` (new file)

Slim full-width strip shown when `user.is_trial === true`. Mounted once in `App.js` above `<Routes>`.

```
⏱ [N] days left in your Pro trial  ·  [Upgrade to Pro →]
```

- `N <= 2` → `.trial-banner--urgent` (amber)
- `N === 0` → `.trial-banner--critical` (danger)
- No dismiss button.

---

#### 12. Frontend — `components/TrialExpiredModal.js` (new file)

Modal shown when `trialJustExpired === true`. Mounted in `App.js`.

```
Your Pro trial has ended
You had 7 days of full Pro access. Upgrade to keep
unlimited questions, hard mocks, and more.

[Start Pro — ₹X/mo]   [Maybe later]
```

- "Start Pro" → `UpgradeButton plan="pro"` → on payment success → `clearTrialJustExpired()`.
- "Maybe later" → `clearTrialJustExpired()`. Does not re-show in the same session.

---

#### 13. Frontend — `pages/LandingPage.js` changes (Pro pricing column only)

Below the existing "Start Pro" CTA, add a trial CTA with state machine:
- `unauthenticated` → "Try free for 7 days →" → navigate to `/auth?intent=trial`
- `eligible` → "Try free for 7 days →" → call `startTrial()` directly
- `unverified` → "Verify your email to unlock the free trial" (hint text)
- `used` / paid → hidden

Intent preservation: set `sessionStorage.setItem('trial_intent', '1')` before navigating to `/auth`. In `AuthPage.js` post-login/register handler, check for the key → call `startTrial()` → clear key → redirect to `/practice/sql`.

---

#### 14. Frontend — `App.css` additions

Trial banner, trial CTA button, and trial expired modal styles. See full CSS in prior spec version.

---

#### 15. Docs to update (same commit as implementation)

- `docs/backend.md` — Add trial endpoints and new `users` columns.
- `docs/features/pricing.md` — Add "Trial Pro" section.
- `CLAUDE.md` — Update backend behaviour + API table + add `TRIAL_DURATION_DAYS` env var.

---

#### 16. Test cases — `backend/tests/test_trial.py` (new file)

Groups:
- **A** — Gate checks: anonymous, unverified, trial_used, already paid, already on trial, disposable email → all 403/422
- **B** — Happy path: success response shape, DB state, plan_changes audit row, custom duration
- **C** — IP rate limiting: second activation from same IP → 429; resets after 25h
- **D** — `GET /api/trial/status`: all eligibility states
- **E** — Lazy expiry via `GET /api/auth/me`: fires expiry, sets DB correctly, flag is one-shot
- **F** — Upgrade during trial: clears trial state, cannot re-trial after upgrade or after expiry
- **G** — Gmail canonical deduplication: `+suffix`, dot variants, googlemail normalization, non-Gmail unaffected
- **H** — Disposable email blocklist: blocked at registration and at trial start
- **I** — Unlock integration: trial user gets Pro access; expired trial user gets free-tier locks

---

#### Effort summary

| Area | Est. days |
|---|---|
| DB migration | 0.25 |
| Disposable domain list + `disposable_domains.py` | 0.25 |
| Gmail canonical normalization | 0.25 |
| `db.py` helpers + lazy expiry | 0.5 |
| `routers/trial.py` + `models.py` + config | 0.5 |
| `routers/razorpay.py` trial-clear on upgrade | 0.25 |
| `AuthContext.js` (setTimeout, trialJustExpired) | 0.5 |
| `TrialBanner.js` + mount in `App.js` | 0.5 |
| `TrialExpiredModal.js` | 0.5 |
| `LandingPage.js` CTA + intent preservation | 0.5 |
| `App.css` additions | 0.25 |
| Tests (`test_trial.py`) | 1.0 |
| Docs | 0.25 |
| **Total** | **~5.5 days** |

---

**Deferred: Lifetime Pro → Lifetime Elite upgrade (delta payment)**
When volume warrants it: create a Razorpay Order for the price delta only, reuse existing verify-payment flow, upgrade plan to `lifetime_elite`, show prompt on Account page for `lifetime_pro` users. Until then: handled manually via email.

---

## Phase 2 — Engineering foundations

**React Query adoption**
Replace manual `useState + useEffect + axios` data fetching with TanStack Query.
- Install `@tanstack/react-query` in `frontend/package.json`
- Wrap `App.js` in `QueryClientProvider`
- Migrate `catalogContext.js`, `QuestionPage`, `ProgressDashboard` first; new pages use it from day one
- `useMutation` for submit/mock-start/mock-finish; `useQuery` for catalog, insights, path data

**Configurable DB connection pool**
`asyncpg` currently uses a fixed pool size — will exhaust under real load.
- Add `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_MAX_INACTIVE_LIFETIME` to `backend/config.py`
- Apply in `backend/db.py`
- Defaults: min=5, max=50, inactive lifetime=300s

**DuckDB connection pool**
Single shared DuckDB cursor is a concurrency bottleneck.
- Replace with a pool of pre-loaded in-memory connections in `backend/database.py`
- Pool size configurable via `DUCKDB_POOL_SIZE` env var (default: 8)

**CI/CD gaps**
- Deploy-on-merge step (Railway webhook or `railway up` on push to `main`)
- ESLint step (add `.eslintrc.js`, wire into `.github/workflows/ci.yml`)
- JS bundle-size budget (fail CI if gzipped bundle exceeds threshold, e.g. 500 KB)

---

## Phase 3 — Workspace

**Monaco SQL autocomplete**
- Register table names + column names from `question.schema` as completions in `CodeEditor.js`
- `monaco.languages.registerCompletionItemProvider('sql', ...)` — trigger on `.` after alias → columns; trigger on whitespace → table names
- SQL-only; Python editor unchanged

**Keyboard shortcuts help modal**
- `?` key (when cursor outside Monaco) opens a modal listing all shortcuts
- Create `frontend/src/components/KeyboardShortcutsModal.js`
- Wire in `QuestionPage.js` alongside existing `⌘↵` / `⌘⇧↵` bindings

---

## Phase 4 — TypeScript migration

- Add `tsconfig.json` + update `vite.config.js`
- Rename new files `.tsx`/`.ts` as they are created (no big-bang rename)
- Add `frontend/src/types/api.ts` for API response types
- Start after React Query is in place (gives a cleaner migration surface)

---

## Phase 5 — Community & profiles

Do not start until Phases 2 and 3 are stable.

**`/profile` page** (`frontend/src/pages/ProfilePage.js`)
```
TOPBAR
PROFILE HEADER — initials avatar · name/email · plan badge · member-since · total solved · streak
BADGES ROW — earned badges with unlock date; locked badges greyed with unlock criteria tooltip
STATS GRID — 2×2 (desktop) per-track solve count + progress bar
MOCK HISTORY — table: date · mode · track · score · time · [Review]
ACTIVITY HEATMAP — GitHub-style contribution grid from submissions table (CSS grid, 5-level --success opacity scale)
```
Wire at `/profile` in `App.js`. Add "See all badges →" link from Dashboard badge strip.

**`/leaderboard`** (`frontend/src/pages/Leaderboard.js`)
```
TABS — Weekly · All-time · By track
TABLE — rank · user (anonymised unless opt-in) · track · solved · avg time; current user highlighted
OPT-IN BANNER — "Make your stats public?" shown if not opted in
```
Backend: query `submissions` + `mock_sessions` — no new schema needed. Add `leaderboard_opt_in` bool to `users` table.

**Achievement badges**
Computed at read time from `submissions` + `mock_sessions` (no separate badge table initially):
- SQL Starter — first SQL question solved
- Speed Demon — hard question solved in < 5 min
- 7-Day Streak — 7 consecutive days with ≥ 1 solve
- Mock Pro — 5 mock sessions completed
- Century — 100 total questions solved

Surface on `/profile` and as a compact strip on `/dashboard` (5 most recent; "See all →" links to profile).
New component: `frontend/src/components/BadgeCard.js`

**Per-question discussion threads**
- New `discussion_posts` table: `id, question_id, track, user_id, body, created_at`
- `GET /api/questions/{id}/discussion`, `POST /api/questions/{id}/discussion`
- Flat threads (no voting, no nesting); requires account; rate-limited
- Frontend: collapsible discussion section at bottom of `QuestionPage.js`

**Internal question management**
Recommendation: GitHub/CI workflow for now (zero additional infrastructure), revisit `/admin` when question volume demands it.
