# Mock Benchmark Spec

Status: canonical planning spec
Owner: product + orchestration
Last updated: 2026-05-19

## Purpose

This spec defines what the mock product should optimize for during the modality migration.

## Core position

Mock is a benchmark layer, not a faster version of practice.

That means the mock experience must prioritize:

- credibility as a readiness signal
- consistent rules across a session
- delayed answer revelation
- strong post-session diagnosis
- track-aware composition instead of one-size-fits-all session templates

## Benchmark invariants

- No correctness reveal mid-session
- No solution reveal mid-session
- `Submit` is final for every track during a benchmark mock
- `Run` is allowed only on executable tracks
- Session composition should follow track blueprints, not one universal question count
- Custom configurable sessions belong to drill mode, not the benchmark contract

## Benchmark vs drill

| Mode | Purpose | Mid-session feedback | Composition |
|---|---|---|---|
| Benchmark mock | Measure readiness | Minimal, no verdict reveal beyond acceptance of submission | Track blueprint |
| Drill / custom session | Target practice under constraints | Flexible | User-configured |

The product may keep both, but they should not be framed as the same thing.

## Blueprint principle

Mock composition must respect modality.

| Modality family | Mock implication |
|---|---|
| Executable problem-solving | Longer per-question time, `Run` allowed, no result verdict until finish |
| Code-adjacent reasoning | Prompts should emphasize debugging, prediction, or execution reasoning |
| Constructed reasoning | Prompts should emphasize case analysis, prioritization, tradeoffs, and interpretation |
| Hybrid | Session blueprint must mix subtypes intentionally rather than randomly |

## Summary contract

Every finished benchmark session should produce:

- score headline
- time usage context
- per-question review with official solution or explanation
- concept breakdown for the session
- comparison against relevant historical baseline
- strongest pattern observed
- weakest pattern observed
- one clear next action

## Analytics contract

Mock analytics should answer four questions:

- How is the user's score trending?
- Which concepts repeatedly break under timed conditions?
- Which tracks or modalities are lagging behind the user's practice confidence?
- What should the user do next in practice or paths?

## Plan philosophy

Plan gating can change over time, but the premium split should follow this logic:

- Free: taste the benchmark loop without replacing the practice product
- Pro: serious mock usage and useful post-session review
- Elite: deep analytics, targeted focus controls, and the most coach-like debrief layer

## Filter philosophy

- Company filtering is a narrow SQL-specific capability today, not a universal mock paradigm.
- For the broader mock redesign, context or concept targeting is more defensible than forcing company filters across every track.

## Anti-patterns

- A 2-question timer dressed up as a benchmark
- Immediate right/wrong reveal that collapses the interview simulation
- Treating every track as if it should have the same mock shape
- Strong practice analytics with weak mock follow-through
- Feature gating that feels arbitrary rather than aligned to benchmark value

## Migration implications

The current Quick / Full / Custom system is an implementation starting point, not the final product contract. The modality rollout should separate benchmark mocks from drill-style sessions and make the benchmark rules explicit in backend responses, UI copy, and analytics.
