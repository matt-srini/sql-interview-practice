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
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
RAZORPAY_PLAN_PRO=plan_...            # monthly subscription plan id
RAZORPAY_PLAN_ELITE=plan_...          # monthly subscription plan id
RAZORPAY_AMOUNT_LIFETIME_PRO=799900   # amount in paise (₹7,999)
RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900 # amount in paise (₹14,999)
RAZORPAY_CURRENCY=INR
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
  -e SECURE_COOKIES=true \
  -e LOGIN_LOCKOUT_MAX_ATTEMPTS=5 \
  -e LOGIN_LOCKOUT_WINDOW_MINUTES=15 \
  -e RAZORPAY_KEY_ID=... \
  -e RAZORPAY_KEY_SECRET=... \
  -e RAZORPAY_WEBHOOK_SECRET=... \
  -e RAZORPAY_PLAN_PRO=... \
  -e RAZORPAY_PLAN_ELITE=... \
  -e RAZORPAY_AMOUNT_LIFETIME_PRO=799900 \
  -e RAZORPAY_AMOUNT_LIFETIME_ELITE=1499900 \
  -e SENTRY_DSN=... \
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
| `RAZORPAY_KEY_ID` | Yes | Razorpay API key id (`rzp_live_...` in prod, `rzp_test_...` in test mode) |
| `RAZORPAY_KEY_SECRET` | Yes | Razorpay API key secret — used to sign client-callback HMAC |
| `RAZORPAY_WEBHOOK_SECRET` | Yes | Secret configured on the Razorpay webhook endpoint |
| `RAZORPAY_PLAN_PRO` | Yes (for subs) | Razorpay Plan id backing the monthly Pro subscription |
| `RAZORPAY_PLAN_ELITE` | Yes (for subs) | Razorpay Plan id backing the monthly Elite subscription |
| `RAZORPAY_AMOUNT_LIFETIME_PRO` | — | Amount in paise for the Lifetime Pro one-time order (default `799900` = ₹7,999) |
| `RAZORPAY_AMOUNT_LIFETIME_ELITE` | — | Amount in paise for the Lifetime Elite one-time order (default `1499900` = ₹14,999) |
| `RAZORPAY_CURRENCY` | — | Currency code for Razorpay charges; defaults to `INR` |
| `RAZORPAY_PLAN_PRO_USD` | — | Razorpay Plan id for the monthly Pro subscription billed in USD (set after international approval) |
| `RAZORPAY_PLAN_ELITE_USD` | — | Razorpay Plan id for the monthly Elite subscription billed in USD (set after international approval) |
| `RAZORPAY_AMOUNT_LIFETIME_PRO_USD` | — | Amount in cents for the USD Lifetime Pro one-time order (default `8900` = $89) |
| `RAZORPAY_AMOUNT_LIFETIME_ELITE_USD` | — | Amount in cents for the USD Lifetime Elite one-time order (default `16900` = $169) |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins; defaults to localhost dev origins |
| `FRONTEND_DIST_DIR` | — | Path to built SPA assets; defaults to `../frontend/dist` |
| `RATE_LIMIT_REQUESTS` | — | Requests per window per IP; default `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | — | Window size in seconds; default `60` |
| `SECURE_COOKIES` | — | Controls cookie `secure` attribute; defaults to `true` in production |
| `LOGIN_LOCKOUT_MAX_ATTEMPTS` | — | Failed login attempts before temporary lock; default `5` |
| `LOGIN_LOCKOUT_WINDOW_MINUTES` | — | Temporary login lock window; default `15` minutes |
| `SENTRY_DSN` | — | Optional backend Sentry DSN for production error capture |
| `VITE_SENTRY_DSN` | — | Optional frontend Sentry DSN (set at build time via Vite) |
| `VITE_POSTHOG_KEY` | — | PostHog project API key for product analytics (set at build time via Vite) |
| `VITE_POSTHOG_HOST` | — | PostHog ingest host; defaults to `https://us.i.posthog.com` |

In `production` mode, startup will fail fast if `DATABASE_URL`, `REDIS_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, or `RAZORPAY_WEBHOOK_SECRET` are missing.

### Razorpay dashboard setup

1. Sign up at [dashboard.razorpay.com](https://dashboard.razorpay.com) with an Indian business (PAN + bank account for KYC).
2. Under **Settings → API Keys**, generate keys for Test mode first. Copy `Key Id` → `RAZORPAY_KEY_ID` and `Key Secret` → `RAZORPAY_KEY_SECRET`. Repeat under Live mode once KYC is approved.
3. Under **Subscriptions → Plans**, create two plans:
   - Pro monthly: amount `₹799` (79900 paise), period `monthly`, interval `1` → copy Plan id → `RAZORPAY_PLAN_PRO`.
   - Elite monthly: amount `₹1599` (159900 paise), period `monthly`, interval `1` → `RAZORPAY_PLAN_ELITE`.
4. Lifetime plans do **not** need Plan objects — the backend creates a one-time Order with the amount read from `RAZORPAY_AMOUNT_LIFETIME_PRO` / `RAZORPAY_AMOUNT_LIFETIME_ELITE` (paise).
5. Under **Settings → Webhooks**, add `https://<host>/api/razorpay/webhook` and subscribe to: `payment.captured`, `payment.failed`, `subscription.activated`, `subscription.charged`, `subscription.cancelled`, `subscription.halted`. Paste the generated secret into `RAZORPAY_WEBHOOK_SECRET`.
6. Test mode cards: `4111 1111 1111 1111`, any future expiry, any CVV, OTP `1234`.

---

## Railway

`railway.json` configures Railway to:
- Build using the root `Dockerfile`
- Health-check at `/health`
- Restart on failure (up to 10 retries)

Set the environment variables listed above in the Railway service settings. Railway provides managed Postgres and Redis as add-on services; copy their connection strings into `DATABASE_URL` and `REDIS_URL`.

---

## Pre-launch admin seed

Run once against the production database after migrations complete (idempotent upsert):

```bash
cd backend
DATABASE_URL="postgresql://..." \
  ADMIN_EMAIL="admin@yourdomain.com" \
  ADMIN_NAME="Admin" \
  ADMIN_PASSWORD="ReplaceWithStrongPassword1" \
  ../.venv/bin/python scripts/seed_admin.py
```
