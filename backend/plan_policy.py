"""Shared paid-plan sets + upgrade-path policy used by every billing rail.

The upgrade-path matrix is a business rule, not a Razorpay- or Paddle-specific
detail — both rails must enforce the *identical* matrix. It lives here as the
single source of truth so the policy can never drift between rails (and so a
future rail inherits it for free).

Canonical contract: docs/features/pricing.md § Backend upgrade path matrix.
"""

from __future__ import annotations

LIFETIME_PLANS = {"lifetime_pro", "lifetime_elite"}
SUBSCRIPTION_PLANS = {"pro", "elite"}
ALL_PAID_PLANS = LIFETIME_PLANS | SUBSCRIPTION_PLANS

# current_plan -> set of plans the user may upgrade or switch to.
_ALLOWED_TARGETS: dict[str, set[str]] = {
    "free":           {"pro", "elite", "lifetime_pro", "lifetime_elite"},
    "pro":            {"elite", "lifetime_pro", "lifetime_elite"},
    "lifetime_pro":   {"elite", "lifetime_elite"},
    "elite":          {"lifetime_elite"},
    "lifetime_elite": set(),
}


def target_plan_is_allowed(current_plan: str, target_plan: str) -> bool:
    return target_plan in _ALLOWED_TARGETS.get(current_plan, set())
