# Authoring System Refactor — Tracking Doc

> **Delete this file once Phase 3 ships and Interview Loop is live in production.** This is a temporary tracking artifact, not canonical documentation.

**Started:** 2026-05-21
**Owner:** matt + Claude
**Goal:** Re-found the question authoring system around datathink's philosophy (durable professional reasoning, interview success as consequence), a per-track concept taxonomy with teeth, a mandatory single authoring entry point, and a mock layer that supports atomic follow-up chains and an Elite-only Interview Loop mode.

---

## Why this refactor exists

The platform accumulated four overlapping sources of truth for question authoring:

1. A universal authoring agent
2. Nine per-track authoring agents (40% overlap with universal)
3. `content-authoring.md` (988 lines with per-track encyclopedia)
4. `concept-hooks.md` (1,048 lines, Socratic but not enforced) + hardcoded `concept_families.py`

Result: drift, ad-hoc authoring decisions, inconsistent concept tagging, no enforceable contract between content and the mock/insights surfaces that consume it. This refactor consolidates to **one universal agent + per-track knowledge docs + one canonical taxonomy + one mandatory rule**.

---

## Canonical decisions (locked, do not relitigate)

### Philosophy
The platform's North Star is professional reasoning development — interview success is the consequence, not the goal. Full text in `docs/specs/platform-north-star.md`.

### Authoring architecture
- One universal agent: `.github/agents/question-authoring.agent.md`
- Per-track knowledge in `docs/tracks/<track>.md` (NOT per-track agent files)
- `docs/concept-taxonomy.md` is the canonical concept-family registry — per-track, NOT cross-track
- `docs/content-authoring.md` slims to the platform-level authoring contract
- **Mandatory-agent rule:** no question authored or modified without the agent

### Concept taxonomy
- One `concepts` field on each question; families derived via taxonomy registry
- Per-track families only (no cross-track family namespace)
- Blocklists per track (mechanic-name tags forbidden where they obscure reasoning)
- New tags require PR to taxonomy doc first

### Mock contract
- Three modes: `benchmark`, `short_drill`, `long_drill`
- `custom` mode dropped from canonical surface
- `focus_concepts` filter: Elite only
- `interview_loop` mode: Elite only, chain-driven only (parents with `follow_ups[]` length ≥2)
- Plan-gated pool sourcing:
  - Free → practice pool only (no mock-only, no chains)
  - Pro → practice + mock-only, chains eligible
  - Elite → same as Pro + focus mode + Interview Loop
- **Chain atomicity:** parent + all follow_ups travel together; consumed once per user globally
- Consumption trigger: session start; reclaimable within 2-min discard window
- Pool exhaustion: hard 409 with "switch tracks" copy
- Chain length: 2–4
- Consecutive follow_up_dimension values must differ within a chain
- Child cannot have own follow_ups (no nesting)
- Child cannot be referenced by two parents

### Follow-up dimension taxonomy (7 universal)
scale_pivot · business_rule_pivot · data_quality_pivot · edge_case_pivot · performance_pivot · ambiguity_pivot · stakeholder_pivot

---

## Phase status

### Phase 0 — Cleanup [in progress]
- [x] Delete 6 stale planning docs (mock-modality-rollout-plan.md, concept-expansion-plan.md, 4 phase-0 audits)
- [x] Delete 6 obsolete agent/prompt files (mock-modality-orchestrator + 3 codex agents + 2 prompts)
- [x] Update governance-source references in `platform-north-star.md`
- [x] Create this tracking doc

### Phase 1 — Foundation specs [pending]
- [ ] Commit A: `docs/concept-taxonomy.md` + extend `docs/specs/mock-benchmark-spec.md`
- [ ] Commit B: 9 × `docs/tracks/<track>.md`
- [ ] Commit C: refine universal agent + north-star + content-authoring + CLAUDE.md, delete 9 per-track agents

### Phase 1.5 — Frontend copy sweep [pending]
- [ ] Landing page, topbar, auth, mock, dashboard, pricing, empty states
- [ ] Scrub remaining FAANG-prep language

### Phase 1 followup — Color review [pending]
- [ ] Browser pass on `--bg-page` token, written recommendation

### Phase 2 — Content alignment [pending]
- [ ] Remap existing 993 question `concepts` arrays to new per-track families
- [ ] Author new mock-only content with `follow_up_dimension` + `follow_ups[]` — target 3-month Pro runway per track (~180 questions/track from current 8–38)
- [ ] Refactor `concept_families.py` to load from taxonomy doc
- [ ] Add catalog-load validations (chain integrity, dimension diversity, no orphans)
- [ ] Add CI check that flags question file edits without agent invocation marker

### Phase 3 — Interview Loop full stack [pending, depends on Phase 2 content]
- [ ] DB: `mock_chain_consumption` table + Alembic migration
- [ ] Backend: chain-aware selection, Interview Loop endpoint, plan gating
- [ ] Frontend: Interview Loop UI in MockHub + MockSession
- [ ] Analytics: dimension-level weak-spot insight in dashboard

---

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-05-21 | Per-track concept families, NOT cross-track | Cross-track aggregation is a Phase 3 dashboard lens, not a taxonomy constraint; forcing alignment muddies authoring |
| 2026-05-21 | Drop per-track authoring agents | 40% overlap with universal agent caused drift; track docs hold the knowledge instead |
| 2026-05-21 | Mock chains are globally atomic per user | Simplest mental model ("zero or one"); preserves readiness signal |
| 2026-05-21 | Mock-only is Pro/Elite, free uses practice pool | Fairness alignment with paid value; chains stay premium |
| 2026-05-21 | Interview Loop is chain-only | Otherwise it's "benchmark with a name" |
| 2026-05-21 | Pool exhaustion → hard 409 | Soft fallback dilutes the readiness signal |
| 2026-05-21 | New philosophy: development primary, interview success consequence | Tonal shift away from "FAANG prep" toward "build the reasoning that makes a data professional effective" |

---

## Open questions / follow-ups

- Sizing for Phase 2 mock content expansion — confirm 3-month-Pro-runway target after observing real usage patterns
- Whether to keep `custom` mock mode as an Elite power-user surface (currently dropped)
- Whether free-tier mock should be allowed to re-show solved practice questions (default: yes, fresh-first)
