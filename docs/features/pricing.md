# Pricing Feature Reference

The pricing section lives in the landing page at `/` (`LandingPage.js`, `#landing-pricing`). It presents three subscription tiers — Free, Pro, and Elite — with monthly and lifetime purchase options. The section is hidden only for `lifetime_elite` users (who are already at the ceiling). Upgrade buttons are rendered via the `UpgradeButton` component, which opens the Razorpay Checkout modal.

---

## What the pricing page shows

The tier grid has three columns:

| Column | Shown when |
|---|---|
| **Free** | Always |
| **Pro** | Always (CTAs vary by current plan) |
| **Elite** | Always (CTAs vary by current plan) |

The entire `#landing-pricing` section is hidden only when `userPlan === 'lifetime_elite'`.

### CTA state by current plan

**Pro column:**

| Current plan | CTA rendered |
|---|---|
| `free` | Monthly upgrade button + lifetime button |
| `pro` | Lifetime button only ("Switch to lifetime") |
| `lifetime_pro` | "Current plan" label — no buttons |
| `elite` / `lifetime_elite` | No CTA (Pro is below their tier) |

**Elite column:**

| Current plan | CTA rendered |
|---|---|
| `free` / `pro` / `lifetime_pro` | Monthly upgrade button + lifetime button |
| `elite` | Lifetime button only ("Switch to lifetime") |
| `lifetime_elite` | "Current plan" label — no buttons (entire section hidden) |

---

## Plan-feature mapping

> **Mock plan gates: canonical source of truth is [`docs/features/mock.md`](./mock.md#plan-tier-matrix-canonical-sot).** Do not restate mock plan gates in this doc — link instead. The summary below is for at-a-glance reference; mock.md owns the full matrix, daily caps, rationale, and Interview Loop / chain mechanics.

| Feature | Free | Pro | Elite |
|---|---|---|---|
| Easy questions (per-track easy bank) | ✓ All | ✓ All | ✓ All |
| Medium questions | Batch-gated by easy solves | ✓ All | ✓ All |
| Hard questions | Batch-gated (cap: **8** code / **5** PySpark) | ✓ All (no cap) | ✓ All (no cap) |
| Learning paths | Free paths (`tier=free`) | All | All |
| **Mock — easy `benchmark`** | 1 per rolling 7 days | 3 per day | Unlimited |
| **Mock — `benchmark` (medium/hard)** | Blocked | 3 per day | Unlimited |
| **Mock — `custom` drill** | Blocked | 3 per day | Unlimited |
| **Mock-only question pool + follow-up chains** | Blocked | ✓ | ✓ |
| **Mock — `focus_concepts` filter** | Blocked | Blocked | ✓ |
| **Mock — Interview Loop mode** | Blocked | Blocked | ✓ |
| **Mock — history analytics + trend** | Blocked | Detailed history | + Trend, dimension analysis |
| **Mock — coaching debrief + readiness score + study plan** | Blocked | Blocked | ✓ |
| Weakest concept coaching (dashboard) | Blocked | ✓ | ✓ |
| Top-3 weak areas coaching panel (dashboard) | Blocked | Blocked | ✓ (concept, accuracy %, summary, path + drill links) |
| Interview readiness score (per-track) | Blocked | Blocked | ✓ |
| Personalised study plan | Blocked | Blocked | ✓ |

### Lifetime variants

`lifetime_pro` and `lifetime_elite` grant identical access to their base plans. They are stored separately in the database so a `subscription.cancelled` webhook from a prior monthly subscription cannot revoke a one-time purchase. All access-control functions call `normalize_plan()` first:

```python
normalize_plan("lifetime_pro")   # → "pro"
normalize_plan("lifetime_elite") # → "elite"
normalize_plan("free")           # → "free"  (unchanged)
```

**Important:** `lifetime_*` plans are never passed directly into access logic; `normalize_plan()` is the single choke-point. Code paths that skipped this call were fixed in the DEV-4 patch (see below).

---

## Upgrade flow

### Starting state: anonymous user

1. User sees the pricing section with upgrade CTAs in the Pro and Elite columns.
2. Clicking any `UpgradeButton` detects no authenticated user (`useAuth().user === null`).
3. The button redirects to `/auth` with state `{ from: '/', upgradeTier: tier }` — no API call is made.
4. After signup/login the user lands back on the site where they can click the upgrade button again.

### Starting state: Free user

1. Both Pro and Elite columns show a monthly CTA (via `UpgradeButton`) and a lifetime CTA.
2. `UpgradeButton.handleClick()` calls `POST /api/razorpay/create-order` with `{ plan, currency }`.
3. The backend validates the upgrade path, creates a Razorpay Order (lifetime) or Subscription (monthly), and returns the checkout payload.
4. The frontend loads the Razorpay Checkout JS SDK and opens the modal.
5. On success Razorpay fires `handler(resp)` with `razorpay_payment_id`, `razorpay_signature`, and either `razorpay_order_id` (one-time) or `razorpay_subscription_id` (recurring).
6. `POST /api/razorpay/verify-payment` is called. The backend verifies the HMAC signature and applies the plan upgrade.
7. The landing page redirects to `/?upgraded=true`.

### Starting state: Pro user

- The landing pricing section is hidden for paying users.
- Plan upgrades remain available from other gated surfaces where an upgrade is relevant.
- Pro user cannot create an order for `pro` (same plan) — backend returns 400.

### Starting state: Elite user

- The landing pricing section is hidden for paying users.
- Plan upgrades remain available from other gated surfaces where an upgrade is relevant.
- Elite user cannot create an order for `pro` or `elite` — backend returns 400.

---

## Razorpay integration

### Order vs Subscription

| Plan | Razorpay object | Fields in response |
|---|---|---|
| `pro` / `elite` | Subscription (`subscription_id`) | `subscription_id`, `is_subscription: true`, `amount: 0` |
| `lifetime_pro` / `lifetime_elite` | Order (`order_id`) | `order_id`, `amount` (paise), `is_subscription: false` |

The `amount` for subscriptions is `0` — the actual amount is resolved from the plan in the Razorpay dashboard and displayed by the checkout modal.

### Amounts (configured via env vars)

| Plan | INR (paise) | USD (cents) |
|---|---|---|
| `lifetime_pro` | 1,199,900 (₹11,999) | 12,900 ($129) |
| `lifetime_elite` | 1,999,900 (₹19,999) | 22,900 ($229) |

Monthly amounts are set in the Razorpay dashboard plan and not stored in the application.

### Currency detection

`detectCurrency()` in `frontend/src/utils/currency.js` uses `Intl.DateTimeFormat().resolvedOptions().timeZone`. Users in `Asia/Kolkata` or `Asia/Calcutta` get INR; all others get USD. The detected currency is passed as `currency` in the create-order request.

### HMAC verification (`verify-payment`)

The signed string depends on the payment flow:

| Flow | Signed body | 
|---|---|
| Order (one-time) | `"{order_id}|{payment_id}"` |
| Subscription | `"{payment_id}|{subscription_id}"` |

The backend uses `hmac.new(RAZORPAY_KEY_SECRET, body, sha256).hexdigest()` and `hmac.compare_digest()` for constant-time comparison. If both `razorpay_order_id` and `razorpay_subscription_id` are set the request is rejected as ambiguous (400).

### Webhook idempotency

All webhook events are deduped on `event.id` using the `payment_events` table:

1. `is_event_processed(event_id)` is checked before any plan change.
2. If already processed the endpoint returns `{"status": "already processed"}` (200).
3. The webhook signature (`X-Razorpay-Signature`) is verified with `RAZORPAY_WEBHOOK_SECRET` before processing.

`subscription.cancelled` and `subscription.halted` events that target a user on a `lifetime_*` plan are silently ignored — logged at INFO level, no plan change applied.

### Webhook events handled

| Event | Action |
|---|---|
| `payment.captured` | Apply `target_plan` from notes to user |
| `subscription.activated` | Apply `target_plan` from notes to user |
| `subscription.charged` | Apply `target_plan` (no-op if already on that plan) |
| `subscription.cancelled` | Downgrade to `free` (unless user is on a lifetime plan) |
| `subscription.halted` | Same as `subscription.cancelled` |
| `payment.failed` | Logged only, no plan change |
| All others | Ignored |

---

## Admin operator grants

Operators can give specific users time-limited Pro or Elite access for beta testing, invited cohorts, or trial extensions — without going through Razorpay. This is **internal tooling only**; users cannot grant or extend their own access.

**Mechanism:** Two nullable columns on `users` — `plan_override` (text) and `plan_override_until` (timestamptz) — store the override. At every auth resolution point, `_effective_plan()` in `db.py` checks if an active override exists and returns it in place of the base `plan` column. Expiry is **lazy** — evaluated per request, no cron job needed. After expiry the user silently reverts to their base plan at next session load.

**Endpoints** (all require `Authorization: Bearer <ADMIN_SECRET>`):

| Method | Path | Description |
|---|---|---|
| POST | `/api/admin/grant-plan` | Grant a time-limited Pro or Elite override. Body: `{ email, plan: "pro"│"elite", days: 1–365 }`. Safe to re-call — overwrites the existing override (use to extend or upgrade). |
| DELETE | `/api/admin/grant-plan` | Revoke the override immediately. User returns to base `plan`. |
| GET | `/api/admin/grants` | List all users with a `plan_override` set (active and expired). |

`ADMIN_SECRET` must be set in the Railway environment (generate with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`). If unset, all admin endpoints return 503.

**What it is not:** This is not a user-facing coupon or redemption flow. It produces no invoice, no webhook, and no `plan_changes` audit row. It does not affect the Razorpay subscription lifecycle.

---

## API reference

### `POST /api/razorpay/create-order`

**Auth required:** Yes (session cookie). Returns 403 for anonymous users.  
**Email verification required:** Yes. Returns 403 if `email_verified = false`.

**Request:**
```json
{ "plan": "pro", "currency": "INR" }
```

`plan` must be one of: `pro`, `elite`, `lifetime_pro`, `lifetime_elite`.  
`currency` must be `INR` or `USD`. Defaults to `INR`.

**Response (subscription):**
```json
{
  "order_id": null,
  "subscription_id": "sub_abc123",
  "amount": 0,
  "currency": "INR",
  "key_id": "rzp_live_...",
  "name": "datathink",
  "description": "datathink Pro (monthly)",
  "prefill_email": "user@example.com",
  "prefill_name": "User Name",
  "is_subscription": true
}
```

**Response (one-time order):**
```json
{
  "order_id": "order_abc123",
  "subscription_id": null,
  "amount": 1199900,
  "currency": "INR",
  "key_id": "rzp_live_...",
  "name": "datathink",
  "description": "datathink Lifetime Pro",
  "prefill_email": "user@example.com",
  "prefill_name": "User Name",
  "is_subscription": false
}
```

**Error responses** (all include `{ error, request_id }`):

| Status | Condition |
|---|---|
| 400 | Invalid plan, unsupported currency, upgrade path not allowed |
| 403 | Not authenticated or email not verified |
| 503 | Razorpay SDK not installed or keys not configured |

---

### `POST /api/razorpay/verify-payment`

**Auth required:** Yes.

**Request:**
```json
{
  "plan": "lifetime_pro",
  "razorpay_payment_id": "pay_...",
  "razorpay_signature": "hexdigest...",
  "razorpay_order_id": "order_..."
}
```

For subscriptions use `razorpay_subscription_id` instead of `razorpay_order_id`. Do not send both.

**Response:**
```json
{ "plan": "lifetime_pro" }
```

**Error responses** (`{ error, request_id }`):

| Status | Condition |
|---|---|
| 400 | Invalid signature, invalid plan, upgrade path not allowed, both order+subscription IDs supplied |
| 403 | Not authenticated |

---

### `POST /api/razorpay/webhook`

**Auth required:** No (uses `X-Razorpay-Signature` header for authentication).  
**CSRF protection:** Exempt (webhook bypass is explicit in CSRF middleware).

**Headers:**
```
X-Razorpay-Signature: <hmac-sha256-hex>
```

**Response:**
```json
{ "status": "processed" | "already processed" | "ignored" }
```

**Error responses** (`{ error, request_id }`):

| Status | Condition |
|---|---|
| 400 | Invalid signature, malformed JSON, missing event id/type |
| 503 | Webhook secret not configured |

---

### `POST /api/user/plan` (admin/test only)

Disabled in production (`IS_PROD = true` returns 403). Used in tests and dev to set arbitrary plans.

**Request:**
```json
{ "user_id": "uuid", "new_plan": "lifetime_elite", "context": "optional" }
```

Valid plans: `free`, `pro`, `elite`, `lifetime_pro`, `lifetime_elite`.

**Response:**
```json
{
  "user_id": "uuid",
  "old_plan": "free",
  "new_plan": "lifetime_elite",
  "success": true,
  "reason": null
}
```

On failure `success` is `false` and `reason` contains a human-readable explanation. Status code remains 200 for business-logic failures; 404 for unknown user.

---

## Error shape

All API errors from both HTTPException handlers and the global exception handler return:

```json
{
  "error": "Human-readable message",
  "request_id": "uuid-v4"
}
```

The `request_id` is also present in the `X-Request-ID` response header.

---

## Test coverage summary

`backend/tests/test_pricing.py` covers:

| Scenario | Test class |
|---|---|
| Anonymous user blocked from create-order and verify-payment; error shape verified | `TestAnonymousUser` |
| Free user creates orders for all 4 paid plans in both INR and USD | `TestFreeUserCreateOrder` |
| Invalid plan, free plan, and unsupported currency return 400 | `TestFreeUserCreateOrder` |
| Pro user upgrades to Elite / lifetime Pro / lifetime Elite succeed | `TestProUserUpgrades` |
| Pro user blocked from same-plan and downgrade | `TestProUserUpgrades` |
| Elite user can switch to lifetime Elite; blocked from same-plan / downgrade | `TestEliteUserUpgrades` |
| `lifetime_elite` user is blocked from all further upgrades | `TestEliteUserUpgrades` |
| `normalize_plan()` unit tests for all values | `TestNormalizePlan` |
| `lifetime_pro` / `lifetime_elite` can access Pro-tier paths (DEV-4 fix) | `TestNormalizePlan` |
| Free user cannot access Pro-tier paths | `TestNormalizePlan` |
| Tampered HMAC signature returns 400 with error shape | `TestHMACVerification` |
| Correct order HMAC upgrades plan | `TestHMACVerification` |
| Correct subscription HMAC upgrades plan | `TestHMACVerification` |
| Bad/missing webhook signature returns 400 | `TestHMACVerification` |
| Ambiguous request (both order+subscription IDs) rejected | `TestHMACVerification` |
| Webhook replay returns "already processed" with no extra plan change | `TestWebhookIdempotency` |
| verify-payment replay is a safe no-op | `TestWebhookIdempotency` |
| `lifetime_pro` / `lifetime_elite` stored verbatim in DB | `TestWebhookIdempotency` |
| `subscription.cancelled` does not downgrade lifetime plans | `TestWebhookIdempotency` |
| All valid plan transitions via `/api/user/plan` succeed | `TestAdminPlanEndpoint` |
| Invalid plan returns `success=false` with reason | `TestAdminPlanEndpoint` |
| Same plan returns `success=true, reason="No change"` | `TestAdminPlanEndpoint` |
| Unknown user returns 404 with error shape | `TestAdminPlanEndpoint` |

Additional Razorpay webhook lifecycle tests (subscription events, halted, payment.failed, crafted plans) are covered in `backend/tests/test_isolated_razorpay.py`.

---

## Upgrade CTA reference

Every in-app surface that prompts an upgrade, what it shows, when it appears, and how it navigates.

### Navigation convention

All "see plans" links that land on the pricing section use router-state navigation — no hash or query param in the URL:

```js
navigate('/', { state: { scrollTo: 'landing-pricing' } })
```

`LandingPage` reads `location.state?.scrollTo` on mount, scrolls to the element with that id (`landing-pricing`), then clears the state from browser history so back-navigation doesn't re-trigger the scroll. The scroll fires at 220 ms, 500 ms, and 1200 ms to survive async render delays.

Direct upgrade buttons (all `UpgradeButton` instances) skip the landing page entirely and open the Razorpay Checkout modal immediately.

### CTA map

| Surface | Component | Copy | Shown when | Action |
|---|---|---|---|---|
| **Landing — pricing section** | `UpgradeButton` | "Upgrade to Pro / Elite" + "Lifetime access — ₹X" | Plan allows the upgrade (see table below) | Opens Razorpay directly |
| **Practice sidebar — bottom panel** | `UpgradeButton` | "Unlock Pro" / "Unlock Elite" | `free` or `pro` plan | Opens Razorpay; `successPath` preserves `?path=` if in path mode |
| **Practice sidebar — path hint** | `<button>` | "Pro — unlock all ↗" / "Elite — unlock all ↗" | `free` plan + path mode + locked questions exist | Navigates to `/ + state.scrollTo` |
| **Question page — locked callout** | `UpgradeButton` | "Unlock now with Pro" | `free` plan, question is threshold-locked | Opens Razorpay |
| **Question page — hard gate** | `UpgradeButton` | "Upgrade to Pro" | `free` plan, hard question beyond free cap | Opens Razorpay |
| **Track hub — TierBanner** | `<button>` | "See plans →" | `free` plan | Navigates to `/ + state.scrollTo` |
| **Dashboard — weak-areas gate** | `UpgradeButton` | "Upgrade to Pro" | `free` plan, "Where to focus" panel | Opens Razorpay |
| **Landing — weak-spots gate** | `UpgradeButton` | "Upgrade to Pro" | `free` logged-in user with weak data | Opens Razorpay |
| **Mock hub — difficulty button** | `UpgradeButton` | "Pro unlocks this" / "Elite unlocks this" | Plan blocked for that difficulty | Opens Razorpay |
| **Mock hub — notice strip** | `UpgradeButton` | "Unlock more with Pro" | `free` hard or mixed blocked | Opens Razorpay |
| **Account page** | `<button>` | "Upgrade to Pro or Elite" | `free` plan | Navigates to `/ + state.scrollTo` |

### Pricing section CTA state by plan

`PricingSection` receives the **raw** plan string (including `lifetime_` prefix) so the `lifetime_pro` / `lifetime_elite` checks in `proColCta()` / `eliteColCta()` fire correctly.

| Current plan | Pro column | Elite column |
|---|---|---|
| `free` | Monthly + Lifetime buttons | Monthly + Lifetime buttons |
| `pro` | "Switch to lifetime" only | Monthly + Lifetime buttons |
| `lifetime_pro` | "Current plan" (no button) | Monthly + Lifetime buttons |
| `elite` | — (no CTA) | "Switch to lifetime" only |
| `lifetime_elite` | — (entire pricing section hidden) | — |

### Backend upgrade path matrix

`_target_plan_is_allowed(current, target)` in `backend/routers/razorpay.py`:

| From ↓ \ To → | `pro` | `elite` | `lifetime_pro` | `lifetime_elite` |
|---|---|---|---|---|
| `free` | ✓ | ✓ | ✓ | ✓ |
| `pro` | — | ✓ | ✓ | ✓ |
| `lifetime_pro` | — | ✓ | — | ✓ |
| `elite` | — | — | — | ✓ |
| `lifetime_elite` | — | — | — | — |

Any path not marked ✓ returns 400 `"This upgrade path is not available."`.

### Unauthenticated upgrade flow

1. `UpgradeButton.handleClick()` detects `user === null`.
2. Navigates to `/auth` with `{ state: { from: location.pathname + location.search, upgradeTier: tier } }`.
   - `from` includes `?path=` if in path mode, so the user returns to the right page after sign-in.
3. `AuthPage` shows an upgrade-intent banner: *"Sign in or create an account to complete your upgrade to **{tier}**."* (tier label is dynamic, not hardcoded).
4. After **sign-in**: `navigate(returnTo, { state: { upgradeTier } })`. User lands back at the original page; they must click the upgrade button again (Razorpay is not auto-opened — deliberate choice, no unsolicited payment modal).
5. After **OAuth**: upgrade intent is saved to `sessionStorage` as `pendingUpgrade` before the provider redirect. `AppRoutes` reads and clears it once auth resolves, then navigates to `returnTo` with `{ upgradeTier }` in state.
6. After **sign-up** (email/password): user lands on the email-verification screen. `create-order` requires `email_verified = true` (returns 403 otherwise), so the upgrade cannot be completed until the user verifies. "Continue to practice" returns the user to `returnTo` (the original page) rather than `/`.

### `successPath` and `?upgraded=true` cleanup

After Razorpay completes, `window.location.assign(successPath)` fires. `successPath` is built by the caller:

- **Landing page**: `/?upgraded=true`
- **AppShell sidebar**: `{pathname}?path={slug}&upgraded=true` (when in path mode) or `{pathname}?upgraded=true`

`AppShell` detects `?upgraded=true` on mount, calls `refreshUser()` and `refresh()` (catalog reload), then strips `upgraded` from the search string while preserving all other params (including `?path=`). `LandingPage` does the same for its own `/?upgraded=true` landing.

### Known limitations

- **No auto-open after sign-in**: returning to the practice page with `upgradeTier` state in the router does not automatically open Razorpay. The exception is `ProgressDashboard`, which opens the Elite readiness modal when `location.state?.upgradeTier === 'elite'`.
- **Email verification blocks upgrade**: a newly registered user cannot complete an upgrade until their email is verified. The upgrade intent is not persisted across the verification step.
