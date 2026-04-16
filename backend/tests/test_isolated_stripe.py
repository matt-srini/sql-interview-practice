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
            "password": "Password123",
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


# ---------------------------------------------------------------------------
# Helpers for extended tests
# ---------------------------------------------------------------------------

_iso_counter = 0


def _make_user(client: TestClient, plan: str = "free", suffix: str = "") -> dict:
    """Register a user, optionally upgrade their plan. Returns the user dict."""
    global _iso_counter
    _iso_counter += 1
    email = f"iso-ext-{_iso_counter}{suffix}@internal.test"
    client.get("/api/catalog")
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Iso Test", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, f"could not set plan to {plan}: {up.text}"
        assert up.json()["success"], f"plan change to {plan} failed: {up.json()}"
        user["plan"] = plan
    return user


def _configure_webhook_full(monkeypatch, event, *, include_lifetime_prices: bool = True):
    """Webhook-only stripe stub with lifetime price IDs."""
    def construct_event(payload, signature, secret):
        if signature != "good-signature":
            raise ValueError("invalid signature")
        return event

    stripe_stub = SimpleNamespace(
        api_key=None,
        Customer=SimpleNamespace(create=lambda **kw: SimpleNamespace(id="cus_iso_full")),
        checkout=SimpleNamespace(
            Session=SimpleNamespace(create=lambda **kw: SimpleNamespace(url="https://checkout.stripe.test/iso"))
        ),
        Webhook=SimpleNamespace(construct_event=construct_event),
    )
    monkeypatch.setattr(stripe_router, "stripe", stripe_stub)
    monkeypatch.setattr(stripe_router, "STRIPE_SECRET_KEY", "sk_test_iso")
    monkeypatch.setattr(stripe_router, "STRIPE_WEBHOOK_SECRET", "whsec_iso")
    monkeypatch.setattr(stripe_router, "PRICE_IDS", {
        "pro":            "price_pro_iso",
        "elite":          "price_elite_iso",
        "lifetime_pro":   "price_ltp_iso" if include_lifetime_prices else None,
        "lifetime_elite": "price_lte_iso" if include_lifetime_prices else None,
    })


def _send_webhook(client, event_dict):
    return client.post(
        "/api/stripe/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "good-signature"},
    )


def _checkout_event(event_id, user_id, target_plan, customer="cus_iso_full"):
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer,
                "metadata": {"user_id": user_id, "target_plan": target_plan},
            }
        },
    }


def _sub_deleted_event(event_id, customer="cus_iso_full"):
    return {
        "id": event_id,
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": customer, "metadata": {}}},
    }


# ---------------------------------------------------------------------------
# Checkout completed — all plan types stored as-is
# ---------------------------------------------------------------------------

def test_checkout_completed_upgrades_to_elite(monkeypatch) -> None:
    with TestClient(app) as client:
        user = _make_user(client)
        event = _checkout_event("evt_to_elite_1", user["id"], "elite")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "elite"


def test_checkout_completed_upgrades_to_lifetime_pro(monkeypatch) -> None:
    """
    Lifetime plan values must be stored verbatim ('lifetime_pro'), not collapsed
    to their base plan ('pro').  The distinction prevents subscription-deleted
    webhooks from ever downgrading lifetime users.
    """
    with TestClient(app) as client:
        user = _make_user(client)
        event = _checkout_event("evt_to_ltp_1", user["id"], "lifetime_pro")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro", (
            "lifetime_pro must be stored as 'lifetime_pro', not normalised to 'pro'"
        )


def test_checkout_completed_upgrades_to_lifetime_elite(monkeypatch) -> None:
    with TestClient(app) as client:
        user = _make_user(client)
        event = _checkout_event("evt_to_lte_1", user["id"], "lifetime_elite")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_elite", (
            "lifetime_elite must be stored as 'lifetime_elite', not normalised to 'elite'"
        )


# ---------------------------------------------------------------------------
# Checkout completed — edge cases
# ---------------------------------------------------------------------------

def test_checkout_completed_with_unknown_user_id_does_not_crash(monkeypatch) -> None:
    """A checkout event referencing a non-existent user must be handled gracefully."""
    event = _checkout_event(
        "evt_unknown_user_1",
        "00000000-0000-0000-0000-000000000000",
        "pro",
        customer="cus_nobody_123",
    )
    _configure_webhook_full(monkeypatch, event)
    with TestClient(app) as client:
        r = _send_webhook(client, event)
        assert r.status_code == 200, (
            f"unknown user_id must not cause 5xx, got {r.status_code}: {r.json()}"
        )


def test_checkout_completed_with_invalid_target_plan_does_not_change_plan(monkeypatch) -> None:
    """
    An event with target_plan='hacked_plan' must be rejected silently — the user's
    plan must remain unchanged.  This guards against crafted webhook payloads.
    """
    with TestClient(app) as client:
        user = _make_user(client)
        event = _checkout_event("evt_bad_plan_1", user["id"], "hacked_plan")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "free", (
            "invalid target_plan in webhook must not change the user's plan"
        )


def test_checkout_completed_resolves_user_by_customer_id_when_metadata_missing(monkeypatch) -> None:
    """
    When metadata.user_id is absent, the webhook handler falls back to the
    customer ID to look up the user.  This covers replays and edge cases where
    metadata propagation fails.
    """
    with TestClient(app) as client:
        user = _make_user(client)

        # Seed a stripe_customer_id for this user by going through checkout
        seed_event = {"id": "evt_noop_seed", "type": "noop", "data": {"object": {}}}
        _configure_webhook_full(monkeypatch, seed_event)
        client.post(
            "/api/stripe/create-checkout",
            json={"plan": "pro"},
            headers={"Origin": "http://localhost:5173"},
        )

        # Webhook with no metadata.user_id but with the correct customer ID
        event = {
            "id": "evt_by_customer_1",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_iso_full",  # matches what the stripe stub returns
                    "metadata": {},              # no user_id
                }
            },
        }
        event["data"]["object"]["metadata"]["target_plan"] = "pro"
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro", (
            "user must be resolved by customer ID when metadata.user_id is absent"
        )


# ---------------------------------------------------------------------------
# Subscription deleted — downgrade + lifetime protection (CRITICAL)
# ---------------------------------------------------------------------------

def test_subscription_deleted_downgrades_monthly_elite_to_free(monkeypatch) -> None:
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
        # Seed customer ID so the webhook can resolve the user
        seed_event = {"id": "evt_noop_seed2", "type": "noop", "data": {"object": {}}}
        _configure_webhook_full(monkeypatch, seed_event)
        client.post("/api/stripe/create-checkout", json={"plan": "lifetime_elite"},
                    headers={"Origin": "http://localhost:5173"})

        event = _sub_deleted_event("evt_del_elite_1", customer="cus_iso_full")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "free", "monthly elite must be downgraded to free on subscription deletion"


def test_subscription_deleted_does_NOT_downgrade_lifetime_pro(monkeypatch) -> None:
    """
    CRITICAL: A lifetime_pro user who previously had a monthly subscription must
    not be downgraded to free if a stale subscription.deleted event arrives.
    Lifetime purchases are permanent — they have no subscription to delete.
    """
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_pro")
        # Seed customer ID
        seed_event = {"id": "evt_noop_seed3", "type": "noop", "data": {"object": {}}}
        _configure_webhook_full(monkeypatch, seed_event)
        client.post("/api/stripe/create-checkout", json={"plan": "elite"},
                    headers={"Origin": "http://localhost:5173"})

        event = _sub_deleted_event("evt_del_ltp_1", customer="cus_iso_full")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro", (
            "subscription.deleted must NEVER downgrade a lifetime_pro user — "
            f"got plan={profile.json()['plan']!r}"
        )


def test_subscription_deleted_does_NOT_downgrade_lifetime_elite(monkeypatch) -> None:
    """CRITICAL: Same protection as above, for lifetime_elite."""
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_elite")
        seed_event = {"id": "evt_noop_seed4", "type": "noop", "data": {"object": {}}}
        _configure_webhook_full(monkeypatch, seed_event)
        # Lifetime elite can't upgrade further via checkout, but we still need to seed
        # the customer_id so the webhook handler can resolve the user.
        # Use a no-op checkout (will fail but side-effects the customer creation).
        client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                    headers={"Origin": "http://localhost:5173"})

        event = _sub_deleted_event("evt_del_lte_1", customer="cus_iso_full")
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_elite", (
            "subscription.deleted must NEVER downgrade a lifetime_elite user — "
            f"got plan={profile.json()['plan']!r}"
        )


def test_subscription_deleted_with_unknown_customer_does_not_crash(monkeypatch) -> None:
    event = _sub_deleted_event("evt_del_unknown_1", customer="cus_totally_unknown_xyz")
    _configure_webhook_full(monkeypatch, event)
    with TestClient(app) as client:
        r = _send_webhook(client, event)
        assert r.status_code == 200, (
            f"unknown customer in subscription.deleted must not cause 5xx, got {r.status_code}"
        )


# ---------------------------------------------------------------------------
# Invoice payment failed
# ---------------------------------------------------------------------------

def test_invoice_payment_failed_does_not_change_plan_and_is_ignored(monkeypatch) -> None:
    """
    A failed payment must not downgrade the user immediately — only a
    subscription.deleted event should do that (after Stripe's retry window).
    The response status must be 'ignored', not 'processed'.
    """
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        seed_event = {"id": "evt_noop_seed5", "type": "noop", "data": {"object": {}}}
        _configure_webhook_full(monkeypatch, seed_event)
        client.post("/api/stripe/create-checkout", json={"plan": "elite"},
                    headers={"Origin": "http://localhost:5173"})

        event = {
            "id": "evt_payment_failed_1",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_iso_full", "metadata": {}}},
        }
        _configure_webhook_full(monkeypatch, event)
        r = _send_webhook(client, event)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored", (
            f"invoice.payment_failed must return 'ignored', got {r.json()['status']!r}"
        )
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro", (
            "invoice.payment_failed must not change the user's plan"
        )
