"""
Data models for user, plan, unlock, and payment state.
"""

from typing import Annotated, Optional

from pydantic import BaseModel, Field


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
    currency: str = "INR"


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


class PaddleCheckoutRequest(BaseModel):
    plan: str


class PaddleCheckoutResponse(BaseModel):
    # Paddle.js is price-ID-driven and opens the overlay client-side; the backend
    # returns the config it needs. The actual amount + currency are resolved by
    # Paddle from the price in its catalog (overlay-controlled), mirroring how
    # Razorpay subscription amounts are dashboard-controlled.
    client_token: str
    environment: str            # 'sandbox' | 'production'
    price_id: str
    is_subscription: bool
    customer_email: Optional[str] = None
    # Echoed back verbatim on the transaction/subscription webhook so we can
    # resolve the user + target plan (Paddle's equivalent of Razorpay notes).
    custom_data: dict[str, str]


class RunCodeRequest(BaseModel):
    code: str
    question_id: int


class SubmitCodeRequest(BaseModel):
    code: str
    question_id: int
    duration_ms: int | None = None


class PySparkSubmitRequest(BaseModel):
    selected_option: Annotated[int, Field(ge=0, le=3)]
    question_id: int
    duration_ms: int | None = None
