"""TC-208 to TC-223 — Razorpay Payments."""
import hashlib
import hmac as _hmac
import json
import os
import uuid

import pytest
from starlette.testclient import TestClient
from unittest.mock import MagicMock, patch

import backend.main as main
from conftest import _db_conn, _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _verified_user(client: TestClient, plan: str = "free") -> dict:
    """Create a user and mark their email as verified."""
    user = _make_user(client, plan=plan)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET email_verified = true WHERE id = %s::uuid",
                (user["id"],),
            )
        conn.commit()
    finally:
        conn.close()
    return user


def _make_razorpay_mock(
    order_id: str = "order_test123",
    subscription_id: str = "sub_test123",
) -> MagicMock:
    mock_client = MagicMock()
    mock_client.order.create.return_value = {"id": order_id}
    mock_client.subscription.create.return_value = {"id": subscription_id}
    mock_client.customer.create.return_value = {"id": "cust_test123"}
    return mock_client


# ---------------------------------------------------------------------------
# TC-208 to TC-212: create-order
# ---------------------------------------------------------------------------

def test_tc208_create_order_pro_returns_subscription():
    """TC-208: plan=pro → is_subscription=True, subscription_id non-null."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    mock_client = _make_razorpay_mock()
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"), \
         patch("routers.razorpay.RAZORPAY_PLAN_PRO", "plan_pro_123"), \
         patch("routers.razorpay.razorpay") as mock_razorpay_module:
        mock_razorpay_module.Client.return_value = mock_client
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_subscription"] is True
    assert body["subscription_id"] is not None
    assert body["order_id"] is None


def test_tc209_create_order_lifetime_pro_returns_order_with_amount():
    """TC-209: plan=lifetime_pro → order_id non-null, amount=1199900."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    mock_client = _make_razorpay_mock()
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"), \
         patch("routers.razorpay.RAZORPAY_AMOUNT_LIFETIME_PRO", 1199900), \
         patch("routers.razorpay.razorpay") as mock_razorpay_module:
        mock_razorpay_module.Client.return_value = mock_client
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_pro"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_subscription"] is False
    assert body["order_id"] is not None
    assert body["amount"] == 1199900


def test_tc210_create_order_lifetime_elite_returns_correct_amount():
    """TC-210: plan=lifetime_elite → amount=1999900."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    mock_client = _make_razorpay_mock()
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"), \
         patch("routers.razorpay.RAZORPAY_AMOUNT_LIFETIME_ELITE", 1999900), \
         patch("routers.razorpay.razorpay") as mock_razorpay_module:
        mock_razorpay_module.Client.return_value = mock_client
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/create-order", json={"plan": "lifetime_elite"})
    assert r.status_code == 200, r.text
    assert r.json()["amount"] == 1999900


def test_tc211_invalid_plan_returns_400():
    """TC-211: Invalid plan name → 400."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/create-order", json={"plan": "not_a_real_plan"})
    assert r.status_code == 400


def test_tc212_unauthenticated_create_order_returns_401():
    """TC-212: Unauthenticated POST /api/razorpay/create-order → 401."""
    with TestClient(app) as client:
        r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
    assert r.status_code == 401


def test_create_order_razorpay_failure_returns_clean_502():
    """A Razorpay SDK failure (e.g. subscriptions not enabled → 'Authentication
    failed') must surface as a clean 502 with a user-facing message, not a bare
    unhandled 500 (which the browser hides cross-origin as a 'Network Error')."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    mock_client = _make_razorpay_mock()
    mock_client.subscription.create.side_effect = Exception("Authentication failed")
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"), \
         patch("routers.razorpay.RAZORPAY_PLAN_PRO", "plan_pro_123"), \
         patch("routers.razorpay.razorpay") as mock_razorpay_module:
        mock_razorpay_module.Client.return_value = mock_client
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/create-order", json={"plan": "pro"})
    assert r.status_code == 502, r.text
    assert "checkout" in r.json()["error"].lower()


# ---------------------------------------------------------------------------
# Payment payload contract — the guardrail against the da772b5 regression.
#
# WHY THIS EXISTS: these tests mock the Razorpay client, and a mock accepts ANY
# payload. da772b5 shipped a broken `customer_id` field precisely because the
# mocked tests couldn't see that the REAL Razorpay API rejects it (400
# "Authentication failed"), which broke every monthly upgrade in production.
# So we pin the EXACT payload here (forbid stray fields), and add a real-API
# smoke test at the bottom as the backstop mocks structurally cannot provide.
# ---------------------------------------------------------------------------

def _capture_create_order(existing_user, plan: str, currency: str = "INR"):
    """Drive create-order with a mocked Razorpay client; return (response, mock_client)
    so callers can assert exactly what payload reached Razorpay."""
    mock_client = _make_razorpay_mock()
    with patch("routers.razorpay.RAZORPAY_KEY_ID", "rzp_key_123"), \
         patch("routers.razorpay.RAZORPAY_KEY_SECRET", "rzp_secret_123"), \
         patch("routers.razorpay.RAZORPAY_PLAN_PRO", "plan_pro_123"), \
         patch("routers.razorpay.RAZORPAY_PLAN_ELITE", "plan_elite_123"), \
         patch("routers.razorpay.razorpay") as mod:
        mod.Client.return_value = mock_client
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=existing_user)
            r = client.post("/api/razorpay/create-order", json={"plan": plan, "currency": currency})
    return r, mock_client


@pytest.mark.parametrize("plan,expected_plan_id,target", [
    ("pro", "plan_pro_123", "pro"),
    ("elite", "plan_elite_123", "elite"),
])
def test_subscription_payload_contract(plan, expected_plan_id, target):
    """Monthly (pro/elite): subscription.create must receive EXACTLY the allowed
    keys — and NEVER customer_id (da772b5 → Razorpay 400 'Authentication failed').
    The strict key-set assertion forces any payload change through review."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    r, mock_client = _capture_create_order(user, plan)
    assert r.status_code == 200, r.text
    assert mock_client.subscription.create.called
    assert not mock_client.order.create.called
    payload = mock_client.subscription.create.call_args[0][0]
    assert set(payload) == {"plan_id", "customer_notify", "total_count", "notes"}, (
        f"subscription payload keys changed to {sorted(payload)} — a stray field "
        "(e.g. customer_id) makes Razorpay reject the call. Change deliberately."
    )
    assert "customer_id" not in payload
    assert payload["plan_id"] == expected_plan_id
    assert payload["total_count"] == 24
    assert payload["customer_notify"] == 1
    assert payload["notes"] == {"user_id": str(user["id"]), "target_plan": target}
    # the customer pre-warm was removed — no customer is created during checkout
    assert not mock_client.customer.create.called


@pytest.mark.parametrize("plan,expected_amount,target", [
    ("lifetime_pro", 1199900, "lifetime_pro"),
    ("lifetime_elite", 1999900, "lifetime_elite"),
])
def test_lifetime_order_payload_contract(plan, expected_amount, target):
    """Lifetime (one-time): order.create must receive EXACTLY the allowed keys."""
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    r, mock_client = _capture_create_order(user, plan)
    assert r.status_code == 200, r.text
    assert mock_client.order.create.called
    assert not mock_client.subscription.create.called
    payload = mock_client.order.create.call_args[0][0]
    assert set(payload) == {"amount", "currency", "payment_capture", "notes"}
    assert "customer_id" not in payload
    assert payload["amount"] == expected_amount
    assert payload["currency"] == "INR"
    assert payload["payment_capture"] == 1
    assert payload["notes"] == {"user_id": str(user["id"]), "target_plan": target}
    assert not mock_client.customer.create.called


@pytest.mark.skipif(
    not (os.environ.get("RUN_RAZORPAY_LIVE") == "1" and os.environ.get("RAZORPAY_KEY_ID")),
    reason="live Razorpay smoke test — set RUN_RAZORPAY_LIVE=1 with real test keys to run",
)
def test_live_create_order_pro_accepted_by_razorpay():
    """END-TO-END against the REAL Razorpay test API — the backstop mocks can't give.
    Mocked tests couldn't catch da772b5 because a mock accepts any payload; only the
    real API rejects a bad one. Drives the real create-order endpoint, asserts Razorpay
    accepts the subscription, then cancels it so nothing is left behind. Skipped in CI
    (no keys); run manually before shipping any Razorpay payment change."""
    import razorpay
    from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
        _make_user(client, plan="free", existing_user=user)
        r = client.post("/api/razorpay/create-order", json={"plan": "pro", "currency": "INR"})
    assert r.status_code == 200, f"Razorpay rejected our subscription payload: {r.text}"
    body = r.json()
    assert body["is_subscription"] is True
    assert body["subscription_id"]
    # cleanup — cancel the test-mode subscription we just created (best effort)
    try:
        razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)).subscription.cancel(
            body["subscription_id"], {"cancel_at_cycle_end": 0}
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# TC-213 to TC-216: verify-payment
# ---------------------------------------------------------------------------

def _make_hmac(secret: str, body: str) -> str:
    return _hmac.new(
        secret.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def test_tc213_verify_payment_order_valid_signature():
    """TC-213: Correct HMAC for order flow → 200 with plan applied."""
    test_secret = "test_key_secret_abc"
    order_id = "order_test_abc"
    payment_id = "pay_test_abc"
    sig = _make_hmac(test_secret, f"{order_id}|{payment_id}")

    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    with patch("routers.razorpay.RAZORPAY_KEY_SECRET", test_secret):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "lifetime_pro",
                "razorpay_payment_id": payment_id,
                "razorpay_order_id": order_id,
                "razorpay_signature": sig,
            })
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "lifetime_pro"


def test_tc214_verify_payment_invalid_signature_returns_400():
    """TC-214: Wrong signature for order → 400."""
    test_secret = "test_key_secret_abc"
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    with patch("routers.razorpay.RAZORPAY_KEY_SECRET", test_secret):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "lifetime_pro",
                "razorpay_payment_id": "pay_test_xyz",
                "razorpay_order_id": "order_test_xyz",
                "razorpay_signature": "wrong_signature_here",
            })
    assert r.status_code == 400


def test_tc215_verify_payment_subscription_valid_signature():
    """TC-215: Correct HMAC for subscription flow → 200 with plan applied."""
    test_secret = "test_key_secret_def"
    payment_id = "pay_sub_test"
    subscription_id = "sub_test_def"
    sig = _make_hmac(test_secret, f"{payment_id}|{subscription_id}")

    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    with patch("routers.razorpay.RAZORPAY_KEY_SECRET", test_secret):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/razorpay/verify-payment", json={
                "plan": "pro",
                "razorpay_payment_id": payment_id,
                "razorpay_subscription_id": subscription_id,
                "razorpay_signature": sig,
            })
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "pro"


def test_tc216_verify_payment_idempotent():
    """TC-216: Duplicate payment_id → second call returns 200 (already processed)."""
    test_secret = "test_key_secret_idem"
    order_id = "order_idem_test"
    payment_id = "pay_idem_test"
    sig = _make_hmac(test_secret, f"{order_id}|{payment_id}")
    payload = {
        "plan": "lifetime_pro",
        "razorpay_payment_id": payment_id,
        "razorpay_order_id": order_id,
        "razorpay_signature": sig,
    }

    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    with patch("routers.razorpay.RAZORPAY_KEY_SECRET", test_secret):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r1 = client.post("/api/razorpay/verify-payment", json=payload)
            r2 = client.post("/api/razorpay/verify-payment", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200


# ---------------------------------------------------------------------------
# TC-217 to TC-223: Webhook
# ---------------------------------------------------------------------------

def _make_webhook_hmac(secret: str, body: bytes) -> str:
    return _hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


def test_tc217_webhook_no_secret_configured_returns_503():
    """TC-217: RAZORPAY_WEBHOOK_SECRET not set → 503."""
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", ""):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=b'{"event":"test"}',
                headers={"X-Razorpay-Signature": "anything"},
            )
    assert r.status_code == 503


def test_tc218_webhook_invalid_signature_returns_400():
    """TC-218: WEBHOOK_SECRET set but wrong signature → 400."""
    test_secret = "wh_secret_test"
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=b'{"event":"payment.captured","id":"evt_test"}',
                headers={"X-Razorpay-Signature": "wrong_sig"},
            )
    assert r.status_code == 400


def test_tc219_webhook_valid_signature_unknown_event_returns_200():
    """TC-219: Valid signature + unknown event type → 200 (no-op)."""
    test_secret = "wh_secret_test2"
    payload = json.dumps({
        "id": f"evt_{uuid.uuid4().hex}",
        "event": "refund.created",
        "payload": {},
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r.status_code == 200


def test_tc220_webhook_payment_captured_upgrades_plan():
    """TC-220: payment.captured with valid user notes → plan upgraded."""
    test_secret = "wh_secret_test3"
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = json.dumps({
        "id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_webhook",
                    "notes": {
                        "user_id": str(user_id),
                        "target_plan": "lifetime_pro",
                    }
                }
            }
        }
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r.status_code == 200

    # Verify plan was upgraded
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        assert row[0] == "lifetime_pro"
    finally:
        conn.close()


def test_tc221_webhook_subscription_cancelled_downgrades_to_free():
    """TC-221: subscription.cancelled for non-lifetime user → plan → free."""
    test_secret = "wh_secret_test4"
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    user_id = user["id"]

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = json.dumps({
        "id": event_id,
        "event": "subscription.cancelled",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_test_cancel",
                    "notes": {
                        "user_id": str(user_id),
                    }
                }
            }
        }
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r.status_code == 200

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        assert row[0] == "free"
    finally:
        conn.close()


def test_tc222_webhook_lifetime_user_ignores_subscription_cancelled():
    """TC-222: subscription.cancelled for lifetime user → plan stays lifetime_pro."""
    test_secret = "wh_secret_test5"
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_pro")
    user_id = user["id"]

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = json.dumps({
        "id": event_id,
        "event": "subscription.cancelled",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_test_lifetime",
                    "notes": {
                        "user_id": str(user_id),
                    }
                }
            }
        }
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r.status_code == 200

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        assert row[0] == "lifetime_pro", f"Expected lifetime_pro, got {row[0]}"
    finally:
        conn.close()


def test_tc223_webhook_idempotent_duplicate_event():
    """TC-223: Duplicate event_id → second call returns 200 (already processed)."""
    test_secret = "wh_secret_test6"
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = json.dumps({
        "id": event_id,
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_idem_webhook",
                    "notes": {
                        "user_id": str(user_id),
                        "target_plan": "pro",
                    }
                }
            }
        }
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret):
        with TestClient(app) as client:
            r1 = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
            r2 = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json() == {"status": "already processed"}


def test_tc223b_webhook_subscription_charged_resolves_plan_from_plan_id():
    """Regression for the P0: a mid-cycle Pro→Elite switch updates the
    subscription's plan_id but NOT its frozen notes.target_plan. On the next
    subscription.charged the webhook must apply the plan from the (authoritative)
    plan_id, not the stale notes — otherwise the user is charged Elite but stays
    Pro forever. plan_id resolution must win."""
    test_secret = "wh_secret_switch"
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    user_id = user["id"]

    event_id = f"evt_{uuid.uuid4().hex}"
    payload = json.dumps({
        "id": event_id,
        "event": "subscription.charged",
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_switched",
                    "plan_id": "plan_elite_live",        # NEW plan after the switch
                    "notes": {
                        "user_id": str(user_id),
                        "target_plan": "pro",            # STALE — frozen at creation
                    },
                }
            }
        }
    }).encode()
    sig = _make_webhook_hmac(test_secret, payload)
    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", test_secret), \
         patch("routers.razorpay.RAZORPAY_PLAN_PRO", "plan_pro_live"), \
         patch("routers.razorpay.RAZORPAY_PLAN_ELITE", "plan_elite_live"):
        with TestClient(app) as client:
            r = client.post(
                "/api/razorpay/webhook",
                content=payload,
                headers={"X-Razorpay-Signature": sig},
            )
    assert r.status_code == 200

    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s::uuid", (user_id,))
            row = cur.fetchone()
        assert row[0] == "elite", f"plan_id must win over stale notes; got {row[0]}"
    finally:
        conn.close()
