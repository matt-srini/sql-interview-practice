# Frontend

> **Navigation:** [Docs index](./README.md) · [Project blueprint](./project-blueprint.md) · [Backend](./backend.md) · [UI design system](./ui-design-system.md)

React 18 + React Router + Vite. Monaco editor. Axios API client. Single global stylesheet (`App.css`) with CSS custom properties.

---

## Route tree

Defined in `frontend/src/App.js`:

```
/                                → LandingPage (4-tile track grid)
/auth                            → AuthPage (register / sign in)
/dashboard                       → ProgressDashboard (cross-track progress)
/sample/:difficulty              → SampleQuestionPage (SQL samples only)
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

Entry point. Shows "Data Interview Practice" on the left edge of the fixed topbar and dashboard/auth actions on the right. Logged-out users still see the centered hero with the primary "Get sharp at data interviews" message and CTAs. Below that sits a single tabbed landing shell:
- Track tabs for `sql`, `python`, `python-data`, `pyspark`
- A `SQL Samples` tab for unauthenticated sample entry points
- Each track tab shows a compact progress summary and CTA into `/practice/:topic`
- Uses existing dashboard data only; no new API shape

### AuthPage (`/auth`)

Register or sign in with email/password. On successful register, anonymous session is upgraded in place (progress preserved). On login, anonymous progress can be merged into an existing account.

### TrackHubPage (`/practice/:topic`)

Per-track landing rendered by `Outlet` when no question is active. Shows:
- Track name + overall solved/total progress bar
- Per-difficulty breakdown (easy/medium/hard bars)
- "Continue where I left off" button → navigates to next unlocked question
- "What you'll practice" focus card with next unlocked question summary
- Compact concept preview for the track
- My solved concepts (concept tags from solved questions only, shown as a short strip)

Uses `useCatalog()` for question/progress data.

### QuestionPage (`/practice/:topic/questions/:id`)

Main practice screen. Layout and behavior vary by topic:

| Topic | Editor | Left panel | Result area |
|---|---|---|---|
| SQL | Monaco (sql) | Schema viewer | ResultsTable (run + submit) |
| Python | Monaco (python) | Description only | TestCasePanel + PrintOutputPanel |
| Python (Data) | Monaco (python) | VariablesPanel + description | ResultsTable + PrintOutputPanel |
| PySpark | Read-only code snippet (if present) | Description only | MCQPanel → reveal explanation |

- Left panel is widened slightly and remains sticky on desktop
- Question header includes a compact status line derived from catalog metadata
- On mobile, question actions use a low-profile sticky dock for Run / Submit controls
- Loads question from topic API: `/api/python/questions/:id`, `/api/pyspark/questions/:id`, etc.
- Run → calls topic-specific run endpoint (`/api/python/run-code`, `/api/python-data/run-code`)
- Submit → calls topic-specific submit endpoint; marks solved on correct
- On correct: `refresh()` updates catalog context so sidebar reflects new unlock state
- PySpark: no Run button; MCQPanel handles option selection + submit + explanation reveal
- "Next Question" navigates to `/practice/:topic/questions/:nextId`

### SampleQuestionPage (`/sample/:difficulty`)

Standalone SQL sample practice (unchanged). No sidebar. SQL-only.

### ProgressDashboard (`/dashboard`)

Cross-track progress overview. 4-card grid with TrackProgressBar per track, concept tags by track, and recent activity list. Fetches `GET /api/dashboard` on mount.

---

## Components

| Component | File | Purpose |
|---|---|---|
| AppShell | `components/AppShell.js` | Challenge workspace shell: fixed topbar with direct track nav, collapsible sidebar |
| SidebarNav | `components/SidebarNav.js` | Question list grouped by difficulty; topic-aware NavLinks |
| CodeEditor | `components/CodeEditor.js` | Language-agnostic Monaco editor (language prop: `'sql'` \| `'python'`) |
| SQLEditor | `components/SQLEditor.js` | Thin re-export of CodeEditor with `language="sql"` (backward compat) |
| ResultsTable | `components/ResultsTable.js` | Tabular results with sticky headers and null value rendering |
| SchemaViewer | `components/SchemaViewer.js` | Dataset table schema — table names and column token grid |
| TestCasePanel | `components/TestCasePanel.js` | Python test case results (pass/fail per case, input/expected/actual, hidden summary) |
| PrintOutputPanel | `components/PrintOutputPanel.js` | Captured stdout block (rendered only if non-empty) |
| VariablesPanel | `components/VariablesPanel.js` | Available DataFrame variables with CSV source and column list |
| MCQPanel | `components/MCQPanel.js` | Radio-button MCQ with correct/wrong highlighting and explanation after submit |
| TrackProgressBar | `components/TrackProgressBar.js` | Reusable horizontal progress bar with configurable color and label |

### AppShell

- Fixed topbar shows a home-brand link plus direct track nav (`SQL`, `Python`, `Python (Data)`, `PySpark`)
- Track nav links route directly to `/practice/{topic}`
- Desktop: sidebar 328px, collapsible via toggle
- Mobile (<900px): sidebar becomes fixed overlay with backdrop
- Desktop question-bank toggle lives in workspace controls, not the header
- Mobile keeps a compact menu button in the header for opening the question drawer
- Upgrade panel shown for `free` and `pro` plan users
- Upgrade controls live in the sidebar instead of the topbar
- Handles `?upgraded=true` query param from Stripe redirect

### SidebarNav

- Collapsible difficulty groups
- Per-question state: `unlocked`, `locked`, `solved`, `next`, `current`
- NavLinks point to `/practice/${topic}/questions/${id}` (topic from `useTopic()`)
- Sidebar starts directly with the difficulty groups and question bank
- Test coverage in `components/SidebarNav.test.js`

---

## Contexts

### `contexts/TopicContext.js`

Provides current topic and track metadata to the entire component tree.

```js
// TRACK_META[topic] shape:
{
  label: 'Python (Data)',
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

### SQL challenge flow (unchanged)
1. `/practice/sql` → `TopicShell` provides topic + catalog
2. `AppShell` shows TrackHubPage or auto-navigates to next question
3. Question route → fetch `/api/questions/:id`
4. Run SQL → `POST /api/run-query` → ResultsTable
5. Submit → `POST /api/submit` → verdict + compare grid + hints/solution
6. On correct → `refresh()` → sidebar unlock state updates

### Python algorithm flow
1. `/practice/python/questions/:id` → fetch `/api/python/questions/:id`
2. Editor initialized with `question.starter_code`
3. Run → `POST /api/python/run-code` → TestCasePanel shows public cases
4. Submit → `POST /api/python/submit` → TestCasePanel + hidden test summary
5. On correct: solution_code + explanation revealed

### Python (Data) flow
1. `/practice/python-data/questions/:id` → fetch `/api/python-data/questions/:id`
2. VariablesPanel shows available DataFrames from `question.dataframes`
3. Run → `POST /api/python-data/run-code` → ResultsTable + PrintOutputPanel
4. Submit → `POST /api/python-data/submit` → correct/incorrect + DataFrame comparison

### PySpark MCQ flow
1. `/practice/pyspark/questions/:id` → fetch `/api/pyspark/questions/:id`
2. MCQPanel shows options (+ code_snippet if present)
3. User selects option → click Submit → `POST /api/pyspark/submit`
4. Response `{ correct, explanation }` → MCQPanel highlights correct/wrong + reveals explanation
5. No Run button; no code editor

### Sample flow
1. `/sample/:difficulty` → `GET /api/sample/:difficulty`
2. Backend marks sample as seen and returns question
3. Run/submit via `/api/sample/run-query` and `/api/sample/submit`
4. 409 on exhaustion → reset button → `POST /api/sample/:difficulty/reset` → re-fetch
5. No effect on challenge progress
