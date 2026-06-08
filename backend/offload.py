"""Off-event-loop execution for the blocking evaluators.

Every code execution on this platform is **blocking**:

* SQL grading runs synchronous DuckDB queries (``evaluator.evaluate`` / ``run_query``);
* Python / Pandas / statistics grading spawns an OS subprocess sandbox and blocks on
  ``subprocess.communicate()`` for up to 5–12 s.

The API endpoints are ``async def`` and run on a single event loop (one uvicorn
worker per replica). Calling a blocking evaluator directly from the coroutine freezes
that loop for the call's full duration — every other request (other users, /health,
the catalog) stalls behind it. This is head-of-line blocking; with a 5 s Python
timeout a single submission froze a concurrent /health for ~4.7 s in measurement.

These helpers move the blocking work into a worker thread (``asyncio.to_thread``) so
the loop stays free, and gate it with the global code-execution semaphore so total
concurrency stays bounded (peak sandbox memory = concurrency × RLIMIT_AS). The
semaphore was previously cosmetic: because the call blocked the loop, requests
serialized *before* the semaphore could parallelize them.

SQL is a special case. DuckDB is a single in-process engine; concurrent use of its
connection (even creating a cursor while another thread executes) is not thread-safe
and segfaults the process. So SQL additionally runs under a process-wide async lock,
making exactly one DuckDB operation in flight at a time — still off the loop, so
head-of-line blocking is fixed regardless. The lock is acquired *before* the
semaphore so SQL never consumes more than one execution slot, leaving the rest for
subprocess sandboxes. SQL grading is sub-100 ms on the (≤ ~9k-row) datasets, so
serialization is not the throughput bottleneck for this product's traffic mix; the
conservative single-writer discipline is the right call for a determinism-critical
grader (see docs/decisions/DECISIONS.md).
"""
from __future__ import annotations

import asyncio
import os
from typing import Any, Callable, TypeVar

T = TypeVar("T")

# Serializes all DuckDB in-process engine access. asyncio primitives created at
# import time bind to the running loop lazily on first await (Python ≥3.10); the app
# runs one worker == one loop, so this is safe.
_sql_lock = asyncio.Lock()


def _hash_concurrency() -> int:
    # PBKDF2 is CPU-bound and releases the GIL, so the natural ceiling is roughly the
    # core count; leave one core for the event loop itself. Override with
    # MAX_CONCURRENT_HASHES (kept independent of MAX_CONCURRENT_EXECUTIONS on purpose).
    default = max(2, (os.cpu_count() or 4) - 1)
    raw = os.environ.get("MAX_CONCURRENT_HASHES")
    if raw is None:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


# Bounds concurrent password hashing. Auth hashing (``run_blocking_hash``) and sandbox
# code execution (``run_blocking_exec``) are different resource classes — a small CPU
# burst vs. a heavy 512 MB subprocess — so they get SEPARATE caps and never contend
# for each other's slots (an auth burst must not starve code execution, or vice
# versa). Same lazy loop-binding as ``_sql_lock`` above.
_hash_semaphore = asyncio.Semaphore(_hash_concurrency())


def _execution_semaphore() -> asyncio.Semaphore:
    # Lazy import avoids the main → routers → offload → main import cycle; by the time
    # a request runs, main is fully loaded.
    import main as _main
    return _main.get_execution_semaphore()


async def run_blocking_exec(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking SUBPROCESS-backed evaluator off the loop, under the global cap.

    Subprocess sandboxes are process-isolated, so several may run concurrently up to
    the semaphore limit (default cores − 2). Use this for Python / Pandas / statistics
    code execution.
    """
    async with _execution_semaphore():
        return await asyncio.to_thread(fn, *args, **kwargs)


async def run_blocking_sql(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking DuckDB evaluator off the loop, serialized behind the SQL lock.

    Acquire the SQL lock first (one DuckDB op at a time, waiting cheaply in the loop),
    then the global cap, then offload. Use this for ``evaluator.evaluate`` and
    ``evaluator.run_query``.
    """
    async with _sql_lock:
        async with _execution_semaphore():
            return await asyncio.to_thread(fn, *args, **kwargs)


async def run_blocking_hash(fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """Run a blocking password hash/verify (PBKDF2) off the loop, under the hash cap.

    PBKDF2 with 260k iterations is ~22 ms of CPU per call and runs *synchronously*
    inside ``hashlib.pbkdf2_hmac``. Called directly from an ``async def`` auth endpoint
    it blocks the single event loop for that whole 22 ms — under an auth burst the
    calls serialize on the loop (e.g. 100 concurrent logins ≈ 2.2 s of loop block,
    stalling every unrelated request). Offloading to a worker thread keeps the loop
    free (``pbkdf2_hmac`` releases the GIL, so threads run truly parallel across cores);
    ``_hash_semaphore`` bounds how many of those CPU burns run at once. Use this for
    ``db.hash_password`` / ``db.verify_password_async``.
    """
    async with _hash_semaphore:
        return await asyncio.to_thread(fn, *args, **kwargs)
