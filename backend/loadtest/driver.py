"""Realistic multi-virtual-user load driver for datathink.

Drives a *running* server over HTTP (not in-process) with weighted, cookie-bearing
user journeys (see ``scenarios.py``), ramps virtual-user (VU) count through a series
of steps to find the knee, and reports per-step throughput, latency percentiles,
error/throttle/reject rates, a head-of-line-blocking probe, and (optionally) server
resource saturation.

Why a pure-asyncio + httpx driver instead of k6 / Locust / artillery
-------------------------------------------------------------------
* **Zero new dependencies.** ``httpx`` is already a backend dependency; k6 needs a
  Go binary, Locust is a heavy extra dep, artillery needs Node. A harness that
  "anyone can run" should not require an install step the rest of the repo doesn't.
* **Native session handling.** Each VU owns an ``httpx.AsyncClient`` whose cookie
  jar is the backend session — exactly the per-user isolation the journeys need —
  and we can attach the prod CSRF ``Origin`` header trivially.
* **Full control of the measurement.** Stepped ramp, per-window percentiles, the
  separate head-of-line probe, and resource sampling all live in one process, so
  the numbers in the report come from one coherent clock.

Locust remains a fine choice if you want its web UI / distributed mode; the
journeys in ``scenarios.py`` are written so they could be ported to a Locust
``HttpUser`` with little change. We lead with the zero-dep driver on purpose.

Usage
-----
    # 1. Start a server (single worker, mirrors prod's `uvicorn main:app`):
    cd backend && ENV=development DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice \
        ../.venv/bin/uvicorn main:app --port 8000 --workers 1

    # 2. Ramp it (find the knee):
    cd backend && ../.venv/bin/python -m loadtest.driver \
        --base-url http://127.0.0.1:8000 --steps 1,4,8,16,32,64 --step-seconds 15

    # Single fixed level instead of a ramp:
    ../.venv/bin/python -m loadtest.driver --base-url http://127.0.0.1:8000 --vus 16 --duration 30

    # Sample server CPU/RSS too (macOS/Linux; needs psutil + the server PID):
    ../.venv/bin/python -m loadtest.driver --steps 8,16,32 --server-pid 12345
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import math
import sys
import time
from dataclasses import dataclass, field

import httpx

from loadtest import scenarios

try:  # optional — resource sampling only
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


_email_counter = itertools.count(1)
_RUN_TAG = str(int(time.time()))


# --------------------------------------------------------------------------- #
# Sample recording + metrics
# --------------------------------------------------------------------------- #
@dataclass
class Sample:
    t: float            # monotonic timestamp at request completion
    name: str           # logical endpoint name
    latency_ms: float
    klass: str          # ok | rejected | throttled | error


@dataclass
class CorrectnessCheck:
    t: float            # monotonic timestamp
    name: str           # oracle name (e.g. "pandas_correct")
    passed: bool        # True iff the response body was correct


class Recorder:
    """Single-event-loop sample store (plain list append is safe here)."""

    def __init__(self) -> None:
        self.samples: list[Sample] = []
        self.probe: list[Sample] = []
        self.correctness: list[CorrectnessCheck] = []

    def add(self, s: Sample) -> None:
        self.samples.append(s)

    def add_probe(self, s: Sample) -> None:
        self.probe.append(s)

    def add_correctness_check(self, name: str, passed: bool) -> None:
        """Record whether a journey's correctness oracle passed.

        Journeys that submit a known-correct solution call this with the result
        of ``payload.get("correct") is True``.  A False here means the server
        returned HTTP 200 with an error body (e.g. an OpenBLAS sandbox abort)
        that the status-code-only classifier would count as "ok".
        """
        self.correctness.append(CorrectnessCheck(time.monotonic(), name, passed))

    def correctness_summary(self) -> dict:
        """Return per-oracle {total, passed, pass_rate_pct} keyed by name."""
        by_name: dict[str, list[bool]] = {}
        for c in self.correctness:
            by_name.setdefault(c.name, []).append(c.passed)
        result = {}
        for name, checks in sorted(by_name.items()):
            total = len(checks)
            passed = sum(1 for ok in checks if ok)
            result[name] = {
                "total": total,
                "passed": passed,
                "pass_rate_pct": round(100.0 * passed / total, 1) if total else 0.0,
            }
        return result


def _pct(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    idx = q / 100.0 * (len(s) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


@dataclass
class Window:
    label: str
    vus: int
    seconds: float
    samples: list[Sample]
    probe: list[Sample]
    cpu_pct: float | None = None
    rss_mb: float | None = None

    def _classed(self, *klasses: str) -> list[Sample]:
        return [s for s in self.samples if s.klass in klasses]

    def summary(self) -> dict:
        served = self._classed("ok", "rejected")  # completed (non-network) responses
        lat = [s.latency_ms for s in served]
        total = len(self.samples)
        errors = sum(1 for s in self.samples if s.klass == "error")
        throttled = sum(1 for s in self.samples if s.klass == "throttled")
        rejected = sum(1 for s in self.samples if s.klass == "rejected")
        probe_health = [s.latency_ms for s in self.probe if s.name == "probe_health"]
        probe_catalog = [s.latency_ms for s in self.probe if s.name == "probe_catalog"]
        return {
            "vus": self.vus,
            "requests": total,
            "throughput_rps": round(total / self.seconds, 1) if self.seconds else 0.0,
            "p50_ms": round(_pct(lat, 50), 1),
            "p95_ms": round(_pct(lat, 95), 1),
            "p99_ms": round(_pct(lat, 99), 1),
            "max_ms": round(max(lat), 1) if lat else 0.0,
            "errors": errors,
            "throttled": throttled,
            "rejected": rejected,
            "error_rate_pct": round(100.0 * errors / total, 1) if total else 0.0,
            "probe_health_p95_ms": round(_pct(probe_health, 95), 1),
            "probe_health_max_ms": round(max(probe_health), 1) if probe_health else 0.0,
            "probe_catalog_p95_ms": round(_pct(probe_catalog, 95), 1),
            "cpu_pct": self.cpu_pct,
            "rss_mb": self.rss_mb,
        }


# --------------------------------------------------------------------------- #
# Virtual user
# --------------------------------------------------------------------------- #
class VirtualUser:
    def __init__(self, client: httpx.AsyncClient, recorder: Recorder, rng) -> None:
        self.client = client
        self.recorder = recorder
        self.rng = rng
        self._registered = False
        self._pro = False
        self.user_id: str | None = None

    async def _do(self, method: str, path: str, name: str, **kw):
        start = time.perf_counter()
        klass = "error"
        payload = None
        try:
            resp = await self.client.request(method, path, **kw)
            ms = (time.perf_counter() - start) * 1000.0
            sc = resp.status_code
            if sc == 429:
                klass = "throttled"
            elif 500 <= sc:
                klass = "error"
            elif 400 <= sc:
                klass = "rejected"
            else:
                klass = "ok"
                try:
                    payload = resp.json()
                except Exception:
                    payload = None
        except Exception:
            ms = (time.perf_counter() - start) * 1000.0
        self.recorder.add(Sample(time.monotonic(), name, ms, klass))
        return payload

    async def get(self, path: str, name: str):
        return await self._do("GET", path, name)

    async def post(self, path: str, name: str, json: dict | None = None):
        return await self._do("POST", path, name, json=json or {})

    async def ensure_registered(self) -> None:
        if self._registered:
            return
        # Anonymous user row first (mirrors the real flow), then upgrade in place.
        await self.get("/api/catalog", name="catalog_sql")
        email = f"load-{_RUN_TAG}-{next(_email_counter)}@internal.test"
        payload = await self._do(
            "POST", "/api/auth/register", name="register",
            json={"email": email, "name": "Load VU", "password": "Password1"},
        )
        if isinstance(payload, dict):
            self.user_id = (payload.get("user") or {}).get("id")
        self._registered = True

    async def ensure_pro(self) -> None:
        if self._pro or not self.user_id:
            return
        await self._do(
            "POST", "/api/user/plan", name="plan_upgrade",
            json={"user_id": self.user_id, "new_plan": "pro", "context": "loadtest"},
        )
        self._pro = True


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
class LoadEngine:
    def __init__(self, base_url: str, origin: str, timeout: float, server_pid: int | None) -> None:
        self.base_url = base_url
        self.origin = origin
        self.timeout = timeout
        self.recorder = Recorder()
        self._stop = asyncio.Event()
        self._vu_tasks: list[asyncio.Task] = []
        self._clients: list[httpx.AsyncClient] = []
        self._proc = None
        if server_pid and psutil is not None:
            try:
                self._proc = psutil.Process(server_pid)
                self._proc.cpu_percent(None)  # prime
            except Exception:
                self._proc = None

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"Origin": self.origin},
            follow_redirects=False,
        )

    async def _vu_loop(self, vu_index: int) -> None:
        client = self._new_client()
        self._clients.append(client)
        rng = __import__("random").Random(vu_index * 7919 + 1)
        vu = VirtualUser(client, self.recorder, rng)
        while not self._stop.is_set():
            journey = scenarios.pick_journey(rng)
            try:
                await journey(vu)
            except Exception:
                pass  # journeys should not raise; swallow to keep the VU alive
            await asyncio.sleep(rng.uniform(0.05, 0.25))  # brief think-time

    async def _probe_loop(self) -> None:
        """Continuously hit two cheap endpoints to detect head-of-line blocking.

        /health → event-loop-lag proxy (no heavy work; if it spikes the loop is
        blocked). /api/catalog → DB-touch proxy (if it spikes while /health is fine,
        the Postgres pool is the bottleneck, not the loop).
        """
        client = self._new_client()
        self._clients.append(client)
        while not self._stop.is_set():
            for path, name in (("/health", "probe_health"), ("/api/catalog", "probe_catalog")):
                start = time.perf_counter()
                klass = "error"
                try:
                    resp = await client.get(path)
                    klass = "ok" if resp.status_code < 400 else "error"
                except Exception:
                    pass
                ms = (time.perf_counter() - start) * 1000.0
                self.recorder.add_probe(Sample(time.monotonic(), name, ms, klass))
            await asyncio.sleep(0.25)

    async def _scale_to(self, target: int) -> None:
        while len(self._vu_tasks) < target:
            idx = len(self._vu_tasks)
            self._vu_tasks.append(asyncio.create_task(self._vu_loop(idx)))

    def _sample_resources(self) -> tuple[float | None, float | None]:
        if self._proc is None:
            return None, None
        try:
            return round(self._proc.cpu_percent(None), 1), round(self._proc.memory_info().rss / 1e6, 1)
        except Exception:
            return None, None

    async def run_ramp(self, steps: list[int], step_seconds: float) -> list[Window]:
        probe = asyncio.create_task(self._probe_loop())
        windows: list[Window] = []
        try:
            for step_vus in steps:
                await self._scale_to(step_vus)
                w_start = time.monotonic()
                cpu_samples: list[float] = []
                rss_latest: float | None = None
                # sample resources ~1/s across the window
                elapsed = 0.0
                while elapsed < step_seconds:
                    await asyncio.sleep(min(1.0, step_seconds - elapsed))
                    cpu, rss = self._sample_resources()
                    if cpu is not None:
                        cpu_samples.append(cpu)
                    if rss is not None:
                        rss_latest = rss
                    elapsed = time.monotonic() - w_start
                w_end = time.monotonic()
                samples = [s for s in self.recorder.samples if w_start <= s.t < w_end]
                probes = [s for s in self.recorder.probe if w_start <= s.t < w_end]
                windows.append(Window(
                    label=f"{step_vus} VUs", vus=step_vus, seconds=w_end - w_start,
                    samples=samples, probe=probes,
                    cpu_pct=round(max(cpu_samples), 1) if cpu_samples else None,
                    rss_mb=rss_latest,
                ))
        finally:
            self._stop.set()
            probe.cancel()
            for t in self._vu_tasks:
                t.cancel()
            await asyncio.gather(*self._vu_tasks, probe, return_exceptions=True)
            for c in self._clients:
                await c.aclose()
        return windows


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def print_report(windows: list[Window], recorder: Recorder | None, as_json: bool) -> None:
    rows = [w.summary() for w in windows]
    if as_json:
        payload: dict = {"windows": rows}
        if recorder is not None:
            payload["correctness"] = recorder.correctness_summary()
        print(json.dumps(payload, indent=2))
        return
    hdr = (
        f"{'VUs':>5} {'req':>7} {'rps':>7} {'p50':>7} {'p95':>8} {'p99':>9} "
        f"{'max':>9} {'err%':>6} {'thr':>5} {'rej':>5} {'/health p95':>12} {'/cat p95':>10} {'cpu%':>6} {'rssMB':>7}"
    )
    print("\n" + hdr)
    print("-" * len(hdr))
    for r in rows:
        print(
            f"{r['vus']:>5} {r['requests']:>7} {r['throughput_rps']:>7} "
            f"{r['p50_ms']:>7} {r['p95_ms']:>8} {r['p99_ms']:>9} {r['max_ms']:>9} "
            f"{r['error_rate_pct']:>6} {r['throttled']:>5} {r['rejected']:>5} "
            f"{r['probe_health_p95_ms']:>12} {r['probe_catalog_p95_ms']:>10} "
            f"{str(r['cpu_pct']) if r['cpu_pct'] is not None else '-':>6} "
            f"{str(r['rss_mb']) if r['rss_mb'] is not None else '-':>7}"
        )
    print(
        "\nLegend: err%=5xx+transport rate · thr=429 throttled · rej=4xx business rejects (locks/limits) ·"
        "\n        /health p95 = event-loop-lag proxy · /cat p95 = Postgres-pool proxy."
    )

    # Correctness oracle — catches 200-with-{error} silent failures (e.g. OpenBLAS abort)
    if recorder is not None:
        summary = recorder.correctness_summary()
        if summary:
            print("\nCorrectness oracle:")
            print(f"  {'oracle':<40} {'passed':>8} {'total':>8} {'pass%':>7}  result")
            print("  " + "-" * 72)
            for name, s in summary.items():
                marker = "PASS" if s["pass_rate_pct"] >= 100.0 else "FAIL ← silent 200-error"
                print(
                    f"  {name:<40} {s['passed']:>8} {s['total']:>8} "
                    f"{s['pass_rate_pct']:>6.1f}%  {marker}"
                )


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="datathink load driver")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--origin", default=None, help="CSRF Origin header (defaults to base-url origin)")
    p.add_argument("--steps", default=None, help="comma list of VU counts for a ramp, e.g. 1,4,8,16,32")
    p.add_argument("--step-seconds", type=float, default=15.0)
    p.add_argument("--vus", type=int, default=None, help="single fixed VU level (alternative to --steps)")
    p.add_argument("--duration", type=float, default=20.0, help="seconds for the single fixed level")
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--server-pid", type=int, default=None, help="sample this process's CPU/RSS (needs psutil)")
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return p.parse_args(argv)


async def _amain(args: argparse.Namespace) -> None:
    origin = args.origin or args.base_url.rstrip("/")
    if args.steps:
        steps = [int(x) for x in args.steps.split(",") if x.strip()]
        step_seconds = args.step_seconds
    else:
        steps = [args.vus or 8]
        step_seconds = args.duration
    if not args.json:
        print(f"[loadtest] base={args.base_url} steps={steps} step_seconds={step_seconds} "
              f"psutil={'on' if psutil and args.server_pid else 'off'}")
    engine = LoadEngine(args.base_url, origin, args.timeout, args.server_pid)
    windows = await engine.run_ramp(steps, step_seconds)
    print_report(windows, engine.recorder, args.json)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    asyncio.run(_amain(args))


if __name__ == "__main__":
    main()
