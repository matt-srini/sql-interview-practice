# Mock Interview — Feature Reference

## Overview

The mock interview system lets users practise under real interview conditions: a countdown timer, no mid-session solutions, and a post-session debrief. It is accessible to all authenticated users at `/mock` (requires login) and now frames the surface explicitly as benchmarks plus drills, rather than a single undifferentiated mock mode.

---

## Session Modes

| Mode | Time limit | Questions |
|---|---|---|
| Benchmark | Track-specific fixed shape | Track-specific fixed shape |
| Sprint drill | 30 min | 2 |
| Custom drill | 10–90 min (user-set) | 1–5 (user-set) |

Benchmark is now the primary serious mock mode. It is fixed-shape by track and rejects the Mixed track. Mixed remains drill-only.

Benchmark blueprints:

| Track | Benchmark shape | Time limit |
|---|---|---|
| SQL | 3 executable problems | 60 min |
| Python | 2 executable problems | 50 min |
| Pandas | 2 executable problems | 50 min |
| Statistics | 1 numerical + 2 conceptual | 45 min |
| PySpark | 6 code-adjacent reasoning prompts | 40 min |
| Data Engineering | 6 constructed reasoning prompts | 40 min |
| Data Modeling | 5 constructed reasoning prompts | 40 min |
| ML Fundamentals | 6 constructed reasoning prompts | 40 min |
| Experimentation | 6 constructed reasoning prompts | 40 min |

Benchmark composition now follows track-specific type targets where the bank supports them. For example, PySpark benchmarks still target code-adjacent Spark forms, Statistics benchmarks enforce `1 numerical + 2 conceptual`, and ML Fundamentals / Experimentation benchmarks explicitly pull from scenario, MCQ, predict-output, and debug forms instead of inheriting PySpark's composition rules.

Custom drill validates server-side: `num_questions` must be 1–5, `time_minutes` must be 10–90.

On MockHub, drill modes now get their own planner surface with session shape, purpose, and inline custom controls. That keeps drill setup visually distinct from the fixed-shape benchmark blueprint instead of presenting drills as only alternate mode cards.

---

## Tracks and Difficulties

**Tracks:** SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation, Mixed (SQL + Python + Pandas + PySpark only)

**Mock-only question bank status:**

| Track | Dedicated mock bank? | Notes |
|---|---|---|
| SQL | ✅ | 38 mock-only questions |
| Python | ✅ | 20 mock-only questions |
| Pandas | ✅ | 26 mock-only questions |
| PySpark | ✅ | 21 mock-only questions |
| ML Fundamentals | ✅ | 25 mock-only questions |
| Experimentation | ✅ | 25 mock-only questions |
| Statistics | ✅ | 8 mock-only questions |
| Data Modeling | ✅ | 1 mock-only question (expanding) |
| Data Engineering | ✅ | 1 mock-only question (expanding) |

Sessions for tracks without a dedicated mock bank draw from practice questions. The Mixed track pools only the four code-execution tracks (SQL, Python, Pandas, PySpark) and is available only in drill modes.

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

`GET /api/mock/analytics` returns aggregated stats over the last 50 completed sessions. The session-level metrics are now separated so benchmark comparisons stay clean:

- `total_sessions`, `sessions_last_30d`
- `benchmark_summary`: score/time/trend/breakdown metrics for benchmark sessions only
- `drill_summary`: score/time/trend/breakdown metrics for non-benchmark sessions
- `mode_breakdown`: counts for `benchmark` and `drill`
- `top_concepts`: top 5 by attempt count (with accuracy)
- `weak_concepts`: worst 3 concepts by accuracy (≥3 attempts, <60%)

Returns 403 for non-Elite plans. On MockHub, the primary Elite panel now uses `benchmark_summary` as the comparable benchmark view and surfaces drills as a secondary summary.

---

## Active Session (`/mock/:id`)

- **Session framing card** in the left panel makes the current session type explicit: benchmark sessions show the fixed-shape blueprint framing for that track, while drills show flexible follow-up framing.
- **Countdown timer** in the topbar — colour-coded: normal → amber (<10 min) → red (<3 min). Browser tab title updates with remaining time.
- **Auto-finish** when timer reaches 0.
- **Question navigation** — numbered dot tabs, each shows solved/unsolved state.
- **Run code** — SQL, Python, and Pandas support running code against the live evaluator mid-session (same as practice mode). PySpark is MCQ-only.
- **SQL schema viewer** — Description / Schema toggle in the left panel.
- **Hints and concept tags** visible on each question.
- **Submit per question** — returns correct/incorrect + feedback immediately. **No solution revealed mid-session** (verified by API; solutions are withheld from the `/submit` response).
- **Exit confirmation** — clicking Exit or End Session shows a confirm dialog.
- **Discard prompt** — if a user exits within ~60 seconds of starting with no activity (no submissions), the frontend offers to discard the session entirely. `DELETE /api/mock/:id` removes it from history and stats. The server enforces a 120-second window; requests outside the window return 403.
- **Active session guard** — starting a new session while one is already active returns 409 from `POST /api/mock/start`. The response body includes the existing `session_id`, `track`, `difficulty`, and `mode` so the UI can offer a "Resume" link.
- **Session reload recovery** — navigating back to `/mock/:id` restores state from the server. Remaining time is recomputed from `started_at`.
- **Mobile** — collapsible left panel for the question description.

---

## Post-session Summary

Shown after `POST /api/mock/:id/finish`:

- **Mode-aware summary framing** — topbar and intro block now distinguish benchmark vs drill, restate the session shape, and keep older legacy `60min` sessions readable.
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
- **Restart CTA** — routes back to `/mock` as `Start another benchmark` or `Start another drill` depending on the finished session mode.

---

## History (`/mock` page)

- Shows the last 20 sessions split into benchmark and drill sections so fixed-shape benchmarks are not visually blended with flexible drills.
- Mode labels are normalized in the UI so users see `Benchmark`, `Sprint drill`, `Custom drill`, or `Full (legacy)` instead of raw stored mode keys.
- **Review →** for completed sessions, **Resume →** for in-progress ones.
- Empty state links to practice tracks and the dashboard.

---

## How to Use (the `?` button on /mock)

1. **Choose session type** — Benchmark for the fixed-shape track benchmark, Sprint drill for a short calibration round, or Custom drill for targeted follow-up practice.
2. **Pick track and difficulty** — Difficulty buttons show live access state (remaining daily sessions or upgrade CTAs). Drill modes also show a dedicated planner card with the session shape before you start.
3. **Track benchmark availability** — Mixed stays drill-only; single-track sessions can use Benchmark.
4. **(Elite, SQL track)** Optionally select a **Company** filter.
5. **Start** — the timer starts immediately.
6. **During the session** — write your answer in the editor, run it to check, and submit each question. No solutions are shown yet.
7. **End session** — click "End session" or let the timer run out.
8. **Review** — see your score, solutions to every question, and (Elite) your concept weak-spots with a drill link.

---

## Backend Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/mock/access` | Required | Pre-flight: per-difficulty access state for a given track |
| GET | `/api/mock/history` | Required | Last 20 sessions |
| GET | `/api/mock/analytics` | Required (Elite) | Aggregate analytics over last 50 sessions — benchmark/drill summaries, trends, and concept signals |
| POST | `/api/mock/start` | Required | Start a session; accepts `mode="benchmark"` for fixed-shape track benchmarks and `focus_concepts` for Elite focus mode. Returns 409 if an active session already exists (body includes `session_id`, `track`, `difficulty`, `mode`). |
| GET | `/api/mock/:id` | Required | Load/reload session state |
| POST | `/api/mock/:id/submit` | Required | Submit one answer mid-session |
| POST | `/api/mock/:id/finish` | Required | End session, get full summary with solutions |
| DELETE | `/api/mock/:id` | Required | Discard an active session (no history entry, no stats impact). Must be called within 120 s of `started_at`. Returns 204. Returns 403 if too old, 400 if already completed. |

---

## Test Coverage

See `backend/tests/test_11_mock.py` for the focused mock backend suite covering:
- Access endpoint (all plans, all difficulties)
- Daily limit enforcement (free medium 1/day, pro hard 3/day, elite unlimited)
- Session lifecycle, summary visibility, and mixed-session behavior for the current mock system
- Benchmark mode track-shape enforcement, including the statistics `1 numerical + 2 conceptual` blueprint and mixed-track rejection
- Analytics separation between benchmark and drill sessions
- Track-specific benchmark composition for reasoning tracks
- Custom mode validation
- Mixed track sessions
- Company filter gating (free/pro blocked, elite/lifetime_elite allowed)
- History endpoint shape
- Solution visibility (absent during session, present after finish)

There is no standalone `test_session_debrief.py` file in the current repository. Debrief behavior is validated indirectly through the mock and insights suites plus manual product review.
