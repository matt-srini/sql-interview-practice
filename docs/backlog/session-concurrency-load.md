# Opus session prompt — Load & concurrency readiness

Paste the block below into a fresh Opus session. Context, the known head-of-line-blocking
finding, the bottleneck stack, and the pre-scoped fix are all embedded so the session needn't
rediscover them. See [`../../TODO.md`](../../TODO.md) for the one-line summary.

---

```
# datathink — Load & concurrency readiness: simulate multi-user load, find the ceiling, fix it

You are an Opus session. Hold all five CLAUDE.md lenses (read CLAUDE.md first for product
frame, standing instructions: commit to main, keep CI green, verify-then-report-then-fix,
never break the sandbox/entitlement/grading-determinism hardening already in place).

## The problem (why this session exists)
The platform has only ever been exercised by ONE user at a time (manual testing + functional
unit tests that fire a single request). We have NO load tests and NO multi-user flow
simulation. We do not actually know how many concurrent users it can serve before latency
explodes or it falls over — and the goal is to support many concurrent learners (realistic
target: low thousands now, with a mapped architectural path beyond). This session must:
(1) BUILD the capability to simulate concurrent users running realistic flows,
(2) MEASURE the current architecture's ceiling and where it breaks,
(3) FIX the bottlenecks in priority order,
(4) RE-MEASURE to prove the improvement.

Terms (so we're precise):
- "Head-of-line blocking": one slow request stalls others behind it. Suspected here because
  async endpoints call blocking code directly (see below).
- "The knee": the concurrency level where latency / error-rate stops being flat and explodes.
- "p95/p99 latency": the 95th/99th-percentile response time — the slow-tail users feel.

## What is ALREADY KNOWN — do not rediscover (established in a prior session, verify don't re-derive)
- HEAD-OF-LINE BLOCKING (prime suspect): every code-execution endpoint is `async def` but
  calls its BLOCKING evaluator DIRECTLY (e.g. `return run_python_code(...)`, no
  `await asyncio.to_thread`). A 5–12 s code execution therefore stalls the whole event loop —
  every other request (other users, /health, catalog) freezes for that duration. The global
  concurrency semaphore added recently (main.py `_execution_semaphore`, dep
  `deps.get_execution_semaphore`, default cores−2 via MAX_CONCURRENT_EXECUTIONS) is largely
  COSMETIC because of this — blocking calls already serialize on the single-threaded loop.
- THE BOTTLENECK STACK to scrutinize:
    * DuckDB — single-process, in-memory, loaded once (SQL execution). `SET threads TO 1` on
      the golden connection for grading determinism (database.py:42). duckdb is pinned to 1.5.0.
    * Subprocess-per-execution — Python/Pandas/statistics each spawn an OS subprocess
      (512 MB RLIMIT_AS, RLIMIT_NPROC/FSIZE/CPU, killpg-on-timeout); bounded by the cores−2
      semaphore.
    * Postgres async pool (db.py) — identity/progress/plans/billing.
    * Redis rate limiter (60 req/min/IP) / in-memory fallback.
    * Single Railway replica: 8 vCPU / 8 GB (MAX_CONCURRENT_EXECUTIONS=6 set in Railway env).
- THE PRE-SCOPED FIX (verify, then implement after measuring): offload the blocking evaluator
  to a thread INSIDE the semaphore — `async with sem: return await asyncio.to_thread(fn, …)` —
  uniformly across ALL code-exec endpoints (questions.py, python_questions.py,
  python_data_questions.py, statistics_questions.py, sample.py, mock.py). DuckDB CAVEAT: the
  subprocess paths are process-isolated (safe to run concurrently in threads); SQL is DuckDB
  IN-PROCESS, so verify cursor thread-safety and default to serializing SQL behind a lock
  (still off-loop) if unsure.
- Pointers: docs/backend.md (§ Python execution pipeline, § Code-execution concurrency cap,
  § Category-3 caps), docs/decisions/DECISIONS.md (concurrency + sandbox entries),
  docs/deployment.md (Railway scale / replica limits).

## DELIVERABLE 1 — the load-simulation capability (the foundation; we have none today)
- Two tiers:
    (a) FAST in-process concurrency tests (pytest + async test client / httpx.AsyncClient):
        fire N simultaneous requests and assert the system stays BOUNDED and RESPONSIVE —
        e.g. while a deliberately-slow code execution runs, /health and /catalog stay fast
        (this directly tests the head-of-line-blocking fix). Small N, CI-runnable.
    (b) REALISTIC LOAD HARNESS (off-CI, run against a local/staging deploy): pick + justify a
        tool (k6, Locust, or artillery — must handle session cookies, the prod CSRF/Origin
        rule, and code-execution payloads). Simulate concurrent VIRTUAL USERS running real
        FLOWS, not one hammered endpoint.
- Define the real user journeys to script (weight them realistically — most traffic is
  read/browse, a minority is execute-heavy):
    * Anonymous: land → browse catalog → open a sample question → submit a sample (code run).
    * Register in place → solve a practice question WITH code execution (the expensive path).
    * Mock interview session (start → fetch questions → submit → finish).
    * Dashboard / insights read.
- Commit the harness + scenarios into the repo (e.g. backend/loadtest/), documented so anyone
  can run a load profile, plus the CI smoke-concurrency test.

## DELIVERABLE 2 — measure the current ceiling (baseline BEFORE any fix)
- Ramp virtual users; capture per level: throughput (req/s), latency p50/p95/p99, error rate,
  and resource saturation (CPU, memory, Postgres connections-in-use vs pool size, live
  subprocess count, event-loop lag). Find the knee.
- Quantify head-of-line blocking explicitly: measured /health latency WHILE code executions
  are in flight, before vs after the fix.
- Report the honest current concurrent-user ceiling and what saturates first.

## DELIVERABLE 3 — fix bottlenecks (prioritized, AFTER measurement) + re-measure
- Likely P0: the head-of-line offload fix above. Then: Postgres pool sizing vs replicas;
  catalog/static caching; rate-limiter behavior under burst.
- Be honest about the architectural ceiling: a single-replica, single-process-DuckDB,
  subprocess-per-execution design has a hard limit (likely low-thousands concurrent for
  read-heavy, far less for execute-heavy). Map a TIERED roadmap, don't promise "millions" on
  the current shape:
    * Tier 1 (config + the offload fix + pool tuning): → low thousands concurrent.
    * Tier 2 (horizontal app replicas behind Railway; stateless app tier; Redis-backed shared
      state; read replicas / connection pooler for Postgres; CDN for the SPA): → tens of thousands.
    * Tier 3 (externalize code execution to a dedicated horizontally-scaled worker fleet /
      queue, so the web tier never blocks; DuckDB per-worker or a query service): → the real
      ceiling-raiser for execute-heavy load.
  For each tier: the change, the expected ceiling, the effort/risk.

## METHOD
Verify every claim against the real code. Produce a BASELINE measurement + a prioritized
findings/roadmap report and STOP for approval before large request-path changes. Then
implement the P0 offload fix carefully (subprocess paths concurrent, SQL serialized off-loop),
re-measure to prove it, and keep CI green. The load harness lives in the repo; the CI smoke
test must be fast. Do not weaken the sandbox, entitlement, or grading-determinism guarantees.

## START BY
Read CLAUDE.md + docs/backend.md + docs/deployment.md + docs/decisions/DECISIONS.md; confirm
(don't assume) that no load/concurrency tests exist today; build the Deliverable-1 harness +
scenarios; capture the baseline ceiling; THEN present the findings + tiered roadmap before
implementing fixes.
```
