# Statistics Track

> **Authoring rule, no exceptions:** Every Statistics question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/statistics_questions/*.json` bypass the difficulty arc, the dual-subtype contract, and the concept-taxonomy registry.

## What this track trains

A working data scientist's worth in interviews and on the job comes from **reasoning about uncertainty as a first-class quantity** — picking the right inference tool, recognising when assumptions break, refusing to over-claim from noisy data. The Statistics track exists to test both the conceptual frame and the numerical chops. Both matter, separately.

> *Datathink philosophy applied:* The PM-pleasing answer ("yes, it's significant") is everywhere. The practitioner who says "the p-value is 0.04 but my power is 0.42, the multiple-testing correction makes this not actually significant, and the segment effect doesn't replicate — here's what we can defensibly claim" is the one whose work survives audit.

## Modality

**Hybrid.** Every question carries `subtype`:
- **`conceptual`** — MCQ with options + correct_option + explanation. No execution.
- **`numerical`** — Python code execution with starter / expected / solution code + test cases. Same evaluator as Python track. Sandbox-restricted imports.

The subtype is exposed in the UI so users know which mode they're entering before they answer. This is non-negotiable — blurring conceptual MCQ and numerical code into "Stats questions" loses signal.

Mix by difficulty:
- Easy: ~70% conceptual / ~30% numerical
- Medium: ~60% conceptual / ~40% numerical
- Hard: ~50% conceptual / ~50% numerical

## ID range (TXNNN scheme)

`T=7` for Statistics. Both subtypes share the same ID space; subtype is a field, not a separate file.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 71001–71999 | `backend/content/statistics_questions/easy.json` |
| Medium | 72001–72999 | `backend/content/statistics_questions/medium.json` |
| Hard | 73001–73999 | `backend/content/statistics_questions/hard.json` |

Samples for Statistics are auto-sliced from the first 3 practice questions per difficulty (no dedicated sample IDs).

## Difficulty vocabulary

| Tier | Conceptual focus | Numerical focus |
|---|---|---|
| **Easy** | Descriptive stats, basic probability, conditional probability, expected value, normal/z-scores, basic combinatorics | Implementing simple calculations: mean / median / variance / single-distribution probabilities |
| **Medium** | CLT, sampling distributions, confidence intervals for means, hypothesis-testing basics, Type I/II, power, correlation vs causation, A/B-test setup, sample-size estimation, Bayes basics, Law of Large Numbers, Poisson | Building CIs, running t-tests, computing power, sampling demonstrations |
| **Hard** | Bayesian posterior calculation, multiple comparisons (Bonferroni / FDR), Simpson's paradox, power analysis with effect size, regression interpretation, bootstrap, MLE, chi-squared, ANOVA, survival analysis, variance decomposition | Bayesian updates by code, bootstrap CIs, MLE for non-trivial distributions, regression coefficient interpretation, ANOVA decomposition |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses formula recall. Even easy questions ask what a number *means*, not just how to compute it.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Interpret a z-score for a single observation · conditional probability of an event from a described setup · what a mean/median gap implies · compute a single-distribution probability. One concept, unambiguous. |
| **Medium** | Build a CI for a conversion rate · choose t vs z for a given sample · estimate sample size for an A/B test · separate correlation from causation in a real claim. Reasoning over inference tools. |
| **Hard** | "PM ran 8 tests, one hit p<0.05" (multiple comparisons) · diagnose Simpson's paradox in segmented data · Bayesian posterior under a stated prior · bootstrap CI for a skewed metric. Production-grade statistical judgement. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Descriptive statistics → basic probability + conditional probability → independence + expected value → Bernoulli / binomial → normal distribution + z-scores → 68-95-99.7 rule → basic combinatorics |
| Medium | Central Limit Theorem → sampling distributions → confidence intervals for means → hypothesis testing basics (null hypothesis, p-value, significance level) → Type I and Type II errors → statistical power → t vs z → correlation vs causation → A/B testing setup → sample-size estimation → Bayesian basics → Law of Large Numbers → Poisson |
| Hard | Bayesian posterior calculation → multiple comparisons + Bonferroni → Simpson's paradox → power analysis + effect size (Cohen's d) → regression (R², bias-variance) → bootstrap + resampling → maximum likelihood estimation → chi-squared tests → ANOVA → survival analysis basics → variance decomposition |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → Statistics section](../concept-taxonomy.md#statistics--concept-families).

13 families. **Statistics uses lowercase canonical tag style** (e.g. `probability`, `hypothesis testing`, `central limit theorem`) — a deliberate exception to the UPPERCASE convention used by the other tracks. This preserves the existing tag corpus and matches academic / industry conventions where lowercase is normal.

Same concept families apply to both subtypes. A `central limit theorem` question can be conceptual (MCQ about when CLT applies) or numerical (Python code demonstrating convergence).

## Authoring allocation matrix

| Question kind | Where | Subtype distribution | When |
|---|---|---|---|
| Practice easy | `easy.json` no `mock_only` | ~70% conceptual / 30% numerical | Single concept, unambiguous. |
| Practice medium | `medium.json` no `mock_only` | ~60% / 40% | Reasoning over inference tools. |
| Practice hard | `hard.json` no `mock_only` | ~50% / 50% | Production-grade statistical judgement. |
| Mock-only medium | `medium.json` with `mock_only: true` | Match practice mix | Real scenarios: "PM ran 8 tests and one was p<0.05" (multiple testing); "your bootstrap CI is bimodal — what's wrong?" |
| Mock-only hard | `hard.json` with `mock_only: true` | Match practice mix | Bayesian decision-making under conflicting priors; power-vs-effect-size argued under business pressure. |
| Mock-only chain | parent + 1–3 follow-ups | Match practice mix per question | Pivots: ambiguity (PM wants a simpler answer), data quality (5% MNAR), business rule (definition changed), scale (10× more samples). Chains may stay subtype-pure (all conceptual or all numerical) for coherence. |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and realism, not new concepts. A mock-only question recombines statistical reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh applied scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Coverage & sizing targets

**Phase 2 complete (2026-05-26).** All 13 concept families have ≥1 practice question (rule-1) and ≥4 mock-only questions (rule-2).

| Tier | Practice | Mock-only | Total |
|---|---|---|---|
| Easy | 31 | 0 (by design) | 31 |
| Medium | 43 | 66 | 109 |
| Hard | 26 | 50 | 76 |
| **Total** | **100** | **116** | **216** |

Mock-only ratio: 116 / 100 = **1.16×** — landed inside the locked target band of **1.15–1.25×**.

**Target-ratio justification.** The 1.15–1.25× band was locked at Stage A against two anchors: (a) PySpark 1.17× as the closest modality precedent (code-adjacent reasoning with MCQ evaluation, similar per-question authoring constraint); (b) the dual-subtype format imposes a stricter anti-clone ceiling than pure-MCQ tracks — a mock-only numerical question must have meaningfully different numerical scaffolding from its practice equivalent, which bounds the practical authoring ceiling lower than pure-MCQ tracks (SQL 1.40×, Python 1.30×). 1.16× represents the achievable runway under that quality constraint.

**Per-subtype ratio.** Of the 116 mock-only questions, 85 are conceptual and 31 are numerical. Of the 100 practice questions, 60 are conceptual and 40 are numerical.

| Subtype | Practice | Mock-only | Ratio |
|---|---|---|---|
| Conceptual | 60 | 85 | **1.42×** |
| Numerical | 40 | 31 | **0.78×** |
| Total | 100 | 116 | **1.16×** |

The numerical mock-only ratio (0.78×) is materially below the 1.0× contract floor. This is an acknowledged outcome, not an oversight, but it is **provisional**: it stands only as long as the numerical-pool runway is empirically sufficient for power-user consumption, and is the first remediation candidate if a future audit shows fresh-first exhaustion on numerical benchmarks. Rationale for the present landing: (a) numerical questions with deterministic starter/expected code and hidden test cases are the hardest format to anti-clone — a mock-only numerical question must have visually and computationally distinct scaffolding from its practice counterpart, and the practice numerical pool (40 questions) already occupies much of the available recombination surface; (b) the conceptual surplus (1.42×) carries the overall 1.16× ratio. Numerical mock distributes as 13 medium + 18 hard (≈1 per family at medium, ≈1.4 per family at hard across the 13-family registry); benchmark composition is `1 numerical + 2 conceptual` per benchmark (per `docs/specs/mock-benchmark-spec.md`), so the 31-question numerical mock pool supports roughly 15 distinct hard benchmarks before fresh-first exhausts — borderline-sufficient under steady benchmark use, fragile under heavy drill mode. **First remediation if exhaustion is observed:** numerical-only top-up authoring to bring the pool to ~40 (≈1.0×), not retroactive ratio inflation.

**Mock difficulty split.** Medium/hard mock split: 66 medium / 50 hard = 1:0.76.

The hard-skewed preference (55/45 or 60/40 medium/hard per the platform contract) would target closer to 1:0.87. The observed 1:0.76 skew toward medium is explained by two factors: (1) Statistics easy questions are practice-only by design (0 easy mock), so the full 116 mock-only budget spans only medium and hard; (2) the Statistics hard difficulty covers highly combinable families (Bayesian, ANOVA, survival analysis, multiple testing) but has fewer family-pair recombination surfaces than medium, where the 13 families span wider conceptual distances. The 1:0.76 ratio is within acceptable bounds — it is not a quality failure, and further hard authoring would risk cloning the existing 50-question hard pool.

**Family coverage (mock-only floor ≥4 per applicable tier):**

| Family | Status |
|---|---|
| descriptive statistics | ✓ |
| bayesian inference | ✓ |
| probability & combinatorics | ✓ |
| distributions | ✓ |
| sampling & central limit theorem | ✓ |
| confidence intervals & estimation | ✓ |
| hypothesis testing | ✓ |
| errors & power | ✓ |
| multiple testing & correction | ✓ |
| correlation, regression & causality | ✓ |
| experimental design (within stats) | ✓ |
| variance decomposition & ANOVA | ✓ |
| survival analysis & time-to-event | ✓ |

`_TAXONOMY_VALIDATED_TRACKS` includes `"statistics"` — all concept tags are fully validated against the registry.

**No mock-only realism families** (`MOCK_ONLY_REALISM_FAMILIES["statistics"] = set()`). Statistics' dual-subtype format (conceptual MCQ + numerical code execution) makes every reasoning lens directly gradeable; the SQL/Pandas "assessment lens" rationale does not transfer.

## Anti-patterns specific to Statistics

- **Mixing subtypes silently** — the user must know whether they're answering conceptual or numerical before they answer.
- **Pure formula-recall questions** — "what's the formula for standard error of the mean?" Test the *use* (when does SE matter, what does halving the sample size do to it) not the recall.
- **Numerical questions where the answer is a single magic number** — test the *process* (assertion-based test cases that check intermediate behavior, not just final value).
- **Conceptual questions with one obviously correct answer** — distractors must reflect real misconceptions (e.g. "p-value is the probability the null is true" is a real misunderstanding to refute).
- **Bayesian questions that punt on the prior** — pick a defensible prior and defend it; don't dodge the choice.

## JSON schema (conceptual subtype)

```json
{
  "id": 72018,
  "order": 11,
  "topic": "statistics",
  "type": "conceptual",
  "subtype": "conceptual",
  "difficulty": "medium",
  "title": "When does halving the sample size double the confidence interval width?",
  "description": "You computed a 95% confidence interval for the mean from a sample of 400 observations. Holding everything else constant, what's the closest description of what happens to the CI width if you re-compute from a sample of 100?",
  "options": [
    "It halves.",
    "It stays the same — the CI width depends on the population variance only.",
    "It doubles.",
    "It increases by a factor of 4."
  ],
  "correct_option": 2,
  "explanation": "CI width scales with the standard error, which scales as σ/√n. Going from n=400 to n=100 makes √n drop from 20 to 10 — a factor of 2 in standard error, hence a factor of 2 in CI width. (Option 0) reverses the relationship. (Option 1) confuses CI width with population variance; the CI explicitly accounts for sample size. (Option 3) confuses sample-size ratio (4×) with width ratio (2×).",
  "hints": [
    "CI width depends on standard error, which scales with sample size — but not linearly.",
    "Walk through the √n factor explicitly."
  ],
  "concepts": ["confidence intervals & estimation", "sampling & central limit theorem"]
}
```

## JSON schema (numerical subtype)

```json
{
  "id": 72021,
  "order": 13,
  "topic": "statistics",
  "type": "numerical",
  "subtype": "numerical",
  "difficulty": "medium",
  "title": "Bootstrap a 95% CI for the median",
  "description": "Given a list of observations, return a 2-tuple `(low, high)` for the 95% bootstrap percentile CI for the median. Use 2000 bootstrap resamples and `random.Random(42)` for determinism.",
  "starter_code": "def solve(observations: list[float]) -> tuple[float, float]:\n    # Your code here\n    pass",
  "expected_code": "def solve(observations: list[float]) -> tuple[float, float]:\n    import random, statistics\n    rng = random.Random(42)\n    n = len(observations)\n    medians = []\n    for _ in range(2000):\n        sample = [observations[rng.randint(0, n - 1)] for _ in range(n)]\n        medians.append(statistics.median(sample))\n    medians.sort()\n    return (medians[int(0.025 * 2000)], medians[int(0.975 * 2000)])",
  "solution_code": "<same as expected, annotated>",
  "explanation": "Percentile bootstrap: resample with replacement N times, compute the statistic on each resample, take the 2.5th and 97.5th percentiles of the bootstrap distribution. The `random.Random(42)` seed makes the test deterministic.",
  "test_cases": [
    {"input": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]], "expected": [3.5, 7.0], "tolerance": 0.5},
    {"input": [[10.0] * 20], "expected": [10.0, 10.0], "tolerance": 0.0}
  ],
  "public_test_cases": [
    {"input": [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]], "expected": [3.5, 7.0], "tolerance": 0.5}
  ],
  "hints": [
    "Bootstrap = resample with replacement, compute the statistic, repeat many times.",
    "The 95% percentile CI uses the 2.5th and 97.5th quantiles of the bootstrap distribution."
  ],
  "concepts": ["confidence intervals & estimation", "sampling & central limit theorem"]
}
```

Numerical subtype allowed imports (sandboxed): `math`, `statistics`, `numpy`, `random`, `collections`, `itertools`, `functools`, `decimal`, `fractions`, `operator`, `typing`. No `scipy`, no `pandas`, no I/O.

Test cases may include `tolerance` for floating-point or bootstrap-randomness tolerance.

## Verification before commit

```bash
# Conceptual:
# - Walk through each distractor and confirm it reflects a real statistical misconception
# - Confirm explanation refutes each wrong option

# Numerical:
cd backend && ../.venv/bin/python -c "
import json
q = json.load(open('content/statistics_questions/medium.json'))[INDEX]
exec(q['expected_code'])
for tc in q['test_cases']:
    result = solve(*tc['input'])
    tol = tc.get('tolerance', 0)
    expected = tc['expected']
    # match shape, then values within tol
    ...
print('All test cases pass')
"

python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/ -q -k statistics
```
