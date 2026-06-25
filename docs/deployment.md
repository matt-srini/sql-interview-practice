# Deployment

> **Navigation:** [Docs index](../README.md) · [Architecture](./architecture.md) · [Backend](./backend.md)

---

## ⚠️ Pending production DB migrations

> **The production DB is never updated automatically.** `ENV=production` disables auto-migrate at startup. Every Alembic migration that ships in a commit **must be applied manually to Railway Postgres before that commit's features will work on the live site.** The agent that authors the migration is responsible for running it immediately — not as a follow-up, not "later". Prod is the real product.

### How to apply on production

The production DATABASE_URL is in `backend/.env` (line 4, commented out). Read it from there — never paste it into a doc or command history. Uncomment the line temporarily or pass it inline:

```bash
cd backend
# Read DATABASE_URL from backend/.env line 4
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic upgrade head

# Confirm — must print the latest revision ID followed by (head):
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic current
```

After confirming, move the entries below from "Currently pending" to "Already applied."

---

### Currently pending

_Nothing. Production is at head (`20260624_000001`)._

---

### Already applied to production

| Revision | Description | Applied date |
|---|---|---|
| ≤ `20260511_000001` | All prior migrations | Before 2026-05-28 |
| `20260528_000001` | Add `role TEXT` column to `mock_sessions` | 2026-05-28 |
| `20260528_000002` | Add `follow_up_dimension TEXT` column to `mock_session_questions` | 2026-05-28 |
| `20260528_000003` | Create `mock_chain_consumption` table + index | 2026-05-28 |
| `20260609_000001` | Rename `python_data`/`python-data` topic → `pandas` in `user_progress`, `user_sample_seen`, `submissions`, `mock_sessions`, `mock_session_questions` (Pandas slug/db-topic cleanup) | 2026-06-09 |
| `20260610_000001` | Add `plan_override TEXT` and `plan_override_until TIMESTAMPTZ` to `users` (time-limited beta-access grants via `/api/admin/grant-plan`) | 2026-06-10 |
| `20260610_000002` | Create `mock_discards` table + index — per-day penalty-free discard cap (audit C4) | 2026-06-10 |
| `20260612_000001` | Add `provider TEXT NOT NULL DEFAULT 'razorpay'` to `payment_events` (dual-rail Razorpay + Paddle) | 2026-06-13 |
| `20260624_000001` | add mock_sessions.loop_escalated (per-session Interview Loop escalation; history/active read it, pre-start stays cell-level) | 2026-06-25 |

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
RAZORPAY_AMOUNT_LIFETIME_PRO=1199900   # amount in paise (₹11,999)
RAZORPAY_AMOUNT_LIFETIME_ELITE=1999900 # amount in paise (₹19,999)
RAZORPAY_CURRENCY=INR
# Paddle (global rail — Merchant of Record; set after Paddle onboarding)
PADDLE_ENVIRONMENT=sandbox            # 'sandbox' or 'production'
PADDLE_CLIENT_TOKEN=test_...          # client-side token for Paddle.js
PADDLE_WEBHOOK_SECRET=pdl_ntfset_...  # notification-destination signing secret
PADDLE_PRICE_PRO=pri_...              # USD monthly Pro price id
PADDLE_PRICE_ELITE=pri_...            # USD monthly Elite price id
PADDLE_PRICE_LIFETIME_PRO=pri_...     # USD one-time Lifetime Pro price id
PADDLE_PRICE_LIFETIME_ELITE=pri_...   # USD one-time Lifetime Elite price id
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

### ⚠️ Two-track schema — always update `_SCHEMA_SQL` alongside the migration

The schema is defined in **two independent places** that are never auto-synced:

| Track | Location | Used by |
|---|---|---|
| `_SCHEMA_SQL` | `backend/db.py` (hardcoded SQL string) | Local dev (`ensure_schema()` at startup) + test suite (`ensure_schema_admin()` in `conftest.py`) |
| Alembic migrations | `backend/alembic/versions/` | Production only (applied manually via `alembic upgrade head`) |

**Every time you write a migration that adds or alters schema, you must also update `_SCHEMA_SQL`:**

- **New column:** append `ALTER TABLE <table> ADD COLUMN IF NOT EXISTS <col> <type>;` at the bottom of `_SCHEMA_SQL`.
- **New table:** append the full `CREATE TABLE IF NOT EXISTS <table> (...)` block.
- **Column rename / type change:** update the `CREATE TABLE` definition inside `_SCHEMA_SQL` and add a matching `ALTER TABLE` if needed for `IF NOT EXISTS` safety.

If you skip this, the test suite will fail with `column <name> does not exist` because `conftest.py` builds the test DB from `_SCHEMA_SQL`, not from Alembic. This was the root cause of the 2026-06-10 `plan_override` bug — migration added the columns, `_SCHEMA_SQL` did not. See `docs/decisions/DECISIONS.md` 2026-06-10 entry.

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

The runtime container starts Uvicorn on `0.0.0.0` and binds to `${PORT}` when the platform injects one (for example Railway). For local Docker runs, it falls back to `8000`.

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
  -e RAZORPAY_AMOUNT_LIFETIME_PRO=1199900 \
  -e RAZORPAY_AMOUNT_LIFETIME_ELITE=1999900 \
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
| `RAZORPAY_AMOUNT_LIFETIME_PRO` | — | Amount in paise for the Lifetime Pro one-time order (default `1199900` = ₹11,999) |
| `RAZORPAY_AMOUNT_LIFETIME_ELITE` | — | Amount in paise for the Lifetime Elite one-time order (default `1999900` = ₹19,999) |
| `RAZORPAY_CURRENCY` | — | Currency code for Razorpay charges; defaults to `INR` |
| `RAZORPAY_PLAN_PRO_USD` | — | Razorpay Plan id for the monthly Pro subscription billed in USD (set after international approval) |
| `RAZORPAY_PLAN_ELITE_USD` | — | Razorpay Plan id for the monthly Elite subscription billed in USD (set after international approval) |
| `RAZORPAY_AMOUNT_LIFETIME_PRO_USD` | — | Amount in cents for the USD Lifetime Pro one-time order (default `14900` = $149) |
| `RAZORPAY_AMOUNT_LIFETIME_ELITE_USD` | — | Amount in cents for the USD Lifetime Elite one-time order (default `24900` = $249) |
| `PADDLE_ENVIRONMENT` | — | Paddle.js environment: `sandbox` (default) or `production` |
| `PADDLE_CLIENT_TOKEN` | — | Paddle client-side token for the checkout overlay. Unset → `/api/paddle/create-checkout` returns 503 (global rail off) |
| `PADDLE_WEBHOOK_SECRET` | — | Paddle notification-destination signing secret (verifies the `Paddle-Signature` header). Unset → `/api/paddle/webhook` returns 503 |
| `PADDLE_PRICE_PRO` / `PADDLE_PRICE_ELITE` | — | USD Paddle price ids for the monthly Pro / Elite subscriptions |
| `PADDLE_PRICE_LIFETIME_PRO` / `PADDLE_PRICE_LIFETIME_ELITE` | — | USD Paddle price ids for the one-time Lifetime Pro / Elite purchases |
| `PADDLE_API_KEY` | — | Paddle server-side API key (reserved for future cancel / customer-portal flows; unused at launch) |
| `ALLOWED_ORIGINS` | — | Comma-separated CORS origins; defaults to localhost dev origins |
| `FRONTEND_DIST_DIR` | — | Path to built SPA assets; defaults to `../frontend/dist` |
| `RATE_LIMIT_REQUESTS` | — | Requests per window per IP; default `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | — | Window size in seconds; default `60` |
| `FORWARDED_ALLOW_IPS` | — | Immediate-peer address(es) uvicorn trusts `X-Forwarded-For` from, deriving `request.client.host` (which the per-IP rate limiter keys on). Default `127.0.0.1` (= uvicorn's default; behaviour unchanged). Set to the **verified** Railway edge-proxy hop if per-IP keying is collapsing to one proxy bucket — **never `*`** (IP-spoofing hole). See § Rate-limiter operational notes & findings. |
| `MAX_CONCURRENT_EXECUTIONS` | — | Max concurrent code executions (DuckDB SQL + subprocess sandboxes) across the app; default **cores − 2**. Bounds peak sandbox memory (× `RLIMIT_AS` 512 MB) and CPU. Prod sets `6` on the 8-vCPU replica. See `backend/offload.py`. |
| `MAX_CONCURRENT_HASHES` | — | Max concurrent password hashes (PBKDF2, ~22 ms/call) run off the event loop; default **cores − 1**. Kept **independent** of `MAX_CONCURRENT_EXECUTIONS` (auth hashing vs. sandbox execution are different resource classes). A latency-vs-throughput knob — lower it (e.g. `cores/2`) to protect bystander latency during an auth burst at the cost of burst-drain speed; see § Concurrency & scaling model. See `backend/offload.py` `run_blocking_hash`. |
| `DB_POOL_SIZE` | — | Postgres connection pool size per replica; default `10` |
| `DB_MAX_OVERFLOW` | — | Extra Postgres connections beyond the pool under burst; default `20` (→ 30 max per replica) |
| `DB_POOL_TIMEOUT` | — | Seconds a request waits for a free DB connection before failing fast; default `10` |
| `DB_POOL_RECYCLE_SECONDS` | — | Recycle pooled connections older than this many seconds; default `1800` |
| `AUTH_RATE_LIMIT_REQUESTS` | — | Requests per window for auth endpoints (`/api/auth/*`); default `20` |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | — | Window size in seconds for auth endpoint limiter; default `60` |
| `AUTH_TOKEN_ISSUE_RATE_LIMIT_REQUESTS` | — | Stricter limiter for token-issuing auth routes (OAuth authorize, magic-link request); default `5` |
| `AUTH_TOKEN_ISSUE_RATE_LIMIT_WINDOW_SECONDS` | — | Window size for token-issuing limiter; default `300` |
| `SECURE_COOKIES` | — | Controls cookie `secure` attribute; defaults to `true` in production |
| `LOGIN_LOCKOUT_MAX_ATTEMPTS` | — | Failed login attempts before temporary lock; default `5` |
| `LOGIN_LOCKOUT_WINDOW_MINUTES` | — | Temporary login lock window; default `15` minutes |
| `MAGIC_LINK_TTL_MINUTES` | — | Magic-link token TTL in minutes; default `10` |
| `OAUTH_STATE_TTL_MINUTES` | — | OAuth state token TTL in minutes; default `5` |
| `APP_BASE_URL` | Strongly recommended | Public backend origin used for OAuth callback URLs; in single-service deploys this is usually the same as the frontend origin |
| `FRONTEND_BASE_URL` | Strongly recommended | Public frontend origin used in redirects and email links |
| `CANONICAL_BASE_URL` | Optional | Canonical public origin for SEO absolute URLs (canonical tags, `og:url`, sitemap `<loc>`, JSON-LD). Defaults to `https://datathink.co`. Single source of truth for the SEO domain — see [`seo.md`](seo.md). |
| `ALLOWED_ORIGINS` | Strongly recommended | Comma-separated browser origins allowed by CORS and production CSRF checks |
| `RESEND_API_KEY` | Recommended | Enables verification and password-reset emails |
| `EMAIL_FROM` | Recommended | Sender identity for auth emails |
| `GOOGLE_CLIENT_ID` | Optional | Enable Google OAuth login |
| `GOOGLE_CLIENT_SECRET` | Optional | Enable Google OAuth login |
| `GOOGLE_REDIRECT_URI` | Recommended | Explicit Google OAuth callback URL; required in production when Google OAuth credentials are configured |
| `GITHUB_CLIENT_ID` | Optional | Enable GitHub OAuth login |
| `GITHUB_CLIENT_SECRET` | Optional | Enable GitHub OAuth login |
| `GITHUB_REDIRECT_URI` | Recommended | Explicit GitHub OAuth callback URL; required in production when GitHub OAuth credentials are configured |
| `SENTRY_DSN` | — | Optional backend Sentry DSN for production error capture |
| `SENTRY_TRACES_SAMPLE_RATE` | — | Optional backend Sentry tracing sample rate from `0.0` to `1.0`; defaults to `0.0` |
| `VITE_SENTRY_DSN` | — | Optional frontend Sentry DSN; read from runtime config in production and from Vite env in local dev |
| `VITE_POSTHOG_KEY` | — | PostHog project API key for product analytics; read from runtime config in production and from Vite env in local dev |
| `VITE_POSTHOG_HOST` | — | PostHog ingest host; defaults to `https://us.i.posthog.com` |
| `SENTRY_AUTH_TOKEN` | Optional | Required only if you want the frontend build to upload sourcemaps to Sentry |
| `SENTRY_ORG` | Optional | Sentry organization slug for frontend sourcemap upload |
| `SENTRY_PROJECT` | Optional | Sentry project slug for frontend sourcemap upload |
| `SENTRY_RELEASE` | Optional | Release name for backend Sentry + frontend sourcemap upload. **You normally do not need to set this** — both halves fall back to Railway's per-deploy `RAILWAY_GIT_COMMIT_SHA` automatically (frontend: `vite.config.js`; backend: `config.py`), so they share one release id per deploy and Sentry's "resolved in next release" / regression auto-reopen works (see [`runbooks/sentry-fix-pipeline.md`](runbooks/sentry-fix-pipeline.md) Stage 6). **Gotcha:** do *not* set `SENTRY_RELEASE=${{RAILWAY_GIT_COMMIT_SHA}}` — Railway's `${{ }}` reference syntax does **not** resolve Railway-provided vars, so it lands empty and shows `release=unset` in the boot log. The code reads `RAILWAY_GIT_COMMIT_SHA` directly instead. Only set `SENTRY_RELEASE` explicitly if you want a custom release name. |

In `production` mode, startup (`config.validate_production_config()`, called at import) fails fast if `DATABASE_URL`, `REDIS_URL`, `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, the Razorpay subscription plan IDs `RAZORPAY_PLAN_PRO` / `RAZORPAY_PLAN_ELITE` (without them the Pro/Elite subscribe flow 500s at runtime), `RESEND_API_KEY` (transactional email — password reset + verification), or `ADMIN_SECRET` (which must also be **≥32 characters**) are missing. When the Paddle rail is enabled (`PADDLE_CLIENT_TOKEN` set), it **additionally** requires `PADDLE_WEBHOOK_SECRET`, all four `PADDLE_PRICE_*`, and `PADDLE_ENVIRONMENT=production` — so a half-configured Paddle deploy crashes loudly at boot (Railway marks the deploy failed) instead of silently breaking checkout/webhooks. INR-only deploys leave all Paddle vars unset and boot cleanly. Webhook secrets, client tokens, and price IDs are whitespace-stripped at read time, so a pasted trailing newline can't break HMAC verification.

OAuth provider callback URIs should be configured exactly as the redirect vars below:
- `${GOOGLE_REDIRECT_URI}`
- `${GITHUB_REDIRECT_URI}`

Magic-link callback uses:
- `${APP_BASE_URL}/api/auth/magic-link/callback?token=...`

### Production rollout order

1. Provision Postgres and Redis.
2. Set all production environment variables before the first deploy.
3. Run Alembic migrations against the production Postgres database.
4. Deploy the app container.
5. Verify `GET /health`.
6. Verify auth, email flows, payments, and Sentry/PostHog on the deployed URL.

### Single-service production example

For a single Railway-style deployment where FastAPI serves the built SPA and API from the same domain:

```env
ENV=production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECURE_COOKIES=true

APP_BASE_URL=https://your-app.up.railway.app
FRONTEND_BASE_URL=https://your-app.up.railway.app
ALLOWED_ORIGINS=https://your-app.up.railway.app

SENTRY_DSN=https://...
SENTRY_TRACES_SAMPLE_RATE=0.0
VITE_SENTRY_DSN=https://...
VITE_POSTHOG_KEY=phc_...
VITE_POSTHOG_HOST=https://us.i.posthog.com
```

The frontend observability values are injected into the SPA at request time by the backend router, so Railway does not need to pass them as Docker build args.

For backend Sentry, the API automatically tags events with `request_id`, request metadata, and the current user/session context when available.

**Release consistency (important for closing the loop):** backend and frontend both auto-derive the release from `RAILWAY_GIT_COMMIT_SHA`, so they report the *same* release per deploy and Sentry's "Resolved in next release" → auto-reopen-on-regression (the bad-fix tripwire in the [fix pipeline](runbooks/sentry-fix-pipeline.md)) can match events to deploys. No manual `SENTRY_RELEASE` needed — and do **not** use the `${{ RAILWAY_GIT_COMMIT_SHA }}` reference (it lands empty; see the env-var table above).

**Boot-check (confirm the backend is actually reporting):** `init_sentry()` logs its status at startup, so you can verify from the Railway deploy logs without waiting for an error:
- `Sentry initialized (environment=production, release=<sha>, traces_sample_rate=…)` — wired correctly. If `release=unset`, `RAILWAY_GIT_COMMIT_SHA` isn't reaching the runtime env (rare; would also mean the frontend release is unset).
- `Sentry DISABLED in production — SENTRY_DSN is not set` (WARNING) — the backend is dark; set `SENTRY_DSN` in Railway. This is the recurrence guard for the launch finding where the DSN was in local `.env` but never added to Railway, so production captured nothing. Guarded by `tests/test_sentry_bootcheck.py`.

### Frontend sourcemaps

Frontend builds emit hidden sourcemaps. If `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, and `SENTRY_PROJECT` are present **during the build**, `@sentry/vite-plugin` uploads them to Sentry and injects the release; if absent, the build still succeeds and skips upload.

**Critical for the Dockerfile deploy:** "present during the build" means present *inside the Docker build*, which is **not** automatic. Railway only forwards a service variable into a Dockerfile build when the `Dockerfile` declares it as `ARG`. The `frontend-build` stage therefore declares `ARG SENTRY_AUTH_TOKEN / SENTRY_ORG / SENTRY_PROJECT / SENTRY_RELEASE / RAILWAY_GIT_COMMIT_SHA` and passes them inline to `npm run build` (inline, not `ENV`, so the auth token is never baked into an image layer). Without those `ARG` lines the plugin silently no-ops — minified stack traces and `release=unset` on the frontend even when the Railway vars are set. This was the launch finding: the vars were set in Railway but never reached the build. `RAILWAY_GIT_COMMIT_SHA` is declared too so the frontend release matches the backend's (which reads it at runtime).

Build args needed in Railway (service variables, used at build): `SENTRY_AUTH_TOKEN` (an **Organization Auth Token** from Sentry → Settings → Auth/Organization Tokens), `SENTRY_ORG` (e.g. `self-c16`), `SENTRY_PROJECT` (the frontend project, e.g. `javascript-react`).

### Razorpay dashboard setup

1. Sign up at [dashboard.razorpay.com](https://dashboard.razorpay.com) with an Indian business (PAN + bank account for KYC).
2. Under **Settings → API Keys**, generate keys for Test mode first. Copy `Key Id` → `RAZORPAY_KEY_ID` and `Key Secret` → `RAZORPAY_KEY_SECRET`. Repeat under Live mode once KYC is approved.
3. Under **Subscriptions → Plans**, create two plans:
   - Pro monthly: amount `₹999` (99900 paise), period `monthly`, interval `1` → copy Plan id → `RAZORPAY_PLAN_PRO`.
   - Elite monthly: amount `₹1,999` (199900 paise), period `monthly`, interval `1` → `RAZORPAY_PLAN_ELITE`.
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

For Dockerfile-based services on Railway, the application must listen on Railway's injected `PORT`. This repo's Docker image now binds Uvicorn to `${PORT}` with a fallback to `8000` for local container runs. If a Railway deploy shows "build succeeded" followed by a network or healthcheck failure, first verify:

1. the container is listening on `${PORT}`
2. `ENV=production` — **required**. Without this, the app tries to auto-apply schema migrations at startup; if the DB isn't available yet the startup crashes before binding the port and Railway sees a healthcheck timeout instead of a clean 503.
3. `DATABASE_URL` — must point to the Railway-provisioned Postgres service, not localhost. Add a PostgreSQL service in the Railway project, then reference it with `${{Postgres.DATABASE_URL}}` or copy the connection string directly.
4. `REDIS_URL`
5. `RAZORPAY_KEY_ID`
6. `RAZORPAY_KEY_SECRET`
7. `RAZORPAY_WEBHOOK_SECRET`

**Healthcheck behaviour:** `/health` returns HTTP 200 when both Postgres and DuckDB are ready, and HTTP 503 when either is unavailable. Railway marks the deploy as failed on 503, which is intentional — it means a required environment variable is missing or the DB service isn't reachable yet.

---

## Rollback runbook

> **Context:** Production is on Railway with `ENV=production`, which disables Alembic auto-migrate at startup. Redeploying an old image does **not** touch the database schema unless you also run a migration manually. This means code rollback and schema rollback are independent operations — and in most incidents only the code rollback is needed.

### 1. Code rollback (Railway dashboard)

When a bad deploy is live:

1. Open the Railway dashboard → your project → the **datathink** service.
2. Click the **Deployments** tab. Find the last successful deploy (green tick, before the bad one).
3. Click the `···` menu on that deploy → **Redeploy** (some Railway UI versions label this **Rollback**).
4. Railway builds and deploys that image. The health-check at `/health` must return 200 before Railway marks it live.

**Why this is usually safe and fast:** because `ENV=production` disables auto-migrate, redeploying old code does *not* run any migration — the DB schema is unchanged. A code-only rollback takes the same time as a normal deploy and carries zero DB risk.

**Confirm the rollback worked:** the healthcheck passes automatically; then run the smoke checklist in step 4 below.

---

### 2. Database migration decision tree

Only needed when the bad deploy also shipped an Alembic migration. First, confirm the current production revision:

```bash
cd backend
# Read DATABASE_URL from backend/.env line 4 — never hardcode it
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic current
```

Then decide based on what the migration did:

#### Additive migration (ADD COLUMN / CREATE TABLE / CREATE INDEX)

**Do nothing to the DB.** Old code simply ignores the new column or table — additive changes are backward-compatible. Do NOT run `alembic downgrade`. The schema is harmless at head; fix the code bug and redeploy forward.

#### Destructive or irreversible migration (DROP/RENAME column, type narrowing, data backfill/transform)

These are **not safely auto-reversible.** Running `alembic downgrade` may permanently delete or corrupt data. Steps before any action:

1. **Inspect the `downgrade()` body first.** Open the migration file in `backend/alembic/versions/` and read exactly what `downgrade()` does. A `DROP COLUMN IF EXISTS` loses every row of data in that column — no undo.
2. **Prefer a roll-forward fix over a downgrade.** Write a new migration that restores the old shape (re-adds a dropped column, renames it back, etc.) and deploy that. This is almost always safer than running `downgrade` against live data.
3. **If a downgrade is unavoidable:** take a DB snapshot/backup from the Railway dashboard (Postgres service → Backups → Take snapshot) *before* running the downgrade. Then:

```bash
cd backend
# Inspect what downgrade() will do before running it:
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic show <revision_id>

# Downgrade exactly one step (review the output first — this is destructive):
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic downgrade -1

# Confirm the revision:
DATABASE_URL="<from backend/.env line 4>" ../.venv/bin/alembic current
```

Replace `<revision_id>` with the ID printed by `alembic current` before the downgrade. Use the `asyncpg` driver prefix (`postgresql+asyncpg://...`) if the env var uses it — match whatever form is in `backend/.env`.

---

### 3. Post-rollback smoke checklist

Run these checks before standing down to confirm the rollback is actually good:

- [ ] `GET /health` returns `{"status": "ok", "postgres": true, ...}` (HTTP 200)
- [ ] Sign in with a test account works (session cookie is set, `/api/auth/me` returns the user)
- [ ] A practice question loads (GET `/api/practice/<track>/<id>`)
- [ ] A submit succeeds (POST `/api/practice/<track>/<id>/submit` with any answer)
- [ ] A payment webhook receipt path is live — either Razorpay or Paddle signature verification does not 500 (check recent Railway logs for any `500` on `/api/razorpay/webhook` or `/api/paddle/webhook`)

If any check fails, the rollback is not clean — investigate logs before standing down.

---

### 4. When NOT to roll back

Rolling back is not always the right move:

- **The migration was additive and the bug is in code logic:** roll forward with a one-line fix rather than reverting a destructive migration. Additive schema is safe to leave at head.
- **The bad commit touched many files and users have new data:** a code rollback drops the fix; a DB downgrade may lose user progress or payment records accrued since the bad deploy. In these cases a targeted roll-forward patch is safer.
- **The incident is a configuration error (wrong env var, rate limit, CORS):** fix the env var in Railway settings and redeploy at current head — no code or DB rollback needed.

---

## Concurrency & scaling model

**Readiness snapshot (Tier 1 — verified 2026-06-08).** Launch-ready for load & concurrency on a single replica; no blockers. The fixes: all code execution + password hashing run off the event loop (P0/P2), DuckDB access is serialized + table-set snapshotted (no segfault, no head-of-line block), Postgres pool tuned (P1), rate limiter degrades gracefully (P2.2). Two non-blocking operator follow-ups remain: verify the prod proxy peer (§ Rate-limiter operational notes & findings) and the `MAX_CONCURRENT_HASHES` default (below). Decisions: `docs/decisions/DECISIONS.md` (2026-06-08 entries — off-loop execution, off-loop hashing P2.1, rate-limiter P2.2, FORWARDED_ALLOW_IPS).

*Reading the capacity numbers (this is where people misjudge):*
- **Concurrent vs total users.** Only ~1–10% of users are active in the same second, so "low thousands *concurrent*" backs **tens of thousands of *registered*** users. "Hundreds of thousands of users" almost always means total, of which thousands–tens-of-thousands are concurrent at peak.
- **VUs vs real users.** Load-test "VUs" (`backend/loadtest/`) hammer non-stop; a real learner fires a request every several seconds (reads/types between clicks), so **1 VU ≈ 50–100 real users**. The measured ~16–32-VU knee therefore ≈ **a few thousand real concurrent learners**.

*Measured before → after the fixes (single worker, 8 vCPU, mixed read-heavy workload):*

| Signal | Before | After |
|---|---|---|
| `/health` p95, 6 code-execs in flight | 127 ms (9.4×) | ~23 ms (1.2×) |
| `/health` behind one 5 s execution | 4723 ms | ~0 (loop free) |
| 3 concurrent 5 s executions | 15.0 s | 5.0 s |
| Knee (mixed workload) | ~16 VUs | ~16–32 VUs, then CPU-bound |
| Peak throughput | ~250 rps | ~300 rps |
| 5xx errors | 0 | 0 |

The app serves all traffic on a **single event loop per replica** (`uvicorn main:app`, one worker). Code execution is blocking (DuckDB SQL grading; a 5–12 s subprocess sandbox), so it runs **off the loop** via `backend/offload.py` (subprocess sandboxes concurrent up to `MAX_CONCURRENT_EXECUTIONS`; DuckDB serialized behind a process-wide lock — see `docs/backend.md` § Off-loop code execution). **Password hashing** (PBKDF2, ~22 ms/call) is the other blocking-CPU call on the request path and is offloaded the same way under its own `MAX_CONCURRENT_HASHES` cap (see `docs/backend.md` § Off-loop password hashing). Reproduce/measure with `backend/loadtest/` (driver + head-of-line probe; README documents usage).

**Per-replica connection budget.** Each replica opens up to `DB_POOL_SIZE + DB_MAX_OVERFLOW` (default 30) Postgres connections. Keep `replicas × 30` comfortably below the managed-Postgres `max_connections` (Railway's default is ~100–400 depending on plan). Beyond that, put PgBouncer (transaction pooling) in front of Postgres.

**Auth bursts are CPU-bound, not loop-blocking — don't misread the `/health` spike.** Offloading password hashing fixes loop *blocking* (no single 22 ms hash freezes the loop serially), but PBKDF2 is *CPU-bound*, so a burst of many simultaneous registrations/logins genuinely **saturates cores** — and bystander `/health` (which needs a CPU slice + a Postgres ping) slows in proportion. This is expected, not a regression: it is the CPU ceiling, the same one the VU ramp hits at high concurrency. Measured (30 simultaneous registrations, 8-core box, all 201, zero errors): with `MAX_CONCURRENT_HASHES=1`, loaded `/health` p95 = 9 ms (**1.3×** idle); at the default `7`, p95 = 167 ms (**21×**). The cap *changing* the inflation is the proof it is CPU contention — a *blocked* loop would be insensitive to it. So `MAX_CONCURRENT_HASHES` is a **latency-vs-throughput knob**: the default `cores−1` favors burst throughput (drains the hash backlog fastest) at the cost of bystander tail latency *during* a burst; lowering it (e.g. `cores/2`) leaves more cores for the loop and protects bystander latency at the cost of slower burst drain. The cap only binds under a heavy *simultaneous* auth burst — normal load (a few concurrent auths) never reaches it, so day-to-day latency is unaffected either way. Re-confirm with `backend/loadtest/` (the auth-burst probe pattern).

**Tiered roadmap** (honest about the single-process-DuckDB, subprocess-per-execution shape):

| Tier | Change | Expected ceiling (read-heavy) | Effort / risk |
|---|---|---|---|
| **1 — current** | Off-loop execution + real semaphore + DuckDB serialize/table-cache + pool tuning | low **thousands** of concurrent users on one replica; ~`MAX_CONCURRENT_EXECUTIONS` truly-concurrent executions. CPU is the next limiter (single replica saturated ~32 active VUs at 8 vCPU in measurement). | done; low |
| **2 — horizontal replicas** | Multiple stateless app replicas behind Railway; Redis-backed shared rate-limit/session state (already Redis-ready); PgBouncer + a Postgres read replica; CDN for the SPA. DuckDB is loaded per-replica (fine — read-only catalog data). | **tens of thousands** | medium; shared-state correctness |
| **3 — externalize execution** | Move code execution to a dedicated, horizontally-scaled worker fleet / queue so the web tier never blocks on a sandbox; DuckDB per-worker or a query service. | lifts the **execute-heavy** ceiling (the real constraint — execution is CPU/subprocess-bound, not loop-bound) | high; new infra |

**Advance on a *measured* trigger, not ambition** — the harness is how you see it coming:
- **Tier 1 → 2:** one replica's CPU is regularly high (≳70%) at peak. The app is already stateless (state in Postgres + Redis), so Tier 2 is mostly infra (replicas, PgBouncer, read replica, CDN), not code.
- **Tier 2 → 3:** code execution *specifically* is what saturates replicas (web work is cheap but sandboxes peg CPU). Externalizing execution lets read and execute load scale independently.
- **Beyond 3** (hundreds of thousands *concurrent*): cache read-mostly content (Redis/edge), shard Postgres by user, multi-region + autoscale. Mostly a cost question once content is cached and per-user writes shard cleanly.

---

## Rate-limiter operational notes & findings

The per-IP limiter (`RATE_LIMIT_REQUESTS`/`RATE_LIMIT_WINDOW_SECONDS`, default 60/60s) plus the two auth limiters are documented behaviourally in `docs/backend.md` § Rate limiting. Operational findings from the burst probe (`backend/loadtest/ratelimit.py`, 2026-06-08):

- **Degrades gracefully under burst** — measured 60 pass / next 20 `429` with `Retry-After` + `X-RateLimit-*` + the canonical `{error, request_id}` body; the check is O(1), so a burst never stalls the loop.
- **In-memory fallback is single-replica-only, and enforced** — `create_rate_limiter` raises at startup in production if `REDIS_URL` is unset or Redis init fails. The process-local `InMemoryRateLimiter` is dev-only; across horizontal replicas it would be per-replica (ineffective as a global limit), so **`REDIS_URL` is mandatory in prod** (already in the required-env list above and the Tier-2 scaling row).
- **Transient Redis errors fail gracefully, not as 500s** — `check_safe` fails open for the coarse IP + auth-baseline limiters and closed for the token-issue limiter (see `docs/backend.md`).

### Action item — verify per-IP keying behind the prod proxy

The middleware keys on `request.client.host`. The prod Dockerfile now starts `uvicorn` with `--forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"` — the default `127.0.0.1` reproduces uvicorn's built-in default (`proxy_headers=True`), so behaviour is **unchanged until `FORWARDED_ALLOW_IPS` is set**. Empirically (probe, this venv): `X-Forwarded-For` is **trusted from a `127.0.0.1` peer** (we rewrote `client.host` to `8.8.8.8` from loopback) and **ignored from any other peer**.

Consequence: per-IP rate limiting is correct **iff** Railway's edge proxy reaches the container from `127.0.0.1`. If it reaches it from another internal address, `X-Forwarded-For` is dropped and *every* client collapses into a single proxy-IP bucket — the 60/min limit becomes near-global (too aggressive for legitimate users sharing the egress, useless against a distributed abuser).

**To verify:** the app already logs `client_ip=<host>` per request — inspect prod logs for whether `client_ip` shows diverse real client IPs or one repeated internal/proxy address.

**To fix (if it's keying on the proxy):** set the **`FORWARDED_ALLOW_IPS`** env var to the **actual Railway proxy hop** so uvicorn rewrites `client.host` from the trusted `X-Forwarded-For`. The Dockerfile already wires this env into `--forwarded-allow-ips`, so the fix is a **single env-var set — no image change**. **Never set it to `*`** — that lets any client spoof its IP to evade the limiter or frame another address. This is a deliberate deployment + security change pending confirmation of the real prod peer address; it is not applied automatically (the default keeps today's `127.0.0.1`-only trust).

---

## Pre-launch admin seed

Run once against the production database after migrations complete (idempotent upsert).

Credentials can be passed as CLI args or read from `backend/.env` — any env vars present in that file are loaded automatically by the script.

**Seed your personal admin account:**

```bash
cd backend
DATABASE_URL="postgresql://..." \
  ADMIN_EMAIL="admin@datathink.co" \
  ADMIN_NAME="Admin" \
  ADMIN_PASSWORD="ReplaceWithStrongPassword1" \
  ../.venv/bin/python scripts/seed_admin.py
```

The `--plan` flag accepts `free`, `pro`, `elite`, `lifetime_pro`, or `lifetime_elite` (default: `elite`).

**Seed QA test accounts (all `@datathink.co`, bypasses registration restrictions):**

Add `QA_SEED_PASSWORD` to `backend/.env`, then:

```bash
cd backend

../.venv/bin/python scripts/seed_admin.py --email qa_free@datathink.co          --name "QA Free"           --plan free
../.venv/bin/python scripts/seed_admin.py --email qa_pro@datathink.co           --name "QA Pro"            --plan pro
../.venv/bin/python scripts/seed_admin.py --email qa_pro_lifetime@datathink.co  --name "QA Pro Lifetime"   --plan lifetime_pro
../.venv/bin/python scripts/seed_admin.py --email qa_elite@datathink.co         --name "QA Elite"          --plan elite
../.venv/bin/python scripts/seed_admin.py --email qa_elite_lifetime@datathink.co --name "QA Elite Lifetime" --plan lifetime_elite
```

All seeded accounts are created with `email_verified = true` and are idempotent — safe to re-run to reset credentials or plan.

---

## Sandbox security hardening

The user-code execution sandbox has three layers of defense against escape/exfiltration.
The first two are implemented in code and active now; the third requires Railway/infra
configuration.

### Layer 1 — Scrubbed subprocess environment (active)

`python_evaluator._spawn_harness` passes a minimal allow-list env to the sandbox
subprocess (`env=_sandbox_env()`). The subprocess receives only: `PATH`, `HOME`,
`LANG`, `LC_*`, `TMPDIR`, `TZ`, `PYTHONIOENCODING`, `PYTHONDONTWRITEBYTECODE`,
`PYTHONNOUSERSITE`. Every secret (`DATABASE_URL`, `RAZORPAY_KEY_SECRET`,
`GOOGLE/GITHUB_CLIENT_SECRET`, `RESEND_API_KEY`, `SENTRY_DSN`, etc.) is absent.
No `PYTHONPATH` either, so the sandbox cannot `import` backend app modules.

### Layer 2 — AST guard + in-process OS isolation (active)

`python_guard.validate_code` rejects known escape gadgets before execution: dangerous
bare names (`globals`, `locals`, `getattr`, `eval`, `exec`, `__builtins__`, etc.),
dunder chains (`__class__`, `__globals__`, `__subclasses__`, frame/traceback walks),
`str.format`/`.format_map` templates that hide a dunder accessor inside the string
literal (`"{0.__globals__}".format(solve)`, caught by `visit_Constant`),
blocked imports, and pandas/numpy filesystem I/O methods. The guard is tested by
40 red-team attempts in `tests/test_guard_redteam.py` (all must be BLOCKED) and 13
legitimate interview snippets (all must PASS — no false positives). As defense-in-depth
the harness also execs user code with a **restricted `__builtins__`**
(`_safe_builtins`, keeping `__import__`/`__build_class__`), so the AST guard is not the
sole gate on builtins.

`python_evaluator._sandbox_preexec` (the subprocess `preexec_fn`) additionally:
- Calls `os.setsid()` — puts the sandbox in its own process group so a timeout
  SIGKILL terminates the entire subprocess tree, not just the direct child.
- Calls `os.chdir('/tmp')` — moves the cwd away from `/app/backend` so relative
  `open()` calls cannot reach app source files or the backend module tree.
- Calls `_install_seccomp_filter()` — see Layer 3.

### Layer 3 — Seccomp egress filter + read-only app dir (active)

Railway's managed platform uses **eBPF networking** and grants **no `NET_ADMIN`, no
custom `--security-opt`, and no `--read-only`/`--tmpfs`** — so the *container-level*
forms of these (in-container `iptables`, a Docker seccomp profile, a read-only root
fs) are unavailable. We implement the equivalents **in code / in the image** instead:

| Hardening | How we do it (no Railway dependency) | Status |
|---|---|---|
| **Network egress block** | `python_evaluator._install_seccomp_filter` installs a per-process **seccomp** filter in the sandbox `preexec_fn` that denies the network-syscall family (`socket`, `connect`, `sendto`, …) — an unprivileged process can install a filter once `NO_NEW_PRIVS` is set (libseccomp does this on `.load()`). A guard escape cannot open a socket → cannot phone home, exfiltrate, or scan the internal network. Denylist model (allow-by-default) so pandas/numpy file+compute syscalls are untouched. **Validated:** CI (`tests/test_sandbox_seccomp.py`) asserts `socket()`/`connect()` are denied on Linux. | ✅ active |
| **Seccomp profile** | Same filter — it *is* the seccomp profile, applied per-process rather than via the (unavailable) Docker `--security-opt`. | ✅ active |
| **Read-only app dir** | Dockerfile leaves `/app` **root-owned** and runs as non-root `appuser` (no `chown`). appuser reads+executes the app but cannot write it, so an escape cannot drop a backdoor or overwrite a module. `PYTHONDONTWRITEBYTECODE=1` app-wide. Only `/tmp` (world-writable) is writable. The in-image equivalent of `--read-only`. | ✅ active |
| **Memory limit** | `RLIMIT_AS` 512 MB is enforced per-subprocess in the harness. A container-level cap is belt-and-suspenders — set a **Railway service RAM cap** (Settings → Resource Limits, e.g. 1–2 GB) as the last backstop against a memory bomb OOM-killing the whole app process. | ⚠️ set in Railway dashboard |

**Dependencies:** `pyseccomp` (requirements.txt) + `libseccomp2` (Dockerfile `apt-get`,
and the CI `Install libseccomp` step). If either is absent the filter **fails open** —
no breakage, but the egress block is inactive, so both must be present in production.

**The one remaining manual step before launch:** set the Railway service memory cap
(P2). Everything else in this layer is active in code and validated by CI.
