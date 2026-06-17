"""Account management endpoints — subscription, billing, plan switching."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import (
    RAZORPAY_KEY_ID,
    RAZORPAY_KEY_SECRET,
    RAZORPAY_PLAN_PRO,
    RAZORPAY_PLAN_ELITE,
)
from db import clear_user_subscription_id, delete_user_account, record_plan_change, set_user_plan, update_user_name  # noqa: F401
from deps import clear_session_cookie, require_authenticated_user

try:
    import razorpay
except ImportError:
    razorpay = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/account", tags=["account"])

LIFETIME_PLANS = {"lifetime_pro", "lifetime_elite"}
SUBSCRIPTION_PLANS = {"pro", "elite"}

# Higher number = higher tier
PLAN_HIERARCHY: dict[str, int] = {"pro": 1, "elite": 2}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_razorpay_client() -> Any:
    if razorpay is None:
        raise HTTPException(status_code=503, detail="Razorpay SDK is not installed.")
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Razorpay is not configured.")
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def _plan_id_for(plan: str) -> str | None:
    return {
        "pro": RAZORPAY_PLAN_PRO,
        "elite": RAZORPAY_PLAN_ELITE,
    }.get(plan)


def _is_cancelled_at_cycle_end(sub: dict[str, Any]) -> bool:
    """True if the subscription is scheduled for cancellation at cycle end
    but the paid period has not yet expired.

    Razorpay behaviour:
    - cancel_at_cycle_end=1 on an active subscription: user requested cancellation;
      billing stops at cycle end but access continues until current_end.
    - status='cancelled' with current_end in the future: subscription moved to
      cancelled state but the paid period hasn't elapsed yet.

    NOTE: end_at is NOT a cancellation signal — Razorpay sets it on every
    subscription that has total_count, reflecting the outer lifecycle boundary.
    Only cancel_at_cycle_end=1 indicates a user-initiated pending cancellation.
    """
    now = time.time()
    status = sub.get("status", "")

    # Active subscription with an explicit cycle-end cancellation requested
    if status == "active" and sub.get("cancel_at_cycle_end") == 1:
        return True

    # Already moved to cancelled but current period not yet expired
    if status == "cancelled":
        current_end = sub.get("current_end") or 0
        if current_end > now:
            return True

    return False


def _normalize_invoice_status(status: str) -> str:
    if status in {"paid", "captured"}:
        return "paid"
    if status in {"failed", "attempted", "unpaid"}:
        return "failed"
    if status in {"draft", "issued", "pending"}:
        return "pending"
    return status or "unknown"


# ---------------------------------------------------------------------------
# GET /api/account/billing
# ---------------------------------------------------------------------------

@router.get("/billing")
async def get_billing(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Return plan info, billing cycle dates, and the last 10 invoices.

    Free plan  → { plan, is_subscription: false, is_lifetime: false, invoices: [] }
    Lifetime   → { plan, is_subscription: false, is_lifetime: true,  invoices: [] }
    Subscription → full billing info fetched live from Razorpay.
    """
    plan = current_user.get("plan", "free")

    _base: dict[str, Any] = {
        "plan": plan,
        "is_subscription": False,
        "is_lifetime": False,
        "subscription_status": None,
        "cancelled_at_cycle_end": False,
        "billing_cycle_start": None,
        "billing_cycle_end": None,
        "charge_at": None,
        "plan_amounts": None,
        "plan_currency": "INR",
        "invoices": [],
    }

    if plan == "free":
        return _base

    if plan in LIFETIME_PLANS:
        return {**_base, "is_lifetime": True}

    # Monthly subscription (pro / elite)
    _base["is_subscription"] = True
    subscription_id = current_user.get("razorpay_subscription_id")

    if not subscription_id or not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        _base["subscription_status"] = "unknown"
        return _base

    client = _require_razorpay_client()

    # --- Subscription details ---
    def _fetch_sub() -> Any:
        return client.subscription.fetch(subscription_id)

    try:
        sub = await run_in_threadpool(_fetch_sub)
    except Exception:
        logger.exception("[billing] failed to fetch subscription %s", subscription_id)
        raise HTTPException(status_code=502, detail="Could not retrieve subscription details.")

    cancelled_at_cycle = _is_cancelled_at_cycle_end(sub)
    _base.update(
        subscription_status=sub.get("status", ""),
        cancelled_at_cycle_end=cancelled_at_cycle,
        billing_cycle_start=sub.get("current_start"),
        billing_cycle_end=sub.get("current_end"),
        charge_at=sub.get("charge_at") if not cancelled_at_cycle else None,
    )

    # --- Plan prices (best-effort, for switcher UI) ---
    plan_amounts: dict[str, int | None] = {"pro": None, "elite": None}
    plan_currency = "INR"

    for plan_key, plan_id in [("pro", RAZORPAY_PLAN_PRO), ("elite", RAZORPAY_PLAN_ELITE)]:
        if not plan_id:
            continue

        def _fetch_plan(pid: str = plan_id) -> Any:
            return client.plan.fetch(pid)

        try:
            plan_obj = await run_in_threadpool(_fetch_plan)
            item = plan_obj.get("item") or {}
            amount = item.get("unit_amount") or item.get("amount")
            if amount:
                plan_amounts[plan_key] = int(amount)
            plan_currency = item.get("currency", "INR")
        except Exception:
            pass  # Non-fatal; frontend falls back to generic price display

    _base.update(plan_amounts=plan_amounts, plan_currency=plan_currency)

    # --- Invoices (best-effort; falls back to payment list) ---
    invoices: list[dict[str, Any]] = []

    def _fetch_invoices() -> Any:
        return client.invoice.all(
            {"type": "invoice", "subscription_id": subscription_id, "count": 10}
        )

    try:
        inv_resp = await run_in_threadpool(_fetch_invoices)
        items = inv_resp.get("items", []) if isinstance(inv_resp, dict) else []
        for inv in items:
            invoices.append(
                {
                    "id": inv.get("id"),
                    "amount": inv.get("amount") or inv.get("gross_amount") or 0,
                    "currency": inv.get("currency", plan_currency),
                    "status": _normalize_invoice_status(inv.get("status", "")),
                    "date": inv.get("date") or inv.get("created_at") or 0,
                    "pdf_url": inv.get("short_url"),
                }
            )
    except Exception:
        def _fetch_payments() -> Any:
            return client.payment.all(
                {"subscription_id": subscription_id, "count": 10}
            )

        try:
            pmt_resp = await run_in_threadpool(_fetch_payments)
            items = pmt_resp.get("items", []) if isinstance(pmt_resp, dict) else []
            for pmt in items:
                invoices.append(
                    {
                        "id": pmt.get("id"),
                        "amount": pmt.get("amount", 0),
                        "currency": pmt.get("currency", plan_currency),
                        "status": "paid" if pmt.get("status") == "captured" else "failed",
                        "date": pmt.get("created_at", 0),
                        "pdf_url": None,
                    }
                )
        except Exception:
            pass  # invoices remain []; non-fatal

    _base["invoices"] = invoices
    return _base


# ---------------------------------------------------------------------------
# PATCH /api/account/profile
# ---------------------------------------------------------------------------

class ProfileUpdateRequest(BaseModel):
    name: str


@router.patch("/profile")
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Update the authenticated user's display name."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    if len(name) > 120:
        raise HTTPException(status_code=400, detail="Name must be 120 characters or fewer.")

    await update_user_name(current_user["id"], name)
    return {"ok": True, "name": name}


# ---------------------------------------------------------------------------
# POST /api/account/cancel-subscription
# ---------------------------------------------------------------------------

@router.post("/cancel-subscription")
async def cancel_subscription(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Cancel the user's active monthly subscription at the end of the billing cycle.

    Does NOT downgrade the plan immediately — the subscription.cancelled webhook does that.
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
    if _is_cancelled_at_cycle_end(sub):
        raise HTTPException(
            status_code=400,
            detail="This subscription is already scheduled to cancel at the cycle end.",
        )

    def _cancel() -> Any:
        return client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 1})

    try:
        cancelled_sub = await run_in_threadpool(_cancel)
    except Exception:
        logger.exception("[cancel-subscription] Razorpay cancel failed sub=%s", subscription_id)
        raise HTTPException(
            status_code=502, detail="Failed to cancel subscription with payment provider."
        )

    cancel_at = cancelled_sub.get("current_end") or cancelled_sub.get("charge_at")
    logger.info(
        "[cancel-subscription] user_id=%s sub_id=%s cancel_at=%s",
        current_user["id"],
        subscription_id,
        cancel_at,
    )
    return {"cancel_at": cancel_at}


# ---------------------------------------------------------------------------
# POST /api/account/switch-plan
# ---------------------------------------------------------------------------

class SwitchPlanRequest(BaseModel):
    target_plan: str
    timing: str = "cycle_end"


@router.post("/switch-plan")
async def switch_plan(
    body: SwitchPlanRequest,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Switch between Pro and Elite on the existing subscription.

    Downgrade (Elite → Pro): always cycle_end; returns 400 if timing='now'.
    Upgrade   (Pro → Elite): honours timing='now' or 'cycle_end'.

    timing='now': the change takes effect at Razorpay immediately, so we apply the
    new plan to the DB here too (instant entitlement). timing='cycle_end' (all
    downgrades + scheduled upgrades): the DB is NOT changed now — the webhook
    applies it at the next charge, resolving the plan from the subscription's
    updated plan_id (not the frozen notes.target_plan). See
    docs/features/pricing.md § Switching plans.
    """
    plan = current_user.get("plan", "free")

    if plan in LIFETIME_PLANS:
        raise HTTPException(status_code=400, detail="Lifetime plans cannot be switched.")
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="You do not have an active subscription.")
    if body.target_plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail=f"Invalid target plan: {body.target_plan!r}.")
    if body.target_plan == plan:
        raise HTTPException(status_code=400, detail="You are already on this plan.")

    new_plan_id = _plan_id_for(body.target_plan)
    if not new_plan_id:
        raise HTTPException(
            status_code=503, detail="Target plan is not configured. Please contact support."
        )

    current_rank = PLAN_HIERARCHY.get(plan, 0)
    target_rank = PLAN_HIERARCHY.get(body.target_plan, 0)
    is_upgrade = target_rank > current_rank

    if not is_upgrade and body.timing == "now":
        raise HTTPException(
            status_code=400,
            detail="Downgrades are always applied at the end of the current billing cycle.",
        )

    timing = body.timing if is_upgrade else "cycle_end"

    subscription_id = current_user.get("razorpay_subscription_id")
    if not subscription_id:
        raise HTTPException(
            status_code=400, detail="No subscription on record. Please contact support."
        )

    client = _require_razorpay_client()

    def _do_update() -> Any:
        return client.subscription.update(
            subscription_id,
            {
                "plan_id": new_plan_id,
                "quantity": 1,
                "schedule_change_at": timing,
            },
        )

    try:
        updated_sub = await run_in_threadpool(_do_update)
    except Exception:
        logger.exception("[switch-plan] Razorpay update failed sub=%s", subscription_id)
        raise HTTPException(
            status_code=502, detail="Failed to update subscription with payment provider."
        )

    if timing == "now":
        # Applies at Razorpay immediately → reflect the new entitlement in our DB
        # now (instant access) instead of waiting for the subscription.charged
        # webhook. target_plan != plan is already validated above, and this is an
        # upgrade (timing='now' is rejected for downgrades), so it is a real change.
        await set_user_plan(current_user["id"], body.target_plan)
        await record_plan_change(
            current_user["id"], plan, body.target_plan, context="razorpay-switch-now",
        )
        effective_at = updated_sub.get("charge_at") or updated_sub.get("current_start")
    else:
        # cycle_end: NOT applied now. The webhook applies it at the next charge
        # from the subscription's updated plan_id (see razorpay.py webhook).
        effective_at = (
            updated_sub.get("change_scheduled_at") or updated_sub.get("current_end")
        )

    logger.info(
        "[switch-plan] user=%s %s→%s timing=%s effective_at=%s",
        current_user["id"],
        plan,
        body.target_plan,
        timing,
        effective_at,
    )
    return {"effective_at": effective_at, "timing": timing}


# ---------------------------------------------------------------------------
# POST /api/account/update-payment-method
# ---------------------------------------------------------------------------

@router.post("/update-payment-method")
async def update_payment_method(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Return a Razorpay-hosted URL where the subscriber can update their payment method.

    Razorpay subscriptions expose a `short_url` field that opens the checkout/payment
    management page.  We return this as `redirect_url` for the frontend to open in a
    new tab.
    """
    plan = current_user.get("plan", "free")

    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(
            status_code=400,
            detail="Payment method updates only apply to active monthly subscriptions.",
        )

    subscription_id = current_user.get("razorpay_subscription_id")
    if not subscription_id:
        raise HTTPException(
            status_code=400, detail="No subscription on record. Please contact support."
        )

    client = _require_razorpay_client()

    def _fetch() -> Any:
        return client.subscription.fetch(subscription_id)

    try:
        sub = await run_in_threadpool(_fetch)
    except Exception:
        logger.exception("[update-payment-method] fetch failed sub=%s", subscription_id)
        raise HTTPException(status_code=502, detail="Could not retrieve subscription details.")

    redirect_url = sub.get("short_url")
    if not redirect_url:
        raise HTTPException(
            status_code=400,
            detail="No managed payment URL available for this subscription. Please contact support.",
        )

    return {"redirect_url": redirect_url}


# ---------------------------------------------------------------------------
# POST /api/account/reactivate-subscription
# ---------------------------------------------------------------------------

@router.post("/reactivate-subscription")
async def reactivate_subscription(
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> dict[str, Any]:
    """Un-schedule a pending cycle-end cancellation.

    Only valid when the subscription is in 'cancelled_at_cycle_end' state
    (cancel was requested but the billing period hasn't ended yet).

    Calls the Razorpay cancel endpoint with cancel_at_cycle_end=false which,
    on a subscription that is pending cancellation (not yet expired), removes
    the scheduled cancellation and keeps the subscription active.
    """
    plan = current_user.get("plan", "free")

    if plan in LIFETIME_PLANS:
        raise HTTPException(status_code=400, detail="Lifetime plans do not require reactivation.")
    if plan not in SUBSCRIPTION_PLANS:
        raise HTTPException(status_code=400, detail="You do not have a subscription to reactivate.")

    subscription_id = current_user.get("razorpay_subscription_id")
    if not subscription_id:
        raise HTTPException(
            status_code=400, detail="No subscription on record. Please contact support."
        )

    client = _require_razorpay_client()

    def _fetch() -> Any:
        return client.subscription.fetch(subscription_id)

    try:
        sub = await run_in_threadpool(_fetch)
    except Exception:
        logger.exception("[reactivate] fetch failed sub=%s", subscription_id)
        raise HTTPException(status_code=502, detail="Could not retrieve subscription details.")

    if not _is_cancelled_at_cycle_end(sub):
        raise HTTPException(
            status_code=400,
            detail="This subscription is not pending cancellation.",
        )

    # Per spec: cancel_at_cycle_end=false on a pending-cancellation subscription
    # removes the scheduled end and keeps it running.
    def _reactivate() -> Any:
        return client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 0})

    try:
        await run_in_threadpool(_reactivate)
    except Exception:
        logger.exception("[reactivate] Razorpay call failed sub=%s", subscription_id)
        raise HTTPException(
            status_code=502, detail="Failed to reactivate subscription with payment provider."
        )

    logger.info("[reactivate] user=%s sub=%s reactivated", current_user["id"], subscription_id)
    return {"reactivated": True}


# ---------------------------------------------------------------------------
# DELETE /api/account/delete
# ---------------------------------------------------------------------------

@router.delete("/delete", status_code=204)
async def delete_account(
    request: Request,
    current_user: dict[str, Any] = Depends(require_authenticated_user),
) -> Response:
    """Permanently delete the authenticated user's account and all associated data.

    Steps:
    1. Cancel any active Razorpay subscription immediately (best-effort).
    2. Run a single DB transaction: remove plan_changes, anonymise payment_events,
       then delete the user row (CASCADE handles everything else).
    3. Clear the session cookie.
    """
    user_id: str = current_user["id"]
    plan: str = current_user.get("plan", "free")
    subscription_id: str | None = current_user.get("razorpay_subscription_id")

    # Step 1 — cancel active Razorpay subscription (best-effort; never blocks deletion)
    if plan in SUBSCRIPTION_PLANS and subscription_id and RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            client = _require_razorpay_client()

            def _cancel_now() -> Any:
                return client.subscription.cancel(subscription_id, {"cancel_at_cycle_end": 0})

            await run_in_threadpool(_cancel_now)
            logger.info("[delete-account] cancelled subscription sub=%s user=%s", subscription_id, user_id)
        except Exception:
            logger.exception(
                "[delete-account] Razorpay cancellation failed sub=%s user=%s — proceeding with deletion",
                subscription_id,
                user_id,
            )

    # Step 2 — delete from DB in a single transaction
    await delete_user_account(user_id)
    logger.info("[delete-account] user deleted user_id=%s", user_id)

    # Step 3 — clear session cookie
    payload: Response = JSONResponse(status_code=204, content=None)
    clear_session_cookie(payload)
    return payload
