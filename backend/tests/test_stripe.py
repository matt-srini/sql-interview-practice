from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from routers import stripe as stripe_router


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _register_user(client: TestClient, email: str = "stripe@example.com") -> dict:
    client.get("/api/catalog")
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Stripe User",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def _configure_stripe(monkeypatch, *, event):
    calls = {
        "customers": [],
        "sessions": [],
        "webhooks": [],
    }

    def create_customer(**kwargs):
        calls["customers"].append(kwargs)
        return SimpleNamespace(id="cus_test_123")

    def create_session(**kwargs):
        calls["sessions"].append(kwargs)
        return SimpleNamespace(url="https://checkout.stripe.test/session_123")

    def construct_event(payload, signature, secret):
        calls["webhooks"].append(
            {
                "payload": payload,
                "signature": signature,
                "secret": secret,
            }
        )
        if signature == "bad-signature":
            raise ValueError("invalid signature")
        return event

    stripe_stub = SimpleNamespace(
        api_key=None,
        Customer=SimpleNamespace(create=create_customer),
        checkout=SimpleNamespace(Session=SimpleNamespace(create=create_session)),
        Webhook=SimpleNamespace(construct_event=construct_event),
    )

    monkeypatch.setattr(stripe_router, "stripe", stripe_stub)
    monkeypatch.setattr(stripe_router, "STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setattr(stripe_router, "STRIPE_WEBHOOK_SECRET", "whsec_test_123")
    monkeypatch.setattr(stripe_router, "PRICE_IDS", {"pro": "price_pro_123", "elite": "price_elite_123"})
    return calls


def test_stripe_create_checkout_session(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        user = _register_user(client)
        response = client.post(
            "/api/stripe/create-checkout",
            json={"plan": "pro"},
            headers={"Origin": "http://localhost:5173"},
        )

        assert response.status_code == 200
        assert response.json()["checkout_url"] == "https://checkout.stripe.test/session_123"
        assert calls["customers"][0]["metadata"]["user_id"] == user["id"]
        assert calls["sessions"][0]["customer"] == "cus_test_123"
        assert calls["sessions"][0]["line_items"] == [{"price": "price_pro_123", "quantity": 1}]
        assert calls["sessions"][0]["metadata"]["target_plan"] == "pro"
        assert calls["sessions"][0]["success_url"] == "http://localhost:5173/practice?upgraded=true"


def test_stripe_checkout_rejects_anonymous_users(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        client.get("/api/catalog")
        response = client.post("/api/stripe/create-checkout", json={"plan": "pro"})

        assert response.status_code == 403


def test_invalid_webhook_signature_returns_400(monkeypatch) -> None:
    event = {"id": "evt_invalid", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        response = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "bad-signature"},
        )

        assert response.status_code == 400


def test_unknown_webhook_type_is_acknowledged(monkeypatch) -> None:
    event = {
        "id": "evt_unknown_1",
        "type": "customer.created",
        "data": {"object": {"metadata": {"user_id": "missing"}}},
    }
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        response = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "good-signature"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
