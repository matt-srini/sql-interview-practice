from __future__ import annotations

import argparse
import asyncio
import json

from db import cleanup_stale_anonymous_users, close_pool, init_pool


async def _run(days: int) -> dict[str, int]:
    await init_pool()
    try:
        return await cleanup_stale_anonymous_users(days)
    finally:
        await close_pool()


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete stale anonymous users and expired sessions.")
    parser.add_argument("--days", type=int, default=30, help="Delete anonymous users older than this many days.")
    args = parser.parse_args()
    result = asyncio.run(_run(args.days))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
