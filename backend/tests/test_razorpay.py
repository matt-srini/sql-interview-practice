import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from routers import razorpay as razorpay_router
from tests.conftest import verify_test_user


app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


KEY_SECRET = "test_secret_abc"
WEBHOOK_SECRET = "whsec_test_rzp"


def _register_user(client: TestClient, email: str = "rzp@example.com") -> dict:
    client.get("/api/catalog")
    response = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Razorpay User", "password": "Password123"},
    )
    assert response.status_code == 201
    user = response.json()["user"]
    verify_test_user(user["id"])
    return user


def _configure_razorpay(monkeypatch, *, configure_plans: bool = True):
    """Stub the razorpay SDK and all config values.

    Returns a `calls` dict that records every order/subscription/customer create.
    """
    calls = {"orders": [], "subscriptions": [], "customers": []}

    class _Order:
        @staticmethod
        def create(params):
            calls["orders"].append(params)
            return {"id": "order_test_rzp"}

    class _Subscription:
        @staticmethod
        def create(params):
            calls["subscriptions"].append(params)
            return {"id": "sub_test_rzp"}

    class _Customer:
        @staticmethod
        def create(params):
            calls["customers"].append(params)
            return {"id": "cust_test_rzp"}

    class _Client:
        def __init__(self, auth=None):  # noqa: D401
            self.order = _Order
            self.subscription = _Subscription
            self.customer = _Customer

    rzp_stub = SimpleNamespace(Client=_Client)

    monkeypatch.setattr(razorpay_router, "razorpay", rzp_stub)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_ID", "rzp_test_key")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(
        razorpay_router,
        "RAZORPAY_PLAN_PRO",
        "plan_pro_test" if configure_plans else None,
    )
    monkeypatch.setattr(
        razorpay_router,
        "RAZORPAY_PLAN_ELITE",
        "plan_elite_test" if configure_plans else None,
    )
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_PRO", 799900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_ELITE", 1499900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_CURRENCY", "INR")
    return calls


def _sign_webhook(raw: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def _sign_order_payment(order_id: str, payment_id: str) -> str:
    body = f"{order_id}|{payment_id}".encode()
    return hmac.new(KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()


def _sign_subscription_payment(payment_id: str, subscription_id: str) -> str:
    body = f"{payment_id}|{subscription_id}".encode()
    return hmac.new(KEY_SECRET.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# create-order
# ---------------------------------------------------------------------------


def test_create_order_for_pro_returns_subscription_id(monkeypatch) -> None:
    calls = _configure_razorpay(monkeypatch)

    with TestClient(app) as client:
        user = _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["subscription_id"] == "sub_test_rzp"
        assert body["order_id"] is None
        assert body["is_subscription"] is True
        assert body["key_id"] == "rzp_test_key"
        assert calls["subscriptions"][0]["plan_id"] == "plan_pro_test"
        assert calls["subscriptions"][0]["notes"]["user_id"] == user["id"]
        assert calls["subscriptions"][0]["notes"]["target_plan"] == "pro"


def test_create_order_for_elite_returns_subscription_id(monkeypatch) -> None:
    calls = _configure_razorpay(monkeypatch)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "elite"})
        assert r.status_code == 200, r.text
        assert calls["subscriptions"][0]["plan_id"] == "plan_elite_test"


def test_create_order_for_lifetime_pro_returns_order_id_with_amount(monkeypatch) -> None:
    calls = _configure_razorpay(monkeypatch)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_pro"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["order_id"] == "order_test_rzp"
        assert body["subscription_id"] is None
        assert body["amount"] == 799900
        assert body["is_subscription"] is False
        assert calls["orders"][0]["amount"] == 799900
        assert calls["orders"][0]["currency"] == "INR"


def test_create_order_for_lifetime_elite_uses_correct_amount(monkeypatch) -> None:
    calls = _configure_razorpay(monkeypatch)

    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite"})
        assert r.status_code == 200
        assert calls["orders"][0]["amount"] == 1499900


def test_create_order_rejects_anonymous_users(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        client.get("/api/catalog")
        r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
        assert r.status_code == 403


def test_create_order_rejects_unknown_plan(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "enterprise"})
        assert r.status_code == 400


@pytest.mark.parametrize(
    "current_plan,target_plan",
    [
        ("elite", "pro"),
        ("lifetime_elite", "pro"),
        ("lifetime_elite", "lifetime_pro"),
        ("pro", "pro"),
        ("lifetime_elite", "lifetime_elite"),
    ],
)
def test_create_order_rejects_invalid_upgrade_path(monkeypatch, current_plan, target_plan) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        user = _register_user(client, email=f"inv-{current_plan}-{target_plan}@ex.com")
        client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": current_plan, "context": "test-setup"},
        )
        r = client.post("/api/razorpay/create-order", json={"plan": target_plan})
        assert r.status_code == 400, r.json()


def test_create_order_returns_503_when_plan_not_configured(monkeypatch) -> None:
    _configure_razorpay(monkeypatch, configure_plans=False)
    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
        assert r.status_code == 503


def test_create_order_returns_503_when_sdk_not_installed(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    monkeypatch.setattr(razorpay_router, "razorpay", None)
    with TestClient(app) as client:
        _register_user(client)
        r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
        assert r.status_code == 503


def test_create_order_creates_customer_once_per_user(monkeypatch) -> None:
    calls = _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        _register_user(client)
        client.post("/api/razorpay/create-order", json={"plan": "pro"})
        client.post("/api/razorpay/create-order", json={"plan": "elite"})
        assert len(calls["customers"]) == 1


# ---------------------------------------------------------------------------
# verify-payment (fast-path)
# ---------------------------------------------------------------------------


def test_verify_payment_with_valid_signature_applies_plan(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        user = _register_user(client)
        sig = _sign_order_payment("order_test_rzp", "pay_test_1")
        r = client.post(
            "/api/razorpay/verify-payment",
            json={
                "plan": "lifetime_pro",
                "razorpay_payment_id": "pay_test_1",
                "razorpay_order_id": "order_test_rzp",
                "razorpay_signature": sig,
            },
        )
        assert r.status_code == 200, r.json()
        assert r.json()["plan"] == "lifetime_pro"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro"


def test_verify_payment_with_invalid_signature_is_rejected(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        _register_user(client)
        r = client.post(
            "/api/razorpay/verify-payment",
            json={
                "plan": "lifetime_pro",
                "razorpay_payment_id": "pay_test_2",
                "razorpay_order_id": "order_test_rzp",
                "razorpay_signature": "deadbeef",
            },
        )
        assert r.status_code == 400


def test_verify_payment_is_idempotent(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        user = _register_user(client)
        sig = _sign_order_payment("order_rep", "pay_rep_1")
        payload = {
            "plan": "lifetime_pro",
            "razorpay_payment_id": "pay_rep_1",
            "razorpay_order_id": "order_rep",
            "razorpay_signature": sig,
        }
        first = client.post("/api/razorpay/verify-payment", json=payload)
        assert first.status_code == 200
        second = client.post("/api/razorpay/verify-payment", json=payload)
        assert second.status_code == 200
        assert second.json()["plan"] == "lifetime_pro"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro"


def test_verify_payment_subscription_flow_uses_payment_pipe_sub_signature(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        user = _register_user(client)
        sig = _sign_subscription_payment("pay_s_1", "sub_s_1")
        r = client.post(
            "/api/razorpay/verify-payment",
            json={
                "plan": "pro",
                "razorpay_payment_id": "pay_s_1",
                "razorpay_subscription_id": "sub_s_1",
                "razorpay_signature": sig,
            },
        )
        assert r.status_code == 200, r.json()
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro"


# ---------------------------------------------------------------------------
# webhook
# ---------------------------------------------------------------------------


def test_webhook_rejects_missing_signature(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        r = client.post("/api/razorpay/webhook", content=b"{}")
        assert r.status_code == 400


def test_webhook_rejects_bad_signature(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        r = client.post(
            "/api/razorpay/webhook",
            content=b"{}",
            headers={"X-Razorpay-Signature": "bad"},
        )
        assert r.status_code == 400


def test_webhook_returns_503_when_secret_not_configured(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_WEBHOOK_SECRET", None)
    with TestClient(app) as client:
        r = client.post(
            "/api/razorpay/webhook",
            content=b"{}",
            headers={"X-Razorpay-Signature": "anything"},
        )
        assert r.status_code == 503


def _send_webhook(client, event: dict):
    raw = json.dumps(event).encode("utf-8")
    return client.post(
        "/api/razorpay/webhook",
        content=raw,
        headers={"X-Razorpay-Signature": _sign_webhook(raw)},
    )


def test_webhook_unknown_event_type_is_acknowledged_as_ignored(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        r = _send_webhook(
            client,
            {
                "id": "evt_unknown_1",
                "event": "customer.created",
                "payload": {},
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"


def test_webhook_payment_captured_upgrades_user_with_notes_user_id(monkeypatch) -> None:
    _configure_razorpay(monkeypatch)
    with TestClient(app) as client:
        user = _register_user(client)
        event = {
            "id": "evt_pay_cap_1",
            "event": "payment.captured",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_wh_1",
                        "notes": {
                            "user_id": user["id"],
                            "target_plan": "lifetime_pro",
                        },
                    }
                }
            },
        }
        r = _send_webhook(client, event)
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro"
