"""Plan management endpoints: profile, plan changes, and unlock state."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from config import IS_PROD
from db import get_user_by_id, get_solved_ids, record_plan_change, set_user_plan
from deps import get_current_user
from models import PlanChangeRequest, PlanChangeResult, UnlockState, UserProfile
from questions import get_questions_by_difficulty
from unlock import compute_unlock_state

router = APIRouter()

logger = logging.getLogger(__name__)


async def _resolve_user(user_id: str | None, current_user: dict[str, Any]) -> dict[str, Any]:
    target_id = user_id or current_user["id"]
    user = await get_user_by_id(target_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/api/user/profile", response_model=UserProfile)
async def get_user_profile_route(
    user_id: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserProfile:
    user = await _resolve_user(user_id, current_user)
    return UserProfile(**user)


@router.put("/api/user/profile", response_model=UserProfile)
async def update_user_profile(
    plan: str,
    user_id: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UserProfile:
    if IS_PROD:
        raise HTTPException(status_code=403, detail="Direct plan changes disabled in production.")
    if plan not in ("free", "pro", "elite"):
        raise HTTPException(status_code=400, detail="Invalid plan")

    target = await _resolve_user(user_id, current_user)
    updated = await set_user_plan(target["id"], plan)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    if updated["plan"] != target["plan"]:
        await record_plan_change(target["id"], target["plan"], updated["plan"], context="profile-update")
    return UserProfile(**updated)


@router.post("/api/user/plan", response_model=PlanChangeResult)
async def change_plan(req: PlanChangeRequest) -> PlanChangeResult:
    if IS_PROD:
        raise HTTPException(status_code=403, detail="Direct plan changes disabled in production.")
    user = await get_user_by_id(req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_plan = user["plan"]
    valid_plans = ("free", "pro", "elite", "lifetime_pro", "lifetime_elite")
    if req.new_plan not in valid_plans:
        return PlanChangeResult(
            user_id=req.user_id,
            old_plan=old_plan,
            new_plan=old_plan,
            success=False,
            reason="Invalid plan",
        )
    if req.new_plan == old_plan:
        return PlanChangeResult(
            user_id=req.user_id,
            old_plan=old_plan,
            new_plan=old_plan,
            success=True,
            reason="No change",
        )

    allowed_transitions = {
        "free":           {"pro", "elite", "lifetime_pro", "lifetime_elite"},
        "pro":            {"elite", "lifetime_pro", "lifetime_elite", "free"},
        "elite":          {"pro", "lifetime_pro", "lifetime_elite", "free"},
        "lifetime_pro":   {"pro", "elite", "lifetime_elite", "free"},
        "lifetime_elite": {"pro", "elite", "lifetime_pro", "free"},
    }
    if req.new_plan not in allowed_transitions.get(old_plan, set()):
        return PlanChangeResult(
            user_id=req.user_id,
            old_plan=old_plan,
            new_plan=old_plan,
            success=False,
            reason="Transition not allowed",
        )

    updated = await set_user_plan(req.user_id, req.new_plan)
    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")
    await record_plan_change(req.user_id, old_plan, req.new_plan, context=req.context)
    logger.info("[plan-change] user_id=%s %s->%s", req.user_id, old_plan, req.new_plan)
    return PlanChangeResult(
        user_id=req.user_id,
        old_plan=old_plan,
        new_plan=req.new_plan,
        success=True,
    )


@router.get("/api/user/unlocks", response_model=UnlockState)
async def get_unlock_state(
    user_id: str | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> UnlockState:
    user = await _resolve_user(user_id, current_user)
    questions_by_diff = get_questions_by_difficulty()
    solved_ids = await get_solved_ids(user["id"])
    unlock_state = compute_unlock_state(user["plan"], solved_ids, questions_by_diff)

    unlocked_questions = [str(qid) for qid, state in unlock_state.items() if state == "unlocked"]
    solved_questions = [str(qid) for qid, state in unlock_state.items() if state == "solved"]
    access_map = {str(qid): state for qid, state in unlock_state.items()}

    return UnlockState(
        user_id=user["id"],
        unlocked_questions=unlocked_questions,
        solved_questions=solved_questions,
        access_map=access_map,
    )
