"""Rate-limiter burst probe — actually exercises the per-IP limiter over HTTP.

The realistic load driver (``driver.py``) can't see the rate limiter at all: it
runs against ``127.0.0.1`` and **localhost is exempt in dev** (``IS_PROD`` false +
``client_ip in {127.0.0.1, ::1, localhost}`` in ``main.ip_rate_limit_middleware``),
so a local ramp measures the app's concurrency ceiling, not the 60-req/min/IP guard.

This probe sidesteps the exemption by **source-binding** its client socket to a
loopback *alias* (default ``127.0.0.2``) via ``httpx``'s ``local_address``. The
server then sees ``request.client.host == "127.0.0.2"`` — a non-exempt peer — so the
limiter engages even in dev, no prod deploy required. It fires a burst larger than
the limit at a cheap path and reports how the limiter degrades:

  * how many requests passed vs. got ``429``,
  * the observed effective limit (from ``X-RateLimit-Limit`` / the pass count),
  * whether throttled responses carry a sane ``Retry-After`` + ``X-RateLimit-*``,
  * the error shape (``{error, request_id}``) on a throttled response.

Target path defaults to a **non-existent** ``/api/...`` route: the rate-limit
middleware runs *before* routing, so the request is limited without creating an
anonymous user or touching Postgres (unlike ``/api/catalog``). Under the limit it
404s; over the limit it 429s — exactly the signal we want, zero side effects.

    # 1. Start a dev server bound so the alias can reach it (single worker, like prod):
    cd backend && ENV=development DATABASE_URL=postgresql://postgres:postgres@localhost:5432/sql_practice \
        ../.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1

    # 2. (macOS only) add the loopback alias once — Linux already routes all of 127/8:
    sudo ifconfig lo0 alias 127.0.0.2 up

    # 3. Fire the burst:
    cd backend && ../.venv/bin/python -m loadtest.ratelimit --burst 80

    # Against a real prod-mode deploy (no alias needed — non-loopback client):
    ../.venv/bin/python -m loadtest.ratelimit --base-url https://… --source-ip "" --burst 120

If you see 0 throttles from a loopback source in dev, that's the exemption doing its
job — the probe prints how to actually engage the limiter.
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import httpx


async def _fire_one(client: httpx.AsyncClient, path: str) -> tuple[int, dict[str, str], dict | None]:
    try:
        resp = await client.get(path)
    except Exception as exc:  # transport error (e.g. source-bind failed)
        return -1, {"_transport_error": type(exc).__name__ + ": " + str(exc)}, None
    body: dict | None = None
    if resp.status_code == 429:
        try:
            body = resp.json()
        except Exception:
            body = None
    interesting = {k: v for k, v in resp.headers.items() if k.lower().startswith(("retry-after", "x-ratelimit", "x-request-id"))}
    return resp.status_code, interesting, body


async def _amain(args: argparse.Namespace) -> int:
    origin = args.base_url.rstrip("/")
    transport = None
    if args.source_ip:
        # Bind the client's SOURCE address to the loopback alias so the server's
        # request.client.host is non-loopback (and thus not dev-exempt).
        transport = httpx.AsyncHTTPTransport(local_address=args.source_ip)

    client_kwargs = dict(base_url=args.base_url, timeout=10.0, headers={"Origin": origin}, follow_redirects=False)
    if transport is not None:
        client_kwargs["transport"] = transport

    print(
        f"[ratelimit] base={args.base_url} source_ip={args.source_ip or '(default/loopback)'} "
        f"path={args.path} burst={args.burst}"
    )

    async with httpx.AsyncClient(**client_kwargs) as client:
        results = await asyncio.gather(*[_fire_one(client, args.path) for _ in range(args.burst)])

    transport_errors = [r for r in results if r[0] == -1]
    if transport_errors and len(transport_errors) == len(results):
        msg = transport_errors[0][1].get("_transport_error", "unknown")
        print(f"\n  ✗ every request failed at the transport layer: {msg}")
        if args.source_ip:
            print(
                "    The source-bind to "
                f"{args.source_ip} likely isn't routable. On macOS add the alias first:\n"
                f"      sudo ifconfig lo0 alias {args.source_ip} up\n"
                "    (Linux routes all of 127.0.0.0/8 by default.) Or target a prod deploy with --source-ip ''."
            )
        return 1

    statuses = [r[0] for r in results if r[0] != -1]
    throttled = [r for r in results if r[0] == 429]
    passed = [s for s in statuses if s != 429]
    n_pass, n_throttle = len(passed), len(throttled)

    print(f"\n  fired {len(statuses)} requests → {n_pass} passed the limiter, {n_throttle} throttled (429)")
    # Status histogram (passed requests may be 404 on the probe path — that's fine).
    hist: dict[int, int] = {}
    for s in statuses:
        hist[s] = hist.get(s, 0) + 1
    print("  status histogram: " + ", ".join(f"{code}×{cnt}" for code, cnt in sorted(hist.items())))

    if throttled:
        sample = throttled[0]
        limit = sample[1].get("x-ratelimit-limit", "?")
        retry = sample[1].get("retry-after", "?")
        window = sample[1].get("x-ratelimit-window", "?")
        print(
            f"\n  ✓ limiter ENGAGED and degraded gracefully:\n"
            f"      X-RateLimit-Limit={limit}  X-RateLimit-Window={window}s  Retry-After={retry}s\n"
            f"      throttled body: {sample[2]!r}"
        )
        # Sanity: the first ~limit requests should pass, the rest throttle.
        if limit not in ("?", None):
            print(f"      observed pass count {n_pass} vs advertised limit {limit} (burst {args.burst})")
        return 0

    # No throttles — explain why (this is itself the documented finding).
    print("\n  ⚠ no 429s — the limiter did not engage for this burst. Likely causes:")
    src = args.source_ip or "(default — your client's loopback source 127.0.0.1)"
    print(
        f"      • Dev localhost exemption: source IP {src} is in the exempt set and ENV != production.\n"
        f"        Re-run with a non-exempt source, e.g. --source-ip 127.0.0.2 (after the lo0 alias on macOS),\n"
        f"        or against a prod-mode deploy.\n"
        f"      • Burst ({args.burst}) below the limit, or window already rolled. Try a larger --burst."
    )
    return 0


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="rate-limiter burst probe (non-loopback source)")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument(
        "--source-ip",
        default="127.0.0.2",
        help="bind client source to this address so the server sees a non-exempt peer "
        "(default 127.0.0.2; pass '' to use the OS default source, e.g. for a remote prod deploy)",
    )
    p.add_argument(
        "--path",
        default="/api/__ratelimit_probe__",
        help="target path — defaults to a non-existent /api route so the limiter runs "
        "(middleware precedes routing) with no DB side effects",
    )
    p.add_argument("--burst", type=int, default=80, help="number of concurrent requests to fire (default 80 > 60/min limit)")
    args = p.parse_args(argv if argv is not None else sys.argv[1:])
    raise SystemExit(asyncio.run(_amain(args)))


if __name__ == "__main__":
    main()
