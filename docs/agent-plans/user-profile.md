
# User Profile Layer

## Objective
This layer is the single source of truth for user identity, plan, and entitlement-related state in the SQL interview practice platform. It is responsible for storing and retrieving user profile data, including plan assignment (free, pro, elite) and minimal entitlement state. The user profile layer is strictly a data storage and access layer—no business logic, unlock rules, or payment processing are present here. It is designed for simplicity, determinism, and extensibility, and is fully decoupled from unlock logic and payment systems.

## Scope

**Included:**
- User identity (user_id)
- Plan storage (free, pro, elite)
- Minimal persisted entitlement-related metadata if required (e.g., feature flags), but not derived access entitlements
- Read and write access to user plan (for plan-change or payment flows)

**Excluded:**
- Unlock logic or progression rules (handled by unlock-system)
- Plan transition rules or validation (handled by plan-change)
- Payment processing or billing (handled by stripe-flow)
- UI or presentation concerns

## Dependencies

None (this is the foundational data layer for all user progression and entitlement features)

## Inputs / Outputs

**Inputs:**
- user_id
- plan updates (from plan-change or stripe-flow)

**Outputs:**
- user profile object (source-of-truth state):
  - user_id
  - plan
  - metadata (optional, minimal)

## Key Design Principles

- Single source of truth for user plan and entitlement state
- No business or policy logic (pure data layer only)
- Plan is the only persisted driver of entitlements; access is derived downstream
- Deterministic reads: same state always yields same output
- Stateless query interface over persistent state
- Minimal schema: only store what is necessary (avoid over-design)
- Extensible for future entitlement types (features, modules, etc.)
- Safe defaults: new users default to 'free' plan
- Efficient lookup and update for user profile data

## Implementation Steps

1. Define user_profile storage (table or collection) with fields: user_id (primary key), plan, metadata (optional)
2. Implement get_user_profile(user_id) to retrieve the user profile object
3. Implement upsert_user_profile(user_id, plan, metadata=None) to create or update a user's plan
4. Ensure new users are assigned the default plan ('free') if no plan is set
5. Add indexing or efficient lookup on user_id for fast access
6. Add validation to ensure only allowed plans (free, pro, elite) are stored
