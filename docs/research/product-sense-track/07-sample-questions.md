# 07 · Illustrative sample questions — Product Sense

> Research/proposal. These are **illustrations of the design**, authored from scratch to show the exact
> MCQ shape, the difficulty bar, and the "the discriminator is the *judgment*" quality standard — **not a
> content drop.** Per the "never lift content" rule (applied even in research docs), none is copied or
> paraphrased from any source; the products and numbers are invented to be plausible. If the track is
> greenlit, real questions are authored only via `question-authoring.agent.md`, not from this file.

Each example is shown in the production schema. The bar every one must clear: all four options are
observably distinct; the explanation refutes each distractor on a specific *reasoning* ground; the
candidate cannot answer by computing a value, deriving a statistic, or writing a query (or it belongs in
SQL/Stats/Experimentation — the [boundary rule](03-concept-taxonomy.md#boundary--the-families-that-share-an-edge-with-another-track)).

---

## Easy

### E1 · `METRIC SELECTION & GOAL TRANSLATION` (scenario)

```json
{
  "difficulty": "easy",
  "type": "scenario",
  "title": "Success metric for a 'Save recipe' button",
  "scenario_context": "A recipe app adds a 'Save' button so users can bookmark recipes to cook later. The team's stated goal is to help users come back and actually cook what they saved.",
  "description": "Which single metric best captures that goal?",
  "options": [
    "Total saves across all users — it directly counts the new behaviour the button enables.",
    "Saves per active user per week — it normalises for audience size and shows adoption depth.",
    "Share of saved recipes that are opened again (or marked cooked) within 14 days — it ties the save to the goal of cooking later.",
    "Number of users who tapped the button at least once — it shows how many people discovered the feature."
  ],
  "correct_option": 2,
  "explanation": "The goal is not saving, it is *coming back to cook what was saved* — so the metric must connect the save to a later return-and-use, which (Option C) does. (Option A) is a vanity count that grows with the user base and rewards saving even if nothing is ever cooked. (Option B) measures adoption depth but still stops at the save, not the return. (Option D) is a one-time discovery metric, not a measure of the goal. The discriminator is recognising that the success metric must reach the *intended outcome*, not the *enabling action*.",
  "hints": ["The button's job is not 'get saves' — re-read the stated goal.", "Which option would still look great if users saved hundreds of recipes and cooked none?"],
  "concepts": ["METRIC SELECTION & GOAL TRANSLATION"]
}
```

### E2 · `GUARDRAIL & COUNTER-METRIC REASONING` (conceptual)

```json
{
  "difficulty": "easy",
  "type": "conceptual",
  "title": "Which is the guardrail, not the success metric?",
  "scenario_context": "A news app will start auto-playing the next video when one finishes, to raise watch time (the success metric).",
  "description": "Which metric belongs as a GUARDRAIL alongside that success metric?",
  "options": [
    "Average watch time per session — the thing the change is trying to grow.",
    "Next-day return rate — a metric that must not fall, because auto-play could inflate watch time while annoying users into leaving.",
    "Number of videos auto-played — a count of how often the feature fires.",
    "Total videos uploaded — the supply of content available to play."
  ],
  "correct_option": 1,
  "explanation": "A guardrail is a metric that must *not degrade* while you optimise the primary — it protects against winning the target while harming the product. (Option B) is the classic guardrail here: auto-play can pump watch time while quietly driving users away, so return rate must hold. (Option A) is the success metric itself, not a guardrail. (Option C) is an instrumentation count of feature firing, not a health signal. (Option D) is upstream supply, unaffected by and unprotective of this change. The discriminator is the *role* a metric plays (protect vs optimise), not the metric itself.",
  "hints": ["A guardrail answers 'what could this change quietly break?'", "Auto-play can raise watch time and still make the app worse. Which metric would catch that?"],
  "concepts": ["GUARDRAIL & COUNTER-METRIC REASONING"]
}
```

## Medium

### M1 · `CONFLICTING-METRIC & TRADE-OFF JUDGMENT` (scenario)

```json
{
  "difficulty": "medium",
  "type": "scenario",
  "title": "Engagement up, session length down after a feed rerank",
  "scenario_context": "A social app reranks the home feed. Week over week: daily active users +3%, posts viewed per session +9%, average session length −6%, 7-day retention flat. The PM reads a clear win and wants to ship to everyone.",
  "description": "Which interpretation is the most defensible before shipping?",
  "options": [
    "Clear win: more DAU and more posts viewed are both up; the shorter sessions just mean the feed is more efficient.",
    "The signals are ambiguous: more posts in less time could mean a better, snappier feed OR shallower, lower-quality sessions — and retention being flat (not up) is the guardrail that says don't celebrate yet. Distinguish the two before shipping.",
    "Clear loss: session length fell, so engagement quality dropped; do not ship.",
    "Ship to everyone but keep watching retention — if it later drops, roll back."
  ],
  "correct_option": 1,
  "explanation": "Two readings fit the same numbers and they imply opposite actions, so the defensible move is to distinguish them, not to pick the flattering one. (Option B) names that ambiguity (efficient feed vs shallow sessions) and treats flat retention as the guardrail that gates the celebration. (Option A) assumes the optimistic read without evidence and ignores that shorter sessions can mean disengagement. (Option C) assumes the pessimistic read just as blindly. (Option D) ships first and treats the guardrail as a rollback trigger rather than a pre-ship gate — exactly backwards for a 100% launch. The discriminator is holding two interpretations and resolving them, not collapsing to one.",
  "hints": ["More views in less time has (at least) two very different explanations. What would tell them apart?", "Retention is flat, not up. For a 100% launch, is that a green light or a yellow one?"],
  "concepts": ["CONFLICTING-METRIC & TRADE-OFF JUDGMENT", "GUARDRAIL & COUNTER-METRIC REASONING"]
}
```

### M2 · `METRIC MOVEMENT DIAGNOSIS` + `REAL-CHANGE VS ARTIFACT` (scenario)

```json
{
  "difficulty": "medium",
  "type": "scenario",
  "title": "Sign-ups jumped overnight — first move",
  "scenario_context": "A SaaS product's daily new sign-ups jumped from a steady ~2,000/day to ~3,200/day overnight, exactly the day after a marketing site redeploy. Activation rate (sign-ups who complete onboarding) fell from 58% to 40% the same day.",
  "description": "What is the most defensible FIRST step?",
  "options": [
    "Celebrate and scale the marketing spend — a 60% sign-up jump is a strong acquisition win.",
    "Before treating the jump as real demand, verify it isn't an instrumentation or bot artifact — a sudden overnight step right after a deploy, with activation collapsing, is the signature of double-counted events or junk sign-ups, not a demand surge.",
    "Investigate the activation drop by redesigning onboarding — a 58%→40% fall means the funnel broke.",
    "Run an A/B test on the new marketing site to measure its true effect on sign-ups."
  ],
  "correct_option": 1,
  "explanation": "A sudden step change coinciding with a deploy, plus a correlated metric moving the 'wrong' way (activation collapsing), is the canonical tell of a measurement artifact — double-counted sign-up events, a tracking duplication, or bot/junk traffic — so the data-quality gate comes first. (Option B) checks that before building any behavioural story. (Option A) scales spend on a number that may be fake. (Option C) jumps to a product fix for an activation drop that is likely the *same artifact* (junk sign-ups never activate), not a broken funnel. (Option D) designs a future experiment instead of explaining the present anomaly — root cause first, experiment later. The discriminator is ruling out 'is it even real' before interpreting behaviour.",
  "hints": ["What does a sudden overnight step right after a deploy usually smell like?", "If 1,200 of the new sign-ups were junk, what would happen to the activation *rate*?"],
  "concepts": ["METRIC MOVEMENT DIAGNOSIS", "REAL-CHANGE VS ARTIFACT"]
}
```

## Hard

### H1 · `SHIP / NO-SHIP DECISION` (scenario)

```json
{
  "difficulty": "hard",
  "type": "scenario",
  "title": "Compound result: primary up, guardrail regressing, novelty suspected",
  "scenario_context": "A marketplace tests a pushier 'complete your booking' nudge. After 10 days: bookings +5% (primary, significant), repeat-booking-rate −2% (a declared guardrail), host-rated guest quality flat, and the treatment effect on bookings is largest in days 1–3 and tapering by day 10. Leadership wants a decision tomorrow.",
  "description": "What is the most defensible recommendation?",
  "options": [
    "Ship — the primary metric is significantly up and the guardrail breach is small.",
    "Kill — a guardrail regressed, and guardrails are non-negotiable.",
    "Don't ship yet: the tapering day-1–3-heavy effect points to a novelty bump that may not hold, and the −2% on repeat-rate (a long-term guardrail) could outweigh a fading short-term booking gain — extend the test and watch whether the lift survives and the guardrail recovers.",
    "Ship to 50% and use the held-back 50% as a permanent holdout to monitor long-term effects."
  ],
  "correct_option": 2,
  "explanation": "The result is a compound: a fading short-term primary gain set against a regressing *long-term* guardrail (repeat-rate), which is exactly the case where a 10-day read is untrustworthy. (Option C) reads the day-1–3-heavy taper as a novelty signal and refuses to trade a possibly-temporary booking bump for a durable repeat-rate loss without more data. (Option A) treats statistical significance as launch-worthiness and waves off a long-term guardrail. (Option B) is reflexive — a small guardrail move warrants investigation and an extended read, not an automatic kill. (Option D) confuses a rollout tactic with the decision and proposes a 'permanent holdout' that isn't the question asked. 'Don't ship yet, here's the specific evidence and what would change my mind' is the strong-hire shape; reflexive ship or kill is not.",
  "hints": ["Which of these four numbers is about the *long term*, and which effect looks like it's already fading?", "Is 'significant' the same as 'worth shipping'? What would make the lift trustworthy?"],
  "concepts": ["SHIP / NO-SHIP DECISION", "CONFLICTING-METRIC & TRADE-OFF JUDGMENT"]
}
```

### H2 · `METRIC GAMING & ROBUSTNESS` (scenario)

```json
{
  "difficulty": "hard",
  "type": "scenario",
  "title": "A 'creator health' metric a growth team can't game",
  "scenario_context": "A video platform wants one 'creator health' metric for a growth team to optimise. A PM proposes 'total videos uploaded per week' because it's simple and sensitive.",
  "description": "What is the strongest objection, and the better design?",
  "options": [
    "It's fine — upload volume is a direct, sensitive measure of a healthy creator base.",
    "It's gameable: a team can hit 'uploads' by pushing creators to post more low-value content, raising the number while audience value falls — so pair an output metric (e.g. share of uploads that reach a minimum watch threshold, or creators retained at 30 days) with it, so volume can't rise on junk alone.",
    "Replace it with total watch time — a single metric that captures everything that matters.",
    "Add more decimal places and report it daily so the team can react faster."
  ],
  "correct_option": 1,
  "explanation": "This is Goodhart's law: once 'uploads' is the target, the cheapest way to move it is more low-value posting, which inflates the metric without improving creator health. (Option B) names that and fixes it the right way — a counter/quality metric that volume can't satisfy by spamming (watched-threshold share, or retained-creator count) so the pair resists gaming. (Option A) ignores the gaming vector entirely. (Option C) swaps one single metric for another single metric — watch time is *also* gameable (autoplay, clickbait) and collapses the multi-dimensional 'health' into one number. (Option D) addresses cadence/precision, not the gaming problem. The discriminator is anticipating adversarial optimisation and designing the counter-metric, not picking a 'better' single number.",
  "hints": ["If a growth team is paid to move 'uploads,' what's the cheapest way to do it — and does the product get better?", "A single number is easy to game. What would make the metric only rise when something *good* happened?"],
  "concepts": ["METRIC GAMING & ROBUSTNESS", "GUARDRAIL & COUNTER-METRIC REASONING"]
}
```

### H3 · `CAUSAL VS CORRELATIONAL JUDGMENT` (debug)

```json
{
  "difficulty": "hard",
  "type": "debug",
  "title": "What's wrong with the weekend-bonus argument",
  "scenario_context": "An analyst writes: 'Sellers who list items on weekends average 30% higher sales than weekday-only sellers. We should pay all sellers a bonus to list on weekends — it will lift platform sales ~30%.'",
  "description": "What is the central flaw in this recommendation?",
  "options": [
    "The math: a 30% per-seller gap doesn't equal a 30% platform lift because of rounding.",
    "It treats a correlation as causal: weekend listers likely differ systematically (more committed or full-time sellers, or higher-demand categories), so their higher sales may be self-selection, not an effect of the weekend — bonusing weekday sellers to list on weekends needn't reproduce it. A test (or a like-for-like comparison) is needed before acting.",
    "The sample is too small to be statistically significant.",
    "Weekend sales are seasonal and the analyst should have used year-over-year data."
  ],
  "correct_option": 1,
  "explanation": "The argument infers a *causal* policy effect ('bonus → +30%') from an *observational* correlation between a self-selected group (weekend listers) and an outcome. (Option B) identifies the self-selection/confounding: weekend listers are plausibly different sellers (commitment, category), so their advantage may not transfer to weekday sellers nudged to list on weekends. (Option A) invents a rounding issue that isn't the flaw. (Option C) raises significance, but even a perfectly precise 30% gap would still be non-causal — sample size is not the central problem. (Option D) raises seasonality, a real-but-secondary concern that doesn't touch the core correlation-vs-causation error. The discriminator is recognising the causal leap, not the statistical mechanics of testing it (that machinery lives in the Experimentation track).",
  "hints": ["Are weekend listers the *same kind* of seller as weekday-only listers? What might differ about them?", "Even with infinite data and a precise 30%, would paying weekday sellers to switch reproduce it?"],
  "concepts": ["CAUSAL VS CORRELATIONAL JUDGMENT", "METRIC MOVEMENT DIAGNOSIS"]
}
```

---

## What these illustrate (the bar)

- **The discriminator is judgment, never computation.** Not one example can be answered by a query, a
  formula, or a statistic — that's the boundary that keeps the track out of SQL/Stats/Experimentation.
- **Distractors are defensible, not strawmen** (especially at hard) — each wrong option is a real position
  a candidate under pressure would pick (reflexive ship, reflexive kill, the optimistic read, the
  single-number fix), and the explanation refutes each on its own reasoning ground.
- **Difficulty is reasoning depth.** Easy = one role/translation; medium = hold-two-readings or a first
  decomposition; hard = a compound decision or an adversarial design.
- **Realism without lifting.** Plausible products and internally-consistent numbers, all invented.
