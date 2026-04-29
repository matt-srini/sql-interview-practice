# Monetisation Restructuring + Mock Enhancement — Progress Tracker

Full implementation spec: `/Users/matt/.claude/plans/you-are-working-on-jazzy-summit.md`

---

## Phase A — Access gate changes
*Tighten free hard cap, gate dashboard coaching, fix PySpark count.*

- [x] `FREE_HARD_CAP_CODE = 8` in `backend/unlock.py` (was 15)
- [x] `FREE_HARD_CAP_PYSPARK = 5` in `backend/unlock.py` (was 10)
- [x] InsightStrip Tile 3 (weakest concept) gated behind Pro+ in `frontend/src/components/InsightStrip.js`
- [x] `totalQuestions: 102` for PySpark in `frontend/src/contexts/TopicContext.js` (was 90)
- [x] `pytest tests/ -q` passes with no regressions
- [x] This tracking file created

---

## Phase B — Mock infrastructure
*mock_only catalog separation, plan-split pool, freshness scoring, follow-up injection.*

- [x] `validate_content.py` — new rules for `mock_only`, `follow_up_id`, `framing`, `type: "reverse"`, `type: "debug"`
- [x] `backend/questions.py` — `_ALL_QUESTIONS` raw, `QUESTIONS` filtered, `_INDEX` covers all, `get_mock_questions_by_difficulty()` added
- [x] `backend/python_questions.py` — same changes
- [x] `backend/python_data_questions.py` — same changes
- [x] `backend/pyspark_questions.py` — same changes
- [x] Alembic migration: `is_follow_up BOOLEAN NOT NULL DEFAULT false` on `mock_session_questions`
- [x] `backend/db.py` — `get_previously_mocked_ids()` added
- [x] `backend/db.py` — `inject_follow_up_question()` added
- [x] `backend/db.py` — `get_mock_session()` includes `is_follow_up` in question payload
- [x] `backend/routers/mock.py` — `_pool_for_track()` rewritten with plan-split logic
- [x] `backend/routers/mock.py` — freshness scoring in `_select_questions()`
- [x] `backend/routers/mock.py` — follow-up injection in submit handler
- [x] `backend/tests/test_mock_pool.py` — full test suite (pool composition, freshness, catalog filter)
- [ ] `backend/tests/test_mock_session.py` — follow-up injection tests
- [x] `backend/tests/test_unlock.py` — cap tests already covered by existing test suite
- [x] `pytest tests/ -q` passes

---

## Phase C — Frontend changes
*MockSession renderers for debug, reverse SQL, scenario framing, follow-up UI.*

- [x] `frontend/src/pages/MockSession.js` — follow-up badge on question tab
- [x] `frontend/src/pages/MockSession.js` — follow-up banner (fade-in, 3s auto-dismiss)
- [x] `frontend/src/pages/MockSession.js` — scenario framing brief block (`framing === "scenario"`)
- [x] `frontend/src/pages/MockSession.js` — reverse SQL renderer (`type === "reverse"` → result table)
- [x] `frontend/src/pages/MockSession.js` — debug renderer (`type === "debug"` → error callout + pre-fill editor)
- [x] `frontend/src/pages/MockSession.js` — follow-up injection: re-fetches session on `follow_up_injected`
- [x] `frontend/src/App.css` — `.mock-follow-up-badge`, `.mock-follow-up-banner`, `.mock-scenario-brief`, `.mock-debug-error` added
- [x] Browser smoke test: existing mock flow unaffected (build clean, no JS errors)

---

## Phase D — Content authoring
*~105 new mock-only questions across 4 tracks. Run validate_content.py after each batch.*

### SQL (batch 1)
- [ ] ~19 mock-only medium questions (standard + reverse + debug)
- [ ] ~14 mock-only hard questions (standard + reverse + debug + scenario framing)
- [ ] 6 follow-up pairs authored
- [ ] `validate_content.py` passes clean

### Pandas (batch 2)
- [ ] ~10 mock-only medium questions (standard + debug)
- [ ] ~14 mock-only hard questions (standard + debug + scenario framing)
- [ ] 5 follow-up pairs authored
- [ ] `validate_content.py` passes clean

### Python (batch 3)
- [ ] ~8 mock-only medium questions
- [ ] ~12 mock-only hard questions (standard + scenario framing)
- [ ] 5 follow-up pairs authored
- [ ] `validate_content.py` passes clean

### PySpark (batch 4)
- [ ] ~10 mock-only medium questions (MCQ/predict_output + scenario type)
- [ ] ~10 mock-only hard questions (MCQ/predict_output + scenario type)
- [ ] 5 follow-up pairs authored
- [ ] `validate_content.py` passes clean

---

## Phase E — Landing page & pricing copy sync
*Update pricing bullets and pricing.md to reflect shipped plan gates.*

- [ ] `frontend/src/pages/LandingPage.js` — Free tier bullets updated (hard cap: 8 per track)
- [ ] `frontend/src/pages/LandingPage.js` — Pro tier bullets include fresh mock bank + weakest concept dashboard
- [ ] `frontend/src/pages/LandingPage.js` — Elite tier bullets accurate
- [ ] `docs/features/pricing.md` — plan-feature table updated
- [ ] Browser check: `/#landing-pricing` renders correctly

---

## Phase F — Docs sync
*Authoring spec, CLAUDE.md content footprint, authoring agents.*

- [ ] `docs/content-authoring.md` — mock-only question spec section added
- [ ] `CLAUDE.md` — content footprint table updated with Phase D counts
- [ ] `.github/agents/sql-question-authoring.agent.md` — mock-only spec added
- [ ] `.github/agents/python-question-authoring.agent.md` — mock-only spec added
- [ ] `.github/agents/pandas-question-authoring.agent.md` — mock-only spec added
- [ ] `.github/agents/pyspark-question-authoring.agent.md` — mock-only spec added
