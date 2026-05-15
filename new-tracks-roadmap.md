# New Tracks Roadmap

Three new tracks to extend the platform toward data engineers and data analysts.
Ordered by implementation priority. Do not implement concurrently — complete one track end-to-end before starting the next.

---

## Implementation status

| Track | Status | Backend | Frontend | Content | Docs | Launched |
|---|---|---|---|---|---|---|
| Data Engineering Concepts | Not started | — | — | — | — | — |
| Data Modeling | Not started | — | — | — | — | — |
| Statistics & Probability | Not started | — | — | — | — | — |

**Status values:** `Not started` · `In progress` · `Content authoring` · `QA` · `Done`

Update this table as phases complete. "Launched" = date the track went live on production.

---

## Question formats available

| Format | Evaluation method | Existing infrastructure |
|---|---|---|
| MCQ | Option comparison | PySpark track — fully working |
| Predict-output / scenario | Option comparison | PySpark track — fully working |
| Debug (MCQ variant) | Option comparison | PySpark track — fully working |
| Python numerical | Subprocess sandbox + test cases | Python/Pandas track — fully working |
| SQL DDL validation | DuckDB execution | **Not yet built** — future option for Data Modeling |

**Key insight:** Stats & Probability can mix MCQ with Python-executor questions (reusing the Pandas/Python pipeline for numerical computation questions). DE Concepts uses pure MCQ/scenario like PySpark. Data Modeling starts MCQ, with SQL DDL as a future upgrade path.

---

## Track 1 — Data Engineering Concepts (ETL & Systems)

**Status:** `Not started`  
**Target audience:** Data engineers (primary), analytics engineers (secondary)  
**Format:** MCQ + predict-output + scenario + debug (same as PySpark — no new executor)  
**Question target:** ~80 questions — 30 easy / 30 medium / 20 hard  
**Slug:** `data-engineering` (`:topic` param value)  
**Started:** —  
**Launched:** —

### Why this track first

The single biggest gap for DE candidates. Nothing in SQL/Python/PySpark/Pandas tests pipeline architecture and operational judgment. This is a dedicated interview round at FAANG, with a large deterministic question space that maps directly to the MCQ format we already have.

### Content coverage

| Subtopic | Easy | Medium | Hard |
|---|---|---|---|
| ETL vs ELT fundamentals | ✓ | ✓ | |
| Idempotency & backfill design | ✓ | ✓ | ✓ |
| Orchestration (DAGs, retries, task deps) | ✓ | ✓ | ✓ |
| Schema evolution & compatibility | | ✓ | ✓ |
| Batch vs streaming tradeoffs | ✓ | ✓ | ✓ |
| Watermarking & exactly-once semantics | | ✓ | ✓ |
| Partitioning, clustering, pruning | ✓ | ✓ | ✓ |
| Data quality, SLAs vs SLOs, lineage | ✓ | ✓ | |
| Slowly Changing Dimensions (SCD types) | ✓ | ✓ | |
| Data lake vs warehouse vs lakehouse | ✓ | ✓ | ✓ |
| Cost optimization (file formats, compute) | | ✓ | ✓ |
| Incident response & observability | | | ✓ |

### Question formats breakdown (target)

- ~50% scenario ("Given this pipeline design, what happens when...?")
- ~30% predict-output ("This Airflow DAG has a dependency cycle — which task fails first?")
- ~20% debug ("This ELT job produces duplicates on retry — what is the root cause?")

### Implementation tasks

#### Phase 1 — Backend
- [ ] Create `backend/content/data_engineering_questions/` directory
- [ ] Create `easy.json`, `medium.json`, `hard.json` with question schema (mirror `pyspark_questions/`)
- [ ] Create `backend/data_engineering_questions.py` catalog loader (copy structure from `pyspark_questions.py`)
- [ ] Create `backend/routers/data_engineering_questions.py` with:
  - `GET /api/data-engineering/catalog`
  - `GET /api/data-engineering/questions/{id}`
  - `POST /api/data-engineering/submit` (option comparison, same logic as PySpark submit)
- [ ] Register router in `backend/main.py`
- [ ] Add `data-engineering` to unlock policy in `backend/unlock.py` (use PySpark thresholds — MCQ is lower effort)
- [ ] Add `data-engineering` to progress helpers in `backend/progress.py`
- [ ] Add 3 sample questions (1 per difficulty) with `sample: true`
- [ ] Extend `backend/routers/sample.py` to handle `data-engineering` topic
- [ ] Mock session support: add `data-engineering` to allowed tracks in `backend/routers/mock.py`

#### Phase 2 — Frontend
- [ ] Add `data-engineering` entry to `TRACK_META` in `frontend/src/contexts/TopicContext.js`
  - Label: "Data Engineering"
  - Icon/color: warm amber — distinct from PySpark's indigo
  - Description: "ETL pipelines, orchestration, streaming systems, and warehouse architecture"
- [ ] Add route `/practice/data-engineering` to `frontend/src/App.js` (copy PySpark pattern)
- [ ] Verify `MCQPanel.js` works as-is (it should — it's topic-agnostic)
- [ ] Add "Data Engineering" tile to `LandingPage.js` track grid
- [ ] Add sample tiles for `data-engineering` to `LandingPage.js` sample section
- [ ] Add `data-engineering` to `SidebarNav.js` track switcher
- [ ] Verify `TrackHubPage.js` renders correctly with new track metadata

#### Phase 3 — Content authoring
- [ ] Create `.github/agents/data-engineering-question-authoring.agent.md`
- [ ] Author 30 easy questions
- [ ] Author 30 medium questions
- [ ] Author 20 hard questions
- [ ] Validate all questions with `backend/scripts/validate_content.py`

#### Phase 4 — Learning paths
- [ ] Author `starter` path: "Pipeline Fundamentals" (ETL, idempotency, basic orchestration) — free tier
- [ ] Author `intermediate` path: "Advanced DE Systems" (streaming, SCD, cost, observability) — pro tier

#### Phase 5 — Docs & CLAUDE.md
- [ ] Add `data-engineering` track to content footprint table in `CLAUDE.md`
- [ ] Add to tech stack / track list in `CLAUDE.md`
- [ ] Update `docs/content-authoring.md` with DE Concepts concept coverage map and schema
- [ ] Update `docs/backend.md` with new API endpoints
- [ ] Update `docs/frontend.md` with new route and track metadata

### Launch gate checklist

Before marking this track as launched, all of the following must be true:

- [ ] All 80 questions authored and passing `validate_content.py`
- [ ] 3 sample questions live (1 per difficulty)
- [ ] Backend routes returning correct responses (catalog, question detail, submit)
- [ ] Unlock policy wired and tested manually (free/pro/elite gates)
- [ ] Track visible on landing page and in track switcher
- [ ] Mock interview integration working for this track
- [ ] Both learning paths published
- [ ] CLAUDE.md and all affected docs updated
- [ ] Commit pushed and deployed to production

---

## Track 2 — Data Modeling

**Status:** `Not started`  
**Target audience:** Data engineers (primary), analytics engineers, senior data analysts (secondary)  
**Format:** MCQ + scenario (no executor needed to start; SQL DDL validation is a future upgrade)  
**Question target:** ~70 questions — 25 easy / 25 medium / 20 hard  
**Slug:** `data-modeling`  
**Started:** —  
**Launched:** —

### Why this track second

Tested as a dedicated DE interview round. Complementary to DE Concepts — where DE Concepts covers operational/pipeline judgment, Data Modeling covers structural/architectural judgment. Also overlaps with the analytics engineer audience (dbt users). Clean MCQ question space with unambiguous correct answers.

### Content coverage

| Subtopic | Easy | Medium | Hard |
|---|---|---|---|
| Star vs snowflake vs galaxy schema | ✓ | ✓ | |
| Normalization (1NF, 2NF, 3NF) vs denormalization | ✓ | ✓ | |
| Fact and dimension table design | ✓ | ✓ | |
| Surrogate vs natural keys | ✓ | ✓ | |
| Slowly Changing Dimensions (SCD 1/2/3/4) | ✓ | ✓ | ✓ |
| Grain definition and fact table design | | ✓ | ✓ |
| Bridge tables and many-to-many relationships | | ✓ | ✓ |
| Partitioning and clustering strategy | ✓ | ✓ | ✓ |
| Schema design from business scenario | | ✓ | ✓ |
| Data lake vs warehouse vs lakehouse tradeoffs | ✓ | ✓ | ✓ |
| dbt model materialization strategy | | ✓ | ✓ |
| Referential integrity and constraint tradeoffs | | | ✓ |

### Question formats breakdown (target)

- ~40% pure MCQ ("Which schema type reduces storage redundancy at the cost of query complexity?")
- ~60% scenario ("An e-commerce company needs to track historical product prices — which SCD type is appropriate and why?")

### Future upgrade: SQL DDL evaluation

A richer question format — "design the schema for X as SQL DDL" — is technically possible by:
1. Running `CREATE TABLE` statements in DuckDB
2. Inserting test data via the question's `solution`
3. Running a validation query from the question spec to verify structure

This is a meaningful engineering investment. Not in scope for initial launch; note it here as the natural evolution.

### Implementation tasks

#### Phase 1 — Backend
- [ ] Create `backend/content/data_modeling_questions/` directory
- [ ] Create `easy.json`, `medium.json`, `hard.json`
- [ ] Create `backend/data_modeling_questions.py` catalog loader
- [ ] Create `backend/routers/data_modeling_questions.py` with:
  - `GET /api/data-modeling/catalog`
  - `GET /api/data-modeling/questions/{id}`
  - `POST /api/data-modeling/submit`
- [ ] Register router in `backend/main.py`
- [ ] Add `data-modeling` to unlock policy (`unlock.py`) — use PySpark thresholds
- [ ] Add `data-modeling` to progress helpers (`progress.py`)
- [ ] Add 3 sample questions (1 per difficulty)
- [ ] Extend `backend/routers/sample.py` for `data-modeling` topic
- [ ] Mock session support: add `data-modeling` to allowed tracks in `mock.py`

#### Phase 2 — Frontend
- [ ] Add `data-modeling` to `TRACK_META` in `TopicContext.js`
  - Label: "Data Modeling"
  - Description: "Schema design, normalization, dimensional modeling, and warehouse architecture"
- [ ] Add route `/practice/data-modeling` to `App.js`
- [ ] Add tile to `LandingPage.js`
- [ ] Add sample section to `LandingPage.js`
- [ ] Add to `SidebarNav.js` track switcher
- [ ] Verify `TrackHubPage.js` renders correctly

#### Phase 3 — Content authoring
- [ ] Create `.github/agents/data-modeling-question-authoring.agent.md`
- [ ] Author 25 easy questions
- [ ] Author 25 medium questions
- [ ] Author 20 hard questions
- [ ] Validate with `validate_content.py`

#### Phase 4 — Learning paths
- [ ] Author `starter` path: "Schema Design Basics" (star schema, normalization, surrogate keys) — free tier
- [ ] Author `intermediate` path: "Dimensional Modeling Deep Dive" (SCD, grain, bridge tables, dbt) — pro tier

#### Phase 5 — Docs & CLAUDE.md
- [ ] Update content footprint in `CLAUDE.md`
- [ ] Update `docs/content-authoring.md`
- [ ] Update `docs/backend.md`
- [ ] Update `docs/frontend.md`

### Launch gate checklist

- [ ] All 70 questions authored and passing `validate_content.py`
- [ ] 3 sample questions live (1 per difficulty)
- [ ] Backend routes returning correct responses (catalog, question detail, submit)
- [ ] Unlock policy wired and tested manually (free/pro/elite gates)
- [ ] Track visible on landing page and in track switcher
- [ ] Mock interview integration working for this track
- [ ] Both learning paths published
- [ ] CLAUDE.md and all affected docs updated
- [ ] Commit pushed and deployed to production

---

## Track 3 — Statistics & Probability

**Status:** `Not started`  
**Target audience:** Data analysts (primary), data scientists (secondary)  
**Format:** Mixed — MCQ for conceptual questions + Python executor for numerical computation questions  
**Question target:** ~80 questions — 28 easy / 28 medium / 24 hard  
**Slug:** `statistics`  
**Started:** —  
**Launched:** —

### Why this track third

Highest-frequency data analyst interview topic after SQL (tested in ~80% of DA interviews per InterviewQuery data). Python track infrastructure already handles numerical questions, so this is lower implementation cost than it appears — mostly content + routing.

### Two question subtypes

**Subtype A — Conceptual MCQ** (e.g., "What does a p-value of 0.03 mean?")
- Evaluated exactly like PySpark: `selected_option` vs `correct_option`
- No executor needed

**Subtype B — Numerical Python** (e.g., "Write a function that computes the 95% confidence interval for a sample mean given n, x̄, and σ")
- Evaluated exactly like Python algorithm track: test cases + expected outputs
- Uses existing `python_evaluator.py` sandbox
- Question JSON includes `function_signature`, `test_cases`, `starter_code`

The question JSON schema needs a `subtype` field: `"conceptual"` | `"numerical"`. The submit handler routes accordingly.

### Content coverage

| Subtopic | Format | Easy | Medium | Hard |
|---|---|---|---|---|
| Distributions (normal, binomial, Poisson, uniform) | MCQ | ✓ | ✓ | |
| Descriptive stats: mean, median, std, variance | MCQ + Python | ✓ | ✓ | |
| Confidence intervals | MCQ + Python | ✓ | ✓ | ✓ |
| Hypothesis testing, p-values, significance | MCQ + Python | ✓ | ✓ | ✓ |
| Type I / Type II errors | MCQ | ✓ | ✓ | |
| A/B test design & sample size calculation | MCQ + Python | | ✓ | ✓ |
| Correlation vs covariance | MCQ | ✓ | ✓ | |
| Bayesian probability & conditional probability | MCQ | ✓ | ✓ | ✓ |
| Simpson's Paradox | MCQ | | ✓ | ✓ |
| CLT (Central Limit Theorem) | MCQ | ✓ | ✓ | |
| Regression basics (R², residuals, overfitting) | MCQ | | ✓ | ✓ |
| Non-parametric tests (when normality fails) | MCQ | | | ✓ |
| Sampling methods & bias | MCQ | ✓ | ✓ | |

### Implementation tasks

#### Phase 1 — Backend
- [ ] Create `backend/content/statistics_questions/` directory
- [ ] Create `easy.json`, `medium.json`, `hard.json` — questions include a `subtype` field (`"conceptual"` | `"numerical"`)
- [ ] Create `backend/statistics_questions.py` catalog loader
- [ ] Create `backend/routers/statistics_questions.py` with:
  - `GET /api/statistics/catalog`
  - `GET /api/statistics/questions/{id}`
  - `POST /api/statistics/run-code` (for numerical subtype — delegates to `python_evaluator.py`)
  - `POST /api/statistics/submit` — routes to option comparison (conceptual) or Python evaluator (numerical) based on `subtype`
- [ ] Register router in `backend/main.py`
- [ ] Add `statistics` to unlock policy (`unlock.py`) — use code-track thresholds (mix of MCQ and Python)
- [ ] Add `statistics` to progress helpers (`progress.py`)
- [ ] Add 3 sample questions (1 per difficulty; mix subtypes)
- [ ] Extend `backend/routers/sample.py` for `statistics` topic
- [ ] Mock session support: add `statistics` to allowed tracks

#### Phase 2 — Frontend
- [ ] Add `statistics` to `TRACK_META` in `TopicContext.js`
  - Label: "Statistics"
  - Description: "Probability, hypothesis testing, A/B experimentation, and statistical reasoning"
- [ ] Add route `/practice/statistics` to `App.js`
- [ ] `QuestionPage.js` — extend topic-aware rendering to handle `statistics`:
  - `MCQPanel.js` for `subtype: "conceptual"` questions
  - `CodeEditor.js` + `TestCasePanel.js` for `subtype: "numerical"` questions
- [ ] Add tile to `LandingPage.js`
- [ ] Add sample section to `LandingPage.js`
- [ ] Add to `SidebarNav.js` track switcher

#### Phase 3 — Content authoring
- [ ] Create `.github/agents/statistics-question-authoring.agent.md` (covers both subtypes, with spec for how numerical questions include test cases)
- [ ] Author 28 easy questions (~70% MCQ / 30% numerical)
- [ ] Author 28 medium questions (~60% MCQ / 40% numerical)
- [ ] Author 24 hard questions (~50% MCQ / 50% numerical)
- [ ] Validate with `validate_content.py`

#### Phase 4 — Learning paths
- [ ] Author `starter` path: "Stats for Analysts" (distributions, confidence intervals, hypothesis testing) — free tier
- [ ] Author `intermediate` path: "Experimental Design & Inference" (A/B testing, Bayesian, regression) — pro tier

#### Phase 5 — Docs & CLAUDE.md
- [ ] Update content footprint in `CLAUDE.md`
- [ ] Update tech stack / track list in `CLAUDE.md`
- [ ] Update `docs/content-authoring.md` with Statistics concept coverage and dual-subtype schema
- [ ] Update `docs/backend.md`
- [ ] Update `docs/frontend.md`

### Launch gate checklist

- [ ] All 80 questions authored and passing `validate_content.py`
- [ ] 3 sample questions live (1 per difficulty)
- [ ] Backend routes returning correct responses (catalog, question detail, submit, run-code)
- [ ] `subtype` routing tested: conceptual submits go to option compare, numerical submits go to Python evaluator
- [ ] Unlock policy wired and tested manually (free/pro/elite gates)
- [ ] Track visible on landing page and in track switcher
- [ ] `QuestionPage.js` renders correct panel for both subtypes
- [ ] Mock interview integration working for this track
- [ ] Both learning paths published
- [ ] CLAUDE.md and all affected docs updated
- [ ] Commit pushed and deployed to production

---

## Cross-track considerations

### Unlock model
- DE Concepts and Data Modeling: use **PySpark thresholds** (higher easy baseline before medium unlocks, lower hard cap) — MCQ/scenario questions are quicker to answer
- Statistics: use **Python/Pandas thresholds** (lower easy baseline) — numerical questions take real effort

### Mock interview integration
- All three tracks should be available in MockHub track selector once launched
- DE Concepts + Data Modeling: natural fit for a 30-min "DE systems" mock session
- Statistics: natural fit for DA-focused mock (pair with SQL for a complete DA mock)
- Consider: "Data Analyst mock" preset (SQL + Statistics), "Data Engineer mock" preset (SQL + DE Concepts)

### Learning paths
- Each new track ships with exactly 2 paths: one `starter` (free) and one `intermediate` (pro) — matching the convention for existing tracks
- Starter paths act as unlock shortcuts (completing starter → all medium unlocked; completing intermediate → full hard cap unlocked)
