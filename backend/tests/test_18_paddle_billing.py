"""Paddle billing-parity on the account endpoints.

A Paddle subscriber is a user on a paid plan with NO Razorpay subscription but a
recorded Paddle charge in payment_events (international / Merchant-of-Record rail).
The Razorpay-backed /account billing + management endpoints must (a) surface a
rail-aware billing view for them rather than an empty Razorpay-shaped panel, and
(b) return an honest 409 (managed via Paddle) on cancel / switch / update-payment
rather than the misleading "no subscription on record" 400.
"""
import json
import uuid

import pytest
from starlette.testclient import TestClient

import backend.main as main
from conftest import _db_conn, _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _make_paddle_subscriber(client: TestClient, plan: str = "pro") -> dict:
    """A user whose only payment is a recorded Paddle charge (no Razorpay sub)."""
    user = _make_user(client, plan=plan)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO payment_events (event_id, event_type, user_id, provider, payload_summary)
                VALUES (%s, 'transaction.completed', %s::uuid, 'paddle', %s::jsonb)
                """,
                (
                    f"paddle:evt_{uuid.uuid4().hex}",
                    user["id"],
                    json.dumps({
                        "type": "transaction.completed",
                        "user_id": user["id"],
                        "target_plan": plan,
                        "amount": "1500",
                        "currency": "USD",
                        "transaction_id": "txn_acct",
                    }),
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return user


def test_billing_is_rail_aware_for_paddle_subscriber():
    with TestClient(app) as client:
        _make_paddle_subscriber(client, plan="pro")
        r = client.get("/api/account/billing")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["provider"] == "paddle"
    assert body["managed_externally"] is True
    assert body["is_subscription"] is True
    assert body["plan_currency"] == "USD"
    assert len(body["invoices"]) == 1
    inv = body["invoices"][0]
    assert inv["amount"] == "1500"
    assert inv["currency"] == "USD"
    assert inv["status"] == "paid"


def test_cancel_returns_409_managed_by_paddle():
    with TestClient(app) as client:
        _make_paddle_subscriber(client, plan="pro")
        r = client.post("/api/account/cancel-subscription")
    assert r.status_code == 409, r.text
    assert "Paddle" in r.text


def test_switch_returns_409_managed_by_paddle():
    with TestClient(app) as client:
        _make_paddle_subscriber(client, plan="pro")
        r = client.post("/api/account/switch-plan", json={"target_plan": "elite"})
    assert r.status_code == 409, r.text
    assert "Paddle" in r.text


def test_update_payment_method_returns_409_managed_by_paddle():
    with TestClient(app) as client:
        _make_paddle_subscriber(client, plan="pro")
        r = client.post("/api/account/update-payment-method")
    assert r.status_code == 409, r.text
    assert "Paddle" in r.text


def test_razorpay_subscriber_short_circuits_paddle_guard():
    """A user with a Razorpay subscription id is unaffected by the Paddle guard:
    billing stays on the Razorpay rail (provider == 'razorpay')."""
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
        conn = _db_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET razorpay_subscription_id = %s WHERE id = %s::uuid",
                    ("sub_rzp_unaffected", user["id"]),
                )
            conn.commit()
        finally:
            conn.close()
        r = client.get("/api/account/billing")
    assert r.status_code == 200, r.text
    assert r.json()["provider"] == "razorpay"
