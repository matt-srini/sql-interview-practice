# SQL Interview Practice Platform

A web platform for practicing SQL interview questions by writing queries against sample datasets. The platform executes your query and evaluates whether the result matches the expected output.

---

## Tech Stack

| Layer     | Technology                        |
|-----------|-----------------------------------|
| Backend   | Python, FastAPI, DuckDB, Pandas   |
| Frontend  | React (Vite), Monaco Editor, Axios |
| Datasets  | CSV files loaded into DuckDB      |

---

## Project Structure

```
sql-interview-practice/
├── backend/
│   ├── main.py          # FastAPI app and routes
│   ├── database.py      # DuckDB connection and dataset loader
│   ├── questions.py     # Question catalog loader + helpers
│   ├── question_bank/   # Seeded question bank (easy/medium/hard)
│   ├── progress.py      # DuckDB-backed per-user progression
│   ├── evaluator.py     # Query execution and answer evaluation
│   ├── requirements.txt
│   └── datasets/
│       ├── employees.csv
│       ├── departments.csv
│       ├── customers.csv
│       └── orders.csv
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
      ├── index.js
      ├── App.js
        ├── App.css
        ├── pages/
      │   ├── QuestionListPage.js
      │   └── QuestionPage.js
        └── components/
        ├── SQLEditor.js
        ├── ResultsTable.js
        └── SchemaViewer.js
        ├── catalogContext.js
        ├── pages/
        │   └── QuestionPage.js
        └── components/
            ├── AppShell.js
            ├── SidebarNav.js
            ├── SQLEditor.js
            ├── ResultsTable.js
            └── SchemaViewer.js
|---|-------------------------------|------------|
| 1 | Second Highest Salary          | Easy       |
| 2 | Find Duplicate Emails          | Easy       |
| 3 | Top 3 Salaries per Department  | Hard       |
| 4 | Customers With No Orders       | Medium     |
  ## Guided Progression (MVP)

  - The question bank contains **75 starter questions** (25 Easy, 25 Medium, 25 Hard).
  - Progression is **sequential within each difficulty**:
    - The first question in each difficulty starts unlocked.
    - The next question unlocks only after the previous one is solved.
  - Progress is tracked per user via a cookie session id (`sql_practice_uid`) and stored in DuckDB (`user_progress`).
  - For testing or API clients, you can explicitly identify the user via the `X-User-Id` header.

  See [ARCHITECTURE.md](ARCHITECTURE.md) for a short design note.
  For end-to-end verification, use [MANUAL_TEST_CHECKLIST.md](MANUAL_TEST_CHECKLIST.md).
- Node.js 18+

---

### Backend

```bash
cd backend
pip install fastapi uvicorn duckdb pandas
pip install -r requirements.txt
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

API docs (Swagger UI): `http://localhost:8000/docs`

Health endpoint: `http://localhost:8000/health`

Run tests:

```bash
cd backend
pytest -q
```

If the frontend is deployed on a different origin, allow it through CORS with:

```bash
export ALLOWED_ORIGINS="https://app.example.com,http://localhost:5173"
```

`CORS_ALLOW_ORIGINS` is also supported as an alias.

---

### Frontend

```bash
cd frontend
npm install
npm start
```

API routing is resolved differently depending on how the frontend is served:

- In Vite dev mode, requests can use the dev proxy.
- If the frontend is served directly from `localhost` without a proxy, the app automatically calls `http://localhost:8000/api`.
- If the frontend is deployed separately from the backend, set `VITE_BACKEND_URL` to the browser-reachable backend origin, for example `https://api.example.com`.

If `npm install` fails with a cache permissions error on macOS, use the repo-local cache:

```bash
cd frontend
npm config set cache .npm-cache --location=project
npm install
```

The app will be available at `http://localhost:5173`.

Run frontend tests:

```bash
cd frontend
npm test
```

---

## Query Guardrails

- Only single `SELECT` / `WITH` queries are allowed.
- Multi-statement SQL is blocked.
- Query timeout is enforced (3 seconds).
- Result row count is capped at 200 rows per execution.
- Potential Cartesian joins are blocked (joins must use `ON` or `USING`).
- Query complexity is capped at 4 joins.

## API Rate Limiting

- Per-IP request limiting is enabled for API routes (except `/health`).
- Distributed limiting is used automatically when `REDIS_URL` is configured.
- If Redis is unavailable, the app safely falls back to in-memory limiting.
- Default limit: 60 requests per 60-second window.
- Limit values can be configured with environment variables:
  - `RATE_LIMIT_REQUESTS`
  - `RATE_LIMIT_WINDOW_SECONDS`
  - `REDIS_URL` (optional, enables shared/distributed limits)
- Responses include rate-limit headers:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Window`

---

## One-Command Startup (Docker Compose)

If Docker is installed:

```bash
docker compose up --build
```

Services:

- Redis: `localhost:6379`
- Backend API: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Production Deployment

The recommended production setup for this project is:

- GitHub as the source repo
- Railway running a single service from the root `Dockerfile`
- Cloudflare in front of Railway with your custom domain

This deployment shape is intentional:

- FastAPI serves both the API and the built React app from one origin.
- The browser uses same-origin `/api` requests in production.
- CORS is only needed when you deliberately split frontend and backend across different origins.

### Railway

- Deploy the repository root, not `frontend/` or `backend/` individually.
- Railway should build from the root `Dockerfile`.
- Set the health check path to `/health`.
- If you later split the frontend and backend across separate domains, set `ALLOWED_ORIGINS` on the backend and `VITE_BACKEND_URL` on the frontend.

### Cloudflare

- Point your custom domain at the Railway service.
- Keep the app under one public origin, for example `https://sql.example.com`.
- Leave API requests on the same origin so the frontend continues using `/api` without extra routing logic.

---

## API Endpoints

| Method | Endpoint            | Description                              |
|--------|---------------------|------------------------------------------|
| GET    | `/health`           | Service health and loaded tables         |
| GET    | `/catalog`          | Grouped questions + per-user status metadata |
| GET    | `/questions`        | List all questions (id, title, difficulty) |
| GET    | `/questions/{id}`   | Get full question detail                 |
| POST   | `/run-query`        | Execute a SQL query and return results   |
| POST   | `/submit`           | Evaluate user's answer                   |

---

## CI

GitHub Actions workflow is included at `.github/workflows/ci.yml` and runs:

- Backend tests (`pytest`) on push and pull requests
- Frontend production build (`npm run build`) on push and pull requests

### POST `/run-query` request body

```json
{
  "query": "SELECT * FROM employees",
  "question_id": 1
}
```

### POST `/submit` request body

```json
{
  "query": "SELECT MAX(salary) FROM employees WHERE salary < (SELECT MAX(salary) FROM employees)",
  "question_id": 1
}
```
