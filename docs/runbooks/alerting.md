# Alerting runbook — payment failures & uptime

Operator setup guide. All steps are performed once in the relevant dashboards
(Sentry, UptimeRobot / Better Stack). Nothing here requires a code deploy.

> This covers **how an alert reaches you**. For what happens *after* — turning a
> Sentry issue into a deployed fix — see [`sentry-fix-pipeline.md`](sentry-fix-pipeline.md).

---

## 1. What is captured and how to find it

`backend/sentry_utils.py::capture_payment_failure` fires at every revenue-critical
failure point. Every event carries two stable Sentry tags:

| Tag | Values | Purpose |
|---|---|---|
| `alert` | `payment_failure` (always) | Single filter for the alert rule below |
| `payment_stage` | see table below | Narrows to the exact failure point |
| `payment_provider` | `razorpay` \| `paddle` \| absent | Which billing rail |

### `payment_stage` values

| Stage | Where | What it means |
|---|---|---|
| `webhook_signature` | `paddle.py` / `razorpay.py` | Signature verification failed — possible spoofed POST |
| `webhook_parse` | `paddle.py` | Webhook body is not valid JSON |
| `plan_resolution` | `paddle.py` / `razorpay.py` | Payment event arrived but `user_id` or `target_plan` could not be resolved — money collected, entitlement NOT applied |
| `plan_persist` | `paddle.py` / `razorpay.py` | DB write for plan upgrade threw — money collected, Razorpay/Paddle confirmed, our DB was not updated |
| `payment_failed` | `razorpay.py` | Razorpay sent `payment.failed` — not immediately a billing inconsistency but worth monitoring for persistent failures |
| `verify_payment_signature` | `razorpay.py` | Client-side verify-payment call had a bad signature |
| `switch_now` | `account.py` | Razorpay accepted an instant plan switch but the DB write failed — user paying for new tier, system shows old tier |

### Searching in Sentry

- **Issues → Search:** `tags[alert]:payment_failure` — shows all payment failure events.
- Add `tags[payment_stage]:plan_persist` etc. to narrow.
- The `payment_failure_detail` context block on each event carries non-sensitive
  identifiers: `event_id`, `event_type`, `target_plan`, `error` (exception class name),
  `subscription_id`. Use these to look up the event in Razorpay/Paddle dashboards.

---

## 2. Sentry alert rules to create

> **Getting to the alert builder:** Alerts are **not** under the org gear/Settings.
> Reach the builder with **⌘K → "Create Alert"**, or the direct URL
> `https://<org>.sentry.io/alerts/rules/` → **Create Alert**.
>
> **Free-plan note:** the **Issues** alerts (Rules A, C, D) work on the free
> Developer plan — these are the must-haves. The **Metric** alerts (Rules B, E,
> the spike rules) require a paid **Team** plan; if "Metric" isn't offered as an
> alert type, skip B/E for now. Use **email** as the action unless the Slack
> integration is connected.

### Rule A — Any payment failure (highest priority)

> Create Alert → Issues (or Error)

| Field | Value |
|---|---|
| **Name** | `payment_failure — any` |
| **Environment** | `production` |
| **Condition** | "An issue is seen" |
| **Filter** | `tags[alert] = payment_failure` |
| **Action** | Send notification → Slack `#alerts-billing` AND email `ops@datathink.co` |
| **Threshold** | 1 event in 5 minutes (alert on first occurrence) |

This catches all stages in a single rule. Tune down the noise by also adding:

### Rule B — Error-rate spike (high volume = attack or outage)

> Create Alert → Metric Alert → Number of Errors

| Field | Value |
|---|---|
| **Name** | `payment_failure — spike` |
| **Environment** | `production` |
| **Query** | `tags[alert]:payment_failure` |
| **Threshold** | CRITICAL when count > 10 in 5 minutes |
| **Action** | PagerDuty or Slack `#alerts-billing` with `@oncall` |

A burst of `webhook_signature` failures in a short window is a strong signal of a
replay or brute-force attempt and warrants an urgent page.

### Rule C — `plan_resolution` or `plan_persist` (revenue impact)

Create a second, narrower rule so these always page immediately even if Rule B's
count threshold is not yet reached:

| Field | Value |
|---|---|
| **Name** | `payment_failure — entitlement not applied` |
| **Environment** | `production` |
| **Filter** | `tags[payment_stage] = plan_resolution OR tags[payment_stage] = plan_persist OR tags[payment_stage] = switch_now` |
| **Threshold** | 1 event in 1 minute |
| **Action** | PagerDuty or direct email to the on-call engineer |

These stages mean money was collected but the user's entitlement was not persisted —
they should be treated as P1.

### Baseline application errors (non-payment)

Rules A–C only cover billing. A non-payment 500 — a sandbox/DuckDB crash, an auth
regression, any unhandled exception — would otherwise sit in Sentry unannounced.
These two rules are the safety net for everything else. (4xx app errors are already
dropped by `before_send` in `sentry_utils.py`, so these fire only on real errors.)

### Rule D — Any new production issue

> Create Alert → Issues

| Field | Value |
|---|---|
| **Name** | `new-issue — production baseline` |
| **Environment** | `production` |
| **Condition** | "A new issue is created" (fires once per *novel* issue, not per event) |
| **Filter** | none — every new error type, payment or not |
| **Action** | Send notification → Slack `#alerts` AND email `ops@datathink.co` |

This is the single most important non-payment rule: it guarantees you hear about a
class of error the first time it ever happens, instead of when a user emails you.

### Rule E — Overall error-rate spike

> Create Alert → Metric Alert → Number of Errors

| Field | Value |
|---|---|
| **Name** | `error-rate — spike` |
| **Environment** | `production` |
| **Query** | none (all errors) |
| **Threshold** | CRITICAL when count > 50 in 5 minutes — **tune to your baseline traffic** |
| **Action** | Slack `#alerts` with `@oncall` |

Catches an outage or a regression hitting many users at once, even when each error
is an already-known (non-new) issue that Rule D won't re-fire for.

---

## 3. Uptime monitor

Use **UptimeRobot** (free tier) or **Better Stack** (free tier) to monitor the
`/health` endpoint.

### Recommended settings (UptimeRobot)

1. **Monitor type:** HTTP(s)
2. **URL:** `https://api.datathink.co/health` (or your Railway domain)
3. **Interval:** 5 minutes (UptimeRobot free-tier floor; Better Stack free does 30s–1min)
4. **Alert contact:** email + Slack webhook
5. **Alert after:** 2 consecutive failures (avoids single-blip noise)
6. **Keyword match (optional):** `"status":"ok"` — ensures the endpoint returns a
   valid body, not just a 200 from a CDN or load balancer.

A down alert from the uptime monitor plus a simultaneous `payment_failure` Sentry
alert is a strong signal of a full-service outage rather than a transient webhook
replay — treat that combination as P0.

---

## 4. Remediation quick-reference

| Stage | Immediate action |
|---|---|
| `plan_resolution` | Look up `event_id` in Razorpay/Paddle dashboard. Identify the user from `user_id` in the Sentry extra context. Manually apply the plan via `POST /api/admin/grant-plan`. |
| `plan_persist` | Same as above — user may have been double-charged or left on free. Check `plan_changes` table. |
| `switch_now` | Check `users` table for the `user_id`. If `plan` column still shows old tier, run `set_user_plan` manually or via the admin grant endpoint. |
| `webhook_signature` | Single occurrence is likely noise; a burst in 5 min is a potential replay attack. Rotate the webhook secret in Razorpay/Paddle dashboard and update `RAZORPAY_WEBHOOK_SECRET` / `PADDLE_WEBHOOK_SECRET` in Railway env. |
| `payment_failed` | Check Razorpay dashboard for retry status. No immediate entitlement action needed unless the subscription enters `halted` (handled by the `subscription.halted` webhook). |
