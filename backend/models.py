"""
Data models for user, plan, unlock, and payment state.
"""
from typing import Optional
from pydantic import BaseModel

class UserProfile(BaseModel):
    user_id: str
    plan: str  # 'free', 'pro', 'elite'
    metadata: Optional[dict] = None

class PlanChangeRequest(BaseModel):
    user_id: str
    new_plan: str  # 'free', 'pro', 'elite'
    context: Optional[str] = None  # e.g., 'dev', 'stripe', etc.

class PlanChangeResult(BaseModel):
    user_id: str
    old_plan: str
    new_plan: str
    success: bool
    reason: Optional[str] = None

class UnlockState(BaseModel):
    user_id: str
    unlocked_questions: list[str]
    solved_questions: list[str]
    access_map: dict  # question_id -> 'locked' | 'unlocked' | 'solved'

class StripeSession(BaseModel):
    user_id: str
    session_id: str
    customer_id: Optional[str] = None
    status: str  # 'created', 'completed', 'failed', etc.
    plan: str
    created_at: Optional[str] = None
