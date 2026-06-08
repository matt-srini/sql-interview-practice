from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Optional

try:
    import redis
except Exception:  # pragma: no cover - import availability depends on environment
    redis = None


logger = logging.getLogger(__name__)


@dataclass
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    window_seconds: int
    retry_after: int


class BaseRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, key: str) -> RateLimitDecision:
        raise NotImplementedError

    def check_safe(self, key: str, *, fail_open: bool = True) -> RateLimitDecision:
        """``check`` that never raises — graceful degradation on a backend blip.

        ``RedisRateLimiter.check`` can raise on a transient Redis connectivity error
        *after* a successful startup validation (socket timeout, connection reset).
        Letting that propagate turns a Redis hiccup into a **500 for the user's
        request** — the worst outcome: ugly *and* unprotected. Instead we degrade
        deliberately, and log it at WARNING so the blip is visible:

          * ``fail_open=True``  → allow the request. For coarse availability guards
            (the global per-IP limiter; the auth *baseline* limiter, where the
            Postgres login-lockout is the real brute-force control) a brief blip must
            not 500 every page load.
          * ``fail_open=False`` → deny with a short ``Retry-After``. For the
            token-issue limiter, which bounds *expensive side effects* (magic-link /
            verification emails, OAuth state): better to refuse new tokens for a few
            seconds than to allow an unbounded blast while Redis is flaky.

        The in-memory limiter never raises, so this only ever triggers with Redis
        configured (i.e. production — REDIS_URL is required there).
        """
        try:
            return self.check(key)
        except Exception:
            logger.warning(
                "Rate limiter backend error; failing %s for key=%s",
                "open (allow)" if fail_open else "closed (deny)",
                key,
            )
            if fail_open:
                return RateLimitDecision(
                    allowed=True,
                    limit=self.max_requests,
                    remaining=self.max_requests,
                    window_seconds=self.window_seconds,
                    retry_after=0,
                )
            return RateLimitDecision(
                allowed=False,
                limit=self.max_requests,
                remaining=0,
                window_seconds=self.window_seconds,
                retry_after=min(5, self.window_seconds),
            )

    def clear(self) -> None:
        raise NotImplementedError


class InMemoryRateLimiter(BaseRateLimiter):
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        super().__init__(max_requests=max_requests, window_seconds=window_seconds)
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str) -> RateLimitDecision:
        now = time.monotonic()
        bucket = self._buckets[key]

        while bucket and (now - bucket[0]) > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            oldest = bucket[0] if bucket else now
            retry_after = max(1, int(self.window_seconds - (now - oldest)))
            return RateLimitDecision(
                allowed=False,
                limit=self.max_requests,
                remaining=0,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
            )

        bucket.append(now)
        remaining = max(0, self.max_requests - len(bucket))
        return RateLimitDecision(
            allowed=True,
            limit=self.max_requests,
            remaining=remaining,
            window_seconds=self.window_seconds,
            retry_after=0,
        )

    def clear(self) -> None:
        self._buckets.clear()


class RedisRateLimiter(BaseRateLimiter):
    def __init__(
        self,
        redis_url: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        if redis is None:
            raise RuntimeError("redis package is not installed")
        super().__init__(max_requests=max_requests, window_seconds=window_seconds)
        self._prefix = "sql_practice:ratelimit"
        self.client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=1,
            socket_connect_timeout=1,
        )
        # Validate early so we can safely fallback to in-memory.
        self.client.ping()

    def check(self, key: str) -> RateLimitDecision:
        now_ms = int(time.time() * 1000)
        window_ms = self.window_seconds * 1000
        window_start_ms = now_ms - window_ms
        redis_key = f"{self._prefix}:{key}"

        pipeline = self.client.pipeline()
        pipeline.zremrangebyscore(redis_key, 0, window_start_ms)
        pipeline.zadd(redis_key, {str(now_ms): now_ms})
        pipeline.zcard(redis_key)
        pipeline.pexpire(redis_key, window_ms)
        _, _, count, _ = pipeline.execute()

        if count > self.max_requests:
            # Pull oldest timestamp to estimate retry-after.
            oldest = self.client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_score = int(oldest[0][1])
                retry_after = max(1, int((window_ms - (now_ms - oldest_score)) / 1000))
            else:
                retry_after = self.window_seconds
            return RateLimitDecision(
                allowed=False,
                limit=self.max_requests,
                remaining=0,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
            )

        remaining = max(0, self.max_requests - int(count))
        return RateLimitDecision(
            allowed=True,
            limit=self.max_requests,
            remaining=remaining,
            window_seconds=self.window_seconds,
            retry_after=0,
        )

    def clear(self) -> None:
        # No-op for shared Redis to avoid deleting global keys in non-test envs.
        return


def create_rate_limiter(
    max_requests: int,
    window_seconds: int,
    redis_url: Optional[str] = None,
) -> BaseRateLimiter:
    from config import IS_PROD

    if redis_url:
        try:
            limiter = RedisRateLimiter(
                redis_url=redis_url,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
            logger.info("Using Redis rate limiter")
            return limiter
        except Exception as exc:
            if IS_PROD:
                logger.error("Redis initialization failed in production")
                raise RuntimeError("Redis initialization failed in production") from exc
            logger.warning("Redis unavailable, falling back to in-memory rate limiter")
            return InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)

    if IS_PROD:
        raise RuntimeError("Redis is required in production")

    logger.info("Using in-memory rate limiter")
    return InMemoryRateLimiter(max_requests=max_requests, window_seconds=window_seconds)
