# Platform Backlog

Consolidated from TODO.md and path-to-world-class.md. Remove items as they ship; update `docs/` and `CLAUDE.md` in the same commit.

**Current state (2026-05-06):** Core platform is feature-complete. Auth, all four tracks, mock interviews, learning paths, dashboard insights, streak system, workspace polish (bookmarks, drafts, diff, resizable pane, focus mode, hints, concept panel, skeleton loaders, animations), and observability (Sentry + PostHog) are all shipped. What remains is engineering foundations, two workspace gaps, and Phase 6 community features.

---

## Remaining work

---

### Trial Pro (7-day free trial)

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

Add lazy expiry logic in the single shared helper that converts a DB row to a user dict (extract this into a `_row_to_user(row) -> dict` helper if it doesn't already exist, to avoid repeating the check):

```python
def _row_to_user(row, *, trial_just_expired: bool = False) -> dict:
    user = dict(row)
    # Lazy trial expiry
    just_expired = False
    if user.get("is_trial") and user.get("trial_expires_at"):
        if user["trial_expires_at"] < datetime.now(tz=timezone.utc):
            just_expired = True
            # Caller must handle the actual DB update — return flag and let caller decide
    user["trial_just_expired"] = trial_just_expired or just_expired
    return user
```

Actually, the cleanest approach: add a `_check_and_expire_trial(conn, user_id, user_dict)` coroutine called inline in `get_current_user()`:

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

Update `UserResponse` (or whatever Pydantic model represents the `GET /api/auth/me` response) to include:

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
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.deps import get_current_user
from backend import db, rate_limiter
from backend.config import settings
from backend.disposable_domains import is_disposable_email
from backend.models import TrialStartResponse, TrialStatusResponse

router = APIRouter(prefix="/api/trial", tags=["trial"])
```

**`GET /api/trial/status`**
- Auth: `get_current_user` (anonymous OK — returns eligible=false with reason="anonymous_user")
- No side effects.
- Response: `TrialStatusResponse`
- Logic:
  1. If user is anonymous (no email): `eligible=False, reason="anonymous_user"`
  2. If `not email_verified`: `eligible=False, reason="email_not_verified"`
  3. If `trial_used`: `eligible=False, reason="trial_used"`
  4. If `plan in ('pro', 'elite', 'lifetime_pro', 'lifetime_elite')`: `eligible=False, reason="already_paid"`
  5. If `is_trial` (should not happen if trial_used check above is correct, but defensive): `eligible=False, reason="already_on_trial"`
  6. Otherwise: `eligible=True, reason=None`

**`POST /api/trial/start`**
- Auth: `get_current_user` (must be real user, not anonymous)
- Body: empty (`{}` or no body)
- Response: `TrialStartResponse`
- Gates (return `HTTP 403` with `{ "error": "...", "request_id": "..." }` for each):
  1. Anonymous user (no email): `"You must create an account to start a trial."`
  2. `not email_verified`: `"Please verify your email address before starting a trial."`
  3. `trial_used`: `"You have already used your free trial."`
  4. `plan in ('pro', 'elite', 'lifetime_pro', 'lifetime_elite')`: `"You are already on a paid plan."`
  5. `is_trial`: `"You already have an active trial."` (defensive)
  6. Disposable email check: `is_disposable_email(user["email"])` → `HTTP 422, "Email domain not accepted for trial."`
  7. IP rate limit: `rate_limiter.check(f"trial_start:{client_ip}", limit=1, window_seconds=86400)` → `HTTP 429, "Too many trial activations from this network. Try again tomorrow."`
- Action:
  1. Call `await db.activate_trial(user["id"], settings.TRIAL_DURATION_DAYS)`
  2. Call `await db.record_plan_change(user["id"], old_plan="free", new_plan="pro", context="trial_start")`
  3. Return `TrialStartResponse` with `plan`, `is_trial=True`, `trial_expires_at`, `trial_days_remaining`
- No Razorpay interaction. No email sent (keep it frictionless).

Register in `main.py`:
```python
from backend.routers import trial
app.include_router(trial.router)
```

---

#### 8. Backend — `routers/razorpay.py` changes

In `_apply_plan_change()` (the function called by both `verify-payment` and the webhook handler), after confirming the plan upgrade is valid and before/after calling `set_user_plan`:

```python
# If user is upgrading out of a trial, clear trial state
if user.get("is_trial"):
    await db.expire_trial(user["id"])  # sets plan=free, is_trial=false, trial_expires_at=NULL
    # expire_trial sets plan=free — then set_user_plan below will set the correct paid plan
    # Keep trial_used=true (expire_trial does not reset it)
```

Make sure `expire_trial` is called BEFORE `set_user_plan` so the final DB state is the paid plan, not free.

Also: the Razorpay subscription-cancelled / payment-failed webhook path that downgrades back to `free` should NOT set `is_trial=true`. It should only call `expire_trial` if `is_trial` was somehow still true (defensive), otherwise just `set_user_plan(user_id, 'free')` as it does today.

---

#### 9. Backend — `routers/auth.py` changes

In the `GET /api/auth/me` handler: the `trial_just_expired` flag is already handled by `_check_and_expire_trial` in `db.py`. No extra logic needed here — just ensure the `UserResponse` model includes the trial fields and they flow through from the DB dict.

---

#### 10. Frontend — `api.js` changes

Add two new API helpers:

```js
export const getTrialStatus = () => api.get('/api/trial/status')
export const startTrial = () => api.post('/api/trial/start')
```

---

#### 11. Frontend — `contexts/AuthContext.js` changes

The existing `AuthContext` exposes `user` (from `GET /api/auth/me`) and `refreshUser()`. Extend:

1. Consume the new trial fields from the `/api/auth/me` response — they flow through automatically since `user` is the full response object.

2. Add a `setTimeout` for automatic expiry detection. After every successful `refreshUser()` call, if `user.is_trial === true` and `user.trial_expires_at` is in the future:

```js
const trialTimerRef = useRef(null)

// Inside refreshUser, after setting user state:
if (trialTimerRef.current) clearTimeout(trialTimerRef.current)
if (data.is_trial && data.trial_expires_at) {
  const msUntilExpiry = new Date(data.trial_expires_at) - Date.now() + 2000  // +2s clock skew
  if (msUntilExpiry > 0) {
    trialTimerRef.current = setTimeout(async () => {
      await refreshUser()  // backend lazy-checks → returns trial_just_expired=true
    }, msUntilExpiry)
  }
}

// Cleanup on unmount:
useEffect(() => () => { if (trialTimerRef.current) clearTimeout(trialTimerRef.current) }, [])
```

3. Add a `trialJustExpired` state derived from `user.trial_just_expired`. Reset it after it's been consumed (so re-fetches don't keep showing the modal):

```js
const [trialJustExpired, setTrialJustExpired] = useState(false)

// In refreshUser, after setting user:
if (data.trial_just_expired) setTrialJustExpired(true)
```

Expose `trialJustExpired` and `clearTrialJustExpired` (a setter to `false`) from the context.

4. Also detect "trial already expired on page load" (user had tab closed when trial lapsed):

```js
// After setting user in initial load:
if (!data.is_trial && data.trial_used && data.trial_expires_at &&
    new Date(data.trial_expires_at) < new Date()) {
  // Trial expired while tab was closed — show the modal
  setTrialJustExpired(true)
}
```

Wait — `trial_expires_at` is NULLed by `expire_trial`. So if the backend already ran lazy expiry before this page load, `trial_expires_at` will be NULL. The `trial_just_expired` flag on the response is the right signal here. The "tab was closed" case is handled: on the next `GET /api/auth/me` after the tab reopens, the backend lazy-checks, runs `expire_trial`, and returns `trial_just_expired=true`. The frontend sees it and sets state. No extra client-side date comparison needed.

---

#### 12. Frontend — `components/TrialBanner.js` (new file)

A slim full-width strip rendered above the main content area (or inline in Topbar). Shown when `user.is_trial === true`.

Content:
```
⏱ [N] days left in your Pro trial  ·  [Upgrade to Pro →]
```

- `N` = `user.trial_days_remaining`
- When `N === 0`: "Last day of your Pro trial · [Upgrade to Pro →]"
- When `N <= 2`: apply `.trial-banner--urgent` class (amber/warning colour scheme)
- When `N === 0`: apply `.trial-banner--critical` class (danger colour scheme)
- "Upgrade to Pro →" button: reuses the existing `UpgradeButton` component with `plan="pro"`. On successful payment, `refreshUser()` is called by the checkout flow and the banner disappears automatically (since `is_trial` becomes false).
- No close/dismiss button — it's important information. It goes away on upgrade or expiry.

Mount in `Topbar.js`: render `<TrialBanner />` immediately after the topbar element, outside the topbar itself (so it doesn't affect topbar layout), only when `user?.is_trial`. Example in any page that uses `Topbar`:

```jsx
<>
  <Topbar ... />
  {user?.is_trial && <TrialBanner />}
  {/* rest of page */}
</>
```

Actually: mount it once in `App.js` at the route level, above `<Routes>`, so it persists across navigation:
```jsx
{user?.is_trial && <TrialBanner />}
<Routes>...</Routes>
```

CSS class `.trial-banner`:
- `background: var(--warning-bg, #FEF3C7)` (light) / `#2D2200` (dark)
- `color: var(--warning-text, #92400E)` (light) / `#FCD34D` (dark)
- `border-bottom: 1px solid var(--warning-border, #FDE68A)`
- `padding: 8px 16px`
- `text-align: center`
- `font-size: 0.875rem`
- `.trial-banner--urgent`: `background: #FFF7ED`, amber text
- `.trial-banner--critical`: `background: var(--danger-bg)`, `color: var(--danger)` border

---

#### 13. Frontend — `components/TrialExpiredModal.js` (new file)

Modal shown when `trialJustExpired === true` in AuthContext.

```
[ overlay ]
┌─────────────────────────────┐
│  Your Pro trial has ended   │
│                             │
│  You had 7 days of full     │
│  Pro access. Upgrade to     │
│  keep unlimited questions,  │
│  hard mocks, and more.      │
│                             │
│  [Start Pro — ₹X/mo]        │
│  [Maybe later]              │
└─────────────────────────────┘
```

- "Start Pro" button: same as `UpgradeButton plan="pro"`. On successful payment verification → `clearTrialJustExpired()` → modal unmounts → `TrialBanner` also gone.
- "Maybe later" button: calls `clearTrialJustExpired()` → modal unmounts. The user is now on free plan; locked questions will show their standard locked state.
- Modal does NOT re-show on the same session after dismiss (state is in memory, cleared on dismiss). It will show again on next page load if somehow the backend still returns `trial_just_expired=true` — but it won't because the flag is set only once per expiry event.
- Mount in `App.js`:
  ```jsx
  {trialJustExpired && <TrialExpiredModal onClose={clearTrialJustExpired} />}
  ```
- Reuse existing modal overlay CSS pattern (`position: fixed; inset: 0; background: rgba(0,0,0,0.5)`).

---

#### 14. Frontend — `pages/LandingPage.js` changes (pricing section, Pro column only)

Below the existing "Start Pro" CTA button in the Pro pricing column, add:

```jsx
{trialCTAState === 'eligible' && (
  <button className="trial-cta-btn" onClick={handleTrialStart}>
    Try free for {TRIAL_DAYS} days →
  </button>
)}
{trialCTAState === 'loading' && <span className="trial-cta-loading">Activating…</span>}
{trialCTAState === 'used' && null}  {/* hide silently — don't shame them */}
{trialCTAState === 'unverified' && (
  <span className="trial-cta-hint">Verify your email to unlock the free trial</span>
)}
{trialCTAState === 'unauthenticated' && (
  <button className="trial-cta-btn" onClick={() => navigate('/auth?intent=trial')}>
    Try free for {TRIAL_DAYS} days →
  </button>
)}
```

`TRIAL_DAYS` — derive from `user.trial_days_remaining` if on trial, otherwise read from... we don't expose the configured value to the frontend directly. Hardcode `7` in the UI copy but store it in a `VITE_TRIAL_DURATION_DAYS` env var (default "7") read at build time. Or just hardcode 7 in the copy and only change it if the env var changes — acceptable for now.

`trialCTAState` logic (compute in component):
- No user / anonymous user → `'unauthenticated'`
- User but `!email_verified` → `'unverified'`
- `trial_used` → `'used'`
- `plan` is paid → `'used'` (hide the button)
- Otherwise → `'eligible'`
- During API call → `'loading'`

`handleTrialStart`:
```js
async function handleTrialStart() {
  setTrialCTAState('loading')
  try {
    await startTrial()
    await refreshUser()  // AuthContext re-fetches /api/auth/me — user.is_trial becomes true
    // TrialBanner now appears; show a success toast
    toast({ message: 'Your 7-day Pro trial has started!', type: 'success' })
  } catch (err) {
    setTrialCTAState('eligible')
    toast({ message: err.response?.data?.error ?? 'Could not start trial.', type: 'error' })
  }
}
```

**Intent preservation for unauthenticated users:** When an unauthenticated user clicks "Try free for 7 days →", navigate to `/auth?intent=trial`. In `AuthPage.js`, on successful registration/login, check `sessionStorage.getItem('trial_intent')` (set it before navigating) — if present, call `startTrial()` after `refreshUser()` completes, then redirect to `/practice/sql`. This mirrors the existing `upgrade_intent` sessionStorage pattern already in the codebase.

Specifically in `LandingPage.js`:
```js
onClick={() => {
  sessionStorage.setItem('trial_intent', '1')
  navigate('/auth?intent=trial')
}}
```

In `AuthPage.js`, in the post-login/register success handler:
```js
if (sessionStorage.getItem('trial_intent')) {
  sessionStorage.removeItem('trial_intent')
  try { await startTrial() } catch (_) {}  // best-effort; gates will reject if ineligible
  await refreshUser()
}
```

---

#### 15. Frontend — `App.css` additions

```css
/* Trial banner */
.trial-banner {
  width: 100%;
  padding: 8px 20px;
  text-align: center;
  font-size: 0.875rem;
  font-weight: 500;
  background: #FEF3C7;
  color: #92400E;
  border-bottom: 1px solid #FDE68A;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 90;
}
.trial-banner--urgent { background: #FFF7ED; color: #C2410C; border-color: #FED7AA; }
.trial-banner--critical { background: #FEF2F2; color: var(--danger); border-color: #FECACA; }
[data-theme="dark"] .trial-banner { background: #2D2200; color: #FCD34D; border-color: #3D3000; }
[data-theme="dark"] .trial-banner--urgent { background: #3D1F00; color: #FB923C; border-color: #7C2D12; }
[data-theme="dark"] .trial-banner--critical { background: #3B0000; color: #FCA5A5; border-color: #7F1D1D; }
.trial-banner-upgrade-btn {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--accent);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* Trial CTA on landing pricing */
.trial-cta-btn {
  width: 100%;
  padding: 10px 16px;
  border: 1.5px solid var(--accent);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--accent);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  margin-top: 8px;
  transition: background 0.15s, color 0.15s;
}
.trial-cta-btn:hover { background: var(--accent); color: #fff; }
.trial-cta-hint { font-size: 0.75rem; color: var(--text-secondary); margin-top: 8px; display: block; text-align: center; }

/* Trial expired modal */
.trial-expired-modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.55);
  z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.trial-expired-modal {
  background: var(--surface-card);
  border-radius: var(--radius-lg);
  padding: 36px 32px;
  max-width: 420px;
  width: 90%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.trial-expired-modal h2 { font-size: 1.25rem; font-weight: 700; margin-bottom: 12px; }
.trial-expired-modal p { font-size: 0.9375rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 24px; }
.trial-expired-modal-actions { display: flex; flex-direction: column; gap: 10px; }
.trial-expired-dismiss { background: none; border: none; color: var(--text-secondary); font-size: 0.875rem; cursor: pointer; padding: 4px; }
.trial-expired-dismiss:hover { color: var(--text-strong); }
```

---

#### 16. Docs to update (same commit as implementation)

- `docs/backend.md` — Add `GET /api/trial/status` and `POST /api/trial/start` to the API table. Add `email_canonical`, `is_trial`, `trial_expires_at`, `trial_used` to the users table description.
- `docs/features/pricing.md` — Add a "Trial Pro" section covering: eligibility rules, duration config, abuse mitigations, what happens on expiry, what happens on upgrade during trial.
- `CLAUDE.md` — Update the "Backend behaviour" section to mention the trial model. Update the API endpoints table. Add `TRIAL_DURATION_DAYS` to env vars section.

---

#### 17. Test cases — `backend/tests/test_trial.py` (new file)

All tests use `pytest + httpx` against the test DB (same pattern as existing tests). Use fixture helpers from `conftest.py` for creating verified users, anon users, etc.

**Group A — `POST /api/trial/start` gate checks (all return 403)**

- `test_trial_start_anonymous_blocked`: POST as anonymous user (no email) → 403, error contains "account"
- `test_trial_start_unverified_email_blocked`: POST as registered user with `email_verified=false` → 403, error contains "verify your email"
- `test_trial_start_already_used_blocked`: Set `trial_used=true` in DB first → POST → 403, error contains "already used"
- `test_trial_start_already_on_pro_blocked`: Set `plan='pro'` in DB first → POST → 403, error contains "already on a paid plan"
- `test_trial_start_already_on_elite_blocked`: Same for `plan='elite'`
- `test_trial_start_already_on_lifetime_pro_blocked`: Same for `plan='lifetime_pro'`
- `test_trial_start_already_on_trial_blocked`: Set `is_trial=true` in DB → POST → 403, error contains "active trial"
- `test_trial_start_disposable_email_blocked`: Register user with `mailinator.com` email (bypass normal registration check by inserting directly into DB with `email_verified=true`) → POST `/api/trial/start` → 422, error contains "domain not accepted"

**Group B — `POST /api/trial/start` happy path**

- `test_trial_start_success`: Verified user, eligible → POST → 200, response has `plan="pro"`, `is_trial=true`, `trial_expires_at` is ~7 days from now (within 5s tolerance), `trial_days_remaining=7`
- `test_trial_start_sets_db_correctly`: After successful trial start, fetch user from DB directly → `plan='pro'`, `is_trial=true`, `trial_used=true`, `trial_expires_at` is set
- `test_trial_start_records_plan_change`: After trial start, check `plan_changes` table → row with `old_plan='free'`, `new_plan='pro'`, `context='trial_start'`
- `test_trial_start_custom_duration`: Set `settings.TRIAL_DURATION_DAYS = 3` (monkeypatch) → POST → `trial_days_remaining=3`

**Group C — IP rate limiting**

- `test_trial_start_ip_rate_limit`: Same IP, two different verified users → first succeeds, second returns 429
- `test_trial_start_ip_rate_limit_resets_after_window`: Same IP, first succeeds; mock time 25h later; second succeeds

**Group D — `GET /api/trial/status`**

- `test_trial_status_eligible`: Verified user, no prior trial → `eligible=true`, `reason=null`
- `test_trial_status_anonymous`: Anonymous user → `eligible=false`, `reason="anonymous_user"`
- `test_trial_status_unverified`: `eligible=false`, `reason="email_not_verified"`
- `test_trial_status_used`: `eligible=false`, `reason="trial_used"`
- `test_trial_status_already_paid`: `eligible=false`, `reason="already_paid"`
- `test_trial_status_active_trial`: On active trial → `eligible=false`, `reason="already_on_trial"`, `is_trial=true`, `trial_days_remaining=N`

**Group E — Lazy expiry via `GET /api/auth/me`**

- `test_trial_expiry_lazy`: Activate trial, then set `trial_expires_at = now() - 1 second` in DB directly → GET `/api/auth/me` → response has `plan="free"`, `is_trial=false`, `trial_just_expired=true`
- `test_trial_expiry_sets_db`: After the above GET, fetch user from DB → `plan='free'`, `is_trial=false`, `trial_expires_at=NULL`, `trial_used=true` (persisted)
- `test_trial_just_expired_flag_one_shot`: Two consecutive `GET /api/auth/me` after expiry → first returns `trial_just_expired=true`, second returns `trial_just_expired=false` (the flag is transient — only true when we actually ran the expiry in that request). NOTE: since the backend lazy-check only fires when `is_trial=true`, after the first expiry sets `is_trial=false`, subsequent calls won't re-fire the flag. This test verifies that.
- `test_active_trial_not_expired`: Activate trial, do NOT set expires_at to the past → GET `/api/auth/me` → `plan='pro'`, `is_trial=true`, `trial_just_expired=false`, `trial_days_remaining > 0`

**Group F — Upgrade during trial**

- `test_upgrade_during_trial_clears_trial_state`: Activate trial → simulate successful Razorpay payment by calling `_apply_plan_change(user, new_plan='pro')` directly → fetch user from DB → `is_trial=false`, `trial_expires_at=NULL`, `plan='pro'`, `trial_used=true` (still true)
- `test_upgrade_to_elite_during_trial`: Same but `new_plan='elite'`
- `test_cannot_retrial_after_upgrade`: Activate trial → upgrade via Razorpay → POST `/api/trial/start` → 403 (reason: already_paid)
- `test_cannot_retrial_after_expiry`: Activate trial → expire it → POST `/api/trial/start` → 403 (reason: trial_used)

**Group G — Gmail canonical deduplication**

- `test_gmail_canonical_blocks_plus_suffix`: Register `user@gmail.com` successfully. Attempt to register `user+1@gmail.com` → 409 conflict.
- `test_gmail_canonical_blocks_dot_variant`: Register `u.ser@gmail.com`, then attempt `user@gmail.com` → 409.
- `test_googlemail_normalized_to_gmail`: Register `user@googlemail.com`, then attempt `user@gmail.com` → 409.
- `test_non_gmail_canonical_no_normalization`: Register `user+1@outlook.com` successfully even if `user@outlook.com` exists (we do not normalize non-Gmail).
- `test_canonical_stored_correctly`: After registration with `user+tag@gmail.com`, check DB `email_canonical = 'user@gmail.com'`.

**Group H — Disposable email blocklist**

- `test_disposable_email_blocked_at_registration`: POST `/api/auth/register` with `email@mailinator.com` → 422.
- `test_disposable_email_blocked_at_trial_start`: Insert user with `mailinator.com` email bypassing registration check, verify email directly in DB → POST `/api/trial/start` → 422.
- `test_legitimate_email_not_blocked`: `user@gmail.com` and `user@company.com` pass the check.

**Group I — Unlock access during trial (integration)**

- `test_trial_user_can_access_medium_questions`: Activate trial → GET `/api/catalog` → medium questions are unlocked (same as pro user).
- `test_trial_user_can_start_hard_mock`: Activate trial → GET `/api/mock/access?difficulty=hard` → `can_start=true`.
- `test_expired_trial_user_loses_access`: Activate trial → expire it → GET `/api/catalog` → medium/hard lock state same as free user.

---

#### 18. Effort summary

| Area | Est. days |
|---|---|
| DB migration | 0.25 |
| Disposable domain list + `disposable_domains.py` | 0.25 |
| Gmail canonical normalization in `auth.py` + `db.py` | 0.25 |
| `db.py` helpers + lazy expiry | 0.5 |
| `routers/trial.py` + `models.py` + config | 0.5 |
| `routers/razorpay.py` trial-clear on upgrade | 0.25 |
| `AuthContext.js` (setTimeout, trialJustExpired state) | 0.5 |
| `TrialBanner.js` + mount in `App.js` | 0.5 |
| `TrialExpiredModal.js` | 0.5 |
| `LandingPage.js` CTA + intent preservation | 0.5 |
| `App.css` additions | 0.25 |
| Tests (`test_trial.py`) | 1.0 |
| Docs (`CLAUDE.md`, `docs/backend.md`, `docs/features/pricing.md`) | 0.25 |
| **Total** | **~5.5 days** |

---

**Lifetime Pro → Lifetime Elite upgrade (delta payment)**
Currently `lifetime_pro` users have no self-serve upgrade path; the Account page tells them to email support.
When volume warrants it, implement automated delta-payment upgrade:
- Create a Razorpay Order for `(lifetime_elite_price − lifetime_pro_price)` only
- Reuse the existing `POST /api/razorpay/create-order` + `POST /api/razorpay/verify-payment` flow
- On successful payment verification, upgrade `plan` to `lifetime_elite` in the DB
- Show an "Upgrade to Lifetime Elite — pay the difference" prompt on the Account page for `lifetime_pro` users
- Add a `context="lifetime_upgrade"` field to `plan_changes` for audit clarity
Until then: email support@datathink.co, handled manually within 7 business days.

---

### Engineering foundations

**React Query adoption**
Replace manual `useState + useEffect + axios` data fetching with TanStack Query.
- Install `@tanstack/react-query` in `frontend/package.json`
- Wrap `App.js` in `QueryClientProvider`
- Migrate `catalogContext.js`, `QuestionPage`, `ProgressDashboard` first; new pages use it from day one
- `useMutation` for submit/mock-start/mock-finish; `useQuery` for catalog, insights, path data

**Configurable DB connection pool**
`asyncpg` currently uses a fixed pool size — will exhaust under real load.
- Add `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_MAX_INACTIVE_LIFETIME` to `backend/config.py`
- Apply in `backend/db.py` `create_async_engine` call
- Defaults: min=5, max=50, inactive lifetime=300s; override via env vars in production

**DuckDB connection pool**
Single shared DuckDB cursor is a concurrency bottleneck.
- Replace with a pool of pre-loaded in-memory connections in `backend/database.py`
- Pool size configurable via `DUCKDB_POOL_SIZE` env var (default: 8)
- Each connection is a full DuckDB instance with all CSV tables loaded at startup

**CI/CD gaps**
Question validation and dependency audits already run in CI. Missing:
- Deploy-on-merge step (Railway webhook or `railway up` on push to `main`)
- ESLint step (add `.eslintrc.js`, wire into `.github/workflows/ci.yml`)
- JS bundle-size budget (fail CI if gzipped bundle exceeds threshold, e.g. 500 KB)

---

### Workspace

**Monaco SQL autocomplete**
- Register table names + column names from `question.schema` as completions in `CodeEditor.js`
- `monaco.languages.registerCompletionItemProvider('sql', ...)` — trigger on `.` after alias → show columns; trigger on whitespace → suggest table names
- SQL-only; Python editor unchanged

**Keyboard shortcuts help modal**
- `?` key (when cursor outside Monaco) opens a modal overlay listing all shortcuts
- Create `frontend/src/components/KeyboardShortcutsModal.js`
- Wire in `QuestionPage.js` alongside existing `⌘↵` / `⌘⇧↵` bindings

---

### Content

**Schema design question type**
- Debug-type questions (`"type": "debug"`) exist; `"type": "schema_design"` does not
- Requires evaluator decision before authoring: MCQ-style (select the correct DDL) or free-form DDL via DuckDB execution (see `new-tracks-roadmap.md` for the DuckDB DDL validation approach)
- No questions authored yet; not in any difficulty file

---

---

### TypeScript migration

- Add `tsconfig.json` + update `vite.config.js`
- Rename new files `.tsx`/`.ts` as they are created (no big-bang rename)
- Add `frontend/src/types/api.ts` for API response types
- Start after React Query is in place (gives a cleaner migration surface)

---

### Community & profiles (Phase 6)

Do not start until the engineering foundations above are stable.

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
Decision still open. Options:
- **`/admin` UI** — protected route, question list + edit form, admin-only flag on `users` table
- **GitHub/CI workflow** — question edits via PR; CI validation is the gatekeeper (already partially in place with `validate_content.py`)

Recommend: GitHub/CI workflow for now (zero additional infrastructure), revisit `/admin` when question volume demands it.
