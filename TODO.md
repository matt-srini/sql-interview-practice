# Platform Upgrade TODO

Phased roadmap to evolve datanest into a top-tier data interview practice platform. Remove items as they are shipped. Update `docs/` and `CLAUDE.md` when each phase lands.

**Research basis:** Competitor analysis (DataLemur, StrataScratch, Interview Query, HackerRank, LeetCode) + user pain point research. Full strategic context in the Claude memory/plan file.

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
