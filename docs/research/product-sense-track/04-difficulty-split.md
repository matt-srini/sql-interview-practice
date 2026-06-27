# 04 · Difficulty split — Product Sense

> Research/proposal. Applies the cross-track [difficulty model](../../content-authoring.md#difficulty-model-cross-track)
> (Easy = one concept · Medium = a trade-off / "which tool fits" · Hard = layered, dependent reasoning,
> all distractors defensible) to this track's families ([`03`](03-concept-taxonomy.md)). Difficulty is
> **reasoning depth**, never the number of sub-questions or framework-name obscurity. Every external
> source converges on the same arc: single metric → trade-offs/diagnosis → gaming/multi-stakeholder/
> composite ([`01`](01-external-research.md)).

## The ladder

| Tier | Reasoning shape | What the candidate does |
|---|---|---|
| **Easy** | One concept, a clear best answer | Recognise the sensible metric / the right guardrail / the obvious vanity metric / the correct unit; read a single, one-direction metric movement; identify one funnel stage. No trade-off, no diagnosis tree, no gaming. |
| **Medium** | A trade-off, or a *first* decomposition; tempting distractors | Resolve two conflicting signals; take the defensible *first* diagnostic step (decompose before concluding); pick a denominator that doesn't hide the effect; weigh a basic two-sided trade-off; separate real change from artifact. |
| **Hard** | Multi-factor judgment; every distractor defensible | Design a gaming-robust / composite metric; make a ship/no-ship call on a compound result (guardrail regression + novelty + segment conflict); run a full multi-cause diagnosis under seasonality + a measurement constraint; resolve a 3-stakeholder trade-off; size a no-comparable opportunity. |

## Per-tier family placement

Families are **gated by tier** (the Experimentation precedent: easy questions may not use medium/hard
families — difficulty drift via family is an anti-pattern). Proposed placement:

| Family ([`03`](03-concept-taxonomy.md)) | Easy | Medium | Hard |
|---|:--:|:--:|:--:|
| METRIC SELECTION & GOAL TRANSLATION | ● | ● | |
| GUARDRAIL & COUNTER-METRIC REASONING | ● | ● | |
| METRIC DEFINITION INTEGRITY | | ● | ● |
| BUSINESS-MODEL METRIC FLUENCY | ● (vocab) | ● (apply) | (co-tag) |
| ENGAGEMENT & STICKINESS REASONING | ● (define) | ● | ● |
| FUNNEL & CONVERSION REASONING | ● (read one stage) | ● | ● |
| RETENTION & COHORT REASONING | | ● | ● |
| METRIC MOVEMENT DIAGNOSIS | | ● | ● |
| SEGMENTATION & DECOMPOSITION REASONING | | ● | ● |
| REAL-CHANGE VS ARTIFACT | | ● | ● |
| GROWTH & ACQUISITION REASONING | | ● | ● |
| CONFLICTING-METRIC & TRADE-OFF JUDGMENT | | ● | ● |
| OPPORTUNITY SIZING & ESTIMATION | | ● | ● |
| PRODUCT CASE STRUCTURING | | ● | ● |
| CAUSAL VS CORRELATIONAL JUDGMENT | | ● | ● |
| SHIP / NO-SHIP DECISION | | ● | ● |
| METRIC GAMING & ROBUSTNESS | | | ● |
| PRODUCT HEALTH & STRATEGIC TRADE-OFFS | | | ● |

**Easy is deliberately narrow** — only the four "what is a good metric" families + the read-one-funnel /
define-engagement / business-vocabulary entries. Everything that requires a *tree* (diagnosis), a
*trade-off* (competing goods), or *adversarial* thinking (gaming) starts at medium. The two
signature-hard families (gaming, product-health/strategic) are hard-only.

## Allowed business scenarios per tier

The construct list above says *what families are in bounds*; this says *what the question should feel
like* (both gate the question, per the difficulty model).

- **Easy:** "pick the success metric for this feature/goal" · "which is the guardrail, not the success
  metric" · "is this a vanity or actionable metric" · "read this one-direction movement" · "what's the
  right unit of analysis here" · "what's the marketplace's liquidity metric." *Familiar consumer products
  (Spotify, Instagram, Netflix); one metric; clean criterion.*
- **Medium:** "two metrics conflict — which read is right" · "metric dropped — what's the defensible first
  check" · "design success + 1 guardrail for a launch" · "basic two-sided trade-off" · "is this movement
  real or an artifact" · "which estimation approach is sound." *Multiple plausible reads; one trade-off
  or one decomposition.*
- **Hard:** "design a gaming-robust / composite health metric" · "ship/no-ship on a compound result" ·
  "full diagnosis under seasonality + a logging gap + segment conflict" · "three-stakeholder trade-off
  with a deliverable problem" · "define success when the goal is to *reduce* a metric" · "size a
  no-comparable opportunity." *Layered, dependent reasoning; every option defensible.*

## Concept arc (early → late)

Reproduced from [`02`](02-track-design.md) for completeness:

| Tier | Progression |
|---|---|
| Easy | what a good metric is (success vs guardrail vs vanity) → unit/population/window basics → leading vs lagging → reading one unambiguous movement → one funnel stage → business-model vocabulary |
| Medium | conflicting-metric interpretation → first-pass diagnosis (segment/time/instrumentation) → denominator & definition traps → basic two-sided / counter-metric trade-offs → real-vs-artifact → which estimation approach |
| Hard | gaming & Goodhart-robust design → composite/health-metric systems → ship/no-ship under conflicting + guardrail-regressing results → full multi-cause diagnosis → multi-stakeholder trade-offs & the deliverable problem → no-comparable opportunity sizing |

## Proposed counts

Sized to the reasoning-track norm (Experimentation 87 practice / 104 mock-only; ML 100/143). Easy is
practice-only (no easy mock-only, every track). A **v1 authoring target** (content-driven in the end —
bank shape governs blueprint):

| | Easy | Medium | Hard | Total |
|---|--:|--:|--:|--:|
| **Practice** | ~30 | ~33 | ~24 | **~87** |
| **Mock-only** | 0 | ~45 | ~55 | **~100** |
| **Sample** | 3 | 3 | 3 | **9** |

- Mock/practice ratio ≈ **1.15×** (mid-band; chains included).
- The medium/hard mock skew is intentional — this round is hardest at the judgment-dense end, and the
  signature hard families (gaming, product-health, ship-decision) are where mock pressure adds the most.
- Per the **subset rule** ([`06`](06-mock-and-interview-loops.md)), every mock-only question recombines a
  *practice-taught* family at that difficulty or lower — so the practice bank must cover each family at
  the difficulty its mock questions assume *before* those mock questions are authored.

## Difficulty anti-drift checks (at authoring time)

- No easy question may carry a medium/hard-only family (`METRIC MOVEMENT DIAGNOSIS`, `SEGMENTATION &
  DECOMPOSITION REASONING`, `METRIC GAMING & ROBUSTNESS`, `SHIP / NO-SHIP DECISION`, etc.).
- "You can make it harder by *removing* a clarification" → it was ambiguous, not hard. Reject.
- A hard question whose correct option is the only defensible one is mis-tiered (it's easy/medium). At
  hard, every distractor is a position a competent practitioner could argue.
- Run the dumb-baseline balance checks (position ≤40%, unique-longest ≤45%) on every MCQ batch — the
  cross-track guard applies here unchanged.
