# Mock Modality Phase 0 Review

Status: approved by orchestrator
Date: 2026-05-19
Owner: GPT-5.4 orchestrator

## Purpose

This document records the orchestrator review of the parallel Phase 0 lane outputs and freezes the decisions that now govern Phase 1.

Reviewed inputs:

- [docs/phases/mock-modality-phase-0-backend-audit.md](./mock-modality-phase-0-backend-audit.md)
- [docs/phases/mock-modality-phase-0-frontend-audit.md](./mock-modality-phase-0-frontend-audit.md)
- [docs/phases/mock-modality-phase-0-content-audit.md](./mock-modality-phase-0-content-audit.md)
- [docs/mock-modality-rollout-plan.md](../mock-modality-rollout-plan.md)
- [docs/specs/platform-north-star.md](../specs/platform-north-star.md)
- [docs/specs/practice-modality-spec.md](../specs/practice-modality-spec.md)
- [docs/specs/mock-benchmark-spec.md](../specs/mock-benchmark-spec.md)

## Phase 0 Result

Phase 0 is complete.

The repo now has a verified planning foundation for modality migration:

- the platform-level north star is codified
- the practice modality taxonomy is frozen
- the mock benchmark contract is frozen
- backend, frontend, and content control surfaces have been audited independently
- cross-lane dependencies are explicit enough to start implementation without reopening product-level ambiguity

No product-code behavior changed in Phase 0.

## Approved Decisions

### 1. Metadata migration stays additive first

Phase 1 must add modality metadata without breaking the current product contract.

Approved rule:

- keep existing `type` fields during migration
- add canonical `interaction_mode` in additive fashion
- preserve existing statistics `subtype` behavior
- stabilize naming drift between `type`, `question_type`, and `subtype` rather than trying to replace all legacy fields in one move

### 2. PySpark is the Phase 1 pilot

PySpark remains the correct first implementation slice because:

- it has the clearest gap between current framing and actual intent
- it sits on a high-value Data Engineer role path
- it benefits materially from better modality language even before deeper content rewrites

### 3. Mock redesign is not Phase 1 runtime work

The audits confirm that the current mock experience still mixes benchmark and drill behavior.

Approved sequencing:

- Phase 1: do not redesign the mock runtime yet
- later phases: separate benchmark and drill explicitly, remove mid-session correctness reveal for benchmark mode, and move away from Quick/Full/Custom as the benchmark model

### 4. Content quality caveat is mandatory

The content audit is approved with an explicit caveat:

- relabeling reasoning-heavy tracks does not by itself close content-quality gaps
- PySpark has the highest superficial-rebrand risk
- Data Engineering and Data Modeling have targeted easy-tier rewrite pressure
- ML Fundamentals and Experimentation remain unfinished hook audits and must stay marked unfinished until audited

### 5. Statistics remains the reference hybrid track

Statistics already has the strongest metadata foundation and should be treated as the reference implementation for hybrid track handling.

## Cross-Lane Findings That Matter For Phase 1

### Backend

- `backend/tracks.py` is the main registry hook for additive modality metadata
- `backend/routers/mock.py` is the controlling surface for later mock contract cleanup
- per-track loader validation is predictable enough for targeted additive changes

### Frontend

- `frontend/src/trackRegistry.js` is the main terminology multiplier across landing, hubs, and dashboard
- `frontend/src/pages/QuestionPage.js` is still largely code-vs-MCQ in shape and is the main practice rendering control point
- the current mock session UI is intentionally deferred from runtime redesign until later phases

### Content

- deterministic mapping from current `type` patterns to `interaction_mode` is now good enough to implement for Phase 1
- no whole-bank rewrite is justified
- rewrite and net-new pressure is uneven and should stay explicit by track

## Phase 0 Exit Criteria Review

| Exit criterion | Result |
|---|---|
| No unresolved taxonomy ambiguity for PySpark and Statistics | Met |
| All affected surfaces identified before execution starts | Met |
| ML Fundamentals and Experimentation explicitly tracked as unfinished concept-hook audits | Met |
| Advanced mock-only hook expansion assigned to later content work | Met |

## Phase 1 Authorization

Phase 1 is approved to begin with this exact scope:

- additive backend exposure of PySpark-first modality metadata and stable subtype surfaces where already applicable
- frontend terminology cleanup and PySpark-first practice UX uplift
- no runtime benchmark/drill split yet
- no broad content rewrites yet

## Review Guardrails For Phase 1

- reject any implementation that reintroduces generic MCQ-first language for reasoning-heavy tracks
- reject any implementation that widens scope into benchmark runtime redesign
- reject any implementation that rewrites content substance under the banner of metadata cleanup
- require focused validation per lane before merge