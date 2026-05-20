# Manual Test Checklist (End-to-End)

## Startup

- Backend: `cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Open `http://localhost:5173`
- Check `GET /health` returns `status: healthy` with postgres, duckdb, and redis all OK

---

## Landing page

### Hero (logged-out)
- 2-column layout: left copy + CTA, right HeroIDE animation cycling through all 9 tracks
- "Start thinking →" links to `/sample/sql/easy`; "Find your track ↓" smooth-scrolls to the tracks section
- Logged-in: 3-card strip (Resume · Dashboard · Mock) replaces the hero CTAs

### Editorial sections (all users)
- Thesis (3 columns), Wrong/Right diff table (right column animates in on scroll)
- Role selector: 4 tabs (Data Analyst · Data Engineer · Analytics Engineer · Data Scientist) — each shows relevant tracks
- Proof strip: stat row with count-up animation on scroll
- Tracks index: all 9 tracks listed with color dots, question counts, format tags, and "Enter →" links
- Guided progressions: renders path cards from `/api/paths`
- Pricing: Free / Pro / Elite columns — visible to all users except `lifetime_elite`

---

## Sample flow

- Visit `/sample/sql/easy` — returns first unseen easy SQL sample (no login required)
- Topbar: `datathink` at left edge, `← SQL sample` centered, `Start the challenge` at right edge
- Run Query returns a results table; Submit shows verdict + compare grid; no progress impact
- After 3 samples exhausted — 409 → exhaustion card with Reset and "Take the challenge" buttons
- Reset clears exposure and cycling restarts from question 1
- `/sample/easy` (legacy) redirects to `/sample/sql/easy`

### Multi-track samples
- `/sample/python/easy` — Python algorithm question, code editor, TestCasePanel
- `/sample/python-data/easy` — Pandas question, VariablesPanel, DataFrame output
- `/sample/pyspark/easy` — MCQ radio options, no code editor, explanation on submit
- Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation — auto-sliced from first 3 practice questions per difficulty (no dedicated sample IDs)
- Topbar label reflects track ("Python sample", "Pandas sample", etc.)

---

## Challenge tracks

### SQL (`/practice/sql`)
- Track hub shows progress bars (easy/medium/hard), next unlocked question, concept preview, paths
- Sidebar shows 3 collapsible groups: Easy (37), Medium (45), Hard (30) — total 112
- First question unlocked; locked questions dimmed and not clickable
- Run Query → results table (capped at 200 rows, 3 s timeout)
- Submit → verdict, compare grid, hints; solution + quality analysis revealed on correct
- Solving Easy #1 → Easy #2 becomes `Next`; sidebar refreshes

### Python (`/practice/python`)
- Sidebar: Easy (39), Medium (32), Hard (24) — total 95
- Editor initialized with `starter_code`
- Run Code → TestCasePanel (public test cases) + PrintOutputPanel (stdout)
- Submit → public + hidden test results; `solution_code` revealed on correct

### Pandas (`/practice/python-data`)
- Sidebar: Easy (27), Medium (36), Hard (23) — total 86
- VariablesPanel shows available DataFrames with schema
- Run Code → DataFrame output table + PrintOutputPanel
- Submit → DataFrame comparison (your output vs expected)

### PySpark (`/practice/pyspark`)
- Sidebar: Easy (41), Medium (39), Hard (26) — total 106
- MCQPanel shows radio options; no Run button; question-form badges (MCQ / predict-output / debug / scenario)
- Submit → highlights correct/wrong option + reveals explanation

### Data Engineering (`/practice/data-engineering`)
- Sidebar: Easy (30), Medium (33), Hard (23) — total 86
- MCQ / scenario / debug formats; no code execution
- Locked MCQ shows stem but hides options; submitting locked returns 403

### Data Modeling (`/practice/data-modeling`)
- Sidebar: Easy (25), Medium (28), Hard (23) — total 76
- MCQ / scenario formats; no code execution

### Statistics (`/practice/statistics`)
- Sidebar: Easy (31), Medium (41), Hard (25) — total 97
- **Dual-subtype**: conceptual questions → MCQ panel; numerical questions → Python code editor + test harness
- `Run Code` appears only for numerical subtype; MCQ-only for conceptual

### ML Fundamentals (`/practice/ml-fundamentals`)
- Sidebar: Easy (30), Medium (35), Hard (25) — total 90
- MCQ / scenario / predict-output / debug formats

### Experimentation (`/practice/experimentation`)
- Sidebar: Easy (30), Medium (30), Hard (20) — total 80
- MCQ / scenario / predict-output / debug formats

---

## Progression

- Solve a question correctly → sidebar refreshes, next question unlocks
- Refresh the page → progress persists (PostgreSQL-backed)
- **Free plan unlock thresholds (code tracks — SQL / Python / Pandas):**
  - Medium: 8 easy → 3 medium · 15 easy → 8 medium · 25 easy → all medium
  - Hard: 8 medium → 3 hard · 15 medium → 8 hard · 22 medium → 15 hard (cap: 8)
- **Free plan unlock thresholds (MCQ tracks — PySpark / Data Engineering):**
  - Medium: 10 easy → 3 medium · 17 easy → 8 medium · 25 easy → all medium
  - Hard: 12 medium → 5 hard (cap: 5)
- Locked MCQ questions: stem visible, options hidden; submitting returns 403
- Solved questions remain solved permanently across plan changes

---

## Auth flow

- Register with email/password — anonymous session upgraded in place (progress preserved)
- Login with existing account — merges anonymous progress if applicable
- Logout — clears session cookie; page reverts to logged-out state
- Forgot password → reset email → `/auth/reset-password?token=...` → new password accepted
- Email verification banner appears for unverified accounts; resend link works
- Magic link: `POST /api/auth/magic-link` → click link → signed in, redirected to frontend

---

## Responsive / mobile

- At <900px:
  - Desktop sidebar collapse button (`‹`) hidden
  - Hamburger "Questions" button in app topbar; sidebar opens as full-height overlay
  - Escape key or selecting a question closes the drawer
  - Two-column question layout collapses to single column
  - Question actions use sticky dock at bottom of screen
- At >900px (desktop):
  - `‹` collapses the question bank; `›` expands it again from the content area

---

## Plan / billing

- Upgrade panel appears in sidebar for `free` and `pro` users
- `POST /api/razorpay/create-order` creates a Razorpay Order or Subscription
- `POST /api/razorpay/verify-payment` verifies HMAC and applies plan immediately
- `POST /api/razorpay/webhook` idempotent plan update (authoritative source of truth)
- After upgrade: plan refreshes automatically, new questions unlock in sidebar

---

## Dashboard (`/dashboard`)

- 9-track grid shows per-track solve counts and progress bars
- Coaching insights: speed comparison, accuracy by difficulty, weakest concepts (≥3 attempts, <60%)
- Streak tracking: consecutive solve days, "at risk" state shown in topbar
- **(Elite only)** Readiness scores (0–100 per track) and personalised study plan
- Fetches `GET /api/dashboard` + `GET /api/dashboard/insights`

---

## Mock interviews (`/mock`)

### Setup (MockHub)
- Two-column desktop layout: left config, right sticky session brief + Start CTA
- Mode cards: Benchmark (fixed-shape), Sprint drill (30 min, 2 questions), Custom drill (user-set)
- Benchmark rejects Mixed track; drill modes allow Mixed (SQL + Python + Pandas + PySpark)
- Track selector + difficulty buttons show live access state (remaining daily sessions or upgrade CTAs)
- Pre-flight: `GET /api/mock/access?track=<track>` called on every track change
- **(Elite only)** Company filter dropdown when SQL track selected
- **(Elite only)** Focus mode concept multi-select (1–3 concepts)

### Session (`/mock/:id`)
- Countdown timer, colour-coded: normal → amber (<10 min) → red (<3 min); browser tab title updates
- Session framing card: benchmark → fixed-shape blueprint; drill → flexible framing
- Question navigation: numbered dot tabs, solved/unsolved state
- Submit per question: one real submission; no solution shown mid-session; blank/unselected returns 422 (no slot consumed)
- After submitting all questions: "All questions answered — end your session when ready."
- Exit confirmation dialog; discard prompt if exiting within ~60 s with no submissions
- Session reload recovery: navigating back restores state from server

### Post-session summary
- Score headline (X/Y correct), time used
- **(Pro+)** Baseline comparison (above/below historical accuracy)
- Per-question breakdown: solved badge, time spent, expandable "See solution"
- **(Pro+)** Concept breakdown table, "Drill weak concepts →" link
- **(Elite)** Session debrief coaching narrative (headline, patterns, priority action)
- **(Elite)** "Known weakness" amber badge on concepts matching cross-session weak spots
- Share result: native share sheet or clipboard fallback

### Plan gates
- Free: unlimited easy mocks, 1 medium/day (requires medium unlocked in practice first)
- Pro: all difficulties, 3 hard/day
- Elite: unlimited, focus mode, company filter, debrief, mock history analytics

### History
- Last 20 sessions split into Benchmark and Drill sections
- Mode labels normalized: Benchmark · Sprint drill · Custom drill · Full (legacy)

---

## Learning paths (`/learn`)

- Index shows all 42 paths grouped by track; topic pills filter by track
- `/learn/:topic/:slug` shows path with breadcrumb, progress bar, and question list
- Completing a track's Starter path → all medium unlocked immediately
- Completing the Intermediate path → full free-tier hard cap unlocked

---

## Error states

- `GET /api/questions/{id}` for a locked question → 403 (backend enforced)
- Starting a mock with an active session → 409 (includes `session_id` in body; frontend offers Resume link)
- Sample exhausted → 409 → exhaustion card
- Blank code or unselected MCQ on mock submit → 422 (slot not consumed)
- Discard mock after >120 s → 403
- All user-facing errors carry `{ error, request_id }` and `X-Request-ID` + `X-Response-Time-Ms` headers
