---
name: Kickoff Modality Phase
description: Kick off one phase of the modality migration with an orchestrated parallel-lane plan.
argument-hint: "Phase number and goal, e.g. 'Phase 1 PySpark practice uplift'"
agent: "Mock Modality Orchestrator"
---

Use [docs/mock-modality-rollout-plan.md](../../docs/mock-modality-rollout-plan.md) as the source of truth.

For the requested phase:

- identify the exact objective
- split the work into backend, frontend, and content lanes where safe
- specify which lanes can run in parallel and which must wait
- define acceptance criteria and validation commands for each lane
- list the exact risks, dependencies, and review gates before implementation begins

Return only the execution brief for this phase.