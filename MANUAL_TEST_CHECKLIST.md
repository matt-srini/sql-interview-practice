# Manual Test Checklist (End-to-End)

## Startup

- Backend: `cd backend && uvicorn main:app --reload`
- Frontend: `cd frontend && npm start`
- Open `http://localhost:5173`

## Catalog + Sidebar

- Sidebar shows 3 collapsible groups: Easy / Medium / Hard
- Each group shows counts `solved/total` and totals are 25 per group
- Each group has exactly one `Next` question initially (the first one)
- Locked questions show `Locked` and are not clickable

## Progression

- Solve Easy #1 correctly:
  - Submit returns `correct: true`
  - Sidebar updates and Easy #2 becomes unlocked
- Try to run/submit a locked question:
  - UI disables actions
  - Backend returns `403 Question is locked` if called directly
- Solve a few questions, refresh the page:
  - Progress remains (cookie session id + DuckDB persistence)

## Query Flow

- Run Query returns results table with row count capped at 200
- Submit shows:
  - verdict
  - user vs expected output on incorrect
  - official solution + explanation after submission

## Responsive

- At narrow widths (<900px):
  - hamburger button shows
  - sidebar opens as drawer with backdrop
  - selecting a question closes the drawer
