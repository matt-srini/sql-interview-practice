# Mock Interview Feature — Audit Tracker

**Created:** 2026-06-09 · **Status:** active remediation tracker · **Owner:** rolling

This is the working tracker for the comprehensive Mock-feature audit. It exists to (a) fix
findings one-by-one in priority order, and (b) serve as **self-contained handoff context** —
any entry below should let a fresh session (including a Sonnet handoff) act without re-deriving
the finding. Each entry carries file:line, firsthand evidence, root cause, a fix approach, and a
verification step.

**Durable rules still live in the SoT docs**, not here. When a fix lands, update the relevant SoT
in the *same* commit and flip the status in the table:

| Area | SoT doc |
|---|---|
| Mock contract, plan-tier matrix, chain atomicity, Interview Loop | `docs/features/mock.md` (canonical) |
| Benchmark invariants, blueprint, modality-mode mapping | `docs/specs/mock-benchmark-spec.md` |
| Practice modality matrix, eval kinds, subtypes | `docs/specs/practice-modality-spec.md` |
| Backend routes/behaviour | `docs/backend.md` |
| Frontend pages/components | `docs/frontend.md` |
| Why a decision/reversal was made | `docs/decisions/DECISIONS.md` |

> **Handoff note (Sonnet):** these are *code/UX fixes*, not question authoring — the question-authoring
> agent and its Sonnet model-gate do **not** apply. Do not touch any question/answer/hint/option content.
> If a task appears to require editing question JSON content fields, stop and flag it.

**Method of record:** 3 parallel tracing agents (backend selection/gating, frontend inventory, doc
cross-check) + firsthand mock runs by the auditor as Free (`matt.srini@gmail.com`), Pro
(`srinivas.assampally@gmail.com`), Elite (`admin@datathink.co`), pw `Test1234!`, on the dev stack
(frontend :5173, backend :8000). Every HIGH/material item below was reproduced firsthand; items
marked `[agent-located]` were located by a tracing agent and are code-cited but not independently re-run.

---

## Status board

Severity: **H** high · **M** medium · **L** low. Status: `TODO` · `WIP` · `DONE` · `WONTFIX`.

| ID | Sev | Status | Kind | Title |
|---|---|---|---|---|
| **A1** | H | DONE | code | Reload after finishing reverts to stale **active** session with a live timer |
| **A2** | H | DONE | code | Free **easy-only** benchmark bypassable via the **Mixed** difficulty |
| **A3** | H | DONE | code | Interview Loop payoff under-delivers (raw pivot token + `is_follow_up` lost + debrief ignores pivots) |
| C1 | H | TODO | doc+code | `company_filter` is a gated **phantom feature** (no UI, never applied; advertised in SoT) |
| C3 | M | TODO | code | Code-track benchmark submit leaks `correct` + `expected_result` mid-session |
| B1 | M | TODO | code | Free sees an **"Elite"** badge on the Pro-tier Custom drill card |
| B2 | M | DONE | code | Interview Loop summary titled **"Drill summary"** (fixed with A3) |
| B3 | M | TODO | code | History **"Time"** column shows the limit, not time used |
| B4 | M | TODO | code | Start button **enabled when `/access` fetch fails** (`accessState` null) |
| A4a | M | TODO | code | Blocked difficulty pills clickable but silently inert (no tooltip/why) |
| A4b | M | TODO | code | Locked mode cards clickable, silently switch mode with no upsell-at-click |
| A5a | M | TODO | code | Concept tags exposed on the live question (telegraphs the approach) |
| C4 | M | TODO | code | Discarded sessions don't count vs rate limits → create-discard cap reset |
| B7 | L | TODO | code | PySpark lobby blueprint shows a composition the backend doesn't serve |
| B5 | L | TODO | code | Elite analytics: network error indistinguishable from empty state |
| B6 | L | TODO | code | Mixed-track shows two Role selectors |
| B8 | L | TODO | code | Dead UI (`NO_MOCK_BANK_TRACKS` empty; first-run CTA hardcodes `/practice/sql`) |
| C5 | L | DONE | code | `is_follow_up` never persisted (root cause of A3) |
| C6 | L | TODO | code | `30min` legacy → generic "Invalid mode" instead of read-only message |
| C7 | L | TODO | code | Daily-cap `CURRENT_DATE` not explicitly UTC; TOCTOU on check→create |
| D2 | M | TODO | doc | `loop_summary` shape (dict vs list, missing fields); `accuracy` vs `accuracy_pct` across specs |
| D3 | M | TODO | doc | `readiness_scores`/`study_plan` live in dashboard insights, not mock analytics |
| D4 | L | TODO | doc | Discard chip window 60s (frontend) vs 120s (doc + server) |
| D5 | L | TODO | doc | Chain reclaim: spec schema says `reclaimed=TRUE`; code deletes the row |
| D6 | L | DONE | doc | Pivot-card spec says render `framing`; `framing` is only the type token (reconciled with A3) |
| **E1** | M | TODO | content+code+doc | `follow_up_dimension` drift: 16 chain children use non-canonical tokens; validator doesn't enforce the 7-list |

> Several IDs (A4a/A4b/A5a/A6/B-series/D-series) map to the original audit's lettered findings;
> the narrative report is preserved verbatim in the entries below.

---

## A — User / product experience (lead)

### A1 — `[H]` `[DONE]` Finishing a mock + refreshing shows a stale **active** session with a live countdown
- **Files:** `frontend/src/pages/MockSession.js` load effect (the `useEffect` keyed on `[id, isElite]`) + `initFromData`.
- **Evidence (firsthand):** Started benchmark 384 via the UI → finished it (server `status:completed`) → reloaded. Page rendered a fresh **active** benchmark — ticking timer (59:33→59:17, counting down on a completed session), empty editor, Q1 unsubmitted. A clean nav (`/mock/384?fresh=1`, no history state) correctly showed the "2/3 solved" summary.
- **Root cause:** On start, MockHub navigates with `location.state.sessionData` (`status:'active'`). React Router stores it in `history.state`, which **survives a full browser reload**. The load effect used it unconditionally and never reconciled against the server's now-`completed` status.
- **Why it matters:** Worst-case moment — a stressed candidate who refreshes their results page sees the interview apparently *reset* with a running clock (reads as data loss / broken).
- **Fix applied:** When `location.state.sessionData` exists, keep the optimistic instant paint but **also `GET /mock/:id` and re-init when `r.data.status !== sessionData.status`** (i.e. exactly when the cached nav state is stale). No-state loads (reloads, History "Review") already fetch fresh. Self-heals even if `status` is absent.
- **Verify:** start→finish→reload now shows the summary; start→(active)→reload still shows the active session with a correct timer; History "Review" still shows the summary.

### A2 — `[H]` `[DONE]` Free's "easy-only" benchmark bypassable via the **Mixed** difficulty
- **Files:** `backend/unlock.py` `compute_mock_access` free+benchmark branch.
- **Evidence (firsthand):** As Free, `access.medium.can_start=false` ("Medium and hard benchmarks require a Pro plan") but `access.mixed.can_start=true`. Starting a Mixed SQL benchmark returned **200** and drew a **medium** question (id 12001) next to two easy. UI: the Mixed pill was selectable and left **Start enabled with no block**.
- **Blast radius (precise):** Leaked questions are **practice-pool only** — `_pool_for_track` gates `mock_only` behind Pro/Elite independently, so the premium mock bank is **not** exposed. What leaks: (a) the easy-only spec is violated for Free, (b) the medium/hard→Pro upsell is bypassed. Scales with the user's practice-unlock progress.
- **Root cause:** the free benchmark guard checked `difficulty in ("medium","hard")`, omitting `"mixed"`.
- **Fix applied:** guard on `difficulty != "easy"` (blocks medium, hard, mixed, and any future value) with an accurate message ("Medium, hard, and mixed benchmarks require a Pro plan."). **Backend-only** — the frontend's `getDifficultyButtonState` derives `blocked` purely from `access[diff].can_start`, so the Mixed pill, upgrade chip, and Start-disable all follow automatically.
- **Verify:** `/access` returns `mixed.can_start=false` for Free; starting a Free Mixed benchmark returns 403; Pro/Elite Mixed still allowed; new backend test added.

### A3 — `[H]` `[DONE]` Interview Loop's signature payoff under-delivers (the premium-value finding)
**Fixed 2026-06-09.** Shipped: shared `FOLLOW_UP_DIMENSIONS` map + `dimensionLabel()`/`dimensionBlurb()` in `frontend/src/mockModeConfig.js` (7 canonical dimensions + `_pivot`-less aliases + humanize-unknown fallback so a raw token never shows); pivot card now renders the human label as heading + a dimension-specific interviewer blurb (`MockSession.js`); post-mortem marks each follow-up with a "↩ Follow-up · {label}" chip (depends on C5); lobby per-dimension analytics use the label (`MockHub.js`); the Loop summary title is fixed (B2). `mock.md` pivot-card spec reconciled (D6). Verified live (Elite Loop): pivot card "Edge cases" + blurb, post-mortem "Interview Loop summary" + "↩ Follow-up · Edge cases", analytics "Business rules"/"Edge cases" — zero raw `_pivot` tokens. Deferred (separate picks): dimension-specific text inside the *backend* debrief narrative (the debrief stays concept-focused; the per-question chip + analytics carry the pivot signal) and the content/validator drift (E1).
Three confirmed defects compounded at the Elite payoff moment:
1. **Pivot card shows a raw enum token + generic copy.** Firsthand the card read "INTERVIEW LOOP · PIVOT / `business_rule_pivot` / The interviewer is shifting focus. This follow-up explores a different dimension of the same problem." The dimension is raw snake_case; the body is **identical for every pivot**. (`frontend/src/pages/MockSession.js` pivot card ~1238-1255, hardcoded.)
2. **`is_follow_up` never persisted** → post-mortem doesn't mark the follow-up (see C5). Firsthand: follow-up 12078 (`follow_up_dimension: business_rule_pivot`) reads `is_follow_up:false` from `GET /mock/:id` and `finish`; Elite summary showed Q1/Q2 with no ↩ badge.
3. **Per-session debrief never mentions the pivot** — shows the same concept breakdown a Pro drill shows; the dimension the Loop is built around appears only in lobby analytics (and there too as the raw token "business_rule_pivot 0%").
- **Fix approach:** (a) add a human-readable dimension label map (scale/business-rule/dirty-data/ambiguity/…) used by BOTH the pivot card and analytics; (b) persist `is_follow_up` (C5); (c) consider dimension-specific pivot copy and a per-dimension line in the Loop post-mortem. Reconcile with mock.md's pivot-card spec (D6) — `framing` is just the type token, so a label map is the right source, not `framing`.
- **Verify:** pivot card + analytics show friendly labels; Loop summary marks the follow-up and references the pivot dimension.

### A4a — `[M]` `[TODO]` Blocked difficulty pills are clickable but silently inert
- Free clicking Medium/Hard does nothing, no `title`/tooltip explaining why. Add an explanatory affordance (tooltip or inline note) at the point of interaction. `frontend/src/pages/MockHub.js` difficulty pills (~567-587).

### A4b — `[M]` `[TODO]` Locked mode cards clickable; silently switch mode with no upsell-at-click
- `MockHub.js:427` only short-circuits `card.disabled`, not `card.locked` — a Free user can click "Custom drill", land fully-configured in a mode they can't run. Premium pattern: surface the upgrade on click. (Related to B1.)

### A5a — `[M]` `[TODO]` Concept tags exposed on the live question
- `MockSession.js:937-943` renders concept tags during the active session, telegraphing the approach — in tension with the "reasoning, not recognition" positioning. Consider hiding during active mock sessions (still show in the post-mortem).

### A5b — `[L]` `[TODO]` Free benchmark time generous (60 min for 3 easy SQL) — realism tuning, optional.

### A6 — `[M]` `[TODO]` Harsh "0/X, Y% below your historical accuracy" headline tone
- Accurate but demoralizing on poor sessions for interview-week users. Consider a gentler frame when score is low. `MockSession.js` summary headline (~552-565).

**What works (do not regress):** one-shot/timed realism, freshness scoring + chain consumption (no repeats), the Pro→Elite summary differentiation, and the Elite *debrief content* (headline + patterns + deep-linked NEXT STEP).

---

## B — UI findings

### B1 — `[M]` `[TODO]` Free sees an **"Elite"** badge on the Pro-tier Custom drill card
- `frontend/src/pages/MockHub.js:436` — `{card.locked && <span ...>Elite</span>}` renders "Elite" for **any** locked card; Custom is locked for Free but is a **Pro** feature. The intended "Pro" badge (`:437-439`) only renders when `!card.locked`, so it never fires for Free (`card.locked = !isPro`). Net: Free is told Custom needs *Elite* (badge) while the text says *Pro or Elite* — mis-steers the upgrade.
- **Fix approach:** badge text should reflect the unlocking tier (Pro for custom, Elite for interview_loop). Drive from `card` config (e.g. `card.requiredTier`), not a hardcoded "Elite". Remove the dead `:437-439` branch.

### B2 — `[M]` `[TODO]` Interview Loop summary titled "Drill summary"
- `MockSession.js:538` — `summaryDescriptor.isBenchmark ? 'Benchmark summary' : 'Drill summary'`; Loop has `isBenchmark:false`. Add an explicit Interview-Loop title.

### B3 — `[M]` `[TODO]` History "Time" column shows the limit, not time used
- `MockHub.js:1064/1097/1125` — `formatDuration(s.time_limit_s, null)`. Pass actual `time_used_s` (the summary view already reads it). If history rows lack it, add to the history query.

### B4 — `[M]` `[TODO]` Start button enabled when `/access` fetch fails (`accessState` null)
- `MockHub.js:786-791` — guard `(accessState && !...can_start)`; null short-circuits to enabled. Treat null/failed access as not-startable (or show an explicit retry).

### B5 — `[L]` `[TODO]` Elite analytics: network error indistinguishable from empty state `[agent-located]`
- `MockHub.js:925-927` — `analytics` is null on both initial state and `.catch`. Add a distinct error+retry state.

### B6 — `[L]` `[TODO]` Mixed-track shows two Role selectors `[agent-located]`
- `MockHub.js:526-547` (top filter, has "All") + `:591-620` (mixed-specific, no "All") render together; redundant, two "Role" labels.

### B7 — `[L]` `[TODO]` PySpark lobby blueprint shows a composition the backend doesn't serve
- `MockHub.js:43-45` `PYSPARK_FORMAT_TARGETS` (display-only, used at `:67`) diverges from backend selection/`mock.md`: frontend easy = `conceptual×3 + predict_output×2 + debug×1` and medium includes `optimization`; backend easy = `predict_output×3 + conceptual×2 + debug×1`. Confirmed firsthand. Align the display constant to the backend targets.

### B8 — `[L]` `[TODO]` Dead UI `[agent-located]`
- `MockHub.js:25` `NO_MOCK_BANK_TRACKS = new Set()` makes the "no mock bank" note (`:624-628`) unreachable; first-run "Warm up in SQL" CTA (`:1180`) hardcodes `/practice/sql` regardless of selected role/track. Remove dead code; route the CTA to the selected track.

---

## C — Backend question-drawing / tier-correctness

**Correct (verified firsthand):** per-tier pool gating (Free no mock-only; Pro drew mock-only ids 12069/12074 + practice); chain atomicity + consumption (consumed chain 12077/12078 not re-served; a 2nd Loop drew 12079/12080) + 2-min reclaim (204); Interview Loop Elite-only; focus_concepts Elite-only; role required for Mixed; Pro 3/day independent benchmark+custom; Free 1/rolling-7-day; benchmark composition (backend) matches mock.md.

### C1 — `[H]` `[TODO]` `company_filter` is a gated **phantom feature**
- Accepted at `backend/routers/mock.py:115`; passed only to the access gate at `:1187`; **never referenced in `_select_questions`/`_pool_for_track`** (grep: zero `companies` in selection). **Zero `company` references in `MockHub.js`** (no UI). Meanwhile `docs/features/mock.md` §"Company Filter (Elite only)" (~361-365) describes a Company dropdown for SQL, lists 16 companies; the plan-tier matrix (`:134`) lists it as an Elite ✅ perk; the API ref (`:509`) documents the param.
- **Decision needed:** build it end-to-end (UI + apply `companies` filter in selection) **or** delete the param + gating + the SoT rows so Elite isn't sold an absent feature. Until decided, doc-drift + dead gating code.

### C3 — `[M]` `[TODO]` Code-track benchmark submit leaks `correct` + `expected_result` mid-session
- `backend/routers/mock.py:1453` — the "no correctness reveal mid-session" suppression applies **only when `eval_kind == "mcq"`**. Firsthand: SQL benchmark submit returned `correct`, `feedback`, **and `expected_result`** (the answer's output table) per question. Frontend doesn't display it, but it's transmitted — network inspection defeats one-shot integrity.
- **Fix approach:** for benchmark/interview_loop, strip `correct`/`feedback`/`expected_result` (and any solution-bearing fields) for **all** tracks, not just MCQ. Keep run-output (the user's own result) so "Run" still works; suppress the verdict + expected.

### C4 — `[M]` `[TODO]` Discarded sessions don't count vs rate limits → cap reset `[mechanism confirmed]`
- `discard_mock_session` hard-deletes the row (`backend/db.py` ~1384); counters `COUNT(*)` only surviving rows. A Pro user can create→discard (within 2 min) to recover a benchmark/custom slot and re-roll without burning quota.
- **Fix approach:** either count discarded sessions toward the cap (a `discarded` tombstone) or accept-and-document. Note the legitimate use (penalty-free re-roll within 2 min) when deciding.

### C5 — `[L]` `[DONE]` `is_follow_up` never persisted (root cause of A3.2)
**Fixed 2026-06-09.** The column already existed (db.py:204, migration `20260429`) — no migration needed. `create_mock_session`'s INSERT (db.py:1253-1255) now carries `is_follow_up`, and `start_session` sets it on the loop `selected` rows (parent False, follow-ups True); benchmark/custom default False. Regression test `test_interview_loop_follow_up_flag_persisted` added. Verified live: GET now returns `is_follow_up=true` for the follow-up.

### C6 — `[L]` `[TODO]` `30min` legacy → generic "Invalid mode"
- `MODE_CONFIGS` only contains `60min` (`mock.py:62-64`); `30min` isn't in `valid_start_modes`, so it returns "Invalid mode." rather than the legacy-specific copy `60min` gets. Cosmetic; both are correctly un-startable.

### C7 — `[L]` `[TODO]` Daily-cap `CURRENT_DATE` tz + TOCTOU `[agent-located]`
- `db.py:2314/2334` use `CURRENT_DATE` (server-tz, not explicitly UTC); no atomicity between usage check and `create_mock_session` (concurrent starts can exceed the cap). Not currently broken on UTC Railway.

---

## D — Doc / SoT drift

- **D1** — Company filter (see C1).
- **D2 `[M]`** `[agent-located]` `loop_summary`: code returns `per_dimension_performance` as a **dict** and omits `chains_completed`/`weakest_dimension`/`strongest_dimension`; both specs show a **list** with those fields. mock.md uses `accuracy_pct` (matches code); mock-benchmark-spec.md uses `accuracy` (stale) — the two specs contradict each other.
- **D3 `[M]`** `[agent-located]` `readiness_scores`/`study_plan` live in `/api/dashboard/insights`, not `/api/mock/analytics`; mock.md's analytics matrix row implies they're mock analytics.
- **D4 `[L]`** `[agent-located]` Discard chip: frontend offers the prompt for 60s (`MockSession.js:341`); doc + server use 120s — 60s UI dead zone.
- **D5 `[L]`** `[agent-located]` Chain reclaim: mock-benchmark-spec.md schema implies `reclaimed=TRUE`; code **deletes** the row (mock.md is right).
- **D6 `[L]` `[DONE]`** Pivot-card spec (mock.md §"Pivot card UX" + the Interview Loop walkthrough) said render the follow-up's `framing` text; `framing` is only the question *type* token ("scenario"). Reconciled 2026-06-09 to match the product: the card shows the human dimension label + a dimension-specific blurb from the 7-dimension taxonomy (via `mockModeConfig.js`), and the post-mortem marks follow-ups + uses human labels in analytics.

---

## E — Content / taxonomy consistency

### E1 — `[M]` `[TODO]` `follow_up_dimension` values drift from the canonical 7; validator doesn't enforce membership
- **Found during A3.** Across the mock chain children actually reachable in Interview Loop, 16 questions carry **non-canonical** `follow_up_dimension` tokens: the `_pivot`-less form of 6 of the 7 (`data_quality` ×4, `business_rule` ×3, `performance` ×3, `ambiguity` ×3, `edge_case` ×3, `stakeholder` ×1) and **`abstraction_pivot` ×2**, which is not one of the canonical 7 at all.
- **Doc/validator drift:** `docs/concept-taxonomy.md:1032` claims "Chain `follow_up_dimension` must be from the 7-dimension list. **Anything else crashes catalog load.**" — but `backend/scripts/validate_content.py:985` only checks that a chain child *has* a `follow_up_dimension`, not that it's one of the 7. So the claim is false and the drift went undetected.
- **Why it matters:** these tokens reach the Elite pivot card + per-dimension analytics. The A3 frontend humanizes them (so nothing renders raw), and per-dimension analytics now bucket `data_quality` and `data_quality_pivot` *separately* (they alias to the same label for display but the backend keys are distinct) — splitting what should be one dimension's stats.
- **Fix approach (separate pick — content edits MUST go through the authoring agent):** (1) normalize the bank's `follow_up_dimension` values to the canonical 7 (`_pivot` form) via the question-authoring agent — and decide whether `abstraction_pivot` becomes an 8th canonical dimension (update concept-taxonomy.md) or is remapped; (2) add a real validator rule in `validate_content.py` enforcing membership in the canonical set (make concept-taxonomy.md:1032 true); (3) once the bank is clean, the backend can key analytics on the canonical set directly. Do NOT hand-edit question JSON.

---

## Fix log (append per landed change)

- **2026-06-09 — A1 + A2** — fixed on `main`.
  - A2: `backend/unlock.py` free benchmark guard `difficulty != "easy"` (+ message); closes the Mixed bypass. Added `backend/tests/test_11_mock.py` coverage.
  - A1: `frontend/src/pages/MockSession.js` load effect reconciles cached nav-state status against the server.
  - SoT: `docs/features/mock.md` clarified Free = easy-only (mixed included); `docs/decisions/DECISIONS.md` entry appended.
- **2026-06-09 — A3 + C5 (+ B2, D6)** — fixed on `main`. Sonnet implemented backend (C5) and frontend (A3) on disjoint files; Opus reviewed + verified live + wrote docs.
  - C5: `backend/db.py` + `backend/routers/mock.py` persist `is_follow_up` (column pre-existed; no migration). Test `test_interview_loop_follow_up_flag_persisted`.
  - A3: `frontend/src/mockModeConfig.js` `FOLLOW_UP_DIMENSIONS` + `dimensionLabel()`/`dimensionBlurb()` (aliases + humanize fallback); pivot card label-heading + dimension blurb, post-mortem "↩ Follow-up · {label}" chip, lobby analytics labels (`MockSession.js`, `MockHub.js`, `App.css`). B2 (Loop summary title) folded in. Unit tests added to `mockModeConfig.test.js`.
  - SoT: `docs/features/mock.md` pivot-card spec reconciled (D6 — label+blurb, not `framing`); `docs/decisions/DECISIONS.md` entry appended.
  - Spun off: **E1** (follow_up_dimension content/validator drift — needs the authoring agent).
