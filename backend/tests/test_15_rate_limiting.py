"""TC-224 to TC-228 — Rate Limiting."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
import routers.auth as auth_router
from conftest import _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def test_tc224_global_rate_limiter_returns_429_on_excess(monkeypatch):
    """TC-224: Global limit=3 → 4th request to a non-health API path gets 429."""
    # Lower the limit to 3 and clear existing state
    monkeypatch.setattr(main.rate_limiter, "max_requests", 3)
    main.rate_limiter.clear()

    # TestClient uses "testclient" as client IP, which bypasses the localhost
    # exemption but not the /health path skip; use /api/catalog instead.
    with TestClient(app) as client:
        responses = [client.get("/api/catalog") for _ in range(4)]

    statuses = [r.status_code for r in responses]
    assert 429 in statuses, f"Expected a 429; got {statuses}"


def test_tc225_auth_rate_limiter_returns_429_on_excess(monkeypatch):
    """TC-225: Auth rate limit=3 → 4th request to a rate-limited auth endpoint gets 429."""
    monkeypatch.setattr(auth_router._auth_rate_limiter, "max_requests", 3)
    auth_router._auth_rate_limiter.clear()

    from conftest import _unique_email
    with TestClient(app) as client:
        results = []
        for _ in range(4):
            # magic-link calls _check_auth_limits which uses _auth_rate_limiter
            r = client.post("/api/auth/magic-link", json={"email": _unique_email()})
            results.append(r.status_code)

    assert 429 in results, f"Expected a 429; got {results}"


def test_tc226_auth_token_issue_rate_limiter_returns_429(monkeypatch):
    """TC-226: Token issue limit=2 → 3rd request to a token-issuing auth endpoint → 429."""
    monkeypatch.setattr(auth_router._auth_token_issue_limiter, "max_requests", 2)
    auth_router._auth_token_issue_limiter.clear()

    from conftest import _unique_email
    with TestClient(app) as client:
        results = []
        for _ in range(3):
            # magic-link calls _check_auth_limits(issue_token=True) which uses
            # both _auth_rate_limiter and _auth_token_issue_limiter
            r = client.post("/api/auth/magic-link", json={"email": _unique_email()})
            results.append(r.status_code)

    assert 429 in results, f"Expected a 429; got {results}"


def test_tc227_localhost_exempted_from_rate_limit():
    """TC-227: 100 requests to /health from localhost → no 429."""
    with TestClient(app) as client:
        for _ in range(100):
            r = client.get("/health")
            assert r.status_code != 429, "localhost should not be rate-limited"


def test_tc228_clear_rate_limit_state_allows_new_requests(monkeypatch):
    """TC-228: After exhausting limit, clear state → next request succeeds."""
    monkeypatch.setattr(main.rate_limiter, "max_requests", 2)
    main.rate_limiter.clear()

    from conftest import _unique_email
    email = _unique_email()
    with TestClient(app) as client:
        # Exhaust limit
        for _ in range(3):
            client.get("/health")
        # Clear state
        main.rate_limiter.clear()
        # This should succeed now
        r = client.get("/health")
    assert r.status_code != 429


# --- TC-229..231 — check_safe graceful degradation on a backend (Redis) blip -------
# A transient Redis error during check() must NOT become a 500 for the user. The
# in-memory limiter never raises, so a backend that raises stands in for the prod
# Redis-blip case. See rate_limiter.BaseRateLimiter.check_safe.

def _raising_limiter(max_requests: int, window_seconds: int):
    """A real BaseRateLimiter subclass whose check() always raises (flaky-Redis stand-in).

    Subclasses the real base so we exercise the actual ``check_safe`` implementation.
    """
    from rate_limiter import BaseRateLimiter

    class _Raising(BaseRateLimiter):
        def check(self, key):
            raise RuntimeError("redis down")

        def clear(self):
            pass

    return _Raising(max_requests=max_requests, window_seconds=window_seconds)


def test_tc229_check_safe_fails_open_on_backend_error():
    """fail_open=True (coarse IP / auth-baseline limiters) → allow on backend error."""
    lim = _raising_limiter(max_requests=60, window_seconds=60)
    decision = lim.check_safe("1.2.3.4", fail_open=True)
    assert decision.allowed is True
    assert decision.retry_after == 0


def test_tc230_check_safe_fails_closed_on_backend_error():
    """fail_open=False (token-issue limiter) → deny on backend error, with Retry-After."""
    lim = _raising_limiter(max_requests=5, window_seconds=300)
    decision = lim.check_safe("1.2.3.4", fail_open=False)
    assert decision.allowed is False
    assert decision.retry_after >= 1


def test_tc231_check_safe_passes_through_normal_decisions():
    """check_safe must not alter allow/deny when the backend is healthy."""
    from rate_limiter import InMemoryRateLimiter

    lim = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert lim.check_safe("k").allowed is True
    assert lim.check_safe("k").allowed is True
    assert lim.check_safe("k").allowed is False  # 3rd request is over the limit
