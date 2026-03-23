"""
Plan management endpoints: plan change, profile, unlocks, Stripe integration.
"""
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from typing import Optional

from backend.models import UserProfile, PlanChangeRequest, PlanChangeResult, UnlockState, StripeSession
from backend.database import get_user_profile, set_user_profile, init_user_profile_storage

router = APIRouter()


STRIPE_SESSIONS = {}


@router.get("/api/user/profile", response_model=UserProfile)
def get_user_profile_route(user_id: str):
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    return UserProfile(**profile)


@router.put("/api/user/profile", response_model=UserProfile)
def update_user_profile(user_id: str, plan: str, metadata: Optional[dict] = None):
    if plan not in ("free", "pro", "elite"):
        raise HTTPException(status_code=400, detail="Invalid plan")
    set_user_profile(user_id, plan, metadata)
    profile = get_user_profile(user_id)
    return UserProfile(**profile)

@router.post("/api/user/plan", response_model=PlanChangeResult)

def change_plan(req: PlanChangeRequest):
    profile = get_user_profile(req.user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")
    old_plan = profile["plan"]
    valid_plans = ("free", "pro", "elite")
    if req.new_plan not in valid_plans:
        return PlanChangeResult(user_id=req.user_id, old_plan=old_plan, new_plan=old_plan, success=False, reason="Invalid plan")
    if req.new_plan == old_plan:
        return PlanChangeResult(user_id=req.user_id, old_plan=old_plan, new_plan=old_plan, success=True, reason="No change")

    # Plan transition validation
    allowed_transitions = {
        "free": {"pro", "elite"},
        "pro": {"elite", "free"},
        "elite": {"pro", "free"},
    }
    if req.new_plan not in allowed_transitions.get(old_plan, set()):
        return PlanChangeResult(user_id=req.user_id, old_plan=old_plan, new_plan=old_plan, success=False, reason="Transition not allowed")

    # Audit log (placeholder)
    import logging
    logging.info(f"[plan-change] user_id={req.user_id} {old_plan}->{req.new_plan}")

    # Unlock recompute trigger (placeholder)
    # In a real system, would trigger unlock recalculation here

    set_user_profile(req.user_id, req.new_plan, profile.get("metadata"))
    return PlanChangeResult(user_id=req.user_id, old_plan=old_plan, new_plan=req.new_plan, success=True)


# Stripe integration (stub)
import backend.progress as progress
import json
import os
import logging
import uuid
try:
    import stripe
except ImportError:
    stripe = None

def _load_questions_by_difficulty():
    base = os.path.join(os.path.dirname(__file__), "../content/questions")
    questions_by_diff = {}
    for diff in ("easy", "medium", "hard"):
        path = os.path.join(base, f"{diff}.json")
        with open(path, "r", encoding="utf-8") as f:
            questions_by_diff[diff] = json.load(f)
    return questions_by_diff


@router.get("/api/user/unlocks", response_model=UnlockState)
def get_unlock_state(user_id: str):
    profile = get_user_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="User not found")

    plan = profile["plan"]
    # Plan determines accessible difficulties
    if plan == "free":
        allowed = ["easy"]
    elif plan == "pro":
        allowed = ["easy", "medium"]
    elif plan == "elite":
        allowed = ["easy", "medium", "hard"]
    else:
        allowed = []

    questions_by_diff = _load_questions_by_difficulty()
    allowed_questions = {d: questions_by_diff[d] for d in allowed}
    solved_ids = progress.get_solved_question_ids(user_id)
    statuses = progress.compute_statuses(questions_by_difficulty=allowed_questions, solved_ids=solved_ids)

    unlocked_questions = [str(qid) for qid, st in statuses.items() if st.state == "unlocked"]
    solved_questions = [str(qid) for qid, st in statuses.items() if st.state == "solved"]
    access_map = {str(qid): st.state for qid, st in statuses.items()}

    return UnlockState(
        user_id=user_id,
        unlocked_questions=unlocked_questions,
        solved_questions=solved_questions,
        access_map=access_map,
    )

@router.post("/api/stripe/create-session", response_model=StripeSession)
def create_stripe_session(user_id: str, plan: str):
    # Simulate Stripe session creation
    if stripe is None:
        session_id = f"sess_{user_id}_{plan}_{uuid.uuid4().hex[:8]}"
        session = StripeSession(user_id=user_id, session_id=session_id, plan=plan, status="created")
        STRIPE_SESSIONS[session_id] = session
        return session
    # Real Stripe integration would go here
    # session = stripe.checkout.Session.create(...)
    # return StripeSession(...)
    session_id = f"sess_{user_id}_{plan}_{uuid.uuid4().hex[:8]}"
    session = StripeSession(user_id=user_id, session_id=session_id, plan=plan, status="created")
    STRIPE_SESSIONS[session_id] = session
    return session

@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    # Simulate Stripe webhook event
    payload = await request.body()
    event = None
    try:
        event = json.loads(payload)
    except Exception:
        return {"error": "Invalid payload"}

    # In real integration, validate signature and event type
    event_type = event.get("type")
    data = event.get("data", {})
    user_id = data.get("user_id")
    plan = data.get("plan")
    if event_type == "checkout.session.completed" and user_id and plan:
        # Ensure user profile exists before plan change
        profile = get_user_profile(user_id)
        if not profile:
            set_user_profile(user_id, plan, None)
        req = PlanChangeRequest(user_id=user_id, new_plan=plan, context="stripe")
        change_plan(req)
        logging.info(f"[stripe-webhook] Upgraded user {user_id} to {plan}")
        return {"status": "plan changed"}
    return {"status": "webhook received"}
