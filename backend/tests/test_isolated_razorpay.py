"""Isolated webhook & state-transition tests for the Razorpay integration.

These focus on webhook event handling end-to-end — signature verification,
plan-change application, idempotency, and the lifetime-protection invariant.
"""
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


KEY_SECRET = "iso_key_secret"
WEBHOOK_SECRET = "iso_whsec"


def _configure(monkeypatch):
    class _Order:
        @staticmethod
        def create(p):
            return {"id": "order_iso"}

    class _Subscription:
        @staticmethod
        def create(p):
            return {"id": "sub_iso"}

    class _Customer:
        @staticmethod
        def create(p):
            return {"id": "cust_iso"}

    class _Client:
        def __init__(self, auth=None):
            self.order = _Order
            self.subscription = _Subscription
            self.customer = _Customer

    monkeypatch.setattr(razorpay_router, "razorpay", SimpleNamespace(Client=_Client))
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_ID", "rzp_test_iso")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_PRO", "plan_pro_iso")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_ELITE", "plan_elite_iso")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_PRO", 799900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_ELITE", 1499900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_CURRENCY", "INR")


def _sign(raw: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def _send(client: TestClient, event: dict):
    raw = json.dumps(event).encode("utf-8")
    return client.post(
        "/api/razorpay/webhook",
        content=raw,
        headers={"X-Razorpay-Signature": _sign(raw)},
    )


_iso_counter = 0


def _make_user(client: TestClient, plan: str = "free") -> dict:
    global _iso_counter
    _iso_counter += 1
    email = f"rzp-iso-{_iso_counter}@example.test"
    client.get("/api/catalog")
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Iso", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    verify_test_user(user["id"])
    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200
        user["plan"] = plan
    return user


def _payment_event(event_id: str, user_id: str, target_plan: str) -> dict:
    return {
        "id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": f"pay_{event_id}",
                    "notes": {"user_id": user_id, "target_plan": target_plan},
                }
            }
        },
    }


def _subscription_event(event_id: str, event_type: str, user_id: str, target_plan: str) -> dict:
    return {
        "id": event_id,
        "event": event_type,
        "payload": {
            "subscription": {
                "entity": {
                    "id": f"sub_{event_id}",
                    "notes": {"user_id": user_id, "target_plan": target_plan},
                }
            },
            "payment": {
                "entity": {"id": f"pay_{event_id}"}
            },
        },
    }


def _subscription_cancel_event(event_id: str, user_id: str, event_type: str = "subscription.cancelled") -> dict:
    return {
        "id": event_id,
        "event": event_type,
        "payload": {
            "subscription": {
                "entity": {
                    "id": f"sub_{event_id}",
                    "notes": {"user_id": user_id},
                }
            }
        },
    }


# ---------------------------------------------------------------------------
# payment.captured — lifetime plans stored verbatim
# ---------------------------------------------------------------------------


def test_payment_captured_upgrades_to_lifetime_pro(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client)
        r = _send(client, _payment_event("evt_ltp_1", user["id"], "lifetime_pro"))
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro"


def test_payment_captured_upgrades_to_lifetime_elite(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client)
        r = _send(client, _payment_event("evt_lte_1", user["id"], "lifetime_elite"))
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_elite"


def test_payment_captured_is_idempotent(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client)
        event = _payment_event("evt_dup_1", user["id"], "lifetime_pro")
        first = _send(client, event)
        assert first.json()["status"] == "processed"
        second = _send(client, event)
        assert second.status_code == 200
        assert second.json()["status"] == "already processed"


# ---------------------------------------------------------------------------
# subscription.activated / .charged — recurring plans
# ---------------------------------------------------------------------------


def test_subscription_activated_upgrades_to_pro(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client)
        r = _send(
            client,
            _subscription_event("evt_sub_act_1", "subscription.activated", user["id"], "pro"),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro"


def test_subscription_charged_keeps_user_on_plan(monkeypatch) -> None:
    """subscription.charged fires each monthly renewal; plan should remain stable."""
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        r = _send(
            client,
            _subscription_event("evt_sub_chg_1", "subscription.charged", user["id"], "pro"),
        )
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro"


# ---------------------------------------------------------------------------
# subscription.cancelled / halted — downgrade + lifetime protection
# ---------------------------------------------------------------------------


def test_subscription_cancelled_downgrades_monthly_elite_to_free(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="elite")
        r = _send(client, _subscription_cancel_event("evt_cancel_1", user["id"]))
        assert r.status_code == 200
        assert r.json()["status"] == "processed"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "free"


def test_subscription_halted_downgrades_monthly_pro_to_free(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        r = _send(
            client,
            _subscription_cancel_event("evt_halt_1", user["id"], event_type="subscription.halted"),
        )
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "free"


def test_subscription_cancelled_does_NOT_downgrade_lifetime_pro(monkeypatch) -> None:
    """CRITICAL: stray subscription.cancelled must not revoke a lifetime purchase."""
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_pro")
        r = _send(client, _subscription_cancel_event("evt_stale_ltp", user["id"]))
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_pro"


def test_subscription_cancelled_does_NOT_downgrade_lifetime_elite(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_elite")
        r = _send(client, _subscription_cancel_event("evt_stale_lte", user["id"]))
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "lifetime_elite"


def test_subscription_cancelled_with_unknown_user_does_not_crash(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        r = _send(
            client,
            _subscription_cancel_event(
                "evt_cancel_unknown", "00000000-0000-0000-0000-000000000000"
            ),
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# payment.failed — logged but not acted on
# ---------------------------------------------------------------------------


def test_payment_failed_does_not_change_plan_and_is_ignored(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        event = {
            "id": "evt_pay_fail_1",
            "event": "payment.failed",
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_fail_1",
                        "notes": {"user_id": user["id"]},
                    }
                }
            },
        }
        r = _send(client, event)
        assert r.status_code == 200
        assert r.json()["status"] == "ignored"
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "pro"


# ---------------------------------------------------------------------------
# invalid target_plan hardening
# ---------------------------------------------------------------------------


def test_webhook_with_crafted_invalid_target_plan_is_silently_ignored(monkeypatch) -> None:
    _configure(monkeypatch)
    with TestClient(app) as client:
        user = _make_user(client)
        event = _payment_event("evt_bad_target_1", user["id"], "hacked_plan")
        r = _send(client, event)
        assert r.status_code == 200
        profile = client.get("/api/user/profile", params={"user_id": user["id"]})
        assert profile.json()["plan"] == "free"
