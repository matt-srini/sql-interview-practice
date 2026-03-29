"""
Data models for user, plan, unlock, and payment state.
"""

from typing import Optional

from pydantic import BaseModel


class UserProfile(BaseModel):
    id: str
    email: Optional[str] = None
    name: Optional[str] = None
    plan: str


class PlanChangeRequest(BaseModel):
    user_id: str
    new_plan: str
    context: Optional[str] = None


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
    access_map: dict[str, str]


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class RunCodeRequest(BaseModel):
    code: str
    question_id: int


class SubmitCodeRequest(BaseModel):
    code: str
    question_id: int


class PySparkSubmitRequest(BaseModel):
    selected_option: int
    question_id: int
