# Manual Test Checklist (End-to-End)

## Startup

- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Open `http://localhost:5173`
- Check `GET /health` returns `status: healthy` with postgres, duckdb, redis all OK

## Catalog + Sidebar

- Sidebar shows 3 collapsible groups: Easy / Medium / Hard
- Group totals: Easy 30, Medium 30, Hard 26
- Each group shows `solved/total` counts
- Each group has exactly one `Next` question initially (the first unlocked)
- Locked questions are visually dimmed and not clickable

## Progression

- Solve Easy #1 correctly:
  - Submit returns `correct: true`
  - Sidebar refreshes and Easy #2 becomes the next question
- Attempt to run/submit a locked question:
  - UI disables Run and Submit buttons
  - Backend returns `403` if called directly
- Solve a few questions, refresh the page:
  - Progress persists (PostgreSQL-backed sessions)

## Query Flow

- Run Query returns a results table with row count (capped at 200)
- Submit shows:
  - Verdict banner (Correct / Keep iterating)
  - On incorrect: Your Output vs Expected Output compare grid
  - After submit: hints revealed one at a time via "Reveal Hint N" button
  - Solution button only appears after all hints are revealed
  - On correct: Next Question button appears

## Sample Flow

- Visit `/sample/easy` — returns first unseen easy sample
- Run and submit SQL — works independently from challenge progression
- After 3 samples exhausted — 409 response shows exhaustion card
- Reset samples — clears exposure and allows cycling again

## Auth Flow

- Register with email/password — session upgrades anonymous user in place
- Login with existing account — merges anonymous progress if applicable
- Logout — clears session cookie

## Responsive

- At narrow widths (<900px):
  - Hamburger button shows in top bar
  - Sidebar opens as drawer with backdrop overlay
  - Selecting a question closes the drawer
  - Two-column question layout collapses to single column

## Plan / Billing

- GET `/api/user/profile` returns plan tier (free/pro/elite)
- Upgrade panel in top bar shows for free and pro users
- POST `/api/stripe/create-checkout` redirects to Stripe Checkout (requires `STRIPE_SECRET_KEY`)
- Stripe webhook verifies signature and applies idempotent plan change
