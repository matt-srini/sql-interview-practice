# Path to World-Class — Experience Upgrade Plan

> Living document. Update the **Progress tracker** at the bottom as work lands.
> This doc is the hand-off contract — an agent should be able to resume by reading this alone.

---

## 0. Context

The landing-showcase redesign shipped ("The Interview IDE"). An experience audit of the full repo followed, run by three Explore agents plus spot-verification. This plan is the agreed multi-phase path from the current 70% polished state to a world-class premium interview-practice platform (benchmarks: Linear, Vercel, Stripe, Raycast, LeetCode Premium, DataLemur).

**Explicitly out of scope (owner decision):**

- **Question content quality / difficulty calibration** — addressed in a separate pass.
- **Brand identity, icon primitive, strict spacing tokens, motion grammar, full a11y audit** (Phase 5). Deferred to a design-led workstream.
- **Monaco editor stays always-dark.** Same for the landing-showcase IDE window. Both are intentional per [CLAUDE.md](CLAUDE.md) and recent owner direction.

**In scope (this plan):** Phases 1–4, sequential. Each phase = one commit minimum, co-authored per CLAUDE.md.

---

## 1. Top-of-mind verdict

**Four weakness clusters:**

1. **Unfinished corners** — crashes on the 404 page, fragmented dark-mode CSS, two divergent topbar implementations, hardcoded color fallbacks.
2. **Funnel clarity** — pricing hidden below the fold, tier copy vague, sample→pro transition confusing, zero trust signals, blank hero for logged-in visitors.
3. **Meta-experience depth** — `/dashboard` is a ledger (not a coach), mock summary is a results dump (not a post-mortem), path completion silently grants unlocks, empty states are flat.
4. **Workspace power-user polish** — keyboard shortcuts invisible, wide tables silently truncated, schema viewer unsearchable, inconsistent rhythm, low-contrast chrome buttons.

---

## 2. Confirmed blockers (verified in code)

| Id | Issue | Evidence | Fix location |
|---|---|---|---|
| **B1** | `useTheme()` crash on 4 pages — destructure `cycleTheme`, `themeIcon`, `themeLabel` from a context that only exposes `{ theme, setTheme }`. | [App.js:22-49](frontend/src/App.js), [NotFoundPage.js:6](frontend/src/pages/NotFoundPage.js), [AuthPage.js:83](frontend/src/pages/AuthPage.js), [VerifyEmailPage.js](frontend/src/pages/VerifyEmailPage.js), [ResetPasswordPage.js](frontend/src/pages/ResetPasswordPage.js) | Extend `ThemeContext` value in [App.js:32-49](frontend/src/App.js). |
| **B2** | Dark-mode CSS fragmented — 2× `@media (prefers-color-scheme: dark)` blocks + 88× `[data-theme="dark"]` rules can conflict on first paint. | [App.css:3615, 4587](frontend/src/App.css) and 88 selectors. | Remove the `@media` blocks; set `data-theme` eagerly via `index.html` pre-hydration script. |
| **B3** | Two topbar implementations drift — `Topbar.js` (150 LOC) and the inline topbar in `AppShell.js` (350 LOC). Different dropdown behavior, plan pill only in shell, different padding. | [Topbar.js](frontend/src/components/Topbar.js), [AppShell.js:178-275](frontend/src/components/AppShell.js) | Extract `Topbar` to a composable shell with slots; refactor AppShell to pass slots. |
| **B4** | Logged-in users see a blank hero on `/`. Entire hero is gated on `!user`. | [LandingPage.js:288-303](frontend/src/pages/LandingPage.js) | Add a "Welcome back" block under the same conditional, or restructure so the hero has both states. |

---

## 3. Architecture decisions (binding for implementing agents)

### 3.1 Theme context

Single source of truth in [`App.js`](frontend/src/App.js):

```js
// ThemeContext value (final shape after Phase 1.1)
{
  theme: 'light' | 'dark',
  setTheme: (value: 'light' | 'dark') => void,
  isDark: boolean,
  cycleTheme: () => void,                 // toggles between light/dark
  themeIcon: '☀' | '☾',                  // character shown on toggle button
  themeLabel: string,                     // aria-label + title for the toggle
}
```

All consumers import from `../App` (existing pattern). Local `isDark`/`themeIcon`/`themeLabel` derivations in `Topbar.js` and `AppShell.js` are removed; they pull from context instead.

### 3.2 Dark-mode consolidation

- **Source of truth:** `[data-theme="dark"]` CSS selectors (88 existing rules).
- **Remove:** both `@media (prefers-color-scheme: dark) { :root { ... } }` blocks in [`App.css`](frontend/src/App.css) (line 3615 and line 4587).
- **Prevent FOUC:** add a 6-line bootstrap script to `<head>` in [`frontend/index.html`](frontend/index.html) that sets `data-theme` from `localStorage.theme || matchMedia('(prefers-color-scheme: dark)')` BEFORE React mounts. Script must run synchronously (no `async`/`defer`).
- **Keep** the existing `ThemeProvider` `useEffect` that syncs attribute on change — this handles runtime toggles.
- Any token that existed only in the `@media` block but not in the `[data-theme="dark"]` block must be ported over before deletion.

### 3.3 Unified Topbar

Single `<Topbar>` component used by every page, with composition slots:

```jsx
<Topbar
  active={'mock' | 'dashboard' | null}   // highlight a nav link
  leftSlot={ReactNode}                   // appears in brand row (AppShell: mobile sidebar toggle)
  centerSlot={ReactNode}                 // appears centered (AppShell: mode pill "SQL · Challenge")
  userExtras={ReactNode}                 // appears before user name (AppShell: plan pill "Pro")
  belowTopbar={ReactNode}                // extra row under topbar (AppShell: upgrade banner)
  showPricingLink={boolean}              // for logged-out visitors (Phase 1.5)
/>
```

**Refactor plan:**

1. Rewrite `Topbar.js` to accept the slots above. Keep the existing unauthenticated/authenticated branches and the verify-email banner logic.
2. `AppShell.js` renders `<Topbar leftSlot={sidebarToggle} centerSlot={modePill} userExtras={planPill} belowTopbar={upgradeBanner} />` and drops ~90 lines of inline JSX.
3. `AuthPage.js`, `NotFoundPage.js`, `VerifyEmailPage.js`, `ResetPasswordPage.js` — each currently has inline topbar JSX. Replace with `<Topbar />` and remove local theme-toggle wiring.
4. `LandingPage.js` already uses `<Topbar />` — pass `showPricingLink` when `!user`.

**Slot composition guarantee:** `Topbar` renders in this order left-to-right:
`[brand] [leftSlot] ··· [centerSlot] ··· [nav-dropdown] [Mock] [Dashboard] [Pricing?] [themeToggle] [sep] [userExtras] [user-pill | sign-in]`

### 3.4 Welcome-back block (Phase 1.4)

Replace `!user && <hero>` with:

```jsx
{user ? <LoggedInWelcome user={user} /> : <MarketingHero />}
```

**`LoggedInWelcome` requirements:**

- Greets by `user.name || user.email`.
- Shows three cards horizontally (stacks under 900px): **Resume** (last-answered question if known, else last-active track), **Dashboard** link, **Mock** link.
- "Last question" is determined via `GET /api/submissions?limit=1` — falls back to dashboard if none.
- Reuses existing `.landing-hero-inner` spacing tokens so the vertical rhythm is unchanged.
- Skeleton-loads the resume card while the submission fetch is in flight (no layout shift).

### 3.5 Pricing link in topbar (Phase 1.5)

- Only shown when `!user && showPricingLink`.
- Renders as `<a href="#landing-pricing">Pricing</a>` on the landing page (smooth-scroll anchor) and as `<Link to="/#landing-pricing">Pricing</Link>` on non-landing logged-out pages.
- Requires adding `id="landing-pricing"` to the pricing section in [LandingPage.js](frontend/src/pages/LandingPage.js) (currently unanchored).

---

## 4. Phase 1 — Stop the bleed (~1 day)

**Goal:** nothing unfinished visible to a first-time visitor or returning user.

| # | Task | Files | Acceptance |
|---|---|---|---|
| 1.1 | Extend ThemeContext with `isDark`, `cycleTheme`, `themeIcon`, `themeLabel`. | [App.js](frontend/src/App.js) | All 4 pages that destructure these render without crashing. |
| 1.2 | Consolidate dark-mode CSS. Remove `@media prefers-color-scheme` blocks after porting any missing tokens into `[data-theme="dark"]`. Add pre-hydration bootstrap script in `index.html`. | [App.css](frontend/src/App.css), [frontend/index.html](frontend/index.html) | No theme flash on load; dark-system / light-explicit users see light from the first frame. |
| 1.3 | Unified `<Topbar>` with slots; migrate AppShell + AuthPage + NotFoundPage + VerifyEmailPage + ResetPasswordPage to use it. | [Topbar.js](frontend/src/components/Topbar.js), [AppShell.js](frontend/src/components/AppShell.js), 4 pages | One component owns the nav shell. AppShell loses ~90 LOC of inline topbar JSX. |
| 1.4 | Logged-in landing: `LoggedInWelcome` block with Resume / Dashboard / Mock cards. | [LandingPage.js](frontend/src/pages/LandingPage.js), `components/LoggedInWelcome.js` (new) | `/` for a logged-in user shows a real welcome panel, not negative space. |
| 1.5 | Add `Pricing` link to unauthenticated topbar; add `id="landing-pricing"` anchor. | [Topbar.js](frontend/src/components/Topbar.js), [LandingPage.js](frontend/src/pages/LandingPage.js) | Logged-out visitor can jump to pricing from any page. |
| 1.6 | `NotFoundPage` CTA: "Start practising" → "Sign in" when logged-out. | [NotFoundPage.js](frontend/src/pages/NotFoundPage.js) | Unauthenticated visitor doesn't hit the auth wall from the 404 page. |

**Verification (all of):**

- `preview_screenshot` each of: `/`, `/auth`, `/nonexistent`, `/mock`, `/dashboard`, `/practice/sql` — both themes, both auth states.
- `preview_eval` DOM: `.topbar` exists and is identical across pages (same class list, same structure).
- `document.documentElement.getAttribute('data-theme')` matches localStorage on first paint (no flicker).
- 900px and 560px viewports render correctly.
- `cd backend && ../.venv/bin/python -m pytest tests/ -q` green.
- Update [docs/frontend.md](docs/frontend.md): topbar description, theme context.
- Commit with `Co-Authored-By: Claude Opus 4.7`.

---

## 5. Phase 2 — Tighten the funnel (~1 day)

**Goal:** convert more visitors; stop leaking first-time users in the sample → pro funnel.

| # | Task | Files | Architectural note |
|---|---|---|---|
| 2.1 | Rewrite pricing tier copy with hard numbers. Free = 95 easy SQL + unlock path. Pro = all 350 questions + 3 mock/day. Elite = everything + company filter. Use [TRACK_DIFFICULTIES](frontend/src/pages/LandingPage.js:14) as the source for counts. | [LandingPage.js](frontend/src/pages/LandingPage.js) | Hard-coded counts; no runtime fetch. |
| 2.2 | Sample-exhausted state copy: "You've seen all 3 {difficulty} samples. Ready for the full {n}-question {track} track? Pro unlocks it." | [SampleQuestionPage.js](frontend/src/pages/SampleQuestionPage.js) | Reuse `TRACK_DIFFICULTIES` for `n`. |
| 2.3 | One trust signal above the fold — real or placeholder: three visible metrics row ("X questions · Y concepts · Z minutes of practice"). NOT fabricated testimonials. | [LandingPage.js](frontend/src/pages/LandingPage.js) | New `.landing-proof-row` between hero and showcase. |
| 2.4 | OAuth disabled UX: pick one affordance (visible `coming-soon` pill + grayed label), drop the `disabled` attribute + tooltip. | [AuthPage.js](frontend/src/pages/AuthPage.js) | Buttons remain clickable (no-op) to preserve hover affordance; or make them not buttons (`<span>`). |
| 2.5 | Email verification page: add spam-folder line + "link expires in 24h" + working resend button. | [VerifyEmailPage.js](frontend/src/pages/VerifyEmailPage.js) | Reuses the existing `/api/auth/resend-verification` endpoint. |
| 2.6 | Signup: client-side password-confirm validation before hitting the API. | [AuthPage.js](frontend/src/pages/AuthPage.js) | Add `passwordConfirm` field + inline error on blur. Submit disabled when mismatch. |
| 2.7 | Replace hardcoded `'#5B6AF0'` fallbacks with `var(--accent)`. | [LandingPage.js:244](frontend/src/pages/LandingPage.js) + grep for other instances | Simple find/replace; no behavioral change. |

**Verification:**

- Pricing section: mobile (375px) and desktop screenshots show real numbers.
- Sample exhausted state: visit `/sample/sql/easy` three times to trigger; check copy.
- Signup password-confirm: submit with mismatched passwords; observe client-side error.
- Backend: no new endpoints; tests unchanged.
- Commit + docs sync.

---

## 6. Phase 3 — Workspace power polish (~2 days)

**Goal:** workspace feels like a tool, not a prototype.

| # | Task | Files | Architectural note |
|---|---|---|---|
| 3.1 | Inline `⌘↵` / `⌘⇧↵` badges on Run and Submit buttons; add a `?` shortcut help popover in the workspace chrome. | [QuestionPage.js](frontend/src/pages/QuestionPage.js), [App.css](frontend/src/App.css) | Badge = `<kbd>` element; popover can reuse existing modal/backdrop primitive if present, else a simple `<details>`. |
| 3.2 | Results table: sticky first header row; horizontal-scroll cue ("→ X more columns") when `scrollWidth > clientWidth`. Listen via `ResizeObserver`. | [ResultsTable.js](frontend/src/components/ResultsTable.js), [App.css](frontend/src/App.css) | `position: sticky; top: 0` on `<thead>`; add `.results-table-scroll-cue` that fades in when overflow is present. |
| 3.3 | Schema viewer: add search input; click-to-copy column names. | [SchemaViewer.js](frontend/src/components/SchemaViewer.js) | Client-only filter (table names + column names). Clipboard API for copy. |
| 3.4 | Submit double-click protection: set the submitting state synchronously before the API call (not inside `.then`). | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Guard with `if (submitting) return;` at function top. |
| 3.5 | Solution-reveal button placement: render inside the verdict card header, not below feedback. | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Re-order existing JSX; no new state. |
| 3.6 | Sidebar unlock-nudge copy: compute thresholds dynamically per track from the catalog payload (currently hardcoded "10 easy / 10 medium"). | [AppShell.js:300-304](frontend/src/components/AppShell.js) | Backend already exposes unlock state per question; surface the thresholds (or approximate them from the first locked question's `unlock_requirement` string if available). Worst case: hardcode per-track map matching [unlock.py](backend/unlock.py). |
| 3.7 | Past-attempts panel expanded by default on second visit to the same question (persist via `localStorage.last_seen_question_id`). | [QuestionPage.js](frontend/src/pages/QuestionPage.js) | Simple localStorage key; no backend change. |
| 3.8 | Secondary-button contrast in dark editor chrome: raise `rgba(255,255,255,0.07)` to `rgba(255,255,255,0.14)` OR add `1px solid rgba(255,255,255,0.12)`. Verify against WCAG AA (4.5:1). | [App.css:2725-2735](frontend/src/App.css) | Use contrast checker in dev-tools. |

**Verification:**

- Keyboard: `⌘↵` runs, `⌘⇧↵` submits, `?` toggles help — all on both SQL and Python workspaces.
- Results table at 800px viewport with 12-column result shows the scroll cue and sticky header.
- Schema viewer search filters both tables and columns.
- Submit rapid double-click produces only one submission (check network tab).
- Contrast: measure in Chrome devtools → buttons ≥ 4.5:1 on dark chrome.
- Commit + docs sync.

---

## 7. Phase 4 — Meta depth (~3 days, includes new backend)

**Goal:** `/dashboard` coaches, `/mock` summarizes with insight, path completion is a moment.

### 7.1 Backend: new `/api/dashboard/insights` endpoint

**File:** [backend/routers/](backend/routers/) — new `insights.py` router, registered in [backend/main.py](backend/main.py).

**Endpoint:** `GET /api/dashboard/insights` (auth required).

**Response shape:**

```json
{
  "per_track": {
    "sql":          { "solve_count": 28, "median_solve_seconds": 512, "accuracy_pct": 0.82 },
    "python":       { "solve_count": 12, "median_solve_seconds": 740, "accuracy_pct": 0.71 },
    "python-data":  { "solve_count": 5,  "median_solve_seconds": 930, "accuracy_pct": 0.80 },
    "pyspark":      { "solve_count": 18, "median_solve_seconds": 120, "accuracy_pct": 0.88 }
  },
  "weakest_concepts": [
    { "concept": "window functions", "track": "sql", "attempts": 8, "correct": 3, "accuracy_pct": 0.375 },
    { "concept": "dynamic programming", "track": "python", "attempts": 5, "correct": 2, "accuracy_pct": 0.40 }
  ],
  "cross_track_insight": "You solve Python ~4 minutes slower than SQL. Try 3 Python mediums to close the gap.",
  "streak_days": 7
}
```

**Implementation notes:**

- Aggregates from the existing `submissions` table (no schema changes required).
- `median_solve_seconds` = median of `created_at - question_started_at` over correct submissions, per track.
- `weakest_concepts` = group submissions by question's `concepts[]` (client-side join with catalog), compute accuracy, return bottom 3 with ≥3 attempts.
- `cross_track_insight` = deterministic text template based on the largest gap in `median_solve_seconds`; if no gap > 60s, return null.
- `streak_days` = distinct days with ≥1 correct submission, ending today; 0 if today has none.
- Cache in-process for 60s per user_id.

**Tests:** [backend/tests/test_dashboard_insights.py](backend/tests/) — at minimum: auth required, empty-state response (new user), populated response, cache behavior.

### 7.2 Frontend: Dashboard → coach

| # | Task | Files |
|---|---|---|
| 4.1 | Fetch insights on mount; render above existing "Track overview" cards. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js) |
| 4.2 | New component `InsightStrip` with 3 tiles: cross-track insight sentence, streak, weakest concept. | `components/InsightStrip.js` (new) |
| 4.3 | Per-track cards gain "median solve time" and "accuracy" rows. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js) |

### 7.3 Frontend: Mock → post-mortem

| # | Task | Files |
|---|---|---|
| 4.4 | Mock summary header: add "X/Y correct, Z% above your session average" (reuses insights endpoint). | [MockSession.js](frontend/src/pages/MockSession.js) |
| 4.5 | Per-concept accuracy row: list concepts touched this session with ✓ / ✗ counts. Concepts come from question metadata already attached to session. | [MockSession.js](frontend/src/pages/MockSession.js) |
| 4.6 | "Drill weak concepts" CTA button → links to `/practice/{track}?concepts={slug1,slug2}` (requires sidebar to honor `?concepts=` query — Phase 3 side quest if not already implemented). | [MockSession.js](frontend/src/pages/MockSession.js), [SidebarNav.js](frontend/src/components/SidebarNav.js) |

### 7.4 Frontend: Path completion + empty states

| # | Task | Files |
|---|---|---|
| 4.7 | Path page: when `solved_count === question_count`, show a completion banner with "🎉 Path complete!" + "What's next" CTA → path index filtered to same track. Celebration banner uses existing `.app-banner-success` primitive or a new `.path-celebration` class. | [LearningPath.js](frontend/src/pages/LearningPath.js) |
| 4.8 | Path index: partition into "In progress" (1 ≤ solved < total, sorted by `solved / total` desc) and "All paths" (rest). Add a "Continue where you left off" rail above the grid when in-progress exists. | [LearningPathsIndex.js](frontend/src/pages/LearningPathsIndex.js) |
| 4.9 | Real empty states with CTAs across `/dashboard`, `/mock`, `/learn`. | [ProgressDashboard.js](frontend/src/pages/ProgressDashboard.js), [MockHub.js](frontend/src/pages/MockHub.js), [LearningPathsIndex.js](frontend/src/pages/LearningPathsIndex.js) |

**Verification:**

- New endpoint: `curl -H 'Cookie: session=...' localhost:8000/api/dashboard/insights` returns valid JSON for an authenticated user.
- Dashboard: populated user sees InsightStrip + enhanced cards. Brand-new user sees a different "start solving to unlock insights" empty state.
- Mock: finish a session, summary shows concept accuracy + comparison sentence.
- Path completion: solve the last question in any path, refresh, see celebration banner.
- Backend tests pass.
- Commit + docs sync: [docs/backend.md](docs/backend.md) new endpoint, [docs/frontend.md](docs/frontend.md) dashboard+mock changes, [CLAUDE.md](CLAUDE.md) API table.

---

## 8. Polish backlog (single commit at the end)

Batch these after Phase 4 lands:

- Topbar brand class naming consistency (`landing-brand` → `brand-wordmark`).
- Long defensive sample-section copy ("no account required, no progress recorded") → tighten to one line.
- Em-dash vs hyphen consistency in pricing CTAs.
- Loading skeletons for sample page, solution analysis.
- Landing tab state: `sessionStorage` → `localStorage` for stickiness.
- Remove stale `docs/frontend.md:83` verdict-string claim (the string was removed earlier).
- Add mailto: to ErrorBoundary "contact us".
- Path-nav-bar visible even when user navigates via sidebar (not just from `/learn/...`).
- Showcase: move `prefers-reduced-motion` check into initial state.

---

## 9. Verification contract (applies to every phase)

Each phase commit must:

1. Pass `cd backend && ../.venv/bin/python -m pytest tests/ -q` (existing tests + any new ones added in the phase).
2. Pass manual walk of every changed surface at **light + dark** × **logged-in + logged-out** × **1440px + 900px + 560px** viewports. Use `preview_screenshot` + `preview_eval` for DOM spot-checks.
3. Keyboard-tab through every changed interactive surface. Focus rings visible.
4. `prefers-reduced-motion` emulated in devtools → no new motion, no broken tab activation.
5. Update [docs/frontend.md](docs/frontend.md) (and [docs/backend.md](docs/backend.md) + [CLAUDE.md](CLAUDE.md) if backend touched) in the same commit per CLAUDE.md sync rule.
6. Commit on `main` with message describing the change and `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>`.

---

## 10. Scope decisions (confirmed, binding)

1. **Phases 1 → 4 execute sequentially.** Phase 5 (brand + system + a11y audit) is deferred to a separate workstream.
2. **Phase 4 extends the backend.** New `/api/dashboard/insights` endpoint aggregates per-concept accuracy, time-to-solve medians, weak-area detection, streak. Client stays thin.
3. **Question content quality is separately owned.** Not addressed here.
4. **Monaco and landing-showcase IDE stay always-dark.** Intentional per CLAUDE.md and owner confirmation on 2026-04-20.

---

## 11. Non-issues (verified as intentional — do NOT "fix")

- **Monaco editor theme = `vs-dark` always.** CLAUDE.md: "the two-tone editor (always dark)."
- **Landing-showcase IDE window is dark in both themes.** Owner confirmed; Linear/Vercel/Stripe pattern.

---

## 12. Progress tracker

Update checkboxes as work lands. Do not delete completed items — the tracker is the audit trail.

### Phase 1 — Stop the bleed

- [x] 1.1 Extend ThemeContext (`isDark`, `cycleTheme`, `themeIcon`, `themeLabel`) — [App.js](frontend/src/App.js)
- [x] 1.2 Consolidate dark-mode CSS + enhance `index.html` bootstrap script (matchMedia fallback) — [App.css](frontend/src/App.css), [frontend/index.html](frontend/index.html)
- [x] 1.3 Unified `<Topbar>` with slots; migrate AppShell + 4 pages — [Topbar.js](frontend/src/components/Topbar.js), [AppShell.js](frontend/src/components/AppShell.js), [AuthPage.js](frontend/src/pages/AuthPage.js), [NotFoundPage.js](frontend/src/pages/NotFoundPage.js), [VerifyEmailPage.js](frontend/src/pages/VerifyEmailPage.js), [ResetPasswordPage.js](frontend/src/pages/ResetPasswordPage.js)
- [x] 1.4 Logged-in `LoggedInWelcome` block on landing — [LandingPage.js](frontend/src/pages/LandingPage.js), [components/LoggedInWelcome.js](frontend/src/components/LoggedInWelcome.js)
- [x] 1.5 Pricing link in unauthenticated topbar + anchor on landing — [Topbar.js](frontend/src/components/Topbar.js), [LandingPage.js](frontend/src/pages/LandingPage.js)
- [x] 1.6 NotFoundPage CTA conditional on `user` — [NotFoundPage.js](frontend/src/pages/NotFoundPage.js)
- [x] Phase 1 verification + docs sync — [docs/frontend.md](docs/frontend.md)
- [x] Phase 1 commit

### Phase 2 — Tighten the funnel

- [ ] 2.1 Pricing tier copy with hard numbers
- [ ] 2.2 Sample-exhausted state concrete CTA
- [ ] 2.3 Above-the-fold trust signal (metrics row)
- [ ] 2.4 OAuth disabled UX simplification
- [ ] 2.5 Verify-email copy improvements
- [ ] 2.6 Signup password-confirm client-side
- [ ] 2.7 Remove hardcoded color fallbacks
- [ ] Phase 2 verification + docs sync
- [ ] Phase 2 commit

### Phase 3 — Workspace power polish

- [ ] 3.1 Keyboard shortcut badges + `?` help popover
- [ ] 3.2 Results table sticky header + horizontal-scroll cue
- [ ] 3.3 Schema viewer search + click-to-copy columns
- [ ] 3.4 Submit double-click protection
- [ ] 3.5 Solution-reveal in verdict card header
- [ ] 3.6 Dynamic sidebar unlock thresholds (track-aware)
- [ ] 3.7 Past-attempts expanded on return visit
- [ ] 3.8 Secondary-button contrast in dark chrome (WCAG AA)
- [ ] Phase 3 verification + docs sync
- [ ] Phase 3 commit

### Phase 4 — Meta depth

- [ ] 4.0 New `/api/dashboard/insights` endpoint + tests
- [ ] 4.1 Fetch insights in `ProgressDashboard`
- [ ] 4.2 `InsightStrip` component (3 tiles)
- [ ] 4.3 Per-track cards: median solve time + accuracy
- [ ] 4.4 Mock summary: session comparison header
- [ ] 4.5 Mock summary: per-concept accuracy
- [ ] 4.6 Mock summary: "Drill weak concepts" CTA + sidebar `?concepts=` query param
- [ ] 4.7 Path completion celebration banner
- [ ] 4.8 Path index: "In progress" rail + sort
- [ ] 4.9 Real empty states (dashboard, mock, paths)
- [ ] Phase 4 verification + docs sync
- [ ] Phase 4 commit

### Polish backlog

- [ ] Polish batch commit (see §8)

---

## 13. Hand-off notes for the next agent

If the last known commit is Phase 1 partial, resume by:

1. Reading this doc top to bottom.
2. Checking the progress tracker — find the first unchecked box.
3. Re-verifying the assumption from §3 that still stands (read the corresponding source files).
4. Continue from that task. Don't skip ahead.

If anything in §3 (architecture decisions) looks wrong given the current code state, pause and ask the owner before reinventing. §3 is binding — it was negotiated up-front.
