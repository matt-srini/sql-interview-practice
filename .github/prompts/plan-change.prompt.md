---
description: Validates and executes plan transitions (upgrade/downgrade/dev-mode), updates user-profile, triggers entitlement recomputation.
---

## Objective
Validate and execute plan transitions, update plan in user-profile, and trigger unlock-system recomputation.

## Inputs
- requested plan change (free/pro/elite)
- current user state (user_id, current plan, metadata)
- context (dev-mode override, payment event ref)

## Outputs
- updated plan state (persisted via user-profile)
- transition result (success/failure, reason)
- trigger for unlock recomputation

## Invariants / Rules
- Explicit, auditable plan transitions
- Stateless API, deterministic, idempotent
- No unlock or payment logic
- Only allowed transitions (free↔pro↔elite)
- Safe for concurrent requests (last-write-wins)

## Transition Model
- free → pro/elite (upgrade)
- pro → elite/free (upgrade/downgrade)
- elite → pro/free (downgrade)
- Re-applying same plan is a no-op

## Error Handling / Edge Cases
- 400: invalid plan
- 403: disallowed transition
- 409: conflict (concurrent updates)
- 200: success or idempotent no-op
- Dev mode: direct switching allowed, same validation

## Extension Points
- Future transition constraints (cooldowns, grace periods)
- Audit logging
- More downgrade rules

## Example Usage
- POST /api/user/plan { plan: "pro" }
