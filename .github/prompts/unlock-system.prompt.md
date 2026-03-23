---
description: Stateless, deterministic policy engine for content unlocking based on user progress and plan.
---

## Objective
Compute derived entitlements (unlocked question IDs, per-question access state) from user progress and plan.

## Inputs
- user progress (solved counts, accuracy per difficulty)
- user plan (from user-profile)
- question catalog (ordered by difficulty)

## Outputs
- Map of question_id → access state (locked, unlocked, solved)
- Set of unlocked question IDs

## Invariants / Rules
- Stateless, pure, deterministic, idempotent
- No persistence or side effects
- Solved state always overrides unlock/locked
- Plan overrides adjust unlock limits
- Unlock rules per difficulty, no cross-tier dependencies
- Consistent ordering

## Unlock Logic
- EASY → MEDIUM: Solve ≥10 easy → unlock 3 medium; ≥20 easy → 8 medium; ≥30 easy → all medium
- MEDIUM → HARD (free cap): Solve ≥10 medium → 3 hard; ≥20 → 8 hard; ≥30 → 15 hard (free cap)
- Pro: all easy/medium unlocked, hard capped (e.g., 22)
- Elite: all content unlocked
- Access states: solved > unlocked > locked

## Error Handling / Edge Cases
- Always recompute from current state
- Accuracy is informational (future use)

## Extension Points
- New unlock rules
- Skill-based gating

## Example Usage
- Compute entitlements for user_id X with plan Y and progress Z
