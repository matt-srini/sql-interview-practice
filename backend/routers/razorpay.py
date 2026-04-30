from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from config import (
    RAZORPAY_AMOUNT_LIFETIME_ELITE,
    RAZORPAY_AMOUNT_LIFETIME_PRO,
    RAZORPAY_AMOUNT_LIFETIME_ELITE_USD,
    RAZORPAY_AMOUNT_LIFETIME_PRO_USD,
    RAZORPAY_CURRENCY,
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    RAZORPAY_PLAN_ELITE,
    RAZORPAY_PLAN_PRO,
    RAZORPAY_PLAN_ELITE_USD,
    RAZORPAY_PLAN_PRO_USD,
    RAZORPAY_WEBHOOK_SECRET,
)
from db import (
    get_user_by_id,
    get_user_by_razorpay_customer_id,
    is_event_processed,
    record_payment_event,
    record_plan_change,
    set_user_plan,
    set_user_razorpay_customer_id,
)
from deps import get_current_user
from models import (
    CreateOrderRequest,
    CreateOrderResponse,
    VerifyPaymentRequest,
    VerifyPaymentResponse,
)

try:
    import razorpay
except ImportError:
    razorpay = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/razorpay", tags=["razorpay"])


LIFETIME_PLANS = {"lifetime_pro", "lifetime_elite"}
SUBSCRIPTION_PLANS = {"pro", "elite"}
ALL_PAID_PLANS = LIFETIME_PLANS | SUBSCRIPTION_PLANS


def _plan_ids() -> dict[str, str | None]:
    """Lazy lookup so tests that monkeypatch config are picked up."""
    return {
        "pro":   RAZORPAY_PLAN_PRO,
        "elite": RAZORPAY_PLAN_ELITE,
    }


def _plan_ids_usd() -> dict[str, str | None]:
    return {
        "pro":   RAZORPAY_PLAN_PRO_USD,
        "elite": RAZORPAY_PLAN_ELITE_USD,
    }


def _lifetime_amounts() -> dict[str, int]:
    return {
        "lifetime_pro":   RAZORPAY_AMOUNT_LIFETIME_PRO,
        "lifetime_elite": RAZORPAY_AMOUNT_LIFETIME_ELITE,
    }


def _require_razorpay_client() -> Any:
    if razorpay is None:
        raise HTTPException(status_code=503, detail="Razorpay SDK is not installed.")
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay is not configured for checkout.")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _target_plan_is_allowed(current_plan: str, target_plan: str) -> bool:
    allowed_targets: dict[str, set[str]] = {
        "free":           {"pro", "elite", "lifetime_pro", "lifetime_elite"},
        "pro":            {"elite", "lifetime_pro", "lifetime_elite"},
        "lifetime_pro":   {"elite", "lifetime_elite"},
        "elite":          {"lifetime_elite"},
        "lifetime_elite": set(),
    }
    return target_plan in allowed_targets.get(current_plan, set())


def _normalized_uuid_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


async def _ensure_customer_id(user: dict[str, Any], client: Any) -> str:
    existing = user.get("razorpay_customer_id")
    if existing:
        return str(existing)

    # Razorpay rejects duplicate customers on the same email with an error —
    # we catch it and fall back to finding the existing one via their list API.
    def _create() -> Any:
        try:
            return client.customer.create({
                "email": user["email"],
                "name": user.get("name") or user["email"],
                "fail_existing": "0",
                "notes": {"user_id": str(user["id"])},
            })
        except Exception:
            logger.exception("[razorpay] customer create failed")
            raise

    created = await run_in_threadpool(_create)
    customer_id = str(created["id"])

    updated_user = await set_user_razorpay_customer_id(user["id"], customer_id)
    if updated_user is None or not updated_user.get("razorpay_customer_id"):
        raise HTTPException(status_code=500, detail="Unable to persist Razorpay customer.")
    return str(updated_user["razorpay_customer_id"])


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


def _verify_payment_signature(req: VerifyPaymentRequest) -> bool:
    """HMAC-SHA256 verification of Razorpay's payment callback signature.

    Per Razorpay docs the signed body depends on flow:
      - Order (one-time)    : f"{order_id}|{payment_id}"
      - Subscription        : f"{payment_id}|{subscription_id}"
    """
    if not RAZORPAY_KEY_SECRET:
        return False

    if req.razorpay_order_id and req.razorpay_subscription_id:
        return False  # ambiguous — only one should be set

    if req.razorpay_order_id:
        body = f"{req.razorpay_order_id}|{req.razorpay_payment_id}"
    elif req.razorpay_subscription_id:
        body = f"{req.razorpay_payment_id}|{req.razorpay_subscription_id}"
    else:
        return False

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, req.razorpay_signature)


def _verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    if not RAZORPAY_WEBHOOK_SECRET or not signature:
        return False
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# Endpoint 0: ensure-customer  (pre-warm — call in background when pricing renders)
# ---------------------------------------------------------------------------

@router.post("/ensure-customer")
async def ensure_customer(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, bool]:
    """Pre-create the Razorpay customer so create-order only needs one API call."""
    if not current_user.get("email"):
        return {"ok": False}
    if current_user.get("razorpay_customer_id"):
        return {"ok": True}
    try:
        client = _require_razorpay_client()
        await _ensure_customer_id(current_user, client)
    except HTTPException:
        pass
    return {"ok": True}


# ---------------------------------------------------------------------------
# Endpoint 1: create-order
# ---------------------------------------------------------------------------

@router.post("/create-order", response_model=CreateOrderResponse)
async def create_order(
    body: CreateOrderRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CreateOrderResponse:
    if current_user.get("email") is None:
        raise HTTPException(status_code=403, detail="Create an account before upgrading.")

    if not current_user.get("email_verified"):
        raise HTTPException(status_code=403, detail="Please verify your email address before upgrading.")

    if body.plan not in ALL_PAID_PLANS:
        raise HTTPException(status_code=400, detail="Invalid upgrade plan.")

    if body.currency not in {"INR", "USD"}:
        raise HTTPException(status_code=400, detail="Unsupported currency. Must be INR or USD.")

    requested_currency = body.currency

    if not _target_plan_is_allowed(current_user["plan"], body.plan):
        raise HTTPException(status_code=400, detail="This upgrade path is not available.")

    client = _require_razorpay_client()

    display_name = "datathink"
    email = current_user["email"]
    name = current_user.get("name") or email

    if body.plan in LIFETIME_PLANS:
        if requested_currency == "USD":
            amount = (
                RAZORPAY_AMOUNT_LIFETIME_PRO_USD
                if body.plan == "lifetime_pro"
                else RAZORPAY_AMOUNT_LIFETIME_ELITE_USD
            )
        else:
            amount = _lifetime_amounts()[body.plan]
        if not amount or amount <= 0:
            raise HTTPException(status_code=503, detail="Lifetime amount is not configured.")
        description = "datathink Lifetime Pro" if body.plan == "lifetime_pro" else "datathink Lifetime Elite"

        def _create_order() -> Any:
            return client.order.create({
                "amount": int(amount),
                "currency": requested_currency,
                "payment_capture": 1,
                "notes": {
                    "user_id": str(current_user["id"]),
                    "target_plan": body.plan,
                },
            })

        order = await run_in_threadpool(_create_order)
        return CreateOrderResponse(
            order_id=str(order["id"]),
            subscription_id=None,
            amount=int(amount),
            currency=requested_currency,
            key_id=str(RAZORPAY_KEY_ID),
            name=display_name,
            description=description,
            prefill_email=email,
            prefill_name=name,
            is_subscription=False,
        )

    # Recurring subscription (pro / elite)
    if requested_currency == "USD":
        plan_ids = _plan_ids_usd()
        plan_id = plan_ids.get(body.plan)
        if not plan_id:
            raise HTTPException(
                status_code=503,
                detail="International checkout not available yet.",
            )
    else:
        plan_ids = _plan_ids()
        plan_id = plan_ids.get(body.plan)
        if not plan_id:
            raise HTTPException(status_code=503, detail="Razorpay plan is not configured for this tier.")

    # Keep a customer object so we can look up the user from the webhook payload
    customer_id = await _ensure_customer_id(current_user, client)

    description = "datathink Pro (monthly)" if body.plan == "pro" else "datathink Elite (monthly)"

    def _create_subscription() -> Any:
        return client.subscription.create({
            "plan_id": plan_id,
            "customer_notify": 1,
            # total_count is mandatory per Razorpay API. 120 months ≈ a decade —
            # users can cancel any time; this is just a ceiling so the subscription
            # is not indefinite from Razorpay's POV.
            "total_count": 120,
            "customer_id": customer_id,
            "notes": {
                "user_id": str(current_user["id"]),
                "target_plan": body.plan,
            },
        })

    subscription = await run_in_threadpool(_create_subscription)

    # Subscription amount comes from the Plan in the Razorpay dashboard — we
    # don't know it here, but the checkout modal auto-resolves it from plan_id.
    # We still need to pass a sensible amount to the response so the modal can
    # render a price hint; 0 tells the client "modal-controlled".
    return CreateOrderResponse(
        order_id=None,
        subscription_id=str(subscription["id"]),
        amount=0,
        currency=requested_currency,
        key_id=str(RAZORPAY_KEY_ID),
        name=display_name,
        description=description,
        prefill_email=email,
        prefill_name=name,
        is_subscription=True,
    )


# ---------------------------------------------------------------------------
# Endpoint 2: verify-payment  (fast-path plan apply from client callback)
# ---------------------------------------------------------------------------

@router.post("/verify-payment", response_model=VerifyPaymentResponse)
async def verify_payment(
    body: VerifyPaymentRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> VerifyPaymentResponse:
    if body.plan not in ALL_PAID_PLANS:
        raise HTTPException(status_code=400, detail="Invalid plan.")

    if not _verify_payment_signature(body):
        raise HTTPException(status_code=400, detail="Invalid payment signature.")

    # Idempotency check runs before the upgrade-path check so a replayed
    # callback (same payment_id, user already upgraded) is a safe no-op
    # rather than a 400.
    synthetic_event_id = f"verify:{body.razorpay_payment_id}"
    if await is_event_processed(synthetic_event_id):
        fresh = await get_user_by_id(current_user["id"])
        return VerifyPaymentResponse(plan=str(fresh["plan"]) if fresh else current_user["plan"])

    if not _target_plan_is_allowed(current_user["plan"], body.plan):
        raise HTTPException(status_code=400, detail="This upgrade path is not available.")

    await _apply_plan_change(
        user=current_user,
        new_plan=body.plan,
        context="razorpay-verify-payment",
        payment_event_id=synthetic_event_id,
    )
    await record_payment_event(
        synthetic_event_id,
        "verify.payment",
        user_id=str(current_user["id"]),
        payload_summary={
            "type": "verify.payment",
            "user_id": str(current_user["id"]),
            "target_plan": body.plan,
            "payment_id": body.razorpay_payment_id,
            "order_id": body.razorpay_order_id,
            "subscription_id": body.razorpay_subscription_id,
        },
    )
    return VerifyPaymentResponse(plan=body.plan)


# ---------------------------------------------------------------------------
# Endpoint 3: webhook  (source of truth, lifecycle events)
# ---------------------------------------------------------------------------

async def _resolve_event_user(entity: dict[str, Any]) -> dict[str, Any] | None:
    notes = entity.get("notes") or {}
    user_id = _normalized_uuid_or_none(notes.get("user_id"))
    if user_id:
        return await get_user_by_id(str(user_id))

    customer_id = entity.get("customer_id")
    if customer_id:
        return await get_user_by_razorpay_customer_id(str(customer_id))

    return None


@router.post("/webhook")
async def razorpay_webhook(request: Request) -> dict[str, str]:
    if not RAZORPAY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay webhook secret is not configured.")

    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature") or ""
    if not _verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid Razorpay signature.")

    import json
    try:
        event = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from exc

    event_id = str(event.get("id") or event.get("event_id") or "")
    event_type = str(event.get("event") or "")
    if not event_id or not event_type:
        raise HTTPException(status_code=400, detail="Missing event id or type.")

    if await is_event_processed(event_id):
        return {"status": "already processed"}

    payload = event.get("payload") or {}

    # Razorpay groups entities under payload.<entity>.entity; we look at payment
    # first (always present for payment events) then subscription.
    payment_entity: dict[str, Any] = (payload.get("payment") or {}).get("entity") or {}
    subscription_entity: dict[str, Any] = (payload.get("subscription") or {}).get("entity") or {}
    # For subscription.* events the notes live on the subscription entity; for
    # payment.captured the notes usually live on the payment entity (set at
    # order/subscription creation and copied across by Razorpay).
    lookup_entity = subscription_entity or payment_entity

    resolved_user: dict[str, Any] | None = None
    handled = False

    if event_type in {"payment.captured", "subscription.activated", "subscription.charged"}:
        resolved_user = await _resolve_event_user(lookup_entity)
        notes = (lookup_entity.get("notes") or {})
        target_plan = notes.get("target_plan")
        if resolved_user and target_plan in ALL_PAID_PLANS:
            await _apply_plan_change(
                user=resolved_user,
                new_plan=str(target_plan),
                context=f"razorpay-{event_type}",
                payment_event_id=event_id,
            )
            handled = True

    elif event_type in {"subscription.cancelled", "subscription.halted"}:
        resolved_user = await _resolve_event_user(lookup_entity)
        if resolved_user:
            if resolved_user.get("plan") in LIFETIME_PLANS:
                # A lifetime purchase should never be revoked by a stray
                # subscription.cancelled (e.g. from a prior monthly that was
                # cancelled before the user switched to lifetime).
                logger.info(
                    "[razorpay-webhook] %s ignored — user is on a lifetime plan "
                    "user_id=%s plan=%s",
                    event_type,
                    resolved_user["id"],
                    resolved_user["plan"],
                )
            else:
                await _apply_plan_change(
                    user=resolved_user,
                    new_plan="free",
                    context=f"razorpay-{event_type}",
                    payment_event_id=event_id,
                )
                handled = True

    elif event_type == "payment.failed":
        resolved_user = await _resolve_event_user(lookup_entity)
        logger.warning(
            "[razorpay-webhook] payment.failed user_id=%s",
            None if resolved_user is None else resolved_user["id"],
        )
    else:
        logger.info("[razorpay-webhook] Ignoring event type=%s", event_type)

    payload_summary = {
        "type": event_type,
        "user_id": str(resolved_user["id"]) if resolved_user else None,
        "target_plan": (lookup_entity.get("notes") or {}).get("target_plan"),
        "payment_id": payment_entity.get("id"),
        "subscription_id": subscription_entity.get("id"),
    }

    await record_payment_event(
        event_id,
        event_type,
        user_id=str(resolved_user["id"]) if resolved_user else None,
        payload_summary=payload_summary,
    )
    return {"status": "processed" if handled else "ignored"}
