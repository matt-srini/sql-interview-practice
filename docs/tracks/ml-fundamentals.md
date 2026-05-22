# ML Fundamentals Track

> **Authoring rule, no exceptions:** Every ML question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/ml_fundamentals_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working ML practitioner ships models that survive production. That requires more than choosing the right algorithm: it requires diagnosing **what went wrong, why, and what to change** — overfitting vs underfitting symptoms, leakage detection before it embarrasses you in prod, class-imbalance handling that doesn't game the metric, monitoring drift before customers tell you the model is broken. The ML track tests this diagnostic + decision skill. Reading a confusion matrix, naming the leakage, choosing the loss function for the business cost — these are the skills that separate "can run scikit-learn" from "can ship ML."

> *Datathink philosophy applied:* The candidate who lists three regularization techniques is everywhere. The candidate who reads a learning curve and says "this is high variance, regularization will help but feature pruning would help more given the dimensionality, and we should also recheck for leakage given the suspicious test gap" — that's the practitioner who builds models that don't quietly degrade.

## Modality

**Constructed reasoning, with selected code-adjacent cases.** No execution. MCQ / scenario / predict_output / debug.

Subtypes:
- **`mcq`** — conceptual question with concrete scenario context
- **`scenario`** — `scenario_context` carries the situation; description asks the decision
- **`predict_output`** — for cases where reading a small code snippet drives the diagnosis (e.g. "what does this train/test split do?")
- **`debug`** — broken ML pipeline; identify what's wrong

## ID range (TXNNN scheme)

`T=8` for ML.

| Difficulty | ID range | File |
|---|---|---|
| Easy | 81001–81999 | `backend/content/ml_fundamentals_questions/easy.json` |
| Medium | 82001–82999 | `backend/content/ml_fundamentals_questions/medium.json` |
| Hard | 83001–83999 | `backend/content/ml_fundamentals_questions/hard.json` |

ML samples are auto-sliced from the first 3 practice questions per difficulty.

## Difficulty vocabulary

| Tier | Reasoning depth | Topics |
|---|---|---|
| **Easy** | Single concept, unambiguous; one obvious right answer | Supervised vs unsupervised, overfitting basics, bias-variance intuition, train/test/val splits, basic scaling needs, classification metrics basics |
| **Medium** | Trade-off reasoning; distractors are tempting | Ensembles, class imbalance, dimensionality reduction, calibration, leakage detection, boosting mechanics, feature importance interpretation |
| **Hard** | Multi-factor production trade-offs; all distractors plausible | Neural network design choices, gradient pathology (vanishing / exploding), transfer learning, monitoring + drift detection, deployment constraints, training-serving skew |

### Representative scenarios per tier

Difficulty controls reasoning depth, never licenses algorithm-name trivia. Even easy questions test what a result *tells you*, not the calculation.

| Tier | Representative scenarios |
|---|---|
| **Easy** | Read a learning curve for over/underfitting · pick a metric for an imbalanced classifier · why feature scaling matters for a given model · supervised vs unsupervised for a stated task. One concept, one right answer. |
| **Medium** | Choose an imbalance strategy for a described dataset · spot leakage in a pipeline · interpret feature importance · calibration for a probability output. Trade-off with tempting distractors. |
| **Hard** | "95% in eval, 70% in prod — why?" (training-serving skew) · gradient pathology in a deep net · drift-monitoring choice · deployment latency/memory trade-off. Production-grade multi-factor judgement. |

## Concept arc (early → late)

| Tier | Progression |
|---|---|
| Easy | Supervised vs unsupervised → overfitting / bias-variance → train/test/val splits → feature scaling necessity → classification metrics (precision / recall / F1 / AUC) |
| Medium | Ensembles (bagging / boosting / stacking) → class imbalance handling → dimensionality reduction → calibration → leakage detection → boosting mechanics → feature importance interpretation |
| Hard | NN design → gradient pathology → transfer learning → monitoring + drift → deployment constraints (latency / memory / batch vs online) → training-serving skew |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → ML Fundamentals section](../concept-taxonomy.md#ml-fundamentals--concept-families).

29 families. Already-tight pre-existing registry (29 unique tags total in the bank).

## Authoring allocation matrix

| Question kind | Where | When |
|---|---|---|
| Practice easy | `easy.json` no `mock_only` | One concept, one right answer. Build vocabulary. |
| Practice medium | `medium.json` no `mock_only` | Trade-off; tempting distractors. |
| Practice hard | `hard.json` no `mock_only` | Production-grade multi-factor. |
| Mock-only medium | `medium.json` with `mock_only: true` | Real scenarios: "your model's recall dropped 15% last quarter, here's the symptom data, diagnose"; leakage cases anchored in plausible data setups; calibration debate framed under business cost. Heavy `DATA LEAKAGE DETECTION`, `MODEL MONITORING`, `TRAINING-SERVING SKEW`. |
| Mock-only hard | `hard.json` with `mock_only: true` | Deep-net / deployment / drift scenarios. `GRADIENT PATHOLOGY`, `DEPLOYMENT CONSTRAINTS`, `INTERPRETABILITY TRADEOFF`. |
| Mock-only chain | parent + 1–3 follow-ups | Pivots: scale (10× more training data), business rule (label def changes), data quality (10% noisy labels), edge case (rare class with 12 examples), performance (50ms latency budget), stakeholder (risk team blocks deployment). |

**Easy mock-only: never.** Easy is practice-only.

**Practice teaches, mock-only stress-tests transfer.** The difference is framing and production realism, not new concepts. A mock-only question recombines ML reasoning the practice bank already teaches at that difficulty (or lower), anchored in a fresh production or failure scenario; it must not clone an existing practice question and must not introduce a concept family the curriculum never taught. If a mock would need an untaught concept, author the practice question first.

## Anti-patterns specific to ML

- **Algorithm-trivia questions** — "which algorithm uses gradient descent?" Reject. Test what the *use* tells you, not the name.
- **Hard questions with obvious "use cross-validation" answer** — every senior practitioner knows CV; the question must drill into *which* CV strategy for *which* failure mode.
- **Questions that ignore the production angle** — at hard tier, "build a model that gets 95% accuracy" is not the test. The test is "this model gets 95% accuracy in eval but 70% in prod, why."
- **Confusion-matrix arithmetic dressed as ML reasoning** — calculating F1 from numbers is arithmetic, not ML. Test the *choice* of metric, not the calculation.
- **Bias-variance "which is which" recall** — test the *diagnostic reading* (here's a learning curve, what does it tell you).

## JSON schema

```json
{
  "id": 82014,
  "order": 9,
  "topic": "ml-fundamentals",
  "type": "scenario",
  "difficulty": "medium",
  "title": "Diagnose the source of a 5% train/test gap on a tabular boosting model",
  "scenario_context": "You trained an XGBoost classifier on a credit-risk dataset (200K rows, 60 features). 5-fold CV accuracy is 89%. Held-out test accuracy is 84%. Training accuracy on the full set is 99.5%. Feature importance shows the top feature is `application_timestamp` (with feature-importance gain 3× the next).",
  "description": "Which diagnosis best fits the symptoms?",
  "options": [
    "Classic high-variance overfitting; reduce model depth and add L2 regularization.",
    "Target leakage via the timestamp feature, which encodes time-since-default-event in a way that wouldn't be available at scoring time.",
    "Insufficient training data; the test set is in a different regime than train.",
    "Class imbalance; the model is overfitting to the majority class on train and underfitting the minority on test."
  ],
  "correct_option": 1,
  "explanation": "The smoking gun is `application_timestamp` as the top feature with 3× the gain of the next feature. In credit-risk datasets, time features often correlate with the *period* during which the label became known — meaning the feature partially encodes the outcome. The 99.5% train accuracy + 89% CV + 84% test pattern combined with the importance distribution is the canonical leakage signature: high train, decent CV (if the leakage is partially captured in folds), lower true test. (Option 0) — would explain a train/test gap but not the importance distribution; pure overfitting doesn't usually produce one massively dominant feature unless that feature contains leakage. (Option 2) — possible but doesn't explain the dominant timestamp feature. (Option 3) — class imbalance would affect train and test similarly, and would surface in precision/recall rather than top-line accuracy.",
  "hints": [
    "The train / CV / test gap pattern is informative, but the feature-importance distribution is the bigger clue.",
    "Why would a timestamp feature be the most important feature in a credit model? What information is it carrying?"
  ],
  "concepts": ["DATA LEAKAGE DETECTION", "FEATURE IMPORTANCE INTERPRETATION", "OVERFITTING DIAGNOSIS"]
}
```

Required:
- Exactly 4 options, each ≥ 20 characters.
- Explanation refutes every distractor.
- Scenarios include enough numerical / behavioural detail that the diagnosis is grounded, not hand-waved.

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k ml_fundamentals
```
