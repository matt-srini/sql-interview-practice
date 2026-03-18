from rate_limiter import InMemoryRateLimiter, create_rate_limiter


def test_create_rate_limiter_falls_back_to_memory_on_bad_redis_url() -> None:
    limiter = create_rate_limiter(
        max_requests=5,
        window_seconds=60,
        redis_url="redis://127.0.0.1:6399/0",
    )
    assert isinstance(limiter, InMemoryRateLimiter)


def test_in_memory_rate_limiter_enforces_limit() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert limiter.check("client-1").allowed is True
    assert limiter.check("client-1").allowed is True
    third = limiter.check("client-1")
    assert third.allowed is False
    assert third.retry_after >= 1
