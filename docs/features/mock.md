# Mock Interview — Feature Reference

## Overview

The mock interview system lets users practise under real interview conditions: a countdown timer, no mid-session solutions, and a post-session debrief. It is accessible to all authenticated users at `/mock` (requires login).

---

## Session Modes

| Mode | Time limit | Questions |
|---|---|---|
| Quick | 30 min | 2 |
| Full | 60 min | 3 |
| Custom | 10–90 min (user-set) | 1–5 (user-set) |

Custom mode validates server-side: `num_questions` must be 1–5, `time_minutes` must be 10–90.

---

## Tracks and Difficulties

**Tracks:** SQL, Python, Pandas, PySpark, Mixed (draws from all four)

**Difficulties:** Easy, Medium, Hard, Mixed (blend)

---

## Plan-based Access Gates

| Feature | Free | Pro | Elite / Lifetime Elite |
|---|---|---|---|
| Easy mocks | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited |
| Medium mocks | ✅ Unlimited easy · **1 medium/day** (requires medium unlocked in practice first) | ✅ Unlimited | ✅ Unlimited |
| Hard mocks | ❌ Plan-locked (upgrade to Pro) | ✅ **3 hard/day** | ✅ Unlimited |
| Mixed mocks | ✅ (restricted to unlocked difficulties) | ✅ | ✅ |
| Company-filtered mocks | ❌ | ❌ | ✅ (SQL track only) |
| Focus mode (concept-targeted sessions) | ❌ | ❌ | ✅ |
| Weak-spot insights in summary | ❌ | ✅ | ✅ |
| **Session debrief (coaching narrative)** | ❌ | ❌ | ✅ |
| Mock history analytics | ❌ | ❌ | ✅ |

**Pre-flight access check:** `GET /api/mock/access?track=<track>` is called every time the track selector changes. It returns per-difficulty `can_start`, `daily_limit`, `daily_used`, `needs_upgrade`, and `block_copy` so the UI can render gate state without a round-trip on Start.

---

## Company Filter (Elite only)

Elite users see a **Company** dropdown when the SQL track is selected. Selecting a company sends `company_filter: "Meta"` (etc.) in the start payload. The backend validates that the user has Elite tier before allowing the session to proceed.

Available companies: Airbnb, Amazon, Amplitude, Databricks, Google, LinkedIn, Meta, Microsoft, Netflix, PayPal, Salesforce, Shopify, Snowflake, Stripe, Zendesk, eBay.

---

## Focus Mode (Elite only)

Elite users can enable **Focus mode** on the mock setup page. When active, a concept pill multi-select appears (1–3 concepts max). The session pool is filtered to questions tagged with the selected concepts.

**Fallback:** if fewer matching questions exist than needed, the session fills remaining slots from the general pool and sets `focus_fallback: true` in the `/start` response. The session page shows a subtle notice when this happens.

**Request:** `focus_concepts: ["WINDOW FUNCTIONS", "COHORT RETENTION"]` in the `POST /api/mock/start` body.

---

## Mock History Analytics (Elite only)

`GET /api/mock/analytics` returns aggregated stats over the last 50 completed sessions:

- `total_sessions`, `sessions_last_30d`
- `avg_score_pct`, `best_score_pct`, `avg_time_used_pct`
- `track_breakdown`: per-track session count and avg score
- `difficulty_breakdown`: per-difficulty session count and avg score
- `score_trend`: last 10 session scores (chronological, for sparkline)
- `top_concepts`: top 5 by attempt count (with accuracy)
- `weak_concepts`: worst 3 concepts by accuracy (≥3 attempts, <60%)

Returns 403 for non-Elite plans. Panel appears on MockHub.js above the history table.

---

## Active Session (`/mock/:id`)

- **Countdown timer** in the topbar — colour-coded: normal → amber (<10 min) → red (<3 min). Browser tab title updates with remaining time.
- **Auto-finish** when timer reaches 0.
- **Question navigation** — numbered dot tabs, each shows solved/unsolved state.
- **Run code** — SQL, Python, and Pandas support running code against the live evaluator mid-session (same as practice mode). PySpark is MCQ-only.
- **SQL schema viewer** — Description / Schema toggle in the left panel.
- **Hints and concept tags** visible on each question.
- **Submit per question** — returns correct/incorrect + feedback immediately. **No solution revealed mid-session** (verified by API; solutions are withheld from the `/submit` response).
- **Exit confirmation** — clicking Exit or End Session shows a confirm dialog.
- **Session reload recovery** — navigating back to `/mock/:id` restores state from the server. Remaining time is recomputed from `started_at`.
- **Mobile** — collapsible left panel for the question description.

---

## Post-session Summary

Shown after `POST /api/mock/:id/finish`:

- **Score headline** — `X/Y correct`.
- **(Pro+)** Baseline comparison — `X% above/below your historical accuracy` pulled from `/api/dashboard/insights`.
- **Time used** — `MM:SS used of MM:SS limit`.
- **Per-question breakdown** — solved/unsolved badge, time spent, expandable **"See solution"** toggle (reference solution + explanation, revealed only after finish).
- **(Pro+) Concept breakdown table** — lists every concept that appeared in the session with `correct / attempted`, sorted worst-first.
- **(Pro+) "Drill weak concepts →"** — links to `/practice/:track?concepts=...` pre-filtered to the worst 2 concepts from the session.
- **(Elite) Session debrief** — a coaching narrative panel shown above the per-question list. Generated server-side (template-based, no external AI) from session data and submission history. Contains:
  - **Headline** — one-sentence overall verdict with score and time context.
  - **Patterns** — up to 3 observations: which concepts were strong/weak, follow-up question performance, and whether a single question dominated session time.
  - **Priority action** — the single most important next step, with a direct link to the recommended learning path when one exists.
  - Historical context: if a session concept matches a known weak area in the user's submission history (≥3 past attempts, <60% accuracy), the pattern observation uses stronger "known weakness" language.
  - Returned as `debrief` in the `POST /api/mock/:id/finish` response. `null` for non-Elite plans.
- **(Elite) "Known weakness" badge** — when a session concept matches one of the user's cross-session `weakest_concepts` from the dashboard insights, the concept row is highlighted in amber and tagged "known weakness". Elite users also see a path recommendation link ("Study in {title} →") when `recommended_path_slug` is present; Pro users see a generic drill link.
- **Share result** — copies a summary string to clipboard.

---

## History (`/mock` page)

- Shows the last 20 sessions in a table: Date, Mode, Track, Difficulty, Score (X/Y), Time limit.
- **Review →** for completed sessions, **Resume →** for in-progress ones.
- Empty state links to practice tracks and the dashboard.

---

## How to Use (the `?` button on /mock)

1. **Choose mode** — Quick (30 min, 2 questions), Full (60 min, 3 questions), or Custom.
2. **Pick track and difficulty** — Difficulty buttons show live access state (remaining daily sessions or upgrade CTAs).
3. **(Elite, SQL track)** Optionally select a **Company** filter.
4. **Start** — the timer starts immediately.
5. **During the session** — write your answer in the editor, run it to check, and submit each question. No solutions are shown yet.
6. **End session** — click "End session" or let the timer run out.
7. **Review** — see your score, solutions to every question, and (Elite) your concept weak-spots with a drill link.

---

## Backend Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/mock/access` | Required | Pre-flight: per-difficulty access state for a given track |
| GET | `/api/mock/history` | Required | Last 20 sessions |
| GET | `/api/mock/analytics` | Required (Elite) | Aggregate analytics over last 50 sessions — scores, trends, concepts |
| POST | `/api/mock/start` | Required | Start a session; accepts `focus_concepts` for Elite focus mode |
| GET | `/api/mock/:id` | Required | Load/reload session state |
| POST | `/api/mock/:id/submit` | Required | Submit one answer mid-session |
| POST | `/api/mock/:id/finish` | Required | End session, get full summary with solutions |

---

## Test Coverage

See `backend/tests/test_mock.py` for the full test suite covering:
- Access endpoint (all plans, all difficulties)
- Daily limit enforcement (free medium 1/day, pro hard 3/day, elite unlimited)
- Full session lifecycle for all 4 tracks (SQL, Python, Pandas, PySpark)
- Custom mode validation
- Mixed track sessions
- Company filter gating (free/pro blocked, elite/lifetime_elite allowed)
- History endpoint shape
- Solution visibility (absent during session, present after finish)

`backend/tests/test_session_debrief.py` covers the debrief builder in isolation (27 unit tests):
- Plan gating (Elite-only; None for Pro/Free/empty)
- Headline generation across all score/time combinations
- Pattern observations (strong concepts, weak concepts, follow-up, time-sink, known-weakness language)
- Priority action and path recommendation logic
- Response shape (all required keys, no internal keys leaked)
