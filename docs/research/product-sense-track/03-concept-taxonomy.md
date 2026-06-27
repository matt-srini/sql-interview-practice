# 03 · Concept taxonomy — Product Sense

> Research/proposal. Format mirrors [`docs/concept-taxonomy.md`](../../concept-taxonomy.md) per-track
> registries (family name · what it tests · typical question shape · difficulty placement · boundary
> co-tags). If greenlit, these families move into `docs/concept-taxonomy.md` and
> `backend/concept_families.py` *first* (the "new families require a PR to this file first" rule), before
> any question is tagged.

**Modality:** Constructed reasoning · `eval_kind: mcq` · question `type`s: `scenario` (dominant) ·
`conceptual` · `debug` · `predict_output` (see [`02`](02-track-design.md) §Modality — `optimization` and
`numerical` are deliberately excluded). **Reasoning archetype:** decide *what to measure and why*,
*why a number moved*, and *which good to trade for which* — the judgment layer on top of the data, never
its computation.

**Design discipline.** The external research surfaced ~74 distinct micro-topics across 8 source
taxonomies ([`01-external-research.md`](01-external-research.md)). Following the Experimentation
precedent (24 families is "the tightest registry in the bank"), those consolidate into **18 families** —
tight enough to be a real diagnostic on the dashboard, granular enough that each names a distinct
reasoning move. The families are grouped below by sub-skill for readability; the registry itself is flat.

---

## §A — Metric design (4 families)

#### `METRIC SELECTION & GOAL TRANSLATION`
**What it tests:** turning a vague product goal ("make Stories better") into a defensible *primary /
success* metric; connecting a user action to a business objective; recognising when a metric is
representative + actionable vs a vanity restatement of the goal.
**Typical question shape:** "A team ships feature X to achieve goal G — pick the success metric that best
captures G" (easy) → "the obvious metric has a fatal flaw; pick the better one and say why" (medium).
**Difficulty:** easy → medium.

#### `GUARDRAIL & COUNTER-METRIC REASONING`
**What it tests:** the metric *system*, not the single number — distinguishing primary vs guardrail vs
counter vs health metric; choosing the guardrail that would actually catch the disqualifying side effect;
leading vs lagging.
**Typical question shape:** "which of these is the *guardrail* you'd watch, not a success metric?" ·
"the success metric is X — name the counter-metric that protects against gaming it."
**Difficulty:** easy → medium.

#### `METRIC GAMING & ROBUSTNESS`
**What it tests:** Goodhart's law in practice — which metric survives an adversarial team optimising for
it; spotting the proxy that a team can inflate without delivering real value; designing a metric (or a
counter-metric pair) that resists gaming.
**Typical question shape:** "design a 'creator health' metric a growth team can't game by spamming
low-value posts" (hard) · "this metric went up — could a team hit it without the product getting better?"
**Difficulty:** medium → hard. **A signature hard-tier family.**

#### `METRIC DEFINITION INTEGRITY`
**What it tests:** the choices that decide whether a metric *means what you claim* — unit of analysis
(user vs session vs impression vs creator), population/denominator boundaries, time window, and how a
composite metric (CTR = clicks/impressions) can move for numerator *or* denominator reasons.
**Typical question shape:** "a denominator change made the funnel 'improve' — what actually happened?" ·
"per-user or per-session for this question, and why does it change the read?"
**Boundary co-tag:** touches SQL's `METRIC INTERPRETATION & DENOMINATOR CHOICE` — but SQL owns *computing*
the metric; this owns *choosing the definition for meaning*. Test the choice, never the query.
**Difficulty:** medium → hard.

## §B — Metric diagnosis (3 families)

#### `METRIC MOVEMENT DIAGNOSIS`
**What it tests:** the structured investigation of "metric X moved Y% — why?": clarify the metric +
magnitude + window → form MECE hypotheses → decide what to check first → validate. Rewards a *structured
decomposition* over a guessed cause.
**Typical question shape:** "daily orders dropped 6% on Tuesday — what's the first thing you check, and
why not the metric itself?" The structured-investigation family (the TROPICS / clarify→hypothesise→
validate spine).
**Difficulty:** medium → hard.

#### `SEGMENTATION & DECOMPOSITION REASONING`
**What it tests:** whether a movement is *global or concentrated* — breaking a metric down by segment
(platform / region / cohort age / user type / channel) to localise a cause; Simpson's-paradox awareness
(the aggregate can move opposite to every segment); when "the segment that moved *is* the diagnosis."
**Typical question shape:** "watch-time fell only in one region during a known event — separate signal
from noise" · "every segment improved but the aggregate fell — explain."
**Difficulty:** medium → hard.

#### `REAL-CHANGE VS ARTIFACT`
**What it tests:** before believing a number, ruling out the *measurement* explanation — instrumentation
/ logging gap / a release / a definition change — and separating internal causes from external ones
(seasonality, competitor action, macro event); sudden-vs-gradual as a tell (a step change smells like a
release/bug; a drift smells like behaviour).
**Typical question shape:** "the metric jumped exactly at the deploy — real or artifact?" · "is this dip
a product change or a holiday?"
**Boundary co-tag:** the *skepticism* sibling of SQL's `DATA QUALITY SKEPTICISM`, but applied to a
business metric's *interpretation*, not a query's correctness.
**Difficulty:** medium → hard.

## §C — Engagement, retention & funnel reasoning (3 families)

#### `FUNNEL & CONVERSION REASONING`
**What it tests:** reading a funnel as a sequence of conversion steps; locating the actionable drop-off
(the bottleneck-vs-biggest-opportunity distinction: a 50% drop at a low-volume step can matter less than
a 5% drop at a high-volume one); proposing where to intervene.
**Typical question shape:** "map the app-open → purchase funnel; which drop-off would you attack first
and why?"
**Boundary co-tag:** SQL owns `FUNNEL ANALYSIS` (the query); this owns *which* step matters and *what to do*.
**Difficulty:** easy (read one stage) → hard (prioritise interventions across segments).

#### `RETENTION & COHORT REASONING`
**What it tests:** interpreting retention — n-day (classic, bounded) vs rolling (unbounded) and when each
flatters/penalises a product; reading a cohort table's *shape* (a healthy "smile" plateau vs continued
decline); diagnosing "drop in all cohorts (product change) vs only new cohorts (acquisition/onboarding
quality)"; churn and resurrection.
**Typical question shape:** "D7 retention for one user type is 20% lower — what does the curve shape tell
you, and what next?"
**Boundary co-tag:** SQL owns `COHORT RETENTION` (the query); this owns *reading and acting on* the table.
**Difficulty:** medium → hard.

#### `ENGAGEMENT & STICKINESS REASONING`
**What it tests:** DAU/WAU/MAU and the DAU/MAU stickiness ratio (and why the benchmark is
product-category-dependent — a daily utility ≠ a travel app); breadth (sessions/user) vs depth
(actions/session) and how they can diverge; the power-user curve as a diagnostic; spotting engagement
*inflated by notifications* ("active because pushed" vs "active because wanted").
**Typical question shape:** "DAU/MAU is 0.18 — good? what would you want to know first?" · "engagement is
up but it's all from re-engagement pushes — is that a win?"
**Difficulty:** easy (define) → hard (interpret a divergence).

## §D — Growth reasoning (1 family)

#### `GROWTH & ACQUISITION REASONING`
**What it tests:** growth *loops* (compounding) vs the linear funnel; k-factor / virality conceptually
(k = invites × invitee-conversion; k>1 is viral; why burst virality ≠ sustained); the growth-accounting
identity (end = start + new + resurrected − churned) to localise *which lever* drives a change; channel
quality (which channel yields high-LTV cohorts).
**Typical question shape:** "users grew 15% but messages grew 3% — which growth lever explains it?" ·
"at what point is k<1 not a crisis for this referral loop?"
**Difficulty:** medium → hard.

## §E — Trade-offs & the ship decision (2 families)

#### `CONFLICTING-METRIC & TRADE-OFF JUDGMENT`
**What it tests:** resolving competing signals — two metrics moving opposite ways, two user groups
(two-sided marketplace host/guest, creator/viewer, driver/rider), or two time horizons (short-term lift
vs long-term retention/LTV). Rewards naming the trade-off explicitly and choosing a defensible hierarchy
for *this* goal, not picking the bigger number.
**Typical question shape:** "engagement +8% but creator satisfaction −2% — launch?" · "GMV up, host churn
up — which wins and why?"
**Difficulty:** medium → hard. **A signature family of the track.**

#### `SHIP / NO-SHIP DECISION`
**What it tests:** the *product decision* on a result (NOT the statistics): practical vs statistical
significance ("+0.1% on 100M users — worth the eng cost + tech debt?"); novelty-effect / decay suspicion
(short-window social wins fade); a guardrail regression that gates a positive primary; "10 variants, one
won at p<0.05" read as a *product* risk, not a stats lecture; reversibility + blast radius in the call.
**Typical question shape:** "+5% bookings, −2% repeat-rate, flat NPS after 10 days — ship, kill, or
extend?" · "your colleague says 'significant, ship it' — what do you ask first?"
**Boundary co-tag:** the most-overlapping family with Experimentation. The rule: Experimentation owns
*how to run/measure the test correctly* (power, SRM, CUPED, correction); this owns *given the result,
should you ship and why*. A question that turns on computing power or detecting SRM is Experimentation's;
a question that turns on the launch judgment is this track's. Never test the mechanic here.
**Difficulty:** medium → hard. **A signature family of the track.**

## §F — Causal & strategic judgment (2 families)

#### `CAUSAL VS CORRELATIONAL JUDGMENT`
**What it tests:** the product-lens version of causal reasoning — spotting the "X correlates with good
outcome, so incentivise X" trap (the "weekend sellers have 30% higher sales — bonus them?" archetype:
self-selection, not causation); reasoning about the right counterfactual/control population; anticipating
second-order effects and unintended consequences of a change.
**Boundary co-tag:** Experimentation/Statistics own the *identification machinery* (IV, DiD, propensity,
confounder/collider classification); this owns the *judgment* that a proposed action rests on a
correlation and what would be needed to believe it. Test the trap-recognition, never the estimator.
**Difficulty:** medium → hard.

#### `PRODUCT HEALTH & STRATEGIC TRADE-OFFS`
**What it tests:** holistic product-health reasoning (no single metric; a portfolio view); wellbeing /
brand-safety / equity / trust metrics as guardrails in consumer products (incl. the goal-metric *tension*
case — "the explicit goal is to *reduce* time spent; define success"); decision-making under incomplete
information (what you know vs what you'd need); when the technically-right answer and the deliverable
diverge (stakeholder reality).
**Typical question shape:** "define 'health' for Facebook Groups" · "design success metrics for a feature
whose goal is to reduce usage" · "leadership wants to ship Friday on conflicting evidence — frame it."
**Difficulty:** hard. **The IC5/IC6-level family** (Meta's framing: cross-org, durable measurement).

## §G — Cases & sizing (2 families)

#### `PRODUCT CASE STRUCTURING`
**What it tests:** imposing structure on an ambiguous, data-free product prompt — clarify → define
success → decompose → recommend; "improve product X" as segment → pain-point → solution → instrument-it;
keeping the structure stable as the interviewer adds constraints mid-stream (the Meta Analytical-Reasoning
dynamic). The synthesis family — it composes the others.
**Typical question shape (as MCQ):** "given this open product prompt, which *first move* best structures
it?" · "the interviewer just added a constraint — which adjustment keeps the analysis coherent?"
**Difficulty:** medium → hard.

#### `OPPORTUNITY SIZING & ESTIMATION`
**What it tests:** Fermi / market-/opportunity-sizing reasoning — top-down vs bottom-up decomposition,
making + defending assumptions, sanity-checking the order of magnitude; used to *prioritise* ("is this
worth building?").
**Typical question shape (as MCQ):** "which estimation approach is sound for sizing X?" · "which of these
assumption sets is internally consistent?" · "this estimate is off by ~100× — which assumption broke?"
**Difficulty:** medium → hard. *(Lower-frequency in DS loops — ~6% per Emma Ding — so a small family.)*

## §H — Applied context (1 family)

#### `BUSINESS-MODEL METRIC FLUENCY`
**What it tests:** knowing the metric vocabulary a business model lives by, so a candidate reaches for the
right one: marketplace (GMV, take rate, liquidity, supply/demand balance, per-side retention); SaaS
(MRR/ARR, NRR, churn, LTV:CAC); ad-supported (CPM, CTR, fill rate, advertiser-ROI vs user-experience);
social/content (creation rate, virality, creator retention); e-commerce (AOV, repeat-purchase, cart
abandonment).
**Typical question shape:** usually a **co-tag** on a metric-design or diagnosis question set in a named
business model; occasionally primary ("which metric is the marketplace's liquidity signal?").
**Difficulty:** easy (vocabulary) → medium (apply to a tension). Often co-tagged, rarely the sole skill.

---

## §Boundary — the families that share an edge with another track

This track's entire reason to exist is the *judgment layer*; its entire authoring risk is sliding into a
neighbour's *mechanic*. The boundary co-tags above are the discipline. Summary:

| This family | Shares an edge with | The line (this track tests the left, the neighbour tests the right) |
|---|---|---|
| `SHIP / NO-SHIP DECISION` | Experimentation (A/B mechanics) | *should we ship given the result* ↔ *is the test designed/powered/valid* |
| `CAUSAL VS CORRELATIONAL JUDGMENT` | Experimentation / Statistics | *is this action resting on a correlation* ↔ *the IV/DiD/propensity estimator* |
| `METRIC DEFINITION INTEGRITY` | SQL (`METRIC INTERPRETATION & DENOMINATOR CHOICE`) | *which definition makes the metric mean what we claim* ↔ *how to compute it* |
| `FUNNEL & CONVERSION REASONING` | SQL (`FUNNEL ANALYSIS`) | *which step to attack, what to do* ↔ *the funnel query* |
| `RETENTION & COHORT REASONING` | SQL (`COHORT RETENTION`) | *reading + acting on the cohort table* ↔ *the cohort query* |
| `REAL-CHANGE VS ARTIFACT` | SQL (`DATA QUALITY SKEPTICISM`) | *is the business metric's movement real* ↔ *is the query/data correct* |

**Authoring rule (load-bearing):** a question belongs in Product Sense only if its *discriminator* is the
product judgment. If a candidate could answer it by computing a value, deriving a statistic, or writing a
query, it belongs in SQL / Statistics / Experimentation — move it. (This mirrors content-authoring's
"re-teaching a neighbour track" anti-pattern; here it is the track's defining constraint.)

## §Cross-track reuse

Per [`concept-taxonomy.md` §Cross-track family naming reusability](../../concept-taxonomy.md), a family
*name* may recur across tracks when the *reasoning* is the same. Candidates for shared names with other
reasoning tracks: `SEGMENTATION & DECOMPOSITION REASONING` (cf. Experimentation `SEGMENTATION ANALYSIS`)
and the `METRIC …` family stems. When this track is registered, reconcile these names deliberately with
the existing registry rather than minting near-duplicates — the registrar's call at greenlight time.

## §Follow-up dimensions (for interview-loop chains)

Chains use the **8 universal follow-up dimensions** unchanged (no new dimension is needed — the audit
that produced this package confirmed the existing 8 cover product-sense escalations cleanly). The
natural pivots for this track:

| Dimension | Product-sense escalation angle |
|---|---|
| `business_rule_pivot` | "Leadership just redefined the goal — does your success metric still hold?" |
| `stakeholder_pivot` | "The PM/exec pushes to ship despite the guardrail — frame the push-back." |
| `data_quality_pivot` | "A logging gap surfaced for the window you diagnosed — salvage the read." |
| `scale_pivot` | "Same question, but now across 30 markets at 100× the users — what changes?" |
| `ambiguity_pivot` | "Define 'engagement' for this — I'm not giving you one." |
| `edge_case_pivot` | "The segment driving the metric is 0.5% of users — does your conclusion survive?" |
| `abstraction_pivot` | "Generalise: what *class* of metric is always vulnerable to this gaming?" |
| `performance_pivot` | *Least natural here* — the round isn't compute-bound; use sparingly. |

Full chain designs in [`06-mock-and-interview-loops.md`](06-mock-and-interview-loops.md).
