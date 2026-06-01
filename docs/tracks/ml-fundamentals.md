# ML Fundamentals Track

> **Authoring rule, no exceptions:** Every ML question is created or modified via [`.github/agents/question-authoring.agent.md`](../../.github/agents/question-authoring.agent.md). Direct edits to `backend/content/ml_fundamentals_questions/*.json` bypass the difficulty arc and the concept-taxonomy registry.

## What this track trains

A working ML practitioner ships models that survive production. That requires more than choosing the right algorithm: it requires diagnosing **what went wrong, why, and what to change** — overfitting vs underfitting symptoms, leakage detection before it embarrasses you in prod, class-imbalance handling that doesn't game the metric, monitoring drift before customers tell you the model is broken. The ML track tests this diagnostic + decision skill. Reading a confusion matrix, naming the leakage, choosing the loss function for the business cost — these are the skills that separate "can run scikit-learn" from "can ship ML."

> *Datathink philosophy applied:* The candidate who lists three regularization techniques is everywhere. The candidate who reads a learning curve and says "this is high variance, regularization will help but feature pruning would help more given the dimensionality, and we should also recheck for leakage given the suspicious test gap" — that's the practitioner who builds models that don't quietly degrade.

## Modality

**Constructed reasoning, with selected code-adjacent cases.** No execution. Response: MCQ.

Question types:
- **`conceptual`** — conceptual question with concrete scenario context, evaluated via single-best-answer MCQ
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

ML Fundamentals has **dedicated sample questions** in `backend/content/sample_questions/ml_fundamentals.json` (IDs 811–813 easy, 821–823 medium, 831–833 hard). Sample questions are completely separate from the practice and mock pools and must never duplicate practice content.

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
| Hard | NN design → gradient pathology → transfer learning → monitoring + drift → deployment constraints (latency / memory / batch vs online) → training-serving skew → fairness diagnosis and metric selection |

## Concept families

Full registry: [`docs/concept-taxonomy.md` → ML Fundamentals section](../concept-taxonomy.md#ml-fundamentals--concept-families).

30 families. ALGORITHMIC FAIRNESS added 2026-05-26 (BIAS/FAIRNESS Phase 2.5); path (ii) preserved — fairness is practice-grounded, not a realism lens. `MOCK_ONLY_REALISM_FAMILIES["ml-fundamentals"]` remains empty.

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

## Coverage (Phase 2 complete — 2026-05-26; BIAS/FAIRNESS Phase 2.5 complete — 2026-05-26)

**Practice:** 100 questions (30 easy / 40 medium / 30 hard) · ratio 1.430×  
**Mock-only standalone:** 127 questions (0 easy / 59 medium / 68 hard)  
**Mock chains:** 8 chains — 8 parents (all hard, counted in the 68h standalone) + 16 children (all hard) = 24 chain-member slots  
**Mock-only total (standalone + chain children):** 143 (0e / 59m / 84h)

**Type mix (practice + mock-only combined):**

| Type | Practice | Mock-only standalone | Chain children |
|---|---|---|---|
| conceptual | 54 (54%) | 32 | 4 |
| scenario | 43 (43%) | 66 | 9 |
| debug | 4 (4%) | 16 | 2 |
| predict_output | 3 (3%) | 13 | 1 |

Note: all 7 BIAS/FAIRNESS Phase 2.5 questions are `scenario` type, raising practice scenario share (36→43) and mock standalone scenario share (62→66).

Mock-only intentionally skews toward scenario (66/127 standalones = 52%) and away from conceptual (32/127 = 25%, vs practice's 54% conceptual share) — production-realism framing in mock differentiates from the conceptual-heavy practice tier (the conceptual mock-only allocation is held down because conceptual mock would be hard to differentiate from practice conceptual without the full mock narrative).

**Chain dimensions used:** all 7 — data_quality_pivot ×3, business_rule_pivot ×3, ambiguity_pivot ×3, performance_pivot ×2, edge_case_pivot ×2, scale_pivot ×2, stakeholder_pivot ×1.

**Realism family decision (path ii):** No mock-only realism family. ML's curriculum already absorbs the realism lens via six pathology-flavoured families (`DATA LEAKAGE DETECTION`, `OVERFITTING DIAGNOSIS`, `MODEL MONITORING`, `TRAINING-SERVING SKEW`, `GRADIENT PATHOLOGY`, `DEPLOYMENT CONSTRAINTS`). `MOCK_ONLY_REALISM_FAMILIES["ml-fundamentals"] = set()` in `concept_families.py`.

**Sizing note:** The hard mock-only count (68 standalone, including 8 chain parents) landed above the original Stage B plan. Deviation sources from Phase 2: (a) 3 BOOSTING MECHANICS floor-fix questions (83084–83086); (b) chain children (16) are additional rather than pulled from the batch count — making the hard total additive; (c) Stage C remediation promoted 7 medium mock-only questions to hard (83119–83125). BIAS/FAIRNESS Phase 2.5 added 4 more hard standalone (83128–83131): Stage A planned 2 medium + 2 hard mock, but M4 (DEPLOYMENT CONSTRAINTS) and M5 (MODEL MONITORING) were escalated to hard because these families have no easy/medium practice coverage (rule 1), consistent with the track's difficulty vocabulary placing both as hard-tier concepts. The ratio 1.430× is within acceptable range.

## Verification before commit

```bash
python scripts/validate_content.py
cd backend && ../.venv/bin/python -m pytest tests/test_api.py -q -k ml_fundamentals
```
