from __future__ import annotations

import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from config import STRIPE_PRICE_ELITE, STRIPE_PRICE_PRO, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from config import STRIPE_PRICE_LIFETIME_PRO, STRIPE_PRICE_LIFETIME_ELITE
from db import get_user_by_id, get_user_by_stripe_customer_id, is_event_processed, record_plan_change
from db import record_stripe_event, set_user_plan, set_user_stripe_customer_id
from deps import get_current_user
from models import CheckoutRequest, CheckoutResponse

try:
    import stripe
except ImportError:
    stripe = None


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

PRICE_IDS = {
    "pro":            STRIPE_PRICE_PRO,
    "elite":          STRIPE_PRICE_ELITE,
    "lifetime_pro":   STRIPE_PRICE_LIFETIME_PRO,
    "lifetime_elite": STRIPE_PRICE_LIFETIME_ELITE,
}

# Plans that use a one-time payment rather than a subscription
LIFETIME_PLANS = {"lifetime_pro", "lifetime_elite"}


def _require_stripe() -> Any:
    if stripe is None:
        raise HTTPException(status_code=503, detail="Stripe SDK is not installed.")
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured for checkout.")
    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def _target_plan_is_allowed(current_plan: str, target_plan: str) -> bool:
    allowed_targets: dict[str, set[str]] = {
        "free":           {"pro", "elite", "lifetime_pro", "lifetime_elite"},
        "pro":            {"elite", "lifetime_pro", "lifetime_elite"},
        "lifetime_pro":   {"elite", "lifetime_elite"},
        "elite":          {"lifetime_elite"},
        "lifetime_elite": set(),
    }
    return target_plan in allowed_targets.get(current_plan, set())


def _frontend_base_url(request: Request) -> str:
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        return referer.rstrip("/").split("/practice", 1)[0]
    return str(request.base_url).rstrip("/")


def _normalized_uuid_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


async def _ensure_customer_id(user: dict[str, Any], stripe_client: Any) -> str:
    existing_customer_id = user.get("stripe_customer_id")
    if existing_customer_id:
        return existing_customer_id

    customer = await run_in_threadpool(
        lambda: stripe_client.Customer.create(
            email=user["email"],
            metadata={"user_id": str(user["id"])},
        )
    )
    updated_user = await set_user_stripe_customer_id(user["id"], customer.id)
    if updated_user is None or not updated_user.get("stripe_customer_id"):
        raise HTTPException(status_code=500, detail="Unable to persist Stripe customer.")
    return str(updated_user["stripe_customer_id"])


async def _resolve_event_user(event_object: dict[str, Any]) -> dict[str, Any] | None:
    metadata = event_object.get("metadata") or {}
    user_id = _normalized_uuid_or_none(metadata.get("user_id"))
    if user_id:
        return await get_user_by_id(str(user_id))

    customer_id = event_object.get("customer")
    if customer_id:
        return await get_user_by_stripe_customer_id(str(customer_id))

    return None


async def _apply_plan_change(
    *,
    user: dict[str, Any],
    new_plan: str,
    context: str,
    stripe_event_id: str,
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
        stripe_event_id=stripe_event_id,
    )


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> CheckoutResponse:
    if current_user.get("email") is None:
        raise HTTPException(status_code=403, detail="Create an account before upgrading.")

    if body.plan not in PRICE_IDS:
        raise HTTPException(status_code=400, detail="Invalid upgrade plan.")

    if not _target_plan_is_allowed(current_user["plan"], body.plan):
        raise HTTPException(status_code=400, detail="This upgrade path is not available.")

    price_id = PRICE_IDS[body.plan]
    if not price_id:
        raise HTTPException(status_code=503, detail="Stripe price is not configured for this plan.")

    stripe_client = _require_stripe()
    customer_id = await _ensure_customer_id(current_user, stripe_client)
    frontend_base_url = _frontend_base_url(request)
    is_lifetime = body.plan in LIFETIME_PLANS
    checkout_kwargs: dict[str, Any] = dict(
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment" if is_lifetime else "subscription",
        success_url=f"{frontend_base_url}/practice?upgraded=true",
        cancel_url=f"{frontend_base_url}/practice",
        metadata={
            "user_id": str(current_user["id"]),
            "target_plan": body.plan,
        },
        client_reference_id=str(current_user["id"]),
    )
    session = await run_in_threadpool(
        lambda: stripe_client.checkout.Session.create(**checkout_kwargs)
    )
    return CheckoutResponse(checkout_url=str(session.url))


@router.post("/webhook")
async def stripe_webhook(request: Request) -> dict[str, str]:
    stripe_client = _require_stripe()
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe webhook secret is not configured.")

    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature.")

    try:
        event = await run_in_threadpool(
            lambda: stripe_client.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        )
    except Exception as exc:
        logger.warning("Invalid Stripe webhook signature: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.") from exc

    event_id = str(event["id"])
    event_type = str(event["type"])
    event_object = dict(event.get("data", {}).get("object", {}))

    if await is_event_processed(event_id):
        return {"status": "already processed"}

    payload_summary = {
        "type": event_type,
        "user_id": _normalized_uuid_or_none((event_object.get("metadata") or {}).get("user_id")),
        "target_plan": (event_object.get("metadata") or {}).get("target_plan"),
        "customer": event_object.get("customer"),
    }

    # resolved_user tracks the DB user found during event processing.  We use
    # their actual primary key (rather than the raw metadata UUID) as the FK
    # in stripe_events so we never write an orphaned user_id reference.
    resolved_user: dict[str, Any] | None = None

    if event_type == "checkout.session.completed":
        resolved_user = await _resolve_event_user(event_object)
        target_plan = (event_object.get("metadata") or {}).get("target_plan")
        if resolved_user and target_plan in {"pro", "elite", "lifetime_pro", "lifetime_elite"}:
            await _apply_plan_change(
                user=resolved_user,
                new_plan=str(target_plan),
                context="stripe-checkout",
                stripe_event_id=event_id,
            )
    elif event_type == "customer.subscription.deleted":
        resolved_user = await _resolve_event_user(event_object)
        if resolved_user:
            if resolved_user.get("plan") in {"lifetime_pro", "lifetime_elite"}:
                # Lifetime plans are one-time purchases — they have no subscription to
                # delete.  A stale subscription.deleted event (e.g. from a prior monthly
                # plan that was cancelled before the user switched to lifetime) must never
                # strip lifetime access.
                logger.info(
                    "[stripe-webhook] subscription.deleted ignored — user is on a lifetime plan "
                    "user_id=%s plan=%s",
                    resolved_user["id"],
                    resolved_user["plan"],
                )
            else:
                await _apply_plan_change(
                    user=resolved_user,
                    new_plan="free",
                    context="stripe-subscription-deleted",
                    stripe_event_id=event_id,
                )
    elif event_type == "invoice.payment_failed":
        resolved_user = await _resolve_event_user(event_object)
        logger.warning(
            "[stripe-webhook] invoice.payment_failed user_id=%s customer=%s",
            None if resolved_user is None else resolved_user["id"],
            event_object.get("customer"),
        )
    else:
        logger.info("[stripe-webhook] Ignoring event type=%s", event_type)

    await record_stripe_event(
        event_id,
        event_type,
        # Use the verified DB user id — never the raw metadata UUID, which may
        # reference a non-existent user and would violate the FK constraint.
        user_id=str(resolved_user["id"]) if resolved_user else None,
        payload_summary=payload_summary,
    )
    return {"status": "processed" if event_type in {"checkout.session.completed", "customer.subscription.deleted"} else "ignored"}
