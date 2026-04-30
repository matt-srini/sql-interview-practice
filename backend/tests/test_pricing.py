"""Comprehensive pricing integration tests.

Covers:
- Anonymous user cannot call create-order or verify-payment; error shape is correct
- Free user can create orders for all paid plan variants
- Pro user can upgrade to Elite; cannot "downgrade" or re-buy same plan
- Elite user upgrade attempts handled gracefully
- lifetime_pro / lifetime_elite: normalize_plan resolves in all access-check paths
- Webhook with lifetime plan values upgrades correctly and is idempotent on replay
- HMAC verification: tampered signature returns 400 with {error, request_id}
- Webhook replay: processing same event ID twice results in exactly one plan change
- /api/user/plan admin endpoint: valid and invalid transitions
"""

from __future__ import annotations

import hashlib
import hmac
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from routers import razorpay as razorpay_router
from tests.conftest import verify_test_user
from unlock import normalize_plan

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KEY_SECRET = "test_key_secret_pricing"
WEBHOOK_SECRET = "test_webhook_secret_pricing"

_counter = 0


def _configure(monkeypatch) -> None:
    """Patch Razorpay SDK and config values so no live calls are made."""

    class _Order:
        @staticmethod
        def create(p):
            return {"id": "order_test_pricing"}

    class _Subscription:
        @staticmethod
        def create(p):
            return {"id": "sub_test_pricing"}

    class _Customer:
        @staticmethod
        def create(p):
            return {"id": "cust_test_pricing"}

    class _Client:
        def __init__(self, auth=None):
            self.order = _Order
            self.subscription = _Subscription
            self.customer = _Customer

    monkeypatch.setattr(razorpay_router, "razorpay", SimpleNamespace(Client=_Client))
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_ID", "rzp_test_pricing")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_PRO", "plan_pro_test")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_ELITE", "plan_elite_test")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_PRO_USD", "plan_pro_usd_test")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_PLAN_ELITE_USD", "plan_elite_usd_test")
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_PRO", 1199900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_ELITE", 1999900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_PRO_USD", 12900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_AMOUNT_LIFETIME_ELITE_USD", 22900)
    monkeypatch.setattr(razorpay_router, "RAZORPAY_CURRENCY", "INR")


def _make_user(client: TestClient, plan: str = "free") -> dict:
    """Register, verify email, and optionally set plan. Returns user dict."""
    global _counter
    _counter += 1
    email = f"pricing-{_counter}@example.test"
    client.get("/api/catalog")  # warm up anonymous session
    r = client.post(
        "/api/auth/register",
        json={"email": email, "name": "Pricing Test", "password": "Password123"},
    )
    assert r.status_code == 201, r.text
    user = r.json()["user"]
    verify_test_user(user["id"])
    if plan != "free":
        up = client.post(
            "/api/user/plan",
            json={"user_id": user["id"], "new_plan": plan, "context": "test-setup"},
        )
        assert up.status_code == 200, up.text
        user["plan"] = plan
    return user


def _sign_webhook(raw: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()


def _send_webhook(client: TestClient, event: dict) -> object:
    raw = json.dumps(event).encode()
    return client.post(
        "/api/razorpay/webhook",
        content=raw,
        headers={"X-Razorpay-Signature": _sign_webhook(raw)},
    )


def _payment_captured_event(event_id: str, user_id: str, target_plan: str) -> dict:
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


def _verify_sig(payment_id: str, order_id: str) -> str:
    body = f"{order_id}|{payment_id}"
    return hmac.new(KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


def _verify_sub_sig(payment_id: str, subscription_id: str) -> str:
    body = f"{payment_id}|{subscription_id}"
    return hmac.new(KEY_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Error shape helper
# ---------------------------------------------------------------------------

def _assert_error_shape(resp) -> None:
    """All error responses must contain {error, request_id}."""
    data = resp.json()
    assert "error" in data, f"Missing 'error' key in: {data}"
    assert "request_id" in data, f"Missing 'request_id' key in: {data}"


# ---------------------------------------------------------------------------
# Anonymous user tests
# ---------------------------------------------------------------------------


class TestAnonymousUser:
    def test_create_order_requires_auth(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            client.cookies.clear()
            r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
            assert r.status_code in {401, 403}
            _assert_error_shape(r)

    def test_verify_payment_requires_auth(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            client.cookies.clear()
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "pro",
                "razorpay_payment_id": "pay_anon",
                "razorpay_signature": "bad",
                "razorpay_order_id": "order_anon",
            })
            # Either 401/403 (auth check) or 400 (HMAC check fires before auth in this flow)
            assert r.status_code in {400, 401, 403}
            _assert_error_shape(r)

    def test_anonymous_error_has_request_id(self, monkeypatch) -> None:
        """Verify both endpoints return the correct error shape for anonymous calls."""
        _configure(monkeypatch)
        with TestClient(app) as client:
            client.cookies.clear()
            for endpoint, body in [
                ("/api/razorpay/create-order", {"plan": "pro"}),
                ("/api/razorpay/verify-payment", {
                    "plan": "pro",
                    "razorpay_payment_id": "pay_x",
                    "razorpay_signature": "sig_x",
                    "razorpay_order_id": "order_x",
                }),
            ]:
                r = client.post(endpoint, json=body)
                assert r.status_code in {400, 401, 403}
                data = r.json()
                assert "error" in data
                assert "request_id" in data


# ---------------------------------------------------------------------------
# Free user: create-order
# ---------------------------------------------------------------------------


class TestFreeUserCreateOrder:
    def test_create_order_pro_monthly_inr(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "pro", "currency": "INR"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["subscription_id"] == "sub_test_pricing"
            assert data["is_subscription"] is True
            assert data["order_id"] is None
            assert data["currency"] == "INR"
            assert data["key_id"] == "rzp_test_pricing"

    def test_create_order_elite_monthly_inr(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "elite", "currency": "INR"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["subscription_id"] == "sub_test_pricing"
            assert data["is_subscription"] is True

    def test_create_order_lifetime_pro_inr(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_pro", "currency": "INR"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["order_id"] == "order_test_pricing"
            assert data["is_subscription"] is False
            assert data["subscription_id"] is None
            assert data["amount"] == 1199900
            assert data["currency"] == "INR"

    def test_create_order_lifetime_elite_inr(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite", "currency": "INR"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["order_id"] == "order_test_pricing"
            assert data["is_subscription"] is False
            assert data["amount"] == 1999900

    def test_create_order_pro_monthly_usd(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "pro", "currency": "USD"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["currency"] == "USD"
            assert data["is_subscription"] is True

    def test_create_order_lifetime_pro_usd(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_pro", "currency": "USD"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["amount"] == 12900
            assert data["currency"] == "USD"
            assert data["is_subscription"] is False

    def test_create_order_lifetime_elite_usd(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite", "currency": "USD"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["amount"] == 22900
            assert data["currency"] == "USD"

    def test_create_order_invalid_plan_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "hacker_plan"})
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_create_order_free_plan_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "free"})
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_create_order_unsupported_currency_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/create-order", json={"plan": "pro", "currency": "EUR"})
            assert r.status_code == 400
            _assert_error_shape(r)


# ---------------------------------------------------------------------------
# Pro user: upgrades and blocked paths
# ---------------------------------------------------------------------------


class TestProUserUpgrades:
    def test_pro_can_upgrade_to_elite_monthly(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/razorpay/create-order", json={"plan": "elite"})
            assert r.status_code == 200, r.text
            assert r.json()["is_subscription"] is True

    def test_pro_can_upgrade_to_lifetime_pro(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_pro"})
            assert r.status_code == 200, r.text
            assert r.json()["is_subscription"] is False

    def test_pro_can_upgrade_to_lifetime_elite(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite"})
            assert r.status_code == 200, r.text

    def test_pro_cannot_buy_same_plan_pro(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_pro_cannot_downgrade_to_free(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="pro")
            r = client.post("/api/razorpay/create-order", json={"plan": "free"})
            assert r.status_code == 400
            _assert_error_shape(r)


# ---------------------------------------------------------------------------
# Elite user: further upgrade attempts
# ---------------------------------------------------------------------------


class TestEliteUserUpgrades:
    def test_elite_can_upgrade_to_lifetime_elite(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite"})
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["is_subscription"] is False
            assert data["amount"] == 1999900

    def test_elite_cannot_buy_same_plan_elite(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post("/api/razorpay/create-order", json={"plan": "elite"})
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_elite_cannot_downgrade_to_pro(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="elite")
            r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_lifetime_elite_cannot_upgrade_further(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            for plan in ("pro", "elite", "lifetime_pro", "lifetime_elite"):
                r = client.post("/api/razorpay/create-order", json={"plan": plan})
                assert r.status_code == 400, f"Expected 400 for plan={plan}, got {r.status_code}"
                _assert_error_shape(r)


# ---------------------------------------------------------------------------
# normalize_plan correctness
# ---------------------------------------------------------------------------


class TestNormalizePlan:
    def test_lifetime_pro_normalizes_to_pro(self) -> None:
        assert normalize_plan("lifetime_pro") == "pro"

    def test_lifetime_elite_normalizes_to_elite(self) -> None:
        assert normalize_plan("lifetime_elite") == "elite"

    def test_free_unchanged(self) -> None:
        assert normalize_plan("free") == "free"

    def test_pro_unchanged(self) -> None:
        assert normalize_plan("pro") == "pro"

    def test_elite_unchanged(self) -> None:
        assert normalize_plan("elite") == "elite"

    def test_unknown_plan_unchanged(self) -> None:
        assert normalize_plan("something_else") == "something_else"

    def test_lifetime_pro_can_access_pro_paths(self, monkeypatch) -> None:
        """lifetime_pro users must be able to access Pro-tier learning paths."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_pro")
            r = client.get("/api/paths")
            assert r.status_code == 200, r.text
            paths = r.json()
            pro_paths = [p for p in paths if p["tier"] == "pro"]
            # All pro paths should be accessible to lifetime_pro
            for p in pro_paths:
                assert p["accessible"] is True, f"Path {p['slug']} should be accessible to lifetime_pro"

    def test_lifetime_elite_can_access_pro_paths(self, monkeypatch) -> None:
        """lifetime_elite users must be able to access Pro-tier learning paths."""
        with TestClient(app) as client:
            _make_user(client, plan="lifetime_elite")
            r = client.get("/api/paths")
            assert r.status_code == 200, r.text
            paths = r.json()
            pro_paths = [p for p in paths if p["tier"] == "pro"]
            for p in pro_paths:
                assert p["accessible"] is True, f"Path {p['slug']} should be accessible to lifetime_elite"

    def test_free_user_cannot_access_pro_paths(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.get("/api/paths")
            assert r.status_code == 200, r.text
            paths = r.json()
            pro_paths = [p for p in paths if p["tier"] == "pro"]
            for p in pro_paths:
                assert p["accessible"] is False, f"Path {p['slug']} should NOT be accessible to free"


# ---------------------------------------------------------------------------
# HMAC verification
# ---------------------------------------------------------------------------


class TestHMACVerification:
    def test_tampered_signature_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "pro",
                "razorpay_payment_id": "pay_test",
                "razorpay_signature": "tampered_signature",
                "razorpay_order_id": "order_test",
            })
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_correct_signature_order_flow_upgrades_plan(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            order_id = "order_sig_test"
            payment_id = "pay_sig_test"
            sig = _verify_sig(payment_id, order_id)
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "lifetime_pro",
                "razorpay_payment_id": payment_id,
                "razorpay_signature": sig,
                "razorpay_order_id": order_id,
            })
            assert r.status_code == 200, r.text
            assert r.json()["plan"] == "lifetime_pro"
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_pro"

    def test_correct_signature_subscription_flow(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            payment_id = "pay_sub_sig"
            sub_id = "sub_sig_test"
            sig = _verify_sub_sig(payment_id, sub_id)
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "pro",
                "razorpay_payment_id": payment_id,
                "razorpay_signature": sig,
                "razorpay_subscription_id": sub_id,
            })
            assert r.status_code == 200, r.text
            assert r.json()["plan"] == "pro"

    def test_wrong_webhook_signature_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            event = _payment_captured_event("evt_bad_whsig", user["id"], "pro")
            raw = json.dumps(event).encode()
            r = client.post(
                "/api/razorpay/webhook",
                content=raw,
                headers={"X-Razorpay-Signature": "bad_signature"},
            )
            assert r.status_code == 400
            _assert_error_shape(r)

    def test_missing_webhook_signature_returns_400(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            event = _payment_captured_event("evt_no_sig", user["id"], "pro")
            raw = json.dumps(event).encode()
            r = client.post("/api/razorpay/webhook", content=raw)
            assert r.status_code in {400, 503}

    def test_both_order_id_and_subscription_id_returns_400(self, monkeypatch) -> None:
        """Ambiguous verify-payment request (both order_id and subscription_id) must be rejected."""
        _configure(monkeypatch)
        with TestClient(app) as client:
            _make_user(client, plan="free")
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "pro",
                "razorpay_payment_id": "pay_ambiguous",
                "razorpay_signature": "any_sig",
                "razorpay_order_id": "order_ambiguous",
                "razorpay_subscription_id": "sub_ambiguous",
            })
            assert r.status_code == 400
            _assert_error_shape(r)


# ---------------------------------------------------------------------------
# Webhook idempotency
# ---------------------------------------------------------------------------


class TestWebhookIdempotency:
    def test_replay_results_in_exactly_one_plan_change(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            event = _payment_captured_event("evt_idem_1", user["id"], "lifetime_pro")

            first = _send_webhook(client, event)
            assert first.status_code == 200
            assert first.json()["status"] == "processed"

            second = _send_webhook(client, event)
            assert second.status_code == 200
            assert second.json()["status"] == "already processed"

            # Plan should still be lifetime_pro, not double-applied or corrupted
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_pro"

    def test_verify_payment_replay_is_safe_noop(self, monkeypatch) -> None:
        """Replaying verify-payment with same payment_id should be a safe no-op."""
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            payment_id = "pay_idem_verify"
            order_id = "order_idem_verify"
            sig = _verify_sig(payment_id, order_id)
            payload = {
                "plan": "lifetime_pro",
                "razorpay_payment_id": payment_id,
                "razorpay_signature": sig,
                "razorpay_order_id": order_id,
            }
            first = client.post("/api/razorpay/verify-payment", json=payload)
            assert first.status_code == 200
            assert first.json()["plan"] == "lifetime_pro"

            # Second call — user is now lifetime_pro; replay should be safe
            second = client.post("/api/razorpay/verify-payment", json=payload)
            assert second.status_code == 200
            # Plan should not regress
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_pro"

    def test_webhook_lifetime_pro_plan_stored_verbatim(self, monkeypatch) -> None:
        """lifetime_pro must be stored as 'lifetime_pro', not 'pro'."""
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = _send_webhook(client, _payment_captured_event("evt_ltp_verb", user["id"], "lifetime_pro"))
            assert r.status_code == 200
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_pro"

    def test_webhook_lifetime_elite_plan_stored_verbatim(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = _send_webhook(client, _payment_captured_event("evt_lte_verb", user["id"], "lifetime_elite"))
            assert r.status_code == 200
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_elite"

    def test_subscription_cancelled_does_not_downgrade_lifetime_pro(self, monkeypatch) -> None:
        """A stray subscription.cancelled must never revoke a lifetime purchase."""
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="lifetime_pro")
            cancel_event = {
                "id": "evt_cancel_ltp",
                "event": "subscription.cancelled",
                "payload": {
                    "subscription": {
                        "entity": {
                            "id": "sub_old",
                            "notes": {"user_id": user["id"]},
                        }
                    }
                },
            }
            r = _send_webhook(client, cancel_event)
            assert r.status_code == 200
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_pro"

    def test_subscription_cancelled_does_not_downgrade_lifetime_elite(self, monkeypatch) -> None:
        _configure(monkeypatch)
        with TestClient(app) as client:
            user = _make_user(client, plan="lifetime_elite")
            cancel_event = {
                "id": "evt_cancel_lte",
                "event": "subscription.cancelled",
                "payload": {
                    "subscription": {
                        "entity": {
                            "id": "sub_old",
                            "notes": {"user_id": user["id"]},
                        }
                    }
                },
            }
            r = _send_webhook(client, cancel_event)
            assert r.status_code == 200
            profile = client.get("/api/user/profile", params={"user_id": user["id"]})
            assert profile.json()["plan"] == "lifetime_elite"


# ---------------------------------------------------------------------------
# /api/user/plan admin endpoint
# ---------------------------------------------------------------------------


class TestAdminPlanEndpoint:
    def test_free_to_pro_succeeds(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "pro",
                "context": "test",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["new_plan"] == "pro"
            assert data["old_plan"] == "free"

    def test_free_to_elite_succeeds(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "elite",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True

    def test_free_to_lifetime_pro_succeeds(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "lifetime_pro",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True
            assert r.json()["new_plan"] == "lifetime_pro"

    def test_free_to_lifetime_elite_succeeds(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "lifetime_elite",
            })
            assert r.status_code == 200
            assert r.json()["success"] is True

    def test_invalid_plan_returns_error_shape(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="free")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "hacker_plan",
            })
            assert r.status_code == 200  # endpoint returns 200 with success=False
            data = r.json()
            assert data["success"] is False
            assert "reason" in data

    def test_same_plan_returns_success_no_change(self) -> None:
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            r = client.post("/api/user/plan", json={
                "user_id": user["id"],
                "new_plan": "pro",
            })
            assert r.status_code == 200
            data = r.json()
            assert data["success"] is True
            assert data["old_plan"] == "pro"
            assert data["new_plan"] == "pro"

    def test_unknown_user_returns_404(self) -> None:
        with TestClient(app) as client:
            _make_user(client, plan="free")  # warm up session
            r = client.post("/api/user/plan", json={
                "user_id": "00000000-0000-0000-0000-000000000000",
                "new_plan": "pro",
            })
            assert r.status_code == 404
            _assert_error_shape(r)

    def test_all_valid_plans_can_be_set(self) -> None:
        """Every valid plan string must be accepted by the admin endpoint."""
        for plan in ("free", "pro", "elite", "lifetime_pro", "lifetime_elite"):
            with TestClient(app) as client:
                user = _make_user(client, plan="free")
                r = client.post("/api/user/plan", json={
                    "user_id": user["id"],
                    "new_plan": plan,
                })
                assert r.status_code == 200, f"Plan {plan} failed: {r.text}"
                data = r.json()
                assert data["success"] is True or data.get("reason") == "No change"
