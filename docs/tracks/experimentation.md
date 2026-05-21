# Experimentation Track

> **Authoring rule, no exceptions:** Every Experimentation question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/experimentation_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working experimentation practitioner gets paid to **say "no, we can't claim that yet"** more often than to say "yes, ship it." Real A/B testing fails in operationally interesting ways: sample-ratio mismatch you didn't notice, novelty effect that fades after 2 weeks, network effects that violate SUTVA in any marketplace product, multiple testing inflating false positives, segments that flip directionality, power that wasn't enough but the PM peeked anyway. The Experimentation track tests whether the candidate sees these failure modes coming and knows how to design around them — or, when they can't, how to communicate the uncertainty honestly.

> *Datathink philosophy applied:* The candidate who explains p-values cleanly is everywhere. The candidate who says "the p-value is 0.03 but SRM is significant, so the randomization may be broken; before I look at the metric I need to investigate that" — that's the one whose experiments produce trustworthy decisions.

## Modality

**Constructed reasoning.** No execution. MCQ / scenario / predict_output / debug. 4 options.

Subtypes:
- **`mcq`** — conceptual experimentation question with scenario anchor
- **`scenario`** — `scenario_context` carries the experiment setup / observation; description asks the call
- **`predict_output`** — given experiment-output numbers or a setup, predict what the right read would be
- **`debug`** — broken experiment design; identify the flaw

## ID range (TXNNN scheme)

`T=9` for Experimentation.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 91001–91999 | `backend/content/experimentation_questions/easy.json` |
| Medium | 92001–92999 | `backend/content/experimentation_questions/medium.json` |
| Hard | 93001–93999 | `backend/content/experimentation_questions/hard.json` |

Experimentation samples are auto-sliced from the first 3 practice questions per difficulty.

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | Single concept, clear right answer | Experiment design basics, hypothesis formulation, statistical significance, Type I/II, metric selection, power basics |
| **Medium** | Trade-off; tempting distractors | Multiple testing, sample-ratio mismatch (SRM), novelty effects, variance reduction (CUPED), network effects, segmentation analysis |
| **Hard** | Multi-factor; all distractors plausible | Causal inference (IV, propensity scoring, RDD), switchback experiments, Bayesian experimentation, multi-armed bandit, holdout groups, quasi-experimental methods |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Experiment design basics → hypothesis formulation → significance → Type I and II errors → metric selection → power basics |
| Medium | Multiple testing → SRM → novelty effects → variance reduction (CUPED) → network effects → segmentation |
| Hard | Causal inference (IV / propensity / RDD) → switchback experiments → Bayesian experimentation → multi-armed bandit → holdout groups → quasi-experimental methods |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Experimentation section](../concept-taxonomy.md#experimentation--concept-families).

22 families. **The tightest pre-existing registry in the bank** (22 unique tags total). Formalisation endorses current practice.

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One concept, clean. |
| Practice medium | `medium.json` no `mock_only` | Trade-off under realistic constraints. |
| Practice hard | `hard.json` no `mock_only` | Production / advanced topic. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real scenarios: "your A/B showed +3% lift in the treatment, but SRM is significant"; "PM wants to ship after 5 days, your MDE says you need 14"; "novelty effect is killing your read". Heavy `SAMPLE RATIO MISMATCH`, `NOVELTY EFFECTS`, `NETWORK EFFECTS`, `EXPERIMENT DURATION`. |
| Mock-only hard | `hard.json` with `mock_only: true` | Causal / switchback / bandit / Bayesian-vs-frequentist debate. `CAUSAL INFERENCE`, `SWITCHBACK EXPERIMENTS`, `BAYESIAN EXPERIMENTATION`, `QUASI-EXPERIMENTAL METHODS`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: business rule (success metric changes mid-experiment), data quality (tracking gap), edge case (one arm got 1% by accident), stakeholder (leadership wants to ship despite inconclusive). |

**Easy mock-only: never.**

## Anti-patterns specific to Experimentation

- **"P-value < 0.05 ship it" framing** — every question must respect that this is the candidate-defeating reasoning style; never reward it.
- **Tool-name questions** — "what does Optimizely call X?" Reject.
- **Pure formula recall** — "what's the formula for statistical power?" Test the *application* (which lever moves it, what does halving sample size do).
- **Bayesian-vs-frequentist tribal questions** — both frameworks are valid; questions that frame it as ideology are reject. Test when each is *operationally* the right tool.
- **Hard questions with one famous right answer** — every distractor must reflect a defensible expert-level position.

## JSON schema

```json
{
  "id": 92011,
  "order": 8,
  "topic": "experimentation",
  "type": "scenario",
  "difficulty": "medium",
  "title": "Treatment shows +4% lift but SRM is significant — what's your call?",
  "scenario_context": "You're running a 50/50 A/B test on a checkout-flow change. After 7 days, your treatment group shows +4% conversion lift (95% CI: +1.2% to +6.8%, p = 0.003). Sample-ratio check shows 51.3% in control vs 48.7% in treatment (chi-squared p = 0.001 against a 50/50 null). The PM is pushing to ship today.",
  "description": "What's the right next move?",
  "options": [
    "Ship — the lift is statistically significant and meaningful; the SRM is a minor traffic-routing issue that won't affect the read.",
    "Investigate the SRM first; the assignment difference suggests the randomization may be broken, which could bias the lift estimate in unknown directions.",
    "Extend the experiment by 14 days; the SRM might wash out with more sample and the lift will stabilize.",
    "Recompute the lift using only the smaller arm to neutralize the SRM, then ship if it's still positive."
  ],
  "correct_option": 1,
  "explanation": "SRM with p = 0.001 is a serious red flag: the assumption underpinning the lift calculation (that A and B users are exchangeable) is suspect. The lift could be biased in either direction by selection effects in the broken randomization (e.g. cache assignment leaking, bot traffic filtered differently). Until SRM is explained — usually by checking exposure logs, examining bots vs humans, validating the assignment service — the lift estimate cannot be trusted. (Option 0) ignores the canonical pre-condition for A/B reads. (Option 2) extending an experiment with broken randomization just produces more biased data. (Option 3) using only the smaller arm changes nothing about the bias direction and discards data without diagnosis.",
  "hints": [
    "SRM is not a 'minor issue.' Why does it invalidate the lift read?",
    "What needs to be true about A vs B for the lift to be a causal estimate?"
  ],
  "concepts": ["SAMPLE RATIO MISMATCH", "A/B TEST MECHANICS", "EXPERIMENT DESIGN"]
}
```

Required:
- Exactly 4 options, each ≥ 20 characters.
- Explanation refutes every distractor with a specific reason.
- Scenarios use plausible real numbers — sample sizes that match the implied product, lifts in believable ranges, p-values that match the lift / sample / variance.

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k experimentation
```
