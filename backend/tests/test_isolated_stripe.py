from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from routers import stripe as stripe_router


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _register_user(client: TestClient, email: str = "isolated@example.com") -> dict:
    client.get("/api/catalog")
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Isolated Stripe User",
            "password": "password123",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def _configure_webhook(monkeypatch, event):
    def construct_event(payload, signature, secret):
        if signature != "good-signature":
            raise ValueError("invalid signature")
        return event

    stripe_stub = SimpleNamespace(
        api_key=None,
        Customer=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(id="cus_test_456")),
        checkout=SimpleNamespace(
            Session=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(url="https://checkout.stripe.test/session_456"))
        ),
        Webhook=SimpleNamespace(construct_event=construct_event),
    )

    monkeypatch.setattr(stripe_router, "stripe", stripe_stub)
    monkeypatch.setattr(stripe_router, "STRIPE_SECRET_KEY", "sk_test_456")
    monkeypatch.setattr(stripe_router, "STRIPE_WEBHOOK_SECRET", "whsec_test_456")
    monkeypatch.setattr(stripe_router, "PRICE_IDS", {"pro": "price_pro_456", "elite": "price_elite_456"})


def test_checkout_completed_webhook_updates_plan_and_is_idempotent(monkeypatch) -> None:
    with TestClient(app) as client:
        user = _register_user(client)
        event = {
            "id": "evt_checkout_completed_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "user_id": user["id"],
                        "target_plan": "pro",
                    }
                }
            },
        }
        _configure_webhook(monkeypatch, event)

        first = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "good-signature"},
        )
        assert first.status_code == 200
        assert first.json()["status"] == "processed"

        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.status_code == 200
        assert profile.json()["plan"] == "pro"

        second = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "good-signature"},
        )
        assert second.status_code == 200
        assert second.json()["status"] == "already processed"


def test_subscription_deleted_webhook_downgrades_user(monkeypatch) -> None:
    with TestClient(app) as client:
        user = _register_user(client, email="downgrade@example.com")
        upgrade = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": "pro", "context": "test-setup"},
        )
        assert upgrade.status_code == 200

        checkout_event = {
            "id": "evt_checkout_seed_customer",
            "type": "noop",
            "data": {"object": {}},
        }
        _configure_webhook(monkeypatch, checkout_event)
        checkout = client.post(
            "/api/stripe/create-checkout",
            json={"plan": "elite"},
            headers={"Origin": "http://localhost:5173"},
        )
        assert checkout.status_code == 200

        deleted_event = {
            "id": "evt_subscription_deleted_1",
            "type": "customer.subscription.deleted",
            "data": {
                "object": {
                    "customer": "cus_test_456",
                    "metadata": {},
                }
            },
        }
        _configure_webhook(monkeypatch, deleted_event)

        response = client.post(
            "/api/stripe/webhook",
            content=b"{}",
            headers={"Stripe-Signature": "good-signature"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "processed"

        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.status_code == 200
        assert profile.json()["plan"] == "free"
