# PostHog "Acquisition Funnel" dashboard (M9) — build spec

**Status:** instrument verified, dashboard not yet built (PostHog MCP is read-only, so it cannot create the dashboard for us). This doc is the exact build a human runs in PostHog in ~5 minutes. Once write-to-dashboards is granted, the same spec can be created programmatically.

**Owner surface:** PostHog project `Default project` (id `479535`), org `datathink`, timezone UTC. Base URL `https://us.posthog.com/project/479535`.

Related: [`gtm-strategy.md`](gtm-strategy.md) (the funnel this instruments), [`editorial-calendar.md`](editorial-calendar.md).

---

## 1. Instrument state (verified 2026-06-29 via PostHog MCP)

The seven funnel events are all wired in frontend code. Pre-launch, only dev/test traffic exists, so volumes are near-zero. That is expected. The point of M9 is to have the instrument ready, not to read data.

| Funnel step | Event | Fired yet? | Key custom properties (from code) |
|---|---|---|---|
| 1. Arrival | `sample_landed` | not yet (0 vol) | `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `referrer`, `role` |
| 2. Tried a sample | `sample_submitted` | yes | `track`, `difficulty`, `question_id`, `correct` |
| 3. Signed up | `account_created` | not yet (0 vol) | `method` (`password`) |
| 4. Solved a real question | `question_solved` | yes | `track`, `difficulty`, `question_id`, `first_try` |
| 5. Started a mock | `mock_started` | yes | (mock session props) |
| 6. Began checkout | `plan_upgrade_started` | not yet (0 vol) | `tier`, `source`, `rail` (`paddle`/`razorpay`) |
| 7. Paid | `plan_upgraded` | not yet (0 vol) | `tier`, `source`, `rail` |

PostHog only lists an event in the schema once it has been ingested at least once. The four "not yet" events are absent from the schema purely because no one has triggered them in this pre-launch window, not because the instrument is missing. `posthog-js` also auto-attaches UTM params to every event and stores first-touch UTM as person properties (`$initial_utm_source`, etc.), so channel attribution has a fallback even before the explicit `sample_landed` props accumulate.

Property keys are the source of truth from code: `frontend/src/analytics.js` (`sample_landed`, UTM keys), `frontend/src/contexts/AuthContext.js` (`account_created`), `frontend/src/components/UpgradeButton.js` (`plan_upgrade_started`/`plan_upgraded`).

---

## 2. What to build

One dashboard, **"Acquisition Funnel"**, with the tiles below. Build each insight, then add it to the dashboard. Set the dashboard default date range to **Last 30 days** (each tile can override).

### Tile A — Acquisition funnel (the spine)
- **Insight type:** Funnel
- **Steps, in order:** `sample_landed` → `sample_submitted` → `account_created` → `question_solved` → `mock_started` → `plan_upgrade_started` → `plan_upgraded`
- **Conversion window:** 14 days (default) is fine for a prep tool; consider 30 days once real traffic lands.
- **Order:** "Sequential" is too strict (a user can sign up before trying a sample). Use **"Any order"** is too loose. Choose **"Ordered"** (steps happen in this order but other events may occur between them).
- **Aggregation:** Unique users.
- Name it `Acquisition funnel (full)`.

> Note: many real users skip step 1 (they land on a role page or `/guides`, not a sample). Keep a second funnel, `Activation funnel (signup-first)`, with steps `account_created` → `question_solved` → `mock_started` → `plan_upgraded` for the cohort that enters past the sample.

### Tile B — North star: Weekly Activated Learners
"Activated" = signed up **and** solved at least one real question in the same 7-day window.
- **Insight type:** Funnel, **visualization = "Historical trends"** (the funnel-trend line over time), interval **weekly**.
- **Steps:** `account_created` → `question_solved`
- **Aggregation:** Unique users, **first-time for user** math on `account_created` so each user counts once at signup.
- The trend line's *converted count* per week is the Weekly Activated Learners number. Name it `North star — Weekly Activated Learners`.
- Alternative if you want a single rolling number instead of a trend: a Trends insight with two series (`account_created` unique users, `question_solved` unique users) and a formula is **not** equivalent (it does not enforce same-user AND). The funnel is the correct definition; do not substitute a ratio of two independent counts.

### Tile C — Channel attribution (where arrivals come from)
Three Trends insights, each `sample_landed`, unique users, broken down by one property:
- C1: breakdown by `utm_source`
- C2: breakdown by `utm_campaign`
- C3: breakdown by `$referring_domain` (cleaner than raw `referrer`; use `referrer` only if you need the full URL)
- Chart type: bar (value), Last 30 days. Name them `Arrivals by utm_source` / `by utm_campaign` / `by referrer domain`.

### Tile D — Conversion-rate tiles (three single-number cards)
Each is a Funnel insight, **visualization = "Conversion"**, showing the overall rate. Use the number/big-value display.
- D1 `Sample → signup`: steps `sample_submitted` → `account_created`
- D2 `Signup → activation`: steps `account_created` → `question_solved`
- D3 `Activation → paid`: steps `question_solved` → `plan_upgraded`
- Aggregation: unique users, Last 30 days.

### Tile E — Event trends over time
One Trends insight, **all seven events as separate series**, unique users, weekly interval, line chart, Last 90 days. Name it `Funnel events over time`. This is the at-a-glance "is anything moving" tile.

---

## 3. Step-by-step (PostHog UI)

1. **New insight → Funnel.** Add the seven events for Tile A in order. Set order = Ordered, window 14d, unique users. Save as `Acquisition funnel (full)`.
2. Repeat for Tile B: Funnel with the two steps, switch the toggle to **Historical trends**, interval weekly, save.
3. Tiles C: **New insight → Trends.** Series = `sample_landed`, unique users. Add breakdown → event property → `utm_source`. Save. Duplicate, swap the breakdown to `utm_campaign`, then `$referring_domain`.
4. Tiles D: **New insight → Funnel** with two steps each, switch visualization to **Conversion** (single number), save the three.
5. Tile E: **New insight → Trends**, add all seven events as series, unique users, weekly, save.
6. **New dashboard → "Acquisition Funnel."** Add all of the above. Drag the funnel spine (A) and north star (B) to the top row; conversion cards (D) as a row of three; channel (C) and trends (E) below. Set dashboard date range Last 30 days.
7. Optional: pin it, and set the north-star tile (B) as the dashboard's primary tile.

---

## 4. Guardrails / gotchas

- **Bot filtering:** PostHog now tags traffic with `$virt_is_bot` / `$virt_traffic_type`. For a clean funnel, add a global dashboard filter `$virt_is_bot = false` (AI crawlers will otherwise inflate `sample_landed` and `$pageview` once the SEO surfaces get indexed).
- **`account_created` is password-only today.** OAuth/magic-link signups do not yet fire it (see the TODO in `AuthContext.js`). Until that backend `is_new` signal exists, the signup step undercounts OAuth users. Note this on the dashboard description so no one misreads a low signup-conversion as a funnel problem.
- **Do not approximate the north star as a ratio of two trends.** Two independent unique-user counts (`account_created`, `question_solved`) do not guarantee the same users; only the funnel enforces "same user did both."
- **Pre-launch zeros are correct.** Empty tiles now are the instrument working, not a defect.

---

## 5. If write access is granted later

With `insights` + `dashboards` write scope on the PostHog MCP (or app token), this entire spec is reproducible programmatically: create each insight via `insight-create` with the query schemas above (`query-funnel` for A/B/D, `query-trends` for C/E), then `dashboard-create` and attach. The read-only confirmation pass (events present, property keys correct) is already done.
