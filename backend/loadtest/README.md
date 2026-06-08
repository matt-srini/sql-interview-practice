# Load-simulation harness

> Simulate concurrent learners running realistic flows, find the concurrency knee,
> and measure head-of-line blocking. Built because the platform had **no** load or
> multi-user tests — every prior test fires a single request.

There are two tiers, plus a CI smoke test:

| Tier | What | Where | Runs in CI? |
|---|---|---|---|
| **A — realistic load** | Many virtual users (VUs) replay weighted journeys against a *running* server; stepped ramp finds the knee | `loadtest/driver.py` + `loadtest/scenarios.py` | No (off-CI) |
| **A′ — focused probe** | Isolated head-of-line measurement: `/health` latency while N code-executions are in flight | `loadtest/headofline.py` | No (off-CI) |
| **B — smoke concurrency** | Fast in-process assertion that a slow execution does *not* freeze cheap endpoints | `backend/tests/test_concurrency_smoke.py` | **Yes** (fast) |

## Why a pure-asyncio + httpx driver (and not k6 / Locust / artillery)

- **Zero new dependencies.** `httpx` is already a backend dependency. k6 needs a Go
  binary, Locust is a heavy extra dependency, artillery needs Node. A harness that
  "anyone can run" shouldn't require an install the rest of the repo doesn't have.
- **Native session + CSRF handling.** Each VU owns an `httpx.AsyncClient`; its cookie
  jar *is* the backend session (per-user isolation the journeys need), and the prod
  CSRF `Origin` header is one line.
- **One coherent clock.** Stepped ramp, per-window percentiles, the separate
  head-of-line probe, and (optional) resource sampling all live in one process.

Locust remains a fine pick if you want a web UI or distributed generation — the
journeys in `scenarios.py` port to a Locust `HttpUser` with little change. We lead
with the zero-dep driver deliberately.

## User journeys (weighted, read-heavy — see `scenarios.py`)

| Journey | Weight | Flow |
|---|---|---|
| `anon_browse_sample` | 50 | land → catalog → open a sample → submit a sample (1 cheap SQL execution) |
| `browse_only` | 25 | catalog + question-detail reads (no execution) |
| `practice_execute` | 15 | register in place → solve a practice question **with code execution** (subprocess — expensive) |
| `mock_session` | 5 | start → fetch → submit → finish a mock (DB-heavy; PySpark MCQ = no code exec) |
| `dashboard_read` | 5 | dashboard + coaching insights reads |

The weights mirror real usage: most traffic browses/reads; a minority executes code.

## Running it

```bash
# 1. Start a server the way prod does (single worker, one event loop):
cd backend
ENV=development DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice \
  MAX_CONCURRENT_EXECUTIONS=6 ../.venv/bin/uvicorn main:app --port 8000 --workers 1

# 2. Ramp to find the knee (steps = VU counts):
../.venv/bin/python -m loadtest.driver --base-url http://127.0.0.1:8000 \
  --steps 1,4,8,16,32,64 --step-seconds 14

# Single fixed level instead of a ramp:
../.venv/bin/python -m loadtest.driver --vus 16 --duration 30

# Sample server CPU/RSS too (pip install psutil; pass the listening PID):
../.venv/bin/python -m loadtest.driver --steps 8,16,32 \
  --server-pid "$(lsof -ti tcp:8000 -s tcp:listen | head -1)"

# Focused head-of-line probe:
../.venv/bin/python -m loadtest.headofline --inflight 6
```

`--json` emits machine-readable per-step rows for trend tracking.

## Reading the output

```
  VUs     req     rps     p50      p95   ...   /health p95   /cat p95   cpu%
```

- **p50/p95/p99/max** — response latency over completed (non-network) responses.
- **err%** — 5xx + transport/timeout rate. **thr** — 429 throttled. **rej** — 4xx
  business rejects (locked questions / mock limits — expected, not failure).
- **`/health` p95 — the head-of-line-blocking signal.** `/health` does almost no
  work; if its p95 climbs under load, the **event loop is blocked** by something
  (today: blocking code executions). This is the single most important column.
- **`/cat` p95** — `/api/catalog` touches Postgres; if it climbs while `/health`
  stays flat, the **Postgres pool** is the bottleneck, not the loop.
- **cpu% / rssMB** — server process saturation (only when `--server-pid` + psutil).

## Notes / gotchas

- **Localhost bypasses the rate limiter in dev** (`IS_PROD` false + `127.0.0.1`), so a
  local ramp measures the app's concurrency ceiling, not the 60-req/min limiter. To
  exercise the limiter, run against a prod-mode deploy or a non-loopback address.
- Each VU registers a unique `load-<runtag>-<n>@internal.test` user; the mock journey
  self-upgrades to Pro via the dev-only `/api/user/plan`. Run against a disposable DB.
- Server should run **single-worker** to mirror the production `uvicorn main:app`
  (one replica, one event loop) — that is the configuration whose ceiling we care about.
