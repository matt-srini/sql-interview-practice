# Manual Test Checklist (End-to-End)

## Startup

- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Open `http://localhost:5173`
- Check `GET /health` returns `status: healthy` with postgres, duckdb, redis all OK

---

## Landing page

### Hero (logged-out)
- Hero section shows headline, tagline, two CTAs ("Explore tracks ↓" and "Create account")
- "Explore tracks ↓" scrolls to the track selection section (`#landing-tracks`)
- Hero is hidden once logged in

### Showcase
- Dark section animates through all 4 tracks automatically (~5 s each)
- Active card expands with colored glow; inactive cards dim
- Both question and answer phases appear (typing animation)
- Full answer content is visible without clipping (SQL card has 17 lines — the longest)

### Track selection (`#landing-tracks`)
- Pill nav tabs switch between SQL / Python / Pandas / PySpark panels
- Each panel shows: description, progress bar (thin), CTA, and Easy/Medium/Hard sample tiles
- **Mobile**: sample tiles scroll horizontally — all three difficulties reachable without vertical stacking
- "Open sample →" links on each tile navigate to the correct `/sample/:topic/:difficulty` route
- Logged-in users: progress bar reflects real solve count; CTA shows "Continue" instead of "Start"

---

## Sample flow

- Visit `/sample/sql/easy` — returns first unseen easy SQL sample
- Topbar: `datanest` at left edge, `← SQL sample` centered, `Start the challenge` at right edge
- Back arrow (`←`) navigates to `/` and smooth-scrolls to the track selection section
- Run Query returns a results table; Submit shows verdict + compare grid
- After 3 samples exhausted — 409 → exhaustion card with Reset and Take the challenge buttons
- Reset clears exposure and cycling starts again from question 1
- `/sample/easy` (legacy) redirects to `/sample/sql/easy`

### Multi-track samples
- `/sample/python/easy` — Python algorithm question, code editor, test case panel
- `/sample/python-data/easy` — Pandas question, VariablesPanel, DataFrame output
- `/sample/pyspark/easy` — MCQ, no code editor, explanation revealed on submit
- Each track's topbar label reflects the track ("Python sample", "Pandas sample", etc.)

---

## Challenge tracks

### SQL (`/practice/sql`)
- Track hub shows progress bars (easy/medium/hard), next unlocked question, concept preview
- Sidebar shows 3 collapsible groups: Easy (30), Medium (30), Hard (26) — totals 86
- First question unlocked; locked questions are dimmed and not clickable
- Run Query → results table (capped at 200 rows)
- Submit → verdict, compare grid, hints; solution revealed on correct
- Solving Easy #1 → Easy #2 becomes `Next`; sidebar refreshes
- Attempting to call a locked question directly → backend returns `403`

### Python (`/practice/python`)
- Sidebar: Easy (30), Medium (25), Hard (20) — totals 75
- Editor initialized with `starter_code` from the question
- Run Code → TestCasePanel with public test cases + PrintOutputPanel for stdout
- Submit → public + hidden test results; solution_code revealed on correct

### Pandas (`/practice/python-data`)
- Sidebar: Easy (30), Medium (25), Hard (20) — totals 75
- VariablesPanel shows available DataFrames with schema
- Run Code → DataFrame output table + PrintOutputPanel
- Submit → correct/incorrect + DataFrame comparison (your output vs expected)

### PySpark (`/practice/pyspark`)
- Sidebar: Easy (30), Medium (25), Hard (20) — totals 75
- MCQPanel shows radio options; no Run button
- Submit → highlights correct/wrong option + reveals explanation

---

## Progression

- Solve a question correctly → sidebar refreshes, next question unlocks
- Refresh the page → progress persists (PostgreSQL-backed sessions)
- Free plan: easy questions all open; medium unlocks at 10/20/30 solved easy; hard gated similarly
- Solved questions stay solved permanently across plan changes

---

## Auth flow

- Register with email/password — anonymous session upgraded in place (progress preserved)
- Login with existing account — merges anonymous progress if applicable
- Logout — clears session cookie; page reverts to logged-out state

---

## Responsive / mobile

- At <900px:
  - Desktop sidebar collapse button (`‹`) is hidden
  - Hamburger "Questions" button shows in the app topbar
  - Sidebar opens as full-height overlay with backdrop; Escape key closes it
  - Selecting a question closes the drawer
  - Two-column question layout collapses to single column
  - Question actions use sticky dock at bottom of screen
- At >900px (desktop):
  - `‹` icon button at the top of the sidebar collapses the question bank
  - `›` button appears in content area to expand it again
  - Collapsing gives full-width question workspace

---

## Plan / billing

- Upgrade panel appears in the **sidebar** for `free` and `pro` users
- `POST /api/stripe/create-checkout` redirects to Stripe Checkout (requires `STRIPE_SECRET_KEY`)
- Stripe webhook verifies signature and applies idempotent plan change
- After upgrade redirect (`?upgraded=true`): plan refreshes automatically, new questions unlock in sidebar

---

## Dashboard (`/dashboard`)

- 4-card grid shows per-track solve counts and progress bars
- Concept tags per track surface solved concepts
- Fetches `GET /api/dashboard`
