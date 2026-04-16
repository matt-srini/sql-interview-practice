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
            "password": "Password123",
        },
    )
    assert response.status_code == 201
    return response.json()["user"]


def _configure_stripe(monkeypatch, *, event, include_lifetime_prices: bool = True):
    """
    Stub the stripe module and all relevant config values.

    Returns a `calls` dict that records every Customer.create and
    checkout.Session.create invocation so tests can assert on the exact
    arguments passed to Stripe.

    Set include_lifetime_prices=False to simulate the env state where
    STRIPE_PRICE_LIFETIME_* are not yet configured (price ID is None).
    """
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
    monkeypatch.setattr(stripe_router, "PRICE_IDS", {
        "pro":            "price_pro_123",
        "elite":          "price_elite_123",
        "lifetime_pro":   "price_ltp_123" if include_lifetime_prices else None,
        "lifetime_elite": "price_lte_123" if include_lifetime_prices else None,
    })
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


# ---------------------------------------------------------------------------
# Checkout — billing mode (subscription vs one-time payment)
# ---------------------------------------------------------------------------

def test_checkout_uses_subscription_mode_for_pro(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200
        assert calls["sessions"][0]["mode"] == "subscription", (
            "monthly Pro must use subscription mode, not one-time payment"
        )


def test_checkout_uses_subscription_mode_for_elite(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "elite"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200
        assert calls["sessions"][0]["mode"] == "subscription", (
            "monthly Elite must use subscription mode, not one-time payment"
        )


def test_checkout_uses_payment_mode_for_lifetime_pro(monkeypatch) -> None:
    """Lifetime plans are one-time purchases — Stripe must receive mode='payment'."""
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "lifetime_pro"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200, r.json()
        assert calls["sessions"][0]["mode"] == "payment", (
            "lifetime_pro must use payment (one-time) mode, not subscription"
        )


def test_checkout_uses_payment_mode_for_lifetime_elite(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "lifetime_elite"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 200, r.json()
        assert calls["sessions"][0]["mode"] == "payment", (
            "lifetime_elite must use payment (one-time) mode, not subscription"
        )


# ---------------------------------------------------------------------------
# Checkout — Stripe customer ID reuse
# ---------------------------------------------------------------------------

def test_checkout_does_not_create_duplicate_stripe_customer(monkeypatch) -> None:
    """
    A Stripe Customer should be created exactly once per user, even across
    multiple checkout calls.  Creating duplicates leaks customer objects in
    Stripe and breaks webhook resolution by customer_id.
    """
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)

        client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                    headers={"Origin": "http://localhost:5173"})
        client.post("/api/stripe/create-checkout", json={"plan": "elite"},
                    headers={"Origin": "http://localhost:5173"})

        assert len(calls["customers"]) == 1, (
            f"Expected 1 Stripe Customer creation, got {len(calls['customers'])}"
        )


# ---------------------------------------------------------------------------
# Checkout — input validation
# ---------------------------------------------------------------------------

def test_checkout_rejects_unknown_plan_name(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "enterprise"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 400, f"unknown plan should return 400, got {r.status_code}"
        assert "error" in r.json(), "error response must contain 'error' key"


@pytest.mark.parametrize("current_plan,target_plan", [
    ("elite",          "pro"),
    ("elite",          "lifetime_pro"),
    ("lifetime_elite", "pro"),
    ("lifetime_elite", "elite"),
    ("lifetime_elite", "lifetime_pro"),
    ("pro",            "pro"),            # same-plan upgrade
    ("lifetime_pro",   "lifetime_pro"),   # same-plan upgrade
    ("lifetime_elite", "lifetime_elite"), # already at ceiling
])
def test_checkout_rejects_invalid_upgrade_path(monkeypatch, current_plan, target_plan) -> None:
    """
    Downgrade and lateral moves must be rejected at the API layer — they must
    never reach Stripe.  Accepting them would let users pay for a plan they
    already have or one that represents a service reduction.
    """
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        user = _register_user(client, email=f"invalid-{current_plan}-{target_plan}@example.com")
        # Force the user onto current_plan via the internal admin endpoint
        client.post("/api/user/plan", json={"user_id": user["id"], "new_plan": current_plan, "context": "test-setup"})

        r = client.post("/api/stripe/create-checkout", json={"plan": target_plan},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 400, (
            f"{current_plan} → {target_plan} should be rejected (400), got {r.status_code}: {r.json()}"
        )


def test_checkout_returns_503_when_lifetime_price_not_configured(monkeypatch) -> None:
    """
    If STRIPE_PRICE_LIFETIME_PRO is unset (None) the endpoint must return 503
    rather than crashing or silently passing a None price to Stripe.
    """
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event, include_lifetime_prices=False)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "lifetime_pro"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 503, (
            f"unconfigured lifetime price ID should return 503, got {r.status_code}: {r.json()}"
        )


def test_checkout_returns_503_when_stripe_secret_key_missing(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)
    monkeypatch.setattr(stripe_router, "STRIPE_SECRET_KEY", None)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 503, f"missing secret key should return 503, got {r.status_code}"


def test_checkout_returns_503_when_stripe_sdk_not_installed(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)
    monkeypatch.setattr(stripe_router, "stripe", None)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                        headers={"Origin": "http://localhost:5173"})
        assert r.status_code == 503, f"missing stripe SDK should return 503, got {r.status_code}"


# ---------------------------------------------------------------------------
# Checkout — URL construction
# ---------------------------------------------------------------------------

def test_checkout_success_and_cancel_urls_use_origin_header(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                    headers={"Origin": "http://app.example.com"})

        assert calls["sessions"][0]["success_url"] == "http://app.example.com/practice?upgraded=true", (
            "success_url must be built from the Origin header"
        )
        assert calls["sessions"][0]["cancel_url"] == "http://app.example.com/practice", (
            "cancel_url must be built from the Origin header"
        )


def test_checkout_success_url_falls_back_to_referer_header(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        _register_user(client)
        client.post(
            "/api/stripe/create-checkout",
            json={"plan": "pro"},
            headers={"Referer": "http://fallback.example.com/practice/sql/questions/1"},
        )

        assert calls["sessions"][0]["success_url"].startswith("http://fallback.example.com"), (
            "success_url must fall back to Referer host when Origin header is absent"
        )


# ---------------------------------------------------------------------------
# Checkout — metadata integrity
# ---------------------------------------------------------------------------

def test_checkout_metadata_contains_user_id_and_target_plan(monkeypatch) -> None:
    """
    Stripe metadata is the primary key used by the webhook to identify which
    user to upgrade and to which plan.  Both fields are mandatory.
    """
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        user = _register_user(client)
        client.post("/api/stripe/create-checkout", json={"plan": "lifetime_pro"},
                    headers={"Origin": "http://localhost:5173"})

        meta = calls["sessions"][0]["metadata"]
        assert meta["user_id"] == user["id"], "metadata.user_id must match the authenticated user"
        assert meta["target_plan"] == "lifetime_pro", "metadata.target_plan must match the requested plan"


def test_checkout_sets_client_reference_id_to_user_id(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    calls = _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        user = _register_user(client)
        client.post("/api/stripe/create-checkout", json={"plan": "pro"},
                    headers={"Origin": "http://localhost:5173"})

        assert calls["sessions"][0]["client_reference_id"] == user["id"], (
            "client_reference_id must equal user_id for Stripe dashboard traceability"
        )


# ---------------------------------------------------------------------------
# Webhook — structural / configuration validation
# ---------------------------------------------------------------------------

def test_webhook_returns_400_when_stripe_signature_header_missing(monkeypatch) -> None:
    """
    The Stripe-Signature header is required to verify webhook authenticity.
    A missing header must be rejected immediately — it indicates the request
    did not come from Stripe.
    """
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)

    with TestClient(app) as client:
        r = client.post("/api/stripe/webhook", content=b"{}")
        assert r.status_code == 400, (
            f"missing Stripe-Signature header must return 400, got {r.status_code}"
        )


def test_webhook_returns_503_when_webhook_secret_not_configured(monkeypatch) -> None:
    event = {"id": "evt_unused", "type": "noop", "data": {"object": {}}}
    _configure_stripe(monkeypatch, event=event)
    monkeypatch.setattr(stripe_router, "STRIPE_WEBHOOK_SECRET", None)

    with TestClient(app) as client:
        r = client.post("/api/stripe/webhook", content=b"{}",
                        headers={"Stripe-Signature": "good-signature"})
        assert r.status_code == 503, (
            f"missing webhook secret must return 503, got {r.status_code}"
        )
