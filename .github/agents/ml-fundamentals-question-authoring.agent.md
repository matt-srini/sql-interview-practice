---
name: ml-fundamentals-question-authoring
description: Generate and improve ML Fundamentals interview questions for a FAANG-level data interview prep platform. MCQ / scenario / predict-output / debug; no code execution.
argument-hint: "e.g., 'generate 4 medium scenario questions on class imbalance' or '3 hard questions on training-serving skew' or 'improve this question: <paste JSON>'"
---

# ML Fundamentals Question Authoring Agent

Use this agent to generate new ML Fundamentals questions for the platform. Read [`docs/content-authoring.md`](../../docs/content-authoring.md) (authoritative) and the universal [`question-authoring.agent.md`](./question-authoring.agent.md) for cross-track guardrails — this file is the ML-Fundamentals specialization.

## Track overview

**Track:** `ml-fundamentals`
**Format:** MCQ / scenario / predict_output / debug
**Eval kind:** MCQ (no code execution — option selection only; `eval_kind="mcq"`, `unlock_profile="mcq"`, `in_mixed_mock=false`)
**ID space:** Easy `81001–81999` · Medium `82001–82999` · Hard `83001–83999`
**Content directory:** `backend/content/ml_fundamentals_questions/`

## Question schema

```json
{
  "id": 81001,
  "order": 1,
  "topic": "ml-fundamentals",
  "type": "mcq",
  "difficulty": "easy",
  "title": "Supervised vs Unsupervised: Choosing the Right Paradigm",
  "description": "Full question text — a concrete, realistic ML situation, not a definition prompt.",
  "options": [
    "Option A (a real misconception, ≥20 chars)",
    "Option B",
    "Option C",
    "Option D"
  ],
  "correct_option": 1,
  "explanation": "Why the correct option holds AND a paragraph per distractor explaining why it is wrong.",
  "hints": ["Directional hint (no answer term)", "Second hint"],
  "concepts": ["SUPERVISED VS UNSUPERVISED"]
}
```

Required: `id`, `order`, `topic` (`"ml-fundamentals"`), `type`, `difficulty`, `title`, `description`, `options` (exactly 4), `correct_option` (**0-indexed** int 0–3), `explanation`, `hints`, `concepts`.

Optional: `code_snippet` (string, shown in monospace above options — required for `predict_output`/`debug`), `scenario_context` (string lead-in paragraph — required for `scenario`), `mock_only` (bool, default false).

Allowed `type` values: `"mcq"`, `"scenario"`, `"predict_output"`, `"debug"`.

- `predict_output`: include a small, mentally runnable `code_snippet`; the candidate predicts what it produces (metric value, shape, or error).
- `debug`: `code_snippet` has exactly one realistic ML bug (leakage, wrong split, scaling on full data, metric misuse); the question asks for the root cause/fix.
- `scenario`: populate `scenario_context` with the situation; `description` poses the decision.

## Difficulty rules

- **Easy:** single concept family, one clear decision; distractors wrong for simple, clear reasons. Concepts: supervised vs unsupervised, overfitting diagnosis, bias-variance, data splitting, feature scaling necessity, cross-validation design, classification/regression metrics, loss-function selection, gradient-descent behavior, regularization effect.
- **Medium:** compose 2 families or a genuine tradeoff; tempting distractors. Ensemble strategy, class imbalance, dimensionality reduction, feature-importance interpretation, calibration, feature selection, missing-data strategy, hyperparameter sensitivity, boosting mechanics, clustering evaluation, data-leakage detection.
- **Hard:** multi-family judgment, ambiguous-by-design; distractors represent expert-level mistakes; all option strings ≥20 chars. NN design, gradient pathology, transfer-learning strategy, model monitoring, deployment constraints, interpretability tradeoff, training-serving skew.

Difficulty is reasoning depth, never trivia obscurity.

## Concept families (use these as concept tags)

```
SUPERVISED VS UNSUPERVISED   OVERFITTING DIAGNOSIS        BIAS-VARIANCE TRADEOFF
DATA SPLITTING STRATEGY      FEATURE SCALING NECESSITY    CROSS-VALIDATION DESIGN
CLASSIFICATION METRICS       REGRESSION METRICS           LOSS FUNCTION SELECTION
GRADIENT DESCENT BEHAVIOR    REGULARIZATION EFFECT        ENSEMBLE STRATEGY
CLASS IMBALANCE HANDLING     DIMENSIONALITY REDUCTION     FEATURE IMPORTANCE INTERPRETATION
MODEL CALIBRATION            FEATURE SELECTION STRATEGY   MISSING DATA STRATEGY
HYPERPARAMETER SENSITIVITY   BOOSTING MECHANICS           CLUSTERING EVALUATION
DATA LEAKAGE DETECTION       NEURAL NETWORK DESIGN        GRADIENT PATHOLOGY
TRANSFER LEARNING STRATEGY   MODEL MONITORING             DEPLOYMENT CONSTRAINTS
INTERPRETABILITY TRADEOFF    TRAINING-SERVING SKEW
```

Use 1–4 tags per question drawn from these families (easy questions are often a single family).

## Concept blocklist — FORBIDDEN as concept tags

`sklearn`, `tensorflow`, `pytorch`, `keras`, `xgboost`, `lightgbm`, `catboost`,
`random_forest`, `svm`, `pca`, `kmeans`, `adam`, `sgd`, `relu`, `sigmoid`,
`softmax`, `dropout`, `batchnorm`, `rmsprop`, `tanh`, `fit`, `predict`,
`transform`, `pipeline`, `cross_val_score`, `gridsearchcv`, `randomizedsearchcv`,
`roc_auc_score`, `f1_score`, `recall_score`, `precision_score`,
`logistic_regression`, `tsne`, `umap`

Library/API/algorithm names are too implementation-specific. Use the family names. The validator rejects blocklisted tags.

## Hint rules

| Difficulty | Min | Max |
|---|---|---|
| easy | 1 | 2 |
| medium | 2 | 3 |
| hard | 2 | 3 |

**First-hint leak patterns — NEVER appear in the first hint:**
`bias-variance`, `overfitting`, `underfitting`, `regularization`,
`cross-validation`, `gradient descent`, `ensemble`, `boosting`, `bagging`,
`data leakage`, `concept drift`, `training-serving skew`, `calibration`,
`SMOTE`, `SHAP`

The first hint frames the reasoning direction; later hints may name the mechanism.

## ID assignment rules

- IDs are append-only. Never reuse or renumber existing IDs.
- Check the current highest ID in the target difficulty file; assign the next sequential ID and `order`.
- Mock-only questions use `"mock_only": true` at the top of medium/hard ranges (after practice). **No mock-only at easy** by design.
- ML Fundamentals has no dedicated sample IDs — samples auto-slice from the first 3 practice questions per difficulty.

## Quality checklist per question

- [ ] `topic` is `"ml-fundamentals"`; `type` is one of the four allowed values
- [ ] Description is a concrete situation, not "what is the definition of X"
- [ ] 4 options; correct option definitively right; distractors are real misconceptions
- [ ] Explanation tells you why each distractor is wrong, not only why the answer is right
- [ ] `predict_output`/`debug` have a `code_snippet`; `scenario` has `scenario_context`; hard option strings ≥20 chars
- [ ] `concepts` 1–4 family tags, none blocklisted
- [ ] Hint count within min/max; first hint has no leak-pattern words
- [ ] Difficulty matches reasoning depth

## Workflow

1. Read the existing question files to find the next ID/order.
2. Author the requested questions following the schema exactly.
3. Append to the appropriate difficulty JSON file (do not rewrite the whole file).
4. Run `python scripts/validate_content.py` from `backend/` to verify.
5. Report the IDs and titles authored.
