"""Paddle billing rail — Merchant of Record for non-INR (global) customers.

India checks out through Razorpay (`routers/razorpay.py`); the rest of the world
goes through Paddle, which is the **Merchant of Record**: it is the legal seller
to the end customer and collects + remits global VAT/GST/sales tax on our behalf.
We never see the customer's card or their local tax — Paddle pays us a net payout
and tells us, via signed webhooks, which user bought which plan.

Two endpoints:
  - POST /api/paddle/create-checkout — returns the config the client-side Paddle.js
    overlay needs (client token, environment, price id, custom_data). No server-side
    Paddle API call: the overlay is price-id driven, so there is no SDK dependency.
  - POST /api/paddle/webhook — the source of truth. Verifies Paddle's signature,
    dedupes on a "paddle:"-prefixed event id (collision-proof against Razorpay in
    the shared payment_events PK), and applies/revokes the plan.

Plan-upgrade policy is shared with Razorpay via plan_policy.py — both rails enforce
the identical upgrade-path matrix. Full contract: docs/features/pricing.md.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from config import (
    PADDLE_CLIENT_TOKEN,
    PADDLE_ENVIRONMENT,
    PADDLE_PRICE_ELITE,
    PADDLE_PRICE_LIFETIME_ELITE,
    PADDLE_PRICE_LIFETIME_PRO,
    PADDLE_PRICE_PRO,
    PADDLE_WEBHOOK_SECRET,
)
from db import (
    get_user_by_id,
    is_event_processed,
    record_payment_event,
    record_plan_change,
    set_user_plan,
)
from deps import require_authenticated_user
from models import PaddleCheckoutRequest, PaddleCheckoutResponse
from plan_policy import ALL_PAID_PLANS, LIFETIME_PLANS, SUBSCRIPTION_PLANS, target_plan_is_allowed
from sentry_utils import capture_payment_failure

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paddle", tags=["paddle"])

# Paddle event ids are namespaced with this prefix when stored in payment_events
# so they can never collide with a Razorpay id in the shared event_id PK column
# (Razorpay's own synthetic verify events use the "verify:" prefix — same idea).
_EVENT_PREFIX = "paddle:"

# Webhook event types that GRANT the target plan (idempotent — apply_plan_change
# is a no-op when the user is already on the plan, so re-delivery is harmless):
#   transaction.completed — fires for one-time (lifetime) buys AND each recurring
#                            subscription payment (incl. renewals).
#   subscription.activated — first activation of a recurring plan.
#   subscription.updated   — plan switch within Paddle while active.
_GRANT_EVENTS = {"transaction.completed", "subscription.activated", "subscription.updated"}
# Event types that REVOKE access (downgrade to free) — note Paddle's US spelling.
_REVOKE_EVENTS = {"subscription.canceled"}


def _price_ids() -> dict[str, str | None]:
    """Lazy lookup so tests that monkeypatch config are picked up."""
    return {
        "pro": PADDLE_PRICE_PRO,
        "elite": PADDLE_PRICE_ELITE,
        "lifetime_pro": PADDLE_PRICE_LIFETIME_PRO,
        "lifetime_elite": PADDLE_PRICE_LIFETIME_ELITE,
    }


def _plan_tier_for_price_id(price_id: str | None) -> str | None:
    """Reverse-map a Paddle price_id -> our plan tier. The subscription's CURRENT
    price_id is authoritative on a mid-cycle plan switch (`subscription.updated`),
    whereas `custom_data.target_plan` is frozen at checkout and would re-apply the
    original plan. Mirrors the Razorpay `_plan_tier_for_plan_id` fix. Returns None
    if the price_id isn't one we configured -> caller falls back to custom_data."""
    if not price_id:
        return None
    for tier, configured_id in _price_ids().items():
        if configured_id and configured_id == price_id:
            return tier
    return None


def _verify_paddle_signature(raw_body: bytes, signature_header: str) -> bool:
    """Verify Paddle Billing's `Paddle-Signature` header.

    Header form: ``ts=<unix_seconds>;h1=<hmac_sha256_hex>``. The signed payload is
    ``f"{ts}:{raw_body}"`` keyed with the notification-destination secret. Constant
    time compare, like the Razorpay webhook.
    """
    if not PADDLE_WEBHOOK_SECRET or not signature_header:
        return False
    parts: dict[str, str] = {}
    for segment in signature_header.split(";"):
        key, _, value = segment.partition("=")
        if key.strip():
            parts[key.strip()] = value.strip()
    ts = parts.get("ts")
    h1 = parts.get("h1")
    if not ts or not h1:
        return False
    signed_payload = ts.encode("utf-8") + b":" + raw_body
    expected = hmac.new(PADDLE_WEBHOOK_SECRET.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, h1)


async def _apply_plan_change(
    *,
    user: dict[str, Any],
    new_plan: str,
    context: str,
    payment_event_id: str,
) -> None:
    old_plan = user["plan"]
    if old_plan == new_plan:
        return
    updated = await set_user_plan(user["id"], new_plan)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    await record_plan_change(
        user["id"],
        old_plan,
        new_plan,
        context=context,
        payment_event_id=payment_event_id,
    )


# ---------------------------------------------------------------------------
# Endpoint 1: create-checkout  (returns Paddle.js overlay config)
# ---------------------------------------------------------------------------

@router.post("/create-checkout", response_model=PaddleCheckoutResponse)
async def create_checkout(
    body: PaddleCheckoutRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> PaddleCheckoutResponse:
    if not current_user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email address before upgrading.")

    if body.plan not in ALL_PAID_PLANS:
        raise HTTPException(status_code=400, detail="Invalid upgrade plan.")

    if not target_plan_is_allowed(current_user["plan"], body.plan):
        raise HTTPException(status_code=400, detail="This upgrade path is not available.")

    if not PADDLE_CLIENT_TOKEN:
        raise HTTPException(status_code=503, detail="International checkout is not configured yet.")

    price_id = _price_ids().get(body.plan)
    if not price_id:
        raise HTTPException(status_code=503, detail="International checkout is not configured for this tier.")

    return PaddleCheckoutResponse(
        client_token=str(PADDLE_CLIENT_TOKEN),
        environment=PADDLE_ENVIRONMENT,
        price_id=str(price_id),
        is_subscription=body.plan in SUBSCRIPTION_PLANS,
        customer_email=current_user.get("email"),
        custom_data={
            "user_id": str(current_user["id"]),
            "target_plan": body.plan,
        },
    )


# ---------------------------------------------------------------------------
# Endpoint 2: webhook  (source of truth, lifecycle events)
# ---------------------------------------------------------------------------

async def _resolve_event_user(data: dict[str, Any]) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve the (user, target_plan) from a Paddle entity's custom_data.

    custom_data is what we set at checkout (create-checkout above) and Paddle
    echoes it back verbatim on the transaction + subscription — the equivalent of
    Razorpay's `notes`.
    """
    custom_data = data.get("custom_data") or {}
    if not isinstance(custom_data, dict):
        return None, None
    user_id = custom_data.get("user_id")
    target_plan = custom_data.get("target_plan")
    if not user_id:
        return None, target_plan if target_plan in ALL_PAID_PLANS else None
    user = await get_user_by_id(str(user_id))
    return user, (target_plan if target_plan in ALL_PAID_PLANS else None)


@router.post("/webhook")
async def paddle_webhook(request: Request) -> dict[str, str]:
    if not PADDLE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Paddle webhook secret is not configured.")

    raw_body = await request.body()
    signature = request.headers.get("Paddle-Signature") or ""
    if not _verify_paddle_signature(raw_body, signature):
        capture_payment_failure(
            "Paddle webhook: invalid signature — possible spoofed delivery",
            stage="webhook_signature",
            provider="paddle",
            extra={"has_signature_header": bool(signature)},
        )
        raise HTTPException(status_code=400, detail="Invalid Paddle signature.")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        capture_payment_failure(
            "Paddle webhook: malformed JSON payload",
            stage="webhook_parse",
            provider="paddle",
            extra={"error": type(exc).__name__},
        )
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc

    raw_event_id = str(event.get("event_id") or "")
    event_type = str(event.get("event_type") or "")
    if not raw_event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing event id or type.")

    # Namespace before any dedup/storage so Paddle + Razorpay ids never collide.
    event_id = f"{_EVENT_PREFIX}{raw_event_id}"
    if await is_event_processed(event_id):
        return {"status": "already processed"}

    data: dict[str, Any] = event.get("data") or {}
    resolved_user, target_plan = await _resolve_event_user(data)
    # Prefer the subscription's CURRENT price_id (authoritative on a mid-cycle
    # plan switch); custom_data.target_plan is frozen at checkout and would
    # re-apply the original plan. Mirrors the Razorpay plan_id resolution fix.
    _items = data.get("items") or []
    _price_id = (_items[0].get("price") or {}).get("id") if _items and isinstance(_items[0], dict) else None
    _plan_from_price = _plan_tier_for_price_id(_price_id)
    if _plan_from_price:
        target_plan = _plan_from_price
    handled = False

    if event_type in _GRANT_EVENTS:
        if resolved_user and target_plan:
            try:
                await _apply_plan_change(
                    user=resolved_user,
                    new_plan=str(target_plan),
                    context=f"paddle-{event_type}",
                    payment_event_id=event_id,
                )
            except Exception as exc:
                capture_payment_failure(
                    "Paddle webhook: plan persistence failed after payment",
                    stage="plan_persist",
                    provider="paddle",
                    user_id=str(resolved_user["id"]),
                    extra={
                        "event_type": event_type,
                        "event_id": event_id,
                        "target_plan": target_plan,
                        "error": type(exc).__name__,
                    },
                )
                raise
            handled = True
        else:
            # Payment event arrived but we cannot resolve who to upgrade — this
            # means money was collected but entitlement was NOT applied.
            capture_payment_failure(
                "Paddle webhook: grant event received but user/plan unresolvable — entitlement NOT applied",
                stage="plan_resolution",
                provider="paddle",
                extra={
                    "event_type": event_type,
                    "event_id": event_id,
                    "resolved_user": bool(resolved_user),
                    "target_plan": target_plan,
                },
            )

    elif event_type in _REVOKE_EVENTS:
        if resolved_user:
            if resolved_user.get("plan") in LIFETIME_PLANS:
                # A lifetime purchase must never be revoked by a stray subscription
                # cancellation (e.g. from a prior monthly cancelled after switching
                # to lifetime) — mirrors the Razorpay webhook guard.
                logger.info(
                    "[paddle-webhook] %s ignored — user is on a lifetime plan user_id=%s plan=%s",
                    event_type, resolved_user["id"], resolved_user["plan"],
                )
            else:
                await _apply_plan_change(
                    user=resolved_user,
                    new_plan="free",
                    context=f"paddle-{event_type}",
                    payment_event_id=event_id,
                )
                handled = True
    else:
        logger.info("[paddle-webhook] Ignoring event type=%s", event_type)

    await record_payment_event(
        event_id,
        event_type,
        user_id=str(resolved_user["id"]) if resolved_user else None,
        provider="paddle",
        payload_summary={
            "type": event_type,
            "user_id": str(resolved_user["id"]) if resolved_user else None,
            "target_plan": target_plan,
            # Charge total (minor units) + currency — drives the rail-aware billing
            # history for Paddle subscribers (who have no Razorpay invoices).
            "amount": ((data.get("details") or {}).get("totals") or {}).get("grand_total"),
            "currency": data.get("currency_code"),
            "transaction_id": data.get("id") if event_type.startswith("transaction.") else data.get("transaction_id"),
            "subscription_id": data.get("subscription_id") or (data.get("id") if event_type.startswith("subscription.") else None),
        },
    )
    return {"status": "processed" if handled else "ignored"}
