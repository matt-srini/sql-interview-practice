"""Paddle billing rail (global / Merchant-of-Record) — create-checkout + webhook.

Mirrors test_14_payments.py (Razorpay) for the second rail, plus the dual-rail
invariants that only matter once two providers feed one payment_events log:
  - Paddle event ids are stored with a "paddle:" prefix and provider='paddle'.
  - A Paddle event id IDENTICAL to a Razorpay event id does not collide (both
    process) — the property that lets both rails share the event_id PK.
"""
import hashlib
import hmac as _hmac
import json
import uuid

import pytest
from starlette.testclient import TestClient
from unittest.mock import patch

import backend.main as main
from conftest import _db_conn, _make_user

app = main.app
pytestmark = pytest.mark.usefixtures("isolated_state")


def _verified_user(client: TestClient, plan: str = "free") -> dict:
    user = _make_user(client, plan=plan)
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET email_verified = true WHERE id = %s::uuid", (user["id"],))
        conn.commit()
    finally:
        conn.close()
    return user


def _user_plan(user_id: str) -> str:
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT plan FROM users WHERE id = %s::uuid", (user_id,))
            return cur.fetchone()[0]
    finally:
        conn.close()


def _payment_event(event_id: str) -> tuple | None:
    conn = _db_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT event_id, provider, event_type FROM payment_events WHERE event_id = %s", (event_id,))
            return cur.fetchone()
    finally:
        conn.close()


def _paddle_sig(secret: str, body: bytes, ts: str = "1700000000") -> str:
    """Build a Paddle-Signature header: 'ts=<unix>;h1=<hmac(secret, ts:body)>'."""
    signed = ts.encode("utf-8") + b":" + body
    h1 = _hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"ts={ts};h1={h1}"


_CFG = dict(
    client_token="live_token_test",
    price_pro="pri_pro_usd",
    price_elite="pri_elite_usd",
    price_lifetime_pro="pri_lt_pro_usd",
    price_lifetime_elite="pri_lt_elite_usd",
)


def _patch_checkout_config():
    return [
        patch("routers.paddle.PADDLE_CLIENT_TOKEN", _CFG["client_token"]),
        patch("routers.paddle.PADDLE_ENVIRONMENT", "sandbox"),
        patch("routers.paddle.PADDLE_PRICE_PRO", _CFG["price_pro"]),
        patch("routers.paddle.PADDLE_PRICE_ELITE", _CFG["price_elite"]),
        patch("routers.paddle.PADDLE_PRICE_LIFETIME_PRO", _CFG["price_lifetime_pro"]),
        patch("routers.paddle.PADDLE_PRICE_LIFETIME_ELITE", _CFG["price_lifetime_elite"]),
    ]


# ---------------------------------------------------------------------------
# create-checkout
# ---------------------------------------------------------------------------

def test_create_checkout_pro_returns_subscription_config():
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    patches = _patch_checkout_config()
    for p in patches:
        p.start()
    try:
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "pro"})
    finally:
        for p in patches:
            p.stop()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["price_id"] == _CFG["price_pro"]
    assert body["is_subscription"] is True
    assert body["client_token"] == _CFG["client_token"]
    assert body["environment"] == "sandbox"
    assert body["custom_data"]["user_id"] == str(user["id"])
    assert body["custom_data"]["target_plan"] == "pro"


def test_create_checkout_lifetime_is_one_time():
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    patches = _patch_checkout_config()
    for p in patches:
        p.start()
    try:
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "lifetime_elite"})
    finally:
        for p in patches:
            p.stop()
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["price_id"] == _CFG["price_lifetime_elite"]
    assert body["is_subscription"] is False


def test_create_checkout_not_configured_returns_503():
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    # Client token empty → international checkout not live yet.
    with patch("routers.paddle.PADDLE_CLIENT_TOKEN", ""):
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "pro"})
    assert r.status_code == 503


def test_create_checkout_invalid_plan_returns_400():
    with TestClient(app) as client:
        user = _verified_user(client, plan="free")
    patches = _patch_checkout_config()
    for p in patches:
        p.start()
    try:
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "not_a_plan"})
    finally:
        for p in patches:
            p.stop()
    assert r.status_code == 400


def test_create_checkout_disallowed_upgrade_path_returns_400():
    # Elite user cannot "upgrade" to pro (downgrade) — shared plan_policy matrix.
    with TestClient(app) as client:
        user = _verified_user(client, plan="elite")
    patches = _patch_checkout_config()
    for p in patches:
        p.start()
    try:
        with TestClient(app) as client:
            _make_user(client, plan="elite", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "pro"})
    finally:
        for p in patches:
            p.stop()
    assert r.status_code == 400


def test_create_checkout_unverified_email_returns_403():
    with TestClient(app) as client:
        user = _make_user(client, plan="free")  # NOT email-verified
    patches = _patch_checkout_config()
    for p in patches:
        p.start()
    try:
        with TestClient(app) as client:
            _make_user(client, plan="free", existing_user=user)
            r = client.post("/api/paddle/create-checkout", json={"plan": "pro"})
    finally:
        for p in patches:
            p.stop()
    assert r.status_code == 403


def test_create_checkout_unauthenticated_returns_401():
    with TestClient(app) as client:
        r = client.post("/api/paddle/create-checkout", json={"plan": "pro"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# webhook
# ---------------------------------------------------------------------------

def test_webhook_no_secret_returns_503():
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", ""):
        with TestClient(app) as client:
            r = client.post(
                "/api/paddle/webhook",
                content=b'{"event_type":"transaction.completed","event_id":"evt_x"}',
                headers={"Paddle-Signature": "ts=1;h1=abc"},
            )
    assert r.status_code == 503


def test_webhook_invalid_signature_returns_400():
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", "wh_secret"):
        with TestClient(app) as client:
            r = client.post(
                "/api/paddle/webhook",
                content=b'{"event_type":"transaction.completed","event_id":"evt_x"}',
                headers={"Paddle-Signature": "ts=1700000000;h1=deadbeef"},
            )
    assert r.status_code == 400


def test_webhook_malformed_signature_header_returns_400():
    secret = "wh_secret"
    body = b'{"event_type":"transaction.completed","event_id":"evt_x"}'
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post(
                "/api/paddle/webhook",
                content=body,
                headers={"Paddle-Signature": "garbage-without-ts-or-h1"},
            )
    assert r.status_code == 400


def test_webhook_valid_signature_unknown_event_returns_200_ignored():
    secret = "wh_secret2"
    body = json.dumps({"event_id": f"evt_{uuid.uuid4().hex}", "event_type": "address.created", "data": {}}).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


def test_webhook_transaction_completed_grants_plan_and_records_provider():
    secret = "wh_secret3"
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]
    raw_event_id = f"evt_{uuid.uuid4().hex}"
    body = json.dumps({
        "event_id": raw_event_id,
        "event_type": "transaction.completed",
        "data": {"id": "txn_1", "custom_data": {"user_id": str(user_id), "target_plan": "lifetime_pro"}},
    }).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r.status_code == 200
    assert _user_plan(user_id) == "lifetime_pro"
    # Stored under the namespaced id with provider='paddle'.
    row = _payment_event(f"paddle:{raw_event_id}")
    assert row is not None, "expected a paddle:-prefixed payment_events row"
    assert row[1] == "paddle"
    assert row[2] == "transaction.completed"


def test_webhook_subscription_activated_grants_plan():
    secret = "wh_secret4"
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]
    body = json.dumps({
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "subscription.activated",
        "data": {"id": "sub_1", "custom_data": {"user_id": str(user_id), "target_plan": "pro"}},
    }).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r.status_code == 200
    assert _user_plan(user_id) == "pro"


def test_webhook_subscription_canceled_downgrades_non_lifetime():
    secret = "wh_secret5"
    with TestClient(app) as client:
        user = _make_user(client, plan="pro")
    user_id = user["id"]
    body = json.dumps({
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "subscription.canceled",
        "data": {"id": "sub_2", "custom_data": {"user_id": str(user_id)}},
    }).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r.status_code == 200
    assert _user_plan(user_id) == "free"


def test_webhook_subscription_canceled_ignores_lifetime_user():
    secret = "wh_secret6"
    with TestClient(app) as client:
        user = _make_user(client, plan="lifetime_pro")
    user_id = user["id"]
    body = json.dumps({
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "subscription.canceled",
        "data": {"id": "sub_3", "custom_data": {"user_id": str(user_id)}},
    }).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r.status_code == 200
    assert _user_plan(user_id) == "lifetime_pro"


def test_webhook_idempotent_duplicate_event():
    secret = "wh_secret7"
    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]
    body = json.dumps({
        "event_id": f"evt_{uuid.uuid4().hex}",
        "event_type": "transaction.completed",
        "data": {"id": "txn_idem", "custom_data": {"user_id": str(user_id), "target_plan": "pro"}},
    }).encode()
    sig = _paddle_sig(secret, body)
    with patch("routers.paddle.PADDLE_WEBHOOK_SECRET", secret):
        with TestClient(app) as client:
            r1 = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
            r2 = client.post("/api/paddle/webhook", content=body, headers={"Paddle-Signature": sig})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json() == {"status": "already processed"}


def test_paddle_and_razorpay_event_ids_do_not_collide():
    """The dual-rail safety property: identical raw ids on the two rails coexist."""
    paddle_secret = "wh_paddle_collide"
    rzp_secret = "wh_rzp_collide"
    shared_id = f"evt_{uuid.uuid4().hex}"

    with TestClient(app) as client:
        user = _make_user(client, plan="free")
    user_id = user["id"]

    # Razorpay event with id == shared_id (payment.captured grants lifetime_pro)
    rzp_body = json.dumps({
        "id": shared_id,
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_c", "notes": {"user_id": str(user_id), "target_plan": "lifetime_pro"}}}},
    }).encode()
    rzp_sig = _hmac.new(rzp_secret.encode(), rzp_body, hashlib.sha256).hexdigest()

    # Paddle event with event_id == shared_id (downgrade-neutral: grants pro on a
    # fresh user would conflict with lifetime; use a no-op-safe unknown-user grant
    # by reusing the same user — apply_plan_change is a no-op once on lifetime_pro,
    # so we instead assert both events are RECORDED, which is the collision test).
    pad_body = json.dumps({
        "event_id": shared_id,
        "event_type": "transaction.completed",
        "data": {"id": "txn_c", "custom_data": {"user_id": str(user_id), "target_plan": "lifetime_pro"}},
    }).encode()
    pad_sig = _paddle_sig(paddle_secret, pad_body)

    with patch("routers.razorpay.RAZORPAY_WEBHOOK_SECRET", rzp_secret), \
         patch("routers.paddle.PADDLE_WEBHOOK_SECRET", paddle_secret):
        with TestClient(app) as client:
            r_rzp = client.post("/api/razorpay/webhook", content=rzp_body, headers={"X-Razorpay-Signature": rzp_sig})
            r_pad = client.post("/api/paddle/webhook", content=pad_body, headers={"Paddle-Signature": pad_sig})

    assert r_rzp.status_code == 200
    assert r_pad.status_code == 200
    # Neither was treated as a replay of the other → two distinct rows recorded.
    assert _payment_event(shared_id) is not None              # razorpay (unprefixed)
    assert _payment_event(f"paddle:{shared_id}") is not None   # paddle (prefixed)
    assert _payment_event(shared_id)[1] == "razorpay"
    assert _payment_event(f"paddle:{shared_id}")[1] == "paddle"
