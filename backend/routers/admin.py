"""Admin router — protected operations for the platform operator.

All endpoints require an Authorization: Bearer <ADMIN_SECRET> header.
ADMIN_SECRET must be set in the environment; if absent the endpoints
return 503 so the server can start without it in local dev.

Endpoints
---------
POST /api/admin/grant-plan
    Grant a time-limited Pro or Elite override to a user by email.

DELETE /api/admin/grant-plan
    Revoke the override (user drops back to their base plan immediately).

GET /api/admin/grants
    List all users who have (or had) an override set.
"""

import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, field_validator

from config import ADMIN_SECRET
from db import grant_plan_override, list_plan_overrides, revoke_plan_override

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_OVERRIDE_PLANS = {"pro", "elite"}
MAX_GRANT_DAYS = 365


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_admin(authorization: str | None) -> None:
    """Raise 401/403/503 if the request is not authorised."""
    if not ADMIN_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin operations are not configured on this server (ADMIN_SECRET not set).",
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header required.")
    token = authorization.removeprefix("Bearer ").strip()
    if token != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Invalid admin secret.")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class GrantRequest(BaseModel):
    email: str
    plan: str
    days: int

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v

    @field_validator("plan")
    @classmethod
    def validate_plan(cls, v: str) -> str:
        if v not in VALID_OVERRIDE_PLANS:
            raise ValueError(f"plan must be one of {sorted(VALID_OVERRIDE_PLANS)}")
        return v

    @field_validator("days")
    @classmethod
    def validate_days(cls, v: int) -> int:
        if v < 1 or v > MAX_GRANT_DAYS:
            raise ValueError(f"days must be between 1 and {MAX_GRANT_DAYS}")
        return v


class RevokeRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return v.strip().lower()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/grant-plan", summary="Grant a time-limited plan override")
async def grant_plan(
    req: GrantRequest,
    authorization: str | None = Header(default=None),
):
    """Set plan_override + plan_override_until on the user.

    Safe to call again — overwrites any existing override (use to extend
    duration or upgrade from Pro to Elite).
    """
    _require_admin(authorization)
    result = await grant_plan_override(email=req.email, plan=req.plan, days=req.days)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No user found with email: {req.email}")
    logger.info(
        "[admin] grant-plan email=%s plan=%s days=%d until=%s",
        req.email, req.plan, req.days, result.get("plan_override_until"),
    )
    return {
        "ok": True,
        "email": result["email"],
        "name": result["name"],
        "effective_plan": result["effective_plan"],
        "plan_override": result["plan_override"],
        "plan_override_until": result["plan_override_until"],
    }


@router.delete("/grant-plan", summary="Revoke a plan override")
async def revoke_plan(
    req: RevokeRequest,
    authorization: str | None = Header(default=None),
):
    """Clear plan_override and plan_override_until — user returns to base plan."""
    _require_admin(authorization)
    result = await revoke_plan_override(email=req.email)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No user found with email: {req.email}")
    logger.info("[admin] revoke-plan email=%s", req.email)
    return {
        "ok": True,
        "email": result["email"],
        "name": result["name"],
        "effective_plan": result["effective_plan"],
    }


@router.get("/grants", summary="List all plan overrides")
async def list_grants(
    authorization: str | None = Header(default=None),
):
    """Return all users with a plan_override set (active and expired)."""
    _require_admin(authorization)
    grants = await list_plan_overrides()
    return {"grants": grants, "total": len(grants)}
