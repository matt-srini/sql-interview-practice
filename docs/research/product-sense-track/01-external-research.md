# 01 · External research digest — Product Sense / Metrics

> Research/proposal. A synthesis of the online research that grounds this package — *what the round
> actually tests*, by company and by guide, the per-source taxonomies, the framework inventory, the
> rewarded-vs-failure patterns, and a representative example-question bank. Built from three parallel
> web-research passes (metric design + diagnosis; cases + sizing + trade-offs; per-source taxonomy +
> growth/funnel) plus company-loop breakdowns (Meta, Google, Uber, Airbnb). Sources at the foot.
>
> **The example questions below are real interview questions surfaced from public guides — they are
> here as *coverage evidence*, to verify the taxonomy isn't missing anything a senior round probes.
> They are NOT a content source: per the "never lift content" rule, every authored question is written
> from scratch against datathink framing (see [`07`](07-sample-questions.md)).**

---

## 1 · The round in the wild

Across the largest data-science employers, "product sense / metrics" is a **distinct, high-weight,
open-ended round** — and it's the round candidates most often fail (Airbnb guides: "most candidates who
fail the DS loop fail on product sense, not statistics"). It is the *data-driven* flavor (define and
diagnose **metrics**, reason to a **decision**) — not PM product-design/strategy. How it appears:

| Company | The round(s) | Character |
|---|---|---|
| **Meta** | **Analytical Execution** + **Analytical Reasoning** (two separate rounds) | Execution = a concrete product scenario, define metrics precisely + design/critique + recommend (SQL/Python often in scope). Reasoning = a *verbal, data-free, deliberately ambiguous* prompt; causal/system instincts, conflicting metrics, trade-offs; the interviewer adds constraints mid-conversation. IC4→IC6 raises altitude (single surface → cross-org durable measurement). |
| **Google** | **Product Sense & Metrics** (distinct from the stats/experimentation round) | Metric design for real products (Search/YouTube/Ads), HEART framework expected, multi-product trade-offs ("a change to Search that helps one KPI and hurts another"). |
| **Uber** | **Product / analytics case** (distinct from the stats round) | Marketplace-framed: "rider wait times +18%, investigate"; two-sided supply/demand trade-offs; clarify → primary + guardrails → methodology → limitations. |
| **Airbnb** | **Product Sense + Metrics** round (+ a take-home) | "What should we measure and why" for a two-sided marketplace; open-ended product situations; the round is ~40% of signal combined with experimentation. |

**The consistent shape:** an open-ended product situation → define what success means (metrics) → reason
about why a number moved or which trade-off to make → land a concrete recommendation. Graded on the
*thinking*, not a numeric answer.

## 2 · Per-source topic taxonomies (how the field carves it up)

The authoritative guides taxonomize the skill consistently; the differences are emphasis. Attributed:

| Source | Its taxonomy |
|---|---|
| **Emma Ding / Data Interview Pro** (360+ Qs, 46 companies) | 7 types by frequency: **Measure Success (23%)** · **A/B Testing (22%)** · **Diagnose a Problem (18%)** · Product-Specific (13%) · Improve a Product (10%) · Strategic Thinking (6%) · **Estimation (6%)**. |
| **RocketBlocks** | 4 drills: Assessing a Product (**TOFU** = Tech/Objects/Finance/Users, with **HEART** under Users) · Optimizing User Flows (funnels) · A/B Testing · Investigating Anomalies. |
| **StellarPeers** | 8 types: Behavioral · Brainstorming · **Estimation** · **Execution** · **Metrics** · Product Design · **Strategy** · Technical. (Metrics framework: North Star + Counter + Guardrail + Health.) |
| **Lewis Lin — "Decode and Conquer"** | **CIRCLES** (design) · **AARM** (Acquisition/Activation/Retention/Monetization — metrics & execution) · DIGS (behavioral). |
| **"Ace the DS Interview" (Singh & Huo)** | Ch 10 Product Sense (metrics central to KPIs ↔ business goals) + Ch 11 Case Studies ("the boss chapter" — open-ended, blends product + stats + SQL). |
| **Interview Query** | 3 categories: **Analyzing a Metric Problem** (most common) · **Measuring Impact of a New Feature** · **Designing a Product**. |
| **StrataScratch** (42-question bank) | 3 types: **Metric Investigation** · Product Design · **Metrics/Success Measurement**. |
| **Meta (Prepfully/IGotAnOffer)** | Execution: hypothesis framing, metric definition discipline, MDE/power-as-judgment, primary/guardrail selection, funnel+cohort. Reasoning: product-health, conflicting metrics, causal/systems thinking, bias/seasonality, privacy/constraint scenarios, trade-off recommendations. |

**The convergence:** every source has a **measure-success / metric-design** pillar, a **diagnose-a-metric**
pillar, and a **trade-off / decision** pillar — plus **estimation** as a small, recurring tail. That is the
spine of [`03-concept-taxonomy.md`](03-concept-taxonomy.md)'s 18 families.

## 3 · The synthesized concept surface

Consolidating ~74 micro-topics across the eight taxonomies yields these clusters (→ the 18 families in
[`03`](03-concept-taxonomy.md)):

- **Metric design** — what a good metric is (meaningful/measurable/moveable; vanity vs actionable;
  Goodhart-resistant); the metric *hierarchy* (north-star · primary/OEC · driver · guardrail · counter ·
  health; leading vs lagging; proxy validity); operationalisation (unit / population / denominator / window
  / aggregation); business-model alignment (marketplace/SaaS/ads/social/e-commerce).
- **Metric diagnosis** — clarify → real-vs-artifact (data-quality gate) → sudden-vs-gradual → internal-vs-
  external → **TROPICS** axes → formula decomposition (DAU = new+resurrected−churned) → segment localisation
  → seasonality (WoW/YoY) → related-metric coherence → hypothesis prioritise + validate; traps (mix-shift,
  denominator inflation, cannibalization, single-cause anchoring).
- **Engagement / retention / funnel / growth** — DAU/MAU stickiness + depth-vs-breadth + power-user curve;
  n-day vs rolling retention + cohort-curve shape + churn/resurrection; funnel drop-off (bottleneck vs
  opportunity); growth loops vs funnel + k-factor + growth accounting.
- **Trade-offs & ship decision** — conflicting metrics + competing user groups (two-sided) + time horizons;
  ship/no-ship under compound/novelty/guardrail-regressing results; prioritisation (RICE/ICE/value-effort);
  feature kill/sunset.
- **Causal & strategic judgment** — correlation-vs-causation traps + counterfactual reasoning; product
  health (portfolio view); wellbeing/trust/brand-safety guardrails; decision under incomplete info; the
  goal-metric tension.
- **Cases & sizing** — open case structuring (clarify→structure→analyse→recommend); estimation (top-down/
  bottom-up Fermi, TAM/SAM/SOM, sanity-check).

## 4 · Framework inventory (the scaffolds candidates are expected to wield)

These are *scaffolds for the candidate's reasoning*, never the answer — the track tests their **application**,
never their recall (the anti-pattern in [`02`](02-track-design.md)).

| Framework | One-line | Cluster |
|---|---|---|
| **HEART + GSM** (Google) | Happiness · Engagement · Adoption · Retention · Task-Success, via Goals-Signals-Metrics | metric design |
| **AARRR** ("pirate") | Acquisition · Activation · Retention · Referral · Revenue funnel | metric design / growth |
| **AARM** (Lewis Lin) | Acquisition · Activation · Retention · Monetization | metric design |
| **North Star + guardrails** | one value-proxy metric + must-not-degrade guardrails | metric design |
| **OEC** (Microsoft/Kohavi) | weighted composite primary that proxies the long-term goal | metric design |
| **GQM / GAME** | Goal → (Question/Action) → Metric → Evaluation | metric design |
| **3 Ms** | a good metric is Meaningful · Measurable · Moveable | metric design |
| **Goodhart's Law** | "when a measure becomes a target, it ceases to be a good measure" | gaming |
| **TROPICS** | Time · Region · Other-products · Platform · Industry · Cannibalization · Segmentation | diagnosis |
| **MECE issue tree** | mutually-exclusive, collectively-exhaustive decomposition (internal vs external first) | diagnosis |
| **Growth accounting** | end = start + new + resurrected − churned | growth/diagnosis |
| **CIRCLES** (Lewis Lin) | Comprehend·Identify·Report·Cut·List·Evaluate·Summarize | cases |
| **BUS** | Business objective · User problems · Solutions | cases |
| **RICE / ICE / MoSCoW / value-vs-effort** | prioritisation scores | trade-offs |
| **TAM / SAM / SOM**, top-down & bottom-up Fermi | market/opportunity sizing | sizing |

## 5 · What strong answers do (and the failure modes)

The rubric is remarkably consistent across Exponent, Emma Ding, DataInterview, Prepfully, Airbnb guides:

**Rewarded:**
- **Clarify before acting** — establish the metric formula, window, magnitude, and goal *first* (skipping
  this is the single most-penalised error).
- **Hierarchy, not a list** — one primary + one guardrail + one counter, defended — not six metrics with no
  priority.
- **Operationalise to formula level** — "songs added per user per week," with unit + window — not "songs added."
- **Data-quality gate first in diagnosis** — rule out instrumentation before any behavioural story.
- **Segment before concluding** — "is it concentrated or broad-based?" (most real root-causes are one segment).
- **Surface Goodhart / second-order effects unprompted.**
- **Name the trade-off explicitly and make a directional call** — don't average two conflicting metrics.
- **End on a concrete recommendation** — "if cause is X do Y; ship to 10% and watch guardrail Z for 2 weeks" —
  and treat **"don't ship," with rationale, as a strong, scorable answer**.

**Penalised:** metric lists without hierarchy · ignoring the business model · skipping clarifying questions ·
missing the data-quality gate · assuming broad-based without segmenting · single-cause anchoring ·
correlation→causation leaps · generic "casual/power user" segments with no operational definition · proposing
an A/B test as the *first* step of a *diagnosis* (a test designs a future intervention, it doesn't explain a
present drop) · analysis with no recommendation.

## 6 · Difficulty signals (corroborates [`04`](04-difficulty-split.md))

| Tier | Cue (cross-source) |
|---|---|
| **Easy** | single familiar product, single metric, clean criterion; "define a north star for X"; "estimate # of Y." |
| **Medium** | conflicting/compound metric or a first decomposition; full primary+guardrail stack; two-sided design; "metric dropped — investigate." |
| **Hard** | metric gaming / composite health metric; ship/no-ship on a compound result; multi-cause diagnosis with mix-shift/cannibalization; 3-stakeholder trade-off; no-comparable opportunity sizing; the goal-metric tension. |

## 7 · Representative example-question bank (coverage evidence — NOT a content source)

Surfaced from public guides, organised by family, to verify taxonomy coverage. *(Authored questions are
written from scratch — these are not to be reused; see the note at the top.)*

- **Metric design:** "How would you measure the success of [Save button / YouTube Shorts / Airbnb
  Experiences / a subscription product]?" · "Define a north star for a two-sided marketplace + its counter
  metric." · "Metrics to balance ad revenue vs user experience."
- **Diagnosis:** "[DAU / tweets / Uber Black rides / Reddit traffic] dropped X% — investigate." · "A spike in
  Yammer uploads in October — why?" · "Skype DAU *fell* when COVID started — why?" · "Privacy-respected up
  8% AND engagement down 14% — reconcile."
- **Engagement/retention/funnel:** "DAU/MAU is 0.18 — good?" · "D7 retention is 20% lower for one user type —
  what does the curve mean?" · "Map the app-open→purchase funnel; which drop-off first?" · "Users +15% but
  messages +3% — explain."
- **Trade-offs / ship:** "Engagement +8%, creator satisfaction −2% — launch?" · "Primary +4%, post-creation
  −2%, ads flat — ship?" · "Driver growth or rider growth this quarter?" · "Sunset Airbnb Experiences — what
  criteria?"
- **Causal / strategic:** "Weekend sellers sell 30% more — bonus them?" · "Define 'health' for Facebook
  Groups." · "Design success for a feature whose goal is to *reduce* time spent."
- **Sizing:** "How many Uber rides/day in the US?" · "Size the US food-delivery market." · "Opportunity for an
  in-app tipping feature at 50M MAU."

Every one maps to a family in [`03`](03-concept-taxonomy.md) and a tier in [`04`](04-difficulty-split.md) —
the coverage check passes (no surfaced archetype is un-homed).

## 8 · Scope boundary (the no-duplication map)

The single biggest design constraint — this track owns the **judgment layer**, neighbours own the mechanics:

| Question turns on… | …belongs to | Product Sense owns instead |
|---|---|---|
| computing power / MDE / SRM / CUPED / a causal estimator (IV/DiD) | **Experimentation** | *should we ship given the result*; *is this action resting on a correlation* |
| deriving a statistic / distribution / CI | **Statistics** | *what the number means for the product* |
| writing the cohort / funnel / segmentation query | **SQL** | *reading + acting on* the output; *which definition makes it meaningful* |
| choosing/evaluating a model | **ML Fundamentals** | (n/a) |

**Defining test:** if a candidate could answer by computing, deriving, or querying, it's a neighbour's
question — move it. Product Sense questions are answered by *judgment* alone.

---

## Sources

*Company loops:* [Prepfully — Meta DS Analytical Execution](https://prepfully.com/interview-guides/meta-ds-analytical-execution) · [Prepfully — Meta DS Analytical Reasoning](https://prepfully.com/interview-guides/meta-ds-analytical-reasoning) · [IGotAnOffer — Meta DS](https://igotanoffer.com/blogs/tech/facebook-data-scientist-interview) · [Exponent — Google DS](https://www.tryexponent.com/guides/google-data-scientist-interview) · [IGotAnOffer — Uber DS](https://igotanoffer.com/en/advice/uber-data-scientist-interview) · [Prepfully — Uber DS](https://prepfully.com/interview-guides/uber-data-scientist-) · [InterviewQuery — Airbnb DS](https://www.interviewquery.com/interview-guides/airbnb-data-scientist) · [CodingInterview — Airbnb DS](https://www.codinginterview.com/guide/airbnb-data-scientist-interview/)

*Taxonomies & frameworks:* [Emma Ding — 7 Types of Product Case Questions](https://www.emmading.com/blog/how-to-ace-the-7-types-of-product-case-interview-questions) · [Emma Ding — Cracking Business Case Interviews Pt 1](https://towardsdatascience.com/the-ultimate-guide-to-cracking-business-case-interviews-for-data-scientists-part-1-cb768c37edf4/) · [Pt 2](https://towardsdatascience.com/the-ultimate-guide-to-cracking-business-case-interviews-for-data-scientists-part-2-7bc38fbe635f/) · [RocketBlocks — Product Execution (TOFU/HEART)](https://www.rocketblocks.me/guide/pm/product-execution-interviews.php) · [RocketBlocks — Success Metrics](https://www.rocketblocks.me/blog/success-metrics-pm-interviews.php) · [StellarPeers — Metrics Framework](https://stellarpeers.com/framework-collection/generic-metrics/) · [Lewis Lin — CIRCLES & Metrics](https://www.lewis-lin.com/blog/circles-framework-and-metrics) · [Ace the Data Science Interview](https://www.acethedatascienceinterview.com/) · [Interview Query — Product DS Interview](https://www.interviewquery.com/p/product-data-science-interview) · [StrataScratch — Types of Product-Sense Questions](https://www.stratascratch.com/blog/types-of-product-sense-questions-in-data-science-interviews/) · [StrataScratch — 42 Product Questions](https://www.stratascratch.com/blog/42-data-science-product-interview-questions) · [Exponent — Product Sense Prep](https://www.tryexponent.com/blog/product-sense-interview) · [DataInterview — Product DS Prep](https://www.datainterview.com/blog/product-data-scientist-interview-prep) · [Aakash Gupta — Product Metrics (GAME)](https://www.news.aakashg.com/p/product-metrics-interview)

*Diagnosis, metrics theory, estimation, trade-offs:* [TDS — Metric-Change Ultimate Guide (TROPICS)](https://towardsdatascience.com/answering-the-data-science-metric-change-interview-question-the-ultimate-guide-5e18d62d0dc6/) · [Sequoia — Seasonal Factors](https://articles.sequoiacap.com/metrics-seasonal-factors) · [Meta Analytics — How (Not) to Use Proxy Metrics](https://medium.com/@AnalyticsAtMeta/dont-be-seduced-by-the-allure-a-guide-for-how-not-to-use-proxy-metrics-in-experiments-9530caa0eb7c) · [Mixpanel — Guardrail Metrics](https://mixpanel.com/blog/guardrail-metrics/) · [TDS — Goodhart's Law & A/B Testing](https://towardsdatascience.com/goodharts-law-and-the-dangers-of-metric-selection-with-a-b-testing-91b48d1c1bef/) · [Reforge — North Star Metrics](https://www.reforge.com/blog/north-star-metrics) · [Microsoft Research — OEC / North Star](https://www.microsoft.com/en-us/research/articles/experimentation-and-the-north-star-metric/) · [Google Research — HEART](https://research.google/pubs/measuring-the-user-experience-on-a-large-scale-user-centered-metrics-for-web-applications/) · [StellarPeers — Estimation Framework](https://stellarpeers.com/framework-collection/generic-estimation/) · [DataInterview — Estimation & Fermi Questions](https://www.datainterview.com/blog/estimation-and-fermi-interview-questions) · [IGotAnOffer — Prioritization & Trade-off](https://igotanoffer.com/blogs/product-manager/prioritization-and-trade-off-interview-questions) · [Lenny's Newsletter — Analytical Thinking Interviews](https://www.lennysnewsletter.com/p/the-definitive-guide-to-mastering-f81) · [kojino — 120 DS Questions: Product Metrics](https://github.com/kojino/120-Data-Science-Interview-Questions/blob/master/product-metrics.md)

*(Accessed 2026-06; URLs may drift — the synthesis, not any single page, is the durable artifact.)*
