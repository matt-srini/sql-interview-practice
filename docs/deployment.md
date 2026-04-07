# Deployment

> **Navigation:** [Docs index](./README.md) · [Architecture](./architecture.md) · [Backend](./backend.md)

---

## Local development

The standard local setup runs backend and frontend natively, with Postgres and Redis in Docker.

### Prerequisites

- Python virtualenv at `.venv/` in the **project root** (not `backend/`), with `backend/requirements.txt` installed:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install -r backend/requirements.txt
  ```
- Node.js and npm (verify: `node --version`). On macOS the binary may be at `/usr/local/bin/node` and not on the shell path — use the full path if `npm` is not found.

### 1. Start infrastructure

```bash
docker compose up postgres redis -d
```

This starts:
- Postgres 16 on port `5432` — user `postgres`, password `postgres`, database `sql_practice`
- Redis 7 on port `6379`

### 2. Configure backend

Create `backend/.env` (relative to project root: `backend/.env`):

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice
```

Optional additions:

```
REDIS_URL=redis://localhost:6379/0
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_ELITE=price_...
```

### 3. Start backend

Always run from the `backend/` directory so relative imports and data paths resolve correctly:

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

### 4. Start frontend

```bash
cd frontend
npm run dev
# or if node isn't on PATH:
/usr/local/bin/node node_modules/.bin/vite
```

Vite starts on port `5173` (increments if occupied). The API client resolves to `http://localhost:8000/api` when running on localhost without a same-origin backend.

### 5. Run backend tests

```bash
cd backend
../.venv/bin/python -m pytest tests/ -q
```

### Health check

```
GET http://localhost:8000/health
→ { "status": "ok", "postgres": true, "tables_loaded": 11 }
```

---

## Database migrations (Alembic)

Alembic manages schema changes. The `env.py` is configured for async connections, so the `DATABASE_URL` must use the `asyncpg` driver even when running migrations from the CLI.

### Apply pending migrations

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sql_practice" \
  ../.venv/bin/alembic upgrade head
```

### First-time setup on an existing database

If the database schema was created by the app's `ensure_schema()` startup function (before Alembic was introduced), Alembic has no version tracking. Stamp the baseline revision first, then upgrade:

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sql_practice" \
  ../.venv/bin/alembic stamp 20260323_000001

DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sql_practice" \
  ../.venv/bin/alembic upgrade head
```

### Create a new migration

```bash
cd backend
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/sql_practice" \
  ../.venv/bin/alembic revision --autogenerate -m "describe the change"
```

Review the generated file in `alembic/versions/` before applying.

---

## Full Docker stack (optional)

`docker-compose.yml` also includes `backend` and `frontend` service definitions for running everything in containers:

```bash
docker compose up --build
```

Service ports:
- `5432` — Postgres
- `6379` — Redis
- `8000` — Backend
- `5173` — Frontend (Vite dev server in container)

The frontend container sets `VITE_BACKEND_URL=http://localhost:8000` so the API client points at the backend container.

---

## Production build

The production image is a single Docker container: FastAPI serves both the API and the pre-built React SPA.

**`Dockerfile` stages:**

1. `frontend-build` (node:20-alpine) — runs `npm ci && npm run build`, outputs `frontend/dist/`
2. `runtime` (python:3.11-slim) — installs Python deps, copies backend code and `frontend/dist/`

```bash
docker build -t sql-practice .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_URL=redis://... \
  -e ENV=production \
  -e STRIPE_SECRET_KEY=... \
  -e STRIPE_WEBHOOK_SECRET=... \
  sql-practice
```

The `FRONTEND_DIST_DIR` env var defaults to `/app/frontend/dist` inside the image (set in the Dockerfile). The SPA router (`routers/spa.py`) serves static assets and falls back to `index.html` for all non-`/api` paths.

---

## Environment variables

| Variable | Required in prod | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `ENV` | — | `production` enables strict validation; defaults to `development` |
| `STRIPE_SECRET_KEY` | Yes | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRICE_PRO` | — | Stripe price ID for Pro plan |
| `STRIPE_PRICE_ELITE` | — | Stripe price ID for Elite plan |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins; defaults to localhost dev origins |
| `FRONTEND_DIST_DIR` | — | Path to built SPA assets; defaults to `../frontend/dist` |
| `RATE_LIMIT_REQUESTS` | — | Requests per window per IP; default `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | — | Window size in seconds; default `60` |

In `production` mode, startup will fail fast if `DATABASE_URL`, `REDIS_URL`, `STRIPE_SECRET_KEY`, or `STRIPE_WEBHOOK_SECRET` are missing.

---

## Railway

`railway.json` configures Railway to:
- Build using the root `Dockerfile`
- Health-check at `/health`
- Restart on failure (up to 10 retries)

Set the environment variables listed above in the Railway service settings. Railway provides managed Postgres and Redis as add-on services; copy their connection strings into `DATABASE_URL` and `REDIS_URL`.
