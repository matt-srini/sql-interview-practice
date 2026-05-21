# Mock Interview — Feature Reference

> **Canonical source of truth for the mock plan-tier matrix, chain atomicity, and Interview Loop contract.** Other docs (CLAUDE.md, pricing.md, north-star.md) reference this file rather than restating gates. Any change to mock gating must land here first.

## Overview

The mock interview system lets users practise under real interview conditions: a countdown timer, no mid-session solutions, and a post-session debrief. It is accessible to all authenticated users at `/mock` (requires login) and frames the surface explicitly as benchmarks plus drills, never as "practice with a timer."

datathink's mock layer is a **benchmark, not a faster version of practice**. Every design decision below — atomicity, plan gates, mode separation — exists to defend the readiness signal.

---

## Session Modes (canonical, post-2026-05 refactor)

| Mode | Time limit | Questions | Purpose |
|---|---|---|---|
| `benchmark` | Track-specific fixed shape | Track-specific fixed shape | The serious readiness signal. Fixed blueprint. Compares against historical baseline. |
| `short_drill` | 30 min | 2 | Fast calibration. Warm-up. Habit hook. |
| `custom_drill` | 10–90 min (user-set) | 1–5 (user-set) | User-tuned to competency. Targeted practice under timed conditions. |

The legacy `60min` 3-question drill is retired; `custom_drill` covers that range. `60min` sessions in history are read-only.

Benchmark is fixed-shape by track and rejects the Mixed track. Mixed remains drill-only. Custom drill validates server-side: `num_questions` must be 1–5, `time_minutes` must be 10–90.

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

## Plan-tier Matrix (canonical SoT)

This is the single source of truth. Any other doc that mentions mock plan gates must link here rather than restating.

### Quick view

| Capability | Free | Pro | Elite / Lifetime Elite |
|---|---|---|---|
| `short_drill` (easy) | ✅ Unlimited, fresh-first from practice pool | ✅ Unlimited (inherits Free) | ✅ Unlimited |
| `short_drill` (medium/hard) | ❌ | ✅ Counts toward 3-drill/day cap | ✅ Unlimited |
| `custom_drill` (any difficulty) | ❌ | ✅ Counts toward 3-drill/day cap | ✅ Unlimited |
| `benchmark` (any track/difficulty) | ✅ **1 per rolling 7 days** | ✅ 3/day | ✅ Unlimited |
| Mock-only question pool | ❌ — Free draws from practice pool only | ✅ | ✅ |
| Follow-up chains | ❌ (no mock-only access) | ✅ | ✅ |
| `focus_concepts` filter | ❌ | ❌ | ✅ |
| Interview Loop mode | ❌ | ❌ | ✅ |
| Mock-only company filter (SQL) | ❌ | ❌ | ✅ |
| Post-session score + per-Q solutions | ✅ | ✅ | ✅ |
| Detailed history + concept breakdown | ❌ | ✅ | ✅ |
| Cross-session trend, dimension analysis, readiness score, study plan, debrief | ❌ | ❌ | ✅ |
| Chain reclaim window (discard without consuming) | n/a | 2 min | 2 min |

### Daily caps, explained

- **Free** — Unlimited easy `short_drill` so the daily habit hook lives without artificial counters. Exactly 1 `benchmark` per rolling 7 days (NOT calendar week — rolling avoids Monday-spike load and "I wasted my Sunday slot" frustration), any track, any difficulty. This is the *demo* — the free user gets to experience real benchmarking once a week and feel what they would be upgrading to. No mock-only content, no chains, no focus, no Loop.

- **Pro** — Inherits the Free benefits and adds:
  - **3 drills/day, combined** across `short_drill` (medium/hard) + `custom_drill` (any difficulty). User chooses how to spend: 3 short, 3 custom, or any mix. Easy `short_drill` does not count toward this cap.
  - **3 `benchmarks`/day**, any track/difficulty.
  - Mock-only content pool unlocked. Chain follow-ups eligible.
  - Daily caps reset at user-local midnight (server-side: tracked as UTC day with user's IANA TZ offset).

- **Elite** — All Pro features, plus:
  - Counts surfaced as "Unlimited" in UI. Backend enforces a soft anti-abuse rate-limit (~10 sessions/hour rolling) that never displays unless triggered.
  - `focus_concepts` filter (1–3 concept families per session).
  - **Interview Loop mode** (chain-driven iterative interviewer dialogue — see [Interview Loop](#interview-loop-mode-elite-only) below).
  - Deep analytics (cross-session trends, dimension analysis, readiness score, study plan), debrief coaching narrative.

### Why this shape (design rationale)

- **Free getting a real `benchmark` once a week is the conversion mechanism.** A free user who only ever sees easy drills cannot picture what they'd be paying for. Letting them experience the full benchmark loop once a week (with debrief) creates a clean conversion moment: "want another? upgrade."
- **The 1-benchmark/week limit is rolling 7 days from last benchmark**, not calendar week. Smoother UX, no Monday spike, no Sunday regret.
- **Pro's combined 3-drill cap (not 2+2)** preserves user agency without doubling the mental counter.
- **Easy `short_drill` is unlimited at every tier.** The habit loop matters; daily counters on easy mocks read as mobile-game energy, off-brand for a serious professional tool.
- **No daily cap on a single counter — caps live separately for drills and benchmarks.** Combining them would force users to choose between a benchmark (the demo experience) and warm-up drills, which is a false tradeoff.
- **6 total/day for Pro (3 + 3)** is aggressive but matches peak prep cadence (week-of-interview). Elite still wins clearly on count + focus + Loop + analytics.

### Pre-flight access check

`GET /api/mock/access?track=<track>` is called every time the track selector changes. Returns per-difficulty + per-mode `can_start`, `daily_limit`, `daily_used`, `weekly_limit`, `weekly_used` (free benchmark), `needs_upgrade`, `block_copy` so the UI can render gate state without a round-trip on Start.

### Surface in the UI

Plan-tier rules must be visible to the user, not buried in account settings. Required surfaces:
- **MockHub** — short note under the track/mode selector showing the user's remaining daily/weekly count and the upgrade nudge when relevant ("Pro · 2 of 3 benchmarks used today" / "Free · weekly benchmark available — use it any time before Sun Mar 12").
- **Plan upgrade modal** — triggered when a gated capability is clicked. Modal explicitly lists what unlocks at each tier in plain language, with the matrix above as the source.
- **Mock-only badge** in MockSession — when a question is from the mock-only pool (Pro/Elite indicator).
- **Chain indicator** — when a follow-up question loads, banner indicates "Follow-up from previous question · {dimension}" so the user knows the interviewer-pivot framing is intentional.

---

## Follow-up Chain Atomicity (Pro/Elite — mock-only content)

Follow-up chains are the platform's way of simulating real interviewer pivots — the moment a senior interviewer says "now exclude refunded orders" or "what if the dataset were 10× larger?" Every chain is anchored to a parent question and travels as an atomic unit.

### The atomicity rule (locked decision)

**A parent question and all entries in its `follow_ups[]` form an atomic mock unit. A user sees the entire chain together, exactly once, ever. Zero or all.**

This rule applies across every mock mode (benchmark, short_drill, custom_drill, Interview Loop) and to every Pro and Elite user. It is the simplest mental model and the strongest guarantee against signal dilution.

### Schema

On the **parent** question JSON (always `mock_only: true`):
```json
"follow_ups": [<id1>, <id2>, <id3>]   // ordered chain; max length 4 (parent + up to 3 follow-ups)
```

On each **follow-up** question JSON:
```json
"mock_only": true,
"parent_id": <parent_id>,             // back-ref, validated at catalog load
"follow_up_dimension": "scale_pivot"  // one of the 7 universal dimensions below
```

### Selection rules

1. **Within a session:** if the selector picks parent P, it reserves N+1 contiguous adjacent slots (P + N follow-ups). If insufficient slots remain in the session blueprint, P is skipped — chains are never split.
2. **Across sessions:** once P's chain is selected for any session, the entire chain is marked consumed for that user and never reappears in any future mock session (benchmark, drill, focus, Loop — all of them).
3. **Children are never directly selectable.** They enter sessions only via their parent. Orphan selection is forbidden by the validator.
4. **Consumption trigger:** chain is marked consumed at **session start** (`POST /api/mock/start`), not at finish. Otherwise users could re-roll by abandoning.
5. **Reclaim window:** within 2 minutes of session start, `DELETE /api/mock/<id>` reclaims the chain (returns it to the user's pool). After 2 min, consumption is final regardless of whether the user submitted anything.
6. **Pool exhaustion:** when no fresh chains/questions remain for a user × track × difficulty, mock returns 409 with `pool_exhausted: true` and copy nudging the user to switch tracks, try practice paths, or wait for new content. **No soft fallback** — we do not silently re-show consumed chains. Re-showing dilutes the readiness signal.

### Why session-start, not finish-of-first-question?

Considered alternatives:
- Consume at `POST /start` (chosen) — simple, prevents peek-and-bail abuse, 2-min reclaim is the safety valve
- Consume at first submission — allows users to read all questions and never submit, infinite re-rolls
- Consume at finish — same abuse vector

The 2-min reclaim is the right balance: long enough for "I clicked the wrong track" recovery, short enough that "let me peek at the chain and bail" is not viable.

### The 7 universal follow-up dimensions

Every follow-up escalates exactly one dimension. The full taxonomy lives in `docs/concept-taxonomy.md`; summarised here:

| Dimension | What it tests | Cross-track example |
|---|---|---|
| `scale_pivot` | How does this change at 10× / 100× / petabyte scale? | SQL: "now the orders table has 10B rows"; PySpark: "shuffle strategy must change"; DE: "small-file problem emerges" |
| `business_rule_pivot` | What changes when the business definition shifts? | SQL: "exclude refunded orders"; Stats: "now the metric definition changes"; ML: "label definition shifts" |
| `data_quality_pivot` | How does the answer adapt to dirty data? | SQL: "duplicates in this table"; PySpark: "late-arriving events"; DE: "schema drift upstream" |
| `edge_case_pivot` | What about empty windows, ties, missing days? | SQL: "what if a user has zero orders"; Stats: "small-sample inference"; ML: "rare class" |
| `performance_pivot` | How would you reduce cost/latency? | SQL: "reduce repeated scans"; PySpark: "minimise shuffle"; DE: "cost optimisation" |
| `ambiguity_pivot` | The business question is unclear — what would you ask? | Cross-track: "what counts as 'active'?"; Exp: "is this even testable?" |
| `stakeholder_pivot` | A stakeholder wants a different answer — how do you respond? | "Exec wants weekly not monthly"; "PM wants a simpler explanation"; "Finance wants attribution" |

### Authoring rules for chains (enforced by `validate_content.py`)

- Chain length: 2 (parent + 1) minimum for Interview Loop eligibility, 4 maximum (parent + 3 follow-ups).
- **Each follow-up in a chain must use a different `follow_up_dimension` than the previous follow-up.** No two consecutive scale pivots, etc. — variety is the point.
- A child cannot have its own `follow_ups[]` (no nested chains).
- A child can only appear in one parent's `follow_ups[]` (no shared children).
- All chain questions must share the same `track` and same or escalating `difficulty`.

### Persistence model (Phase 3 implementation)

New table `mock_chain_consumption`:
```
user_id          UUID
parent_id        INT
consumed_at      TIMESTAMP
session_id       INT  (nullable — reclaim sets this null)
reclaimed        BOOL DEFAULT FALSE
```

Selection algorithm extension: filter pool to exclude every question that is (a) a parent in a consumed-not-reclaimed row OR (b) a `parent_id` value referenced by such a row (children of consumed parents).

---

## Interview Loop Mode (Elite only)

Interview Loop is the chain-driven mode — the iterative interviewer-pivot dialogue that turns mock sessions into a simulated real interview rather than a question-answer round.

**Status: spec only as of 2026-05-21. Backend + UI ship in Phase 3 of the authoring refactor.**

### What it is

The user picks a track and a focus area (or "any"), and the system composes a session of **1–3 chains** — each chain a parent question plus its follow-ups. Within a chain, the user experiences:
1. The parent question (normal mock UX)
2. After submit, an interviewer-style pivot card: *"Good. Now…"* followed by the follow-up framing
3. The follow-up question, building on the same dataset / problem / context
4. Repeat for chain length

This mode simulates the real interview shape — interviewers don't ask 5 unrelated questions; they ask one question and iterate on it. Loop trains adaptability, not memorisation.

### Eligibility

- **Plan:** Elite only.
- **Content:** Only parents with `follow_ups[]` of length ≥2 are eligible. (Loop is chain-only; single-question parents belong to benchmark/drill modes.)
- **Atomicity:** all chain atomicity rules apply. Each Loop session consumes 1–3 full chains; once consumed, they're gone from that user's pool.

### Session shape

| Parameter | Default | Range |
|---|---|---|
| Number of chains | 2 | 1–3 |
| Total questions | sum of chain lengths (typically 4–9) | bounded by chain availability |
| Time limit | 15 min × chain count | proportional |
| Mid-session reveal | none (benchmark invariants apply) | — |

### Mode interaction with focus

If user enables `focus_concepts` together with Loop, the focus filter applies to the **parent's** concepts only. The full chain travels regardless of whether follow-ups carry the focus concept — that's the iterative-pivot point.

### Analytics

After completion, Loop sessions feed a new analytics dimension: **performance by follow-up dimension**. This answers "which kinds of interviewer pivot break this user?" — e.g., "Strong on scale pivots, weak on ambiguity pivots." Surfaced in the Elite dashboard alongside concept-family weak-spots.

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
- **Submit per question** — each question allows exactly one real submission. **No feedback is shown on submit** — the submit button locks (label changes to `✗ Submitted` on a wrong answer; `✓ Solved` on a correct one) and that is the only mid-session signal. Solutions are withheld until the session ends. A second `/submit` for the same question returns 409. Blank code or a missing MCQ selection returns 422 and does not consume the slot, so users can run and iterate freely before committing their final answer. After any submit (correct or wrong) a **"Next question →"** button appears on non-last questions; on the last question a nudge paragraph appears instead — "All questions answered — end your session when ready." if every question has been submitted, or "End your session when ready, or go back to answer remaining questions." if some are still unanswered.
- **Exit confirmation** — clicking Exit or End Session shows a confirm dialog.
- **Discard window (2 minutes)** — within 120 seconds of session start, the user can discard the session (`DELETE /api/mock/:id` returns 204; session removed from history; chains, if any, reclaimed to the user's pool). After 120 seconds the request returns 403 and the session is locked in regardless of submission state. Two minutes is the correct ballpark: short enough to prevent peek-and-bail abuse of chains, long enough for "I clicked the wrong track" recovery. UX must make this prominent — not buried behind Exit:
  - **Visible countdown chip** in the topbar during the first 120 s: "Discard within 1:34 — no penalty"
  - **"Discard & re-roll" button** next to "End session" while the window is open; vanishes silently after 2 min
  - **Chain reclaim copy** when a chain is involved: "This chain will return to your pool — you'll see it again next time."
  - **Benchmark friction** — confirm modal on discard, since benchmark scores feed analytics. Friction, not blocking.
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
- **(Pro+) "Drill weak concepts →"** — drill summaries link to `/practice/:track?concepts=...` pre-filtered to the worst 2 concepts from the session, and benchmark summaries can still surface the same concept-focused follow-up inside the concept block.
- **(Elite) Session debrief** — a coaching narrative panel shown above the per-question list. Generated server-side (template-based, no external AI) from session data and submission history. Contains:
  - **Headline** — one-sentence overall verdict with score and time context.
  - **Patterns** — up to 3 observations: which concepts were strong/weak, follow-up question performance, and whether a single question dominated session time.
  - **Priority action** — the single most important next step, with a direct link to the recommended learning path when one exists.
  - Historical context: if a session concept matches a known weak area in the user's submission history (≥3 past attempts, <60% accuracy), the pattern observation uses stronger "known weakness" language.
  - Returned as `debrief` in the `POST /api/mock/:id/finish` response. `null` for non-Elite plans.
- **(Elite) "Known weakness" badge** — when a session concept matches one of the user's cross-session `weakest_concepts` from the dashboard insights, the concept row is highlighted in amber and tagged "known weakness". Elite users also see a path recommendation link ("Study in {title} →") when `recommended_path_slug` is present; Pro users see a generic drill link.
- **Share result** — uses `navigator.share({ text })` when available (mobile OS share sheet) with clipboard fallback. Share text includes: `{Track} {benchmark/drill} · {Difficulty} · {N}/{total} ({pct}%)`, a baseline delta line for Pro/Elite (`X% above/below my avg accuracy`), the top 2 weak concept gaps from the session (all tiers), and `datathink.co`.
- **Mode-aware footer actions** — benchmark summaries show `Share result` + `Back to Mock` + `Plan follow-up drill` (primary); drill summaries show `Drill weak concepts →` (Pro/Elite when weak concepts exist) or `Continue targeted drill` (prefilled short-drill preset), plus `Back to drill lobby`.
- **Summary-to-hub handoff** — clicking the follow-up drill action sends `location.state.mockPreset` into MockHub, which displays a `Recommended next step` banner and pre-fills the drill planner with track, difficulty, and short-session defaults.

---

## History (`/mock` page)

- Shows the last 20 sessions split into benchmark and drill sections so fixed-shape benchmarks are not visually blended with flexible drills.
- Mode labels are normalized in the UI so users see `Benchmark`, `Sprint drill`, `Custom drill`, or `Full (legacy)` instead of raw stored mode keys.
- First-run users now see explicit benchmark-versus-drill framing instead of a single generic empty state, so the lobby teaches when to benchmark and when to drill before any history exists.
- Partial-history states are also explicit: benchmark-only users see `No drill sessions yet` guidance, while drill-only users see `No benchmark sessions yet` guidance.
- **Review →** for completed sessions, **Resume →** for in-progress ones.
- Empty state links to practice tracks and the dashboard.

---

## How to Use (the `?` button on /mock)

1. **Choose session type** — Benchmark for the fixed-shape track benchmark, Sprint drill for a short calibration round, or Custom drill for targeted follow-up practice.
2. **Pick track and difficulty** — Difficulty buttons show live access state (remaining daily sessions or upgrade CTAs). Drill modes also show a dedicated planner card with the session shape before you start.
3. **Track benchmark availability** — Mixed stays drill-only; single-track sessions can use Benchmark.
4. **(Elite, SQL track)** Optionally select a **Company** filter.
5. **Start** — the timer starts immediately.
6. **During the session** — write your answer and run it as many times as you like to test. When ready, submit — **each question is one shot**. Blank code or an unselected MCQ option is rejected before it counts. After submitting you can keep editing, but your score for that question is locked.
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

Frontend e2e also covers repeatable mock plan-tier flows in `frontend/e2e/mock-plan-flows.spec.js`, including free/pro/elite setup surfaces, right/wrong PySpark submissions, drill summary actions, elite benchmark debrief visibility, and the `Plan follow-up drill` handoff back into MockHub.
