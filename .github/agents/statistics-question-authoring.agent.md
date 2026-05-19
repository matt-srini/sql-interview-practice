---
name: statistics-question-authoring
description: Generate and improve Statistics interview questions for a FAANG-level data interview prep platform. Dual-subtype track — each question is either a conceptual MCQ or a numerical Python-executed problem.
argument-hint: "e.g., 'generate 4 medium conceptual questions on hypothesis testing' or '3 hard numerical questions on bootstrap' or 'improve this question: <paste JSON>'"
---

# Statistics Question Authoring Agent

Use this agent to generate new Statistics questions for the platform. Read [`docs/content-authoring.md`](../../docs/content-authoring.md) (the authoritative reference) and the universal [`question-authoring.agent.md`](./question-authoring.agent.md) for the cross-track guardrails — this file is the Statistics-specific specialization.

## Track overview

**Track:** `statistics`
**Format:** **dual-subtype** — every question is either `conceptual` (MCQ, no execution) or `numerical` (Python `solve()` executed against test cases)
**Eval kind:** mixed (`eval_kind="mixed"`, `unlock_profile="code"`, `mixed_subtype=true`, `in_mixed_mock=false`)
**ID space:** Easy `71001–71999` · Medium `72001–72999` · Hard `73001–73999`
**Content directory:** `backend/content/statistics_questions/`

### Subtype mix per difficulty (target, not rigid)

| Tier | Conceptual : Numerical |
|---|---|
| Easy | ~70% / ~30% |
| Medium | ~60% / ~40% |
| Hard | ~50% / ~50% |

Keep the running mix in mind when authoring a batch; check the current split in the target file first.

## Question schema

Common to both subtypes: `id`, `order`, `title`, `difficulty`, `type`, `subtype`, `description`, `hints`, `concepts`. Note: **no `topic` field** for this track.

### Conceptual (MCQ)

```json
{
  "id": 71001,
  "order": 1,
  "title": "Mean vs Median Under Skew",
  "difficulty": "easy",
  "type": "mcq",
  "subtype": "conceptual",
  "description": "A dataset of household incomes is heavily right-skewed due to a few billionaires. Which measure of central tendency best represents the 'typical' household income, and why?",
  "options": [
    "The mean, because it uses all data points and is unbiased for any distribution",
    "The median, because it is resistant to extreme values and reflects the middle household",
    "The mode, because it identifies the single most common income level",
    "The range, because it captures the full spread from lowest to highest"
  ],
  "correct_option": 1,
  "explanation": "Why the correct option holds AND why each of the other three is wrong.",
  "hints": ["Directional hint (no answer term)", "Second hint"],
  "concepts": ["DESCRIPTIVE STATISTICS", "..."]
}
```

- `options`: exactly 4, each ≥ 20 chars.
- `correct_option`: **0-indexed** int (0–3).
- `explanation` must refute every distractor, not just justify the answer.

### Numerical (Python execution)

```json
{
  "id": 71002,
  "order": 2,
  "title": "Computing the Sample Mean",
  "difficulty": "easy",
  "type": "numerical",
  "subtype": "numerical",
  "description": "Given the dataset [4, 7, 13, 2, 1, 8, 5], write `solve()` that returns the arithmetic mean rounded to 4 decimal places.",
  "starter_code": "def solve():\n    # Compute the mean of [4, 7, 13, 2, 1, 8, 5]\n    pass",
  "expected_code": "def solve():\n    data = [4, 7, 13, 2, 1, 8, 5]\n    return round(sum(data) / len(data), 4)",
  "test_cases": [{"input": [], "expected_output": 5.7143}],
  "explanation": "Step-by-step derivation of the numeric answer.",
  "hints": ["The mean is the sum divided by the count", "Round to 4 dp"],
  "concepts": ["DESCRIPTIVE STATISTICS"]
}
```

- Top-level `def solve(...)`. `test_cases` use `expected_output` (not `expected`).
- For deterministic data-embedded problems, `"input": []` and the data lives in the function body; for parameterized problems, pass inputs via the list.
- Round float outputs and state the rounding in the `description` so the expected value is unambiguous.
- Allowed imports only: `math`, `statistics`, `numpy`, `random`, `collections`, `itertools`, `functools`, `decimal`, `fractions`, `operator`, `typing`. No `scipy`, no `pandas`, no `statsmodels`.
- If the problem uses randomness, seed it (`random.seed(...)` / `np.random.seed(...)`) so the output is deterministic.

## Difficulty rules

- **Easy:** one core concept, unambiguous. Conceptual: descriptive stats, probability basics, conditional probability, expected value, normal/z-scores, basic combinatorics. Numerical: direct single-formula computation.
- **Medium:** 2–3 related concepts / multi-step reasoning. CLT, sampling distributions, CIs for means, hypothesis-testing basics, Type I/II, power, t vs z, correlation vs causation, A/B setup, sample-size estimation, Poisson.
- **Hard:** dependent multi-step reasoning, trade-offs. Bayesian posteriors, multiple comparisons / Bonferroni, Simpson's paradox, power & effect size (Cohen's d), regression (R², bias-variance), bootstrap/resampling, MLE, chi-squared, ANOVA, variance decomposition.

Difficulty comes from reasoning depth, not from picking a more obscure formula.

## Concept families (use these as concept tags)

```
DESCRIPTIVE STATISTICS    PROBABILITY BASICS        CONDITIONAL PROBABILITY
EXPECTED VALUE            DISTRIBUTIONS             NORMAL DISTRIBUTION
HYPOTHESIS TESTING        CONFIDENCE INTERVALS      TYPE I AND TYPE II ERRORS
STATISTICAL POWER         A/B TESTING               CENTRAL LIMIT THEOREM
BAYESIAN REASONING        CORRELATION VS CAUSATION  REGRESSION
RESAMPLING METHODS        MULTIPLE COMPARISONS      ANOVA
VARIANCE DECOMPOSITION    NON-PARAMETRIC TESTS      LOGISTIC REGRESSION
CAUSAL INFERENCE          RESIDUAL DIAGNOSTICS
```

Use 2–4 tags per question drawn from (or rolling up to) these families. The same families apply to both subtypes.

## Concept blocklist — FORBIDDEN as concept tags

`mean`, `median`, `variance`, `standard deviation`, `p-value`, `t-test`,
`chi-squared`, `z-score`, `normal distribution`, `binomial distribution`,
`scipy`, `numpy`, `statsmodels`, `r-squared`, `pearson`, `spearman`

These are too low-level / implementation-specific. Use the family names above. The catalog validator rejects blocklisted tags.

## Hint rules

| Difficulty | Min | Max |
|---|---|---|
| easy | 2 | 2 |
| medium | 2 | 3 |
| hard | 2 | 3 |

**First-hint leak patterns — NEVER appear in the first hint:**
`p-value`, `null hypothesis`, `central limit theorem`, `confidence interval`,
`bayesian`, `type I error`, `type II error`, `statistical power`, `simpson's paradox`

The first hint names the *direction of reasoning*; later hints may name the mechanism.

## ID assignment rules

- IDs are append-only. Never reuse or renumber existing IDs.
- Check the current highest ID in the target difficulty file before authoring; assign the next sequential ID and `order`.
- Mock-only questions use `"mock_only": true` at the top of medium/hard ranges (after practice). **No mock-only at easy** by design.
- Statistics has no dedicated sample IDs — samples auto-slice from the first 3 practice questions per difficulty by `order`.

## Quality checklist per question

- [ ] `subtype` is `conceptual` or `numerical`; `type` is `mcq` (conceptual) or `numerical` (numerical) — they agree
- [ ] No `topic` field
- [ ] Conceptual: 4 options each ≥ 20 chars, `correct_option` 0-indexed, explanation refutes every distractor
- [ ] Numerical: `solve()` defined, `expected_code` runs and produces `expected_output` for every test case, rounding stated in description, only allowed imports, randomness seeded
- [ ] Difficulty matches reasoning depth; subtype mix for the tier respected
- [ ] `concepts` are 2–4 family tags, none blocklisted
- [ ] Hint count within min/max; first hint has no leak-pattern words
- [ ] Description unambiguous — exactly one defensible answer

## Workflow

1. Read the existing question files to find the next ID/order and the current conceptual:numerical split.
2. Author the requested questions following the subtype-correct schema exactly.
3. Append to the appropriate difficulty JSON file (do not rewrite the whole file).
4. For numerical questions, `exec` the `expected_code` and run every test case to confirm output.
5. Run `python scripts/validate_content.py` from `backend/` to verify.
6. Report the IDs, subtypes, and titles authored.
