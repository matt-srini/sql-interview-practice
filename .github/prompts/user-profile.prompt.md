---
description: Source of truth for user identity, plan, and entitlement state. Pure data layer—no business logic or unlock/payment rules.
---

## Objective
Store and retrieve user profile data, including plan assignment (free, pro, elite) and minimal entitlement metadata. No business logic.

## Inputs
- user_id
- plan updates (from plan-change or stripe-flow)

## Outputs
- user profile object (user_id, plan, metadata)

## Invariants / Rules
- Single source of truth for plan/entitlement state
- No business or policy logic
- Plan is the only persisted driver of entitlements
- Deterministic reads
- Stateless query interface
- Minimal schema (user_id, plan, metadata)
- Safe defaults: new users default to 'free' plan
- Only allowed plans (free, pro, elite)

## Error Handling / Edge Cases
- Validation for allowed plans
- Efficient lookup and update

## Extension Points
- Additional entitlement types (features, modules)
- Minimal schema expansion

## Example Usage
- get_user_profile(user_id)
- upsert_user_profile(user_id, plan, metadata=None)
