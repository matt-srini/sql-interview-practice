# SQL Interview Practice Platform

A SQL practice platform with a React frontend, a FastAPI backend, and DuckDB-backed execution. Users can work through gated challenge questions, try a separate sample track, run read-only SQL, and compare their output against expected results.

---

## Current State

- Challenge bank: 85 questions total
  - Easy: 30
  - Medium: 30
  - Hard: 25
- Sample bank: 9 questions total
  - 3 per difficulty in backend/sample_questions.py
- Challenge content is JSON-backed in backend/content/questions/
- Sample content is Python-backed in backend/sample_questions.py
- Query execution is isolated per request using in-memory DuckDB connections scoped to question dataset_files
- Question schemas are validated against the committed dataset headers at load time
- Semantic reasoning tags (`concepts` field) are surfaced as pill badges on each question page
- Hints are revealed progressively one at a time before the solution is shown

For the fuller architectural reference, see docs/project-blueprint.md.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, DuckDB, Pandas |
| Frontend | React 18, React Router, Vite, Monaco Editor, Axios |
| Testing | pytest, httpx, Vitest, React Testing Library |
| Datasets | Generated CSV files loaded into DuckDB |

---

## Repository Layout

```text
sql-interview-practice/
├── backend/
│   ├── content/questions/        # JSON-backed challenge questions
│   ├── datasets/                 # Committed generated CSV datasets + metadata
│   ├── middleware/               # Request context and request_id handling
│   ├── routers/                  # API and SPA route modules
│   ├── scripts/                  # Dataset generation scripts
│   ├── tests/                    # Backend tests
│   ├── database.py               # DuckDB loading and isolated execution setup
│   ├── evaluator.py              # Query execution and result comparison
│   ├── main.py                   # FastAPI app wiring
│   ├── progress.py               # Challenge/sample progress storage
│   ├── questions.py              # Challenge catalog loader
│   ├── sample_questions.py       # Sample question catalog
│   └── sql_guard.py              # Read-only SQL validation
├── docs/
│   ├── project-blueprint.md      # Detailed architecture and current-state reference
│   ├── project-overview.md       # Concise product summary
│   └── question-authoring-guidelines.md
├── frontend/
│   ├── src/components/           # App shell, sidebar, editor, results, schema
│   ├── src/pages/                # Landing, challenge, and sample flows
│   ├── src/api.js                # API client and environment resolution
│   └── package.json
├── Dockerfile                    # Single-service production build
└── docker-compose.yml            # Local Redis + backend + frontend stack
```

---

## Dataset Inventory

The committed datasets live in backend/datasets/.

| CSV | What it models | Current committed count |
|-----|----------------|-------------------------|
| users.csv | User/account dimension with signup and plan metadata | 600 |
| categories.csv | Product category taxonomy | 16 |
| products.csv | Product catalog | 260 |
| orders.csv | Order headers linked to users | 4200 |
| order_items.csv | Line items within orders | 12665 |
| payments.csv | Payment events for orders | 4737 |
| sessions.csv | Website sessions | 9000 |
| events.csv | Session-level event stream | 44964 |
| support_tickets.csv | Customer support cases | 1300 |
| departments.csv | Department dimension | 10 |
| employees.csv | Employee records | 180 |

The current committed metadata snapshot is in backend/datasets/dataset_metadata_v1.json.

The generator currently supports small and medium profiles via backend/scripts/generate_v1_datasets.py.

Note:
- backend/datasets/DATA_DICTIONARY_V1.md is referenced in older docs but is not present in the current workspace.
- The generator script and metadata JSON are the current source of truth.

---

## Local Development

### Prerequisites

- Python 3.11 recommended
- Node.js 20 recommended
- Docker optional for the compose workflow

### Backend

```bash
cd backend
../.venv/bin/python -m pip install -r requirements.txt
../.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend URLs:
- API root: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

Run backend tests:

```bash
cd backend
../.venv/bin/python -m pytest -q
```

Generate datasets into a separate output folder:

```bash
cd backend
../.venv/bin/python scripts/generate_v1_datasets.py --seed 20260318 --scale small
```

By default this writes to backend/datasets_generated/.

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1
```

Frontend URL:
- http://127.0.0.1:5173

Run frontend tests:

```bash
cd frontend
npm test
```

If npm cache permissions fail on macOS:

```bash
cd frontend
npm config set cache .npm-cache --location=project
npm install
```

### API base URL behavior

The frontend resolves the backend as follows:
- If VITE_BACKEND_URL is set, use that origin plus /api
- If running on localhost without same-origin backend routing, fall back to http://localhost:8000/api
- Otherwise use same-origin /api

For split-origin development or deployment, configure:

```bash
export ALLOWED_ORIGINS="https://app.example.com,http://localhost:5173"
```

CORS_ALLOW_ORIGINS is also supported as an alias.

---

## Application Behavior

### Challenge progression

- Progression is sequential within each difficulty
- The first unsolved question in each difficulty is the next unlocked question
- Progress is tracked in DuckDB using user_progress
- User identity is best-effort via cookie or the X-User-Id header

### Sample mode

- Sample mode is separate from challenge progression
- Each difficulty has exactly 3 sample questions
- Seen-sample tracking is stored in user_sample_seen
- Sample exhaustion returns HTTP 409 until the user resets that difficulty

### Query guardrails

- Only single SELECT-style queries are allowed
- Multi-statement SQL is blocked
- Query timeout is 3 seconds
- Result rows are capped at 200
- Cartesian joins are blocked unless properly constrained
- Query complexity is capped at 4 joins

### Error and request handling

- User-facing error responses follow { error, request_id }
- Responses include X-Request-ID
- Structured logs use the format [request_id=<id>] message

### API rate limiting

- Per-IP request limiting applies to API traffic except /health
- Redis-backed limiting is used when REDIS_URL is configured
- Otherwise the app falls back to in-memory limiting
- Default limit is 60 requests per 60-second window

---

## API Endpoints

### System and catalog

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Service health and loaded persistent tables |
| GET | /catalog | Grouped challenge catalog with per-user state |
| GET | /api/catalog | Same as /catalog |

### Challenge routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /questions | Lightweight challenge list |
| GET | /api/questions | Same as /questions |
| GET | /questions/{id} | Challenge question detail |
| GET | /api/questions/{id} | Same as /questions/{id} |
| POST | /run-query | Execute SQL for a challenge question |
| POST | /api/run-query | Same as /run-query |
| POST | /submit | Evaluate a challenge answer and return acceptance/result feedback |
| POST | /api/submit | Same as /submit |

### Sample routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/sample/{difficulty} | Get next unseen sample question |
| POST | /api/sample/{difficulty}/reset | Reset sample progress for that difficulty |
| POST | /api/sample/run-query | Execute SQL for a sample question |
| POST | /api/sample/submit | Evaluate a sample answer |

### Example request body

```json
{
  "query": "SELECT * FROM users",
  "question_id": 1001
}
```

---

## Docker Compose

If Docker is installed:

```bash
docker compose up --build
```

Services:
- Redis: localhost:6379
- Backend API: http://localhost:8000
- Frontend: http://localhost:5173

---

## Production Deployment

Recommended shape:
- GitHub as the source repo
- Railway building the repository root Dockerfile
- Cloudflare in front of Railway for the public domain

This keeps the production app on one origin:
- FastAPI serves the built React app and the API
- The browser uses same-origin /api requests
- CORS is only needed for intentional split-origin setups

### Railway

- Deploy the repository root, not frontend/ or backend/ individually
- Build from the root Dockerfile
- Use /health as the health check path
- If you split frontend and backend later, set ALLOWED_ORIGINS on the backend and VITE_BACKEND_URL on the frontend

### Cloudflare

- Point your custom domain at the Railway service
- Keep the app under one origin such as https://sql.example.com

---

## CI

The GitHub Actions workflow at .github/workflows/ci.yml runs:
- Backend tests with pytest
- Frontend production build with npm run build

---

## Related Docs

- docs/project-blueprint.md: detailed architecture and current-state reference
- docs/project-overview.md: concise product summary
- docs/question-authoring-guidelines.md: question authoring standard
- MANUAL_TEST_CHECKLIST.md: manual verification steps
