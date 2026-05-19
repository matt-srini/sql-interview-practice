---
name: Review Codex Phase Output
description: Review completed Codex lane outputs against the approved modality-migration phase plan.
argument-hint: "Paste the completed lane outputs and the active phase"
agent: "Mock Modality Orchestrator"
---

Review the provided Codex lane outputs against [docs/mock-modality-rollout-plan.md](../../docs/mock-modality-rollout-plan.md).

Check:

- scope adherence
- modality fidelity
- validation quality
- cross-lane inconsistencies
- docs or prompt drift

Return:

1. pass / revise verdict per lane
2. blocking issues
3. safe merge order
4. next wave recommendation