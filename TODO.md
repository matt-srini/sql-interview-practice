# Platform Upgrade TODO

Phased roadmap to evolve datathink into a top-tier data interview practice platform. Remove items as they are shipped. Update `docs/` and `CLAUDE.md` when each phase lands.

**Research basis:** Competitor analysis (DataLemur, StrataScratch, Interview Query, HackerRank, LeetCode) + user pain point research. Full strategic context in the Claude memory/plan file.

---

## Production readiness checklist

### Admin account + reserved emails (pre-launch)

- **Reserved email blocking** is already live in `auth.py` — no action needed, applies to prod automatically.
- **Admin seed script** (`backend/scripts/seed_admin.py`) must be run once against the Railway Postgres DB before launch:
  ```bash
  DATABASE_URL="<railway-postgres-url>" \
  ADMIN_EMAIL=<your-real-email> \
  ADMIN_PASSWORD=<strong-password> \
    .venv/bin/python backend/scripts/seed_admin.py
  ```
  Options for running against Railway: `railway run python backend/scripts/seed_admin.py` (with env vars set in Railway dashboard), or exec into the running container via `railway shell`.
- Use a real email address you own for the prod admin account (not `admin@internal.test`).
- The script is idempotent — safe to re-run if credentials need rotating.

---

## UI Architecture & Layout Plan

This section defines the full frontend blueprint across all phases — route tree, navigation evolution, new page layouts, and how existing pages change. Implement phases in order; each phase builds on the last.

---

### Full route tree

```
/                              → LandingPage
/auth                          → AuthPage
/dashboard                     → ProgressDashboard
/practice/:topic               → TopicShell → TrackHubPage
/practice/:topic/questions/:id → QuestionPage
/sample/:topic/:difficulty     → SampleQuestionPage
/mock                          → MockHub
/mock/:id                      → MockSession / MockSummary
/learn/:path-slug              → LearningPath
/profile                       → ProfilePage                [Phase 6 — new]
/leaderboard                   → Leaderboard                [Phase 6 — new]
```

Legacy redirects remain unchanged: `/practice`, `/practice/questions/:id`, `/questions/:id`, `/sample/:difficulty`.

`App.js` additions still needed:
- Phase 6: add `/profile`, `/leaderboard`

---

### Global navigation (topbar) — current state

All topbar variants are shipped. No changes needed until Phase 6 adds `/profile` and `/leaderboard` links.

---

### New pages — layout blueprints

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

#### ProgressDashboard (`/dashboard`)

**Phase 6:** Add badges row at the top of the dashboard:
```
BADGES ROW  (horizontal strip, compact)
  5 most recent badges shown; [See all →] links to /profile
```

---

### New components needed (Phase 6)

| Component | Purpose |
|---|---|
| `BadgeCard.js` | Achievement badge display (ProfilePage + Dashboard) |
| `ActivityHeatmap.js` | GitHub-style contribution grid |
| `LeaderboardTable.js` | Ranked table with current-user highlight |

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

Phase 6 activity heatmap uses a 5-level intensity scale built from `--success` with opacity steps — no new color tokens needed.

---

---

## UX Polish & Learning Experience

This section covers what separates a *functional* product from a *top-notch* one. These are the details that make users stay longer, return daily, and recommend the platform. Many are small individually; together they define the feel of the product.

---

### Auto-save code drafts ✦ must-have

**Problem:** Navigating away from a question — accidentally clicking a link, hitting back, or closing the tab — loses all unsaved code. This is a trust-destroying experience.

**What to build:**
- On every editor change, debounce-save to `localStorage` keyed by `{topic}:{questionId}`
- On question load, check localStorage first; if draft exists, restore it silently
- Show a faint "Draft saved" indicator in the editor topbar (fades after 2s)
- "Clear draft" option resets to starter code

**Files:** `frontend/src/pages/QuestionPage.js`, `frontend/src/pages/SampleQuestionPage.js`

---

### Daily streak system ✦ single strongest retention mechanism

**Problem:** Users have no reason to return daily. Streaks are the most proven mechanism for building practice habits (Duolingo, LeetCode, Brilliant all use them).

**Backend:**
- `GET /api/auth/me` already exists — add `streak_days` and `streak_at_risk` to response
- Computed from `user_progress` table (solved at least one question today and yesterday)
- `streak_at_risk: true` when current day has no solve yet

**Frontend:**
- Streak flame counter in the topbar next to the user name: `🔥 7`
- On first solve of the day: toast notification "Streak extended! 🔥 8 days"
- On `streak_at_risk: true`: subtle yellow indicator "Solve today to keep your streak"
- Streak broken: "Your streak ended at 7 days. Start a new one." (no punishment, just a nudge)
- Milestone toasts: 7, 30, 100 days

**Files:** `backend/db.py`, `backend/routers/auth.py`, `frontend/src/components/AppShell.js`, `frontend/src/App.css`

---

### Wrong answer diff visualization ✦ core feedback quality

**Problem:** On an incorrect SQL submission, users see two separate result tables (yours vs expected). They have to scan both mentally to find the difference. This is slow and frustrating.

**What to build:**
- Row-level diff in `ResultsTable.js` when showing submit comparison:
  - Rows only in user result: highlighted red background
  - Rows only in expected result: highlighted green background
  - Rows in both but with differing cell values: cell-level yellow highlight
- Summary line above the table: `"Your query returns 47 rows, expected 23. 24 extra rows found."`
- For Python track: test case diff shows input → your output vs expected output side-by-side

**Files:** `frontend/src/components/ResultsTable.js`, `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### Progressive hint system redesign ✦ learning experience

**Problem:** Current hint system is a simple reveal counter (hint 1, hint 2, solution). It doesn't scaffold learning — it just reveals pre-written text. Users either ignore hints or go straight to the solution.

**What to build:**

Replace the current hint reveal with a **"Help me" journey**:

```
[I'm stuck]  ←── single CTA, always visible below question

  Step 1: Conceptual nudge       "Think about how to identify the earliest event per user"
  Step 2: Approach hint          "You'll need to group by user_id and find the minimum timestamp"
  Step 3: Code structure hint    "Consider: SELECT user_id, MIN(event_time) FROM events GROUP BY ..."
  Step 4: Show full solution     (with explanation)
```

- Each step is a tap/click to reveal; can't skip steps (reduces solution shortcutting)
- Time gate: can advance to next step immediately, but solution requires 2 min on page (soft gate)
- Show how many users needed each step: "67% of users solved this without hints" (social proof + motivation)
- Hint steps are structured fields in question JSON: `hint_conceptual`, `hint_approach`, `hint_structure`

**Files:** Question JSON schema (add `hint_conceptual`, `hint_approach`, `hint_structure`), `frontend/src/pages/QuestionPage.js`, new `frontend/src/components/HintStepper.js`

---

### Concept tag explanation modal ✦ learning depth

**Problem:** Concept tags (e.g., "COHORT ANALYSIS", "RUNNING TOTAL") are displayed as decorative pills. Clicking them does nothing. This is a missed learning opportunity.

**What to build:**
- Clicking any concept tag opens a slide-in panel (right side, 320px):
  ```
  COHORT ANALYSIS
  ─────────────────────────────
  Group users by their signup period, then track their
  behavior over subsequent time periods relative to when
  they joined — not by calendar date.

  Common pattern:
  WITH cohorts AS (
    SELECT user_id, DATE_TRUNC('month', signup_date) AS cohort
    FROM users
  )
  ...

  Questions using this concept:  [3 questions →]
  ```
- Concept explanations stored in a `backend/content/concepts.json` map (concept name → explanation + code example)
- Panel is dismissible; ESC key closes it

**Files:** New `backend/content/concepts.json`, new `frontend/src/components/ConceptPanel.js`, `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### "Similar questions" after solving ✦ session length driver

**Problem:** After solving a question correctly, users see "Next Question →" which goes to the next sequential question. There's no recommendation of related questions. Users who want to reinforce a concept have no easy path.

**What to build:**
- After a correct submission, show a "Practice more like this" strip below the verdict card:
  ```
  You just practiced: [COHORT ANALYSIS]  [RUNNING TOTAL THRESHOLD]

  Similar questions:
  ┌──────────────────────────────┐  ┌──────────────────────────────┐
  │ Monthly Retention Rate       │  │ Rolling 7-day Active Users    │
  │ Medium · SQL                 │  │ Hard · SQL                    │
  │ [Solve →]                    │  │ [Solve →]                     │
  └──────────────────────────────┘  └──────────────────────────────┘
  ```
- Computed client-side: find unsolved questions that share ≥1 concept tag with the solved question
- Show max 2 recommendations; exclude already-solved and locked questions
- "Continue to next →" still exists as the primary CTA; this is secondary

**Files:** `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### Monaco editor enhancements ✦ editor quality

The editor is where users spend 80% of their time. It must feel excellent.

**SQL autocomplete with schema awareness:**
- Register table names and column names from `question.schema` as Monaco completions
- Trigger on `.` after a table alias → show columns for that table
- Trigger on whitespace/newline → suggest table names
- Implementation: `monaco.languages.registerCompletionItemProvider('sql', ...)`

**Auto-format SQL:**
- `Cmd+Shift+F` (or `Ctrl+Shift+F`) formats the SQL in the editor
- Use `sql-formatter` npm package (lightweight, no backend call needed)
- Also auto-format on submit (optional, show formatted version in solution)

**Query history (within session):**
- Last 5 Run results accessible via a `↑↓` toggle in the editor topbar
- Clicking a history entry restores that code into the editor
- Stored in component state (not persisted — session only)

**Font size control:**
- `A−` / `A+` buttons in the editor topbar
- Range: 12px–20px, step 2px
- Persisted in localStorage (`editor_font_size`)

**Files:** `frontend/src/components/CodeEditor.js`, `frontend/src/App.css`, `frontend/package.json` (add `sql-formatter`)

---

### Skeleton loaders ✦ polish

**Problem:** Loading states currently show nothing or a spinner. Skeleton loaders feel significantly more polished and reduce perceived load time.

**What to build:**
- `QuestionPage` skeleton: placeholder blocks for question title, description text, editor area
- `SidebarNav` skeleton: 8 placeholder question rows while catalog loads
- `TrackHubPage` skeleton: progress bar placeholder + question list stubs
- `ProgressDashboard` skeleton: 4-card grid with pulsing placeholder content
- CSS: use `animation: skeleton-pulse 1.5s ease-in-out infinite` with a light gray shimmer

**Files:** New `frontend/src/components/Skeleton.js`, all page components, `frontend/src/App.css`

---

### Micro-animations & transitions ✦ look and feel

**Problem:** The current UI is static — progress bars snap to their values, navigating between pages is instant but jarring, and solving a question feels no different from getting one wrong.

**What to build:**

**Progress bar animations:**
- All `TrackProgressBar` fills animate from previous value to new value (`transition: width 600ms ease-out`)
- Triggering moment: catalog refresh after a correct submit

**Solve celebration:**
- On first correct submission for a question: brief confetti burst (use `canvas-confetti`, ~5KB)
- Subsequent correct submits: green checkmark pulse only (no repeat confetti)
- Unlock event: when a new difficulty unlocks, show a toast: "Medium questions unlocked! 🔓"

**Page transitions:**
- Fade-in on route change (`opacity: 0 → 1`, 150ms) using React Router's location key
- Eliminates the jarring "white flash" on navigation

**Button loading states:**
- Run/Submit buttons show a spinner inside when loading (not just `disabled`)
- Submit button: "Checking..." text during submission

**Milestone toasts:**
- 1st question solved: "First one down! Keep going →"
- 10 easy questions: "Medium questions unlocking soon!"
- 25 total: "You're on a roll — 25 questions solved"
- First hard: "Hard mode unlocked. You're ready for this."

**Files:** `frontend/src/App.css`, `frontend/src/components/TrackProgressBar.js`, `frontend/src/pages/QuestionPage.js`, `frontend/package.json` (add `canvas-confetti`)

---

### Session goals & focus mode ✦ longer sessions

**Problem:** Users open the app without a clear intention. Having a goal ("solve 3 questions today") dramatically increases session length and return rate.

**Daily goal widget:**
- Set on first visit of the day (or from settings): "Today's goal: 3 questions"
- Shown as a compact progress indicator in the sidebar header: `🎯 1 / 3 today`
- Completing the goal: green checkmark + "Goal met! See you tomorrow."
- Goal persists in localStorage; resets at midnight

**Focus mode:**
- Toggle button (⊡ icon) in the editor topbar
- Hides: sidebar, topbar nav links, concept pills, status metadata
- Shows: only question description + editor + run/submit buttons
- URL gains `?focus=1`; ESC exits focus mode
- Ideal for timed practice or deep work

**Files:** `frontend/src/components/AppShell.js`, `frontend/src/components/SidebarNav.js`, `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### Keyboard shortcuts ✦ power user experience

Power users who practice daily will reach for shortcuts. Missing shortcuts are a friction that accumulates.

| Shortcut | Action |
|---|---|
| `Cmd/Ctrl + Enter` | Run code |
| `Cmd/Ctrl + Shift + Enter` | Submit |
| `Cmd/Ctrl + ]` | Next question |
| `Cmd/Ctrl + [` | Previous question |
| `Cmd/Ctrl + Shift + F` | Format SQL |
| `?` | Open keyboard shortcuts modal |
| `Esc` | Close any open panel / exit focus mode |
| `H` | Show next hint (when focused outside editor) |

- Register via `useEffect` + `keydown` listener in `QuestionPage.js`
- `?` key opens a `KeyboardShortcutsModal.js` overlay
- Shortcuts disabled when cursor is inside Monaco editor (Monaco handles its own)

**Files:** `frontend/src/pages/QuestionPage.js`, new `frontend/src/components/KeyboardShortcutsModal.js`, `frontend/src/App.css`

---

### Resizable split pane ✦ editor ergonomics

**Problem:** The question description vs editor split is a fixed CSS grid. Users writing long queries want more editor space; users re-reading the question want more description space.

**What to build:**
- Draggable divider between left panel and right editor panel
- Drag handle: 4px wide bar, hover shows cursor `col-resize`
- Range: left panel 260px–500px; persisted in localStorage
- Snap to default (330px) on double-click of divider
- Mobile: not applicable (stacked layout)

**Implementation:** Pure CSS/JS resize (no library needed — ~30 lines of drag logic).

**Files:** `frontend/src/components/AppShell.js` or `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

### Empty states with guidance ✦ clarity

Every empty state must tell the user what to do next. Currently most are blank or missing.

| Location | Empty state message |
|---|---|
| TrackHubPage (0 solved) | "Start with an Easy question — they're designed to build your foundation." + [First question →] |
| ProgressDashboard (new user) | "You haven't solved any questions yet. Pick a track to start." + track cards |
| Submission history | "No past attempts — submit your answer to start tracking." |
| SidebarNav search (no results) | "No questions match '{query}'. Try a different concept or clear the filter." |
| Concept filter (no matches) | "No questions match these filters. Try removing one." |
| Mock session history | "No mock sessions yet. [Start your first mock →]" |

**Files:** All page components, `frontend/src/App.css`

---

### Accessibility baseline ✦ non-negotiable

**What to ensure before public launch:**
- All interactive elements reachable via `Tab` key
- Sidebar question list navigable with arrow keys
- Focus ring visible on all focused elements (currently may be suppressed by CSS)
- `aria-label` on icon-only buttons (collapse toggle, theme toggle, hint reveal)
- Color alone never conveys state (solved/locked states use icons + color, not color alone)
- Minimum contrast ratio 4.5:1 for all text (audit `--text-secondary` on light backgrounds)
- Monaco editor: `aria-label="Code editor"` attribute

Run Lighthouse accessibility audit; target score ≥ 90 before Phase 2 launch.

**Files:** `frontend/src/components/AppShell.js`, `frontend/src/components/SidebarNav.js`, `frontend/src/App.css`

---

### Result error clarity ✦ feedback quality

**Problem:** When SQL has a syntax error or runtime error, the error message is displayed as raw text from DuckDB. This is opaque to learners.

**What to build:**
- Parse common DuckDB error patterns and show a human-friendly version:
  - `Parser Error: syntax error at or near "FORM"` → `Syntax error: Did you mean FROM instead of FORM?`
  - `Binder Error: Referenced table "user" not found` → `Table "user" not found. Available tables: users, orders, products...`
  - Timeout → `Your query took too long (>3 seconds). Try adding a WHERE clause to filter rows first.`
- Highlight the error line in Monaco (Monaco supports `editor.deltaDecorations`)
- Link to the relevant table in SchemaViewer when a "table not found" error fires

**Files:** `frontend/src/pages/QuestionPage.js`, new `frontend/src/utils/sqlErrorParser.js`, `frontend/src/components/CodeEditor.js`

---

### Question bookmarks ✦ return-to-later

**Problem:** Users encounter questions they want to return to (too hard now, interesting pattern to revisit) but have no way to mark them.

**What to build:**
- Bookmark icon (☆/★) in the question header
- Bookmarks stored in localStorage (no backend needed — keep it simple)
- "Bookmarked" section at the bottom of `SidebarNav` (shown only when bookmarks exist)
- Max 20 bookmarks; oldest removed when exceeded

**Files:** `frontend/src/pages/QuestionPage.js`, `frontend/src/components/SidebarNav.js`, `frontend/src/App.css`

---

### Per-question soft timer ✦ interview awareness

**Problem:** Users have no awareness of how long they spend on each question. In real interviews, time awareness is a skill. This is separate from mock mode — it's always-on, non-enforced, educational.

**What to build:**
- Subtle elapsed timer in the editor topbar: `⏱ 4:32` (starts when question loads)
- Pauses when tab loses focus (no anxiety from background time)
- Color: neutral → orange (>10 min for easy, >20 min for medium, >30 min for hard)
- Recorded in submission payload as `duration_ms` (already in the submissions schema)
- After submit: "You solved this in 6:24. Median for this question: 8:10." (Phase 3+ once data exists)

**Files:** `frontend/src/pages/QuestionPage.js`, `frontend/src/App.css`

---

## Tech Stack Decisions

Decisions to make before or alongside implementation. Deferring these creates compounding debt.

### Adopt React Query (TanStack Query) — Phase 1

**Problem:** Every page does manual `useState + useEffect + fetch` for server data. As mock sessions, submission history, and leaderboards land, managing loading/error/stale states manually becomes unmaintainable.

**Decision:** Replace manual data fetching with TanStack Query (`@tanstack/react-query`).
- Automatic caching, background refetch, stale-while-revalidate
- `useQuery` for reads, `useMutation` for writes (submit, mock start/finish)
- Remove ~40% of boilerplate from every page component
- Works alongside existing Axios client (`api.js`)

**Scope:** Migrate `catalogContext.js`, `QuestionPage`, `ProgressDashboard` first. New pages (MockHub, MockSession) use it from day one.

**File additions:** `frontend/package.json` (add `@tanstack/react-query`), `frontend/src/App.js` (wrap in `QueryClientProvider`)

---

### TypeScript migration — Phase 4 (after core features stable)

**Problem:** Plain JS frontend has no type safety. With 10+ new pages and components planned, bugs from bad prop types and API response shapes will grow.

**Decision:** Migrate frontend to TypeScript incrementally.
- Start: add `tsconfig.json`, rename new files `.tsx`/`.ts` as they are created
- Don't rename all existing files at once — migrate as each file is touched
- Add API response types in `frontend/src/types/api.ts`
- Adds ~zero runtime cost, massive developer experience improvement

**Files:** `frontend/tsconfig.json` (new), `frontend/vite.config.js` (update), new components in `.tsx`

---

### Email service — Phase 1 (prerequisite for account recovery)

**Problem:** Password reset UI exists in `AuthPage.js` but the backend has no email sending capability. Users who forget their password are permanently locked out.

**Recommended:** [Resend](https://resend.com) (simple API, generous free tier) or Postmark.

**What to build:**
- `password_reset_tokens` table: `token`, `user_id`, `expires_at`, `used`
- `POST /api/auth/forgot-password` — generate token, send email, 15-min expiry
- `POST /api/auth/reset-password` — validate token, update password hash, invalidate token
- `POST /api/auth/verify-email` — optional but recommended for paid users
- Welcome email on registration

**Env vars to add:** `EMAIL_FROM`, `RESEND_API_KEY` (or equivalent)

**Files:** `backend/routers/auth.py`, `backend/db.py`, `backend/alembic/`, `backend/email.py` (new utility)

---

## Platform Health

Infrastructure that must exist before significant user growth. Not features — foundations.

### Error monitoring — Sentry ✦ add before Phase 2 launch

**Problem:** Production errors are invisible. Users encounter bugs; we have no signal.

**What to add:**
- Backend: `sentry-sdk[fastapi]` — catches unhandled exceptions, attaches `request_id`, user context
- Frontend: `@sentry/react` — catches JS errors, records component stack
- Set up separate DSNs for backend/frontend
- Filter out 4xx errors (expected); alert on 5xx spikes

**Env vars:** `SENTRY_DSN` (backend + frontend)

**Files:** `backend/main.py` (init Sentry before app creation), `frontend/src/App.js` (wrap with `Sentry.ErrorBoundary`)

---

### Analytics — PostHog ✦ add before Phase 2 launch

**Problem:** No visibility into user behavior — can't measure where users drop off, which questions get abandoned, free→paid conversion, or which features drive engagement.

**Recommended:** [PostHog](https://posthog.com) — open source, self-hostable, generous free cloud tier.

**Key events to track:**
- `question_started`, `question_submitted`, `question_solved` (with track, difficulty, question_id)
- `mock_session_started`, `mock_session_completed` (with mode, track, score)
- `plan_upgraded` (with from/to plan)
- `sample_completed`, `sample_reset`
- Page views (automatic with PostHog's autocapture)

**Funnel to measure:** Landing → Track selection → First question → First solve → Registration → Plan upgrade

**Files:** `frontend/src/App.js` (PostHog init), `frontend/src/pages/QuestionPage.js` (track events), `frontend/package.json`

---

### SEO — add in Phase 1 ✦ low effort, high compounding return

**Problem:** `index.html` has `<title>datathink</title>` and nothing else. No description, no og:* tags, no structured data. A client-rendered React SPA with no meta tags gets zero organic traffic.

**What to add:**

1. **Static meta tags** in `frontend/index.html` (immediate):
   ```html
   <meta name="description" content="Practice SQL, Python, Pandas, and PySpark for data interviews. 311+ real interview questions with instant feedback." />
   <meta property="og:title" content="datathink — Data Interview Practice" />
   <meta property="og:description" content="..." />
   <meta property="og:image" content="/og-image.png" />
   <meta name="twitter:card" content="summary_large_image" />
   ```

2. **Dynamic meta tags** per page using `react-helmet-async`:
   - Landing: brand description
   - TrackHubPage: "Practice SQL interview questions — datathink"
   - QuestionPage: question title in `<title>` (helps with direct links)

3. **robots.txt** and **sitemap.xml** served by FastAPI:
   - Block `/api/*`, `/auth`, `/mock/:id`
   - Include `/`, `/practice/sql`, `/practice/python`, `/sample/*`, `/learn/*`

4. **Prerender/SSG for landing page** (longer term): For a React SPA, consider adding `react-snap` or moving the landing page to a static HTML file for full Google indexability.

**Files:** `frontend/index.html`, `frontend/public/robots.txt`, `backend/routers/system.py` (add sitemap endpoint), `frontend/package.json` (add `react-helmet-async`)

---

### CI/CD pipeline — complete the loop ✦ before Phase 2

**Current state:** CI runs tests on every push but nothing deploys automatically. Production deployments are manual.

**What to add to `.github/workflows/ci.yml`:**
1. **On merge to `main`:** trigger Railway deploy via `railway up` or Railway webhook
2. **Question JSON validation job:** catch malformed question JSON before merge
   ```yaml
   - name: Validate question JSON
     run: python backend/scripts/validate_questions.py
   ```
3. **Dependency security scan:** `pip-audit` for backend, `npm audit` for frontend
4. **ESLint** check for frontend (add `.eslintrc.js`)
5. **Bundle size check:** fail if JS bundle exceeds threshold (e.g., 500KB gzipped)

**Files:** `.github/workflows/ci.yml`, `backend/scripts/validate_questions.py` (new), `.eslintrc.js` (new)

---

### Security hardening — Phase 1

**Current gaps:**
- No HTTPS enforcement (redirect http → https in production)
- No security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Content-Security-Policy`)
- No CSRF protection (FastAPI uses cookies; CSRF is a real vector)
- No password strength validation on registration
- No account lockout after N failed login attempts

**What to add to `backend/main.py`:**
```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

**CSRF:** Use `double-submit cookie` pattern or `sameSite=strict` on session cookie (already partially mitigated if session cookie is `SameSite=Strict`).

---

### Database connection pool tuning — Phase 5 prerequisite

**Problem:** `asyncpg` defaults to 10 connections. Under real load with concurrent users this exhausts immediately.

**Add to `config.py`:**
```python
DB_POOL_MIN_SIZE: int = 5
DB_POOL_MAX_SIZE: int = 50  # PGPOOL_MAX_SIZE env var
DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME: float = 300.0
```

Apply when creating pool in `db.py`:
```python
pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=settings.DB_POOL_MIN_SIZE,
    max_size=settings.DB_POOL_MAX_SIZE,
    max_inactive_connection_lifetime=settings.DB_POOL_MAX_INACTIVE_CONNECTION_LIFETIME,
)
```

---

### Question search — Phase 4

**Problem:** At 311+ questions (growing), users can't find specific questions without browsing all difficulty groups.

**What to build:**
- Lightweight full-text search over question `title` + `description` + `concepts`
- Client-side search via `fuse.js` (no backend changes — catalog is already loaded)
- Search bar in the sidebar above concept filters
- Results: question title · difficulty badge · track · [Go →]

**Files:** `frontend/src/components/SidebarNav.js`, `frontend/package.json` (add `fuse.js`), `frontend/src/App.css`

---

### Admin / question management — Phase 4

**Problem:** 311+ questions managed via raw JSON file edits. No way to add/edit questions without touching source code.

**Minimal admin interface (internal tool, not public):**
- Protected route `/admin` (admin-only flag on user row)
- Question list with search and filter
- Edit form for question JSON fields
- Saves to PostgreSQL question cache (or writes back to JSON files via API)
- Question preview (render as it would appear to users)

**Alternative (simpler):** GitHub-based workflow — question edits go through PRs with automated validation CI job. No admin UI needed; CI is the gatekeeper.

---

### Onboarding — Phase 1 ✦ biggest retention lever

**Problem:** New users (anonymous) land on the platform with no guidance. The conversion from "landed" to "first question solved" is the most important funnel step.

**What to build:**
- First-time visitor modal or tooltip sequence:
  1. "Pick a track" → highlight track pills
  2. "Try a sample question first — no login needed" → highlight sample tiles
  3. Skip option always visible
- First solve celebration: confetti or highlight animation on first correct answer
- Empty state in `TrackHubPage`: "You haven't solved any questions yet. Start with Easy →"
- Progress nudge: after 5 easy questions solved, show "Unlock medium questions — 5 more to go" progress indicator

**Files:** New `frontend/src/components/OnboardingTooltip.js`, `frontend/src/pages/QuestionPage.js` (first-solve celebration), `frontend/src/pages/TrackHubPage.js` (empty state), `frontend/src/App.css`

---

## Phase 1 — Quick wins (core experience) ✦ high impact, low effort

~~All Phase 1 items shipped — see Completed section.~~

---

## Phase 2 — Mock interview mode ✦ highest competitive impact

~~All Phase 2 items shipped — commit bd21542+.~~

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
- Browser tab title: `"12:34 — Mock Interview | datathink"`

**MockSummary (inline after completion):**
- Score card: X/Y solved · time used
- Per-question: title · solved/unsolved · time spent · final code toggle
- "Practice weaknesses" CTA → concept-filtered question list
- "Share result" → copy text ("2/3 SQL questions in 28 min")

**Files to create:** `frontend/src/pages/MockHub.js`, `frontend/src/pages/MockSession.js`, `backend/routers/mock.py`

**Files to change:** `frontend/src/App.js`, `backend/db.py`, `backend/alembic/`, `frontend/src/App.css`

---

~~Phase 3 shipped — see Completed section.~~

---

## Phase 4 — Content & discovery ✦ retention and depth

### Company tags on questions

- Add `"companies": ["Meta", "Stripe", "Airbnb"]` to question JSON
- Filter chips in sidebar: "Show Meta questions" (builds on Phase 1C concept filter)
- Landing page: "Practice questions from top companies" section
- No backend schema changes — metadata on question JSON only

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

### Auth page tightening

**Current gaps in `AuthPage.js`:**

1. **OAuth buttons are unimplemented.** Google, GitHub, and Apple buttons are rendered and hit `/auth/oauth/{provider}` which doesn't exist — they just surface an error. Remove them or replace with a disabled/"Coming soon" state until OAuth is actually built.

2. **Forgot password silently misleads users.** Submitting the forgot-password form shows a hardcoded fake-success message ("Password reset is not yet available"). Users who are genuinely locked out think a reset email was sent. Fix: show the honest message *before* submission (static copy in the form), or remove the `forgot` mode entirely until the email service is live (see Email service section above).

3. **No real password complexity enforcement.** Signup only has `minLength={8}` on the HTML input with no backend validation. Add client-side rules and a matching server-side check: min 8 chars, at least one uppercase, one lowercase, one number. No symbol requirement — accessible but not trivial. Show a short requirements hint under the password field on signup.

**Files:** `frontend/src/pages/AuthPage.js`, `backend/routers/auth.py`, `frontend/src/App.css`

---

## Completed

### Phase 4 · Learning paths — shipped

4 curated SQL learning paths stored as JSON in `backend/content/paths/`: Window Functions Mastery (7 questions), Aggregation Patterns (7), Cohort & Retention (6), Funnel & Event Analysis (5). `GET /api/paths` returns list with per-user `solved_count`; `GET /api/paths/:slug` returns detail with per-question `state` (solved/unlocked/locked) using existing `compute_unlock_state()`. `LearningPath.js` page at `/learn/:slug` with topbar, breadcrumb, progress bar, and question list (✓ solved / → next / 🔒 locked). `PathProgressCard` component (used by LandingPage + TrackHubPage). LandingPage gets "Structured learning paths" section below track selection. TrackHubPage shows filtered path cards below "What you'll practice".

*commit: (current)*

---

### Phase 4 · Company tags on SQL questions — shipped

`"companies"` field added to all 86 SQL questions with contextual assignments (Stripe for payments, Meta/Airbnb for user/cohort questions, Amazon/Shopify for orders/products, Google/Microsoft for HR, etc.). `CompanyFilter` component added to `SidebarNav.js` below the concept filter — frequency-sorted chips, active accent style, AND logic with concept filter. `/api/catalog` extended to include `companies` per question. Company strip added to `LandingPage.js` between showcase and tracks sections (10 company chips linking to `#landing-tracks`).

*commit: 294e464*

---

### 1D · Mobile UX improvements — shipped

Track tiles stack vertically on mobile (<600px) instead of horizontal scroll. Schema viewer on SQL question pages becomes a bottom-sheet drawer on mobile — "Schema (N tables)" button slides up an overlay panel. CSS in `App.css`; bottom-sheet JSX + `schemaSheetOpen` state in `QuestionPage.js`.

---

### 1C · Concept filter in sidebar — shipped

Frequency-sorted concept chips above difficulty groups in `SidebarNav.js`. Top 8 shown by default; "+N more ▾" expands all. Active chip shows accent fill + ×; "Clear" link resets. Client-side filter updates question list and counts in real time. Backend: `concepts` field added to all four catalog responses (`routers/catalog.py`, `python_questions.py`, `python_data_questions.py`, `pyspark_questions.py`).

*commit: d35f550 (initial), concepts parity fix: follow-up commit*

---

### 1B · Dark mode persistence — shipped

localStorage-backed theme toggle (light / dark / system) with ◐/☾/☀ icon button in both topbars (LandingPage + AppShell). `ThemeContext` + `useTheme` hook in `App.js`; anti-FOUC inline script in `index.html`; `[data-theme="dark"]` and `[data-theme="light"]` CSS override selectors in `App.css` mirror the existing `@media (prefers-color-scheme: dark)` block.

*commit: a4681ec*

---

### 3 · Solution quality scorecard — shipped

After a correct SQL submission, an expandable "Solution analysis" section appears in `QuestionPage.js` showing: **Efficiency** (DuckDB EXPLAIN-based estimated row comparison), **Style** (SELECT *, nested subqueries, CTE usage), **Complexity** (from `complexity_hint` field in question JSON), and **Alternative approach** (from `alternative_solution` field). Backend: `_get_explain_total_ec()`, `_analyze_query_style()`, `_compute_quality()` added to `evaluator.py`; `quality` returned alongside correct verdicts. `complexity_hint` + `alternative_solution` added to medium Q2001/2003/2004 and hard Q3001/3003/3004.

---

### 1A · Submission history — shipped

Records every submit attempt per user. Collapsible "Past attempts" panel in QuestionPage shows last 5 attempts with pass/fail badge, relative timestamp, and code expand toggle. Backend: `submissions` table in `_SCHEMA_SQL`, `record_submission()` + `get_submissions()` in `db.py`, `GET /api/submissions` endpoint, called in all 4 submit handlers.

*commit: c0aab30*
