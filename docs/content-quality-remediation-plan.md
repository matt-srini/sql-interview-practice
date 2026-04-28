# Content Quality Remediation Plan

> Living document. Update the checkboxes and progress tracker as work lands.
> This doc is the hand-off contract for improving question quality, hinting, progression, and coaching claims. A future LLM should be able to resume by reading this file alone.

---

## 0. Purpose

This plan converts the audit findings into an implementation roadmap that can be shipped phase by phase.

The goal is not just to improve the question bank. The goal is to make the full product experience honest and defensible against the platform's premium claims:

- FAANG-level interview preparation
- real-world data interview scenarios
- instant feedback
- guided progression
- weak-spot insights
- paid-tier differentiation that feels earned

This plan assumes the current platform is already structurally stable:

- Question counts are correct.
- Catalog loading works.
- `backend/scripts/validate_content.py` passes.
- Unlock logic, learning paths, and mock access controls already exist.

The problems now are qualitative and product-level:

- concept tags are too syntax-level in several banks
- hint quality is uneven and often too implementation-specific
- the UI frames hinting as a multi-step scaffold, but the content rarely supports that ladder
- progression exists, but is mostly gating and path access, not adaptive coaching
- weak-spot insights exist, but are mostly frontend tallies over raw concept tags
- Python and PySpark do not consistently support the current premium positioning

---

## 1. Current Audit Summary

### Strongest areas

- SQL is the strongest premium-aligned track.
- Pandas is the strongest practical analytics-interview track.
- The learning-path catalog is real, structured, and worth preserving.
- The unlock model is coherent and better than random gating.
- The platform genuinely uses real datasets across SQL and Pandas.

### Weakest areas

- SQL and Pandas concept tags often violate the semantic-tag standard in `docs/content-authoring.md`.
- Python has good algorithm coverage but weak differentiation from generic coding-prep sites.
- PySpark has good conceptual content but too much MCQ-style evaluation and too little guided reasoning.
- Weak-spot insights are thinner than the pricing and landing-page copy imply.
- Hint quality varies by track and is especially weak in PySpark.

### Product-risk summary

- Free tier is credible.
- Pro tier is broadly defensible, especially for SQL + Pandas users.
- Elite is the least justified today because the incremental coaching layer is not deep enough yet.

---

## 2. Ground Truth Files

Any implementing agent should read these first before starting a phase:

- `docs/content-authoring.md`
- `backend/content/questions/*.json`
- `backend/content/python_questions/*.json`
- `backend/content/python_data_questions/*.json`
- `backend/content/pyspark_questions/*.json`
- `backend/content/paths/*.json`
- `backend/scripts/validate_content.py`
- `backend/routers/insights.py`
- `backend/unlock.py`
- `frontend/src/pages/QuestionPage.js`
- `frontend/src/pages/MockSession.js`
- `frontend/src/pages/LandingPage.js`
- `docs/features/pricing.md`

---

## 3. Operating Rules For Future LLMs

### Work phase by phase

- Do not mix unrelated phases in one pass.
- Finish the current phase fully before starting the next one.
- Tick every completed checkbox in this file as part of the same change.

### Preserve product truth

- If the product copy overclaims, either improve the feature or narrow the claim.
- Do not add marketing language first and hope the implementation catches up later.

### Prefer systemic fixes over scattered edits

- If a weakness affects all tracks, add validation or authoring rules, not just isolated content edits.
- If a weakness is caused by metadata shape, fix the metadata model and the validation script before doing large-scale rewrites.

### Validate every phase

- Run targeted validations after each phase.
- If a phase changes content rules, update `backend/scripts/validate_content.py` and `docs/content-authoring.md` in the same pass.
- If a phase changes user-facing claims or behavior, update `docs/README.md`, relevant feature docs, and `CLAUDE.md` when needed.

### Do not mark a phase complete unless all of these are true

- Code and content changes are landed.
- Docs are updated.
- Validation passes.
- The phase checklist in this file is updated.

---

## 4. Progress Tracker

- [x] Phase 1 - Concept Taxonomy Repair
- [x] Phase 2 - Hint System And Hint Content Overhaul
- [x] Phase 3 - Guided Progression Upgrade
- [x] Phase 4 - Weak-Spot Insights V2
- [ ] Phase 5 - Track-Specific Content Remediation
- [ ] Phase 6 - Pricing And Claim Realignment

---

## 5. Phase 1 - Concept Taxonomy Repair

**Goal:** Make concept tags useful for learning, progression, and diagnostics.

**Why this phase comes first:** The dashboard, mock weak-spot summary, drill links, and future adaptive progression all depend on concept tags. If the tags stay syntax-level, every downstream coaching feature stays shallow.

### Current problems

- SQL tags often use syntax labels like `GROUP BY`, `WHERE`, `COUNT`, `JOIN`.
- Pandas tags often use API labels like `groupby`, `merge`, `dropna`, `str accessor`.
- Some tags are semantically good, but the bank is inconsistent.
- Weak-spot insights currently treat all tags as equally meaningful.

### Deliverables

- A semantic tag standard that is concrete enough for automated validation.
- Updated concept tags across all 4 tracks.
- Validation rules that reject low-signal raw API tags except in narrowly allowed cases.
- Updated authoring docs with examples per track.

### Checklist

- [x] Define allowed concept-tag style by track in `docs/content-authoring.md`.
- [x] Add an explicit anti-pattern list for tags such as raw SQL clauses and raw pandas method names.
- [x] Decide whether any low-level tags remain allowed as secondary tags, and document that clearly.
- [x] Add validation to `backend/scripts/validate_content.py` for concept-tag quality.
- [x] Audit and rewrite SQL concept tags in `backend/content/questions/*.json`.
- [x] Audit and rewrite Python concept tags in `backend/content/python_questions/*.json`.
- [x] Audit and rewrite Pandas concept tags in `backend/content/python_data_questions/*.json`.
- [x] Audit and rewrite PySpark concept tags in `backend/content/pyspark_questions/*.json`.
- [x] Re-run validation and ensure no question is left with empty or single-word low-signal tags unless intentionally allowed.

### Implementation notes

- A good SQL tag is `COHORT RETENTION`, not `GROUP BY`.
- A good Pandas tag is `TIME-SERIES BUCKETING`, not `resample`.
- A good Python tag is `MONOTONIC WINDOW MAINTENANCE`, not `deque`.
- A good PySpark tag is `SHUFFLE BOUNDARY DETECTION`, not `repartition()`.
- Keep 2 to 4 tags per question where possible.
- Prefer stable mental-model tags over library-version-sensitive wording.

### Files most likely to change

- `docs/content-authoring.md`
- `backend/scripts/validate_content.py`
- `backend/content/questions/easy.json`
- `backend/content/questions/medium.json`
- `backend/content/questions/hard.json`
- `backend/content/python_questions/easy.json`
- `backend/content/python_questions/medium.json`
- `backend/content/python_questions/hard.json`
- `backend/content/python_data_questions/easy.json`
- `backend/content/python_data_questions/medium.json`
- `backend/content/python_data_questions/hard.json`
- `backend/content/pyspark_questions/easy.json`
- `backend/content/pyspark_questions/medium.json`
- `backend/content/pyspark_questions/hard.json`

### Acceptance criteria

- The top repeated tags in SQL and Pandas are mostly semantic patterns, not raw syntax.
- Weak-spot insight output would read like learner coaching, not parser terminology.
- `backend/scripts/validate_content.py` fails on obviously low-signal new tags.

### Validation

- `cd backend && ../.venv/bin/python scripts/validate_content.py`
- Run a small profiling script or targeted checks to inspect top repeated tags per track.
- Spot-check at least 5 questions per track after rewrite.

---

## 6. Phase 2 - Hint System And Hint Content Overhaul

**Goal:** Make hinting genuinely developmental instead of lightly staged reveal text.

**Why this phase comes second:** Once concepts are fixed, hints can ladder through better abstractions and point toward the right reasoning pattern.

### Current problems

- `QuestionPage.js` frames hints as `Conceptual hint`, `Approach hint`, `Structure hint`, `Final hint`, but the content rarely supplies that ladder.
- Many Python and Pandas hints reveal implementation too early.
- PySpark often has only one hint, which makes the stepper feel cosmetic.
- The authoring guide says hints should guide reasoning, but the banks are inconsistent.

### Deliverables

- A hint rubric per difficulty and per track.
- Rewritten hints across all banks using a consistent ladder.
- UI behavior that does not overpromise a four-step scaffold when only one or two hints exist.
- Optional validation heuristics for overly explicit hints.

### Checklist

- [x] Expand `docs/content-authoring.md` with a strict hint ladder by difficulty.
- [x] Define minimum hint counts by difficulty and track.
- [x] Decide whether PySpark easy can stay at one hint or must be upgraded to two.
- [x] Add validation heuristics for overly explicit hints in `backend/scripts/validate_content.py`.
- [x] Rewrite SQL hints to keep easy hints concept-first and hard hints structure-first.
- [x] Rewrite Python hints to avoid immediately naming the exact data structure unless needed.
- [x] Rewrite Pandas hints to reduce direct method leakage where a pattern hint would teach better.
- [x] Rewrite PySpark hints to focus on execution reasoning and distractor elimination.
- [x] Adjust `frontend/src/pages/QuestionPage.js` so the labels match the actual number and type of hints.
- [x] If needed, replace the fixed four-label array with dynamic labels derived from hint count and question metadata.

### Hint rubric to implement

#### Easy

- Hint 1: identify the mental model or operation class
- Hint 2: point to the concrete tool or transformation class

#### Medium

- Hint 1: identify the core pattern
- Hint 2: identify the subproblem split or intermediate representation
- Hint 3: identify the tool or control-flow shape if needed

#### Hard

- Hint 1: identify the decomposition strategy
- Hint 2: identify the dependency ordering or state representation
- Hint 3: identify the final assembly or constraint to watch

### Files most likely to change

- `docs/content-authoring.md`
- `backend/scripts/validate_content.py`
- all question JSON files under `backend/content/`
- `frontend/src/pages/QuestionPage.js`

### Acceptance criteria

- Hint progression feels real when used in the UI.
- At least sampled questions in every track move from reasoning to structure instead of from blank page to answer giveaway.
- PySpark no longer feels like it has an empty stepper for most questions.

### Validation

- `cd backend && ../.venv/bin/python scripts/validate_content.py`
- Manual spot-check in the workspace UI on 2 questions per track.
- Confirm the hint stepper labels still read naturally for questions with 1, 2, and 3 hints.

---

## 7. Phase 3 - Guided Progression Upgrade

**Goal:** Turn progression from mostly unlock logic into learning guidance.

**Why this phase comes third:** Once tags and hints are stronger, progression can route users based on meaningful concepts rather than just completed counts.

### Current problems

- Progression is real, but mainly threshold-based.
- Learning paths are strong, but the product does not consistently explain why a user should do a specific path next.
- Unlock messaging explains access, not remediation.
- There is no explicit bridge from weak areas to the most relevant path or question sequence.

### Deliverables

- Richer learning-path metadata.
- Track-aware next-step recommendations in the practice and dashboard surfaces.
- Better unlock copy that explains both the gate and the fastest route through it.
- Optional path metadata for concepts covered and recommended prerequisites.

### Checklist

- [x] Audit all files in `backend/content/paths/*.json` for curricular coherence.
- [x] Decide whether each path needs explicit `outcomes`, `focus_concepts`, and `recommended_after` metadata.
- [x] Extend path schema and loader if new metadata is added.
- [x] Update `docs/content-authoring.md` with path-authoring rules if schema changes.
- [x] Improve unlock and path recommendation copy in `backend/unlock.py` and the frontend surfaces that consume it.
- [x] Add a deterministic next-step recommender using solved state plus weak concepts.
- [x] Surface those recommendations in track hub, dashboard, or question page where they add the most value.
- [x] Ensure the recommendations do not conflict with free-tier access rules.

### Implementation notes

- Preserve the current starter and intermediate path shortcut behavior.
- Do not remove gating. Make it more legible.
- Recommendation priority should be:
  1. unresolved weak concept with an accessible path
  2. next unfinished starter or intermediate path
  3. next unlocked question in current track

### Files most likely to change

- `backend/content/paths/*.json`
- `backend/path_loader.py`
- `backend/unlock.py`
- `frontend/src/pages/TrackHubPage.js`
- `frontend/src/pages/ProgressDashboard.js`
- `frontend/src/pages/LearningPath.js`
- `frontend/src/pages/LearningPathsIndex.js`
- `docs/content-authoring.md`
- `docs/frontend.md`

### Acceptance criteria

- A user can see not just what is unlocked, but what to do next and why.
- Learning paths feel like curriculum, not a secondary catalog.
- Progression copy feels more like coaching and less like access control.

### Validation

- Manual walkthroughs for free, pro, and elite users.
- Confirm recommendations respect access boundaries.
- Validate path schema loading if metadata changes.

---

## 8. Phase 4 - Weak-Spot Insights V2

**Goal:** Make weak-spot analysis worthy of the premium coaching claim.

**Why this phase comes fourth:** It depends on stronger concept tags and more coherent path mapping.

### Current problems

- Dashboard insights are currently a compact aggregate over submission events.
- Mock-session weak-spot analysis is largely computed in the frontend from `questions[].concepts` and `is_solved`.
- The current output is useful but thin: it is mainly concept accuracy counts and a drill link.
- The landing page and pricing copy imply deeper analysis than the implementation currently delivers.

### Deliverables

- Backend-owned weak-spot insights that are more than a frontend tally.
- Better sample-size handling and confidence thresholds.
- Recommendations that point to paths or question clusters, not just practice routes.
- Copy that clearly states what the feature does today.

### Checklist

- [x] Decide which parts of concept analysis must move from frontend to backend.
- [x] Expand `backend/routers/insights.py` to return actionable recommendation objects, not just the bottom 3 concepts.
- [x] Add sample-size and recency logic so one bad session does not dominate results.
- [x] Decide whether to segment weak concepts by question difficulty.
- [x] Update mock summary UI to consume richer backend insight payloads.
- [x] Update dashboard UI to explain weak spots in plain English.
- [x] Fix misleading copy such as comparisons labeled `session average` when they are based on broader history.
- [ ] Revisit Elite pricing copy and landing copy once the feature is upgraded.
- [x] Add or expand backend tests for the new insight behavior.

### Suggested insight payload shape

Use a richer structure rather than only flat concept rows. Example:

```json
{
  "weakest_concepts": [
    {
      "concept": "COHORT RETENTION",
      "track": "sql",
      "attempts": 8,
      "correct": 3,
      "accuracy_pct": 0.375,
      "recommended_path_slug": "cohort-and-retention",
      "recommended_question_ids": [3005, 3011],
      "summary": "You usually set up the cohort correctly but lose accuracy when calculating follow-on month retention."
    }
  ]
}
```

### Files most likely to change

- `backend/routers/insights.py`
- `backend/tests/test_dashboard.py`
- `backend/tests/test_mock.py`
- `frontend/src/pages/MockSession.js`
- `frontend/src/pages/ProgressDashboard.js`
- `docs/features/dashboard.md`
- `docs/features/mock.md`
- `docs/backend.md`
- `docs/frontend.md`

### Acceptance criteria

- Weak-spot analysis reads like coaching, not a scoreboard.
- Elite gets a real qualitative upgrade over Pro.
- Mock summary and dashboard tell the same story using consistent data.

### Validation

- Backend test coverage for new insight shapes and thresholds.
- Manual checks with users who have sparse history and rich history.
- Verify drill links actually point to relevant accessible work.

---

## 9. Phase 5 - Track-Specific Content Remediation

**Goal:** Close the gaps that most undermine the premium positioning.

This phase is track-specific and should be executed in subphases.

### 5A - SQL cleanup

- [ ] Audit SQL easy questions against the documented easy-tier rules.
- [ ] Remove or reclassify any easy questions that violate the difficulty contract.
- [ ] Review SQL tag consistency after Phase 1.
- [ ] Review SQL hint quality after Phase 2.
- [ ] Remove any other low-value or repetitive SQL questions discovered during the audit.

### 5B - Python differentiation

- [ ] Audit the Python bank for overreliance on generic LeetCode classics.
- [ ] Decide the intended product position for Python: general interview track or data-role-specific coding track.
- [ ] If staying premium-data-focused, add more realistic data/engineering problem framing.
- [ ] Add questions about tradeoffs, data handling, or production-adjacent reasoning where appropriate.
- [ ] Rewrite overly generic problem statements so more of the bank reflects the platform philosophy.

### 5C - Pandas deduplication and polish

- [x] Remove or rewrite near-duplicate easy questions.
- [x] Review whether too many Pandas tags remain API-level after Phase 1.
- [x] Tighten easy and medium hints to teach patterns rather than method names where possible.

### 5D - PySpark format upgrade

- [x] Audit the balance of `mcq`, `predict_output`, `debug`, and `optimization` items.
- [x] Add more debug and diagnosis questions.
- [x] Add richer production-scenario framing to easy questions where they currently read like syntax quizzes.
- [x] Decide whether a new question format is needed beyond MCQ to better simulate interviews.
- [x] If a new format is added, update schemas, loaders, authoring docs, and frontend rendering.

### Files most likely to change

- all track content files under `backend/content/`
- `docs/content-authoring.md`
- `backend/scripts/validate_content.py`
- possibly frontend track renderers if PySpark format expands

### Acceptance criteria

- Python no longer reads like mostly generic algorithm practice.
- PySpark no longer feels mostly quiz-based.
- Duplicate and quality-drift issues are materially reduced.

### Validation

- `cd backend && ../.venv/bin/python scripts/validate_content.py`
- Add content-focused tests if schema or format changes.
- Spot-review a representative sample from every track and difficulty after edits.

---

## 10. Phase 6 - Pricing And Claim Realignment

**Goal:** Align what the site promises with what the product actually delivers after the earlier phases land.

**Important:** Do not start this phase early unless a claim is clearly false and harmful today.

### Current product-copy risks

- `Weak-spot insights after every session` currently sounds deeper than the implementation.
- `guided progression` is directionally true, but currently more path-and-unlock driven than adaptive.
- Elite differentiation is not yet strong enough in the current coaching layer.

### Deliverables

- Updated landing copy.
- Updated pricing copy.
- Updated feature docs.
- A clear decision on whether Elite is repriced, re-scoped, or upgraded further.

### Checklist

- [ ] Re-audit the product after Phases 1 to 5 are complete.
- [ ] Decide whether Free, Pro, and Elite value boundaries still make sense.
- [ ] Update `frontend/src/pages/LandingPage.js` to narrow or strengthen claims accordingly.
- [ ] Update `docs/features/pricing.md`.
- [ ] Update any related feature docs and `CLAUDE.md` if product behavior changes.
- [ ] Ensure company-filter messaging accurately reflects actual coverage by track.

### Decision framework

Choose one of these paths explicitly:

- Improve Elite until the current price is defensible.
- Narrow Elite claims and preserve price.
- Lower Elite price or compress the gap to Pro.
- Re-segment feature access between Pro and Elite.

### Acceptance criteria

- Pricing copy is truthful.
- Elite has a clear, concrete, user-visible advantage.
- No premium claim depends on interpretation or hidden caveats.

### Validation

- Manual copy audit of landing page and pricing doc.
- Spot-check every premium claim against implementation.

---

## 11. Suggested Execution Order Inside Each Phase

Use this sequence unless the phase requires a different order:

1. Update the docs and validation rules first.
2. Update the underlying content or code model.
3. Update the UI behavior or API payloads.
4. Run validation.
5. Tick completed boxes in this file.

---

## 12. Fast Wins That Can Be Pulled Forward Safely

These can be done earlier if needed without destabilizing the roadmap:

- fix SQL easy questions that clearly violate documented difficulty rules
- remove duplicate Pandas easy questions
- fix misleading UI copy like `session average` when it references broader history
- improve weak-spot marketing copy before the deeper backend work lands
- improve PySpark hint counts without changing the format model yet

If one of these lands early, update the relevant phase checklist rather than creating an untracked side path.

---

## 13. Done Criteria For The Whole Plan

The plan is complete only when all of the following are true:

- Every phase checkbox in the progress tracker is checked.
- The content authoring guide matches the actual quality bar.
- Weak-spot analysis is clearly useful and materially better than simple concept counting.
- Guided progression feels like coaching, not just unlock gating.
- Python and PySpark no longer weaken the premium positioning.
- Landing and pricing copy are fully defensible.

---

## 14. Progress Log

Update this section whenever a phase or subphase lands.

- 2026-04-27: Plan created from the full content, hinting, progression, and coaching audit. No remediation work shipped yet.
- 2026-04-27: Phase 1 completed. Added explicit semantic concept-tag rules to `docs/content-authoring.md`, added concept-tag validation to `backend/scripts/validate_content.py`, and rewrote low-signal concept tags across all four question banks until `scripts/validate_content.py` passed again.
- 2026-04-27: Phase 3 completed. Added `focus_concepts`, `outcomes`, and `recommended_after` to all 22 path JSONs. Extended `routers/paths.py` to return new fields. Upgraded `routers/insights.py` to attach `recommended_path_slug` / `recommended_path_title` to each `weakest_concepts` entry (concept→path index, starter paths preferred). TrackHubPage now sorts paths by role order (starter → intermediate → advanced, incomplete before complete) and labels the first recommended path. PathProgressCard accepts `recommendationLabel` prop. InsightStrip links weak concept to its recommended path when available. Docs updated in `content-authoring.md`, `backend.md`, `frontend.md`.