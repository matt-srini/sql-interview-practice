# Mock Modality Phase 0: Content Audit Foundation

Date: 2026-05-19
Owner lane: Phase 0 content lane (docs-only)
Scope: reasoning-heavy tracks only (PySpark, Data Engineering, Data Modeling, Statistics, ML Fundamentals, Experimentation)

## 1) Objective Of The Content Phase 0 Lane

Establish a frozen, evidence-backed content foundation for modality migration without changing question substance.

Phase 0 content-lane objective:
- inventory current question metadata patterns (`type`, `subtype`, `mock_only`) across reasoning-heavy tracks
- propose a canonical mapping from existing `type` patterns to `interaction_mode` aligned to approved modality specs
- identify ambiguity, shallow shape risk, and likely rewrite pressure without masking weaknesses via relabeling
- reconcile track status against concept-hook governance docs so unfinished audits are explicit
- classify follow-on work by track: metadata-only vs targeted rewrite vs likely net-new later

Non-goals in this phase:
- no question rewrites
- no question JSON edits
- no loader/product code changes

## 2) Proposed Mapping: Existing `type` Patterns -> Canonical `interaction_mode`

This mapping is designed to be deterministic in Phase 1 implementation while preserving track-level modality intent from `docs/specs/practice-modality-spec.md`.

| Existing metadata pattern | Canonical `interaction_mode` | Where this applies now | Rationale |
|---|---|---|---|
| `type = numerical` (Statistics) | `executable_problem_solving` | Statistics numerical questions | User writes/runs Python code with test cases. |
| `type = mcq` and `subtype = conceptual` (Statistics) | `constructed_reasoning` | Statistics conceptual questions | Non-executable analytical interpretation. |
| `type in {debug, predict_output, optimization}` (PySpark) | `code_adjacent_reasoning` | PySpark | Prompts test execution reasoning/debugging without Spark execution. |
| `type in {mcq, scenario}` (PySpark) | `code_adjacent_reasoning` (default) | PySpark | Track-level canonical modality is code-adjacent; these stems are mostly execution/behavior reasoning. |
| `type in {mcq, scenario}` (Data Engineering) | `constructed_reasoning` | Data Engineering | System-design and pipeline judgment framing, non-executable. |
| `type in {mcq, scenario}` (Data Modeling) | `constructed_reasoning` | Data Modeling | Schema/design tradeoff reasoning, non-executable. |
| `type = scenario` (ML Fundamentals, Experimentation) | `constructed_reasoning` | ML Fundamentals, Experimentation | Case analysis and decision reasoning dominate current bank. |
| `type = mcq` (ML Fundamentals, Experimentation) | `constructed_reasoning` (current default) | ML Fundamentals, Experimentation | Current stems are mostly conceptual judgment checks, not executable workflows. |
| `type in {debug, predict_output}` (ML Fundamentals) | `code_adjacent_reasoning` candidate tag for later selective uplift | ML Fundamentals (small subset) | Spec allows selected code-adjacent cases later; keep explicit candidate bucket. |
| `type in {debug, predict_output}` (Experimentation) | `constructed_reasoning` (current), `code_adjacent_reasoning` candidate later if stem quality supports | Experimentation (very small subset) | Current items remain primarily conceptual/causal reasoning despite debug/predict labels. |

Mapping guardrail:
- do not auto-promote weak answer-picking prompts into deeper modes without noting weakness and scheduling rewrite.

## 3) Track-By-Track Audit Summary (Reasoning-Heavy Tracks)

### PySpark

Current metadata inventory (127 total):
- `mcq`: 77
- `predict_output`: 22
- `scenario`: 16
- `debug`: 10
- `optimization`: 2
- mock-only: 21 (medium 11, hard 10)

Phase 0 reading:
- classification is mostly metadata-normalization, but quality pressure is high because `mcq` still dominates the bank.
- despite `mcq` prevalence, many stems are genuinely code-adjacent; this supports a metadata-first uplift in Phase 1.
- highest immediate risk is superficial rebrand: if copy changes to "reasoning" without improving thin API-trivia items, user-perceived depth will not improve.

### Data Engineering

Current metadata inventory (87 total):
- `mcq`: 50
- `scenario`: 37
- mock-only: 1 (hard scenario)

Phase 0 reading:
- modality is structurally consistent with constructed reasoning.
- medium/hard scenario presence is strong enough for metadata-first rollout.
- easy-tier MCQ density suggests targeted rewrite pressure for deeper systems judgment over definition recall.

### Data Modeling

Current metadata inventory (77 total):
- `mcq`: 38
- `scenario`: 39
- mock-only: 1 (hard scenario)

Phase 0 reading:
- near-even split of MCQ and scenario supports constructed-reasoning framing.
- hard tier already scenario-heavy, which aligns with desired interview realism.
- easiest rewrite opportunities are in definitional MCQ items where tradeoff reasoning can be strengthened later.

### Statistics

Current metadata inventory (105 total):
- `mcq`: 64 (all `subtype = conceptual`)
- `numerical`: 41 (all `subtype = numerical`)
- mock-only: 8 hard (6 conceptual MCQ, 2 numerical)

Phase 0 reading:
- this is already the cleanest hybrid metadata model in the six-track set.
- subtype is consistently populated and semantically aligned with modality families.
- main Phase 1 need is adding canonical `interaction_mode` in payloads, not content surgery.

### ML Fundamentals

Current metadata inventory (115 total):
- `scenario`: 52
- `mcq`: 56
- `predict_output`: 4
- `debug`: 3
- mock-only: 25 (12 medium, 13 hard)

Phase 0 reading:
- high scenario share supports constructed-reasoning framing.
- small `debug`/`predict_output` pool is a candidate set for later selected code-adjacent lane (per spec), but not broad enough to reframe the track today.

Phase 2 audit update (2026-05-19):
- hook-vs-bank audit is complete with gaps recorded; this track should no longer be treated as unaudited.
- strongest coverage clusters: bias-variance and overfitting, leakage and splitting, metrics and imbalance, ensemble reasoning, and production monitoring.
- recorded gaps: parametric vs non-parametric framing, inductive bias, encoding strategy, activation-function comparisons, batch normalization, attention/self-attention, and deeper PCA vs t-SNE vs UMAP treatment.
- shallow-but-present areas: AUC-ROC vs AUC-PR, dropout, and interpretability-method tradeoffs.

### Experimentation

Current metadata inventory (105 total):
- `scenario`: 68
- `mcq`: 30
- `predict_output`: 4
- `debug`: 3
- mock-only: 25 (all scenario)

Phase 0 reading:
- strongest constructed-reasoning shape among non-hybrid tracks due scenario dominance.
- small debug/predict subset is currently conceptual in nature; no forced code-adjacent promotion in Phase 1.

Phase 2 audit update (2026-05-19):
- hook-vs-bank audit is complete with gaps recorded; this track should no longer be treated as unaudited.
- broad hook coverage is strong enough to treat the taxonomy as mapped; all 22 concept families are represented somewhere in the current bank.
- strongest coverage clusters: experiment design and power, significance and multiple testing, SRM, network effects and holdouts, quasi-experimental methods, Bayesian experimentation, bandits, and variance reduction.
- recorded gaps: direct ratio-metric / delta-method coverage, deeper surrogate-vs-long-term metric validation, and broader control-vs-holdout / A/A nuance beyond a small foundation subset.

## 4) Explicit Track Classification: Metadata-Only vs Targeted-Rewrite vs Likely Net-New Later

Phase 0 content classification (for planning, not implementation in this phase):

### Metadata-only first pass
- Statistics (primary)

Reason:
- already strong `type` + `subtype` hybrid structure; low rewrite pressure relative to other reasoning-heavy tracks.

### Targeted-rewrite tracks (later phase)
- PySpark (high)
- Data Engineering (medium)
- Data Modeling (medium)
- ML Fundamentals (medium)
- Experimentation (medium)

Reason:
- all five can be metadata-labeled now, but each has detectable shallow-shape pockets that should be rewritten selectively instead of rebranded.

### Likely net-new-content later
- ML Fundamentals (medium-high)
- Experimentation (medium-high)
- PySpark (medium, mainly for advanced benchmark mix)

Reason:
- ML Fundamentals and Experimentation audits are now complete with recorded gaps, and both still have enough uncovered or shallow hooks to justify selective net-new work later.
- advanced mock-blueprint depth likely needs additional high-signal items after rewrite triage, not only retagging.

## 5) Concept-Hooks Reconciliation Summary

Cross-doc reconciliation summary (`docs/concept-hooks.md` + `docs/concept-expansion-plan.md`):

- PySpark: hooks present and prior gap analysis marked complete.
- Data Engineering: hooks present and prior gap analysis marked complete.
- Data Modeling: hooks present and prior gap analysis marked complete.
- Statistics: hooks present and prior gap analysis marked complete.
- ML Fundamentals: audit completed 2026-05-19 with gaps recorded; follow-on work is targeted authoring, not hook-definition.
- Experimentation: audit completed 2026-05-19 with gaps recorded; follow-on work is targeted authoring, not hook-definition.

Critical governance note:
- ML Fundamentals and Experimentation no longer belong in the "unfinished audit" bucket; their recorded gaps should stay explicit in rollout tracking so future authoring work is driven by evidence instead of being treated as generic backlog.

## 6) Advanced Mock-Only Hook Coverage Status And Remaining Expansion

Current status from `docs/concept-hooks.md`:
- advanced mock-only hook section exists only for Data Modeling, Data Engineering, and Statistics.

What is missing for future parity:
- no parallel advanced mock-only hook sections yet for PySpark, ML Fundamentals, or Experimentation.
- rollout plan explicitly calls out that advanced mock-only hook expansion currently covers only a subset and must be extended later.

Implication:
- current mock-only question inventory can continue operating, but automation-ready benchmark blueprinting is uneven until advanced-hook taxonomy is expanded across all mock-relevant tracks.

## 7) Flagged Shallow Or Misleading Question-Shape Categories (No Rewrites Performed)

These are audit flags only; no content was changed.

1. Definition-recall MCQ overuse in easy tiers
- seen most in Data Engineering and some Data Modeling easy banks
- risk: constructed-reasoning tracks feel like glossary checks instead of interview judgment

2. API-trivia PySpark prompts labeled as reasoning depth
- seen in portions of PySpark MCQ inventory
- risk: "code-adjacent reasoning" label can overpromise where stem demands only recall

3. Obvious-elimination option sets in some scenario/MCQ items
- seen across multiple reasoning tracks
- risk: test-taking heuristics can beat domain reasoning

4. Keyword-cued long scenarios with one dominant option
- seen in ML Fundamentals and Experimentation hard tiers
- risk: long stem length creates perceived depth without proportional decision ambiguity

5. Mixed intent hidden under same `type` value
- e.g., `mcq` includes both recall and true diagnostic reasoning in several tracks
- risk: coarse `type` alone is insufficient for UX language and mock blueprint quality control

6. Under-specified distinction between conceptual and code-adjacent micro-forms outside Statistics
- especially for small debug/predict subsets in ML Fundamentals and Experimentation
- risk: accidental mode drift if future metadata mapping is applied too mechanically

## 8) Recommendations: Phase 1 Vs Later Phases

### Phase 1 (execute now)
- implement metadata uplift only (no rewrites): expose canonical `interaction_mode` mapping from existing metadata.
- prioritize PySpark practice-language and payload uplift as first code-adjacent pilot.
- preserve Statistics hybrid behavior explicitly (`numerical` executable vs conceptual reasoning).
- add audit-safe caveat in implementation notes: relabeling does not imply quality closure.

### Later phases (after Phase 1 stabilization)
- run targeted rewrite queue for flagged shallow categories, starting with PySpark high-priority items and easy-tier DE/DM definition-heavy items.
- complete ML Fundamentals and Experimentation hook-vs-bank audits before any "coverage complete" claim.
- expand advanced mock-only hooks to all mock-relevant tracks (at minimum PySpark, ML Fundamentals, Experimentation) to support robust benchmark composition.
- evaluate net-new content only after targeted rewrites, using hook coverage and mock blueprint gaps as explicit entry criteria.

## Source Files Audited

- `docs/mock-modality-rollout-plan.md`
- `docs/specs/platform-north-star.md`
- `docs/specs/practice-modality-spec.md`
- `docs/specs/mock-benchmark-spec.md`
- `docs/concept-hooks.md`
- `docs/concept-expansion-plan.md`
- `backend/content/pyspark_questions/easy.json`
- `backend/content/pyspark_questions/medium.json`
- `backend/content/data_engineering_questions/easy.json`
- `backend/content/data_engineering_questions/medium.json`
- `backend/content/data_modeling_questions/easy.json`
- `backend/content/data_modeling_questions/medium.json`
- `backend/content/statistics_questions/easy.json`
- `backend/content/statistics_questions/hard.json`
- `backend/content/ml_fundamentals_questions/medium.json`
- `backend/content/ml_fundamentals_questions/hard.json`
- `backend/content/experimentation_questions/medium.json`
- `backend/content/experimentation_questions/hard.json`
