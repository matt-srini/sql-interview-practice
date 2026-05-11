"""Account management endpoints (subscription cancellation, etc.)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET
from db import clear_user_subscription_id
from deps import require_authenticated_user

try:
    import razorpay
except ImportError:
    razorpay = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/account", tags=["account"])

LIFETIME_PLANS = {"lifetime_pro", "lifetime_elite"}
SUBSCRIPTION_PLANS = {"pro", "elite"}


def _require_razorpay_client() -> Any:
    if razorpay is None:
        raise HTTPException(status_code=503, detail="Razorpay SDK is not installed.")
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay is not configured.")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Cancel the user's active monthly subscription at the end of the current billing cycle.

    - Returns 400 if the user is on a lifetime plan (nothing to cancel).
    - Returns 400 if the user is on the free plan (no active subscription).
    - Returns 400 if no subscription ID is on record (e.g. never activated via webhook).
    - Calls Razorpay with cancel_at_cycle_end=true so access continues until the period end.
    - Does NOT downgrade the plan immediately — the subscription.cancelled webhook does that.
    """
    plan = current_user.get("plan", "free")

    if plan in LIFETIME_PLANS:
        raise HTTPException(
            status_code=400,
            detail="Lifetime plans cannot be cancelled — they are a one-time purchase.",
        )

    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(
            status_code=400,
            detail="You do not have an active subscription to cancel.",
        )

    subscription_id = current_user.get("razorpay_subscription_id")
    if not subscription_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription on record. Please contact support.",
        )

    client = _require_razorpay_client()

    # Fetch current subscription state to check it isn't already cancelled.
    def _fetch() -> Any:
        return client.subscription.fetch(subscription_id)

    try:
        sub = await run_in_threadpool(_fetch)
    except Exception:
        logger.exception("[cancel-subscription] failed to fetch subscription %s", subscription_id)
        raise HTTPException(status_code=502, detail="Could not retrieve subscription details.")

    sub_status = sub.get("status", "")
    if sub_status in {"cancelled", "expired", "completed"}:
        raise HTTPException(
            status_code=400,
            detail="This subscription is already cancelled or expired.",
        )

    # Cancel at cycle end — access continues until current_end.
    def _cancel() -> Any:
        return client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 1})

    try:
        cancelled_sub = await run_in_threadpool(_cancel)
    except Exception:
        logger.exception("[cancel-subscription] Razorpay cancel failed for sub %s", subscription_id)
        raise HTTPException(status_code=502, detail="Failed to cancel subscription with payment provider.")

    # current_end is the Unix timestamp when the paid period ends.
    cancel_at = cancelled_sub.get("current_end") or cancelled_sub.get("charge_at")

    logger.info(
        "[cancel-subscription] user_id=%s sub_id=%s cancel_at=%s",
        current_user["id"],
        subscription_id,
        cancel_at,
    )

    return {"cancel_at": cancel_at}
