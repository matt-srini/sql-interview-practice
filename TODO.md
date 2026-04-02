# Platform Upgrade TODO

Phased roadmap to evolve datanest into a top-tier data interview practice platform. Remove items as they are shipped. Update `docs/` and `CLAUDE.md` when each phase lands.

**Research basis:** Competitor analysis (DataLemur, StrataScratch, Interview Query, HackerRank, LeetCode) + user pain point research. Full strategic context in the Claude memory/plan file.

---

## UI Architecture & Layout Plan

This section defines the full frontend blueprint across all phases — route tree, navigation evolution, new page layouts, and how existing pages change. Implement phases in order; each phase builds on the last.

---

### Full route tree (current + all phases)

```
/                              → LandingPage
/auth                          → AuthPage
/dashboard                     → ProgressDashboard          [Phase 1A evolved]
/practice/:topic               → TopicShell → TrackHubPage  [Phase 1C, 4 evolved]
/practice/:topic/questions/:id → QuestionPage               [Phase 1A, 3 evolved]
/sample/:topic/:difficulty     → SampleQuestionPage
/mock                          → MockHub                    [Phase 2 — new]
/mock/:id                      → MockSession / MockSummary  [Phase 2 — new]
/learn/:path-slug              → LearningPath               [Phase 4 — new]
/profile                       → ProfilePage                [Phase 6 — new]
/leaderboard                   → Leaderboard                [Phase 6 — new]
```

Legacy redirects remain unchanged: `/practice`, `/practice/questions/:id`, `/questions/:id`, `/sample/:difficulty`.

`App.js` additions per phase:
- Phase 2: add `/mock` and `/mock/:id` routes (wrap in `AuthRequired`)
- Phase 4: add `/learn/:path-slug`
- Phase 6: add `/profile`, `/leaderboard`

---

### Global navigation (topbar) evolution

The topbar is the primary wayfinding element. It changes in two ways: link set grows with phases, and it enters a special focused state during a mock session.

**Phase 1 topbar (Practice workspace — `AppShell.js`):**
```
datanest  [SQL] [Python] [Pandas] [PySpark]  ···  [☀/☾]  [Dashboard]  [name · Sign out]
                                                   ↑ Phase 1B: theme toggle
```

**Phase 2+ topbar (global — all non-mock pages):**
```
datanest  [Practice ▾]  [Mock]  [Dashboard]  ···  [☀/☾]  [name · Sign out]
                ↓ dropdown
           SQL · Python · Pandas · PySpark
```
- "Practice" becomes a dropdown when the nav grows; direct track links move inside it
- "Mock" is a top-level link (high-visibility, this is a key feature)
- Dashboard stays visible

**Mock session topbar (special focused state — `MockSession.js`):**
```
[◀ Exit]   Q1 ●  Q2 ○  Q3 ○   [  12:34  ]   [End session]
             question dots         timer
```
- No brand link, no nav — user should stay focused
- Timer centred and always visible
- Timer background: neutral → yellow (<10 min) → red pulsing (<3 min)
- "Exit" returns to `/mock` with a confirmation modal ("Your progress will be lost")
- On completion: topbar stays but timer shows "Done" and "End session" becomes "View results"

**LandingPage topbar (unchanged from current):**
```
datanest                                       [Dashboard]  [name · Sign out]  or  [Sign in]
```

---

### New pages — layout blueprints

#### MockHub (`/mock`)

```
TOPBAR  (global nav)

HERO ROW
  "Mock Interview"  h1
  "Simulate real interview conditions with a countdown timer." p

MODE SELECTOR  (3 cards in a row, card selected = accent border)
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │  Quick          │  │  Full           │  │  Custom         │
  │  30 min         │  │  60 min         │  │  __ min         │
  │  2 questions    │  │  3 questions    │  │  1–5 questions  │
  └─────────────────┘  └─────────────────┘  └─────────────────┘

CONFIGURATION ROW  (shown below mode selector)
  Track:       [SQL ●]  [Python]  [Pandas]  [PySpark]  [Mixed]
  Difficulty:  [Easy]  [Medium ●]  [Hard]  [Mixed]

[Start Mock Interview]  btn-primary, full-width on mobile

RECENT SESSIONS  (shown only if user has past sessions)
  h2: "Recent sessions"
  Table/list: date · track · difficulty · score (2/3) · time used · [Review →]
  "View all" link → /mock/history  (future; for now show last 5 inline)
```

Responsive: mode cards wrap to single column on mobile (<600px). Configuration pills scroll horizontally if needed.

---

#### MockSession (`/mock/:id`)

Two states: **Active** (timer running) and **Summary** (after finish).

**Active state layout:**

```
MOCK TOPBAR  (special focused state — see nav section above)

CONTENT AREA  (full height below topbar, CSS Grid: sidebar | editor)

LEFT: Question tabs + info  (240px, fixed)
  ┌──────────────────────────┐
  │ [Q1]  [Q2]  [Q3]         │  tab strip (dots = solved/unsolved)
  ├──────────────────────────┤
  │ Q1 · Medium              │
  │ "Top Products by Revenue"│  question title
  │                          │
  │ [Description]  [Schema]  │  toggle tabs
  │                          │
  │ Question text here...    │
  │                          │
  │ Concepts: [RANKING] [...]│
  └──────────────────────────┘

RIGHT: Editor + results  (flex-grow 1)
  Same Monaco editor + Run/Submit layout as QuestionPage
  On submit: verdict shows inline (no full page reload)
  Correct: question tab dot turns green; "Next question →" shown
```

Mobile (<900px): tabs collapse to a top strip; left panel becomes a slide-up drawer triggered by "Question" button in action dock.

**Summary state layout** (replaces content area after timer ends or user clicks "End session"):

```
TOPBAR  (simplified — no timer, "Back to Mock" link on left)

SUMMARY CARD  (centered, max-width 640px)
  Score: "2 / 3 questions solved"  (large, success color if >50%, danger if 0)
  Time:  "Used 27:43 of 30:00"
  ──────────────────────────────
  Per-question breakdown (3 rows):
    Q1  Top Products    ✓ solved   4:12   [See solution ▾]
    Q2  Cohort Retention ✗ unsolved  —    [See solution ▾]
    Q3  Running Total   ✓ solved  11:30   [See solution ▾]
  ──────────────────────────────
  [Practice weaknesses →]   btn-secondary  (links to concept-filtered question list)
  [Share result]            btn-secondary  (copy "2/3 Medium SQL in 27m")
  [New mock interview]      btn-primary

TIPS STRIP  (below card, only if score < 100%)
  Concept tags from unsolved questions + link to each concept in the sidebar
```

---

#### LearningPath (`/learn/:path-slug`) — Phase 4

```
TOPBAR  (global nav)

PATH HEADER  (full-width, light surface)
  Breadcrumb: Practice › Learning Paths › Window Functions Mastery
  h1: "Window Functions Mastery"
  p:  "8 questions building from basics to advanced ranking."
  Progress bar: 3 / 8 completed

QUESTION SEQUENCE  (centered, max-width 720px)
  ┌─────────────────────────────────────────────────────┐
  │ 1 ✓  Running Totals           Easy    [Review →]   │
  │ 2 ✓  Rank by Revenue          Easy    [Review →]   │
  │ 3 ✓  Dense Rank Gaps          Medium  [Review →]   │
  │ 4 →  Top-N per Category       Medium  [Start →]    │  ← next
  │ 5 🔒  Event Sequence Filter    Medium  (locked)     │
  │ 6 🔒  Retention by Cohort      Hard    (locked)     │
  └─────────────────────────────────────────────────────┘

  Each row: number · solved/locked state · title · difficulty badge · action
  Clicking a solved row → /practice/:topic/questions/:id (preserves path context)
  Clicking current → same, marks path progress
```

---

#### ProfilePage (`/profile`) — Phase 6

```
TOPBAR  (global nav)

PROFILE HEADER
  Avatar (initials only, no image upload needed) · name/email · plan badge
  Member since · total questions solved · streak

BADGES ROW  (horizontal scroll on mobile)
  Each badge: icon · name · unlock date
  Locked badges shown greyed-out with unlock criteria tooltip

STATS GRID  (2×2 on desktop, 1-column on mobile)
  ┌─────────────────┐  ┌─────────────────┐
  │ SQL             │  │ Python          │
  │ 42/86 solved    │  │ 18/75 solved    │
  │ progress bar    │  │ progress bar    │
  └─────────────────┘  └─────────────────┘
  (Pandas, PySpark same pattern)

MOCK HISTORY  (table)
  Date · Mode · Track · Score · Time · [Review]

SUBMISSION ACTIVITY  (heatmap — Phase 6)
  GitHub-style contribution grid showing solve activity by day
  (simple implementation: query submissions table, render CSS grid)
```

---

#### Leaderboard (`/leaderboard`) — Phase 6

```
TOPBAR  (global nav)

TABS  [Weekly ●]  [All-time]  [By track ▾]

TABLE
  Rank · User (anonymised unless opt-in) · Track · Questions solved · Avg time
  Current user highlighted if on the list

OPT-IN BANNER  (shown if user is not opted in)
  "You're not on the leaderboard. Make your stats public?"  [Opt in]
```

---

### Existing pages — evolution by phase

#### LandingPage (`/`)

**Phase 1B:** Add theme toggle button to topbar (sun/moon icon, right of Dashboard link).

**Phase 1D:** Replace horizontal scroll sample tiles with vertical card stack on mobile (<600px). Schema viewer becomes bottom-sheet drawer on mobile.

**Phase 4:** Insert "Top company questions" strip between Showcase and Track Selection:
```
COMPANY STRIP  (light, between showcase and track section)
  "Practice questions from:"
  Logo row: [Meta] [Stripe] [Airbnb] [Uber] [Netflix] ...  (greyscale, opacity 0.6)
  These are filter links — clicking "Meta" opens Track Selection filtered to Meta questions
```

**Phase 4:** Insert "Learning paths" section after Track Selection:
```
LEARNING PATHS  (below track selection, light surface)
  h2: "Structured learning paths"
  3–4 path cards in a row:
  ┌─────────────────────┐
  │ Window Functions    │
  │ Mastery             │
  │ 8 questions · SQL   │
  │ ████░░░░ 3/8        │  (progress if logged in)
  │ [Start path →]      │
  └─────────────────────┘
```

---

#### ProgressDashboard (`/dashboard`)

**Current:** 4-track progress cards, concept tags, recent activity list.

**Phase 1A:** Add "Recent submissions" feed below the 4-track grid:
```
RECENT SUBMISSIONS  (table, last 10 across all tracks)
  Time · Track · Question title · ✓/✗ · [Go to question →]
```

**Phase 2:** Add "Mock sessions" summary card alongside the 4-track grid:
```
MOCK SESSIONS CARD
  Sessions completed: 12
  Best score: 3/3 (Full · SQL · Hard)
  Recent: [date · 2/3 · 28m] [date · 1/2 · 15m]  [View all →]
```

**Phase 6:** Add badges row at the top of the dashboard:
```
BADGES ROW  (horizontal strip, compact)
  5 most recent badges shown; [See all →] links to /profile
```

---

#### QuestionPage (`/practice/:topic/questions/:id`)

**Phase 1A:** Add "Past attempts" panel below the verdict card:
```
PAST ATTEMPTS  (collapsible, shown after first submission)
  ▾ Past attempts (3)
  ──────────────────────────────────────────
  2 hours ago   ✗  [Show code ▾]
  Yesterday     ✓  [Show code ▾]
  3 days ago    ✗  [Show code ▾]
```

**Phase 3:** Add "Solution analysis" section after a correct verdict:
```
SOLUTION ANALYSIS  (expandable, shown only on correct submit)
  ▾ Solution analysis
  Efficiency:  Your query scans ~4,200 rows. Optimal: ~260 rows.
               [Suggestion: filter on orders before joining products]
  Style:       ✓ Uses CTEs clearly  ✗ Inconsistent aliasing
  Complexity:  O(n log n) — expected for this pattern

  [See alternative approach ▾]
    (second solution from question JSON, if available)
```

---

#### SidebarNav (`/practice/:topic`)

**Phase 1C:** Add concept filter chips above difficulty groups:
```
CONCEPT FILTER  (collapsible, above difficulty groups)
  Filter by concept:
  [COHORT ANALYSIS ×] [RUNNING TOTAL] [RANKING] [FUNNEL] [+12 more ▾]
  Active filter chip shown with accent fill + ×; inactive = outlined
  "Clear filters" link when any active
```

**Phase 4:** Add company filter alongside concept filter:
```
FILTERS  (collapsible section)
  Concepts:  [RANKING ×]  [FUNNEL]  ...
  Companies: [Meta ×]  [Stripe]  [Airbnb]  ...
```

---

#### TrackHubPage (`/practice/:topic`)

**Phase 4:** Add learning paths entry point below the existing "What you'll practice" card:
```
LEARNING PATHS FOR THIS TRACK
  ┌──────────────────────┐  ┌──────────────────────┐
  │ Window Functions     │  │ Aggregation Deep Dive │
  │ 8 questions          │  │ 6 questions           │
  │ ████░░ 3/8           │  │ Not started           │
  │ [Continue →]         │  │ [Start →]             │
  └──────────────────────┘  └──────────────────────┘
```

---

### New components needed

| Component | Phase | Purpose |
|---|---|---|
| `MockTimerBanner.js` | 2 | Full-width timer bar for MockSession topbar |
| `MockSummaryCard.js` | 2 | Score + per-question breakdown after session |
| `QuestionTabStrip.js` | 2 | Q1/Q2/Q3 tab navigation in MockSession sidebar |
| `SolutionAnalysis.js` | 3 | Efficiency + style scorecard in QuestionPage |
| `PathProgressCard.js` | 4 | Learning path card with progress bar |
| `ConceptFilter.js` | 1C | Filter chip set for sidebar (reused in Phase 4 with company filter) |
| `BadgeCard.js` | 6 | Achievement badge display (ProfilePage + Dashboard) |
| `ActivityHeatmap.js` | 6 | GitHub-style contribution grid |
| `LeaderboardTable.js` | 6 | Ranked table with current-user highlight |

---

### Responsive strategy

| Breakpoint | Behaviour |
|---|---|
| `< 600px` | Single column everywhere. Sample tiles stack vertically. MockSession: left panel is a slide-up drawer. Mode cards stack. Profile stats stack. |
| `600–900px` | Two columns for grids where sensible. Sidebar still overlay. MockSession tabs condense. |
| `> 900px` | Full desktop layout. Sidebar pinned. MockSession two-column. Dashboard 2×2 grid. |

All new pages must be tested at 375px (iPhone SE) and 768px (iPad) in addition to desktop.

---

### Design token additions

No new tokens needed for Phase 1–3 — use existing palette. Phase 2 mock timer requires two states that can use existing tokens:

```css
/* Mock timer states — add to App.css in Phase 2 */
.mock-timer--warning  { background: var(--warning-soft); color: var(--warning); }
.mock-timer--danger   { background: var(--danger-soft);  color: var(--danger);  animation: pulse 1s infinite; }
```

Phase 6 activity heatmap uses a 5-level intensity scale built from `--success` with opacity steps — no new color tokens.

---

## Phase 1 — Quick wins (core experience) ✦ high impact, low effort

### 1A · Submission history

**Problem:** Users can't track improvement or revisit past attempts — the #1 retention signal missing.

**Backend:**
- New `submissions` table in PostgreSQL:
  ```sql
  CREATE TABLE submissions (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(id),
    track        TEXT NOT NULL,
    question_id  INTEGER NOT NULL,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    is_correct   BOOLEAN NOT NULL,
    code         TEXT,
    duration_ms  INTEGER
  );
  ```
- `GET /api/submissions?track=sql&question_id=42&limit=10`
- Call `record_submission()` inside every submit handler

**Frontend:**
- Collapsible "Past attempts" panel below verdict card in `QuestionPage.js`
- Show last 5 attempts: timestamp · pass/fail · code toggle

**Files:** `backend/db.py`, `backend/routers/questions.py` (+ python/pyspark variants), `backend/alembic/`, `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### 1B · Dark mode persistence

**Problem:** `prefers-color-scheme` resets on every visit; users who prefer dark mode get inconsistent experience.

- Store `theme` preference in `localStorage` (`light` / `dark` / `system`)
- Add theme toggle button (sun/moon icon) in the topbar
- Apply `data-theme` attribute on `<html>` that overrides the media query

**Files:** `frontend/src/App.js`, `frontend/src/App.css`, `frontend/src/components/AppShell.js`

---

### 1C · Concept filter in sidebar

**Problem:** No way to find "all window function questions" or practice a specific concept cluster.

- Concept filter chips above the question list in `SidebarNav.js`
- Clicking a chip filters the visible question list (client-side, no API change needed)
- All question metadata already has `concepts` arrays

**Files:** `frontend/src/components/SidebarNav.js`, `frontend/src/App.css`

---

### 1D · Mobile UX improvements

**Problem:** Horizontal scroll sample tiles are a workaround; schema viewer is awkward on mobile.

- Replace horizontal scroll tiles with vertical card stack on mobile (<600px)
- Schema viewer: bottom-sheet drawer on mobile (tap "Schema" → slide up)
- Ensure sticky action dock doesn't overlap results

**Files:** `frontend/src/App.css`, `frontend/src/pages/LandingPage.js`, `frontend/src/pages/QuestionPage.js`

---

## Phase 2 — Mock interview mode ✦ highest competitive impact

**Rationale:** The #1 missing feature vs every competitor. Users consistently cite timed mock practice as what they want but can't find.

### Data model

New PostgreSQL tables:
```sql
CREATE TABLE mock_sessions (
  id           SERIAL PRIMARY KEY,
  user_id      INTEGER REFERENCES users(id),
  mode         TEXT NOT NULL,      -- '30min' | '60min' | 'custom'
  track        TEXT NOT NULL,
  difficulty   TEXT,               -- 'easy' | 'medium' | 'hard' | 'mixed'
  started_at   TIMESTAMPTZ DEFAULT NOW(),
  ended_at     TIMESTAMPTZ,
  time_limit_s INTEGER NOT NULL,
  status       TEXT DEFAULT 'active'  -- 'active' | 'completed' | 'abandoned'
);

CREATE TABLE mock_session_questions (
  id           SERIAL PRIMARY KEY,
  session_id   INTEGER REFERENCES mock_sessions(id),
  question_id  INTEGER NOT NULL,
  track        TEXT NOT NULL,
  position     INTEGER NOT NULL,
  is_solved    BOOLEAN DEFAULT FALSE,
  submitted_at TIMESTAMPTZ,
  final_code   TEXT,
  time_spent_s INTEGER
);
```

### New API endpoints

```
POST /api/mock/start       { mode, track, difficulty } → { session_id, questions[], time_limit_s }
POST /api/mock/:id/submit  { question_id, code }       → { correct, feedback }
POST /api/mock/:id/finish  →                             { summary }
GET  /api/mock/:id         → session state (for reload recovery)
GET  /api/mock/history     → past sessions list
```

Question selection: 2 questions for 30-min, 3 for 60-min. Randomized from unlocked questions within difficulty tier.

### Frontend

**New routes:** `/mock` (hub), `/mock/:id` (active session)

**MockHub (`/mock`):**
- 3 mode cards: Quick (30 min · 2 questions) · Full (60 min · 3 questions) · Custom
- Track filter: SQL / Python / Mixed
- Difficulty: Easy / Medium / Hard / Mixed
- Recent sessions (last 5 with score + date)

**MockSession (`/mock/:id`):**
- Top banner: countdown `MM:SS` · question dots (Q1 · Q2 · Q3) · "End" button
- Yellow background when <10 min; red + pulse when <3 min
- Tab list on left; full Monaco editor + run/submit on right
- Timer hits zero → auto-submits current state → transitions to summary
- Reload recovery: `GET /api/mock/:id` → compute `started_at + time_limit_s - now()`
- Browser tab title: `"12:34 — Mock Interview | datanest"`

**MockSummary (inline after completion):**
- Score card: X/Y solved · time used
- Per-question: title · solved/unsolved · time spent · final code toggle
- "Practice weaknesses" CTA → concept-filtered question list
- "Share result" → copy text ("2/3 SQL questions in 28 min")

**Files to create:** `frontend/src/pages/MockHub.js`, `frontend/src/pages/MockSession.js`, `backend/routers/mock.py`

**Files to change:** `frontend/src/App.js`, `backend/db.py`, `backend/alembic/`, `frontend/src/App.css`

---

## Phase 3 — AI-enhanced feedback ✦ strong differentiation

**Problem:** Pass/fail verdict tells users *what* happened, not *why* their solution is good or bad.

### Solution quality scorecard

After correct submission, show a 3-axis scorecard:
1. **Correctness** ✓ (already exists)
2. **Efficiency** — run `EXPLAIN` on user query and expected query in DuckDB; compare estimated row scans
3. **Style** — CTE vs subquery choice, aliasing, readability heuristic

**Backend:**
- Add `explain_query()` utility to `evaluator.py` using DuckDB `EXPLAIN`
- Return `{ quality: { efficiency_note, style_notes[] } }` alongside correct verdicts
- Add `complexity_hint` field to question JSON (e.g., `"O(n log n) with sort"`)

**Frontend:**
- Expandable "Solution analysis" section below verdict card
- Show EXPLAIN comparison + style notes + complexity hint

**Alternative approaches:**
- Questions can carry multiple `solutions` in JSON
- "See another approach" toggle reveals second solution + explanation
- No AI inference — curated content, added over time

**Files:** `backend/evaluator.py`, `backend/routers/questions.py`, `backend/content/questions/*.json` (add fields), `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

## Phase 4 — Content & discovery ✦ retention and depth

### Company tags on questions

- Add `"companies": ["Meta", "Stripe", "Airbnb"]` to question JSON
- Filter chips in sidebar: "Show Meta questions" (builds on Phase 1C concept filter)
- Landing page: "Practice questions from top companies" section
- No backend schema changes — metadata on question JSON only

### Learning paths

- Curated question sequences building toward a skill (e.g., "Window Functions Mastery" → 8 questions easy to hard)
- Stored as JSON configs in `backend/content/paths/`
- New route: `/learn/:path-slug` → guided sequential experience
- Progress tracked per path (separate from free-form challenge progress)

### New question types (longer term, new evaluator logic required)

- **Query debugging** — given a broken query, fix it
- **Schema design** — given a business description, design tables

---

## Phase 5 — Scalability architecture ✦ required before viral growth

See `docs/architecture.md` — Scalability section for full technical detail.

### DuckDB connection pool

Replace single shared cursor with a `DuckDBPool` of pre-loaded connections (8 by default, configurable via `DUCKDB_POOL_SIZE`). Each connection is a full DuckDB in-memory instance with all tables loaded.

**File:** `backend/database.py`

### Python sandbox worker pool

Replace per-request subprocess spawn with `multiprocessing.Pool` of pre-forked workers. Eliminates cold-start latency (~50–100ms saved per request).

**File:** `backend/python_evaluator.py`

### CDN for static assets

Build frontend to `dist/` with hashed filenames → serve from Cloudflare/CloudFront with long `Cache-Control` TTL. FastAPI only handles `/api/*` and `index.html` fallback.

**File:** `Dockerfile`, `railway.json`, static asset caching config

### Horizontal API scaling

FastAPI is already stateless. Requires `REDIS_URL` to be set (already required in prod) for shared rate limiting. Deploy multiple containers behind Railway's load balancer.

### PostgreSQL connection pool tuning

- Increase `asyncpg` pool size (10 → 50)
- Add PgBouncer connection pooler for 1,000+ concurrent connections
- Add read replica for dashboard/catalog reads

---

## Phase 6 — Community features ✦ low priority, high complexity

> Add only after Phase 1–3 are complete and the core experience is solid.

### Leaderboards (opt-in)

- Weekly: most questions solved this week, per track
- All-time: total solved, mock interview scores
- Privacy: opt-in only (default anonymous)
- Implementation: query `submissions` + `mock_sessions` tables — no new infrastructure

### Achievement badges

Awarded automatically from existing `submissions` data:
- "SQL Starter" — first SQL question solved
- "Speed Demon" — hard question solved in <5 min
- "7-Day Streak" — solved at least 1 question/day for 7 days
- "Mock Pro" — completed 5 mock sessions
- Computed at read time (no separate badge table needed initially)

### Solution discussion

- Per-question comment threads
- New `discussion_posts` table
- Requires account, rate-limited, moderated
- Simple flat threads (no voting) to start

---

## Completed

*(Move items here when shipped, with the commit SHA)*
