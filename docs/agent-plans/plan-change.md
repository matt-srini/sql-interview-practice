# Plan Change Layer

## Objective
Define how users transition between plans (free, pro, elite), including upgrade, downgrade, and dev-mode plan switching. This layer is responsible for validating transitions, updating the source-of-truth plan in the user-profile layer, and triggering downstream recomputation of entitlements. It orchestrates plan mutations without embedding unlock or payment logic.

## Scope
- Included:
  - API and frontend interaction for plan changes (dev-mode and future production)
  - State transitions and validation (eligibility, allowed transitions, downgrade effects)
  - Writing plan changes to user-profile (source of truth)
  - Emitting/triggering recomputation of entitlements (unlock-system)
  - Support for idempotent operations and safe retries
- Excluded:
  - Payment processing and external billing (see stripe-flow.md)
  - Unlock rule logic and entitlement computation (see unlock-system.md)
  - Data storage schema and persistence details (see user-profile.md)
  - Detailed UI/UX for plan selection

## Dependencies
- user-profile.md (for reading current plan and updating plan state as source of truth)
- stripe-flow.md (for production payment-triggered plan changes)

## Inputs / Outputs

Inputs:
- requested plan change (free/pro/elite)
- current user state (user_id, current plan, metadata)
- context (dev-mode override, or payment event reference in production)

Outputs:
- updated plan state (persisted via user-profile)
- transition result (success/failure, reason)
- trigger for unlock recomputation (invalidate/recompute entitlements)

## Key Design Principles
- Explicit, auditable plan transitions (every change is logged and attributable)
- Stateless API: each request fully describes the desired transition without relying on prior call context
- Deterministic: same request and input state yields the same result
- Idempotent operations: repeating the same transition request does not create duplicate side effects
- Clear separation of concerns: no unlock logic or payment logic in this layer
- Does not depend on unlock-system for decision logic; only triggers entitlement recomputation
- Plan transitions validated against allowed rules (e.g., free→pro allowed, pro→free allowed with constraints)
- Support for future transition constraints (downgrade rules, cooldowns, grace periods)
- Responsible for updating user-profile plan state as the source of truth
- Plan changes only modify plan state; entitlement changes are derived downstream
- Safe handling of concurrent requests (default: last-write-wins unless explicitly configured otherwise)

## Transition Model
Define allowed transitions and semantics (initial v1):
- free → pro (upgrade)
- free → elite (upgrade)
- pro → elite (upgrade)
- pro → free (downgrade)
- elite → pro (downgrade)
- elite → free (downgrade)

Notes:
- Downgrades may take effect immediately in dev mode; in production they may honor billing periods (handled via stripe-flow)
- Re-applying the same plan (e.g., pro → pro) is a no-op and should be idempotent

## Validation Rules
- Requested plan must be one of the supported values (free, pro, elite)
- Transition must be allowed by the transition model
- Optional future checks:
  - cooldown windows for frequent switching
  - downgrade restrictions or grace periods

## Access Recompute Trigger
- After a successful plan change, the system must trigger entitlement recomputation (via unlock-system)
- No unlock state is persisted here; downstream systems recompute based on new plan

## Implementation Steps
- Define API endpoint: POST /api/user/plan
- Validate input plan and current state
- Check transition validity (allowed transitions)
- Perform idempotency check (no-op if same plan)
- Update user_profile (upsert plan as source of truth)
- Emit/trigger entitlement recomputation (e.g., invalidate cache or call unlock-system)
- Return response (updated plan, status)
- Add audit logging for transitions (optional but recommended)

## Error Handling
- 400: invalid plan value
- 403: disallowed transition (if enforced)
- 409: conflict (optional, for concurrent updates)
- 200: success or idempotent no-op

## Dev Mode Support
- Allow direct plan switching via API (no payment required)
- Optional header override for testing (e.g., X-Plan)
- Ensure dev mode follows same validation and idempotency rules
