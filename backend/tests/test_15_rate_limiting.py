"""TC-224 to TC-228 — Rate Limiting."""
import pytest
from starlette.testclient import TestClient

import backend.main as main
import routers.auth as auth_router
from conftest import _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def test_tc224_global_rate_limiter_returns_429_on_excess(monkeypatch):
    """TC-224: Global limit=3 → 4th request gets 429."""
    # Lower the limit to 3 and clear existing state
    monkeypatch.setattr(main.rate_limiter, "max_requests", 3)
    main.rate_limiter.clear()

    with TestClient(app) as client:
        _make_user(client, plan="free")
        responses = [client.get("/health") for _ in range(4)]

    statuses = [r.status_code for r in responses]
    assert 429 in statuses, f"Expected a 429; got {statuses}"


def test_tc225_auth_rate_limiter_returns_429_on_excess(monkeypatch):
    """TC-225: Auth rate limit=3 → 4th auth request gets 429."""
    monkeypatch.setattr(auth_router._auth_rate_limiter, "max_requests", 3)
    auth_router._auth_rate_limiter.clear()

    from conftest import _unique_email
    email = _unique_email()
    with TestClient(app) as client:
        results = []
        for _ in range(4):
            r = client.post("/api/auth/login", json={"email": email, "password": "wrong_pw"})
            results.append(r.status_code)

    assert 429 in results, f"Expected a 429; got {results}"


def test_tc226_auth_token_issue_rate_limiter_returns_429(monkeypatch):
    """TC-226: Token issue limit=2 → 3rd registration attempt from same IP → 429."""
    monkeypatch.setattr(auth_router._auth_token_issue_limiter, "max_requests", 2)
    auth_router._auth_token_issue_limiter.clear()

    from conftest import _unique_email
    with TestClient(app) as client:
        results = []
        for _ in range(3):
            r = client.post(
                "/api/auth/forgot-password",
                json={"email": _unique_email()},
            )
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
