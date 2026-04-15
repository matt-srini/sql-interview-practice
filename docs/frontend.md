# Frontend

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md) · [Backend](./backend.md)

React 18 + React Router + Vite. Monaco editor. Axios API client. Single global stylesheet (`App.css`) with CSS custom properties. No CSS framework, no CSS modules.

---

## Route tree

Defined in `frontend/src/App.js`:

```
/                                → LandingPage (hero + showcase + track tabs)
/auth                            → AuthPage (register / sign in / forgot password / OAuth)
/auth/reset-password             → ResetPasswordPage (consume reset token, set new password)
/dashboard                       → ProgressDashboard (cross-track progress)
/mock                            → MockHub (mode/track/difficulty selector + history)  [AuthRequired]
/mock/:id                        → MockSession (active session + inline summary)        [AuthRequired]
/learn                           → LearningPathsIndex (all paths, grouped by track, topic pills)
/learn/:topic                    → LearningPathsIndex (filtered to one track)
/learn/:topic/:slug              → LearningPath (curated path — breadcrumb, progress bar, question list)
/sample/:topic/:difficulty       → SampleQuestionPage (topic-aware sample mode)
/sample/:difficulty              → redirect → /sample/sql/:difficulty
/practice/:topic                 → TopicShell (TopicProvider + CatalogProvider + AppShell)
  /practice/:topic               → TrackHubPage (track overview when no question selected)
  /practice/:topic/questions/:id → QuestionPage (topic-aware)
/practice/questions/:id          → redirect → /practice/sql/questions/:id  (legacy)
/practice                        → redirect → /practice/sql
/questions/:id                   → redirect → /practice/sql/questions/:id  (legacy)
```

`:topic` values: `sql` | `python` | `python-data` | `pyspark`

---

## Pages

### LandingPage (`/`)

Three stacked sections on a single scroll:

1. **Hero** (`.landing-hero`, logged-out only) — centered headline, tagline, CTAs ("Explore tracks ↓" and "Create account")
2. **Showcase** (`.landing-showcase`) — dark section (`#0C0C0A`), 4-card flex grid showing one animated question+answer per track; active card expands with a colored glow. Code font is Geist Mono weight 300. Auto-advances every ~5 s.
3. **Track selection** (`.landing-practice-section`, `id="landing-tracks"`) — pill nav selects a track; panel shows description, progress bar, CTA, and easy/medium/hard sample tiles. Mobile sample tiles use horizontal scroll.

On mount, checks `window.location.hash` and scrolls to the matching element (used by the sample page back arrow → `/#landing-tracks`).

### AuthPage (`/auth`)

Register or sign in. Supports email/password, Google OAuth, and GitHub OAuth. Also contains a "Forgot password?" flow that sends a reset email. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress merges into an existing account. OAuth callbacks redirect back to `/` after setting a session cookie.

### ResetPasswordPage (`/auth/reset-password`)

Consumes a password reset token (passed as `?token=…` query param) and lets the user set a new password. Redirects to `/auth` on success or if the token is invalid/expired.

### TrackHubPage (`/practice/:topic`)

Per-track landing rendered by `Outlet` when no question is active:
- Track name + overall solved/total progress bar
- Per-difficulty breakdown (easy/medium/hard bars)
- "Continue where I left off" button → navigates to next unlocked question
- Focus card with next unlocked question summary
- Concept preview for the track
- Solved concepts strip (concept tags from solved questions only)

Uses `useCatalog()` for question/progress data.

### QuestionPage (`/practice/:topic/questions/:id`)

Main practice screen. Layout and behavior vary by topic:

| Topic | Editor | Left panel | Result area |
|---|---|---|---|
| SQL | Monaco (sql) | Schema viewer | ResultsTable (run + submit) |
| Python | Monaco (python) | Description only | TestCasePanel + PrintOutputPanel |
| Pandas | Monaco (python) | VariablesPanel + description | ResultsTable + PrintOutputPanel |
| PySpark | Read-only code snippet (if present) | Description only | MCQPanel → reveal explanation |

- Compact status line in question header (difficulty / question position / open count)
- On mobile, question actions use a low-profile sticky dock for Run / Submit controls
- On correct: `refresh()` updates catalog context so sidebar reflects new unlock state
- "Next Question" navigates to `/practice/:topic/questions/:nextId`
- **Delta hint** (SQL only, wrong submissions): client-side row/column diff shows a targeted message — e.g. "Your output has 3 more rows than expected. Check for a missing filter or a JOIN that multiplies rows."
- **Verdict insight line**: on first-attempt correct solve shows "First-attempt solve — the system logged your approach"; on 3+ attempts shows an encouraging note
- **Writing notes auto-expand**: the Solution Analysis section (`solutionAnalysisOpen`) auto-expands on a first-attempt correct solve
- Submission history fetched with `limit: 20`; `priorAttemptCountRef` tracks attempt count before each submit to compute insight text
- **Path context**: when `?path=slug` is in the URL, fetches path data and shows a path nav bar (breadcrumb + position counter + prev/next links)

### SampleQuestionPage (`/sample/:topic/:difficulty`)

Standalone sample practice. No sidebar. No effect on challenge progression.

**Topbar** — three-column, full-width:
- Left: `datanest` home link
- Center: `←` back arrow (`<a href="/#landing-tracks">`) + track + difficulty label
- Right: "Start the challenge" CTA → `/practice/:topic`

### ProgressDashboard (`/dashboard`)

Cross-track progress overview. 4-card grid with TrackProgressBar per track, concept tags, and recent activity. Fetches `GET /api/dashboard` on mount.

### LearningPathsIndex (`/learn`, `/learn/:topic`)

Index of all learning paths. Grouped by track. Topic-filter pills narrow to a single track when `:topic` is present in the URL. Each path shown as a card with title, description, solved count, and a link to the path.

### LearningPath (`/learn/:topic/:slug`)

Curated path page. Shows breadcrumb (Learn → track → path title), overall progress bar, and a question list with per-question state (solved/unlocked/locked). Each question links to `/practice/:topic/questions/:id?path=:slug` so `QuestionPage` shows the path nav bar.

---

## Components

| Component | File | Purpose |
|---|---|---|
| AppShell | `components/AppShell.js` | Challenge workspace: fixed topbar with direct track nav, collapsible sidebar |
| SidebarNav | `components/SidebarNav.js` | Question list grouped by difficulty; topic-aware NavLinks |
| CodeEditor | `components/CodeEditor.js` | Language-agnostic Monaco editor (`language` prop: `'sql'` \| `'python'`) |
| SQLEditor | `components/SQLEditor.js` | Thin re-export of CodeEditor with `language="sql"` (backward compat) |
| ResultsTable | `components/ResultsTable.js` | Tabular results with sticky headers and null value rendering |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema — table names and column token grid |
| TestCasePanel | `components/TestCasePanel.js` | Python test case results (pass/fail per case, input/expected/actual, hidden summary) |
| PrintOutputPanel | `components/PrintOutputPanel.js` | Captured stdout block (rendered only if non-empty) |
| VariablesPanel | `components/VariablesPanel.js` | Available DataFrame variables with CSV source and column list |
| MCQPanel | `components/MCQPanel.js` | Radio-button MCQ with correct/wrong highlighting and explanation after submit |
| TrackProgressBar | `components/TrackProgressBar.js` | Reusable horizontal progress bar with configurable color and label |
| PathProgressCard | `components/PathProgressCard.js` | Path card with track color dot, progress bar, and CTA; used on LandingPage and TrackHubPage |
| Topbar | `components/Topbar.js` | Shared top nav bar used by standalone pages (LandingPage, MockHub, MockSession, ProgressDashboard, AuthPage); includes Practice dropdown, Mock link, Dashboard link, and auth state |
| TierBanner | `components/TierBanner.js` | Inline upgrade prompt shown when a user hits a plan gate (e.g. locked hard questions); renders contextual copy and upgrade CTA |
| UpgradeButton | `components/UpgradeButton.js` | Reusable upgrade CTA button; opens Stripe Checkout for the target plan tier |

### AppShell

- Fixed topbar with three zones:
  - **Left** (`app-topbar-brand`): hamburger on mobile, `datanest` brand link
  - **Center** (`app-topbar-center`): mode pill (`.shell-pill-mode`) — e.g. "SQL · Challenge", "SQL · Path", "Python · Challenge" — shown only when a question is active (not on TrackHub). Dot color matches the track color.
  - **Right** (`app-topbar-actions`): Practice ▾ dropdown (all 4 tracks), Mock link, theme toggle (cycles system/light/dark), plan pill (`.shell-pill-plan-free/pro/elite`)
- Desktop: sidebar 328px, collapsible; toggle is a `‹` icon button (`.sidebar-collapse-btn`); a `›` expand button (`.sidebar-expand-btn`) appears in the content area when collapsed
- Mobile (<900px): sidebar becomes fixed overlay with backdrop; hamburger button in topbar
- Upgrade panel shown for `free` and `pro` plan users; lives in the sidebar beneath the question list
- Unlock nudge message shown in sidebar for free-plan users who have locked questions

### SidebarNav

Accepts a `plan` prop (passed from AppShell) to drive progressive unlock behavior for free-plan users:

- Collapsible difficulty groups
- Per-question state: `unlocked`, `locked`, `solved`, `next`, `current`
- NavLinks point to `/practice/${topic}/questions/${id}` (topic from `useTopic()`)
- **Progressive unlock bar** (`.sidebar-unlock-bar`): shown in difficulty group headers when there are locked questions. Displays a progress bar filling toward the next unlock threshold plus a "{N} more to unlock" label. Thresholds mirror `backend/unlock.py` (e.g. SQL/Python/Pandas medium: 8→3, 15→8, 25→all; PySpark medium: 12→3, 20→8, 30→all).
- **Locked question tooltip** (`title` attribute on the locked row `div`): explains exactly how many more solves are needed — e.g. "Solve 7 more easy questions to unlock this". Pro users see "Upgrade to Elite to unlock all hard questions" on hard rows.
- Concept filter (chip grid, most-frequent first, expand/collapse) and Company filter (SQL only)
- Test coverage in `components/SidebarNav.test.js`

---

## Contexts

### `contexts/TopicContext.js`

Provides current topic and track metadata to the entire component tree.

```js
// TRACK_META[topic] shape:
{
  label: 'Pandas',
  description: 'pandas and numpy data manipulation',
  color: '#C47F17',
  apiPrefix: '/python-data',   // used to build API paths
  language: 'python',
  hasRunCode: true,
  hasMCQ: false,
  totalQuestions: 10,
  tagline: 'pandas · numpy · data wrangling',
}
```

`TopicProvider` reads `:topic` from URL params via `useParams()`. `useTopic()` returns `{ topic, meta }`.

### `catalogContext.js`

Fetches catalog for the current topic on mount. URL determined by `useTopic()`:
- `sql` → `/catalog`
- `python` → `/python/catalog`
- `python-data` → `/python-data/catalog`
- `pyspark` → `/pyspark/catalog`

Exposes `{ catalog, loading, error, refresh }`. Resets when topic changes.

### `contexts/AuthContext.js`

Provides `{ user, loading, logout, refreshUser }`. Fetches `/api/auth/me` on mount.

---

## API client

`frontend/src/api.js` — Axios instance with base URL resolution:

1. If `VITE_BACKEND_URL` env var is set → use that origin + `/api`
2. If on `localhost` without same-origin backend → fall back to `http://localhost:8000/api`
3. Otherwise → same-origin `/api`

All requests use `withCredentials: true` so the `session_token` cookie is sent during cross-origin local development.

---

## Data flows

### SQL challenge
1. `/practice/sql` → `TopicShell` provides topic + catalog
2. Question route → fetch `/api/questions/:id`
3. Run SQL → `POST /api/run-query` → ResultsTable
4. Submit → `POST /api/submit` → verdict + compare grid + hints/solution
5. On correct → `refresh()` → sidebar unlock state updates

### Python algorithm
1. `/practice/python/questions/:id` → fetch `/api/python/questions/:id`
2. Editor initialized with `question.starter_code`
3. Run → `POST /api/python/run-code` → TestCasePanel shows public cases
4. Submit → `POST /api/python/submit` → TestCasePanel + hidden test summary
5. On correct: solution_code + explanation revealed

### Pandas
1. `/practice/python-data/questions/:id` → fetch `/api/python-data/questions/:id`
2. VariablesPanel shows available DataFrames from `question.dataframes`
3. Run → `POST /api/python-data/run-code` → ResultsTable + PrintOutputPanel
4. Submit → `POST /api/python-data/submit` → correct/incorrect + DataFrame comparison

### PySpark MCQ
1. `/practice/pyspark/questions/:id` → fetch `/api/pyspark/questions/:id`
2. MCQPanel shows options (+ code_snippet if present)
3. User selects option → click Submit → `POST /api/pyspark/submit`
4. Response `{ correct, explanation }` → MCQPanel highlights correct/wrong + reveals explanation
5. No Run button, no code editor

### Sample flow
1. `/sample/:topic/:difficulty` → `GET /api/sample/:topic/:difficulty`
2. Backend marks that topic+difficulty sample as seen, returns next sample question
3. Run/submit uses topic-specific sample endpoints
4. 409 on exhaustion → reset button → `POST /api/sample/:topic/:difficulty/reset` → re-fetch
5. No effect on challenge progress

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Philosophy:** Professional tool aesthetic — calm, fast, distraction-free. Designed for long sessions (30–90 min). Light mode primary, warm dark mode via `prefers-color-scheme`. The SQL editor pane always uses a dark background (`#1e1e1e`) regardless of color scheme — intentional two-tone split.

### Color tokens

Defined in `:root` in `App.css`. Dark mode overrides in `@media (prefers-color-scheme: dark)`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg-page` | `#F7F7F5` | `#141413` | Page background |
| `--surface-card` | `#FFFFFF` | `#1C1C1A` | Cards, panels |
| `--surface-card-alt` | `#F0EFED` | `#242422` | Sidebar, secondary surfaces |
| `--border-subtle` | `rgba(26,26,24,0.08)` | — | Default borders |
| `--text-strong` | `#1A1A18` | `#F0EEE9` | Headings |
| `--text-primary` | `#2D2D2B` | `#D8D5CE` | Body text |
| `--text-secondary` | `#6B6862` | — | Labels, metadata |
| `--text-muted` | `#A8A49F` | — | Placeholders, disabled |
| `--accent` | `#5B6AF0` | `#7B8AF5` | Interactive elements, links |
| `--success` | `#2D9E6B` | — | Correct answer |
| `--warning` | `#C47F17` | — | Hints, locked |
| `--danger` | `#D94F3D` | — | Errors, wrong answer |

### Typography

```
--font-sans: "Inter", "Avenir Next", "Segoe UI", sans-serif
--font-mono: "JetBrains Mono", "SFMono-Regular", Consolas, monospace
```

| Font | Weight | Use |
|---|---|---|
| Inter | 400/500/600 | All UI text |
| JetBrains Mono | 400/600 | Editor, results tables, inline code blocks |
| Geist Mono | 300 | Showcase animation code block only |

### Buttons

Three tiers: `.btn-primary` (accent fill, Submit), `.btn-secondary` (outlined, Run / nav), `.btn-success` (success-soft tint, Next Question).

All hover: `translateY(-1px)`, `150ms ease-out`. No transforms on disabled.

`.btn-secondary` is context-sensitive: `rgba(255,255,255,0.07)` bg inside dark editor wrapper; `rgba(0,0,0,0.03)` outside.

### Radii and shadows

```
--radius-lg: 20px    (editor wrapper)
--radius-md: 14px    (inner cards, schema blocks)
--radius-sm: 10px    (badges, tokens)

--shadow-sm: 0 1px 4px rgba(26,26,24,0.08)
--shadow-md: 0 4px 16px rgba(26,26,24,0.10)
--shadow-lg: 0 8px 40px rgba(26,26,24,0.12)
```

### Layout

**Landing page:** Three stacked sections on one scroll — Hero (logged-out only) → Showcase (dark) → Track selection (light). Max-width 1040px centered for Track selection; Showcase is full-width.

**App shell (challenge workspace):**
- Sidebar: 328px, sticky, collapsible
- Topbar: 64px, sticky, blurred backdrop
- Question page: CSS Grid `minmax(330px,400px) / minmax(0,1fr)` — left panel sticky at `top: 88px`
- Mobile breakpoint: 900px — sidebar becomes fixed overlay
- Container max-width: 1180px centered

**Sample page topbar:** Three-column, full-width (`max-width: none`) — Left: home link · Center: back arrow + label · Right: CTA.

**Question page chrome:** No section kickers. Compact uppercase status line (difficulty / position / open count). Editor topbar single-line. Editor footer buttons-only, right-aligned on desktop, sticky dock on mobile. Post-submit: `.submit-outcome` wrapper groups verdict + feedback.

### Editor pane

Always dark. `#1e1e1e` background (Monaco `vs-dark`).
- Theme: `vs-dark`
- Font: JetBrains Mono, 14px
- No minimap, word wrap on, tab size 2

### Showcase card anatomy

4 cards in `.landing-showcase-grid` (flex row, `align-items: stretch`):
- Inactive: `opacity 0.38`, `flex-grow 1`, `min-height 300px`
- Active (`.is-active`): `opacity 1`, `flex-grow 2.4`, `height 510px`, `translateY(-6px)`, colored glow border via `--active-color`
- Code block: Geist Mono weight 300, `height 360px` on active, typing animation + cursor blink
- Auto-advances through all 4 tracks; responsive: 2×2 at 960px, column at 560px

---

## Phase 2: Mock interview mode

### New routes

| Path | Component | Auth |
|---|---|---|
| `/mock` | `MockHub` | Required (registered users only) |
| `/mock/:id` | `MockSession` | Required |

`AuthRequired` wrapper in `App.js` redirects unauthenticated and anonymous users (`user.email === null`) to `/auth`.

### MockHub (`pages/MockHub.js`)

Self-contained page with its own topbar (Practice dropdown + Mock link + Dashboard + theme toggle). Does not use `AppShell`.

**State:** `mode` ('30min'/'60min'/'custom'), `track`, `difficulty`, `numQuestions`, `timeMinutes`, `history[]`.

**Flow:** Select mode/track/difficulty → `POST /api/mock/start` → navigate to `/mock/:id` passing `sessionData` via router state.

**Layout:** Mode cards (3) → config pills (track + difficulty) → custom controls (if mode=custom) → Start button → recent sessions table.

### MockSession (`pages/MockSession.js`)

Full-screen layout. Does not use `AppShell`. Has two states:

**Active state:**
- Custom topbar: `[◀ Exit] [Q1• Q2○ Q3○] [MM:SS timer] [End session]`
- Body: 280px left panel (question description/schema + concepts) | flex-grow right panel (editor + run/submit)
- Timer: countdown from `time_limit_s`. Recomputed from `started_at` on reload. Auto-finishes when it hits zero.
- Timer CSS states: neutral → `.mock-timer--warning` (<10min) → `.mock-timer--danger` (<3min, pulsing)

**Summary state (after finish):**
- Score card: X/Y solved, time used
- Per-question rows: title · solved badge · time spent · collapsible solution
- Share CTA → `navigator.clipboard.writeText(...)`
- "New mock interview" → `/mock`

**Reload recovery:** On mount, if no `location.state.sessionData`, fetches `GET /api/mock/:id`. Computes `remainingS = time_limit_s - elapsed_since_started_at`.

### Navigation changes

**AppShell topbar:** Track links moved into a `nav-dropdown` "Practice ▾" dropdown. "Mock" added as a top-level `NavLink`.

**LandingPage topbar:** "Mock" link added before "Dashboard".

**ProgressDashboard:** Mock sessions history table shown below the track grid (fetched from `GET /api/mock/history`).
