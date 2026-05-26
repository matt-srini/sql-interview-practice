# Experimentation Track

> **Authoring rule, no exceptions:** Every Experimentation question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/experimentation_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working experimentation practitioner gets paid to **say "no, we can't claim that yet"** more often than to say "yes, ship it." Real A/B testing fails in operationally interesting ways: sample-ratio mismatch you didn't notice, novelty effect that fades after 2 weeks, network effects that violate SUTVA in any marketplace product, multiple testing inflating false positives, segments that flip directionality, power that wasn't enough but the PM peeked anyway. The Experimentation track tests whether the candidate sees these failure modes coming and knows how to design around them — or, when they can't, how to communicate the uncertainty honestly.

> *Datathink philosophy applied:* The candidate who explains p-values cleanly is everywhere. The candidate who says "the p-value is 0.03 but SRM is significant, so the randomization may be broken; before I look at the metric I need to investigate that" — that's the one whose experiments produce trustworthy decisions.

## Modality

**Constructed reasoning.** No execution. Response: MCQ (4 options).

Question types:
- **`conceptual`** — conceptual experimentation question with scenario anchor, evaluated via single-best-answer MCQ
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
| **Medium** | Trade-off; tempting distractors | Multiple testing, sample-ratio mismatch (SRM), novelty effects, variance reduction (CUPED), network effects, segmentation analysis, metric sensitivity |
| **Hard** | Multi-factor; all distractors plausible | Causal inference (IV, propensity scoring, RDD), switchback experiments, Bayesian experimentation, multi-armed bandit, holdout groups, quasi-experimental methods, sequential testing, metric sensitivity (advanced) |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses formula or tool-name recall. Even easy questions are anchored in a real experiment decision.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Formulate a hypothesis + metric for a feature · what Type I/II error means for this test · basic power intuition · pick a primary metric for a stated goal. One concept, clear right answer. |
| **Medium** | Diagnose a sample-ratio mismatch · correct for multiple testing · spot a novelty effect in a read · apply CUPED for variance reduction. Trade-off with tempting distractors. |
| **Hard** | Pick a causal method when randomization is impossible · design a switchback for network effects · Bayesian vs frequentist read under business pressure · holdout-group design. Multi-factor, all distractors plausible. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Experiment design basics → hypothesis formulation → significance → Type I and II errors → metric selection → power basics |
| Medium | Multiple testing → SRM → novelty effects → variance reduction (CUPED) → network effects → segmentation |
| Hard | Causal inference (IV / propensity / RDD) → switchback experiments → Bayesian experimentation → multi-armed bandit → holdout groups → quasi-experimental methods → sequential testing → metric sensitivity (advanced) |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Experimentation section](../concept-taxonomy.md#experimentation--concept-families).

24 families (Phase 2 expanded from 22 → 24: added SEQUENTIAL TESTING at hard difficulty and METRIC SENSITIVITY at medium + hard). **The tightest registry in the bank** (24 unique tags total).

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One concept, clean. |
| Practice medium | `medium.json` no `mock_only` | Trade-off under realistic constraints. |
| Practice hard | `hard.json` no `mock_only` | Production / advanced topic. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real scenarios: "your A/B showed +3% lift in the treatment, but SRM is significant"; "PM wants to ship after 5 days, your MDE says you need 14"; "novelty effect is killing your read". Heavy `SAMPLE RATIO MISMATCH`, `NOVELTY EFFECTS`, `NETWORK EFFECTS`, `EXPERIMENT DURATION`. |
| Mock-only hard | `hard.json` with `mock_only: true` | Causal / switchback / bandit / Bayesian-vs-frequentist debate. `CAUSAL INFERENCE`, `SWITCHBACK EXPERIMENTS`, `BAYESIAN EXPERIMENTATION`, `QUASI-EXPERIMENTAL METHODS`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: business rule (success metric changes mid-experiment), data quality (tracking gap), edge case (one arm got 1% by accident), stakeholder (leadership wants to ship despite inconclusive). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and stakeholder realism, not new concepts. A mock-only question recombines experimentation reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh real-world experiment scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

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

## Coverage (Phase 2 final state)

| Metric | Value |
|---|---|
| Practice questions | 87 (30 easy / 33 medium / 24 hard) |
| Mock-only questions | 104 (0 easy / 45 medium / 59 hard) |
| Mock / practice ratio | 1.20× |
| Mock m:h split | 45 medium : 59 hard |
| Chain count | 10 (10 parents + 20 children = 30 members, 29% of mock-only) |
| Realism path | (ii) — no mock-only realism families; all 24 families are direct-gradeable via MCQ |
| Highest-anchoring families | None exceed the 50% rule-3 ceiling. Highest mock-only shares: EXPERIMENT DESIGN 21% · CAUSAL INFERENCE 16% · EXPERIMENT DURATION / SEGMENTATION ANALYSIS / STATISTICAL SIGNIFICANCE all 12%. SAMPLE RATIO MISMATCH at 9% of mock-only is the canonical "broken experiment" diagnostic anchor but is not statistically load-bearing. |
| Registry | 24 families (22 original + 2 added in Phase 2: SEQUENTIAL TESTING, METRIC SENSITIVITY) |
| Validator gate | Added to `_TAXONOMY_VALIDATED_TRACKS` in `backend/scripts/validate_content.py` |

**Type mix in mock-only:** scenario 75 (72%) · debug 18 (17%) · predict_output 10 (10%) · conceptual 1 (1%). Heavy scenario skew is intentional — operational A/B reasoning grades cleanest as scenario MCQ; debug and predict_output anchor the second-largest reasoning surfaces.

**Phase 2 decision log:**
- Registry expanded 22→24: SEQUENTIAL TESTING (hard) covers mSPRT / group sequential / alpha spending / optional stopping; METRIC SENSITIVITY (medium + hard) covers structural detectability limits from high-variance or coarsely-defined metrics.
- Realism path (ii) chosen: MCQ-only track. Every reasoning lens (SRM diagnosis, novelty detection, peeking, network contamination) is directly gradeable as scenario/debug/predict_output without a code-execution harness. The "assessment lens" rationale for SQL/Pandas mock-only realism families does not transfer here.
- 10 chains (30 members) cover: SRM+CDN bias, sequential testing Q4 pressure, Thompson Sampling bandit, Bayesian stop-at-95%, switchback carryover, national policy quasi-exp, 5% long-run holdout, HTE desktop+mobile, email referral network effects, MDE/CUPED sample size.
- Q83029 resurrected from ML Fundamentals (git `60005e9`) at ID 93038 with tags CAUSAL INFERENCE + SEGMENTATION ANALYSIS (uplift modeling, 4-segment HTE).

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k experimentation
```
