# Platform North Star Spec

Status: canonical planning spec
Owner: product + orchestration
Last updated: 2026-05-19

## Purpose

This spec defines what datathink is trying to become at the product level so implementation work does not drift into disconnected feature shipping.

## Product goal

Build the strongest data interview preparation platform for serious candidates by combining:

- a full practice curriculum that teaches durable reasoning patterns
- role-aware track combinations that mirror real hiring funnels
- a dashboard that diagnoses progress and weak areas across tracks
- a mock layer that benchmarks interview readiness instead of acting like another practice surface

## Core product model

| Surface | Job to be done | What it is not |
|---|---|---|
| Practice | Learn the full curriculum by track and difficulty | Not a disposable teaser or a random drill bucket |
| Samples | Let first-time users feel the product quickly | Not the main curriculum |
| Learning paths | Curate order and accelerate unlocks | Not a separate content bank |
| Dashboard | Turn attempt history into coaching and prioritization | Not just a vanity stats page |
| Mock | Benchmark readiness under constraint | Not answer-reveal practice with a timer |

## Canonical facts

- Active tracks: SQL, Python, Pandas, PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation
- Hiring roles surfaced on landing: Data Analyst, Data Engineer, Analytics Engineer, Data Scientist
- Practice bank: 828 questions
- Mock-only bank: 165 questions
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

The practice catalog is not a marketing wrapper around mock. It is the main learning system. Unlock rules, path shortcuts, hints, and question sequencing should preserve a real curriculum arc.

### Mock is a benchmark

Mock exists to measure readiness under pressure. It should feel stricter than practice, not just faster.

### Depth over fake execution

Not every track should be forced into a coding interaction. The right standard is whether the interaction matches the real interview skill being assessed.

### Cross-track coaching matters

The dashboard should connect track-level performance, weak concepts, pacing, and mock outcomes into a clear next action.

## Filter policy

- Company filters are currently justified only for SQL because the bank already carries structured company provenance there.
- Do not spread company tags to other tracks unless the content provenance is real and broad enough to avoid becoming noisy theater.
- For reasoning-heavy tracks, prefer industry, context, system domain, or interview-situation filters over pseudo-company filters.

## Governance sources

- `docs/concept-hooks.md` is the canonical concept inventory by track.
- `docs/concept-expansion-plan.md` is the historical audit and expansion record.
- `frontend/src/pages/LandingPage.js` is the live role-to-track product mapping.
- `docs/mock-modality-rollout-plan.md` is the execution plan for the current modality migration.

## Success bar

The platform is aligned when:

- users can understand what each track is training and why it belongs to a role path
- practice feels like structured skill-building rather than a question dump
- dashboard outputs lead to obvious next actions
- mock outcomes feel trustworthy as readiness signals
- documentation and prompts describe the same product the code is actually building
