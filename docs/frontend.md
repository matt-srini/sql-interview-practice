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

Four stacked sections on a single scroll:

1. **Hero / Welcome** — logged-out: centered headline, tagline, CTAs ("Explore tracks ↓" and "Create account"). Logged-in: `LoggedInWelcome` component with Resume, Dashboard, and Mock cards.
2. **Proof + showcase + companies** — `.landing-proof-row`, `.landing-showcase`, and `.landing-companies` are rendered only for logged-out visitors. The showcase is the same Interview IDE module (always-dark editor) and now respects `prefers-reduced-motion` at initial render plus media-query changes.
3. **Track selection** (`.landing-practice-section`, `id="landing-tracks"`) — pill nav selects a track; panel shows description, progress bar, CTA, and easy/medium/hard sample tiles. Mobile sample tiles use horizontal scroll.
4. **Pricing** (`id="landing-pricing"`) — three-column tier table with hard question counts derived from `TOTAL_EASY` / `TOTAL_QUESTIONS` constants. Free: 129 easy questions. Pro: all 350 questions + 3 mocks/day. Elite: everything + company filter + unlimited mocks. Hidden for `lifetime_elite` users.

`TRACK_DIFFICULTIES` mirrors the real per-track/difficulty question counts (32/34/29 SQL, 30/29/24 Python, 29/30/23 Pandas, 38/30/22 PySpark). `TOTAL_EASY` and `TOTAL_QUESTIONS` are derived totals used in pricing copy.

Landing consistency updates: unified landing widths (720 / 1040), `.landing-tier-inner` deduplicated, all landing border tokens normalized to `var(--border-subtle)`, company chips rendered as non-interactive spans, and active landing tab persistence stored in `localStorage` (`landingActiveTab`). The practice-track section now uses neutral card surfaces with per-track gradient hover/active highlights on the four track tiles (no left accent rail), plus fully opaque accent rails on sample strips and sample tiles, and opaque surface-mixed difficulty chips instead of tinted card fills.

On mount, checks `window.location.hash` and scrolls to the matching element (used by the sample page back arrow → `/#landing-tracks`).

### AuthPage (`/auth`)

Register or sign in. Supports email/password, Google OAuth (coming soon), and GitHub OAuth (coming soon). Also contains a "Forgot password?" flow that sends a reset email. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress merges into an existing account.

**Signup form:** includes a `passwordConfirm` field with inline blur-validation ("Passwords do not match") and disabled submit when there's a mismatch. Success message includes spam-folder guidance and 24h link expiry note.

**OAuth buttons:** rendered with a "Soon" badge and `opacity: 0.65` via `.auth-oauth-btn--coming-soon`; `disabled` attribute not used to preserve hover affordance.

### ResetPasswordPage (`/auth/reset-password`)

Consumes a password reset token (passed as `?token=…` query param) and lets the user set a new password. Redirects to `/auth` on success or if the token is invalid/expired.

### VerifyEmailPage (`/auth/verify-email`)

Consumes an email verification token (`?token=…`). On error (expired/invalid), shows a message noting the 24h expiry, spam-folder guidance, and a direct "Resend verification email" button (calls `/api/auth/resend-verification`) if the user is currently signed in. Logged-out users in the error state see "Sign in to resend" footer link.



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
- **Path context persistence**: sidebar question links preserve `?path=slug` so breadcrumb/path nav remains active while moving within a path.
- **Keyboard shortcuts** (wired via Monaco `onMount` / `editor.addCommand`; refs prevent stale-closure bugs):
  - `Cmd/Ctrl + Enter` → Run Query / Run Code (safe, reversible; guarded by `running`, `submitting`, `isLocked`, `meta.hasRunCode`)
  - `Cmd/Ctrl + Shift + Enter` → Submit Answer (permanent; guarded by `running`, `submitting`, `isLocked`)
  - Not active for MCQ (PySpark) questions — no editor is rendered
- **Shortcut affordance + help popover**: Run/Submit buttons show inline `<kbd>` badges (`⌘↵`, `⌘⇧↵`) and editor chrome includes a `?` shortcut-help toggle. Pressing `?` outside editable fields opens/closes the same popover.
- **Editor height toggle** (`⊞`/`⊟` button in the editor topbar): switches Monaco between 340 px (default) and 560 px. Preference is persisted to `localStorage` under the key `editor-height-pref`.
- **Draft autosave**: editor content is debounced to `localStorage` under `draft:{topic}:{questionId}` and restored silently on load; editor chrome shows "Saving draft…" / "Draft saved" state and includes a clear-draft control.
- **Per-question soft timer**: editor topbar shows elapsed time; timer pauses on tab blur / hidden state and resumes on focus; `duration_ms` is attached on submit payloads and returned in submission history when available.
- **Question bookmarks**: header toggle stores bookmarks in `localStorage` (`bookmarks:{topic}`), capped at 20, and SidebarNav renders a Bookmarked section above difficulty groups.
- **Concept panel**: concept pills in the prompt are clickable and open a right-side concept explanation panel with interview example copy.
- **Similar-question recommendations**: after a correct submission, up to two unsolved questions sharing concepts are suggested in a secondary recommendation card.
- **SQL error clarity**: SQL run/submit failures pass through a client-side parser that maps common DuckDB errors (missing table/column, syntax, ambiguous refs, GROUP BY mismatch, divide-by-zero) into concise corrective hints, preserving line numbers when present.
- **Submit guard hardening**: `handleSubmit` now exits immediately when `submitting` is already true to prevent accidental double-submit races.
- **Past attempts revisit behavior**: submission history panel auto-expands when revisiting the same question as `localStorage.last_seen_question_id`.
- **Solution reveal placement**: the "Review Official Solution" control now lives in the verdict header (instead of below feedback/hints) once reveal criteria are met.
- **Submit skeleton** (SQL): while submit is in-flight, a placeholder skeleton appears where solution analysis/writing notes will render.

### SampleQuestionPage (`/sample/:topic/:difficulty`)

Standalone sample practice. No sidebar. No effect on challenge progression.

**Topbar** — three-column, full-width:
- Left: `datanest` home link
- Center: `←` back arrow (`<a href="/#landing-tracks">`) + track + difficulty label
- Right: "Start the challenge" CTA → `/practice/:topic`

Has the same **keyboard shortcuts** and **editor height toggle** as `QuestionPage` (same implementation pattern — refs for stale-closure safety, `localStorage` persistence). No `isLocked` guard since sample questions are always accessible.

Sample editor drafts are auto-saved per sample question key (`sample-draft:{topic}:{difficulty}:{questionId}`), restored on load, and can be cleared from the editor topbar.

Loading state now renders a skeleton card instead of plain text while fetching a sample question.

### ProgressDashboard (`/dashboard`)

Cross-track progress overview. Fetches `GET /api/dashboard`, `GET /api/dashboard/insights`, and `GET /api/mock/history` on mount.

- Returning users see an `InsightStrip` with 3 tiles: cross-track coaching sentence, streak days, weakest concept.
- Track cards now include `median_solve_seconds` and `accuracy_pct` rows from `/api/dashboard/insights`.
- New users (no solves yet) see a dedicated empty state with CTAs into practice and learning paths.
- `by_difficulty` still renders as "X/Y" counts per difficulty level (`{ solved, total }` objects, not plain integers).

### LearningPathsIndex (`/learn`, `/learn/:topic`)

Index of all learning paths. Grouped by track. Topic-filter pills narrow to a single track when `:topic` is present in the URL. Each path shown as a card with title, description, solved count, and a link to the path.

Current catalog footprint shown on this page: **22 paths total** (SQL 7, Python 5, Pandas 5, PySpark 5).

- Adds an "In progress" rail above the grouped grids (`1 <= solved_count < question_count`), sorted by completion percentage descending.
- Empty state upgraded from plain text to CTA card (`/practice/sql`, `/dashboard`).

### LearningPath (`/learn/:topic/:slug`)

Curated path page. Shows breadcrumb (Learn → track → path title), overall progress bar, and a question list with per-question state (solved/unlocked/locked). Each question links to `/practice/:topic/questions/:id?path=:slug` so `QuestionPage` shows the path nav bar.

When `solved_count === question_count`, a completion banner is shown with a "What's next" CTA back to the track's path index.

---

## Components

| Component | File | Purpose |
|---|---|---|
| AppShell | `components/AppShell.js` | Challenge workspace: fixed topbar with direct track nav, collapsible sidebar |
| SidebarNav | `components/SidebarNav.js` | Question list grouped by difficulty; topic-aware NavLinks |
| CodeEditor | `components/CodeEditor.js` | Language-agnostic Monaco editor (`language`, `height`, `onMount` props; always dark theme) |
| SQLEditor | `components/SQLEditor.js` | Thin re-export of CodeEditor with `language="sql"` (backward compat) |
| ResultsTable | `components/ResultsTable.js` | Tabular results with sticky headers, horizontal overflow cue (`→ X more columns`), and null value rendering |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema with client-side search and click-to-copy column tokens |
| TestCasePanel | `components/TestCasePanel.js` | Python test case results (pass/fail per case, input/expected/actual, hidden summary) |
| PrintOutputPanel | `components/PrintOutputPanel.js` | Captured stdout block (rendered only if non-empty) |
| VariablesPanel | `components/VariablesPanel.js` | Available DataFrame variables with CSV source and column list |
| MCQPanel | `components/MCQPanel.js` | Radio-button MCQ with correct/wrong highlighting and explanation after submit |
| ConceptPanel | `components/ConceptPanel.js` | Slide-in concept detail panel opened from concept pills on `QuestionPage` |
| InsightStrip | `components/InsightStrip.js` | Dashboard coaching strip: cross-track insight, streak tile, weakest concept tile |
| TrackProgressBar | `components/TrackProgressBar.js` | Reusable horizontal progress bar with configurable color and label |
| PathProgressCard | `components/PathProgressCard.js` | Path card with track color dot, progress bar, and CTA; used on LandingPage and TrackHubPage |
| Topbar | `components/Topbar.js` | Single unified top nav used by every page (landing, auth, 404, practice workspace, mock, dashboard, learning paths). Composition slots for `leftSlot`, `centerSlot`, `userExtras`, `belowTopbar`; three variants: `'landing'` (default, container-bounded), `'app'` (full-bleed workspace chrome), `'minimal'` (auth / verify / reset / 404 — brand + theme + user pill only). `showPricingLink` for logged-out visitors. |
| LoggedInWelcome | `components/LoggedInWelcome.js` | Welcome-back block on `/` for authenticated users. Three cards: Resume (last-solved question via `/api/dashboard` recent_activity), Dashboard, Mock. Replaces the marketing hero for returning users. |
| TierBanner | `components/TierBanner.js` | Inline upgrade prompt shown when a user hits a plan gate (e.g. locked hard questions); renders contextual copy and upgrade CTA |
| UpgradeButton | `components/UpgradeButton.js` | Reusable upgrade CTA button; opens Stripe Checkout for the target plan tier |

### AppShell

- Uses the shared `<Topbar variant="app" />` component (no inline topbar JSX). Passes these slots:
  - `leftSlot` — hamburger sidebar toggle on mobile (`<900px`)
  - `centerSlot` — mode pill (`.shell-pill-mode`), e.g. "SQL · Challenge" / "Python · Path"; hidden when at the TrackHub
  - `userExtras` — streak pill (`.shell-pill-streak`) and plan pill (`.shell-pill-plan-free/pro/elite`)
  - `belowTopbar` — upgrade confirmation / error banner
- Desktop: sidebar 328px, collapsible; toggle is a `‹` icon button (`.sidebar-collapse-btn`); a `›` expand button (`.sidebar-expand-btn`) appears in the content area when collapsed
- Mobile (<900px): sidebar becomes fixed overlay with backdrop; hamburger button in topbar
- Upgrade panel shown for `free` and `pro` plan users; lives in the sidebar beneath the question list
- Unlock nudge message shown in sidebar for free-plan users who have locked questions
- Unlock nudge message is track-aware and mirrors `backend/unlock.py` thresholds (code tracks vs. PySpark)

### SidebarNav

Accepts a `plan` prop (passed from AppShell) to drive progressive unlock behavior for free-plan users:

- Collapsible difficulty groups
- Per-question state: `unlocked`, `locked`, `solved`, `next`, `current`
- NavLinks point to `/practice/${topic}/questions/${id}` (topic from `useTopic()`)
- **Progressive unlock bar** (`.sidebar-unlock-bar`): shown in difficulty group headers when there are locked questions. Displays a progress bar filling toward the next unlock threshold plus a "{N} more to unlock" label. Thresholds mirror `backend/unlock.py` (e.g. SQL/Python/Pandas medium: 8→3, 15→8, 25→all; PySpark medium: 12→3, 20→8, 30→all).
- **Locked question tooltip** (`title` attribute on the locked row `div`): explains exactly how many more solves are needed — e.g. "Solve 7 more easy questions to unlock this". Pro users see "Upgrade to Elite to unlock all hard questions" on hard rows.
- Concept filter (chip grid, most-frequent first, expand/collapse) and Company filter (SQL only)
- Fuzzy question search input (Fuse.js) over title/concepts/difficulty with inline clear control
- Supports deep-link concept drilling via `?concepts=slug1,slug2` query params on `/practice/:topic`; slugs are matched back to concept names and auto-applied as active filters.
- Bookmarked questions rail reads per-topic IDs from `localStorage` and stays in sync with QuestionPage updates via `bookmarks-updated` window events.
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
  totalQuestions: 82,          // real question count (sql=95, python=83, python-data=82, pyspark=90)
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

**Philosophy:** Professional tool aesthetic — calm, fast, distraction-free. Designed for long sessions (30–90 min). Light mode primary, warm dark mode driven by the `[data-theme="dark"]` attribute. A bootstrap script in `index.html` sets `data-theme` pre-mount from `localStorage.theme` (explicit choice) or `matchMedia('(prefers-color-scheme: dark)')` (system default) — prevents theme-flash on first paint. The SQL editor pane always uses a dark background (`#1e1e1e`) regardless of scheme — intentional two-tone split.

### Color tokens

Defined in `:root` in `App.css`. Dark-mode overrides live under `[data-theme="dark"]` selectors (single source of truth). `theme` is managed by `ThemeProvider` in `App.js` (`{ theme, setTheme, isDark, cycleTheme, themeIcon, themeLabel }`) and persisted to `localStorage.theme`.

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
| Geist Mono | 400/500 | Showcase IDE chrome, tabs, code, status bar |

### Metadata pills

Two pill variants used in question prompts:

| Class | Style | Use |
|---|---|---|
| `.tag-concept` | Neutral fill (`rgba(0,0,0,0.04)`), `--text-secondary`, subtle border | Concept/skill tags — intentionally muted so they don't compete with question text |
| `.tag-company` | Transparent bg, `--text-secondary`, `--border` | Company attribution tags |

Both are kept visually quiet — neither should draw the eye away from the question description or schema.

### Buttons

Three tiers: `.btn-primary` (accent fill, Submit), `.btn-secondary` (outlined, Run / nav), `.btn-success` (success-soft tint, Next Question).

All hover: `translateY(-1px)`, `150ms ease-out`. No transforms on disabled.

`.btn-secondary` is context-sensitive: `rgba(255,255,255,0.14)` bg inside dark editor wrapper (contrast-raised), `rgba(0,0,0,0.03)` outside.

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

**Landing page:** Three stacked sections on one scroll — Hero (logged-out only) → Showcase (theme-responsive surface, always-dark IDE) → Track selection (light). Max-width 1040px centered for Track selection; Showcase is full-width.

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

### Showcase IDE anatomy

Single `.landing-ide` window (max-width 1120px) inside `.landing-showcase`:
- **Chrome bar** — three traffic-light dots, 4 filename tabs (`.ide-tab`, `.is-active` gets track-color bottom edge + top-inset glow), and a `.ide-difficulty-pill` on the right.
- **Body** — `.ide-body-inner` is a 2fr/3fr grid: `.ide-brief` (kicker, title, meta, prose paragraph, returns note, concepts) + `.ide-code-pane` (filename header, `.ide-code-block` with `.ide-code-gutter` line numbers and syntax-highlighted `.ide-code`). Swapping tabs triggers a 350ms `ideSwap` crossfade.
- **Status bar** — language + line count on the left; 4 clickable `.ide-rotation-dot` elements on the right (active dot is filled in the track color).
- **Syntax highlighting** — `highlightCode(code, language)` from [landingShowcaseHighlight.js](frontend/src/pages/landingShowcaseHighlight.js) wraps keywords/strings/numbers/comments/function-calls in `.tok-kw / .tok-str / .tok-num / .tok-com / .tok-fn` spans. Colors shared across light/dark since the IDE is always dark.
- **Theme-responsive surface** — section tokens (`--sc-surface`, `--sc-dot`, `--sc-ink`, `--sc-ink-soft`) switch under `[data-theme="dark"]`. The IDE window itself keeps fixed dark tokens (`--sc-ide-bg`, `--sc-ide-chrome-bg`, `--sc-ide-code-bg`) in both modes.
- **Motion** — auto-rotates every 8 s when in view; pauses on pointer-enter, focus, or tab click. Fully honors `prefers-reduced-motion` (no rotation, no crossfade, no fade-in).
- **Responsive** — ≤900px: body stacks (brief above code), paragraph clamps to 3 lines. ≤560px: tabs scroll horizontally, line count hidden, gutter narrows.

---

## Phase 2: Mock interview mode

### New routes

| Path | Component | Auth |
|---|---|---|
| `/mock` | `MockHub` | Required (registered users only) |
| `/mock/:id` | `MockSession` | Required |

`AuthRequired` wrapper in `App.js` redirects unauthenticated and anonymous users (`user.email === null`) to `/auth`.

### MockHub (`pages/MockHub.js`)

Standalone page using the shared `<Topbar active="mock" />`. Does not use `AppShell`.

**State:** `mode` ('30min'/'60min'/'custom'), `track`, `difficulty`, `numQuestions`, `timeMinutes`, `history[]`.

**Flow:** Select mode/track/difficulty → `POST /api/mock/start` → navigate to `/mock/:id` passing `sessionData` via router state.

**Layout:** Mode cards (3) → config pills (track + difficulty) → custom controls (if mode=custom) → Start button → recent sessions table.

When no history exists, shows a richer empty state with warm-up and dashboard CTAs.

### MockSession (`pages/MockSession.js`)

Full-screen layout. Does not use `AppShell`. Has two states:

**Active state:**
- Custom topbar: `[◀ Exit] [Q1• Q2○ Q3○] [MM:SS timer] [End session]`
- Body: 280px left panel (question description/schema + concepts) | flex-grow right panel (editor + run/submit)
- Timer: countdown from `time_limit_s`. Recomputed from `started_at` on reload. Auto-finishes when it hits zero.
- Timer CSS states: neutral → `.mock-timer--warning` (<10min) → `.mock-timer--danger` (<3min, pulsing)

**Summary state (after finish):**
- Score card: `X/Y correct, Z% above/below your session average` (comparison against `GET /api/dashboard/insights` track accuracy baseline), plus time used
- Per-concept session accuracy row (`correct/attempts`) built from concepts touched in this mock
- "Drill weak concepts" CTA to `/practice/{track}?concepts={slug1,slug2}`
- Per-question rows: title · solved badge · time spent · collapsible solution
- Share CTA → `navigator.clipboard.writeText(...)`
- "New mock interview" → `/mock`

**Reload recovery:** On mount, if no `location.state.sessionData`, fetches `GET /api/mock/:id`. Computes `remainingS = time_limit_s - elapsed_since_started_at`.

### Navigation changes

**AppShell topbar:** Track links moved into a `nav-dropdown` "Practice ▾" dropdown. "Mock" added as a top-level `NavLink`.

**LandingPage topbar:** "Mock" link added before "Dashboard".

**ProgressDashboard:** Mock sessions history table shown below the track grid (fetched from `GET /api/mock/history`).

---

## Testing

| Suite | File | Coverage |
|---|---|---|
| SidebarNav unit | `src/components/SidebarNav.test.js` | Collapse/expand difficulty groups, locked vs unlocked question rendering, navigation |
| ProgressDashboard unit | `src/pages/ProgressDashboard.test.js` | X/Y count rendering for all 4 tracks, zero counts, loading/error states, regression guard against plain-int shape returned by older API |
| Plan-tier e2e | `e2e/plan-tiers.spec.js` | Dashboard counts, sidebar lock state, TrackHub plan banner, mock difficulty gating — verified against live dev servers for elite/pro/free plans |

**Tooling:**
- Unit tests: Vitest + React Testing Library + jsdom (`npm test`)
- E2E: Playwright 1.59 (`npx playwright test`); config in `playwright.config.js`
- E2E setup: `e2e/global-setup.js` creates one user per plan tier before the suite; credentials written to `e2e/.test-users.json` (gitignored) for reuse across all tests
- `package.json` has `"type": "module"` (required for Playwright ESM config and globalSetup)
- `vite.config.js` excludes `**/e2e/**` from Vitest so Playwright specs aren't picked up as unit tests

**Running tests:**
```bash
# Unit tests
cd frontend && npm test

# E2E (requires backend on :8000 and frontend on :5173)
cd frontend && npx playwright test
```
