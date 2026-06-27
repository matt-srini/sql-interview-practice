# 02 · Track design — Product Sense

> Research/proposal. Mirrors the section structure of a production track doc
> ([`docs/tracks/experimentation.md`](../../tracks/experimentation.md) is the structural template —
> the closest analog: a constructed-reasoning, scenario-MCQ, interview-loop-bearing judgment track).

## What this track trains

A working data scientist or analyst is paid, more than for any single query or model, to answer three
questions a product team cannot answer for itself: **what should we measure, why did the number move,
and is the trade-off worth it.** Product sense is where that judgment is graded directly. The candidate
who can compute DAU is everywhere; the one who can say *"DAU is up but sessions-per-user are down, so
before we celebrate I'd want to know whether we've added low-intent users or cannibalised the power
users — those imply opposite product actions"* is the one whose analysis a PM will actually act on.

This track trains the reasoning *underneath* the metric, not the metric's arithmetic (that lives in SQL)
or the experiment's statistics (that lives in Experimentation):

- **Metric design** — turning a vague goal ("make Stories better") into a defensible measurement system:
  a primary/success metric, guardrails, counter-metrics, and the unit/population/window that make the
  number mean what you claim. Recognising vanity, proxy-gaming, and Goodhart risk.
- **Metric diagnosis** — given a metric that moved, decomposing the cause MECE-style (real change vs
  instrumentation; internal vs external; by segment / time / region / platform / funnel-stage) instead
  of guessing.
- **Trade-off & ship judgment** — choosing between competing goods (engagement vs revenue; one side of a
  two-sided marketplace vs the other; short-term lift vs long-term retention) and deciding whether a
  result — including a flat, conflicting, or guardrail-regressing one — justifies shipping.
- **Structured product cases** — taking an ambiguous, data-free product prompt and imposing a structure
  (clarify → define success → decompose → recommend) that a stakeholder can follow.

> *Datathink philosophy applied:* this is the round that most embodies "develop the kind of reasoning
> that makes someone genuinely effective in a data-driven world… understands what question is really
> worth asking and how the answer should inform a decision" (north-star). It earns its place on
> reasoning depth, not on interview frequency.

## Modality

**Family: Constructed reasoning. No execution. `eval_kind: mcq`.** Per
[`practice-modality-spec.md`](../../specs/practice-modality-spec.md) §Modality families, product sense is a
textbook *Constructed reasoning* track — "analyse a scenario, design, tradeoff, or result and commit to a
justified answer" (verbs: **diagnose · design · interpret · prioritise**) — the **same family as
Experimentation / Data Engineering / Data Modeling**, and unlike PySpark, which is *code-adjacent*. It is
**not executable** and **not hybrid**: nothing here is computed (the computation lives in SQL / Statistics),
so there is **no numerical subtype and no code editor** — forcing one on would be the spec's
"fake execution / code-editor-because-coding-feels-premium" anti-pattern. The product surface is the
existing `MCQPanel` + `scenario_context` + `ConceptPanel`; no new UI.

> **Terminology (the spec's pushback, applied).** `mcq` is the **response mechanism** (`eval_kind`), *never*
> a question `type`. This is **not** "an MCQ track" — it is a constructed-reasoning track whose response
> happens to be single-best-answer. Below are the real `type` values.

**Question `type` values — four of the six valid types, deliberately chosen (no force-fit):**

- **`scenario`** — *the dominant type.* A `scenario_context` carries a real product situation (a metric
  read, a feature decision, a marketplace tension); the prompt asks for the call/diagnosis/decision. The
  round is scenario-driven, so expect a heavy scenario skew (Experimentation runs ~72% scenario in mock-only).
- **`conceptual`** — a product-reasoning principle anchored in a brief scenario ("which of these is the
  better *guardrail* for a notifications launch, and why").
- **`debug`** — critique flawed product/metric *reasoning*: a gameable metric, a denominator that hides the
  effect, a correlation-treated-as-causal leap, a diagnosis that skipped the instrumentation check. "Find
  the flaw." (Illustrated in [`07`](07-sample-questions.md) H3.)
- **`predict_output`** — *the smallest type,* scoped precisely as **forward outcome prediction**: given a
  stated product change, predict which metrics move and in which direction ("we remove the like-count
  display — predict the effect on posting rate and on engagement"). It tests the candidate's
  behavioural/causal model, and is genuinely distinct from `scenario` (which hands you the result and asks
  for judgment). This is the Experimentation precedent ("predict the right read"), **not** a code-output
  force-fit — there is no numeric execution; the predicted *direction* is what's observably distinct across
  options.

**Two valid types are deliberately EXCLUDED (the no-force-fit discipline you'd expect):**

- **`optimization`** — a *code-adjacent* type ("this works but is expensive — make it efficient," PySpark's
  signature). A judgment round has nothing to optimise for compute; "improve this weak metric/analysis"
  already lives in `debug`/`scenario`. Excluded.
- **`numerical`** — Statistics' code-execution subtype. No computation is the skill here. Excluded.

**Phase-2 open-response extension (out of scope for v1, recorded for completeness).** The one thing
scenario-MCQ cannot do is make a candidate *generate* a metric system or case structure from a blank
page. A future modality — a short rubric-graded free-text response (the candidate proposes a primary
metric + one guardrail + a risk, scored against a rubric, not a single key) — would close that gap. It
needs an evaluation harness the platform does not have (an LLM-or-rubric grader, new eval_kind, new UI),
so it is **explicitly deferred**. v1 ships as MCQ, exactly as Experimentation does for the equally-open
A/B-judgment skill. This trade-off is honest and consistent with the rest of the bank.

## ID range (TXNNN scheme) — open allocation question

The production [`TXNNN` scheme](../../content-authoring.md#txnnn-id-scheme-authoritative--no-deviation)
uses a **single** leading digit `T` for the track, and **all nine digits 1–9 are already assigned** to
the nine existing tracks (e.g. `T=2` Python, `T=9` Experimentation). A tenth track has **no free single
digit** — so this is a genuine open decision for whoever greenlights the track, not something this
research can settle. Three options, in rough order of preference:

1. **Two-character alpha-prefixed range** (e.g. `PS` + NNN) — cleanest, self-describing, no collision
   with the numeric tracks; requires the ID parser/validator to accept a non-numeric prefix.
2. **A wider numeric block** (e.g. `10NNNN`) — keeps IDs numeric but breaks the "5-digit TXNNN" invariant
   the docs call "authoritative — no deviation," so it would need a deliberate scheme amendment + decision-log entry.
3. **Re-pack** an under-used digit — not recommended (touches existing content).

Sample IDs would follow the 3-digit `TXS` sample convention analogously (an open sub-question of the above).

## Difficulty vocabulary

Difficulty controls **reasoning depth**, never the number of sub-questions or the obscurity of a
framework name (per the cross-track [difficulty model](../../content-authoring.md#difficulty-model-cross-track)).
The arc below is the one every external source converges on (single metric → trade-offs/diagnosis →
gaming/multi-stakeholder/composite; see [`01-external-research.md`](01-external-research.md)).

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | One concept, a clear best answer | Pick a sensible success metric for a stated goal; name a guardrail; read a simple one-direction metric movement; identify a vanity metric; basic funnel stage; leading vs lagging; the right unit of analysis for one stated question. |
| **Medium** | A trade-off or a first decomposition; tempting distractors | Two metrics move in conflict (engagement ↑, session length ↓) — which read is right; first-step diagnosis of a metric drop (decompose by segment/time/instrumentation before concluding); choose a denominator that doesn't hide the effect; basic two-sided trade-off (host vs guest); is this movement real or an instrumentation artifact. |
| **Hard** | Multi-factor judgment; all distractors defensible | Metric gaming / Goodhart (which metric survives an adversarial team); composite "health" metric design with conflicting inputs; ship/no-ship on a result with a guardrail regression + novelty suspicion; full diagnosis under conflicting signals + seasonality + a privacy/measurement constraint; multi-stakeholder trade-off where the technical answer and the deliverable diverge; new-market measurement with no clean baseline. |

### Representative scenarios per tier

Even easy questions are anchored in a real product decision — never a definition-recall prompt.

| Tier | Representative scenarios |
|---|---|
| **Easy** | "A team ships a 'Save for later' button. Pick the single best success metric." · "Which of these is a *guardrail* you'd watch, not a success metric?" · "Notifications sends doubled and opens rose — which read is premature?" · "Is 'total signups' a vanity or an actionable metric for this goal?" |
| **Medium** | "Engagement is up 8% but time-per-session is down 4% after a feed change — what's the most defensible interpretation?" · "Daily orders dropped 6% on Tuesday — what's the first thing you check, and why not the metric itself?" · "Marketplace GMV is up but host churn ticked up — which guardrail matters and what's the trade-off?" · "A conversion-rate denominator change made the funnel 'improve' — what actually happened?" |
| **Hard** | "Design a single 'creator health' metric that a growth team can't game by spamming low-value posts." · "An A/B shows +5% bookings, −2% repeat-rate, and a flat NPS guardrail after 10 days — ship, kill, or extend, and why?" · "Reels watch-time fell only in India during a festival week with a known logging gap — separate the real signal." · "Two metrics say opposite things about the same launch and leadership wants to ship Friday — frame the decision." |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | What a good metric is (success vs guardrail vs vanity) → unit/population/window basics → leading vs lagging → reading a single, unambiguous metric movement → one funnel stage |
| Medium | Conflicting-metric interpretation → first-pass metric diagnosis (segment/time/instrumentation decomposition) → denominator & definition traps → basic two-sided / counter-metric trade-offs → real-vs-artifact distinction |
| Hard | Metric gaming & Goodhart-robust design → composite/health-metric systems → ship/no-ship judgment under conflicting + guardrail-regressing results → full multi-cause diagnosis (seasonality, selection, measurement constraint) → multi-stakeholder trade-offs & the deliverable problem → opportunity sizing for prioritisation |

## Concept families

Full registry: [`03-concept-taxonomy.md`](03-concept-taxonomy.md). Target **~16–20 families** — tight and
defensible, in the spirit of Experimentation's "tightest registry in the bank" (24). The families cluster
into the sub-skills above: *metric design*, *metric diagnosis*, *trade-offs & ship judgment*, *product
cases & structure*, *funnel/retention/engagement reasoning*, and *opportunity sizing* — with explicit
**boundary co-tags** that keep the track from re-teaching Experimentation/Statistics/SQL/ML (see the
taxonomy's §Boundary).

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One concept, clean: pick a metric, name a guardrail, read one movement. |
| Practice medium | `medium.json` no `mock_only` | A trade-off or a first decomposition under realistic product framing. |
| Practice hard | `hard.json` no `mock_only` | Gaming-robust design, composite metrics, ship judgment, full diagnosis. |
| Mock-only medium | `medium.json` `mock_only: true` | Fresh, named-product scenarios that **recombine** taught medium reasoning under stakeholder pressure ("your launch read conflicts and the PM wants to ship in 3 days"). |
| Mock-only hard | `hard.json` `mock_only: true` | Advanced trade-off / diagnosis / gaming scenarios at recombination depth — never a new concept. |
| Mock-only chain | parent + 1–3 follow-ups | Interview-loop escalations: a metric-design parent that pivots to *business_rule* (the goal changes), *stakeholder* (leadership pushes back), *data_quality* (a logging gap surfaces). See [`06-mock-and-interview-loops.md`](06-mock-and-interview-loops.md). |

**Easy mock-only: never** (practice-only, like every track). **Mock-only never introduces an untaught
concept** — the governing rule for this whole package; every mock-only question must recombine reasoning
the practice bank already teaches at that difficulty or lower. ([`06`](06-mock-and-interview-loops.md)
§The subset rule makes this concrete.)

## Anti-patterns specific to Product Sense

The realism of this round is also its biggest authoring hazard — it is the easiest track to write *badly*.

- **Framework-name recall.** "What does the H in HEART stand for?" / "Name the steps of CIRCLES." Reject.
  Frameworks are scaffolding for the candidate's reasoning, never the answer. Test the *application*
  (which guardrail, which decomposition), never the vocabulary.
- **Drifting into PM product-design / strategy.** "Design a new feature for Instagram." "What's Uber's
  go-to-market?" That is the PM interview, not the DS/analyst product-*metrics* round. Every question
  must stay anchored in **measurement, metrics, and data-driven judgment** — the data flavor.
- **One famous right answer.** At hard tier, every distractor must reflect a position a competent
  practitioner could defend (a different-but-reasonable metric, a plausible-but-incomplete diagnosis).
  No "obvious correct + three strawmen."
- **Opinion masquerading as judgment.** The correct option must be defensible on a stated *reasoning*
  ground (this metric is harder to game; this decomposition rules out the cheaper hypothesis first), not
  on taste. If two options are both defensible and the "key" is just a preference, the question is invalid
  (the cross-track "multiple defensible interpretations → reject" rule).
- **Re-teaching a neighbour track.** A question whose actual skill is "compute the retention query"
  (SQL), "calculate the power" (Experimentation/Stats), or "pick the model" (ML) belongs in that track.
  Product-sense questions own the *judgment* layer; they may *reference* a number but never *test its
  derivation* (enforced via boundary co-tags in the taxonomy).
- **Numbers that don't add up.** Scenario metrics (lifts, segment splits, funnel rates) must be internally
  consistent and plausible for the named product — the same realism bar Experimentation holds for sample
  sizes and p-values.
- **Difficulty-drift via family.** Easy questions must not use the diagnosis/gaming/composite families
  (those are medium/hard). One concept at easy, by family, not just by prose.

## JSON schema

Identical shape to Experimentation (`scenario` example). The discriminator is the *judgment*, expressed
so all four options are observably distinct and the explanation refutes each distractor on a specific
reasoning ground. See [`07-sample-questions.md`](07-sample-questions.md) for fully worked illustrations.

```json
{
  "id": "PS2007",
  "order": 7,
  "topic": "product-sense",
  "type": "scenario",
  "difficulty": "medium",
  "title": "Engagement up, session length down after a feed change — what's the read?",
  "scenario_context": "A team reranked the home feed. Week over week: daily active users +3%, posts viewed per session +9%, average session length −6%, 7-day retention flat. The PM reads this as a clear win and wants to ship to 100%.",
  "description": "Which interpretation is the most defensible before shipping?",
  "options": ["…(metric-savvy distractors, each defensible to someone who half-reads the numbers)…"],
  "correct_option": 2,
  "explanation": "…refutes each distractor on a specific reasoning ground (cannibalisation vs added low-intent users imply opposite actions; retention-flat is the guardrail that gates the celebration)…",
  "hints": ["Two of these numbers point the same way and one points the other. Which is the guardrail?", "More views in less time can mean *better* feed or *shallower* sessions. What would distinguish them?"],
  "concepts": ["CONFLICTING METRIC INTERPRETATION", "GUARDRAIL & COUNTER-METRIC REASONING"]
}
```

## Proposed coverage (sizing target)

Aligned to the reasoning-track norm (Experimentation 87 practice / 104 mock-only / 10 chains; ML 100/143).
A defensible **v1 target**:

| Metric | Proposed |
|---|---|
| Practice | ~80–90 (≈ 30 easy / 33 medium / 24 hard) |
| Mock-only | ~95–105 (0 easy / ~45 medium / ~55 hard), ratio ~1.15–1.25× |
| Interview-loop chains | ~8–10 (parents + 2–3 follow-ups each) |
| Concept families | ~16–20 |
| Learning paths | 4–6 |
| Sample questions | 9 (3/3/3) |

These are *targets to author toward*, content-driven in the end (bank shape governs blueprint). Per-tier
detail in [`04-difficulty-split.md`](04-difficulty-split.md).

## Benchmark shape per difficulty

Like every MCQ reasoning track, the benchmark blueprint is **derived from the on-disk bank**, scenario-heavy.
A plausible target (to be set against the real bank once authored): easy `scenario×2 + conceptual×2 +
predict_output×1 + debug×1`; medium/hard skew further to `scenario` + `debug`. Final shape follows the
bank, never the other way around ([mock-benchmark-spec](../../specs/mock-benchmark-spec.md) §Blueprint feasibility).
