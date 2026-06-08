"""Concurrency smoke tests — regression guard for head-of-line blocking.

The platform serves all traffic on a single event loop (one uvicorn worker per
replica). Every code execution is blocking (DuckDB SQL grading; a 5–12 s subprocess
sandbox for Python/Pandas/statistics). Before the offload fix, those blocking calls
ran directly on the loop, so one slow submission froze every other request — a
concurrent /health was measured stalling ~4.7 s behind a single 5 s execution.

These tests assert the offload discipline in ``offload.py`` that prevents that:

  1. blocking work runs OFF the loop (the loop stays responsive while it runs);
  2. subprocess-style execution is bounded by the global semaphore;
  3. SQL execution is serialized (exactly one DuckDB op in flight at a time);
  4. ``database.get_loaded_tables()`` is served from the startup snapshot and never
     queries the shared DuckDB connection (concurrent use of which segfaults).

Fast + deterministic by design: no DB, no real subprocess — a ``time.sleep`` stands
in for the blocking evaluator so the test exercises the *scheduling* discipline, not
the evaluators themselves (those have their own tests).
"""
import asyncio
import threading
import time

import offload


def _fresh_sql_lock() -> None:
    """Rebind the module-level SQL lock to the current loop.

    ``offload._sql_lock`` is created at import and binds to the first event loop that
    awaits it; each ``asyncio.run`` below is a fresh loop, so we rebind. In the real
    app there is exactly one loop for the process lifetime, so this is a test-only
    concern. ``run_blocking_sql`` reads the module global at call time, so reassigning
    it here is picked up.
    """
    offload._sql_lock = asyncio.Lock()


def test_blocking_exec_does_not_block_the_event_loop():
    """A blocking call dispatched through run_blocking_exec must not stall the loop."""
    async def scenario() -> int:
        _fresh_sql_lock()
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0.01)

        t = asyncio.create_task(ticker())
        await asyncio.sleep(0.01)  # let the ticker start
        await offload.run_blocking_exec(time.sleep, 0.4)  # 0.4 s of blocking work
        t.cancel()
        return ticks

    ticks = asyncio.run(scenario())
    # If the loop were blocked for the 0.4 s, the ~10 ms-cadence ticker could not run.
    assert ticks >= 10, f"event loop appeared blocked during offloaded work (ticks={ticks})"


def test_blocking_sql_does_not_block_the_event_loop():
    """The SQL path is serialized, but must still run off the loop."""
    async def scenario() -> int:
        _fresh_sql_lock()
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                ticks += 1
                await asyncio.sleep(0.01)

        t = asyncio.create_task(ticker())
        await asyncio.sleep(0.01)
        await offload.run_blocking_sql(time.sleep, 0.4)
        t.cancel()
        return ticks

    ticks = asyncio.run(scenario())
    assert ticks >= 10, f"event loop appeared blocked during offloaded SQL (ticks={ticks})"


def test_run_blocking_exec_bounded_by_semaphore():
    """Subprocess-style execution never exceeds the global concurrency cap."""
    import main
    cap = main._MAX_CONCURRENT_EXECUTIONS
    lock = threading.Lock()
    state = {"cur": 0, "peak": 0}

    def job() -> None:
        with lock:
            state["cur"] += 1
            state["peak"] = max(state["peak"], state["cur"])
        time.sleep(0.2)
        with lock:
            state["cur"] -= 1

    async def scenario() -> None:
        _fresh_sql_lock()
        await asyncio.gather(*[offload.run_blocking_exec(job) for _ in range(cap + 4)])

    asyncio.run(scenario())
    assert state["peak"] <= cap, f"semaphore breached: peak={state['peak']} cap={cap}"
    assert state["peak"] >= min(2, cap), "executions did not actually overlap — not concurrent"


def test_run_blocking_sql_is_serialized():
    """All DuckDB access runs one-at-a-time (peak concurrency == 1)."""
    lock = threading.Lock()
    state = {"cur": 0, "peak": 0}

    def job() -> None:
        with lock:
            state["cur"] += 1
            state["peak"] = max(state["peak"], state["cur"])
        time.sleep(0.12)
        with lock:
            state["cur"] -= 1

    async def scenario() -> None:
        _fresh_sql_lock()
        await asyncio.gather(*[offload.run_blocking_sql(job) for _ in range(5)])

    asyncio.run(scenario())
    assert state["peak"] == 1, f"SQL was not serialized: peak concurrency={state['peak']}"


def test_get_loaded_tables_served_from_cache_not_shared_conn():
    """get_loaded_tables() must read the startup snapshot, not query the shared conn.

    Querying the shared golden connection concurrently (which the previous
    implementation did on every /health and every SQL query) segfaults the process.
    """
    import database

    if not database._loaded_table_names:
        database.init_query_engine()
    snapshot = database.get_loaded_tables()
    assert snapshot, "expected a non-empty loaded-table snapshot after init"
    assert "users" in snapshot

    class _Boom:
        def execute(self, *a, **k):
            raise AssertionError("get_loaded_tables queried the shared DuckDB connection")

    saved = database._golden_conn
    try:
        database._golden_conn = _Boom()  # any shared-conn use now raises
        assert database.get_loaded_tables() == snapshot
    finally:
        database._golden_conn = saved
