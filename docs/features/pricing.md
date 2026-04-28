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

| Feature | Free | Pro | Elite |
|---|---|---|---|
| Easy questions (32 SQL · 30 Python · 22 Pandas · 38 PySpark) | ✓ All | ✓ All | ✓ All |
| Medium questions | Batch-gated by easy solves | ✓ All | ✓ All |
| Hard questions | Batch-gated (cap: 15 code / 10 PySpark) | ✓ All | ✓ All |
| Learning paths | 3 per track (tier=`free` paths) | All (up to 5 per track) | All (up to 5 per track) |
| Easy mocks | Unlimited | Unlimited | Unlimited |
| Medium mocks | 1 per day | Unlimited | Unlimited |
| Hard mocks | Blocked | 3 per day | Unlimited |
| Mixed mocks | Follows track limits | Follows track limits | Unlimited |
| Company-filtered mocks | Blocked | Blocked | ✓ |
| Weak-spot insights after mock | Blocked | Blocked | ✓ (concept accuracy + drill link) |
| Top-3 weak areas coaching panel (dashboard) | Blocked | Blocked | ✓ (concept, accuracy %, summary, path + drill links) |

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
7. The page redirects to `/practice?upgraded=true`.

### Starting state: Pro user

- Pro column: shows lifetime Pro button only ("Switch to lifetime — ₹7,999").
- Elite column: shows monthly Elite button + lifetime Elite button.
- Pro user cannot create an order for `pro` (same plan) — backend returns 400.

### Starting state: Elite user

- Pro column: no CTA shown.
- Elite column: shows lifetime Elite button only ("Switch to lifetime — ₹14,999").
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
| `lifetime_pro` | 799,900 (₹7,999) | 8,900 ($89) |
| `lifetime_elite` | 1,499,900 (₹14,999) | 16,900 ($169) |

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
  "amount": 799900,
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
