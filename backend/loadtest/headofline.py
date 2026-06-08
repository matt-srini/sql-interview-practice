"""Focused head-of-line-blocking probe (HTTP-level).

Isolates the single effect the P0 fix targets: does an in-flight *code execution*
(the heavy, blocking path) delay an unrelated cheap request (``/health``)?

It measures ``/health`` latency (1) at idle, then (2) while ``--inflight`` concurrent
Python *submit* requests (each spawns a subprocess sandbox) are continuously in
flight, and prints the inflation. On the unfixed server the blocking evaluator runs
directly on the single event loop, so idle ``/health`` (~5-10ms) balloons to
hundreds of ms — every other user feels it. After the offload fix, loaded
``/health`` should stay close to idle.

    cd backend && ../.venv/bin/python -m loadtest.headofline --base-url http://127.0.0.1:8000 --inflight 6
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

import httpx

from loadtest.driver import _pct

_PY_ANSWER = "def solve(*args, **kwargs):\n    return None\n"


async def _register(client: httpx.AsyncClient) -> int | None:
    await client.get("/api/catalog")
    tag = str(int(time.time() * 1000))
    r = await client.post("/api/auth/register",
                          json={"email": f"hol-{tag}@internal.test", "name": "HOL", "password": "Password1"})
    cat = await client.get("/api/python/catalog")
    try:
        for g in cat.json().get("groups", []):
            for q in g.get("questions", []):
                if q.get("state") != "locked":
                    return q.get("id")
    except Exception:
        return None
    return None


async def _health_samples(client: httpx.AsyncClient, n: int, gap: float) -> list[float]:
    out = []
    for _ in range(n):
        t = time.perf_counter()
        try:
            await client.get("/health")
        except Exception:
            pass
        out.append((time.perf_counter() - t) * 1000.0)
        await asyncio.sleep(gap)
    return out


async def _hammer(client: httpx.AsyncClient, qid: int, stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await client.post("/api/python/submit",
                              json={"question_id": qid, "code": _PY_ANSWER, "duration_ms": 100})
        except Exception:
            pass


async def _amain(args) -> None:
    base = args.base_url
    origin = base.rstrip("/")
    async with httpx.AsyncClient(base_url=base, timeout=30.0, headers={"Origin": origin}) as probe:
        idle = await _health_samples(probe, 30, 0.05)

        # Spin up N hammer clients each looping heavy submits.
        stop = asyncio.Event()
        hammers = []
        clients = []
        for _ in range(args.inflight):
            c = httpx.AsyncClient(base_url=base, timeout=30.0, headers={"Origin": origin})
            clients.append(c)
            qid = await _register(c)
            if qid is not None:
                hammers.append(asyncio.create_task(_hammer(c, qid, stop)))
        await asyncio.sleep(1.0)  # let executions fill the pipe
        loaded = await _health_samples(probe, 50, 0.05)
        stop.set()
        for h in hammers:
            h.cancel()
        await asyncio.gather(*hammers, return_exceptions=True)
        for c in clients:
            await c.aclose()

    print(f"\n/health latency — idle vs {args.inflight} code-executions in flight")
    print("-" * 58)
    print(f"{'':10}{'p50':>8}{'p95':>9}{'p99':>9}{'max':>9}")
    print(f"{'idle':10}{_pct(idle,50):>8.1f}{_pct(idle,95):>9.1f}{_pct(idle,99):>9.1f}{max(idle):>9.1f}")
    print(f"{'loaded':10}{_pct(loaded,50):>8.1f}{_pct(loaded,95):>9.1f}{_pct(loaded,99):>9.1f}{max(loaded):>9.1f}")
    infl = _pct(loaded, 95) / _pct(idle, 95) if _pct(idle, 95) else float("nan")
    print(f"\nhead-of-line inflation (loaded p95 / idle p95): {infl:.1f}x")


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="head-of-line-blocking probe")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--inflight", type=int, default=6)
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
