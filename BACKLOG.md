# Platform Backlog

Consolidated from TODO.md and path-to-world-class.md. Remove items as they ship; update `docs/` and `CLAUDE.md` in the same commit.

**Current state (2026-05-06):** Core platform is feature-complete. Auth, all four tracks, mock interviews, learning paths, dashboard insights, streak system, workspace polish (bookmarks, drafts, diff, resizable pane, focus mode, hints, concept panel, skeleton loaders, animations), and observability (Sentry + PostHog) are all shipped. What remains is engineering foundations, two workspace gaps, and Phase 6 community features.

---

## Remaining work

### Engineering foundations

**React Query adoption**
Replace manual `useState + useEffect + axios` data fetching with TanStack Query.
- Install `@tanstack/react-query` in `frontend/package.json`
- Wrap `App.js` in `QueryClientProvider`
- Migrate `catalogContext.js`, `QuestionPage`, `ProgressDashboard` first; new pages use it from day one
- `useMutation` for submit/mock-start/mock-finish; `useQuery` for catalog, insights, path data

**Configurable DB connection pool**
`asyncpg` currently uses a fixed pool size — will exhaust under real load.
- Add `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE`, `DB_POOL_MAX_INACTIVE_LIFETIME` to `backend/config.py`
- Apply in `backend/db.py` `create_async_engine` call
- Defaults: min=5, max=50, inactive lifetime=300s; override via env vars in production

**DuckDB connection pool**
Single shared DuckDB cursor is a concurrency bottleneck.
- Replace with a pool of pre-loaded in-memory connections in `backend/database.py`
- Pool size configurable via `DUCKDB_POOL_SIZE` env var (default: 8)
- Each connection is a full DuckDB instance with all CSV tables loaded at startup

**CI/CD gaps**
Question validation and dependency audits already run in CI. Missing:
- Deploy-on-merge step (Railway webhook or `railway up` on push to `main`)
- ESLint step (add `.eslintrc.js`, wire into `.github/workflows/ci.yml`)
- JS bundle-size budget (fail CI if gzipped bundle exceeds threshold, e.g. 500 KB)

---

### Workspace

**Monaco SQL autocomplete**
- Register table names + column names from `question.schema` as completions in `CodeEditor.js`
- `monaco.languages.registerCompletionItemProvider('sql', ...)` — trigger on `.` after alias → show columns; trigger on whitespace → suggest table names
- SQL-only; Python editor unchanged

**Keyboard shortcuts help modal**
- `?` key (when cursor outside Monaco) opens a modal overlay listing all shortcuts
- Create `frontend/src/components/KeyboardShortcutsModal.js`
- Wire in `QuestionPage.js` alongside existing `⌘↵` / `⌘⇧↵` bindings

---

### Content

**Schema design question type**
- Debug-type questions (`"type": "debug"`) exist; `"type": "schema_design"` does not
- Requires evaluator decision before authoring: MCQ-style (select the correct DDL) or free-form DDL via DuckDB execution (see `new-tracks-roadmap.md` for the DuckDB DDL validation approach)
- No questions authored yet; not in any difficulty file

---

---

### TypeScript migration

- Add `tsconfig.json` + update `vite.config.js`
- Rename new files `.tsx`/`.ts` as they are created (no big-bang rename)
- Add `frontend/src/types/api.ts` for API response types
- Start after React Query is in place (gives a cleaner migration surface)

---

### Community & profiles (Phase 6)

Do not start until the engineering foundations above are stable.

**`/profile` page** (`frontend/src/pages/ProfilePage.js`)
```
TOPBAR
PROFILE HEADER — initials avatar · name/email · plan badge · member-since · total solved · streak
BADGES ROW — earned badges with unlock date; locked badges greyed with unlock criteria tooltip
STATS GRID — 2×2 (desktop) per-track solve count + progress bar
MOCK HISTORY — table: date · mode · track · score · time · [Review]
ACTIVITY HEATMAP — GitHub-style contribution grid from submissions table (CSS grid, 5-level --success opacity scale)
```
Wire at `/profile` in `App.js`. Add "See all badges →" link from Dashboard badge strip.

**`/leaderboard`** (`frontend/src/pages/Leaderboard.js`)
```
TABS — Weekly · All-time · By track
TABLE — rank · user (anonymised unless opt-in) · track · solved · avg time; current user highlighted
OPT-IN BANNER — "Make your stats public?" shown if not opted in
```
Backend: query `submissions` + `mock_sessions` — no new schema needed. Add `leaderboard_opt_in` bool to `users` table.

**Achievement badges**
Computed at read time from `submissions` + `mock_sessions` (no separate badge table initially):
- SQL Starter — first SQL question solved
- Speed Demon — hard question solved in < 5 min
- 7-Day Streak — 7 consecutive days with ≥ 1 solve
- Mock Pro — 5 mock sessions completed
- Century — 100 total questions solved

Surface on `/profile` and as a compact strip on `/dashboard` (5 most recent; "See all →" links to profile).
New component: `frontend/src/components/BadgeCard.js`

**Per-question discussion threads**
- New `discussion_posts` table: `id, question_id, track, user_id, body, created_at`
- `GET /api/questions/{id}/discussion`, `POST /api/questions/{id}/discussion`
- Flat threads (no voting, no nesting); requires account; rate-limited
- Frontend: collapsible discussion section at bottom of `QuestionPage.js`

**Internal question management**
Decision still open. Options:
- **`/admin` UI** — protected route, question list + edit form, admin-only flag on `users` table
- **GitHub/CI workflow** — question edits via PR; CI validation is the gatekeeper (already partially in place with `validate_content.py`)

Recommend: GitHub/CI workflow for now (zero additional infrastructure), revisit `/admin` when question volume demands it.

---

## Shipped (reference)

All items below are fully implemented. Listed for historical context; no action needed.

### Auth & identity
- Anonymous-first identity with session upgrade on registration
- Login merges anonymous progress into existing account
- Password reset flow (forgot → email → token → reset)
- Email verification (register → verify token → mark verified)
- Magic-link sign-in (`POST /api/auth/magic-link` + callback)
- OAuth authorize + callback (`google`, `github`) with server-side state token, one-time use
- Login lockout after N failed attempts (`LOGIN_LOCKOUT_MAX_ATTEMPTS`)
- Reserved email prefix blocking on registration
- CSRF mitigation (Origin header check on mutating `/api/*` in production)
- Streak system: `streak_days` + `streak_at_risk` in `GET /api/auth/me`; streak pill in topbar; milestone toasts at 7/30/100 days

### Tracks & execution
- SQL (95 questions): DuckDB execution, 3s timeout, 200-row cap, read-only guard, solution quality scorecard
- Python (83 questions): subprocess sandbox, AST guard, 5s timeout, 512 MB RLIMIT_AS, test case comparison
- Pandas (76 questions): same sandbox as Python, DataFrame output comparison
- PySpark (102 questions): MCQ/predict-output/debug/scenario, option comparison, explanation always returned
- Mock-only questions (`mock_only: true`) excluded from practice catalog, only in mock sessions

### Mock interviews
- MockHub (`/mock`): mode/track/difficulty selection, daily limits by plan, mock history
- MockSession (`/mock/:id`): countdown timer, per-question submit (no solution revealed mid-session), reload recovery, auto-submit on expiry
- Post-mortem: score card, per-question breakdown, concept accuracy, "Drill weak concepts" CTA
- Elite: Focus mode (concept-filtered pool), mock history analytics (`GET /api/mock/analytics`)
- Plan gates: Free = 1 medium/day, Pro = 3 hard/day, Elite = unlimited

### Progress & unlock model
- Per-track solve history in PostgreSQL; unlock policy pure-function in `unlock.py`
- Free tier: easy all unlocked; medium/hard unlock in batches by solve thresholds (code-track vs PySpark thresholds differ)
- Learning path shortcuts: starter path completion → all medium unlocked; intermediate → full hard cap
- 22 learning paths (SQL: 7, Python: 5, Pandas: 5, PySpark: 5)
- Path pages with breadcrumb, progress bar, completion banner, in-progress rail on index

### Dashboard & insights
- Cross-track progress: solve counts, accuracy, median solve time per track
- Coaching insights: weakest concepts (bottom 3 with ≥ 3 attempts), cross-track pacing insight, streak, Elite readiness scores + study plan
- Cached 60s per user in-process

### Workspace — QuestionPage
- Draft autosave to `localStorage` (`draft:{topic}:{id}`), restore on load, clear-draft control
- Per-question soft timer (elapsed, pause-on-tab-hide, `duration_ms` in submissions)
- Resizable split pane (drag divider, localStorage persistence, double-click reset)
- Focus mode (`?focus=1`, sidebar hidden, togglable)
- Wrong-answer diff: row-level + cell-level highlighting, extra/missing row summary badge
- Progressive hint stepper: labeled steps (Conceptual → Approach → Structure → Solution), soft gate on solution reveal
- Concept explanation panel (`ConceptPanel.js`) from concept pills
- Similar-question recommendations after correct solves
- Question bookmarks: header toggle, localStorage cap 20, Bookmarks rail in SidebarNav
- Submission history: collapsible past-attempts panel, expands automatically on return visit
- Solution analysis (correct SQL): efficiency note, style notes, complexity hint, alternative approach

### Sidebar & navigation
- Concept filter chips (frequency-sorted, top 8 + expand, AND logic)
- Company filter chips (SQL only, frequency-sorted)
- Fuzzy full-text search via `fuse.js` (title + concepts)
- Unlock nudge copy is dynamic per-track (matches `unlock.py` thresholds)
- Lock/solved/next-up states, streak milestone toasts on solves

### Editor (CodeEditor / Monaco)
- Always-dark (`vs-dark`) — intentional, not a bug
- SQL `sql-formatter` shortcut (`⌘⇧F`)
- Run history popover (last 5 executions, session-only)
- Font-size persistence (`⌘+` / `⌘−`, A+/A− buttons, localStorage)
- `⌘↵` run, `⌘⇧↵` submit badges on buttons
- Schema viewer: search filter, click-to-copy column names
- Submit double-click protection

### UI & design
- Single global stylesheet (`App.css`), no CSS modules
- Dark/light mode toggle (ThemeContext, localStorage, pre-hydration anti-FOUC script)
- Skeleton loaders: `Skeleton.js` primitive used across QuestionPage, SidebarNav, TrackHubPage, ProgressDashboard
- Animated progress bars (`TrackProgressBar.js`), first-solve celebration, unlock/streak toasts, route fade-ins
- Onboarding walkthrough (`OnboardingTooltip.js`, localStorage-dismissed, 2-step)
- Responsive: 900px breakpoint, 600px breakpoint for mobile-specific layouts
- Sample pages: 36 sandbox questions (3 per track × difficulty), no login, no progress impact

### Platform health
- Sentry: backend (`sentry-sdk[fastapi]`) + frontend (`@sentry/react` with Session Replay on errors)
- PostHog: funnel events (question_submitted, solved, mock_started, mock_completed, plan_upgrade_started, plan_upgraded, sample_submitted)
- `X-Request-ID` + `X-Response-Time-Ms` on all responses
- Redis-backed rate limiting (in-memory fallback in dev)
- `error, request_id` shape on all user-facing errors

### Payments
- Razorpay: Orders (lifetime) + Subscriptions (pro/elite), HMAC-verified webhooks, idempotent plan updates
- Three tiers: Free / Pro / Elite (plus `lifetime_elite`)
