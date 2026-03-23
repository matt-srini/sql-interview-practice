# Unlock System Layer

## Objective
This layer is a deterministic, stateless policy engine that governs progression-based and plan-based content unlocking for the SQL interview practice platform. It evaluates user progress (questions solved), skill (accuracy), and plan (free, pro, elite) to produce derived entitlements—specifically, the access state (locked, unlocked, solved) and set of accessible question IDs. The unlock system never stores state or side effects; all entitlements are computed on demand from current inputs.

## Scope

**Included:**
- Unlock rules for content progression (easy → medium → hard)
- Hybrid logic combining skill and progress (counts and accuracy thresholds)
- Plan-based overrides (free, pro, elite)
- Determining per-question access state: locked, unlocked, solved

**Excluded:**
- Data storage or persistence (handled by user-profile)
- Plan transitions or validation (handled by plan-change)
- Payment or billing logic (handled by stripe-flow)
- UI or presentation concerns

## Dependencies

- user-profile.md (for plan and user state inputs)

## Inputs / Outputs

**Inputs:**
- user progress:
  - number of questions solved per difficulty
  - submission accuracy per difficulty
- user plan (from user-profile)
- full question catalog (grouped by difficulty, ordered)

**Outputs:**
- derived entitlements (access contract):
  - set of unlocked question IDs
  - per-question access state (locked, unlocked, solved)

## Key Design Principles
- Solved state is independent of unlock rules and must always be respected as a higher-priority override
- Rule evaluation must be deterministic and based solely on input state (no hidden or time-dependent sequencing)
- Stateless and pure: no persistence, no side effects
- Deterministic rule evaluation: same inputs always yield same outputs
- Evaluation is idempotent: repeated execution with identical inputs yields identical outputs
- No storage of unlock state; all entitlements are computed dynamically
- Clear separation from data and API layers
- Extensible rule system: new unlock rules can be added without refactoring
- Plan overrides must adjust unlock limits without redefining core unlock rules
- Unlock rules are evaluated independently per difficulty level (no cross-dependency between tiers)
- Unlock limits apply to the prefix of the ordered question list per difficulty (first N by defined order)
- Consistent ordering guarantees (question order is preserved)
- Simple, transparent rule definitions (avoid deeply nested logic)
- Accuracy is currently informational and not enforced in unlock rules (reserved for future skill-based gating)

## Unlock Logic Definition

### EASY → MEDIUM
- Solve ≥10 easy → unlock first 3 medium
- Solve ≥20 easy → unlock first 8 medium
- Solve ≥30 easy → unlock all medium

### MEDIUM → HARD (FREE PLAN CAP)
- Solve ≥10 medium → unlock first 3 hard
- Solve ≥20 medium → unlock first 8 hard
- Solve ≥30 medium → unlock first 15 hard (maximum cap for free plan; remaining hard questions stay permanently locked unless upgraded)

## Plan Overrides

### Free:
- Uses unlock rules as defined above

### Pro:
- All easy and medium questions unlocked
- Hard capped at a predefined configurable threshold (e.g., 22), independent of unlock rule progression

### Elite:
- Full access to all content, including boss question

## Access State Rules

- solved → already completed by user (always takes precedence)
- unlocked → accessible but not solved
- locked → not accessible

Solved state always overrides locked/unlocked state and must be applied after all unlock rules are evaluated.

## Implementation Steps

1. Compute user metrics (solved counts and accuracy per difficulty)
2. Evaluate unlock limits for each difficulty and plan
3. Apply unlock limits to ordered question lists to determine which are unlocked
4. Merge unlocked set with solved set to assign final access state per question
5. Return a map of question_id → access state (locked, unlocked, solved)
6. Do not persist unlock results; recompute entitlements on every evaluation
