# Platform North Star Spec

Status: canonical planning spec
Owner: product + orchestration
Last updated: 2026-05-21

## Purpose

This spec defines what datathink is trying to become at the product level so implementation work does not drift into disconnected feature shipping.

## The datathink philosophy (canonical, verbatim)

> We live in an era defined by data. Every transaction, interaction, and decision leaves a digital trace — and the volume of this data is growing faster than our collective ability to make sense of it.
>
> But data, on its own, means nothing. The real work is generating meaning from it — building systems that store it efficiently, retrieve it reliably, model it thoughtfully, and ultimately transform raw signal into insight that drives better decisions, better products, and better outcomes for people.
>
> This work gave rise to an entire class of technical professions: data engineers who design the pipelines, analysts who surface the patterns, scientists who build the models, and architects who ensure the systems scale. These are not peripheral roles — they are increasingly the backbone of how modern organizations function and grow.
>
> Datathink exists for these professionals — and for those becoming them.
>
> Not as another platform of interview puzzles to crack before a hiring deadline, but as a place to develop the kind of reasoning that makes someone genuinely effective in a data-driven world. The kind of professional who doesn't just write a correct query, but understands why the data is structured the way it is, what question is really worth asking, and how the answer should inform a decision.
>
> If that preparation also makes you exceptional in interviews — and it will — that's a consequence, not the goal.

This text is the canonical product framing. Every authoring agent, every doc, and every user-facing surface should reflect it. The old "FAANG-level interview preparation" framing is retired as the primary frame and survives only as the secondary grounding test ("would the same reasoning earn the offer in a real interview screen?").

## Product goal

Build the strongest platform for developing durable data-professional reasoning by combining:

- a full practice curriculum that teaches reasoning patterns a practitioner relies on years into the role
- role-aware track combinations that mirror real hiring funnels
- a dashboard that diagnoses progress and weak areas across tracks
- a mock layer that benchmarks readiness under realistic conditions — not "practice with a timer"

Interview performance follows from reasoning quality. Build for the practitioner; the candidate gets the win.

## Core product model

| Surface | Job to be done | What it is not |
|---|---|---|
| Practice | Build the reasoning durably, by track and difficulty | Not a disposable teaser or a random drill bucket |
| Samples | Let first-time visitors feel the product quickly | Not the main curriculum |
| Learning paths | Curate order and accelerate the right unlocks | Not a separate content bank |
| Dashboard | Turn attempt history into coaching and prioritization | Not a vanity stats page |
| Mock | Benchmark readiness under constraint — and via Interview Loop, simulate iterative interviewer dialogue | Not answer-reveal practice with a timer |

**Mock layer canonical source of truth:** [`docs/features/mock.md`](../features/mock.md) — owns the plan-tier matrix, chain atomicity, Interview Loop contract, and discard-window UX. Do not restate mock gates in other docs; link.

## Canonical facts

- Active tracks: SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation
- Hiring roles surfaced on landing: Data Analyst, Data Engineer, Analytics Engineer, Data Scientist
- Practice bank: 878 questions
- Mock-only bank: 1,148 questions
- Practice is the full curriculum; mock-only content is supplemental benchmark inventory

## Role-to-track framing

| Role | Core tracks |
|---|---|
| Data Analyst | SQL, Statistics, Pandas, Python |
| Data Engineer | Python, SQL, PySpark, Data Engineering, Data Modeling |
| Analytics Engineer | SQL, Data Modeling, Pandas, Python |
| Data Scientist | ML Fundamentals, Statistics, Experimentation, Python, SQL |

This mapping is a product promise. Track quality and modality choices must strengthen, not weaken, the credibility of each role path.

## Product principles

### Practice is the curriculum

The practice catalog is not a marketing wrapper around mock. It is the main learning system. Unlock rules, hints, learning-path sequencing, and question ordering should preserve a real curriculum arc. (Learning paths are an ordered grouping of existing practice questions — they do not unlock anything; unlocks are threshold-only.)

### Mock is a benchmark

Mock exists to measure readiness under pressure. It should feel stricter than practice, not just faster.

### Depth over fake execution

Not every track should be forced into a coding interaction. The right standard is whether the interaction matches the real interview skill being assessed.

### Cross-track coaching matters

The dashboard should connect track-level performance, weak concepts, pacing, and mock outcomes into a clear next action.

## Filter policy

- The company filter is a **practice-catalog convenience only** (free, all tiers, SQL), justified because the SQL bank already carries structured company provenance. It is **not** a paid/premium feature and is **not** offered in mock (the stubbed Elite mock company filter was removed 2026-06-09 — see `docs/decisions/DECISIONS.md`): a company filter is a grind-market lever that contradicts the reasoning-premium positioning, so we never gate or advertise it as a tier differentiator.
- Do not spread company tags to other tracks unless the content provenance is real and broad enough to avoid becoming noisy theater.
- For reasoning-heavy tracks, prefer industry, context, system domain, or interview-situation filters over pseudo-company filters.

## Governance sources

- `docs/concept-taxonomy.md` is the canonical concept-family registry per track and the follow-up dimension taxonomy. Every question concept tag must map to a family registered here.
- `docs/concept-hooks.md` is the Socratic interview-hook inventory by track (used to seed conceptual coverage when authoring).
- `docs/tracks/<track>.md` is the per-track knowledge base, philosophy, and authoring allocation matrix.
- `.github/agents/question-authoring.agent.md` is the mandatory authoring entry point — no question is created or modified without it.
- `frontend/src/roleRegistry.js` is the live role-to-track product mapping (the SoT — consumed by the landing role selector, the `/interview-prep/<role>` SEO landing pages, the `/interview-prep` index, and the Sample Hub role filter). The role pages render this promise as indexable, role-specific prep pages.

## Success bar

The platform is aligned when:

- users can understand what each track is training and why it belongs to a role path
- practice feels like structured skill-building rather than a question dump
- dashboard outputs lead to obvious next actions
- mock outcomes feel trustworthy as readiness signals
- documentation and prompts describe the same product the code is actually building
