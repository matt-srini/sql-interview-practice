# 05 · Learning paths — Product Sense

> Research/proposal. Follows the canonical paths contract in
> [`content-authoring.md` §Learning paths](../../content-authoring.md#learning-paths-curated-sequences).
> **Paths are a different axis from concept families** — a *pattern* is the *practitioner skill* a path
> masters; a *concept family* is the *reasoning* a question exercises (and drives the dashboard +
> mock-focus). A path declares **both** `patterns[]` (what you pick up) and `focus_concepts[]` (which
> families it strengthens). These are *design proposals*: with no question bank yet, there is no
> `questions[]` list — that array is derived (5–9 questions, easy→hard) once the practice bank exists.

## Patterns to register (`path_patterns.py`, track `product-sense`)

Kebab-case practitioner-skill slugs — the *subject matter* a walk masters, deliberately coarser than the
18 concept families:

| Pattern slug | The practitioner skill |
|---|---|
| `metric-design` | Turn a goal into a defensible metric system (primary + guardrails + honest definition) |
| `metric-diagnosis` | Investigate "why did this metric move?" with a structured decomposition |
| `engagement-and-retention` | Read and act on engagement, stickiness, retention, and cohort signals |
| `funnel-analysis` | Read a conversion funnel and locate the drop-off worth attacking |
| `growth-reasoning` | Reason about growth loops, virality, and which growth lever is moving |
| `trade-offs-and-ship-decisions` | Resolve conflicting metrics and make a defensible ship/no-ship call |
| `metric-gaming` | Design metrics that resist gaming; reason about holistic product health |
| `product-cases` | Structure an open-ended product case end-to-end |
| `opportunity-sizing` | Size a market/opportunity to prioritise (Fermi / TAM-SAM-SOM) |

## Proposed paths (6)

Content-driven levels (≥1 foundational, enforced; the rest by what the content warrants). Acyclic
`recommended_after` graph. The 5–9 sweet spot governs the eventual `questions[]`.

### 1 · `metric-design-fundamentals` — **foundational** ("Start here")
- **patterns:** `metric-design`
- **focus_concepts:** `METRIC SELECTION & GOAL TRANSLATION` · `GUARDRAIL & COUNTER-METRIC REASONING` ·
  `METRIC DEFINITION INTEGRITY` · `BUSINESS-MODEL METRIC FLUENCY`
- **outcomes:** *You'll turn a vague product goal into a defensible measurement system — a primary metric,
  the guardrails that protect it, and a definition (unit, population, window) that means what you claim.*
- **recommended_after:** `[]`
- *The obvious entry point: every other path assumes you can pick and define a metric.*

### 2 · `diagnosing-a-metric-move` — **intermediate**
- **patterns:** `metric-diagnosis`
- **focus_concepts:** `METRIC MOVEMENT DIAGNOSIS` · `SEGMENTATION & DECOMPOSITION REASONING` ·
  `REAL-CHANGE VS ARTIFACT`
- **outcomes:** *You'll investigate "why did X move?" with a structured decomposition — ruling out
  instrumentation first, then localising the cause by segment, time, and formula — instead of guessing.*
- **recommended_after:** `[metric-design-fundamentals]` *(you must know what the metric is to diagnose it)*

### 3 · `engagement-retention-and-funnels` — **intermediate**
- **patterns:** `engagement-and-retention`, `funnel-analysis`
- **focus_concepts:** `ENGAGEMENT & STICKINESS REASONING` · `RETENTION & COHORT REASONING` ·
  `FUNNEL & CONVERSION REASONING` · `GROWTH & ACQUISITION REASONING`
- **outcomes:** *You'll read engagement, stickiness, retention-curve shape, funnel drop-off, and growth
  signals — and say what each implies for a product action.*
- **recommended_after:** `[metric-design-fundamentals]`
- *Spans two patterns legitimately (the contract permits it) — funnels and retention are one practitioner
  cluster in practice.*

### 4 · `trade-offs-and-the-ship-decision` — **advanced**
- **patterns:** `trade-offs-and-ship-decisions`
- **focus_concepts:** `CONFLICTING-METRIC & TRADE-OFF JUDGMENT` · `SHIP / NO-SHIP DECISION` ·
  `CAUSAL VS CORRELATIONAL JUDGMENT`
- **outcomes:** *You'll resolve two metrics moving opposite ways, weigh a two-sided trade-off, and make a
  defensible ship / no-ship / extend call on a compound result (guardrail regression, novelty, segment
  conflict) — the product decision, not the statistics.*
- **recommended_after:** `[metric-design-fundamentals, diagnosing-a-metric-move]`

### 5 · `metric-gaming-and-product-health` — **advanced**
- **patterns:** `metric-gaming`
- **focus_concepts:** `METRIC GAMING & ROBUSTNESS` · `PRODUCT HEALTH & STRATEGIC TRADE-OFFS`
- **outcomes:** *You'll design metrics a team can't game (Goodhart-robust, with counter-metrics) and
  reason about holistic product health, wellbeing/trust guardrails, and the goal-metric tension.*
- **recommended_after:** `[metric-design-fundamentals]`
- *The signature-hard cluster — the IC5/IC6-altitude reasoning Meta's Analytical Reasoning round probes.*

### 6 · `product-cases-and-opportunity-sizing` — **advanced**
- **patterns:** `product-cases`, `opportunity-sizing`
- **focus_concepts:** `PRODUCT CASE STRUCTURING` · `OPPORTUNITY SIZING & ESTIMATION` ·
  `BUSINESS-MODEL METRIC FLUENCY`
- **outcomes:** *You'll impose structure on an open product prompt (clarify → define success → decompose →
  recommend) and size an opportunity to prioritise it.*
- **recommended_after:** `[metric-design-fundamentals, engagement-retention-and-funnels]`
- *The synthesis path — `PRODUCT CASE STRUCTURING` composes the families the earlier paths drilled.*

## Path graph (recommended order)

```
            metric-design-fundamentals  (foundational · Start here)
            /            |            \
 diagnosing-a-    engagement-retention-   metric-gaming-and-
 metric-move      and-funnels             product-health
       \              /        \
   trade-offs-and-the-      product-cases-and-
   ship-decision            opportunity-sizing
```

Acyclic ✓ · one foundational ✓ · 2 intermediate · 3 advanced. Sized for a coherent first-pass curriculum;
more paths can split out later (e.g. `opportunity-sizing` standing alone) if the bank grows enough to
support a 5–9-question walk for each.

## Notes for the eventual build

- `questions[]` is **derived**, not hand-authored: each path's questions are the practice questions whose
  primary pattern routes to the path (the "route by objective, analytical wins" rule), sorted easy→hard.
  So the practice bank must exist first; these paths are the *target structure* it's authored toward.
- Every path question must carry a concept tag in one of the path's `focus_concepts[]` families (the
  mechanical "path drills what it claims" guarantee).
- Mock-only questions never appear in a path (pattern-paths are practice-only).
- A path unlocks nothing — unlocks are threshold-only (paths are curated walks over already-unlockable
  practice).
