# Frontend

> **Navigation:** [Docs index](./README.md) · [Project blueprint](./project-blueprint.md) · [Backend](./backend.md) · [UI design system](./ui-design-system.md)

React 18 + React Router + Vite. Monaco editor. Axios API client. Single global stylesheet (`App.css`) with CSS custom properties.

---

## Route tree

Defined in `frontend/src/App.js`:

```
/                          → LandingPage
/auth                      → AuthPage (register / sign in)
/sample/:difficulty        → SampleQuestionPage
/practice                  → AppShell (with CatalogProvider)
  /practice/questions/:id  → QuestionPage
/questions/:id             → redirect → /practice/questions/:id
```

---

## Pages

### LandingPage (`/`)
Entry point for both tracks. Centered hero with a headline, one-line description, and two primary CTAs ("Start the challenge" → `/practice`, "Try a sample" → `/sample/easy`). Below the hero, three sample tiles link directly to `/sample/easy`, `/sample/medium`, and `/sample/hard`. Topbar shows "Sign in" for anonymous visitors or the user's name + sign-out for authenticated users.

### AuthPage (`/auth`)
Register or sign in with email/password. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress can be merged into an existing account.

### QuestionPage (`/practice/questions/:id`)
Main practice screen. Two-column layout: sticky left panel (description + schema) + right panel (editor + results).

- Loads question detail from `/api/questions/:id`
- 403 response → shows locked callout
- Run → calls `/api/run-query`, shows results table
- Submit → calls `/api/submit`, shows verdict inline
- On correct: `refresh()` called on catalog context so sidebar unlock state updates immediately
- Post-submit: verdict + feedback wrapped in `.submit-outcome` container; hints revealed one at a time; solution button appears only after all hints shown

**Minimal chrome approach:** No section kickers on prompt or schema cards (content is self-evident from titles and badges). Editor topbar is a single line ("SQL editor" left, "DuckDB sandbox" right). Editor footer is buttons-only, right-aligned — no instructional text.

### SampleQuestionPage (`/sample/:difficulty`)
Standalone sample practice. Same editor layout as QuestionPage but no sidebar.

- Loads next unseen sample from `/api/sample/:difficulty`
- Shows sample counter (e.g. "2 of 3 · Easy")
- 409 response → exhaustion card with reset option
- Reset → calls `/api/sample/:difficulty/reset`, re-fetches
- Does not affect challenge progression

---

## Components

| Component | File | Purpose |
|---|---|---|
| AppShell | `components/AppShell.js` | Challenge workspace shell: sticky topbar, collapsible sidebar, upgrade panel |
| SidebarNav | `components/SidebarNav.js` | Question list grouped by difficulty; lock/next/solved states; active question highlight |
| SQLEditor | `components/SQLEditor.js` | Monaco editor wrapper (vs-dark, JetBrains Mono 14px, no minimap) |
| ResultsTable | `components/ResultsTable.js` | Tabular query results with sticky headers and null value rendering |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema — table names and column token grid |

### AppShell
- Desktop: sidebar 328px, collapsible via toggle (display:none on `sidebar-collapsed`)
- Mobile (<900px): sidebar becomes fixed overlay with backdrop
- Upgrade panel shown for `free` and `pro` plan users
- Handles `?upgraded=true` query param from Stripe redirect to trigger catalog + user refresh

### SidebarNav
- Collapsible difficulty groups (easy open by default, medium/hard collapsed)
- Per-question state: `unlocked`, `locked`, `solved`, `next`, `current`
- Active question highlighted with left accent border
- Test coverage in `components/SidebarNav.test.js`

---

## Shared state

### `catalogContext.js`
- Wraps the practice shell with `CatalogProvider`
- Fetches `/api/catalog` on mount
- Exposes `{ catalog, loading, error, refresh }`
- `refresh()` called after correct submission to update unlock state

### `contexts/AuthContext.js`
- Provides `{ user, loading, refreshUser }`
- Fetches `/api/auth/me` on mount
- Used by AppShell to show plan pill and upgrade controls

---

## API client

`frontend/src/api.js` — Axios instance with base URL resolution:

1. If `VITE_BACKEND_URL` env var is set → use that origin + `/api`
2. If on `localhost` without same-origin backend → fall back to `http://localhost:8000/api`
3. Otherwise → same-origin `/api`

All requests use `withCredentials: true` so the `session_token` cookie is sent during cross-origin local development.

---

## Data flows

### Challenge flow
1. `/practice` → `CatalogProvider` fetches catalog
2. `AppShell` renders layout; auto-navigates to first `is_next` question
3. Question route → fetch `/api/questions/:id`
4. User runs SQL → `POST /api/run-query` → results table appears
5. User submits → `POST /api/submit` → verdict + compare grid + hints/solution
6. On correct → `refresh()` → sidebar unlock state updates

### Sample flow
1. `/sample/:difficulty` → `GET /api/sample/:difficulty`
2. Backend marks sample as seen and returns question
3. Run/submit via `/api/sample/run-query` and `/api/sample/submit`
4. 409 on exhaustion → reset button → `POST /api/sample/:difficulty/reset` → re-fetch
5. No effect on challenge progress
