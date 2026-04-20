# Path to World-Class — Experience Upgrade Plan

> Living document. Update the **Progress tracker** at the bottom as work lands.
> This doc is the hand-off contract — an agent should be able to resume by reading this alone.

---

## 0. Context

The landing-showcase redesign shipped ("The Interview IDE"). An experience audit of the full repo followed, run by three Explore agents plus spot-verification. This plan is the agreed multi-phase path to a world-class premium interview-practice platform (benchmarks: Linear, Vercel, Stripe, Raycast, LeetCode Premium, DataLemur).

**Current state (as of 2026-04-20):** Phases 1, 2, 3, and 4 are complete. Next up: Polish batch.

**Explicitly out of scope (owner decision):**

- **Question content quality / difficulty calibration** — addressed in a separate pass.
- **Brand identity, icon primitive, strict spacing tokens, motion grammar, full a11y audit** (Phase 5). Deferred to a design-led workstream.
- **Monaco editor stays always-dark.** Same for the landing-showcase IDE window. Both are intentional per [CLAUDE.md](CLAUDE.md).

**In scope (this plan):** Phases 1–4, sequential. Each phase = one commit minimum, co-authored per CLAUDE.md.

---

## 1. What shipped

### Phase 1 — Stop the bleed ✓

- Extended `ThemeContext` with `isDark`, `cycleTheme`, `themeIcon`, `themeLabel` — fixed crashes on 4 pages.
- Consolidated dark-mode CSS: removed both `@media prefers-color-scheme` blocks; added pre-hydration script in `index.html`.
- Unified `<Topbar>` with composition slots (`leftSlot`, `centerSlot`, `userExtras`, `belowTopbar`); all pages now use it.
- Added `LoggedInWelcome` component on `/` — logged-in users see Resume / Dashboard / Mock cards instead of blank space.
- Added `Pricing` link to unauthenticated topbar + `id="landing-pricing"` anchor on landing.
- `NotFoundPage` CTA now shows "Sign in" for unauthenticated visitors instead of the auth-walled "Start practising".

### Phase 2 — Tighten the funnel ✓

- Pricing tier copy rewritten with hard numbers: Free lists 129 easy questions by track; Pro shows all 350 + 3 mocks/day; Elite adds company filter + unlimited mocks.
- `TRACK_DIFFICULTIES` and `TRACK_META.totalQuestions` corrected to real counts (SQL 95, Python 83, Pandas 82, PySpark 90).
- `.landing-proof-row` between hero and showcase: "350 questions · 4 tracks · 11 real-world datasets · instant feedback".
- Sample-exhausted copy: "You've seen all 3 {difficulty} samples. Ready for the full {n}-question track? Pro unlocks medium + hard."
- OAuth buttons: removed `disabled` attribute; now styled as intentionally inert (`opacity: 0.65`, `cursor: default`).
- Signup form: added `passwordConfirm` field with blur validation and disabled submit on mismatch; success message includes spam-folder + 24h link-expiry guidance.
- `VerifyEmailPage` error state: 24h expiry note, spam-folder line, direct resend button for signed-in users.
- Replaced hardcoded `'#5B6AF0'` fallbacks with `var(--accent)` in LandingPage.

---

## 2. Architecture decisions (binding for implementing agents)

### 2.1 Theme context

Single source of truth in [`App.js`](frontend/src/App.js):

```js
// ThemeContext value shape (shipped in Phase 1)
{
  theme: 'light' | 'dark',
  setTheme: (value: 'light' | 'dark') => void,
  isDark: boolean,
  cycleTheme: () => void,       // toggles between light/dark
  themeIcon: '☀' | '☾',        // character shown on toggle button
  themeLabel: string,           // aria-label + title for the toggle
}
```

All consumers import from `../App`. Do not add local `isDark`/`themeIcon`/`themeLabel` derivations.

### 2.2 Dark-mode

- **Source of truth:** `[data-theme="dark"]` CSS selectors.
- **No `@media prefers-color-scheme` blocks** — both were removed in Phase 1.
- Pre-hydration script in `frontend/index.html` sets `data-theme` before React mounts (no FOUC).

### 2.3 Unified Topbar

Single `<Topbar>` used by every page. Slots:

```jsx
<Topbar
  active={'mock' | 'dashboard' | null}  // highlights a nav link
  leftSlot={ReactNode}                  // AppShell: mobile sidebar toggle
  centerSlot={ReactNode}                // AppShell: mode pill "SQL · Challenge"
  userExtras={ReactNode}                // AppShell: plan pill "Pro"
  belowTopbar={ReactNode}               // AppShell: upgrade banner
  showPricingLink={boolean}             // logged-out visitors only
  variant={'landing' | 'app' | 'minimal'}
/>
```

Render order: `[brand] [leftSlot] ··· [centerSlot] ··· [nav-dropdown] [Mock] [Dashboard] [Pricing?] [themeToggle] [sep] [userExtras] [user-pill | sign-in]`

### 2.4 `/api/dashboard/insights` endpoint (Phase 4)

New router at `backend/routers/insights.py`, registered in `backend/main.py`.

```json
{
  "per_track": {
    "sql":          { "solve_count": 28, "median_solve_seconds": 512, "accuracy_pct": 0.82 },
    "python":       { "solve_count": 12, "median_solve_seconds": 740, "accuracy_pct": 0.71 },
    "python-data":  { "solve_count": 5,  "median_solve_seconds": 930, "accuracy_pct": 0.80 },
    "pyspark":      { "solve_count": 18, "median_solve_seconds": 120, "accuracy_pct": 0.88 }
  },
  "weakest_concepts": [
    { "concept": "window functions", "track": "sql", "attempts": 8, "correct": 3, "accuracy_pct": 0.375 }
  ],
  "cross_track_insight": "You solve Python ~4 minutes slower than SQL. Try 3 Python mediums to close the gap.",
  "streak_days": 7
}
```

- Aggregates from the existing `submissions` table (no schema changes required).
- `median_solve_seconds` = median of `created_at - question_started_at` over correct submissions, per track.
- `weakest_concepts` = bottom 3 concepts with ≥3 attempts by accuracy.
- `cross_track_insight` = deterministic text template on largest `median_solve_seconds` gap; null if gap < 60s.
- `streak_days` = distinct days with ≥1 correct submission ending today; 0 if today has none.
- Cache 60s in-process per user_id.

---

## 3. Non-issues (do NOT "fix")

- **Monaco editor theme = `vs-dark` always.** CLAUDE.md: "the two-tone editor (always dark)."
- **Landing-showcase IDE window is dark in both themes.** Owner confirmed; Linear/Vercel/Stripe pattern.

---

## 4. Phase 3 — Workspace power polish

**Goal:** workspace feels like a tool, not a prototype.

| # | Task | Files | Notes |
|---|---|---|---|
| 3.1 | Inline `⌘↵` / `⌘⇧↵` badges on Run and Submit buttons; add a `?` shortcut help popover in the workspace chrome. | [QuestionPage.js](frontend/src/pages/QuestionPage.js), [App.css](frontend/src/App.css) | Badge = `<kbd>` element; popover = `<details>` or backdrop primitive. |
| 3.2 | Results table: sticky first header row; horizontal-scroll cue ("→ X more columns") when `scrollWidth > clientWidth`. Listen via `ResizeObserver`. | [ResultsTable.js](frontend/src/components/ResultsTable.js), [App.css](frontend/src/App.css) | `position: sticky; top: 0` on `<thead>`; `.results-table-scroll-cue` fades in on overflow. |
| 3.3 | Schema viewer: add search input; click-to-copy column names. | [SchemaViewer.js](frontend/src/components/SchemaViewer.js) | Client-only filter on table + column names. Clipboard API for copy. |
| 3.4 | Submit double-click protection: set submitting state synchronously before the API call. | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Guard with `if (submitting) return;` at function top. |
| 3.5 | Solution-reveal button: move inside the verdict card header, not below feedback. | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Re-order JSX; no new state. |
| 3.6 | Sidebar unlock-nudge copy: compute thresholds per track from `unlock.py` constants (currently hardcoded "10 easy / 10 medium"). | [AppShell.js](frontend/src/components/AppShell.js) | Hardcode per-track map matching [unlock.py](backend/unlock.py) if no runtime signal available. |
| 3.7 | Past-attempts panel expanded by default on return visit to the same question (`localStorage.last_seen_question_id`). | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Simple localStorage key; no backend change. |
| 3.8 | Secondary-button contrast in dark editor chrome: raise to ≥ 4.5:1 (WCAG AA). | [App.css](frontend/src/App.css) | Raise `rgba(255,255,255,0.07)` → `0.14` or add `1px solid rgba(255,255,255,0.12)`. |

**Verification:**

- `⌘↵` runs, `⌘⇧↵` submits, `?` toggles help — on both SQL and Python workspaces.
- Results table at 800px with 12-column output shows scroll cue and sticky header.
- Schema viewer search filters tables and columns; clicking a column name copies it.
- Rapid double-click submit produces only one network request.
- Contrast ≥ 4.5:1 on dark chrome measured in devtools.
- `cd backend && ../.venv/bin/python -m pytest tests/ -q` green.
- Update [docs/frontend.md](docs/frontend.md).
- Commit on `main` with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

---

## 5. Phase 4 — Meta depth

**Goal:** `/dashboard` coaches, `/mock` summarizes with insight, path completion is a moment.

### 5.1 Backend

| # | Task | Files |
|---|---|---|
| 4.0 | `GET /api/dashboard/insights` endpoint + tests. See §2.4 for spec. | `backend/routers/insights.py` (new), [backend/main.py](backend/main.py), `backend/tests/test_dashboard_insights.py` (new) |

### 5.2 Dashboard → coach

| # | Task | Files |
|---|---|---|
| 4.1 | Fetch insights on mount; render above existing track cards. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js) |
| 4.2 | New `InsightStrip` component — 3 tiles: cross-track insight, streak, weakest concept. | `frontend/src/components/InsightStrip.js` (new) |
| 4.3 | Per-track cards gain "median solve time" and "accuracy %" rows. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js) |

### 5.3 Mock → post-mortem

| # | Task | Files |
|---|---|---|
| 4.4 | Mock summary header: "X/Y correct, Z% above your session average" (reuse insights endpoint). | [MockSession.js](frontend/src/pages/MockSession.js) |
| 4.5 | Per-concept accuracy row: concepts touched this session with ✓ / ✗ counts. | [MockSession.js](frontend/src/pages/MockSession.js) |
| 4.6 | "Drill weak concepts" CTA → `/practice/{track}?concepts={slug1,slug2}`. Requires sidebar to honor `?concepts=` query param. | [MockSession.js](frontend/src/pages/MockSession.js), [SidebarNav.js](frontend/src/components/SidebarNav.js) |

### 5.4 Path completion + empty states

| # | Task | Files |
|---|---|---|
| 4.7 | Path page: completion banner when `solved_count === question_count` + "What's next" CTA. | [LearningPath.js](frontend/src/pages/LearningPath.js) |
| 4.8 | Path index: "In progress" rail (1 ≤ solved < total, sorted by completion desc) above full grid. | [LearningPathsIndex.js](frontend/src/pages/LearningPathsIndex.js) |
| 4.9 | Real empty states with CTAs on `/dashboard`, `/mock`, `/learn`. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js), [MockHub.js](frontend/src/pages/MockHub.js), [LearningPathsIndex.js](frontend/src/pages/LearningPathsIndex.js) |

**Verification:**

- `curl -H 'Cookie: session=...' localhost:8000/api/dashboard/insights` returns valid JSON.
- Dashboard: populated user sees InsightStrip + enhanced cards. New user sees "start solving to unlock insights" state.
- Mock: finish a session → summary shows concept accuracy + comparison sentence.
- Path: solve the last question in any path → celebration banner appears on refresh.
- Backend tests pass.
- Docs sync: [docs/backend.md](docs/backend.md) (new endpoint), [docs/frontend.md](docs/frontend.md) (dashboard + mock), [CLAUDE.md](CLAUDE.md) (API table).
- Commit on `main` with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

---

## 6. Polish backlog (single commit after Phase 4)

- Tighten sample-section defensive copy ("no account required, no progress recorded") to one line.
- Em-dash vs hyphen consistency in pricing CTAs.
- Loading skeletons for sample page and solution analysis panel.
- Landing tab state: `sessionStorage` → `localStorage` for cross-session stickiness.
- Add `mailto:` to `ErrorBoundary` "contact us" link.
- Path breadcrumb nav visible when user navigates via sidebar (not only from `/learn/...`).
- Showcase: move `prefers-reduced-motion` check into initial state (avoids one tick of animation before suppression).

---

## 7. Post-Phase-4 backlog

Items below are prioritized after Phases 1–4 land. Owner decides sequencing.

### 7.1 Pre-launch checklist

- Reserved-email blocking is live in `auth.py`; no code change needed.
- Run `backend/scripts/seed_admin.py` once against the production Postgres DB before launch (idempotent).

### 7.2 Workspace depth

| Item | Files |
|---|---|
| **Auto-save drafts** — debounce-save to `localStorage` keyed by `{topic}:{questionId}`; restore silently on load; "Draft saved" indicator; "Clear draft" button. | [QuestionPage.js](frontend/src/pages/QuestionPage.js), [SampleQuestionPage.js](frontend/src/pages/SampleQuestionPage.js) |
| **Wrong-answer diff** — row-level and cell-level diffing in `ResultsTable` for incorrect SQL; summary line for extra/missing rows; side-by-side diff for Python test failures. | [ResultsTable.js](frontend/src/components/ResultsTable.js), [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Progressive hints** — 4-step scaffolded system: conceptual → approach → structure → full solution. Soft gate on solution reveal. | [QuestionPage.js](frontend/src/pages/QuestionPage.js), `components/HintStepper.js` (new) |
| **Concept explanation panel** — `backend/content/concepts.json` maps concept names to explanations + examples. Click on a concept pill → slide-in panel. | `backend/content/concepts.json`, `components/ConceptPanel.js` (new), [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Similar-question recommendations** — after correct solve, recommend ≤2 unsolved questions sharing a concept. Secondary to "Continue to next". | [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Monaco upgrades** — SQL schema-aware autocomplete, `sql-formatter` shortcut, session query history, persisted font-size. | [CodeEditor.js](frontend/src/components/CodeEditor.js) |
| **Result error clarity** — translate common DuckDB errors to learner-friendly copy; highlight relevant Monaco line. | `frontend/src/utils/sqlErrorParser.js` (new), [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Question bookmarks** — header toggle + bookmarked section in `SidebarNav`; localStorage cap 20. | [QuestionPage.js](frontend/src/pages/QuestionPage.js), [SidebarNav.js](frontend/src/components/SidebarNav.js) |
| **Per-question soft timer** — elapsed timer in editor topbar; pause on tab blur; `duration_ms` in submissions. | [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Resizable split pane** — draggable divider between description and editor; persist in `localStorage`; double-click resets. | [QuestionPage.js](frontend/src/pages/QuestionPage.js) |
| **Session goals + focus mode** — daily-goal widget in `localStorage`; focus mode hides chrome, syncs to `?focus=1`. | [AppShell.js](frontend/src/components/AppShell.js), [QuestionPage.js](frontend/src/pages/QuestionPage.js) |

### 7.3 Engagement and retention

| Item | Files |
|---|---|
| **Daily streak system** — `streak_days` + `streak_at_risk` in `GET /api/auth/me`; surface in topbar; milestone toasts. | `backend/db.py`, `backend/routers/auth.py`, [AppShell.js](frontend/src/components/AppShell.js) |
| **Motion and transitions** — animated progress bars, first-solve celebration, unlock toasts, route fade-ins, milestone toasts. | [App.css](frontend/src/App.css), [TrackProgressBar.js](frontend/src/components/TrackProgressBar.js) |
| **Skeleton loaders** — reusable skeleton primitive + shimmer animation for `QuestionPage`, `SidebarNav`, `TrackHubPage`, `ProgressDashboard`. | `components/Skeleton.js` (new), affected pages |

### 7.4 Discovery and onboarding

| Item | Files |
|---|---|
| **Onboarding walkthrough** — first-visit tooltips for track selection and sample questions; visible skip. | `components/OnboardingTooltip.js` (new), [TrackHubPage.js](frontend/src/pages/TrackHubPage.js) |
| **Question search** — client-side full-text search over title + description + concepts via `fuse.js` in sidebar. | [SidebarNav.js](frontend/src/components/SidebarNav.js) |
| **Accessibility baseline** — full keyboard reachability, visible focus rings, icon-button labels, non-color states, Monaco `aria-label`, Lighthouse a11y ≥ 90. | [AppShell.js](frontend/src/components/AppShell.js), [App.css](frontend/src/App.css) |

### 7.5 Platform foundations

| Item | Files |
|---|---|
| **React Query adoption** — migrate `catalogContext.js`, `QuestionPage`, `ProgressDashboard` first. | `frontend/package.json`, [App.js](frontend/src/App.js) |
| **TypeScript migration** — incremental; `tsconfig.json`; centralize API types in `frontend/src/types/api.ts`. | `frontend/tsconfig.json`, `frontend/vite.config.js` |
| **Observability** — Sentry (frontend + backend), PostHog event tracking for question / sample / mock / plan-upgrade funnels. | `backend/main.py`, `frontend/src/App.js` |
| **SEO** — static meta tags, `react-helmet-async`, `robots.txt`, `sitemap.xml`; prerender landing page. | `frontend/index.html`, `backend/routers/system.py` |
| **CI/CD pipeline** — deploy on merge, validate question JSON, dependency audit, ESLint, bundle-size budget. | `.github/workflows/ci.yml` |
| **Security hardening** — HTTPS enforcement, security headers, CSRF review, account-lockout policy. | `backend/main.py`, auth flow |
| **DB pool tuning** — make asyncpg pool sizing configurable in `config.py`. | `backend/config.py`, `backend/db.py` |

### 7.6 Community and profiles (Phase 6)

| Item | Notes |
|---|---|
| **`/profile` page** | Profile header, badges, per-track stats, mock history, activity heatmap |
| **`/leaderboard`** | Weekly / all-time, per-track filter, opt-in visibility |
| **Achievement badges** | Computed from submissions + mock sessions (SQL Starter, Speed Demon, 7-Day Streak…) |
| **Discussion threads** | Per-question flat threads — no voting, no nesting until core is stable |
| **Internal question management** | Choose between `/admin` UI and GitHub/CI editing workflow |

---

## 8. Verification contract (applies to every phase)

Each phase commit must:

1. Pass `cd backend && ../.venv/bin/python -m pytest tests/ -q`.
2. Manual walk of every changed surface: **light + dark** × **logged-in + logged-out** × **1440px + 900px + 560px**.
3. Keyboard-tab through every changed interactive surface. Focus rings visible.
4. `prefers-reduced-motion` emulated → no new motion, no broken tab activation.
5. Docs synced in the same commit per CLAUDE.md rules.
6. Commit on `main` with `Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>`.

---

## 9. Progress tracker

### Phase 1 — Stop the bleed ✓

- [x] 1.1 Extend ThemeContext (`isDark`, `cycleTheme`, `themeIcon`, `themeLabel`)
- [x] 1.2 Consolidate dark-mode CSS + pre-hydration script in `index.html`
- [x] 1.3 Unified `<Topbar>` with slots; migrate AppShell + 4 pages
- [x] 1.4 `LoggedInWelcome` block on landing
- [x] 1.5 Pricing link in unauthenticated topbar + `id="landing-pricing"` anchor
- [x] 1.6 `NotFoundPage` CTA conditional on auth state
- [x] Phase 1 docs sync + commit

### Phase 2 — Tighten the funnel ✓

- [x] 2.1 Pricing tier copy with hard numbers + real question counts
- [x] 2.2 Sample-exhausted state CTA ("You've seen all 3…")
- [x] 2.3 `.landing-proof-row` trust signal above showcase
- [x] 2.4 OAuth buttons: remove `disabled`, use `.auth-oauth-btn--coming-soon`
- [x] 2.5 `VerifyEmailPage`: 24h expiry note, spam-folder line, resend button
- [x] 2.6 Signup `passwordConfirm` field with blur validation + disabled submit
- [x] 2.7 Replace `'#5B6AF0'` fallbacks with `var(--accent)`
- [x] Phase 2 docs sync + commit

### Phase 3 — Workspace power polish ✓

- [x] 3.1 Keyboard shortcut badges (`⌘↵` / `⌘⇧↵`) + `?` help popover
- [x] 3.2 Results table: sticky header + horizontal-scroll cue
- [x] 3.3 Schema viewer: search + click-to-copy columns
- [x] 3.4 Submit double-click protection
- [x] 3.5 Solution-reveal button inside verdict card header
- [x] 3.6 Sidebar unlock thresholds: dynamic per-track copy
- [x] 3.7 Past-attempts panel expanded on return visit
- [x] 3.8 Secondary-button contrast ≥ 4.5:1 in dark chrome
- [x] Phase 3 docs sync + commit

### Phase 4 — Meta depth

- [x] 4.0 `GET /api/dashboard/insights` endpoint + tests
- [x] 4.1 Fetch + render insights in `ProgressDashboard`
- [x] 4.2 `InsightStrip` component (3 tiles)
- [x] 4.3 Per-track cards: median solve time + accuracy
- [x] 4.4 Mock summary: session comparison header
- [x] 4.5 Mock summary: per-concept accuracy row
- [x] 4.6 Mock summary: "Drill weak concepts" CTA + sidebar `?concepts=` param
- [x] 4.7 Path completion celebration banner
- [x] 4.8 Path index: "In progress" rail
- [x] 4.9 Empty states on dashboard, mock, learn
- [x] Phase 4 docs sync + commit

### Polish batch (after Phase 4)

- [ ] Sample-section copy tighten
- [ ] Em-dash consistency in pricing CTAs
- [ ] Skeleton loaders (sample page, solution analysis)
- [ ] Landing tab `sessionStorage` → `localStorage`
- [ ] `ErrorBoundary` mailto link
- [ ] Path breadcrumb nav via sidebar
- [ ] Showcase `prefers-reduced-motion` in initial state

---

## 10. Hand-off notes

Resume by:

1. Read §9 (Progress tracker) — find the first unchecked box.
2. Read the corresponding phase section (§4 = Phase 3, §5 = Phase 4) for the full spec.
3. Check the relevant source files before writing any code — the spec was written pre-implementation and details may have shifted.
4. Don't skip ahead.

If anything in §2 (architecture decisions) looks wrong given current code, pause and ask the owner before reinventing. §2 is binding.


---

