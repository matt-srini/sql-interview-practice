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
/pricing                         → PricingPage (public Free/Pro/Elite feature comparison + Free-tier unlock ladders)
/mock                            → MockHub (mode/track/difficulty selector + history)  [AuthRequired]
/mock/:id                        → MockSession (active session + inline summary)        [AuthRequired]
/learn                           → LearningPathsIndex (all paths, grouped by track, topic pills)
/learn/:topic                    → LearningPathsIndex (filtered to one track)
/learn/:topic/:slug              → LearningPath (curated path — breadcrumb, progress bar, question list)
/sample                          → SampleHubPage (discovery surface — 9-track × 3-difficulty grid)
/sample/:topic/:difficulty       → SampleQuestionPage (topic-aware sample mode)
/sample/:difficulty              → redirect → /sample/sql/:difficulty (legacy)
                                   /sample/:track → /sample/:track/easy (URL-guess convenience)
/practice/:topic                 → TopicShell (TopicProvider + CatalogProvider + AppShell)
  /practice/:topic               → TrackHubPage (track overview when no question selected)
  /practice/:topic/questions/:id → QuestionPage (topic-aware)
/practice/questions/:id          → redirect → /practice/sql/questions/:id  (legacy)
/practice                        → redirect → /practice/sql
/questions/:id                   → redirect → /practice/sql/questions/:id  (legacy)
```

`:topic` values: `sql` | `python` | `pandas` | `pyspark` | `data-engineering` | `data-modeling` | `statistics` | `ml-fundamentals` | `experimentation`

Active tracks (`TRACK_SLUGS`): all 9 tracks above. `ALL_TRACK_SLUGS` is the same set (no more `comingSoon` tracks).

App-level route changes now animate with a short fade-in wrapper (`.route-transition`) around the route tree.

---

## Pages

### LandingPage (`/`)

Editorial 8-section layout (Phase E redesign). All sections use the `lp-*` CSS namespace; sections animate in on scroll via `IntersectionObserver` / `.lp-reveal` (no-op for `prefers-reduced-motion`). Max-width 1040px inner wrapper (`lp-inner`) on all sections.

**Sections:**

1. **Hero** — Logged-out: 2-col grid with interview-urgent eyebrow copy, a large headline tying interview readiness to durable on-the-job reasoning, CTAs ("Try a free sample →" / "Find your role ↓"), and `HeroIDE` component (character-by-character SQL typing animation, result rows stream in ~55ms/row). Logged-in: 3-card strip (Resume / Dashboard / Mock) using `.lp-li-card`.
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
- `HeroIDE({ reduced })` — state machine: `typing → running → streaming → done`; respects `prefers-reduced-motion`. Cycles through all tracks using the hardcoded `IDE_TRACKS` array (one entry per track with a high-signal practitioner scenario). **`IDE_TRACKS` is NOT derived from `trackRegistry.js`** — adding a new track requires a new entry here manually.
- `Reveal({ children, delay, className })` — wrapper adding `lp-reveal` + `is-visible` on intersection
- `ROLES` config defines the 4 role tab entries with ordered `tracks[]` slugs and role tagline — also hardcoded, must be updated when a new track is added
- `trackRegistry.js`: `TRACK_SLUGS` (active non-comingSoon tracks, for routing/catalog/mock) and `ALL_TRACK_SLUGS` (all tracks including coming-soon, for landing tracks index and proof strip count)
- **Logged-in home coaching** (`WeakSpotsSection`, below `ContinuePathsSection` + `YourTracksSection`): **Pro/Elite** see up to 3 weak-concept cards, each with a single *Drill this →* CTA ([concept drill](#concept-drill), `?drill=`) — kept deliberately minimal, **no path option on the landing tile** (the dashboard "Where to focus" panel is where the path secondary lives). **Free** users with weak data see an upgrade gate (`.lp-weak-spot-gate`) that never leaks concept names; free users with no data see nothing (the section is hidden). The dead, never-mounted `InsightStrip` component that once duplicated this surface was removed.

### AuthPage (`/auth`)

Register or sign in. Supports email/password, provider-gated Google/GitHub OAuth, magic-link request, and a "Forgot password?" flow that sends a reset email. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress merges into an existing account.

**Signup form:** includes a `passwordConfirm` field with inline blur-validation ("Passwords do not match") and disabled submit when there's a mismatch. Success message includes spam-folder guidance and 24h link expiry note.

**OAuth buttons:** rendered only for providers returned by `GET /api/config` (`oauth_providers`). Clicking a provider button calls `/api/auth/oauth/{provider}/authorize` and redirects the browser to the provider URL.

**Magic-link UX:** submitting in `mode=magic` always shows a non-enumerating success message. In non-production environments without email delivery configured, backend may return a `dev_magic_link` and the page renders a direct developer-only callback link.

### ResetPasswordPage (`/auth/reset-password`)

Consumes a password reset token (passed as `?token=…` query param) and lets the user set a new password. Redirects to `/auth` on success or if the token is invalid/expired.

### VerifyEmailPage (`/auth/verify-email`)

Consumes an email verification token (`?token=…`). On error (expired/invalid), shows a message noting the 24h expiry, spam-folder guidance, and a direct "Resend verification email" button (calls `/api/auth/resend-verification`) if the user is currently signed in. Logged-out users in the error state see "Sign in to resend" footer link.

### Policy pages (`/privacy`, `/terms`, `/refund-policy`, `/faq`, `/contact`)

Privacy, Terms, Refund, and FAQ render as **dedicated standalone pages** (minimal topbar, centered card, scroll-to-top on mount) — both when visited directly and when opened from the landing footer. Their footer "Back to home" button returns the user to the landing **footer**, not the top, via `<Link to="/" state={{ scrollTo: 'footer' }}>` (the `LandingPage` scroll-to-section effect honors `state.scrollTo`), so they can keep scanning the other legal links without re-scrolling.

Contact is the one exception: from the landing footer it opens in a **modal overlay** (`<Link to="/contact" state={{ backgroundLocation: location }}>`) that preserves the background route and scroll position; the top-right close and footer "Close" button return to the footer (`navigate(..., { state: { preserveScroll: true } })`) instead of jumping to the top or redirecting to `/`. Visited directly, `/contact` renders standalone with a "Back to home" that also targets the footer.

`RouteTransition` (App.js) owns scroll-to-top on route changes but skips the reset when a hash anchor is present, when a modal is open over a background page (`state.backgroundLocation`), or when a close asked to keep position (`state.preserveScroll`) — this is what lets the footer → policy → back and Contact-modal-close flows land on the footer rather than the top.

### PricingPage (`/pricing`)

Public, full-detail plan comparison (no auth gate) — the "no hiding behind short adjectives" surface. Renders entirely from a single data source, **`frontend/src/data/tierFeatures.js`** (`COMPARISON_TIERS`, `COMPARISON_GROUPS`, `FREE_UNLOCK`), so the matrix has one home and tracks the entitlement SoT (`pricing.md` / `mock.md` / `unlock.py`). Layout: tier summary cards (Pro featured, `UpgradeButton` CTAs) → grouped Free/Pro/Elite feature matrix (✓ / — / value per cell, Pro column tinted) → the **Free-tier unlock ladders** (code vs conceptual tracks, in plain language). Reached from a "Compare every feature in detail →" link below the landing `#landing-pricing` grid (`.lp-pricing-compare-link`). The internal mirror of the same content is `docs/tier-wise-features.html`.



Per-track landing rendered by `Outlet` when no question is active:
- Track name + overall solved/total progress bar
- Per-difficulty breakdown (easy/medium/hard bars)
- Mixed-form reasoning tracks now show a compact `What you'll practice` strip in the header with the most common question-form labels for that catalog, so users can see variants like `Scenario`, `Debug`, `Predict output`, or `Numerical` before entering the workspace.
- "Continue where I left off" button → navigates to next unlocked question
- Learning paths section: paths are sorted by level order (foundational → intermediate → advanced) with incomplete paths before complete ones. The first incomplete accessible path gets a contextual `recommendationLabel` ("Start here" for an unstarted foundational path, "Continue" for an in-progress path, "Recommended next" for any other). Up to 2 paths shown; "View all N →" link to `/learn/:topic` when there are more.

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

#### Concept drill

When `?drill=<concept>` is present, `QuestionPage` fetches `GET /api/practice/drill?track={topic}&concept={concept}` into a `drillContext` (mirroring `pathContext`) and renders a **drill nav bar** — the `.path-nav-bar` markup reused with a `.path-nav-bar--drill` accent edge, a *Drilling: {concept}* label, a position counter, and prev/next links that preserve `?drill=`. The post-solve Next ladder gains two branches: **Next in drill** (walks only the concept's questions) and, on the last question, **Drill complete →** (navigates to `/dashboard`). Path context takes precedence if both `?path=` and `?drill=` are somehow present.

While a drill is active, **`AppShell` swaps the full-catalog `SidebarNav` for a scoped `DrillSidebar`** — exactly as `?path=` swaps in `PathSidebar`. It mirrors `PathSidebar` (reusing the `.path-sidebar*` CSS with a `.path-sidebar--drill` accent + a *Concept drill* kicker): a concept title, a progress bar (`{solved}/{total} cleared`), and **only the concept's questions** — fetched by `AppShell` from the same `GET /api/practice/drill` endpoint — each linking with `?drill=` preserved, plus an *Exit drill → Practice* footer. So the left panel matches the walk instead of showing the whole catalog. Drill is Pro+, so no locked-question handling is needed (all accessible).

Entry: every coaching *Drill* CTA (dashboard focus card + weak-areas rows, logged-in landing weak-spots, mock post-mortem) links to `/practice/{track}?drill={concept}`. `AppShell`'s hub effect redirects that to the first **unsolved** matching question while **preserving** the `?drill=` param. The redirect target is taken from the **backend drill result** (`GET /api/practice/drill` — already family-aware *and* unsolved-first ordered), the single source of truth; `AppShell` navigates to its `questions[0]` rather than re-deriving the match against the catalog in the frontend. (A prior frontend substring re-match silently failed for **hyphenated / non-substring family names** — e.g. *Multi-table entity linking* — stranding even Pro/Elite users on the hub; fixed 2026-06-18. Earlier still, the `?drill=` link reused the `?concepts=` redirect, which dropped the param — the "drill dumps you into the full catalog" bug.) Concept drills are **Pro+**, gated on both sides: the endpoint returns 403 for Free/anonymous, **and** `AppShell` makes `?drill=` **inert** for non-Pro (derives `canDrill` from the plan, fail-closed while auth loads) — so a Free/anonymous visitor who opens a drill link is **redirected to the clean URL** (the `?drill=` stripped, `replace`) — the normal practice question or hub + full-catalog sidebar, never drill chrome — and gets a **dismissible "Concept drills are a Pro feature" banner** (`DrillUpsellBanner` + `UpgradeButton`, `.app-banner-upsell`) below the topbar, driven by a router-state flag set during the redirect and re-armed per navigation. (`DrillSidebar` only renders for Pro+, and shows a finite "Drill unavailable" fallback rather than an infinite shimmer if its fetch ever fails.) `QuestionPage` gates its own drill fetch the same way. This is the practice-side weak-concept drill — distinct from the mock **custom-drill** mode (`focus_concepts`, Pro/Elite, in `MockHub`/`MockSession`).
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
- **Run vs Submit error handling (SQL):** Run (`/run-query`) surfaces errors as a red `runError` box — fast, raw, disposable. Submit (`/submit`) never surfaces a raw error box; the backend wraps any parse/guard error into `{ correct: false, feedback: [msg] }` so `submitResult` is always populated and the verdict → hint stepper → solution reveal flow is always reachable. This is intentional product design: a user who submits broken SQL is not stuck — they get hints and a path to the official solution.
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

### SampleHubPage (`/sample`)

Discovery surface for the 81 sample questions — the entry point users hit from the landing hero CTA, the closer CTA, the Tracks Index "Try sample →" links, and the Topbar Practice dropdown "Try a sample" entry.

**Layout:**
- Topbar (shared `Topbar` component, `variant='landing'`) so the user can still pivot to Mock, Dashboard, Practice ▾, or sign in
- Hero block (`.sample-hub-header`) — eyebrow ("Free samples · no account required"), h1, sub-copy
- 9-track grid (`.sample-hub-grid`) — 3 cols at ≥ 901 px, 2 cols 641–900 px, 1 col ≤ 640 px
- Each card (`.sample-hub-card`) shows: track color dot + label, 3-line description, and a 3-column row of difficulty buttons. Card hover border-color uses the track color.
- Each difficulty button (`.sample-hub-diff-btn`) links to `/sample/:topic/:difficulty`. Logged-in users see `tried/total` markers (`✓ all tried` when complete); logged-out users see a ghost `3 questions` label
- Footer block — copy + "Create a free account →" CTA

**Tried markers** come from `GET /api/sample/summary`, fetched on mount only when logged in. Anonymous visitors never see counters — matches the no-friction promise (no surveilling pre-signup).

### SampleQuestionPage (`/sample/:topic/:difficulty`)

Standalone sample practice. No sidebar. No effect on challenge progression.

**Topbar** — three-column, full-width:
- Left: `datathink` home link
- Center: `←` back arrow (→ `/sample`) + track-mode pill + in-page `SampleSwitcher` (track `<select>` + Easy/Medium/Hard pill group). Switching difficulty/track is a single click — no return to the Hub required.
- Right: "Start the challenge" CTA → `/practice/:topic`

Has the same **keyboard shortcuts** and **editor height toggle** as `QuestionPage` (same implementation pattern — refs for stale-closure safety, `localStorage` persistence). No `isLocked` guard since sample questions are always accessible.

**Mixed-subtype rendering (Statistics).** For `mixedSubtype: true` tracks, `SampleQuestionPage` derives `renderMode` from the loaded question's `subtype` field rather than the static `meta.hasMCQ` flag — mirroring the same `renderMode` useMemo pattern used by `QuestionPage`. A `subtype === 'numerical'` question renders the Python editor with Run Code + Submit Answer; a `subtype === 'conceptual'` question renders the MCQ panel. Submit payload and draft-autosave logic are both gated on `renderMode`, not `meta.hasMCQ`. Statistics numerical sample submissions show `TestCasePanel` + `PrintOutputPanel` results (same panels as the Python track). This is a product contract — any new mixed-subtype track added to the registry must be exercised in the sample flow without additional frontend changes.

Sample editor drafts are auto-saved per sample question key (`sample-draft:{topic}:{difficulty}:{questionId}`), restored on load, and can be cleared from the editor topbar.

Loading state now renders a skeleton card instead of plain text while fetching a sample question.

### ProgressDashboard (`/dashboard`)

Cross-track progress overview. Fetches `GET /api/dashboard`, `GET /api/dashboard/insights`, and `GET /api/mock/history` on mount.

- Renders one overview card per active track (all 9 tracks), not just the original executable slice.
- Returning **Pro/Elite** users see a **focus card** (hero CTA — *Drill {top weak concept} → Go*, the [concept drill](#concept-drill); falls back to a cross-track pace insight or continue-practice nudge) and a **"Where to focus"** panel of weak-concept rows, each with a primary *Drill this concept →* (`?drill=`) and an honest secondary *Or take the … path →* when a matching path exists. **Free** users see an upgrade teaser there. The solve streak shows on the dashboard hero stat (`.db-streak-at-risk`). Full coaching spec: [dashboard.md](features/dashboard.md). *(The previously-documented `InsightStrip` component was dead code — never mounted — and has been removed.)*
- Track cards now include `median_solve_seconds` and `accuracy_pct` rows from `/api/dashboard/insights`.
- New users (no solves yet) see a dedicated empty state with CTAs into practice and learning paths.
- `by_difficulty` still renders as "X/Y" counts per difficulty level (`{ solved, total }` objects, not plain integers).
- Loading state now uses reusable skeleton tiles and cards instead of plain text.

### LearningPathsIndex (`/learn`, `/learn/:topic`)

Index of all learning paths. Grouped by track. Topic-filter pills narrow to a single track when `:topic` is present in the URL. Each path shown as a card with title, description, solved count, and a link to the path.

Current catalog footprint shown on this page: **96 paths total** (SQL 11, Python 11, Pandas 9, PySpark 14, Data Engineering 9, Data Modeling 11, Statistics 11, ML Fundamentals 12, Experimentation 8).

- Empty state upgraded from plain text to CTA card (`/practice/sql`, `/dashboard`).
- Header sub frames paths as routes through the practice catalog ("the same questions, in a deliberate order"), with a **"Browse the full catalog →"** back-pointer to `/practice/:topic` (or `/practice/sql` on top-level `/learn`).

#### Practice ↔ Paths messaging (consistent across surfaces)

Practice (the per-track catalog) and Learning Paths are two layouts over the **same** question bank with **shared progress** — solving a question in either place marks it done in both. This is stated consistently on three surfaces so the two never read as competing offerings:
- **TrackHubPage** (`/practice/:topic`): a compact **"Two ways to work {track}"** strip (`.trackhub-twoways`) sits between the progress stat card and the Learning-paths section — labels the full catalog vs. guided routes and carries the canonical caption *"Same questions — solve one in either place and it's marked done in both. You never redo a question."* The "Learning paths" item links to `/learn/:topic`.
- **LandingPage** `PathsShowcaseSection`: the sub-copy weaves in "Same questions as the Practice catalog, just put in order: solve one in either place and it's marked done in both."
- **LearningPathsIndex** (`/learn`): the header sub + catalog back-pointer (above).

### LearningPath (`/learn/:topic/:slug`)

Curated path page. Shows breadcrumb (Learn → track → path title), overall progress bar, and a question list with per-question state (solved/unlocked/locked). Each question links to `/practice/:topic/questions/:id?path=:slug` so `QuestionPage` shows the path nav bar.

When `solved_count === question_count`, a completion banner is shown with a "What's next" CTA back to the track's path index.

---

#### Brand icons & social card

All brand icons derive from the canonical two-diagonal-squares mark on the Forest & Ink ground `#0D1A10` (green mark `#2FBE6B`/`#87B09A` — kept matched to the UI accent: `#4ADE80`→`#43D27C` 2026-06-13, `#43D27C`→`#5FB98C`→`#2FBE6B` 2026-06-17).

**Source SVGs** (do not modify — these are the design source of truth):
- `frontend/public/favicon.svg` — 64×64 rounded chip; **theme-adaptive** via an internal `@media (prefers-color-scheme)` block: dark scheme = forest-ink chip (`#0D1A10`) + bright mark; light scheme = white chip + hairline border + deep-green mark (`#166534`/`#4B6858`). Source for both dark and light favicon PNGs.
- `frontend/public/icon-maskable.svg` — 512×512 full-bleed (no corner rounding; platforms apply their own mask); source for `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`
- `frontend/public/og-image.svg` — 1200×630 social card with wordmark, tagline, and durable stat copy ("9 tracks · 850+ curated questions · 1,000+ mock-exclusive"); source for `og-image.png` (dark, the canonical share card)
- `frontend/public/og-image-light.svg` — 1200×630 light-ground alternate of the OG card (same copy/layout, light palette); source for `og-image-light.png`. This is a standalone asset for light-background placements (emails, docs) — it is NOT wired into `og:image`/`twitter:image` (share platforms cannot switch by viewer theme; the dark card remains canonical).

**Rasterized PNGs** (generated; do not hand-edit — re-run the script instead):

Dark-scheme favicons: `favicon-16.png` (16×16), `favicon-32.png` (32×32), `favicon-48.png` (48×48).
Light-scheme favicons: `favicon-light-16.png` (16×16), `favicon-light-32.png` (32×32), `favicon-light-48.png` (48×48).
PWA icons: `apple-touch-icon.png` (180×180), `icon-192.png` (192×192), `icon-512.png` (512×512).
OG cards: `og-image.png` (1200×630, dark), `og-image-light.png` (1200×630, light).

**Render script:** `frontend/scripts/render-brand-assets.mjs` — Node ESM, uses Playwright Chromium. Run from `frontend/`: `node scripts/render-brand-assets.mjs`. Each TARGETS entry carries a `colorScheme` field (`'dark'` or `'light'`); before each screenshot the script calls `page.emulateMedia({ colorScheme })` so the adaptive `favicon.svg` renders in the correct scheme. The OG font-load branch triggers on `source.startsWith('og-image')`, covering both `og-image.svg` and `og-image-light.svg`. It inlines each SVG directly into the DOM (required for OG web-font pickup), sets an exact-pixel viewport, and screenshots with `deviceScaleFactor: 1`.

**Web app manifest:** `frontend/public/site.webmanifest` — `theme_color` and `background_color` both `#0D1A10`; references `icon-192.png` and `icon-512.png` with `"purpose": "any maskable"`.

**`index.html` wiring:** SVG favicon is first (modern browsers — the SVG itself handles both schemes via its internal media query). Dark PNGs (`favicon-32.png`, `favicon-16.png`) follow as the media-less universal fallback. Light PNGs (`favicon-light-32.png`, `favicon-light-16.png`) are gated to `media="(prefers-color-scheme: light)"`. `theme-color` is a single light tint `#F5F7F4` at launch (light-only; the dark `(prefers-color-scheme: dark)` `#0D1A10` variant is dormant — restore the two media-scoped tags to re-enable dark). Favicons still adapt to the OS/browser-chrome scheme — that is tab-bar contrast, independent of the app's locked-light theme.

**OG image versioning:** The OG image URL is versioned (`og-image.png?v=3`) in `index.html`, `backend/routers/spa.py` (server-side injection), and all pages that set `og:image`/`twitter:image` via Helmet (`LandingPage.js`, `LearningPath.js`, `SampleQuestionPage.js`, `TrackHubPage.js`, `LearningPathsIndex.js`). When the OG art changes: re-render via the script, bump `?v=N` in all these locations simultaneously. `og-image-light.png` is not versioned — it is not served as a share card and carries no cache-busting requirement.

---

## Components

| Component | File | Purpose |
|---|---|---|
| AppShell | `components/AppShell.js` | Challenge workspace: fixed topbar with direct track nav, collapsible sidebar |
| SidebarNav | `components/SidebarNav.js` | Question list grouped by difficulty; topic-aware NavLinks |
| CodeEditor | `components/CodeEditor.js` | Language-agnostic Monaco editor (`language`, `height`, `fontSize`, `onMount`, `ariaLabel` props). Always dark, but **theme-aware**: `forest-dark` under light pages, `charcoal-dark` (`#16181C`) under dark pages — switched via `useTheme().isDark` (2026-06-17) |
| SQLEditor | `components/SQLEditor.js` | Thin re-export of CodeEditor with `language="sql"` (backward compat) |
| ResultsTable | `components/ResultsTable.js` | Tabular results with sticky headers, horizontal overflow cue, null value rendering, and optional `diffMode` for cell-level diff highlighting |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema with client-side search and click-to-copy column tokens |
| TestCasePanel | `components/TestCasePanel.js` | Python test case results (pass/fail per case, input/expected/actual, hidden summary) |
| PrintOutputPanel | `components/PrintOutputPanel.js` | Captured stdout block (rendered only if non-empty) |
| VariablesPanel | `components/VariablesPanel.js` | Available DataFrame variables with CSV source and column list |
| MCQPanel | `components/MCQPanel.js` | Radio-button response panel with configurable explanation/lock copy; still used for option-based reasoning tracks |
| ConceptPanel | `components/ConceptPanel.js` | Slide-in concept detail panel opened from concept pills on `QuestionPage` |
| Skeleton | `components/Skeleton.js` | Reusable shimmer primitive (`skeleton-block` + `skeleton-shimmer`) used in QuestionPage, SidebarNav, TrackHubPage, ProgressDashboard |
| TrackProgressBar | `components/TrackProgressBar.js` | Reusable horizontal progress bar with configurable color and label |
| PathProgressCard | `components/PathProgressCard.js` | Path card with track color dot, progress bar, and CTA; used on LandingPage and TrackHubPage. Accepts optional `recommendationLabel` prop that replaces the tier badge with a contextual label ("Start here", "Recommended next", "Continue"). |
| OnboardingTooltip | `components/OnboardingTooltip.js` | First-visit, target-anchored walkthrough tooltip with Back/Next/Skip and Esc-to-close support |
| Topbar | `components/Topbar.js` | Single unified top nav used by every page (landing, auth, 404, practice workspace, mock, dashboard, learning paths). Composition slots for `leftSlot`, `centerSlot`, `userExtras`, `belowTopbar`; three variants: `'landing'` (default, container-bounded), `'app'` (full-bleed workspace chrome), `'minimal'` (auth / verify / reset / 404 — brand + user pill only; theme toggle removed, light-only at launch). `showPricingLink` for logged-out visitors. The brand mark now uses the bar lockup assets from `frontend/public/branding/` (`lockup-bar-no-bg.svg` / `lockup-bar-reverse-no-bg.svg`) and always resolves to the top of the landing page. `lockup-bar-no-bg.svg` uses D `#5B6AF0` with bar `#242a60`; `lockup-bar-reverse-no-bg.svg` uses D `#FFFFFF` with bar `#5B6AF0`. |
| ToastViewport | `components/ToastViewport.js` | Global in-app toast stack (first-solve, unlock, and streak milestone feedback) rendered by `ToastProvider` |
| LoggedInWelcome | `components/LoggedInWelcome.js` | Welcome-back block on `/` for authenticated users. Three cards: Resume (last-solved question via `/api/dashboard` recent_activity), Dashboard, Mock. Replaces the marketing hero for returning users. |
| TierBanner | `components/TierBanner.js` | Inline upgrade prompt shown when a user hits a plan gate (e.g. locked hard questions); renders contextual copy and upgrade CTA |
| UpgradeButton | `components/UpgradeButton.js` | Reusable upgrade CTA. Picks the billing rail via `railForCurrency` (`utils/currency.js`) from the **silently detected** currency (`detectCurrency()` — India `Asia/Kolkata`/`Asia/Calcutta` → INR, else → USD): INR → Razorpay Checkout, any other currency → Paddle.js overlay (Merchant of Record). There is **no user-facing currency selector** (removed); every upgrade surface is rail-consistent without the caller threading a currency value. |

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
  apiPrefix: '/pandas',   // used to build API paths
  language: 'python',
  hasRunCode: true,
  hasMCQ: false,
  tagline: 'pandas · numpy · data wrangling',
}
```

`TopicProvider` reads `:topic` from URL params via `useParams()`. `useTopic()` returns `{ topic, meta }`.

**Track registry (`frontend/src/trackRegistry.js`):** Single source of truth for all track metadata (`TRACK_META`). Adding a track here is the only frontend change needed — catalog paths, sidebar, TrackHub, and SidebarNav all read from it. Current tracks: `sql`, `python`, `pandas`, `pyspark`, `data-engineering`, `data-modeling`, `statistics`, `ml-fundamentals`, `experimentation`.

`data-engineering` entry: `color: '#B9762B'`, `hasMCQ: true`, `hasRunCode: false`, `apiPrefix: '/data-engineering'`.

`statistics` entry: `color: '#7A5AF0'`, `hasMCQ: true`, `hasRunCode: true`, `mixedSubtype: true`, `apiPrefix: '/statistics'`, `language: 'python'`. The `mixedSubtype: true` flag tells both `QuestionPage.js` and `SampleQuestionPage.js` to derive `renderMode` from `question.subtype` at runtime rather than using the static `hasMCQ` flag — enabling a single page to render both conceptual (MCQ) and executable numerical questions. Both pages compute `renderMode` via the same useMemo pattern: `mixedSubtype ? (question?.subtype === 'numerical' ? 'code' : 'mcq') : (hasMCQ ? 'mcq' : 'code')`.

Reasoning-first practice now reads additive `interaction_mode` metadata across PySpark, Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and Statistics. `QuestionPage` keeps `question.type` / `question_type` separate so headings, header guidance, and submit labels can still distinguish predict-output, debug, optimization, and scenario variants even when multiple question forms share the same modality family.

### `catalogContext.js`

Fetches catalog for the current topic on mount. URL determined by `useTopic()` using each track's `apiPrefix` from the registry:
- `sql` → `/catalog`
- `python` → `/python/catalog`
- `pandas` → `/pandas/catalog`
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
1. `/practice/pandas/questions/:id` → fetch `/api/pandas/questions/:id`
2. VariablesPanel shows available DataFrames from `question.dataframes`
3. Run → `POST /api/pandas/run-code` → ResultsTable + PrintOutputPanel
4. Submit → `POST /api/pandas/submit` → correct/incorrect + DataFrame comparison

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

### Sample flow (resume model)
1. `/sample/:topic/:difficulty` → `GET /api/sample/:topic/:difficulty` returns the next **unattempted** question. GET is read-only — refresh, navigate-back, or close/reopen the tab is idempotent.
2. Run uses `/api/sample/{topic}/run-code` (no marking). Submit uses `/api/sample/{topic}/submit` — submit is the commitment event that marks the question as attempted (correct + incorrect both count).
3. "Another sample →" calls `POST /api/sample/:topic/:difficulty/skip` with the current `question_id` to mark it attempted without submitting, then re-fetches.
4. 409 on exhaustion → the page renders the exhausted state with a primary "Take the challenge" CTA and a demoted `Or redo this set from scratch →` link that calls `POST /api/sample/:topic/:difficulty/reset` and re-fetches.
5. The Hub tile counters reflect submit/skip events only — pure views never advance them.
6. No effect on challenge progress.

---

## Observability

### Sentry (error capture)

Initialized in `index.js` when `VITE_SENTRY_DSN` is available. In local dev it comes from Vite env; in the deployed single-service app it is injected at request time into `window.__APP_CONFIG__` by `routers/spa.py`. Uses `@sentry/react` with:
- Browser tracing (10% sample rate)
- Session Replay on errors (100% of error sessions, 0% baseline) — `maskAllText:true` so visible text (incl. email in topbar, question content) is never sent to Sentry
- `ErrorBoundary.js` calls `Sentry.captureException()` on component crashes
- **User identity:** `setSentryUser()` called in `AuthContext.js` alongside `identifyUser` on session restore / login / register; `Sentry.setUser(null)` on logout. Only set for authenticated users (email present); anonymous sessions leave Sentry user context null. This mirrors the backend tagging in `deps.py` so every error — frontend or backend — carries user/plan attribution.

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
| `plan_upgrade_started` | UpgradeButton | `tier`, `source`, `rail` (`razorpay` \| `paddle`) |
| `plan_upgraded` | UpgradeButton | `tier`, `source`, `rail` (`razorpay` \| `paddle`) |

**Funnel:** Landing → Track selection → First question → First solve → Registration → Plan upgrade.

**Production sourcemaps:** `vite.config.js` emits hidden sourcemaps for production builds. If `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are provided during build, `@sentry/vite-plugin` uploads them automatically, then deletes them from `dist/` via `filesToDeleteAfterUpload`. This matters because `sourcemap:'hidden'` only omits the `//# sourceMappingURL` comment — the `.map` files are still present in `dist/` and served by the backend's static handler without the delete step.

---

## Design system

Single global stylesheet: `frontend/src/App.css`. No CSS framework, no CSS modules.

**Philosophy:** Professional tool aesthetic — calm, fast, distraction-free. Designed for long sessions (30–90 min). **Light-only at launch** — dark mode is deferred to a future version and dormant (see [`color-palette.md`](../design/color-palette.md) § Active theme launch status). The `index.html` bootstrap script and `ThemeProvider` (`App.js`) both force `data-theme="light"` pre-mount, ignoring `localStorage.theme` + `matchMedia('(prefers-color-scheme: dark)')` and flushing any stored preference — so there is no theme-flash and a dark-OS / previously-dark visitor lands on light. The `[data-theme="dark"]` CSS remains in `App.css` for the eventual re-enable. The code editor pane is always dark — an intentional two-tone split — but matches the page theme's flavor: forest-green (`#0F2218`) under light pages, neutral charcoal (`#16181C`) under dark pages (theme-aware as of 2026-06-17; see color-palette.md § Code editor & sandbox surfaces).

### Color tokens

**Active theme: Forest & Ink.** Full token table with all values: [`docs/design/color-palette.md`](../design/color-palette.md).

Defined in `:root` in `App.css`. Dark-mode overrides under `[data-theme="dark"]`; light-mode force under `[data-theme="light"]`. Theme managed by `ThemeProvider` in `App.js` — context shape `{ theme, setTheme, isDark, cycleTheme, themeIcon, themeLabel }` is preserved, but **locked to light at launch**: `theme='light'`, `isDark=false`, `setTheme`/`cycleTheme` are no-ops, `localStorage` + OS `prefers-color-scheme` are ignored, and any stored `theme` is flushed. The theme toggle is removed from `Topbar`. Dark is a near-one-line re-enable here + in the `index.html` pre-paint bootstrap (deferred to a future version — see [`docs/decisions/DECISIONS.md`](../decisions/DECISIONS.md) 2026-06-17 defer-dark).

Light mode is **Forest & Ink** (deep-green on warm paper). Dark mode is
**charcoal** (near-neutral surfaces; brand green as an accent, not the
environment — 2026-06-12). Full rationale + the primary-button rule in the
palette doc.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg-page` | `#F5F7F4` | `#121315` | Page background |
| `--surface-card` | `#FFFFFF` | `#1A1B1E` | Cards, panels |
| `--surface-card-alt` | `#EDF3EF` | `#212327` | Sidebar, secondary surfaces |
| `--border-subtle` | `rgba(20,41,27,0.08)` | `rgba(228,231,235,0.08)` | Default borders |
| `--text-strong` | `#14291B` | `#ECEEF0` | Headings |
| `--text-primary` | `#1D3526` | `#CDD1D6` | Body text |
| `--text-secondary` | `#4B6858` | `#9BA1A9` | Labels, metadata |
| `--text-muted` | `#7A9485` | `#6E747D` | Placeholders, disabled |
| `--accent` | `#166534` | `#2FBE6B` | Active states, links, small accents (dark `#43D27C`→`#5FB98C`→re-sharpened `#2FBE6B` 2026-06-17) |
| `--success` | `#15803D` | `#4CAF82` | Correct answer |
| `--warning` | `#C47F17` | `#D4973A` | Hints, locked |
| `--danger` | `#D94F3D` | `#E06B5A` | Errors, wrong answer |

> **Primary button is not `--accent` in dark mode.** `.btn-primary` (and
> everything composing it — `.mock-start-btn`, both `UpgradeButton` tiers,
> `.auth-submit-btn`, `.acct-save-btn`, `.path-nav-btn--next`,
> `.lp-paths-cta-primary`) uses the deep **action green `#1C8A4F` + white**,
> hover `#229B5A`; Elite keeps the green→teal gradient. `--accent` stays
> reserved for accents. See the palette doc.

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

**Layout:** Two-column desktop lobby (`1fr 292px` CSS grid, 1060px max-width). Left column: hero → mode cards (3) → track-specific benchmark blueprint or dedicated drill planner → config pills (track + difficulty). Right rail (sticky at top 72px): session brief card showing active mode badge, track, difficulty, question count, time limit, access state, and the anchored start button. Below the lobby: Elite analytics panel → split recent benchmark/drill history tables with first-run and partial-history benchmark/drill guidance. Collapses to single-column below 900px.

- MockHub hero now frames `/mock` as a baseline-then-improvement workflow in plain language (`benchmark` first, `custom` drills second, `Interview Loop` for Elite depth), with the help button rendered as a separate adjacent control rather than inline punctuation.
- The Data Engineer role filter now includes Data Modeling, matching the canonical role mapping used elsewhere in the product.
- Benchmark is now the default starting mode on single-track sessions and is presented as the fixed-shape, serious mock.
- Custom drill is the live flexible follow-up mode. Legacy `30min` sessions remain reviewable in history only.
- Drill modes now render a dedicated planner card with the session shape, purpose, and inline custom controls so drills read as a separate setup surface instead of just alternate mode cards.
- Mixed track supports role-based benchmark and custom drill setup; role selection is required before start, while Interview Loop remains single-track only.
- Elite analytics now use `benchmark_summary` as the comparable primary view and surface drill performance in a smaller secondary card.
- History rows format stored mode values into human labels (`Benchmark`, `Sprint drill`, `Custom drill`, `Full (legacy)`) so older sessions stay legible without preserving the old setup framing, and the tables are split into `Recent benchmark sessions` and `Recent custom drills`.
- When no history exists, MockHub now teaches the benchmark-then-drill workflow explicitly instead of collapsing to a single generic empty state.
- When only one side of history exists, MockHub now renders targeted guidance (`No benchmark sessions yet` or `No drill sessions yet`) so users understand what the missing session type is for.

### MockSession (`pages/MockSession.js`)

Full-screen layout. Does not use `AppShell`. Has two states:

**Active state:**
- Custom topbar: `[◀ Exit] [Q1• Q2○ Q3○] [MM:SS timer] [End session]`
- Left panel now opens with a session-context card that makes the current mode explicit: benchmark sessions show a fixed-shape benchmark badge, shape summary, and track-specific benchmark framing; drills show flexible drill framing instead.
- Below the session-context card: a `.mock-session-rule` sidebar callout (left-bordered, muted background) with two concise lines. The first line is track-aware: code tracks (`!meta.hasMCQ` — SQL, Python, Pandas) show "Each question is one shot — run freely before you commit."; MCQ/mixed tracks show "Each question is one shot — select carefully before you commit." The second line is always "Use ← → at the top to move between questions."
- Body: 280px left panel (question description/schema + concepts) | flex-grow right panel (editor + run/submit)
- Timer: countdown from `time_limit_s`. Recomputed from `started_at` on reload. Auto-finishes when it hits zero.
- Timer CSS states: neutral → `.mock-timer--warning` (<10min) → `.mock-timer--danger` (<3min, pulsing)
- **Submit model (one-shot):** Each question allows exactly one real submission. The submit button is disabled once `submitted[q.id]` is true. Blank code (code tracks) or a missing MCQ selection also disables the button. After a wrong submit the button label switches to `✗ Submitted`. **No feedback is rendered from submit** — the button state is the only signal. Run results remain visible and unaffected by submit (Run never clears the submit lock).
- **Post-submit navigation:** After any submit (correct or wrong), a `Next question →` button appears on non-last questions. On the last question after submitting, a `.mock-all-done` nudge paragraph appears instead — two variants: "All questions answered — end your session when ready." when every question has been submitted (`allSubmitted`), or "End your session when ready, or go back to answer remaining questions." when some earlier questions are still unanswered.
- **Reload recovery:** `submitted{}` state is initialised from `submitted_at` per question in the `GET /api/mock/{id}` response, so the one-shot lock survives page reload.

**Summary state (after finish):**
- Summary topbar and intro card now distinguish `Benchmark summary` vs `Drill summary`, show the human-readable mode label, and restate the session shape before the score block.
- Score card: `X/Y correct, Z% above/below your session average` (comparison against `GET /api/dashboard/insights` track accuracy baseline), plus time used
- Per-concept session accuracy row (`correct/attempts`) built from concepts touched in this mock
- Benchmark summaries show footer actions: `Share result` + `Back to Mock` + `Plan follow-up drill` (primary).
- Drill summaries push targeted follow-up: Pro/Elite users get `Drill weak concepts →` to `/practice/{track}?concepts={slug1,slug2}`; other cases get a prefilled short drill preset CTA plus `Back to drill lobby`.
- Per-question rows: title · solved badge · time spent · collapsible solution
- Share CTA: uses `navigator.share({ text })` when available (mobile OS share sheet); falls back to `navigator.clipboard.writeText`. Share text format: `{Track} {benchmark/drill} · {Difficulty} · {N}/{total} ({pct}%)` + baseline delta line (Pro/Elite) + top 2 weak concept gaps + `datathink.co`.
- MockHub accepts summary-driven `location.state.mockPreset` recommendations and surfaces them as a `Recommended next step` banner plus prefilled drill planner state.

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
| Mock plan-tier e2e | `e2e/mock-plan-flows.spec.js` | Repeatable free/pro/elite MockHub + MockSession checks: plan-specific `/mock` surfaces, right/wrong PySpark submissions, drill summary CTA behavior, elite benchmark debrief, and summary-to-hub drill handoff |

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
