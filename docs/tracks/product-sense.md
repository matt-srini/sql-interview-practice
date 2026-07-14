# Product Sense Track

> **Authoring rule, no exceptions:** Every Product Sense question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/product_sense_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working data scientist or analyst is paid, more than for any single query or model, to answer three questions a product team cannot answer for itself: **what should we measure, why did the number move, and is the trade-off worth it.** Product sense is where that judgment is graded directly. The candidate who can compute DAU is everywhere; the one who can say *"DAU is up but sessions-per-user are down, so before we celebrate I'd want to know whether we've added low-intent users or cannibalised the power users — those imply opposite product actions"* is the one whose analysis a PM will actually act on.

This track trains the reasoning *underneath* the metric, not the metric's arithmetic (that lives in SQL) or the experiment's statistics (that lives in Experimentation):

- **Metric design** — turning a vague goal ("make Stories better") into a defensible measurement system: a primary/success metric, guardrails, counter-metrics, and the unit/population/window that make the number mean what you claim. Recognising vanity, proxy-gaming, and Goodhart risk.
- **Metric diagnosis** — given a metric that moved, decomposing the cause MECE-style (real change vs instrumentation; internal vs external; by segment / time / region / platform / funnel-stage) instead of guessing.
- **Trade-off & ship judgment** — choosing between competing goods (engagement vs revenue; one side of a two-sided marketplace vs the other; short-term lift vs long-term retention) and deciding whether a result — including a flat, conflicting, or guardrail-regressing one — justifies shipping.
- **Structured product cases** — taking an ambiguous, data-free product prompt and imposing a structure (clarify → define success → decompose → recommend) that a stakeholder can follow.

> *Datathink philosophy applied:* this is the round that most embodies "develop the kind of reasoning that makes someone genuinely effective in a data-driven world — understands what question is really worth asking and how the answer should inform a decision" (north-star). It earns its place on reasoning depth, not on interview frequency.

## Modality

**Constructed reasoning.** No execution. Response: MCQ (4 options). `eval_kind: mcq`.

Product sense is a textbook *Constructed reasoning* track — "analyse a scenario, design, tradeoff, or result and commit to a justified answer" — the same family as Experimentation / Data Engineering / Data Modeling. It is **not executable**: nothing here is computed (the computation lives in SQL / Statistics), so there is **no numerical subtype and no code editor**.

Question types:
- **`scenario`** — *the dominant type.* A `scenario_context` carries a real product situation (a metric read, a feature decision, a marketplace tension); the prompt asks for the call/diagnosis/decision. Expect a heavy scenario skew (Experimentation runs ~72% scenario in mock-only).
- **`conceptual`** — a product-reasoning principle anchored in a brief scenario ("which of these is the better *guardrail* for a notifications launch, and why").
- **`debug`** — critique flawed product/metric *reasoning*: a gameable metric, a denominator that hides the effect, a correlation-treated-as-causal leap, a diagnosis that skipped the instrumentation check. "Find the flaw."
- **`predict_output`** — *the smallest type,* scoped precisely as **forward outcome prediction**: given a stated product change, predict which metrics move and in which direction. Tests the candidate's behavioural/causal model; genuinely distinct from `scenario` (which hands you the result and asks for judgment).

**Two valid types are deliberately EXCLUDED:**

- **`optimization`** — a code-adjacent type. A judgment round has nothing to optimise for compute; "improve this weak metric/analysis" already lives in `debug`/`scenario`. Excluded.
- **`numerical`** — Statistics' code-execution subtype. No computation is the skill here. Excluded.

**Phase-2 open-response extension (out of scope for v1, recorded for completeness).** The one thing scenario-MCQ cannot do is make a candidate *generate* a metric system or case structure from a blank page. A future modality — a short rubric-graded free-text response scored against a rubric rather than a single key — would close that gap. It needs an evaluation harness the platform does not yet have, so it is **explicitly deferred**. v1 ships as MCQ, exactly as Experimentation does for the equally-open A/B-judgment skill.

## ID range (TXNNN scheme)

`T=10` for Product Sense (two-character leading digit; a deliberate scheme extension — digits 1–9 are all assigned to the nine existing tracks).

| Difficulty | ID range | File |
|---|---|---|
| Easy | 101001–101999 | `backend/content/product_sense_questions/easy.json` |
| Medium | 102001–102999 | `backend/content/product_sense_questions/medium.json` |
| Hard | 103001–103999 | `backend/content/product_sense_questions/hard.json` |

Product Sense has **dedicated sample questions** in `backend/content/sample_questions/product-sense.json` (IDs 1011–1013 easy, 1021–1023 medium, 1031–1033 hard). Sample questions are completely separate from the practice and mock pools and must never duplicate practice content.

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | One concept, a clear best answer | Pick a sensible success metric for a stated goal; name a guardrail; read a simple one-direction metric movement; identify a vanity metric; basic funnel stage; leading vs lagging; the right unit of analysis for one stated question; business-model vocabulary |
| **Medium** | A trade-off or a first decomposition; tempting distractors | Two metrics move in conflict (engagement ↑, session length ↓) — which read is right; first-step diagnosis of a metric drop (decompose by segment/time/instrumentation before concluding); choose a denominator that doesn't hide the effect; basic two-sided trade-off (host vs guest); is this movement real or an instrumentation artifact; which estimation approach is sound |
| **Hard** | Multi-factor judgment; all distractors defensible | Metric gaming / Goodhart (which metric survives an adversarial team); composite "health" metric design with conflicting inputs; ship/no-ship on a result with a guardrail regression + novelty suspicion; full diagnosis under conflicting signals + seasonality + a privacy/measurement constraint; multi-stakeholder trade-off where the technical answer and the deliverable diverge; new-market measurement with no clean baseline |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses framework-name recall. Even easy questions are anchored in a real product decision.

| Tier | Representative scenarios |
|---|---|
| **Easy** | "A team ships a 'Save for later' button — pick the single best success metric." · "Which of these is a *guardrail* you'd watch, not a success metric?" · "Notifications sends doubled and opens rose — which read is premature?" · "Is 'total signups' a vanity or an actionable metric for this goal?" |
| **Medium** | "Engagement is up 8% but time-per-session is down 4% after a feed change — what's the most defensible interpretation?" · "Daily orders dropped 6% on Tuesday — what's the first thing you check, and why not the metric itself?" · "Marketplace GMV is up but host churn ticked up — which guardrail matters and what's the trade-off?" · "A conversion-rate denominator change made the funnel 'improve' — what actually happened?" |
| **Hard** | "Design a single 'creator health' metric that a growth team can't game by spamming low-value posts." · "An A/B shows +5% bookings, −2% repeat-rate, and a flat NPS guardrail after 10 days — ship, kill, or extend, and why?" · "Reels watch-time fell only in India during a festival week with a known logging gap — separate the real signal." · "Two metrics say opposite things about the same launch and leadership wants to ship Friday — frame the decision." |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | What a good metric is (success vs guardrail vs vanity) → unit/population/window basics → leading vs lagging → reading a single, unambiguous metric movement → one funnel stage → business-model vocabulary |
| Medium | Conflicting-metric interpretation → first-pass metric diagnosis (segment/time/instrumentation decomposition) → denominator & definition traps → basic two-sided / counter-metric trade-offs → real-vs-artifact distinction → which estimation approach is sound |
| Hard | Metric gaming & Goodhart-robust design → composite/health-metric systems → ship/no-ship judgment under conflicting + guardrail-regressing results → full multi-cause diagnosis (seasonality, selection, measurement constraint) → multi-stakeholder trade-offs & the deliverable problem → opportunity sizing for prioritisation |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Product Sense section](../concept-taxonomy.md#product-sense--concept-families).

**18 families** — tight and defensible. The external research surfaced ~74 distinct micro-topics across 8 source taxonomies; these consolidate following the Experimentation precedent ("tightest registry in the bank"). The registry is flat; the groupings below are for readability.

### §A — Metric design (4 families)

**`METRIC SELECTION & GOAL TRANSLATION`** — turning a vague product goal into a defensible *primary / success* metric; connecting a user action to a business objective; recognising when a metric is representative + actionable vs a vanity restatement of the goal. Easy → medium.

**`GUARDRAIL & COUNTER-METRIC REASONING`** — the metric *system*, not the single number: distinguishing primary vs guardrail vs counter vs health metric; choosing the guardrail that would actually catch the disqualifying side effect; leading vs lagging. Easy → medium.

**`METRIC GAMING & ROBUSTNESS`** — Goodhart's law in practice: which metric survives an adversarial team optimising for it; designing a metric (or a counter-metric pair) that resists gaming. **A signature hard-tier family.** Medium → hard.

**`METRIC DEFINITION INTEGRITY`** — the choices that decide whether a metric *means what you claim*: unit of analysis (user vs session vs impression vs creator), population/denominator boundaries, time window, and how a composite metric can move for numerator *or* denominator reasons. Medium → hard. *Boundary:* SQL's `METRIC INTERPRETATION & DENOMINATOR CHOICE` owns *computing* the metric; this family owns *choosing the definition for meaning*.

### §B — Metric diagnosis (3 families)

**`METRIC MOVEMENT DIAGNOSIS`** — the structured investigation of "metric X moved Y% — why?": clarify the metric + magnitude + window → form MECE hypotheses → decide what to check first → validate. Rewards a *structured decomposition* over a guessed cause. Medium → hard.

**`SEGMENTATION & DECOMPOSITION REASONING`** — whether a movement is *global or concentrated*: breaking a metric down by segment (platform / region / cohort age / user type / channel) to localise a cause; Simpson's-paradox awareness (the aggregate can move opposite to every segment); when "the segment that moved *is* the diagnosis." Medium → hard.

**`REAL-CHANGE VS ARTIFACT`** — before believing a number, ruling out the *measurement* explanation: instrumentation / logging gap / a release / a definition change; separating internal causes from external ones (seasonality, competitor action, macro event); sudden-vs-gradual as a tell. Medium → hard. *Boundary:* the *skepticism* sibling of SQL's `DATA QUALITY SKEPTICISM`, applied to a business metric's *interpretation*, not a query's correctness.

### §C — Engagement, retention & funnel reasoning (3 families)

**`FUNNEL & CONVERSION REASONING`** — reading a funnel as a sequence of conversion steps; locating the actionable drop-off (bottleneck vs biggest-opportunity distinction: a 50% drop at a low-volume step can matter less than a 5% drop at a high-volume one); proposing where to intervene. Easy (read one stage) → hard (prioritise interventions across segments). *Boundary:* SQL owns `FUNNEL ANALYSIS` (the query); this family owns *which* step matters and *what to do*.

**`RETENTION & COHORT REASONING`** — interpreting retention: n-day (classic, bounded) vs rolling (unbounded) and when each flatters/penalises a product; reading a cohort curve shape (a healthy plateau vs continued decline); diagnosing "drop in all cohorts (product change) vs only new cohorts (acquisition/onboarding quality)." Medium → hard. *Boundary:* SQL owns `COHORT RETENTION` (the query); this family owns *reading and acting on* the table.

**`ENGAGEMENT & STICKINESS REASONING`** — DAU/WAU/MAU and the DAU/MAU stickiness ratio (benchmark is product-category-dependent); breadth (sessions/user) vs depth (actions/session) and how they can diverge; the power-user curve as a diagnostic; spotting engagement *inflated by notifications*. Easy (define) → hard (interpret a divergence).

### §D — Growth reasoning (1 family)

**`GROWTH & ACQUISITION REASONING`** — growth *loops* (compounding) vs the linear funnel; k-factor / virality conceptually (k = invites × invitee-conversion; k>1 is viral; why burst virality ≠ sustained); the growth-accounting identity (end = start + new + resurrected − churned) to localise which lever drives a change; channel quality (which channel yields high-LTV cohorts). Medium → hard.

### §E — Trade-offs & the ship decision (2 families)

**`CONFLICTING-METRIC & TRADE-OFF JUDGMENT`** — resolving competing signals: two metrics moving opposite ways, two user groups (two-sided marketplace host/guest, creator/viewer, driver/rider), or two time horizons (short-term lift vs long-term retention/LTV). Rewards naming the trade-off explicitly and choosing a defensible hierarchy for *this* goal, not picking the bigger number. **A signature family of the track.** Medium → hard.

**`SHIP / NO-SHIP DECISION`** — the *product decision* on a result, not the statistics: practical vs statistical significance; novelty-effect / decay suspicion (short-window social wins fade); a guardrail regression that gates a positive primary; reversibility + blast radius in the call. **A signature family of the track.** Medium → hard. *Boundary:* Experimentation owns *how to run/measure the test correctly* (power, SRM, CUPED, correction); this family owns *given the result, should you ship and why*. A question that turns on computing power or detecting SRM is Experimentation's; a question that turns on the launch judgment is this track's.

### §F — Causal & strategic judgment (2 families)

**`CAUSAL VS CORRELATIONAL JUDGMENT`** — the product-lens version of causal reasoning: spotting the "X correlates with good outcome, so incentivise X" trap (the "weekend sellers have 30% higher sales — bonus them?" archetype: self-selection, not causation); reasoning about the right counterfactual/control population; anticipating second-order effects of a change. Medium → hard. *Boundary:* Experimentation/Statistics own the *identification machinery* (IV, DiD, propensity); this family owns the *judgment* that a proposed action rests on a correlation.

**`PRODUCT HEALTH & STRATEGIC TRADE-OFFS`** — holistic product-health reasoning (no single metric; a portfolio view); wellbeing / brand-safety / equity / trust metrics as guardrails in consumer products (incl. the goal-metric *tension* case — "the explicit goal is to *reduce* time spent; define success"); decision-making under incomplete information; when the technically-right answer and the deliverable diverge. Hard only. **The IC5/IC6-level family.**

### §G — Cases & sizing (2 families)

**`PRODUCT CASE STRUCTURING`** — imposing structure on an ambiguous, data-free product prompt: clarify → define success → decompose → recommend; keeping the structure stable as the interviewer adds constraints mid-stream. The synthesis family — it composes the others. Medium → hard.

**`OPPORTUNITY SIZING & ESTIMATION`** — Fermi / market-/opportunity-sizing reasoning: top-down vs bottom-up decomposition, making + defending assumptions, sanity-checking the order of magnitude; used to *prioritise* ("is this worth building?"). Medium → hard.

### §H — Applied context (1 family)

**`BUSINESS-MODEL METRIC FLUENCY`** — knowing the metric vocabulary a business model lives by: marketplace (GMV, take rate, liquidity, supply/demand balance, per-side retention); SaaS (MRR/ARR, NRR, churn, LTV:CAC); ad-supported (CPM, CTR, fill rate); social/content (creation rate, virality, creator retention); e-commerce (AOV, repeat-purchase, cart abandonment). Usually a **co-tag** on a metric-design or diagnosis question; occasionally primary ("which metric is the marketplace's liquidity signal?"). Easy (vocab) → medium (apply to a tension).

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One concept, clean: pick a metric, name a guardrail, read one movement. |
| Practice medium | `medium.json` no `mock_only` | A trade-off or a first decomposition under realistic product framing. |
| Practice hard | `hard.json` no `mock_only` | Gaming-robust design, composite metrics, ship judgment, full diagnosis. |
| Mock-only medium | `medium.json` `mock_only: true` | Fresh, named-product scenarios that **recombine** taught medium reasoning under stakeholder pressure ("your launch read conflicts and the PM wants to ship in 3 days"). |
| Mock-only hard | `hard.json` `mock_only: true` | Advanced trade-off / diagnosis / gaming scenarios at recombination depth — never a new concept. Heavy `SHIP / NO-SHIP DECISION`, `CONFLICTING-METRIC & TRADE-OFF JUDGMENT`, `METRIC MOVEMENT DIAGNOSIS`, `METRIC GAMING & ROBUSTNESS`, `PRODUCT HEALTH & STRATEGIC TRADE-OFFS`. |
| Mock-only chain | parent + 1–3 follow-ups | Interview-loop escalations: a metric-design parent that pivots to *business_rule* (the goal changes), *stakeholder* (leadership pushes back), *data_quality* (a logging gap surfaces). See [`docs/research/product-sense-track/06-mock-and-interview-loops.md`](../research/product-sense-track/06-mock-and-interview-loops.md). |

**Easy mock-only: never** (practice-only, like every track). **Mock-only never introduces an untaught concept** — the governing rule. Every mock-only question must recombine reasoning the practice bank already teaches at that difficulty or lower. A mock idea that would need an untaught family requires the practice question to be authored first.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and stakeholder realism, not new concepts. A strong mock-only question reads like a slice of a real Analytical-Execution round: *"Reels watch-time is +4%, original-post creation is −2%, ads-revenue-per-session is flat after 9 days, and leadership wants a Friday decision — what's your call?"* — every reasoning move in it was taught separately in practice; mock recombines them under time pressure.

## Anti-patterns specific to Product Sense

This round's realism is also its biggest authoring hazard — it is the easiest track to write *badly*.

- **Framework-name recall.** "What does the H in HEART stand for?" / "Name the steps of CIRCLES." Reject. Frameworks are scaffolding for the candidate's reasoning, never the answer. Test the *application* (which guardrail, which decomposition), never the vocabulary.
- **Drifting into PM product-design / strategy.** "Design a new feature for Instagram." "What's Uber's go-to-market?" That is the PM interview, not the DS/analyst product-*metrics* round. Every question must stay anchored in **measurement, metrics, and data-driven judgment** — the data flavor.
- **One famous right answer.** At hard tier, every distractor must reflect a position a competent practitioner could defend (a different-but-reasonable metric, a plausible-but-incomplete diagnosis). No "obvious correct + three strawmen."
- **Opinion masquerading as judgment.** The correct option must be defensible on a stated *reasoning* ground (this metric is harder to game; this decomposition rules out the cheaper hypothesis first), not on taste. If two options are both defensible and the "key" is just a preference, the question is invalid (the cross-track "multiple defensible interpretations → reject" rule).
- **Re-teaching a neighbour track.** A question whose actual skill is "compute the retention query" (SQL), "calculate the power" (Experimentation/Stats), or "pick the model" (ML) belongs in that track. Product Sense questions own the *judgment* layer; they may *reference* a number but never *test its derivation*. Enforced via boundary co-tags in the taxonomy.
- **Numbers that don't add up.** Scenario metrics (lifts, segment splits, funnel rates) must be internally consistent and plausible for the named product — the same realism bar Experimentation holds for sample sizes and p-values.
- **Concept over-tagging — tag what the *key* actually tests.** Product Sense's rich metric vocabulary makes it the easiest track to *over-tag*: attaching a concept family the question's **keyed reasoning** never exercises. A tag belongs only if the correct answer's discriminator (and its refutation of the distractors) turns on that family — not if the family merely flavours a distractor, sits in the scenario as context, or is a reflexive co-tag. Recurring false co-tags to reject: `METRIC MOVEMENT DIAGNOSIS` / `REAL-CHANGE VS ARTIFACT` bolted onto any "a metric changed" scenario that already gives the cause or tests a single shape-tell (no clarify→hypothesise→validate step); `CONFLICTING-METRIC & TRADE-OFF JUDGMENT` wherever "trade-off" appears in prose but no competing goods are weighed into a hierarchy; `SHIP / NO-SHIP DECISION` used as launch-deadline *dressing* on a question whose real flaw is self-selection; `GROWTH & ACQUISITION REASONING` on a "referral/invite" topic with no k-factor/loop mechanics; `BUSINESS-MODEL METRIC FLUENCY` when the business-model term appears only in a refuted option. Mock questions recombine 2+ families *in the scenario*, but never force a second tag — one accurate tag beats two where one is theatre. (Audit precedent: 2026-07-14 mock over-tag sweep, DECISIONS.md.)
- **Experiment-terminology precision.** Product Sense references experiments (holdouts, treatment/control, guardrails) while Experimentation owns their mechanics — but the vocabulary must still be correct. A **holdout** is the group *withheld* from the change (kept on control), never the group receiving the new version (that is the **treatment / test group**). Loose A/B terminology reads as a tell to a strong candidate.
- **Difficulty-drift via family.** Easy questions must not use the diagnosis/gaming/composite families (those are medium/hard). One concept at easy, by family, not just by prose:
  - **Easy (permitted):** `METRIC SELECTION & GOAL TRANSLATION`, `GUARDRAIL & COUNTER-METRIC REASONING`, `ENGAGEMENT & STICKINESS REASONING` (define only), `FUNNEL & CONVERSION REASONING` (read one stage), `BUSINESS-MODEL METRIC FLUENCY` (vocab).
  - **Medium (permitted):** first decomposition / first trade-off families — `METRIC MOVEMENT DIAGNOSIS`, `SEGMENTATION & DECOMPOSITION REASONING`, `REAL-CHANGE VS ARTIFACT`, `CONFLICTING-METRIC & TRADE-OFF JUDGMENT`, `SHIP / NO-SHIP DECISION`, `RETENTION & COHORT REASONING`, `METRIC DEFINITION INTEGRITY`, `CAUSAL VS CORRELATIONAL JUDGMENT`, `GROWTH & ACQUISITION REASONING`, `OPPORTUNITY SIZING & ESTIMATION`, `PRODUCT CASE STRUCTURING`, `METRIC GAMING & ROBUSTNESS` (introductory only).
  - **Hard (required):** advanced or multi-factor treatment of the above — plus `METRIC GAMING & ROBUSTNESS` (adversarial / composite design), `PRODUCT HEALTH & STRATEGIC TRADE-OFFS` (hard-only).

## JSON schema

```json
{
  "id": 102007,
  "order": 7,
  "topic": "product-sense",
  "type": "scenario",
  "difficulty": "medium",
  "title": "Engagement up, session length down after a feed change — what's the read?",
  "scenario_context": "A team reranked the home feed. Week over week: daily active users +3%, posts viewed per session +9%, average session length −6%, 7-day retention flat. The PM reads this as a clear win and wants to ship to 100%.",
  "description": "Which interpretation is the most defensible before shipping?",
  "options": [
    "The result is a clear win — all engagement metrics moved in the right direction, and session length is a lagging indicator that will correct over time.",
    "This is ambiguous without knowing *why* session length fell — if users are finding content faster, shorter sessions are fine; if they're leaving dissatisfied, they're not.",
    "The flat 7-day retention is the decisive guardrail: engagement gains with no retention benefit suggest the change is attracting low-intent sessions, not improving the product.",
    "Wait two more weeks before deciding — novelty effects can inflate post views and DAU in the first week, so the read may not be stable yet."
  ],
  "correct_option": 2,
  "explanation": "Option C is correct: flat 7-day retention is the guardrail that gates this decision. Engagement is up but retention — the indicator that users found enough value to come back — did not improve. That pattern is consistent with the change attracting low-intent browsing sessions: more scrolls, shorter dwell, no loyalty gain. Before shipping to 100% on this read, that tension needs an explanation. Option A treats all engagement metrics as equivalent, session length and retention carry different structural weight. Option B frames the ambiguity correctly but stops short — the flat retention already points to a concrete direction. Option D's novelty-effect caution is valid reasoning but weaker here than a direct retention signal; extending the test with no hypothesis risks an undirected wait.",
  "hints": [
    "Two of these metrics point to engagement; one is a retention guardrail. Which is structurally different?",
    "More posts viewed in less time can mean *better* feed quality or *shallower* sessions. What's the metric that would distinguish them?"
  ],
  "concepts": ["CONFLICTING-METRIC & TRADE-OFF JUDGMENT", "GUARDRAIL & COUNTER-METRIC REASONING"]
}
```

Required:
- Exactly 4 options, each ≥ 20 characters.
- Explanation refutes every distractor with a specific reasoning ground.
- Scenarios use plausible, internally consistent metrics — lifts, segment splits, and rates that match the named product's scale.
- `scenario_context` carries all the numbers; `description` asks the call. No definition-recall as the discriminator.

## Coverage & sizing target

| Metric | Value |
|---|---|
| Practice questions | **87** (30 easy / 33 medium / 24 hard) |
| Mock-only — `mock-standalone` | **~70** (0 easy / ~33 medium / ~37 hard) |
| Mock-only — `mock-chain` (members) | **~30** from **~10 chains** (0 easy / ~12 medium / ~18 hard) |
| Mock-only total | **~100** (0 easy / ~45 medium / ~55 hard) |
| Mock / practice ratio | **~1.15×** (mid-band) |
| Sample questions | **9** (3/3/3) |
| Concept families | **18** |
| Learning paths | **7** (3 foundational / 1 intermediate / 3 advanced) |
| `eval_kind` | `mcq` |
| `unlock_profile` | `mcq` |
| `in_mixed_mock` | `false` |
| `mixed_subtype` | `false` |
| Roles | Data Scientist · Data Analyst |
| Track color | `#8E3B6E` (Mulberry) |
| Validator gate | Add to `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py` when the bank is authored |

**Type mix target in mock-only:** `scenario` dominant (~70% — the Experimentation precedent), `debug` (~15–18%, flawed product/metric arguments), `predict_output` (~10–12%, forward outcome prediction), `conceptual` minimal at medium/hard (the round is situational). Chains are scenario-led.

**Per-tier family placement (gated — difficulty-drift via family is an anti-pattern):**

| Family | Easy | Medium | Hard |
|---|:--:|:--:|:--:|
| METRIC SELECTION & GOAL TRANSLATION | ● | ● | |
| GUARDRAIL & COUNTER-METRIC REASONING | ● | ● | |
| METRIC DEFINITION INTEGRITY | | ● | ● |
| BUSINESS-MODEL METRIC FLUENCY | ● (vocab) | ● (apply) | co-tag |
| ENGAGEMENT & STICKINESS REASONING | ● (define) | ● | ● |
| FUNNEL & CONVERSION REASONING | ● (one stage) | ● | ● |
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
| METRIC GAMING & ROBUSTNESS | | ● (intro) | ● |
| PRODUCT HEALTH & STRATEGIC TRADE-OFFS | | | ● |

Easy is deliberately narrow — only the four "what is a good metric" families + the read-one-funnel / define-engagement / business-vocabulary entries. Everything that requires a *tree* (diagnosis), a *trade-off* (competing goods), or *adversarial* thinking (gaming) starts at medium. `METRIC GAMING & ROBUSTNESS` enters at medium in **introductory** form (which of two candidate metrics is more gameable, and why — recognition, not design) and reaches its signature depth (adversarial / composite metric design) at hard. `PRODUCT HEALTH & STRATEGIC TRADE-OFFS` is the one hard-only signature family.

## Benchmark shape per difficulty

The Product Sense benchmark blueprint is derived from the on-disk bank (bank shape governs blueprint — see [`docs/specs/mock-benchmark-spec.md` § Blueprint feasibility](../specs/mock-benchmark-spec.md)). These are **authoring targets**; the final blueprint is set against the real bank once authored and registered in `backend/routers/mock.py` `_benchmark_type_targets`. Canonical doc render: [`docs/features/mock.md` § Benchmark composition](../features/mock.md).

| Difficulty | Blueprint target (6 slots) | Notes |
|---|---|---|
| Easy | `scenario × 3 + conceptual × 2 + predict_output × 1` | No `debug` if the easy bank has too few; easy scenarios are clean + one-concept |
| Medium | `scenario × 4 + debug × 1 + predict_output × 1` | Heavy scenario skew intentional — operational product judgment grades cleanest as scenario MCQ |
| Hard | `scenario × 4 + debug × 2` | Scenario-dominant + debug (flawed reasoning critiques); predict_output if the bank supports it |

Final shape follows the bank — never author a type just to fill a slot.

## Mock-only & interview-loop chains

Full contract (chain atomicity, session gating, consent-gated replay): [`docs/features/mock.md`](../features/mock.md).

**The subset rule.** Every mock-only question — standalone *or* chain — must recombine a concept family the practice bank has already taught at that difficulty or lower. If a mock scenario would rely on an untaught family, author the practice question first. This rule is load-bearing: product-sense scenarios are *seductive* and it is easy to write a great mock case that quietly relies on a reasoning move the practice bank never showed the user.

**The two draw surfaces.** The ~100 mock-only questions are **not one pool** — they split into two separately-balanced draw surfaces:

| Sub-pool | Target count (E / M / H) | Drawn by | Shape |
|---|---|---|---|
| **`mock-standalone`** | **~70** (0 / ~33 / ~37) | **Benchmark** + **Custom** (Pro+) | self-contained single questions |
| **`mock-chain`** | **~30 members** from **~10 chains** (0 / ~12 / ~18) | **Interview Loop** (Elite) only | atomic parent→follow-up chains |

**Balance-check each surface separately** (the dilution trap: a biased chain pool hides when averaged into the combined group). Run `scripts/check_batch_balance.py` on the standalone batch *and* on the chain batch separately (position ≤40%, unique-longest ≤45%). Per the cross-track validator state, `mock-chain` starts WARN-level; `mock-standalone` / `practice` / `sample` are ERROR-level.

**Interview-loop chains (Elite only).** Product Sense is an *excellent* fit for chains — the real Analytical-Reasoning round literally *is* an interviewer adding constraints mid-conversation ("…now suppose creator satisfaction also dropped…"), which is exactly the chain shape. Chains use the **8 universal follow-up dimensions** unchanged (no new dimension needed). Richest pivots for this track:

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

Target: **~10 chains (~30 members)**. Chain length 2–4 (parent + 1–3 follow-ups); 3-question chains (parent + 2 follow-ups, 45 min per Loop session) are the sweet spot. Difficulty same-or-escalating along the chain. Consecutive follow-ups must differ in dimension. Chains are mock-only and never enter a learning path.

**Choose the dimension by the pivot's *reasoning*, not its surface topic.** A follow-up that reveals a **confounding sub-population** ("the fast responders are actually property-management bots") is an `edge_case_pivot` — a special segment that changes whether the conclusion generalises — **not** a `data_quality_pivot`, which is specifically a logging / instrumentation / measurement problem. A follow-up that swaps the **reference class or benchmark** used to interpret a number ("benchmark this against a daily-utility product instead") is closest to `abstraction_pivot` (it moves the frame of comparison); it is **not** a `business_rule_pivot`, since no goal or rule changed. There is no dedicated "reframe-the-benchmark" dimension — `abstraction_pivot` is its intended home. (Audit precedent: 2026-07-14, DECISIONS.md.)

Full chain designs (8 illustrative + 2 more toward the ~10 target): [`docs/research/product-sense-track/06-mock-and-interview-loops.md`](../research/product-sense-track/06-mock-and-interview-loops.md).

## Learning paths

Full paths contract: [`docs/content-authoring.md` §Learning paths](../content-authoring.md#learning-paths-curated-sequences). Paths are **not** concept-family lists — they are curated question walks through a *pattern* (practitioner skill). A path declares one or more `patterns[]` (registered in `backend/path_patterns.py`), a `level`, and `focus_concepts[]`; `questions[]` is derived once the bank exists. **Size: sweet spot 5–9, default cap 15** (16–20 by explicit per-path approval; absolute floor 3). **A path's `level` is its position in the prerequisite arc, not the difficulty of its questions** — a foundational path routinely spans easy→medium→hard (see [`DECISIONS.md`](../decisions/DECISIONS.md) 2026-06-08 "Path levels are content-driven" + 2026-07-14).

**7 paths — 3 foundational / 1 intermediate / 3 advanced** (the validator enforces ≥1 foundational; all levels uncapped). The count follows where the 87 practice questions land, not one-path-per-pattern: five patterns are individually rich enough for their own path, while `growth-reasoning`, `product-cases`, and `opportunity-sizing` are intentionally light (curriculum weight follows reasoning surface, per CLAUDE.md) and **bundle** rather than distort the count allocation. A structural consequence of the narrow easy tier — only `metric-design`, `engagement-and-retention`, and `funnel-analysis` carry easy questions — is that **the three foundational paths are exactly the three easy-bearing patterns**: the entry points hold the easy on-ramps, and every intermediate/advanced path is legitimately medium/hard. `questions[]` is finalized (Phase 5, 2026-07-14) — the seven `backend/content/paths/*.json` files are the SoT: 74 of 87 practice questions allocated across the 7 paths (13 intentionally catalog-only), no split needed.

| Path slug | Level | Patterns | Focus concepts | Note (span · final size, Phase 5) |
|---|---|---|---|---|
| `metric-design-fundamentals` | **foundational** | `metric-design` | METRIC SELECTION & GOAL TRANSLATION · GUARDRAIL & COUNTER-METRIC REASONING · METRIC DEFINITION INTEGRITY · BUSINESS-MODEL METRIC FLUENCY | Primary entry point — every other path assumes you can pick and define a metric. Easy (pick / guardrail) → hard (definition integrity). **13**. |
| `engagement-and-retention` | **foundational** | `engagement-and-retention` | ENGAGEMENT & STICKINESS REASONING · RETENTION & COHORT REASONING · BUSINESS-MODEL METRIC FLUENCY | Reading engagement (DAU / stickiness) and retention / cohort curves. Easy (define engagement) → hard (interpret a divergence, read a cohort curve). No prerequisite. **12**. |
| `funnels-and-growth-loops` | **foundational** | `funnel-analysis`, `growth-reasoning` | FUNNEL & CONVERSION REASONING · GROWTH & ACQUISITION REASONING · BUSINESS-MODEL METRIC FLUENCY | Reading a funnel plus the acquisition / growth-loop layer. Easy (read one stage) → hard (prioritise interventions, growth accounting). `growth-reasoning` bundles here rather than starving as a thin standalone. **13**. |
| `diagnosing-a-metric-move` | intermediate | `metric-diagnosis` | METRIC MOVEMENT DIAGNOSIS · SEGMENTATION & DECOMPOSITION REASONING · REAL-CHANGE VS ARTIFACT · CAUSAL VS CORRELATIONAL JUDGMENT | The "number moved — why?" investigation. Builds on a foundational metric grounding. Medium → hard. **13**. |
| `trade-offs-and-the-ship-decision` | advanced | `trade-offs-and-ship-decisions` | CONFLICTING-METRIC & TRADE-OFF JUDGMENT · SHIP / NO-SHIP DECISION · CAUSAL VS CORRELATIONAL JUDGMENT | Weigh competing goods; decide ship / no-ship. Builds on design + diagnosis. Medium → hard. **10**. |
| `metric-gaming-and-product-health` | advanced | `metric-gaming` | METRIC GAMING & ROBUSTNESS · PRODUCT HEALTH & STRATEGIC TRADE-OFFS | The signature-hard cluster — IC5/IC6-altitude reasoning. Medium → hard. **8**. |
| `product-cases-and-opportunity-sizing` | advanced | `product-cases`, `opportunity-sizing` | PRODUCT CASE STRUCTURING · OPPORTUNITY SIZING & ESTIMATION · BUSINESS-MODEL METRIC FLUENCY | Synthesis path — case structuring composes the earlier families; `opportunity-sizing` bundles here (both light patterns). Medium → hard. **5**. |

**Acyclic prereq graph** (Phase 5 final). The three foundational paths — `metric-design-fundamentals`, `engagement-and-retention`, `funnels-and-growth-loops` — are the no-prerequisite entry points (each a "Start here"). `diagnosing-a-metric-move` (intermediate) builds on that metric grounding; the three advanced paths — `trade-offs-and-the-ship-decision`, `metric-gaming-and-product-health`, `product-cases-and-opportunity-sizing` — build on diagnosis (and, for trade-offs, on design). Acyclic by construction.

**Size-driven flex — Phase 5 outcome: no split needed.** `engagement-and-retention` was curated to 12 (not split into `engagement-and-stickiness` + `retention-and-cohorts`); all seven paths land inside the 5–15 range. The floor-of-3 discipline held: the three light patterns (`growth-reasoning`, `product-cases`, `opportunity-sizing`) bundle so no path starves — `growth-reasoning` rides inside `funnels-and-growth-loops` and `opportunity-sizing` inside `product-cases-and-opportunity-sizing`, each promotable to its own walk once the bank supports 5+ questions.

Mock-only questions never appear in a path. A path unlocks nothing — question access follows the plan policy (free = easy; Pro/Elite = all difficulties).

## Boundary co-tags

This track's entire reason to exist is the *judgment layer*; its entire authoring risk is sliding into a neighbour's *mechanic*. The rule: a question belongs in Product Sense only if its *discriminator* is the product judgment. If a candidate could answer it by computing a value, deriving a statistic, or writing a query, it belongs in SQL / Statistics / Experimentation.

| This family | Shares an edge with | The line — this track owns the left; the neighbour owns the right |
|---|---|---|
| `SHIP / NO-SHIP DECISION` | **Experimentation** (A/B mechanics) | *should we ship given the result* ↔ *is the test designed / powered / valid* |
| `CAUSAL VS CORRELATIONAL JUDGMENT` | **Experimentation / Statistics** | *is this action resting on a correlation* ↔ *the IV/DiD/propensity estimator* |
| `METRIC DEFINITION INTEGRITY` | **SQL** (`METRIC INTERPRETATION & DENOMINATOR CHOICE`) | *which definition makes the metric mean what we claim* ↔ *how to compute it* |
| `FUNNEL & CONVERSION REASONING` | **SQL** (`FUNNEL ANALYSIS`) | *which step to attack, what to do* ↔ *the funnel query* |
| `RETENTION & COHORT REASONING` | **SQL** (`COHORT RETENTION`) | *reading + acting on the cohort table* ↔ *the cohort query* |
| `REAL-CHANGE VS ARTIFACT` | **SQL** (`DATA QUALITY SKEPTICISM`) | *is the business metric's movement real* ↔ *is the query/data correct* |

## Verification before commit

```bash
cd backend && ../.venv/bin/python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k product-sense
```
