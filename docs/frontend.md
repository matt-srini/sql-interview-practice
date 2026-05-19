# Frontend

> **Navigation:** [Docs index](../README.md) · [Architecture](./architecture.md) · [Backend](./backend.md)

React 18 + React Router + Vite. Monaco editor. Axios API client. Single global stylesheet (`App.css`) with CSS custom properties. No CSS framework, no CSS modules.

---

## Route tree

Defined in `frontend/src/App.js`:

```
/                                → LandingPage (editorial landing — hero IDE, role selector, 9-track index)
/auth                            → AuthPage (register / sign in / forgot password / OAuth)
/auth/reset-password             → ResetPasswordPage (consume reset token, set new password)
/auth/verify-email               → VerifyEmailPage (consume email verification token)
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

`:topic` values: `sql` | `python` | `python-data` | `pyspark` | `data-engineering` | `data-modeling` | `statistics` | `ml-fundamentals` | `experimentation`

Active tracks (`TRACK_SLUGS`): all 9 tracks above. `ALL_TRACK_SLUGS` is the same set (no more `comingSoon` tracks).

App-level route changes now animate with a short fade-in wrapper (`.route-transition`) around the route tree.

---

## Pages

### LandingPage (`/`)

Editorial 8-section layout (Phase E redesign). All sections use the `lp-*` CSS namespace; sections animate in on scroll via `IntersectionObserver` / `.lp-reveal` (no-op for `prefers-reduced-motion`). Max-width 1040px inner wrapper (`lp-inner`) on all sections.

**Sections:**

1. **Hero** — Logged-out: 2-col grid with eyebrow, large headline, copy, CTAs ("Start thinking →" / "Find your track ↓"), and `HeroIDE` component (character-by-character SQL typing animation, result rows stream in ~55ms/row). Logged-in: 3-card strip (Resume / Dashboard / Mock) using `.lp-li-card`.
2. **Thesis** — 3-column editorial with mono index numbers: "Recognition ≠ reasoning" · "Depth, not breadth" · "Real engines".
3. **Wrong / Right** — 2-col diff table; right column rows stagger in on intersection.
4. **Role Selector** — `role="tablist"` with 4 tabs (Data Analyst · Data Engineer · Analytics Engineer · Data Scientist). Each panel shows an ordered list of relevant tracks as cards (left 3px border in track color via inline style). Coming-soon tracks display a `lp-badge-soon` badge and no CTA link. Arrow-key keyboard navigation.
5. **Proof Strip** — Stat row: N tracks · N+ questions. Question count uses `useCountUp(target, 900, inView)` rAF animation on scroll.
6. **Tracks Index** — Dense list of all 9 tracks from `ALL_TRACK_SLUGS` (all live). Per-row: color dot, name, description, question count, format tagline, "Enter →" link. `.lp-track-enter` link colored with track's CSS color.
7. **Guided Progressions** — Fetches `/api/paths`; renders `PathProgressCard` per path (same component used in TrackHub).
8. **Pricing** — Free / Pro / Elite columns with monthly + lifetime CTAs. Hidden only for `lifetime_elite` users (pro users see it to discover Elite). Reuses existing `landing-tier-*` CSS classes.

**Key internals:**
- `useInView(ref, margin)` — thin IntersectionObserver hook returning boolean
- `useCountUp(target, duration, trigger)` — rAF count-up with ease-out-cubic curve
- `HeroIDE({ reduced })` — state machine: `typing → running → streaming → done`; respects `prefers-reduced-motion`. Cycles through all tracks using the hardcoded `IDE_TRACKS` array (one entry per track with a demo question/code snippet). **`IDE_TRACKS` is NOT derived from `trackRegistry.js`** — adding a new track requires a new entry here manually.
- `Reveal({ children, delay, className })` — wrapper adding `lp-reveal` + `is-visible` on intersection
- `ROLES` config defines the 4 role tab entries with ordered `tracks[]` slugs and role tagline — also hardcoded, must be updated when a new track is added
- `trackRegistry.js`: `TRACK_SLUGS` (active non-comingSoon tracks, for routing/catalog/mock) and `ALL_TRACK_SLUGS` (all tracks including coming-soon, for landing tracks index and proof strip count)

### AuthPage (`/auth`)

Register or sign in. Supports email/password, provider-gated Google/GitHub OAuth, magic-link request, and a "Forgot password?" flow that sends a reset email. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress merges into an existing account.

**Signup form:** includes a `passwordConfirm` field with inline blur-validation ("Passwords do not match") and disabled submit when there's a mismatch. Success message includes spam-folder guidance and 24h link expiry note.

**OAuth buttons:** rendered only for providers returned by `GET /api/config` (`oauth_providers`). Clicking a provider button calls `/api/auth/oauth/{provider}/authorize` and redirects the browser to the provider URL.

**Magic-link UX:** submitting in `mode=magic` always shows a non-enumerating success message. In non-production environments without email delivery configured, backend may return a `dev_magic_link` and the page renders a direct developer-only callback link.

### ResetPasswordPage (`/auth/reset-password`)

Consumes a password reset token (passed as `?token=…` query param) and lets the user set a new password. Redirects to `/auth` on success or if the token is invalid/expired.

### VerifyEmailPage (`/auth/verify-email`)

Consumes an email verification token (`?token=…`). On error (expired/invalid), shows a message noting the 24h expiry, spam-folder guidance, and a direct "Resend verification email" button (calls `/api/auth/resend-verification`) if the user is currently signed in. Logged-out users in the error state see "Sign in to resend" footer link.

### Policy pages (`/privacy`, `/terms`, `/refund-policy`, `/contact`)

Policy pages render as standalone screens when visited directly (minimal topbar, centered card, scroll-to-top on mount). When opened from the landing footer, they appear in a modal overlay that preserves the background route; the top-right close and footer "Close" button return to the previous view instead of redirecting to `/`.



Per-track landing rendered by `Outlet` when no question is active:
- Track name + overall solved/total progress bar
- Per-difficulty breakdown (easy/medium/hard bars)
- Mixed-form reasoning tracks now show a compact `What you'll practice` strip in the header with the most common question-form labels for that catalog, so users can see variants like `Scenario`, `Debug`, `Predict output`, or `Numerical` before entering the workspace.
- "Continue where I left off" button → navigates to next unlocked question
- Learning paths section: paths are sorted by role order (starter → intermediate → advanced) with incomplete paths before complete ones. The first incomplete accessible path gets a contextual `recommendationLabel` ("Start here" for an unstarted starter, "Continue" for an in-progress path, "Recommended next" for any other). Up to 2 paths shown; "View all N →" link to `/learn/:topic` when there are more.

Uses `useCatalog()` for question/progress data.

### QuestionPage (`/practice/:topic/questions/:id`)

Main practice screen. Layout and behavior vary by modality and topic:

| Track / modality slice | Editor | Left panel | Result area |
|---|---|---|---|
| SQL | Monaco (sql) | Schema viewer | ResultsTable (run + submit) |
| Python / numerical Statistics | Monaco (python) | Description only | TestCasePanel + PrintOutputPanel |
| Pandas | Monaco (python) | VariablesPanel + description | ResultsTable + PrintOutputPanel |
| PySpark and other reasoning-first tracks | Read-only snippet when present, otherwise no editor | Description and prompt context | Option-based or explanation-first verdict panel |

- **SEO**: easy questions are indexable — `noindex` is omitted and a `canonical` link is injected via Helmet. Medium and hard questions retain `noindex, nofollow` because they 403 for unauthenticated crawlers. Title format: `"{Question Title} — {Track} {Primary Concept} — datathink"`.
- **Modality-aware reasoning copy**: `QuestionPage` now reads `interaction_mode` as the coarse modality family and keeps `question.type` / `question_type` for the specific prompt verb, so constructed-reasoning tracks can expose stable metadata without losing subtype-specific copy like predict, debug, or scenario.
- **Question-form badge**: when a question exposes `type` / `question_type` metadata, the header now shows a compact badge like `Debug`, `Scenario`, `Predict output`, or `Numerical` next to the difficulty pill so the interaction model is visible before the user starts reading.
- **Prompt-guidance strip**: reasoning-first and code-adjacent MCQ prompts now render a compact guidance block under the header that spells out the modality family, the exact task, and what evidence to inspect before answering.
- **Code-adjacent evidence layout**: when a reasoning prompt includes a code snippet and/or observed output, `QuestionPage` groups those artifacts into an explicit evidence stack with labeled cards so code-adjacent prompts feel like diagnosis/prediction work rather than generic MCQ copy.
- Compact status line in question header (difficulty / question position / open count)
- On mobile, question actions use a low-profile sticky dock for Run / Submit controls
- On correct: `refresh()` updates catalog context so sidebar reflects new unlock state
- "Next Question" navigates to `/practice/:topic/questions/:nextId`
- **Delta hint** (SQL only, wrong submissions): client-side row/column diff shows a targeted message — e.g. "Your output has 3 more rows than expected. Check for a missing filter or a JOIN that multiplies rows."
- **Verdict insight line**: on first-attempt correct solve shows "First-attempt solve — the system logged your approach"; on 3+ attempts shows an encouraging note
- **Milestone toasts**: correct solves now trigger lightweight in-app toasts for first-try solves, newly unlocked questions, and streak milestones (`3/7/14/30/60/100` days)
- **First-solve celebration motion**: the verdict block gets a one-shot celebration animation on first-attempt correct submissions
- **Writing notes auto-expand**: the Solution Analysis section (`solutionAnalysisOpen`) auto-expands on a first-attempt correct solve
- Submission history fetched with `limit: 20`; `priorAttemptCountRef` tracks attempt count before each submit to compute insight text
- **Path context**: when `?path=slug` is in the URL, fetches path data and shows a path nav bar (breadcrumb + position counter + prev/next links)
- **Path context persistence**: sidebar question links preserve `?path=slug` so breadcrumb/path nav remains active while moving within a path.
- **Keyboard shortcuts** (wired via Monaco `onMount` / `editor.addCommand`; refs prevent stale-closure bugs):
  - `Cmd/Ctrl + Enter` → Run Query / Run Code (safe, reversible; guarded by `running`, `submitting`, `isLocked`, `meta.hasRunCode`)
  - `Cmd/Ctrl + Shift + Enter` → Submit Answer (permanent; guarded by `running`, `submitting`, `isLocked`)
  - Not active for non-executable questions — no editor is rendered on reasoning-first tracks
- **Shortcut affordance + help popover**: Run/Submit buttons show inline `<kbd>` badges (`⌘↵`, `⌘⇧↵`) and editor chrome includes a `?` shortcut-help toggle. Pressing `?` outside editable fields opens/closes the same popover.
- **Accessibility baseline hardening**: a shared focus-visible ring style now covers interactive controls (`a`, `button`, form inputs, tab controls, role-button surfaces), sidebar filter controls were refactored to avoid nested buttons, and mobile sidebar backdrop dismissal is keyboard reachable (Enter/Space).
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
- **Cell-level wrong-answer diff**: on wrong SQL/Pandas submissions, `ResultsTable` in "Your Output" highlights mismatched cells (red) and extra rows (amber) using `diffMode`/`expectedColumns`/`expectedRows` props. A diff summary badge above the table shows mismatch count, extra rows, and missing rows at a glance.
- **Progressive hints reveal**: hints are revealed one at a time in a stepwise card. Multi-hint questions now use difficulty-aware labels (`Mental model`, `Core pattern`, `Decomposition`, etc.) derived from the question difficulty and hint count, while single-hint questions render as a simple `Guiding hint` reveal so the UI does not imply a missing ladder. The soft gate on solution reveal remains: all hints must be exhausted before the solution can be shown.
- **SQL schema autocomplete**: on SQL questions, a Monaco completion provider is registered when the editor mounts and updated when the question changes. It suggests table names and column names from `question.schema`, with dot-context (`table.col`) awareness.
- **SQL formatter**: `Cmd/Ctrl + Shift + F` formats the editor SQL via `sql-formatter` with the `duckdb` dialect.
- **Font-size persistence**: `Cmd/Ctrl + =` / `Cmd/Ctrl + -` adjust editor font size (range 11–24 px, default 14); persisted in `localStorage` under `editor-font-size`; the same value is passed to the `fontSize` prop of `CodeEditor`. A/+ and A/- buttons also appear in the editor topbar.
- **Run history**: each "Run Query/Run Code" call prepends the code to a per-question history (up to 20 entries) stored in `sessionStorage` under `run-history:{topic}:{id}`. A `↑` button in the editor topbar opens a history popover; clicking an entry loads it into the editor.
- **Resizable split pane**: a `split-divider` element between the left description panel and the right editor panel allows drag-to-resize. Left panel width defaults to 380 px (range 260–620), persisted in `localStorage` under `split-pane-width`. Double-clicking the divider resets to default. On mobile (≤ 980 px), the divider is hidden and the layout collapses to single-column.
- **Focus mode**: when `?focus=1` is in the URL, AppShell automatically collapses the sidebar. A "⊞ Focus" / "⊡ Focus" toggle pill in the workspace topbar adds/removes the param. This narrows the workspace to just the editor + question panel.
- **Session goal widget**: a small widget in the sidebar bottom tracks "questions solved this session" against a user-set target (1–20, default 5, stored in `localStorage` under `session-goal`). Session baseline is captured once from `catalog` on mount and stored in `sessionStorage` under `session-start-solved`. The widget shows a progress bar and a "Goal reached" message when the target is met.

### SampleQuestionPage (`/sample/:topic/:difficulty`)

Standalone sample practice. No sidebar. No effect on challenge progression.

**Topbar** — three-column, full-width:
- Left: `datathink` home link
- Center: `←` back arrow (`<a href="/#landing-tracks">`) + track + difficulty label
- Right: "Start the challenge" CTA → `/practice/:topic`

Has the same **keyboard shortcuts** and **editor height toggle** as `QuestionPage` (same implementation pattern — refs for stale-closure safety, `localStorage` persistence). No `isLocked` guard since sample questions are always accessible.

Sample editor drafts are auto-saved per sample question key (`sample-draft:{topic}:{difficulty}:{questionId}`), restored on load, and can be cleared from the editor topbar.

Loading state now renders a skeleton card instead of plain text while fetching a sample question.

### ProgressDashboard (`/dashboard`)

Cross-track progress overview. Fetches `GET /api/dashboard`, `GET /api/dashboard/insights`, and `GET /api/mock/history` on mount.

- Renders one overview card per active track (all 9 tracks), not just the original executable slice.
- Returning users see an `InsightStrip` with 3 tiles: cross-track coaching sentence, streak days, weakest concept. The weakest concept tile shows a `summary` coaching sentence (from the insights payload), a primary link to the recommended learning path when `recommended_path_slug` is present ("Study in {title} →"), and a secondary "Practice a question →" link to the first unsolved `recommended_question_ids` entry.
- Track cards now include `median_solve_seconds` and `accuracy_pct` rows from `/api/dashboard/insights`.
- New users (no solves yet) see a dedicated empty state with CTAs into practice and learning paths.
- `by_difficulty` still renders as "X/Y" counts per difficulty level (`{ solved, total }` objects, not plain integers).
- Loading state now uses reusable skeleton tiles and cards instead of plain text.

### LearningPathsIndex (`/learn`, `/learn/:topic`)

Index of all learning paths. Grouped by track. Topic-filter pills narrow to a single track when `:topic` is present in the URL. Each path shown as a card with title, description, solved count, and a link to the path.

Current catalog footprint shown on this page: **42 paths total** (SQL 9, Python 6, Pandas 5, PySpark 5, Data Engineering 2, Data Modeling 4, Statistics 3, ML Fundamentals 4, Experimentation 4).

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
| CodeEditor | `components/CodeEditor.js` | Language-agnostic Monaco editor (`language`, `height`, `fontSize`, `onMount`, `ariaLabel` props; always dark theme) |
| SQLEditor | `components/SQLEditor.js` | Thin re-export of CodeEditor with `language="sql"` (backward compat) |
| ResultsTable | `components/ResultsTable.js` | Tabular results with sticky headers, horizontal overflow cue, null value rendering, and optional `diffMode` for cell-level diff highlighting |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema with client-side search and click-to-copy column tokens |
| TestCasePanel | `components/TestCasePanel.js` | Python test case results (pass/fail per case, input/expected/actual, hidden summary) |
| PrintOutputPanel | `components/PrintOutputPanel.js` | Captured stdout block (rendered only if non-empty) |
| VariablesPanel | `components/VariablesPanel.js` | Available DataFrame variables with CSV source and column list |
| MCQPanel | `components/MCQPanel.js` | Radio-button response panel with configurable explanation/lock copy; still used for option-based reasoning tracks |
| ConceptPanel | `components/ConceptPanel.js` | Slide-in concept detail panel opened from concept pills on `QuestionPage` |
| InsightStrip | `components/InsightStrip.js` | Dashboard coaching strip: cross-track insight, streak tile, weakest concept tile. Weakest concept tile shows a coaching `summary` sentence, a primary path link ("Study in …") when `recommended_path_slug` is present, and a secondary "Practice a question →" link from `recommended_question_ids`. |
| Skeleton | `components/Skeleton.js` | Reusable shimmer primitive (`skeleton-block` + `skeleton-shimmer`) used in QuestionPage, SidebarNav, TrackHubPage, ProgressDashboard |
| TrackProgressBar | `components/TrackProgressBar.js` | Reusable horizontal progress bar with configurable color and label |
| PathProgressCard | `components/PathProgressCard.js` | Path card with track color dot, progress bar, and CTA; used on LandingPage and TrackHubPage. Accepts optional `recommendationLabel` prop that replaces the tier badge with a contextual label ("Start here", "Recommended next", "Continue"). |
| OnboardingTooltip | `components/OnboardingTooltip.js` | First-visit, target-anchored walkthrough tooltip with Back/Next/Skip and Esc-to-close support |
| Topbar | `components/Topbar.js` | Single unified top nav used by every page (landing, auth, 404, practice workspace, mock, dashboard, learning paths). Composition slots for `leftSlot`, `centerSlot`, `userExtras`, `belowTopbar`; three variants: `'landing'` (default, container-bounded), `'app'` (full-bleed workspace chrome), `'minimal'` (auth / verify / reset / 404 — brand + theme + user pill only). `showPricingLink` for logged-out visitors. The brand mark now uses the bar lockup assets from `frontend/public/branding/` (`lockup-bar-no-bg.svg` / `lockup-bar-reverse-no-bg.svg`) and always resolves to the top of the landing page. `lockup-bar-no-bg.svg` uses D `#5B6AF0` with bar `#242a60`; `lockup-bar-reverse-no-bg.svg` uses D `#FFFFFF` with bar `#5B6AF0`. |
| ToastViewport | `components/ToastViewport.js` | Global in-app toast stack (first-solve, unlock, and streak milestone feedback) rendered by `ToastProvider` |
| LoggedInWelcome | `components/LoggedInWelcome.js` | Welcome-back block on `/` for authenticated users. Three cards: Resume (last-solved question via `/api/dashboard` recent_activity), Dashboard, Mock. Replaces the marketing hero for returning users. |
| TierBanner | `components/TierBanner.js` | Inline upgrade prompt shown when a user hits a plan gate (e.g. locked hard questions); renders contextual copy and upgrade CTA |
| UpgradeButton | `components/UpgradeButton.js` | Reusable upgrade CTA button; opens Stripe Checkout for the target plan tier |

### AppShell

- Uses the shared `<Topbar variant="app" />` component (no inline topbar JSX). Passes these slots:
  - `leftSlot` — hamburger sidebar toggle on mobile (`<900px`)
  - `centerSlot` — mode pill (`.shell-pill-mode`), e.g. "SQL · Challenge" / "Python · Path"; hidden when at the TrackHub
  - `userExtras` — focus mode toggle pill (`.shell-pill-focus`), streak pill (`.shell-pill-streak`) and plan pill (`.shell-pill-plan-free/pro/elite`)
  - `belowTopbar` — upgrade confirmation / error banner
- Desktop: sidebar 328px, collapsible; toggle is a `‹` icon button (`.sidebar-collapse-btn`); a `›` expand button (`.sidebar-expand-btn`) appears in the content area when collapsed
- Mobile (<900px): sidebar becomes fixed overlay with backdrop; hamburger button in topbar
- **Focus mode**: reading `?focus=1` from the URL auto-collapses the sidebar; the focus toggle pill in the topbar adds/removes the param.
- **Session goal widget**: shown in the sidebar for logged-in users. Tracks questions solved since the session started (captured once from catalog, stored in `sessionStorage`). Goal is adjustable (1–20), stored in `localStorage`.
- Upgrade panel shown for `free` and `pro` plan users; lives in the sidebar beneath the question list
- Unlock nudge message shown in sidebar for free-plan users who have locked questions
- Unlock nudge message is track-aware and mirrors `backend/unlock.py` thresholds (code tracks vs. PySpark)

### SidebarNav

Accepts a `plan` prop (passed from AppShell) to drive progressive unlock behavior for free-plan users:

- Collapsible difficulty groups
- Per-question state: `unlocked`, `locked`, `solved`, `next`, `current`
- NavLinks point to `/practice/${topic}/questions/${id}` (topic from `useTopic()`)
- Reasoning-heavy tracks now render a compact question-form badge in each row when the catalog includes additive `type` metadata, so users can tell `Debug` from `Scenario` or `Predict output` without opening the prompt.
- Sidebar filters now include a `Filter by question form` chip group when a catalog contains more than one distinct form label, letting users narrow reasoning-heavy banks by variants like `Debug`, `Scenario`, `Predict output`, or `Numerical`.
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
  tagline: 'pandas · numpy · data wrangling',
}
```

`TopicProvider` reads `:topic` from URL params via `useParams()`. `useTopic()` returns `{ topic, meta }`.

**Track registry (`frontend/src/trackRegistry.js`):** Single source of truth for all track metadata (`TRACK_META`). Adding a track here is the only frontend change needed — catalog paths, sidebar, TrackHub, and SidebarNav all read from it. Current tracks: `sql`, `python`, `python-data`, `pyspark`, `data-engineering`, `data-modeling`, `statistics`, `ml-fundamentals`, `experimentation`.

`data-engineering` entry: `color: '#B9762B'`, `hasMCQ: true`, `hasRunCode: false`, `apiPrefix: '/data-engineering'`.

`statistics` entry: `color: '#7A5AF0'`, `hasMCQ: true`, `hasRunCode: true`, `mixedSubtype: true`, `apiPrefix: '/statistics'`, `language: 'python'`. The `mixedSubtype: true` flag tells `QuestionPage.js` to derive `renderMode` from `question.subtype` at runtime rather than using the static `hasMCQ` flag — enabling a single page to render both conceptual reasoning and executable numerical questions.

Reasoning-first practice now reads additive `interaction_mode` metadata across PySpark, Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and Statistics. `QuestionPage` keeps `question.type` / `question_type` separate so headings, header guidance, and submit labels can still distinguish predict-output, debug, optimization, and scenario variants even when multiple question forms share the same modality family.

### `catalogContext.js`

Fetches catalog for the current topic on mount. URL determined by `useTopic()` using each track's `apiPrefix` from the registry:
- `sql` → `/catalog`
- `python` → `/python/catalog`
- `python-data` → `/python-data/catalog`
- `pyspark` → `/pyspark/catalog`
- `data-engineering` → `/data-engineering/catalog`

Exposes `{ catalog, loading, error, refresh }`. Resets when topic changes.

### `contexts/AuthContext.js`

Provides `{ user, loading, login, register, logout, requestMagicLink, refreshUser }`. Fetches `/api/auth/me` on mount.

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

### PySpark reasoning
1. `/practice/pyspark/questions/:id` → fetch `/api/pyspark/questions/:id`
2. MCQPanel shows options (+ code_snippet if present)
3. User selects option → click Submit → `POST /api/pyspark/submit`
4. Response `{ correct, explanation }` → MCQPanel highlights correct/wrong + reveals explanation
5. No Run button, no code editor

### Reasoning-first tracks
1. `/practice/:topic/questions/:id` → fetch topic-specific question detail for Data Engineering, Data Modeling, ML Fundamentals, Experimentation, or conceptual Statistics
2. Prompt renders the stem, supporting context, and option or scenario UI without pretending the task is executable
3. Submit → topic-specific submit endpoint returns verdict + explanation
4. No `Run` affordance unless the question's modality is executable

### Sample flow
1. `/sample/:topic/:difficulty` → `GET /api/sample/:topic/:difficulty`
2. Backend marks that topic+difficulty sample as seen, returns next sample question
3. Run/submit uses topic-specific sample endpoints
4. 409 on exhaustion → reset button → `POST /api/sample/:topic/:difficulty/reset` → re-fetch
5. No effect on challenge progress

---

## Observability

### Sentry (error capture)

Initialized in `index.js` when `VITE_SENTRY_DSN` is available. In local dev it comes from Vite env; in the deployed single-service app it is injected at request time into `window.__APP_CONFIG__` by `routers/spa.py`. Uses `@sentry/react` with:
- Browser tracing (10% sample rate)
- Session Replay on errors (100% of error sessions, 0% baseline)
- `ErrorBoundary.js` calls `Sentry.captureException()` on component crashes

### PostHog (product analytics)

Initialized via `analytics.js` when `VITE_POSTHOG_KEY` is available. In local dev it comes from Vite env; in the deployed single-service app it is injected at request time into `window.__APP_CONFIG__` by `routers/spa.py`. All calls no-op when the key is absent.

**Identity lifecycle:** `identifyUser()` on session restore / login / register; `resetIdentity()` on logout.

**SPA page views:** Tracked on every route change via `RouteTransition` in `App.js`.

**Key events:**

| Event | Location | Properties |
|---|---|---|
| `question_submitted` | QuestionPage | `track`, `question_id`, `difficulty`, `correct` |
| `question_solved` | QuestionPage | `track`, `question_id`, `difficulty`, `first_try` |
| `sample_submitted` | SampleQuestionPage | `track`, `difficulty`, `question_id`, `correct` |
| `mock_started` | MockHub | `mode`, `track`, `difficulty`, `session_id` |
| `mock_completed` | MockSession | `session_id`, `score`, `total`, `track` |
| `plan_upgrade_started` | UpgradeButton | `tier`, `source` |
| `plan_upgraded` | UpgradeButton | `tier`, `source` |

**Funnel:** Landing → Track selection → First question → First solve → Registration → Plan upgrade.

**Production sourcemaps:** `vite.config.js` emits hidden sourcemaps for production builds. If `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are provided during build, `@sentry/vite-plugin` uploads them automatically.

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Philosophy:** Professional tool aesthetic — calm, fast, distraction-free. Designed for long sessions (30–90 min). Light mode primary, warm dark mode driven by the `[data-theme="dark"]` attribute. A bootstrap script in `index.html` sets `data-theme` pre-mount from `localStorage.theme` (explicit choice) or `matchMedia('(prefers-color-scheme: dark)')` (system default) — prevents theme-flash on first paint. The SQL editor pane always uses a dark background (`#1e1e1e`) regardless of scheme — intentional two-tone split.

### Color tokens

**Active theme: Forest & Ink.** Full token table with all values: [`docs/design/color-palette.md`](../design/color-palette.md).

Defined in `:root` in `App.css`. Dark-mode overrides under `[data-theme="dark"]`; light-mode force under `[data-theme="light"]`. Theme managed by `ThemeProvider` in `App.js` (`{ theme, setTheme, isDark, cycleTheme, themeIcon, themeLabel }`), persisted to `localStorage.theme`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg-page` | `#F5F7F4` | `#0D1A10` | Page background |
| `--surface-card` | `#FFFFFF` | `#132218` | Cards, panels |
| `--surface-card-alt` | `#EDF3EF` | `#1B2E22` | Sidebar, secondary surfaces |
| `--border-subtle` | `rgba(20,41,27,0.08)` | `rgba(200,230,210,0.08)` | Default borders |
| `--text-strong` | `#14291B` | `#E8F5E9` | Headings |
| `--text-primary` | `#1D3526` | `#C8DFD0` | Body text |
| `--text-secondary` | `#4B6858` | `#87B09A` | Labels, metadata |
| `--text-muted` | `#7A9485` | `#5A7F6A` | Placeholders, disabled |
| `--accent` | `#166534` | `#4ADE80` | Interactive elements, links |
| `--success` | `#15803D` | `#4CAF82` | Correct answer |
| `--warning` | `#C47F17` | `#D4973A` | Hints, locked |
| `--danger` | `#D94F3D` | `#E06B5A` | Errors, wrong answer |

Track colors (`--track-sql`, `--track-python`, etc.) are **fixed** and do not change with the site theme — see palette doc for values.

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

**Sample page topbar:** Three-column, full-width (`max-width: none`) — Left: home link using the bar branding asset · Center: back arrow + label · Right: CTA.

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

**State:** `mode` (`'benchmark'/'30min'/'custom'` plus legacy `'60min'` labels in history), `track`, `difficulty`, `numQuestions`, `timeMinutes`, `history[]`.

**Flow:** Select mode/track/difficulty → `POST /api/mock/start` → navigate to `/mock/:id` passing `sessionData` via router state.

**Layout:** Benchmark/drill mode cards (3) → track-specific benchmark blueprint card when `mode='benchmark'` or dedicated drill planner card when `mode!='benchmark'` → config pills (track + difficulty) → Start button → benchmark analytics panel → split recent benchmark/drill history tables.

- MockHub hero now frames `/mock` explicitly as a benchmarks-and-drills surface instead of a generic mock page, which is the first visible Phase 5 drill split cue.
- The Data Engineer role filter now includes Data Modeling, matching the canonical role mapping used elsewhere in the product.
- Benchmark is now the default starting mode on single-track sessions and is presented as the fixed-shape, serious mock.
- Sprint drill (`30min`) and Custom drill are the flexible follow-up modes.
- Drill modes now render a dedicated planner card with the session shape, purpose, and inline custom controls so drills read as a separate setup surface instead of just alternate mode cards.
- Mixed track is drill-only; when users switch to Mixed, MockHub automatically exits benchmark mode and explains why.
- Elite analytics now use `benchmark_summary` as the comparable primary view and surface drill performance in a smaller secondary card.
- History rows format stored mode values into human labels (`Benchmark`, `Sprint drill`, `Custom drill`, `Full (legacy)`) so older sessions stay legible without preserving the old setup framing, and the tables are split into `Recent benchmark sessions` and `Recent drill sessions`.

When no history exists, shows a richer empty state with warm-up and dashboard CTAs.

### MockSession (`pages/MockSession.js`)

Full-screen layout. Does not use `AppShell`. Has two states:

**Active state:**
- Custom topbar: `[◀ Exit] [Q1• Q2○ Q3○] [MM:SS timer] [End session]`
- Left panel now opens with a session-context card that makes the current mode explicit: benchmark sessions show a fixed-shape benchmark badge, shape summary, and track-specific benchmark framing; drills show flexible drill framing instead.
- Body: 280px left panel (question description/schema + concepts) | flex-grow right panel (editor + run/submit)
- Timer: countdown from `time_limit_s`. Recomputed from `started_at` on reload. Auto-finishes when it hits zero.
- Timer CSS states: neutral → `.mock-timer--warning` (<10min) → `.mock-timer--danger` (<3min, pulsing)

**Summary state (after finish):**
- Summary topbar and intro card now distinguish `Benchmark summary` vs `Drill summary`, show the human-readable mode label, and restate the session shape before the score block.
- Score card: `X/Y correct, Z% above/below your session average` (comparison against `GET /api/dashboard/insights` track accuracy baseline), plus time used
- Per-concept session accuracy row (`correct/attempts`) built from concepts touched in this mock
- "Drill weak concepts" CTA to `/practice/{track}?concepts={slug1,slug2}`
- Per-question rows: title · solved badge · time spent · collapsible solution
- Share CTA → `navigator.clipboard.writeText(...)`, now prefixed with the human-readable mode label
- Primary CTA returns to `/mock` as `Start another benchmark` or `Start another drill` depending on the completed session mode

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
| ProgressDashboard unit | `src/pages/ProgressDashboard.test.js` | Legacy regression coverage for the original 4-track dashboard slice, plus X/Y count rendering, loading/error states, and guard against the older plain-int API shape |
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
