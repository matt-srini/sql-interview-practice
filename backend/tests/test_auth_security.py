import pytest
from fastapi.testclient import TestClient

import backend.main as main
from routers import auth as auth_router


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _register_user(client: TestClient, email: str, password: str = "StrongPass1") -> None:
    client.get("/catalog")
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Auth Tester",
            "password": password,
        },
    )
    assert response.status_code == 201


def test_login_lockout_after_repeated_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_router, "LOGIN_LOCKOUT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(auth_router, "LOGIN_LOCKOUT_WINDOW_MINUTES", 15)

    with TestClient(app) as client:
        _register_user(client, "lockout@example.com")
        client.post("/api/auth/logout")

        for _ in range(2):
            bad = client.post(
                "/api/auth/login",
                json={"email": "lockout@example.com", "password": "WrongPass1"},
            )
            assert bad.status_code == 401

        threshold_attempt = client.post(
            "/api/auth/login",
            json={"email": "lockout@example.com", "password": "WrongPass1"},
        )
        assert threshold_attempt.status_code == 429

        locked = client.post(
            "/api/auth/login",
            json={"email": "lockout@example.com", "password": "WrongPass1"},
        )
        assert locked.status_code == 429

        still_locked = client.post(
            "/api/auth/login",
            json={"email": "lockout@example.com", "password": "StrongPass1"},
        )
        assert still_locked.status_code == 429


def test_login_failures_reset_after_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_router, "LOGIN_LOCKOUT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(auth_router, "LOGIN_LOCKOUT_WINDOW_MINUTES", 15)

    with TestClient(app) as client:
        _register_user(client, "lockout-reset@example.com")
        client.post("/api/auth/logout")

        for _ in range(2):
            bad = client.post(
                "/api/auth/login",
                json={"email": "lockout-reset@example.com", "password": "WrongPass1"},
            )
            assert bad.status_code == 401

        good = client.post(
            "/api/auth/login",
            json={"email": "lockout-reset@example.com", "password": "StrongPass1"},
        )
        assert good.status_code == 200

        bad_again = client.post(
            "/api/auth/login",
            json={"email": "lockout-reset@example.com", "password": "WrongPass1"},
        )
        assert bad_again.status_code == 401


def test_csrf_origin_enforced_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "IS_PROD", True)
    monkeypatch.setattr(main, "_CSRF_ALLOWED_ORIGINS", {"http://testserver"})

    with TestClient(app) as client:
        # Create a session cookie first.
        catalog = client.get("/catalog")
        assert catalog.status_code == 200

        blocked = client.post("/api/auth/logout")
        assert blocked.status_code == 403

        allowed = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
        assert allowed.status_code == 200


def test_reserved_email_prefix_rejected_on_registration() -> None:
    with TestClient(app) as client:
        client.get("/catalog")
        response = client.post(
            "/api/auth/register",
            json={
                "email": "admin@example.com",
                "name": "Reserved",
                "password": "StrongPass1",
            },
        )
        assert response.status_code == 422
