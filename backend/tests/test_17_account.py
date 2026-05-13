"""TC-224 to TC-248 — Account billing and subscription management.

Covers all five endpoints added in the billing-management feature:

    GET  /api/account/billing
    POST /api/account/cancel-subscription
    POST /api/account/switch-plan
    POST /api/account/update-payment-method
    POST /api/account/reactivate-subscription

Razorpay SDK calls are mocked throughout; no live network traffic is made.
"""

from __future__ import annotations

import contextlib
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_SUB_ID = "sub_account_test"
_FUTURE = int(time.time()) + 30 * 24 * 3600   # 30 days from now
_PAST   = int(time.time()) -  5 * 24 * 3600   # 5 days ago

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_sub_id(user_id: str, sub_id: str = _SUB_ID) -> None:
    """Directly write a razorpay_subscription_id into the test DB for a user."""
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET razorpay_subscription_id = %s WHERE id = %s::uuid",
                (sub_id, user_id),
            )
        conn.commit()
    finally:
        conn.close()


def _active_sub(**overrides: Any) -> dict:
    """Razorpay subscription object in normal active state."""
    base: dict[str, Any] = {
        "id": _SUB_ID,
        "status": "active",
        "current_start": _PAST,
        "current_end": _FUTURE,
        "charge_at": _FUTURE,
        "end_at": None,
        "short_url": "https://rzp.io/l/testlink",
    }
    return {**base, **overrides}


def _pending_cancel_sub(**overrides: Any) -> dict:
    """Active subscription with cancel_at_cycle_end=1 — user requested cancellation at cycle end."""
    base: dict[str, Any] = {
        "id": _SUB_ID,
        "status": "active",
        "current_start": _PAST,
        "current_end": _FUTURE,
        "charge_at": None,
        "cancel_at_cycle_end": 1,   # _is_cancelled_at_cycle_end → True
        "end_at": _FUTURE,
        "short_url": "https://rzp.io/l/testlink",
    }
    return {**base, **overrides}


def _mock_rzp_client(
    sub: dict | None = None,
    plan_amount: int = 29900,
    invoices: list | None = None,
) -> MagicMock:
    """Build a minimal Razorpay Client mock for account endpoints."""
    mc = MagicMock()

    mc.subscription.fetch.return_value = sub if sub is not None else _active_sub()
    mc.subscription.cancel.return_value = {
        "id": _SUB_ID, "status": "cancelled", "current_end": _FUTURE,
    }
    mc.subscription.update.return_value = {
        "id": _SUB_ID,
        "status": "active",
        "current_end": _FUTURE,
        "charge_at": _FUTURE,
        "change_scheduled_at": _FUTURE,
    }
    mc.plan.fetch.return_value = {
        "id": "plan_test",
        "item": {"unit_amount": plan_amount, "currency": "INR"},
    }
    if invoices is None:
        invoices = [
            {
                "id": "inv_001",
                "amount": plan_amount,
                "currency": "INR",
                "status": "paid",
                "date": _PAST,
                "short_url": "https://rzp.io/inv/001",
            }
        ]
    mc.invoice.all.return_value = {"items": invoices}
    return mc


@contextlib.contextmanager
def _razorpay_patched(mock_client: MagicMock):
    """Patch Razorpay config + SDK in routers.account for one test block."""
    with (
        patch("routers.account.RAZORPAY_KEY_ID", "rzp_key_test"),
        patch("routers.account.RAZORPAY_KEY_SECRET", "rzp_secret_test"),
        patch("routers.account.RAZORPAY_PLAN_PRO", "plan_pro_test"),
        patch("routers.account.RAZORPAY_PLAN_ELITE", "plan_elite_test"),
        patch("routers.account.razorpay") as mock_mod,
    ):
        mock_mod.Client.return_value = mock_client
        yield


# ===========================================================================
# GET /api/account/billing  (TC-224 to TC-228)
# ===========================================================================

def test_tc224_billing_unauthenticated_returns_401():
    """TC-224: GET /api/account/billing without session → 401."""
    with TestClient(app) as client:
        r = client.get("/api/account/billing")
    assert r.status_code == 401


def test_tc225_billing_free_user_returns_base_response():
    """TC-225: Free plan → no Razorpay call; returns skeleton billing response."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.get("/api/account/billing")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] == "free"
    assert body["is_subscription"] is False
    assert body["is_lifetime"] is False
    assert body["invoices"] == []


def test_tc226_billing_lifetime_user_returns_lifetime_flag():
    """TC-226: Lifetime plan → is_lifetime=True, is_subscription=False, no Razorpay call."""
    with TestClient(app) as client:
        _make_user(client, plan="lifetime_pro")
        r = client.get("/api/account/billing")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] == "lifetime_pro"
    assert body["is_lifetime"] is True
    assert body["is_subscription"] is False
    assert body["invoices"] == []


def test_tc227_billing_pro_without_subscription_id_returns_unknown_status():
    """TC-227: Pro plan but no subscription_id stored → subscription_status='unknown'.

    This happens when the user paid but the webhook has not fired yet, or the
    subscription_id was never persisted.
    """
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        # No _set_sub_id call — razorpay_subscription_id is NULL
        r = client.get("/api/account/billing")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_subscription"] is True
    assert body["subscription_status"] == "unknown"


def test_tc228_billing_pro_with_subscription_id_returns_live_data():
    """TC-228: Pro + subscription_id → full billing response fetched from Razorpay mock."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.get("/api/account/billing")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_subscription"] is True
    assert body["subscription_status"] == "active"
    assert body["cancelled_at_cycle_end"] is False
    assert body["billing_cycle_end"] == _FUTURE
    assert body["plan_amounts"] is not None
    assert len(body["invoices"]) == 1
    assert body["invoices"][0]["status"] == "paid"
    assert body["invoices"][0]["pdf_url"] == "https://rzp.io/inv/001"
    mc.subscription.fetch.assert_called_once()


# ===========================================================================
# POST /api/account/cancel-subscription  (TC-229 to TC-234)
# ===========================================================================

def test_tc229_cancel_unauthenticated_returns_401():
    """TC-229: POST /api/account/cancel-subscription without session → 401."""
    with TestClient(app) as client:
        r = client.post("/api/account/cancel-subscription")
    assert r.status_code == 401


def test_tc230_cancel_free_user_returns_400():
    """TC-230: Free plan → 400 (no subscription to cancel)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/account/cancel-subscription")
    assert r.status_code == 400


def test_tc231_cancel_lifetime_user_returns_400():
    """TC-231: Lifetime plan → 400 (one-time purchase, cannot cancel via this endpoint)."""
    with TestClient(app) as client:
        _make_user(client, plan="lifetime_pro")
        r = client.post("/api/account/cancel-subscription")
    assert r.status_code == 400


def test_tc232_cancel_pro_without_subscription_id_returns_400():
    """TC-232: Pro plan but no subscription_id stored → 400 before any Razorpay call."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        r = client.post("/api/account/cancel-subscription")
    assert r.status_code == 400


def test_tc233_cancel_active_subscription_returns_cancel_at():
    """TC-233: Pro with active subscription → 200; Razorpay cancel called; cancel_at returned."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/cancel-subscription")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cancel_at"] == _FUTURE
    mc.subscription.cancel.assert_called_once_with(_SUB_ID, {"cancel_at_cycle_end": 1})


def test_tc234_cancel_already_cancelled_subscription_returns_400():
    """TC-234: Subscription status='cancelled' → 400 (already expired/cancelled)."""
    mc = _mock_rzp_client(sub={**_active_sub(), "status": "cancelled"})
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/cancel-subscription")

    assert r.status_code == 400
    # Razorpay cancel should NOT have been called
    mc.subscription.cancel.assert_not_called()


# ===========================================================================
# POST /api/account/switch-plan  (TC-235 to TC-240)
# ===========================================================================

def test_tc235_switch_unauthenticated_returns_401():
    """TC-235: POST /api/account/switch-plan without session → 401."""
    with TestClient(app) as client:
        r = client.post("/api/account/switch-plan", json={"target_plan": "elite"})
    assert r.status_code == 401


def test_tc236_switch_free_user_returns_400():
    """TC-236: Free plan → 400 (no subscription to switch)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/account/switch-plan", json={"target_plan": "elite"})
    assert r.status_code == 400


def test_tc237_switch_same_plan_returns_400():
    """TC-237: target_plan equals current plan → 400."""
    with TestClient(app) as client:
        _make_user(client, plan="pro")
        # No subscription_id needed — validation fires before the Razorpay check
        r = client.post("/api/account/switch-plan", json={"target_plan": "pro"})
    assert r.status_code == 400


def test_tc238_switch_downgrade_with_timing_now_returns_400():
    """TC-238: Elite→Pro downgrade with timing='now' → 400 (downgrades are always cycle_end)."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="elite")
            _set_sub_id(user["id"])
            r = client.post("/api/account/switch-plan", json={"target_plan": "pro", "timing": "now"})

    assert r.status_code == 400
    mc.subscription.update.assert_not_called()


def test_tc239_switch_upgrade_cycle_end_schedules_change():
    """TC-239: Pro→Elite upgrade with timing='cycle_end' → 200; correct Razorpay update called."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post(
                "/api/account/switch-plan", json={"target_plan": "elite", "timing": "cycle_end"}
            )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["timing"] == "cycle_end"
    assert body["effective_at"] is not None
    mc.subscription.update.assert_called_once_with(
        _SUB_ID,
        {"plan_id": "plan_elite_test", "quantity": 1, "schedule_change_at": "cycle_end"},
    )


def test_tc240_switch_upgrade_now_switches_immediately():
    """TC-240: Pro→Elite upgrade with timing='now' → 200; Razorpay update called with 'now'."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post(
                "/api/account/switch-plan", json={"target_plan": "elite", "timing": "now"}
            )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["timing"] == "now"
    mc.subscription.update.assert_called_once_with(
        _SUB_ID,
        {"plan_id": "plan_elite_test", "quantity": 1, "schedule_change_at": "now"},
    )


# ===========================================================================
# POST /api/account/update-payment-method  (TC-241 to TC-244)
# ===========================================================================

def test_tc241_update_payment_unauthenticated_returns_401():
    """TC-241: POST /api/account/update-payment-method without session → 401."""
    with TestClient(app) as client:
        r = client.post("/api/account/update-payment-method")
    assert r.status_code == 401


def test_tc242_update_payment_free_user_returns_400():
    """TC-242: Free plan → 400 (not a subscriber)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/account/update-payment-method")
    assert r.status_code == 400


def test_tc243_update_payment_returns_razorpay_short_url():
    """TC-243: Pro with subscription_id; Razorpay returns short_url → 200 with redirect_url."""
    mc = _mock_rzp_client()
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/update-payment-method")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["redirect_url"] == "https://rzp.io/l/testlink"


def test_tc244_update_payment_no_short_url_returns_400():
    """TC-244: Subscription exists but short_url is None → 400 (no hosted URL available)."""
    mc = _mock_rzp_client(sub={**_active_sub(), "short_url": None})
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/update-payment-method")

    assert r.status_code == 400


# ===========================================================================
# POST /api/account/reactivate-subscription  (TC-245 to TC-248)
# ===========================================================================

def test_tc245_reactivate_unauthenticated_returns_401():
    """TC-245: POST /api/account/reactivate-subscription without session → 401."""
    with TestClient(app) as client:
        r = client.post("/api/account/reactivate-subscription")
    assert r.status_code == 401


def test_tc246_reactivate_free_user_returns_400():
    """TC-246: Free plan → 400 (no subscription to reactivate)."""
    with TestClient(app) as client:
        _make_user(client, plan="free")
        r = client.post("/api/account/reactivate-subscription")
    assert r.status_code == 400


def test_tc247_reactivate_active_non_pending_subscription_returns_400():
    """TC-247: Active subscription NOT pending cancellation → 400.

    cancel_at_cycle_end not set means _is_cancelled_at_cycle_end → False.
    """
    mc = _mock_rzp_client(sub=_active_sub())  # cancel_at_cycle_end not set
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/reactivate-subscription")

    assert r.status_code == 400
    mc.subscription.cancel.assert_not_called()


def test_tc248_reactivate_pending_cancel_subscription_returns_reactivated():
    """TC-248: Subscription with cancel_at_cycle_end=1 (pending cancel) → 200; reactivated=True.

    Verifies that Razorpay is called with cancel_at_cycle_end=0, which removes
    the scheduled cancellation.
    """
    mc = _mock_rzp_client(sub=_pending_cancel_sub())
    with _razorpay_patched(mc):
        with TestClient(app) as client:
            user = _make_user(client, plan="pro")
            _set_sub_id(user["id"])
            r = client.post("/api/account/reactivate-subscription")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reactivated"] is True
    mc.subscription.cancel.assert_called_once_with(_SUB_ID, {"cancel_at_cycle_end": 0})
