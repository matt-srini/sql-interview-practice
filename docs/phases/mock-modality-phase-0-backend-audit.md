# Mock Modality Migration - Phase 0 Backend Audit

Status: completed (backend lane, docs-only)
Date: 2026-05-19
Scope: backend audit/foundation only, no product code changes

## 1) Objective of the backend Phase 0 lane

Freeze a backend-ready foundation for modality migration without changing runtime behavior yet.

The Phase 0 backend objective is to:
- map current control points for content metadata, public question payloads, mock composition, and dashboard/insights intersections
- identify the minimal additive contract surface needed for later phases (`interaction_mode`, subtype normalization/stabilization, and optional `eval_kind` exposure)
- predefine exact files/functions to change in Phase 1+ so implementation can be surgical and non-breaking

## 2) Current controlling code paths

### A. Content loaders and question metadata

Primary registry and routing of metadata:
- `backend/tracks.py`
  - `TrackConfig` fields currently controlling modality-adjacent behavior: `eval_kind`, `unlock_profile`, `in_mixed_mock`, `mixed_subtype`
  - `TRACKS`, `get_track()`, `mixed_mock_slugs()`

Per-track loader modules (authoritative content parsing + validation + public pre-submit question payload):
- `backend/questions.py` (SQL)
- `backend/python_questions.py` (Python)
- `backend/python_data_questions.py` (Pandas)
- `backend/pyspark_questions.py` (PySpark)
- `backend/data_engineering_questions.py`
- `backend/data_modeling_questions.py`
- `backend/statistics_questions.py` (hybrid: `subtype` enforced)
- `backend/ml_fundamentals_questions.py`
- `backend/experimentation_questions.py`

Common loader control functions (present across modules with track-specific rules):
- `_validate_question(...)`
- `get_public_question(question)`
- `get_questions_by_difficulty()`
- `get_mock_questions_by_difficulty()`
- `get_question(question_id)`

Current metadata state:
- `interaction_mode`: not implemented anywhere in backend code
- `type`: present for reasoning-heavy tracks and stats; used variably as question-form signal
- `subtype`: explicitly present only for statistics (`conceptual`/`numerical`)
- `eval_kind`: track-level only in `TrackConfig` (not exposed in public question payloads)

Supporting validator entrypoint:
- `backend/scripts/validate_content.py`
  - `_validate_statistics_subtypes()`
  - `_validate_mcq_scenario_questions()`
  - `_validate_mock_fields()`

### B. Public question serializers per track

#### SQL
- `backend/routers/questions.py`
  - `get_question_detail(...)` delegates payload build to `deps._question_detail_payload(...)`
- `backend/deps.py`
  - `_question_detail_payload(...)` uses `questions.get_public_question(...)`

#### Python and Pandas (executable)
- `backend/routers/python_questions.py`
  - `get_python_question_detail(...)`
- `backend/routers/python_data_questions.py`
  - `get_python_data_question_detail(...)`

#### Reasoning-heavy tracks
- `backend/routers/pyspark_questions.py`
  - `get_pyspark_question_detail(...)` (locked questions return stem-only without options)
- `backend/routers/data_engineering_questions.py`
  - `get_de_question_detail(...)`
- `backend/routers/data_modeling_questions.py`
  - `get_dm_question_detail(...)`
- `backend/routers/ml_fundamentals_questions.py`
  - `get_ml_question_detail(...)`
- `backend/routers/experimentation_questions.py`
  - `get_question_detail(...)`

#### Hybrid statistics
- `backend/routers/statistics_questions.py`
  - `get_statistics_catalog(...)` includes `subtype`
  - `get_statistics_question_detail(...)` includes both `type` and `subtype`

Catalog serializers:
- all per-track `get_*_catalog(...)` functions return per-question list metadata (`id`, `title`, `difficulty`, `order`, progress state, concepts)
- only statistics catalog currently adds subtype to list rows

### C. Mock composition and mock session payloads

Single control plane:
- `backend/routers/mock.py`

Core composition and payload functions:
- `_pool_for_track(...)`
  - merges unlock-eligible practice questions + mock-only pool (plan-sensitive)
- `_select_questions(...)`
  - track/difficulty-aware selection with focus-concept filtering and freshness
- `_sample_by_format(...)`, `_pyspark_format_targets(...)`
  - current format balancing based on `type` for MCQ-eval tracks
- `_sample_by_difficulty(...)`, `_mixed_difficulty_targets(...)`
- `_public_question_payload(...)`
  - central serializer for mock start/get/finish question payloads
- `_solution_payload(...)`
  - finish-only solution expansion
- `_evaluate_submission(...)`
  - dispatch by `track` + `get_track(track).eval_kind` + `mixed_subtype`

Endpoint surfaces affected by modality metadata in future phases:
- `POST /api/mock/start` -> `start_session(...)`
- `GET /api/mock/{session_id}` -> `get_session(...)`
- `POST /api/mock/{session_id}/submit` -> `submit_answer(...)`
- `POST /api/mock/{session_id}/finish` -> `finish_session(...)`

Important current behavior note:
- mock question payload already includes `type` (generic), and for MCQ-like branches also `question_type`
- this creates dual naming that should be stabilized when modality metadata is formalized

### D. Dashboard/insights payload intersections (modality-related only)

- `backend/routers/dashboard.py`
  - builds per-track totals from `_TOPIC_MODULES`
  - no modality fields in payload

- `backend/routers/insights.py`
  - uses `TRACKS` for track ordering/labels/module binding
  - builds concept and readiness analytics by track and submissions
  - no `eval_kind`, `subtype`, or modality fields returned today

- `backend/routers/mock.py` analytics endpoint
  - `get_analytics(...)` and `_compute_mock_analytics(...)`
  - track/difficulty/concept statistics only; no modality dimension

## 3) Minimal backend contract changes needed later

These are the minimal additive changes to support approved specs without redesigning current product behavior.

### A. `interaction_mode`

Needed later:
- add `interaction_mode` to reasoning/hybrid question content schema
- validate allowed values in each relevant loader (`_validate_question`) and validator script
- expose `interaction_mode` in public question payloads (practice detail + mock question payloads)

Compatibility guidance:
- additive only; keep existing `type` during migration
- clients can migrate to `interaction_mode` while legacy `type` remains available

### B. Subtype normalization/stabilization

Needed later:
- keep statistics `subtype` contract stable (`conceptual`/`numerical`)
- introduce consistent subtype conventions for reasoning tracks where needed (without forcing statistics semantics onto all tracks)
- stabilize naming collisions between `type` and `question_type` in mock payloads

Compatibility guidance:
- preserve existing fields while adding normalized subtype surface
- avoid changing correctness/evaluation semantics in Phase 1 metadata work

### C. `eval_kind` and modality exposure to frontend

Needed later (minimal):
- decide track-level exposure point for frontend modality logic (either explicit `eval_kind` or canonicalized derived metadata)
- keep per-question payload authoritative for rendering where question-level mode differs (notably hybrid statistics)

Compatibility guidance:
- prefer additive track metadata in catalog/start payloads rather than replacing existing fields

## 4) Exact files and functions likely to change in later phases

### Core registry and validation
- `backend/tracks.py`
  - `TrackConfig` (likely metadata extension)
  - `TRACKS` entries for modality metadata alignment
- `backend/scripts/validate_content.py`
  - `_validate_statistics_subtypes(...)`
  - `_validate_mcq_scenario_questions(...)`
  - likely new `interaction_mode` validation block

### Loader modules (per-track)
- `backend/pyspark_questions.py`
  - `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`
- `backend/data_engineering_questions.py`
  - `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`
- `backend/data_modeling_questions.py`
  - `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`
- `backend/ml_fundamentals_questions.py`
  - `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`
- `backend/experimentation_questions.py`
  - `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`
- `backend/statistics_questions.py`
  - `VALID_SUBTYPES`, `VALID_TYPES`, `_validate_question(...)`, `get_public_question(...)`

Potentially touched for consistency (if modality metadata becomes cross-track standard):
- `backend/questions.py`
- `backend/python_questions.py`
- `backend/python_data_questions.py`

### Practice serializers
- `backend/deps.py`
  - `_question_detail_payload(...)` (if SQL/practice envelope gets additional modality keys)
- `backend/routers/pyspark_questions.py`
  - `get_pyspark_catalog(...)`, `get_pyspark_question_detail(...)`
- `backend/routers/data_engineering_questions.py`
  - `get_de_catalog(...)`, `get_de_question_detail(...)`
- `backend/routers/data_modeling_questions.py`
  - `get_dm_catalog(...)`, `get_dm_question_detail(...)`
- `backend/routers/ml_fundamentals_questions.py`
  - `get_ml_catalog(...)`, `get_ml_question_detail(...)`
- `backend/routers/experimentation_questions.py`
  - `get_catalog(...)`, `get_question_detail(...)`
- `backend/routers/statistics_questions.py`
  - `get_statistics_catalog(...)`, `get_statistics_question_detail(...)`

### Mock composition/session serialization
- `backend/routers/mock.py`
  - `_select_questions(...)`
  - `_pyspark_format_targets(...)`
  - `_sample_by_format(...)`
  - `_public_question_payload(...)`
  - `_evaluate_submission(...)`
  - `start_session(...)`, `get_session(...)`, `finish_session(...)`

### Tests likely to require updates/additions
- `backend/tests/test_08_pyspark.py`
- `backend/tests/test_11_mock.py`
- `backend/tests/test_19_data_engineering.py`
- `backend/tests/test_20_data_modeling.py`
- `backend/tests/test_30_statistics.py`
- likely additions for ML Fundamentals and Experimentation serializer coverage

## 5) Risks, dependencies, and cross-lane alignment points

- Field drift risk:
  - current dual usage (`type`, `question_type`, `subtype`) can fragment frontend behavior if not normalized in one contract pass.

- Track inconsistency risk:
  - statistics already has hybrid subtype semantics; other reasoning tracks currently rely only on `type`.
  - migration must avoid implying executable behavior where none exists.

- Mock/practice divergence risk:
  - modality metadata must be aligned across practice detail payloads and mock payloads.

- Frontend dependency:
  - frontend lane needs stable additive fields and deprecation plan for `type`/`question_type` usage.

- Content dependency:
  - content lane must apply canonical `interaction_mode`/subtype vocabulary consistently in JSON banks.
  - validation rules in `backend/scripts/validate_content.py` should enforce vocabulary before rollout.

- Analytics dependency:
  - dashboard/insights currently have no modality dimension.
  - any modality-aware analytics in later phases require explicit schema decisions before frontend relies on them.

## 6) Focused validation commands for later backend phases

Run from repo root unless noted.

- Content schema and metadata validation
```bash
cd backend && ../.venv/bin/python scripts/validate_content.py
```

- Core unlock/catalog regression
```bash
cd backend && ../.venv/bin/python -m pytest tests/test_03_catalog.py tests/test_04_questions.py -q
```

- Track serializer/evaluator regressions
```bash
cd backend && ../.venv/bin/python -m pytest tests/test_08_pyspark.py tests/test_19_data_engineering.py tests/test_20_data_modeling.py tests/test_30_statistics.py -q
```

- Mock contract and session behavior
```bash
cd backend && ../.venv/bin/python -m pytest tests/test_11_mock.py -q
```

- Dashboard/insights regression guard
```bash
cd backend && ../.venv/bin/python -m pytest tests/test_12_dashboard.py -q
```

## 7) Recommendation: Phase 1 vs later phases

### Phase 1 (PySpark uplift) should do

- backend-only additive contract for PySpark modality metadata
- expose stable modality keys in PySpark practice detail and mock payloads
- keep existing evaluation flow and existing fields backward-compatible
- add/update targeted tests for payload shape and lock-state behavior

### Later phases should do

- generalize the same contract to Data Engineering, Data Modeling, ML Fundamentals, Experimentation, and conceptual statistics
- normalize subtype strategy and reduce `type` vs `question_type` ambiguity
- decide whether/how `eval_kind` is exposed publicly as track-level metadata
- only then extend modality dimensions into benchmark composition rules and analytics payloads

## Backend Phase 0 conclusion

Backend is structurally ready for additive modality metadata rollout: loaders, serializers, and mock composition are centralized enough to implement without broad refactor. The critical Phase 1 success factor is strict contract stabilization (field naming and backwards compatibility) before widening to all reasoning tracks.
