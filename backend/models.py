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


class CreateOrderRequest(BaseModel):
    plan: str


class CreateOrderResponse(BaseModel):
    # Exactly one of order_id / subscription_id is set depending on whether
    # the target plan is a one-time (lifetime_*) or recurring (pro/elite) purchase.
    order_id: Optional[str] = None
    subscription_id: Optional[str] = None
    amount: int                 # in paise (INR * 100)
    currency: str
    key_id: str
    name: str                   # merchant display name shown in the Razorpay modal
    description: str
    prefill_email: Optional[str] = None
    prefill_name: Optional[str] = None
    is_subscription: bool


class VerifyPaymentRequest(BaseModel):
    plan: str
    razorpay_payment_id: str
    razorpay_signature: str
    # One of the two below is provided depending on the flow
    razorpay_order_id: Optional[str] = None
    razorpay_subscription_id: Optional[str] = None


class VerifyPaymentResponse(BaseModel):
    plan: str


class RunCodeRequest(BaseModel):
    code: str
    question_id: int


class SubmitCodeRequest(BaseModel):
    code: str
    question_id: int
    duration_ms: int | None = None


class PySparkSubmitRequest(BaseModel):
    selected_option: int
    question_id: int
    duration_ms: int | None = None
