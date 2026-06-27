# Product Sense / Metrics — track research & design proposal

> **Status: RESEARCH / PROPOSAL. Not production content. Do not wire into code.**
>
> This folder is a **self-contained research + design package** for a *potential* tenth practice
> track. It lives deliberately **apart from the production track docs** (`docs/tracks/`,
> `docs/concept-taxonomy.md`, `docs/features/mock.md`, `backend/`) so nothing here is mistaken for
> shipped curriculum or enforced by any validator. **No frontend code, no backend code, no question
> JSON, no track config** is part of this work — it is documentation only. If/when this track is
> greenlit, this package becomes the brief from which the per-track doc (`docs/tracks/product-sense.md`),
> the concept-family registry, and the `question-authoring.agent.md` run are built.

Builds on the **2026-06-26 read-only DS-gap audit** ([`docs/decisions/DECISIONS.md`](../../decisions/DECISIONS.md)),
which found that the five-then-six Data Scientist tracks cover the quantitative core well but omit the
**product-sense / metric-design / metric-diagnosis / open case-study** round — a major, near-universal
DS (and Data Analyst) interview component — and backlogged it ([`TODO.md`](../../../TODO.md) §P2). This
package is the deep research that backlog item asked for.

---

## 1. Why this track should exist — the reasoning-premium case

The justification is **reasoning depth, never interview frequency** (the line CLAUDE.md §Platform
position draws against the grind market). Two ways to read that test, both pass decisively:

- **It is the most reasoning-dense round in the data-science loop.** Every other DS surface has a
  "correct" technical answer you converge on (the right join, the right estimator, the right metric
  formula). Product sense is the round where the work *is* the judgment: *which* metric captures
  success and why, *why* a number moved, *which* of two goods to trade against the other. That is the
  literal datathink thesis — "the professional who doesn't just write a correct query, but understands
  what question is really worth asking and how the answer should inform a decision"
  (north-star philosophy, verbatim).
- **It is durable beyond the interview.** A practicing data scientist or analyst reasons about metric
  definition, metric diagnosis, and measurement trade-offs *every week, for years* — far more than they
  run a switchback experiment or hand-derive a posterior. By the "one test every question must pass"
  ([`content-authoring.md`](../../content-authoring.md) §The one test), this is exactly the reasoning
  the platform exists to build.

What this is **not** an argument from: "StrataScratch/Interview Query/Ace-the-DS-Interview cover it."
Per CLAUDE.md, competitor coverage is never a defense. The defense above stands on durable reasoning
surface alone — the round just happens to also be near-universal at the largest DS employers (Meta's
Analytical Execution + Analytical Reasoning rounds, Google's Product Sense & Metrics, Uber's product
case, Airbnb's product-sense round; see [`01-external-research.md`](01-external-research.md)).

It also closes a real **role-credibility gap**: the [north-star role map](../../specs/platform-north-star.md#role-to-track-framing)
promises Data Scientist and Data Analyst paths, and product sense is the round candidates for *both*
most often fail on — yet it is the one round those role paths can't currently rehearse.

## 2. Why scenario-MCQ, not "fake execution" — the modality fit

The obvious objection to this track has always been *"product sense is open-ended free-response; the
platform is MCQ + code, so it can't be done honestly."* The north-star spec answers this directly:

> **Depth over fake execution.** *Not every track should be forced into a coding interaction. The right
> standard is whether the interaction matches the real interview skill being assessed.*

Product sense is a **judgment** skill, not a coding skill — so forcing a code editor onto it would be
exactly the "fake execution" the spec rejects. The right modality is the one the platform already uses
for its other judgment-heavy rounds — **Experimentation, ML Fundamentals, PySpark, Data Engineering,
Data Modeling**: *constructed-reasoning MCQ* (a scenario anchor + a single-best-answer choice among four
defensible-looking options). Experimentation is the proof of concept: "is this A/B read trustworthy
given the SRM?" is every bit as open-ended in a real interview as "which metric captures success?", yet
it grades cleanly and durably as a scenario MCQ. Product sense is the same shape.

**The honest limitation (stated up front).** Scenario-MCQ tests whether a candidate can *recognise* the
strong metric / the defensible first diagnostic step / the sound trade-off — it does not make them
*generate* a metric system from a blank page the way the live round does. We accept that gap as the same
gap every reasoning-MCQ track already accepts (Experimentation doesn't make you *run* the experiment
either). [`02-track-design.md`](02-track-design.md) §Modality records a possible **Phase-2 open-response
extension** (rubric-graded short free-text) as a future modality, explicitly out of scope for v1.

No new UI is required: this track reuses the existing `MCQPanel` + `scenario_context` + `ConceptPanel`
surface that every reasoning track already renders (so it inherits the calm, two-pane, Forest-&-Ink
look-and-feel unchanged — see CLAUDE.md §Design system).

## 3. Scope boundary — what this track owns vs. what already exists

The single biggest design risk is **duplicating reasoning the bank already teaches**. Product sense sits
next to four existing surfaces; the boundary that keeps it distinct:

| Adjacent surface | Owns | This track does NOT re-teach |
|---|---|---|
| **Experimentation** track | A/B *mechanics*: power, MDE, CUPED, SRM, sequential testing, causal identification (IV/DiD/RDD) | the statistical machinery of an experiment |
| **Statistics** track | inference, distributions, hypothesis testing, Bayesian | the math behind a claim |
| **SQL** track (`METRIC INTERPRETATION & DENOMINATOR CHOICE`, `FUNNEL ANALYSIS`, `COHORT RETENTION`) | *computing* a metric / funnel / cohort in a query | how to write the query |
| **ML Fundamentals** track | model choice, evaluation metrics, production trade-offs | model internals |

**This track owns the judgment layer that sits on top of all of them:** *what* to measure and why
(metric design), *why a number moved* (diagnosis), *which good to trade for which* (trade-offs),
*whether to ship* (the product decision on a result), and *how to structure an ambiguous product
question* (cases). Where it touches A/B testing, it owns only the **product-decision lens** ("given this
result and a guardrail regression, do you ship?") and explicitly hands the **mechanics** to
Experimentation. The boundary is enforced in the taxonomy by *naming the judgment family, never the
mechanic* (see [`03-concept-taxonomy.md`](03-concept-taxonomy.md) §Boundary co-tags).

## 4. Proposed standard attributes (the "everything standard for a track" checklist)

| Attribute | Proposal | Rationale |
|---|---|---|
| Track name | **Product Sense** (slug `product-sense`) | The universal round name candidates search for. Alternatives weighed in [`02-track-design.md`](02-track-design.md): *Metrics & Product Sense*, *Product Analytics*. |
| Roles | Data Scientist + Data Analyst | Both loops contain this round; the analyst loop arguably leans on it harder. |
| `eval_kind` | `mcq` | Constructed-reasoning, no execution (mirrors Experimentation/ML/PySpark/DE/DM). |
| `unlock_profile` | `mcq` | MCQ effort profile → the higher free-tier thresholds (10/17/25 · 12→5 cap), per [`backend/unlock.py`](../../../backend/unlock.py). |
| `in_mixed_mock` | `false` | Like the other reasoning tracks; role-Mixed benchmarks draw from their declared role pools, not the generic mixed pool. |
| Question types | `scenario` (dominant) · `conceptual` · `debug` · `predict_output` | Same four as Experimentation; `optimization`/`numerical` **excluded** (no compute to optimise, nothing numerical) — see [`02-track-design.md`](02-track-design.md) §Modality. `mcq` is the *response mechanism*, never a `type`. |
| Mock-only pool | **~100** = `mock-standalone` (~70) + `mock-chain` (~30 members / ~10 chains) | Two **separately balance-checked** draw surfaces — Benchmark/Custom vs Interview Loop ([`04`](04-difficulty-split.md) · [`06`](06-mock-and-interview-loops.md)). |
| ID range (TXNNN) | `T=?` — **needs a free digit** | Digits 1–9 are taken (see [`02-track-design.md`](02-track-design.md) §ID scheme); this is an open allocation question for whoever greenlights the track. |
| Datasets | none (no execution) | Scenarios are self-contained narratives, like Experimentation. |
| Hints | the active 1–3 hint ladder | Same hint discipline as every track. |
| Sample questions | 3 easy / 3 medium / 3 hard | The standard per-track sample allocation. |
| Concept families | ~16–20 (see taxonomy) | A tight, defensible registry. |
| Learning paths | 4–6 curated walks | Patterns (mastery walks), distinct from concept families. |
| Interview-loop chains | yes — uses the 8 universal pivots | The round naturally escalates ("…and now creator satisfaction dropped"). |

## 5. Package index

Each doc mirrors the structure of a real production track-design brief so this reads as a ready-to-build
package, not loose notes.

| Doc | Covers |
|---|---|
| [`01-external-research.md`](01-external-research.md) | The sourced online research digest — what the round actually tests, by company and by guide, with example questions and the framework inventory. |
| [`02-track-design.md`](02-track-design.md) | "What this track trains" framing, modality + the Phase-2 open-response note, difficulty model, authoring-allocation matrix, anti-patterns, ID-scheme open question. |
| [`03-concept-taxonomy.md`](03-concept-taxonomy.md) | The concept families (the backbone) with what-it-tests / question-shape / boundary co-tags, in the production registry format. |
| [`04-difficulty-split.md`](04-difficulty-split.md) | Easy/medium/hard reasoning ladder, per-tier allowed scenarios, the concept arc, and proposed practice + mock counts. |
| [`05-learning-paths.md`](05-learning-paths.md) | The curated pattern-paths (≠ concept families), with levels, focus_concepts, and outcomes. |
| [`06-mock-and-interview-loops.md`](06-mock-and-interview-loops.md) | Mock-only strategy under the **mock-never-introduces-an-untaught-concept** rule, benchmark shape, and the interview-loop chain designs with their pivots. |
| [`07-sample-questions.md`](07-sample-questions.md) | Illustrative authored-from-scratch example questions per concept × difficulty, showing the exact MCQ shape (these are *illustrations of the design*, not a content drop). |

---

*Produced by an Opus orchestration: three parallel Sonnet web-research agents gathered the external
material; Opus internalised the production track conventions (the Experimentation track doc as the
structural template, the 8 follow-up dimensions, the paths contract, the cross-track difficulty model)
and authored the synthesis. All example questions herein are illustrative and authored from scratch —
nothing is lifted from any source (the "never lift content" rule, applied even to research docs).*
