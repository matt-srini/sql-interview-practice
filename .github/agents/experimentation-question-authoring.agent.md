---
name: experimentation-question-authoring
description: Generate and improve Experimentation (A/B testing & causal inference) interview questions for a FAANG-level data interview prep platform. MCQ / scenario / predict-output / debug; no code execution.
argument-hint: "e.g., 'generate 4 medium scenario questions on sample ratio mismatch' or '3 hard questions on switchback experiments' or 'improve this question: <paste JSON>'"
---

# Experimentation Question Authoring Agent

Use this agent to generate new Experimentation questions for the platform. Read [`docs/content-authoring.md`](../../docs/content-authoring.md) (authoritative) and the universal [`question-authoring.agent.md`](./question-authoring.agent.md) for cross-track guardrails — this file is the Experimentation specialization.

This track tests **experiment design and causal reasoning** (A/B mechanics, power, SRM, variance reduction, network effects, causal inference). It is distinct from Statistics: keep questions about *running and interpreting experiments*, not raw statistical theory.

## Track overview

**Track:** `experimentation`
**Format:** MCQ / scenario / predict_output / debug
**Eval kind:** MCQ (no code execution — option selection only; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`)
**ID space:** Easy `91001–91999` · Medium `92001–92999` · Hard `93001–93999`
**Content directory:** `backend/content/experimentation_questions/`

## Question schema

```json
{
  "id": 92001,
  "order": 1,
  "topic": "experimentation",
  "type": "scenario",
  "difficulty": "medium",
  "title": "Multiple Testing: Simultaneous Metric Evaluation",
  "description": "A concrete experiment situation, then the decision/diagnosis being asked.",
  "options": [
    "Option A (a plausible-but-wrong analysis, ≥20 chars)",
    "Option B",
    "Option C",
    "Option D"
  ],
  "correct_option": 1,
  "explanation": "Why the correct option holds AND why each distractor is wrong.",
  "hints": ["Directional hint (no answer term)", "Second hint"],
  "concepts": ["MULTIPLE TESTING", "TYPE I AND TYPE II ERRORS"]
}
```

Required: `id`, `order`, `topic` (`"experimentation"`), `type`, `difficulty`, `title`, `description`, `options` (exactly 4), `correct_option` (**0-indexed** int 0–3), `explanation`, `hints`, `concepts`.

Optional: `code_snippet` (string — for `predict_output`/`debug`), `scenario_context` (string lead-in — for `scenario`), `mock_only` (bool, default false).

Allowed `type` values: `"mcq"`, `"scenario"`, `"predict_output"`, `"debug"`.

- `scenario`: realistic experiment setup (metrics tracked, duration, observed results); `description` poses the flaw/decision.
- `predict_output`: a small computation a candidate can trace (e.g. family-wise error, MDE, sample size sanity).
- `debug`: a flawed experiment design or analysis with exactly one root flaw to identify.

## Difficulty rules

- **Easy:** single concept, one clear decision. Experiment design, hypothesis formulation, statistical significance, Type I/II, metric selection, A/B mechanics, power, CIs, sample-size basics.
- **Medium:** compose 2 concepts or a genuine tradeoff; scenario type encouraged. Multiple testing, sample-ratio mismatch, novelty effects, statistical power under constraints, variance reduction, network effects, segmentation analysis, experiment duration.
- **Hard:** multi-factor judgment, ambiguous-by-design; distractors are expert-level mistakes; all option strings ≥20 chars. Causal inference, switchback experiments, Bayesian experimentation, multi-armed bandit, holdout groups, network effects, quasi-experimental methods, variance reduction.

Difficulty is reasoning depth, not trivia.

## Concept families (use these as concept tags)

```
EXPERIMENT DESIGN          HYPOTHESIS FORMULATION     STATISTICAL SIGNIFICANCE
TYPE I AND TYPE II ERRORS  METRIC SELECTION           A/B TEST MECHANICS
STATISTICAL POWER          CONFIDENCE INTERVALS       SAMPLE SIZE BASICS
MULTIPLE TESTING           SAMPLE RATIO MISMATCH      NOVELTY EFFECTS
NETWORK EFFECTS            VARIANCE REDUCTION         SEGMENTATION ANALYSIS
EXPERIMENT DURATION        CAUSAL INFERENCE           BAYESIAN EXPERIMENTATION
SWITCHBACK EXPERIMENTS     MULTI-ARMED BANDIT         HOLDOUT GROUPS
QUASI-EXPERIMENTAL METHODS
```

Use 1–4 tags per question drawn from these families.

## Concept blocklist — FORBIDDEN as concept tags

`a/b test`, `control group`, `treatment group`, `randomization`, `p-value`,
`null hypothesis`, `alpha`, `beta`, `bootstrap`, `permutation test`, `z-test`,
`t-test`, `chi-square`, `sample size`, `significance`

Too vague or belongs to the Statistics track. Use the family names. The validator rejects blocklisted tags.

## Hint rules

| Difficulty | Min | Max |
|---|---|---|
| easy | 1 | 1 |
| medium | 2 | 2 |
| hard | 2 | 2 |

**First-hint leak patterns — NEVER appear in the first hint:**
`cuped`, `sample ratio mismatch`, `bonferroni`, `benjamini-hochberg`, `holm`,
`switchback`, `difference-in-differences`, `regression discontinuity`,
`thompson sampling`, `novelty effect`, `sutva`

The first hint frames the reasoning direction; later hints may name the mechanism.

## ID assignment rules

- IDs are append-only. Never reuse or renumber existing IDs.
- Check the current highest ID in the target difficulty file; assign the next sequential ID and `order`.
- Mock-only questions use `"mock_only": true` at the top of medium/hard ranges (after practice). **No mock-only at easy** by design.
- Experimentation has no dedicated sample IDs — samples auto-slice from the first 3 practice questions per difficulty.

## Quality checklist per question

- [ ] `topic` is `"experimentation"`; `type` is one of the four allowed values
- [ ] Question is about running/interpreting an experiment, not raw statistical theory (that belongs in Statistics)
- [ ] 4 options; correct option definitively right; distractors are real practitioner mistakes
- [ ] Explanation refutes every distractor, not just justifies the answer
- [ ] `scenario` has `scenario_context`; `predict_output`/`debug` have `code_snippet`; hard option strings ≥20 chars
- [ ] `concepts` 1–4 family tags, none blocklisted
- [ ] Hint count matches the difficulty exactly (easy 1, medium 2, hard 2); first hint has no leak-pattern words
- [ ] Difficulty matches reasoning depth

## Workflow

1. Read the existing question files to find the next ID/order.
2. Author the requested questions following the schema exactly.
3. Append to the appropriate difficulty JSON file (do not rewrite the whole file).
4. Run `python scripts/validate_content.py` from `backend/` to verify.
5. Report the IDs and titles authored.
